import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from typing import Dict, List, Any

class ExcelReporter:
    """Generates professional, color-coded Excel reports based on reconciliation results."""
    
    # Colors for highlighting
    MATCH_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")  # Light Green
    MISMATCH_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")  # Light Red
    MISSING_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")   # Light Yellow
    
    def generate_report(self, recon_data: Dict[str, Any], output_path: str):
        """
        Takes the dictionary from ReconEngine and writes a formatted Excel file.
        """
        summary = recon_data.get("summary", {})
        details = recon_data.get("detail", []) # List of {key, differences: {col: {val_a, val_b}}}
        
        # 1. Create Summary Sheet
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # High level summary
            summary_df = pd.DataFrame([
                {"Metric": "Total Rows in Group A", "Value": summary.get("total_a")},
                {"Metric": "Total Rows in Group B", "Value": summary.get("total_b")},
                {"Metric": "Successfully Matched", "Value": summary.get("matched")},
                {"Metric": "Mismatched Rows", "Value": summary.get("mismatches")},
                {"Metric": "Only in Group A", "Value": len(summary.get("only_in_a", []))},
                {"Metric": "Only in Group B", "Value": len(summary.get("only_in_b", []))},
            ])
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            
            # TODO: Add detail sheet with color coding
            # This requires lower-level openpyxl access for cell-by-cell styling
            self._write_detailed_sheet(writer, recon_data)

    def _write_detailed_sheet(self, writer, recon_data):
        """Helper to write and style the detailed reconciliation sheet."""
        # For Phase 1, we focus on generating the core 'Differences' view
        pass
