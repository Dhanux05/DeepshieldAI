# Phase 11 — async prediction pipeline (Celery + Redis)

## Why this phase exists

Before this phase, `POST /predictions/analyze/{document_id}` ran the
detector inline, inside the request handler, and the client waited for the
whole thing. That's invisible for Image or the XGBoost bot detector (well
under a second), but Audio (wav2vec2) and Video (16-frame R3D-18) routinely
take several seconds on CPU-only hardware. Uvicorn's default worker handles
one request at a time — a slow Video analysis blocked every other request
to the API for its entire duration, including a different user just trying
to load their dashboard.

## Architecture

```
Client                    FastAPI                     Redis            Celery worker
  |                          |                           |                    |
  |--- POST /analyze/{id} -->|                           |                    |
  |                          |-- create Prediction ------|                    |
  |                          |   (status="Processing")   |                    |
  |                          |-- enqueue task ---------->|                    |
  |<-- 202 + Processing -----|                           |--- pop task ------>|
  |                          |                           |                    |-- registry.get_detector()
  |   (client polls)         |                           |                    |-- detector.predict()
  |--- GET /predictions/id ->|                           |                    |-- update row
  |<-- still "Processing" ---|                           |                    |   (Completed/Failed)
  |         ... repeats every 1.5s ...                   |                    |
  |--- GET /predictions/id ->|                           |                    |
  |<-- "Completed" + result -|                           |                    |
```

The FastAPI process and the Celery worker process never talk to each other
directly — they communicate only through the `predictions` table (Postgres)
and the task queue (Redis). This is deliberate: it's what makes it safe to
restart either one independently, and to run more than one worker later
without anyone having to change the API.

## Design decisions

**Redis as broker only, no result backend.** Celery supports storing a
task's return value in a "result backend" (often Redis too). This project
doesn't configure one — the `predictions` table already IS the durable
record of a task's outcome (`processing_status`, `predicted_label`,
`confidence_score`, ...). A result backend would just be a second place
that record could live, and the two could disagree. See
`backend/app/core/celery_app.py`.

**Models load once per worker process, not once per task.** A Celery worker
is a separate OS process from `uvicorn`. It does not share the `registry`
singleton the API process warmed up at startup — singletons are per-process.
`worker_process_init` (fires once, before the worker takes its first task)
calls `registry.load_all()`, mirroring what `app/main.py`'s `lifespan` does
for the API. Getting this wrong (e.g. loading inside the task function)
would reload Audio's 380 MB checkpoint on every single request — slower
than the synchronous code this phase replaces.

**The detector is resolved before a Prediction row is created, not inside
the task.** `PredictionService.start_analysis()` calls
`registry.get_detector(document_type)` synchronously, in the request
handler, before writing anything to the database. An unsupported or
unloaded modality fails the HTTP request immediately with a 503 — it never
becomes a queued task that fails invisibly, with nobody watching, minutes
later.

**`run_analysis()` is the only place inference logic lives.** It doesn't
know or care whether it was called by the Celery task
(`app/tasks/prediction_tasks.py`) or directly (e.g. by a test running Celery
in eager mode). There's exactly one implementation, so there's exactly one
place it can be wrong.

**No automatic retries (`max_retries=0`).** A model failing on a specific
file (corrupt video, missing weights) doesn't fix itself if you run it
again — retrying would just delay the user seeing "Failed" by however long
the retry backoff is, for no benefit.

**Frontend polls a REST endpoint it already had, not a new channel.**
`Predict.jsx`'s `handleAnalyze` now does `POST /analyze/{id}` → gets back a
"Processing" row immediately → polls `GET /predictions/{id}` every 1.5s
until the status changes → then refreshes history. No websocket, no
server-sent events, no new endpoint — the same read-only route the History
page already relies on.

## Running it locally

You need a Redis server reachable at `CELERY_BROKER_URL`
(`redis://localhost:6379/0` by default). Windows has no first-party Redis
build, so pick one:

1. **Docker Desktop** (if you already have it — this is also what Phase 12
   sets up permanently): `docker run -d --name deepshield-redis -p 6379:6379 redis:7`
2. **WSL** (Windows Subsystem for Linux): install Redis inside your WSL
   distro (`sudo apt install redis-server && redis-server`) — it's reachable
   from Windows at `localhost:6379` the same as if it were native.
3. **Memurai** (memurai.com) — a free, native Windows Redis-protocol server,
   no WSL/Docker needed at all. Simplest if you have neither of the above.

Then, from `backend/`, in **two separate terminals**:

```
# Terminal 1 — the API (unchanged command)
python -m uvicorn app.main:app --reload

# Terminal 2 — the Celery worker (new)
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

`--pool=solo` is required on Windows (see `celery_app.py`'s docstring —
Celery's default pool needs `os.fork()`, which Windows doesn't have). It
means one task runs at a time in the worker, which is fine for a
single-developer demo.

If the worker isn't running, `POST /analyze/{id}` still succeeds (the row
is created "Processing") but nothing ever picks the task up — the
prediction will sit at "Processing" forever and the frontend will
eventually show the 2-minute poll-timeout message. That's expected, not a
bug: start the worker before testing analysis.

## What's deliberately out of scope for this phase

**Explanation generation (`/explanations/generate/{id}`) is still
synchronous.** SHAP/LIME/Grad-CAM generation is triggered on-demand from
the Explain page for one already-completed prediction and, for most
modalities, finishes in well under the time a user would notice. Moving it
async would use the exact same pattern established here (a Celery task, a
"Pending" row on the `explanations` table, frontend polling) — a natural
follow-on phase, not attempted now, to keep this phase's diff reviewable.

**No task retries, no dead-letter queue, no priority queues.** All
reasonable production concerns; all unnecessary complexity for a
single-developer project being demoed on one machine.
