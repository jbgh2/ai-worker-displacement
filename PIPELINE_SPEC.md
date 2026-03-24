# Pipeline Specification: AI Worker Displacement Analysis

This document specifies how to reproduce the full analysis from raw data sources through to the final blog post outputs. Every step includes expected intermediate outputs so you can verify correctness as you go.

## O*NET Version Note

This pipeline was developed and validated against **O*NET 28.1 (August 2023)**. As of March 2026, the current release is **O*NET 30.2**.

**Recommended approach:**
1. First, reproduce with O*NET 28.1 and verify all checkpoint values match. This confirms the pipeline code is correct.
2. Then, re-run with O*NET 30.2 (or whatever is current) and compare outputs. Any differences are real changes in the occupational data, not bugs.
3. Document what changed between versions — shifts in tier distributions, individual occupation movements, and whether the Indeed correlations hold. This is interesting content in its own right.

The checkpoint values in this spec are all based on 28.1. If using a newer release, expect minor differences throughout (the number of occupations may change, z-scores will shift slightly, tier counts will move). The structure and logic of every step stays the same.

---

## Raw Data Sources

All raw data lives in `code/data/raw/`. You will need:

| File | Source | Description |
|------|--------|-------------|
| `Work Context.xlsx` | O*NET 28.1 (Aug 2023) | Work context survey data for 894 occupations |
| `indeed_hiring_lab/job_postings_by_sector_us.csv` | Indeed Hiring Lab | Daily job posting index by sector, US |
| `indeed_hiring_lab/remote_postings_sector.csv` | Indeed Hiring Lab | Remote posting share by sector |
| `oews_timeseries/oesm24nat/oesm24nat/national_M2024_dl.xlsx` | BLS OEWS May 2024 | National occupation employment and wage estimates |

The Indeed data is publicly available at https://hiringlab.indeed.com/data/. The O*NET data is at https://www.onetcenter.org/database.html (download "Work Context" from the database files). BLS OEWS data is at https://www.bls.gov/oes/tables.htm.

---

## Step 1: Build Delegation Resistance (DR) Index

### Input
`Work Context.xlsx`

### Process

1. Load the Excel file. It has 297,676 rows and 16 columns.

2. Filter to rows where `Scale Name == 'Context'`. This gives 50,958 rows.

3. Filter to the 11 DR items by `Element Name`:

**High-friction items** (high score = hard to delegate):

- `Face-to-Face Discussions with Individuals and Within Teams`
- `Physical Proximity`
- `Deal With External Customers or the Public in General`
- `Contact With Others`
- `Work With or Contribute to a Work Group or Team`

**Physical items** (high score = hard to delegate):

- `Spend Time Using Your Hands to Handle, Control, or Feel Objects, Tools, or Controls`
- `Spend Time Standing`
- `Spend Time Walking or Running`
- `Outdoors, Exposed to All Weather Conditions`

**Desk-work items** (high score = EASY to delegate, must be FLIPPED):

- `E-Mail`
- `Spend Time Sitting`

This gives 9,834 rows: 894 occupations x 11 items each.

4. Pivot to a wide table: rows = O*NET-SOC Code (894), columns = 11 Element Names, values = `Data Value`. No NaN values should exist.

5. Z-score each column independently (mean=0, std=1) across the 894 occupations.

6. **FLIP the desk-work items**: multiply the z-scored `E-Mail` and `Spend Time Sitting` columns by -1. After flipping, a high z-score on every item means "hard to delegate."

7. Compute the DR index as the **mean of all 11 z-scored (and flipped) items** per occupation.

### Checkpoints

| Check | Expected |
|-------|----------|
| Rows after Context filter | 50,958 |
| Rows after DR items filter | 9,834 |
| Pivot shape | (894, 11) |
| Any NaN in pivot | False |
| Each column mean after z-score | ~0.0000 |
| Each column std after z-score | ~1.0000 |
| DRrange | -2.1844 to 1.1357 |
| DRmean | ~0.0000 |
| DRstd | 0.5313 |
| DRfor Software Developers (15-1252.00) | -1.4266 |
| DRfor Veterinarians (29-1131.00) | 0.7637 |
| DRfor Electricians (47-2111.00) | 0.9745 |
| DRfor Elementary School Teachers (25-2021.00) | 0.7511 |

### Output
A table of 894 rows with columns: `O*NET-SOC Code`, `Title`, `comm_friction` (the raw DR index), and optionally all 11 z-scored item columns for use in Step 4.

To produce `comm_friction_onet_norm` (min-max normalized to 0-1), apply: `(cf - cf.min()) / (cf.max() - cf.min())`.

---

## Step 2: Build Anchor Score

### Input
The 894 x 11 z-scored (and flipped) item matrix from Step 1.

### Process

1. For each occupation, compute `sum_positive_z`: sum of all z-scored items that are > 0 (clip negative values to 0, then sum across the 11 items).

2. Compute `anchor_count`: the number of items > 0 per occupation.

3. Compute `max_z`: the maximum z-score across all 11 items per occupation.

4. Min-max normalize `sum_positive_z` to produce the anchor score: `anchor_score = (sum_positive_z - min) / (max - min)`. This produces a 0-1 scale where 1 = most anchored.

5. `exposure_score = 1 - anchor_score`.

6. Classify "truly anchorless" occupations as those where `max_z < 0` (every single item is below the cross-occupation average).

### CRITICAL NOTE ON FLIPPING

The z-scores used here MUST be the flipped versions from Step 1 (E-Mail and Sitting negated). Without flipping, high email use and high sitting would count as "anchors" when they are actually markers of AI-vulnerable desk work. The flipped version produces 29 truly anchorless occupations. The unflipped version produces 0, which is wrong.

### Checkpoints

| Check | Expected |
|-------|----------|
| sum_positive_z range | 0.0000 to 13.5849 |
| anchor_score range | 0.0000 to 1.0000 |
| anchor_score median | 0.3143 |
| anchor_score mean | 0.3363 |
| Truly anchorless (max_z < 0) | 29 |
| Tier: Very Exposed (< 0.15) | 261 occupations |
| Tier: Exposed (0.15-0.35) | 219 occupations |
| Tier: Moderate (0.35-0.55) | 219 occupations |
| Tier: Anchored (0.55-0.75) | 155 occupations |
| Tier: Well Anchored (>= 0.75) | 40 occupations |

**Occupation-level checkpoints:**

| O*NET Code | Title | anchor_score | anchor_count | sum_pos_z |
|------------|-------|-------------|-------------|-----------|
| 25-2021.00 | Elementary School Teachers | 0.7513 | 9/11 | 10.2062 |
| 47-2111.00 | Electricians | 0.8365 | 10/11 | 11.3641 |
| 29-1131.00 | Veterinarians | 0.6959 | 9/11 | 9.4531 |
| 29-1141.00 | Registered Nurses | 0.5322 | 7/11 | ~7.23 |
| 29-1123.00 | Physical Therapists | 0.6200 | 10/11 | ~8.42 |
| 47-2152.00 | Plumbers | 0.6530 | 7/11 | ~8.87 |
| 11-1021.00 | General Managers | 0.3150 | 7/11 | ~4.28 |
| 23-1011.00 | Lawyers | 0.1090 | 2/11 | ~1.48 |
| 15-1252.00 | Software Developers | 0.0580 | 1/11 | 0.7879 |
| 15-1254.00 | Web Developers | 0.0000 | 0/11 | 0.0000 |
| 19-3011.00 | Economists | 0.0000 | 0/11 | 0.0000 |
| 43-9021.00 | Data Entry Keyers | 0.0000 | 0/11 | 0.0000 |
| 15-2021.00 | Mathematicians | 0.0000 | 0/11 | 0.0000 |
| 13-2011.00 | Accountants | 0.1030 | 4/11 | ~1.40 |
| 27-1024.00 | Graphic Designers | 0.0590 | 2/11 | ~0.80 |

### Output
A table of 894 rows with: `O*NET-SOC Code`, `Title`, `anchor_score`, `sum_positive_z`, `anchor_count`, `max_z`.

---

## Step 3: Match BLS Employment Data

### Input
- The 894-occupation table from Step 2
- `oews_timeseries/oesm24nat/oesm24nat/national_M2024_dl.xlsx` (BLS OEWS May 2024)

### Process

1. Load the OEWS national file. It has ~1,403 rows with columns including `OCC_CODE`, `OCC_TITLE`, `TOT_EMP`, `A_MEDIAN`.

2. Build a lookup from `OCC_CODE` -> `(TOT_EMP, A_MEDIAN)`. Some cells contain non-numeric values (e.g., `*` for suppressed data); treat these as 0.

3. For each of the 894 O*NET occupations, match by truncating the O*NET code to 6-digit SOC:
   - First try: `O*NET-SOC Code[:7]` (e.g., `15-1252.00` -> `15-1252`)
   - If no match: try `O*NET-SOC Code[:6] + '0'` (e.g., `15-1252.00` -> `15-1250`)
   - If still no match: set employment to 0

4. Note: when multiple O*NET codes map to the same BLS code, they will share the same employment figure. This is correct for per-occupation display but will overcount in aggregate sums.

### Checkpoints

| Check | Expected |
|-------|----------|
| OEWS rows loaded | ~1,403 |
| Matched via soc6 | 865 |
| Matched via soc5 (fallback) | 28 more |
| Total matched | 893 |
| Unmatched | 1 (Fishing and Hunting Workers) |

### Output
Add `employment` and `median_wage` columns to the 894-occupation table.

---

## Step 4: Build Indeed Crosswalk (DR to Sector Mapping)

### Input
- The DR scores from Step 1
- `indeed_hiring_lab/job_postings_by_sector_us.csv`

### Process

1. Load the Indeed sector postings file. Columns: `date`, `jobcountry`, `indeed_job_postings_index`, `variable` (sector code), `display_name` (sector label).

2. Extract the list of Indeed sector names from the `display_name` column. There should be 44 unique sectors (plus an aggregate).

3. Build a keyword crosswalk: for each Indeed sector, match O*NET occupation titles using keyword overlap. The original implementation used keyword matching between Indeed sector names and O*NET occupation titles. This is the least reproducible step. The resulting crosswalk is saved at `indeed_soc_crosswalk.csv` with columns: `indeed_sector`, `soc_code`, `title`, `quadrant_onet`, `cf`, `vf`.

4. Compute sector-level DR as the mean of all matched occupations' DR scores within each sector.

### Checkpoints

| Check | Expected |
|-------|----------|
| Crosswalk rows | 367 |
| Unique Indeed sectors in crosswalk | 35 |
| Unique O*NET codes in crosswalk | 329 |
| Sector scores table rows | 35 |

### Output
- `indeed_soc_crosswalk.csv`: 367 rows mapping sectors to occupations
- `indeed_sector_scores.csv`: 35 rows with per-sector DR means

### Reproducibility Note
The keyword crosswalk is the hardest step to reproduce exactly. The crosswalk file is provided as a reproducibility artifact. If rebuilding from scratch, the key matching logic was: for each of Indeed's 44 sector display names, search for O*NET occupation titles containing relevant keywords from that sector name. Manual review excluded poor matches.

---

## Step 5: Indeed Validation (DR vs. Posting Change)

### Input
- Sector DR scores from Step 4
- `indeed_hiring_lab/job_postings_by_sector_us.csv`

### Process

1. Load Indeed sector postings. Filter to US (`jobcountry == 'US'`).

2. For each sector, compute:
   - `pre_ai_level`: mean posting index for Jan-Oct 2022
   - `current_level`: most recent posting index value
   - `ai_era_change`: `(current_level - pre_ai_level) / pre_ai_level`

3. Merge with sector DR scores from Step 4.

4. Exclude sectors with fewer than 2 matched O*NET occupations. This leaves 32 sectors.

5. Compute correlation between sector DR and `ai_era_change`.

### Checkpoints

| Check | Expected |
|-------|----------|
| Sectors after min-occupation filter | 32 |
| r(DR, ai_era_change) | 0.6509 |
| p-value | 0.0001 |

### Output
`indeed_option_a_results.csv`: 32 rows with columns `sector`, `cf`, `vf`, `n_occ`, `ai_era_change`, `current_level`, `pre_ai_level`.

---

## Step 6: Indeed Remote Work Validation

### Input
- Sector DR scores from Step 4
- `indeed_hiring_lab/remote_postings_sector.csv`

### Process

1. Load the remote postings file. Columns: `date`, `jobcountry`, `normtitlecategory_consistent` (sector), `remote_share_postings`.

2. Compute current remote share per sector (most recent date available).

3. Merge with sector DR scores. This yields 28 sectors with both DR and remote data.

4. Compute correlation between DR and `remote_current`.

### Checkpoints

| Check | Expected |
|-------|----------|
| Sectors with remote data | 28 |
| r(DR, remote_current) | -0.7044 |
| p-value | < 0.001 |

### Output
`indeed_option_c_results.csv`: 28 rows with columns `sector`, `cf`, `vf`, `remote_pre_covid`, `remote_current`, `remote_peak`, `remote_change`.

---

## Step 7: Timing Analysis (Pre/Post ChatGPT) — CONFOUNDED

### ⚠️ Important Context

This step was originally framed as a "natural experiment" using the ChatGPT launch date (Nov 30, 2022) as a clean break point. Subsequent analysis revealed this is **confounded by the 2022 tech sector cooling** driven by interest rate hikes. Low-DR desk-work sectors (Software Development, Data & Analytics) were already declining against their 2022 peaks before ChatGPT launched. The blog post has been updated to acknowledge this.

The checkpoint values below depend critically on two factors:
1. **Window choice**: Which months define "before" and "after." The only period with r ≈ 0 is late 2021 (Q4), during the transition between the COVID-era desk-work boom and the 2022 tech cooling. Using the first half of 2022 produces r ≈ 0.62.
2. **Crosswalk composition**: The original spec's crosswalk excluded 3 highly negative-DR sectors (Data & Analytics, IT Systems & Solutions, IT Infrastructure, Operations & Support) because Indeed renamed them after the sector-title examples file was created. Including these sectors amplifies all correlations.

### Input
- Sector DR scores from Step 4
- `indeed_hiring_lab/job_postings_by_sector_us.csv`

### Process

1. For each sector, compute posting change in a rolling window before and after ChatGPT launch (Nov 30, 2022).

2. Before ChatGPT: compute DR-posting correlation using changes measured entirely within the pre-ChatGPT period.

3. After ChatGPT: compute DR-posting correlation using changes from a pre-ChatGPT baseline to post-ChatGPT dates.

### Checkpoints

These values depend on window choice and crosswalk composition. The "original spec" column reflects the 35-sector crosswalk missing the 3 renamed tech sectors. The "full crosswalk" column includes all 44 sectors.

| Check | Original spec (35 sectors) | Full crosswalk (44 sectors) |
|-------|---------------------------|---------------------------|
| Pre-ChatGPT DR-posting correlation | r ≈ -0.01 | r ≈ 0.62 |
| Post-ChatGPT DR-posting correlation | r ≈ 0.62 | r ≈ 0.67 |

**Note**: The pre-ChatGPT discrepancy is expected and traceable. It is not a pipeline bug. The core Step 5 result (r = 0.65, DR vsfull AI-era posting change) is unaffected and remains the strongest finding. The blog post now frames the timing analysis as "consistent with but not proof of" an AI-specific mechanism.

---

## Step 8: Quadrant Timeseries

### Input
- Sector DR scores and crosswalk from Step 4
- `indeed_hiring_lab/job_postings_by_sector_us.csv`

### Process

1. Split sectors into 4 groups based on DR (above/below median). The original analysis used DR and VF to create 4 quadrants, but the current blog post simplifies to "Low DR group A/B" and "High DR group A/B". The labels in the data are `Already Exposed` (AE), `AI Disruption Zone` (ADZ), `Verification Shield` (VS), and `Doubly Protected` (DP). In the blog chart, AE and VS are the low-DR groups; ADZ and DP are the high-DR groups.

2. For each group, compute the mean posting index per month, indexed to Feb 2020 = 100.

### Checkpoints

| Check | Expected |
|-------|----------|
| Timeseries rows | 73 (months from Feb 2020 to Feb 2026) |
| Columns | `date`, `Already Exposed`, `AI Disruption Zone`, `Verification Shield`, `Doubly Protected` |
| Feb 2020 values | ~100 for all groups |
| Feb 2026 AE value | ~93.7 |
| Feb 2026 DP value | ~125.8 |

### Output
`indeed_quadrant_timeseries.csv`: 73 rows x 5 columns.

---

## Step 9: Backward Validation (Offshoring Era)

### Input
- DR scores from Step 1
- BLS OEWS panel data (2004-2024), harmonized to SOC 2018 codes

### Process

1. The OEWS panel (`kw_oews_panel.csv`) contains 3,581 rows across 21 years and ~173 occupations, already harmonized to SOC 2018 codes. Each row has `YEAR`, `OCC_CODE`, `TOT_EMP`, wages, and DR scores.

2. Compute employment growth during the offshoring era: for each occupation, calculate `(employment_2010 - employment_2004) / employment_2004`.

3. Regress offshoring-era employment growth on DR.

### Checkpoints

| Check | Expected |
|-------|----------|
| t-statistic for DR predicting offshoring-era growth | 2.12 |
| p-value | 0.036 |
| Direction | WRONG (low-DR grew MORE, not less) |

### Note
The backward validation fails. This is documented honestly in the blog post.

---

## Step 10: Assemble Blog Post Data

### Input
All outputs from Steps 1-9.

### Process

The blog post (`blog_post.html`) is a self-contained HTML file with inline Plotly.js charts. All chart data is embedded as JavaScript variables:

1. `scatterCF`: 32-element array from `indeed_option_a_results.csv`. Each element has `sector`, `cf`, `vf`, `ai_era_change`, `n_occ`.

2. `scatterRemote`: 28-element array from `indeed_option_c_results.csv`. Each element has `sector`, `cf`, `remote_current`.

3. `quadrantTS`: 73-element array from `indeed_quadrant_timeseries.csv`. Each element has `date`, `AE`, `ADZ`, `VS`, `DP`.

4. `anchorData`: 894-element array of all occupations with anchor scores. Each element has `title`, `score` (anchor_score to 4 decimal places), `emp`, `anchors` (count), `wage`, `group` (major occupation group). Sorted by score ascending.

### Verification

After assembling the blog post, verify these values appear in the embedded data:

| Variable | Check | Expected |
|----------|-------|----------|
| scatterCF | length | 32 |
| scatterCF | Data & Analytics cf | 0.337 |
| scatterCF | Therapy cf | 0.657 |
| scatterRemote | length | 28 |
| quadrantTS | length | 73 |
| quadrantTS | first date | 2020-02-29 |
| quadrantTS | last date | 2026-02-28 |
| anchorData | length | 894 |
| anchorData | count where score == 0 | 29 |
| anchorData | max score | 1.0 |
| anchorData | Software Developers score | 0.058 |
| anchorData | Web Developers score | 0.0 |
| anchorData | Elementary Teachers score | 0.7513 |
| anchorData | Electricians score | 0.8365 |

---

## File Manifest

### Raw Data (inputs)
```
code/data/raw/Work Context.xlsx                         O*NET Work Context (297,676 rows)
code/data/raw/indeed_hiring_lab/job_postings_by_sector_us.csv   Indeed sector postings
code/data/raw/indeed_hiring_lab/remote_postings_sector.csv      Indeed remote share
code/data/raw/oews_timeseries/oesm24nat/.../national_M2024_dl.xlsx  BLS OEWS 2024
```

### Intermediate Artifacts
```
indeed_soc_crosswalk.csv          367-row sector-to-occupation mapping
indeed_sector_scores.csv          35-row sector DR/VF means
indeed_option_a_results.csv       32-row DR vsposting change
indeed_option_c_results.csv       28-row DR vsremote share
indeed_quadrant_timeseries.csv    73-row monthly posting index by group
kw_oews_panel.csv                 3,581-row OEWS panel (2004-2024)
anchor_scores_corrected.csv       894-row occupation anchor scores
```

### Final Outputs
```
blog_post.html                    Self-contained interactive blog post
anchor_score_chart.html           Standalone anchor score visualization
blog_data_bundle/                 Reproducibility bundle (8 CSVs + README)
```

---

## Known Issues and Limitations

1. **Indeed crosswalk is hand-tuned.** The keyword matching between Indeed sectors and O*NET occupations involves judgment calls. The crosswalk file is provided as-is. Different keyword strategies would produce different sector DR scores and therefore different correlations.

2. **Employment sharing.** When multiple O*NET codes map to the same BLS SOC code, they share the same employment figure. Tier-level employment aggregates will overcount. Per-occupation employment figures are correct for display but not for summing.

3. **O*NET data vintage.** The Work Context data is from August 2023. O*NET updates items on a rolling basis, so scores for individual occupations may change in future releases.

4. **The OEWS panel harmonization** involved mapping pre-2018 SOC codes to 2018 codes. Eight occupations with many-to-one crosswalk discontinuities were excluded. This harmonization was done in a previous session and the panel file is provided as a pre-built artifact.
