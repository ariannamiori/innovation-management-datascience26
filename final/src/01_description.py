"""
Step 1 · General description of the sector: what the field looks like and how it uses IP
Team 27 · Utility-scale energy storage · client Enel

Questions
    Which technologies make up the field? How big is it, is it growing, flat or declining?
    Which technology classes dominate, and how is the mix shifting? Patent-heavy, or does it rely on secrecy?

What it does
    1. volume: families per priority year, growth rate over config `description.growth_window`
       (truncated years after `years.last_complete` flagged, not read as a decline)
    2. technology mix: share of families by CPC subclass, and its change over time (Y tags kept apart)
    3. geography: filing offices (tls201.appln_auth) and applicant countries (tls206.person_ctry_code)
    4. appropriability: no code, an argued paragraph comparing with the literature (patents vs secrecy)

Input   data/families.csv (Step 0) · config/sector.yaml
        PATSTAT (TIP): tls201 (years, offices), tls224 (CPC), tls206 + tls207 (applicant countries)
Output  outputs/figures/step1_families_per_year.png     truncated years shaded
        outputs/figures/step1_cpc_mix.png               CPC subclass shares over time
        outputs/tables/step1_volume.csv                 families per priority year, growth rate
        outputs/tables/step1_top_cpc.csv                top CPC subclasses (add their official definitions)
        outputs/tables/step1_geography.csv              filing offices and applicant countries

Deck    families over time · CPC mix over time · top CPC table with definitions · appropriability paragraph
Reuse   tutorial_0/02_step1_general_description.ipynb, tutorial_0/david/02_step1_general_description_team27.ipynb
"""


def main():
    # TODO 1 load families + config; query applications, CPC, applicant countries (src/common.py)
    # TODO 2 families per priority year + growth rate; figure with truncated years shaded
    # TODO 3 CPC subclass mix and its change; top-CPC table
    # TODO 4 filing offices and applicant countries
    raise NotImplementedError


if __name__ == "__main__":
    main()
