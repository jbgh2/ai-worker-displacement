# Covid Was the Rehearsal. AI Is the Show.

An analysis of 894 US occupations measuring which jobs AI will displace, using a framework called Delegation Resistance built from O*NET Work Context data and validated against 4.4 million Indeed job postings.

**[Read the blog post](https://jbgh2.github.io/ai-worker-displacement/)**

## Repository Structure

```
docs/               GitHub Pages site
  index.html        The blog post (self-contained, interactive charts)
  anchor_score_chart.html   Standalone anchor score visualization

data/
  raw/              Source data files
    Work Context.xlsx                   O*NET 28.1 Work Context survey
    indeed_hiring_lab/                  Indeed Hiring Lab public data
    oews/national_M2024_dl.xlsx         BLS OEWS May 2024
  anchor_scores_corrected.csv           894 occupations with anchor scores

PIPELINE_SPEC.md    Step-by-step reproduction instructions with checkpoints
```

## Data Sources

- **O*NET 28.1**: [O*NET Resource Center](https://www.onetcenter.org/database.html) — Work Context survey data
- **Indeed Hiring Lab**: [hiringlab.indeed.com/data](https://hiringlab.indeed.com/data/) — Job posting indices by sector
- **BLS OEWS**: [bls.gov/oes/tables.htm](https://www.bls.gov/oes/tables.htm) — May 2024 national employment estimates
