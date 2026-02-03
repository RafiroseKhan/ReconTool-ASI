import pandas as pd
from typing import Dict, List, Optional, Tuple

class ReconEngine:
    """The core logic for comparing two datasets (Group A and Group B)."""
    
    def __init__(self, df_a: pd.DataFrame, df_b: pd.DataFrame):
        self.df_a = df_a
        self.df_b = df_b
        self.results = {}

    def reconcile(self, key_col: str, mapping: Dict[str, str]) -> Dict:
        """
        Executes reconciliation based on a unique key and column mapping.
        
        Args:
            key_col: The column name in Group A used as the unique identifier.
            mapping: A dict where {col_in_A: col_in_B}
        """
        # 1. Align column names in B to match A for easier comparison
        inv_mapping = {v: k for k, v in mapping.items()}
        df_b_aligned = self.df_b.rename(columns=inv_mapping)
        
        # 2. Identify Row Deltas (Missing in A or B)
        keys_a = set(self.df_a[key_col])
        keys_b = set(df_b_aligned[key_col])
        
        only_in_a = keys_a - keys_b
        only_in_b = keys_b - keys_a
        common_keys = keys_a & keys_b
        
        # 3. Cell-by-Cell Comparison for common keys
        mismatches = []
        
        # Set index to key_col for fast lookup
        a_indexed = self.df_a.set_index(key_col)
        b_indexed = df_b_aligned.set_index(key_col)
        
        for key in common_keys:
            row_a = a_indexed.loc[key]
            row_b = b_indexed.loc[key]
            
            row_diffs = {}
            for col_a in mapping.keys():
                val_a = row_a[col_a]
                val_b = row_b[col_a] # Col B was renamed to match Col A
                
                if val_a != val_b:
                    row_diffs[col_a] = {"val_a": val_a, "val_b": val_b}
            
            if row_diffs:
                mismatches.append({
                    "key": key,
                    "differences": row_diffs
                })
                
        return {
            "summary": {
                "total_a": len(self.df_a),
                "total_b": len(self.df_b),
                "matched": len(common_keys),
                "mismatches": len(mismatches),
                "only_in_a": list(only_in_a),
                "only_in_b": list(only_in_b)
            },
            "detail": mismatches
        }
