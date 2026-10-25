# test_import_side_effects.py
"""
F1-12: importing godml must not touch the host process. It used to install
global warning filters, overwrite TensorFlow env vars, configure root and
third-party loggers, and create logs/godml.log in the current directory.
"""

import json
import logging
import subprocess
import sys

PROBE = r"""
import json, logging, os, sys, warnings

# Core third-party deps first: they have their own import side effects
# (scikit-learn sets KMP_* env vars). Only godml's own changes count.
import numpy, pandas, sklearn, xgboost, mlflow  # noqa: F401

env_before = dict(os.environ)
filters_before = list(warnings.filters)
root_handlers_before = list(logging.getLogger().handlers)
levels_before = {n: logging.getLogger(n).level for n in ("mlflow", "sagemaker", "urllib3")}

import godml
import godml.monitoring_service.logger
import godml.core_service.executors
import godml.notebook_api
import godml.providers.mlflow
import godml.utils.scaffold

godml_logger = logging.getLogger("GODML")
print(json.dumps({
    "env_changed": sorted(
        k for k in set(env_before) | set(os.environ) if env_before.get(k) != os.environ.get(k)
    ),
    "filters_changed": list(warnings.filters) != filters_before,
    "root_handlers_changed": list(logging.getLogger().handlers) != root_handlers_before,
    "third_party_levels_changed": {
        n: logging.getLogger(n).level for n in levels_before
    } != levels_before,
    "godml_handlers": sorted(type(h).__name__ for h in godml_logger.handlers),
    "tensorflow_imported": "tensorflow" in sys.modules,
}))
"""


def probe(cwd) -> dict:
    out = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_import_creates_no_files(tmp_path):
    probe(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_import_leaves_process_state_alone(tmp_path):
    result = probe(tmp_path)
    assert result["env_changed"] == []
    assert result["filters_changed"] is False
    assert result["root_handlers_changed"] is False
    assert result["third_party_levels_changed"] is False


def test_optional_frameworks_are_not_imported(tmp_path):
    """TensorFlow changes env vars and is slow; a broken install broke `godml --help`."""
    assert probe(tmp_path)["tensorflow_imported"] is False


def test_library_logger_has_only_null_handler(tmp_path):
    assert probe(tmp_path)["godml_handlers"] == ["NullHandler"]


def test_cli_logging_writes_to_the_given_dir(tmp_path):
    """Output is configured only by the CLI, explicitly."""
    from godml.monitoring_service.logger import configure_cli_logging

    logger = logging.getLogger("GODML")
    saved = list(logger.handlers), logger.level, logger.propagate
    try:
        configure_cli_logging(log_dir=tmp_path)
        logger.info("hello from the cli")
        for h in logger.handlers:
            h.flush()
        assert "hello from the cli" in (tmp_path / "godml.log").read_text(
            encoding="utf-8"
        )
    finally:
        handlers, level, propagate = saved
        for h in list(logger.handlers):
            if h not in handlers:
                logger.removeHandler(h)
                h.close()
        logger.setLevel(level)
        logger.propagate = propagate
