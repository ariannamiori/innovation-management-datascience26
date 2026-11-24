"""
Export the applicant names of the sector, to build the firm harmonisation
Team 27 · Utility-scale energy storage · client Enel

What it does
    1. reads the sector's patent families (Step 0 output, one column `docdb_family_id`)
    2. fetches from PATSTAT every applicant (applt_seq_nr > 0) of those families,
       with the three name versions PATSTAT offers:
           psn_name      EEE-PPAT standardised name   (what 03_present_score.py groups on)
           han_name      OECD HAN harmonised name     (already merges some spellings)
           doc_std_name  DOCDB standardised name
    3. writes one row per distinct name combination, with how many families it holds,
       so the biggest names (the ones that matter for the ranking) come first

Output  outputs/tables/firm_names.csv
        columns: psn_id, psn_name, han_id, han_name, doc_std_name_id, doc_std_name, psn_sector,
                 countries, n_person_ids, applications, families, families_in_window,
                 first_priority_year, last_priority_year

Runs on TIP (needs `epo.tipdata`).

    python src/export_firm_names.py                   # from final/, family list in data/families.csv
    python src/export_firm_names.py --all-sectors     # also individuals, universities, ...
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

CONFIG = dict(
    input_csv="data/families.csv",                # Step 0 output
    output_csv="outputs/tables/firm_names.csv",
    env="PROD",
    window=(2010, 2018),           # same scoring window as 03_present_score.py
    companies_only=True,           # same filter as the scoring: psn_sector contains COMPANY
)
CHUNK = 5000                       # ids per IN (...) query
NAME_COLS = ["psn_id", "psn_name", "han_id", "han_name", "doc_std_name_id", "doc_std_name", "psn_sector"]


def _chunks(values, size=CHUNK):
    values = [int(v) for v in values]
    for i in range(0, len(values), size):
        yield values[i:i + size]


def fetch_applicants(family_ids: list[int], env: str) -> pd.DataFrame:
    """One row per application x applicant, with all name versions and the priority year."""
    from epo.tipdata.patstat import PatstatClient
    from epo.tipdata.patstat.database.models import TLS201_APPLN, TLS206_PERSON, TLS207_PERS_APPLN

    patstat = PatstatClient(env=env)
    db = patstat.orm()

    def run(make_query, ids):
        parts = [patstat.df(make_query(chunk)) for chunk in _chunks(ids)]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    try:
        apps = run(lambda c: db.query(
            TLS201_APPLN.appln_id, TLS201_APPLN.docdb_family_id, TLS201_APPLN.earliest_filing_year,
        ).filter(TLS201_APPLN.docdb_family_id.in_(c)), family_ids)
        apps = apps[apps.appln_id < 900_000_000]                # drop PATSTAT dummy applications

        people = run(lambda c: db.query(
            TLS207_PERS_APPLN.appln_id, TLS206_PERSON.person_id, TLS206_PERSON.person_ctry_code,
            TLS206_PERSON.psn_id, TLS206_PERSON.psn_name, TLS206_PERSON.psn_sector,
            TLS206_PERSON.han_id, TLS206_PERSON.han_name,
            TLS206_PERSON.doc_std_name_id, TLS206_PERSON.doc_std_name,
        ).join(TLS206_PERSON, TLS206_PERSON.person_id == TLS207_PERS_APPLN.person_id)
         .filter(TLS207_PERS_APPLN.applt_seq_nr > 0)
         .filter(TLS207_PERS_APPLN.appln_id.in_(c)), apps.appln_id.unique())
    finally:
        try:
            patstat.close_session()
        except Exception:
            pass

    print(f"PATSTAT ({env}): {len(apps):,} applications, {len(people):,} applicant links")
    return people.merge(apps, on="appln_id")


def name_table(df: pd.DataFrame, cfg=CONFIG) -> pd.DataFrame:
    """One row per distinct name combination, biggest portfolios first."""
    df = df.copy()
    for col in ["psn_name", "han_name", "doc_std_name", "psn_sector", "person_ctry_code"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    for col in ["psn_id", "han_id", "doc_std_name_id"]:
        df[col] = df[col].fillna(-1).astype(int)              # -1 = no id
    if cfg["companies_only"]:
        df = df[df.psn_sector.str.contains("COMPANY")]

    year = df.earliest_filing_year.where(df.earliest_filing_year < 9999)
    lo, hi = cfg["window"]
    df = df.assign(year=year, fam_in_window=df.docdb_family_id.where(year.between(lo, hi)))

    out = df.groupby(NAME_COLS).agg(
        countries=("person_ctry_code", lambda s: " ".join(sorted(set(s) - {""}))),
        n_person_ids=("person_id", "nunique"),
        applications=("appln_id", "nunique"),
        families=("docdb_family_id", "nunique"),
        families_in_window=("fam_in_window", "nunique"),
        first_priority_year=("year", "min"),
        last_priority_year=("year", "max"),
    ).reset_index()
    out = out.sort_values(["families", "psn_name"], ascending=[False, True])

    print(f"{len(out):,} name combinations · {out.psn_id.nunique():,} psn_id · "
          f"{out.han_id.nunique():,} han_id · {out.doc_std_name_id.nunique():,} doc_std_name_id")
    print(f"psn_names with more than one han_name: "
          f"{(out.groupby('psn_name').han_name.nunique() > 1).sum():,} · "
          f"han_names with more than one psn_name: "
          f"{(out.groupby('han_name').psn_name.nunique() > 1).sum():,}")
    return out


def main(cfg=CONFIG):
    ids = pd.read_csv(cfg["input_csv"]).docdb_family_id.dropna().astype(int).unique().tolist()
    print(f"{len(ids):,} families read from {cfg['input_csv']}")
    names = name_table(fetch_applicants(ids, cfg["env"]), cfg)

    out = Path(cfg["output_csv"])
    out.parent.mkdir(parents=True, exist_ok=True)
    names.to_csv(out, index=False)
    print(f"Saved to {out}. Top 30 by families:")
    print(names.head(30)[["psn_name", "han_name", "doc_std_name", "countries", "families"]].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export the sector's applicant names for harmonisation")
    parser.add_argument("--input", default=CONFIG["input_csv"], help="CSV with a docdb_family_id column")
    parser.add_argument("--output", default=CONFIG["output_csv"])
    parser.add_argument("--env", default=CONFIG["env"], choices=["TEST", "PROD"])
    parser.add_argument("--all-sectors", action="store_true", help="keep individuals, universities, ... too")
    a = parser.parse_args()
    main({**CONFIG, "input_csv": a.input, "output_csv": a.output, "env": a.env,
          "companies_only": not a.all_sectors})
