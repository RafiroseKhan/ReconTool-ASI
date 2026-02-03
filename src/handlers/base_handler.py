from abc import ABC, abstractmethod
import pandas as pd

class BaseHandler(ABC):
    """Abstract base class for all file ingestion handlers."""
    
    @abstractmethod
    def read(self, file_path: str) -> pd.DataFrame:
        """Read the file and return a standardized DataFrame."""
        pass

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generic cleaning: trim whitespace, handle NaN, etc."""
        # Clean headers first
        df.columns = [str(c).strip() for c in df.columns]
        
        # Convert all object columns to string, strip whitespace, and replace NaN with empty string
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        return df.fillna("")
