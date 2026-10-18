#!/usr/bin/env python3
"""
qpcr_gate_report.py — Assemble the 6-week gate verdict.

Usage:
    python3 scripts/qpcr_gate_report.py --gsc-export path/to/gsc.csv --ga4-export path/to/ga4.csv
    python3 scripts/qpcr_gate_report.py --dry-run  # returns formatted table with zeros

Gate thresholds (from frozen spec):
  - Top-15 position on qPCR cluster
  - 100+ upload→view→export journeys
  - 20+ returning uploaders
  - AI mentions (manual check, flagged as such)
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

GATE_THRESHOLDS = {
    "position_target": 15,
    "journeys_target": 100,
    "returners_target": 20,
}


def load_gsc(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def load_ga4(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def analyze_gsc(rows):
    qpcr_pages = defaultdict(lambda: {"clicks": 0, "impressions": 0, "position_sum": 0.0})
    for r in rows:
        page = r.get("Page", r.get("page", ""))
        if "qpcr" not in page.lower() and "q-pcr" not in page.lower():
            continue
        qpcr_pages[page]["clicks"] += int(r.get("Clicks", 0) or 0)
        qpcr_pages[page]["impressions"] += int(r.get("Impressions", 0) or 0)
        qpcr_pages[page]["position_sum"] += float(r.get("Position", 0) or 0) * int(r.get("Impressions", 0) or 0)

    total_imp = sum(d["impressions"] for d in qpcr_pages.values())
    avg_pos = sum(d["position_sum"] for d in qpcr_pages.values()) / max(total_imp, 1)
    return {
        "qpcr_pages": len(qpcr_pages),
        "qpcr_clicks": sum(d["clicks"] for d in qpcr_pages.values()),
        "qpcr_impressions": total_imp,
        "avg_position": round(avg_pos, 1),
        "top_pages": sorted(qpcr_pages.items(), key=lambda x: -x[1]["impressions"])[:10],
    }


def analyze_ga4(rows):
    events = defaultdict(int)
    for r in rows:
        event = r.get("event_name", r.get("Event name", ""))
        if event.startswith("qpcr_"):
            events[event] += int(r.get("Event count", r.get("count", 1)) or 1)
    uploads = events.get("qpcr_file_uploaded", 0)
    views = events.get("qpcr_analysis_viewed", 0)
    saved = events.get("qpcr_view_saved", 0)
    methods = events.get("qpcr_methods_copied", 0)
    pdfs = events.get("qpcr_pdf_exported", 0)
    shares = events.get("qpcr_share_copied", 0)
    # Journeys = uploads that led to at least one export (approx: min of uploads and (pdfs+shares))
    journeys = min(uploads, pdfs + shares) if uploads else 0
    return {
        "uploads": uploads,
        "views": views,
        "views_saved": saved,
        "methods_copied": methods,
        "pdf_exported": pdfs,
        "share_copied": shares,
        "journeys_approx": journeys,
        "returning_uploaders": 0,  # requires user-level GA4 data, manual
    }


def print_verdict(gsc, ga4, dry_run=False):
    pos = gsc["avg_position"] if gsc else 0
    journeys = ga4["journeys_approx"] if ga4 else 0
    returners = ga4["returning_uploaders"] if ga4 else 0

    print("=" * 60)
    print("  qPCR 6-Week Gate Verdict")
    print("=" * 60)
    print(f"  {'Metric':<30} {'Value':>8} {'Target':>8} {'Status':>8}")
    print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*8}")
    print(f"  {'Avg position (qPCR cluster)':<30} {pos:>8.1f} {'≤15':>8} {'PASS' if pos <= 15 and pos > 0 else 'FAIL' if pos > 0 else 'N/A':>8}")
    print(f"  {'Upload→view→export journeys':<30} {journeys:>8} {'≥100':>8} {'PASS' if journeys >= 100 else 'FAIL' if journeys > 0 else 'N/A':>8}")
    print(f"  {'Returning uploaders':<30} {returners:>8} {'≥20':>8} {'PASS' if returners >= 20 else 'FAIL' if returners > 0 else 'N/A':>8}")
    print(f"  {'AI mentions':<30} {'manual':>8} {'any':>8} {'CHECK':>8}")
    print("=" * 60)
    if dry_run:
        print("  DRY RUN — no real data, all zeros")
    print()
    if gsc:
        print(f"  GSC: {gsc['qpcr_pages']} pages, {gsc['qpcr_clicks']} clicks, {gsc['qpcr_impressions']} impressions")
    if ga4:
        print(f"  GA4: {ga4['uploads']} uploads, {ga4['views']} views, {ga4['pdf_exported']} PDFs, {ga4['share_copied']} shares")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gsc-export", help="GSC performance export CSV")
    parser.add_argument("--ga4-export", help="GA4 events export CSV")
    parser.add_argument("--dry-run", action="store_true", help="Return formatted table with zeros")
    args = parser.parse_args()

    gsc = None
    ga4 = None
    if args.dry_run:
        gsc = {"qpcr_pages": 0, "qpcr_clicks": 0, "qpcr_impressions": 0, "avg_position": 0, "top_pages": []}
        ga4 = {"uploads": 0, "views": 0, "views_saved": 0, "methods_copied": 0, "pdf_exported": 0, "share_copied": 0, "journeys_approx": 0, "returning_uploaders": 0}
    else:
        if args.gsc_export:
            gsc = analyze_gsc(load_gsc(args.gsc_export))
        if args.ga4_export:
            ga4 = analyze_ga4(load_ga4(args.ga4_export))

    print_verdict(gsc, ga4, dry_run=args.dry_run)


if __name__ == "__main__":
    main()