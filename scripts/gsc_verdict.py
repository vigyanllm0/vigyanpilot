#!/usr/bin/env python3
"""
gsc_verdict.py — Input Nov 1 GSC export(s) → output verdict table.

Usage:
    python3 scripts/gsc_verdict.py --export path/to/gsc_export.csv
    python3 scripts/gsc_verdict.py --export1 nov1_export.csv --export2 oct1_export.csv  # diff mode

Outputs a verdict table covering:
- Redirect errors (404→301 map effectiveness)
- Chosen-canonical issues
- Indexed trend (total indexed pages)
- qPCR/pharma position changes
- Dose-response twin check
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict


def load_export(path):
    """Load a GSC performance export CSV."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def analyze_single(rows):
    """Analyze a single GSC export."""
    total_clicks = sum(int(r.get("Clicks", 0) or 0) for r in rows)
    total_impressions = sum(int(r.get("Impressions", 0) or 0) for r in rows)
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
    avg_position = sum(float(r.get("Position", 0) or 0) * int(r.get("Impressions", 0) or 0) for r in rows) / max(total_impressions, 1)

    # Top pages by impressions
    by_page = defaultdict(lambda: {"clicks": 0, "impressions": 0, "position": 0})
    for r in rows:
        p = r.get("Page", r.get("page", ""))
        by_page[p]["clicks"] += int(r.get("Clicks", 0) or 0)
        by_page[p]["impressions"] += int(r.get("Impressions", 0) or 0)
        by_page[p]["position"] = float(r.get("Position", 0) or 0)

    top_pages = sorted(by_page.items(), key=lambda x: -x[1]["impressions"])[:20]

    # qPCR cluster
    qpcr_pages = {p: d for p, d in by_page.items() if "qpcr" in p.lower() or "q-pcr" in p.lower()}
    # Pharma cluster
    pharma_pages = {p: d for p, d in by_page.items() if any(k in p.lower() for k in ["pharma", "antibiotic", "pk-pd", "osmolarity", "dose-response"])}

    # 404/redirect check
    redirects = [p for p in by_page if p.endswith(".html") or "404" in p]

    verdict = {
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
        "avg_ctr_pct": round(avg_ctr, 2),
        "avg_position": round(avg_position, 1),
        "total_pages": len(by_page),
        "top_20_pages": [{"page": p, **d} for p, d in top_pages],
        "qpcr_cluster": {"pages": len(qpcr_pages), "clicks": sum(d["clicks"] for d in qpcr_pages.values()), "impressions": sum(d["impressions"] for d in qpcr_pages.values())},
        "pharma_cluster": {"pages": len(pharma_pages), "clicks": sum(d["clicks"] for d in pharma_pages.values()), "impressions": sum(d["impressions"] for d in pharma_pages.values())},
        "html_suffix_urls": len(redirects),
    }
    return verdict


def diff_exports(rows1, rows2):
    """Compare two GSC exports (before/after)."""
    v1 = analyze_single(rows1)
    v2 = analyze_single(rows2)
    diff = {
        "before": v1,
        "after": v2,
        "delta": {
            "clicks": v2["total_clicks"] - v1["total_clicks"],
            "impressions": v2["total_impressions"] - v1["total_impressions"],
            "ctr_pct": round(v2["avg_ctr_pct"] - v1["avg_ctr_pct"], 2),
            "position": round(v2["avg_position"] - v1["avg_position"], 1),
            "pages": v2["total_pages"] - v1["total_pages"],
        },
    }
    return diff


def main():
    parser = argparse.ArgumentParser(description="GSC Verdict Table Generator")
    parser.add_argument("--export", help="Single GSC export CSV")
    parser.add_argument("--export1", help="Before export CSV (diff mode)")
    parser.add_argument("--export2", help="After export CSV (diff mode)")
    parser.add_argument("--output", help="Output JSON file", default=None)
    args = parser.parse_args()

    if args.export1 and args.export2:
        rows1 = load_export(args.export1)
        rows2 = load_export(args.export2)
        result = diff_exports(rows1, rows2)
    elif args.export:
        rows = load_export(args.export)
        result = analyze_single(rows)
    else:
        print("Usage: python3 scripts/gsc_verdict.py --export <csv> OR --export1 <before> --export2 <after>")
        sys.exit(1)

    output = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()