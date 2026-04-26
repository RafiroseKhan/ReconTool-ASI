import pandas as pd
from typing import Dict, List, Optional, Tuple, Any

class ReconEngine:
    """The core logic for comparing two datasets (Group A and Group B)."""
    
    def __init__(self, df_a: pd.DataFrame, df_b: pd.DataFrame, data_mapping: Dict[str, Dict[str, str]] = None):
        self.df_a = df_a.copy()
        self.df_b = df_b.copy()
        self.data_mapping = data_mapping or {}
        
        # Pre-process: strip column names
        self.df_a.columns = [str(c).strip() for c in self.df_a.columns]
        self.df_b.columns = [str(c).strip() for c in self.df_b.columns]

    def _apply_data_mapping(self, val, col_name):
        """Applies user-defined translation for a specific column."""
        if col_name in self.data_mapping:
            mapping = self.data_mapping[col_name]
            str_val = str(val).strip()
            if str_val in mapping:
                return mapping[str_val]
        return val

    def reconcile(self, key_col: str, mapping: Dict[str, str], tolerance: Any = 0.01, accepted_matches: set = None) -> Dict:
        """
        Executes reconciliation based on a unique key and column mapping.
        """
        accepted_matches = accepted_matches or set()
        
        # Handle tolerance as either a float (global) or a dict (mixed)
        if isinstance(tolerance, dict):
            global_tol = tolerance.get("default", 0.01)
            column_tolerances = tolerance
        else:
            global_tol = float(tolerance)
            column_tolerances = {}

        # 1. Preparation: Handle asymmetric composite keys
        if key_col in mapping:
            # Explicit full-key mapping (e.g. "FirstName+LastName" -> "FullName")
            key_cols_a = key_col.split("+")
            key_cols_b = mapping[key_col].split("+")
        else:
            # Component-level mapping (e.g. "FullName" -> "FirstName+LastName")
            key_cols_a = key_col.split("+")
            key_cols_b = []
            for k in key_cols_a:
                mapped = mapping.get(k, k)
                key_cols_b.extend(mapped.split("+"))

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
        
        def build_key(row, cols):
            # Concatenate normalized parts and remove spaces to ensure asymmetric matching 
            # (e.g. File A "John Smith" matches File B "John" + "Smith")
            return "".join([normalize_key(row[c]).replace(" ", "") for c in cols if c in row.index])

        # Generate match key for A and B
        df_a_work['_match_key'] = df_a_work.apply(lambda row: build_key(row, key_cols_a), axis=1)
        
        df_b_work = self.df_b.copy()
        df_b_work['_match_key'] = df_b_work.apply(lambda row: build_key(row, key_cols_b), axis=1)
        
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
                    
                    # Apply Data Mapping (Translation)
                    val_a_mapped = self._apply_data_mapping(val_a, col_a)
                    val_b_mapped = self._apply_data_mapping(val_b, col_b)

                    # Handle nulls
                    if pd.isna(val_a_mapped) and pd.isna(val_b_mapped):
                        continue
                    
                    # Numerical comparison with tolerance
                    try:
                        num_a, num_b = float(val_a_mapped), float(val_b_mapped)
                        
                        # Fetch column-specific tolerance or fallback to global
                        tol = column_tolerances.get(col_a, global_tol)
                        
                        if abs(num_a - num_b) > tol:
                            row_diffs[col_a] = {"val_a": val_a, "val_b": val_b}
                        continue
                    except:
                        pass
                    
                    # String comparison (Case-Insensitive)
                    str_a, str_b = str(val_a_mapped).strip(), str(val_b_mapped).strip()
                    if str_a.lower() != str_b.lower():
                        # Check for 'logical match' (date formats etc)
                        if str_a.replace("/", "-").lower() != str_b.replace("/", "-").lower():
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
            "detail": mismatches,
            "key_name": key_col
        }
