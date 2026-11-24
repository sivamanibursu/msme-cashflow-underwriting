import polars as pl

tables = [
    "dim_sme_applications.parquet",
    "fact_bank_ledger.parquet",
    "fact_macro_priors.parquet",
    "fact_b2b_invoices.parquet",
]

for table in tables:
    path = f"data/bronze/sme_hybrid/{table}"
    df = pl.read_parquet(path)
    print("=" * 55)
    print(f"TABLE: {table} | ROWS: {df.height:,} | COLS: {df.width}")
    print("Null counts per column:")
    print(df.null_count())
    print("Sample 3 rows:")
    print(df.head(3))
