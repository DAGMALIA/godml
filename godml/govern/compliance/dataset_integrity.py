# compliance_service/dataset_integrity.py
# SPDX-License-Identifier: MIT
"""Pinned dataset hash verification (F1-05)."""

import os
from typing import Optional

from godml.govern.compliance.errors import DatasetIntegrityError
from godml.govern.hash import calculate_file_hash


def is_pinned(expected: Optional[str]) -> bool:
    """A hash is pinned unless it is empty or 'auto'."""
    return bool(expected and expected.strip() and expected.strip().lower() != "auto")


def verify_dataset_hash(path: str, expected: Optional[str]) -> None:
    """Fail-closed check of `path` against a pinned SHA-256 (hex, optional 'sha256:')."""
    if not is_pinned(expected):
        return
    assert expected is not None  # narrowed by is_pinned
    pinned = expected.strip().lower().removeprefix("sha256:")
    if not os.path.exists(path):
        raise DatasetIntegrityError(
            f"dataset.hash is pinned but the dataset does not exist: {path}"
        )
    actual = calculate_file_hash(path)
    if actual != pinned:
        raise DatasetIntegrityError(
            f"dataset.hash mismatch for {path}: pinned {pinned}, actual {actual}. "
            "The data changed since the hash was pinned. If the change is "
            "intended, update it with `godml calc-hash <file> --update-yaml <godml.yml>`."
        )
