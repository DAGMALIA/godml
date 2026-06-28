import pytest
import pandas as pd
from godml.compliance_service.pii_detector import PiiDetector


class TestPiiDetectorColumnType:
    def setup_method(self):
        self.detector = PiiDetector()

    def test_detects_email(self):
        s = pd.Series(["user@example.com", "admin@test.org", "john@company.co"])
        assert self.detector.detect_column_type(s) == "email"

    def test_detects_ssn(self):
        s = pd.Series(["123-45-6789", "987-65-4321", "456-78-9012"])
        assert self.detector.detect_column_type(s) == "ssn"

    def test_detects_zip_code(self):
        s = pd.Series(["12345", "90210", "10001"])
        assert self.detector.detect_column_type(s) == "zip_code"

    def test_detects_dob(self):
        s = pd.Series(["1990-07-15", "2000-01-01", "1985-12-31"])
        assert self.detector.detect_column_type(s) == "dob"

    def test_detects_cvv(self):
        s = pd.Series(["123", "456", "789"])
        assert self.detector.detect_column_type(s) == "cvv"

    def test_detects_expiration_date(self):
        s = pd.Series(["01/25", "12/26", "06/27"])
        assert self.detector.detect_column_type(s) == "expiration_date"

    def test_unknown_type_text(self):
        s = pd.Series(["hello", "world", "test"])
        assert self.detector.detect_column_type(s) == "unknown"

    def test_unknown_type_numeric(self):
        # 6-digit IDs: too long for CVV (3-4 digits) and no other PII pattern matches
        s = pd.Series([100000, 200000, 300000])
        assert self.detector.detect_column_type(s) == "unknown"

    def test_handles_nulls_gracefully(self):
        s = pd.Series([None, "user@example.com", "admin@test.org", None])
        result = self.detector.detect_column_type(s)
        assert result == "email"

    def test_empty_series_returns_unknown(self):
        s = pd.Series([], dtype=str)
        result = self.detector.detect_column_type(s)
        assert result == "unknown"


class TestPiiDetectorDetectAll:
    def setup_method(self):
        self.detector = PiiDetector()

    def test_detects_multiple_pii_columns(self, pii_dataframe):
        detected = self.detector.detect_all(pii_dataframe)
        assert "email" in detected
        assert "ssn" in detected
        assert "zip_code" in detected

    def test_non_pii_columns_not_detected(self, pii_dataframe):
        detected = self.detector.detect_all(pii_dataframe)
        assert "age" not in detected
        assert "score" not in detected

    def test_empty_dataframe_returns_empty_dict(self):
        result = self.detector.detect_all(pd.DataFrame())
        assert result == {}

    def test_no_pii_df_returns_empty_dict(self):
        df = pd.DataFrame({
            "name": ["Alice", "Bob", "Carol"],
            "value": [10, 20, 30],
        })
        result = self.detector.detect_all(df)
        assert result == {}

    def test_returns_dict_with_correct_types(self, pii_dataframe):
        detected = self.detector.detect_all(pii_dataframe)
        assert isinstance(detected, dict)
        for col, pii_type in detected.items():
            assert isinstance(col, str)
            assert isinstance(pii_type, str)
