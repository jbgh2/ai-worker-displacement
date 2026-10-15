"""Step 6: BLS CES monthly industry employment, 2018-latest, for the industry-level sequencing check.

Output: results/ces_industries.csv (pre-COVID trend, 2022-25 trend, last-12-month change, peak, change since peak)
"""
import time
import requests
import pandas as pd
from common import RESULTS, RAW

BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
SERIES = {
 "CES0000000001": "Total nonfarm", "CES5552400001": "W2 Insurance carriers", "CES5552420001": "W2 Insurance agencies/brokerages",
 "CES5552200001": "W2 Credit intermediation", "CES5051300001": "W2 Publishing", "CES5051800001": "W2 Data processing/hosting",
 "CES5051600001": "W2 Computing infrastructure", "CES6054150001": "W2 Computer systems design", "CES6054120001": "W2 Accounting/bookkeeping",
 "CES6054110001": "W2 Legal services", "CES5552300001": "W2 Securities", "CES6054180001": "W2 Advertising/PR",
 "CES6056142001": "W1 Telephone call centers", "CES6056140001": "W1 Business support services", "CES6056110001": "W1 Office administrative services",
 "CES6056132001": "Placebo Temporary help", "CES6562000001": "Control Health care", "CES7072200001": "Control Food services",
 "CES2000000001": "Control Construction", "CES6054130001": "Control Architecture/engineering", "CES6054160001": "Control Consulting",
}

def ann(m, a, b):
    n = (int(b[:4]) - int(a[:4])) * 12 + int(b[5:]) - int(a[5:]); return 100 * ((m[b] / m[a]) ** (12 / n) - 1)

if __name__ == "__main__":
    ids = list(SERIES); out = {}
    for i in range(0, len(ids), 25):
        r = requests.post(BLS_API, json={"seriesid": ids[i:i+25], "startyear": "2018", "endyear": "2026"}, headers={"Content-type": "application/json"}, timeout=60).json()
        print(r["status"], r.get("message"))
        for s in r["Results"]["series"]:
            rows = sorted((x["year"] + "-" + x["period"][1:], float(x["value"])) for x in s["data"] if x["period"] != "M13")
            if rows: out[s["seriesID"]] = rows
        time.sleep(1)
    (RAW / "ces").mkdir(exist_ok=True)
    pd.DataFrame([(sid, SERIES[sid], d, v) for sid, rows in out.items() for d, v in rows], columns=["series", "name", "month", "employment_k"]).to_csv(RAW / "ces" / "ces_industries_monthly.csv", index=False)
    res = []
    for sid, rows in out.items():
        m = dict(rows); last = rows[-1][0]; y, mm = int(last[:4]), last[5:]; prev = f"{y-1}-{mm}"
        pk = max((x for x in rows if x[0] >= "2018-01"), key=lambda x: x[1])
        res.append({"industry": SERIES[sid], "latest_month": last, "employment_k": m[last], "pre_covid_trend_pct_yr": round(ann(m, "2018-01", "2020-02"), 2),
                    "trend_2022_2025_pct_yr": round(ann(m, "2022-01", "2025-02"), 2), "last_12m_pct": round(100 * (m[last] / m[prev] - 1), 2),
                    "peak_month": pk[0], "since_peak_pct": round(100 * (m[last] / pk[1] - 1), 2)})
    df = pd.DataFrame(res).sort_values("last_12m_pct"); df.to_csv(RESULTS / "ces_industries.csv", index=False); print(df.to_string(index=False))
