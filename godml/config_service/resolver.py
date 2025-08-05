# config_service/resolver.py
import os
import re

env_var_pattern = re.compile(r"\$\{(\w+)(?::([^\}]+))?\}")

def resolve_env_variables(config_dict):
    def resolve_value(value):
        if isinstance(value, str):
            match = env_var_pattern.search(value)
            if match:
                env_var, default = match.groups()
                return os.getenv(env_var, default)
        return value

    resolved = {}
    for k, v in config_dict.items():
        if isinstance(v, dict):
            resolved[k] = resolve_env_variables(v)
        elif isinstance(v, list):
            resolved[k] = [resolve_value(i) for i in v]
        else:
            resolved[k] = resolve_value(v)
    return resolved
