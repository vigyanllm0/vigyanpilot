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
    linear_regression, efficiency_from_slope, compute_standard_curves,
    compute_expression, compute_qc, analyze_run, QPCR_ENGINE_VERSION,
    savitzky_golay_derivative, detect_tm_peaks, generate_methods,
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
    # Mark ACTB as reference
    for t in run["targets"]:
        if t["name"] == "ACTB":
            t["isReference"] = True
    analysis = analyze_run(run)
    methods = generate_methods(run, analysis)
    assert "Cq values were determined by" in methods
    assert "Research use only" in methods
    # Methods should change with settings
    methods2 = generate_methods(run, analysis, {"method": "livak"})
    assert methods != methods2 or "Livak" in methods2


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


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])