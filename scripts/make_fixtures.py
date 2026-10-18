#!/usr/bin/env python3
"""make_fixtures.py — DETERMINISTIC generator for the universal-format fixture corpus.

Phase 0 (T0.1) + Phase 3 (T3.3) of QPCR_UNIVERSAL_FORMAT_SUPPORT_TASKS.md.

Every fixture is byte-stable: fixed RNG seeds, fixed ZIP timestamps, fixed
sector layout.  `--check` re-generates to memory and compares with the files
on disk (used by tests/test_universal.py so a regeneration can never silently
change the corpus).

Fixtures produced (all into tests/fixtures/qpcr/):
  unknown_long.csv   multi-section unknown layout (meta + amplification-long
                     + Cq results) — exercises the layout reasoner's section
                     splitting and cross-section sameWell merge
  cq_only.csv        unfamiliar Cq-only table (no "well" token) — reasoner
                     cq-table path + run.cqOnly honesty
  semicol.csv        semicolon-delimited table — delimiter detection
  utf16.tsv          UTF-16LE with BOM — BOM decode path
  unknown_wide.xlsx  minimal XLSX, wide Cycle N grid with unfamiliar headers
  demo.xls           deterministic OLE2/CFB + BIFF8 twin of unknown_wide.xlsx
                     (same grid → both must yield the same analysis; exercises
                     RK, MULRK, LABELSST, NUMBER, FORMULA cache, miniFAT)
  stub.qbd           Rotor-Gene-family binary stub (no data) → guided card
  junk.csv           random binary bytes renamed .csv → format doctor
  eds_demo.eds       Applied Biosystems EDS bundle (ZIP + apldbio/sds/) —
                     native per-well read (Delta Rn curves, ABI column-major)
  wrapped_qbg.qbg    printable vendor banner + gzip → rich vendor-DB card
  wrapped_run.qbd    printable vendor banner + gzip of a template CSV —
                     content beats the ROTOR-family extension

Run:  python3 scripts/make_fixtures.py          (write/refresh)
      python3 scripts/make_fixtures.py --check  (verify byte-identical)
"""
import io
import math
import os
import random
import struct
import sys
import zipfile
import zlib

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "qpcr")
ZIP_DATE = (2026, 1, 1, 0, 0, 0)  # fixed DOS timestamp → byte-stable zips

# ─────────────────────────────────────────────────────────────────
# Shared wide grid (the .xlsx / .xls twins must parse identically)
# ─────────────────────────────────────────────────────────────────
CYCLES = 40


def curve_for(seed, half):
    """Deterministic sigmoid amplification curve, 4 dp."""
    out = []
    for c in range(1, CYCLES + 1):
        v = 0.05 + 1.9 / (1.0 + math.exp(-(c - half) / 1.6))
        out.append(round(v, 4))
    return out


def flat_curve():
    return [round(0.05 + 0.002 * c, 4) for c in range(1, CYCLES + 1)]


WIDE_HEADER = ["Pos", "Specimen", "Assay", "Reporter", "Cq"] + [str(c) for c in range(1, CYCLES + 1)]
WIDE_ROWS = [
    ["A1", "S1", "GAPDH", "FAM", 20.5, *curve_for(1, 20)],
    ["A2", "S2", "GAPDH", "FAM", 24.1, *curve_for(2, 24)],
    ["A3", "NTC", "GAPDH", "FAM", None, *flat_curve()],
    ["B1", "S1", "ACTB", "HEX", 22.3, *curve_for(3, 22)],
]


# ─────────────────────────────────────────────────────────────────
# Text fixtures
# ─────────────────────────────────────────────────────────────────
def unknown_long_csv():
    lines = [
        "Run Info",
        "Instrument,OnePCR-Emulator",
        "Software,OnePCR Suite 4.2",
        "Run Date,2026-10-18",
        "",
        "Amplification Curves",
        "Chamber,Specimen,Assay,Reporter,Cycle,Signal",
    ]
    for row in WIDE_ROWS:
        pos, spec, assay, reporter = row[0], row[1], row[2], row[3]
        curve = row[5:]
        for c, v in enumerate(curve, start=1):
            lines.append(f"{pos},{spec},{assay},{reporter},{c},{v:.4f}")
    lines += ["", "Cq Results", "Chamber,Specimen,Assay,Cq,Cq SD"]
    cq_vals = [("A1", "S1", "GAPDH", "20.50", "0.12"),
               ("A2", "S2", "GAPDH", "24.10", "0.21"),
               ("A3", "NTC", "GAPDH", "", ""),
               ("B1", "S1", "ACTB", "22.30", "0.09")]
    for pos, spec, assay, cq, sd in cq_vals:
        lines.append(f"{pos},{spec},{assay},{cq},{sd}")
    return "\n".join(lines) + "\n"


def cq_only_csv():
    lines = ["Position,Specimen,Assay,Cq",
             "A1,S1,GAPDH,20.50",
             "A2,S2,GAPDH,24.10",
             "A3,NTC,GAPDH,",
             "B1,S1,ACTB,22.30"]
    return "\n".join(lines) + "\n"


def semicol_csv():
    lines = ["Well;Sample;Target;Channel;Cq;Tm",
             "A1;S1;GAPDH;FAM;20.5;82.1",
             "A2;S2;GAPDH;FAM;24.1;82.4",
             "B1;S1;ACTB;HEX;22.3;79.5"]
    return "\n".join(lines) + "\n"


def utf16_tsv():
    text = "\n".join([
        "Well\tSample\tTarget\tChannel\tCq",
        "A1\tS1\tGAPDH\tFAM\t20.5",
        "A2\tS2\tGAPDH\tFAM\t24.1",
    ]) + "\n"
    return b"\xff\xfe" + text.encode("utf-16-le")


# ─────────────────────────────────────────────────────────────────
# Minimal deterministic XLSX (stored entries, inline strings)
# ─────────────────────────────────────────────────────────────────
def _col_letter(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _esc(v):
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def make_xlsx():
    rows_xml = []
    all_rows = [WIDE_HEADER] + [r for r in WIDE_ROWS]
    for ri, row in enumerate(all_rows, start=1):
        cells = []
        for ci, v in enumerate(row):
            ref = f"{_col_letter(ci)}{ri}"
            if v is None or v == "":
                continue
            if isinstance(v, (int, float)):
                cells.append(f'<c r="{ref}"><v>{v}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{_esc(v)}</t></is></c>')
        rows_xml.append(f'<row r="{ri}">' + "".join(cells) + "</row>")
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             "<sheetData>" + "".join(rows_xml) + "</sheetData></worksheet>")
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>")
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="Results" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
               "</Relationships>")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:  # STORED → byte-stable
        for name, data in [
            ("[Content_Types].xml", ct),
            ("_rels/.rels", rels),
            ("xl/workbook.xml", wb),
            ("xl/_rels/workbook.xml.rels", wb_rels),
            ("xl/worksheets/sheet1.xml", sheet),
        ]:
            zi = zipfile.ZipInfo(name, date_time=ZIP_DATE)
            zi.compress_type = zipfile.ZIP_STORED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data.encode("utf-8"))
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────
# BIFF8 record helpers + RK codec (spec Phase 3; bidirectional test first)
# ─────────────────────────────────────────────────────────────────
def rec(rid, payload=b""):
    return struct.pack("<HH", rid, len(payload)) + payload


def rk_encode(x):
    """Encode a number as BIFF8 RK. Integral / x100 values are exact; all
    other values use the IEEE high-32-bit path (30-bit mantissa)."""
    if x is None:
        return None
    xi = int(round(x))
    if xi == x and -(1 << 29) <= xi < (1 << 29):
        return ((xi & 0x3FFFFFFF) << 2) | 0b10
    x100 = int(round(x * 100))
    if abs(x100 / 100.0 - x) < 1e-9 and -(1 << 29) <= x100 < (1 << 29):
        return ((x100 & 0x3FFFFFFF) << 2) | 0b11
    # IEEE path: RK holds the HIGH 32 bits of the little-endian double
    # (sign + exponent + top 20 mantissa bits), low 2 flag bits cleared.
    raw = struct.pack("<d", float(x))
    hi = struct.unpack("<I", raw[4:8])[0]
    return hi & 0xFFFFFFFC


def rk_decode(rk):
    """Decode a BIFF8 RK value (bit0 fx100, bit1 integer-in-high-30)."""
    rk &= 0xFFFFFFFF
    if rk & 2:
        num = rk >> 2
        if num >= (1 << 29):
            num -= (1 << 30)
    else:
        num = struct.unpack("<d", struct.pack("<Q", (rk & 0xFFFFFFFC) << 32))[0]
    if rk & 1:
        num /= 100.0
    return num


def _xlstr(s):
    b = s.encode("latin-1", "replace")
    return struct.pack("<HB", len(s), 0) + b  # compressed 8-bit


def make_workbook_stream():
    """Build the Workbook stream (globals substream + sheet substream)."""
    all_rows = [WIDE_HEADER] + [r for r in WIDE_ROWS]
    # Shared string table: every text cell
    sst = []
    sst_index = {}
    for row in all_rows:
        for v in row:
            if isinstance(v, str) and v != "":
                if v not in sst_index:
                    sst_index[v] = len(sst)
                    sst.append(v)
    # Sheet records
    sheet = []
    for ri, row in enumerate(all_rows):
        # Cq column (4): NUMBER exact / empty / one FORMULA cache exercise
        # Everything else positioned per row:
        for ci, v in enumerate(row):
            if isinstance(v, str) and v != "":
                sheet.append(rec(0x00FD, struct.pack("<HHHI", ri, ci, 0, sst_index[v])))  # LABELSST
                continue
            if ci == 4:
                if v is None:
                    continue
                if ri == 2:  # A2 Cq via FORMULA cached numeric result
                    payload = struct.pack("<HHH", ri, ci, 0) + struct.pack("<d", float(v)) + struct.pack("<HII", 0, 0, 0)
                    sheet.append(rec(0x0006, payload))  # FORMULA
                else:
                    sheet.append(rec(0x0203, struct.pack("<HHH", ri, ci, 0) + struct.pack("<d", float(v))))  # NUMBER
                continue
            # numeric: data rows 1–3 curves are written explicitly below (MULRK / RK runs)
            if ri in (1, 2, 3):
                continue
            sheet.append(rec(0x027E, struct.pack("<HHHI", ri, ci, 0, rk_encode(v))))  # RK

    # MULRK runs: A1 (row 1) cols 5..44, A3 (row 3) cols 5..44
    for ri in (1, 3):
        row = all_rows[ri]
        pairs = b""
        for ci in range(5, 5 + CYCLES):
            pairs += struct.pack("<HI", 0, rk_encode(row[ci]))
        sheet.append(rec(0x00BD, struct.pack("<HH", ri, 5) + pairs + struct.pack("<H", 5 + CYCLES - 1)))
    # A2 (row 2) curves: RK singles
    for ci in range(5, 5 + CYCLES):
        sheet.append(rec(0x027E, struct.pack("<HHHI", 2, ci, 0, rk_encode(all_rows[2][ci]))))

    sheet_bytes = rec(0x0809, struct.pack("<HHHHII", 0x0600, 0x0010, 0x0DBB, 0x07CC, 0, 0))
    sheet_bytes += b"".join(sheet)
    sheet_bytes += rec(0x000A)

    # Globals substream
    name = "Results"
    g_bof = rec(0x0809, struct.pack("<HHHHII", 0x0600, 0x0005, 0x0DBB, 0x07CC, 0, 0))
    sst_payload = struct.pack("<II", len(sst), len(sst)) + b"".join(_xlstr(s) for s in sst)
    sst_rec = rec(0x00FC, sst_payload)
    # offset of sheet BOF = len(g_bof) + len(boundsheet) + len(sst_rec) + len(EOF)
    bs_pos = len(g_bof)
    bs_len = 4 + 8 + len(name)  # record header + lbPlyPos/grbit/cch/grbit + name
    sheet_pos = bs_pos + bs_len + len(sst_rec) + 4
    boundsheet = rec(0x0085, struct.pack("<IHBB", sheet_pos, 0, len(name), 0) + name.encode("latin-1"))
    assert len(boundsheet) == bs_len, (len(boundsheet), bs_len)
    globals_bytes = g_bof + boundsheet + sst_rec + rec(0x000A)
    return globals_bytes + sheet_bytes


# ─────────────────────────────────────────────────────────────────
# Deterministic OLE2 / CFB container (spec T3.1)
# ─────────────────────────────────────────────────────────────────
ENDOFCHAIN = 0xFFFFFFFE
FREESECT = 0xFFFFFFFF


def make_cfb(stream_bytes):
    """Wrap a byte stream in a minimal single-FAT OLE2 compound file.
    Streams < 4096 B go through the mini-stream + miniFAT (exercises that path)."""
    n_mini = max(1, (len(stream_bytes) + 63) // 64)
    mini_data = stream_bytes + b"\x00" * (n_mini * 64 - len(stream_bytes))
    if len(mini_data) % 512:  # mini-stream lives in regular 512-byte sectors
        mini_data += b"\x00" * (512 - (len(mini_data) % 512))
    mini_fat = b"".join(struct.pack("<I", (i + 1) if i < n_mini - 1 else ENDOFCHAIN)
                        for i in range(n_mini))
    mini_fat += struct.pack("<I", FREESECT) * ((128 - (len(mini_fat) // 4) % 128) % 128)
    assert len(mini_fat) == 512, len(mini_fat)

    # Sector order: 0 = miniFAT, 1 = directory, 2.. = ministream, last = FAT
    dir_entry_count = 4  # root + Workbook + 2 padding (one 512-byte dir sector)
    n_mini_sect = len(mini_data) // 512
    assert len(mini_data) % 512 == 0
    first_mini = 2
    dir_sect = 1
    fat_sect = first_mini + n_mini_sect

    fat = [FREESECT] * 128
    fat[0] = ENDOFCHAIN          # miniFAT chain end
    fat[dir_sect] = ENDOFCHAIN   # directory chain end
    for i in range(n_mini_sect):
        s = first_mini + i
        fat[s] = (first_mini + i + 1) if i < n_mini_sect - 1 else ENDOFCHAIN
    fat[fat_sect] = ENDOFCHAIN

    def dirent(name, obj_type, start, size, child=FREESECT):
        nb = name.encode("utf-16-le") + b"\x00\x00"
        nb = nb + b"\x00" * (64 - len(nb))
        return (nb + struct.pack("<HBB", (len(name) + 1) * 2, obj_type, 1)
                + struct.pack("<III", FREESECT, FREESECT, child)
                + b"\x00" * 16 + struct.pack("<I", 0)
                + struct.pack("<QQ", 0, 0)
                + struct.pack("<IQ", start, size) + b"\x00" * 4)[:128]

    directory = (dirent("Root Entry", 5, first_mini, len(mini_data), child=1)
                 + dirent("Workbook", 2, 0, len(stream_bytes))
                 + dirent("", 0, 0, 0) + dirent("", 0, 0, 0))
    assert len(directory) == 512

    header = bytearray(512)
    header[0:8] = bytes.fromhex("D0CF11E0A1B11AE1")
    struct.pack_into("<HHHH", header, 24, 0x003E, 0x0003, 0xFFFE, 9)
    struct.pack_into("<H", header, 32, 6)
    struct.pack_into("<I", header, 44, 1)        # num FAT sectors
    struct.pack_into("<I", header, 48, dir_sect)  # first dir sector
    struct.pack_into("<I", header, 56, 4096)      # mini stream cutoff
    struct.pack_into("<I", header, 60, 0)         # first miniFAT sector
    struct.pack_into("<I", header, 64, 1)         # num miniFAT sectors
    struct.pack_into("<II", header, 68, ENDOFCHAIN, 0)  # first DIFAT / count
    for i in range(109):
        struct.pack_into("<I", header, 76 + i * 4, fat_sect if i == 0 else FREESECT)

    out = bytes(header)
    out += mini_fat                                   # sector 0
    out += directory                                  # sector 1
    out += mini_data                                  # sectors 2..
    out += struct.pack("<128I", *fat)                 # FAT sector
    return out


def make_xls():
    return make_cfb(make_workbook_stream())


# ─────────────────────────────────────────────────────────────────
# Rotor-Gene family stub + junk
# ─────────────────────────────────────────────────────────────────
def stub_qbd():
    rng = random.Random(42)  # noqa: S311 — seeded, deterministic fixture bytes (not crypto)
    head = b"RGQ1" + bytes([0x02, 0x00]) + b"Rotor-Gene Q 2.3.1" + b"\x00" * 16
    return head + bytes(rng.randrange(256) for _ in range(512))


def junk_csv():
    rng = random.Random(7)  # noqa: S311 — seeded, deterministic fixture bytes (not crypto)
    b = bytearray(rng.randrange(256) for _ in range(640))
    b[10] = 0
    b[200] = 0  # NULs → sniff = binary
    return bytes(b)


# ─────────────────────────────────────────────────────────────────
# Build / check
# ─────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────
# Vendor-container fixtures (EDS bundle + gzip-wrapped tables) — T8/T9
# ─────────────────────────────────────────────────────────────────
def gzip_stored(data):
    """Hand-built gzip of DEFLATE "stored" blocks (no compressor version
    drift → byte-stable across Python releases; valid CRC32 + ISIZE trailer
    so both the native and manual inflate paths accept it)."""
    out = bytearray(b"\x1f\x8b\x08\x00")          # magic, CM=8, FLG=0
    out += struct.pack("<IBB", 0, 0, 0xFF)        # MTIME=0, XFL=0, OS=255
    i = 0
    while True:
        chunk = data[i:i + 65535]
        i += len(chunk)
        out.append(1 if i >= len(data) else 0)    # BFINAL, BTYPE=00 (stored)
        out += struct.pack("<HH", len(chunk), len(chunk) ^ 0xFFFF)
        out += chunk
        if i >= len(data):
            break
    out += struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF,
                       len(data) & 0xFFFFFFFF)
    return bytes(out)


def make_eds_demo():
    """Applied Biosystems EDS bundle: ZIP + apldbio/sds/ analysis_result.txt
    (13-column SDS header, Delta Rn follow rows) + plate_setup.xml
    (detector→reporter) + experiment.xml (instrument model + run state)."""
    header = ["Well", "Sample Name", "Detector", "Task", "Ct", "Avg Ct",
              "Ct SD", "Delta Ct", "Qty", "Avg Qty", "Qty SD", "Amp Status",
              "Cq Conf"]
    recs = [
        (1, "NTC", "Target 1", "NTC", "", "", ""),          # blank Ct → null
        (1, "NTC", "Target 2", "NTC", "", "", ""),
        (12, "Std 1000", "Target 1", "STANDARD", "18.25", "0.12", "1000"),
        (12, "Std 1000", "Target 2", "STANDARD", "19.5", "0.18", "1000"),
        (26, "Sample A", "Target 1", "UNKNOWN", "22.75", "0.25", ""),
        (26, "Sample A", "Target 2", "UNKNOWN", "24.125", "0.31", ""),
    ]
    lines = ["Session Name\t", "\t".join(header)]
    for i, (well, sample, det, task, ct, sd, qty) in enumerate(recs):
        lines.append("\t".join([str(well), sample, det, task, ct, "", sd, "",
                                qty, "", "", "0", "0.95"]))
        lines.append("\t".join(
            ["Rn values"] + ["%.4f" % (100 + 1.5 * c + 7.0 * i)
                             for c in range(1, 6)]))
        lines.append("\t".join(
            ["Delta Rn values"] + ["%.4f" % (0.5 * c + 0.25 * i)
                                   for c in range(1, 6)]))
    ar_text = "\r\n".join(lines) + "\r\n"
    plate = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
             '<Plate><Name></Name><Rows>8</Rows><Columns>12</Columns>\n'
             '<AssayList>\n'
             '<Assay><Name>Target 1</Name><Reporter>FAM</Reporter></Assay>\n'
             '<Assay><Name>Target 2</Name><Reporter>VIC</Reporter></Assay>\n'
             '</AssayList>\n</Plate>\n')
    exp = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Experiment><Name>eds demo protocol</Name>'
           '<RunState>COMPLETE</RunState>\n'
           '<ExperimentProperty type="InstrumentInfo"><Properties>\n'
           '<PropertyValue key="instrumentType"><String>QuantStudio 5 - '
           '96-Well 0.2-mL Block</String></PropertyValue>\n'
           '</Properties></ExperimentProperty>\n'
           '<InstrumentTypeId>appletini</InstrumentTypeId>\n</Experiment>\n')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:  # STORED → stable
        for name, data in [("apldbio/sds/analysis_result.txt", ar_text),
                           ("apldbio/sds/plate_setup.xml", plate),
                           ("apldbio/sds/experiment.xml", exp)]:
            zi = zipfile.ZipInfo(name, date_time=ZIP_DATE)
            zi.compress_type = zipfile.ZIP_STORED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data.encode("utf-8"))
    return buf.getvalue()


def _bh1600_blob():
    """Deterministic vendor-binary payload: schema keys, two run timestamps,
    and assay/well labels in the printable-run shape the label scanner reads
    (NULs act as separators; no data table — decoding it would be guessing)."""
    parts = [
        b"dm.a0\x00schema\x0bItems.Count\x00bh1600\x00",
        b"Samples\x00Cycles\x00MeltCycles\x00AnalyzedResult\x00CtSetting\x00",
        b"2026-01-02 03:04:05\x002026-01-02 03:05:06\x00",
        b"FAM\x00A10\x00SYNTH ASSAY A\x00SYNTH ASSAY B\x00",
    ]
    filler = (b"\x00" + b"\x07\x01\x02\x03") * 64
    return b"".join(parts) + filler


def make_wrapped_qbg():
    """15-byte printable vendor banner + gzip stream (the real .qbg shape:
    sniff → binary, embedded gzip at offset 15 → rich doctor card)."""
    return b"BHKJ20190118798" + gzip_stored(_bh1600_blob())


def make_wrapped_qbd():
    """Printable vendor header + gzip of a template CSV — a ROTOR-extension
    name whose CONTENT is a readable table (content beats extension)."""
    csv = ("Well,Sample,Target,Channel,Cq\n"
           "A1,S1,GAPDH,FAM,20.5\n"
           "A2,S2,GAPDH,FAM,24.1\n"
           "B1,NTC,GAPDH,FAM,\n")
    return b"OnePCR-DEMO-EXPORT-2.0" + gzip_stored(csv.encode("utf-8"))


def build_all():
    return {
        "unknown_long.csv": unknown_long_csv().encode("utf-8"),
        "cq_only.csv": cq_only_csv().encode("utf-8"),
        "semicol.csv": semicol_csv().encode("utf-8"),
        "utf16.tsv": utf16_tsv(),
        "unknown_wide.xlsx": make_xlsx(),
        "demo.xls": make_xls(),
        "stub.qbd": stub_qbd(),
        "junk.csv": junk_csv(),
        "eds_demo.eds": make_eds_demo(),
        "wrapped_qbg.qbg": make_wrapped_qbg(),
        "wrapped_run.qbd": make_wrapped_qbd(),
    }


def main(argv):
    fixtures = build_all()
    if "--check" in argv:
        bad = []
        for name, data in fixtures.items():
            path = os.path.join(FIXTURE_DIR, name)
            if not os.path.exists(path):
                bad.append(f"MISSING {name}")
            elif open(path, "rb").read() != data:
                bad.append(f"DRIFT   {name}")
        if bad:
            print("\n".join(bad))
            return 1
        print(f"OK: {len(fixtures)} generated fixtures byte-identical to tests/fixtures/qpcr/")
        return 0
    os.makedirs(FIXTURE_DIR, exist_ok=True)
    for name, data in fixtures.items():
        path = os.path.join(FIXTURE_DIR, name)
        old = open(path, "rb").read() if os.path.exists(path) else None
        if old != data:
            with open(path, "wb") as f:
                f.write(data)
            print(f"wrote {name} ({len(data)} B)")
        else:
            print(f"unchanged {name} ({len(data)} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
