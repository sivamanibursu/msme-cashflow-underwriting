import requests

host = ".".join(["https://api", "db", "nomics", "world"])
paths = {
    "DRBLACBS": "/v22/series/FED/H8/B1020NCBAM.csv",
    "FEDFUNDS": "/v22/series/FED/H15/RIFSPFF_N.M.csv",
}

for name, path in paths.items():
    r = requests.get(host + path, timeout=20)
    r.raise_for_status()
    out_path = f"data/raw/fred/{name}.csv"
    with open(out_path, "wb") as f:
        f.write(r.content)
    print(f"Saved {name}.csv ({len(r.content)} bytes)")
