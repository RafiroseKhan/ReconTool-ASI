import pandas as pd
import os

def create_database():
    base_dir = "ai-recon-tool/data/test_db"
    os.makedirs(base_dir, exist_ok=True)
    
    # Base Data (A)
    base_data = {
        'Trade_Id': [1, 2, 3],
        'External Ref': ['FO_Murex_1', 'FO_Murex_2', 'FO_Murex_3'],
        'Product Type': ['Cash', 'Equity', 'FX'],
        'Quantity': [100, 200, 300],
        'Price': [105, 50, 1.1],
        'Notional': [10500, 10000, 330],
        'Counter Party': ['CITI', 'GS', 'MS'],
        'Currency': ['EUR', 'USD', 'GBP']
    }
    df_a = pd.DataFrame(base_data)
    df_a.to_excel(f"{base_dir}/source_a.xlsx", index=False)
    
    # Case 1: Same columns, same names (Perfect match)
    df_a.to_csv(f"{base_dir}/case1_source_b.csv", index=False)
    
    # Case 2: Same columns, different names
    df_c2 = df_a.rename(columns={'Trade_Id': 'Tr_Id', 'Quantity': 'Qty', 'Counter Party': 'CP'})
    df_c2.to_excel(f"{base_dir}/case2_source_b.xlsx", index=False)
    
    # Case 3: Different number of columns (Extra columns in B)
    df_c3 = df_a.copy()
    df_c3['Country'] = ['UK', 'USA', 'ZA']
    df_c3.to_excel(f"{base_dir}/case3_source_b.xlsx", index=False)
    
    # Case 4: Diff columns AND Diff names
    df_c4 = df_c2.copy()
    df_c4['Location'] = ['London', 'NY', 'Joburg']
    df_c4.to_csv(f"{base_dir}/case4_source_b.csv", index=False)
    
    # Case 6: Data Type Difference (Price as string in B)
    df_c6 = df_a.copy()
    df_c6['Price'] = df_c6['Price'].astype(str)
    df_c6.to_excel(f"{base_dir}/case6_source_b.xlsx", index=False)
    
    # Case 7: Tolerance (Minor price difference)
    df_c7 = df_a.copy()
    df_c7.loc[0, 'Price'] = 105.001  # Tiny diff
    df_c7.to_excel(f"{base_dir}/case7_source_b.xlsx", index=False)
    
    # Case 8: Mapping (CITI vs CITI Bank)
    df_c8 = df_a.copy()
    df_c8.loc[0, 'Counter Party'] = 'CITI Bank'
    df_c8.to_excel(f"{base_dir}/case8_source_b.xlsx", index=False)

    print(f"Test database created successfully in {base_dir}")

if __name__ == "__main__":
    create_database()
