# Technical appendix · Firm name harmonisation

Team 27 · Utility-scale energy storage · client Enel
Code: `src/harmonize_firms.py` · Input: `outputs/tables/firm_names.csv` (`src/export_firm_names.py`) · Output: `outputs/tables/firm_map.csv`, `outputs/tables/firm_list.csv`

## 1. Why the names must be harmonised

The present score (Step 3) ranks **firms**. PATSTAT does not record firms. It records the applicants written on each filing. One company appears under many names: spellings, legal forms, Chinese and Japanese versions, subsidiaries, branches and research institutes. Counting each name as a firm splits large groups into many small ones. Volume is then too low, the rates rest on too few patents, and a firm can drop below the `min_families` threshold.

Our sector is a strong case. The sector's applicant companies carry **1,912 distinct `psn_name`s**. State Grid alone accounts for **309** of them: the parent company, its provincial companies, their city power-supply branches and their research institutes.

**Definition used.** A firm is **the group that ultimately owns the named entity today**, where "owns" means wholly or majority owned (more than 50 %). The rule follows Clarivate's *Top 100 Global Innovators*, which ranks whole organisations (tutorial 4), and it suits an investor asking who holds the technology now. Joint ventures between two groups stay separate firms. The definition has some consequences, which Section 7 discusses.

## 2. Starting point: `psn_name`, not `han_name`

`tls206_person` offers three standardised names (tutorial 1, `10_patent_attributes`). We compared them on the sector's applicant companies.

| Name | Distinct values | Observation |
|---|---|---|
| `psn_name` (EPO / KU Leuven PATSTAT Standardised Name) | 1,912 | the base used in tutorials 1, 3 and 4 |
| `han_name` (OECD HAN) | 2,103 | **more fragmented**: 123 `psn_name`s are split over several `han_name`s |
| `doc_std_name` (DOCDB) | 2,023 | also more fragmented; some values are inventor names (e.g. KOBE STEEL → *KISHI TOMOYA*) |

`han_name` also makes wrong merges: it puts *Samsung SDI*, *Samsung Electronics* and *Samsung Electro-Mechanics* under one name (three separately listed companies), *State Grid Fujian* under *State Grid Jiangsu*, and the CSG research institute under SGCC's *China Electric Power Research Institute*. We therefore build on `psn_name` and use `han_name` only as a reference when checking by hand (`firm_map.csv` lists the `han_name`s of each name).

## 3. Method: four layers

For each name, the first layer that decides it wins. The method extends the "name game" of tutorial 1 (`11_competitive_landscape`, §2). That section offers three methods, A (a dictionary of legal forms), B (cleanco) and C (Terrorizer), and concludes: *"look at the top of your list by hand: in the end, you decide what one applicant is."* Layer 3 is that hand-made decision, written as rules so it can be repeated and reviewed.

| Layer | What it does | Why | Names decided |
|---|---|---|---|
| 1 · Normalise | full-width characters to ASCII (Unicode NFKC), upper case, single spaces | Japanese filings write Latin names in full-width characters (*ＬＳ ＥＬＥＣＴＲＩＣ*) | (all) |
| 2 · Translate | names in Chinese or Japanese only: a short table of their Latin name; mixed names keep their Latin part | no cleaning method can read them, see below | 4 |
| 3 · Group rules | 51 hand-written rules, regular expressions on the name, merge subsidiaries, branches and institutes into their group | `psn_name` "never merges a subsidiary with its parent" (tutorial 1) | 623 |
| 4 · Clean | tutorial 1 **method B**: `cleanco`, then the legal-form dictionary of method A (`&` read as AND) | variants that differ only in legal form or punctuation | 1,284 |

One name, *埃内欧储能系统有限公司*, is left as it is (1 family, firm not identified).

**Why layer 2 exists.** On our names, method A turns all 9 names written only in Chinese into an **empty string**, and would merge Bosch, Siemens, BMW, Vestas, Honeywell and Dresser-Rand into a single "firm" with no name. The script never merges on an empty key, and the group rules also read the Chinese and Japanese spellings (*罗伯特·博世* → Bosch, *三星SDI* → Samsung SDI, *LS产电* → LS Electric, *株式会社GSユアサ* → GS Yuasa).

**Why layer 4 does little here.** PSN already removes legal forms. Methods A and B both reduce 1,912 names to 1,896 keys, and cleanco differs from method A on only 4 names (*S.L.*, *KGaA*). We keep layer 4 because it is cheap, safe (high precision, Section 5) and catches what remains, e.g. *LITHIUM ENERGY AND POWER & COMPANY* = *LITHIUM ENERGY & POWER & COMPANY*.

**Why not Terrorizer (method C).** Our main problem is ownership: which entity belongs to which group. Name similarity cannot answer that. *STATE GRID HUNAN* and *NARI TECHNOLOGY* belong to the same group, while *GUODIAN NANJING AUTOMATION* (Huadian) and *GUODIAN UNITED POWER* (CHN Energy) do not. The tutorial also notes that Terrorizer "needs a check of the groups it creates". We put that effort into explicit rules instead.

## 4. Group rules (layer 3)

Rules are written for every group whose names add up to roughly 5 or more families. Below that a group cannot reach the scoring threshold (`min_families` = 10), so the long tail is only cleaned (layer 4). The rules are ordered: joint ventures and spin-offs come before their parent. Every rule with its reason is in `GROUP_RULES` in the code. The full list of the names merged into each firm is in `firm_list.csv`.

Main groups (families summed over names, all years / 2010–2018 scoring window):

| Firm | Names merged | Families | Decision and reason |
|---|---:|---:|---|
| State Grid (SGCC) | 309 | 1,754 / 318 | parent, provincial companies (also under their names before the "State Grid" prefix, e.g. *JIANGSU ELECTRIC POWER COMPANY*), their branches and institutes, NARI / Nanrui, CEPRI, Guodiantong |
| China Huaneng Group | 44 | 357 / 4 | Huaneng units; Xi'an Thermal Power Research Institute (TPRI) is Huaneng's; the *China Salt Huaneng* joint venture is excluded |
| China Southern Power Grid (CSG) | 30 | 276 / 21 | CSG and its five provincial grids (Guangdong, Guangxi, Yunnan, Guizhou, Hainan), power supply bureaus, institutes |
| China Three Gorges (CTG) | 5 | 114 / 1 | CTG, CTG Renewables, Yangtze Power, SIDRI |
| PowerChina | 20 | 96 / 4 | Power Construction Corp. of China and its design institutes (ex HydroChina, Sinohydro) |
| China Huadian Group | 23 | 82 / 10 | Huadian units and Guodian Nanzi (SAC), which Huadian controls |
| China Electrical Equipment Group (CEEG) | 14 | 79 / 24 | XJ (Xuji) and Pinggao, moved from SGCC in 2021, and China XD |
| China Energy Engineering (CEEC) | 21 | 67 / 2 | CEEC, its China Power Engineering Consulting institutes, Gezhouba |
| LS Electric | 6 | 62 / 62 | LSIS = LS Industrial Systems, renamed LS Electric in 2020; Chinese and Japanese spellings |
| Panasonic | 4 | 31 / 25 | Panasonic, its IP management unit, Panasonic Electric Works, Sanyo Electric (wholly owned since 2011) |
| Samsung SDI | 2 | 31 / 22 | Samsung SDI only: Samsung Electronics and Electro-Mechanics are separate listed firms |
| GS Yuasa | 3 | 32 / 21 | GS Yuasa, GS Yuasa International, Japanese spelling |
| Siemens Energy | 7 | 18 / 9 | spun off from Siemens in 2020; owns Siemens Gamesa and Dresser-Rand (bought by Siemens in 2015) |
| Baker Hughes | 2 | 14 / 14 | Nuovo Pignone belongs to Baker Hughes (ex GE Oil & Gas) |
| LG Energy Solution | 2 | 21 / 3 | LG Chem spun off its battery unit as LG Energy Solution in 2020 |

Other rules cover Hitachi, Toshiba, Bosch, GE (with Alstom Technology, bought in 2015), MHI, ABB, CATL, BYD, Sungrow, Gotion, SPIC, CHN Energy (Guodian and Shenhua merged in 2017), Datang, CRRC (CSR and CNR merged in 2015), KEPCO, Doosan Enerbility, Clarios (ex Johnson Controls Power Solutions) and a few more: 51 groups in total.

**Joint ventures are not merged.** Toshiba Mitsubishi-Electric (TMEIC), Hitachi Mitsubishi Hydro, Dongfang Hitachi, Lithium Energy and Power (Bosch, GS Yuasa, Mitsubishi Corp.), Shanghai Electric Guoxuan and Yangguang Samsung all stay separate. The rules for multinationals match only at the **start** of the name, so *NOKIA SIEMENS NETWORKS* or *FUJITSU TOSHIBA* are never merged into Siemens or Toshiba.

**Names left apart because their owner is uncertain** (`TO_CHECK` in the code, printed at each run):

| Name | Families | Possible group |
|---|---:|---|
| East China Electric Power Research Institute | 14 | SGCC (East China branch)? |
| North China Electrical Power Research Institute | 13 | SGCC (North China branch / State Grid Jibei)? |
| Changjiang Institute of Survey, Planning, Design and Research | 12 | **not** CTG despite the name: Changjiang Water Resources Commission |
| Shandong Electric Power Engineering Consulting Institute | 10 | CEEC? |
| (Changzhou) NR Electric Power Electronics | 6 | SGCC, via NARI? |
| LG Innotek / Toyota Industries | 4 / 1 | minority-owned (about 41 % / 24 %): separate under our majority rule |

## 5. Validation

**(a) Gold standard of tutorial 1.** We use `PATSTAT_500_label_datav4.csv` (3,192 names, 481 organisations labelled by hand) and the same pairwise precision, recall and F1 as `11_competitive_landscape` §2.4.

| Method | Groups found | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| `psn_name` as it is | 3,192 | 1.000 | 0.000 | 0.000 |
| A · dictionary | 3,006 | 0.995 | 0.002 | 0.005 |
| B · cleanco | 2,978 | 0.996 | 0.003 | 0.006 |
| First word of the name | 536 | 0.961 | 0.923 | 0.942 |
| **Ours (4 layers)** | 2,570 | **0.992** | 0.269 | 0.424 |

How to read it:
- Our method keeps **precision at 0.99**: it almost never merges two different organisations.
- Recall is 0.27, because the gold standard is drawn from other industries (Nokia, Siemens' medical units, Honeywell, Panasonic…) and our group rules are written for the energy storage sector. Recall on a sector depends on its group rules, which is why we wrote them for our sector and checked them by hand.
- An earlier version of our rules matched "SIEMENS", "TOSHIBA" or "PANASONIC" anywhere in a name. Its precision was 0.84, because joint ventures such as Nokia Siemens Networks or Towerjazz Panasonic were merged into the parent. The gold standard revealed this, and the fix (rules anchored at the start of the name) changed nothing on our own names.

**Why "first word" is rejected despite F1 = 0.94.** The gold standard is mostly multinationals whose names start with the brand (*NOKIA …*, *SIEMENS …*). Our sector's names mostly start with a place or a generic word. On our data the first word would merge 123 names into "STATE", 76 into "BEIJING", 74 into "SHENZHEN" and 64 each into "JIANGSU" and "SHANGHAI". A metric computed on another population does not carry over to ours.

**(b) Check by hand.** Each run prints every firm that merges more than one name. `firm_map.csv` lists, for each of the 1,912 names, the firm, the layer that decided it, the reason for the rule, its families and its `han_name`s, so every merge can be traced. The rules were written from a review of all names with 4 or more families and of every name that a group keyword matches without being merged (e.g. *… ELECTRIC POWER …*, *… POWER GRID …*). The printed list is checked again after every change to the rules.

## 6. Effect on the firms (2010–2018 scoring window)

| Before (`psn_name`) | Families | After (firm) | Families |
|---|---:|---|---:|
| SGCC (STATE GRID CORPORATION OF CHINA) | 149 | State Grid (SGCC) | 318 |
| KOBE STEEL | 104 | Kobe Steel | 104 |
| LSIS COMPANY | 43 | LS Electric | 62 |
| STATE GRID SHANGHAI MUNICIPAL ELECTRIC POWER | 20 | Panasonic | 25 |
| SAMSUNG SDI COMPANY | 18 | CEEG (XJ, Pinggao, XD) | 24 |
| GS YUASA INTERNATIONAL | 14 | Samsung SDI | 22 |
| NUOVO PIGNONE | 13 | China Southern Power Grid | 21 |
| HITACHI | 12 | GS Yuasa | 21 |
| PANASONIC INTELLECTUAL PROPERTY | 12 | Robert Bosch | 18 |
| ROBERT BOSCH | 12 | Toshiba | 16 |

The number of firms with at least 10 families in the window rises from 11 to 13. Subsidiaries of SGCC no longer appear as separate firms (e.g. *State Grid Shanghai* at rank 4), and Panasonic (with Sanyo), CEEG and CSG enter the top 10. In these tables families are **summed over names**, so a family filed under two names of the same firm counts twice. The exact counts, one per family and firm, are computed in Step 3 (`src/03_present_score.py`, which calls `firm_of` from `harmonize_firms.py`).

## 7. Limitations and choices to justify

1. **Ownership today vs. at filing.** Under our definition XJ and Pinggao count under CEEG, although they belonged to SGCC when most of their window patents were filed, and Dresser-Rand counts under Siemens Energy although it was independent before 2015. The other option, the owner at filing time, would need ownership histories that PATSTAT does not hold. Since the score answers "who holds the technology now", we keep today's owner.
2. **We follow names, not patents.** When a whole business changes owner, its *name* moves to the new group. Single patents sold or transferred later are not followed: PATSTAT has no reassignment data.
3. **SGCC dominates.** After merging, SGCC holds about 3 times the window families of the second firm. Because the volume indicator is linear, this can decide the ranking alone. One option is to compute volume on log(families) (`log_volume = True` in `src/03_present_score.py`) and report both versions. *[Team decision pending: currently `log_volume = False`.]*
4. **Ownership facts.** Each group rule rests on public company information (annual reports, company websites) as of 2025, and each needs a source in the final appendix. The names in Section 4 that we could not verify are left apart and listed, not guessed.
5. **Coverage.** Group rules cover the groups with roughly 5 or more families. A small group spread over many 1-family names that no rule catches stays split, but it would not pass the scoring threshold either way.

## 8. How to reproduce

From the `final/` folder, with the family list (Step 0) in `data/families.csv`:

```
pip install cleanco
python src/export_firm_names.py     # on TIP: applicant names from PATSTAT -> outputs/tables/firm_names.csv
python src/harmonize_firms.py       # mapping, checks, gold standard -> outputs/tables/firm_map.csv, firm_list.csv
python src/03_present_score.py      # uses firm_of()
```

To change a decision, edit `GROUP_RULES` (or move a name out of `TO_CHECK` into a rule), rerun `harmonize_firms.py` and check the printed list and the gold-standard precision.
