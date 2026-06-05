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
