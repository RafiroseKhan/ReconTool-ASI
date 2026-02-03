import pandas as pd
from .base_handler import BaseHandler

class ExcelHandler(BaseHandler):
    """Handler for Excel files (.xlsx, .xls)."""
    
    def read(self, file_path: str, sheet_name: str = 0) -> pd.DataFrame:
        """Reads an Excel file and returns a cleaned DataFrame."""
        try:
            # Using openpyxl as the default engine for .xlsx
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            return self.clean_data(df)
        except Exception as e:
            raise Exception(f"Error reading Excel file {file_path}: {e}")
