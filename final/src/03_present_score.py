"""
Step 3 · Present score
Team 27 · Utility-scale energy storage · client Enel

What it does
    1. reads the sector's patent families (Step 0 output, one column `docdb_family_id`)
    2. fetches from PATSTAT: applications, CPC codes, applicants, forward citations
    3. keeps the scoring window and the firms with the most families
    4. computes four indicators per firm: volume, influence, success, globalization
    5. combines them into one present score (y-axis of the Magic Quadrant: ability to execute, Step 5)
    6. checks how much the ranking depends on the weights

Input   data/families.csv (Step 0): column `docdb_family_id`
        outputs/tables/firms_to_score.csv (Step 2): column `firm`, the companies to score;
        while it does not exist, the script scores the firms with the most families
        config/sector.yaml: every parameter (sections patstat, present_score, competition)
Output  outputs/tables/present_scores.csv             one row per scored firm
        outputs/tables/present_scores_robustness.csv  rank of each firm under other weights

Runs on TIP (needs `epo.tipdata`). Method follows tutorial_4/40_present_value_score.ipynb.
Firm names: psn_name -> firm with harmonize_firms.py (rules and justification: docs/harmonize_firms.md).

    python src/03_present_score.py                    # parameters from config/sector.yaml
    python src/03_present_score.py --window 2012 2018 --log-volume   # one-off experiment, config unchanged
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from common import CONFIG_PATH, load_config
from harmonize_firms import firm_of          # psn_name -> firm (same folder; needs `pip install cleanco`)

INDICATORS = ["volume", "influence", "success", "globalization"]
ROOT = CONFIG_PATH.parents[1]                # final/: the paths in the config are relative to it


# --------------------------------------------------------------------------- configuration
def build_config(path: str | Path = CONFIG_PATH) -> dict:
    """The parameters of this step, read from config/sector.yaml (every value is justified in the appendix)."""
    y = load_config(path)
    p, comp = y["present_score"], y["competition"]
    offices = p["success_offices"]
    return dict(
        input_csv=ROOT / y["families_csv"],
        output_csv=ROOT / p["output_csv"],
        firms_csv=ROOT / p["firms_csv"] if p.get("firms_csv") else None,
        env=y["patstat"]["env"],
        chunk=y["patstat"]["chunk"],
        window=tuple(p["window"]),
        last_citation_year=p["last_citation_year"],
        citation_window=p["citation_window"],
        min_cohort=p["min_cohort"],
        keep_ipr=tuple(p["keep_ipr"]) if p["keep_ipr"] else None,
        ep_only=p["ep_only"],
        success_offices=tuple(offices) if offices else None,
        n_firms=comp["n_firms_to_score"],
        min_families=comp["min_families"],
        log_volume=p["log_volume"],
        weights=p["weights"],
        method=p["method"],
    )


CONFIG = build_config()


# --------------------------------------------------------------------------- 1. input
def load_family_ids(path: str | Path) -> list[int]:
    """The sector's DOCDB families, from the Step 0 file."""
    df = pd.read_csv(path)
    if "source" in df.columns:
        print("Input families by source:", df.source.value_counts().to_dict())
    ids = df.docdb_family_id.dropna().astype(int).unique().tolist()
    print(f"{len(ids):,} families read from {path}")
    return ids


# --------------------------------------------------------------------------- 2. PATSTAT
def _chunks(values, size=CONFIG["chunk"]):
    values = [int(v) for v in values]
    for i in range(0, len(values), size):
        yield values[i:i + size]


def fetch_from_patstat(family_ids: list[int], env: str):
    """Four raw tables: applications, CPC codes, applicants, family-to-family citations."""
    from sqlalchemy import func
    from epo.tipdata.patstat import PatstatClient
    from epo.tipdata.patstat.database.models import (
        TLS201_APPLN, TLS206_PERSON, TLS207_PERS_APPLN, TLS224_APPLN_CPC, TLS228_DOCDB_FAM_CITN,
    )

    patstat = PatstatClient(env=env)
    db = patstat.orm()
    try:
        return _fetch(patstat, db, func, family_ids, env, TLS201_APPLN, TLS206_PERSON, TLS207_PERS_APPLN,
                      TLS224_APPLN_CPC, TLS228_DOCDB_FAM_CITN)
    finally:
        try:
            patstat.close_session()          # close now, avoids the harmless error printed at exit
        except Exception:
            pass


def _fetch(patstat, db, func, family_ids, env, TLS201_APPLN, TLS206_PERSON, TLS207_PERS_APPLN,
           TLS224_APPLN_CPC, TLS228_DOCDB_FAM_CITN):
    def run(make_query, ids):
        parts = [patstat.df(make_query(chunk)) for chunk in _chunks(ids)]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    # applications of the sector families
    apps = run(lambda c: db.query(
        TLS201_APPLN.appln_id, TLS201_APPLN.docdb_family_id, TLS201_APPLN.appln_auth,
        TLS201_APPLN.appln_kind, TLS201_APPLN.ipr_type, TLS201_APPLN.granted,
        TLS201_APPLN.earliest_filing_year, TLS201_APPLN.earliest_publn_year,
    ).filter(TLS201_APPLN.docdb_family_id.in_(c)), family_ids)
    apps = apps[apps.appln_id < 900_000_000]                    # drop PATSTAT dummy applications
    appln_ids = apps.appln_id.unique()

    # CPC codes, blanks removed
    cpc = run(lambda c: db.query(
        TLS224_APPLN_CPC.appln_id,
        func.replace(TLS224_APPLN_CPC.cpc_class_symbol, " ", "").label("cpc"),
    ).filter(TLS224_APPLN_CPC.appln_id.in_(c)), appln_ids)

    # applicants (applt_seq_nr > 0), with standardised name and sector
    owners = run(lambda c: db.query(
        TLS207_PERS_APPLN.appln_id, TLS206_PERSON.psn_name, TLS206_PERSON.psn_sector,
        TLS206_PERSON.han_name,
    ).join(TLS206_PERSON, TLS206_PERSON.person_id == TLS207_PERS_APPLN.person_id)
     .filter(TLS207_PERS_APPLN.applt_seq_nr > 0)
     .filter(TLS207_PERS_APPLN.appln_id.in_(c)), appln_ids)

    # forward citations between families, and the first publication year of each citing family
    cites = run(lambda c: db.query(
        TLS228_DOCDB_FAM_CITN.docdb_family_id.label("citing_family"),
        TLS228_DOCDB_FAM_CITN.cited_docdb_family_id.label("cited_family"),
    ).filter(TLS228_DOCDB_FAM_CITN.cited_docdb_family_id.in_(c)), family_ids)
    if len(cites):
        years = run(lambda c: db.query(
            TLS201_APPLN.docdb_family_id.label("citing_family"),
            func.min(TLS201_APPLN.earliest_publn_year).label("citing_year"),
        ).filter(TLS201_APPLN.docdb_family_id.in_(c))
         .filter(TLS201_APPLN.earliest_publn_year < 9999)
         .group_by(TLS201_APPLN.docdb_family_id), cites.citing_family.unique())
        cites = cites.merge(years, on="citing_family", how="left")

    print(f"PATSTAT ({env}): {len(apps):,} applications, {len(cpc):,} CPC rows, "
          f"{len(owners):,} applicant links, {len(cites):,} citing-cited pairs")
    return apps, cpc, owners, cites


# --------------------------------------------------------------------------- 3. families and firms
def build_families(apps: pd.DataFrame, cpc: pd.DataFrame) -> pd.DataFrame:
    """One row per family: priority year, first publication year, main CPC subclass."""
    fam = (apps.groupby("docdb_family_id")
               .agg(priority_year=("earliest_filing_year", "min"),
                    first_publn_year=("earliest_publn_year", "min")))
    fam.loc[fam.first_publn_year >= 9999, "first_publn_year"] = np.nan   # 9999 = unknown

    # technology area: most frequent CPC subclass, ignoring the Y tags (Y02E is on almost every family)
    c = cpc.merge(apps[["appln_id", "docdb_family_id"]], on="appln_id")
    c = c[~c.cpc.str.startswith("Y")].assign(cpc4=lambda d: d.cpc.str[:4])
    fam["cpc4"] = c.groupby("docdb_family_id").cpc4.agg(lambda s: s.mode().iat[0])
    fam["cpc4"] = fam.cpc4.fillna("NONE")
    return fam


def describe_sample(apps: pd.DataFrame, fam: pd.DataFrame) -> None:
    """Prints what the sector looks like over time, to choose the window and the success offices."""
    years = fam.priority_year.where(fam.priority_year < 9999)
    print("\nFamilies per priority year:")
    print(years.value_counts().sort_index().astype(int).to_string())
    offices = apps.groupby("docdb_family_id").appln_auth.agg(set)
    print(f"Families with an EP application: {offices.map(lambda s: 'EP' in s).mean():.0%} · "
          f"only filed in CN: {offices.map(lambda s: s == {'CN'}).mean():.0%}")
    print("Most frequent offices (applications):", apps.appln_auth.value_counts().head(6).to_dict(), "\n")


def select_firms(n_families: pd.Series, cfg=CONFIG) -> list[str]:
    """The firms to score: the given list (Step 2), or the largest portfolios."""
    firms_csv = cfg.get("firms_csv")
    if firms_csv and not Path(firms_csv).exists():
        print(f"No shortlist yet ({firms_csv}, Step 2): scoring the {cfg['n_firms']} largest portfolios")
        firms_csv = None
    if firms_csv:
        raw = pd.read_csv(firms_csv).firm.astype(str).str.strip()
        wanted = list(dict.fromkeys(firm_of(n) for n in raw))       # a psn_name or a firm label both work
        missing = [f for f in wanted if f not in n_families.index]
        if missing:
            print("Not found in the window (check spelling or the rules in harmonize_firms.py):", missing)
        small = [f for f in wanted if f in n_families.index and n_families[f] < cfg["min_families"]]
        if small:
            print(f"Fewer than {cfg['min_families']} families, rates will be noisy:", small)
        top = [f for f in wanted if f in n_families.index]
    else:
        top = list(n_families[n_families >= cfg["min_families"]].head(cfg["n_firms"]).index)
    if not top:
        raise ValueError("No firm to score: check firms_csv, or lower min_families / widen the window.")
    return top


def normalise_citations(fam: pd.DataFrame, min_cohort: int) -> pd.Series:
    """Citations / mean of the same priority year x CPC subclass (1 = average). Small cohorts use the year mean."""
    cohort = fam.groupby(["priority_year", "cpc4"]).fwd
    mean_cohort, size = cohort.transform("mean"), cohort.transform("count")
    mean_year = fam.groupby("priority_year").fwd.transform("mean")
    denom = mean_cohort.where(size >= min_cohort, mean_year)
    return (fam.fwd / denom).where(denom > 0, 0.0).where(fam.fwd.notna())


# --------------------------------------------------------------------------- 4. indicators
def compute_indicators(apps, cpc, owners, cites, cfg=CONFIG) -> pd.DataFrame:
    """One row per scored firm with the four indicators (raw values)."""
    apps = apps.copy()
    for col in ["appln_auth", "appln_kind", "ipr_type", "granted"]:
        apps[col] = apps[col].astype(str).str.strip()
    if cfg["keep_ipr"]:
        apps = apps[apps.ipr_type.isin(cfg["keep_ipr"])]
    if cfg["ep_only"]:
        apps = apps[apps.docdb_family_id.isin(apps.loc[apps.appln_auth == "EP", "docdb_family_id"])]

    # sample: families in the window
    fam = build_families(apps, cpc)
    describe_sample(apps, fam)
    lo, hi = cfg["window"]
    fam = fam[fam.priority_year.between(lo, hi)].copy()
    apps = apps[apps.docdb_family_id.isin(fam.index)]
    print(f"Window {lo}-{hi}: {len(fam):,} families, {len(apps):,} applications")

    # owners: companies only, one name per firm, full counting of co-owned families
    own = owners.merge(apps[["appln_id", "docdb_family_id"]], on="appln_id")
    own = own[own.psn_sector.fillna("").str.contains("COMPANY")].copy()
    own["psn_name"] = own.psn_name.str.strip()
    own["firm"] = own.psn_name.map(firm_of)
    own["han_name"] = own.han_name.fillna("").str.strip()
    n_names = own.groupby("firm").psn_name.nunique()
    merged = (own[own.firm.map(n_names) > 1]
              .groupby(["firm", "psn_name", "han_name"]).docdb_family_id.nunique())
    if len(merged):
        print("Names merged into a firm (check them, full list: outputs/tables/firm_map.csv):\n" + merged.to_string())
    fam_firm = own[["docdb_family_id", "firm"]].drop_duplicates()

    n_families = fam_firm.groupby("firm").docdb_family_id.nunique().sort_values(ascending=False)
    top = select_firms(n_families, cfg)
    fam_top = fam_firm[fam_firm.firm.isin(top)]

    # influence: forward citations within N years, relative to the same year x CPC subclass
    w = cfg["citation_window"]
    counts = pd.Series(dtype=float)
    if len(cites):
        c = cites.dropna(subset=["citing_year"])
        c = c[c.citing_family != c.cited_family]
        c = c.assign(lag=c.citing_year - c.cited_family.map(fam.first_publn_year))
        counts = c[c.lag.between(0, w)].groupby("cited_family").citing_family.nunique()
    complete = fam.first_publn_year + w <= cfg["last_citation_year"]       # full window observed
    fam["fwd"] = fam.index.to_series().map(counts).fillna(0).where(complete)
    fam["influence"] = normalise_citations(fam, cfg["min_cohort"])

    # national applications: no PCT requests (WO), no translations of EP patents (kind T)
    national = apps[(apps.appln_auth != "WO") & (~apps.appln_kind.str.startswith("T"))]

    # globalization: distinct offices per family
    fam["offices"] = national.groupby("docdb_family_id").appln_auth.nunique()
    fam["offices"] = fam.offices.fillna(1)

    # success: granted / filed, on the offices chosen in the config
    judged = national if cfg["success_offices"] is None else \
        national[national.appln_auth.isin(cfg["success_offices"])]
    judged = judged.merge(fam_top, on="docdb_family_id")

    per_fam = fam_top.merge(fam[["influence", "offices"]], left_on="docdb_family_id", right_index=True)
    firms = pd.DataFrame(index=pd.Index(top, name="firm"))
    firms["families"] = n_families.reindex(top)
    firms["volume"] = firms.families / len(fam)
    firms["influence"] = per_fam.groupby("firm").influence.mean()
    firms["success"] = judged.groupby("firm").granted.apply(lambda s: (s == "Y").mean())
    firms["success_n_apps"] = judged.groupby("firm").size()              # how many decisions it rests on
    firms["globalization"] = per_fam.groupby("firm").offices.mean()
    return firms


# --------------------------------------------------------------------------- 5. one score
def combine(table: pd.DataFrame, weights: dict, method: str) -> pd.Series:
    """One score per firm. 'mean': 100 = average firm. 'rrf': 100 = first on every indicator."""
    w = pd.Series(weights, dtype=float)
    w = w / w.sum()
    t = table[w.index]
    t = t.fillna(t.mean())                     # missing indicator -> average firm (neutral)
    if method == "mean":
        return 100 * (t / t.mean() * w).sum(axis=1)
    if method == "rrf":
        c = len(t)
        pos = t.rank(ascending=False, method="min")
        return 100 * (w * (c + 1) / (c + pos)).sum(axis=1)
    raise ValueError("method must be 'mean' or 'rrf'")


def for_scoring(firms: pd.DataFrame, cfg=CONFIG) -> pd.DataFrame:
    """The indicator table that enters the score (volume as log of families if log_volume)."""
    table = firms[INDICATORS].copy()
    if cfg.get("log_volume"):
        table["volume"] = np.log1p(firms["families"])
    return table


def robustness(firms: pd.DataFrame, cfg=CONFIG) -> pd.DataFrame:
    """Rank of each firm under other weights; prints the Spearman correlation with ours."""
    schemes = {"ours": cfg["weights"], "equal": {k: 1 for k in INDICATORS}}
    for k in INDICATORS:
        schemes[f"without {k}"] = {j: 1 for j in INDICATORS if j != k}
    table = for_scoring(firms, cfg)
    ranks = pd.DataFrame({name: combine(table, w, cfg["method"]).rank(ascending=False, method="min")
                          for name, w in schemes.items()}).astype(int)
    print("Spearman correlation with our ranking (1 = same order):")
    print(ranks.corr(method="spearman")["ours"].drop("ours").round(2).to_string())
    return ranks


def score(firms: pd.DataFrame, cfg=CONFIG) -> pd.DataFrame:
    firms = firms.copy()
    firms["score"] = combine(for_scoring(firms, cfg), cfg["weights"], cfg["method"])
    firms["rank"] = firms.score.rank(ascending=False, method="min").astype(int)
    return firms.sort_values("rank")


# --------------------------------------------------------------------------- main
def main(cfg=CONFIG):
    family_ids = load_family_ids(cfg["input_csv"])
    apps, cpc, owners, cites = fetch_from_patstat(family_ids, cfg["env"])
    firms = score(compute_indicators(apps, cpc, owners, cites, cfg), cfg)

    out = Path(cfg["output_csv"])
    out.parent.mkdir(parents=True, exist_ok=True)
    firms.round(4).to_csv(out)
    robustness(firms, cfg).to_csv(out.with_name(out.stem + "_robustness.csv"))

    print(f"\nPresent score ({cfg['method']}), saved to {out}:")
    print(firms.round(3).to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 3 · present score of the sector's firms. "
                                     "Parameters come from config/sector.yaml; the options below override them once.")
    parser.add_argument("--config", default=CONFIG_PATH, help="YAML configuration (default: config/sector.yaml)")
    parser.add_argument("--input", help="CSV with a docdb_family_id column")
    parser.add_argument("--firms", help="CSV with a firm column (Step 2 shortlist)")
    parser.add_argument("--env", choices=["TEST", "PROD"])
    parser.add_argument("--window", nargs=2, type=int, metavar=("FROM", "TO"))
    parser.add_argument("--success-offices", help="comma-separated offices, or 'all'")
    parser.add_argument("--method", choices=["mean", "rrf"])
    parser.add_argument("--citation-window", type=int,
                        help="years of forward citations counted (shorter = recent families can be scored)")
    parser.add_argument("--min-families", type=int)
    parser.add_argument("--log-volume", action="store_true", help="volume enters the score as log(families)")
    args = parser.parse_args()

    cfg = build_config(args.config)
    overrides = {"input_csv": args.input, "firms_csv": args.firms, "env": args.env, "method": args.method,
                 "window": tuple(args.window) if args.window else None, "min_families": args.min_families,
                 "citation_window": args.citation_window, "log_volume": True if args.log_volume else None}
    cfg.update({k: v for k, v in overrides.items() if v is not None})
    if args.success_offices:
        cfg["success_offices"] = None if args.success_offices == "all" else tuple(args.success_offices.split(","))
    main(cfg)
