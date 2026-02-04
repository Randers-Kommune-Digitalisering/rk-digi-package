import sys
import types
import pytest
import asyncio
import sqlalchemy
from rkdigi import DatabaseManager

# Mock psycopg2
sys.modules["psycopg2"] = types.ModuleType("psycopg2")
sys.modules["psycopg2.extensions"] = types.ModuleType("psycopg2.extensions")
sys.modules["psycopg2.extras"] = types.ModuleType("psycopg2.extras")
sys.modules["psycopg2"].paramstyle = "pyformat"

# Mock pymssql
sys.modules["pymssql"] = types.ModuleType("pymssql")
sys.modules["pymssql"].paramstyle = "pyformat"
sys.modules["pymssql"].__version__ = "2.2.0"

# Mock airflow and airflow providers
sys.modules["airflow.hooks.base"] = types.ModuleType("airflow.hooks.base")
sys.modules["airflow.providers.postgres.hooks.postgres"] = \
    types.ModuleType("airflow.providers.postgres.hooks.postgres")
sys.modules["airflow.providers.microsoft.mssql.hooks.mssql"] = \
    types.ModuleType("airflow.providers.microsoft.mssql.hooks.mssql")


@pytest.fixture(autouse=True)
def clear_db_manager_instances():
    DatabaseManager._instances.clear()


# General Tests
def test_singleton_behavior(monkeypatch):
    monkeypatch.setattr(DatabaseManager, "can_connect", lambda self: True)
    manager1 = DatabaseManager(
        profile_name="singleton_test",
        db_type="postgres",
        username="user",
        password="pass",
        host="localhost",
    )
    manager2 = DatabaseManager(
        profile_name="singleton_test",
        db_type="postgres",
        username="user2",
        password="pass2",
        host="localhost",
    )
    assert manager1 is manager2
    manager1.dispose()
    assert "singleton_test" not in DatabaseManager._instances


def test_insufficient_credentials():
    with pytest.raises(ValueError):
        DatabaseManager(
            profile_name="incomplete",
            db_type="postgres",
            username="user"
        )


def test_invalid_db_type():
    with pytest.raises(ValueError):
        DatabaseManager(
            profile_name="badtype",
            db_type="sqlite"
        )


# Sync Tests
@pytest.mark.parametrize("db_type", ["postgres", "mssql"])
def test_sync_manager_init_airflow(db_type, monkeypatch):
    # Lines 65->69 in database_manager.py is covered by this test,
    # but due to monkeypatching/pytest-cov limitations
    # it is not visible in coverage report.
    class DummyEngine:
        def dispose(self):
            pass

    class DummyHook:
        def get_sqlalchemy_engine(self):
            return DummyEngine()

    sys.modules["airflow.providers.postgres.hooks.postgres"].PostgresHook = \
        lambda postgres_conn_id: DummyHook()
    sys.modules["airflow.providers.microsoft.mssql.hooks.mssql"].MsSqlHook = \
        lambda mssql_conn_id: DummyHook()
    monkeypatch.setattr(DatabaseManager, "can_connect", lambda self: True)
    manager = DatabaseManager(
        profile_name="airflowtest",
        db_type=db_type,
        airflow_connection_id="dummy_id"
    )
    assert isinstance(manager, DatabaseManager)


@pytest.mark.parametrize("db_type", ["postgres", "mssql"])
def test_sync_manager_init_creds(db_type, monkeypatch):
    monkeypatch.setattr(DatabaseManager, "can_connect", lambda self: True)
    manager = DatabaseManager(
        profile_name="testprofile",
        db_type=db_type,
        username="user",
        password="pass",
        host="localhost",
        database="somedb",
        port=1234
    )
    assert isinstance(manager, DatabaseManager)


@pytest.mark.parametrize("db_type", ["postgres", "mssql"])
def test_sync_manager_init_env_vars(db_type, monkeypatch):
    monkeypatch.setattr(DatabaseManager, "can_connect", lambda self: True)
    monkeypatch.setenv("TESTDB_USERNAME", "envuser")
    monkeypatch.setenv("TESTDB_PASSWORD", "envpass")
    monkeypatch.setenv("TESTDB_HOST", "envhost")
    monkeypatch.setenv("TESTDB_PORT", "1234")
    monkeypatch.setenv("TESTDB_DATABASE", "envdb")
    manager = DatabaseManager(
        profile_name="testdb",
        db_type=db_type
    )
    assert manager._initialized


def test_can_connect_sync(monkeypatch):
    class DummyConnection:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass

    class DummyEngine:
        def connect(self): return DummyConnection()

    monkeypatch.setattr(sqlalchemy,
                        "create_engine",
                        lambda *a, **k: DummyEngine())
    monkeypatch.setattr("sqlalchemy.orm.sessionmaker",
                        lambda *a, **k: lambda: None)

    # Mock can_connect during init and restore afterwards
    orig_can_connect = DatabaseManager.can_connect
    try:
        monkeypatch.setattr(DatabaseManager, "can_connect", lambda self: True)
        manager = DatabaseManager(
            profile_name="connect_test",
            db_type="postgres",
            username="user",
            password="pass",
            host="localhost",
        )
    finally:
        DatabaseManager.can_connect = orig_can_connect

    monkeypatch.setattr(manager, "_engine", DummyEngine())
    assert manager.can_connect() is True
    manager._async_mode = True
    with pytest.raises(RuntimeError):
        manager.can_connect()


def test_get_session_sync(monkeypatch):
    monkeypatch.setattr(DatabaseManager, "can_connect", lambda self: True)
    manager = DatabaseManager(
        profile_name="session_test",
        db_type="postgres",
        username="user",
        password="pass",
        host="localhost",
    )

    class DummySession:
        pass
    manager._Session = lambda: DummySession()
    session = manager.get_session()
    assert isinstance(session, DummySession)
    with pytest.raises(RuntimeError):
        manager._async_mode = True
        manager.get_session()


def test_dispose_sync(monkeypatch):
    monkeypatch.setattr(DatabaseManager, "can_connect", lambda self: True)
    manager = DatabaseManager(
        profile_name="dispose_test",
        db_type="postgres",
        username="user",
        password="pass",
        host="localhost",
    )

    assert "dispose_test" in DatabaseManager._instances
    manager.dispose()
    assert "dispose_test" not in DatabaseManager._instances
    assert manager._engine is None
    assert manager._Session is None
    assert manager._initialized is False
    with pytest.raises(RuntimeError):
        manager._async_mode = True
        manager.dispose()


# Async Tests
# Mock sqlalchemy async
class DummyAsyncConnection:
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc_val, exc_tb): pass


class DummyAsyncEngine:
    def connect(self): return DummyAsyncConnection()
    async def dispose(self): pass


def dummy_create_async_engine(conn_str):
    return DummyAsyncEngine()


def dummy_async_sessionmaker(*args, **kwargs):
    class DummySession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
        async def close(self): pass
    return DummySession


sys.modules["sqlalchemy.ext.asyncio"] = \
    types.ModuleType("sqlalchemy.ext.asyncio")
sys.modules["sqlalchemy.ext.asyncio"].create_async_engine = \
    dummy_create_async_engine
sys.modules["sqlalchemy.ext.asyncio"].async_sessionmaker = \
    dummy_async_sessionmaker
sys.modules["sqlalchemy.ext.asyncio"].AsyncSession = None

# Mock pyodbc for async mssql
pyodbc = types.ModuleType("pyodbc")
pyodbc.drivers = lambda: ["ODBC Driver 18 for SQL Server"]
sys.modules["pyodbc"] = pyodbc


@pytest.mark.asyncio
@pytest.mark.parametrize("db_type", ["postgres", "mssql"])
async def test_async_manager_init_airflow(db_type, monkeypatch):
    # Lines 56->58 in database_manager.py is covered by this test,
    # but due to monkeypatching/pytest-cov limitations
    # it is not visible in coverage report.
    class DummyConnection:
        def get_uri(self):
            return "dummy://user:pass@host:1234/dbname"

    class DummyBaseHook:
        @staticmethod
        def get_connection(conn_id):
            return DummyConnection()

    sys.modules["airflow.hooks.base"].BaseHook = DummyBaseHook

    manager = DatabaseManager(
        profile_name=f"airflowtest_async_{db_type}",
        db_type=db_type,
        airflow_connection_id="dummy_id",
        async_mode=True
    )
    assert isinstance(manager, DatabaseManager)


@pytest.mark.asyncio
@pytest.mark.parametrize("db_type", ["postgres", "mssql"])
async def test_async_manager_init_creds(db_type, monkeypatch):
    # Lines 90->93 and 104->116 in database_manager.py
    # are covered by this test, but due to
    # monkeypatching/pytest-cov limitations
    # it is not visible in coverage report.
    manager = DatabaseManager(
        profile_name=f"airflowtest_async_{db_type}",
        db_type=db_type,
        username="user",
        password="pass",
        host="localhost",
        async_mode=True
    )
    assert isinstance(manager, DatabaseManager)


@pytest.mark.asyncio
def test_can_connect_async():
    manager = DatabaseManager(
        profile_name="connect_async_test",
        db_type="postgres",
        username="user",
        password="pass",
        host="localhost",
        async_mode=True
    )
    manager._engine = DummyAsyncEngine()

    assert asyncio.run(manager.can_connect_async()) is True
    with pytest.raises(RuntimeError):
        manager._async_mode = False
        asyncio.run(manager.can_connect_async())


@pytest.mark.asyncio
def test_get_session_async(monkeypatch):
    monkeypatch.setattr(DatabaseManager, "can_connect", lambda self: True)

    class DummyAsyncSession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc_val, exc_tb): pass
        async def close(self): pass

    manager = DatabaseManager(
        profile_name="session_async_test",
        db_type="postgres",
        username="user",
        password="pass",
        host="localhost",
        async_mode=True
    )
    manager._Session = lambda: DummyAsyncSession()

    async def run():
        async with manager.get_session_async() as session:
            assert isinstance(session, DummyAsyncSession)
        with pytest.raises(RuntimeError):
            manager._async_mode = False
            async with manager.get_session_async() as _:
                pass
    asyncio.run(run())


@pytest.mark.asyncio
def test_dispose_async(monkeypatch):
    monkeypatch.setattr(DatabaseManager, "can_connect", lambda self: True)
    manager = DatabaseManager(
        profile_name="dispose_async_test",
        db_type="postgres",
        username="user",
        password="pass",
        host="localhost",
        async_mode=True
    )
    manager._engine = DummyAsyncEngine()

    assert "dispose_async_test" in DatabaseManager._instances
    assert manager is DatabaseManager._instances["dispose_async_test"]

    async def run():
        await manager.dispose_async()
        assert "dispose_async_test" not in DatabaseManager._instances
        assert manager._engine is None
        assert manager._Session is None
        assert manager._initialized is False
        with pytest.raises(RuntimeError):
            manager._async_mode = False
            await manager.dispose_async()
    asyncio.run(run())
