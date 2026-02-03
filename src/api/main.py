from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
import shutil
import os
from typing import Dict
import json

# Placeholder imports - these will be finalized as we link the modules
# from src.handlers.excel_handler import ExcelHandler
# from src.core.reconciler import ReconEngine
# from src.handlers.excel_reporter import ExcelReporter

app = FastAPI(title="AI Recon Tool API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"status": "AI Recon Tool API is running", "phase": 1}

@app.post("/reconcile")
async def reconcile_files(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    key_column: str = Form(...),
    mapping_json: str = Form(...)
):
    """
    Endpoint to upload two files and receive a reconciliation report.
    """
    # 1. Save files locally
    path_a = os.path.join(UPLOAD_DIR, file_a.filename)
    path_b = os.path.join(UPLOAD_DIR, file_b.filename)
    
    with open(path_a, "wb") as buffer:
        shutil.copyfileobj(file_a.file, buffer)
    with open(path_b, "wb") as buffer:
        shutil.copyfileobj(file_b.file, buffer)

    # 2. Parse mapping
    mapping = json.loads(mapping_json)

    # 3. TODO: Execute Recon Process
    # result_path = "output/reconciliation_report.xlsx"
    
    return {
        "message": "Files received",
        "file_a": file_a.filename,
        "file_b": file_b.filename,
        "key_used": key_column,
        "status": "Processing logic being integrated"
    }
