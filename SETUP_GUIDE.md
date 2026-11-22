# MSME Cash-Flow Underwriting — Setup & Bronze Layer Commands

Complete Windows PowerShell command log from repository initialization through Bronze Parquet table creation.

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
git remote add origin https://github.com
git pull origin main --allow-unrelated-histories --no-edit
git push -u origin main
```

---

## 2. Create Project Folder Structure & Install Python Libraries
```powershell
# Create raw, bronze, and scripts directories
mkdir data\raw\sba, data\raw\bank_ledger, data\raw\fred, data\bronze\sme_hybrid, scripts

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

# Verify all raw files are non-empty
Get-ChildItem -Recurse data\raw -File | Select-Object Name, Length
```

---

## 4. Inspect Raw Schemas & Build Bronze Parquet Tables
```powershell
# Inspect JSON bank statement keys, SBA CSV columns, and macro series
python scripts\inspect_raw.py

# Build standardized Bronze layer tables:
# - data/bronze/sme_hybrid/dim_sme_applications.parquet
# - data/bronze/sme_hybrid/fact_bank_ledger.parquet
# - data/bronze/sme_hybrid/fact_macro_priors.parquet
python scripts\build_hybrid_dataset.py

# Validate row counts, null counts, and sample records
python scripts\verify_bronze.py
```

---

## 5. Save & Push Code Checkpoint to GitHub
```powershell
git status
git add scripts/ SETUP_GUIDE.md
git commit -m "Add Bronze ETL pipeline scripts and setup documentation"
git push
```
