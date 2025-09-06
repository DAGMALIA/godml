# tests/test_compliance_engine.py

import pandas as pd
from godml.core_service.preprocessor import ComplianceEngine

def test_compliance_engine_with_pci_dss():
    data = {
        "card_number": ["1234567890123456"],
        "cvv": ["123"],
        "expiration_date": ["12/24"],
        "name": ["John Doe"],
        "email": ["john@example.com"],
        "address": ["123 Main St"],
        "zip_code": ["12345"],
        "ssn": ["123-45-6789"],
        "dob": ["1985-10-24"]
    }
    df = pd.DataFrame(data)

    # Aplicar cumplimiento
    masked_df = ComplianceEngine.apply(df, "pci-dss")

    # 👀 Debug: imprimir para visualizar
    print("\n=== DataFrame Original ===")
    print(df)
    print("\n=== DataFrame Masked ===")
    print(masked_df)

    # Verificaciones básicas
    assert masked_df is not None
    assert "cvv" not in masked_df.columns  # debe haber sido eliminado
    assert masked_df["card_number"].iloc[0].endswith("3456")
    assert masked_df["email"].iloc[0].startswith("j") and "@" in masked_df["email"].iloc[0]
    assert masked_df["name"].iloc[0] != "John Doe"
    assert masked_df["address"].iloc[0] != "123 Main St"
    assert masked_df["zip_code"].iloc[0].startswith("12")
    assert masked_df["ssn"].iloc[0] != "123-45-6789"
    assert masked_df["dob"].iloc[0] != "1985-10-24"

    return print(masked_df)

