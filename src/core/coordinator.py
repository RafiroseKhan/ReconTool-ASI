from src.handlers.excel_handler import ExcelHandler
from src.handlers.csv_handler import CSVHandler
from src.handlers.pdf_handler import PDFHandler
from src.core.mapping import SemanticMapper
from src.core.reconciler import ReconEngine
from src.handlers.excel_reporter import ExcelReporter
import os
from typing import Any

class ReconCoordinator:
    """Coordinates the end-to-end flow between UI, Handlers, and Engine."""
    
    def __init__(self):
        self.excel_handler = ExcelHandler()
        self.csv_handler = CSVHandler()
        self.pdf_handler = PDFHandler()
        self.mapper = SemanticMapper()
        self.reporter = ExcelReporter()

    def get_handler(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.xlsx', '.xls']:
            return self.excel_handler
        elif ext == '.csv':
            return self.csv_handler
        elif ext == '.pdf':
            return self.pdf_handler
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def run_full_recon(self, path_a: str, path_b: str, key_col: str, mapping: dict, output_path: str, tolerance: Any = 0.01, accepted_matches: set = None):
        # 1. Load Data
        df_a = self.get_handler(path_a).read(path_a)
        df_b = self.get_handler(path_b).read(path_b)

        # Load Data Mappings
        data_map_dict = {}
        map_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "data_mapping.csv")
        if os.path.exists(map_file):
            try:
                map_df = pd.read_csv(map_file)
                for _, row in map_df.iterrows():
                    col = str(row['Column']).strip()
                    src = str(row['Source Value']).strip()
                    tgt = str(row['Target Value']).strip()
                    if col not in data_map_dict: data_map_dict[col] = {}
                    data_map_dict[col][src] = tgt
            except Exception as e:
                print(f"Warning: Could not load data_mapping.csv: {e}")

        # Pre-process: strip column names
        df_a.columns = [str(c).strip() for c in df_a.columns]
        df_b.columns = [str(c).strip() for c in df_b.columns]

        # 2. Validate Key Column exists in the mapping (or is a direct match)
        # Handle composite keys
        key_parts_a = key_col.split("+")
        for k in key_parts_a:
            if k not in df_a.columns:
                raise ValueError(f"Primary Key part '{k}' not found in Group A")
        
        # Mapped keys in B
        key_in_b = mapping.get(key_col, key_col)
        key_parts_b = key_in_b.split("+")
        for k in key_parts_b:
            if k not in df_b.columns:
                 raise ValueError(f"Primary Key part '{k}' not found in Group B")

        # 3. Reconcile
        engine = ReconEngine(df_a, df_b, data_mapping=data_map_dict)
        recon_data = engine.reconcile(key_col, mapping, tolerance=tolerance, accepted_matches=accepted_matches)

        # 4. Generate Report
        self.reporter.generate_report(recon_data, output_path)
        return output_path
