"""Checkpoint tests. Run the pipeline (scripts 02, 01, 03, 04) first, then `pytest tests/`.

These assert the headline numbers in the blog post. If BLS revises OEWS, O*NET publishes a new
release, or the mirror changes, expect small drifts; the qualitative assertions at the bottom are
the ones that matter.
"""
import json
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope="module")
def panel():
    return pd.read_csv(ROOT / "data" / "occupation_panel_2022_2025.csv", dtype={"grp": str})

@pytest.fixture(scope="module")
def summary():
    return json.load(open(ROOT / "results" / "summary.json"))

def test_sample_size(panel):
    assert len(panel) == 218
    assert abs(panel.emp_2022.sum() / 1e6 - 49.1) < 0.2

def test_spot_occupations(panel):
    p = panel.set_index("soc")
    assert p.loc["43-4051", "emp_2022"] == 2879840          # customer service reps, May 2022
    assert round(p.loc["43-4051", "emp_change_pct_22_25"], 1) == -9.9
    assert round(p.loc["43-6014", "emp_change_pct_22_25"], 1) == -6.6   # secretaries
    assert round(p.loc["43-6013", "emp_change_pct_22_25"], 1) == 40.9   # medical secretaries
    assert round(p.loc["15-1252", "emp_change_pct_22_25"], 1) == 10.0   # software developers
    assert round(p.loc["15-1251", "emp_change_pct_22_25"], 1) == -30.5  # programmers
    assert round(p.loc["15-2051", "emp_change_pct_22_25"], 1) == 64.4   # data scientists

def test_cells(summary):
    c = summary["cells"]
    assert abs(c["routine / not embedded"] - (-2.6)) < 0.3
    assert abs(c["routine / embedded"] - 8.4) < 0.3
    assert abs(c["non-routine / not embedded"] - 5.7) < 0.3
    assert abs(c["non-routine / embedded"] - 6.6) < 0.3

def test_quadrants(summary):
    q = summary["quadrants"]
    assert abs(q["IV"] - 8.6) < 0.3 and abs(q["I"] - (-0.5)) < 0.3

def test_regressions(summary):
    r = summary["regressions"]
    aioe = r["AIOE only"]; assert abs(aioe["b_aioe"]) < aioe["se_aioe"]            # exposure predicts nothing
    kwdm = r["KWDM frictions"]; assert abs(kwdm["b_F_comm"]) < kwdm["se_F_comm"]   # communication friction: zero
    two = r["Two-factor"]; assert two["b_intelligence_I"] > 2 * two["se_intelligence_I"]  # Intelligence has the WRONG sign for Cowen
    late = r["Three-factor, 24_25"]; assert late["b_RxP"] > 2 * late["se_RxP"]      # interaction significant in 2024->25

# Qualitative assertions: these should survive data revisions.
def test_qualitative(summary):
    c = summary["cells"]
    assert c["routine / not embedded"] < 0
    assert all(c[k] > 4 for k in c if k != "routine / not embedded")
    q = summary["quadrants"]; assert q["IV"] == max(q.values())
    t = summary["terciles"]; assert t["intelligence_I"]["high"] > t["intelligence_I"]["low"]
    assert t["routine_R"]["high"] < t["routine_R"]["low"]
