"""Step 4: The tests. Employment-weighted group means, WLS regressions with robust SEs, figures.

Reads data/occupation_panel_2022_2025.csv. Writes results/*.csv, results/summary.json, figures/*.png.
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg"); matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt
from common import DATA, RESULTS, FIGURES

ALL_OCC_CHANGE_22_25 = 5.1  # all occupations, OEWS May 2022 -> May 2025 (147,886,000 -> 155,495,730)

def wmean(df, col):
    return float(np.average(df[col], weights=df.emp_2022))

def wls(df, y, xs, label):
    """Employment-weighted least squares with HC1 robust standard errors."""
    X = np.column_stack([np.ones(len(df))] + [df[x].values for x in xs]); Y = df[y].values
    W = np.sqrt(df.emp_2022.values); Xw, Yw = X * W[:, None], Y * W
    b = np.linalg.lstsq(Xw, Yw, rcond=None)[0]; e = Yw - Xw @ b; n, k = Xw.shape
    XtX = np.linalg.inv(Xw.T @ Xw); V = XtX @ ((Xw * e[:, None]).T @ (Xw * e[:, None])) @ XtX * n / (n - k)
    se = np.sqrt(np.diag(V)); r2 = 1 - (e ** 2).sum() / ((Yw - np.average(Y, weights=W ** 2) * W) ** 2).sum()
    return {"model": label, "y": y, **{f"b_{n}": round(float(v), 3) for n, v in zip(["const"] + xs, b)},
            **{f"se_{n}": round(float(v), 3) for n, v in zip(["const"] + xs, se)}, "r2": round(float(r2), 3), "n": n}

def write_map_svg(kw, cells, rm, pm, labels):
    """Compact hand-rolled SVG of the routine x Polanyi map for the web (matplotlib's SVG is ~10x larger)."""
    W, H, L, T, R, B = 720, 560, 50, 40, 20, 50
    sx = lambda x: L + (x + 2.8) / 6.0 * (W - L - R); sy = lambda y: T + (3.0 - y) / 5.7 * (H - T - B)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="system-ui, sans-serif" font-size="11">',
         f'<rect x="{sx(rm):.0f}" y="{sy(pm):.0f}" width="{sx(3.2)-sx(rm):.0f}" height="{sy(-2.7)-sy(pm):.0f}" fill="#e24b4a" fill-opacity="0.06"/>',
         f'<line x1="{sx(rm):.0f}" y1="{T}" x2="{sx(rm):.0f}" y2="{H-B}" stroke="#888780" stroke-dasharray="4 3"/>',
         f'<line x1="{L}" y1="{sy(pm):.0f}" x2="{W-R}" y2="{sy(pm):.0f}" stroke="#888780" stroke-dasharray="4 3"/>']
    for _, r in kw.sort_values("emp_2022", ascending=False).iterrows():
        c = "#e24b4a" if r.emp_change_pct_22_25 < 0 else "#378add"
        o.append(f'<circle cx="{sx(r.routine_R):.1f}" cy="{sy(r.polanyi_P):.1f}" r="{max(2.0, (r.emp_2022/6000)**0.5*0.75):.1f}" fill="{c}" fill-opacity="0.5" stroke="{c}" stroke-width="0.5"><title>{r.title}: {r.emp_change_pct_22_25:+.1f}%</title></circle>')
    for _, r in kw[kw.soc.isin(labels)].iterrows():
        t, (dx, dy) = labels[r.soc]
        o.append(f'<text x="{sx(r.routine_R)+dx*0.9:.0f}" y="{sy(r.polanyi_P)-dy*0.9:.0f}" fill="#2c2c2a">{t} {r.emp_change_pct_22_25:+.0f}%</text>')
    for cell, (x, y, col, anc) in {"routine / not embedded": (sx(rm)+8, H-B-8, "#a32d2d", "start"), "routine / embedded": (sx(rm)+8, T+14, "#185fa5", "start"),
                                   "non-routine / not embedded": (L+8, H-B-8, "#185fa5", "start"), "non-routine / embedded": (L+8, T+14, "#185fa5", "start")}.items():
        o.append(f'<text x="{x:.0f}" y="{y:.0f}" fill="{col}" font-weight="500">{cell.replace(" / ", ", ").capitalize()}: {cells.loc[cell, "emp_change_22_25"]:+.1f}% ({cells.loc[cell, "workers_M"]:.1f}M)</text>')
    o.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-8}" text-anchor="middle" fill="#5f5e5a">Routineness (R) → more routine</text>')
    o.append(f'<text x="14" y="{(T+H-B)/2:.0f}" text-anchor="middle" fill="#5f5e5a" transform="rotate(-90 14 {(T+H-B)/2:.0f})">Polanyi embedding (P) → more embedded</text>')
    o.append("</svg>")
    (FIGURES / "fig_routine_polanyi_map.svg").write_text("\n".join(o))

def write_cells_svg(cells, style):
    """Compact hand-rolled SVG of the four-cell index paths (May 2022 = 100)."""
    W, H, L, T, R, B = 640, 340, 56, 30, 20, 40
    series = {}
    for cell in style:
        c = cells.loc[cell]; idx = [100.0]
        for g in (c.chg_22_23, c.chg_23_24, c.chg_24_25): idx.append(idx[-1] * (1 + g / 100))
        series[cell] = idx
    lo = min(min(v) for v in series.values()) - 1; hi = max(max(v) for v in series.values()) + 1
    sx = lambda i: L + i / 3 * (W - L - R); sy = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    dash = {"-": "", "--": ' stroke-dasharray="7 3"', "-.": ' stroke-dasharray="12 3 2 3"', ":": ' stroke-dasharray="2 3"'}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="system-ui, sans-serif" font-size="11">']
    for v in range(int(lo) + 1, int(hi) + 1, 2):
        o.append(f'<line x1="{L}" y1="{sy(v):.1f}" x2="{W-R}" y2="{sy(v):.1f}" stroke="#e1e0d9" stroke-width="0.8"/><text x="{L-6}" y="{sy(v)+4:.1f}" text-anchor="end" fill="#898781">{v}</text>')
    o.append(f'<line x1="{L}" y1="{sy(100):.1f}" x2="{W-R}" y2="{sy(100):.1f}" stroke="#c3c2b7"/>')
    for i, lab in enumerate(["May 2022", "May 2023", "May 2024", "May 2025"]):
        o.append(f'<text x="{sx(i):.0f}" y="{H-B+16}" text-anchor="middle" fill="#898781">{lab}</text>')
    for k, (cell, (col, ls)) in enumerate(style.items()):
        pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(series[cell]))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"{dash[ls]}/>')
        o += [f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="3" fill="{col}"/>' for i, v in enumerate(series[cell])]
        y = T + 12 + k * 15
        o.append(f'<line x1="{L+8}" y1="{y-4}" x2="{L+30}" y2="{y-4}" stroke="{col}" stroke-width="2"{dash[ls]}/><text x="{L+36}" y="{y}" fill="#52514e">{cell} ({cells.loc[cell, "workers_M"]:.0f}M)</text>')
    o.append(f'<text x="14" y="{(T+H-B)/2:.0f}" text-anchor="middle" fill="#5f5e5a" transform="rotate(-90 14 {(T+H-B)/2:.0f})">Employment index, May 2022 = 100</text>')
    o.append("</svg>")
    (FIGURES / "fig_four_cells_by_year.svg").write_text("\n".join(o))

if __name__ == "__main__":
    kw = pd.read_csv(DATA / "occupation_panel_2022_2025.csv")
    kw["RxP"] = kw.routine_R * kw.polanyi_P
    summary = {"n_occupations": len(kw), "workers_2022_M": round(kw.emp_2022.sum() / 1e6, 1),
               "sample_change_22_25": round(wmean(kw, "emp_change_pct_22_25"), 2)}

    # KWDM quadrants
    q = kw.groupby("kwdm_quadrant").apply(lambda g: pd.Series({"n": len(g), "workers_M": g.emp_2022.sum() / 1e6,
        "emp_change_22_25": wmean(g, "emp_change_pct_22_25"), "wage_change_22_25": wmean(g.dropna(subset=["wage_change_pct_22_25"]), "wage_change_pct_22_25")}))
    q.round(2).to_csv(RESULTS / "kwdm_quadrants.csv"); summary["quadrants"] = q.emp_change_22_25.round(2).to_dict()

    # Routine x Polanyi 2x2
    rm, pm = kw.routine_R.median(), kw.polanyi_P.median()
    kw["cell"] = np.where(kw.routine_R >= rm, "routine", "non-routine") + " / " + np.where(kw.polanyi_P >= pm, "embedded", "not embedded")
    cells = kw.groupby("cell").apply(lambda g: pd.Series({"n": len(g), "workers_M": g.emp_2022.sum() / 1e6,
        "emp_change_22_25": wmean(g, "emp_change_pct_22_25"), "chg_22_23": wmean(g, "emp_change_pct_22_23"),
        "chg_23_24": wmean(g, "emp_change_pct_23_24"), "chg_24_25": wmean(g, "emp_change_pct_24_25"),
        "wage_change_22_25": wmean(g.dropna(subset=["wage_change_pct_22_25"]), "wage_change_pct_22_25")}))
    cells.round(2).to_csv(RESULTS / "routine_x_polanyi_cells.csv"); summary["cells"] = cells.emp_change_22_25.round(2).to_dict()

    # Terciles
    terc = {}
    for col in ["aioe", "polanyi_P", "intelligence_I", "routine_R"]:
        d = kw.dropna(subset=[col]); lo, hi = d[col].quantile([1/3, 2/3])
        terc[col] = {"low": round(wmean(d[d[col] <= lo], "emp_change_pct_22_25"), 2),
                     "mid": round(wmean(d[(d[col] > lo) & (d[col] < hi)], "emp_change_pct_22_25"), 2),
                     "high": round(wmean(d[d[col] >= hi], "emp_change_pct_22_25"), 2)}
    summary["terciles"] = terc

    # Regressions
    a = kw.dropna(subset=["aioe"])
    regs = [wls(a, "emp_change_pct_22_25", ["aioe"], "AIOE only"),
            wls(kw, "emp_change_pct_22_25", ["F_comm", "F_verif"], "KWDM frictions"),
            wls(a, "emp_change_pct_22_25", ["aioe", "F_comm", "F_verif"], "AIOE + KWDM"),
            wls(kw, "emp_change_pct_22_25", ["polanyi_P", "intelligence_I"], "Two-factor"),
            wls(kw, "emp_change_pct_22_25", ["routine_R"], "Routine only"),
            wls(kw, "emp_change_pct_22_25", ["routine_R", "polanyi_P", "RxP", "intelligence_I"], "Three-factor + interaction"),
            wls(a, "emp_change_pct_22_25", ["routine_R", "polanyi_P", "RxP", "intelligence_I", "aioe"], "Three-factor + AIOE"),
            wls(kw, "emp_change_pct_22_25", ["F_comm", "F_verif", "routine_R", "polanyi_P", "RxP", "intelligence_I"], "KWDM + three-factor")]
    for per in ["22_23", "23_24", "24_25"]:
        regs.append(wls(kw, f"emp_change_pct_{per}", ["routine_R", "polanyi_P", "RxP", "intelligence_I"], f"Three-factor, {per}"))
    w = kw.dropna(subset=["wage_change_pct_22_25"]).copy(); w["ln_wage_2022"] = np.log(w.median_wage_2022)
    for qq in ["II", "III", "IV"]: w[f"Q{qq}"] = (w.kwdm_quadrant == qq).astype(float)
    regs.append(wls(w, "wage_change_pct_22_25", ["QII", "QIII", "QIV", "ln_wage_2022"], "Wage: quadrants"))
    regs.append(wls(w, "wage_change_pct_22_25", ["polanyi_P", "intelligence_I", "ln_wage_2022"], "Wage: two-factor"))
    pd.DataFrame(regs).to_csv(RESULTS / "regressions.csv", index=False)
    summary["regressions"] = {r["model"]: {k: v for k, v in r.items() if k.startswith(("b_", "se_", "r2"))} for r in regs}

    summary["biggest_losers"] = kw.assign(d=kw.emp_2025 - kw.emp_2022).nsmallest(8, "d")[["soc", "title", "d"]].to_dict("records")
    summary["biggest_gainers"] = kw.assign(d=kw.emp_2025 - kw.emp_2022).nlargest(8, "d")[["soc", "title", "d"]].to_dict("records")
    json.dump(summary, open(RESULTS / "summary.json", "w"), indent=1, default=float)

    print(f"sample: {len(kw)} occupations, {summary['workers_2022_M']}M workers, change {summary['sample_change_22_25']:+.1f}% (all occ +{ALL_OCC_CHANGE_22_25})")
    print("KWDM quadrants:", summary["quadrants"]); print("R x P cells:", summary["cells"])
    print("terciles:", terc)
    for r in regs: print(f"  {r['model']:28s} " + "  ".join(f"{k[2:]}={r[k]:+.2f}({r['se_'+k[2:]]:.2f})" for k in r if k.startswith("b_") and k != "b_const") + f"  R2={r['r2']}")

    # Figures
    fig, ax = plt.subplots(figsize=(9, 7), dpi=150)
    ax.axvspan(rm, 3.2, ymin=0, ymax=(pm + 2.7) / 5.7, color="#e24b4a", alpha=0.06, lw=0)
    for _, r in kw.iterrows():
        c = "#e24b4a" if r.emp_change_pct_22_25 < 0 else "#378add"
        ax.scatter(r.routine_R, r.polanyi_P, s=max(12, r.emp_2022 / 6000), color=c, alpha=0.5, edgecolors=c, linewidths=0.4)
    ax.axvline(rm, color="#888780", ls="--", lw=0.8); ax.axhline(pm, color="#888780", ls="--", lw=0.8)
    labels = {"43-3031": ("Bookkeepers", (-70, -14)), "43-6014": ("Secretaries", (-90, 8)), "43-6013": ("Medical secretaries", (6, 6)),
              "43-9061": ("Office clerks", (6, 2)), "11-1021": ("Managers", (8, 2)), "15-1252": ("Software developers", (6, -12)),
              "15-1251": ("Programmers", (4, -16)), "43-3011": ("Collectors", (-60, 8)), "23-1011": ("Lawyers", (8, -6)),
              "15-2051": ("Data scientists", (6, 4)), "13-1111": ("Mgmt analysts", (6, 2)), "43-9021": ("Data entry", (6, -10))}
    for _, r in kw[kw.soc.isin(labels)].iterrows():
        t, off = labels[r.soc]; ax.annotate(f"{t} {r.emp_change_pct_22_25:+.0f}%", (r.routine_R, r.polanyi_P), fontsize=8, xytext=off, textcoords="offset points", color="#2c2c2a")
    ax.set_xlim(-2.8, 3.2); ax.set_ylim(-2.7, 3.0)
    ax.set_xlabel("Routineness (R)  →  more routine"); ax.set_ylabel("Polanyi embedding (P)  →  more embedded")
    for cell, (x, y, col) in {"routine / not embedded": (rm + 0.15, -2.55, "#a32d2d"), "routine / embedded": (rm + 0.15, 2.75, "#185fa5"),
                              "non-routine / not embedded": (-2.7, -2.55, "#185fa5"), "non-routine / embedded": (-2.7, 2.75, "#185fa5")}.items():
        ax.text(x, y, f"{cell.replace(' / ', ', ').capitalize()}: {cells.loc[cell, 'emp_change_22_25']:+.1f}%  ({cells.loc[cell, 'workers_M']:.1f}M)", fontsize=9, color=col)
    ax.set_title(f"{len(kw)} knowledge-work occupations, employment change May 2022 → May 2025\nred = shrank, blue = grew, bubble = 2022 employment", fontsize=11)
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig(FIGURES / "fig_routine_polanyi_map.png")
    write_map_svg(kw, cells, rm, pm, labels)

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    style = {"routine / not embedded": ("#e24b4a", "-"), "routine / embedded": ("#378add", "--"), "non-routine / not embedded": ("#1baf7a", "-."), "non-routine / embedded": ("#6250d6", ":")}
    for cell, (col, ls) in style.items():
        c = cells.loc[cell]; idx = [100, 100 * (1 + c.chg_22_23 / 100)]
        idx.append(idx[-1] * (1 + c.chg_23_24 / 100)); idx.append(idx[-1] * (1 + c.chg_24_25 / 100))
        ax.plot(["May 2022", "May 2023", "May 2024", "May 2025"], idx, color=col, ls=ls, lw=2, marker="o", ms=4, label=f"{cell} ({c.workers_M:.0f}M)")
    ax.axhline(100, color="#c3c2b7", lw=0.8); ax.set_ylabel("Employment index, May 2022 = 100"); ax.legend(fontsize=8, frameon=False)
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    ax.set_title("Same four cells, year by year (employment-weighted)", fontsize=11); plt.tight_layout(); plt.savefig(FIGURES / "fig_four_cells_by_year.png")
    write_cells_svg(cells, style)
    print("figures written")
