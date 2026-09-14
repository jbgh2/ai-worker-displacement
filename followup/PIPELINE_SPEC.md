# Pipeline Specification: Follow-up (September 2026)

Same convention as the top-level spec: each step lists inputs, process, checkpoints, outputs.
Checkpoints are from a run on 2026-09-14 against O*NET 30.0, OEWS May 2022–May 2025, Indeed/FRED
through 2026-09-04, and BLS CES through August 2026.

## Step 1: O*NET, Dingel-Neiman, AIOE (`02_fetch_onet.py`)

Downloads O*NET 30.0 text files (Work Context, Skills, Abilities, Work Activities, Education/Training/
Experience, Occupation Data), the Dingel-Neiman teleworkability file, and a 2022 OEWS table with AIOE.

| Check | Expected |
|---|---|
| Work_Context.txt size | 36,782,933 bytes |
| Occupation_Data.txt distinct 6-digit SOC codes | 867 |
| dingel_neiman_teleworkable.csv rows | 968 |
| oews_2022_with_aioe.csv rows | 666 |

## Step 2: OEWS panel (`01_fetch_oews.py`)

Fetches `data/{year}/jobs/{soc}.json` from the mirror for every SOC in step 1, all four years.
Validates 2025 against the BLS API (25 occupations) and 2022 against the AIOE-merged table.

| Check | Expected |
|---|---|
| Mirror rows loaded | 3,218 |
| Occupations with all four years | 794 |
| Mismatches vs BLS API 2025 | 0 of 25 |
| Mismatches vs independent 2022 table | 0 of 653 |

## Step 3: Panel and indices (`03_build_panel.py`)

Item lists are in the script docstring. Each item is z-scored across the knowledge-work sample; each
composite is the mean of its items and is re-standardized. Training items use the expected required
level (category-weighted mean of the PT and OJ distributions). O*NET 8-digit codes are averaged to 6-digit.

Sample rule: Dingel-Neiman `teleworkable == 1` (max across 8-digit sub-codes), **or** SOC major group 15
(DN uses 2010 codes for computer occupations so they don't merge), and 2022 employment ≥ 10,000.

| Check | Expected |
|---|---|
| Occupations with O*NET + full panel | 718 |
| Knowledge-work sample | 218 |
| 2022 employment in sample | 49.1M |
| KWDM quadrant sizes (I/II/III/IV) | 61 / 48 / 48 / 61 |
| Customer Service Representatives emp_2022 | 2,879,840 |
| Software Developers emp_change_pct_22_25 | +10.0 |
| Medical Secretaries emp_change_pct_22_25 | +40.9 |

## Step 4: Analysis (`04_analyze.py`)

Employment-weighted (2022 weights) group means; WLS with HC1 robust SEs. All-occupation baseline
+5.1% (147,886,000 → 155,495,730).

| Check | Expected |
|---|---|
| Sample employment change 22→25 | +3.9% |
| KWDM quadrants I / II / III / IV | −0.5 / +2.7 / +3.3 / +8.6 |
| Routine × Polanyi: routine, not embedded | −2.6% (64 occ, 15.3M) |
| routine, embedded | +8.4% (45, 6.8M) |
| non-routine, not embedded | +5.7% (45, 5.7M) |
| non-routine, embedded | +6.6% (64, 21.3M) |
| AIOE terciles low / mid / high | +3.4 / +2.2 / +7.4 |
| Intelligence terciles low / mid / high | −1.9 / +4.3 / +12.0 |
| Routine terciles low / mid / high | +7.4 / +6.3 / −1.7 |
| AIOE-only regression | b = +2.56 (2.67) |
| KWDM frictions | F_comm −0.03 (0.97), F_verif +2.88 (1.26) |
| Two-factor | P +1.52 (1.19), I +4.15 (1.58) |
| Three-factor + interaction, 22→25 | R −2.50 (1.31), P +0.64 (1.24), R×P +1.45 (1.05), I +2.63 (1.54) |
| Three-factor, 24→25 | R −0.71 (0.54), P −0.29 (0.45), R×P +0.85 (0.40), I +0.76 (0.49) |
| Wage regression, quadrants (with ln wage 2022) | QIII −0.28 (1.62); no quadrant significant |

Outputs: `results/kwdm_quadrants.csv`, `results/routine_x_polanyi_cells.csv`, `results/regressions.csv`,
`results/summary.json`, `figures/fig_routine_polanyi_map.png`, `figures/fig_four_cells_by_year.png`.

## Step 5: Indeed postings (`05_indeed_postings.py`)

FRED series `IHLIDXUS` and `IHLIDXUSTP*`. Change from Jan 2025 monthly mean to the last complete month,
minus the same change in the aggregate. Ten category IDs guessed from the FRED naming pattern returned
404 (Data & Analytics, Banking & Finance, Scientific Research, etc.); 21 series load.

| Check | Expected |
|---|---|
| Aggregate index Jan 2025 → Aug 2026 | 110.2 → 101.9 (−7.5%) |
| Accounting raw / relative | −27.0% / −19.5 pts |
| Customer service raw / relative | +0.7% / +8.2 pts |
| Software development raw / relative | +10.3% / +17.8 pts |
| Group means, relative (I / R / P / M) | +5.8 / +2.0 / −6.8 / +5.2 |

## Step 6: CES industries (`06_ces_industries.py`)

BLS API, 21 detailed industry series, 2018 to latest.

| Check | Expected |
|---|---|
| Insurance carriers pre-COVID trend / last 12m | +3.2%/yr / −2.5% |
| Insurance carriers peak month | 2025-02 |
| Telephone call centers pre-COVID trend | −3.6%/yr |
| Data processing/hosting last 12m | −5.4% |

## Known issues

1. **Routine index is post-hoc.** Defined after Entry 1 of the research log showed losers spanning all
   KWDM quadrants with low I and low P. Items are standard ALM routine proxies, and the interaction
   with the pre-specified Polanyi score carries the late-period result, but discount accordingly.
2. **OEWS is not a time series.** Three-year panel pooling smooths and lags annual changes.
3. **No 2019 baseline.** Pre-trend in bookkeeping, data entry, and call-center work is documented in
   CES but not yet in the occupation panel. BLS blocks the 2019 file; a mirror has not been found.
4. **Occupation-level Polanyi cannot see sector.** Medical secretaries and other secretaries score
   within 0.25 SD of each other on P. The sector did the protecting.
5. **Accountants (13-2011) are not Dingel-Neiman teleworkable** and are outside the 218. The +3.4%
   figure in the post is from the BLS API for 2022→2025 directly.
