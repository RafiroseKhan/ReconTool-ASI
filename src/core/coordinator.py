from src.handlers.excel_handler import ExcelHandler
from src.handlers.csv_handler import CSVHandler
from src.core.mapping import SemanticMapper
from src.core.reconciler import ReconEngine
from src.handlers.excel_reporter import ExcelReporter
import os

class ReconCoordinator:
    """Coordinates the end-to-end flow between UI, Handlers, and Engine."""
    
    def __init__(self):
        self.excel_handler = ExcelHandler()
        self.csv_handler = CSVHandler()
        self.mapper = SemanticMapper()
        self.reporter = ExcelReporter()

    def get_handler(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.xlsx', '.xls']:
            return self.excel_handler
        elif ext == '.csv':
            return self.csv_handler
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def run_full_recon(self, path_a: str, path_b: str, key_col: str, output_path: str):
        # 1. Load Data
        df_a = self.get_handler(path_a).read(path_a)
        df_b = self.get_handler(path_b).read(path_b)

        # 2. Get Semantic Mapping (Auto-suggest)
        mapping = self.mapper.suggest_mapping(df_a.columns.tolist(), df_b.columns.tolist())
        
        # 3. Validate Key Column exists in the mapping (or is a direct match)
        # If the key_col detected in A doesn't have a direct equivalent in B's columns
        # we need to find what B calls that key.
        key_in_b = mapping.get(key_col, key_col)
        
        if key_col not in df_a.columns:
            raise ValueError(f"Primary Key '{key_col}' not found in Group A")
        if key_in_b not in df_b.columns:
             raise ValueError(f"Primary Key '{key_col}' (mapped to '{key_in_b}') not found in Group B")

        # 4. Reconcile
        engine = ReconEngine(df_a, df_b)
        recon_data = engine.reconcile(key_col, mapping)

        # 5. Generate Report
        self.reporter.generate_report(recon_data, output_path)
        return output_path
