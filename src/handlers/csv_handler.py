import pandas as pd
from .base_handler import BaseHandler

class CSVHandler(BaseHandler):
    """Handler for CSV files."""
    
    def read(self, file_path: str) -> pd.DataFrame:
        """Reads a CSV file with automatic delimiter detection."""
        try:
            # First, read a few lines to inspect the delimiter and headers
            with open(file_path, 'r') as f:
                first_line = f.readline()
                print(f"DEBUG: First line of {file_path}: {repr(first_line)}")
            
            # engine='python' allows for better delimiter sniffing
            df = pd.read_csv(file_path, sep=None, engine='python')
            print(f"DEBUG: Columns found: {df.columns.tolist()}")
            return self.clean_data(df)
        except Exception as e:
            raise Exception(f"Error reading CSV file {file_path}: {e}")
