# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT

import os
import sys

# CLI only (F1-12): quiet TensorFlow before anything imports it, without
# overriding values the user already set. The library never touches os.environ.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

from godml.cli.app import app  # noqa: E402
from godml.monitoring_service.logger import configure_cli_logging  # noqa: E402


def _tolerate_any_terminal_encoding() -> None:
    """F1-20: never crash on output a non-UTF-8 terminal cannot encode.

    Characters the stream cannot represent (accents on an ASCII console,
    emoji on cp1252) are printed as "?" instead of raising UnicodeEncodeError.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def main():
    _tolerate_any_terminal_encoding()
    configure_cli_logging()
    app()


if __name__ == "__main__":
    main()
