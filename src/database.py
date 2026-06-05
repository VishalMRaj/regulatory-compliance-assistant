import logging
from psycopg2.pool import ThreadedConnectionPool
from .config_loader import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    _pool = None

    @classmethod
    def initialize_pool(cls):
        if cls._pool is None:
            conn_str = config.get('database.connection_string')
            min_conn = config.get('database.pool_min_size', 1)
            max_conn = config.get('database.pool_max_size', 10)

            try:
                cls._pool = ThreadedConnectionPool(min_conn, max_conn, dsn=conn_str)
                logger.info("Database connection pool initialized.")
            except Exception as e:
                logger.error(f"Error initializing connection pool: {e}")
                raise

    @classmethod
    def get_connection(cls):
        if cls._pool is None:
            cls.initialize_pool()
        return cls._pool.getconn()

    @classmethod
    def release_connection(cls, conn):
        if cls._pool:
            cls._pool.putconn(conn)

    @classmethod
    def close_all_connections(cls):
        if cls._pool:
            cls._pool.closeall()
            cls._pool = None
            logger.info("Database connection pool closed.")

from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg_pool import ConnectionPool
from src.config_loader import config

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base exception for database operations."""
    pass

class ConnectionPoolError(DatabaseError):
    """Raised when there are issues with the connection pool."""
    pass

class SchemaInitializationError(DatabaseError):
    """Raised when DDL execution fails."""
    pass

class DatabaseManager:
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
            # We use open=True but note that if DB is down, it might not fail immediately
            # unless we try to use a connection.
            self.pool = ConnectionPool(conninfo=self.conninfo, open=True)
            logger.info("Connection pool initialized.")

            if run_schema_init:
                # We'll try to initialize but catch connection errors to allow
                # the manager to be instantiated even if DB is temporarily down
                # (though in many cases you want it to fail fast)
                try:
                    self.initialize_schema()
                except SchemaInitializationError as e:
                    logger.warning(f"Initial schema setup deferred: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise ConnectionPoolError(f"Initialization failed: {e}")

    @contextmanager
    def get_connection(self) -> Generator[psycopg.Connection, None, None]:
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
            # Using a small timeout for schema check during startup
            with self.pool.connection(timeout=2.0) as conn:
                with conn.cursor() as cur:
                    cur.execute(ddl_script)
                    conn.commit()
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise SchemaInitializationError(f"DDL execution failed: {e}")

# Singleton instance
db_manager = None

def get_db_manager(run_schema_init: bool = True) -> DatabaseManager:
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager(run_schema_init=run_schema_init)
    return db_manager
