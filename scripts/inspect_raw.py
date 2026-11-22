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

# 2. Inspect SBA Loan CSV columns
sba_df = pl.read_csv(
    "data/raw/sba/FOIA_7a_FY2020_Present_asof_260930.csv",
    n_rows=5,
    ignore_errors=True,
    truncate_ragged_lines=True,
)
print("\nSBA Columns:", sba_df.columns)
print(sba_df.select(["ApprovalDate", "GrossApproval", "NaicsCode", "LoanStatus"]).head(3))

# 3. Inspect Macro CSVs
for name in ["DRBLACBS", "FEDFUNDS"]:
    df = pl.read_csv(f"data/raw/fred/{name}.csv", ignore_errors=True, truncate_ragged_lines=True)
    print(f"\n{name} shape: {df.shape}, columns: {df.columns}")
    print(df.tail(3))
