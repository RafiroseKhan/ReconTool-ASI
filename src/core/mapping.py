import pandas as pd
from typing import List, Dict

class SemanticMapper:
    """Matches columns from Group A to Group B using semantic similarity."""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    def suggest_primary_key(self, df: pd.DataFrame) -> str:
        """Analyzes the DataFrame to suggest the most likely primary key column."""
        # Clean headers again just in case
        df.columns = [str(c).strip() for c in df.columns]
        
        # 1. Look for unique values (100% uniqueness)
        for col in df.columns:
            # Drop NaN for uniqueness check
            non_na_values = df[col].dropna()
            if len(non_na_values) > 0 and non_na_values.nunique() == len(non_na_values):
                # Prioritize columns that look like IDs
                norm_col = "".join(filter(str.isalnum, str(col).lower()))
                if any(k in norm_col for k in ['id', 'ref', 'no', 'key', 'code']):
                    return col
        
        # 2. Fallback to the first column with 100% uniqueness
        for col in df.columns:
            non_na_values = df[col].dropna()
            if len(non_na_values) > 0 and non_na_values.nunique() == len(non_na_values):
                return col
                
        # 3. Ultimate fallback: The first column
        return df.columns[0]

    def suggest_mapping(self, cols_a: List[str], cols_b: List[str]) -> Dict[str, str]:
        """Suggests which column from A maps to which in B."""
        mapping = {}
        for a in cols_a:
            # Normalize: lower case, remove non-alphanumeric, strip spaces
            norm_a = "".join(filter(str.isalnum, str(a).lower()))
            for b in cols_b:
                norm_b = "".join(filter(str.isalnum, str(b).lower()))
                if norm_a == norm_b and norm_a != "":
                    mapping[a] = b
                    break
        
        # LOGGING for debugging
        print(f"DEBUG: Suggested Mapping -> {mapping}")
        return mapping

    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Removes potential hidden spaces/newlines from column headers."""
        df.columns = [str(c).strip() for c in df.columns]
        return df
