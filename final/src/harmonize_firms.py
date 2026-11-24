"""
Firm name harmonisation: from PATSTAT applicant names to firms
Team 27 · Utility-scale energy storage · client Enel

Two names are merged only when the data shows they belong together, in four steps. The result is
deterministic, and every merge records its evidence in firm_map.csv.
    1. same key     same name after tutorial 1 method B (cleanco, then the legal-form dictionary of method A)
    2. variant      same first word and length, the other words equal or abbreviated (IND / INDUSTRIES)
    3. shared id    same OECD HAN id or DOCDB standard-name id, AND one name begins with the other
    4. group name   the name contains the group name of another firm in the data, at the start of a part of the
                    name, after a place word or after "OF" ("NANJING POWER SUPPLY BRANCH OF STATE GRID JIANGSU ...").
                    Group name = the firm's name without organisational words at the end and "CHINA" at the start
                    ("CHINA HUANENG GROUP CORPORATION" -> "HUANENG"); it needs one distinctive word. A name that
                    also contains another firm's group name is a possible joint venture and is left apart.
    5. manual       MANUAL_MERGES: the one case the names cannot show that we checked by hand (see the .md)

Input   outputs/tables/firm_names.csv (export_firm_names.py) · ../tutorial_1/PATSTAT_500_label_datav4.csv (gold standard)
Output  outputs/tables/firm_map.csv (one row per psn_name) · outputs/tables/firm_list.csv (one row per firm)
Used by 03_present_score.py through firm_of().    Run from final/:  python src/harmonize_firms.py
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from math import comb
from pathlib import Path

import pandas as pd
from cleanco import basename                      # tutorial 1, method B (pip install cleanco)

ROOT = Path(__file__).resolve().parents[1]        # final/
NAMES_CSV = ROOT / "outputs/tables/firm_names.csv"
GOLD_CSV = ROOT.parent / "tutorial_1/PATSTAT_500_label_datav4.csv"
OUT = ROOT / "outputs/tables"

# Firms (labels from steps 1-4) that are one company although no name shows it. Found in the Step 3 ranking,
# where LS Electric appeared three times; each merge cites its source.
MANUAL_MERGES = {
    "LS ELECTRIC": (["LSIS", "LS", "LS ELECTRIC"],     # LSIS = LS Industrial Systems; LS产电 / LS电气 = its Chinese names
                    "renamed LS ELECTRIC on 24 Mar 2020, The Asia Business Daily: "
                    "https://view.asiae.co.kr/en/article/2020032410135513971"),
}

LEGAL_FORMS = {                                   # tutorial 1, method A (+ KGAA)
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "LLC", "LP", "PLC", "GMBH",
    "AG", "KG", "MBH", "SE", "SA", "SAS", "SPA", "SRL", "BV", "NV", "AB", "AS", "ASA", "OY", "OYJ", "KK", "KABUSHIKI",
    "KAISHA", "LTDA", "PTY", "THE", "AKTIENGESELLSCHAFT", "GESELLSCHAFT", "KGAA",
}
ORG_WORDS = LEGAL_FORMS | {"GROUP", "HOLDING", "HOLDINGS", "OF", "AND", "INTERNATIONAL", "RESEARCH", "INSTITUTE",
                           "CENTER", "CENTRE", "BRANCH", "BUREAU", "CHINA"}
SECTOR_WORDS = set("""ELECTRIC ELECTRICAL ELECTRICITY ELECTRONIC ELECTRONICS POWER ENERGY GRID NEW STORAGE BATTERY
    SUPPLY GENERATION NUCLEAR WIND SOLAR HYDRO HYDROPOWER THERMAL TECHNOLOGY TECHNOLOGIES TECH SCIENCE ENGINEERING
    DESIGN DEVELOPMENT SYSTEM SYSTEMS SERVICE SERVICES SOLUTIONS EQUIPMENT INDUSTRIAL INDUSTRIES INDUSTRY
    MANUFACTURING AUTOMATION CONTROL SMART INTELLIGENT ECONOMIC TEST PLANNING CONSTRUCTION INVESTMENT MOTOR
    CONSULTING MATERIALS CHEMICAL PRODUCTS INNOVATION PLANT STATION LITHIUM HYDROGEN FUEL CELL PHOTOVOLTAIC WATER
    GAS OIL COAL CLEAN GREEN RENEWABLE AUTOMOBILE GLOBAL CITY COUNTY DISTRICT TRAINING MARKETING TECHNICAL""".split())
PLACES = set("""CHINA NATIONAL JAPAN KOREA AMERICA USA EUROPE GERMANY EAST WEST NORTH SOUTH CENTRAL EASTERN WESTERN
    NORTHERN SOUTHERN NORTHEAST NORTHWEST SOUTHEAST SOUTHWEST INNER MONGOLIA BEIJING TIANJIN HEBEI JIBEI SHANXI
    LIAONING JILIN HEILONGJIANG SHANGHAI JIANGSU ZHEJIANG ANHUI FUJIAN JIANGXI SHANDONG HENAN HUBEI HUNAN GUANGDONG
    GUANGXI HAINAN CHONGQING SICHUAN GUIZHOU YUNNAN TIBET SHAANXI GANSU QINGHAI NINGXIA XINJIANG HONG KONG TAIWAN
    SHENZHEN GUANGZHOU NANJING HANGZHOU WUHAN CHENGDU XIAN SUZHOU HEFEI QINGDAO DALIAN SHENYANG XIAMEN NINGBO
    ZHENGZHOU CHANGSHA JINAN FUZHOU KUNMING NANCHANG HARBIN CHANGCHUN TAIYUAN LANZHOU GUIYANG NANNING ZHUHAI FOSHAN
    WUXI CHANGZHOU NANTONG XUCHANG ZHUZHOU BAODING""".split())
GENERIC = ORG_WORDS | SECTOR_WORDS | PLACES


# --------------------------------------------------------------------------- names
def normalise(name) -> str:
    """Full-width to ASCII (NFKC), upper case, no apostrophes (XI'AN -> XIAN), single spaces."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(name)).upper().replace("'", "")).strip()


def clean_with_dictionary(name: str) -> str:
    """Tutorial 1 method A: letters and digits only, '&' read as AND, legal forms dropped at both ends."""
    words = re.sub(r"[^A-Z0-9 ]", " ", name.upper().replace("&", " AND ")).split()
    while words and words[-1] in LEGAL_FORMS | {"AND"}:
        words.pop()
    while words and words[0] in LEGAL_FORMS | {"AND"}:
        words.pop(0)
    return " ".join(words)


def name_key(name) -> str:
    """Tutorial 1 method B (cleanco, then method A). A name with no Latin letters keeps its own form."""
    n = normalise(name)
    return clean_with_dictionary(basename(n)) or n


def group_name(key: str) -> tuple | None:
    """The name a firm gives its subsidiaries, or None if it has no distinctive word (3+ letters, not generic)."""
    words = key.split()
    while words and words[-1] in ORG_WORDS:
        words.pop()
    while words and words[0] == "CHINA":
        words.pop(0)
    return tuple(words) if any(w not in GENERIC and len(w) >= 3 and not w.isdigit() for w in words) else None


def positions(words):
    """Where a group name may start in one part of a name: at the start, after a place word, after OF (CHINA)."""
    yield 0
    if words and words[0] in PLACES:
        yield 1
    for i, w in enumerate(words):
        if w == "OF":
            yield i + 1
            if words[i + 1:i + 2] == ["CHINA"]:
                yield i + 2


def is_variant(a: list, b: list) -> bool:
    """Same first word and length; every other word equal or a 3+ letter prefix of the other."""
    def abbrev(x, y):
        s, l = sorted((x, y), key=len)
        return x == y or (len(s) >= 3 and l.startswith(s))
    return len(a) == len(b) >= 2 and a[0] == b[0] and all(abbrev(x, y) for x, y in zip(a[1:], b[1:]))


# --------------------------------------------------------------------------- the map
def build_map(names: pd.DataFrame) -> pd.DataFrame:
    """One row per psn_name: firm, step, evidence. `names` needs psn_name; families, han_id, han_name and
    doc_std_name_id are used when present."""
    names = names.assign(families=names.get("families", 1))
    fam = names.groupby("psn_name").families.sum()
    psn = sorted(fam.index)
    key = {n: name_key(n) for n in psn}
    parent = {n: n for n in psn}
    evidence = {}

    def find(n):
        while parent[n] != n:
            n = parent[n]
        return n

    def merge(a, b, step, why):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)              # deterministic root
            evidence.setdefault(a, (step, why))

    # 1 · same key, 2 · spelling variant
    first = {}
    for n in psn:
        if key[n] in first:
            merge(n, first[key[n]], "1 same key", f"same cleaned name as '{first[key[n]]}'")
        first.setdefault(key[n], n)
    buckets = defaultdict(list)
    for k, n in first.items():
        buckets[(k.split()[0], len(k.split()))].append(n)
    for ns in buckets.values():
        for i, a in enumerate(ns):
            for b in ns[i + 1:]:
                if is_variant(key[a].split(), key[b].split()):
                    merge(a, b, "2 variant", f"spelling variant of '{b}'")

    # 3 · shared PATSTAT identifier, and one name begins with the other
    for col in ("han_id", "doc_std_name_id"):
        if col in names:
            for ident, group in names.dropna(subset=[col]).groupby(col).psn_name:
                ms = sorted(set(group))
                for i, a in enumerate(ms):
                    for b in ms[i + 1:]:
                        x, y = sorted((key[a].split(), key[b].split()), key=len)
                        if y[:len(x)] == x:
                            merge(a, b, "3 shared id", f"same {col} {int(ident)} as '{b}', one name begins with the other")

    # 4 · group name of another firm in the data (its psn_name, or its han_name when the HAN id is its alone)
    aliases = {n: {key[n]} for n in psn}
    if "han_name" in names:
        alone = names.groupby("han_id").psn_name.transform("nunique") == 1
        for n, h in names.loc[alone, ["psn_name", "han_name"]].dropna().itertuples(index=False):
            aliases[n].add(name_key(h))
    groups = {}                                            # group name -> the firm it comes from
    for n in psn:
        for k in sorted(aliases[n]):
            g = group_name(k)
            if g and (g not in groups or len(key[n]) < len(key[groups[g]])):
                groups[g] = n
    by_first = defaultdict(list)
    for g in groups:
        by_first[g[0]].append(g)
    parts = {n: [clean_with_dictionary(p).split() for p in normalise(n).split(",") if p.strip()] for n in psn}

    def found_in(n, anywhere=False):
        hits = []
        for p, words in enumerate(parts[n]):
            for i in (range(len(words)) if anywhere else set(positions(words))):
                for g in by_first.get(words[i] if i < len(words) else None, []):
                    if words[i:i + len(g)] == list(g) and groups[g] != n:
                        hits.append((g, p, i))
        return hits

    heads = {}                                             # firm -> its group name that merged others
    for n in psn:
        hits = found_in(n)
        if not hits:
            continue
        g, p, i = min(hits, key=lambda h: (len(h[0]), h[1], h[2]))
        lineage = {find(groups[h]) for h, _, _ in hits if h[:len(g)] == g}
        others = {" ".join(h) for h, q, j in found_in(n, anywhere=True)
                  if not (q == p and i <= j < i + len(g)) and h[0] not in PLACES and find(groups[h]) not in lineage}
        if others:
            evidence[n] = ("0 kept", f"possible joint venture: contains '{' '.join(g)}' and {sorted(others)}")
            continue
        heads[groups[g]] = min(heads.get(groups[g], g), g, key=len)
        merge(n, groups[g], "4 group name", f"contains the group name '{' '.join(g)}' of '{groups[g]}'")

    # label: the group name that merged the firm, else the cleaned name of its largest name
    members = defaultdict(list)
    for n in psn:
        members[find(n)].append(n)
    label = {}
    for ms in members.values():
        hs = [heads[m] for m in ms if m in heads]
        name = " ".join(min(hs, key=lambda g: (len(g), g))) if hs else key[max(ms, key=lambda m: (fam[m], m.isascii(), m))]
        label.update({m: name for m in ms})

    # 5 · manual merges, each with its source
    for firm, (labels, source) in MANUAL_MERGES.items():
        for n in psn:
            if label[n] in labels:
                if label[n] != firm:
                    evidence[n] = ("5 manual", f"merged with '{firm}': {source}")
                label[n] = firm
    return pd.DataFrame({
        "psn_name": psn, "firm": [label[n] for n in psn], "families": [fam[n] for n in psn],
        "step": [evidence.get(n, ("0 kept", ""))[0] for n in psn],
        "evidence": [evidence.get(n, ("", ""))[1] for n in psn],
    })


def firm_of(psn_name) -> str:
    """The firm of one psn_name, from firm_map.csv (03_present_score.py); a name not in the map is its own firm."""
    if not hasattr(firm_of, "lookup"):
        m = pd.read_csv(OUT / "firm_map.csv")
        firm_of.lookup = dict(zip(m.psn_name, m.firm))
    return firm_of.lookup.get(psn_name) or name_key(psn_name)


# --------------------------------------------------------------------------- evaluation (tutorial 1, section 2.4)
def precision_recall_f1(gold_groups, predicted_groups) -> dict:
    """Pairwise precision, recall and F1 of a predicted grouping against the gold groups."""
    df = pd.DataFrame({"gold": list(gold_groups), "pred": list(predicted_groups)})
    pairs = lambda sizes: sum(comb(int(s), 2) for s in sizes)
    tp, tp_fp, tp_fn = pairs(df.groupby(["gold", "pred"]).size()), pairs(df.groupby("pred").size()), pairs(df.groupby("gold").size())
    p, r = (tp / tp_fp if tp_fp else 1.0), (tp / tp_fn if tp_fn else 1.0)
    return {"groups found": df.pred.nunique(), "precision": p, "recall": r, "F1": 2 * p * r / (p + r) if p + r else 0.0}


def evaluate_on_gold(path=GOLD_CSV) -> pd.DataFrame:
    gold = pd.read_csv(path).rename(columns={"comp": "psn_name", "Group": "gold"})
    ours = build_map(gold[["psn_name"]]).set_index("psn_name").firm
    methods = {"psn_name as it is": gold.psn_name,
               "A · dictionary": gold.psn_name.map(lambda n: clean_with_dictionary(normalise(n))),
               "B · cleanco": gold.psn_name.map(name_key),
               "ours (steps 1, 2, 4: the gold standard has no ids)": gold.psn_name.map(ours)}
    return pd.DataFrame({m: precision_recall_f1(gold.gold, p) for m, p in methods.items()}).T


# --------------------------------------------------------------------------- main
def main():
    names = pd.read_csv(NAMES_CSV)
    fmap = build_map(names)
    fmap["families_in_window"] = fmap.psn_name.map(names.groupby("psn_name").families_in_window.sum())
    fmap = fmap.sort_values(["firm", "families"], ascending=[True, False])
    flist = (fmap.groupby("firm").agg(n_names=("psn_name", "size"), families=("families", "sum"),
                                      families_in_window=("families_in_window", "sum"),
                                      names=("psn_name", lambda s: " | ".join(s.head(8))))
             .sort_values("families", ascending=False).reset_index())
    OUT.mkdir(parents=True, exist_ok=True)
    fmap.to_csv(OUT / "firm_map.csv", index=False)
    flist.to_csv(OUT / "firm_list.csv", index=False)

    pd.set_option("display.width", 200)
    print(f"{len(fmap):,} psn_names -> {len(flist):,} firms (saved to {OUT})")
    print("Names merged by each step:", fmap.step.value_counts().sort_index().to_dict(), "\n")
    print("Gold standard of tutorial 1:\n" + evaluate_on_gold().round(3).to_string(), "\n")
    print("Firms with more than one name:\n" + flist[flist.n_names > 1].head(25).drop(columns="names").to_string(index=False), "\n")
    jv = fmap[fmap.evidence.str.startswith("possible joint venture")]
    print("Left apart, possible joint ventures:\n" + jv[["psn_name", "evidence"]].to_string(index=False))


if __name__ == "__main__":
    main()
