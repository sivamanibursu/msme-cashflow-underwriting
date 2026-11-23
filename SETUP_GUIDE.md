# MSME Cash-Flow Underwriting — Setup & Infrastructure Guide

Complete Windows PowerShell command log from repository initialization through 4-Dataset Hybrid Bronze Parquet creation, AWS S3 Medallion infrastructure provisioning (`ap-southeast-2`), and Bronze S3 data upload.

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
# Create raw (4 sources), bronze, scripts, and infrastructure directories
New-Item -ItemType Directory -Force -Path data\raw\sba, data\raw\bank_ledger, data\raw\fred, data\raw\dataco, data\bronze\sme_hybrid, scripts, infra\terraform | Out-Null

# Install core data engineering & AWS SDK libraries
pip install polars pyarrow requests huggingface_hub boto3 awscli
```

---

## 3. Acquire Free Open-Licensed Raw Datasets & Audit Raw Counts
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

# 5. Audit raw file sizes (in bytes and MB)
Get-ChildItem -Recurse data\raw -File | Select-Object Name, Length, @{Name="SizeMB";Expression={[math]::Round($_.Length / 1MB, 2)}}

# 6. Audit raw JSON bank statement file count
python -c "import glob; print('Raw bank ledger JSON files:', len(glob.glob('data/raw/bank_ledger/**/*.json', recursive=True)))"

# 7. Audit exact data row counts across all raw CSV files (handles headers, multiline fields & Latin-1 encoding)
python -c "import polars as pl, glob; [print(f, pl.scan_csv(f, encoding='utf8-lossy', ignore_errors=True).select(pl.len()).collect().item()) for f in glob.glob('data/raw/**/*.csv', recursive=True)]"

```

---

## 4. Inspect Raw Schemas, Build Bronze Tables & Audit Bronze Counts
```powershell
# 1. Inspect JSON bank statement keys, SBA CSV columns, DataCo schema, and macro series
python scripts\inspect_raw.py

# 2. Build standardized 4-dataset Bronze layer tables (with pre-application temporal leakage filter):
# - data/bronze/sme_hybrid/dim_sme_applications.parquet
# - data/bronze/sme_hybrid/fact_bank_ledger.parquet
# - data/bronze/sme_hybrid/fact_b2b_invoices.parquet
# - data/bronze/sme_hybrid/fact_macro_priors.parquet
python scripts\build_hybrid_dataset.py

# 3. Run built-in Bronze validation (row counts, null counts, and sample records)
python scripts\verify_bronze.py

# 4. Audit exact row counts and column schemas across all Bronze Parquet files (metadata-only, zero RAM)
python -c "import polars as pl, glob; [print(f, pl.scan_parquet(f).select(pl.len()).collect().item()) for f in sorted(glob.glob('data/bronze/sme_hybrid/*.parquet'))]"

```

---

## 5. Save & Push Phase 0 Bronze Checkpoint to GitHub
```powershell
git status
git add .gitignore README.md SETUP_GUIDE.md scripts/
git commit -m "feat(bronze): complete 4-dataset hybrid ingestion with DataCo B2B invoices"
git push
```

---

## 6. Phase 1: Provision AWS S3 Medallion Buckets via Terraform
> **Note on Region (`ap-southeast-2`):** The AWS Organization SCP (`p-hxegi4m2`) restricts resource creation to Asia Pacific (Sydney) `ap-southeast-2`. Ensure `default = "ap-southeast-2"` is set in `infra/terraform/main.tf` (or `variables.tf`).

```powershell
# 1. Extract Terraform Windows AMD64 binary to C:\terraform and register in PATH (idempotent)
New-Item -ItemType Directory -Force -Path C:\terraform | Out-Null
Expand-Archive -Path "\$env:USERPROFILE\Downloads\terraform_*_windows_amd64.zip" -DestinationPath C:\terraform -Force
\$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (\$currentPath -notlike "*C:\terraform*") {
    [Environment]::SetEnvironmentVariable("Path", "\$currentPath;C:\terraform", "User")
}
\$env:Path += ";C:\terraform"
terraform --version

# 2. Configure AWS IAM programmatic credentials (Sydney region: ap-southeast-2)
aws configure
# • AWS Access Key ID: (paste your Access Key)
# • AWS Secret Access Key: (paste your Secret Key)
# • Default region name: ap-southeast-2
# • Default output format: json
aws sts get-caller-identity

# 3. Initialize, preview, and apply Terraform Infrastructure-as-Code
# Creates:
# - msme-cashflow-underwriting-bronze-5bd6f33d
# - msme-cashflow-underwriting-silver-5bd6f33d
# - msme-cashflow-underwriting-gold-5bd6f33d
# - msme-cashflow-underwriting-ml-registry-5bd6f33d
Push-Location infra\terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
Remove-Item tfplan
Pop-Location
```

---

## 7. Upload Bronze Parquet Tables to AWS S3
```powershell
# 1. Make sure AWS CLI default region is set to Sydney (ap-southeast-2)
aws configure set region ap-southeast-2

# 2. Upload your 4 Bronze Parquet files to the S3 Bronze bucket
aws s3 cp data\bronze\sme_hybrid\ s3://msme-cashflow-underwriting-bronze-5bd6f33d/sme_hybrid/ --recursive

# 3. Verify all 4 files appear in S3
aws s3 ls s3://msme-cashflow-underwriting-bronze-5bd6f33d/sme_hybrid/
aws s3 ls s3://msme-cashflow-underwriting-bronze-5bd6f33d/sme_hybrid/ --human-readable
```

---

## 8. Save & Push Phase 1 Infrastructure Checkpoint to GitHub
```powershell
# 1.Ensure .terraform/, *.tfstate*, and plan files are ignored in .gitignore before staging
Add-Content -Path .gitignore -Value "`n**/.terraform/*`n*.tfstate`n*.tfstate.*`n*.tfvars`n*tfplan*`n"

# 2.Deduplicate .gitignore rules
Get-Content .gitignore | Select-Object -Unique | Set-Content .gitignore

# 3.Check staged files (ensure no data/ or .tfstate files appear)
git status

# 4. Commit and push Phase 1 checkpoint to GitHub
# Stage all modified and untracked files (respecting .gitignore)
git add .
git commit -m "feat(bronze-infra): set region to ap-southeast-2, populate bronze tables, and upload to S3"
git push
```
