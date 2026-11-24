"""
Step 0 · Build the dataset: which patent families belong to the sector
Team 27 · Utility-scale energy storage · client Enel
STATUS: placeholder, the code is added by the teammate who built the family list

What it does
    1. query PATSTAT for candidate families: CPC prefixes (tls224) + keywords in titles / abstracts (tls202 / tls203)
    2. refine: reference families + text similarity with an adaptive cut-off (produces the columns of the v4 file)
    3. validate: hand-label about 100 random families (precision of the query), or another validation from the literature

Input   config/sector.yaml          CPC codes, keywords, environment
        PATSTAT (TIP)               tls201, tls202, tls203, tls224
Output  data/families.csv           one row per family; required column `docdb_family_id`
                                    (today: utility_scale_storage_reviewed_adaptive_v4.csv: source,
                                    adaptive_reference_family_id, cosine_similarity, adaptive_cutoff, margin_above_cutoff)
        outputs/tables/step0_validation.csv   the hand-labelled sample and the precision of the query

Deck    Step 0 / appendix: the query (codes table, see tutorial_0/david/codes_team27.md, keywords), the
        refinement, the validation result, the final number of families

Cleaning rules used by every later step (kickoff) live in src/common.py and src/harmonize_firms.py:
    unit = DOCDB family · time = earliest priority year · applicants = harmonised firms · last ~3 years flagged
"""


def main():
    # TODO (teammate): candidate query, refinement, validation, write data/families.csv
    raise NotImplementedError("Step 0: the family-list code is added by the teammate who built it")


if __name__ == "__main__":
    main()
