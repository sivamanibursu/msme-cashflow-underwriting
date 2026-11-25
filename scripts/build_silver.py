import os
import boto3
import polars as pl

BRONZE_DIR = "data/bronze/sme_hybrid"
SILVER_DIR = "data/silver/sme_hybrid"
S3_SILVER_BUCKET = "msme-cashflow-underwriting-silver-5bd6f33d"

os.makedirs(SILVER_DIR, exist_ok=True)
s3 = boto3.client("s3")

def save_and_upload(df: pl.DataFrame, filename: str):
    local_path = f"{SILVER_DIR}/{filename}"
    df.write_parquet(local_path)
    s3.upload_file(local_path, S3_SILVER_BUCKET, filename)
    print(f"Saved locally & uploaded to s3://{S3_SILVER_BUCKET}/{filename}")

print("1. Loading Bronze tables...")
dim_sme = pl.read_parquet(f"{BRONZE_DIR}/dim_sme_applications.parquet")
fact_ledger = pl.read_parquet(f"{BRONZE_DIR}/fact_bank_ledger.parquet")
fact_invoices = pl.read_parquet(f"{BRONZE_DIR}/fact_b2b_invoices.parquet")
fact_macro = pl.read_parquet(f"{BRONZE_DIR}/fact_macro_priors.parquet")

print(f"Initial SME count: {dim_sme.height}")

# 2. Clean Macro Priors & Attach Point-in-Time Macro Rates to Every SME
macro_clean = (
    fact_macro
    .with_columns(pl.col("macro_date").str.to_date("%Y-%m-%d", strict=False))
    .drop_nulls("macro_date")
    .unique(subset=["macro_date"], keep="last")
    .sort("macro_date")
)

silver_sme = (
    dim_sme
    .unique(subset=["sme_id"], keep="first")
    .sort("application_date")
    .join_asof(
        macro_clean,
        left_on="application_date",
        right_on="macro_date",
        strategy="backward",
    )
    .with_columns(
        (pl.col("treasury_10y_rate") - pl.col("tbill_3m_rate")).alias("yield_curve_spread")
    )
)
print(f"Silver SME count (after as-of macro join): {silver_sme.height}")

# 3. Clean & Parse Bank Ledger Dates
silver_ledger = (
    fact_ledger
    .with_columns(
        pl.coalesce([
            pl.col("txn_date_raw").str.strip_chars().str.to_date("%Y-%m-%d", strict=False),
            pl.col("txn_date_raw").str.strip_chars().str.to_date("%d/%m/%Y", strict=False),
            pl.col("txn_date_raw").str.strip_chars().str.to_date("%d-%m-%Y", strict=False),
            pl.col("txn_date_raw").str.strip_chars().str.to_date("%m/%d/%Y", strict=False),
        ]).alias("txn_date"),
        pl.col("amount").fill_null(0.0).abs(),
    )
    .drop_nulls(["txn_date", "bank_account_id"])
    .unique(subset=["txn_id"], keep="first")
    .drop("txn_date_raw")
)
print(f"Silver Bank Ledger count: {fact_ledger.height} -> {silver_ledger.height}")

# 4. Deduplicate & Validate B2B Invoices
silver_invoices = (
    fact_invoices
    .unique(subset=["invoice_id", "sme_id"], keep="first")
    .filter(pl.col("declared_sales_usd") > 0)
)
print(f"Silver B2B Invoices count: {fact_invoices.height} -> {silver_invoices.height}")

# 5. Save Locally & Upload Directly to S3 Silver Bucket
save_and_upload(silver_sme, "silver_sme_applications.parquet")
save_and_upload(silver_ledger, "silver_bank_ledger.parquet")
save_and_upload(silver_invoices, "silver_b2b_invoices.parquet")
save_and_upload(macro_clean, "silver_macro_priors.parquet")

print("\nSilver layer build & S3 upload complete!")
