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
| 5 · Manual | three merges checked by hand, each with its source (below) | *LSIS*, *LS产电株式会社* → LS ELECTRIC | 6 |

**The group name** of a firm is its name without organisational words at the end and without "CHINA" at the start: *CHINA HUANENG GROUP CORPORATION* gives *HUANENG*. It must contain a distinctive word, i.e. not only legal, sector or place words (the word lists are in the code). A name that also contains another firm's group name is a possible joint venture and is left apart, e.g. *TOSHIBA MITSUBISHI-ELECTRIC*.

Result: 1,912 names become 1,491 firms.

**The manual merges (Step 5).** Steps 1–4 cannot see a rename or a name written only in Chinese or Japanese. Three such cases surfaced in the Step 3 ranking, where the same company appeared more than once. We checked each one and merged it:

| Firm | Names merged | Evidence |
|---|---|---|
| LS ELECTRIC | *LSIS COMPANY*; the Chinese *LS产电株式会社*, *LS 产电株式会社*, *LS电气株式会社*; *LS ELECTRIC* | LS Industrial Systems (English name LSIS, Korean *LS 산전*, Chinese *LS产电*) adopted the name LS ELECTRIC at its 46th regular shareholders' meeting on 24 March 2020 ([The Asia Business Daily, 24 Mar 2020](https://view.asiae.co.kr/en/article/2020032410135513971)) |
| ROBERT BOSCH | *罗伯特·博世有限公司*; *ROBERT BOSCH* | the Chinese name of Robert Bosch GmbH, as written in Bosch's own brochure *Bosch in China 2011–2012* ([PDF](https://kjc.seu.edu.cn/_upload/article/a6/15/fb4887a84546a850d67c75442af5/4eaecf58-b0e6-456a-bbdf-bbbc00202666.pdf)) |
| GS YUASA | *株式会社ＧＳユアサ*; *GS YUASA*, *GS YUASA INTERNATIONAL* | the legal name of GS Yuasa International Ltd. in its Legal Entity Identifier record ([LEI 353800V9KZ28MPO9AX95](https://lei.bloomberg.com/leis/view/353800V9KZ28MPO9AX95)) |

The remaining names written only in Chinese or Japanese have fewer families in the scoring window than the threshold (`min_families` = 5), so they cannot enter the ranking. The merges are written in `MANUAL_MERGES` in the code, and `firm_map.csv` records the source for each name moved.

## Validation

We tested the method on the gold standard of tutorial 1 (3,192 names in 481 organisations), using the tutorial's pairwise precision, recall and F1. The gold standard has no PATSTAT ids, so Step 3 is not tested.

| Method | Precision | Recall | F1 |
|---|---:|---:|---:|
| `psn_name` as it is | 1.000 | 0.000 | 0.000 |
| A · dictionary | 0.995 | 0.002 | 0.005 |
| B · cleanco | 0.996 | 0.003 | 0.006 |
| **Ours** | **0.984** | **0.900** | **0.940** |

## Limitations

**This is the closest we could get without a paid ownership database.** The method sees only names, so it cannot merge ownership that no name shows.