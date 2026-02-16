import os
import pandas as pd

# Paths
xlsx_path = 'data/load_curves.xlsx'
test_csv_path = 'data/test/h2_load.csv'
output_base = 'data'

# Read the Date column from test CSV
test_dates = pd.read_csv(test_csv_path)['Date']

# Read all sheets from the Excel file
sheets = pd.read_excel(xlsx_path, sheet_name=None)

# Region mapping
region_map = {
    'North': 'INDNO',
    'East': 'INDEA',
    'Northeast': 'INDNE',
    'South': 'INDSO',
    'West': 'INDWE'
}

for sheet_name, df in sheets.items():
    # Remove 'Year' column if exists
    if 'Year' in df.columns:
        df = df.drop(columns=['Year'])
    # Assign 'Date' column from test_dates
    df['Date'] = test_dates
    # Ensure output directory exists
    sheet_dir = os.path.join(output_base, sheet_name)
    os.makedirs(sheet_dir, exist_ok=True)
    # Split and save for each region
    for region, new_col in region_map.items():
        if region in df.columns:
            region_df = df[['Date', region]].copy()
            region_df = region_df.rename(columns={region: new_col})
            out_csv = os.path.join(sheet_dir, f'{new_col}.csv')
            region_df.to_csv(out_csv, index=False)