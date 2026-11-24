"""
Step 5 · Magic Quadrant: place the scored firms on the two axes
Team 27 · Utility-scale energy storage · client Enel

What it does
    1. joins the present score (Step 3) and the future score (Step 4) of the shortlisted firms
    2. axes as in Gartner's Magic Quadrant: x = future score (completeness of vision), y = present score
       (ability to execute); cut at config `quadrant.split` (median of the scored firms, or 100 = average)
    3. labels each firm: Leaders (high/high), Challengers (high present, low future),
       Visionaries (low present, high future), Niche players (low/low)
    4. figure: bubble size = number of families, the recommended firm (Step 6) highlighted
    5. robustness: does a firm change quadrant under the other weights of Step 3 (present_scores_robustness.csv)?

Input   outputs/tables/present_scores.csv, present_scores_robustness.csv (Step 3)
        outputs/tables/future_scores.csv (Step 4) · config/sector.yaml
Output  outputs/tables/quadrant.csv               firm, present, future, families, quadrant, quadrant stability
        outputs/figures/step5_magic_quadrant.png

Deck    the quadrant (the centrepiece of the deck and the pitch); method sources: Gartner, Brockhoff (1992), Ernst (1998)
No PATSTAT query: it only reads the outputs of Steps 3 and 4.
"""


def main():
    # TODO 1 read and join present and future scores
    # TODO 2 cut the axes, assign quadrants
    # TODO 3 bubble chart; quadrant stability under other weights
    raise NotImplementedError


if __name__ == "__main__":
    main()
