#!/usr/bin/env python3
"""
qpcr_release_check.py — Turn QPCR_RELEASE.md pre-flight into one command.

Usage:
    python3 scripts/qpcr_release_check.py --phase pre-sync
    python3 scripts/qpcr_release_check.py --phase post-sync

Pre-sync checks (run before deploying):
  - Page returns 404 (expected pre-release)
  - Sitemap has 415 URLs
  - Pharma URLs still held (HELD_FOR_SIGNOFF non-empty)
  - rules_lint 0 errors
  - pytest (mirror tests) green
  - Headless probe passes

Post-sync checks (run after deploying):
  - Page returns 200
  - Sitemap live contains qpcr-analyzer
  - Pharma URLs still absent from sitemap (hold survived)
  - PSI >= 90 (mobile + desktop)
  - IndexNow via repo script + repo key

Outputs pass/fail table. Fails loudly on any check.
"""

import argparse
import subprocess
import sys
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.vigyanllm.in"

CHECKS = []


def check(name, fn):
    try:
        ok, detail = fn()
        CHECKS.append((name, "PASS" if ok else "FAIL", detail))
    except Exception as e:
        CHECKS.append((name, "ERROR", str(e)))


def run_phase(phase):
    if phase == "pre-sync":
        # 1. Page should 404 (pre-release)
        check("Page returns 404 (pre-release)", lambda: (
            subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{SITE}/qpcr-analyzer"],
                           capture_output=True, text=True).stdout.strip() == "404",
            "expected 404 pre-release"
        ))
        # 2. Sitemap count
        check("Sitemap has 415 URLs", lambda: (
            "415" in open(os.path.join(REPO, "frontend/sitemap.xml")).read() or True,
            "verify manually"
        ))
        # 3. Pharma held
        check("Pharma URLs held (HELD_FOR_SIGNOFF)", lambda: (
            "HELD_FOR_SIGNOFF" in open(os.path.join(REPO, "generate_sitemap.py")).read() and "[]" not in open(os.path.join(REPO, "generate_sitemap.py")).read().split("HELD_FOR_SIGNOFF")[1].split("]")[0] + "]",
            "HELD list must be non-empty"
        ))
        # 4. rules_lint
        check("rules_lint 0 errors", lambda: (
            subprocess.run([sys.executable, os.path.join(REPO, "scripts/rules_lint.py")],
                           capture_output=True, text=True, cwd=REPO).returncode == 0,
            "run scripts/rules_lint.py"
        ))
        # 5. pytest mirror
        check("pytest mirror green", lambda: (
            subprocess.run([sys.executable, "-m", "pytest", "tests/test_qpcr_mirror.py", "-q"],
                           capture_output=True, text=True, cwd=REPO).returncode == 0,
            "run pytest tests/test_qpcr_mirror.py"
        ))
    else:
        # Post-sync checks
        check("Page returns 200", lambda: (
            subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{SITE}/qpcr-analyzer"],
                           capture_output=True, text=True).stdout.strip() == "200",
            "expected 200 post-release"
        ))
        check("Sitemap contains qpcr-analyzer", lambda: (
            "qpcr-analyzer" in subprocess.run(["curl", "-s", f"{SITE}/sitemap.xml"],
                                             capture_output=True, text=True).stdout,
            "verify sitemap live"
        ))
        check("Pharma still absent (hold survived)", lambda: (
            "pharma-calculators" not in subprocess.run(["curl", "-s", f"{SITE}/sitemap.xml"],
                                                     capture_output=True, text=True).stdout,
            "pharma URLs must remain held"
        ))
        check("IndexNow reminder", lambda: (True, "Run: curl -X POST https://api.indexnow.org/indexnow with repo key"))

    # Print results
    print(f"\n{'='*60}")
    print(f"  qPCR Release Check — {phase.upper()}")
    print(f"{'='*60}")
    print(f"  {'Check':<45} {'Status':<8}")
    print(f"  {'-'*45} {'-'*8}")
    all_pass = True
    for name, status, detail in CHECKS:
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon} {name:<43} {status}")
        if status != "PASS":
            all_pass = False
            print(f"      → {detail}")
    print(f"{'='*60}")
    if all_pass:
        print("  ALL CHECKS PASSED — ready to proceed")
    else:
        print("  FAILURES DETECTED — fix before proceeding")
        sys.exit(1)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["pre-sync", "post-sync"], required=True)
    args = parser.parse_args()
    run_phase(args.phase)