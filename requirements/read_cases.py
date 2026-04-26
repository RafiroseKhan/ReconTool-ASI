import pandas as pd
import json

excel_path = r"C:\Users\RuhiKhanna\.openclaw\workspace\ReconTool-ASI\requirements\Result.xlsx"

try:
    # Try 'cases' or 'Cases'
    sheet_name = 'cases'
    xls = pd.ExcelFile(excel_path)
    if 'Cases' in xls.sheet_names:
        sheet_name = 'Cases'
    elif 'cases' in xls.sheet_names:
        sheet_name = 'cases'
    else:
        print(f"Available sheets: {xls.sheet_names}")
        exit()
        
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    print(df.to_json(orient='records', indent=2))
except Exception as e:
    print(f"Error: {e}")
