"""Step 3: Build the knowledge-work occupation panel with all indices.

Indices (each O*NET item z-scored across the sample, then averaged, then the composite re-standardized):

  KWDM communication friction (F_comm): Face-to-Face Discussions, Contact With Others,
      Work With Work Group, Frequency of Decision Making, Time Pressure  [Work Context, CX scale]
  KWDM verification friction (F_verif) = -checkability + risk, where
      checkability = mean(Determine Tasks/Priorities/Goals, -Freedom to Make Decisions)
      risk = mean(Consequence of Error, Importance of Being Exact, Work Outcomes of Other Workers)
  Polanyi (P): On-Site/In-Plant Training, On-the-Job Training [Education/Training, expected level];
      Social Perceptiveness, Coordination, Persuasion, Negotiation [Skills, IM];
      Establishing Relationships, Resolving Conflicts, Guiding Subordinates [Work Activities, IM];
      Physical Proximity [Work Context, CX]
  Intelligence (I): Deductive/Inductive/Mathematical Reasoning, Information Ordering, Written
      Comprehension, Written Expression [Abilities, IM]; Analyzing Data, Processing Information [Work Activities, IM]
  Routine (R): Importance of Repeating Same Tasks, -Determine Tasks/Priorities/Goals, -Freedom to Make Decisions

Sample: Dingel-Neiman teleworkable == 1, plus all SOC 15 (DN uses 2010 codes for computer occupations),
2022 employment >= 10,000, full 2022-2025 panel, full O*NET coverage.

Output: data/occupation_panel_2022_2025.csv
"""
from collections import defaultdict
import numpy as np
import pandas as pd
from common import RAW, DATA

WC = ["Face-to-Face Discussions with Individuals and Within Teams", "Contact With Others",
      "Work With or Contribute to a Work Group or Team", "Frequency of Decision Making", "Time Pressure",
      "Determine Tasks, Priorities and Goals", "Freedom to Make Decisions", "Consequence of Error",
      "Importance of Being Exact or Accurate", "Work Outcomes and Results of Other Workers",
      "Physical Proximity", "Importance of Repeating Same Tasks"]
SK = ["Social Perceptiveness", "Coordination", "Persuasion", "Negotiation"]
WA = ["Establishing and Maintaining Interpersonal Relationships", "Resolving Conflicts and Negotiating with Others",
      "Guiding, Directing, and Motivating Subordinates", "Analyzing Data or Information", "Processing Information"]
AB = ["Deductive Reasoning", "Inductive Reasoning", "Mathematical Reasoning", "Information Ordering",
      "Written Comprehension", "Written Expression"]
P_ITEMS = ["PT", "OJ"] + SK + WA[:3] + ["Physical Proximity"]
I_ITEMS = AB + WA[3:]

def onet_items(fname, scale, elems):
    df = pd.read_csv(RAW / "onet" / fname, sep="\t", usecols=["O*NET-SOC Code", "Element Name", "Scale ID", "Data Value"])
    df = df[(df["Scale ID"] == scale) & df["Element Name"].isin(elems)]
    df["soc"] = df["O*NET-SOC Code"].str[:7]
    return df.groupby(["soc", "Element Name"])["Data Value"].mean().unstack()

def training_levels():
    """Expected required level: category-weighted mean of the PT (on-site) and OJ (on-the-job) distributions."""
    df = pd.read_csv(RAW / "onet" / "Education_Training_and_Experience.txt", sep="\t")
    df = df[df["Scale ID"].isin(["PT", "OJ"])].copy()
    df["soc"] = df["O*NET-SOC Code"].str[:7]; df["w"] = df["Category"].astype(int) * df["Data Value"]
    g = df.groupby(["soc", "Scale ID"]).agg(w=("w", "sum"), v=("Data Value", "sum"))
    return (g["w"] / g["v"]).unstack()

def z(s):
    return (s - s.mean()) / s.std(ddof=0)

if __name__ == "__main__":
    wc = onet_items("Work_Context.txt", "CX", WC)
    sk = onet_items("Skills.txt", "IM", SK)
    wa = onet_items("Work_Activities.txt", "IM", WA)
    ab = onet_items("Abilities.txt", "IM", AB)
    tr = training_levels()
    attrs = wc.join(sk, how="inner").join(wa, how="inner").join(ab, how="inner").join(tr, how="inner").dropna()

    panel = pd.read_csv(DATA / "oews_panel.csv")
    wide = panel.pivot(index="soc", columns="year", values="emp").dropna()
    wage = panel.pivot(index="soc", columns="year", values="median_wage")
    titles = panel.drop_duplicates("soc").set_index("soc")["title"]
    wide.columns = [f"emp_{c}" for c in wide.columns]
    wide["median_wage_2022"] = wage[2022]; wide["median_wage_2025"] = wage[2025]; wide["title"] = titles

    dn = pd.read_csv(RAW / "dingel_neiman_teleworkable.csv")
    dn["soc"] = dn["onetsoccode"].str[:7]
    tele = dn.groupby("soc")["teleworkable"].max()
    aioe = pd.read_csv(RAW / "oews_2022_with_aioe.csv").set_index("OCC_CODE")["AIOE"]

    df = wide.join(attrs, how="inner")
    df["teleworkable"] = tele.reindex(df.index)
    df["aioe"] = aioe.reindex(df.index)
    df["grp"] = df.index.str[:2]
    kw = df[((df.teleworkable == 1) | (df.grp == "15")) & (df.emp_2022 >= 10000)].copy()
    print("occupations with O*NET + panel:", len(df), "| knowledge-work sample:", len(kw),
          f"| {kw.emp_2022.sum()/1e6:.1f}M workers")

    zs = kw[WC + SK + WA + AB + ["PT", "OJ"]].apply(z)
    kw["F_comm"] = z(zs[WC[:5]].mean(axis=1))
    check = (zs["Determine Tasks, Priorities and Goals"] - zs["Freedom to Make Decisions"]) / 2
    risk = zs[["Consequence of Error", "Importance of Being Exact or Accurate", "Work Outcomes and Results of Other Workers"]].mean(axis=1)
    kw["F_verif"] = z(-z(check) + z(risk))
    kw["polanyi_P"] = z(zs[P_ITEMS].mean(axis=1))
    kw["intelligence_I"] = z(zs[I_ITEMS].mean(axis=1))
    kw["routine_R"] = z((zs["Importance of Repeating Same Tasks"] - zs["Determine Tasks, Priorities and Goals"] - zs["Freedom to Make Decisions"]) / 3)
    mc, mv = kw.F_comm.median(), kw.F_verif.median()
    kw["kwdm_quadrant"] = np.select([(kw.F_comm < mc) & (kw.F_verif < mv), (kw.F_comm < mc), (kw.F_verif < mv)], ["I", "II", "III"], "IV")
    for a, b, name in [(2022, 2025, "22_25"), (2022, 2023, "22_23"), (2023, 2024, "23_24"), (2024, 2025, "24_25")]:
        kw[f"emp_change_pct_{name}"] = 100 * (kw[f"emp_{b}"] - kw[f"emp_{a}"]) / kw[f"emp_{a}"]
    kw["wage_change_pct_22_25"] = 100 * (kw.median_wage_2025 - kw.median_wage_2022) / kw.median_wage_2022

    cols = ["title", "grp", "teleworkable", "emp_2022", "emp_2023", "emp_2024", "emp_2025", "median_wage_2022", "median_wage_2025",
            "emp_change_pct_22_25", "emp_change_pct_22_23", "emp_change_pct_23_24", "emp_change_pct_24_25", "wage_change_pct_22_25",
            "routine_R", "polanyi_P", "intelligence_I", "F_comm", "F_verif", "kwdm_quadrant", "aioe"]
    kw[cols].round(4).rename_axis("soc").to_csv(DATA / "occupation_panel_2022_2025.csv")
    print("quadrant sizes:", kw.kwdm_quadrant.value_counts().to_dict())
