import os
import requests

os.makedirs("data/raw/fred", exist_ok=True)

host = ".".join(["https://api", "db", "nomics", "world"])
paths = {
    "DRBLACBS": "/v22/series/FED/H8/B1020NCBAM.csv",         # Commercial Credit Index (Monthly)
    "FEDFUNDS": "/v22/series/FED/H15/RIFSPFF_N.D.csv",      # Daily Effective Fed Funds Rate (~26k rows)
    "DGS10": "/v22/series/FED/H15/RIFLGFCY10_N.B.csv",      # Business-Day 10-Year Treasury Yield (~16k rows)
    "TBILL3M": "/v22/series/FED/H15/RIFSGFSM03_N.B.csv",    # Business-Day 3-Month Treasury Bill (~18k rows)
}

for name, path in paths.items():
    print(f"Downloading {name}...")
    r = requests.get(host + path, timeout=30)
    r.raise_for_status()
    out_path = f"data/raw/fred/{name}.csv"
    with open(out_path, "wb") as f:
        f.write(r.content)
    print(f"Saved {name}.csv ({len(r.content):,} bytes)")
