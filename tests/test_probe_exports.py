"""
Failing-first tests for probe-data plumbing and export surfaces (Phase 0).

Covers the four root causes verified by the workflow study:

  F2  prod submit (/api/pipeline/submit) must forward ``probe_params`` so the
      probe-design step (24) honours the UI's reporter/quencher/Tm/length/GC
      customisation instead of silently falling back to hard-coded defaults.
  F3  ranking/probe extraction must be numbering-agnostic: ranking output
      lived at step 19 under the old 22-step numbering and lives at step 22
      today (the module is still named ``step19_ranking.py``), while step 19
      is now "Clinical Hotspot Filter" and emits no ``ranked_pairs`` at all.
  F4  vendor-order material collection must read the keys step 24 actually
      emits (``probe_results`` + ``ranked_pairs[].probes``) and must not
      double-count pairs from both step 22 and step 24.
  CSV dashboard exports (PG ``/api/reports/<id>/csv`` + SQLite mirror) must
      emit one row per primer pair including ``Probe_*`` columns.

These tests are written before the fixes: helper-level tests fail with
ImportError/AttributeError until the helpers exist; route-level tests fail on
assertions until the plumbing is fixed.
"""

import json
import os
import sqlite3

os.environ.setdefault("PRIMERFORGE_SECRET", "unit-test-secret-for-route-import")
# primerforge/auth.py requires this at import time; the full suite gets it from
# tests/test_verification_fix.py's collection-time assignment, but this module
# must also run standalone.
os.environ.setdefault("PRIMERFORGE_ADMIN_EMAIL", "probe-exports@test.com")
os.environ.setdefault("PRIMERFORGE_ADMIN_PASSWORD", "ProbeExports-Test-1!")

import flask
import pytest

# ── Fixtures (shapes mirror live step 22/24 output, job 82a35f9c) ──────────

FWD = "ATCGFWD" + "ACGT" * 5           # distinctive: easy membership asserts
REV = "GCTAGREV" + "TGCA" * 5
PROBE_SEQ = "GGGGPROBE" + "CACC" * 5   # distinctive probe sequence


def _probe():
    return {
        "sequence": PROBE_SEQ,
        "length": len(PROBE_SEQ),
        "tm": 68.17,
        "gc_percent": 60.0,
        "hairpin_dg": -3.2,
        "reporter_5prime": "FAM",
        "quencher_3prime": "BHQ-1",
        "mod5": "",
        "mod3": "",
        "position_start": 141,
        "position_end": 170,
        "score": 0.91,
        "tm_offset_used": 8.0,
    }


def _pair(with_probe: bool = False):
    p = {
        "rank": 1,
        "pair_id": 1,
        "score": 88.5,
        "penalty_score": 11.5,
        "total_penalty": 11.5,
        "overall_status": "PASS",
        "status": "PASS",
        "overall_pass": True,
        "forward": {"sequence": FWD, "tm": 61.2, "gc": 50.0},
        "reverse": {"sequence": REV, "tm": 62.0, "gc": 52.0},
        "forward_primer": FWD,
        "reverse_primer": REV,
        "amplicon_size": 240,
        "delta_tm_nn": 0.8,
        "cross_dimer_dg": -3.1,
        "product_start": 1382,
        "product_end": 1630,
    }
    if with_probe:
        p["probes"] = [_probe()]
        p["probe_status"] = "probe_designed"
        p["probe_reason"] = None
    return p


def current_era_steps(probe_step_output=None):
    """24-step era: 19 = Clinical Hotspot, 22 = ranking, 24 = probe design."""
    if probe_step_output is None:
        probe_step_output = {
            "probe_results": [
                {"pair_index": 0, "status": "probe_designed",
                 "probes": [_probe()], "reason": None}
            ],
            "ranked_pairs": [_pair(with_probe=True)],
            "probe_note": "Probe design completed for 1 pairs",
        }
    return [
        {"step_number": 19, "step_name": "Clinical Hotspot Filter (ClinVar)",
         "status": "passed", "duration_ms": 0,
         "output_data": {"clinical_checked": [], "clinvar_available": False,
                         "clinvar_note": "ClinVar not available"}},
        {"step_number": 22, "step_name": "Automated Penalty & Ranking Matrix",
         "status": "passed", "duration_ms": 1,
         "output_data": {"ranked_pairs": [_pair()], "top_pairs": [_pair()],
                         "ranking_note": "ok"}},
        {"step_number": 24, "step_name": "Probe Design (qPCR/TaqMan)",
         "status": "passed", "duration_ms": 2502,
         "output_data": probe_step_output},
    ]


def legacy_era_steps():
    """22-step era: ranking lived at step 19 and there was no probe step."""
    return [
        {"step_number": 18, "step_name": "Some step", "status": "passed",
         "duration_ms": 1, "output_data": {"note": "x"}},
        {"step_number": 19, "step_name": "Automated Penalty & Ranking Matrix",
         "status": "passed", "duration_ms": 1,
         "output_data": {"ranked_pairs": [_pair()], "top_pairs": [_pair()]}},
    ]


class _StubExecutor:
    """Captures background submits instead of running a pipeline."""

    def __init__(self):
        self.calls = []

    def submit(self, fn, *args):
        self.calls.append((fn, args))


# ── F2: prod submit forwards probe_params ───────────────────────────────────

class TestProdSubmitProbeParams:

    def _submit(self, monkeypatch, payload):
        from primerforge.engine import pipeline_routes as pr
        import primerforge.database as dbmod

        app = flask.Flask(__name__)
        app.register_blueprint(pr.pipeline_bp)

        captured = {}

        def fake_returning(sql, params=None):
            captured["insert_params"] = params
            return {"id": "11111111-2222-3333-4444-555555555555",
                    "status": "queued", "created_at": "2026-11-17"}

        monkeypatch.setattr(pr, "get_current_user",
                            lambda: {"user_id": 7, "email": "t@example.com",
                                     "role": "user"})
        monkeypatch.setattr(pr, "fetch_one", lambda *a, **k: None)
        monkeypatch.setattr(pr, "execute_returning", fake_returning)
        monkeypatch.setattr(pr, "consume_token", lambda *a, **k: True)
        monkeypatch.setattr(pr, "_celery_broker_available", lambda *a, **k: False)
        monkeypatch.setattr(pr, "_BACKGROUND_EXECUTOR", _StubExecutor())
        monkeypatch.setattr(dbmod, "log_audit", lambda *a, **k: None,
                            raising=False)

        resp = app.test_client().post("/api/pipeline/submit", json=payload)
        return resp, captured

    def test_submit_forwards_probe_params(self, monkeypatch):
        """Custom probe settings must reach the job's input_params (F2)."""
        payload = {
            "sequence": "ATGC" * 40,
            "mode": "express",
            "probe_mode": "taqman",
            "probe_reporter": "HEX",
            "probe_quencher": "BHQ-2",
            "probe_tm_offset_min": 6,
            "probe_tm_offset_max": 9,
            "probe_len_max": 26,
            "probe_gc_min": 35,
            "probe_hairpin_limit": -1.5,
            "probe_mod5": "5Hex",
            "probe_mod3": "",
        }
        resp, captured = self._submit(monkeypatch, payload)
        assert resp.status_code in (200, 202), resp.get_data(as_text=True)
        assert "insert_params" in captured, "job insert must have happened"

        input_params = json.loads(captured["insert_params"][1])
        assert input_params.get("probe_mode") == "taqman", \
            "probe_mode must survive into input_params"

        probe_params = input_params.get("probe_params")
        assert probe_params is not None, \
            "F2: prod submit must forward probe_params (UI customisation)"
        assert probe_params["reporter"] == "HEX"
        assert probe_params["quencher"] == "BHQ-2"
        assert probe_params["tm_offset_min"] == 6
        assert probe_params["tm_offset_max"] == 9
        assert probe_params["len_max"] == 26
        assert probe_params["gc_min"] == 35
        assert probe_params["hairpin_limit"] == -1.5
        assert probe_params["mod5"] == "5Hex"

    def test_submit_probe_defaults_when_absent(self, monkeypatch):
        """A run without probe fields still carries usable probe defaults."""
        resp, captured = self._submit(monkeypatch, {
            "sequence": "ATGC" * 40, "mode": "express",
        })
        assert resp.status_code in (200, 202), resp.get_data(as_text=True)
        input_params = json.loads(captured["insert_params"][1])
        assert input_params.get("probe_mode") in (None, ""), \
            "absent probe_mode must stay falsy (step 24 skips)"
        probe_params = input_params.get("probe_params")
        assert probe_params is not None, "probe_params defaults must exist"
        assert probe_params["reporter"] == "FAM"
        assert probe_params["quencher"] == "BHQ-1"


# ── F3: numbering-agnostic ranking/probe extraction ─────────────────────────

class TestExtractPairsAndProbes:

    def test_current_era_uses_step_22_and_24(self):
        from primerforge.reports_routes import extract_pairs_and_probes
        pairs, probe_results = extract_pairs_and_probes(current_era_steps())
        assert len(pairs) == 1
        assert pairs[0]["forward"]["sequence"] == FWD
        assert pairs[0]["probes"][0]["sequence"] == PROBE_SEQ, \
            "probe-embedded ranked_pairs from step 24 must be used"
        assert len(probe_results) == 1
        assert probe_results[0]["status"] == "probe_designed"

    def test_legacy_era_uses_step_19(self):
        from primerforge.reports_routes import extract_pairs_and_probes
        pairs, probe_results = extract_pairs_and_probes(legacy_era_steps())
        assert len(pairs) == 1
        assert pairs[0]["reverse"]["sequence"] == REV
        assert probe_results == []

    def test_step_19_clinical_output_is_never_mistaken_for_ranking(self):
        """Today's bug: step 19 = Clinical Hotspot has no ranked_pairs."""
        from primerforge.reports_routes import extract_pairs_and_probes
        steps = current_era_steps()
        clinical = steps[0]["output_data"]
        assert "ranked_pairs" not in clinical, "fixture sanity"
        pairs, _ = extract_pairs_and_probes(steps)
        assert pairs, "ranking must be found at step 22, not 19"

    def test_skipped_probe_step_keeps_pairs_without_probes(self):
        from primerforge.reports_routes import extract_pairs_and_probes
        steps = current_era_steps(probe_step_output={
            "probe_results": [],
            "probe_note": "Probe design skipped (probe_mode=False)",
        })
        pairs, probe_results = extract_pairs_and_probes(steps)
        assert len(pairs) == 1, "pairs must survive a skipped step 24"
        assert not pairs[0].get("probes")
        assert probe_results == []

    def test_probe_results_merged_when_pairs_lack_embedded_probes(self):
        from primerforge.reports_routes import extract_pairs_and_probes
        steps = current_era_steps(probe_step_output={
            "probe_results": [
                {"pair_index": 0, "status": "probe_designed",
                 "probes": [_probe()], "reason": None}
            ],
        })
        pairs, probe_results = extract_pairs_and_probes(steps)
        assert len(probe_results) == 1
        assert pairs[0]["probes"][0]["sequence"] == PROBE_SEQ, (
            "probes must be merged into pairs even when step 24 returns "
            "probe_results without re-emitting ranked_pairs"
        )

    def test_string_encoded_step_outputs_are_parsed(self):
        from primerforge.reports_routes import extract_pairs_and_probes
        steps = [
            {"step_number": 22, "output_data": json.dumps(
                {"ranked_pairs": [_pair()], "top_pairs": [_pair()]})},
            {"step_number": 24, "output_data": json.dumps({
                "probe_results": [{"pair_index": 0, "status": "probe_designed",
                                   "probes": [_probe()], "reason": None}],
                "ranked_pairs": [_pair(with_probe=True)],
            })},
        ]
        pairs, probe_results = extract_pairs_and_probes(steps)
        assert len(pairs) == 1
        assert pairs[0]["probes"][0]["sequence"] == PROBE_SEQ
        assert len(probe_results) == 1

    def test_json_is_not_double_encoded_in_report_row(self):
        """full_result may hold steps as JSON strings or native dicts."""
        from primerforge.reports_routes import extract_pairs_and_probes
        pairs, _ = extract_pairs_and_probes(current_era_steps())
        assert isinstance(pairs[0], dict)


# ── F3: report save (PG) ────────────────────────────────────────────────────

class TestSaveReportTopPair:

    def _app(self, monkeypatch):
        from primerforge import reports_routes as rr
        from primerforge import pg_auth

        app = flask.Flask(__name__)
        app.register_blueprint(rr.reports_bp)

        captured = {}

        def fake_fetch_one(sql, params=None):
            flat = " ".join(sql.split())
            if "FROM pipeline_jobs" in flat:
                return {"id": params[0],
                        "input_params": json.dumps({
                            "sequence": "A" * 300, "mode": "full",
                            "accession": "NM_TEST.1", "design_mode": "standard"})}
            return None  # step-19 query finds nothing (current-era bug)

        def fake_fetch_all(sql, params=None):
            return current_era_steps()

        def fake_returning(sql, params=None):
            captured["insert_params"] = params
            return {"id": 42, "created_at": "2026-11-17 10:00:00"}

        monkeypatch.setattr(rr, "fetch_one", fake_fetch_one)
        monkeypatch.setattr(rr, "fetch_all", fake_fetch_all)
        monkeypatch.setattr(rr, "execute_returning", fake_returning)
        monkeypatch.setattr(pg_auth, "get_current_user",
                            lambda: {"user_id": 5, "email": "e@example.com"})
        return app, captured

    def test_top_pair_extracted_for_current_era_job(self, monkeypatch):
        """F3: report save must find ranking at step 22, not step 19."""
        app, captured = self._app(monkeypatch)
        resp = app.test_client().post("/api/reports/save", json={
            "job_id": "job-current", "gene_input": "NM_TEST.1",
            "sequence_length": 300,
        })
        assert resp.status_code == 201, resp.get_data(as_text=True)

        params = captured["insert_params"]
        # INSERT columns: user_id, job_id, title, gene_input, sequence_length,
        # pair_count, top_score, top_forward, top_reverse, amplicon_size,
        # pipeline_mode, design_mode, full_result
        assert params[5] == 1, "pair_count must come from step 22 ranking"
        assert params[6] is not None, "top_score must be populated"
        assert params[7] == FWD, "top_forward must be the ranked fwd primer"
        assert params[8] == REV, "top_reverse must be the ranked rev primer"
        assert params[9] == 240, "amplicon_size must be populated"

    def test_full_result_stores_all_steps_for_download(self, monkeypatch):
        app, captured = self._app(monkeypatch)
        resp = app.test_client().post("/api/reports/save", json={
            "job_id": "job-current-2", "sequence_length": 300,
        })
        assert resp.status_code == 201
        full_result = json.loads(captured["insert_params"][12])
        assert len(full_result["steps"]) == 3
        assert full_result["steps"][-1]["step_number"] == 24


# ── F3 + export: report CSV (PG) ────────────────────────────────────────────

class TestReportCsv:

    def _client(self, monkeypatch):
        from primerforge import reports_routes as rr
        from primerforge import pg_auth

        report = {
            "id": 9, "user_id": 5, "title": "Design", "gene_input": "NM_TEST.1",
            "sequence_length": 300, "pair_count": 1, "top_score": 88.5,
            "top_forward": FWD, "top_reverse": REV, "amplicon_size": 240,
            "pipeline_mode": "full", "design_mode": "standard",
            "job_id": "job-9", "created_at": "2026-11-17 10:00:00",
            "full_result": json.dumps({"steps": current_era_steps()}),
        }

        def fake_fetch_one(sql, params=None):
            if "FROM user_reports" in " ".join(sql.split()):
                return report
            return None

        app = flask.Flask(__name__)
        app.register_blueprint(rr.reports_bp)
        monkeypatch.setattr(rr, "fetch_one", fake_fetch_one)
        monkeypatch.setattr(pg_auth, "get_current_user",
                            lambda: {"user_id": 5, "email": "e@example.com"})
        return app.test_client()

    def test_csv_has_a_row_per_pair(self, monkeypatch):
        """Today: header only — step 19 holds no ranked_pairs."""
        client = self._client(monkeypatch)
        resp = client.get("/api/reports/9/csv")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        lines = [l for l in body.strip().splitlines() if l]
        assert len(lines) >= 2, f"expected a pair row, got: {body!r}"
        assert FWD in body
        assert REV in body

    def test_csv_carries_probe_columns(self, monkeypatch):
        client = self._client(monkeypatch)
        resp = client.get("/api/reports/9/csv")
        body = resp.get_data(as_text=True)
        header = body.splitlines()[0]
        for col in ("Probe_Sequence", "Probe_Tm", "Probe_Status",
                    "Probe_Reporter", "Probe_Quencher"):
            assert col in header, f"missing {col} in {header!r}"
        assert PROBE_SEQ in body, "probe sequence must be in the CSV body"
        assert "FAM" in body
        assert "BHQ-1" in body

    def test_csv_probe_columns_are_appended_at_the_end(self, monkeypatch):
        """Position-based readers of the legacy 16 columns must keep working."""
        client = self._client(monkeypatch)
        header = client.get("/api/reports/9/csv") \
                      .get_data(as_text=True).splitlines()[0].split(",")
        assert header[:16] == [
            "Rank", "Pair_ID", "Score", "Status",
            "Forward_Sequence", "Forward_Tm", "Forward_GC",
            "Reverse_Sequence", "Reverse_Tm", "Reverse_GC",
            "Amplicon_Size", "Delta_Tm", "Cross_Dimer_dG",
            "Total_Penalty", "Design_Date", "Job_ID",
        ], "legacy columns must stay in place"
        assert len(header) > 16, "probe columns must be appended after them"
        assert header[16] == "Probe_Sequence", (
            "Probe_* columns must be appended at the end (never inserted "
            "mid-header, which would shift positional readers)"
        )


# ── F4: vendor order material ──────────────────────────────────────────────

class TestOrderMaterial:

    def test_collects_step_24_probes(self):
        from primerforge.engine.pipeline_routes import collect_order_material
        steps = [
            {"step_number": 22,
             "output_data": json.dumps({"ranked_pairs": [_pair()]})},
            {"step_number": 24,
             "output_data": json.dumps({
                 "probe_results": [{"pair_index": 0, "status": "probe_designed",
                                    "probes": [_probe()], "reason": None}],
                 "ranked_pairs": [_pair(with_probe=True)],
             })},
        ]
        primer_pairs, probes, sequences = collect_order_material(steps)

        assert probes, "F4: step-24 probes must reach the vendor order"
        assert probes[0]["sequence"] == PROBE_SEQ
        assert PROBE_SEQ in sequences, "probe sequences must be compliance-screened"
        assert FWD in sequences and REV in sequences

    def test_pairs_are_not_doubled_by_step_22_and_24(self):
        """Both steps emit ranked_pairs; the last producer is authoritative."""
        from primerforge.engine.pipeline_routes import collect_order_material
        steps = [
            {"step_number": 22,
             "output_data": json.dumps({"ranked_pairs": [_pair()]})},
            {"step_number": 24,
             "output_data": json.dumps({"ranked_pairs": [_pair(with_probe=True)]})},
        ]
        primer_pairs, probes, sequences = collect_order_material(steps)
        assert len(primer_pairs) == 1, "duplicate pairs would double an order"
        assert len([s for s in sequences if s == FWD]) == 1

    def test_legacy_job_without_probe_step_still_yields_pairs(self):
        from primerforge.engine.pipeline_routes import collect_order_material
        steps = [
            {"step_number": 19,
             "output_data": json.dumps({"ranked_pairs": [_pair()],
                                        "top_pairs": [_pair()]})},
        ]
        primer_pairs, probes, sequences = collect_order_material(steps)
        assert len(primer_pairs) == 1
        assert probes == []
        assert FWD in sequences and REV in sequences

    def test_first_probe_candidate_only(self):
        """One probe per pair — not all five design candidates."""
        from primerforge.engine.pipeline_routes import collect_order_material
        best = _probe()
        weaker = dict(_probe(), sequence="TTTTWEAKER" + "ACGT" * 3, tm=60.0)
        steps = [{"step_number": 24, "output_data": json.dumps({
            "probe_results": [{"pair_index": 0, "status": "probe_designed",
                               "probes": [best, weaker], "reason": None}],
            "ranked_pairs": [_pair(with_probe=True)],
        })}]
        _, probes, sequences = collect_order_material(steps)
        assert len(probes) == 1
        assert probes[0]["sequence"] == PROBE_SEQ
        assert "TTTTWEAKERACGTACGTACGTACGTACGTAC" not in sequences


# ── SQLite mirror export (dev-mode dashboard) ───────────────────────────────

class TestSqliteReportCsv:

    def _client(self, monkeypatch):
        from primerforge import reports_routes_sqlite as rr
        import primerforge.auth as auth_mod

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            """CREATE TABLE user_reports (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_email TEXT NOT NULL,
                   job_id TEXT NOT NULL,
                   title TEXT DEFAULT '',
                   forward_seq TEXT DEFAULT '',
                   reverse_seq TEXT DEFAULT '',
                   top_score REAL DEFAULT 0,
                   sequence_length INTEGER DEFAULT 0,
                   full_result TEXT DEFAULT '{}',
                   created_at REAL DEFAULT (strftime('%s','now'))
               )"""
        )
        conn.commit()

        app = flask.Flask(__name__)
        app.register_blueprint(rr.reports_bp)
        monkeypatch.setattr(rr, "get_db", lambda: conn)
        monkeypatch.setattr(auth_mod, "get_current_user",
                            lambda: {"user_id": 5, "email": "e@example.com"})
        return app.test_client()

    def test_save_then_csv_carries_pairs_and_probes(self, monkeypatch):
        client = self._client(monkeypatch)
        save = client.post("/api/reports/save", json={
            "job_id": "sqlite-job-1", "title": "Design",
            "sequence_length": 300,
            "full_result": {"pairs": [_pair(with_probe=True)],
                            "amplicon_size": 240, "pipeline_mode": "full",
                            "geneInput": "NM_TEST.1"},
        })
        assert save.status_code == 201, save.get_data(as_text=True)

        resp = client.get("/api/reports/1/csv")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        lines = [l for l in body.strip().splitlines() if l]
        assert len(lines) >= 2, f"expected a pair row, got: {body!r}"
        header = lines[0]
        assert "Forward_Sequence" in header
        assert "Probe_Sequence" in header
        assert PROBE_SEQ in body
        assert FWD in body and REV in body

    def test_legacy_report_without_pairs_still_downloads(self, monkeypatch):
        """Old saved reports have no pairs — keep the Field/Value fallback."""
        client = self._client(monkeypatch)
        save = client.post("/api/reports/save", json={
            "job_id": "sqlite-job-2", "title": "Old report",
            "sequence_length": 100, "forward_seq": "AAAA",
            "reverse_seq": "TTTT", "top_score": 55.0,
        })
        assert save.status_code == 201
        resp = client.get("/api/reports/1/csv")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Report ID" in body or "Forward_Sequence" in body
