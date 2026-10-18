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


def detect_format(text):
    t = (text or "").strip()
    if not t:
        return "unknown"
    if t.startswith("<?xml") or t.startswith("<rdml") or "<rdml" in t:
        return "rdml"
    if "Well,Fluor,Target,Content" in t or "Well\tFluor\tTarget" in t:
        return "cfx_csv"
    if "Amplification Data" in t and "Well" in t:
        return "cfx_csv"
    if "Cq,Well" in t or "Well,Cq" in t:
        return "cfx_csv"
    if "well\tsample\ttarget\tchannel" in t.lower() or "Well\tSample\tTarget\tChannel" in t:
        return "template"
    return "unknown"


def parse_rdml(text, file_name=None):
    run = make_run({"fileName": file_name or "rdml", "sourceFormat": "rdml"})
    try:
        def get_tag(xml, tag):
            m = re.search(r"<" + tag + r"[^>]*>([\s\S]*?)</" + tag + r">", xml, re.I)
            return m.group(1).strip() if m else None

        def get_all_tags(xml, tag):
            return [m.group(1).strip() for m in re.finditer(r"<" + tag + r"[^>]*>([\s\S]*?)</" + tag + r">", xml, re.I)]

        instrument = get_tag(text, "instrument")
        if instrument:
            run["meta"]["instrument"] = instrument
        date = get_tag(text, "date") or get_tag(text, "runDate")
        if date:
            run["meta"]["runDate"] = date

        targets_seen = set()
        samples_seen = set()
        channels_seen = set()

        for react_xml in get_all_tags(text, "react"):
            pos = get_tag(react_xml, "position") or get_tag(react_xml, "well")
            if not pos:
                continue
            pp = parse_position(pos, 96)
            row, col = pp["row"], pp["col"]

            sample_name = get_tag(react_xml, "sample") or get_tag(react_xml, "sampleId") or "Unknown"
            target_name = get_tag(react_xml, "target") or get_tag(react_xml, "targetId") or "Unknown"

            if sample_name not in samples_seen:
                samples_seen.add(sample_name)
                run["samples"].append(make_sample(len(run["samples"]), sample_name, guess_sample_type(sample_name)))
            if target_name not in targets_seen:
                targets_seen.add(target_name)
                run["targets"].append(make_target(len(run["targets"]), target_name, None, guess_reference(target_name)))

            sample_id = next(i for i, s in enumerate(run["samples"]) if s["name"] == sample_name)
            target_id = next(i for i, t in enumerate(run["targets"]) if t["name"] == target_name)

            raw_dye = get_tag(react_xml, "dye") or get_tag(react_xml, "fluor") or get_tag(react_xml, "channel") or ""
            canon = canonical_channel(raw_dye) or "FAM"
            if canon not in channels_seen:
                channels_seen.add(canon)
                run["channels"].append(make_channel(len(run["channels"]), raw_dye, canon))
            channel_id = next(i for i, c in enumerate(run["channels"]) if c["canonical"] == canon)

            cq_raw = get_tag(react_xml, "cq") or get_tag(react_xml, "Cq") or get_tag(react_xml, "ct")
            cq = float(cq_raw) if cq_raw and _is_number(cq_raw) else None
            if cq is not None and not math.isfinite(cq):
                cq = None

            amp_raw = get_tag(react_xml, "amplificationData") or get_tag(react_xml, "data")
            amp = []
            if amp_raw:
                amp = [float(v) for v in re.split(r"[\s,;]+", amp_raw) if _is_number(v)]

            melt_raw = get_tag(react_xml, "meltData") or get_tag(react_xml, "melt")
            melt = None
            if melt_raw:
                temps = []
                for tag in ["temperature", "temp", "t"]:
                    temps.extend(float(v) for v in get_all_tags(melt_raw, tag) if _is_number(v))
                fluores = []
                for tag in ["fluorescence", "fluor", "f"]:
                    fluores.extend(float(v) for v in get_all_tags(melt_raw, tag) if _is_number(v))
                if temps:
                    melt = {"temps": temps, "fluores": fluores}

            tm_raw = get_tag(react_xml, "tm") or get_tag(react_xml, "Tm")
            tm = float(tm_raw) if tm_raw and _is_number(tm_raw) else None

            well = make_well(len(run["wells"]), row, col, "96")
            well["sampleId"] = sample_id
            well["targetId"] = target_id
            well["channelId"] = channel_id
            well["cq"] = cq
            well["tm"] = tm
            well["amplification"] = amp
            well["melt"] = melt
            run["wells"].append(well)

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


def parse_cfx_csv(text, file_name=None):
    run = make_run({"fileName": file_name or "cfx_csv", "sourceFormat": "cfx_csv"})
    try:
        lines = [l for l in text.splitlines() if l.strip()]
        if not lines:
            raise ValueError("Empty file")

        header_idx = -1
        headers = []
        for i, line in enumerate(lines):
            cols = [c.strip().strip('"') for c in line.split(",")]
            if any(re.search(r"well", c, re.I) for c in cols) and (any(re.search(r"fluor|channel|dye", c, re.I) for c in cols) or any(re.search(r"target", c, re.I) for c in cols)):
                header_idx = i
                headers = cols
                break
        if header_idx == -1:
            header_idx = 0
            headers = [c.strip().strip('"') for c in lines[0].split(",")]

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
        amp_cols = [i for i, h in enumerate(headers) if re.match(r"^cycle\s*\d+$", h, re.I) or re.match(r"^\d+$", h)]

        targets_seen = set()
        samples_seen = set()
        channels_seen = set()

        for i in range(header_idx + 1, len(lines)):
            cols = [c.strip().strip('"') for c in lines[i].split(",")]
            if len(cols) < 2:
                continue
            well_name = cols[well_col] if well_col >= 0 else ""
            if not well_name:
                continue

            pp = parse_position(well_name, 96)
            raw_fluor = cols[fluor_col] if fluor_col >= 0 else ""
            target_name = cols[target_col] if target_col >= 0 else "Unknown"
            content = cols[content_col] if content_col >= 0 else ""
            cq_raw = cols[cq_col] if cq_col >= 0 else ""
            cq = float(cq_raw) if cq_raw and _is_number(cq_raw) else None
            if cq is not None and not math.isfinite(cq):
                cq = None
            cq_sd_raw = cols[cq_sd_col] if cq_sd_col >= 0 else ""
            cq_sd = float(cq_sd_raw) if cq_sd_raw and _is_number(cq_sd_raw) else None
            tm_raw = cols[tm_col] if tm_col >= 0 else ""
            tm = float(tm_raw) if tm_raw and _is_number(tm_raw) else None

            sample_name = content or well_name
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

            amp_vals = []
            for ci in amp_cols:
                if ci < len(cols) and _is_number(cols[ci]):
                    amp_vals.append(float(cols[ci]))

            well = make_well(len(run["wells"]), pp["row"], pp["col"], "96")
            well["sampleId"] = sample_id
            well["targetId"] = target_id
            well["channelId"] = channel_id
            well["cq"] = cq
            well["cqSD"] = cq_sd
            well["tm"] = tm
            well["amplification"] = amp_vals
            run["wells"].append(well)

        if not run["channels"]:
            run["channels"].append(make_channel(0, "FAM", "FAM"))
        for t in run["targets"]:
            if t["channelId"] is None:
                t["channelId"] = 0
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
        headers = [c.strip().strip('"') for c in lines[0].split(delim)]

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

        targets_seen = set()
        samples_seen = set()
        channels_seen = set()

        for i in range(1, len(lines)):
            cols = [c.strip().strip('"') for c in lines[i].split(delim)]
            if len(cols) < 2:
                continue
            well_name = cols[well_col] if well_col >= 0 else cols[0]
            if not well_name:
                continue

            pp = parse_position(well_name, 96)
            sample_name = cols[sample_col] if sample_col >= 0 else well_name
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
                amp = [float(v) for v in re.split(r"[;|]", cols[amp_col]) if _is_number(v)]

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


def parse_run(text, file_name=None):
    fmt = detect_format(text)
    if fmt == "rdml":
        return parse_rdml(text, file_name)
    elif fmt == "cfx_csv":
        return parse_cfx_csv(text, file_name)
    elif fmt == "template":
        return parse_template(text, file_name)
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
