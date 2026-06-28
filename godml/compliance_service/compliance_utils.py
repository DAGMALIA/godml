import hashlib


def hash_sha256(value) -> str:
    if value is None:
        return ""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def hash_truncated(value, length: int = 12) -> str:
    return hash_sha256(value)[:max(1, int(length))]


def mask_string(value: str, num_prefix: int = 2, num_suffix: int = 0, mask_char: str = "*") -> str:
    if value is None:
        return ""
    s = str(value)
    if len(s) <= (num_prefix + num_suffix):
        return mask_char * len(s)
    middle_len = len(s) - num_prefix - num_suffix
    return s[:num_prefix] + (mask_char * middle_len) + (s[-num_suffix:] if num_suffix > 0 else "")


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
    pii_keywords = ["name", "email", "address", "ssn", "card", "cvv", "zip", "postal", "dob", "birth"]
    lower = col_name.lower()
    return any(k in lower for k in pii_keywords)
