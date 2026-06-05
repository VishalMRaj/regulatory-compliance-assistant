import os
import yaml
import logging
from dataclasses import dataclass, field
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
    host: str
    port: int
    user: str
    password: str
    database: str

@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig

def get_env_or_config(config_dict: Dict, keys: list, env_var: str, default: Any = None) -> Any:
    """Helper to get value from environment variable or config dictionary."""
    env_val = os.getenv(env_var)
    if env_val is not None:
        return env_val

    curr = config_dict
    try:
        for k in keys:
            curr = curr[k]
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
        host = get_env_or_config(config_dict, ["database", "state_store", "host"], "DB_HOST", "localhost")
        port = int(get_env_or_config(config_dict, ["database", "state_store", "port"], "DB_PORT", 5432))
        user = get_env_or_config(config_dict, ["database", "state_store", "user"], "DB_USER", "postgres")
        password = get_env_or_config(config_dict, ["database", "state_store", "password"], "DB_PASSWORD", "password")
        database = get_env_or_config(config_dict, ["database", "state_store", "database"], "DB_NAME", "compliance_state")

        db_config = DatabaseConfig(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        return AppConfig(database=db_config)
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise ConfigValidationError(f"Validation failed: {e}")

# Global configuration instance
try:
    config = load_config()
except ConfigError:
    config = None
