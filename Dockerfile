FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV (EasyOCR) and other libraries
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# Adding easyocr, PyMuPDF, fastapi, uvicorn, and python-multipart explicitly 
# to ensure the web dependencies and our new OCR tools are included
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir easyocr PyMuPDF fastapi uvicorn python-multipart

# Copy the rest of the application code
COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]