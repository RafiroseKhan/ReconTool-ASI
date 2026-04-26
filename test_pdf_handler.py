import sys
import os
from src.handlers.pdf_handler import PDFHandler

handler = PDFHandler()
df1 = handler.read("sample_native.pdf")
print("Native:")
print(df1)
df2 = handler.read("sample_scanned.pdf")
print("Scanned:")
print(df2)
