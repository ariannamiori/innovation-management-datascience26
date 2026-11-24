"""
Firm name harmonisation: from PATSTAT applicant names to firms
Team 27 · Utility-scale energy storage · client Enel

What it does
    Gives every PATSTAT standardised name (`psn_name`) a firm, in four layers, the first one that applies wins:
        1. normalise   full-width characters to ASCII (NFKC), upper case, single spaces
        2. translate   names written only in Chinese or Japanese: a small table of their Latin name;
                       mixed names ("テンポラル・パワー TEMPORAL POWER LTD.") keep their Latin part
        3. group       hand-written rules (GROUP_RULES): subsidiaries, branches and research institutes
                       merged into the group that owns them today
        4. clean       tutorial 1 method B: cleanco, then the legal-form dictionary of method A
    and checks the result:
        - pairwise precision / recall / F1 on the gold standard of tutorial 1 (same function as 11_competitive_landscape)
        - the names merged into each firm, for a check by hand
        - TO_CHECK: names that may belong to a group but whose ownership we could not verify

Input   outputs/tables/firm_names.csv (from export_firm_names.py): one row per name combination with its families
        ../tutorial_1/PATSTAT_500_label_datav4.csv: gold standard of the course repository (columns Group, comp)
Output  outputs/tables/firm_map.csv    one row per psn_name: firm, layer, families   (appendix: the full mapping)
        outputs/tables/firm_list.csv   one row per firm: names merged, families      (appendix: the groups)

Used by 03_present_score.py (`from harmonize_firms import firm_of`). Justification: docs/harmonize_firms.md.

    pip install cleanco
    python src/harmonize_firms.py                     # from final/
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from functools import lru_cache
from math import comb
from pathlib import Path

import pandas as pd

try:
    from cleanco import basename
except ImportError as e:                       # same package as tutorial 1, method B
    raise ImportError("harmonize_firms needs cleanco: pip install cleanco") from e

CONFIG = dict(
    names_csv="outputs/tables/firm_names.csv",
    gold_csv="../tutorial_1/PATSTAT_500_label_datav4.csv",
    out_dir="outputs/tables",
)

# --------------------------------------------------------------------------- layer 2: translations
# Names written only in Chinese or Japanese, and not caught by a group rule below. Their Latin name,
# as the same applicant is written elsewhere in PATSTAT, so the cleaning of layer 4 can merge them.
TRANSLATIONS = {
    "麦哲伦&巴伦支私人有限公司": "MAGELLAN & BARENTS",
    # "埃内欧储能系统有限公司": unknown firm (1 family), left as it is
}

# --------------------------------------------------------------------------- layer 3: groups
# One firm = the group that ultimately owns the named entity TODAY (wholly or majority owned), see the .md.
# Each rule: (firm, pattern, exclude, why). Patterns run on the normalised name; the first match wins,
# so a rule for a joint venture or a spin-off must come BEFORE the rule of its parent.
SGCC_PROVINCES = ("BEIJING|TIANJIN|HEBEI|JIBEI|SHANXI|SHAANXI|SHANDONG|SHANGHAI(?: MUNICIPAL)?|JIANGSU|ZHEJIANG|"
                  "ANHUI|FUJIAN|HUBEI|HUNAN|HENAN|JIANGXI|SICHUAN|CHONGQING|LIAONING|JILIN|HEILONGJIANG|"
                  "EAST INNER MONGOLIA|GANSU|QINGHAI|NINGXIA|XINJIANG|TIBET")
GROUP_RULES = [
    # --- Chinese grids. CEEG first: XJ, Pinggao (ex SGCC) and XD were moved into it in 2021
    ("CHINA ELECTRICAL EQUIPMENT GROUP (CEEG)", r"\bXUJI\b|\bXJ\b|\bPINGGAO\b|\bXD\b", None,
     "XJ Group and Pinggao (from SGCC) and China XD merged into CEEG in 2021"),
    ("CHINA SOUTHERN POWER GRID (CSG)",
     r"SOUTH(?:ERN)? ?POWER ?GRID|\bCSG\b|(?:GUANGDONG|GUANGXI|YUNNAN|GUIZHOU|HAINAN) ?POWER ?GRID"
     r"|SHENZHEN POWER SUPPLY BUREAU|GUANGZHOU POWER SUPPLY", None,
     "CSG and its five provincial grids (Guangdong, Guangxi, Yunnan, Guizhou, Hainan), their power supply bureaus and institutes"),
    ("STATE GRID (SGCC)",
     r"STATE GRID|\bSGCC\b|\bNARI\b|NANRUI|(?<!EAST )(?<!NORTH )CHINA ELECTRIC POWER RESEARCH INSTITUTE|CHINA-EPRI|GUODIANTONG"
     rf"|(?:^|\bOF |, )(?:{SGCC_PROVINCES}) ?ELECTRIC ?POWER (?:COMPANY|CORPORATION|GROUP|SUPPLY COMPANY"
     r"|(?:SCIENCE |TEST (?:& |AND )?)?RESEARCH INSTITUTE)", None,
     "SGCC, its provincial companies (also under their names before the 'State Grid' prefix), "
     "their branches and institutes, NARI (Nanrui), CEPRI, Guodiantong"),
    ("INNER MONGOLIA POWER GROUP", r"INNER MONGOLIA POWER \(GROUP\)", None,
     "provincial grid of western Inner Mongolia, owned by the region, not by SGCC"),
    # --- Chinese generation groups and engineering groups
    ("CHINA HUANENG GROUP", r"\bHUANENG\b|XI'?AN THERMAL POWER RESEARCH INSTITUTE", r"CHINA SALT HUANENG",
     "Huaneng subsidiaries and plants; Xi'an Thermal Power Research Institute (TPRI) is Huaneng's; "
     "China Salt Huaneng is a joint venture"),
    ("CHINA HUADIAN GROUP", r"\bHUADIAN\b|GUODIAN NANJING AUTOMATION|NANJING GUODIAN NANZI|NANJING SAC AUTOMATION",
     r"VALMET", "Huadian subsidiaries; Guodian Nanzi (SAC) is controlled by Huadian; Nanzi Valmet is a joint venture"),
    ("CHN ENERGY (GUODIAN + SHENHUA)",
     r"CHN ENERGY|CHINA ENERGY INVESTMENT|SHENHUA|GUOHUA|GUODIAN UNITED POWER|GUODIAN ENVIRONMENTAL|^LONGYUAN", None,
     "Guodian and Shenhua merged in 2017; only the Guodian units of CHN Energy (other 'Guodian' names are not)"),
    ("CHINA DATANG GROUP", r"\bDATANG\b", r"DATANG (?:TELECOM|MOBILE|MICROELECTRONICS|SEMICONDUCTOR)",
     "Datang power units; Datang Telecom is another group (CICT)"),
    ("STATE POWER INVESTMENT CORPORATION (SPIC)", r"\bSPIC\b|STATE POWER INVESTMENT|HUANGHE HYDROPOWER", None,
     "SPIC and its Huanghe Hydropower subsidiary"),
    ("CHINA THREE GORGES (CTG)", r"THREE GORGES|CHINA YANGTZE POWER|SHANGHAI INVESTIGATION,? DESIGN & RESEARCH INSTITUTE",
     None, "CTG, CTG Renewables, Yangtze Power (CTG-controlled), SIDRI (CTG subsidiary)"),
    ("POWERCHINA", r"POWERCHINA|POWER CONSTRUCTION CORPORATION OF CHINA|SINOHYDRO|HYDROCHINA", None,
     "Power Construction Corp. of China and its design institutes (ex HydroChina, Sinohydro)"),
    ("CHINA ENERGY ENGINEERING (CEEC)",
     r"CHINA ?ENERGY E(?:N)?GINEERING|CHINA POWER ENGINEERING CONSULTING|\bCEEC\b|GEZHOUBA|\bCGGC\b", None,
     "CEEC, its China Power Engineering Consulting design institutes, Gezhouba (CGGC)"),
    ("DONGFANG ELECTRIC", r"DONGFANG ELECTRIC(?!ONICS)|DONGFANG TURBINE|\bDEC DONGFANG", r"HITACHI",
     "Dongfang Electric Corp.; Dongfang Hitachi is a joint venture, Dongfang Electronics another firm"),
    ("SHANGHAI ELECTRIC", r"SHANGHAI ELECTRIC(?! POWER)", r"GUOXUAN",
     "Shanghai Electric Group; Shanghai Electric Guoxuan is a joint venture with Gotion"),
    ("CNPC (PETROCHINA)", r"PETROCHINA|\bCNPC\b", None, "PetroChina is majority-owned by CNPC"),
    ("SINOPEC", r"\bSINOPEC\b", None, "Sinopec units"),
    ("CNOOC", r"\bCNOOC\b", None, "CNOOC units"),
    ("CRRC", r"\bCRRC\b|\bCSR\b", None, "CSR and CNR merged into CRRC in 2015"),
    # --- Chinese private firms
    ("CATL", r"CONTEMPORARY AMPEREX|\bCATL\b|宁德时代", None, "Contemporary Amperex Technology and Ningde CATL"),
    ("BYD", r"\bBYD\b", None, "BYD and its subsidiaries"),
    ("SUNGROW", r"\bSUNGROW\b", None, "Sungrow Power Supply and Hefei Sungrow New Energy"),
    ("GOTION HIGH-TECH", r"\bGUOXUAN\b|\bGOTION\b", r"SHANGHAI ELECTRIC", "Hefei Guoxuan = Gotion; joint venture excluded"),
    ("HUAWEI", r"\bHUAWEI\b", None, "Huawei units"),
    ("MIDEA GROUP", r"\bMIDEA\b", None, "Midea units (Welling is Midea's)"),
    ("ENVISION ENERGY", r"ENVISION ENERGY", None, "Envision units"),
    ("DELTA ELECTRONICS", r"DELTA ELECTRONICS", None, "Delta units"),
    ("SINGYES", r"\bSINGYES\b", None, "Singyes units (Shuifa Singyes)"),
    ("BEIJING SIFANG AUTOMATION", r"BEIJING SIFANG", None, "Sifang units; CRRC Qingdao Sifang is another firm"),
    ("CHINT", r"\bCHINT", None, "Chint and its subsidiary Chintpower"),
    # --- Korea
    ("LG ENERGY SOLUTION", r"\bLG CHEM\b|LG ENERGY SOLUTION", None,
     "LG Chem spun off its battery unit as LG Energy Solution in 2020 (still majority owned)"),
    ("LG ELECTRONICS", r"LG ELECTRONICS|LG电子", None, "LG Innotek (about 41 % owned) stays separate"),
    ("SAMSUNG SDI", r"SAMSUNG SDI|三星SDI", r"YANGGUANG", "Samsung SDI only: the Samsung affiliates are separate firms"),
    ("LS ELECTRIC", r"\bLSIS\b|\bLS ?(?:INDUSTRIAL SYSTEMS|ELECTRIC)\b|LS ?(?:产电|电气)", None,
     "LS Industrial Systems = LSIS, renamed LS Electric in 2020; Chinese spellings"),
    ("KEPCO", r"KOREA ELECTRIC POWER CORP|\bKEPCO\b", None, "Korea Electric Power and its subsidiaries"),
    ("DOOSAN ENERBILITY", r"DOOSAN (?:HEAVY|ENERBILITY)", None, "Doosan Heavy Industries, renamed Doosan Enerbility in 2022"),
    # --- Japan (joint ventures between two groups stay separate: they come first or are excluded)
    ("PANASONIC", r"^(?:PANASONIC|MATSUSHITA|SANYO ELECTRIC)\b", r"TOSHIBA|SIEMENS",
     "Panasonic, its IP management unit, Panasonic Electric Works; Sanyo is wholly owned since 2011"),
    ("HITACHI", r"^HITACHI\b", r"MITSUBISHI|SUMITOMO", "Hitachi subsidiaries; joint ventures with Mitsubishi and Dongfang excluded"),
    ("TOSHIBA", r"^TOSHIBA\b", r"MITSUBISHI|MATSUSHITA", "Toshiba subsidiaries; TMEIC (with Mitsubishi Electric) excluded"),
    ("MITSUBISHI HEAVY INDUSTRIES", r"MITSUBISHI HEAVY|MITSUBISHI POWER|MITSUBISHI HITACHI POWER", None,
     "MHI and Mitsubishi Power; Mitsubishi Electric is a separate firm"),
    ("GS YUASA", r"GS ?YUASA|GSユアサ", None, "GS Yuasa and GS Yuasa International; Japanese spelling"),
    ("TEPCO", r"TOKYO ELECTRIC POWER", None, "Tokyo Electric Power and its holding"),
    # --- Europe and US. Spin-offs before their former parent
    ("SIEMENS ENERGY", r"^SIEMENS (?:ENERGY|GAMESA)|^西门子歌美飒|DRESSER-?RAND|德雷瑟", None,
     "spun off from Siemens in 2020; owns Siemens Gamesa and Dresser-Rand (bought by Siemens in 2015)"),
    ("SIEMENS", r"^(?:FIRMA )?SIEMENS\b|^西门子", None, "Siemens AG; Chinese spelling"),
    ("BAKER HUGHES", r"NUOVO PIGNONE|BAKER HUGHES", None, "Nuovo Pignone belongs to Baker Hughes (ex GE Oil & Gas)"),
    ("GENERAL ELECTRIC (GE)", r"^(?:THE )?GENERAL ELECTRIC\b|^GE \(|^ALSTOM TECHNOLOGY", r"P\.?L\.?C|\bGEC\b",
     "GE; Alstom Technology was bought by GE in 2015 (Alstom's power business)"),
    ("ABB", r"^ABB\b", None, "ABB units"),
    ("ROBERT BOSCH", r"^(?:ROBERT )?BOSCH\b|博世", r"SIEMENS", "Bosch; Chinese spelling. Lithium Energy and Power (joint venture) stays separate"),
    ("CLARIOS (EX JOHNSON CONTROLS POWER SOLUTIONS)",
     r"JOHNSON CONTROLS (?:AUTOBATTERIE|ADVANCED POWER|POWER SOLUTIONS)|CLARIOS", None,
     "the battery unit of Johnson Controls, sold in 2019 and renamed Clarios"),
    ("VESTAS", r"^VESTAS\b|维斯塔斯", None, "Vestas; Chinese spelling"),
    ("HONEYWELL", r"^HONEYWELL\b(?!-)|霍尼韦尔", r"PHILIPS|BULL", "Honeywell; Chinese spelling"),
    ("BMW", r"^BAYERISCHE MOTOREN WERKE|^BMW\b|宝马", None, "BMW; Chinese spelling"),
]
GROUP_RULES = [(firm, re.compile(p), re.compile(x) if x else None, why) for firm, p, x, why in GROUP_RULES]

# Names that may belong to a group, left as they are because we could not verify who owns them.
TO_CHECK = {
    "EAST CHINA ELECTRIC POWER RESEARCH INSTITUTE COMPANY": "SGCC? (East China branch)",
    "NORTH CHINA ELECTRICAL POWER RESEARCH INSTITUTE COMPANY": "SGCC? (North China branch / State Grid Jibei)",
    "BEIJING ELECTRIC POWER ECONOMIC TECHNOLOGY RESEARCH INSTITUTE": "SGCC? (State Grid Beijing)",
    "SHANDONG ELECTRIC POWER ENGINEERING CONSULTING INSTITUTE COMPANY": "CEEC? (via China Power Engineering Consulting)",
    "CHANGZHOU NR ELECTRIC POWER ELECTRONICS COMPANY": "SGCC? (NR Electric is a NARI company)",
    "NR ELECTRIC POWER ELECTRONICS COMPANY": "SGCC? (NR Electric is a NARI company)",
    "HANGZHOU GUODIAN DAM SAFETY ENGINEERING COMPANY": "SGCC or CHN Energy? ('Guodian' only means 'national power')",
    "CHANGJIANG INSTITUTE OF SURVEY, PLANNING, DESIGN AND RESEARCH": "not CTG: Changjiang Water Resources Commission",
    "LG INNOTEK COMPANY": "LG Electronics owns about 41 %: below our majority rule",
    "TOYOTA INDUSTRIES CORPORATION": "Toyota Motor owns about 24 %: below our majority rule",
}

# --------------------------------------------------------------------------- layer 4: cleaning (tutorial 1)
LEGAL_FORMS = {                                 # tutorial 1 method A, plus KGAA
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "LLC", "LP", "PLC",
    "GMBH", "AG", "KG", "MBH", "SE", "SA", "SAS", "SPA", "SRL", "BV", "NV", "AB", "AS", "ASA", "OY", "OYJ",
    "KK", "KABUSHIKI", "KAISHA", "LTDA", "PTY", "THE", "AKTIENGESELLSCHAFT", "GESELLSCHAFT", "KGAA",
}


def normalise(name) -> str:
    """Layer 1: full-width to ASCII, upper case, single spaces."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(name)).upper()).strip()


def clean_with_dictionary(name: str) -> str:
    """Tutorial 1 method A: letters and digits only, '&' read as AND, legal forms dropped at both ends."""
    words = re.sub(r"[^A-Z0-9 ]", " ", name.upper().replace("&", " AND ")).split()
    while words and (words[-1] in LEGAL_FORMS or words[-1] == "AND"):
        words.pop()
    while words and (words[0] in LEGAL_FORMS or words[0] == "AND"):
        words.pop(0)
    return " ".join(words)


def clean_with_cleanco(name: str) -> str:
    """Tutorial 1 method B: cleanco first, then method A."""
    return clean_with_dictionary(basename(name))


def latin_part(name: str) -> str:
    """'テンポラル・パワー・リミテッドTEMPORAL POWER LTD.' -> 'TEMPORAL POWER LTD.' ('' if too little Latin text)."""
    latin = re.sub(r"[^\x00-\x7F]+", " ", name)
    latin = re.sub(r"\s+", " ", latin).strip(" ,.、")
    return latin if len(re.findall(r"[A-Z]", latin)) >= 3 else ""


# --------------------------------------------------------------------------- the function used by Step 3
@lru_cache(maxsize=None)
def harmonise(psn_name) -> tuple[str, str]:
    """(firm, layer that decided it) for one psn_name."""
    original = name = normalise(psn_name)
    layer = "cleaned"
    if name in TRANSLATIONS:
        name, layer = TRANSLATIONS[name], "translated"
    elif re.search(r"[^\x00-\x7F]", name) and latin_part(name):
        name, layer = latin_part(name), "latin part"
    for candidate in dict.fromkeys([original, name]):     # the rules also read the Chinese/Japanese spelling
        for firm, pattern, exclude, _ in GROUP_RULES:
            if pattern.search(candidate) and not (exclude and exclude.search(candidate)):
                return firm, "group"
    cleaned = clean_with_cleanco(name)
    if not cleaned:                              # e.g. a name only in Chinese: never merge on an empty key
        return name, "unchanged (non-Latin)"
    return cleaned, layer


def firm_of(psn_name) -> str:
    """The firm of one psn_name (used by 03_present_score.py)."""
    return harmonise(psn_name)[0]


# --------------------------------------------------------------------------- evaluation (tutorial 1, section 2.4)
def pairs_inside(group_sizes) -> int:
    return sum(comb(int(n), 2) for n in group_sizes)


def precision_recall_f1(gold_groups, predicted_groups) -> dict:
    """Pairwise precision, recall and F1 of a predicted grouping against the gold groups (as tutorial 1)."""
    df = pd.DataFrame({"gold": list(gold_groups), "pred": list(predicted_groups)})
    tp = pairs_inside(df.groupby(["gold", "pred"]).size())
    tp_fp = pairs_inside(df.groupby("pred").size())
    tp_fn = pairs_inside(df.groupby("gold").size())
    precision = tp / tp_fp if tp_fp else 1.0
    recall = tp / tp_fn if tp_fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"groups found": df["pred"].nunique(), "precision": precision, "recall": recall, "F1": f1}


def first_word(name) -> str:
    return (clean_with_dictionary(normalise(name)).split() or [""])[0]


def evaluate_on_gold(path: str | Path) -> pd.DataFrame:
    """Every method of tutorial 1 and ours on a gold standard with columns Group, comp."""
    gold = pd.read_csv(path).rename(columns={"comp": "name", "Group": "gold_group"})
    methods = {
        "psn_name as it is": lambda n: n,
        "A · dictionary": lambda n: clean_with_dictionary(normalise(n)),
        "B · cleanco": lambda n: clean_with_cleanco(normalise(n)),
        "first word (rejected, see .md)": first_word,
        "ours (4 layers)": firm_of,
    }
    rows = {m: precision_recall_f1(gold.gold_group, gold.name.map(f)) for m, f in methods.items()}
    out = pd.DataFrame(rows).T
    out.insert(0, "organisations", gold.gold_group.nunique())
    return out


# --------------------------------------------------------------------------- main
def build_tables(names: pd.DataFrame):
    """firm_map (one row per psn_name) and firm_list (one row per firm)."""
    per_name = names.groupby("psn_name").agg(
        families=("families", "sum"), families_in_window=("families_in_window", "sum"),
        han_names=("han_name", lambda s: " | ".join(sorted(set(s.dropna().astype(str))))),
    ).reset_index()
    decided = per_name.psn_name.map(harmonise)
    per_name["firm"] = decided.str[0]
    per_name["layer"] = decided.str[1]
    rule = {firm: why for firm, _, _, why in GROUP_RULES}
    per_name["why"] = per_name.firm.map(rule).fillna("")
    per_name = per_name.sort_values(["firm", "families"], ascending=[True, False])

    firm_list = per_name.groupby("firm").agg(
        n_names=("psn_name", "size"), families=("families", "sum"), families_in_window=("families_in_window", "sum"),
        layer=("layer", lambda s: s.mode().iat[0]),
        names=("psn_name", lambda s: " | ".join(s.head(8)) + (" | ..." if len(s) > 8 else "")),
    ).sort_values("families", ascending=False).reset_index()
    return per_name[["psn_name", "firm", "layer", "families", "families_in_window", "han_names", "why"]], firm_list


def main(cfg=CONFIG):
    names = pd.read_csv(cfg["names_csv"])
    firm_map, firm_list = build_tables(names)

    out = Path(cfg["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    firm_map.to_csv(out / "firm_map.csv", index=False)
    firm_list.to_csv(out / "firm_list.csv", index=False)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 90)
    print(f"{len(firm_map):,} psn_names -> {len(firm_list):,} firms   (saved to {out}/firm_map.csv, firm_list.csv)")
    print("Names decided by each layer:", firm_map.layer.value_counts().to_dict())
    print("Families are summed over names: a family filed under two names counts twice (exact counts: Step 3).\n")

    print("Gold standard of tutorial 1 (pairwise precision / recall / F1):")
    print(evaluate_on_gold(cfg["gold_csv"]).round(3).to_string(), "\n")

    fw = pd.Series([first_word(n) for n in firm_map.psn_name]).value_counts()
    print("Why not 'first word' on our names: it would merge", {k: int(v) for k, v in fw.head(5).items()}, "\n")

    print("Firms that merge more than one name (check by hand):")
    multi = firm_list[firm_list.n_names > 1]
    print(multi.head(40)[["firm", "n_names", "families", "families_in_window", "layer"]].to_string(index=False), "\n")

    print("Top 20 before (psn_name) and after (firm), families in the scoring window:")
    before = firm_map.groupby("psn_name").families_in_window.sum().nlargest(20)
    after = firm_list.set_index("firm").families_in_window.nlargest(20)
    print(pd.DataFrame({"psn_name": before.index, "fam": before.values,
                        "firm": after.index, "fam ": after.values}).to_string(index=False), "\n")

    present = firm_map[firm_map.psn_name.isin(TO_CHECK)]
    print("Ownership to verify (TO_CHECK), not merged into any group:")
    print(present.assign(note=present.psn_name.map(TO_CHECK))[["psn_name", "firm", "families", "note"]].to_string(index=False))
    wrongly = present[present.layer == "group"]
    if len(wrongly):
        print("WARNING, a rule merges names that should stay apart:", wrongly.psn_name.tolist())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Harmonise PATSTAT applicant names into firms")
    parser.add_argument("--names", default=CONFIG["names_csv"], help="output of export_firm_names.py")
    parser.add_argument("--gold", default=CONFIG["gold_csv"], help="gold standard with columns Group, comp")
    parser.add_argument("--out-dir", default=CONFIG["out_dir"])
    a = parser.parse_args()
    main({**CONFIG, "names_csv": a.names, "gold_csv": a.gold, "out_dir": a.out_dir})
