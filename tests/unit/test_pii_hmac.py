# test_pii_hmac.py
"""
F1-06: hash_sensitive used an unkeyed SHA-256 truncated to 12 hex chars,
reversible by brute force for card numbers and emails. PII is hashed with
HMAC-SHA256 keyed by GODML_PII_KEY, and the key is required whenever
compliance is applied, in any environment. The only escape hatch is
GODML_ALLOW_INSECURE_PII_KEY=1 outside prod (public dev key, with a warning).
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
from godml.core_service.preprocessor import ComplianceEngine

EMAIL = "person@example.com"


@pytest.fixture
def env(monkeypatch):
    for var in ("GODML_PII_KEY", "GODML_ENV", "GODML_ALLOW_INSECURE_PII_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(utils, "_warned_dev_key", False)
    return monkeypatch


def emails() -> pd.DataFrame:
    return pd.DataFrame({"email": [EMAIL, "other@example.com"]})


def hashed_email() -> str:
    return PciDssCompliance(policy="hash_sensitive").apply(emails())["email"].iloc[0]


def expected_hmac(key: str, length: int = 12) -> str:
    return hmac.new(key.encode(), EMAIL.encode(), hashlib.sha256).hexdigest()[:length]


class TestKeyedHash:
    def test_uses_keyed_hmac_not_plain_sha256(self, env):
        env.setenv("GODML_PII_KEY", "s3cret")
        value = hashed_email()
        assert value == expected_hmac("s3cret")
        assert value != hash_truncated(EMAIL)  # the 1.x reversible hash

    def test_different_keys_give_different_hashes(self, env):
        env.setenv("GODML_PII_KEY", "key-a")
        a = hashed_email()
        env.setenv("GODML_PII_KEY", "key-b")
        assert hashed_email() != a

    def test_stable_for_the_same_key(self, env):
        env.setenv("GODML_PII_KEY", "key-a")
        assert hashed_email() == hashed_email()


class TestKeyRequired:
    @pytest.mark.parametrize("environment", [None, "dev", "qa", "prod"])
    @pytest.mark.parametrize(
        "policy", ["hash_sensitive", "mask_sensitive", "drop_sensitive"]
    )
    def test_missing_key_fails_in_any_env_and_policy(self, env, environment, policy):
        if environment:
            env.setenv("GODML_ENV", environment)
        with pytest.raises(ComplianceError) as excinfo:
            PciDssCompliance(policy=policy).apply(emails())
        message = str(excinfo.value)
        assert "GODML_PII_KEY" in message
        assert "secrets.token_hex(32)" in message

    def test_engine_path_fails_closed(self, env):
        with pytest.raises(ComplianceError, match="GODML_PII_KEY"):
            ComplianceEngine.apply(emails(), "pci-dss", "mask_sensitive")

    def test_blank_key_counts_as_missing(self, env):
        env.setenv("GODML_PII_KEY", "   ")
        with pytest.raises(ComplianceError):
            pii_hash_key()


class TestInsecureOptIn:
    def test_opt_in_outside_prod_uses_dev_key_and_warns(self, env):
        env.setenv("GODML_ALLOW_INSECURE_PII_KEY", "1")
        warnings_logged: list[str] = []
        env.setattr(
            utils.logger, "warning", lambda m, *a, **k: warnings_logged.append(m)
        )
        assert hashed_email() == expected_hmac(DEV_PII_KEY)
        assert any("GODML_PII_KEY" in m for m in warnings_logged)

    @pytest.mark.parametrize("prod", ["prod", "PROD", "production"])
    def test_opt_in_is_ignored_in_prod(self, env, prod):
        env.setenv("GODML_ALLOW_INSECURE_PII_KEY", "1")
        env.setenv("GODML_ENV", prod)
        with pytest.raises(ComplianceError, match="GODML_ALLOW_INSECURE_PII_KEY"):
            hashed_email()

    @pytest.mark.parametrize("value", ["0", "true", "yes", ""])
    def test_only_the_value_1_opts_in(self, env, value):
        env.setenv("GODML_ALLOW_INSECURE_PII_KEY", value)
        with pytest.raises(ComplianceError):
            hashed_email()


def test_hmac_truncated_length_and_none():
    assert len(hmac_truncated("x", "k", 8)) == 8
    assert hmac_truncated(None, "k") == ""
