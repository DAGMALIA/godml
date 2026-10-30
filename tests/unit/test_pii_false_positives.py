# test_pii_false_positives.py
"""
F1-07: name hints matched as substrings ("tel" in hotel_id, "lat" in plate,
"ip" in tip) and ambiguous content patterns (any 3-4 digit number was a CVV,
any 5-digit number a zip code, any float with 4 decimals a coordinate) made
PCI-DSS drop or hash ordinary features, including the target.
"""

import pandas as pd
import pytest

from godml.compliance_service.compliance_utils import is_pii_column
from godml.compliance_service.pci_dss import PciDssCompliance
from godml.compliance_service.pii_detector import PiiDetector
from godml.config_service.schema import PipelineDefinition
from godml.core_service.pipeline_runner import run_pipeline_preprocessing

NOT_PII = {
    "hotel_id": [1001, 1002, 1003],
    "plate": ["ABC123", "XYZ789", "JKL456"],
    "year": [2019, 2020, 2021],
    "fare": [350, 999, 1225],
    "tip": [10, 20, 15],
    "description": ["window seat", "aisle", "upgrade"],
    "latency_ms": [120.1234, 130.5678, 99.9001],
    "amount": [12345, 67890, 11111],
    "score": [0.1234, 0.5678, 0.9012],
    "filename": ["a.csv", "b.csv", "c.csv"],
}


@pytest.fixture
def detector():
    return PiiDetector()


@pytest.mark.parametrize("column", list(NOT_PII))
def test_ordinary_columns_are_not_pii(detector, column):
    series = pd.Series(NOT_PII[column])
    assert detector.detect_column_type(series, column) == "unknown"
    assert is_pii_column(column) is False


def test_drop_policy_keeps_ordinary_columns():
    df = pd.DataFrame(NOT_PII)
    out = PciDssCompliance(policy="drop_sensitive").apply(df)
    assert list(out.columns) == list(df.columns)


@pytest.mark.parametrize(
    "column, values, expected",
    [
        ("zip_code", ["12345", "90210", "10001"], "zip_code"),
        ("codigo_postal", ["01000", "64000", "44100"], "zip_code"),
        ("cvv", ["123", "456", "789"], "cvv"),
        ("card_cvv", ["123", "456", "789"], "cvv"),
        ("lat", [19.432608, 20.659698, 25.686613], "coordinates"),
        ("pickup_longitude", [-99.133209, -103.349609, -100.316116], "coordinates"),
        ("customer_email", ["a@b.com", "c@d.org", "e@f.net"], "email"),
        ("mobile", ["5512345678", "5587654321", "5511223344"], "phone_us"),
        ("cc_num", ["4111111111111111"] * 3, "card_number"),
    ],
)
def test_real_pii_is_still_detected(detector, column, values, expected):
    assert detector.detect_column_type(pd.Series(values), column) == expected


@pytest.mark.parametrize(
    "column", ["first_name", "home_address", "zip", "email", "dob"]
)
def test_name_heuristic_matches_whole_tokens(column):
    assert is_pii_column(column) is True


def test_camel_case_names_are_tokenized(detector):
    assert detector.detect_column_type(pd.Series(["x"]), "customerEmail") == "email"
    assert detector.detect_column_type(pd.Series([1]), "hotelId") == "unknown"


def test_expiration_needs_a_separator(detector):
    assert detector.detect_column_type(pd.Series(["12/25", "01/27"]), "x") == (
        "expiration_date"
    )
    assert detector.detect_column_type(pd.Series(["1225", "0127"]), "x") == "unknown"


class TestTargetIsNeverTouched:
    def test_excluded_column_survives_drop(self):
        df = pd.DataFrame(
            {"email": ["a@b.com", "c@d.org"], "zip_code": ["12345", "54321"]}
        )
        out = PciDssCompliance(
            policy="drop_sensitive", exclude_columns=["zip_code"]
        ).apply(df)
        assert list(out.columns) == ["zip_code"]
        assert list(out["zip_code"]) == ["12345", "54321"]

    def test_pipeline_target_is_excluded(self, minimal_pipeline_config, tmp_path):
        config = dict(minimal_pipeline_config)
        config["dataset"] = {
            "uri": str(tmp_path / "d.csv"),
            "hash": "auto",
            "target": "zip_code",
        }
        config["governance"] = {
            "owner": "o@x.com",
            "compliance": "pci-dss",
            "policy": "drop_sensitive",
        }
        df = pd.DataFrame(
            {"email": ["a@b.com", "c@d.org"], "zip_code": ["12345", "54321"]}
        )
        out = run_pipeline_preprocessing(PipelineDefinition(**config), df)
        assert "zip_code" in out.columns
        assert "email" not in out.columns
