# DeepShieldAI backend image.
#
# One image, two roles: the same image runs as the FastAPI API (default CMD)
# and as the Celery worker (docker-compose overrides the command — see
# docker-compose.yml and docs/DOCKER.md). Sharing one image means the API
# and the worker can never drift out of sync on a dependency version, which
# matters a lot here: PredictionService.run_analysis() (the actual
# inference logic) runs inside the worker process, but it's defined in the
# same app/ package the API imports too.
#
# Base image: python:3.14-slim, matching this project's documented dev
# runtime (see backend/requirements/ml.txt's note on why Image runs Keras
# on the PyTorch backend rather than TensorFlow — that whole workaround
# exists BECAUSE tensorflow has no Python 3.14 wheel. Building this image
# against an older Python "for safety" would silently make that documented
# constraint pointless and risks a different set of wheel mismatches.)
FROM python:3.14-slim

# System libraries the ML stack needs that aren't pure-Python:
#   libsndfile1  - librosa (Audio) reads audio via libsndfile under the hood
#   ffmpeg       - decodes the wider range of video/audio containers users
#                  actually upload, beyond what OpenCV's built-in decoders cover
#   libgomp1     - OpenMP runtime torch/numpy/xgboost link against
#   curl         - used by the container HEALTHCHECK below
# --no-install-recommends keeps this from pulling in a desktop-oriented
# dependency tree the image will never use.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies before source: this layer only rebuilds when
# requirements/*.txt change, not on every code edit — the biggest single
# win for rebuild speed given how large the ML dependency tree is.
COPY requirements/ requirements/
# ml.txt is the full application (API + all 6 detectors + explainability +
# RAG) — see requirements/ml.txt's own note on why this is the one to
# install for anything beyond bare CRUD/auth testing. -r base.txt is
# already pulled in transitively by ml.txt.
RUN pip install --no-cache-dir -r requirements/ml.txt

COPY . .

# Model weights (backend/models/), uploaded files (backend/uploads/), the
# Chroma vector store (backend/storage/) and knowledge-sources/ are NOT
# baked into this image — see docker-compose.yml's volumes:. They total
# 800MB+, are gitignored, and belong to the deployment (or the developer's
# checkout), not to the image. A rebuilt image must not silently ship
# (or lose) whatever the previous image happened to have on disk.
RUN mkdir -p models uploads storage knowledge-sources

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# Liveness check hits the same /health FastAPI already exposes for exactly
# this purpose (see app/main.py's health() handler docstring: "Liveness
# probe for Docker / orchestrators"). The Celery worker service overrides
# this at the compose level (a worker has no HTTP port to probe).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
