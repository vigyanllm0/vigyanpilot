"""universal_mirror.py — Python mirror of frontend/qpcr/qpcr-universal.js.

Universal Format Engine (QPCR_UNIVERSAL_FORMAT_SUPPORT_TASKS.md):
  sniff content → decode (BOM / UTF-16) → known fast paths (RDML / CFX /
  template) → UNIVERSAL LAYOUT REASONER (column aliases → sections → blocks →
  sameWell merge) → format doctor when nothing matches.

Kept in lockstep with the JS module — tests/test_universal.py runs the same
fixtures through BOTH (JS via node subprocess) and compares canonical runs.

The canonical run shape comes from qpcr_mirror (make_run / make_well / …).
"""
import io
import os
import re
import struct
import zipfile

from qpcr_mirror import (
    canonical_channel,
    detect_format,
    guess_reference,
    guess_sample_type,
    make_channel,
    make_run,
    make_sample,
    make_target,
    make_well,
    parse_cfx_csv,
    parse_position,
    parse_rdml,
    parse_template,
)

ROTOR_EXTS = ["qbd", "qbg", "qbt", "rgd", "rgx", "rex"]

# Supported formats list (format doctor "what works" section — identical in JS)
SUPPORTED_FORMATS = [
    "RDML (.rdml) — full curves + Cq",
    "Bio-Rad CFX CSV — sectioned or long-format",
    "Template CSV/TSV — Well, Sample, Target, Channel, Cq",
    "Any instrument CSV/TSV/TXT — universal layout reasoner",
    "Excel .xlsx — native (ZIP + XML)",
    "Legacy Excel .xls — native OLE2/BIFF8 reader",
    "ZIP — deep-probes inner .csv/.tsv/.txt/.rdml/.xlsx",
]


class FormatError(Exception):
    """Raised when the format doctor rejects a file. `.doctor` carries the card."""

    def __init__(self, message, doctor=None):
        super().__init__(message)
        self.doctor = doctor or {}


# ─────────────────────────────────────────────────────────────────
# 1. Container sniffing (magic bytes — never the extension)
# ─────────────────────────────────────────────────────────────────
def sniff(u8):
    if len(u8) >= 4:
        if u8[0] == 0x50 and u8[1] == 0x4B and u8[2] == 0x03 and u8[3] == 0x04:
            return "zip"
        if u8[0] == 0xD0 and u8[1] == 0xCF and u8[2] == 0x11 and u8[3] == 0xE0:
            return "ole"
        if u8[0] == 0x1F and u8[1] == 0x8B:
            return "gzip"
    head = u8[:1000]
    if b"\x00" in head:
        # UTF-16 without BOM: NULs must be on a consistent parity side
        if len(head) >= 8:
            even_nul = sum(1 for i in range(0, len(head) - 1, 2) if head[i] == 0)
            odd_nul = sum(1 for i in range(1, len(head), 2) if head[i] == 0)
            pairs = len(head) // 2
            if pairs and (even_nul > pairs * 0.3 or odd_nul > pairs * 0.3) and \
               abs(even_nul - odd_nul) > pairs * 0.25:
                return "text"
        return "binary"
    return "text"


def ext_of(file_name):
    base = os.path.basename(file_name or "")
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[-1].lower()


# ─────────────────────────────────────────────────────────────────
# 2. Decoding (BOM-aware; UTF-16 no-BOM via NUL parity)
# ─────────────────────────────────────────────────────────────────
def decode_text(u8):
    if u8[:3] == b"\xef\xbb\xbf":
        return u8[3:].decode("utf-8", "replace")
    if u8[:2] == b"\xff\xfe":
        return u8[2:].decode("utf-16-le", "replace")
    if u8[:2] == b"\xfe\xff":
        return u8[2:].decode("utf-16-be", "replace")
    # UTF-16 without BOM: NUL parity decides.
    # LE ASCII: char bytes at even indices, NULs at ODD. BE: NULs at EVEN.
    if b"\x00" in u8[:200] and len(u8) >= 4:
        even_nul = sum(1 for i in range(0, min(len(u8), 1000) - 1, 2) if u8[i] == 0)
        odd_nul = sum(1 for i in range(1, min(len(u8), 1000), 2) if u8[i] == 0)
        if even_nul > 40 and even_nul > odd_nul * 3:
            return u8.decode("utf-16-be", "replace")
        if odd_nul > 40 and odd_nul > even_nul * 3:
            return u8.decode("utf-16-le", "replace")
    return u8.decode("utf-8", "replace")


def _is_number(v):
    try:
        f = float(str(v).strip())
    except (TypeError, ValueError):
        return False
    return f == f  # not NaN


def _num(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if _is_number(v):
        return float(str(v).strip())
    return None


def _s(v):
    """Normalize a cell to a string for header matching (1.0 → '1')."""
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


# ─────────────────────────────────────────────────────────────────
# 3. Delimiter detection + quote-aware row split
# ─────────────────────────────────────────────────────────────────
def _split_line(line, delim):
    out, cur, in_q = [], [], False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            if in_q and i + 1 < len(line) and line[i + 1] == '"':
                cur.append('"')
                i += 1
            else:
                in_q = not in_q
        elif ch == delim and not in_q:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    out.append("".join(cur))
    return out


def split_rows(text, delim):
    rows = []
    for raw in text.split("\n"):
        line = raw.rstrip("\r")
        if not line.strip():
            continue
        rows.append([c.strip() if isinstance(c, str) else c for c in _split_line(line, delim)])
    return rows


def detect_delimiter(text):
    candidates = [",", "\t", ";", "|"]
    lines = [l for l in text.split("\n") if l.strip()][:15]
    if not lines:
        return ","
    best, best_score = ",", 0.0
    for d in candidates:
        counts = [len(_split_line(l, d)) for l in lines]
        modal = max(set(counts), key=counts.count)
        if modal < 2:
            continue
        consistency = counts.count(modal) / len(counts)
        score = consistency * 10 + min(modal, 40) * 0.1
        if score > best_score:
            best, best_score = d, score
    return best


# ─────────────────────────────────────────────────────────────────
# 4. Column alias table (~90 entries — data, not code)
#    norm_key form: lowercase, non-alnum → single space, stripped
# ─────────────────────────────────────────────────────────────────
COLUMN_ALIASES = [
    # well / position
    ("well", "well"), ("well id", "well"), ("well position", "well"), ("well pos", "well"),
    ("well name", "well"), ("well label", "well"), ("well no", "well"), ("well number", "well"),
    ("position", "well"), ("pos", "well"), ("pos id", "well"), ("chamber", "well"),
    ("chamber id", "well"), ("location", "well"),
    # sample
    ("sample", "sample"), ("sample name", "sample"), ("sample id", "sample"),
    ("sample label", "sample"), ("sample no", "sample"), ("sample number", "sample"),
    ("specimen", "sample"), ("specimen name", "sample"), ("name", "sample"),
    ("sample s", "sample"),
    # target / assay
    ("target", "target"), ("target name", "target"), ("target id", "target"),
    ("assay", "target"), ("assay name", "target"), ("assay id", "target"),
    ("gene", "target"), ("gene name", "target"), ("oligo", "target"), ("oligo name", "target"),
    ("detection", "target"), ("detection name", "target"), ("amplicon", "target"),
    ("amplicon name", "target"), ("target assay", "target"),
    # dye / channel
    ("dye", "dye"), ("dye name", "dye"), ("fluor", "dye"), ("fluorophore", "dye"),
    ("reporter", "dye"), ("channel", "dye"), ("signal channel", "dye"),
    ("fam", "dye"), ("hex", "dye"), ("vic", "dye"), ("joe", "dye"), ("tet", "dye"),
    ("rox", "dye"), ("texas red", "dye"), ("texasred", "dye"), ("cy5", "dye"),
    ("cy 5", "dye"), ("cy5 5", "dye"), ("tamra", "dye"), ("ned", "dye"),
    ("quasar", "dye"), ("quasar 670", "dye"), ("quasar 705", "dye"),
    ("sybr", "dye"), ("sybr green", "dye"), ("sybr green i", "dye"),
    ("eva green", "dye"), ("evagreen", "dye"), ("lc green", "dye"),
    ("cal gold 540", "dye"), ("cal orange 560", "dye"),
    # sample type
    ("type", "stype"), ("sample type", "stype"), ("content", "stype"), ("task", "stype"),
    ("category", "stype"), ("class", "stype"), ("sample class", "stype"), ("role", "stype"),
    ("sample role", "stype"), ("well type", "stype"),
    # quantity / concentration
    ("qty", "qty"), ("quantity", "qty"), ("conc", "qty"), ("concentration", "qty"),
    ("std quantity", "qty"), ("standard quantity", "qty"), ("copy number", "qty"),
    ("copies", "qty"), ("input quantity", "qty"), ("amount", "qty"), ("dilution", "qty"),
    # Cq / Ct / Cp
    ("cq", "cq"), ("ct", "cq"), ("cp", "cq"), ("cq mean", "cq"), ("ct mean", "cq"),
    ("threshold cycle", "cq"), ("cq value", "cq"), ("ct value", "cq"),
    ("cq result", "cq"), ("ct result", "cq"),
    # Cq dispersion
    ("cq sd", "cqsd"), ("cq std dev", "cqsd"), ("cq stddev", "cqsd"),
    ("ct sd", "cqsd"), ("ct std dev", "cqsd"), ("ct stddev", "cqsd"),
    ("standard deviation", "cqsd"), ("sd", "cqsd"), ("cq std", "cqsd"), ("ct std", "cqsd"),
    # melt temperature (per-well Tm result)
    ("tm", "tm"), ("tm 1", "tm"), ("tm1", "tm"), ("tm c", "tm"),
    ("melt temp", "tm"), ("melt temperature", "tm"), ("melting temperature", "tm"),
    ("melting temp", "tm"), ("tm peak", "tm"), ("melting point", "tm"),
    # melt x-axis temperature (melt-long)
    ("temperature", "temp"), ("temp", "temp"), ("temp c", "temp"), ("temperature c", "temp"),
    # cycle index
    ("cycle", "cycle"), ("cycles", "cycle"), ("cycle no", "cycle"), ("cycle number", "cycle"),
    ("pcr cycle", "cycle"), ("amplification cycle", "cycle"), ("cycle index", "cycle"),
    # per-cycle value (long tables)
    ("value", "value"), ("fluorescence", "value"), ("fluorescence value", "value"),
    ("signal", "value"), ("signal value", "value"), ("rfu", "value"), ("delta rn", "value"),
    ("dn", "value"), ("rf", "value"), ("amplitude", "value"),
    # metadata key/value
    ("instrument", "meta"), ("instrument name", "meta"), ("software", "meta"),
    ("run date", "meta"), ("date", "meta"), ("operator", "meta"), ("run name", "meta"),
    ("experiment", "meta"), ("experiment name", "meta"), ("comments", "meta"),
    ("comment", "meta"), ("run", "meta"), ("plate", "meta"), ("plate id", "meta"),
]
_ALIAS_MAP = dict(COLUMN_ALIASES)


def norm_key(s):
    if not isinstance(s, str):
        s = _s(s)
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


_KIND_ORDER = ["well", "sample", "target", "dye", "stype", "qty", "cq", "cqsd", "tm", "temp",
               "cycle", "value", "meta"]


def classify_header(cells):
    """Map column index → canonical kind for cells that hit the alias table."""
    kinds = {}
    for i, cell in enumerate(cells):
        k = _ALIAS_MAP.get(norm_key(cell))
        if k and i not in kinds:
            kinds[i] = k
    return kinds


def detect_header_runs(cells):
    """Ascending bare-numerics (→ cycles), 'Cycle N' labels, M65.0 melt runs."""
    labeled, melt_cols = [], []
    # Cycle N / M##.## labeled cells
    for i, cell in enumerate(cells):
        s = _s(cell)
        m = re.fullmatch(r"cycle\s*(\d+)", s, re.I)
        if m:
            labeled.append((i, int(m.group(1))))
            continue
        m = re.fullmatch(r"m\s*(\d+(?:\.\d+)?)", s, re.I)
        if m:
            melt_cols.append((i, float(m.group(1))))
    # bare numeric ascending runs (1,2,3,…,40)
    runs, run, prev = [], [], None
    for i, cell in enumerate(cells):
        s = _s(cell)
        if re.fullmatch(r"\d+", s):
            v = int(s)
            if prev is not None and v == prev + 1:
                run.append((i, v))
            else:
                if len(run) >= 5:
                    runs.append(run)
                run = [(i, v)] if v == 1 else []
            prev = v
        else:
            if len(run) >= 5:
                runs.append(run)
            run, prev = [], None
    if len(run) >= 5:
        runs.append(run)
    if len(labeled) >= 5:
        cycle_cols = labeled
    else:
        cycle_cols = max(runs, key=len) if runs else []
    if len(melt_cols) < 5:
        melt_cols = []
    return {"cycle": cycle_cols, "melt": melt_cols}


def score_header(cells):
    """→ (kinds, runs) when the row looks like a header row, else ({}, empty runs)."""
    kinds = classify_header(cells)
    runs = detect_header_runs(cells)
    if len(kinds) >= 2:
        return kinds, runs
    if len(kinds) == 1 and (runs["cycle"] or runs["melt"]):
        return kinds, runs
    return {}, {"cycle": [], "melt": []}


# ─────────────────────────────────────────────────────────────────
# 5. Section splitting
# ─────────────────────────────────────────────────────────────────
def split_sections(rows):
    sections, cur = [], {"title": "", "rows": []}
    for row in rows:
        nonempty = [c for c in row if _s(c)]
        if len(nonempty) == 1:
            sections.append(cur)
            cur = {"title": _s(nonempty[0]), "rows": []}
        else:
            cur["rows"].append(row)
    sections.append(cur)
    return [s for s in sections if s["rows"]]


def _classify_section(sec):
    """→ {'kind', 'kinds', 'runs', 'header_idx'} for one section."""
    header_idx = None
    kinds, runs = {}, {"cycle": [], "melt": []}
    for i, row in enumerate(sec["rows"]):
        k, r = score_header(row)
        if k:
            header_idx, kinds, runs = i, k, r
            break
    if header_idx is None:
        return {"kind": "meta", "kinds": {}, "runs": {"cycle": [], "melt": []}, "header_idx": None}
    if runs["cycle"]:
        kind = "amp-wide"
    elif runs["melt"]:
        kind = "melt-wide"
    elif "cycle" in kinds.values() and "value" in kinds.values():
        kind = "amp-long"
    elif "temp" in kinds.values() and "value" in kinds.values():
        kind = "melt-long"
    elif "cq" in kinds.values():
        kind = "cq"
    else:
        kind = "meta"
    return {"kind": kind, "kinds": kinds, "runs": runs, "header_idx": header_idx,
            "title": sec["title"]}


_KIND_LABEL = {
    "amp-wide": "amplification (wide Cycle N matrix)",
    "amp-long": "amplification (long per-cycle table)",
    "melt-wide": "melt (wide M##.## matrix)",
    "melt-long": "melt (long per-temperature table)",
    "cq": "Cq results table",
    "meta": "metadata / key-value",
}


# ─────────────────────────────────────────────────────────────────
# 6. Block readers → fragments
# ─────────────────────────────────────────────────────────────────
def _cell(row, i):
    return row[i] if 0 <= i < len(row) else None


def _frag_from_row(kinds, row):
    f = {"pos": None, "sample": None, "target": None, "dye": None, "stype": None,
         "qty": None, "cq": None, "cqsd": None, "tm": None}
    for i, kind in kinds.items():
        v = _cell(row, i)
        if v is None or not _s(v):
            continue
        if kind == "well":
            f["pos"] = _s(v)
        elif kind == "sample":
            f["sample"] = _s(v)
        elif kind == "target":
            f["target"] = _s(v)
        elif kind == "dye":
            f["dye"] = _s(v)
        elif kind == "stype":
            f["stype"] = _s(v)
        elif kind == "qty":
            n = _num(v)
            if n is not None:
                f["qty"] = n
        elif kind == "cq":
            n = _num(v)
            if n is not None:
                f["cq"] = n
        elif kind == "cqsd":
            n = _num(v)
            if n is not None:
                f["cqsd"] = n
        elif kind == "tm":
            n = _num(v)
            if n is not None:
                f["tm"] = n
    return f


def _has_identity(f):
    return bool(f["pos"] or f["sample"] or f["target"])


def read_amp_wide(info, rows):
    frags = []
    kinds, run_cols = info["kinds"], info["runs"]["cycle"]
    for row in rows[info["header_idx"] + 1:]:
        if sum(1 for c in row if _s(c)) < 2:
            continue
        f = _frag_from_row(kinds, row)
        if not _has_identity(f):
            continue
        f["kind"] = "amp"
        f["cycles"] = []
        for col, num in run_cols:
            v = _num(_cell(row, col))
            if v is not None:
                f["cycles"].append((num, v))
        frags.append(f)
    return frags


def read_amp_long(info, rows):
    cycle_col = next(c for c, k in info["kinds"].items() if k == "cycle")
    value_col = next(c for c, k in info["kinds"].items() if k == "value")
    frags = []
    for row in rows[info["header_idx"] + 1:]:
        if sum(1 for c in row if _s(c)) < 2:
            continue
        f = _frag_from_row(info["kinds"], row)
        if not _has_identity(f):
            continue
        cyc, val = _num(_cell(row, cycle_col)), _num(_cell(row, value_col))
        if cyc is None or val is None:
            continue
        f["kind"] = "amp"
        f["cycles"] = [(int(cyc), val)]
        frags.append(f)
    return _group_amp(frags)


def _group_amp(frags):
    """Anti-duplicate: one fragment per (position|sample, target, dye)."""
    groups, order = {}, []
    for f in frags:
        key = (f["pos"].upper() if f["pos"] else None,
               (f["sample"] or "").lower(), (f["target"] or "").lower(),
               (f["dye"] or "").lower())
        if key in groups:
            groups[key]["cycles"].extend(f["cycles"])
            if not groups[key]["cq"] and f["cq"]:
                groups[key].update(cq=f["cq"], cqsd=f["cqsd"], tm=f["tm"])
        else:
            groups[key] = f
            order.append(key)
    out = []
    for key in order:
        f = groups[key]
        f["cycles"].sort(key=lambda p: p[0])
        out.append(f)
    return out


def read_melt_wide(info, rows):
    frags = []
    run_cols = info["runs"]["melt"]
    for row in rows[info["header_idx"] + 1:]:
        if sum(1 for c in row if _s(c)) < 2:
            continue
        f = _frag_from_row(info["kinds"], row)
        if not _has_identity(f):
            continue
        temps, fluors = [], []
        for col, t in run_cols:
            v = _num(_cell(row, col))
            if v is not None:
                temps.append(t)
                fluors.append(v)
        if not temps:
            continue
        f["kind"] = "melt"
        f["temps"] = temps
        f["fluores"] = fluors
        frags.append(f)
    return frags


def read_melt_long(info, rows):
    temp_col = next(c for c, k in info["kinds"].items() if k == "temp")
    value_col = next(c for c, k in info["kinds"].items() if k == "value")
    frags = []
    for row in rows[info["header_idx"] + 1:]:
        if sum(1 for c in row if _s(c)) < 2:
            continue
        f = _frag_from_row(info["kinds"], row)
        if not _has_identity(f):
            continue
        t, v = _num(_cell(row, temp_col)), _num(_cell(row, value_col))
        if t is None or v is None:
            continue
        f["kind"] = "melt"
        f.setdefault("temps", []).append(t)
        f.setdefault("fluores", []).append(v)
        frags.append(f)
    return _group_melt(frags)


def _group_melt(frags):
    """Anti-duplicate: one fragment per (position|sample, target, dye), temps sorted."""
    groups, order = {}, []
    for f in frags:
        key = (f["pos"].upper() if f["pos"] else None,
               (f["sample"] or "").lower(), (f["target"] or "").lower(),
               (f["dye"] or "").lower())
        if key in groups:
            groups[key]["temps"].extend(f["temps"])
            groups[key]["fluores"].extend(f["fluores"])
        else:
            groups[key] = f
            order.append(key)
    out = []
    for key in order:
        f = groups[key]
        paired = sorted(zip(f["temps"], f["fluores"]), key=lambda p: p[0])
        f["temps"] = [t for t, _ in paired]
        f["fluores"] = [v for _, v in paired]
        out.append(f)
    return out


def read_cq_table(info, rows):
    frags = []
    for row in rows[info["header_idx"] + 1:]:
        if sum(1 for c in row if _s(c)) < 2:
            continue
        f = _frag_from_row(info["kinds"], row)
        if not _has_identity(f):
            continue
        f["kind"] = "cq"
        frags.append(f)
    return frags


def read_meta_section(info, rows):
    pairs = {}
    start = info["header_idx"] if info["header_idx"] is not None else 0
    for row in rows[start:]:
        nonempty = [(i, _s(c)) for i, c in enumerate(row) if _s(c)]
        if len(nonempty) < 2:
            continue
        key = norm_key(nonempty[0][1])
        if key in _ALIAS_MAP and _ALIAS_MAP[key] != "meta":
            continue  # a foreign table header, not a key/value line
        pairs[key] = nonempty[1][1]
    return pairs


# ─────────────────────────────────────────────────────────────────
# 7. sameWell merge rule (replicate-safe)
# ─────────────────────────────────────────────────────────────────
def same_well(a, b):
    pa, pb = a.get("pos"), b.get("pos")
    if pa and pb:
        return pa.upper() == pb.upper()
    sa, sb = (a.get("sample") or "").strip().lower(), (b.get("sample") or "").strip().lower()
    if not sa or not sb:
        return False
    if sa != sb:
        return False
    ta, tb = (a.get("target") or "").strip().lower(), (b.get("target") or "").strip().lower()
    return not ta or not tb or ta == tb


# ─────────────────────────────────────────────────────────────────
# 8. Assembly: fragments → canonical Run
# ─────────────────────────────────────────────────────────────────
_STYPE_KEYWORDS = [
    (r"ntc|negative|no template|blank|water", "ntc"),
    (r"standard|std|stds|calibrat", "standard"),
    (r"control|ctrl|ref|reference", "control"),
]


def _type_from(stype, sample_name):
    if stype:
        low = stype.lower()
        for pat, t in _STYPE_KEYWORDS:
            if re.search(pat, low):
                return t
    return guess_sample_type(sample_name)


def attach_detection(run, fmt, confidence, evidence):
    run["detection"] = {"format": fmt, "confidence": round(confidence, 2),
                        "evidence": list(evidence)}
    return run


def mark_cq_only(run):
    if run["wells"] and all(len(w.get("amplification") or []) == 0 for w in run["wells"]):
        run["cqOnly"] = True
    else:
        run["cqOnly"] = False
    return run


def reason_rows(rows, file_name, source_format="universal", sheet_name=None):
    """The universal layout reasoner. Returns a canonical Run or None."""
    sections = split_sections(rows)
    classified, meta_pairs = [], {}
    for sec in sections:
        info = _classify_section(sec)
        info["_rows"] = sec["rows"]
        if info["kind"] == "meta":
            meta_pairs.update(read_meta_section(info, sec["rows"]))
        else:
            classified.append(info)
    amp_frags, melt_frags, cq_frags = [], [], []
    evidence = []
    for info in classified:
        evidence.append('Section "%s" → %s' % (info.get("title") or "(untitled)",
                                                _KIND_LABEL[info["kind"]]))
        if info["kind"] == "amp-wide":
            amp_frags.extend(read_amp_wide(info, info["_rows"]))
            run_cols = info["runs"]["cycle"]
            if run_cols:
                evidence.append("Ascending bare-numeric cycle run: %d..%d (%d columns)"
                                % (run_cols[0][1], run_cols[-1][1], len(run_cols)))
        elif info["kind"] == "amp-long":
            amp_frags.extend(read_amp_long(info, info["_rows"]))
        elif info["kind"] == "melt-wide":
            melt_frags.extend(read_melt_wide(info, info["_rows"]))
            evidence.append("M##.## melt-temperature run: %d columns"
                            % len(info["runs"]["melt"]))
        elif info["kind"] == "melt-long":
            melt_frags.extend(read_melt_long(info, info["_rows"]))
        elif info["kind"] == "cq":
            cq_frags.extend(read_cq_table(info, info["_rows"]))
    if not amp_frags and not melt_frags and not cq_frags:
        return None

    # instrument identity from metadata
    instrument = meta_pairs.get("instrument")

    # merge: amp base → melt → cq (replicate-safe sameWell)
    order = []

    def _find(f):
        for rec in order:
            if same_well(rec["frag"], f):
                return rec
        return None

    merged_melt = merged_cq = False
    for f in amp_frags:
        rec = _find(f)
        if rec:
            rec["frag"]["cycles"].extend(f["cycles"])
        else:
            order.append({"frag": f, "melt": None, "cq": None})
    for f in melt_frags:
        rec = _find(f)
        if rec and rec.get("melt") is None:
            rec["melt"] = f
            merged_melt = True
        elif rec is None:
            order.append({"frag": f, "melt": f, "cq": None})
    for f in cq_frags:
        rec = _find(f)
        if rec:
            if rec["cq"] is None:
                rec["cq"] = f
                merged_cq = merged_cq or bool(rec["frag"].get("cycles"))
        else:
            order.append({"frag": f, "melt": None, "cq": f})

    # canonical registries
    run = make_run({"fileName": file_name, "sourceFormat": source_format})
    if instrument:
        run["meta"]["instrument"] = instrument
        evidence.append("Instrument identity from file: %s" % instrument)
    sample_ids, target_ids, channel_ids = {}, {}, {}

    def _sample_id(name, qty):
        key = name
        if key in sample_ids:
            if qty is not None and run["samples"][sample_ids[key]].get("quantity") is None:
                run["samples"][sample_ids[key]]["quantity"] = qty
            return sample_ids[key]
        sid = len(run["samples"])
        run["samples"].append(make_sample(sid, name, _type_from(None, name), qty))
        sample_ids[key] = sid
        return sid

    def _target_id(name):
        if name in target_ids:
            return target_ids[name]
        tid = len(run["targets"])
        run["targets"].append(make_target(tid, name, None, guess_reference(name)))
        target_ids[name] = tid
        return tid

    def _channel_id(dye_raw):
        canon = canonical_channel(dye_raw) if dye_raw else None
        canon = canon or (dye_raw.upper() if dye_raw else "FAM")
        if canon in channel_ids:
            return channel_ids[canon]
        cid = len(run["channels"])
        run["channels"].append(make_channel(cid, dye_raw or "FAM", canon))
        channel_ids[canon] = cid
        return cid

    any_pos = any_cq = any_cycles = False
    for rec in order:
        f, cq = rec["frag"], rec["cq"]
        base = dict(f)
        if cq:
            for k in ("cq", "cqsd", "tm"):
                if cq.get(k) is not None and base.get(k) is None:
                    base[k] = cq[k]
            # stype / qty may only exist on the Cq section row
            if not base.get("stype") and cq.get("stype"):
                base["stype"] = cq["stype"]
            if base.get("qty") is None and cq.get("qty") is not None:
                base["qty"] = cq["qty"]
            if not base.get("sample") and cq.get("sample"):
                base["sample"] = cq["sample"]
            if not base.get("target") and cq.get("target"):
                base["target"] = cq["target"]
            if not base.get("dye") and cq.get("dye"):
                base["dye"] = cq["dye"]
        pos = base.get("pos") or ""
        sample_name = base.get("sample") or pos or "Unknown"
        target_name = base.get("target") or "Unknown"
        sid = _sample_id(sample_name, base.get("qty"))
        tid = _target_id(target_name)
        cid = _channel_id(base.get("dye"))
        # sample type override from stype column
        if base.get("stype"):
            t = _type_from(base["stype"], sample_name)
            run["samples"][sid]["type"] = t
        pp = parse_position(pos, 96) if pos else {"row": len(run["wells"]) // 12,
                                                  "col": len(run["wells"]) % 12}
        well = make_well(len(run["wells"]), pp["row"], pp["col"], "96")
        well["sampleId"] = sid
        well["targetId"] = tid
        well["channelId"] = cid
        well["cq"] = base.get("cq")
        well["cqSD"] = base.get("cqsd")
        well["tm"] = base.get("tm")
        cycles = sorted(f.get("cycles") or [], key=lambda p: p[0])
        well["amplification"] = [v for _, v in cycles]
        if rec.get("melt"):
            well["melt"] = {"temps": list(rec["melt"].get("temps") or []),
                            "fluores": list(rec["melt"].get("fluores") or [])}
        run["wells"].append(well)
        if pos:
            any_pos = True
        if well["cq"] is not None:
            any_cq = True
        if well["amplification"]:
            any_cycles = True

    if not run["channels"]:
        run["channels"].append(make_channel(0, "FAM", "FAM"))
    for t in run["targets"]:
        if t["channelId"] is None:
            t["channelId"] = 0

    # evidence + confidence
    kinds_hit = sorted({k for info in classified for k in info["kinds"].values()})
    if kinds_hit:
        evidence.append("Header aliases matched: " + ", ".join(kinds_hit))
    if any_pos:
        evidence.append("Well positions parse as plate addresses (A1-style)")
    if any_cq:
        evidence.append("Instrument-reported Cq values present")
    if any_cycles:
        evidence.append("Per-cycle fluorescence present")
    if merged_cq:
        evidence.append("Cross-section merge: Cq table attached to amplification wells "
                        "by well position")
    if merged_melt:
        evidence.append("Cross-section merge: melt table attached to amplification wells")
    if sheet_name:
        evidence.append('Worksheet "%s" read as grid rows' % sheet_name)

    conf = 0.0
    structured_cycles = any(
        (info["kind"] == "amp-wide" and len(info["runs"]["cycle"]) >= 5)
        or info["kind"] == "amp-long"
        for info in classified)
    if structured_cycles:
        conf += 0.25
    if any_pos:
        conf += 0.2
    if any_cq:
        conf += 0.2
    if any_cycles:
        conf += 0.15
    if sample_ids:
        conf += 0.1
    if target_ids:
        conf += 0.05
    mark_cq_only(run)
    if run["cqOnly"]:
        evidence.append("Cq-only export: no per-cycle fluorescence — the amplification "
                        "chart will state this honestly")
    attach_detection(run, "reasoner", min(conf, 0.99), evidence)
    return run


def reason_grids(grids, file_name, source_format="universal"):
    """grids: [{'name': sheet, 'grid': [[cells]]}] — first sheet that reasons wins."""
    for g in grids:
        grid = g.get("grid") or []
        if not grid:
            continue
        rows = [[_s(c) for c in row] for row in grid]
        run = reason_rows(rows, file_name, source_format=source_format,
                          sheet_name=g.get("name"))
        if run:
            return run
    return None


# ─────────────────────────────────────────────────────────────────
# 9. OLE2 / CFB reader (spec T3.1)
# ─────────────────────────────────────────────────────────────────
ENDOFCHAIN = 0xFFFFFFFE
FREESECT = 0xFFFFFFFF


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def _u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def read_cfb(u8):
    if u8[:8] != bytes.fromhex("D0CF11E0A1B11AE1"):
        raise ValueError("not an OLE2 compound document (bad signature)")
    sector_size = 1 << _u16(u8, 30)
    if sector_size not in (512, 4096):
        raise ValueError("bad sector shift %d" % _u16(u8, 30))
    num_fat = _u32(u8, 44)
    first_dir = _u32(u8, 48)
    mini_cutoff = _u32(u8, 56)
    first_minifat = _u32(u8, 60)
    first_difat = _u32(u8, 68)
    num_difat = _u32(u8, 72)

    def sector(n):
        off = 512 + n * sector_size
        if off + sector_size > len(u8):
            raise ValueError("sector %d beyond EOF" % n)
        return u8[off:off + sector_size]

    # DIFAT: header's 109 entries + chain
    difat = [_u32(u8, 76 + i * 4) for i in range(109)]
    nxt = first_difat
    guard = 0
    while num_difat > 0 and nxt not in (ENDOFCHAIN, FREESECT) and guard < 10000:
        guard += 1
        s = sector(nxt)
        for i in range(sector_size // 4 - 1):
            difat.append(_u32(s, i * 4))
        nxt = _u32(s, sector_size - 4)
    fat = []
    for fs in difat:
        if fs in (ENDOFCHAIN, FREESECT):
            continue
        s = sector(fs)
        fat.extend(_u32(s, i * 4) for i in range(sector_size // 4))
        if len(fat) >= num_fat * (sector_size // 4):
            break

    def chain(start, limit=1 << 20):
        out, n, guard = [], start, 0
        while n not in (ENDOFCHAIN, FREESECT) and guard < limit:
            guard += 1
            out.append(n)
            if n >= len(fat):
                raise ValueError("FAT chain escapes table")
            n = fat[n]
        return out

    def stream_bytes(start, size):
        data = b"".join(sector(n) for n in chain(start))
        return data[:size]

    # directory
    dir_data = b"".join(sector(n) for n in chain(first_dir))
    entries = {}
    root = None
    for i in range(len(dir_data) // 128):
        e = dir_data[i * 128:(i + 1) * 128]
        etype = e[66]
        if etype not in (1, 2, 5):
            continue
        name_len = _u16(e, 64)  # bytes, incl. UTF-16 null terminator
        if name_len < 2:
            if etype == 5:
                root = (etype, _u32(e, 116), struct.unpack_from("<Q", e, 120)[0])
            continue
        name = e[:name_len - 2].decode("utf-16-le", "replace")
        start = _u32(e, 116)
        size = struct.unpack_from("<Q", e, 120)[0]
        rec = (etype, start, size)
        entries[name] = rec
        if etype == 5:
            root = rec
    if root is None:
        raise ValueError("no Root Entry in CFB directory")

    # mini-stream + miniFAT
    ministream = stream_bytes(root[1], root[2]) if root[2] else b""
    mini_fat = []
    if first_minifat not in (ENDOFCHAIN, FREESECT):
        mf = b"".join(sector(n) for n in chain(first_minifat))
        mini_fat = [_u32(mf, i * 4) for i in range(len(mf) // 4)]

    def mini_bytes(start, size):
        out, n, guard = b"", start, 0
        while n not in (ENDOFCHAIN, FREESECT) and guard < 1 << 20:
            guard += 1
            out += ministream[n * 64:(n + 1) * 64]
            if n >= len(mini_fat):
                raise ValueError("miniFAT chain escapes table")
            n = mini_fat[n]
        return out[:size]

    streams = {}
    for name, (etype, start, size) in entries.items():
        if etype != 2:
            continue
        streams[name] = mini_bytes(start, size) if size < mini_cutoff else stream_bytes(start, size)
    if not streams:
        raise ValueError("CFB contains no streams")
    return streams


# ─────────────────────────────────────────────────────────────────
# 10. BIFF8 record reader (spec T3.2; RK decode)
# ─────────────────────────────────────────────────────────────────
def rk_decode(rk):
    rk &= 0xFFFFFFFF
    if rk & 2:
        num = rk >> 2
        if num >= (1 << 29):
            num -= 1 << 30
    else:
        num = struct.unpack("<d", struct.pack("<Q", (rk & 0xFFFFFFFC) << 32))[0]
    if rk & 1:
        num /= 100.0
    return float(num)


def _record_iter(buf, start=0, end=None):
    end = len(buf) if end is None else end
    off = start
    while off + 4 <= end:
        rid = _u16(buf, off)
        rlen = _u16(buf, off + 2)
        if rid == 0 and rlen == 0:
            break
        data = buf[off + 4:off + 4 + rlen]
        yield rid, data
        off += 4 + rlen


def _xl_str(data, off, cch, grbit):
    """XLUnicodeString body at off: returns (text, next_off)."""
    if grbit & 0x01:
        raw = data[off:off + cch * 2]
        return raw.decode("utf-16-le", "replace"), off + cch * 2
    raw = data[off:off + cch]
    return raw.decode("latin-1", "replace"), off + cch


def read_biff8(workbook):
    """→ [{'name': str, 'grid': [[cell]]}].  Records: BOF/BOUNDSHEET/SST/
    LABELSST/LABEL/NUMBER/RK/MULRK/FORMULA(cache)/CONTINUE-tolerant SST."""
    sheets, strings = [], []
    boundsheets = []
    for rid, data in _record_iter(workbook):
        if rid == 0x0085:  # BOUNDSHEET
            pos = _u32(data, 0)
            cch = data[6]
            grbit = data[7]
            name, _ = _xl_str(data, 8, cch, grbit)
            boundsheets.append((name, pos))
        elif rid == 0x00FC:  # SST (no CONTINUE in our corpus; tolerate truncation)
            total, unique = _u32(data, 0), _u32(data, 4)
            off = 8
            try:
                for _ in range(unique):
                    if off + 3 > len(data):
                        raise ValueError("SST truncated")
                    cch = _u16(data, off)
                    grbit = data[off + 2]
                    text, off = _xl_str(data, off + 3, cch, grbit)
                    strings.append(text)
            except (UnicodeDecodeError, struct.error) as e:
                raise ValueError("SST record unreadable: %s" % e)
        elif rid == 0x000A:
            break
    if not boundsheets:
        raise ValueError("no BOUNDSHEET records — no worksheet in workbook stream")

    for name, pos in boundsheets:
        grid = []
        for rid, data in _record_iter(workbook, start=pos):
            if rid == 0x000A:
                break
            try:
                if rid == 0x00FD and len(data) >= 10:  # LABELSST
                    rw, col, _xf, isst = struct.unpack_from("<HHHI", data, 0)
                    val = strings[isst] if isst < len(strings) else ""
                elif rid == 0x0204 and len(data) >= 8:  # LABEL
                    rw, col = _u16(data, 0), _u16(data, 2)
                    cch = _u16(data, 6)
                    val, _ = _xl_str(data, 8, cch, data[7] if len(data) > 7 else 0)
                elif rid == 0x0203 and len(data) >= 14:  # NUMBER
                    rw, col = _u16(data, 0), _u16(data, 2)
                    val = struct.unpack_from("<d", data, 6)[0]
                elif rid == 0x027E and len(data) >= 10:  # RK
                    rw, col, _xf, rk = struct.unpack_from("<HHHI", data, 0)
                    val = rk_decode(rk)
                elif rid == 0x00BD and len(data) >= 8:  # MULRK
                    rw, col0 = _u16(data, 0), _u16(data, 2)
                    ncols = (len(data) - 6) // 6
                    for k in range(ncols):
                        rk = _u32(data, 4 + k * 6 + 2)
                        _set_cell(grid, rw, col0 + k, rk_decode(rk))
                    continue
                elif rid == 0x0006 and len(data) >= 20:  # FORMULA (cached result)
                    rw, col = _u16(data, 0), _u16(data, 2)
                    res = data[6:14]
                    if res[6] == 0xFF and res[7] == 0xFF:
                        continue  # special (string/bool/error) — not a number
                    val = struct.unpack("<d", res)[0]
                else:
                    continue
            except (struct.error, IndexError) as e:
                raise ValueError("BIFF record 0x%04X unreadable: %s" % (rid, e))
            _set_cell(grid, rw, col, val)
        if any(any(_s(c) for c in row) for row in grid):
            sheets.append({"name": name, "grid": grid})
    if not sheets:
        raise ValueError("BIFF sheets contain no cells")
    return sheets


def _set_cell(grid, rw, col, val):
    while len(grid) <= rw:
        grid.append([])
    row = grid[rw]
    while len(row) <= col:
        row.append("")
    row[col] = val


# ─────────────────────────────────────────────────────────────────
# 11. XLSX grid reader (stdlib only — same as JS)
# ─────────────────────────────────────────────────────────────────
def _xml_unescape(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
             .replace("&apos;", "'").replace("&amp;", "&"))


def _col_to_idx(ref):
    m = re.match(r"([A-Z]+)", ref or "")
    if not m:
        return 0
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_xlsx_grids(u8):
    zf = zipfile.ZipFile(io.BytesIO(bytes(u8)))
    names = zf.namelist()
    strings = []
    if "xl/sharedStrings.xml" in names:
        ss = zf.read("xl/sharedStrings.xml").decode("utf-8", "replace")
        for si in re.findall(r"<si>([\s\S]*?)</si>", ss):
            texts = re.findall(r"<t[^>]*>([\s\S]*?)</t>", si)
            strings.append("".join(texts) if texts else "")
    sheet_files = [n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)]
    sheet_files.sort(key=lambda n: int(re.search(r"(\d+)", n).group(1)))
    grids = []
    for sf in sheet_files:
        xml = zf.read(sf).decode("utf-8", "replace")
        grid = []
        for rm in re.finditer(r"<row[^>]*>([\s\S]*?)</row>", xml):
            row = []
            for cm in re.finditer(
                    r'<c\s+r="([A-Z]+)\d+"(?:\s+t="(\w+)")?[^>]*?(?:/>|>([\s\S]*?)</c>)',
                    rm.group(1)):
                ref, ctype, body = cm.group(1), cm.group(2) or "n", cm.group(3) or ""
                idx = _col_to_idx(ref)
                val = ""
                if ctype == "inlineStr":
                    t = re.search(r"<t[^>]*>([\s\S]*?)</t>", body)
                    val = _xml_unescape(t.group(1)) if t else ""
                elif ctype == "str":  # formula string result — value in <v>
                    v = re.search(r"<v>([\s\S]*?)</v>", body)
                    val = _xml_unescape(v.group(1)) if v else ""
                else:
                    v = re.search(r"<v>([\s\S]*?)</v>", body)
                    if v:
                        raw = _xml_unescape(v.group(1))
                        if ctype == "s":
                            try:
                                val = strings[int(raw)]
                            except (ValueError, IndexError):
                                val = ""
                        else:
                            val = float(raw) if _is_number(raw) else raw
                while len(row) <= idx:
                    row.append("")
                row[idx] = val
            grid.append(row)
        if grid:
            grids.append({"name": os.path.basename(sf), "grid": grid})
    if not grids:
        raise ValueError("XLSX contains no worksheets")
    return grids


# ─────────────────────────────────────────────────────────────────
# 12. Format doctor + Rotor-Gene guided card
# ─────────────────────────────────────────────────────────────────
def _printable_snippet(u8, n=72):
    out = []
    for b in u8[:n]:
        out.append(chr(b) if 32 <= b < 127 else "·")
    return "".join(out)


def diagnose(u8, text, file_name):
    kind = sniff(u8) if u8 is not None else "text"
    ext = ext_of(file_name) or "(none)"
    findings = [
        "Container (magic bytes): %s" % kind,
        "Size: %d bytes" % (len(u8) if u8 is not None else 0),
        "Extension: .%s" % ext,
        "First bytes: %s" % (_printable_snippet(u8) if u8 else "(empty)"),
    ]
    guidance = []
    if kind == "gzip":
        title = "Compressed (gzip) container"
        findings.append("This file is gzip-compressed, not a data table")
        guidance.append("Extract the archive first, then drop the inner file here.")
    elif kind == "binary":
        title = "Binary payload — not a recognized container"
        nul = sum(1 for b in (u8 or b"")[:1000] if b == 0)
        findings.append("NUL bytes in first 1 KB: %d (not text)" % nul)
        guidance.append(
            "Content is binary and is neither ZIP, OLE2, gzip nor text — no data table "
            "can be read from these bytes as-is.")
        if ext in ROTOR_EXTS:
            guidance.append("This extension is in the Rotor-Gene family — see the "
                            "family export guidance for the CSV/RDML export menu.")
    elif kind == "zip":
        title = "ZIP archive without readable data files"
        guidance.append("Extract the archive and drop the inner .csv/.tsv/.txt/"
                        ".rdml/.xlsx file directly.")
    else:
        title = "No recognizable data table in this text"
        findings.append("Decoded %d characters of text" % len(text or ""))
        if text and text.strip():
            first = text.strip().split("\n")[0][:72]
            findings.append("First line: %s" % first)
            delim = detect_delimiter(text)
            fields = len(_split_line(text.strip().split("\n")[0], delim))
            findings.append("Detected delimiter: %s (%d fields on first line)"
                            % ("tab" if delim == "\t" else delim, fields))
            rows = split_rows(text, delim)
            kinds = set()
            for row in rows[:10]:
                kinds.update(classify_header(row).values())
            if kinds:
                findings.append("Recognized column names: " + ", ".join(sorted(kinds)))
            else:
                findings.append("No recognized column names in the first rows")
        guidance.append("Supported header vocabulary: Well/Position/Chamber · Sample/"
                        "Specimen · Target/Assay · Dye/Reporter/Channel · Cq/Ct · Tm · "
                        "Cycle · Signal/Fluorescence/Value (any language spelling of "
                        "these works — the reasoner matches column names, not brands).")
    return {
        "title": title,
        "findings": findings,
        "guidance": guidance,
        "supported": list(SUPPORTED_FORMATS),
    }


def rotor_guided(file_name, probe):
    ext = ext_of(file_name)
    return {
        "title": "Rotor-Gene-family file — structure read, data not in a table",
        "findings": [
            "Extension .%s is in the Rotor-Gene family (.qbd/.qbg/.qbt/.rgd/.rgx/.rex)"
            % ext,
            "Probed content first: %s" % probe,
            "These files are written by Corbett Rotor-Gene Q software and the "
            "Genes2Me machines that ship it (OnePCR, RapiCycler) — one file family, "
            "several brands. The instrument name inside is metadata, not a format.",
        ],
        "guidance": [
            "The payload here is proprietary binary — no data table could be read from "
            "it, so there is nothing to plot rather than guess at it.",
            "Export a data table from your instrument software: File → Export (or "
            "Save As) → CSV/Excel, or RDML if offered — in OnePCR/RapiCycler choose "
            "the export menu, not a print-to-file.",
            "Drop that export here — CSV, TSV, TXT, XLS or XLSX from any machine is "
            "read directly by the layout reasoner. No manual reformatting, no data "
            "retyping.",
        ],
        "supported": list(SUPPORTED_FORMATS),
    }


def _format_error(doctor, message=None):
    return FormatError(message or doctor.get("title", "format error"), doctor=doctor)


# ─────────────────────────────────────────────────────────────────
# 13. Text dispatch: fast paths → reasoner → doctor
# ─────────────────────────────────────────────────────────────────
def parse_universal_text(text, file_name=None):
    t = (text or "").strip()
    if not t:
        raise _format_error(diagnose(None, text, file_name), "Empty file — nothing to read")
    fmt = detect_format(text, file_name)
    if fmt == "rdml":
        try:
            run = parse_rdml(text, file_name)
        except Exception as e:
            raise _format_error(
                {"title": "RDML parse failed",
                 "findings": ["First line: %s" % t.split("\n")[0][:72],
                              "Parse error: %s" % e,
                              "RDML structure expected: <rdml> → <experiment> → "
                              "<run> → <react>."],
                 "guidance": ["Re-export as RDML 1.2 from your instrument software, or "
                              "export CSV and drop that instead."],
                 "supported": list(SUPPORTED_FORMATS)})
        mark_cq_only(run)
        attach_detection(run, "rdml", 0.98, ["RDML XML document (<rdml> root)"])
        return run
    fmt = detect_format(text, file_name)
    if fmt == "cfx_csv":
        run = parse_cfx_csv(text, file_name)
        mark_cq_only(run)
        attach_detection(run, "cfx_csv", 0.9,
                         ["CFX-style table (header fingerprints matched)"])
        return run
    if fmt == "template":
        run = parse_template(text, file_name)
        mark_cq_only(run)
        attach_detection(run, "template", 0.95,
                         ["Template header: Well + Sample + Target + Channel"])
        return run
    delim = detect_delimiter(text)
    rows = split_rows(text, delim)
    run = reason_rows(rows, file_name, source_format="universal")
    if run:
        if delim == ";":
            run["detection"]["evidence"].append("Detected ';' delimiter")
        elif delim == "\t":
            run["detection"]["evidence"].append("Detected tab delimiter")
        return run
    raise _format_error(diagnose(_encode(text), text, file_name))


def _encode(text):
    try:
        return text.encode("utf-8")
    except Exception:
        return b""


# ─────────────────────────────────────────────────────────────────
# 14. Master entry: sniff → dispatch
# ─────────────────────────────────────────────────────────────────
def _strict_template_header(text):
    lines = (text or "").split("\n")[:5]
    return (any(re.search(r"well[,\t].*sample", l, re.I) for l in lines)
            and any(re.search(r"target", l, re.I) for l in lines)
            and any(re.search(r"channel", l, re.I) for l in lines))


def _grid_to_csv_text(grid):
    out = []
    for row in grid:
        cells = []
        for c in row:
            s = _s(c)
            if "," in s or '"' in s:
                s = '"' + s.replace('"', '""') + '"'
            cells.append(s)
        out.append(",".join(cells))
    return "\n".join(out)


def parse_file_universal(file_name, buffer_bytes):
    """Master entry (Python mirror of parseFileUniversal). Returns a canonical
    Run dict or raises FormatError with `.doctor`."""
    u8 = bytes(buffer_bytes)
    kind = sniff(u8)
    ext = ext_of(file_name)

    if kind == "ole":
        try:
            streams = read_cfb(u8)
            key = next((k for k in ("Workbook", "Book") if k in streams), None)
            if key is None:
                key = next(iter(streams))
            sheets = read_biff8(streams[key])
            run = reason_grids(sheets, file_name, source_format="xls")
            if not run:
                raise _format_error(doctor_ole(sheets))
            run["meta"]["sourceFormat"] = "xls"
            run["detection"]["format"] = "xls-biff8"
            run["detection"]["evidence"].insert(
                0, "OLE2 compound document → BIFF8 worksheet read (%d sheet%s)"
                % (len(sheets), "" if len(sheets) == 1 else "s"))
            run["detection"]["confidence"] = max(run["detection"]["confidence"], 0.9)
            return run
        except FormatError:
            raise
        except Exception as e:
            raise _format_error(doctor_ole_error(file_name, e))

    if kind == "zip":
        return _parse_zip(file_name, u8)

    if kind == "gzip":
        raise _format_error(diagnose(u8, None, file_name))

    if kind == "binary":
        if ext in ROTOR_EXTS:
            raise _format_error(rotor_guided(
                file_name, "proprietary binary payload (not ZIP/OLE2/gzip/text)"))
        raise _format_error(diagnose(u8, None, file_name))

    # text container → fast paths → reasoner → doctor
    text = decode_text(u8)
    try:
        run = parse_universal_text(text, file_name)
    except FormatError:
        raise
    if ext in ("xls", "xlsx", "qbd", "qbg"):
        run["detection"]["evidence"].append(
            "Text container despite .%s extension — parsed by content, not by name" % ext)
    return run


def _parse_zip(file_name, u8):
    ext = ext_of(file_name)
    try:
        zf = zipfile.ZipFile(io.BytesIO(u8))
        names = zf.namelist()
    except Exception as e:
        raise _format_error({"title": "ZIP archive unreadable",
                             "findings": ["%s" % e],
                             "guidance": ["The file starts with ZIP magic bytes but the "
                                          "central directory cannot be read — it may be "
                                          "truncated. Re-download or re-export it."],
                             "supported": list(SUPPORTED_FORMATS)})
    # 1) XLSX
    if "xl/workbook.xml" in names:
        try:
            grids = read_xlsx_grids(u8)
            text = _grid_to_csv_text(grids[0]["grid"])
            if _strict_template_header(text):
                run = parse_template(text, file_name)
                run["meta"]["sourceFormat"] = "xlsx"
                mark_cq_only(run)
                attach_detection(run, "xlsx", 0.95,
                                 ["ZIP container → XLSX workbook (%d sheet%s, strict "
                                  "template header)"
                                  % (len(grids), "" if len(grids) == 1 else "s")])
                return run
            run = reason_grids(grids, file_name, source_format="xlsx")
            if run:
                run["meta"]["sourceFormat"] = "xlsx"
                run["detection"]["format"] = "xlsx"
                run["detection"]["evidence"].insert(
                    0, "ZIP container → XLSX workbook (%d sheet%s, layout reasoner)"
                    % (len(grids), "" if len(grids) == 1 else "s"))
                return run
        except FormatError:
            raise
        except Exception as e:
            raise _format_error({"title": "XLSX workbook unreadable",
                                 "findings": ["%s" % e],
                                 "guidance": ["Re-save the sheet as CSV and drop that "
                                              "file here."],
                                 "supported": list(SUPPORTED_FORMATS)})
    # 2) RDML inside
    for n in names:
        if n.lower().endswith(".rdml") or (n.lower().endswith(".xml")
                                           and "macosx" not in n.lower()):
            try:
                inner = zf.read(n).decode("utf-8", "replace")
            except Exception:
                continue
            if "<rdml" in inner:
                try:
                    run = parse_rdml(inner, n)
                except Exception:
                    continue
                run["meta"]["sourceFormat"] = "rdml"
                mark_cq_only(run)
                attach_detection(run, "rdml", 0.96,
                                 ["ZIP container → RDML entry %s" % n])
                return run
    # 3) deep probe: inner .csv/.tsv/.txt ≤ 1 MB
    for n in sorted(names):
        low = n.lower()
        if "macosx" in low or low.endswith("/"):
            continue
        if not low.endswith((".csv", ".tsv", ".txt")):
            continue
        info = zf.getinfo(n)
        if info.file_size > 1_000_000:
            continue
        inner = zf.read(n).decode("utf-8", "replace")
        try:
            run = parse_universal_text(inner, n)
        except FormatError:
            continue
        run["detection"]["evidence"].insert(
            0, "ZIP deep-probe → inner data file %s" % n)
        return run
    if ext in ROTOR_EXTS:
        raise _format_error(rotor_guided(
            file_name, "ZIP archive (wrapped) — no readable data tables inside"))
    raise _format_error(diagnose(u8, None, file_name))


def doctor_ole(sheets):
    return {
        "title": "OLE2 document read, but no recognizable data table",
        "findings": ["Compound document parsed; %d worksheet(s) found: %s"
                     % (len(sheets), ", ".join(s["name"] or "?" for s in sheets)),
                     "No header row matched the known column vocabulary."],
        "guidance": ["Open the sheet in Excel/Sheets and re-save as CSV, or check the "
                     "header row spelling — Well/Sample/Target/Cq/Cycle columns are "
                     "recognized automatically."],
        "supported": list(SUPPORTED_FORMATS),
    }


def doctor_ole_error(file_name, err):
    return {
        "title": "OLE2/BIFF document unreadable",
        "findings": ["Container: OLE2 compound document (magic bytes)",
                     "Reader stopped at: %s" % err,
                     "BIFF record classes understood: BOF, BOUNDSHEET, SST, LABEL, "
                     "LABELSST, NUMBER, RK, MULRK, FORMULA(cached numeric)."],
        "guidance": ["Re-save from Excel as .xlsx or CSV — the data table itself is "
                     "portable; only this container's record mix was not."],
        "supported": list(SUPPORTED_FORMATS),
    }
