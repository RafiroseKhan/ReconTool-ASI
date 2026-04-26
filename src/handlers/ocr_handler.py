import pandas as pd
import numpy as np
from typing import List
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
            self.reader = easyocr.Reader(self.languages, gpu=False, verbose=False)

    def extract_table(self, image_path: str) -> pd.DataFrame:
        """Extracts text and attempts to structure it as a DataFrame."""
        if not easyocr:
            raise ImportError("EasyOCR is not installed. Please run 'pip install easyocr'")
            
        self._initialize_reader()
        
        # Read the image
        results = self.reader.readtext(image_path)
        
        # results is a list of (bbox, text, confidence)
        # Disable EasyOCR's internal tqdm progress bar to fix Windows console charmap errors
        import logging
        logging.getLogger("easyocr").setLevel(logging.ERROR)
        
        # Read the image silently without the progress bar
        results = self.reader.readtext(image_path, detail=1)
        
        data = []
        # Ensure the fallback to OCR uses PyMuPDF correctly and disables logging that throws charmap errors
        for (bbox, text, prob) in results:
            # bbox is [[x,y], [x,y], [x,y], [x,y]]
            center_x = (bbox[0][0] + bbox[1][0]) / 2
            center_y = (bbox[0][1] + bbox[2][1]) / 2
            data.append({
                "text": text,
                "x": center_x,
                "y": center_y,
                "conf": prob
            })
            
        if not data:
            return pd.DataFrame()
            
        coord_df = pd.DataFrame(data)
        rows = self.group_by_rows(coord_df)
        
        if not rows:
            return pd.DataFrame()
            
        # Ensure uniform columns
        max_cols = max(len(row) for row in rows)
        padded_rows = [row + [""] * (max_cols - len(row)) for row in rows]
        
        return pd.DataFrame(padded_rows)
            
    def group_by_rows(self, df: pd.DataFrame, y_threshold: int = 15) -> List[List[str]]:
        """Groups OCR text snippets into logical rows based on Y-coordinates and aligns columns by X-coordinates."""
        if df.empty:
            return []
        
        # Sort by Y then X
        df = df.sort_values(by=['y', 'x'])
        
        # 1. Group into raw rows based on Y
        raw_rows = []
        current_row = []
        last_y = df.iloc[0]['y']
        
        for _, item in df.iterrows():
            if abs(item['y'] - last_y) <= y_threshold:
                current_row.append({"text": item['text'], "x": item['x']})
            else:
                raw_rows.append(current_row)
                current_row = [{"text": item['text'], "x": item['x']}]
                last_y = item['y']
        
        if current_row:
            raw_rows.append(current_row)
            
        # 2. Find the row with the most columns to define the grid
        max_cols_row = max(raw_rows, key=len)
        num_cols = len(max_cols_row)
        
        # Extract the X coordinates of this "reference" row
        col_centers = sorted([item['x'] for item in max_cols_row])
        
        # 3. Snap all rows to this grid
        final_rows = []
        for r in raw_rows:
            row_data = [""] * num_cols
            for item in r:
                # Find closest column
                closest_col_idx = min(range(num_cols), key=lambda i: abs(col_centers[i] - item['x']))
                # Append if multiple words land in the same column
                if row_data[closest_col_idx] == "":
                    row_data[closest_col_idx] = item['text']
                else:
                    row_data[closest_col_idx] += " " + item['text']
            final_rows.append(row_data)
            
        return final_rows
