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
            self.pool = ConnectionPool(conninfo=self.conninfo, open=True)
            logger.info("Connection pool initialized.")

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
        ddl_script = """
        CREATE TABLE IF NOT EXISTS session_interaction (
            session_id VARCHAR PRIMARY KEY,
            initiated_by VARCHAR,
            status VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            with self.pool.connection(timeout=2.0) as conn:
                with conn.cursor() as cur:
                    cur.execute(ddl_script)
                    conn.commit()
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise SchemaInitializationError(f"DDL execution failed: {e}")

def get_db_manager(run_schema_init: bool = True) -> DatabaseManager:
    return DatabaseManager.get_instance()
