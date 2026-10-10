# Docking Trust & Realism Program — Progress Tracker

> Started 2026-10-08. Local-only until approval: **no commit, no push** until user approves.
> Plan decided with user: ① install official CPU GNINA binary ② auto pocket detection + manual override
> ③ warn strongly, allow run ④ Phase 1 + demo fix first.

## 🚀 PROGRAM COMPLETE — COMMITTED 2026-10-11 (push pending user go)

All 4 releases + 9 user-run defect fixes + local GNINA (Docker) end-to-end
verification + final polish are done and committed in 4 logical commits:

| Commit | Contents |
|---|---|
| `295f3d20` | part 1/4 — backend, GNINA engine + CI `--version` gate |
| `9f14fc0e` | part 2/4 — frontend rendering (docking.html) |
| `966bd95d` | part 3/4 — regression suites (4 new test files) |
| (this) | part 4/4 — session records (AGENTS.md + progress.md) |

**Final gates (2026-10-11):** full pytest **590 passed / 4 failed** (= 588
baseline + 2 new severity-aware-recommendation tests; the 4 = pre-existing
`test_verification_fix` quartet, confirmed by name) · ruff 0 · rules_lint
0 err/529 · docking.html 4 JS blocks + 5 JSON-LD parse · all 5 UI probes
ALL PASS · real-run proofs: single-ligand DHFR+TMP consensus −7.278
(0.4×−7.65 + 0.6×−7.03 verified) and 5-ligand screen 5/5 CNN-refined with
TMP ranked #1 · Docker-down degradation = clean skip card with human reason.

**Final polish on top of the program (2026-10-11):** "1 molecule" / "All 1
top ligand" singulars · Best-GNINA hero tile 1 dp → 2 dp · severity-aware
`_docking_recommendation()` (suitable-but-critical structures no longer say
"Minor issues"; helper extracted + 2 regression tests).

**Remaining (not blocking):** ① `git push` → CI deploys → prod GNINA v1.1
install + `--version` gate + live E2E (awaiting user go) ② user
acknowledgment of the GNINA v1.3.2 → **v1.1** deviation (v1.3.x links CUDA
libs; cannot load on the GPU-less t3.large) ③ EC2 sizing verdict delivered:
t3.large + 30 GB gp3 is enough to launch; never resize to Graviton/ARM
(GNINA binary is x86-64 only); m6i.large/c6i.xlarge are the upgrades when
sustained docking load demands it.

---

## Status legend
`⬜ not started` · `🔁 in progress` · `✅ done (local gates green)` · `🚀 deployed & live-verified`

---

## Release 1 — Phase 1: GNINA repair + honest numbers + real demo ✅ (local gates green, 2026-10-08)

| # | Task | Files | Status |
|---|------|-------|--------|
| 1.1 | CI/CD installs official GNINA CPU binary → `primerforge/pipelines/bin/gnina` (cached, `.gnina_ver` stamp, disk ≥4000 MB guard) + **hard `--version` execution gate** (no pipe, fails deploy loudly if binary won't run) + `.gitignore` entry — ⚠️ **version v1.3.2 → v1.1 (deviation, see findings)** | `.github/workflows/deploy.yml`, `.gitignore` | ✅ |
| 1.2 | Fix memory trap: `docking_worker.py` RLIMIT_AS **soft-only** 600 MB (hard untouched → children inherit raisable soft); GNINA fork window = `_lift_address_space_limit`/`_restore_address_space_limit` (direct exec, `finally`-restored — preserves ENOEXEC/ENOENT fail-fast semantics) | `primerforge/docking_worker.py`, `docking_engine.py` | ✅ |
| 1.3 | Fix GNINA stdout parser: new `_parse_gnina_stdout()` — header/row-driven, 5-column table (mode/affinity/intramol/CNNscore/CNNaffinity), ValueError on no-table, no fabricated values; honest return (`cnn_score` 0–1, real `cnn_affinity` log mol/L, `intramol_energy`, `poses`, `pose_table`, guarded `confidence`, `box`); bare `--cnn_scoring` → **`--cnn_scoring=rescore` + `--cnn crossdock_default2018`** (both forms live-verified on real v1.1 binary) | `docking_engine.py` | ✅ |
| 1.4 | Honest consensus: `consensus_mode` full/partial/vina_only + per-candidate `score_source` (vina fallback = `consensus_score == vina_score`, tagged "vina", never sold as 2-method); stage3 metadata (`cnn_refined`, `consensus_weights`, `refine_top_k`, `gnina_exhaustiveness`, `cnn_model`, `computation_time`); UI mode chip + **fixed `hasGnina = status!=='skipped'` bug** (`gnina_failed` no longer claims "CNN re-scored"), failure_reasons surfaced in stage-3 card, data-driven table columns, CSV `Score_Source`/`Consensus_Mode`/CNN cols, viewer label + PDB REMARK + structure routes carry `cnn_score`/`cnn_affinity`/`score_source` | `consensus_pipeline.py`, `frontend/docking.html`, `primer_server.py` | ✅ |
| 1.5 | Full value surface: stage-2 rows (exhaustiveness, blind box size+centroid, screening time), stage-3 rows (CNN model, redock exhaustiveness+top-K, refinement time), CNN pose score + CNN affinity in summary/best/table/viewer/CSV/PDB-REMARK, honest interpretation guide (log mol/L ≠ measured Ki; pLDDT tiers incl. 50–69 caution), **50–69 pLDDT caution card** (warn strongly, allow run) | `frontend/docking.html` | ✅ |
| 1.6 | Real demo: **E. coli K-12 DHFR (UniProt P0ABQ4, 159 aa, fetched 2026-10-08) + trimethoprim (PubChem CID 5578, SMILES verified via PUG-REST + rdkit embed)** replaces 71-aa fragment + aspirin; button label + top-N description made honest ("GNINA re-scores the best 10") | `frontend/docking.html` | ✅ |

**Phase 1 gates — ALL GREEN (local):** ruff (CI scope) `All checks passed!` · py_compile ✓ · **full pytest 509 passed / 4 failed** (= baseline 493 + **16 new** in `tests/test_gnina_phase1.py`; failures = pre-existing `test_verification_fix` quartet only) · rules_lint **0 err**/529 · node --check **4/4 inline blocks** + JSON-LD parse ✓ · workflow YAML + `bash -n` on every run-block ✓ · **local E2E harness: ALL PASS** (resume mid-run, stop, guard, re-render; 0 unexpected console errors) — local exercises the `gnina_failed → Vina-only chip` honest path (macOS can't execute the Linux ELF) · no commit/push.

**Phase 1 findings & deviations (all empirical):**
- ⚠️ **GNINA v1.3.2 → v1.1 (deviation from approved plan — needs user acknowledgment)**: ELF NEEDED probe on v1.3.x shows `libcudnn/libcudart/cublas/cufft/cusparse/cusolver` → cannot load on GPU-less t3.large; **v1.1 has zero CUDA deps**, same 5-column stdout table, same `--cnn_scoring=rescore` token (all live-verified via Docker linux/x86_64 on the official release binary). URL: `https://github.com/gnina/gnina/releases/download/v1.1/gnina`.
- **Timing (same receptor+ligand, x86_64 emulation)**: search-only exh=4 **12 s** · default 3-model CNN ensemble rescore **246 s** · single-model `crossdock_default2018` rescore **37 s** (6.6×) → stage-3 uses **single model** (authors' own startup warning recommends it on CPU) + `STAGE3_GNINA_EXHAUSTIVENESS=4`, budget **`+45 s × min(10, n)`** in `_job_timeout_seconds` (clamp 300–900 kept), per-candidate `gnina_time` recorded for tuning against first prod runs.
- **meeko 0.7.1 declares ZERO deps** but imports `scipy` (ligand prep) + `gemmi` (polymer) at runtime; declared nowhere → fresh venv = **every docking job dies** (hit locally during E2E: `Docking error: No module named 'scipy'`). **Fixed**: `requirements.txt` += `scipy>=1.8`, `gemmi>=0.4` with provenance comment. Prod venv already has both (live dockings work) — next deploy just pins them for future rebuilds.
- Local venv drift (not code): `prometheus_client` was missing → 2 metrics tests failed on first full run; installed per declared pin → suite back to 4-failure baseline.
- macOS quirk documented in tests: kernel rejects any finite `RLIMIT_AS` (`ValueError`) → worker guard is a no-op there by design; tests are capability-aware (full assertions on Linux CI).

---

## Release 2 — Phase 4: Protein validation ("broken or perfect")

| # | Task | Files | Status |
|---|------|-------|--------|
| 4.1 | Wire `broken_protein_analyzer.analyze_protein()` at stage 1 for every predicted/uploaded structure; store report in job result | `consensus_pipeline.py` | ✅ |
| 4.2 | Quality badge Good/Usable/Poor + prominent "indicative only" banner when pLDDT < 50 / Poor; caution note 50–70; run always proceeds (user decision: warn, allow) | `frontend/docking.html` | ✅ |
| 4.3 | PDB-upload pre-validation + "Repair structure" offer via `regenerative_folder.py` | `consensus_pipeline.py`, UI | ✅ |
| 4.4 | Per-region pLDDT table (which part of protein is trustworthy) | `frontend/docking.html` | ✅ |
| 4.5 | Tests with broken fixtures (truncated chain, clipped atoms, clashes) | `tests/` | ✅ |

**Phase 4 gates — ALL GREEN (local):** ruff (CI scope) `All checks passed!` · py_compile ✓ · **full pytest 532 passed / 4 failed** (= Phase-1 baseline 509 + **23 new** in `tests/test_protein_validation.py`; failures = pre-existing `test_verification_fix` quartet only) · rules_lint **0 err**/529 · node --check **4/4 inline blocks** + JSON-LD ✓ · **local API probes**: ① 1-residue PDB → **400** (not queued, token not burned) ② sequence-mode run → `stage1.quality` in status (**verdict poor / grade D / 8 regions / totals+truncation / repair_suggested**, `pdb_string` stripped) ③ PDB-upload run → `mode:"upload"` + `plddt_source:"prediction"` (mean 95 → verdict good) · **local UI probe `/tmp/dock_quality_ui.py`: ALL 52 CHECKS PASSED** (poor→fail-card+INDICATIVE ONLY+verdict badge+Defects row+8 proportional strip segments+8-row regions table+repair button; good→pass-card+recommendation+no repair; usable→amber caution only; legacy result→clean render; repair flow: guard error→real `/docking/regenerate`→download+re-run buttons→rerun switches to pdb mode; **0 JS exceptions**) · **local E2E `/tmp/dock_e2e_resume.py`: ALL PASS** (28/28 — real submit, mid-run reload resume, quality "Poor" badge on completed run, stop, duplicate guard, 0 unexpected console errors) · no commit/push.

**Phase 4 notes:** analyzer wired behind guarded import (`_QUALITY_IMPORT_ERROR` → `verdict:"unknown"`, run always proceeds — warn, allow) · pLDDT source honesty: `esmfold` (per-residue) / `prediction` (AlphaFold/ESMFOLD headers or no CRYST1) / `b_factor_estimate` (experimental, 100−B/2) / `unavailable` (neutral 70, UI hides the number) · fallback-helix residue numbering fixed (`{i+1}` — was every residue numbered 1) · defect lists capped (40/20/20/20) with pre-truncation `totals` authoritative for UI counts · repair offered only when gaps/clashes > 0 · queue result keeps `quality`; status route pops only `pdb_string`.

---

## Release 3 — Phase 2: Real docking (pocket-centered box)

| # | Task | Files | Status |
|---|------|-------|--------|
| 2.1 | Wire `pocket_detector.py` into stage 2 → pocket-centered box; fallback centroid box labeled "blind docking (whole protein)"; persist `box{center,size,source,pocket_id,druggability}` in job result | `consensus_pipeline.py`, `docking_engine.py` | ✅ |
| 2.2 | Manual override: advanced panel center/size/residue range via existing `/gridbox` route | `frontend/docking.html` | ✅ |
| 2.3 | Wire `protein_preparer.py` for PDB uploads (waters/ions/protonation) + "what was removed" report | `consensus_pipeline.py` | ✅ |
| 2.4 | Draw docking box + detected pocket in 3D viewer | `frontend/docking.html` | ✅ |
| 2.5 | Exhaustiveness: stage 2 = 2 → 8 for ≤10 ligands (keep 2 for big screens); record actual value in results | `consensus_pipeline.py:218` | ✅ |

---

## Release 4 — Phase 3 + 5: 3D viewer upgrade + efficiency metrics

| # | Task | Files | Status |
|---|------|-------|--------|
| 3.1 | Fullscreen/expanded viewer overlay, larger default, resizable, controls inside | `frontend/docking.html` | ✅ |
| 3.2 | Style controls: cartoon/surface/lines; stick/spacefill/ball-and-stick; color spectrum/chain/**per-residue pLDDT** | `frontend/docking.html` | ✅ |
| 3.3 | Interaction overlays from `interaction_analyzer`: H-bond dashes, hydrophobic, salt bridges, π-stacking, labeled contact residues + distances; measurement tool | `frontend/docking.html` | ✅ |
| 3.4 | Pose carousel prev/next, zoom-to-ligand, spin, snapshot PNG; 2D interaction diagram beside 3D | `frontend/docking.html` | ✅ |
| 5.1 | Wire `advanced_scoring.analyze_poses()` post-run: LE, LLE, BEI, pose clusters/RMSD, pLDDT-weighted confidence per ligand | `consensus_pipeline.py`, UI | ✅ |
| 5.2 | Interaction summary per ligand in ranked table | `frontend/docking.html` | ✅ |
| 5.3 | Downloads: full-complex PDB, interactions JSON, quality report, complete score CSV/JSON | `frontend/docking.html` | ✅ |

**Release 4 verification (2026-10-10)**: backend `_attach_metrics` (hooks at both success returns, stage-3 structure fallback, warn-allow contract) — `tests/test_efficiency_metrics.py` **10/10** (incl. new PDB-ligand fallback regression); viewer/metrics UI probe `/tmp/dock_viewer_ui.py` **71/71, 0 console errors** (canvas snapshot visually verified: rainbow cartoon + salmon ligand); box probe ALL PASS; quality probe ALL PASS (fixtures repointed at `b4dc3a68495e`, A8/D3 checks made fixture-derived — old checks hardcoded the purged fixture's pLDDT 58% and matched "decision-grade" inside the INDICATIVE banner); local E2E **28/28 ALL PASS**. **Real bug found & fixed**: `interaction_analyzer.analyze_interactions` couldn't parse PDB-format ligands (vina-only runs store the pose as PDB, no `$$$$`) → silently analysed a DUMMY atom at origin → **zero contacts for every non-GNINA pose** (both `_attach_metrics` and the client on-demand POST) — now falls back to `_parse_pdb_atoms` (fixture probe: 0 → **11 real interactions**, 5 H-bonds + 6 hydrophobic). Gates: ruff (CI scope) 0 · full pytest **577 passed / 4 failed** (baseline 567/4 + 10 new; failures = pre-existing `test_verification_fix` quartet) · rules_lint 0 err/529 · node --check 4 blocks 0 err.

---

## Audit facts (verified in code, 2026-10-08)

- **6 stacked GNINA bugs (all proven, all fixed in Phase 1)**: (1) prod binary `Exec format error` (no `pipelines/bin/` in repo, PATH binary broken → now CI-installed + `--version` deploy gate); (2) parser takes `parts[5]` = CNNscore (0–1 pose confidence) and mislabels it `cnn_affinity`, discards `parts[6]` = CNNaffinity (real DL affinity) + all RMSDs; (3) `docking_worker.py` RLIMIT_AS hard 600 MB inherited by children → GNINA libtorch (~1–3 GB) would OOM — box is **t3.large, 8 GB** (verified via AWS CLI); (4) fallback `g = gnina or vina` (`consensus_pipeline.py`) made "Consensus" = Vina exactly (screenshot artifact −5.35 vs −5.351); (5) old parser required `len(parts) >= 6` but the real table has **5** tokens/row → never matched, no results ever parsed; (6) bare `--cnn_scoring --out <path>` → boost value<> enum eats `--out` → `Command line parse error`, **exit 1** (reproduced on the real binary).
- **Search box = whole-protein geometric center** (`_compute_box_center`, `docking_engine.py:13`) = blind docking at centroid; stage 2 hard-codes `exhaustiveness=2` (`consensus_pipeline.py:218`); GNINA runs at 4.
- **Unwired engines with live routes**: `broken_protein_analyzer.py` (655 l) `/docking/analyze` · `interaction_analyzer.py` (607) `/docking/interactions` · `advanced_scoring.py` (415) `/docking/analyze-poses` · `regenerative_folder.py` (723) `/docking/regenerate` · `pocket_detector.py` (384) `/docking/pockets` · `protein_preparer.py` (443) `/docking/prepare` · `/gridbox` · `/full-prep` — **none called by the consensus pipeline or docking.html results UI**.
- **3D viewer today**: small fixed container, cartoon+sticks only, no fullscreen/surfaces/interaction labels/pLDDT coloring/box visualization.
- **GNINA binary source (Phase 1, deviated)**: `https://github.com/gnina/gnina/releases/download/v1.1/gnina` — official CPU build, **v1.1 chosen over plan's v1.3.2 because v1.3.x links CUDA libs (libcudnn/libcudart/…) and cannot load on the GPU-less box** (ELF NEEDED probe); v1.1 zero CUDA deps, same stdout table/flags (live-verified in Docker linux/x86_64).
- Existing E2E harnesses: `/tmp/dock_e2e_resume.py` (28 checks), `/tmp/dock_submit_error_ui.py` (36 checks); prod admin token `/tmp/vl_prod_token.txt`, local `/tmp/vl_local_token.txt`.

## Constraints

- **No git commit, no git push until user approval.** Local changes only.
- Never commit: `bandit-report.json`, `docking_queue/`, `deploy/aws/sync-frontend.sh`.
- Repo is public — no tokens/secrets in code or logs.
- Pre-existing test failures: `test_verification_fix` quartet (4) — not ours.
