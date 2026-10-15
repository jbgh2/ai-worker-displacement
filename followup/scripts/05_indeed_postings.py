"""Step 5: Indeed Hiring Lab job postings by occupational category, via FRED (through the latest date).

Change from January 2025 to the latest month, relative to the aggregate index, grouped by which
model claims the category. Output: results/indeed_postings_by_category.csv
"""
import io, csv
import requests
import pandas as pd
from common import RESULTS, RAW

SERIES = {
 "IHLIDXUS": ("ALL", "All postings"),
 "IHLIDXUSTPSOFTDEVE": ("I", "Software development"), "IHLIDXUSTPMATH": ("I", "Mathematics"), "IHLIDXUSTPACCO": ("I", "Accounting"),
 "IHLIDXUSTPLEGA": ("I", "Legal"), "IHLIDXUSTPARCH": ("I", "Architecture"), "IHLIDXUSTPCIVIENGI": ("I", "Civil engineering"),
 "IHLIDXUSTPELECENGI": ("I", "Electrical engineering"), "IHLIDXUSTPINDUENGI": ("I", "Industrial engineering"),
 "IHLIDXUSTPCUSTSERV": ("R", "Customer service"), "IHLIDXUSTPADMIASSI": ("R", "Administrative assistance"),
 "IHLIDXUSTPINSU": ("R", "Insurance"), "IHLIDXUSTPLOGISUPP": ("R", "Logistic support"),
 "IHLIDXUSTPNURS": ("P", "Nursing"), "IHLIDXUSTPCHIL": ("P", "Childcare"), "IHLIDXUSTPCONS": ("P", "Construction"),
 "IHLIDXUSTPMANA": ("M", "Management"), "IHLIDXUSTPPROJMANA": ("M", "Project management"), "IHLIDXUSTPHUMARESO": ("M", "Human resources"),
 "IHLIDXUSTPMARK": ("M", "Marketing"), "IHLIDXUSTPSALE": ("M", "Sales"),
}
GROUPS = {"I": "High-Intelligence (Cowen)", "R": "Routine, not embedded", "P": "Polanyi / embedded", "M": "Managerial / judgment"}

def fred(sid):
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=30)
    if r.status_code != 200 or "observation_date" not in r.text[:200]:
        return None
    df = pd.read_csv(io.StringIO(r.text)); df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce"); df["date"] = pd.to_datetime(df["date"])
    return df.dropna()

if __name__ == "__main__":
    raw = {}
    for sid in SERIES:
        d = fred(sid)
        if d is not None: raw[sid] = d
    (RAW / "indeed").mkdir(exist_ok=True)
    pd.concat([d.assign(series=s) for s, d in raw.items()]).to_csv(RAW / "indeed" / "fred_indeed_postings.csv", index=False)
    def mavg(df, ym): v = df[df.date.dt.strftime("%Y-%m") == ym].value; return v.mean() if len(v) else None
    allp = raw["IHLIDXUS"]
    counts = allp.date.dt.strftime("%Y-%m").value_counts()
    end = max(m for m, n in counts.items() if n >= 20)  # last complete month
    A25, Ae = mavg(allp, "2025-01"), mavg(allp, end)
    rows = []
    for sid, (g, name) in SERIES.items():
        if sid == "IHLIDXUS" or sid not in raw: continue
        d = raw[sid]; last = d.date.max().strftime("%Y-%m"); e = last if last < end else end
        j25, v = mavg(d, "2025-01"), mavg(d, e); ae = mavg(allp, e)
        if j25 is None or v is None: continue
        rows.append({"category": name, "group": GROUPS[g], "jan_2025": round(j25, 1), "latest": round(v, 1), "latest_month": e,
                     "raw_change_pct": round(100 * (v / j25 - 1), 1), "rel_to_aggregate_pts": round(100 * (v / j25 - 1) - 100 * (ae / A25 - 1), 1)})
    out = pd.DataFrame(rows).sort_values("rel_to_aggregate_pts"); out.to_csv(RESULTS / "indeed_postings_by_category.csv", index=False)
    print(f"aggregate index: Jan 2025 {A25:.1f} -> {end} {Ae:.1f} ({100*(Ae/A25-1):+.1f}%)"); print(out.to_string(index=False))
    print("\ngroup means (rel to aggregate):", out.groupby("group").rel_to_aggregate_pts.mean().round(1).to_dict())
