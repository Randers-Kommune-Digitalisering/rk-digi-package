import os
from urllib import parse
from typing import Literal
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class DatabaseManager:
    _instances = {}

    def __new__(cls, profile_name: str, *args, **kwargs):
        if profile_name in cls._instances:
            return cls._instances[profile_name]
        instance = super().__new__(cls)
        cls._instances[profile_name] = instance
        return instance

    def __init__(
        self,
        profile_name: str,
        db_type: Literal["postgres", "mssql"],
        airflow_connection_id: str | None = None,
        database: str | None = None,
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        port: int | None = None,
        async_mode: bool = False,
    ):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._async_mode = async_mode

        if self._async_mode:
            from sqlalchemy.ext.asyncio import create_async_engine, \
                async_sessionmaker, AsyncSession

        if db_type not in ("postgres", "mssql"):
            raise ValueError(
                f"db_type must be 'postgres' or 'mssql', got '{db_type}'"
            )
        elif airflow_connection_id:
            if self._async_mode:
                from airflow.hooks.base import BaseHook
                conn = BaseHook.get_connection(airflow_connection_id)
                conn_str = conn.get_uri()
                if db_type == "postgres":
                    driver = "postgresql+asyncpg"
                elif db_type == "mssql":
                    driver = "mssql+aioodbc"
                conn_str = f"{driver}://{conn_str.split('://', 1)[1]}"
                self._engine = create_async_engine(conn_str)
            else:
                if db_type == "postgres":
                    from airflow.providers.postgres.hooks.postgres \
                        import PostgresHook
                    hook = PostgresHook(postgres_conn_id=airflow_connection_id)
                elif db_type == "mssql":
                    from airflow.providers.microsoft.mssql.hooks.mssql \
                        import MsSqlHook
                    hook = MsSqlHook(mssql_conn_id=airflow_connection_id)
                self._engine = hook.get_sqlalchemy_engine()
        elif all(p is None for p in (username, password, host)):
            env_prefix = profile_name.upper() + "_"
            username = (os.getenv(env_prefix + "USERNAME")
                        or os.getenv(env_prefix + "USER"))
            password = (os.getenv(env_prefix + "PASSWORD")
                        or os.getenv(env_prefix + "PASS"))
            host = os.getenv(env_prefix + "HOST")
            database = os.getenv(env_prefix + "DATABASE")
            port_str = os.getenv(env_prefix + "PORT")
            port = int(port_str) if port_str is not None else None
        elif all((username, password, host)):
            pass
        else:
            raise ValueError(
                "Insufficient parameters provided "
            )

        if not hasattr(self, "_engine"):
            if db_type == "postgres":
                driver = "postgresql+asyncpg" if self._async_mode \
                    else "postgresql+psycopg2"
            elif db_type == "mssql":
                driver = "mssql+aioodbc" if self._async_mode \
                    else "mssql+pymssql"

            conn_str = (
                f"{driver}://{parse.quote_plus(username)}:"
                f"{parse.quote_plus(password)}@{parse.quote_plus(host)}"
            )
            if port:
                conn_str += f":{port}"
            if database:
                conn_str += f"/{parse.quote_plus(database)}"

            if not self._async_mode:
                self._engine = create_engine(conn_str)
            else:
                # 'aioodbc' depends on ODBC driver and it must be specified.
                if db_type == "mssql":
                    import pyodbc
                    drivers = [d for d in pyodbc.drivers()
                               if "ODBC Driver" in d and "SQL Server" in d]
                    conn_str += f"?driver={drivers[0].replace(' ', '+')}"
                self._engine = create_async_engine(conn_str)

        if not self._async_mode:
            self.can_connect()
            self._Session = sessionmaker(bind=self._engine)
        else:
            self._Session = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession
            )

    def can_connect(self):
        if self._async_mode:
            raise RuntimeError("Use can_connect_async for async mode.")
        with self._engine.connect():
            pass
        return True

    def get_session(self):
        if self._async_mode:
            raise RuntimeError("In async mode, use get_session_async instead.")
        return self._Session()

    def dispose(self):
        if hasattr(self, "_engine") and not self._async_mode:
            self._engine.dispose()
            self._engine = None
            self._Session = None
            self._initialized = False
            for name, inst in list(self._instances.items()):
                if inst is self:
                    del self._instances[name]
        else:
            raise RuntimeError("In async mode, use dispose_async instead.")

    async def can_connect_async(self):
        if not self._async_mode:
            raise RuntimeError("Use can_connect for sync mode.")
        async with self._engine.connect():
            pass
        return True

    @asynccontextmanager
    async def get_session_async(self):
        if not self._async_mode:
            raise RuntimeError("Not in async mode.")
        async with self._Session() as session:
            yield session

    async def dispose_async(self):
        if hasattr(self, "_engine") and self._async_mode:
            await self._engine.dispose()
            self._engine = None
            self._Session = None
            self._initialized = False
            for name, inst in list(self._instances.items()):
                if inst is self:
                    del self._instances[name]
        else:
            raise RuntimeError("Not in async mode.")
