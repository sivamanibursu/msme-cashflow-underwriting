import os
import json
import glob
import polars as pl

# 1. Inspect Bank Ledger JSON structure
json_files = sorted(glob.glob("data/raw/bank_ledger/**/*.json", recursive=True))
print(f"Total JSON bank statements found: {len(json_files)}")

if json_files:
    with open(json_files[0], "r", encoding="utf-8") as f:
        sample_bank = json.load(f)
    print("Sample JSON top-level keys:", list(sample_bank.keys()) if isinstance(sample_bank, dict) else type(sample_bank))
    print("Sample JSON preview:", str(sample_bank)[:500])

# 2. Inspect ALL SBA Loan CSVs
sba_files = sorted(glob.glob("data/raw/sba/*.csv"))
print(f"\nTotal SBA CSV files found: {len(sba_files)}")
for fpath in sba_files:
    sba_df = pl.read_csv(
        fpath,
        n_rows=5,
        ignore_errors=True,
        truncate_ragged_lines=True,
    )
    print(f"\nFile: {os.path.basename(fpath)} | Columns ({len(sba_df.columns)}): {sba_df.columns[:8]}...")
    col_map = {c.lower().replace("_", "").replace(" ", ""): c for c in sba_df.columns}
    target_cols = [col_map[k] for k in ["approvaldate", "grossapproval", "naicscode", "loanstatus"] if k in col_map]
    print(sba_df.select(target_cols).head(3))

# 3. Inspect ALL Macro CSVs
for name in ["DRBLACBS", "FEDFUNDS", "DGS10", "TBILL3M"]:
    df = pl.read_csv(f"data/raw/fred/{name}.csv", ignore_errors=True, truncate_ragged_lines=True)
    print(f"\n{name} shape: {df.shape}, columns: {df.columns}")
    print(df.tail(3))
