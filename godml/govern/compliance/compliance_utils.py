import hashlib
import hmac
import logging
import os
import re

from godml.govern.compliance.errors import ComplianceError

logger = logging.getLogger("godml.compliance")

# F1-06: public, insecure key. Only used outside prod when the user opts in
# with GODML_ALLOW_INSECURE_PII_KEY=1; otherwise GODML_PII_KEY is required.
DEV_PII_KEY = "godml-dev-insecure-pii-key"
_PROD_ENVS = {"prod", "production"}
_GENERATE_HINT = (
    'Generate one with: python -c "import secrets; print(secrets.token_hex(32))" '
    "and keep it secret (the same key must be used for training and serving)."
)
_warned_dev_key = False


def pii_hash_key() -> str:
    """Secret for PII hashing: GODML_PII_KEY, required whenever compliance runs.

    Outside prod, GODML_ALLOW_INSECURE_PII_KEY=1 falls back to a public dev
    key (hashes are then NOT protected).
    """
    global _warned_dev_key
    key = os.environ.get("GODML_PII_KEY", "").strip()
    if key:
        return key
    is_prod = os.environ.get("GODML_ENV", "dev").strip().lower() in _PROD_ENVS
    opted_in = os.environ.get("GODML_ALLOW_INSECURE_PII_KEY", "").strip() == "1"
    if opted_in and not is_prod:
        if not _warned_dev_key:
            logger.warning(
                "GODML_PII_KEY is not set and GODML_ALLOW_INSECURE_PII_KEY=1: "
                "hashing PII with the public dev key. These hashes are NOT "
                "protected; never use this with real data."
            )
            _warned_dev_key = True
        return DEV_PII_KEY
    if opted_in:
        raise ComplianceError(
            "GODML_ALLOW_INSECURE_PII_KEY is not allowed with GODML_ENV=prod: "
            f"set GODML_PII_KEY. {_GENERATE_HINT}"
        )
    raise ComplianceError(
        "GODML_PII_KEY is required when compliance is enabled. "
        f"{_GENERATE_HINT} For throwaway local tests only, set "
        "GODML_ALLOW_INSECURE_PII_KEY=1 (not allowed in prod)."
    )


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


def name_tokens(col_name: str) -> list[str]:
    """`customerEmail`, `zip-code` -> ["customer", "email"], ["zip", "code"]."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(col_name or ""))
    return [t for t in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if t]


def name_has_hint(col_name: str, hint: str) -> bool:
    """Whole-token match (F1-07): "tel" matches `tel_casa`, not `hotel_id`.

    Multi-token hints such as "cc_num" must appear as consecutive tokens.
    """
    tokens, wanted = name_tokens(col_name), name_tokens(hint)
    n = len(wanted)
    return n > 0 and any(
        tokens[i : i + n] == wanted for i in range(len(tokens) - n + 1)
    )


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
    return any(name_has_hint(col_name, k) for k in pii_keywords)
