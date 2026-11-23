# MSME (Micro, Small & Medium Enterprise) Cash-Flow Underwriting

## Project Overview

Traditional banks often reject creditworthy **Micro, Small, and Medium Enterprises (MSMEs)** due to limited physical collateral and thin credit histories. This project implements an end-to-end **Cash-Flow Underwriting Engine** that evaluates borrower default risk using daily bank ledger cash flows, B2B invoice settlement behavior, and macroeconomic interest rate indicators.

### Key Architectural Highlights
* **Hybrid Multi-Source Star Schema:** Integrates 4 open-licensed datasets (**8,202** resolved U.S. SBA 7(a) SME loans, **64,698** commercial bank ledger transactions, **54,789** corporate B2B invoices, and **958** FRED macroeconomic observations) into compressed Parquet tables.
* **Leakage-Free Temporal Engineering:** Enforces strict pre-application cutoffs (`invoice_date < application_date`) and backward `as-of` macroeconomic joins so models only train on point-in-time data available at underwriting.
* **AWS S3 Medallion Architecture (IaC):** Automated provisioning of isolated **Bronze, Silver, Gold, and ML Registry** S3 buckets with public-access blocks via **Terraform** (`ap-southeast-2`).
* **Tech Stack:** Python, Polars, PyArrow, Terraform, AWS S3, Boto3, Scikit-Learn / XGBoost / PyTorch.

## Data Licenses & Attribution

* **AgamiAI Indian Bank Statements:** Apache 2.0 (`AgamiAI/Indian-Bank-Statements`).
* **U.S. SBA National Loan Dataset:** Public Domain (`FOIA_7a_FY2020_Present`).
* **DataCo Smart Supply Chain Dataset:** CC BY 4.0 — Constante, Fabian; Silva, Fernando; Pereira, António (2019), *"DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS"*, Mendeley Data, V5, DOI: `10.17632/8gx2fvg2k6.5`.
* **FRED Economic Series:** Public Domain (`DRBLACBS`, `FEDFUNDS`).
