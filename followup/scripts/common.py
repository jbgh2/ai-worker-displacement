"""Shared paths and helpers for the follow-up pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
for p in (RAW, RESULTS, FIGURES):
    p.mkdir(parents=True, exist_ok=True)

YEARS = ("2022", "2023", "2024", "2025")
UA = {"User-Agent": "ai-worker-displacement-followup (research; github.com/jbgh2)"}
