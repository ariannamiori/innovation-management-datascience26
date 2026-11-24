# Technical appendix · Step 3 · Present score

Code: `src/03_present_score.py` · Parameters: `config/sector.yaml` · Input: `data/families.csv` (Step 0), `outputs/tables/firm_map.csv` (`src/harmonize_firms.py`), PATSTAT on TIP · Output: `outputs/tables/present_scores.csv`, `outputs/tables/present_scores_robustness.csv`

## What it does

The present score ranks the sector's main firms by the value of their patents today (the y-axis of the Magic Quadrant, "ability to execute"). It follows tutorial 4 and the four criteria of Clarivate's *Top 100 Global Innovators*.

1. **Data.** For the 6,838 families of the sector, the script queries PATSTAT for:
   - the applications (`tls201`)
   - their CPC codes (`tls224`)
   - the applicants (`tls207` with `applt_seq_nr > 0`, joined to `tls206`)
   - the forward citations between families (`tls228`), each dated by the first publication year of the citing family
2. **Families.** The unit is the DOCDB family, so each invention counts once. Each family gets:
   - its earliest priority year;
   - its first publication year;
   - its main CPC subclass, the most frequent one, ignoring the Y tags.
3. **Window.** Only families with a priority year in the window are scored.
4. **Firms.** Applicants that are companies are mapped to firms with `firm_of` (the firm map). A family filed by two firms counts fully for each (full counting).
5. **Who is scored.** The Step 2 shortlist; while it does not exist, the largest firms with at least `min_families` families in the window.
6. **Indicators.** Four per firm (next section).
7. **Score.** Each indicator is divided by its mean over the scored firms and the results are combined with the weights: **100 = the average scored firm**.
8. **Robustness.** The ranking is recomputed under other choices and compared with ours (Spearman rank correlation).

## The four indicators

| Indicator | What it captures | How it is computed | Source |
|---|---|---|---|
| Volume | weight in the sector | the firm's families ÷ all sector families in the window; in the score as log(families) | Ernst (1998) |
| Influence | technological impact | per family: distinct citing families within 5 years of its first publication ÷ the mean of its priority-year × CPC-subclass cohort; the firm's value is the mean over its families | Hall, Jaffe & Trajtenberg (2001, 2005) |
| Success | quality as judged by examiners | granted ÷ filed applications, at all national offices | Guellec & van Pottelsberghe (2000) |
| Globalization | breadth of protection | mean number of distinct national offices per family | Harhoff, Scherer & Vopel (2003) |

## Configuration (`config/sector.yaml`)

| Variable | Value | What it does | Why this value |
|---|---|---|---|
| `families_csv` | `data/families.csv` | the sector's families | the Step 0 output |
| `patstat.env` | `PROD` | PATSTAT database on TIP | TEST is a small sample with almost no citations between patents |
| `patstat.chunk` | 5000 | ids per `IN (...)` query | keeps each query small enough for TIP |
| `competition.n_firms_to_score` | 15 | how many firms are scored without a shortlist | enough firms to fill the quadrant |
| `competition.min_families` | 5 | minimum families in the window to be scored | with 10, only 6 firms qualified (see below) |
| `present_score.firms_csv` | `outputs/tables/firms_to_score.csv` | the Step 2 shortlist | the firms chosen in Step 2; while it is missing, the largest portfolios |
| `present_score.output_csv` | `outputs/tables/present_scores.csv` | where the scores are written | the robustness table is written next to it |
| `present_score.window` | 2010–2019 | priority years scored | old enough to be examined and cited; the 2010–2018 window held only 13 % of the families |
| `present_score.last_citation_year` | 2025 | last complete year of citations in the PATSTAT edition | the data end in 2026, so 2026 is incomplete |
| `present_score.citation_window` | 5 | years of forward citations counted | standard window: old and young families get the same time to be cited |
| `present_score.min_cohort` | 5 | smallest priority-year × CPC-subclass cohort used for normalisation; smaller cohorts use the year mean | a mean over fewer than 5 families is noise |
| `present_score.keep_ipr` | `[PI]` | patents of invention only | utility models (frequent in China) and designs are not examined like inventions |
| `present_score.ep_only` | `false` | if true, only families with an EP application | 86 % of the families are filed only in China; EP-only would drop most of the sector |
| `present_score.success_offices` | `null` (all national offices) | offices whose decisions count for success | with EP only, success covered 5 % of the families and State Grid had no decision at all |
| `present_score.log_volume` | `true` | volume enters the score as log(families) | with a linear scale, State Grid's volume alone gave it about 190 of its 261 points |
| `present_score.weights` | 0.25 each | weight of each indicator | no indicator is preferred a priori; the robustness table shows what each one changes |
| `present_score.method` | `mean` | how indicators are combined: ratio to the mean (100 = average firm), or `rrf` (reciprocal rank fusion, ranks only) | keeps the size of the differences; `rrf` is reported as a check |

## Choices fixed in the code

- **Unit and time.**
  - The DOCDB family is the unit, and its year is the earliest priority year, the date closest to the invention.
  - PATSTAT dummy applications (`appln_id` ≥ 900,000,000) are dropped.
- **Firms.**
  - Only applicants whose `psn_sector` contains COMPANY are firms.
  - Co-owned families count fully for each owner.
- **Influence.**
  - A family citing itself is dropped; citations from the same firm count, as in the OECD indicators.
  - A family whose 5-year window is not complete by `last_citation_year` is left out of the mean, not counted as 0.
  - The cohort is the family's priority year × its most frequent non-Y CPC subclass.
- **Success and globalization.**
  - Both count national applications only: PCT requests (WO) and EP translations (kind T) are left out.
  - Pending applications count as not granted, which is one reason the window stops at 2019.
- **Missing values.** A firm without a value for an indicator (e.g. no decided application) gets the average of the scored firms, so a missing value counts as neutral. `success_n_apps` shows how many decisions each success rate rests on.

## How the configuration was chosen

| Run | Settings | Families in window | Firms scored | What we saw |
|---|---|---:|---:|---|
| 1 | 2010–2018, success on EP, min 10, linear volume | 924 | 6 | Only 13 % of the families fall in the window, because the sector grew after 2019. Only 5 % of families have an EP filing, so success rested on 0–22 decisions: State Grid had none, LSIS had 0 of 6. Without volume, the ranking correlates only 0.60 with ours. |
| 2 | 2010–2019, all offices, min 5, linear volume | 1,162 | 15 | Success now rests on 8–185 decisions per firm. State Grid scored 261, about 190 points of it from volume. LS Electric appeared three times, which led to the manual merge in the firm map (`docs/harmonize_firms.md`). |
| 3 (current) | run 2 + log volume + LS merge | 1,162 | 15 | Recomputed from the run-2 indicators: State Grid moves from 1st to 4th, the other ranks barely move, and the order of ranks 5–15 is the same under the mean, log-volume and rrf versions. |

## Outputs

`outputs/tables/present_scores.csv` has one row per scored firm:

| Column | Meaning |
|---|---|
| `firm` | firm label from the firm map |
| `families` | families of the firm in the window |
| `volume` | share of the sector's window families |
| `influence` | mean normalised forward citations (1 = cohort average) |
| `success` | share of decided applications granted |
| `success_n_apps` | applications the success rate rests on |
| `globalization` | mean national offices per family |
| `score` | present score (100 = average scored firm) |
| `rank` | rank by score |

`outputs/tables/present_scores_robustness.csv` gives the rank of each firm under seven settings:
- ours;
- without each of the four indicators in turn;
- the other combination method (`rrf`);
- the other volume scale (linear).

The run prints the Spearman correlation of each with our ranking.

## Limitations

- **Relative scores.** The score is relative to the scored set: adding or removing a firm moves everyone's baseline of 100.
- **Success across offices.** Success at all offices mixes the grant practices of different offices. EP alone would be one standard, but it covers only 5 % of this sector.
- **Firm map.** The firm map sees only names, apart from the one sourced manual merge. NARI (State Grid) and Xuji (China Electrical Equipment Group) are scored as separate firms (`docs/harmonize_firms.md`).
- **Recent families.** Families first published after 2020 have no complete citation window. They count for volume, success and globalization, but not for influence.

## How to run

From `final/` on TIP, after `src/export_firm_names.py` and `src/harmonize_firms.py`:

```
python src/03_present_score.py                       # parameters from config/sector.yaml
python src/03_present_score.py --volume linear       # one-off variant, the config is unchanged
```
