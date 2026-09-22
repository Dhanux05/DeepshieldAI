"""
Celery application instance — the async task queue introduced in Phase 11.

WHY THIS EXISTS: `PredictionService.run_analysis()` (the renamed, still-only
inference implementation — see that method's docstring) calls a detector's
`.predict()` directly, which blocks the calling thread for the model's full
inference time. That's fine for Image or the XGBoost bot detector, but Audio
(wav2vec2) and Video (R3D-18, 16 frames) routinely take multiple seconds on
CPU-only hardware — long enough that a FastAPI worker handling that request
cannot serve any other request in the meantime. Moving inference into a
Celery worker process means the API responds in milliseconds ("I've queued
this"), and the actual model run happens somewhere that blocking is fine.

DESIGN DECISIONS:

1. REDIS AS BROKER, NO RESULT BACKEND. Celery needs a message broker to hand
   tasks to workers; Redis is the standard lightweight choice, and this
   project has no other message-queue infrastructure to reuse. A *result
   backend* (where Celery would store a task's return value) is deliberately
   NOT configured: the `predictions` table is already the single source of
   truth for a prediction's status and result, and every endpoint the
   frontend calls reads from Postgres, not from Celery. Adding a second
   place results could live would just be a way for the two to disagree.

2. MODELS ARE LOADED ONCE PER WORKER PROCESS, NOT PER TASK. A Celery worker
   is a separate OS process from the FastAPI process — it does NOT share the
   `registry` singleton FastAPI warmed up at startup (singletons are
   per-process, not system-wide). Re-loading Audio's 380 MB wav2vec2
   checkpoint on every task would make async inference slower than the
   synchronous version it replaces. `worker_process_init` (a Celery signal
   firing exactly once when a worker process starts, before it accepts any
   task) calls `registry.load_all()` here — mirroring exactly what
   `app/main.py`'s `lifespan` does for the API process.

3. THIS FILE HAS NO ROUTES, NO DB SESSIONS, NO REQUEST HANDLING. It only
   builds the `Celery` app object and registers the startup hook. Task
   *logic* lives in `app/tasks/prediction_tasks.py`, kept separate so this
   file stays stable, rarely-changed plumbing.

RUNNING A WORKER (from `backend/`, with Redis already running):

    celery -A app.core.celery_app worker --loglevel=info --pool=solo

`--pool=solo` matters on Windows: Celery's default "prefork" pool relies on
os.fork(), which Windows does not support. `solo` runs tasks one at a time
in the worker's own process — no parallelism, but this project is a
single-developer demo, not a production deployment serving concurrent
traffic, so one task at a time is an honest, acceptable trade-off (documented
here rather than discovered later as a mysterious crash on Windows).
"""

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import settings

celery_app = Celery(
    "deepshieldai",
    broker=settings.CELERY_BROKER_URL,
    include=["app.tasks.prediction_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    # No result backend (see module docstring, decision 1) — task return
    # values are discarded; the predictions table is the only durable state.
    task_ignore_result=True,
    # A stuck model call should not hold a worker slot forever. 10 minutes is
    # generous even for Video on a slow CPU; anything past that is stuck, not
    # slow, and should surface as a Failed prediction instead of hanging.
    task_time_limit=600,
    task_soft_time_limit=540,
)


@worker_process_init.connect
def _load_models_on_worker_start(**kwargs):
    """
    Runs once per worker process, before it pulls its first task off the
    queue. See module docstring, decision 2, for why this can't be "load on
    first task" or "share the API process's registry" instead.
    """
    from app.core.logging import configure_logging, get_logger
    from app.ml.registry import registry

    configure_logging()
    logger = get_logger(__name__)
    logger.info("Celery worker starting - loading model registry...")
    registry.load_all()
    logger.info("Celery worker ready.")
