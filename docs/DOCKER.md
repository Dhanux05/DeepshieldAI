# Docker packaging

## Why this phase exists

Every previous phase assumed a developer's own machine: a Python venv, a
locally-installed Postgres, model weights already sitting in
`backend/models/`, two terminals run by hand. That's fine for building the
project, but it's a bad way to hand it to someone else — a teammate, an
examiner, a grader — who just wants to see it run. "Clone the repo, install
Python 3.14, install Node, install Postgres, create a database, copy
`.env.example`, run migrations, seed reference data, get the model weights
from somewhere, start two terminals" is a lot of places for someone else's
setup to diverge from what was actually tested. This phase collapses all of
that into one command: `docker compose up --build`.

## Architecture

```
                    ┌──────────────────────────────┐
   host:5173  ─────▶│   frontend (nginx + built SPA) │
                    └───────────────┬───────────────┘
                                    │ proxy_pass /api, /docs
                                    ▼
                    ┌──────────────────────────────┐
   host:8000  ─────▶│      backend (FastAPI)         │──────┐
                    └───────────────┬───────────────┘      │
                                    │                        │ same image,
                          reads/writes                       │ different
                                    ▼                        │ command
                    ┌──────────────────────────────┐        │
                    │   postgres (named volume)      │        │
                    └──────────────────────────────┘        │
                                    ▲                        │
                                    │ reads/writes            ▼
                    ┌──────────────────────────────┐  ┌──────────────┐
                    │           redis                │◀─│ celery_worker │
                    │        (broker only)           │  │  (Phase 11)   │
                    └──────────────────────────────┘  └──────────────┘
```

Five containers, four images (`backend` and `celery_worker` are built from
the exact same `backend/Dockerfile` — see that file's top comment for why
sharing one image matters). Nothing here is new architecture: this phase
packages Phases 1–11 into containers, it doesn't change how any of them
work.

## Design decisions

**Model weights, uploads and the vector store are bind-mounted, not baked
into the image.** `backend/models/` alone is 800MB+ (see README.md's "Model
weights" section) and is gitignored — baking it into the image would mean
either committing those weights to the Dockerfile's build context (they
don't belong in an image layer that gets rebuilt on every code change) or
maintaining a second, image-specific copy of them. A bind mount means the
exact same `backend/models/` folder a bare-metal run already uses is what
the containers use too — get the weights once, run either way.
`backend/uploads/` and `backend/storage/` (the Chroma vector store) are
mounted read-write for the same reason in reverse: they're runtime data a
container rebuild must never discard.

**The API and the Celery worker share one image.** `docker-compose.yml`
builds `backend/Dockerfile` twice — once as the `backend` service (default
CMD: `uvicorn`), once as `celery_worker` (command overridden to `celery
... worker`). This mirrors exactly how `docs/ASYNC_PIPELINE.md` already
runs them as two processes from the same codebase on bare metal; Docker
just makes "same codebase" mean "same image; tag" precisely, instead of
"whatever's on disk in `backend/` when each terminal was started."

**No `--pool=solo` in the containerized worker command.** That flag exists
purely because Windows has no `os.fork()` (see `celery_app.py`'s
docstring). A Linux container has no such limitation, so
`docker-compose.yml`'s `celery_worker` command omits it — the worker gets
real concurrency (Celery's default "prefork" pool) instead of the
one-task-at-a-time fallback the bare-metal Windows instructions need.

**Migrations run from the container's own entrypoint, not a documented
manual step.** `backend/docker-entrypoint.sh` runs `alembic upgrade head`
before starting either `uvicorn` or `celery worker` — unconditionally, on
every container start. `alembic upgrade head` against an already-current
schema is a no-op, so this is safe to run twice (once from `backend`, once
from `celery_worker`) without any coordination between the two containers.
The alternative — a separate one-shot "migrate" service, or a step in a
README someone has to remember — is exactly the kind of manual step this
phase exists to remove.

**`environment:` overrides `DATABASE_URL` and `CELERY_BROKER_URL`; nothing
else is duplicated.** `backend/.env` (the same file a bare-metal run
already uses) is loaded via `env_file:` for `SECRET_KEY`, `DEBUG`, and
everything else — there is exactly one place those values are set. Only
the two settings that are structurally different inside Docker
(`localhost` means "this container", not "the postgres container next to
it") are overridden explicitly, and Compose applies `environment:` after
`env_file:`, so the override always wins regardless of what's already in
`.env` for bare-metal use.

**nginx, not `serve` or a Node process, serves the built frontend.**
`npm run build` (see `frontend/package.json`) produces static
HTML/CSS/JS — serving static files is nginx's whole job, at a fraction of
the memory a Node process would use for the same task, and its
`proxy_pass` directive (see `frontend/nginx.conf`) reproduces
`vite.config.js`'s dev-server proxy behavior exactly, so the frontend's own
code (relative `fetch("/api/...")` calls) needs zero changes between
`npm run dev` and this containerized build.

## Running it locally

From the repository root, with Docker Desktop (or Docker Engine + Compose
v2) installed:

```bash
# 1. If you don't already have one, create backend/.env
cp backend/.env.example backend/.env
# then edit it: set a real SECRET_KEY (see the comment in the file)

# 2. Make sure trained model weights are in place (see README.md's "Model
#    weights" section) — the stack still starts without them, but every
#    detector reports itself unavailable via GET /api/predictions/models.

# 3. Build and start everything
docker compose up --build
```

Then open `http://localhost:5173`. The API is directly reachable too, at
`http://localhost:8000` (and `http://localhost:8000/docs` while
`DEBUG=true`).

First-run reference data (roles, document types) is **not** seeded
automatically — that stays a deliberate, explicit step, the same as on
bare metal, because creating the first Admin account needs an
interactively-typed password (see `scripts/create_admin.py`'s own
docstring on why there is no default `admin/admin` account):

```bash
docker compose exec backend python -m scripts.seed_all
docker compose exec backend python -m scripts.create_admin --email you@example.com --name "Your Name"
```

To stop everything: `docker compose down` (add `-v` to also delete the
Postgres volume — the database, not the model weights or uploads, which
live in bind mounts on your own disk regardless).

## What's deliberately out of scope

**No production-hardening (TLS termination, secrets manager, horizontal
scaling, resource limits).** This packages the project for "runs reliably
on one machine with one command," which is what a grading/demo environment
needs — not for a multi-tenant production deployment, which is a
meaningfully larger scope than a final-year project's Phase 12.

**The Celery worker runs as a single replica.** `docker-compose.yml`
doesn't set `deploy.replicas` — scaling to multiple worker containers is a
natural next step (`docker compose up --scale celery_worker=3`) but isn't
needed for this project's actual workload and isn't tested here.

**No automated image publishing / CI pipeline.** These Dockerfiles build
locally; wiring them into a registry push or a CI workflow is future work,
not attempted in this phase.
