import pandas as pd
import json
import os

excel_path = r"C:\Users\RuhiKhanna\.openclaw\workspace\ReconTool-ASI\requirements\Result.xlsx"

try:
    xls = pd.ExcelFile(excel_path)
    output = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, nrows=5)
        output[sheet] = df.columns.tolist()
    
    print(json.dumps(output, indent=2))
except Exception as e:
    print(f"Error: {e}")
