"""
qpcr_mirror.py — Python mirror of every analysis function in qpcr-engine.js.
JS output == Python output on every fixture.
"""
import json
import math
import re
import xml.etree.ElementTree as ET


QPCR_ENGINE_VERSION = "1.0.0"

CHANNEL_ALIASES = {
    "FAM": ["FAM", "SYBR", "SYBR GREEN", "SYBR GREEN I", "SYBRGREEN", "GREEN", "EVA GREEN", "EVAGREEN", "LC GREEN", "LCGREEN"],
    "HEX": ["HEX", "VIC", "TET", "JOE", "FAM", "CAL GOLD 540", "CALGOLD540"],
    "ROX": ["ROX", "TEXAS RED", "TEXASRED", "TAMRA", "CAL ORANGE 560", "CALORANGE560"],
    "CY5": ["CY5", "CY 5", "QUASAR 670", "QUASAR670", "CY5 5", "Cy5"],
    "CY55": ["CY5.5", "CY55", "CY 5.5", "QUASAR 705", "QUASAR705"],
}


def canonical_channel(raw):
    if not raw:
        return None
    key = str(raw).strip().upper().replace("_", " ").replace("-", " ")
    for canon, aliases in CHANNEL_ALIASES.items():
        for a in aliases:
            if key == a.upper().replace("_", " ").replace("-", " "):
                return canon
    if "FAM" in key or "SYBR" in key:
        return "FAM"
    if "HEX" in key or "VIC" in key or "TET" in key or "JOE" in key:
        return "HEX"
    if "ROX" in key or "TAMRA" in key or "TEXAS" in key:
        return "ROX"
    if "CY5.5" in key or "CY 5.5" in key:
        return "CY55"
    if "CY5" in key or "QUASAR" in key:
        return "CY5"
    return None


def make_run(meta=None):
    meta = meta or {}
    return {
        "meta": {
            "fileName": meta.get("fileName", ""),
            "sourceFormat": meta.get("sourceFormat", "unknown"),
            "instrument": meta.get("instrument"),
            "runDate": meta.get("runDate"),
            "chemistry": meta.get("chemistry"),
        },
        "channels": [],
        "targets": [],
        "samples": [],
        "wells": [],
    }


def make_channel(idx, raw, canonical):
    return {"id": idx, "canonical": canonical or canonical_channel(raw) or raw, "label": raw or str(idx), "aliases": []}


def make_target(idx, name, channel_id, is_reference=False):
    return {"id": idx, "name": name, "channelId": channel_id, "isReference": bool(is_reference)}


def make_sample(idx, name, stype, quantity=None):
    return {"id": idx, "name": name, "type": stype or "unknown", "quantity": quantity}


def make_well(idx, row, col, layout="96"):
    return {
        "id": idx, "row": row, "col": col, "layout": layout,
        "position": row * 12 + col,
        "sampleId": None, "targetId": None, "channelId": None,
        "cq": None, "cqSD": None, "tm": None, "tmPeaks": [],
        "amplification": [], "melt": None,
    }


def parse_position(pos, layout_size=96):
    pos = str(pos).strip()
    m = re.match(r"^([A-Za-z]+)(\d+)$", pos)
    if m:
        row = ord(m.group(1).upper()[0]) - 65
        col = int(m.group(2)) - 1
        return {"row": max(0, row), "col": max(0, col)}
    try:
        n = int(pos)
        cols = 24 if layout_size == 384 else 12
        return {"row": (n - 1) // cols, "col": (n - 1) % cols}
    except ValueError:
        return {"row": 0, "col": 0}


def guess_sample_type(name):
    n = (name or "").lower()
    if "ntc" in n or "no template" in n or "neg" in n:
        return "ntc"
    if "std" in n or "standard" in n or "calib" in n:
        return "standard"
    if "ctrl" in n or "control" in n or "ref" in n:
        return "control"
    return "unknown"


def guess_reference(name):
    n = (name or "").lower()
    return any(k in n for k in ["gapdh", "actb", "beta", "18s", "rpl", "tbp"])


def detect_format(text, file_name=None):
    if file_name:
        ext = file_name.lower().split(".")[-1]
        if ext == "pcrd":
            return "pcrd"
        if ext == "rdml":
            return "rdml"
        if ext == "xlsx":
            return "xlsx"
        if ext == "xls":
            return "xls"
        if ext == "qbg":
            return "qbg"
        if ext == "zip":
            return "zip"
    t = (text or "").strip()
    if not t:
        return "unknown"
    if t.startswith("<?xml") or t.startswith("<rdml") or "<rdml" in t:
        return "rdml"
    # First few lines are enough to identify a table header (case-insensitive, comma or tab)
    head_lines = re.split(r"\r?\n", t)[:5]
    has_head = lambda pat: any(re.search(pat, l, re.I) for l in head_lines)
    head = "\n".join(head_lines)
    # Template TSV/CSV: Well + Sample + Target + Channel (check FIRST — CFX has no Sample column)
    if has_head(r"well[,\t].*sample") and has_head(r"target") and has_head(r"channel"):
        return "template"
    # CFX-style summary table: Well + Fluor/Target (comma or tab delimited)
    if has_head(r"well[,\t].*fluor") or has_head(r"well[,\t].*target"):
        return "cfx_csv"
    # Sectioned CFX export (any case)
    if re.search(r"amplification data", t, re.I) and re.search(r"well", head, re.I):
        return "cfx_csv"
    # Long-format per-cycle table: Well + Cycle + Value/Fluorescence/Signal header
    if has_head(r"well") and has_head(r"cycle") and has_head(r"\bvalue\b|fluorescen|signal"):
        return "cfx_csv"
    # Cq-first headers (QuantStudio style)
    if has_head(r"cq[,\t].*well") or has_head(r"well[,\t].*cq"):
        return "cfx_csv"
    return "unknown"


def parse_rdml(text, file_name=None):
    run = make_run({"fileName": file_name or "rdml", "sourceFormat": "rdml"})
    try:
        def get_tag(xml, tag):
            # Word-boundary safe: '<cq' must not match '<cqStartFluor'
            b = tag + r"(?=[\s>])"
            # Handle self-closing tags with id attribute: <tag id="val"/>
            for quote in ('"', "'"):
                pattern = '<' + b + r'[^>]*?id=' + quote + '([^' + quote + ']+)' + quote
                m = re.search(pattern, xml, re.I)
                if m:
                    return m.group(1).strip()
            # Handle tags with text content: <tag>content</tag>
            m = re.search(r"<" + b + r"[^>]*>([\s\S]*?)</" + tag + r">", xml, re.I)
            return m.group(1).strip() if m else None

        def get_all_tags(xml, tag):
            b = tag + r"(?=[\s>])"
            return [m.group(1).strip() for m in re.finditer(r"<" + b + r"[^>]*>([\s\S]*?)</" + tag + r">", xml, re.I)]

        def get_all_blocks(xml, tag):
            return [m.group(1).strip() for m in re.finditer(r"<" + tag + r"\b[^>]*>([\s\S]*?)</" + tag + r">", xml, re.I)]

        instrument = get_tag(text, "instrument")
        if instrument:
            run["meta"]["instrument"] = instrument
        date = get_tag(text, "date") or get_tag(text, "runDate")
        if date:
            run["meta"]["runDate"] = date

        targets_seen = set()
        samples_seen = set()
        channels_seen = set()

        # Top-level sample definitions: <sample id="s1"><name>Sample 1</name></sample>
        sample_name_by_id = {}
        for sd in re.finditer(r'<sample\s+id=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</sample>', text, re.I):
            if "<" in sd.group(2):
                nm = get_tag(sd.group(2), "name")
                if nm:
                    sample_name_by_id[sd.group(1)] = nm

        # Extract nested <dye> blocks with child data (multiplex: one block per dye/channel).
        # Plain <dye>FAM</dye> text values are NOT data blocks — skipped.
        def get_dye_blocks(xml):
            blocks = []
            for m in re.finditer(r"<dye\b([^>]*)>([\s\S]*?)</dye>", xml, re.I):
                inner = m.group(2)
                if "<" not in inner:
                    continue
                idm = re.search(r'\bid=["\']([^"\']+)["\']', m.group(1) or "", re.I)
                blocks.append((idm.group(1) if idm else "", inner.strip()))
            return blocks

        # Amplification extraction — supports:
        #   1. <adp><cyc>1</cyc><tmp>60</tmp><fluor>0.1</fluor></adp>  (standard RDML data points)
        #   2. <adp cyc="1" fluor="0.1"/>                               (attribute form)
        #   3. <ad cycle="1">0.1</ad>                                   (alternate instrument exports)
        #   4. <amplificationData>0.1 0.2 ...</amplificationData>       (flat text)
        def extract_amp(scope):
            adps = get_all_blocks(scope, "adp")
            if adps:
                pts = []
                for a in adps:
                    c_raw = get_tag(a, "cyc")
                    f_raw = get_tag(a, "fluor")
                    f = float(f_raw) if f_raw is not None and _is_number(f_raw) else None
                    if f is not None and math.isfinite(f):
                        c = float(c_raw) if c_raw is not None and _is_number(c_raw) else float(len(pts) + 1)
                        pts.append((c, f))
                if pts:
                    pts.sort(key=lambda p: p[0])
                    return [p[1] for p in pts]
            # attribute-form self-closing adp
            attr_pts = []
            for m in re.finditer(r"<adp\s([^>]*?)/>", scope, re.I):
                cm = re.search(r'\b(?:cycle|cyc)=["\']([^"\']+)["\']', m.group(1), re.I)
                fm = re.search(r'\b(?:fluor|value)=["\']([^"\']+)["\']', m.group(1), re.I)
                if fm and _is_number(fm.group(1)):
                    f = float(fm.group(1))
                    if math.isfinite(f):
                        c = float(cm.group(1)) if cm and _is_number(cm.group(1)) else float(len(attr_pts) + 1)
                        attr_pts.append((c, f))
            if attr_pts:
                attr_pts.sort(key=lambda p: p[0])
                return [p[1] for p in attr_pts]
            # <ad cycle="N">value</ad>
            ad_pts = []
            for m in re.finditer(r"<ad\s([^>]*)>([\s\S]*?)</ad>", scope, re.I):
                cm = re.search(r'\bcycle=["\']([^"\']+)["\']', m.group(1), re.I)
                v_raw = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                if _is_number(v_raw):
                    v = float(v_raw)
                    if math.isfinite(v):
                        c = float(cm.group(1)) if cm and _is_number(cm.group(1)) else float(len(ad_pts) + 1)
                        ad_pts.append((c, v))
            if ad_pts:
                ad_pts.sort(key=lambda p: p[0])
                return [p[1] for p in ad_pts]
            # Flat text blob: <amplificationData>0.05 0.06 ...</amplificationData> (or bare-text <data>)
            amp_raw = get_tag(scope, "amplificationData") or get_tag(scope, "data")
            if amp_raw and "<" not in amp_raw:
                vals = [float(v) for v in re.split(r"[\s,;]+", amp_raw) if _is_number(v)]
                if vals:
                    return vals
            return []

        # Melt extraction — supports:
        #   1. <mdp><tmp>60.0</tmp><fluor>1.51</fluor></mdp>  (standard RDML melt data points)
        #   2. <meltData>/<melt> containing temperature/fluorescence tags (flat/legacy)
        def extract_melt(scope):
            mdps = get_all_blocks(scope, "mdp")
            if mdps:
                temps, fluores = [], []
                for m in mdps:
                    t_raw = get_tag(m, "tmp")
                    f_raw = get_tag(m, "fluor")
                    t = float(t_raw) if t_raw is not None and _is_number(t_raw) else None
                    f = float(f_raw) if f_raw is not None and _is_number(f_raw) else None
                    if t is not None and f is not None and math.isfinite(t) and math.isfinite(f):
                        temps.append(t)
                        fluores.append(f)
                if temps:
                    return {"temps": temps, "fluores": fluores}
            melt_raw = get_tag(scope, "meltData") or get_tag(scope, "melt")
            if melt_raw:
                temps = []
                for tag in ["temperature", "temp", "t"]:
                    temps.extend(float(v) for v in get_all_tags(melt_raw, tag) if _is_number(v))
                fluores = []
                for tag in ["fluorescence", "fluor", "f"]:
                    fluores.extend(float(v) for v in get_all_tags(melt_raw, tag) if _is_number(v))
                if temps:
                    return {"temps": temps, "fluores": fluores}
            return None

        # Build one well from a scope (a <dye> block for multiplex, else the whole <react>)
        def add_well(pos, react_xml, scope_xml, dye_id_override=None):
            if not pos:
                return
            pp = parse_position(pos, 96)
            row, col = pp["row"], pp["col"]

            sample_id_raw = get_tag(react_xml, "sample") or get_tag(react_xml, "sampleId") or "Unknown"
            sample_name = sample_name_by_id.get(sample_id_raw, sample_id_raw)
            target_name = get_tag(scope_xml, "target") or get_tag(scope_xml, "targetId") or "Unknown"

            if sample_name not in samples_seen:
                samples_seen.add(sample_name)
                run["samples"].append(make_sample(len(run["samples"]), sample_name, guess_sample_type(sample_name)))
            if target_name not in targets_seen:
                targets_seen.add(target_name)
                run["targets"].append(make_target(len(run["targets"]), target_name, None, guess_reference(target_name)))
            sample_id = next(i for i, s in enumerate(run["samples"]) if s["name"] == sample_name)
            target_id = next(i for i, t in enumerate(run["targets"]) if t["name"] == target_name)

            raw_dye = dye_id_override if dye_id_override else (get_tag(scope_xml, "dye") or get_tag(scope_xml, "fluor") or get_tag(scope_xml, "channel") or "")
            canon = canonical_channel(raw_dye) or "FAM"
            if canon not in channels_seen:
                channels_seen.add(canon)
                run["channels"].append(make_channel(len(run["channels"]), raw_dye, canon))
            channel_id = next(i for i, c in enumerate(run["channels"]) if c["canonical"] == canon)

            cq_raw = get_tag(scope_xml, "cq") or get_tag(scope_xml, "Cq") or get_tag(scope_xml, "ct")
            cq = float(cq_raw) if cq_raw and _is_number(cq_raw) else None
            if cq is not None and not math.isfinite(cq):
                cq = None
            amp = extract_amp(scope_xml)
            melt = extract_melt(scope_xml)
            tm_raw = get_tag(scope_xml, "tm") or get_tag(scope_xml, "Tm")
            tm = float(tm_raw) if tm_raw and _is_number(tm_raw) else None
            if tm is not None and not math.isfinite(tm):
                tm = None

            well = make_well(len(run["wells"]), row, col, "96")
            well["sampleId"] = sample_id
            well["targetId"] = target_id
            well["channelId"] = channel_id
            well["cq"] = cq
            well["tm"] = tm
            well["amplification"] = amp
            well["melt"] = melt
            run["wells"].append(well)

        # Find react elements: support both <react id="A1"> and <react><position>A1</position>
        react_list = []  # list of (pos, react_xml)
        for rm in re.finditer(r'<react\s+id="([^"]+)"[^>]*>([\s\S]*?)</react>', text, re.I):
            react_list.append((rm.group(1).strip(), rm.group(2).strip()))
        if not react_list:
            for rm in re.finditer(r"<react[^>]*>([\s\S]*?)</react>", text, re.I):
                pos_tag = re.search(r"<position[^>]*>(.*?)</position>", rm.group(1), re.I)
                if pos_tag:
                    react_list.append((pos_tag.group(1).strip(), rm.group(1).strip()))
        for pos, react_xml in react_list:
            if not pos:
                continue
            dye_blocks = get_dye_blocks(react_xml)
            if dye_blocks:
                for dye_id, block_xml in dye_blocks:
                    add_well(pos, react_xml, block_xml, dye_id)
            else:
                add_well(pos, react_xml, react_xml, None)

        if not run["channels"]:
            run["channels"].append(make_channel(0, "FAM", "FAM"))
        for t in run["targets"]:
            if t["channelId"] is None:
                t["channelId"] = 0
    except Exception as e:
        raise ValueError(f"RDML parse failed: {e}")
    return run

def _is_number(v):
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def _split_csv_line(line):
    """Quote-aware CSV line splitter (matches JS splitCsvLine)."""
    if '"' not in line:
        return [c.strip() for c in line.split(",")]
    out = []
    cur = ''
    in_q = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_q:
            if ch == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    cur += '"'
                    i += 1
                else:
                    in_q = False
            else:
                cur += ch
        else:
            if ch == '"':
                in_q = True
            elif ch == ',':
                out.append(cur)
                cur = ''
            else:
                cur += ch
        i += 1
    out.append(cur)
    return [c.strip() for c in out]


def parse_cfx_csv(text, file_name=None):
    run = make_run({"fileName": file_name or "cfx_csv", "sourceFormat": "cfx_csv"})
    try:
        lines = [l for l in text.splitlines() if l.strip()]
        if not lines:
            raise ValueError("Empty file")

        # Section markers (CFX "Export to CSV" puts curves in separate sections)
        def marker_idx(pat):
            for i, l in enumerate(lines):
                if re.match(pat, l.strip().strip('"'), re.I):
                    return i
            return -1

        amp_marker = marker_idx(r"amplification data")
        melt_marker = marker_idx(r"melt data")
        markers = [x for x in (amp_marker, melt_marker) if x >= 0]
        summary_end = min(markers) if markers else len(lines)

        # Find header row within summary region
        header_idx = -1
        headers = []
        for i in range(summary_end):
            cols = _split_csv_line(lines[i])
            if any(re.search(r"well", c, re.I) for c in cols) and (any(re.search(r"fluor|channel|dye", c, re.I) for c in cols) or any(re.search(r"target", c, re.I) for c in cols)):
                header_idx = i
                headers = cols
                break

        targets_seen = set()
        samples_seen = set()
        channels_seen = set()

        def push_well_meta(row, col, raw_fluor, sample_name, target_name, cq, cq_sd, tm, amp, melt):
            if sample_name not in samples_seen:
                samples_seen.add(sample_name)
                run["samples"].append(make_sample(len(run["samples"]), sample_name, guess_sample_type(sample_name)))
            if target_name not in targets_seen:
                targets_seen.add(target_name)
                run["targets"].append(make_target(len(run["targets"]), target_name, None, guess_reference(target_name)))
            canon = canonical_channel(raw_fluor) or "FAM"
            if canon not in channels_seen:
                channels_seen.add(canon)
                run["channels"].append(make_channel(len(run["channels"]), raw_fluor, canon))
            sample_id = next(i for i, s in enumerate(run["samples"]) if s["name"] == sample_name)
            target_id = next(i for i, t in enumerate(run["targets"]) if t["name"] == target_name)
            channel_id = next(i for i, c in enumerate(run["channels"]) if c["canonical"] == canon)

            well = make_well(len(run["wells"]), row, col, "96")
            well["sampleId"] = sample_id
            well["targetId"] = target_id
            well["channelId"] = channel_id
            well["cq"] = cq if cq is not None and math.isfinite(cq) else None
            well["cqSD"] = cq_sd if cq_sd is not None and math.isfinite(cq_sd) else None
            well["tm"] = tm if tm is not None and math.isfinite(tm) else None
            well["amplification"] = amp or []
            well["melt"] = melt
            run["wells"].append(well)
            return well

        def finish():
            if not run["channels"]:
                run["channels"].append(make_channel(0, "FAM", "FAM"))
            for t in run["targets"]:
                if t["channelId"] is None:
                    t["channelId"] = 0

        def parse_section(marker):
            if marker < 0 or marker + 1 >= len(lines):
                return None
            s_headers = _split_csv_line(lines[marker + 1])

            def s_idx(pat):
                for i, h in enumerate(s_headers):
                    if re.search(pat, h, re.I):
                        return i
                return -1

            s_well = s_idx(r"well")
            if s_well < 0:
                return None
            s_fluor = s_idx(r"fluor|channel|dye")
            s_cycle = s_idx(r"cycle")
            s_temp = s_idx(r"temp|temperature")
            s_value = s_idx(r"^value$|fluorescen|signal|^data$")
            if s_value < 0:
                return None
            by_key = {}
            for i in range(marker + 2, len(lines)):
                raw = lines[i].strip()
                if re.match(r"^(amplification data|melt data)", raw.strip('"'), re.I):
                    break
                cols = _split_csv_line(lines[i])
                if len(cols) < 2:
                    continue
                well_name = (cols[s_well] if s_well < len(cols) else "").strip()
                if not well_name:
                    continue
                pp = parse_position(well_name, 96)
                row, col = pp["row"], pp["col"]
                canon = (canonical_channel(cols[s_fluor] if s_fluor >= 0 and s_fluor < len(cols) else "") or "FAM") if s_fluor >= 0 else ""
                try:
                    v = float(cols[s_value])
                except (ValueError, IndexError, TypeError):
                    continue
                if not math.isfinite(v):
                    continue
                key = f"{row},{col},{canon}"
                x = None
                if s_temp >= 0:
                    try:
                        x = float(cols[s_temp])
                    except (ValueError, IndexError, TypeError):
                        x = None
                if x is None and s_cycle >= 0:
                    try:
                        x = float(cols[s_cycle])
                    except (ValueError, IndexError, TypeError):
                        x = None
                if x is None or not math.isfinite(x):
                    x = len(by_key[key]["pts"]) + 1 if key in by_key else 1
                if key not in by_key:
                    by_key[key] = {"row": row, "col": col, "canon": canon, "pts": []}
                by_key[key]["pts"].append({"x": x, "v": v})
            return by_key

        def attach_section(by_key, kind):
            if not by_key:
                return
            for w in run["wells"]:
                ch = run["channels"][w["channelId"]]
                canon = ch["canonical"] if ch else ""
                entry = by_key.get(f"{w['row']},{w['col']},{canon}") or by_key.get(f"{w['row']},{w['col']},") or by_key.get(f"{w['row']},{w['col']},FAM")
                if not entry:
                    continue
                pts = sorted(entry["pts"], key=lambda p: p["x"])
                if kind == "amp":
                    if not w["amplification"]:
                        w["amplification"] = [p["v"] for p in pts]
                else:
                    if not w.get("melt"):
                        w["melt"] = {"temps": [p["x"] for p in pts], "fluores": [p["v"] for p in pts]}

        # No summary header: pure section file (amplification-only or melt-only export)
        if header_idx == -1:
            section = parse_section(amp_marker if amp_marker >= 0 else melt_marker)
            if section:
                for key in section:
                    e = section[key]
                    pts = sorted(e["pts"], key=lambda p: p["x"])
                    well_name = chr(65 + e["row"]) + str(e["col"] + 1)
                    push_well_meta(
                        e["row"], e["col"], e["canon"], well_name, "Unknown",
                        None, None, None,
                        [p["v"] for p in pts] if amp_marker >= 0 else [],
                        {"temps": [p["x"] for p in pts], "fluores": [p["v"] for p in pts]} if melt_marker >= 0 else None,
                    )
                finish()
                return run
            # legacy fallback: first line as header
            header_idx = 0
            headers = _split_csv_line(lines[0])

        def col_index(name):
            for i, h in enumerate(headers):
                if re.search(name, h, re.I):
                    return i
            return -1

        well_col = col_index(r"well")
        fluor_col = col_index(r"fluor|channel|dye")
        target_col = col_index(r"target")
        content_col = col_index(r"content")
        cq_col = col_index(r"cq|ct")
        cq_sd_col = col_index(r"cq.*std|std.*dev|cqsd")
        tm_col = col_index(r"tm|melt")
        cycle_col = col_index(r"cycle")
        value_col = col_index(r"^value$|fluorescen|signal|^data$")
        # wide cycle columns: "Cycle 1"... or bare numeric "1","2",...
        amp_cols = [i for i, h in enumerate(headers) if re.match(r"^cycle\s*\d+$", h, re.I) or re.match(r"^\d+$", h)]

        # Long-format table: one row per cycle (Well,Fluor,Cycle,Value)
        if well_col >= 0 and cycle_col >= 0 and value_col >= 0:
            points_by_key = {}
            meta_by_key = {}
            for i in range(header_idx + 1, summary_end):
                cols = _split_csv_line(lines[i])
                if len(cols) < 2:
                    continue
                well_name = (cols[well_col] if well_col < len(cols) else "").strip()
                if not well_name:
                    continue
                pp = parse_position(well_name, 96)
                row, col = pp["row"], pp["col"]
                raw_fluor = (cols[fluor_col] if fluor_col >= 0 and fluor_col < len(cols) else "") or ""
                canon = canonical_channel(raw_fluor) or "FAM"
                key = f"{row},{col},{canon}"
                try:
                    cyc = float(cols[cycle_col])
                except (ValueError, IndexError, TypeError):
                    cyc = None
                try:
                    val = float(cols[value_col])
                except (ValueError, IndexError, TypeError):
                    val = None
                if key not in points_by_key:
                    points_by_key[key] = []
                if cyc is not None and val is not None and math.isfinite(cyc) and math.isfinite(val):
                    points_by_key[key].append({"c": cyc, "v": val})
                if key not in meta_by_key:
                    cq_raw = (cols[cq_col] if cq_col >= 0 and cq_col < len(cols) else "") or ""
                    content = (cols[content_col] if content_col >= 0 and content_col < len(cols) else "") or ""
                    target_name = (cols[target_col] if target_col >= 0 and target_col < len(cols) else "") or ""
                    cq = float(cq_raw) if cq_raw and _is_number(cq_raw) else None
                    meta_by_key[key] = {
                        "row": row, "col": col, "raw_fluor": raw_fluor,
                        "sample_name": content or well_name,
                        "target_name": target_name or "Unknown",
                        "cq": cq,
                    }
            for key in points_by_key:
                meta = meta_by_key[key]
                pts = sorted(points_by_key[key], key=lambda p: p["c"])
                push_well_meta(meta["row"], meta["col"], meta["raw_fluor"], meta["sample_name"],
                               meta["target_name"], meta["cq"], None, None,
                               [p["v"] for p in pts], None)
            attach_section(parse_section(amp_marker), "amp")
            attach_section(parse_section(melt_marker), "melt")
            finish()
            return run

        # Summary table (one row per well)
        for i in range(header_idx + 1, summary_end):
            cols = _split_csv_line(lines[i])
            if len(cols) < 2:
                continue
            well_name = (cols[well_col] if well_col >= 0 and well_col < len(cols) else "") or ""
            if not well_name:
                continue

            pp = parse_position(well_name, 96)
            row, col = pp["row"], pp["col"]
            raw_fluor = (cols[fluor_col] if fluor_col >= 0 and fluor_col < len(cols) else "") or ""
            target_name = (cols[target_col] if target_col >= 0 and target_col < len(cols) else "") or "Unknown"
            content = (cols[content_col] if content_col >= 0 and content_col < len(cols) else "") or ""
            cq_raw = (cols[cq_col] if cq_col >= 0 and cq_col < len(cols) else "") or ""
            cq = float(cq_raw) if cq_raw and _is_number(cq_raw) else None
            cq_sd_raw = (cols[cq_sd_col] if cq_sd_col >= 0 and cq_sd_col < len(cols) else "") or ""
            cq_sd = float(cq_sd_raw) if cq_sd_raw and _is_number(cq_sd_raw) else None
            tm_raw = (cols[tm_col] if tm_col >= 0 and tm_col < len(cols) else "") or ""
            tm = float(tm_raw) if tm_raw and _is_number(tm_raw) else None

            amp = []
            if amp_cols:
                amp = [float(cols[ci]) for ci in amp_cols if ci < len(cols) and _is_number(cols[ci])]

            push_well_meta(row, col, raw_fluor, content or well_name, target_name or "Unknown",
                           cq, cq_sd, tm, amp, None)

        # Attach curve/melt sections (long tables after markers)
        attach_section(parse_section(amp_marker), "amp")
        attach_section(parse_section(melt_marker), "melt")

        finish()
    except Exception as e:
        raise ValueError(f"CFX CSV parse failed: {e}")
    return run

def parse_template(text, file_name=None):
    run = make_run({"fileName": file_name or "template", "sourceFormat": "template"})
    try:
        lines = [l for l in text.splitlines() if l.strip()]
        if not lines:
            raise ValueError("Empty file")
        delim = "\t" if "\t" in lines[0] else ","

        def split_row(line):
            if delim == ",":
                return _split_csv_line(line)
            return [c.strip().strip('"') for c in line.split(delim)]

        headers = split_row(lines[0])

        def col_index(name):
            for i, h in enumerate(headers):
                if re.search(name, h, re.I):
                    return i
            return -1

        well_col = col_index(r"well")
        sample_col = col_index(r"sample")
        target_col = col_index(r"target")
        channel_col = col_index(r"channel|fluor|dye")
        content_col = col_index(r"content")
        cq_col = col_index(r"cq|ct")
        cq_sd_col = col_index(r"cqsd|cq.*sd|std")
        tm_col = col_index(r"tm|melt")
        amp_col = col_index(r"amplif|data|curve")
        # wide cycle columns: "Cycle 1"... or bare numeric "1","2",...
        amp_cols = [i for i, h in enumerate(headers) if re.match(r"^cycle\s*\d+$", h, re.I) or re.match(r"^\d+$", h)]

        targets_seen = set()
        samples_seen = set()
        channels_seen = set()

        for i in range(1, len(lines)):
            cols = split_row(lines[i])
            if len(cols) < 2:
                continue
            well_name = cols[well_col] if well_col >= 0 else cols[0]
            if not well_name:
                continue

            pp = parse_position(well_name, 96)
            sample_name = (cols[sample_col] if sample_col >= 0 else "") or well_name
            target_name = cols[target_col] if target_col >= 0 else "Unknown"
            raw_channel = cols[channel_col] if channel_col >= 0 else "FAM"
            content = cols[content_col] if content_col >= 0 else ""
            cq_raw = cols[cq_col] if cq_col >= 0 else ""
            cq = float(cq_raw) if cq_raw and _is_number(cq_raw) else None
            if cq is not None and not math.isfinite(cq):
                cq = None
            cq_sd_raw = cols[cq_sd_col] if cq_sd_col >= 0 else ""
            cq_sd = float(cq_sd_raw) if cq_sd_raw and _is_number(cq_sd_raw) else None
            tm_raw = cols[tm_col] if tm_col >= 0 else ""
            tm = float(tm_raw) if tm_raw and _is_number(tm_raw) else None

            if sample_name not in samples_seen:
                samples_seen.add(sample_name)
                run["samples"].append(make_sample(len(run["samples"]), sample_name, guess_sample_type(sample_name)))
            if target_name not in targets_seen:
                targets_seen.add(target_name)
                run["targets"].append(make_target(len(run["targets"]), target_name, None, guess_reference(target_name)))
            canon = canonical_channel(raw_channel) or "FAM"
            if canon not in channels_seen:
                channels_seen.add(canon)
                run["channels"].append(make_channel(len(run["channels"]), raw_channel, canon))

            sample_id = next(i for i, s in enumerate(run["samples"]) if s["name"] == sample_name)
            target_id = next(i for i, t in enumerate(run["targets"]) if t["name"] == target_name)
            channel_id = next(i for i, c in enumerate(run["channels"]) if c["canonical"] == canon)

            amp = []
            if amp_col >= 0 and amp_col < len(cols) and cols[amp_col]:
                amp = [float(v) for v in re.split(r"[;|\s]+", cols[amp_col]) if _is_number(v)]
            elif amp_cols:
                amp = [float(cols[ci]) for ci in amp_cols if ci < len(cols) and _is_number(cols[ci])]

            well = make_well(len(run["wells"]), pp["row"], pp["col"], "96")
            well["sampleId"] = sample_id
            well["targetId"] = target_id
            well["channelId"] = channel_id
            well["cq"] = cq
            well["cqSD"] = cq_sd
            well["tm"] = tm
            well["amplification"] = amp
            run["wells"].append(well)

        if not run["channels"]:
            run["channels"].append(make_channel(0, "FAM", "FAM"))
        for t in run["targets"]:
            if t["channelId"] is None:
                t["channelId"] = 0
    except Exception as e:
        raise ValueError(f"Template parse failed: {e}")
    return run


def parse_xlsx_file(path):
    """Parse an XLSX file using openpyxl. Returns canonical Run."""
    try:
        import openpyxl
    except ImportError:
        raise ValueError("openpyxl not installed")
    import os
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append(list(row))
    if not rows:
        raise ValueError("Empty spreadsheet")
    headers = [str(h).strip() if h is not None else '' for h in rows[0]]
    def col_index(name):
        for i, h in enumerate(headers):
            if re.search(name, h, re.I):
                return i
        return -1
    well_col = col_index(r"well")
    sample_col = col_index(r"sample")
    target_col = col_index(r"target")
    channel_col = col_index(r"channel|fluor|dye")
    content_col = col_index(r"content")
    cq_col = col_index(r"cq|ct")
    cq_sd_col = col_index(r"cqsd|cq.*sd|std")
    tm_col = col_index(r"tm|melt")
    amp_col = col_index(r"amplif|data|curve")

    run = make_run({"fileName": os.path.basename(path), "sourceFormat": "xlsx"})
    targets_seen = set()
    samples_seen = set()
    channels_seen = set()

    for i in range(1, len(rows)):
        cols = rows[i]
        if not cols or all(c is None or str(c).strip() == '' for c in cols):
            continue
        well_name = str(cols[well_col]).strip() if well_col >= 0 and well_col < len(cols) and cols[well_col] is not None else str(cols[0] or '').strip()
        if not well_name:
            continue
        pp = parse_position(well_name, 96)
        sample_name = str(cols[sample_col]).strip() if sample_col >= 0 and sample_col < len(cols) and cols[sample_col] is not None else well_name
        target_name = str(cols[target_col]).strip() if target_col >= 0 and target_col < len(cols) and cols[target_col] is not None else 'Unknown'
        raw_channel = str(cols[channel_col]).strip() if channel_col >= 0 and channel_col < len(cols) and cols[channel_col] is not None else 'FAM'
        content = str(cols[content_col]).strip() if content_col >= 0 and content_col < len(cols) and cols[content_col] is not None else ''
        cq_raw = cols[cq_col] if cq_col >= 0 and cq_col < len(cols) else None
        cq = float(cq_raw) if cq_raw is not None and _is_number(str(cq_raw)) else None
        if cq is not None and not math.isfinite(cq):
            cq = None
        cq_sd_raw = cols[cq_sd_col] if cq_sd_col >= 0 and cq_sd_col < len(cols) else None
        cq_sd = float(cq_sd_raw) if cq_sd_raw is not None and _is_number(str(cq_sd_raw)) else None
        tm_raw = cols[tm_col] if tm_col >= 0 and tm_col < len(cols) else None
        tm = float(tm_raw) if tm_raw is not None and _is_number(str(tm_raw)) else None

        if sample_name not in samples_seen:
            samples_seen.add(sample_name)
            run["samples"].append(make_sample(len(run["samples"]), sample_name, guess_sample_type(sample_name)))
        if target_name not in targets_seen:
            targets_seen.add(target_name)
            run["targets"].append(make_target(len(run["targets"]), target_name, None, guess_reference(target_name)))
        canon = canonical_channel(raw_channel) or "FAM"
        if canon not in channels_seen:
            channels_seen.add(canon)
            run["channels"].append(make_channel(len(run["channels"]), raw_channel, canon))

        sample_id = next(i for i, s in enumerate(run["samples"]) if s["name"] == sample_name)
        target_id = next(i for i, t in enumerate(run["targets"]) if t["name"] == target_name)
        channel_id = next(i for i, c in enumerate(run["channels"]) if c["canonical"] == canon)

        amp = []
        if amp_col >= 0 and amp_col < len(cols) and cols[amp_col] is not None:
            amp = [float(v) for v in str(cols[amp_col]).split(";") if _is_number(v)]

        well = make_well(len(run["wells"]), pp["row"], pp["col"], "96")
        well["sampleId"] = sample_id
        well["targetId"] = target_id
        well["channelId"] = channel_id
        well["cq"] = cq
        well["cqSD"] = cq_sd
        well["tm"] = tm
        well["amplification"] = amp
        run["wells"].append(well)

    if not run["channels"]:
        run["channels"].append(make_channel(0, "FAM", "FAM"))
    for t in run["targets"]:
        if t["channelId"] is None:
            t["channelId"] = 0
    return run


def parse_run(text, file_name=None):
    fmt = detect_format(text, file_name)
    if fmt == "rdml":
        return parse_rdml(text, file_name)
    elif fmt == "cfx_csv":
        return parse_cfx_csv(text, file_name)
    elif fmt == "template":
        return parse_template(text, file_name)
    elif fmt == "xlsx":
        return parse_xlsx_file(file_name) if file_name else None
    elif fmt == "xls":
        raise ValueError("Legacy Excel .xls detected. Please re-save as .xlsx or export as CSV.")
    elif fmt == "qbg":
        raise ValueError("Qiagen Rotor-Gene .qbg is a proprietary binary format. Please export from Rotor-Gene Q: File → Export → Excel/CSV.")
    elif fmt == "pcrd":
        raise ValueError("Bio-Rad .pcrd is a proprietary binary format. Please export from CFX Maestro: File → Export → RDML or CSV.")
    elif fmt == "zip":
        raise ValueError("ZIP archive detected. Please extract the file and upload individually.")
    else:
        raise ValueError("Unknown format. Try the generic template or check your export.")


# ── Analysis functions ──

def linear_regression(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    syy = sum(y * y for y in ys)
    denom = n * sxx - sx * sx
    if denom == 0:
        return None
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    ss_res = syy - 2 * slope * sxy - 2 * intercept * sy + slope * slope * sxx + 2 * slope * intercept * sx + n * intercept * intercept
    ss_tot = syy - (sy * sy) / n
    r2 = 1.0 if ss_tot == 0 else 1 - ss_res / ss_tot
    r2 = max(0.0, min(1.0, r2))
    return {"slope": slope, "intercept": intercept, "r2": r2}


def efficiency_from_slope(slope):
    if slope == 0:
        return None
    return (10 ** (-1.0 / slope) - 1) * 100


def compute_standard_curves(run):
    curves = {}
    for t in run["targets"]:
        std_wells = [w for w in run["wells"]
                     if w["targetId"] == t["id"] and w["cq"] is not None]
        std_wells = [w for w in std_wells
                     if run["samples"][w["sampleId"]]["type"] == "standard"
                     and run["samples"][w["sampleId"]].get("quantity") is not None
                     and run["samples"][w["sampleId"]]["quantity"] > 0]
        if len(std_wells) < 2:
            curves[t["id"]] = None
            continue
        xs = [math.log10(run["samples"][w["sampleId"]]["quantity"]) for w in std_wells]
        ys = [w["cq"] for w in std_wells]
        reg = linear_regression(xs, ys)
        if not reg:
            curves[t["id"]] = None
            continue
        curves[t["id"]] = {
            "slope": reg["slope"],
            "intercept": reg["intercept"],
            "r2": reg["r2"],
            "efficiencyPct": efficiency_from_slope(reg["slope"]),
            "n": len(std_wells),
        }
    return curves


def quantify_unknowns(run, curves):
    result = {}
    for w in run["wells"]:
        s = run["samples"][w["sampleId"]]
        if s["type"] != "unknown":
            continue
        if w["cq"] is None:
            continue
        curve = curves.get(w["targetId"])
        if not curve:
            continue
        q = 10 ** ((w["cq"] - curve["intercept"]) / curve["slope"])
        result[w["id"]] = q
    return result


def compute_expression(run, curves, reference_targets, control_sample, method="pfaffl"):
    expr = {}
    ref_targets = reference_targets if reference_targets else [t["id"] for t in run["targets"] if t.get("isReference")]
    if not ref_targets:
        return expr

    # group wells by sample
    by_sample = {}
    for w in run["wells"]:
        if w["cq"] is None:
            continue
        by_sample.setdefault(w["sampleId"], []).append(w)

    sample_target_cq = {}
    for sid, wells in by_sample.items():
        sample_target_cq[sid] = {}
        by_target = {}
        for w in wells:
            by_target.setdefault(w["targetId"], []).append(w["cq"])
        for tid, cqs in by_target.items():
            mean = sum(cqs) / len(cqs)
            sd = (sum((v - mean) ** 2 for v in cqs) / (len(cqs) - 1)) ** 0.5 if len(cqs) > 1 else 0.0
            sample_target_cq[sid][tid] = {"mean": mean, "sd": sd, "n": len(cqs)}

    control = sample_target_cq.get(control_sample)
    if not control:
        return expr

    for sid, stc in sample_target_cq.items():
        for t in run["targets"]:
            tid = t["id"]
            if tid not in stc:
                continue
            ref_cqs = [stc[rt]["mean"] for rt in ref_targets if rt in stc]
            if not ref_cqs:
                continue
            ref_mean = sum(ref_cqs) / len(ref_cqs)
            ref_sd = (sum((v - ref_mean) ** 2 for v in ref_cqs) / (len(ref_cqs) - 1)) ** 0.5 if len(ref_cqs) > 1 else 0.0

            d_cq = stc[tid]["mean"] - ref_mean
            d_cq_sd = (stc[tid]["sd"] ** 2 + ref_sd ** 2) ** 0.5

            ctrl_ref_cqs = [control[rt]["mean"] for rt in ref_targets if rt in control]
            ctrl_ref_mean = sum(ctrl_ref_cqs) / len(ctrl_ref_cqs) if ctrl_ref_cqs else 0.0
            ctrl_d_cq = control[tid]["mean"] - ctrl_ref_mean if tid in control else 0.0

            dd_cq = d_cq - ctrl_d_cq

            if method == "pfaffl":
                t_eff = (curves[tid]["efficiencyPct"] / 100 + 1) if (curves.get(tid) and curves[tid].get("efficiencyPct") is not None) else 2.0
                r_effs = [(curves[rt]["efficiencyPct"] / 100 + 1) if (curves.get(rt) and curves[rt].get("efficiencyPct") is not None) else 2.0 for rt in ref_targets]
                r_eff_mean = sum(r_effs) / len(r_effs) if r_effs else 2.0
                target_ratio = t_eff ** (ctrl_d_cq - d_cq)
                ref_ratio = r_eff_mean ** (ctrl_ref_mean - ref_mean)
                fold = target_ratio / ref_ratio if ref_ratio != 0 else float("inf")
                fold_sd = abs(fold * math.log(2) * d_cq_sd)
            else:
                fold = 2 ** (-dd_cq)
                fold_sd = abs(fold * math.log(2) * d_cq_sd)

            expr[f"{sid}_{tid}"] = {
                "sampleId": sid,
                "targetId": tid,
                "dCq": d_cq,
                "dCqSd": d_cq_sd,
                "ddCq": dd_cq,
                "fold": fold,
                "foldSD": fold_sd,
                "method": method,
                "n": stc[tid]["n"],
            }
    return expr


def compute_qc(run, curves, thresholds=None):
    thresholds = thresholds or {}
    t = {
        "ntcCq": thresholds.get("ntcCq", 35),
        "replicateSd": thresholds.get("replicateSd", 0.5),
        "effMin": thresholds.get("effMin", 90),
        "effMax": thresholds.get("effMax", 110),
        "r2Min": thresholds.get("r2Min", 0.99),
        "lateCq": thresholds.get("lateCq", 35),
    }
    qc = {"wells": {}, "run": []}

    for w in run["wells"]:
        flags = []
        s = run["samples"][w["sampleId"]]
        if s["type"] == "ntc" and w["cq"] is not None:
            sev = "strong" if w["cq"] < t["ntcCq"] else "weak"
            flags.append({"code": "NTC_AMP", "severity": sev, "detail": f"NTC Cq = {w['cq']}"})
        if w["cq"] is not None and w["cq"] > t["lateCq"]:
            flags.append({"code": "LATE_CQ", "severity": "info", "detail": f"Cq {w['cq']} > {t['lateCq']}"})
        if w["cq"] is None and (not w["amplification"] or max(w["amplification"] + [0]) < 1):
            flags.append({"code": "NO_AMP", "severity": "info", "detail": "No amplification detected"})
        if w.get("tmPeaks") and len(w["tmPeaks"]) > 1:
            flags.append({"code": "MULTI_PEAK", "severity": "warning", "detail": f"{len(w['tmPeaks'])} melt peaks"})
        qc["wells"][w["id"]] = flags

    # replicate SD
    by_sample_target = {}
    for w in run["wells"]:
        if w["cq"] is None:
            continue
        key = f"{w['sampleId']}_{w['targetId']}"
        by_sample_target.setdefault(key, []).append(w["cq"])
    for key, cqs in by_sample_target.items():
        if len(cqs) < 2:
            continue
        mean = sum(cqs) / len(cqs)
        sd = (sum((v - mean) ** 2 for v in cqs) / (len(cqs) - 1)) ** 0.5
        if sd > t["replicateSd"]:
            qc["run"].append({"code": "HIGH_REPLICATE_SD", "severity": "warning", "detail": f"{key}: SD = {sd:.2f} > {t['replicateSd']}"})

    # efficiency flags
    for tid, curve in curves.items():
        if not curve:
            continue
        if curve["efficiencyPct"] < t["effMin"] or curve["efficiencyPct"] > t["effMax"]:
            qc["run"].append({"code": "EFFICIENCY_OUT_OF_RANGE", "severity": "warning", "detail": f"Target {tid}: E = {curve['efficiencyPct']:.1f}%"})
        if curve["r2"] < t["r2Min"]:
            qc["run"].append({"code": "LOW_R2", "severity": "warning", "detail": f"Target {tid}: R² = {curve['r2']:.4f}"})

    return qc


def savitzky_golay_derivative(temps, fluores, window_size=7):
    n = len(temps)
    if n < window_size:
        return {"temps": list(temps), "derivative": [0.0] * n}
    half = window_size // 2
    deriv = [0.0] * n
    for i in range(half, n - half):
        num = 0.0
        den = 0.0
        for j in range(-half, half + 1):
            w = 1 - abs(j) / (half + 1)
            denom_t = 2 * (temps[i + j] - temps[i - j]) if (temps[i + j] - temps[i - j]) != 0 else 1
            num += w * (fluores[i + j] - fluores[i - j]) / denom_t
            den += w
        deriv[i] = (num / den) if den > 0 else 0.0
    return {"temps": list(temps), "derivative": [-v for v in deriv]}


def detect_tm_peaks(temps, derivative, threshold=0.1):
    peaks = []
    max_d = max(abs(v) for v in derivative) if derivative else 0
    thr = max_d * threshold
    for i in range(1, len(derivative) - 1):
        if derivative[i] > derivative[i - 1] and derivative[i] > derivative[i + 1] and derivative[i] > thr:
            peaks.append({"temp": temps[i], "height": derivative[i]})
    return peaks


import base64


def serialize_view_state(vs):
    return base64.b64encode(json.dumps(vs).encode()).decode()


def deserialize_view_state(b64):
    try:
        return json.loads(base64.b64decode(b64).decode())
    except Exception:
        return None


def generate_methods(run, analysis, settings=None):
    settings = settings or (analysis.get("settings") if analysis else {}) or {}
    parts = []
    parts.append("Cq values were determined by " + (run["meta"].get("instrument") or "the instrument") + " software.")
    curves = analysis.get("standardCurves", {}) if analysis else {}
    effs = []
    for tid, c in curves.items():
        if not c:
            continue
        t = next((x for x in run["targets"] if x["id"] == int(tid)), None)
        name = t["name"] if t else "target " + str(tid)
        effs.append(f"{name}: E={c['efficiencyPct']:.1f}%, R²={c['r2']:.3f}")
    if effs:
        parts.append("Efficiency (" + "; ".join(effs) + ") was calculated from standard curve slope.")
    method = settings.get("method") or (analysis.get("settings", {}).get("method") if analysis else None) or "livak"
    method_name = "Pfaffl method (efficiency-corrected)" if method == "pfaffl" else "Livak method (2^-ddCq)"
    ref_targets = settings.get("referenceTargets") or (analysis.get("settings", {}).get("referenceTargets") if analysis else []) or []
    ref_names = []
    for tid in ref_targets:
        t = next((x for x in run["targets"] if x["id"] == tid), None)
        ref_names.append(t["name"] if t else str(tid))
    ctrl_sample = settings.get("controlSample")
    if ctrl_sample is None and analysis:
        ctrl_sample = analysis.get("settings", {}).get("controlSample")
    ctrl_name = next((s["name"] for s in run["samples"] if s["id"] == ctrl_sample), "control")
    if ref_names:
        parts.append("Relative expression was quantified by the " + method_name + " using " + ", ".join(ref_names) + " as reference gene(s) and " + ctrl_name + " as calibrator.")
    parts.append("Research use only. Not for clinical diagnostic decisions.")
    return " ".join(parts)


def analyze_run(run, settings=None):
    settings = settings or {}
    curves = compute_standard_curves(run)
    ref_targets = settings.get("referenceTargets") or [t["id"] for t in run["targets"] if t.get("isReference")]
    control_sample = settings.get("controlSample")
    if control_sample is None:
        ctrl = next((s for s in run["samples"] if s["type"] == "control"), None)
        control_sample = ctrl["id"] if ctrl else (run["samples"][0]["id"] if run["samples"] else None)
    method = settings.get("method") or ("pfaffl" if any(c for c in curves.values() if c) else "livak")
    expression = compute_expression(run, curves, ref_targets, control_sample, method)
    qc = compute_qc(run, curves, settings.get("thresholds"))
    return {
        "standardCurves": curves,
        "expression": expression,
        "qc": qc,
        "settings": {"referenceTargets": ref_targets, "controlSample": control_sample, "method": method},
    }
