from src.core.coordinator import ReconCoordinator
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import shutil
import os
import json

app = FastAPI(title="AI Recon Tool API")
coordinator = ReconCoordinator()

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/reconcile")
async def reconcile_files(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    key_column: str = Form(...),
    mapping_json: str = Form(...)
):
    path_a = os.path.join(UPLOAD_DIR, file_a.filename)
    path_b = os.path.join(UPLOAD_DIR, file_b.filename)
    output_path = os.path.join(OUTPUT_DIR, "reconciliation_report.xlsx")
    
    try:
        with open(path_a, "wb") as buffer:
            shutil.copyfileobj(file_a.file, buffer)
        with open(path_b, "wb") as buffer:
            shutil.copyfileobj(file_b.file, buffer)

        # In a real API, we'd use the provided mapping_json
        # For now, we use the coordinator's full flow
        coordinator.run_full_recon(path_a, path_b, key_column, output_path)
        
        return FileResponse(output_path, filename="recon_report.xlsx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
