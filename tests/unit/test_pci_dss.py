import pytest
import pandas as pd
from godml.compliance_service.pci_dss import PciDssCompliance


class TestPciDssComplianceDropPolicy:
    def test_drops_pii_columns_by_content(self, pii_dataframe):
        compliance = PciDssCompliance(policy="drop_sensitive")
        result = compliance.apply(pii_dataframe)
        assert "age" in result.columns
        assert "score" in result.columns
        # At least some PII columns were dropped
        original_cols = set(pii_dataframe.columns)
        result_cols = set(result.columns)
        assert len(result_cols) < len(original_cols)

    def test_non_pii_df_unchanged_under_drop(self):
        compliance = PciDssCompliance(policy="drop_sensitive")
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        result = compliance.apply(df)
        assert list(result.columns) == ["x", "y"]

    def test_rows_count_preserved_under_drop(self, pii_dataframe):
        compliance = PciDssCompliance(policy="drop_sensitive")
        result = compliance.apply(pii_dataframe)
        assert len(result) == len(pii_dataframe)


class TestPciDssComplianceMaskPolicy:
    def test_masks_email_column(self, pii_dataframe):
        compliance = PciDssCompliance(policy="mask_sensitive")
        original_emails = pii_dataframe["email"].tolist()
        result = compliance.apply(pii_dataframe)
        for orig, masked in zip(original_emails, result["email"].tolist()):
            assert orig != masked

    def test_preserves_non_pii_columns(self, pii_dataframe):
        compliance = PciDssCompliance(policy="mask_sensitive")
        result = compliance.apply(pii_dataframe)
        assert result["age"].tolist() == pii_dataframe["age"].tolist()
        assert result["score"].tolist() == pii_dataframe["score"].tolist()

    def test_columns_still_present(self, pii_dataframe):
        compliance = PciDssCompliance(policy="mask_sensitive")
        result = compliance.apply(pii_dataframe)
        assert set(result.columns) == set(pii_dataframe.columns)

    def test_masked_values_have_asterisks(self, pii_dataframe):
        compliance = PciDssCompliance(policy="mask_sensitive")
        result = compliance.apply(pii_dataframe)
        masked_email = result["email"].iloc[0]
        assert "*" in masked_email


class TestPciDssComplianceHashPolicy:
    def test_hashes_pii_columns(self, pii_dataframe):
        compliance = PciDssCompliance(policy="hash_sensitive", hash_len=12)
        result = compliance.apply(pii_dataframe)
        for val in result["email"].tolist():
            assert isinstance(val, str)
            assert len(val) == 12

    def test_hash_len_respected(self, pii_dataframe):
        compliance = PciDssCompliance(policy="hash_sensitive", hash_len=8)
        result = compliance.apply(pii_dataframe)
        for val in result["ssn"].tolist():
            assert len(val) == 8

    def test_hashes_are_deterministic(self, pii_dataframe):
        c1 = PciDssCompliance(policy="hash_sensitive")
        c2 = PciDssCompliance(policy="hash_sensitive")
        r1 = c1.apply(pii_dataframe.copy())
        r2 = c2.apply(pii_dataframe.copy())
        assert r1["email"].tolist() == r2["email"].tolist()


class TestPciDssComplianceEdgeCases:
    def test_empty_dataframe_returned_as_is(self):
        compliance = PciDssCompliance()
        result = compliance.apply(pd.DataFrame())
        assert result.empty

    def test_none_returned_as_none(self):
        compliance = PciDssCompliance()
        result = compliance.apply(None)
        assert result is None

    def test_original_dataframe_not_mutated(self, pii_dataframe):
        original_cols = list(pii_dataframe.columns)
        original_email = pii_dataframe["email"].iloc[0]
        compliance = PciDssCompliance(policy="drop_sensitive")
        compliance.apply(pii_dataframe)
        assert list(pii_dataframe.columns) == original_cols
        assert pii_dataframe["email"].iloc[0] == original_email

    def test_describe_returns_non_empty_string(self):
        compliance = PciDssCompliance()
        assert isinstance(compliance.describe(), str)
        assert len(compliance.describe()) > 0

    def test_pii_detected_by_column_name_heuristic(self):
        compliance = PciDssCompliance(policy="mask_sensitive")
        df = pd.DataFrame({
            "customer_name": ["Alice Smith", "Bob Jones"],
            "revenue": [1000, 2000],
        })
        result = compliance.apply(df)
        assert "revenue" in result.columns
        assert result["customer_name"].iloc[0] != "Alice Smith"
