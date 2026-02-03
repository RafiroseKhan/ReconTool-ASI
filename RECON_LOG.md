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

## [2026-02-02] - Stage 5 Update (Desktop UI)

### Implementation Details
- **Windows Desktop App:** Created `src/desktop/app.py` using **PySide6 (Qt)**.
- **UI Features:**
    - Dual file selection interface for Group A and Group B.
    - Integrated a `QTableWidget` to display AI-suggested column mappings.
    - Styled "Run Reconciliation" button for professional look and feel.
    - Signal-slot architecture ready to be connected to the `ReconEngine`.
- **Logic:** The UI is designed to be a standalone client that can either run the engine locally or call the FastAPI backend, fulfilling the cross-platform requirement.
- **Next Step:** The "Wiring" - connecting the Handlers, Engine, and UI for a complete end-to-end test.
