# Technical appendix · Firm name harmonisation

Code: `src/harmonize_firms.py` · Input: `outputs/tables/firm_names.csv` · Output: `outputs/tables/firm_map.csv` (one row per name, with the evidence of each merge), `outputs/tables/firm_list.csv` · Tests: `tests/test_indicators.py`

## Problem

The present score ranks firms, but PATSTAT records applicant names. The sector's applicant companies carry 1,912 standardised names (`psn_name`), and one company can appear under hundreds of them: State Grid alone has 284. Counting each name as a firm would split large groups into many small ones.

## Method

The map merges two names only when the data shows they belong together. We start from `psn_name`, as the tutorials do; it is less fragmented than `han_name` (1,912 vs 2,103 distinct names).

| Step | Rule | Example | Names merged |
|---|---|---|---:|
| 1 · Same key | same name after tutorial 1 method B (`cleanco`, then the legal-form dictionary of method A) | *LITHIUM ENERGY & POWER* = *LITHIUM ENERGY AND POWER* | 6 |
| 2 · Variant | same first word and length; the other words equal or abbreviated | *DOOSAN HEAVY IND.* = *DOOSAN HEAVY INDUSTRIES* | 8 |
| 3 · Shared id | same HAN or DOCDB id **and** one name begins with the other (the id alone links e.g. Toshiba and Denso) | *GS YUASA* = *GS YUASA INTERNATIONAL* | 3 |
| 4 · Group name | the name contains another firm's group name: at the start of a part of the name, after a place word, or after "OF" | *NANJING POWER SUPPLY BRANCH OF STATE GRID JIANGSU …* → State Grid | 395 |
| 5 · Manual | one merge checked by hand, with its source (below) | *LSIS*, *LS产电株式会社* → LS ELECTRIC | 4 |

**The group name** of a firm is its name without organisational words at the end and without "CHINA" at the start: *CHINA HUANENG GROUP CORPORATION* gives *HUANENG*. It must contain a distinctive word, i.e. not only legal, sector or place words (the word lists are in the code). A name that also contains another firm's group name is a possible joint venture and is left apart, e.g. *TOSHIBA MITSUBISHI-ELECTRIC*.

Result: 1,912 names become 1,493 firms.

**The manual merge (Step 5).** The Step 3 ranking listed LS Electric three times: as *LSIS* (27 families), as *LS* (its filings under the Chinese names *LS产电* and *LS电气*, 9) and as *LS ELECTRIC* (9). Research showed they are one company. LS Industrial Systems (English name LSIS, Korean *LS 산전*, Chinese *LS产电*) adopted the name LS ELECTRIC (LS Electric Co., Ltd.) at its 46th regular shareholders' meeting on 24 March 2020 ([The Asia Business Daily, 24 Mar 2020](https://view.asiae.co.kr/en/article/2020032410135513971)). A rename leaves no trace in the names, so no rule of Steps 1–4 can find it. The merge is written in `MANUAL_MERGES` in the code, with its source, and `firm_map.csv` records the source for each name it moved.

## Validation

We tested the method on the gold standard of tutorial 1 (3,192 names in 481 organisations), using the tutorial's pairwise precision, recall and F1. The gold standard has no PATSTAT ids, so Step 3 is not tested.

| Method | Precision | Recall | F1 |
|---|---:|---:|---:|
| `psn_name` as it is | 1.000 | 0.000 | 0.000 |
| A · dictionary | 0.995 | 0.002 | 0.005 |
| B · cleanco | 0.996 | 0.003 | 0.006 |
| **Ours** | **0.984** | **0.900** | **0.940** |

## Limitations

**This is the closest we could get without a paid ownership database.** The method sees only names, so it cannot merge ownership that no name shows:
- Sanyo is part of Panasonic;
- NARI belongs to State Grid;
- Guangdong Power Grid belongs to China Southern Power Grid.

Nor can it read names written only in Chinese or Japanese (19 names, about 45 families). Name evidence also follows brands rather than owners: *SIEMENS ENERGY* is merged with Siemens, although it was spun off in 2020. Fixing these cases needs ownership data such as Orbis (global ultimate owner).
