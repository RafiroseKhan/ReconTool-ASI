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
        
        # Strip whitespace from string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
            
        # Optional: Drop completely empty rows or columns if needed
        # df = df.dropna(how='all').dropna(axis=1, how='all')
        
        return df
