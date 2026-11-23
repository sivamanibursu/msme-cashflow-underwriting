import glob
import json
import os
import polars as pl

os.makedirs("data/bronze/sme_hybrid", exist_ok=True)

# 1. Discover bank ledger JSON files first so account mapping matches exact count
json_files = sorted(glob.glob("data/raw/bank_ledger/train/**/*.json", recursive=True))
n_accounts = max(len(json_files), 1)

# 2. Process SBA SME Loan Applications (Real Default Outcomes)
print("Loading SBA SME loan data...")
sba_raw = pl.read_csv(
    "data/raw/sba/FOIA_7a_FY2020_Present_asof_260930.csv",
    ignore_errors=True,
    truncate_ragged_lines=True,
)

# Normalize column names safely in case SBA CSV uses different casing/spacing
sba_cols = {c.lower().replace("_", "").replace(" ", ""): c for c in sba_raw.columns}
status_col = sba_cols.get("loanstatus", "LoanStatus")
gross_col = sba_cols.get("grossapproval", "GrossApproval")
naics_col = sba_cols.get("naicscode", "NaicsCode")
state_col = sba_cols.get("projectstate", "ProjectState")
date_col = sba_cols.get("approvaldate", "ApprovalDate")

dim_sme = (
    sba_raw.filter(pl.col(status_col).cast(pl.Utf8).str.strip_chars().str.to_uppercase().is_in(["CHGOFF", "PIF"]))
    .with_columns(
        pl.arange(1, pl.len() + 1).alias("sme_num"),
        pl.when(pl.col(status_col).cast(pl.Utf8).str.strip_chars().str.to_uppercase() == "CHGOFF")
          .then(1)
          .otherwise(0)
          .alias("default_flag"),
        pl.col(gross_col).cast(pl.Utf8).str.replace_all(r"[$,]", "").cast(pl.Float64, strict=False).alias("requested_loan_usd"),
        pl.col(naics_col).cast(pl.Utf8, strict=False).fill_null("UNKNOWN").alias("naics_industry"),
        pl.col(state_col).cast(pl.Utf8, strict=False).fill_null("NA").alias("region_state"),
        pl.coalesce([
            pl.col(date_col).cast(pl.Utf8).str.strip_chars().str.to_date("%Y-%m-%d", strict=False),
            pl.col(date_col).cast(pl.Utf8).str.strip_chars().str.to_date("%m/%d/%Y", strict=False),
            pl.col(date_col).cast(pl.Utf8).str.strip_chars().str.to_date("%d-%b-%Y", strict=False),
        ]).alias("application_date"),
    )
    .filter(pl.col("application_date").is_not_null() & (pl.col("requested_loan_usd") > 0))
    .with_columns(
        (pl.lit("SME_") + pl.col("sme_num").cast(pl.Utf8).str.zfill(6)).alias("sme_id"),
        (pl.lit("ACC_") + ((pl.col("sme_num") % n_accounts) + 1).cast(pl.Utf8).str.zfill(4)).alias("bank_account_id"),
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

# 3. Process Synthetic Bank Ledger JSON Statements (From train/ only)
print(f"Parsing {len(json_files)} bank ledger JSON files from train/...")
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

# 4. Process Macro Priors
print("Processing macro economic series...")
fed = pl.read_csv("data/raw/fred/FEDFUNDS.csv", ignore_errors=True)
drb = pl.read_csv("data/raw/fred/DRBLACBS.csv", ignore_errors=True)

fed_clean = fed.select(
    pl.col(fed.columns[0]).alias("macro_date"),
    pl.col(fed.columns[-1]).cast(pl.Float64, strict=False).alias("fed_funds_rate"),
).drop_nulls()

drb_clean = drb.select(
    pl.col(drb.columns[0]).alias("macro_date"),
    pl.col(drb.columns[-1]).cast(pl.Float64, strict=False).alias("commercial_credit_index"),
).drop_nulls()

fact_macro = fed_clean.join(drb_clean, on="macro_date", how="full", coalesce=True).sort("macro_date")
fact_macro.write_parquet("data/bronze/sme_hybrid/fact_macro_priors.parquet")
print(f"Saved fact_macro_priors.parquet: {fact_macro.shape}")

# 5. Process DataCo Corporate B2B Invoices + Point-in-Time Macro Join
print("Processing DataCo Corporate B2B invoices...")
dataco_raw = pl.read_csv(
    "data/raw/dataco/DataCoSupplyChainDataset.csv",
    encoding="latin1",
    ignore_errors=True,
)

sme_lookup = dim_sme.select("sme_id", "application_date").sort("sme_id")
n_smes = max(len(sme_lookup), 1)

macro_sorted = (
    fact_macro
    .with_columns(pl.col("macro_date").str.to_date("%Y-%m-%d", strict=False))
    .drop_nulls("macro_date")
    .sort("macro_date")
)

fact_b2b_invoices = (
    dataco_raw
    .filter(pl.col("Customer Segment") == "Corporate")
    .with_columns(
        pl.col("Order Id").cast(pl.Utf8).alias("invoice_id"),
        pl.col("order date (DateOrders)")
          .str.strptime(pl.Datetime, "%m/%d/%Y %H:%M", strict=False)
          .cast(pl.Date)
          .alias("invoice_date"),
        pl.col("Sales").cast(pl.Float64, strict=False).alias("declared_sales_usd"),
        pl.col("Order Profit Per Order").cast(pl.Float64, strict=False).alias("net_profit_usd"),
        pl.col("Late_delivery_risk").cast(pl.Int8, strict=False).alias("late_settlement_flag"),
    )
    .drop_nulls(["invoice_id", "invoice_date"])
    .with_row_index("row_nr")
    .with_columns((pl.col("row_nr") % n_smes).alias("sme_idx"))
    .join(sme_lookup.with_row_index("sme_idx"), on="sme_idx", how="inner")
    # Enforce temporal leakage constraint: strictly pre-application invoices
    .filter(pl.col("invoice_date") < pl.col("application_date"))
    .sort("invoice_date")
    .join_asof(
        macro_sorted,
        left_on="invoice_date",
        right_on="macro_date",
        strategy="backward",
    )
    .select(
        "invoice_id",
        "sme_id",
        "invoice_date",
        "declared_sales_usd",
        "net_profit_usd",
        "late_settlement_flag",
        "commercial_credit_index",
        "fed_funds_rate",
    )
)

fact_b2b_invoices.write_parquet("data/bronze/sme_hybrid/fact_b2b_invoices.parquet")
print(f"Saved fact_b2b_invoices.parquet: {fact_b2b_invoices.shape}")
print("\nBronze layer build complete!")
