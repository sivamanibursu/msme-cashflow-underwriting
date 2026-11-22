import glob
import json
import os
import polars as pl

os.makedirs("data/bronze/sme_hybrid", exist_ok=True)

# 1. Process SBA SME Loan Applications (Real Default Outcomes)
print("Loading SBA SME loan data...")
sba_raw = pl.read_csv(
    "data/raw/sba/FOIA_7a_FY2020_Present_asof_260930.csv",
    ignore_errors=True,
    truncate_ragged_lines=True,
)

dim_sme = (
    sba_raw.filter(pl.col("LoanStatus").is_in(["CHGOFF", "PIF"]))
    .with_columns(
        pl.arange(1, pl.len() + 1).alias("sme_num"),
        pl.when(pl.col("LoanStatus") == "CHGOFF").then(1).otherwise(0).alias("default_flag"),
        pl.col("GrossApproval").cast(pl.Float64, strict=False).alias("requested_loan_usd"),
        pl.col("NaicsCode").cast(pl.Utf8, strict=False).fill_null("UNKNOWN").alias("naics_industry"),
        pl.col("ProjectState").cast(pl.Utf8, strict=False).fill_null("NA").alias("region_state"),
        pl.col("ApprovalDate").str.to_date("%m/%d/%Y", strict=False).alias("application_date"),
    )
    .filter(pl.col("application_date").is_not_null() & (pl.col("requested_loan_usd") > 0))
    .with_columns(
        (pl.lit("SME_") + pl.col("sme_num").cast(pl.Utf8).str.zfill(6)).alias("sme_id"),
        (pl.lit("ACC_") + ((pl.col("sme_num") % 400) + 1).cast(pl.Utf8).str.zfill(4)).alias("bank_account_id"),
    )
    .select(
        "sme_id",
        "bank_account_id",
        "application_date",
        "naics_industry",
        "region_state",
        "requested_loan_usd",
        "default_flag",
    )
)

dim_sme.write_parquet("data/bronze/sme_hybrid/dim_sme_applications.parquet")
print(f"Saved dim_sme_applications.parquet: {dim_sme.shape}")

# 2. Process 400 Synthetic Bank Ledger JSON Statements (From train/ only)
print("Parsing 400 bank ledger JSON files from train/...")
json_files = sorted(glob.glob("data/raw/bank_ledger/train/**/*.json", recursive=True))
ledger_rows = []

for idx, filepath in enumerate(json_files, start=1):
    acc_id = f"ACC_{idx:04d}"
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    txns = []
    if isinstance(data, list):
        txns = data
    elif isinstance(data, dict):
        for val in data.values():
            if isinstance(val, list) and len(val) > 0:
                txns = val
                break

    for t_idx, t in enumerate(txns, start=1):
        if not isinstance(t, dict):
            continue
        amt_raw = t.get("amount") or t.get("Amount") or t.get("debit") or t.get("credit") or 0
        try:
            amt = float(str(amt_raw).replace(",", "").strip())
        except ValueError:
            amt = 0.0

        t_type = str(t.get("type") or t.get("Type") or t.get("transaction_type") or "").upper()
        direction = "INFLOW" if ("CR" in t_type or "IN" in t_type or t.get("credit")) else "OUTFLOW"

        bal_raw = t.get("balance") or t.get("Balance") or t.get("closing_balance") or 0
        try:
            bal = float(str(bal_raw).replace(",", "").strip())
        except ValueError:
            bal = 0.0

        ledger_rows.append({
            "txn_id": f"{acc_id}_T{t_idx:05d}",
            "bank_account_id": acc_id,
            "txn_date_raw": str(t.get("date") or t.get("Date") or t.get("txn_date") or ""),
            "direction": direction,
            "payment_rail": str(t.get("mode") or t.get("Mode") or t.get("channel") or "BANK_TRANSFER"),
            "amount": abs(amt),
            "running_balance": bal,
        })

fact_ledger = pl.DataFrame(ledger_rows)
fact_ledger.write_parquet("data/bronze/sme_hybrid/fact_bank_ledger.parquet")
print(f"Saved fact_bank_ledger.parquet: {fact_ledger.shape}")

# 3. Process Macro Priors
print("Processing macro economic series...")
fed = pl.read_csv("data/raw/fred/FEDFUNDS.csv", ignore_errors=True)
drb = pl.read_csv("data/raw/fred/DRBLACBS.csv", ignore_errors=True)

fed_clean = fed.select(
    pl.col(fed.columns.pop(0)).alias("macro_date"),
    pl.col(fed.columns.pop(-1)).cast(pl.Float64, strict=False).alias("fed_funds_rate"),
).drop_nulls()

drb_clean = drb.select(
    pl.col(drb.columns.pop(0)).alias("macro_date"),
    pl.col(drb.columns.pop(-1)).cast(pl.Float64, strict=False).alias("commercial_credit_index"),
).drop_nulls()

fact_macro = fed_clean.join(drb_clean, on="macro_date", how="full", coalesce=True).sort("macro_date")
fact_macro.write_parquet("data/bronze/sme_hybrid/fact_macro_priors.parquet")
print(f"Saved fact_macro_priors.parquet: {fact_macro.shape}")
print("\nBronze layer build complete!")
