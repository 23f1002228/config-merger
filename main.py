import os
from pathlib import Path
from typing import Any, Dict, List
import yaml
from dotenv import load_dotenv, dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI application
app = FastAPI(title="Configuration Merger Service")

# Enable CORSMiddleware per requirements
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Call load_dotenv() at startup as requested
load_dotenv()

# Supported configuration keys
SUPPORTED_KEYS = {"port", "workers", "debug", "log_level", "api_key"}

# Layer 1: Hardcoded defaults inside Python
DEFAULTS: Dict[str, Any] = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def coerce_value(key: str, value: Any) -> Any:
    """
    Perform type conversion for configuration values.
    
    - 'port': must become integer.
    - 'workers': must become integer.
    - 'debug': must become boolean. Boolean TRUE values are: 'true', '1', 'yes', 'on'
               (case-insensitive). Everything else becomes FALSE.
    - 'log_level': must remain string.
    - 'api_key': must remain string.
    
    Raises:
        ValueError: If integer conversion fails.
    """
    if key in ("port", "workers"):
        if isinstance(value, int):
            return value
        # Attempt conversion from string or float-like string
        try:
            return int(float(str(value)))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert '{value}' to integer for key '{key}'") from e

    elif key == "debug":
        if isinstance(value, bool):
            return value
        val_str = str(value).strip().lower()
        return val_str in ("true", "1", "yes", "on")

    elif key in ("log_level", "api_key"):
        return str(value)

    return value


def load_defaults() -> Dict[str, Any]:
    """
    Load Layer 1: Hardcoded defaults.
    Ensures correct types are applied from the start.
    """
    config: Dict[str, Any] = {}
    for key, val in DEFAULTS.items():
        try:
            config[key] = coerce_value(key, val)
        except ValueError:
            # Fallback to default raw value if coercion somehow fails
            config[key] = val
    return config


def load_yaml() -> Dict[str, Any]:
    """
    Load Layer 2: Environment-specific YAML (config.development.yaml).
    If the file does not exist or is empty, returns an empty dict.
    Continues gracefully on any errors.
    """
    config: Dict[str, Any] = {}
    yaml_path = Path("config.development.yaml")
    
    if not yaml_path.exists():
        return config

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not data or not isinstance(data, dict):
                return config
            
            for key, val in data.items():
                if key in SUPPORTED_KEYS:
                    try:
                        config[key] = coerce_value(key, val)
                    except ValueError:
                        # Ignore this specific key update if type coercion fails
                        pass
    except Exception:
        # Continue gracefully on file errors
        pass
    return config


def load_dotenv_layer() -> Dict[str, Any]:
    """
    Load Layer 3: .env file.
    Uses dotenv_values to read the file directly without modifying os.environ.
    Inside the .env layer, NUM_WORKERS must map to workers.
    Continues gracefully if the file does not exist.
    """
    config: Dict[str, Any] = {}
    dotenv_path = Path(".env")
    
    if not dotenv_path.exists():
        return config

    try:
        dotenv_data = dotenv_values(dotenv_path)
        
        # Mapping from .env variables to internal config keys
        mapping = {
            "APP_PORT": "port",
            "NUM_WORKERS": "workers",  # Special alias only for .env layer
            "APP_DEBUG": "debug",
            "APP_LOG_LEVEL": "log_level",
            "APP_API_KEY": "api_key",
        }
        
        for env_key, val in dotenv_data.items():
            mapped_key = mapping.get(env_key)
            if mapped_key and val is not None:
                try:
                    config[mapped_key] = coerce_value(mapped_key, val)
                except ValueError:
                    # Ignore this specific key update if type coercion fails
                    pass
    except Exception:
        # Continue gracefully on errors
        pass
    return config


def load_os_env() -> Dict[str, Any]:
    """
    Load Layer 4: OS Environment Variables.
    Reads dynamically using os.getenv() so that external updates are visible.
    Does NOT map NUM_WORKERS to workers.
    """
    config: Dict[str, Any] = {}
    
    # OS Environment variable mapping
    mapping = {
        "APP_PORT": "port",
        "APP_WORKERS": "workers",  # Standard OS env workers key
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
    }
    
    for env_key, mapped_key in mapping.items():
        val = os.getenv(env_key)
        if val is not None:
            try:
                config[mapped_key] = coerce_value(mapped_key, val)
            except ValueError:
                # Ignore this specific key update if type coercion fails
                pass
    return config


def apply_cli_overrides(config: Dict[str, Any], set_params: List[str]) -> Dict[str, Any]:
    """
    Load Layer 5: CLI Overrides from Query Parameters.
    Each parameter is formatted as key=value.
    If value cannot convert to integer for port/workers, that override is ignored.
    """
    overridden_config = dict(config)
    for param in set_params:
        if "=" not in param:
            continue
        parts = param.split("=", 1)
        key = parts[0].strip()
        val = parts[1]
        
        if key in SUPPORTED_KEYS:
            try:
                overridden_config[key] = coerce_value(key, val)
            except ValueError:
                # If CLI value cannot convert to integer, ignore that override.
                pass
    return overridden_config


def merge_configs(
    defaults: Dict[str, Any],
    yaml_cfg: Dict[str, Any],
    dotenv_cfg: Dict[str, Any],
    os_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge the four configuration layers with strict precedence:
    Defaults < YAML < .env < OS Env.
    """
    merged = {}
    merged.update(defaults)
    merged.update(yaml_cfg)
    merged.update(dotenv_cfg)
    merged.update(os_cfg)
    return merged


def mask_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask the api_key field to '****' for the response.
    Returns a dictionary with keys ordered exactly as:
    port, workers, debug, log_level, api_key.
    """
    order = ["port", "workers", "debug", "log_level", "api_key"]
    masked: Dict[str, Any] = {}
    for key in order:
        if key == "api_key":
            masked[key] = "****"
        else:
            masked[key] = config.get(key)
    return masked


@app.get("/effective-config")
def get_effective_config(set: List[str] = Query(default=[])):
    """
    Endpoint that merges the configuration layers and applies CLI overrides.
    Returns the final configuration with api_key masked.
    """
    # 1. Load configuration from layers 1-4
    defaults = load_defaults()
    yaml_cfg = load_yaml()
    dotenv_cfg = load_dotenv_layer()
    os_cfg = load_os_env()

    # 2. Merge the configuration layers
    merged_config = merge_configs(defaults, yaml_cfg, dotenv_cfg, os_cfg)

    # 3. Apply layer 5: CLI query parameters overrides
    final_config = apply_cli_overrides(merged_config, set)

    # 4. Mask secrets and enforce correct response ordering
    return mask_config(final_config)
