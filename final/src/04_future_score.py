"""
Step 4 · Future score: our own algorithm for the value of the firms tomorrow (x-axis of the Magic Quadrant)
Team 27 · Utility-scale energy storage · client Enel

Grants and citations do not exist yet for recent filings: score the last 1-2 years of published applications
(config `future_score.publication_years`) with forward-looking signals, per family, then per firm.

Possible ingredients (combine, improve or replace)
    originality         1 - sum of squared shares over the CPC classes of the patents it cites   (Trajtenberg et al., 1997)
    generality          same over the patents that cite it: needs forward citations, careful on recent filings
    novel recombination pairs of CPC codes that never co-occurred before                       (Fleming, 2001; Verhoeven et al., 2016)
    hot subfields       early filing in fast-growing CPC groups / topics (from Step 2)
    text novelty        low similarity to prior art, high similarity to what comes after      (Kelly et al., 2021; Arts et al., 2021)

Proof that it works (back-test)
    freeze time at T (config `backtest_freeze_year`), compute the score with data available at T only,
    measure what happened in the next N years (forward citations, family growth, grants, the firm's activity),
    compare with simple baselines (e.g. volume, family size)

Input   data/families.csv (Step 0) · outputs/tables/firms_to_score.csv (Step 2) · subfield growth (Step 2)
        config/sector.yaml · src/harmonize_firms.py (firm_of)
        PATSTAT (TIP): tls228 (backward / forward family citations), tls225 (family CPC of cited and citing
                       families), tls203 (abstracts), tls201 (dates, family sizes), tls211 (grants)
Output  outputs/tables/future_scores.csv            one row per firm: each ingredient, the score, the rank
        outputs/tables/future_score_backtest.csv    score at T vs outcomes after T, and the baselines
        outputs/figures/step4_backtest.png

Deck    the algorithm (formulas and choices), the back-test against the baselines; details in the appendix
"""


def main():
    # TODO 1 recent families of the shortlisted firms
    # TODO 2 ingredients per family (citations + CPC of cited families, CPC pairs, abstracts)
    # TODO 3 combine into one score per firm
    # TODO 4 back-test at T against baselines
    raise NotImplementedError


if __name__ == "__main__":
    main()
