"""
Step 2 · Competitive landscape: who competes, how concentrated the field is, where the action is
Team 27 · Utility-scale energy storage · client Enel

Questions
    How concentrated is the field, and is it consolidating? Who are the incumbents and the new entrants?
    Which subfields grow fastest? Which political, economic, social and technological forces shape it (PEST)?

What it does
    1. applicants: harmonised firms (src/harmonize_firms.py), with type (firm / start-up / university, from
       psn_sector and age) and main country
    2. concentration: HHI, 1/HHI and CR4 on rolling windows (tutorial 1: six measures of Liston-Heyes &
       Pilkington, 2004), on families
    3. entry: new applicants per year (first patent EVER, any field, before their first sector family), their
       share of families, and the rate of disappearance; incumbents vs entrants (config `entrant_split_year`)
    4. subfields: growth of CPC groups, and/or topics from abstracts (embeddings + clustering, tutorial 2)
    5. shortlist: the firms to score in Steps 3-4 (config `n_firms_to_score`, `min_families`)
    PEST is written in the deck (mandatory table), no code.

Input   data/families.csv (Step 0) · config/sector.yaml · src/harmonize_firms.py (firm_of)
        PATSTAT (TIP): tls206 + tls207 (applicants), tls201 (years; first patent ever of each psn_id),
                       tls224 (CPC groups), tls203 (abstracts, for topics)
Output  outputs/tables/step2_top_applicants.csv    firm, type, country, families, first sector year, incumbent/entrant
        outputs/tables/step2_concentration.csv     HHI, 1/HHI, CR4 per window
        outputs/tables/step2_entry.csv             entrants and exits per year, their share of families
        outputs/tables/step2_subfields.csv         subfield (CPC group or topic), families per year, growth
        outputs/tables/firms_to_score.csv          column `firm`: the shortlist read by Steps 3 and 4
        outputs/figures/step2_concentration_entry.png · outputs/figures/step2_subfield_growth.png

Deck    top applicants table · concentration and entry over time · subfield growth map · PEST table
Reuse   tutorial_1/11_competitive_landscape.ipynb (measures, entrants), tutorial_2 (embeddings, topics)
"""


def main():
    # TODO 1 families + applicants -> firms (firm_of), type and country
    # TODO 2 concentration measures on rolling windows
    # TODO 3 first patent ever per psn_id -> entrants / exits per year
    # TODO 4 subfield growth (CPC groups; topics from abstracts)
    # TODO 5 write the shortlist outputs/tables/firms_to_score.csv
    raise NotImplementedError


if __name__ == "__main__":
    main()
