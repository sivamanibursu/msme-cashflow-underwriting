# MSME Cash-Flow Underwriting — Setup & Bronze Layer Commands

Complete Windows PowerShell command log from repository initialization through 4-Dataset Hybrid Bronze Parquet table creation.

---

## 1. Initialize Git & Connect to GitHub
```powershell
# Initialize local Git repo and configure user identity
git init
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"

# Stage and commit .gitignore first (excludes heavy data/ files from GitHub)
git add .gitignore
git commit -m "Add gitignore"
git branch -M main

# Link local repo to GitHub and sync initial README.md
git remote add origin https://github.com<your-username>/msme-cashflow-underwriting.git
git pull origin main --allow-unrelated-histories --no-edit
git push -u origin main
```

---

## 2. Create Project Folder Structure & Install Python Libraries
```powershell
# Create raw (4 sources), bronze, and scripts directories
mkdir data\raw\sba, data\raw\bank_ledger, data\raw\fred, data\raw\dataco, data\bronze\sme_hybrid, scripts

# Install core data engineering libraries
pip install polars pyarrow requests huggingface_hub
```

---

## 3. Acquire Free Open-Licensed Raw Datasets
```powershell
# 1. Download synthetic commercial bank statements (Apache 2.0) via Hugging Face
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='AgamiAI/Indian-Bank-Statements', repo_type='dataset', local_dir='data/raw/bank_ledger')"

# 2. Download macroeconomic interest rate & commercial credit series (Public Domain)
python scripts\download_fred.py

# 3. U.S. SBA 7(a) FOIA Loan Dataset (Public Domain):
# Downloaded manually from data.sba.gov and placed at:
# data\raw\sba\FOIA_7a_FY2020_Present_asof_260930.csv

# 4. DataCo Smart Supply Chain B2B Invoices (CC BY 4.0):
# Downloaded manually from Mendeley Data (DOI: 10.17632/8gx2fvg2k6.5) and placed at:
# data\raw\dataco\DataCoSupplyChainDataset.csv

# Verify all raw files across all 4 sources are non-empty
Get-ChildItem -Recurse data\raw -File | Select-Object Name, Length
```

---

## 4. Inspect Raw Schemas & Build 4-Dataset Bronze Parquet Tables
```powershell
# Inspect JSON bank statement keys, SBA CSV columns, DataCo schema, and macro series
python scripts\inspect_raw.py

# Build standardized 4-dataset Bronze layer tables (with pre-application temporal leakage filter):
# - data/bronze/sme_hybrid/dim_sme_applications.parquet
# - data/bronze/sme_hybrid/fact_bank_ledger.parquet
# - data/bronze/sme_hybrid/fact_b2b_invoices.parquet
# - data/bronze/sme_hybrid/fact_macro_priors.parquet
python scripts\build_hybrid_dataset.py

# Validate row counts, null counts, and sample records
python scripts\verify_bronze.py
```

---

## 5. Save & Push Phase 0 Bronze Checkpoint to GitHub
```powershell
git status
git add .gitignore README.md SETUP_GUIDE.md scripts/
git commit -m "feat(bronze): complete 4-dataset hybrid ingestion with DataCo B2B invoices"
git push
```
