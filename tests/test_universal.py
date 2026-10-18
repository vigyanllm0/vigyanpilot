"""Universal Format Engine tests — unit + node ESM parity.

QPCR_UNIVERSAL_FORMAT_SUPPORT_TASKS.md. The Python mirror
(tests/universal_mirror.py) and the browser module
(frontend/qpcr/qpcr-universal.js) must produce identical canonical runs on
the shared fixture corpus — parity runs the JS side in a node subprocess
(tests/qpcr_universal_node.mjs) and deep-compares with float tolerance
(RK/Float32 truncation ≈ 3e-6 on curve values).
"""
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import universal_mirror as um  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "qpcr")
NODE_HARNESS = os.path.join(os.path.dirname(__file__), "qpcr_universal_node.mjs")


def _load_make_fixtures():
    spec = importlib.util.spec_from_file_location(
        "make_fixtures", os.path.join(REPO, "scripts", "make_fixtures.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mf = _load_make_fixtures()


def load_bytes(name):
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


# ─────────────────────────────────────────────────────────────────
# 1. Sniffing (magic bytes, never the extension)
# ─────────────────────────────────────────────────────────────────
def test_sniff_containers():
    assert um.sniff(b"PK\x03\x04rest") == "zip"
    assert um.sniff(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1rest") == "ole"
    assert um.sniff(b"\x1f\x8b\x08rest") == "gzip"
    assert um.sniff(b"Well,Cq\nA1,20.5") == "text"
    assert um.sniff(bytes([0x00, 0x41, 0x00, 0x31, 0x00, 0x2C, 0x00, 0x32])) == "text"  # UTF-16LE
    assert um.sniff(bytes([0x00, 0x01, 0x02, 0xFF, 0xFE, 0x00, 0x01, 0x02])) == "binary"
    assert um.sniff(b"") == "text"


def test_sniff_never_uses_extension():
    # Content is ZIP even though the name says .csv — sniff must say zip.
    assert um.sniff(load_bytes("unknown_wide.xlsx")) == "zip"
    assert um.sniff(load_bytes("demo.xls")) == "ole"
    assert um.sniff(load_bytes("utf16.tsv")) == "text"


def test_ext_of():
    assert um.ext_of("run.QBD") == "qbd"
    assert um.ext_of("a/b/c/data.CSV") == "csv"
    assert um.ext_of("noext") == ""


# ─────────────────────────────────────────────────────────────────
# 2. Decoding
# ─────────────────────────────────────────────────────────────────
def test_decode_bom_variants():
    assert um.decode_text(b"\xef\xbb\xbfWell,Cq") == "Well,Cq"
    body = "Well,Sample,Target,Cq\nA1,S1,GAPDH,20.50\nA2,S2,GAPDH,24.10\nB1,S1,ACTB,22.30\n"
    utf16le = body.encode("utf-16")  # BOM + LE
    assert um.decode_text(utf16le) == body
    raw = body.encode("utf-16le")
    assert um.decode_text(b"\xff\xfe" + raw) == body
    assert um.decode_text(raw) == body  # no BOM → NUL parity (>40 NULs threshold)
    be = body.encode("utf-16be")
    assert um.decode_text(b"\xfe\xff" + be) == body


def test_decode_utf16_fixture():
    text = um.decode_text(load_bytes("utf16.tsv"))
    assert "Well" in text and "A1" in text
    assert "\x00" not in text


def test_num_and_s():
    assert um._num("20.50") == 20.5
    assert um._num("") is None
    assert um._num("abc") is None
    assert um._num("1e3") == 1000.0
    assert um._num(None) is None
    assert um._s(1.0) == "1"
    assert um._s(" A1 ") == "A1"
    assert um._s(None) == ""


# ─────────────────────────────────────────────────────────────────
# 3. Delimiter detection + quote-aware split
# ─────────────────────────────────────────────────────────────────
def test_detect_delimiter():
    assert um.detect_delimiter("A,B,C\n1,2,3\n4,5,6") == ","
    assert um.detect_delimiter("A\tB\tC\n1\t2\t3\n4\t5\t6") == "\t"
    assert um.detect_delimiter("A;B;C\n1;2;3\n4;5;6") == ";"
    assert um.detect_delimiter("A|B|C\n1|2|3\n4|5|6") == "|"


def test_split_rows_quotes_and_blank_lines():
    rows = um.split_rows('Well,Sample\nA1,"Smith, J"\n\nB1,S2\n', ",")
    assert rows == [["Well", "Sample"], ["A1", "Smith, J"], ["B1", "S2"]]


# ─────────────────────────────────────────────────────────────────
# 4. Column aliases + header runs + sections
# ─────────────────────────────────────────────────────────────────
def test_column_aliases_vocab():
    assert len(um.COLUMN_ALIASES) >= 80
    kinds = um.classify_header(["Well Position", "Specimen Name", "Assay", "Reporter", "Ct", "Ct SD", "Tm"])
    assert kinds == {0: "well", 1: "sample", 2: "target", 3: "dye", 4: "cq", 5: "cqsd", 6: "tm"}


def test_column_aliases_local_spellings():
    # Vendor-local spellings: Rotor-Gene style headers still classify.
    kinds = um.classify_header(["Location", "Specimen", "Assay", "Reporter", "Ct", "Signal"])
    assert kinds == {0: "well", 1: "sample", 2: "target", 3: "dye", 4: "cq", 5: "value"}


def test_norm_key():
    assert um.norm_key("Cq  Mean ") == "cq mean"
    assert um.norm_key("ΔRn") == "rn"  # non-alnum collapsed + stripped
    assert um.norm_key("WELL-POSITION") == "well position"


def test_detect_header_runs_bare_numeric():
    head = ["Well", "Sample"] + [str(i) for i in range(1, 41)]
    runs = um.detect_header_runs(head)
    assert [n for _, n in runs["cycle"]] == list(range(1, 41))
    assert runs["melt"] == []


def test_detect_header_runs_labeled_and_melt():
    head = ["Well", "Sample"] + [f"Cycle {i}" for i in range(1, 41)]
    runs = um.detect_header_runs(head)
    assert [n for _, n in runs["cycle"]] == list(range(1, 41))
    mhead = ["Well", "Sample"] + [f"M{t:.2f}" for t in [60.0 + 0.5 * i for i in range(30)]]
    mruns = um.detect_header_runs(mhead)
    assert len(mruns["melt"]) == 30
    assert mruns["melt"][0][1] == 60.0


def test_detect_header_runs_needs_five():
    runs = um.detect_header_runs(["Well", "1", "2", "3", "4"])
    assert runs["cycle"] == []  # 4 columns is below the qualification bar


def test_split_sections_banner_rows():
    rows = [["Run Info"], ["Instrument", "X"], ["Data"], ["Well", "Cq"], ["A1", "20"]]
    secs = um.split_sections(rows)
    assert [s["title"] for s in secs] == ["Run Info", "Data"]
    assert secs[0]["rows"] == [["Instrument", "X"]]
    assert secs[1]["rows"] == [["Well", "Cq"], ["A1", "20"]]


# ─────────────────────────────────────────────────────────────────
# 5. sameWell merge rule (replicate-safe)
# ─────────────────────────────────────────────────────────────────
def test_same_well_semantics():
    a = {"pos": "A1", "sample": "S1", "target": "GAPDH"}
    assert um.same_well(a, {"pos": "a1"})
    assert not um.same_well(a, {"pos": "A2"})
    # no pos: sample+target identity
    assert um.same_well({"sample": "S1", "target": "GAPDH"}, {"sample": "s1", "target": "gapdh"})
    assert not um.same_well({"sample": "S1", "target": "GAPDH"}, {"sample": "S1", "target": "ACTB"})
    # unknown target on one side matches (target-agnostic)
    assert um.same_well({"sample": "S1", "target": "GAPDH"}, {"sample": "S1"})
    # different samples never merge
    assert not um.same_well({"sample": "S1"}, {"sample": "S2"})


# ─────────────────────────────────────────────────────────────────
# 6. RK codec — bidirectional against the fixture writer
# ─────────────────────────────────────────────────────────────────
def test_rk_bidirectional():
    for v in [0.0, 1.0, -1.0, 25.5, -3.7, 1234, -1234, 0.05, -0.05, 999, -999,
              2.0 ** 20, -(2.0 ** 20), 0.999, 1e-3, 40.0]:
        enc = mf.rk_encode(v)
        dec = um.rk_decode(enc)
        assert isinstance(dec, float)
        assert math.isclose(dec, v, rel_tol=2e-3, abs_tol=1e-9) or (
            # integer path is exact; the ÷100 path rounds to 2 decimals
            abs(v - round(v, 2)) < 1e-9 and math.isclose(dec, round(v, 2), abs_tol=1e-9)
        ), f"rk round-trip failed for {v}: {enc:#x} -> {dec}"


def test_rk_known_values():
    # Bit-level conformance with the BIFF8 spec examples.
    assert um.rk_decode(0x00000002) == 0.0        # int 0
    assert um.rk_decode(0x00000003) == 0.0        # int 0 ÷100
    assert um.rk_decode((12 << 2) | 0b10) == 12.0
    assert um.rk_decode((-4 << 2) | 0b10 | 1) == -0.04  # -4 ÷100
    # IEEE path: high-32 bits of the double 2.5 = 0x4004000000000000
    assert um.rk_decode(0x40040000) == 2.5


# ─────────────────────────────────────────────────────────────────
# 7. OLE2/CFB + BIFF8 on the real fixture
# ─────────────────────────────────────────────────────────────────
def test_read_cfb_finds_workbook():
    streams = um.read_cfb(load_bytes("demo.xls"))
    assert "Workbook" in streams
    assert len(streams["Workbook"]) > 0


def test_read_biff8_grid():
    streams = um.read_cfb(load_bytes("demo.xls"))
    sheets = um.read_biff8(streams["Workbook"])
    assert len(sheets) == 1
    grid = sheets[0]["grid"]
    header = [um._s(c) for c in grid[0]]
    assert header[:2] == ["Pos", "Specimen"]
    # FORMULA-cached numeric Cq must come through as a float
    cq_vals = [c for row in grid[1:] for c in row if isinstance(c, float) and 20 < c < 30]
    assert any(math.isclose(c, 24.1, abs_tol=1e-9) for c in cq_vals)


def test_read_xlsx_grids_fixture():
    u8 = load_bytes("unknown_wide.xlsx")
    grids = um.read_xlsx_grids(u8)
    assert grids[0]["name"] == "sheet1.xml"
    header = [um._s(c) for c in grids[0]["grid"][0]]
    assert header[0] in ("Pos", "Well")
    assert len(grids[0]["grid"]) >= 5


# ─────────────────────────────────────────────────────────────────
# 8. Reasoner units — evidence, merge, confidence, cq-only
# ─────────────────────────────────────────────────────────────────
# NB: "Chamber"-style headers keep these out of the CFX fast path
# (detect_format routes Well+Target tables to parse_cfx_csv).
MERGE_CSV = (
    "Chamber,Specimen,Assay,Reporter,Cycle 1,Cycle 2,Cycle 3,Cycle 4,Cycle 5\n"
    "A1,S1,GAPDH,FAM,0.05,0.08,0.15,0.35,0.80\n"
    "Run Info\n"
    "Instrument,Rotor-Gene Q\n"
    "Cq Table\n"
    "Position,Specimen,Assay,Reporter,Cq\n"
    "A1,S1,GAPDH,FAM,23.4\n"
)

MELT_LONG_CSV = (
    "Chamber,Specimen,Assay,Reporter,Temperature,Value\n"
    "A1,S1,GAPDH,FAM,65.0,0.10\n"
    "A1,S1,GAPDH,FAM,66.0,0.25\n"
    "A1,S1,GAPDH,FAM,67.0,0.60\n"
    "B1,S2,GAPDH,FAM,65.0,0.05\n"
)


def test_reasoner_cross_section_merge():
    run = um.parse_universal_text(MERGE_CSV, "merge.csv")
    assert len(run["wells"]) == 1
    w = run["wells"][0]
    assert w["cq"] == 23.4
    assert list(w["amplification"]) == [0.05, 0.08, 0.15, 0.35, 0.80]
    assert run["meta"]["instrument"] == "Rotor-Gene Q"
    ev = run["detection"]["evidence"]
    assert any("Cross-section merge: Cq table attached" in e for e in ev)
    assert any("Instrument identity from file: Rotor-Gene Q" in e for e in ev)
    # confidence: structured cycles .25 + pos .2 + cq .2 + cycles .15 + samples .1 + targets .05
    assert run["detection"]["confidence"] == 0.95


def test_reasoner_melt_long_groups_by_well():
    run = um.parse_universal_text(MELT_LONG_CSV, "melt.csv")
    assert len(run["wells"]) == 2
    a1 = run["wells"][0]
    assert a1["melt"]["temps"] == [65.0, 66.0, 67.0]
    assert a1["melt"]["fluores"] == [0.10, 0.25, 0.60]
    assert run["cqOnly"] is True
    ev = run["detection"]["evidence"]
    assert any("Cq-only export" in e for e in ev)


def test_reasoner_cq_only_confidence():
    run = um.parse_universal_text("Position,Sample,Cq\nA1,S1,20.5\nA2,S2,24.1\n", "cq.csv")
    assert run["cqOnly"] is True
    # pos .2 + cq .2 + samples .1 + default "Unknown" target .05 (no target col)
    assert run["detection"]["confidence"] == 0.55
    assert "Per-cycle fluorescence present" not in run["detection"]["evidence"]


def test_reasoner_posless_fallback_positions():
    run = um.parse_universal_text("Sample,Target,Cq\nS1,GAPDH,20.5\nS2,ACTB,22.9\n", "posless.csv")
    assert [w["position"] for w in run["wells"]] == [0, 1]
    ev = run["detection"]["evidence"]
    assert not any("A1-style" in e for e in ev)


def test_reasoner_returns_none_on_garbage():
    assert um.reason_rows([["Foo", "Bar"], ["x", "y"]], "g.csv") is None


def test_mark_cq_only():
    from qpcr_mirror import make_run, make_well
    run = make_run({})
    run["wells"].append(make_well(0, 0, 0, "96"))
    um.mark_cq_only(run)
    assert run["cqOnly"] is True
    run["wells"][0]["amplification"] = [0.1, 0.2]
    um.mark_cq_only(run)
    assert run["cqOnly"] is False
    empty = make_run({})
    um.mark_cq_only(empty)
    assert empty["cqOnly"] is False


# ─────────────────────────────────────────────────────────────────
# 9. Fast paths + doctor + rotor guided card
# ─────────────────────────────────────────────────────────────────
def test_fast_path_rdml():
    run = um.parse_universal_text(load_bytes("test_run.rdml").decode("utf-8"), "test_run.rdml")
    assert run["detection"]["format"] == "rdml"
    assert run["detection"]["confidence"] == 0.98
    assert run["detection"]["evidence"] == ["RDML XML document (<rdml> root)"]


def test_fast_path_cfx_and_template():
    run = um.parse_universal_text(load_bytes("cfx_sectioned.csv").decode(), "cfx_sectioned.csv")
    assert run["detection"]["format"] == "cfx_csv"
    run2 = um.parse_universal_text(load_bytes("template_minimal.tsv").decode(), "template_minimal.tsv")
    assert run2["detection"]["format"] == "template"


def test_doctor_text_findings():
    doc = um.diagnose(b"garbage without table", "garbage without table", "x.csv")
    assert doc["title"].startswith("No recognizable data table")
    assert any("Detected delimiter" in f for f in doc["findings"])
    assert any("Supported header vocabulary" in g for g in doc["guidance"])
    assert doc["supported"] == um.SUPPORTED_FORMATS


def test_rotor_guided_card():
    card = um.rotor_guided("run.qbd", "proprietary binary payload")
    assert "Rotor-Gene-family" in card["title"]
    assert any("OnePCR" in f or "RapiCycler" in f for f in card["findings"])
    assert any("Export" in g for g in card["guidance"])


def test_gzip_doctor():
    with pytest.raises(um.FormatError) as ei:
        um.parse_file_universal("x.csv", b"\x1f\x8b\x08\x00" + bytes(32))
    assert "gzip" in ei.value.doctor["title"].lower() or any(
        "gzip" in f.lower() for f in ei.value.doctor["findings"])


def test_text_despite_extension_evidence():
    # Evidence line is added by the file-level entry (text container + extension match).
    run = um.parse_file_universal("export.qbd",
                                  b"Chamber,Specimen,Assay,Cq\nA1,S1,GAPDH,20.5\n")
    assert any("parsed by content, not by name" in e for e in run["detection"]["evidence"])


# ─────────────────────────────────────────────────────────────────
# 10b. Vendor containers: EDS bundle + gzip-unwrap (spec T8/T9)
# ─────────────────────────────────────────────────────────────────
def test_eds_bundle_fixture():
    run = um.parse_file_universal("eds_demo.eds", load_bytes("eds_demo.eds"))
    assert run["detection"]["format"] == "eds"
    assert run["detection"]["confidence"] == 0.97
    assert len(run["wells"]) == 6 and len(run["samples"]) == 3
    assert len(run["targets"]) == 2 and len(run["channels"]) == 2
    assert [w["cq"] for w in run["wells"]] == [None, None, 18.25, 19.5, 22.75, 24.125]
    assert all(len(w["amplification"]) == 5 for w in run["wells"])
    assert run["wells"][0]["amplification"] == [0.5, 1.0, 1.5, 2.0, 2.5]
    # ABI column-major: well 1 = A1, well 12 = D2, well 26 = B4
    assert [(w["row"], w["col"]) for w in run["wells"]] == [
        (0, 0), (0, 0), (3, 1), (3, 1), (1, 3), (1, 3)]
    assert [s["type"] for s in run["samples"]] == ["ntc", "standard", "unknown"]
    # plate_setup.xml reporters; VIC canonicalizes to HEX (engine rule)
    assert [c["canonical"] for c in run["channels"]] == ["FAM", "HEX"]
    assert run["meta"]["instrument"] == "QuantStudio 5 - 96-Well 0.2-mL Block"
    ev = run["detection"]["evidence"]
    assert ev[0] == ("Applied Biosystems EDS bundle → apldbio/sds/"
                     "analysis_result.txt read natively")
    assert ev[1] == "6 result records → 6 wells, 3 samples, 2 targets, 2 channels"
    assert any("Delta Rn per cycle × 5 cycles" in e for e in ev)
    assert "Detectors: Target 1 → FAM, Target 2 → VIC" in ev
    assert "Run state: COMPLETE" in ev
    assert "Well numbering: ABI column-major (well 1 = A1, 8×12)" in ev


def test_eds_text_standalone():
    # A standalone analysis_result.txt dropped in directly (its "Well … Cq Conf"
    # header trips the engine's cq-first CFX fingerprint — must not hijack).
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(load_bytes("eds_demo.eds"))) as zf:
        text = zf.read("apldbio/sds/analysis_result.txt").decode("utf-8")
    run = um.parse_universal_text(text, "analysis_result.txt")
    assert run["detection"]["format"] == "eds"
    assert run["detection"]["confidence"] == 0.93
    assert len(run["wells"]) == 6
    assert run["detection"]["evidence"][0] == (
        "EDS analysis table (analysis_result.txt layout) → per-well read")
    # no plate_setup.xml here → channels fall back to the detector names
    assert [c["canonical"] for c in run["channels"]] == ["Target 1", "Target 2"]


def test_eds_zero_well_guard():
    header = "Well\tSample Name\tDetector\tTask\tCt\tAvg Ct\tCt SD\tDelta Ct\t" \
             "Qty\tAvg Qty\tQty SD\tAmp Status\tCq Conf\n"
    with pytest.raises(um.FormatError) as ei:
        um.parse_universal_text("Session Name\t\n" + header, "empty_export.txt")
    assert ei.value.doctor["title"] == "Header matched, but no well rows found"
    assert any("First line: Session Name" in f for f in ei.value.doctor["findings"])


def test_wrapped_qbd_content_beats_extension():
    run = um.parse_file_universal("wrapped_run.qbd", load_bytes("wrapped_run.qbd"))
    assert len(run["wells"]) == 3
    assert run.get("cqOnly") is True
    assert [w["cq"] for w in run["wells"]] == [20.5, 24.1, None]
    assert run["detection"]["evidence"][0] == (
        "vendor header + gzip stream at offset 22 → inner text table")


def test_wrapped_qbg_vendor_db_card():
    with pytest.raises(um.FormatError) as ei:
        um.parse_file_universal("wrapped_qbg.qbg", load_bytes("wrapped_qbg.qbg"))
    card = ei.value.doctor
    assert card["title"] == ("Vendor run database — schema read, "
                             "Cq values not in a table")
    assert card["findings"][0] == \
        "vendor header + gzip stream at offset 15 → decompressed to 479 bytes"
    assert any("Schema keys found: bh1600, Samples, Cycles" in f
               for f in card["findings"])
    assert "Run timestamps: 2026-01-02 03:04:05 · 2026-01-02 03:05:06" \
        in card["findings"]
    assert ("Embedded labels (4 of 4): FAM, A10, SYNTH ASSAY A, SYNTH ASSAY B"
            in card["findings"])
    assert any("would mean guessing" in g for g in card["guidance"])
    assert card["supported"] == um.SUPPORTED_FORMATS


def test_plain_gzip_text_unwrap():
    import gzip
    csv = ("Well,Sample,Target,Channel,Cq\nA1,S1,GAPDH,FAM,20.5\n"
           "A2,S2,GAPDH,FAM,24.1\nB1,NTC,GAPDH,FAM,\n")
    run = um.parse_file_universal("run.csv.gz", gzip.compress(csv.encode()))
    assert len(run["wells"]) == 3
    assert run["detection"]["evidence"][0] == "gzip container → inner text table"


def test_find_embedded_gzip():
    payload = b"\x1f\x8b\x08\x00" + bytes(16)
    assert um.find_embedded_gzip(b"HEAD" + payload, 64) == 4
    # a non-printable prefix is not a vendor banner → no unwrap
    assert um.find_embedded_gzip(b"\x00\x01\x02\x03" + payload, 64) == -1
    assert um.find_embedded_gzip(b"short", 64) == -1


def test_supported_formats_lockstep():
    # The doctor's "what works here" list must exist verbatim in the JS module.
    with open(os.path.join(REPO, "frontend", "qpcr", "qpcr-universal.js"),
              encoding="utf-8") as fh:
        js = fh.read()
    for entry in um.SUPPORTED_FORMATS:
        assert entry in js, "JS module missing SUPPORTED_FORMATS entry: %s" % entry


# ─────────────────────────────────────────────────────────────────
# 10. Fixture corpus end-to-end (Python side)
# ─────────────────────────────────────────────────────────────────
def test_fixture_unknown_long():
    run = um.parse_file_universal("unknown_long.csv", load_bytes("unknown_long.csv"))
    d = run["detection"]
    assert d["format"] == "reasoner" and d["confidence"] == 0.95
    assert run["meta"]["instrument"] == "OnePCR-Emulator"
    assert len(run["wells"]) == 4
    assert run["cqOnly"] is False
    cqs = sorted(w["cq"] for w in run["wells"] if w["cq"] is not None)
    assert cqs and cqs[0] >= 18


def test_fixture_cq_only():
    run = um.parse_file_universal("cq_only.csv", load_bytes("cq_only.csv"))
    assert run["cqOnly"] is True
    assert len(run["wells"]) == 4
    assert run["wells"][2]["cq"] is None  # NTC well without Cq
    assert any(s["type"] == "ntc" for s in run["samples"])


def test_fixture_semicolon():
    run = um.parse_file_universal("semicol.csv", load_bytes("semicol.csv"))
    assert any("Detected ';' delimiter" in e for e in run["detection"]["evidence"])
    assert run["wells"][0]["tm"] is not None


def test_fixture_utf16_template():
    run = um.parse_file_universal("utf16.tsv", load_bytes("utf16.tsv"))
    assert run["detection"]["format"] == "template"
    assert run["meta"]["sourceFormat"] == "template"


def test_fixture_unknown_wide_xlsx():
    run = um.parse_file_universal("unknown_wide.xlsx", load_bytes("unknown_wide.xlsx"))
    d = run["detection"]
    assert d["format"] == "xlsx" and d["confidence"] == 0.95
    assert any("layout reasoner" in e for e in d["evidence"])
    assert any("worksheet" in e.lower() for e in d["evidence"])
    assert len(run["wells"]) == 4


def test_fixture_demo_xls():
    run = um.parse_file_universal("demo.xls", load_bytes("demo.xls"))
    d = run["detection"]
    assert d["format"] == "xls-biff8"
    assert d["evidence"][0].startswith("OLE2 compound document")
    assert len(run["wells"]) == 4
    # FORMULA-cached Cq must survive the BIFF read
    assert any(math.isclose(w["cq"], 24.1, abs_tol=1e-6) for w in run["wells"] if w["cq"] is not None)
    # RK-encoded curve values decode close to the written 4-dp values
    w0 = run["wells"][0]
    assert len(w0["amplification"]) > 0
    assert max(w0["amplification"]) <= 2.0


def test_fixture_stub_qbd_rotor_doctor():
    with pytest.raises(um.FormatError) as ei:
        um.parse_file_universal("stub.qbd", load_bytes("stub.qbd"))
    card = ei.value.doctor
    assert "Rotor-Gene-family" in card["title"]
    assert any("CSV" in g for g in card["guidance"])


def test_fixture_junk_doctor():
    with pytest.raises(um.FormatError) as ei:
        um.parse_file_universal("junk.csv", load_bytes("junk.csv"))
    card = ei.value.doctor
    assert card["findings"][0].startswith("Container (magic bytes): binary")
    assert card["supported"] == um.SUPPORTED_FORMATS


def test_xlsx_strict_template_header_path():
    # The frozen test_xlsx.xlsx has a strict Well+Sample+Target+Channel header.
    run = um.parse_file_universal("test_xlsx.xlsx", load_bytes("test_xlsx.xlsx"))
    assert run["detection"]["format"] == "xlsx"
    assert any("strict template header" in e for e in run["detection"]["evidence"])
    assert run["meta"]["sourceFormat"] == "xlsx"


def test_fixture_determinism_check():
    res = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "make_fixtures.py"), "--check"],
                         capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stdout + res.stderr


# ─────────────────────────────────────────────────────────────────
# 11. Node ESM parity (T6.2) — JS module vs Python mirror
# ─────────────────────────────────────────────────────────────────
PARITY_FIXTURES = [
    # new universal fixtures
    "unknown_long.csv", "cq_only.csv", "semicol.csv", "utf16.tsv",
    "unknown_wide.xlsx", "demo.xls", "stub.qbd", "junk.csv",
    # vendor containers (EDS bundle + gzip-wrapped tables)
    "eds_demo.eds", "wrapped_qbg.qbg", "wrapped_run.qbd",
    # frozen corpus routed through the universal entry (fast paths + doctor)
    "test_run.rdml", "rdml_minimal.xml", "cfx_sectioned.csv", "cfx_longformat.csv",
    "template_minimal.tsv", "template_wide_cycles.tsv", "test_xlsx.xlsx",
    "demo-taqman-multiplex.tsv", "demo-problem-run.tsv", "edge_cases.tsv",
]


def _norm_run(run):
    return {
        "meta": run["meta"], "channels": run["channels"], "targets": run["targets"],
        "samples": run["samples"],
        "wells": [
            {**{k: v for k, v in w.items() if k not in ("amplification", "melt")},
             "amplification": list(w.get("amplification") or []),
             "melt": ({"temps": list(w["melt"]["temps"]), "fluores": list(w["melt"]["fluores"])}
                      if w.get("melt") else None)}
            for w in run["wells"]
        ],
        "detection": run.get("detection"),
        "cqOnly": run.get("cqOnly", None),
    }


def _close(a, b, tol=1e-5):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return True
        return abs(a - b) <= tol * max(1.0, abs(a), abs(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return list(a.keys()) == list(b.keys()) and all(_close(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b))
    return a == b


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_node_parity_full_corpus():
    paths = [os.path.join(FIXTURES, n) for n in PARITY_FIXTURES]
    res = subprocess.run(["node", NODE_HARNESS, *paths],
                         capture_output=True, text=True, timeout=300,
                         cwd=os.path.dirname(FIXTURES))
    assert res.returncode == 0, res.stderr[:2000]
    lines = [json.loads(l) for l in res.stdout.strip().splitlines() if l.strip()]
    assert len(lines) == len(PARITY_FIXTURES)

    mismatches = []
    for name, nl in zip(PARITY_FIXTURES, lines):
        assert nl["file"] == name
        try:
            py_run = _norm_run(um.parse_file_universal(name, load_bytes(name)))
            py_err = None
        except um.FormatError as e:
            py_run, py_err = None, e
        if "error" in nl:
            if py_err is None:
                mismatches.append(f"{name}: node errored ({nl['error']['message'][:80]}), python parsed")
                continue
            n_doc = nl["error"].get("doctor") or {}
            if n_doc != py_err.doctor:
                mismatches.append(f"{name}: doctor differs\n  node={json.dumps(n_doc)[:300]}\n  py  ={json.dumps(py_err.doctor)[:300]}")
        else:
            if py_err is not None:
                mismatches.append(f"{name}: python doctor ({py_err.doctor['title'][:60]}), node parsed")
                continue
            if not _close(nl["run"], py_run):
                mismatches.append(f"{name}: run differs\n  node={json.dumps(nl['run'])[:400]}\n  py  ={json.dumps(py_run)[:400]}")
    assert not mismatches, "PARITY MISMATCHES:\n" + "\n".join(mismatches)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_node_module_loads_cleanly():
    res = subprocess.run(
        ["node", "-e", "import('./frontend/qpcr/qpcr-universal.js').then(m => "
         "console.log(JSON.stringify({v: m.QPCR_UNIVERSAL_VERSION, rotor: m.ROTOR_EXTS.length, "
         "aliases: m.COLUMN_ALIASES.length})))"],
        capture_output=True, text=True, timeout=60,
        cwd=REPO)
    assert res.returncode == 0, res.stderr[:1000]
    out = json.loads(res.stdout.strip().splitlines()[-1])
    assert out["v"] == "1.0.0"
    assert out["rotor"] == 6
    assert out["aliases"] >= 80
