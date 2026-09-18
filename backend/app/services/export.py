"""
Export synthetic dataset as CSV or Excel.
"""
import io
import os
from typing import List, Optional

import pandas as pd


def load_synthetic(output_path: str) -> pd.DataFrame:
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Synthetic dataset not found: {output_path}")
    return pd.read_csv(output_path)


def export_csv(df: pd.DataFrame, columns: Optional[List[str]] = None) -> bytes:
    if columns:
        df = df[[c for c in columns if c in df.columns]]
    return df.to_csv(index=False).encode("utf-8")


def export_xlsx(df: pd.DataFrame, columns: Optional[List[str]] = None) -> bytes:
    if columns:
        df = df[[c for c in columns if c in df.columns]]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="SyntheticData")
        # Auto-fit column widths (approximate)
        ws = writer.sheets["SyntheticData"]
        for col_cells in ws.columns:
            max_len = max(
                (len(str(cell.value)) if cell.value is not None else 0)
                for cell in col_cells
            )
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 50)
    return buf.getvalue()


def build_validation_report_xlsx(
    validation_data: dict,
    privacy_data: dict,
) -> bytes:
    """Build a multi-sheet Excel validation report."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Overview sheet
        overview_rows = []
        scores = validation_data.get("overall_scores", {})
        for k, v in scores.items():
            overview_rows.append({"Metric": k, "Score": v})
        pd.DataFrame(overview_rows).to_excel(writer, index=False, sheet_name="Summary")

        # Numerical stats
        num_stats = validation_data.get("numerical_stats", [])
        if num_stats:
            pd.DataFrame(num_stats).to_excel(writer, index=False, sheet_name="Numerical Stats")

        # Categorical stats
        cat_stats = validation_data.get("categorical_stats", [])
        if cat_stats:
            rows = []
            for s in cat_stats:
                rows.append({
                    "column": s["column"],
                    "tvd": s["tvd"],
                    "similarity_score": s["similarity_score"],
                    "chi2_statistic": s.get("chi2_statistic"),
                    "chi2_pvalue": s.get("chi2_pvalue"),
                })
            pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="Categorical Stats")

        # Correlation stats
        corr_stats = validation_data.get("correlation_stats", [])
        if corr_stats:
            pd.DataFrame(corr_stats).to_excel(writer, index=False, sheet_name="Correlations")

        # Privacy
        priv_rows = [
            {"Check": "Exact Duplicates", "Value": privacy_data.get("exact_duplicates", 0)},
            {"Check": "Near Duplicates (estimated)", "Value": privacy_data.get("near_duplicates", 0)},
            {"Check": "Risk Level", "Value": privacy_data.get("risk_level", "Unknown")},
            {"Check": "Disclaimer", "Value": privacy_data.get("details", {}).get("disclaimer", "")},
        ]
        pd.DataFrame(priv_rows).to_excel(writer, index=False, sheet_name="Privacy Checks")

    return buf.getvalue()
