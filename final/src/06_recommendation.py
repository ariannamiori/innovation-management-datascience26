"""
Step 6 · Strategic analysis and recommendation: the evidence behind the firm we recommend to Enel
Team 27 · Utility-scale energy storage · client Enel

Pick the most promising firm FROM ITS POSITION ON THE QUADRANT (not its fame): a Visionary may be an
acquisition target, a Leader or Challenger a partner. This script produces the data behind the argument.

What it does (for config `recommendation.firm`, compared with the other scored firms)
    1. access to many markets: breadth of CPC classes and application domains of its families
    2. hard to imitate: revealed technological advantage per CPC subclass (Patel & Pavitt, 1997),
       citation centrality in the sector's citation network (tutorial 3), persistence over time
    3. fit with the client: Enel's own patent portfolio vs the firm's (overlap / complementarity of CPC
       profiles), for the acquire-or-partner argument (complementary assets, Teece, 1986)
    The deck adds: three arguments for the recommendation, two risks (litigation, freedom to operate,
    dependency, valuation), and the answers to the client's three questions. No code for those.

Input   outputs/tables/quadrant.csv (Step 5) · data/families.csv (Step 0) · config/sector.yaml
        src/harmonize_firms.py (firm_of)
        PATSTAT (TIP): tls224 (CPC of the firm and of the sector), tls228 (citations between firms),
                       tls206 + tls207 + tls201 (Enel's own families, for the fit)
Output  outputs/tables/step6_firm_profile.csv      breadth, RTA, centrality, persistence of the firm vs the others
        outputs/tables/step6_client_fit.csv        CPC overlap / complementarity with Enel
        outputs/figures/step6_rta.png

Deck    Step 6 slides: why this firm, acquire or partner, three arguments, two risks, the three answers
"""


def main():
    # TODO 1 profile of the picked firm: CPC breadth, RTA, citation centrality, persistence
    # TODO 2 Enel's portfolio and the fit
    raise NotImplementedError


if __name__ == "__main__":
    main()
