from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401  — registers all SQLAlchemy mappers
from app.api.routes.audit_log import router as audit_log_router
from app.api.routes.auth import router as auth_router
from app.api.routes.bot_analysis import router as bot_analysis_router
from app.api.routes.document import router as document_router
from app.api.routes.document_type import router as document_type_router
from app.api.routes.explanation import router as explanation_router
from app.api.routes.knowledge_base import router as knowledge_base_router
from app.api.routes.prediction import router as prediction_router
from app.api.routes.report import router as report_router
from app.api.routes.review_analysis import router as review_analysis_router
from app.constants.roles import Roles
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.dependencies.auth import get_current_active_user
from app.dependencies.rbac import require_roles
from app.ml.registry import registry
from app.utils.file_storage import FileStorage

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / shutdown hooks.

    Anything expensive and reusable belongs here — in Phase 5 the ML model
    registry is warmed up at this exact point so that inference never pays
    the weight-loading cost on a request.
    """
    configure_logging()
    FileStorage.create_upload_directories()

    # Weights are read from disk exactly once, here. A failure is logged and
    # recorded rather than raised — a missing model must not stop the API
    # from booting, and /api/predictions/models reports the reason.
    registry.load_all()

    logger.info(
        "%s v%s starting (debug=%s)",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.DEBUG,
    )

    yield

    logger.info("%s shutting down", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

# ---------------------------------------------------------------- middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------- exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Domain errors raised by the service layer become clean 400s."""
    logger.warning("ValueError on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak a stack trace to the client."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ------------------------------------------------------------------ routers
# PUBLIC — no token required
app.include_router(
    auth_router,
    prefix=f"{settings.API_PREFIX}/auth",
    tags=["Authentication"],
)

# AUTHENTICATED — any active, logged-in user
protected = [Depends(get_current_active_user)]

app.include_router(
    document_router,
    prefix=f"{settings.API_PREFIX}/documents",
    tags=["Documents"],
    dependencies=protected,
)
app.include_router(
    document_type_router,
    prefix=f"{settings.API_PREFIX}/document-types",
    tags=["Document Types"],
    dependencies=protected,
)
app.include_router(
    prediction_router,
    prefix=f"{settings.API_PREFIX}/predictions",
    tags=["Predictions"],
    dependencies=protected,
)
app.include_router(
    report_router,
    prefix=f"{settings.API_PREFIX}/reports",
    tags=["Reports"],
    dependencies=protected,
)
app.include_router(
    bot_analysis_router,
    prefix=f"{settings.API_PREFIX}/bot-analysis",
    tags=["Bot Analysis"],
    dependencies=protected,
)
app.include_router(
    review_analysis_router,
    prefix=f"{settings.API_PREFIX}/review-analysis",
    tags=["Review Analysis"],
    dependencies=protected,
)
app.include_router(
    explanation_router,
    prefix=f"{settings.API_PREFIX}/explanations",
    tags=["Explanations"],
    dependencies=protected,
)
app.include_router(
    knowledge_base_router,
    prefix=f"{settings.API_PREFIX}/knowledge-base",
    tags=["Knowledge Base"],
    dependencies=protected,
)

# ADMIN ONLY — audit logs are a compliance surface, not general data
app.include_router(
    audit_log_router,
    prefix=f"{settings.API_PREFIX}/audit-logs",
    tags=["Audit Logs"],
    dependencies=[Depends(require_roles(Roles.ADMIN))],
)


# ------------------------------------------------------------------- health
@app.get("/", tags=["Health"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "ok",
    }


@app.get("/health", tags=["Health"])
def health():
    """Liveness probe for Docker / orchestrators (Phase 13)."""
    return {"status": "healthy"}
