# Copyright (c) 2024 Arturo Gutierrez Rubio Rojas
# SPDX-License-Identifier: MIT
"""Regenerate the published JSON Schema: python -m godml.core.spec [PATH]."""

import sys
from pathlib import Path

from godml.core.spec.v2 import write_json_schema

if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "schemas/godml-v2.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json_schema(target)
