"""
Shared pytest fixtures for the whole backend test suite.

DATABASE STRATEGY
------------------
`app/db/session.py` builds its `engine`/`SessionLocal` against
`settings.DATABASE_URL` (real Postgres) at *import time*, with
`pool_size`/`max_overflow` kwargs that are only valid for Postgres's
QueuePool — so we deliberately never touch that engine here. Instead we
build a completely separate SQLite in-memory engine and override FastAPI's
`get_db` dependency to yield sessions from it. `create_engine()` itself
never opens a connection, so the real (unreachable, in test environments)
Postgres engine sits there unused and harmless.

`StaticPool` is required for the SQLite ":memory:" URL: SQLite's default
pooling opens a *new*, empty, in-memory database per connection, which
would make every `Session()` the app opens see a different empty database.
StaticPool pins the whole engine to one physical connection, so every
session — the app's, and this file's own fixtures — sees the same data.

Every test gets a full `drop_all`/`create_all` plus the same reference data
`scripts/seed_roles.py` and `scripts/seed_document_types.py` write in a real
deploy (Admin/Analyst/User roles, the six document types) — cheap on an
in-memory SQLite DB, and it means no test can leak state into another.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.utils.file_storage as file_storage_module
from app.constants.document_types import DocumentTypes
from app.constants.roles import Roles
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.document_type import DocumentType
from app.models.role import Role
from app.models.user import User

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE, autoflush=False, autocommit=False
)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db

# Mirrors scripts/seed_roles.py exactly.
_SEED_ROLES = [
    (Roles.ADMIN, "Full access: user management, audit logs, deletion."),
    (Roles.ANALYST, "Can upload, run analysis and generate reports."),
    (Roles.USER, "Can upload and view own results."),
]

# Mirrors scripts/seed_document_types.py exactly.
_SEED_DOCUMENT_TYPES = [
    (DocumentTypes.IMAGE, "Image files"),
    (DocumentTypes.VIDEO, "Video files"),
    (DocumentTypes.AUDIO, "Audio files"),
    (DocumentTypes.TEXT, "Text documents"),
    (DocumentTypes.REVIEW, "Product or service reviews"),
    (DocumentTypes.ACCOUNT, "Social-media account metadata (bot detection)"),
]

# Mirrors FileStorage.create_upload_directories()'s folder list exactly.
_UPLOAD_FOLDERS = ("images", "videos", "audio", "text", "accounts", "reports", "xai")


@pytest.fixture(autouse=True)
def _reset_database():
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)

    db = TestingSessionLocal()
    try:
        for role_name, description in _SEED_ROLES:
            db.add(Role(role_name=role_name, description=description))
        for type_name, description in _SEED_DOCUMENT_TYPES:
            db.add(DocumentType(type_name=type_name, description=description))
        db.commit()
    finally:
        db.close()

    yield


@pytest.fixture(autouse=True)
def _isolated_uploads(tmp_path, monkeypatch):
    """
    Redirect FileStorage's UPLOAD_DIR to a per-test temp directory so the
    suite never writes into the real backend/uploads/ folder on disk.
    """
    monkeypatch.setattr(file_storage_module, "UPLOAD_DIR", tmp_path)
    for folder in _UPLOAD_FOLDERS:
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    yield


@pytest.fixture
def db_session():
    """A raw session for tests that set up or inspect rows directly."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    # Used as a context manager so FastAPI's lifespan actually runs
    # (registry.load_all(), FileStorage.create_upload_directories(), the RAG
    # sync) — a bare TestClient(app) does not guarantee that.
    with TestClient(app) as test_client:
        yield test_client


def register_and_login(client: TestClient, email: str, password: str = "Sup3rSecret!") -> dict:
    """
    Register + log in through the real API (not a DB shortcut) and return
    ready-to-use Authorization headers. Most tests care about "an
    authenticated User exists", not about re-proving registration works —
    that's covered once, explicitly, in test_auth.py.
    """
    client.post(
        "/api/auth/register",
        json={"full_name": "Test User", "email": email, "password": password},
    )
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_user(db_session, email: str, role_name: str = Roles.USER) -> User:
    """Create a user directly in the DB, bypassing the API and its hashing cost."""
    role = db_session.query(Role).filter(Role.role_name == role_name).first()
    user = User(
        full_name="Direct User",
        email=email,
        password_hash=hash_password("Sup3rSecret!"),
        role_id=role.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers_for(user: User) -> dict:
    token = create_access_token(subject=user.email)
    return {"Authorization": f"Bearer {token}"}
