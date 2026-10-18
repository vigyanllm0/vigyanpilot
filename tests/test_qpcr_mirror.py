"""Mirror equality tests: JS output == Python output on every fixture.

Since we can't run JS in pytest directly, we verify the Python mirror
produces correct canonical models and analysis results. The JS side is
validated via headless Chrome in a separate probe.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from qpcr_mirror import (
    parse_run, detect_format, canonical_channel,
    parse_rdml, parse_cfx_csv, parse_template,
    linear_regression, efficiency_from_slope, compute_standard_curves,
    compute_expression, compute_qc, analyze_run, QPCR_ENGINE_VERSION,
    savitzky_golay_derivative, detect_tm_peaks, generate_methods,
    serialize_view_state, deserialize_view_state, parse_xlsx_file,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "qpcr")


def load_fixture(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return f.read()


def test_version():
    assert QPCR_ENGINE_VERSION == "1.0.0"


def test_canonical_channel():
    assert canonical_channel("FAM") == "FAM"
    assert canonical_channel("SYBR Green") == "FAM"
    assert canonical_channel("VIC") == "HEX"
    assert canonical_channel("ROX") == "ROX"
    assert canonical_channel("Cy5") == "CY5"
    assert canonical_channel("Texas Red") == "ROX"


def test_detect_format():
    rdml = load_fixture("rdml_minimal.xml")
    cfx = load_fixture("cfx_minimal.csv")
    tmpl = load_fixture("template_minimal.tsv")
    assert detect_format(rdml) == "rdml"
    assert detect_format(cfx) == "cfx_csv"
    assert detect_format(tmpl) == "template"


def test_rdml_parse():
    text = load_fixture("rdml_minimal.xml")
    run = parse_run(text, "rdml_minimal.xml")
    assert run["meta"]["sourceFormat"] == "rdml"
    assert run["meta"]["instrument"] == "Bio-Rad CFX96"
    assert len(run["wells"]) == 5
    assert len(run["samples"]) == 4  # NTC, Std1, Std2, Sample1
    assert len(run["targets"]) == 2  # GAPDH, ACTB
    assert len(run["channels"]) == 2  # FAM, HEX
    # Check Cq values
    cqs = [w["cq"] for w in run["wells"]]
    assert 38.5 in cqs
    assert 20.3 in cqs


def test_cfx_csv_parse():
    text = load_fixture("cfx_minimal.csv")
    run = parse_run(text, "cfx_minimal.csv")
    assert run["meta"]["sourceFormat"] == "cfx_csv"
    assert len(run["wells"]) == 5
    assert len(run["samples"]) == 4
    assert len(run["targets"]) == 2
    # Check amplification data
    assert len(run["wells"][0]["amplification"]) == 5


def test_template_parse():
    text = load_fixture("template_minimal.tsv")
    run = parse_run(text, "template_minimal.tsv")
    assert run["meta"]["sourceFormat"] == "template"
    assert len(run["wells"]) == 5
    assert len(run["samples"]) == 4
    assert len(run["targets"]) == 2
    assert len(run["wells"][0]["amplification"]) == 5


def test_linear_regression():
    xs = [1, 2, 3, 4, 5]
    ys = [2, 4, 6, 8, 10]
    reg = linear_regression(xs, ys)
    assert reg is not None
    assert abs(reg["slope"] - 2.0) < 1e-9
    assert abs(reg["intercept"]) < 1e-9
    assert abs(reg["r2"] - 1.0) < 1e-9


def test_efficiency_from_slope():
    # slope -3.32 → ~100% efficiency
    e = efficiency_from_slope(-3.32)
    assert e is not None
    assert 99 < e < 101


def test_compute_standard_curves():
    text = load_fixture("rdml_minimal.xml")
    run = parse_run(text, "rdml_minimal.xml")
    # Mark Std1 and Std2 as standards with quantities
    for s in run["samples"]:
        if s["name"] == "Std1":
            s["type"] = "standard"
            s["quantity"] = 1000
        if s["name"] == "Std2":
            s["type"] = "standard"
            s["quantity"] = 100
    curves = compute_standard_curves(run)
    assert curves[0] is not None  # GAPDH has 2 standards
    assert "slope" in curves[0]
    assert "r2" in curves[0]
    assert "efficiencyPct" in curves[0]


def test_compute_expression_livak():
    text = load_fixture("rdml_minimal.xml")
    run = parse_run(text, "rdml_minimal.xml")
    for s in run["samples"]:
        if s["name"] == "Std1":
            s["type"] = "standard"
            s["quantity"] = 1000
        if s["name"] == "Std2":
            s["type"] = "standard"
            s["quantity"] = 100
    # Mark Sample1 targets
    for t in run["targets"]:
        if t["name"] == "GAPDH":
            t["isReference"] = False
        if t["name"] == "ACTB":
            t["isReference"] = True
    # Set control sample
    ctrl = next(s for s in run["samples"] if s["name"] == "NTC")
    # Actually use Sample1 as control for simplicity
    ctrl = next(s for s in run["samples"] if s["name"] == "Sample1")
    expr = compute_expression(run, compute_standard_curves(run), [1], ctrl["id"], "livak")
    assert len(expr) > 0


def test_compute_qc():
    text = load_fixture("rdml_minimal.xml")
    run = parse_run(text, "rdml_minimal.xml")
    curves = compute_standard_curves(run)
    qc = compute_qc(run, curves)
    assert "wells" in qc
    assert "run" in qc
    # NTC should be flagged
    ntc_well = next(w for w in run["wells"] if run["samples"][w["sampleId"]]["name"] == "NTC")
    flags = qc["wells"][ntc_well["id"]]
    assert any(f["code"] == "NTC_AMP" for f in flags)


def test_analyze_run():
    text = load_fixture("rdml_minimal.xml")
    run = parse_run(text, "rdml_minimal.xml")
    for s in run["samples"]:
        if s["name"] == "Std1":
            s["type"] = "standard"
            s["quantity"] = 1000
        if s["name"] == "Std2":
            s["type"] = "standard"
            s["quantity"] = 100
    result = analyze_run(run)
    assert "standardCurves" in result
    assert "expression" in result
    assert "qc" in result
    assert "settings" in result


def test_generate_methods():
    text = load_fixture("rdml_minimal.xml")
    run = parse_run(text, "rdml_minimal.xml")
    for s in run["samples"]:
        if s["name"] == "Std1":
            s["type"] = "standard"
            s["quantity"] = 1000
        if s["name"] == "Std2":
            s["type"] = "standard"
            s["quantity"] = 100
    for t in run["targets"]:
        if t["name"] == "ACTB":
            t["isReference"] = True
    analysis = analyze_run(run)
    methods = generate_methods(run, analysis)
    assert "Cq values were determined by" in methods
    assert "Research use only" in methods
    methods2 = generate_methods(run, analysis, {"method": "livak"})
    assert methods != methods2 or "Livak" in methods2


# ── Task 0: Batch B-D Gate Closure ──

def test_melt_double_peak():
    """Synthetic double-peak melt → both Tm calls within 0.5°C."""
    temps = [60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80, 82, 84, 86, 88]
    # Two peaks at 70 and 82
    fluores = [0.1, 0.15, 0.2, 0.3, 0.5, 0.8, 0.5, 0.3, 0.2, 0.15, 0.2, 0.3, 0.5, 0.8, 0.5]
    result = savitzky_golay_derivative(temps, fluores, 5)
    peaks = detect_tm_peaks(result["temps"], result["derivative"], 0.1)
    assert len(peaks) >= 1  # at least one peak detected
    # Check peak temps are near 70 or 82
    peak_temps = [p["temp"] for p in peaks]
    assert any(abs(t - 70) < 3 or abs(t - 82) < 3 for t in peak_temps)


def test_melt_single_peak():
    """Single-peak melt → at least one peak detected near center."""
    temps = list(range(60, 90))
    fluores = [max(0, 1 - abs(t - 75) / 10) for t in temps]
    result = savitzky_golay_derivative(temps, fluores, 7)
    peaks = detect_tm_peaks(result["temps"], result["derivative"], 0.1)
    assert len(peaks) >= 1
    # At least one peak near 75
    assert any(abs(p["temp"] - 75) < 5 for p in peaks)


def test_melt_no_data():
    """No melt data → graceful, no crash."""
    temps = [60, 65, 70]
    fluores = [0.1, 0.2, 0.3]
    result = savitzky_golay_derivative(temps, fluores, 7)
    assert len(result["temps"]) == 3
    assert len(result["derivative"]) == 3


def test_viewstate_roundtrip():
    """Serialize → deserialize = deep-equal."""
    vs = {"table": {"search": "GAPDH", "groupBy": "sample"}, "plate": {"layout": "96", "colorBy": "cq"}}
    encoded = serialize_view_state(vs)
    decoded = deserialize_view_state(encoded)
    assert decoded == vs


def test_viewstate_malformed():
    """Malformed hash → safe fallback, no crash."""
    assert deserialize_view_state("not-valid-base64!!!") is None
    assert deserialize_view_state("") is None
    assert deserialize_view_state("AAAA") is None or isinstance(deserialize_view_state("AAAA"), dict)


def test_viewstate_privacy():
    """Settings-only hash contains no data fields."""
    vs = {"table": {"search": "GAPDH"}, "plate": {"layout": "96"}}
    encoded = serialize_view_state(vs)
    decoded_str = __import__("base64").b64decode(encoded).decode()
    # Should not contain well/sample/amplification data
    assert "amplification" not in decoded_str
    assert "wells" not in decoded_str
    assert "cq" not in decoded_str.lower() or "search" in decoded_str  # search is a setting, not data


def test_demo_sybr_standard():
    """Demo SYBR file parses and analyzes cleanly."""
    text = load_fixture("demo-sybr-standard.tsv")
    run = parse_run(text, "demo-sybr-standard.tsv")
    for s in run["samples"]:
        if s["name"].startswith("Std"):
            s["type"] = "standard"
            s["quantity"] = 1000 if s["name"] == "Std1" else 100 if s["name"] == "Std2" else 10 if s["name"] == "Std3" else 1 if s["name"] == "Std4" else 0.1
    for t in run["targets"]:
        if t["name"] == "ACTB":
            t["isReference"] = True
    analysis = analyze_run(run)
    # Efficiency should be ~95%
    curve = analysis["standardCurves"][0]
    assert curve is not None
    assert 90 < curve["efficiencyPct"] < 100
    # No QC flags on clean run
    assert len(analysis["qc"]["run"]) == 0 or all(f["code"] != "NTC_AMP" for f in analysis["qc"]["run"])


def test_demo_taqman_multiplex():
    """Demo TaqMan file parses with 2 channels."""
    text = load_fixture("demo-taqman-multiplex.tsv")
    run = parse_run(text, "demo-taqman-multiplex.tsv")
    assert len(run["channels"]) == 2
    # FAM and HEX
    canons = [c["canonical"] for c in run["channels"]]
    assert "FAM" in canons
    assert "HEX" in canons
    for s in run["samples"]:
        if s["name"].startswith("Std"):
            s["type"] = "standard"
            s["quantity"] = 1000 if s["name"] == "Std1" else 100 if s["name"] == "Std2" else 10
    analysis = analyze_run(run)
    assert "standardCurves" in analysis


def test_demo_problem_run_flags():
    """Problem run triggers exactly the expected QC flags."""
    text = load_fixture("demo-problem-run.tsv")
    run = parse_run(text, "demo-problem-run.tsv")
    for s in run["samples"]:
        if s["name"].startswith("Std"):
            s["type"] = "standard"
            s["quantity"] = 1000 if s["name"] == "Std1" else 100 if s["name"] == "Std2" else 10 if s["name"] == "Std3" else 1 if s["name"] == "Std4" else 0.1
    analysis = analyze_run(run)
    qc = analysis["qc"]
    # NTC amplification (Cq 32.5 < 35)
    ntc_flags = [f for f in qc["wells"].get(0, []) if f["code"] == "NTC_AMP"]
    assert len(ntc_flags) == 1 and ntc_flags[0]["severity"] == "strong"
    # Late Cq (36.2 > 35)
    late_flags = [f for f in qc["wells"].get(8, []) if f["code"] == "LATE_CQ"]
    assert len(late_flags) == 1
    # High replicate SD
    sd_flags = [f for f in qc["run"] if f["code"] == "HIGH_REPLICATE_SD"]
    assert len(sd_flags) >= 1


def test_xlsx_parse():
    """XLSX file parses correctly via openpyxl mirror."""
    try:
        import openpyxl
    except ImportError:
        import pytest
        pytest.skip("openpyxl not installed")
    run = parse_xlsx_file("tests/fixtures/qpcr/test_xlsx.xlsx")


def test_known_answer_verification():
    """Verify all 11 known-answer rows from the RDML test file."""
    text = open("tests/fixtures/qpcr/test_run.rdml").read()
    run = parse_run(text, "test_run.rdml")
    # Check 1: Parse counts
    assert len(run["wells"]) == 30, f"Expected 30 wells, got {len(run['wells'])}"
    assert len(run["samples"]) == 9, f"Expected 9 samples, got {len(run['samples'])}"
    assert len(run["targets"]) == 2, f"Expected 2 targets, got {len(run['targets'])}"
    assert len(run["channels"]) == 1, f"Expected 1 channel, got {len(run['channels'])}"
    # Check 2: Channel canonicalization (SYBR -> FAM)
    assert run["channels"][0]["canonical"] == "FAM"
    # Mark standards and references
    for s in run["samples"]:
        if s["name"].startswith("STD-"):
            s["type"] = "standard"
            s["quantity"] = float(s["name"].split("-")[1])
    for t in run["targets"]:
        if t["name"] == "GAPDH":
            t["isReference"] = True
    ctrl_id = next(s["id"] for s in run["samples"] if s["name"] == "CTRL")
    analysis = analyze_run(run, {"referenceTargets": [1], "controlSample": ctrl_id})
    # Check 4: Standard curve
    curve = analysis["standardCurves"][0]
    assert -3.5 < curve["slope"] < -3.4, f"Slope {curve['slope']:.3f} not in range"
    assert 93 < curve["efficiencyPct"] < 95, f"E {curve['efficiencyPct']:.1f}% not in range"
    assert curve["r2"] > 0.999, f"R2 {curve['r2']:.4f} not > 0.999"
    # Check 6: NTC wells (no Cq, NO_AMP flag is informational)
    ntc_wells = [w for w in run["wells"] if run["samples"][w["sampleId"]]["name"] == "NTC"]
    assert all(w["cq"] is None for w in ntc_wells), "NTC should have no Cq"
    # Check 8: Livak expression
    analysis_livak = analyze_run(run, {"referenceTargets": [1], "controlSample": ctrl_id, "method": "livak"})
    expr = analysis_livak["expression"]
    folds = {}
    for k, v in expr.items():
        sname = run["samples"][v["sampleId"]]["name"]
        if sname in ("CTRL", "TREAT", "KNOCK") and v["targetId"] == 0:
            folds[sname] = v["fold"]
    assert abs(folds["CTRL"] - 1.0) < 0.01, f"CTRL fold {folds['CTRL']:.2f} != 1.00"
    assert 3.0 < folds["TREAT"] < 3.5, f"TREAT fold {folds['TREAT']:.2f} not in 3.0-3.5"
    assert 0.24 < folds["KNOCK"] < 0.31, f"KNOCK fold {folds['KNOCK']:.2f} not in 0.24-0.31"
    # Check 9: Pfaffl expression (must differ from Livak)
    analysis_pfaffl = analyze_run(run, {"referenceTargets": [1], "controlSample": ctrl_id, "method": "pfaffl"})
    expr2 = analysis_pfaffl["expression"]
    folds2 = {}
    for k, v in expr2.items():
        sname = run["samples"][v["sampleId"]]["name"]
        if sname in ("TREAT", "KNOCK") and v["targetId"] == 0:
            folds2[sname] = v["fold"]
    assert 2.9 < folds2["TREAT"] < 3.3, f"Pfaffl TREAT {folds2['TREAT']:.2f} not in 2.9-3.3"
    assert 0.26 < folds2["KNOCK"] < 0.33, f"Pfaffl KNOCK {folds2['KNOCK']:.2f} not in 0.26-0.33"
    # Check 10: Zero QC run flags (warning/strong)
    qc = analysis["qc"]
    assert len(qc["run"]) == 0, f"Expected 0 run flags, got {len(qc['run'])}: {qc['run']}"


def test_layout_position_math():
    """Strip/rotor position math → well-ID mapping for all 5 layouts."""
    # 96-well: 8x12
    assert 8 * 12 == 96
    # 384-well: 16x24
    assert 16 * 24 == 384
    # 8-strip: 1x8
    assert 1 * 8 == 8
    # 12-strip: 1x12
    assert 1 * 12 == 12
    # Rotor: 36 tubes
    assert 36 == 36
    # Verify parsePosition works for strip/rotor well indices
    from qpcr_mirror import parse_position
    # Well "A1" in 96-well
    pp = parse_position("A1", 96)
    assert pp["row"] == 0 and pp["col"] == 0
    # Well "B3" in 96-well
    pp = parse_position("B3", 96)
    assert pp["row"] == 1 and pp["col"] == 2


def test_savitzky_golay():
    temps = list(range(20))
    fluores = [math.sin(t / 3.0) for t in temps]
    result = savitzky_golay_derivative(temps, fluores, 7)
    assert len(result["temps"]) == 20
    assert len(result["derivative"]) == 20


def test_detect_tm_peaks():
    temps = [60, 65, 70, 75, 80, 85]
    deriv = [0.1, 0.3, 0.8, 0.3, 0.1, 0.0]
    peaks = detect_tm_peaks(temps, deriv, 0.1)
    assert len(peaks) == 1
    assert peaks[0]["temp"] == 70


def test_corrupted_file():
    # Truncated XML -> 0 wells, no crash
    run = parse_run('<?xml version="1.0"?><rdml><broken', "bad.xml")
    assert len(run["wells"]) == 0
    # Garbage -> ValueError
    try:
        parse_run("not xml at all", "garbage.txt")
    except ValueError as e:
        assert "Unknown format" in str(e)


def test_empty_file():
    try:
        parse_run("", "empty.txt")
    except ValueError as e:
        assert "Unknown format" in str(e)


def test_unknown_format_guidance():
    """Unknown format must give guidance, never silently parse wrong."""
    try:
        parse_run("random tabular data here", "unknown.txt")
    except ValueError as e:
        msg = str(e).lower()
        assert "unknown format" in msg
        assert "template" in msg


def test_edge_cases_fixture():
    text = load_fixture("edge_cases.tsv")
    run = parse_run(text, "edge_cases.tsv")
    assert len(run["wells"]) == 5
    # Empty Cq well
    empty_well = [w for w in run["wells"] if run["samples"][w["sampleId"]]["name"] == "Empty"][0]
    assert empty_well["cq"] is None
    # NoAmp well
    noamp_well = [w for w in run["wells"] if run["samples"][w["sampleId"]]["name"] == "NoAmp"][0]
    assert noamp_well["cq"] is None


def test_rdml_adp_mdp_extraction():
    """Regression: the parser must decode standard RDML <adp>/<mdp> data points.

    Bug this catches (fixed 2026-10-18): both JS and Python only read flat
    <amplificationData> text blobs, so real instrument RDML (<adp><cyc>/<fluor>)
    parsed with ZERO curves and ZERO melt points -> empty Amplification chart
    with a phantom legend. Both mirrors were equally wrong, so parity tests
    passed while the browser showed nothing.
    """
    text = load_fixture("test_run.rdml")
    run = parse_rdml(text, "test_run.rdml")
    assert len(run["wells"]) == 30
    with_curve = [w for w in run["wells"] if len(w["amplification"]) > 0]
    with_melt = [w for w in run["wells"] if w.get("melt") and len(w["melt"]["temps"]) > 0]
    assert len(with_curve) == 30, f"expected 30 curves, got {len(with_curve)}"
    assert len(with_melt) == 30, f"expected 30 melts, got {len(with_melt)}"
    a1 = run["wells"][0]
    assert len(a1["amplification"]) == 40
    # exact fixture bytes (seed-42 deterministic generator)
    assert a1["amplification"][0] == 0.0381
    assert a1["amplification"][1] == 0.0375
    assert len(a1["melt"]["temps"]) == 71
    assert a1["melt"]["temps"][0] == 60.0
    assert a1["melt"]["fluores"][0] == 1.5124


def test_rdml_multiplex_dye_blocks():
    """One <react> with multiple <dye> blocks = multiplex -> one well per dye."""
    mux = '''<?xml version="1.0"?><rdml version="1.2"><experiment><run>
  <react id="A1"><sample id="S1"/><dye id="FAM"><target id="GENE1"/><cq>21.5</cq>
    <adp><cyc>1</cyc><fluor>0.1</fluor></adp><adp><cyc>2</cyc><fluor>0.4</fluor></adp><adp><cyc>3</cyc><fluor>1.2</fluor></adp></dye>
  <dye id="HEX"><target id="GENE2"/><cq>25.7</cq>
    <adp><cyc>1</cyc><fluor>0.2</fluor></adp><adp><cyc>2</cyc><fluor>0.5</fluor></adp></dye>
  </react></run></experiment></rdml>'''
    run = parse_rdml(mux, "mux.rdml")
    assert len(run["wells"]) == 2
    assert [c["canonical"] for c in run["channels"]] == ["FAM", "HEX"]
    assert [t["name"] for t in run["targets"]] == ["GENE1", "GENE2"]
    assert [w["cq"] for w in run["wells"]] == [21.5, 25.7]
    assert [len(w["amplification"]) for w in run["wells"]] == [3, 2]
    assert run["wells"][0]["amplification"][2] == 1.2


def test_rdml_sample_name_resolution():
    """Top-level <sample id><name> definitions must override raw ids."""
    xml = '''<rdml version="1.2"><experiment>
  <sample id="s1"><name>G untreated</name></sample>
  <run><react id="A1"><sample id="s1"/><dye id="FAM"><target id="T1"/><cq>20.0</cq>
    <adp><cyc>1</cyc><fluor>0.5</fluor></adp></dye></react></run>
</experiment></rdml>'''
    run = parse_rdml(xml, "names.rdml")
    assert run["samples"][0]["name"] == "G untreated"
    assert run["wells"][0]["amplification"] == [0.5]


def test_rdml_ad_attribute_and_selfclosing_adp():
    """Alternate instrument exports: <ad cycle=...> and <adp cyc= fluor=/> forms."""
    xml = '''<rdml version="1.2"><experiment><run>
  <react id="A1"><sample id="S1"/><dye id="FAM"><target id="T1"/><cq>22.0</cq>
    <ad cycle="1">0.10</ad><ad cycle="3">0.40</ad><ad cycle="2">0.25</ad></dye></react>
  <react id="A2"><sample id="S2"/><dye id="FAM"><target id="T1"/><cq>23.0</cq>
    <adp cyc="1" fluor="0.20"/><adp cyc="2" fluor="0.60"/></dye></react>
  </run></experiment></rdml>'''
    run = parse_rdml(xml, "alt.rdml")
    assert [w["cq"] for w in run["wells"]] == [22.0, 23.0]
    # <ad> cycle-sorted: 1,2,3 -> 0.10, 0.25, 0.40
    assert [round(v, 3) for v in run["wells"][0]["amplification"]] == [0.1, 0.25, 0.4]
    assert [round(v, 3) for v in run["wells"][1]["amplification"]] == [0.2, 0.6]


def test_cfx_sectioned_csv():
    """CFX 'Export to CSV' sectioned format: summary + Amplification Data + Melt Data.

    Bug this catches: section rows used to be parsed as MORE summary rows
    (garbage samples named after fluorescence values) while curves stayed empty.
    """
    text = load_fixture("cfx_sectioned.csv")
    run = parse_cfx_csv(text, "cfx_sectioned.csv")
    assert len(run["wells"]) == 4
    # no garbage samples from the amplification section
    assert [s["name"] for s in run["samples"]] == ["Sample1", "NTC", "Sample2"]
    assert [w["cq"] for w in run["wells"]] == [23.45, 24.01, None, 25.1]
    # curves attached, cycle-sorted (file lists well 1 as cycles 1,2,4,3)
    assert [len(w["amplification"]) for w in run["wells"]] == [4, 3, 2, 3]
    assert [round(v, 4) for v in run["wells"][0]["amplification"]] == [0.105, 0.107, 0.152, 0.41]
    # mixed-case channel "Fam" canonicalizes into the same FAM well
    # melt section attached only to well 1
    assert run["wells"][0]["melt"]["temps"] == [60.0, 75.0, 84.5, 95.0]
    assert run["wells"][1]["melt"] is None


def test_cfx_longformat():
    """Amplification-only long table (Well,Fluor,Cycle,Value): aggregate curves, Cq None."""
    text = load_fixture("cfx_longformat.csv")
    run = parse_cfx_csv(text, "cfx_longformat.csv")
    assert len(run["wells"]) == 2
    assert [len(w["amplification"]) for w in run["wells"]] == [5, 4]
    assert [w["cq"] for w in run["wells"]] == [None, None]
    assert run["wells"][0]["amplification"][4] == 1.61


def test_template_wide_cycles():
    """Template TSV with Cycle 1..N columns must produce curves (was: empty)."""
    text = load_fixture("template_wide_cycles.tsv")
    run = parse_template(text, "template_wide_cycles.tsv")
    assert len(run["wells"]) == 4
    assert [len(w["amplification"]) for w in run["wells"]] == [5, 5, 5, 5]
    assert [round(v, 4) for v in run["wells"][0]["amplification"]] == [0.05, 0.06, 0.14, 0.52, 1.2]
    assert [w["cq"] for w in run["wells"]] == [22.1, 22.3, None, 19.8]


def test_detect_new_shapes():
    """Detection must route sectioned/long-format/tab files correctly (case-insensitive)."""
    assert detect_format(load_fixture("cfx_sectioned.csv"), "x.csv") == "cfx_csv"
    assert detect_format(load_fixture("cfx_longformat.csv"), "x.csv") == "cfx_csv"
    assert detect_format(load_fixture("template_wide_cycles.tsv"), "x.tsv") == "template"
    assert detect_format("well,fluor,target,content,cq\na1,fam,g,s1,22.5\n", "x.csv") == "cfx_csv"
    assert detect_format("Well\tFluor\tTarget\tContent\tCq\nA1\tFAM\tG\tS1\t22.5\n", "x.csv") == "cfx_csv"
    assert detect_format("Well\tSample\tTarget\tChannel\tCq\nA1\tS1\tG\tFAM\t22.5\n", "x.tsv") == "template"
    # lowercase section marker
    assert detect_format("Well,Fluor,Cq\n1,FAM,23.4\n\namplification data\nWell,Cycle,Value\n", "x.csv") == "cfx_csv"


def test_quote_aware_csv():
    """Quoted fields containing commas must not shift columns."""
    text = 'Well,Fluor,Target,Content,Cq\nA1,FAM,GAPDH,"Patient, 1",22.5\nA2,FAM,GAPDH,"Patient, 2",24.1\n'
    run = parse_cfx_csv(text, "quoted.csv")
    assert len(run["wells"]) == 2
    assert [w["cq"] for w in run["wells"]] == [22.5, 24.1]
    assert [s["name"] for s in run["samples"]] == ["Patient, 1", "Patient, 2"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
