import tempfile
import shutil
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.core.config import settings
from backend.app.core.auth import create_authenticated_session
from backend.app.services.storage import storage_service
from backend.app.services.ai_adapter import ai_adapter
from backend.app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def test_environment(temp_storage):
    """Ensure tests run with offline mock provider by default and clean engine state."""
    from backend.app.services.rate_limit import _buckets
    _buckets.clear()
    old_provider = settings.AI_PROVIDER
    old_key = settings.MODEL_API_KEY
    settings.AI_PROVIDER = "mock"
    ai_adapter._engine = None
    try:
        yield
    finally:
        settings.AI_PROVIDER = old_provider
        settings.MODEL_API_KEY = old_key
        ai_adapter._engine = None


@pytest.fixture(scope="function")
def temp_storage():
    """Isolated temporary directory for test storage."""
    temp_dir = tempfile.mkdtemp()
    old_base = storage_service.base_dir
    storage_service.base_dir = temp_dir
    try:
        yield temp_dir
    finally:
        storage_service.base_dir = old_base
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Authenticated client with valid HMAC-SHA256 signed session and CSRF header."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    token, csrf = create_authenticated_session(user_id="demo-user")
    with TestClient(app) as test_client:
        test_client.cookies.set("pk_session", token)
        test_client.headers.update({"X-CSRF-Token": csrf})
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def secondary_client(db_session):
    """Authenticated client for a different user ('other-user') to test authorization boundary."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    token, csrf = create_authenticated_session(user_id="other-user")
    with TestClient(app) as test_client:
        test_client.cookies.set("pk_session", token)
        test_client.headers.update({"X-CSRF-Token": csrf})
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def anonymous_client(db_session):
    """Unauthenticated client without session credentials."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
