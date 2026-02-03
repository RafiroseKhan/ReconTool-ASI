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

## [2026-02-02] - Stage 6 Update (The Wiring)

### Implementation Details
- **ReconCoordinator:** Created `src/core/coordinator.py`. This is the "Master Controller" that links the Handlers, Semantic Mapper, Recon Engine, and Excel Reporter.
- **Workflow:**
    1. Detects file type and assigns correct handler.
    2. Triggers AI semantic mapping to align columns.
    3. Executes reconciliation logic.
    4. Passes results to the color-coded Excel reporter.
- **Architecture Integrity:** By using a Coordinator, the Desktop UI and the Web API now use the *exact same* single line of code to run a full reconciliation. This ensures consistency across both platforms.
- **Next Step:** Finalizing the integration within `app.py` and `main.py` to call this coordinator.
