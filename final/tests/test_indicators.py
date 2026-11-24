"""
Unit tests for the indicators (kickoff: tests/ unit tests for indicators). Run: pytest tests/

Already testable (code exists): name harmonisation and its metric.
To add as each step is written:
    Step 2   HHI / CR4 on a hand-computed example; entrant = first patent ever in the year
    Step 3   normalise_citations (1 = cohort mean, small cohorts use the year mean); success on decided filings only
    Step 4   originality = 1 - sum(s^2) on a hand-computed example; a CPC pair seen before is not novel
    Step 5   quadrant labels at the cut-off
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_pairwise_f1_tutorial_example():
    """Tutorial 1, section 2.4: {NOKIA, NOKIA CORP, NOKIA OYJ} + NOKIAN TYRES all merged -> P 0.5, R 1, F1 0.67."""
    from harmonize_firms import precision_recall_f1
    r = precision_recall_f1([1, 1, 1, 2], ["N", "N", "N", "N"])
    assert r["precision"] == 0.5 and r["recall"] == 1.0 and round(r["F1"], 2) == 0.67


def test_firm_of_groups_and_joint_ventures():
    from harmonize_firms import firm_of
    assert firm_of("STATE GRID JIANGSU ELECTRIC POWER COMPANY") == "STATE GRID (SGCC)"
    assert firm_of("三星SDI株式会社") == "SAMSUNG SDI"
    assert firm_of("NOKIA SIEMENS NETWORKS") != "SIEMENS"                 # joint venture stays apart
    assert firm_of("EAST CHINA ELECTRIC POWER RESEARCH INSTITUTE COMPANY") != "STATE GRID (SGCC)"   # TO_CHECK
