# test_pii_hmac.py
"""
F1-06: hash_sensitive used an unkeyed SHA-256 truncated to 12 hex chars.
PII has a small, guessable value space (card numbers, emails), so those
hashes could be reversed by brute force or a dictionary. It is now an
HMAC-SHA256 keyed by GODML_PII_KEY, which is mandatory in prod.
"""

import hashlib
import hmac

import pandas as pd
import pytest

import godml.compliance_service.compliance_utils as utils
from godml.compliance_service.compliance_utils import (
    DEV_PII_KEY,
    hash_truncated,
    hmac_truncated,
    pii_hash_key,
)
from godml.compliance_service.errors import ComplianceError
from godml.compliance_service.pci_dss import PciDssCompliance

EMAIL = "person@example.com"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.delenv("GODML_PII_KEY", raising=False)
    monkeypatch.delenv("GODML_ENV", raising=False)
    monkeypatch.setattr(utils, "_warned_dev_key", False)
    return monkeypatch


def hashed_email(policy_env) -> str:
    df = pd.DataFrame({"email": [EMAIL, "other@example.com"]})
    return PciDssCompliance(policy="hash_sensitive").apply(df)["email"].iloc[0]


def expected_hmac(key: str, length: int = 12) -> str:
    return hmac.new(key.encode(), EMAIL.encode(), hashlib.sha256).hexdigest()[:length]


class TestHashSensitivePolicy:
    def test_uses_keyed_hmac_not_plain_sha256(self, env):
        env.setenv("GODML_PII_KEY", "s3cret")
        value = hashed_email(env)
        assert value == expected_hmac("s3cret")
        assert value != hash_truncated(EMAIL)  # the 1.x reversible hash

    def test_different_keys_give_different_hashes(self, env):
        env.setenv("GODML_PII_KEY", "key-a")
        a = hashed_email(env)
        env.setenv("GODML_PII_KEY", "key-b")
        assert hashed_email(env) != a

    def test_stable_for_the_same_key(self, env):
        env.setenv("GODML_PII_KEY", "key-a")
        assert hashed_email(env) == hashed_email(env)

    @pytest.mark.parametrize("prod", ["prod", "PROD", "production"])
    def test_prod_without_key_fails_closed(self, env, prod):
        env.setenv("GODML_ENV", prod)
        with pytest.raises(ComplianceError, match="GODML_PII_KEY"):
            hashed_email(env)

    def test_dev_without_key_uses_dev_key_and_warns(self, env):
        warnings_logged: list[str] = []
        env.setattr(
            utils.logger, "warning", lambda m, *a, **k: warnings_logged.append(m)
        )
        assert hashed_email(env) == expected_hmac(DEV_PII_KEY)
        assert any("GODML_PII_KEY" in m for m in warnings_logged)

    def test_mask_policy_does_not_need_a_key_in_prod(self, env):
        env.setenv("GODML_ENV", "prod")
        df = pd.DataFrame({"email": [EMAIL]})
        PciDssCompliance(policy="mask_sensitive").apply(df)


class TestHelpers:
    def test_hmac_truncated_length_and_none(self):
        assert len(hmac_truncated("x", "k", 8)) == 8
        assert hmac_truncated(None, "k") == ""

    def test_empty_key_counts_as_missing(self, env):
        env.setenv("GODML_ENV", "prod")
        env.setenv("GODML_PII_KEY", "   ")
        with pytest.raises(ComplianceError):
            pii_hash_key()
