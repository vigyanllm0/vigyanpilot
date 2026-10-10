"""
Docking Trust & Realism — Phase 1: GNINA repair + honest numbers (2026-10-08).

Every fixture in this file is traceable to an empirical check against the
official gnina v1.1 CPU binary (docker linux/x86_64, run 2026-10-08):

  * stdout results table = 5 whitespace columns per row
    (mode | affinity | intramol | CNN pose score | CNN affinity) — the
    real captured stdout is embedded verbatim below;
  * the old bare `--cnn_scoring --out <path>` form exits 1 with
    "Command line parse error" (boost value<> enum ate `--out`);
  * `--cnn_scoring=rescore --cnn crossdock_default2018` runs CPU-only;
  * timing, same receptor+ligand: search-only(exh=4) 12s · default 3-model
    ensemble rescore 246s · single-model rescore 37s (x86_64 emulation) →
    single model + the queue's 45s/ligand budget term.

Covers: stdout parser, CLI flag contract, honest consensus labelling
(consensus_mode full/partial/vina_only + per-candidate score_source),
stage metadata, job-budget formula sync with consensus_pipeline, and the
worker's soft-only RLIMIT — always via subprocess: importing
docking_worker in-process would cap pytest itself on Linux CI.
"""

import asyncio
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# ── Real captured stdout from `gnina v1.1` (2026-10-08, see docstring) ──────
REAL_GNINA_V11_STDOUT = r"""              _
             (_)
   __ _ _ __  _ _ __   __ _
  / _` | '_ \| | '_ \ / _` |
 | (_| | | | | | | | | (_| |
  \__, |_| |_|_|_| |_|\__,_|
   __/ |
  |___/

gnina v1.1 master:e4cb380+   Built Dec 18 2023.
gnina is based on smina and AutoDock Vina.
Please cite appropriately.

WARNING: No GPU detected. CNN scoring will be slow.
Recommend running with single model (--cnn crossdock_default2018)
or without cnn scoring (--cnn_scoring=none).

Commandline: /w/gnina --receptor 1ubq.pdb --ligand lig.sdf --exhaustiveness 4 --cnn_scoring=rescore --out out.sdf
Using random seed: 1791480954

0%   10   20   30   40   50   60   70   80   90   100%
|----|----|----|----|----|----|----|----|----|----|
***************************************************
 | pose 0 | initial pose not within box

mode |  affinity  |  intramol  |    CNN     |   CNN
     | (kcal/mol) | (kcal/mol) | pose score | affinity
-----+------------+------------+------------+----------
    1       -3.16       -0.58       0.8300      3.282
    2       -3.55       -0.19       0.8193      3.347
    3       -3.49       -0.59       0.7754      3.227
    4       -3.47       -0.51       0.7666      3.287
    5       -3.81       -0.46       0.7608      3.201
"""


# ══════════════════════════════════════════════════════════════════════════
# 1. stdout parser (the pre-Phase-1 parser required >=6 fields and could
#    never match a row of this 5-column table)
# ══════════════════════════════════════════════════════════════════════════

def _parse(text: str):
    from primerforge.pipelines.docking_engine import _parse_gnina_stdout
    return _parse_gnina_stdout(text)


def test_parse_real_v11_stdout():
    parsed = _parse(REAL_GNINA_V11_STDOUT)
    # best pose = mode 1 (rows are printed in rank order)
    assert parsed["affinity"] == pytest.approx(-3.16)
    assert parsed["intramol"] == pytest.approx(-0.58)
    assert parsed["cnn_score"] == pytest.approx(0.8300)      # pose confidence 0-1
    assert parsed["cnn_affinity"] == pytest.approx(3.282)     # log mol/L
    assert parsed["poses"] == 5
    assert parsed["table"][0]["mode"] == 1
    assert parsed["table"][-1]["cnn_affinity"] == pytest.approx(3.201)


def test_parse_skips_banner_progress_and_header_lines():
    parsed = _parse(REAL_GNINA_V11_STDOUT)
    # every data row parsed, and no junk row smuggled in (banner tokens,
    # "0% 10 20..." progress line, "|----" separators, units header)
    assert len(parsed["table"]) == 5
    assert all(r["mode"] >= 1 for r in parsed["table"])


def test_parse_rejects_short_and_non_numeric_rows():
    # 4 numeric columns → not a table row
    with pytest.raises(ValueError):
        _parse("    1       -3.16       -0.58       0.8300\n")
    # leading token not an integer mode
    with pytest.raises(ValueError):
        _parse("mode 1 -3.16 -0.58 0.8300 3.282\n")
    # no table at all
    with pytest.raises(ValueError):
        _parse("gnina v1.1\nsome error output\n")


def test_parse_takes_first_five_of_wider_rows():
    # Robust to a future appended column: the known five come first.
    parsed = _parse("    1       -3.16       -0.58       0.8300      3.282       1.23\n")
    assert parsed["affinity"] == pytest.approx(-3.16)
    assert parsed["cnn_affinity"] == pytest.approx(3.282)


def test_parse_preserves_cnn_sentinels_from_cnn_none():
    # Captured from `--cnn_scoring=none`: CNN columns are -1.0000/0.000.
    # The parser reports values raw (we always run rescore; the engine's
    # `confidence` field is what guards the 0-1 range).
    parsed = _parse(
        "    1       -5.58       -0.21      -1.0000      0.000\n"
        "    2       -5.12       -0.09      -1.0000      0.000\n")
    assert parsed["cnn_score"] == pytest.approx(-1.0)
    assert parsed["cnn_affinity"] == pytest.approx(0.0)


# ══════════════════════════════════════════════════════════════════════════
# 2. CLI flag contract (source-level: the broken forms must not return)
# ══════════════════════════════════════════════════════════════════════════

def test_engine_cli_uses_value_forms_not_bare_flags():
    text = (REPO / "primerforge" / "pipelines" / "docking_engine.py").read_text()
    assert '"--cnn_scoring=rescore"' in text, "value form required (bare flag = exit 1)"
    assert '"--cnn", "crossdock_default2018"' in text, "single-model CPU flag missing"
    # the exact bare pair that made v1.1 print "Command line parse error"
    assert '"--cnn_scoring",' not in text, "bare --cnn_scoring (value-eating) regressed"


# ══════════════════════════════════════════════════════════════════════════
# 3. Memory guard: worker soft-only RLIMIT + engine lift/restore (subprocess)
# ══════════════════════════════════════════════════════════════════════════

def _run_python(body: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        cwd=str(REPO), capture_output=True, text=True, timeout=180)


def test_worker_rlimit_is_soft_only_in_subprocess():
    """Importing the worker must lower SOFT only — a lowered HARD cap is
    inherited by gnina and can never be raised back by an unprivileged
    child (the old design made the CNN impossible by construction).

    Runs in a subprocess because docking_worker applies its guard at import
    time; in-process it would cap pytest's own address space on Linux CI.

    macOS rejects any finite RLIMIT_AS at the kernel (ValueError), so the
    guard degrades to a silent no-op there — either way the hard limit must
    never move.
    """
    out = _run_python("""
        import resource
        soft0, hard0 = resource.getrlimit(resource.RLIMIT_AS)
        mb = 600 * 1024 * 1024
        # Can this OS express a finite address-space cap at all?
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mb, hard0))
            can_cap = True
            resource.setrlimit(resource.RLIMIT_AS, (soft0, hard0))
        except ValueError:
            can_cap = False   # macOS: kernel rejects finite RLIMIT_AS
        import primerforge.docking_worker  # applies the guard at import
        soft1, hard1 = resource.getrlimit(resource.RLIMIT_AS)
        assert hard1 == hard0, f"hard must not move: {hard0} -> {hard1}"
        if can_cap:
            expected = mb if (hard0 == resource.RLIM_INFINITY or hard0 >= mb) else hard0
            assert soft1 == expected, f"soft must be {expected}, got {soft1}"
        else:
            assert soft1 == soft0, f"guard must no-op cleanly, got {soft1}"
        print("RLIMIT_OK")
    """)
    assert out.returncode == 0, out.stderr
    assert "RLIMIT_OK" in out.stdout


def test_gnina_memory_lift_roundtrip_in_subprocess():
    """The engine must lift the inherited 600MB soft cap across the gnina
    fork and restore it for everything else (capability-aware: on macOS,
    where the kernel rejects finite RLIMIT_AS, lift/restore is a no-op)."""
    out = _run_python("""
        import resource
        import primerforge.pipelines.docking_engine as de
        mb = 1024 * 1024
        soft0, hard0 = resource.getrlimit(resource.RLIMIT_AS)
        try:
            target_soft = 300 * mb if hard0 == resource.RLIM_INFINITY else min(300 * mb, hard0)
            resource.setrlimit(resource.RLIMIT_AS, (target_soft, hard0))
            guarded = True
        except ValueError:
            target_soft, guarded = soft0, False   # macOS: cannot cap
        try:
            prev = de._lift_address_space_limit()
            assert prev == (target_soft, hard0), prev
            lifted_soft, lifted_hard = resource.getrlimit(resource.RLIMIT_AS)
            assert lifted_hard == hard0, (lifted_hard, hard0)
            if guarded:
                assert lifted_soft == hard0, (lifted_soft, hard0)
            de._restore_address_space_limit(prev)
            assert resource.getrlimit(resource.RLIMIT_AS) == (target_soft, hard0)
            de._restore_address_space_limit(None)  # no-op must be safe
            assert resource.getrlimit(resource.RLIMIT_AS) == (target_soft, hard0)
            print("LIFT_OK")
        finally:
            try:
                resource.setrlimit(resource.RLIMIT_AS, (soft0, hard0))
            except ValueError:
                pass
    """)
    assert out.returncode == 0, out.stderr
    assert "LIFT_OK" in out.stdout


# ══════════════════════════════════════════════════════════════════════════
# 4. Job budget: GNINA term + sync with the pipeline's top-K
# ══════════════════════════════════════════════════════════════════════════

def test_budget_constants_sync_with_pipeline():
    import primerforge.docking_queue as dq
    from primerforge.pipelines.consensus_pipeline import GNINA_REFINE_TOP_K
    assert dq.GNINA_REFINE_TOP_K == GNINA_REFINE_TOP_K
    assert dq.GNINA_SECONDS_PER_LIGAND == 45


def test_budget_gnina_term_matches_reference_formula():
    import primerforge.docking_queue as dq

    def ref(n, seq_len, has_pdb):
        seq = 0 if has_pdb else int(0.25 * seq_len)
        return int(max(300, min(300 + 8 * n + seq + 45 * min(10, n), 900)))

    for n in (0, 1, 5, 10, 11, 30, 100):
        assert dq._job_timeout_seconds("A" * 100, n, False) == ref(n, 100, False)
        assert dq._job_timeout_seconds("", n, True) == ref(n, 0, True)


# ══════════════════════════════════════════════════════════════════════════
# 5. Honest consensus labelling (consensus_mode + score_source + metadata)
# ══════════════════════════════════════════════════════════════════════════

FAKE_PDB = (
    "ATOM      1  N   MET A   1       0.000   0.000   0.000  1.00 50.00           N\n"
    "ATOM      2  CA  MET A   1       1.458   0.000   0.000  1.00 50.00           C\n"
    "TER\nEND\n"
)


def _run_pipeline(monkeypatch, ligands, gnina_stub, probe=None):
    import primerforge.pipelines.consensus_pipeline as cp
    import primerforge.pipelines.docking_engine as de

    async def fake_esmfold(sequence, progress_callback=None):
        return {"status": "success", "tool": "test", "pdb_string": FAKE_PDB,
                "plddt_score": 88.0, "sequence_length": len(sequence)}

    async def fake_vina(receptor_pdb, ligand_smiles, exhaustiveness=8,
                        receptor_pdbqt_path=None, cpu=None, box=None):
        return {"binding_affinity": -5.0 - (sum(ord(c) for c in ligand_smiles) % 50) / 10.0,
                "computation_time": "1.0s",
                "structure": {"ligand": FAKE_PDB},
                "box": {"center": [1.0, 2.0, 3.0], "size": [25.0, 25.0, 25.0],
                        "source": "protein_centroid"}}

    async def noop_progress(stage, msg, metadata=None):
        return None

    def fake_pdbqt(receptor_pdb, output_path):
        with open(output_path, "w") as f:
            f.write("ATOM      1  C   UNL A   1       0.000   0.000   0.000  0.00  0.00     0.000 C\n")
        return True

    monkeypatch.setattr(cp, "esmfold_predict", fake_esmfold)
    monkeypatch.setattr(cp, "run_vina_docking", fake_vina)
    monkeypatch.setattr(de, "pdb_to_pdbqt", fake_pdbqt)
    monkeypatch.setattr(cp, "run_gnina_docking", gnina_stub)
    # Stub the availability probe as OK — these tests exercise the run path
    # with fake binaries; the real probe (test host may lack GNINA) would
    # legitimately skip stage 3 instead.
    # Stub the availability probe — these tests exercise the run path with
    # fake binaries; the real probe (test host may lack GNINA) would
    # legitimately skip stage 3 instead. A test can override via probe={...}.
    if probe is None:
        probe = {"ok": True, "path": "gnina", "version": "test", "reason": None}
    monkeypatch.setattr(cp, "gnina_available", lambda **kw: probe)

    return asyncio.run(cp.run_consensus_pipeline(
        "ACDEFGHIKLMNPQRSTVWY" * 2, ligands, top_n=len(ligands),
        progress_callback=noop_progress))


def _ok_gnina_factory():
    async def ok_gnina(receptor_pdb, ligand_smiles, exhaustiveness=4,
                       receptor_pdbqt_path=None, box=None):
        return {"binding_affinity": -8.0,
                "cnn_score": 0.83, "cnn_affinity": 3.28,
                "intramol_energy": -0.5, "poses": 9,
                "pose_table": [{"mode": 1, "affinity": -8.0, "intramol": -0.5,
                                "cnn_score": 0.83, "cnn_affinity": 3.28}],
                "computation_time": "12.0s",
                "structure": {"ligand": FAKE_PDB}}
    return ok_gnina


def test_consensus_mode_full_when_every_candidate_refined(monkeypatch):
    ligands = [f"CCCN{i}" for i in range(5)]  # ≤ top-K, all succeed
    result = _run_pipeline(monkeypatch, ligands, _ok_gnina_factory())
    s3 = result["stage3"]
    assert s3["consensus_mode"] == "full", s3
    assert s3["cnn_refined"] == 5
    assert s3["vina_only"] == 0
    ranked = result["ranked_results"]
    assert all(c["score_source"] == "consensus" for c in ranked)
    assert all(c["consensus_score"] == round(0.4 * c["vina_score"] + 0.6 * c["gnina_score"], 3)
               for c in ranked)
    # honest run metadata for the UI
    assert s3["consensus_weights"] == {"vina": 0.4, "gnina": 0.6}
    assert s3["refine_top_k"] == 10
    assert s3["gnina_exhaustiveness"] == 4
    assert s3["cnn_model"] == "crossdock_default2018"
    assert s3["computation_time"].endswith("s")


def test_consensus_mode_partial_when_topk_limit_hits(monkeypatch):
    ligands = [f"CCCN{i}" for i in range(15)]
    result = _run_pipeline(monkeypatch, ligands, _ok_gnina_factory())
    s3 = result["stage3"]
    assert s3["consensus_mode"] == "partial", s3
    assert s3["cnn_refined"] == 10
    assert s3["vina_only"] == 5
    ranked = result["ranked_results"]
    refined = [c for c in ranked if c.get("gnina_score") is not None]
    plain = [c for c in ranked if c.get("gnina_score") is None]
    assert len(refined) == 10 and len(plain) == 5
    assert all(c["score_source"] == "consensus" for c in refined)
    # Vina-only fallback: its "consensus" score IS the plain Vina score —
    # tagged honestly, never presented as a 2-method number.
    assert all(c["score_source"] == "vina" for c in plain)
    assert all(c["consensus_score"] == round(c["vina_score"], 3) for c in plain)


def test_consensus_mode_vina_only_when_gnina_absent(monkeypatch):
    ligands = [f"CCCN{i}" for i in range(4)]
    result = _run_pipeline(monkeypatch, ligands, gnina_stub=None)
    s3 = result["stage3"]
    assert s3["status"] == "skipped"
    assert s3["consensus_mode"] == "vina_only"
    assert s3["refined"] == 0
    ranked = result["ranked_results"]
    assert ranked and all(c["score_source"] == "vina" for c in ranked)
    assert all(c["consensus_score"] == round(c["vina_score"], 3) for c in ranked)


def test_consensus_mode_vina_only_when_all_refines_fail(monkeypatch):
    async def failing_gnina(receptor_pdb, ligand_smiles, exhaustiveness=4,
                            receptor_pdbqt_path=None, box=None):
        raise RuntimeError("per-ligand docking blew up")

    ligands = [f"CCCN{i}" for i in range(3)]
    result = _run_pipeline(monkeypatch, ligands, failing_gnina)
    s3 = result["stage3"]
    assert s3["consensus_mode"] == "vina_only"   # zero candidates got a CNN score
    assert s3["status"] == "gnina_failed"
    assert s3["failure_reasons"]
    assert all(c["score_source"] == "vina" for c in result["ranked_results"])


def test_refined_candidate_carries_honest_cnn_fields(monkeypatch):
    ligands = [f"CCCN{i}" for i in range(2)]
    result = _run_pipeline(monkeypatch, ligands, _ok_gnina_factory())
    c = result["ranked_results"][0]
    assert c["gnina_score"] == -8.0
    assert c["cnn_score"] == 0.83          # pose confidence 0-1 (was mislabeled)
    assert c["cnn_affinity"] == 3.28       # real CNNaffinity (was CNNscore)
    assert c["gnina_time"] == "12.0s"      # per-ligand timing for budget tuning
    assert c["pose_table"][0]["mode"] == 1
    assert c["status"] == "refined"


def test_stage2_exposes_run_parameters(monkeypatch):
    # ≤10 ligands = focused run → deeper search (exhaustiveness 8) — the
    # recorded value is whatever actually ran (Phase 2, task 2.5).
    ligands = [f"CCCN{i}" for i in range(3)]
    result = _run_pipeline(monkeypatch, ligands, _ok_gnina_factory())
    s2 = result["stage2"]
    assert s2["exhaustiveness"] == 8
    assert s2["computation_time"].endswith("s")
    # 2-atom fixture is below the detector's MIN_ATOMS → blind centroid box
    assert s2["box"] and s2["box"]["source"] == "protein_centroid"
    assert s2["box"]["size"] == [25.0, 25.0, 25.0]


def test_stage2_large_screen_keeps_shallow_exhaustiveness(monkeypatch):
    # >10 ligands = library screen → keep depth 2 (queue budget mirrors it)
    ligands = [f"CCCN{i}" for i in range(11)]
    result = _run_pipeline(monkeypatch, ligands, _ok_gnina_factory())
    assert result["stage2"]["exhaustiveness"] == 2


# ══════════════════════════════════════════════════════════════════════════
# gnina_available() pre-flight probe (same `--version` contract as the prod
# deploy gate): an unrunnable binary must read as NOT available — the
# pipeline then honestly SKIPS stage 3 instead of attempting (and failing)
# once per ligand. Covers the user-reported macOS case: a Linux x86-64
# ELF at /usr/local/bin/gnina (errno 8, exec format error).
# ══════════════════════════════════════════════════════════════════════════


def _probe(monkeypatch, tmp_path, body, name="gnina"):
    import primerforge.pipelines.docking_engine as de
    exe = tmp_path / name
    exe.write_text(body)
    exe.chmod(0o755)
    monkeypatch.setattr(de, "_resolve_gnina_bin", lambda: str(exe))
    monkeypatch.setattr(de, "_GNINA_PROBE_CACHE", None)
    return de


def test_gnina_probe_missing_binary(monkeypatch, tmp_path):
    de = _probe(monkeypatch, tmp_path, "#!/bin/sh\necho hi\n", name="unused")
    monkeypatch.setattr(de, "_resolve_gnina_bin", lambda: str(tmp_path / "nope"))
    out = de.gnina_available(force=True)
    assert out["ok"] is False
    assert "not installed" in out["reason"]


def test_gnina_probe_exec_format_error_reads_as_unavailable(monkeypatch, tmp_path):
    # 0x7fELF magic that is not a loadable ELF: execve fails with errno 8
    # (ENOEXEC) on macOS and Linux alike — exactly the user's Mac failure
    # with the official Linux-only GNINA binary.
    de = _probe(monkeypatch, tmp_path, "\x7fELF-garbage-not-runnable\n")
    out = de.gnina_available(force=True)
    assert out["ok"] is False
    assert "different OS/CPU" in out["reason"]


def test_gnina_probe_ok_script(monkeypatch, tmp_path):
    de = _probe(monkeypatch, tmp_path, "#!/bin/sh\necho 'gnina v1.1'\n")
    out = de.gnina_available(force=True)
    assert out["ok"] is True, out
    assert out["version"].startswith("gnina")


def test_gnina_probe_nonzero_exit_is_not_ok(monkeypatch, tmp_path):
    de = _probe(monkeypatch, tmp_path, "#!/bin/sh\necho boom >&2\nexit 3\n")
    out = de.gnina_available(force=True)
    assert out["ok"] is False
    assert "exit 3" in out["reason"] and "boom" in out["reason"]


def test_probe_failure_skips_stage3_without_any_attempt(monkeypatch):
    """No runnable GNINA in this environment → stage 3 SKIPPED (honest
    'not available', human reason), zero subprocess attempts, and the
    Vina-only ranking stays fully intact."""
    calls = {"n": 0}

    async def spy_gnina(receptor_pdb, ligand_smiles, exhaustiveness=4,
                        receptor_pdbqt_path=None, box=None):
        calls["n"] += 1
        raise AssertionError("probe said unavailable — must never be attempted")

    ligands = [f"CCCN{i}" for i in range(5)]
    probe = {"ok": False, "path": "gnina", "version": None,
             "reason": "GNINA binary is built for a different OS/CPU."}
    result = _run_pipeline(monkeypatch, ligands, spy_gnina, probe=probe)
    s3 = result["stage3"]
    assert s3["status"] == "skipped"
    assert s3["consensus_mode"] == "vina_only"
    assert "different OS/CPU" in s3["reason"]
    assert calls["n"] == 0
    ranked = result["ranked_results"]
    assert ranked and all(c["score_source"] == "vina" for c in ranked)
    assert all(c["consensus_score"] == round(c["vina_score"], 3) for c in ranked)
