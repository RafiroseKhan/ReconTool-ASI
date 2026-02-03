import pandas as pd
import numpy as np
try:
    import easyocr
except ImportError:
    easyocr = None

class OCRHandler:
    """Handles extraction of table data from images and scanned PDFs using EasyOCR."""
    
    def __init__(self, languages=['en']):
        self.languages = languages
        self.reader = None

    def _initialize_reader(self):
        if self.reader is None and easyocr:
            # gpu=False by default for stability on most machines
            self.reader = easyocr.Reader(self.languages, gpu=False)

    def extract_table(self, image_path: str) -> pd.DataFrame:
        """Extracts text and attempts to structure it as a DataFrame."""
        if not easyocr:
            raise ImportError("EasyOCR is not installed. Please run 'pip install easyocr'")
            
        self._initialize_reader()
        
        # Read the image
        results = self.reader.readtext(image_path)
        
        # results is a list of (bbox, text, confidence)
        # For Phase 1, we start with a basic coordinate-based row/col grouping
        # This will be refined in Stage 3 for complex banking tables
        data = []
        for (bbox, text, prob) in results:
            # bbox is [[x,y], [x,y], [x,y], [x,y]]
            top_left = bbox[0]
            data.append({
                "text": text,
                "x": top_left[0],
                "y": top_left[1],
                "conf": prob
            })
            
    def group_by_rows(self, df: pd.DataFrame, y_threshold: int = 10) -> List[List[str]]:
        """Groups OCR text snippets into logical rows based on Y-coordinates."""
        if df.empty:
            return []
        
        # Sort by Y then X
        df = df.sort_values(by=['y', 'x'])
        
        rows = []
        current_row = []
        last_y = df.iloc[0]['y']
        
        for _, item in df.iterrows():
            if abs(item['y'] - last_y) <= y_threshold:
                current_row.append(item['text'])
            else:
                rows.append(current_row)
                current_row = [item['text']]
                last_y = item['y']
        
        if current_row:
            rows.append(current_row)
        return rows
