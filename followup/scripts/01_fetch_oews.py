"""Step 2: OEWS national occupation employment and median wage, May 2022-May 2025.

BLS blocks bulk file downloads from scripts (HTTP 403 on the .zip and .htm tables), and the
BLS public API only serves the current OEWS release. So:
  - 2025 (current release) comes from the BLS API and is authoritative.
  - 2022-2024 come from a GitHub mirror (Vabryn/bls) of the published national files.
  - The mirror's 2025 values are validated against the API for a 25-occupation check set,
    and its 2022 values against the AIOE-merged 2022 table (independent source) for all occupations.

Outputs: data/raw/oews/<year>/<soc>.json, data/oews_panel.csv
"""
import json, time, sys
from concurrent.futures import ThreadPoolExecutor
import requests
import pandas as pd
from common import RAW, DATA, YEARS

MIRROR = "https://raw.githubusercontent.com/Vabryn/bls/main/data/{year}/jobs/{soc}.json"
BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
OEWS_DIR = RAW / "oews"
CHECK = ["43-4051", "43-6014", "43-6013", "43-3031", "43-9061", "15-1252", "15-1251", "13-2011",
         "23-1011", "11-1021", "13-1031", "15-2051", "13-1111", "41-4012", "43-4171", "43-9021",
         "43-3011", "13-2041", "13-2072", "43-1011", "11-3021", "11-9111", "13-1161", "43-3021", "43-4151"]

def soc_list():
    occ = RAW / "onet" / "Occupation_Data.txt"
    if not occ.exists():
        sys.exit("Run 02_fetch_onet.py first (needs Occupation_Data.txt for the SOC list).")
    return sorted({c[:7] for c in pd.read_csv(occ, sep="\t")["O*NET-SOC Code"]})

def fetch_one(args):
    year, soc = args
    out = OEWS_DIR / year / f"{soc}.json"
    if out.exists() and out.stat().st_size > 0:
        return
    r = requests.get(MIRROR.format(year=year, soc=soc), timeout=30)
    if r.status_code == 200:
        out.write_bytes(r.content)

def load_mirror():
    rows = []
    for year in YEARS:
        for f in (OEWS_DIR / year).glob("*.json"):
            try:
                j = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue
            if "nat" in j:
                rows.append({"soc": j["soc"], "title": j["title"], "year": int(year),
                             "emp": j["nat"]["emp"], "median_wage": j["nat"]["median"]})
    return pd.DataFrame(rows)

def api_2025(socs):
    ids = [f"OEUN0000000000000{s.replace('-', '')}01" for s in socs]
    vals = {}
    for i in range(0, len(ids), 25):
        r = requests.post(BLS_API, json={"seriesid": ids[i:i+25], "startyear": "2025", "endyear": "2025"},
                          headers={"Content-type": "application/json"}, timeout=60).json()
        if r.get("status") != "REQUEST_SUCCEEDED":
            print("BLS API:", r.get("message")); break
        for s in r["Results"]["series"]:
            if s["data"]:
                vals[s["seriesID"][17:19] + "-" + s["seriesID"][19:23]] = float(s["data"][0]["value"])
        time.sleep(1)
    return vals

if __name__ == "__main__":
    socs = soc_list()
    for y in YEARS:
        (OEWS_DIR / y).mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(24) as ex:
        list(ex.map(fetch_one, [(y, s) for y in YEARS for s in socs]))
    panel = load_mirror()
    full = (panel.groupby("soc")["year"].nunique() == 4).sum()
    print("mirror rows:", len(panel), "| occupations with all four years:", full)

    api = api_2025(CHECK)
    m = panel[(panel.year == 2025)].set_index("soc")["emp"]
    mism = [(s, m.get(s), api[s]) for s in api if s in m.index and abs(m[s] - api[s]) > 1]
    print(f"validation vs BLS API 2025: {len(api)} compared, {len(mism)} mismatches", mism[:5])

    a22 = pd.read_csv(RAW / "oews_2022_with_aioe.csv").set_index("OCC_CODE")["TOT_EMP"]
    m22 = panel[panel.year == 2022].set_index("soc")["emp"]
    common = [s for s in a22.index if s in m22.index]
    mism22 = sum(abs(m22[s] - a22[s]) > 1 for s in common)
    print(f"validation vs independent 2022 table: {len(common)} compared, {mism22} mismatches")
    panel.to_csv(DATA / "oews_panel.csv", index=False)
