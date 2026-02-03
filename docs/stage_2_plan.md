# Stage 2: Ingestion & OCR Plan

## Goal
Build a robust ingestion layer that can handle multiple file formats and convert images/scanned PDFs into structured data.

## Components
1. `src/handlers/base_handler.py`: Abstract base class for all file handlers.
2. `src/handlers/excel_handler.py`: Handles `.xlsx` and `.xls` using `pandas` and `openpyxl`.
3. `src/handlers/csv_handler.py`: Handles `.csv` with auto-delimiter detection.
4. `src/handlers/pdf_handler.py`: 
    - Structured PDF: `pdfplumber` extraction.
    - Scanned PDF: OCR integration using `pytesseract`.
5. `src/handlers/ocr_engine.py`: Wrapper for OCR processing.

## Current Progress
- [x] Defined logic for Stage 2.
- [ ] Implement `base_handler.py`.
- [ ] Implement `excel_handler.py`.
