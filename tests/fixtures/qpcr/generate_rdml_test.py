#!/usr/bin/env python3
"""
generate_rdml_test.py — Synthetic RDML 1.2 verification run for the VigyanLLM qPCR Analyzer.
Usage: python3 generate_rdml_test.py [output.rdml]     (default: test_run.rdml)
Known answers: slope -3.47, E 94.0%, R2 0.9999; Livak 1.00/3.25/0.27; Pfaffl 1.00/3.09/0.29.
"""
import math, random, sys

random.seed(42)                      # reproducible — same file every run
OUT = sys.argv[1] if len(sys.argv) > 1 else "test_run.rdml"
CYCLES = 40
MELT_T = [round(60.0 + 0.5 * i, 1) for i in range(71)]   # 60.0 .. 95.0 C
GOI, GAP = "GOI", "GAPDH"

def amp(cq, plateau, base, steep=1.35):
    """Sigmoidal curve; crosses ~0.5 fluorescence exactly at the reported Cq."""
    c50 = cq + 1.38
    return [max(0.0, base + plateau / (1.0 + math.exp(-(c - c50) / steep))
                + random.uniform(-0.006, 0.006)) for c in range(1, CYCLES + 1)]

def ntc_amp(base):
    return [max(0.0, base + random.uniform(-0.002, 0.002)) for _ in range(CYCLES)]

def melt(tm, high):
    """Raw melt: S-drop centered on tm -> -dF/dT peaks at tm."""
    return [(t, max(0.0, 0.10 + (high - 0.10) / (1.0 + math.exp((t - tm) / 1.3))
                    + random.uniform(-0.004, 0.004))) for t in MELT_T]

def flat_melt():
    return [(t, max(0.0, 0.02 + random.uniform(-0.002, 0.002))) for t in MELT_T]

wells = []
# --- 5-point GOI standard curve, duplicates (A row + B row) ---
STD = [(1e6, 15.0, 15.1), (1e5, 18.5, 18.6), (1e4, 22.0, 22.1),
       (1e3, 25.4, 25.5), (1e2, 28.9, 29.0)]
for i, (q, cq1, cq2) in enumerate(STD):
    for rep, cq in ((0, cq1), (1, cq2)):
        wells.append(dict(id=f"{chr(65+rep)}{i+1}", sample=f"STD-{q:.0f}", target=GOI, cq=cq,
                          amp=amp(cq, random.uniform(1.5, 2.0), random.uniform(0.04, 0.07)),
                          melt=melt(84.6 + random.uniform(-0.2, 0.2), random.uniform(1.4, 1.8))))
# --- NTCs (no Cq element at all) ---
wells.append(dict(id="A6", sample="NTC", target=GOI, cq=None, amp=ntc_amp(0.025), melt=flat_melt()))
wells.append(dict(id="B6", sample="NTC", target=GAP, cq=None, amp=ntc_amp(0.022), melt=flat_melt()))
# --- Unknowns: rows C/D/E, GAPDH cols 1-3, GOI cols 4-6, triplicates ---
UNK = {"CTRL":  ("C", {GAP: (19.0, 19.1, 19.0), GOI: (21.5, 21.6, 21.5)}),
       "TREAT": ("D", {GAP: (19.1, 19.2, 19.0), GOI: (19.8, 19.9, 20.0)}),
       "KNOCK": ("E", {GAP: (19.0, 19.1, 19.2), GOI: (23.4, 23.5, 23.5)})}
for name, (row, tg) in UNK.items():
    for tgt, cqs in ((GAP, tg[GAP]), (GOI, tg[GOI])):
        col0 = 1 if tgt == GAP else 4
        for r, cq in enumerate(cqs):
            wells.append(dict(id=f"{row}{col0 + r}", sample=name, target=tgt, cq=cq,
                              amp=amp(cq, random.uniform(1.4, 1.9), random.uniform(0.04, 0.07)),
                              melt=melt(84.6 + random.uniform(-0.2, 0.2), random.uniform(1.3, 1.7))))

# --- XML emission (RDML 1.2 conventions) ---
L = ['<?xml version="1.0" encoding="UTF-8"?>',
     '<rdml version="1.2" xmlns="http://www.rdml.org"'
     ' xmlns:xs="http://www.w3.org/2001/XMLSchema-instance"'
     ' xs:schemaLocation="http://www.rdml.org rdml_v1_2.xsd">',
     '  <dateMade>2026-10-18T09:00:00</dateMade>',
     '  <dateUpdated>2026-10-18T09:00:00</dateUpdated>',
     '  <id><publisher>VigyanLLM</publisher><serialNumber>TEST-RUN-001</serialNumber></id>',
     '  <experiment>',
     '    <id><publisher>VigyanLLM</publisher><serialNumber>EXP-001</serialNumber></id>',
     '    <run>',
     '      <id><publisher>VigyanLLM</publisher><serialNumber>RUN-001</serialNumber></id>',
     '      <doc><docId>DOC-001</docId><description>Synthetic verification run: 5-pt GOI'
     ' standard curve (E~94%), 3 unknowns x 2 targets x 3 reps, 2 NTCs, SYBR melts ~84.6C.'
     '</description></doc>',
     '      <dateMade>2026-10-18</dateMade>',
     '      <experimenter>VigyanLLM Test Suite</experimenter>',
     '      <thermalCyclingConditions id="tc1"><description>95C/60C/72C x40; melt 60-95C'
     '</description></thermalCyclingConditions>']
for w in wells:
    L += [f'      <react id="{w["id"]}">',
          f'        <sample id="{w["sample"]}"/>',
          '        <dye id="SYBR">',
          f'          <target id="{w["target"]}"/>']
    if w["cq"] is not None:
        L.append(f'          <cq>{w["cq"]:.1f}</cq>')
    L += [f'          <adp><cyc>{c}</cyc><tmp>60.0</tmp><fluor>{f:.4f}</fluor></adp>'
          for c, f in enumerate(w["amp"], 1)]
    L += [f'          <mdp><tmp>{t:.1f}</tmp><fluor>{f:.4f}</fluor></mdp>' for t, f in w["melt"]]
    L += ['        </dye>', '      </react>']
L += ['    </run>', '  </experiment>']
samples = {}
for w in wells:
    s = w["sample"]
    if s.startswith("STD-"):
        samples[s] = (f'    <type>std</type>\n    <quantity><value>{float(s[4:]):.1f}'
                      f'</value><unit>copy</unit></quantity>')
    else:
        samples[s] = f'    <type>{"ntc" if s == "NTC" else "unkn"}</type>'
for sid, body in samples.items():
    L += [f'  <sample id="{sid}">', body, '  </sample>']
for tid, tt in ((GOI, "ToT"), (GAP, "Ref")):
    L += [f'  <target id="{tid}">', f'    <type>{tt}</type>',
          '    <assay><assayType>SYBR</assayType></assay>', '  </target>']
L += ['  <dye id="SYBR"/>', '</rdml>']

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
n_amp = sum(1 for w in wells if w["cq"] is not None)
print(f"Wrote {OUT}: {len(wells)} wells ({n_amp} amplified, {len(wells)-n_amp} NTC), "
      f"{len(samples)} samples, 2 targets, SYBR dye, {CYCLES} cycles + melt 60-95C")
PYEOF