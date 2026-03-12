import pandas as pd
from typing import Dict, List, Optional, Tuple

class ReconEngine:
    """The core logic for comparing two datasets (Group A and Group B)."""
    
    def __init__(self, df_a: pd.DataFrame, df_b: pd.DataFrame):
        self.df_a = df_a.copy()
        self.df_b = df_b.copy()
        
        # Pre-process: strip column names
        self.df_a.columns = [str(c).strip() for c in self.df_a.columns]
        self.df_b.columns = [str(c).strip() for c in self.df_b.columns]

    def reconcile(self, key_col: str, mapping: Dict[str, str], tolerance: float = 0.01, accepted_matches: set = None) -> Dict:
        """
        Executes reconciliation based on a unique key and column mapping.
        """
        accepted_matches = accepted_matches or set()
        
        # 1. Preparation: ensure key_col exists
        if key_col not in self.df_a.columns:
             raise ValueError(f"Primary Key '{key_col}' not found in Group A")
        
        target_key_col = mapping.get(key_col, key_col)
        if target_key_col not in self.df_b.columns:
             raise ValueError(f"Mapped Primary Key '{target_key_col}' not found in Group B")

        def normalize_key(v):
            if pd.isna(v): return "nan"
            try:
                f_val = float(v)
                if f_val == int(f_val): return str(int(f_val)).strip()
                return str(f_val).strip()
            except:
                return str(v).strip()

        # 2. Index Data for fast lookup
        df_a_work = self.df_a.copy()
        df_a_work['_orig_row_idx'] = range(len(df_a_work))
        df_a_work['_match_key'] = df_a_work[key_col].apply(normalize_key)
        
        df_b_work = self.df_b.copy()
        df_b_work['_match_key'] = df_b_work[target_key_col].apply(normalize_key)
        
        # Drop duplicates in index to prevent the 'getting stuck' or expansion issue
        a_indexed = df_a_work.drop_duplicates(subset=['_match_key']).set_index('_match_key')
        b_indexed = df_b_work.drop_duplicates(subset=['_match_key']).set_index('_match_key')
        
        keys_a = set(a_indexed.index)
        keys_b = set(b_indexed.index)
        
        common_keys = keys_a & keys_b
        only_in_a = keys_a - keys_b
        only_in_b = keys_b - keys_a
        
        # 3. Compare Cell-by-Cell
        mismatches = []
        
        for key in common_keys:
            row_a = a_indexed.loc[key]
            row_b = b_indexed.loc[key]
            orig_idx = int(row_a['_orig_row_idx'])
            
            row_diffs = {}
            for col_a, col_b in mapping.items():
                if col_a in row_a.index and col_b in row_b.index:
                    # Feature: Skip if manually accepted in UI
                    if (orig_idx, col_a) in accepted_matches:
                        continue
                        
                    val_a = row_a[col_a]
                    val_b = row_b[col_b]
                    
                    # Handle nulls
                    if pd.isna(val_a) and pd.isna(val_b):
                        continue
                    
                    # Numerical comparison with tolerance
                    try:
                        num_a, num_b = float(val_a), float(val_b)
                        if abs(num_a - num_b) > tolerance:
                            row_diffs[col_a] = {"val_a": val_a, "val_b": val_b}
                        continue
                    except:
                        pass
                    
                    # String comparison
                    str_a, str_b = str(val_a).strip(), str(val_b).strip()
                    if str_a != str_b:
                        # Check for 'logical match' (date formats etc)
                        if str_a.replace("/", "-") != str_b.replace("/", "-"):
                            row_diffs[col_a] = {"val_a": val_a, "val_b": val_b}
            
            if row_diffs:
                mismatches.append({"key": key, "differences": row_diffs})

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
