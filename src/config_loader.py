import os
import yaml
from typing import Any, Dict

class Config:
    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

def load_config(config_path: str = "config/config.yaml") -> Config:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)

    # Override with environment variables if present
    db_conn = os.environ.get("DATABASE_CONNECTION_STRING")
    if db_conn:
        if 'database' not in config_dict:
            config_dict['database'] = {}
        config_dict['database']['connection_string'] = db_conn

    qdrant_host = os.environ.get("QDRANT_HOST")
    if qdrant_host:
        if 'qdrant' not in config_dict:
            config_dict['qdrant'] = {}
        config_dict['qdrant']['host'] = qdrant_host

    return Config(config_dict)

# Global configuration instance
config = load_config()
