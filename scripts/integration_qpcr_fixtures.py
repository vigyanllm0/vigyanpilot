#!/usr/bin/env python3
"""
integration_qpcr_fixtures.py — deep fixture-upload sweep through the real qPCR analyzer page.

Uploads every parser fixture (plus an inline Cq-only honesty probe) via the page's
actual file input, then asserts: parse status, expected well count, amplification chart
series (real curves plotted, not phantom legends), the honest empty state for Cq-only
data, data-table rows, tab switching, melt-canvas paint, and zero console errors.

This is the regression net for the 2026-10-18 "empty Amplification chart" class of bug:
parsers that extracted zero curves while the legend pretended to show data.

Usage:
    python3 scripts/integration_qpcr_fixtures.py
    python3 scripts/integration_qpcr_fixtures.py --url http://localhost:8765/frontend/qpcr-analyzer.html

Requires: websocket-client, repo checkout with tests/fixtures/qpcr/, Chrome.
Exit non-zero on any failure. CI-able.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_DIR = os.path.join(REPO, "tests", "fixtures", "qpcr")

# (filename, expected wells, min amplification chart series)
FIXTURES = [
    ("test_run.rdml", 30, 1),          # standard RDML <adp>/<mdp> — the bug's ground zero
    ("rdml_minimal.xml", 5, 1),        # flat-text amplificationData legacy path
    ("cfx_minimal.csv", 5, 1),         # wide Cycle N columns
    ("cfx_with_melt.csv", 4, 1),
    ("cfx_sectioned.csv", 4, 1),       # summary + Amplification Data + Melt Data sections
    ("cfx_longformat.csv", 2, 1),      # Well,Fluor,Cycle,Value long table
    ("template_minimal.tsv", 5, 1),    # semicolon Amplification column
    ("template_wide_cycles.tsv", 4, 1),
    ("demo-sybr-standard.tsv", 10, 1),
    ("demo-taqman-multiplex.tsv", 10, 1),
    ("demo-problem-run.tsv", 10, 1),
    ("edge_cases.tsv", 5, 1),
    ("stress_384.tsv", 384, 1),
]

# Cq-only export (no per-cycle fluorescence): the exact shape behind the user report.
# Expectation: parses, plots ZERO series, and says so honestly instead of a blank plot.
CQ_ONLY_INLINE = (
    "Well,Fluor,Target,Content,Cq,Cq Std. Dev\n"
    "1,FAM,GAPDH,Sample 1,23.45,0.12\n"
    "2,FAM,GAPDH,Sample 2,31.02,0.45\n"
    "3,FAM,GAPDH,NTC,,0.00\n"
)
CQ_ONLY_WELLS = 3


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def run_sweep(url):
    import websocket

    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome):
        chrome = "google-chrome"
    port = 9241
    profile = "/tmp/chrome_qpcr_integration"
    subprocess.run(["rm", "-rf", profile], capture_output=True)
    proc = subprocess.Popen(
        [chrome, "--headless=new", "--disable-gpu", f"--remote-debugging-port={port}",
         f"--user-data-dir={profile}", "--remote-allow-origins=*", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(4)

    try:
        data = urllib.request.urlopen(f"http://localhost:{port}/json/list").read()
        targets = json.loads(data)
        page_id = next(t["id"] for t in targets if t.get("type") == "page")

        ws = websocket.WebSocket()
        ws.connect(f"ws://localhost:{port}/devtools/page/{page_id}")
        ws.settimeout(5.0)

        msg_id = 0

        def send(method, params=None):
            nonlocal msg_id
            msg_id += 1
            ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
            return msg_id

        def wait_result(mid, timeout=15):
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    msg = json.loads(ws.recv())
                except Exception:
                    continue
                if msg.get("id") == mid and "result" in msg:
                    r = msg["result"]
                    if isinstance(r, dict) and "result" in r:
                        return r["result"].get("value")
                    return r  # command ack (e.g. Page.navigate) — no nested result
            return None

        def evaluate(expr, timeout=15):
            mid = send("Runtime.evaluate",
                       {"expression": expr, "returnByValue": True, "awaitPromise": True})
            return wait_result(mid, timeout)

        # Install console/page error hook BEFORE navigation
        send("Page.enable")
        send("Runtime.enable")
        send("Page.addScriptToEvaluateOnNewDocument", {
            "source": ("window.__qpcrErrors = [];\n"
                       "window.addEventListener('error', e => window.__qpcrErrors.push(String(e.message)));\n"
                       "window.addEventListener('unhandledrejection', e => window.__qpcrErrors.push('rejection: ' + String(e.reason)));\n"
                       "const __origErr = console.error.bind(console);\n"
                       "console.error = function(...a) { window.__qpcrErrors.push('console.error: ' + a.map(String).join(' ')); __origErr(...a); };\n")
        })
        mid = send("Page.navigate", {"url": url})
        wait_result(mid, timeout=20)
        time.sleep(6)  # module engine load

        engine_ok = evaluate("window.__engineLoaded === true")
        if not engine_ok:
            print("FATAL: engine did not load at " + url)
            return False

        checks = []  # (name, ok, detail)

        def check(name, ok, detail=""):
            checks.append((name, bool(ok), detail))

        def upload_and_parse(payload_b64, fname, timeout=30):
            evaluate(f"""
                (() => {{
                    const bin = atob('{payload_b64}');
                    const bytes = new Uint8Array(bin.length);
                    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
                    const file = new File([bytes], '{fname}');
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    const sb = document.getElementById('statusBar');
                    if (sb) {{ sb.textContent = ''; sb.style.display = 'none'; }}
                    const inp = document.getElementById('fileInput');
                    inp.files = dt.files;
                    inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }})()
            """)
            deadline = time.time() + timeout
            while time.time() < deadline:
                txt = evaluate("document.getElementById('statusBar') ? document.getElementById('statusBar').textContent : ''", 5)
                if txt and (txt.startswith("Parsed") or txt.startswith("Parse error")):
                    return txt
                time.sleep(0.5)
            return "(timeout)"

        import re as _re

        def status_wells(status):
            m = _re.search(r"Parsed (\d+) wells", status or "")
            return int(m.group(1)) if m else -1

        def click_tab(name):
            evaluate(f"document.querySelector('.tab[data-tab=\\'{name}\\']').click()")
            time.sleep(0.4)

        def canvas_colored(canvas_id):
            """Count saturated pixels (series colors). Grid/axes/text are gray => excluded."""
            return evaluate(f"""
                (() => {{
                    const c = document.getElementById('{canvas_id}');
                    if (!c || !c.width || !c.height) return -1;
                    const px = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
                    let n = 0;
                    for (let i = 0; i < px.length; i += 4) {{
                        const mx = Math.max(px[i], px[i+1], px[i+2]);
                        const mn = Math.min(px[i], px[i+1], px[i+2]);
                        if (mx - mn > 60) n++;
                    }}
                    return n;
                }})()
            """, 10)

        def canvas_graytext(canvas_id, rgb, tol=16):
            """Count pixels near a specific gray (e.g. empty-message #64748b = 100,116,139)."""
            r, g, b = rgb
            return evaluate(f"""
                (() => {{
                    const c = document.getElementById('{canvas_id}');
                    if (!c || !c.width || !c.height) return -1;
                    const px = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
                    let n = 0;
                    for (let i = 0; i < px.length; i += 4) {{
                        if (Math.abs(px[i]-{r}) < {tol} && Math.abs(px[i+1]-{g}) < {tol} && Math.abs(px[i+2]-{b}) < {tol}) n++;
                    }}
                    return n;
                }})()
            """, 10)

        # ── Fixture sweep ──
        for fname, expect_wells, min_series in FIXTURES:
            path = os.path.join(FIXTURE_DIR, fname)
            if not os.path.exists(path):
                check(f"{fname}: fixture exists", False, "missing")
                continue
            with open(path, "rb") as f:
                payload = b64(f.read())
            status = upload_and_parse(payload, fname)
            ok_parse = status.startswith("Parsed")
            check(f"{fname}: parses", ok_parse, status[:120])
            if not ok_parse:
                continue
            wells = status_wells(status)
            check(f"{fname}: wells={expect_wells}", wells == expect_wells, f"got {wells} ({status[:60]})")
            # activate the amplification tab (re-renders a canvas that may have been
            # sized while hidden), then verify curves actually painted
            click_tab("amplification")
            paint = canvas_colored("ampCanvas")
            check(f"{fname}: amp curves painted", paint is not None and paint > 500, f"colored px={paint}")
            # data table rows (switch to table tab, count body rows)
            click_tab("table")
            rows = evaluate("document.querySelectorAll('#dataTable tbody tr').length")
            check(f"{fname}: table rows >= {expect_wells}", rows is not None and rows >= expect_wells, f"got {rows}")
            # tab sweep: every tab renders without console/page errors
            for t in ("amplification", "melt", "standard", "expression", "plate", "qc"):
                click_tab(t)
            errs = evaluate("window.__qpcrErrors")
            check(f"{fname}: 0 console/page errors", errs == [], f"{errs}")

        # ── Melt canvas paint for the melt-bearing RDML ──
        with open(os.path.join(FIXTURE_DIR, "test_run.rdml"), "rb") as f:
            upload_and_parse(b64(f.read()), "test_run.rdml")
        click_tab("melt")
        melt_paint = canvas_colored("meltCanvas")
        check("test_run.rdml: melt curves painted", melt_paint is not None and melt_paint > 500, f"colored px={melt_paint}")
        click_tab("amplification")

        # ── Cq-only honesty probe ──
        status = upload_and_parse(b64(CQ_ONLY_INLINE.encode()), "cq_only.csv")
        check("cq_only: parses", status.startswith("Parsed"), status[:120])
        wells = status_wells(status)
        check(f"cq_only: wells={CQ_ONLY_WELLS}", wells == CQ_ONLY_WELLS, f"got {wells}")
        click_tab("amplification")
        colored = canvas_colored("ampCanvas")
        check("cq_only: no phantom curves painted",
              colored is not None and 0 <= colored < 50, f"colored px={colored}")
        msg_px = canvas_graytext("ampCanvas", (100, 116, 139))  # #64748b empty-message text
        check("cq_only: honest empty message shown", msg_px is not None and msg_px > 100, f"message px={msg_px}")
        click_tab("table")
        rows = evaluate("document.querySelectorAll('#dataTable tbody tr').length")
        check(f"cq_only: table rows >= {CQ_ONLY_WELLS}", rows is not None and rows >= CQ_ONLY_WELLS, f"got {rows}")

        errs = evaluate("window.__qpcrErrors")
        check("cq_only: 0 console/page errors", errs == [], f"{errs}")

        ws.close()

        # Print results
        print(f"\n{'=' * 64}")
        print("  qPCR Fixture Integration Sweep")
        print(f"  URL: {url}")
        print(f"{'=' * 64}")
        passed = failed = 0
        for name, ok, detail in checks:
            print(f"  {'✓' if ok else '✗'} {name:<52} {'PASS' if ok else 'FAIL'}")
            if ok:
                passed += 1
            else:
                failed += 1
                if detail:
                    print(f"      → {detail}")
        print(f"{'=' * 64}")
        print(f"  {passed} passed, {failed} failed\n")
        return failed == 0

    except Exception as e:
        print(f"Integration sweep error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        proc.terminate()
        proc.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8765/frontend/qpcr-analyzer.html",
                        help="URL of the qPCR analyzer page")
    args = parser.parse_args()
    ok = run_sweep(args.url)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
