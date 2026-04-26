import pdfplumber
import pandas as pd
import os
import tempfile
import fitz  # PyMuPDF
from src.handlers.base_handler import BaseHandler
from src.handlers.ocr_handler import OCRHandler

class PDFHandler(BaseHandler):
    """Handles extraction of tabular data from PDF files."""
    
    def read(self, file_path: str) -> pd.DataFrame:
        """
        Reads a PDF file and attempts to extract the primary table.
        Concatenates tables across multiple pages if found.
        """
        all_data = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Extract tables from each page
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            # Convert table list of lists to DataFrame
                            df = pd.DataFrame(table)
                            all_data.append(df)
            
            if not all_data:
                # Fallback to OCR if no native tables were found
                print("No native text tables found, falling back to OCR...")
                ocr_handler = OCRHandler()
                
                # Use PyMuPDF (fitz) instead of pdf2image to avoid Poppler dependency on Windows
                doc = fitz.open(file_path)
                for page in doc:
                    pix = page.get_pixmap()
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img:
                        temp_file_name = temp_img.name
                    # Save after closing the file handle to avoid Windows permission errors
                    pix.save(temp_file_name)
                    df = ocr_handler.extract_table(temp_file_name)
                    if not df.empty:
                        all_data.append(df)
                    os.remove(temp_file_name)
                doc.close()
                        
            if not all_data:
                return pd.DataFrame()
                
            final_df = pd.concat(all_data, ignore_index=True)
            
            # Remove rows that are entirely empty
            final_df = final_df.dropna(how='all').reset_index(drop=True)
            
            # Use the first row as header if it looks like one (standard PDF table behavior)
            if not final_df.empty:
                final_df.columns = final_df.iloc[0]
                final_df = final_df[1:].reset_index(drop=True)
                
                # Filter out any remaining empty column headers
                final_df.columns = [str(c).strip() if c and str(c).strip() != "" else f"Col_{i}" for i, c in enumerate(final_df.columns)]
                
            return final_df
            
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return pd.DataFrame()

    def write(self, df: pd.DataFrame, file_path: str):
        """Standard PDF writing isn't typical for this tool's internal handlers (outputs are Excel)."""
        raise NotImplementedError("Writing to PDF is not supported by this handler.")
