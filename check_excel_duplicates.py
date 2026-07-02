
import pandas as pd
from collections import Counter

FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/GDR_Products_All_2026-04-20.xlsx'
df = pd.read_excel(FILE_PATH, engine='openpyxl')

print(f"Total rows in Excel: {len(df)}")

# Check duplicate names in Excel
names = df['Product Name'].astype(str).str.strip().str.lower()
name_counts = Counter(names)
dupe_names = {n: c for n, c in name_counts.items() if c > 1}
print(f"Duplicate names in Excel: {len(dupe_names)}")

# Check duplicate codes in Excel
codes = df['Internal Reference'].astype(str).str.strip().str.lower().replace('nan', None).dropna()
code_counts = Counter(codes)
dupe_codes = {c: count for c, count in code_counts.items() if count > 1}
print(f"Duplicate internal references in Excel: {len(dupe_codes)}")

if dupe_names:
    print("\nSample duplicate names in Excel:")
    for n, c in list(dupe_names.items())[:5]:
        print(f"  '{n}': {c} times")

if dupe_codes:
    print("\nSample duplicate codes in Excel:")
    for n, c in list(dupe_codes.items())[:5]:
        print(f"  '{n}': {c} times")
