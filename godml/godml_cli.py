# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT

import os

# CLI only (F1-12): quiet TensorFlow before anything imports it, without
# overriding values the user already set. The library never touches os.environ.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

from godml.cli.app import app  # noqa: E402
from godml.monitoring_service.logger import configure_cli_logging  # noqa: E402


def main():
    configure_cli_logging()
    app()


if __name__ == "__main__":
    main()
