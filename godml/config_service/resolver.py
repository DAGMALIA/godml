# config_service/resolver.py
import os
import re

from godml.monitoring_service.logger import ConfigurationError

env_var_pattern = re.compile(r"\$\{(\w+)(?::([^\}]*))?\}")


def _resolve_string(value: str):
    """Interpolate every `${VAR}` / `${VAR:default}` inside `value` (F1-09).

    A value that is exactly one `${VAR}` keeps the 1.x behavior: unset and
    without default it becomes None. Inside a longer string an unset variable
    without default is an error, so a path never silently loses a segment.
    """
    whole = env_var_pattern.fullmatch(value)
    if whole:
        env_var, default = whole.groups()
        return os.getenv(env_var, default)

    def substitute(match: re.Match) -> str:
        env_var, default = match.groups()
        resolved = os.getenv(env_var, default)
        if resolved is None:
            raise ConfigurationError(
                f"Environment variable '{env_var}' is not set and has no default "
                f"in '{value}'. Set it or use ${{{env_var}:default}}."
            )
        return resolved

    return env_var_pattern.sub(substitute, value)


def _resolve(value):
    if isinstance(value, str):
        return _resolve_string(value)
    if isinstance(value, dict):
        return {k: _resolve(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(item) for item in value]
    return value


def resolve_env_variables(config_dict):
    """Resolve env vars in a config dict, recursing into nested dicts and lists."""
    return _resolve(config_dict)
