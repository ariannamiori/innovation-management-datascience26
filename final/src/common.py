"""
Shared code of the pipeline: configuration, PATSTAT access, and the cleaning rules every step applies
Team 27 · Utility-scale energy storage · client Enel

Every step queries PATSTAT directly on TIP (no local copy of PATSTAT). Only the family list (Step 0) and the
results of each step (outputs/) are files.

Cleaning rules (kickoff, Step 0 "Clean")
    unit of analysis   the DOCDB family: each invention counted once
    time               the earliest priority year of the family (tls201.earliest_filing_year)
    applicants         harmonised firms: psn_name -> firm with src/harmonize_firms.py (firm_of), companies only
    truncation         priority years after config `years.last_complete` are incomplete: flagged, never read as a decline

Run order
    00_dataset -> export_firm_names + harmonize_firms -> 01_description -> 02_competition
    -> 03_present_score -> 04_future_score -> 05_quadrant -> 06_recommendation

TODO: move here from 03_present_score.py the code every step needs (_chunks, fetch_from_patstat, build_families).
"""
from __future__ import annotations

from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "sector.yaml"


def load_config(path: str | Path = CONFIG_PATH) -> dict:
    """config/sector.yaml as a dict."""
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_family_ids(path: str | Path) -> list[int]:
    """The sector's DOCDB families, from the Step 0 file (column docdb_family_id)."""
    raise NotImplementedError


def patstat_session(env: str):
    """(PatstatClient, ORM session) on TIP; closes cleanly at the end."""
    raise NotImplementedError


def run_chunked(patstat, make_query, ids, chunk: int = 5000):
    """One query per chunk of ids (IN (...) stays small), results stacked in one DataFrame."""
    raise NotImplementedError


def build_families(apps, cpc, last_complete: int):
    """One row per family: priority year, first publication year, main CPC subclass, truncated flag."""
    raise NotImplementedError


def firm_table(owners):
    """Applicant links -> (family, firm) with firm_of, companies only, full counting of co-owned families."""
    raise NotImplementedError
