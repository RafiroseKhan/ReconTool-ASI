# Technical Development Log - AI Recon Tool

This log tracks technical decisions, architecture pivots, and implementation details for Oscar (AI Assistant).

## [2026-02-02] - Foundation & Ingestion

### Core Decisions
- **Architecture:** Implemented a **Layered/Hexagonal** design. Created `BaseHandler` abstract class to ensure the Core Engine remains decoupled from file formats (Excel vs. CSV vs. PDF).
- **OCR Engine:** Switched from Tesseract to **EasyOCR** (Option A) to ensure better portability for the future Windows (PySide6) application.
- **Git Strategy:** Moved to a personal GitHub account (`RafiroseKhan/ReconTool-ASI`) to bypass corporate SSO/403 restrictions.

### Implementation Details
- **BaseHandler:** Added `clean_data` method to automatically handle whitespace and NaN values across all ingestion types.
- **ExcelHandler:** Integrated `openpyxl` as the engine for high-precision `.xlsx` reading.
- **CSVHandler:** Implemented auto-delimiter sniffing using the Python engine.
- **SemanticMapper:** Drafted the similarity logic in `src/core/mapping.py` to handle cross-file column alignment.
- **OCRHandler:** Initialized `easyocr.Reader` with coordinate-tracking (X, Y) for spatial table reconstruction.

### Current Sprint: Stage 3 (Reconciliation Core)
- **Objective:** Developing `reconciler.py` to handle key-based row matching and cell-by-cell delta detection.

## [2026-02-02] - Stage 5 Update (API & Interface)

### Implementation Details
- **FastAPI Backend:** Created `src/api/main.py`. 
- **Features:**
    - Implemented file upload endpoints for Group A and Group B.
    - Integrated `Form` data handling for passing the Unique Key and Column Mapping JSON.
    - Set up a local `uploads/` directory management for temporary file processing.
- **Design Decision:** The API is built to be "Stateless." You send the files and the mapping, and it returns the result. This makes it easy to scale or host on a server later.
- **Next Step:** Initializing the Windows Desktop (PySide6) UI skeleton.
