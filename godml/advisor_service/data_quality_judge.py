import pandas as pd

class DataQualityJudge:
    def check(self, df: pd.DataFrame):
        report = {}
        report["nulls"] = df.isnull().sum().to_dict()
        report["duplicates"] = df.duplicated().sum()
        report["cardinality"] = {col: df[col].nunique() for col in df.columns}
        return report
