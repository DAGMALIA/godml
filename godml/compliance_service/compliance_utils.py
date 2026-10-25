import hashlib
import hmac
import logging
import os

from godml.compliance_service.errors import ComplianceError

logger = logging.getLogger("godml.compliance")

# F1-06: public, insecure key used only outside prod when GODML_PII_KEY is
# unset, so hashed features stay stable between training and serving in dev.
DEV_PII_KEY = "godml-dev-insecure-pii-key"
_PROD_ENVS = {"prod", "production"}
_warned_dev_key = False


def pii_hash_key() -> str:
    """Secret for PII hashing: GODML_PII_KEY; mandatory when GODML_ENV is prod."""
    global _warned_dev_key
    key = os.environ.get("GODML_PII_KEY", "").strip()
    if key:
        return key
    if os.environ.get("GODML_ENV", "dev").strip().lower() in _PROD_ENVS:
        raise ComplianceError(
            "GODML_PII_KEY is required in prod to hash PII (hash_sensitive "
            "policy). Set it to a secret value; refusing to continue."
        )
    if not _warned_dev_key:
        logger.warning(
            "GODML_PII_KEY is not set: hashing PII with the public dev key. "
            "These hashes are NOT protected; set GODML_PII_KEY for real data "
            "(it is mandatory with GODML_ENV=prod)."
        )
        _warned_dev_key = True
    return DEV_PII_KEY


def hmac_truncated(value, key: str, length: int = 12) -> str:
    """HMAC-SHA256 of `value`, truncated to `length` hex chars ('' for None)."""
    if value is None:
        return ""
    digest = hmac.new(key.encode("utf-8"), str(value).encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()[: max(1, int(length))]


def hash_sha256(value) -> str:
    if value is None:
        return ""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def hash_truncated(value, length: int = 12) -> str:
    return hash_sha256(value)[: max(1, int(length))]


def mask_string(
    value: str, num_prefix: int = 2, num_suffix: int = 0, mask_char: str = "*"
) -> str:
    if value is None:
        return ""
    s = str(value)
    if len(s) <= (num_prefix + num_suffix):
        return mask_char * len(s)
    middle_len = len(s) - num_prefix - num_suffix
    return (
        s[:num_prefix]
        + (mask_char * middle_len)
        + (s[-num_suffix:] if num_suffix > 0 else "")
    )


def mask_email(email: str) -> str:
    if not email:
        return ""
    email = str(email)
    if "@" not in email:
        return mask_string(email, num_prefix=2)
    user, domain = email.split("@", 1)
    user_mask = mask_string(user, num_prefix=2)
    return f"{user_mask}@{domain}"


def mask_zip_code(zip_code) -> str:
    if zip_code is None:
        return ""
    s = str(zip_code)
    return s[:2] + "*" * max(0, len(s) - 2)


def mask_date(date_str) -> str:
    if date_str is None:
        return ""
    s = str(date_str)
    if len(s) >= 4 and s[:4].isdigit():
        return s[:4] + "-**-**"
    return "****-**-**"


def is_pii_column(col_name: str) -> bool:
    if not col_name:
        return False
    pii_keywords = [
        "name",
        "email",
        "address",
        "ssn",
        "card",
        "cvv",
        "zip",
        "postal",
        "dob",
        "birth",
    ]
    lower = col_name.lower()
    return any(k in lower for k in pii_keywords)
