"""Isolated local test harness. No production code or live provider calls are patched in files."""
import importlib
import importlib.util
import os
from pathlib import Path
import sys
import pytest


def pytest_addoption(parser):
    parser.addoption('--bindr-source', default=str(Path(__file__).resolve().parents[2]))
    parser.addoption('--bindr-auth-hook', default=None)
    parser.addoption('--bindr-diagnostic-anonymous', action='store_true')


@pytest.fixture(scope='session')
def source_root(pytestconfig):
    root = Path(pytestconfig.getoption('--bindr-source')).resolve()
    if not (root / 'backend/app').is_dir():
        pytest.skip('PENDING: backend/app unavailable in selected source; supply --source with available modules')
    # The AI package auto-loads .env. Do not import any tree containing real .env files.
    if any(p.exists() for p in [root / '.env', root / 'backend/app/ai/.env']):
        pytest.skip('PENDING: selected source contains .env; use a credential-free source snapshot')
    sys.path.insert(0, str(root))
    return root


@pytest.fixture(scope='session')
def modules(source_root):
    for name in ('fastapi', 'sqlalchemy', 'httpx', 'multipart'):
        pytest.importorskip(name, reason=f'PENDING: required test dependency {name} unavailable')
    main = importlib.import_module('backend.app.main')
    database = importlib.import_module('backend.app.core.database')
    adapter = importlib.import_module('backend.app.services.ai_adapter')
    storage = importlib.import_module('backend.app.services.storage')
    return main, database, adapter, storage


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """Block paid requests/model downloads. RapidOCR must use installed model assets."""
    import socket
    def denied(*args, **kwargs):
        raise AssertionError('Regression suite forbids external network calls')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket.socket, 'connect_ex', denied)
    monkeypatch.setenv('AI_PROVIDER', 'mock')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'bootstrap.sqlite'))
    monkeypatch.setenv('EVIDENCE_STORAGE_DIR', str(tmp_path / 'evidence'))
    monkeypatch.setenv('EVIDENCE_LOCAL_DIR', str(tmp_path / 'evidence'))
    for key in ('MODEL_API_KEY', 'AI_API_KEY', 'OPENAI_API_KEY', 'META_API_KEY', 'META_BASE_URL'):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def adapter_module(modules, monkeypatch):
    module = modules[2]
    monkeypatch.setattr(module.ai_adapter, '_engine', None)
    settings = getattr(module, 'settings', None)
    if settings is not None:
        if hasattr(settings, 'AI_PROVIDER'):
            monkeypatch.setattr(settings, 'AI_PROVIDER', 'mock')
        if hasattr(settings, 'MODEL_API_KEY'):
            monkeypatch.setattr(settings, 'MODEL_API_KEY', None)
    return module


@pytest.fixture
def db_session(modules):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    base = modules[1].Base
    base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def raw_client(modules, adapter_module, db_session, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    main, database, _, storage = modules
    monkeypatch.setattr(storage.storage_service, 'base_dir', str(tmp_path))
    previous = dict(main.app.dependency_overrides)
    main.app.dependency_overrides[database.get_db] = lambda: db_session
    try:
        # No context-manager entry: do not run production lifespan/bootstrap DB.
        client = TestClient(main.app)
        try:
            yield client
        finally:
            client.close()
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous)
        db_session.rollback()


@pytest.fixture
def api(raw_client, db_session, pytestconfig):
    hook = pytestconfig.getoption('--bindr-auth-hook')
    if hook:
        path = Path(hook).resolve()
        if not path.is_file():
            pytest.skip('PENDING: authentication test hook file unavailable')
        spec = importlib.util.spec_from_file_location('bindr_regression_auth', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.authenticate(raw_client, db_session)
    elif not pytestconfig.getoption('--bindr-diagnostic-anonymous'):
        pytest.skip('PENDING: agreed session/CSRF authentication bootstrap unavailable; provide --auth-hook. Diagnostic anonymous mode verifies route behavior only.')
    return raw_client


@pytest.fixture
def case_and_evidence(api):
    from helpers import new_case, upload
    c = new_case(api)
    e, _ = upload(api, c['id'], 'promise.txt', b'We will refund INR 4999.00 for order DEMO-42.', 'text/plain')
    return c, e


@pytest.fixture
def ai_available(source_root):
    if not (source_root / 'backend/app/ai/engine.py').is_file():
        pytest.skip('PENDING: AI engine code unavailable in selected source')
    try:
        return importlib.import_module('backend.app.ai.engine')
    except ModuleNotFoundError as exc:
        pytest.skip(f'PENDING: AI code/dependency unavailable: {exc.name}')
