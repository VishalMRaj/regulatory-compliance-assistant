import logging
from contextlib import contextmanager
from typing import Generator, Any, Optional

import psycopg
from psycopg_pool import ConnectionPool
from .config_loader import config

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    pass

class ConnectionPoolError(DatabaseError):
    pass

class SchemaInitializationError(DatabaseError):
    pass

class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None

    def __init__(self, run_schema_init: bool = True):
        if not config:
            raise ConnectionPoolError("Configuration not loaded.")

        db_cfg = config.database
        self.conninfo = (
            f"host={db_cfg.host} port={db_cfg.port} "
            f"user={db_cfg.user} password={db_cfg.password} "
            f"dbname={db_cfg.database}"
        )

        try:
            self.pool = ConnectionPool(conninfo=self.conninfo, open=True, kwargs={"autocommit": True})
            logger.info("Connection pool initialized with autocommit.")

            if run_schema_init:
                try:
                    self.initialize_schema()
                except SchemaInitializationError as e:
                    logger.warning(f"Initial schema setup deferred: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise ConnectionPoolError(f"Initialization failed: {e}")

    @classmethod
    def get_instance(cls) -> 'DatabaseManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_connection(cls, timeout: float = 2.0):
        """Maintains backward compatibility with psycopg2 style callers."""
        try:
            return cls.get_instance().pool.getconn(timeout=timeout)
        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
            raise

    @classmethod
    def release_connection(cls, conn):
        """Maintains backward compatibility with psycopg2 style callers."""
        cls.get_instance().pool.putconn(conn)

    @contextmanager
    def connection(self) -> Generator[psycopg.Connection, None, None]:
        try:
            with self.pool.connection() as conn:
                yield conn
        except psycopg.Error as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Connection issue: {e}")

    def initialize_schema(self):
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        init_sql_path = os.path.join(base_dir, "init.sql")
        
        if not os.path.exists(init_sql_path):
            logger.error(f"Schema file not found at: {init_sql_path}")
            raise SchemaInitializationError(f"File not found: {init_sql_path}")

        try:
            with open(init_sql_path, "r") as f:
                ddl_script = f.read()
            
            with self.pool.connection(timeout=2.0) as conn:
                with conn.cursor() as cur:
                    cur.execute(ddl_script)
                    if not conn.autocommit:
                        conn.commit()
            logger.info("Database schema initialized successfully from init.sql.")
        except Exception as e:
            logger.error(f"Failed to initialize schema from init.sql: {e}")
            raise SchemaInitializationError(f"DDL execution failed: {e}")

def get_db_manager(run_schema_init: bool = True) -> DatabaseManager:
    return DatabaseManager.get_instance()
