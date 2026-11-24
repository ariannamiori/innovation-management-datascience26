"""
Unit tests for the indicators (kickoff: tests/ unit tests for indicators). Run from final/: pytest tests/

Tested now: the name harmonisation (each step on a small hand-made example) and its evaluation metric.
To add as each step is written:
    Step 2   HHI / CR4 on a hand-computed example; entrant = first patent ever in the year
    Step 3   normalise_citations (1 = cohort mean, small cohorts use the year mean); success on decided filings only
    Step 4   originality = 1 - sum(s^2) on a hand-computed example; a CPC pair seen before is not novel
    Step 5   quadrant labels at the cut-off
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harmonize_firms import build_map, precision_recall_f1  # noqa: E402


def firms_of(names, **ids):
    df = pd.DataFrame({"psn_name": names, "families": 1, **ids})
    return build_map(df).set_index("psn_name").firm.to_dict()


def test_pairwise_f1_tutorial_example():
    """Tutorial 1, section 2.4: {NOKIA, NOKIA CORP, NOKIA OYJ} + NOKIAN TYRES all merged -> P 0.5, R 1, F1 0.67."""
    r = precision_recall_f1([1, 1, 1, 2], ["N", "N", "N", "N"])
    assert r["precision"] == 0.5 and r["recall"] == 1.0 and round(r["F1"], 2) == 0.67


def test_same_key_and_variant():
    f = firms_of(["LITHIUM ENERGY AND POWER & COMPANY", "LITHIUM ENERGY & POWER & COMPANY",
                  "DOOSAN HEAVY INDUSTRIES & CONSTRUCTION COMPANY", "DOOSAN HEAVY IND. & CONSTRUCTION"])
    assert f["LITHIUM ENERGY AND POWER & COMPANY"] == f["LITHIUM ENERGY & POWER & COMPANY"]          # step 1
    assert f["DOOSAN HEAVY INDUSTRIES & CONSTRUCTION COMPANY"] == f["DOOSAN HEAVY IND. & CONSTRUCTION"]  # step 2


def test_shared_id_needs_name_agreement():
    f = firms_of(["GS YUASA", "GS YUASA INTERNATIONAL", "TOSHIBA CORPORATION", "DENSO CORPORATION"],
                 doc_std_name_id=[1, 1, 2, 2])
    assert f["GS YUASA"] == f["GS YUASA INTERNATIONAL"]
    assert f["TOSHIBA CORPORATION"] != f["DENSO CORPORATION"]          # same id, unrelated names: not merged


def test_group_name_positions_and_joint_ventures():
    f = firms_of(["STATE GRID CORPORATION OF CHINA", "STATE GRID JIANGSU ELECTRIC POWER COMPANY",
                  "NANJING POWER SUPPLY BRANCH OF STATE GRID JIANGSU ELECTRIC POWER COMPANY",
                  "CHINA HUANENG GROUP CORPORATION", "SICHUAN HUANENG KANGDING HYDROPOWER COMPANY",
                  "CHINA SALT HUANENG ENERGY STORAGE TECHNOLOGY COMPANY",
                  "TOSHIBA CORPORATION", "MITSUBISHI ELECTRIC CORPORATION",
                  "TOSHIBA MITSUBISHI-ELECTRIC INDUSTRIAL SYSTEM CORPORATION",
                  "EAST GROUP", "EAST CHINA ELECTRIC POWER RESEARCH INSTITUTE COMPANY"])
    assert f["NANJING POWER SUPPLY BRANCH OF STATE GRID JIANGSU ELECTRIC POWER COMPANY"] == "STATE GRID"   # after OF
    assert f["SICHUAN HUANENG KANGDING HYDROPOWER COMPANY"] == "HUANENG"                                  # after a place
    assert f["CHINA SALT HUANENG ENERGY STORAGE TECHNOLOGY COMPANY"] != "HUANENG"                         # not a position
    assert f["TOSHIBA MITSUBISHI-ELECTRIC INDUSTRIAL SYSTEM CORPORATION"] not in ("TOSHIBA", "MITSUBISHI ELECTRIC")
    assert f["EAST CHINA ELECTRIC POWER RESEARCH INSTITUTE COMPANY"] != f["EAST GROUP"]                   # EAST is generic


def test_no_merge_without_evidence_in_the_names():
    f = firms_of(["PANASONIC CORPORATION", "SANYO ELECTRIC COMPANY"])     # owned by Panasonic, but nothing shows it
    assert f["SANYO ELECTRIC COMPANY"] != f["PANASONIC CORPORATION"]


def test_deterministic():
    names = ["STATE GRID CORPORATION OF CHINA", "STATE GRID HUNAN ELECTRIC POWER COMPANY", "HITACHI", "HITACHI POWER SOLUTIONS COMPANY"]
    assert firms_of(names) == firms_of(list(reversed(names)))
