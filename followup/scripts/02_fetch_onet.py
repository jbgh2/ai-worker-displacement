"""Step 1: O*NET 30.0 database files, Dingel-Neiman teleworkability, and AIOE.

Outputs: data/raw/onet/*.txt, data/raw/dingel_neiman_teleworkable.csv, data/raw/oews_2022_with_aioe.csv
AIOE (Felten, Raj, Seamans 2021) comes from a mirror of the May 2022 OEWS national table with AIOE
merged, from github.com/augw999/ai-labor-market-impact_analysis.
"""
import requests
from common import RAW, UA

ONET = "https://www.onetcenter.org/dl_files/database/db_30_0_text/{f}.txt"
FILES = ["Work Context", "Skills", "Abilities", "Work Activities", "Education, Training, and Experience", "Occupation Data"]
DN = "https://raw.githubusercontent.com/jdingel/DingelNeiman-workathome/master/occ_onet_scores/output/occupations_workathome.csv"
AIOE = "https://raw.githubusercontent.com/augw999/ai-labor-market-impact_analysis/main/cleaned_data_2022.csv"

if __name__ == "__main__":
    d = RAW / "onet"; d.mkdir(exist_ok=True)
    for f in FILES:
        out = d / (f.replace(", ", "_").replace(" ", "_") + ".txt")
        if not out.exists():
            r = requests.get(ONET.format(f=f.replace(" ", "%20")), headers=UA, timeout=120); r.raise_for_status()
            out.write_bytes(r.content)
        print(out.name, out.stat().st_size)
    for url, name in [(DN, "dingel_neiman_teleworkable.csv"), (AIOE, "oews_2022_with_aioe.csv")]:
        out = RAW / name
        if not out.exists():
            r = requests.get(url, timeout=60); r.raise_for_status(); out.write_bytes(r.content)
        print(name, out.stat().st_size)
