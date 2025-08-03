# config_service/loader.py
import yaml
from .schema import Config
from .resolver import resolve_env_variables

def load_config(path):
    with open(path) as f:
        raw = yaml.safe_load(f)
    resolved = resolve_env_variables(raw)
    return Config(**resolved)
