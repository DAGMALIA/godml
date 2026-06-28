import pytest
from godml.compliance_service.compliance_utils import (
    hash_sha256,
    hash_truncated,
    mask_string,
    mask_email,
    mask_zip_code,
    mask_date,
    is_pii_column,
)


class TestHashSha256:
    def test_returns_64_char_hex(self):
        h = hash_sha256("test_value")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_none_returns_empty(self):
        assert hash_sha256(None) == ""

    def test_empty_string(self):
        h = hash_sha256("")
        assert len(h) == 64

    def test_deterministic(self):
        assert hash_sha256("godml") == hash_sha256("godml")

    def test_different_inputs_different_hashes(self):
        assert hash_sha256("abc") != hash_sha256("xyz")

    def test_numeric_input(self):
        h = hash_sha256(12345)
        assert len(h) == 64


class TestHashTruncated:
    def test_default_length_12(self):
        h = hash_truncated("test")
        assert len(h) == 12

    def test_custom_length(self):
        h = hash_truncated("test", 8)
        assert len(h) == 8

    def test_length_1_minimum(self):
        h = hash_truncated("test", 0)
        assert len(h) == 1

    def test_length_64_full(self):
        h = hash_truncated("test", 64)
        assert len(h) == 64

    def test_prefix_of_sha256(self):
        full = hash_sha256("test")
        truncated = hash_truncated("test", 10)
        assert full.startswith(truncated)


class TestMaskString:
    def test_normal_string_masked_with_prefix(self):
        result = mask_string("hello_world", num_prefix=2)
        assert result.startswith("he")
        assert "*" in result
        assert len(result) == len("hello_world")

    def test_with_prefix_and_suffix(self):
        result = mask_string("hello_world", num_prefix=2, num_suffix=3)
        assert result.startswith("he")
        assert result.endswith("rld")
        assert len(result) == len("hello_world")

    def test_short_string_fully_masked(self):
        result = mask_string("ab", num_prefix=2)
        assert result == "**"

    def test_exact_boundary(self):
        result = mask_string("abc", num_prefix=2, num_suffix=1)
        assert result == "***"

    def test_none_returns_empty(self):
        assert mask_string(None, num_prefix=2) == ""

    def test_custom_mask_char(self):
        result = mask_string("hello", num_prefix=1, mask_char="X")
        assert result.startswith("h")
        assert "X" in result


class TestMaskEmail:
    def test_valid_email_masks_user_keeps_domain(self):
        result = mask_email("user@example.com")
        assert "@example.com" in result
        assert result.startswith("us")
        assert "*" in result

    def test_email_without_at_masked_generically(self):
        result = mask_email("not-an-email")
        assert result.startswith("no")
        assert "*" in result

    def test_none_returns_empty(self):
        assert mask_email(None) == ""

    def test_empty_string_returns_empty(self):
        assert mask_email("") == ""

    def test_short_username_masked(self):
        result = mask_email("ab@domain.com")
        assert "@domain.com" in result


class TestMaskZipCode:
    def test_five_digit_zip(self):
        result = mask_zip_code("12345")
        assert result.startswith("12")
        assert "*" in result
        assert len(result) == 5

    def test_nine_digit_zip(self):
        result = mask_zip_code("12345-6789")
        assert result.startswith("12")

    def test_none_returns_empty(self):
        assert mask_zip_code(None) == ""

    def test_integer_input(self):
        result = mask_zip_code(10001)
        assert isinstance(result, str)
        assert result.startswith("10")


class TestMaskDate:
    def test_iso_date_keeps_year(self):
        result = mask_date("1990-07-15")
        assert result == "1990-**-**"

    def test_another_valid_date(self):
        result = mask_date("2023-12-31")
        assert result == "2023-**-**"

    def test_non_date_string(self):
        result = mask_date("not-a-date")
        assert result == "****-**-**"

    def test_none_returns_empty(self):
        assert mask_date(None) == ""

    def test_partial_date(self):
        result = mask_date("2020")
        assert result == "2020-**-**"


class TestIsPiiColumn:
    def test_email_column(self):
        assert is_pii_column("email")
        assert is_pii_column("user_email")
        assert is_pii_column("EMAIL")

    def test_name_column(self):
        assert is_pii_column("name")
        assert is_pii_column("full_name")
        assert is_pii_column("customer_name")

    def test_card_column(self):
        assert is_pii_column("card")
        assert is_pii_column("card_number")
        assert is_pii_column("credit_card")

    def test_ssn_column(self):
        assert is_pii_column("ssn")
        assert is_pii_column("social_ssn")

    def test_address_column(self):
        assert is_pii_column("address")
        assert is_pii_column("home_address")

    def test_zip_column(self):
        assert is_pii_column("zip")
        assert is_pii_column("zip_code")
        assert is_pii_column("postal")

    def test_dob_birth_column(self):
        assert is_pii_column("dob")
        assert is_pii_column("birth")
        assert is_pii_column("birth_date")

    def test_non_pii_columns(self):
        assert not is_pii_column("age")
        assert not is_pii_column("score")
        assert not is_pii_column("feature_1")
        assert not is_pii_column("label")
        assert not is_pii_column("amount")
        assert not is_pii_column("price")

    def test_empty_and_none(self):
        assert not is_pii_column("")
        assert not is_pii_column(None)
