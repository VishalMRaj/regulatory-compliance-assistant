import os
import yaml
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Base class for configuration errors."""
    pass

class ConfigFileNotFoundError(ConfigError):
    """Raised when the configuration file is not found."""
    pass

class ConfigValidationError(ConfigError):
    """Raised when the configuration is invalid."""
    pass

@dataclass(frozen=True)
class DatabaseConfig:
    connection_string: Optional[str]
    pool_min_size: int
    pool_max_size: int
    host: str
    port: int
    user: str
    password: str
    database: str

@dataclass(frozen=True)
class QdrantConfig:
    host: str
    port: int
    collection_name: str

@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig
    qdrant: QdrantConfig

def get_env_or_config(config_dict: Dict, keys: list, env_var: str, default: Any = None) -> Any:
    env_val = os.getenv(env_var)
    if env_val is not None:
        return env_val

    curr = config_dict
    try:
        for k in keys:
            curr = curr[k]
        # Handle cases where the value might be a string with ${VAR}
        if isinstance(curr, str) and curr.startswith("${") and curr.endswith("}"):
            var_name = curr[2:-1]
            return os.getenv(var_name, default)
        return curr
    except (KeyError, TypeError):
        return default

def load_config(config_path: str = "config/config.yaml") -> AppConfig:
    config_dict = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise ConfigValidationError(f"Invalid YAML format: {e}")
    else:
        logger.warning(f"Configuration file not found: {config_path}. Relying on environment variables.")

    try:
        # Database
        db_conn = get_env_or_config(config_dict, ["database", "connection_string"], "DATABASE_CONNECTION_STRING")
        db_min = int(get_env_or_config(config_dict, ["database", "pool_min_size"], "DB_POOL_MIN", 1))
        db_max = int(get_env_or_config(config_dict, ["database", "pool_max_size"], "DB_POOL_MAX", 10))

        db_host = get_env_or_config(config_dict, ["database", "state_store", "host"], "DB_HOST", "localhost")
        db_port = int(get_env_or_config(config_dict, ["database", "state_store", "port"], "DB_PORT", 5432))
        db_user = get_env_or_config(config_dict, ["database", "state_store", "user"], "DB_USER", "postgres")
        db_pass = get_env_or_config(config_dict, ["database", "state_store", "password"], "DB_PASSWORD", "password")
        db_name = get_env_or_config(config_dict, ["database", "state_store", "database"], "DB_NAME", "compliance_state")

        db_config = DatabaseConfig(
            connection_string=db_conn,
            pool_min_size=db_min,
            pool_max_size=db_max,
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name
        )

        # Qdrant
        qd_host = get_env_or_config(config_dict, ["qdrant", "host"], "QDRANT_HOST", "localhost")
        qd_port = int(get_env_or_config(config_dict, ["qdrant", "port"], "QDRANT_PORT", 6333))
        qd_coll = get_env_or_config(config_dict, ["qdrant", "collection_name"], "QDRANT_COLLECTION", "regulatory_compliance")

        qdrant_config = QdrantConfig(
            host=qd_host,
            port=qd_port,
            collection_name=qd_coll
        )

        return AppConfig(database=db_config, qdrant=qdrant_config)
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise ConfigValidationError(f"Validation failed: {e}")

# Global configuration instance
try:
    config = load_config()
except ConfigError:
    config = None
