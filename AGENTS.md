# AGENTS.md — Agent Handoff & Tracking

**Session (latest):** **Docking capacity/speed/robustness — 🟢 LIVE + E2E VERIFIED 2026-10-07 (commits `9c6864c0` + test fix `c4d81feb`, both pushed with the earlier `bb2316e3`; CI run `37659382813` FULLY GREEN; user: "make our system more robust with maximum ligand binding and maximum protein sequence for docking and also increase speed of response"):** **Capacity** — ligand cap **50→100** (route validation + pipeline + frontend) with SMILES normalize/dedupe; **removed the silent `[:5]` truncation in BOTH `docking_queue._process_job` and `docking_worker.main`** (a submitted 100-ligand library was actually docking only 5!); `top_n` clamped 1–100; **sequence mode capped at 400 aa** — `esmfold_engine.MAX_SEQUENCE_LENGTH = 400`, empirically binary-search probed against the free ESMFold web API **today: L=400 → HTTP 200 (27s), L=403/406/412/425/450/500/1000/2000 → HTTP 413** (the old frontend "2000 aa" promise was unreachable — those runs silently fell back to a fake helix); route now rejects early with "…supports up to 400 amino acids. For longer proteins, upload the protein PDB file instead (PDB tab)" — **PDB-upload mode has no length cap** (skips folding) and gained server-side validation: ≤5MB + ATOM-record sanity. **Speed** — ① **structure cache** keyed by seq SHA-256 in `docking_queue/structure_cache/` (7d TTL, 200 entries, **fallback helix never cached**, atomic writes): repeat job **70s → 15.0s**, live-proven with `[served from structure cache]` marker; ② **Vina 2 parallel lanes** (`min(2, cpu_count)` semaphore × `--cpu cores/2` per child — vina's default `--cpu 0` = all cores, verified from `vina --help`) instead of serial; ③ **GNINA refines only top-K=10** by Vina score (rest rank via g=v fallback) + **fail-fast on binary-level errors** (FileNotFoundError/errno 8/13/"Exec format"/"Permission denied"/"No such file" checked INSIDE the semaphore — gather pre-check would race) — prod GNINA previously re-attempted a never-runnable binary per candidate; ④ queue poll **5s→1s** (`start_local_worker(interval=1.0)`), frontend poll **3s→2s** with attempts 180→500 (~17 min, covers job budget), ⑤ **dynamic job timeout** `clamp(300 + 8×ligands + 0.25×residues, 300, 900)` (PDB mode skips residue term) replacing flat 300s — log shows budgets (60aa→323s, 400aa→408s). **Robustness** — worker **heartbeat thread** (`os.utime` running file every 20s; stopped in `finally`) so >5-min jobs are never stale-released & double-run (release_stale fires on RUNNING mtime); `TimeoutExpired` → actionable failure ("Docking timed out after N minutes. Try fewer ligands (≤100)…") instead of "Internal worker error"; worker crash (rc≠0) → **failed with exit code + stderr tail** (was: infinite 5-min requeue loop); MemoryError copy updated (no more "need GPU instance"); RAM-precheck message de-GPU'd; `docking_worker.write_result` now honors `DOCKING_QUEUE_DIR` env. **Gates**: ruff 0 · py_compile · targeted **39/39** (19 new in `tests/test_docking_scaling.py`) · full pytest **471 passed / 4 failed = pre-existing `test_verification_fix` quartet** · rules_lint **0 err/529** · FAQ mirror **Q0/A0** · residual old-cap strings 0 · live local probes (401→400, 101-lig→400, bad AA→400, 400-aa→202, top_n 999→clamped) · real 400-aa job **completed 70s** (plddt 77.41, stage3 `gnina_failed: "[Errno 8] Exec format error: 'gnina'"` surfaced — fail-fast 1 attempt) · headless E2E **13/13 ×2 local, 0 console errors**. **CI incident fixed**: first run `37658689241` FAILED — heartbeat test's `from primerforge import docking_worker` executes `resource.setrlimit(RLIMIT_AS, 600MB)` at import; **Linux enforces it (macOS ignores it)** → pytest process address space capped → `Thread.start()` wedged → 30s pytest-timeout; fix `c4d81feb` = monkeypatch `resource.setrlimit` to no-op **before** first import (right for its standalone subprocess role, never for pytest). **Deploy**: sync-frontend.sh (docking.html, bucket **852**) + invalidation `I9T3NVT48ULE3Q0JHGL4RCLJ6K` Completed → live static **byte-identical**; **prod verification**: validation 400s with new messages ✓ · **live headless E2E ×2 ALL PASS, 0 console errors, 28s** (real web-API fold pLDDT 41% + honest low-confidence warning, Vina −4.81, WebGL canvas 23.2% non-bg / 9,403 colors, rank switch, downloads) — first prod fold also proves the GPU-less prod path end-to-end. **Still true**: prod GNINA broken (reason now visible in stage3 for diagnosis) · local `obabel` still missing (brew install no-op'd; non-blocking — prod has it) · pre-existing: `queue/*` unauthenticated, `REDIS_URL` absent → limiter per-worker, `pages-build-deployment` failures = GitHub Pages.

**Prior session:** **Molecular docking pipeline fixes — no-GPU cloud design + 3D render reliability + rate-limit audit — 2026-10-07 (user: "make docking work with proper 3D data rendering / we do not have GPU on cloud / cross check rate limiting / then commit"):** ① `docking_engine.py` — `_mol_from_pdb()` clash-tolerant receptor parse (sanitize → retry → drop ONLY spurious inter-residue non-backbone bonds; peptide C-N + disulfide SG-SG kept → Vina geometry/coordinates exact; was: RDKit proximity bonding on low-confidence sidechain clashes → sanitize raise → whole job aborted) + single-pose ligand-viewer fallback (Vina PDBQT model 1 only — concatenating all 9 models' ATOM lines garbled 3Dmol); ② `esmfold_engine.py` — pLDDT read from B-factor **cols 61-66** (was occupancy cols 55-60 → always 1.00 → frontend showed false "100%"), 0-1 fraction → percent, **no-GPU guard `_local_gpu_available()`**: GPU-less hosts NEVER load local ESMFold (8.4GB download + >10GB RAM = OOM the whole box + >300s job timeout on CPU; local `import torch` fails anyway today) → free ESMFold web API (remote GPU) with ONE fast **429/5xx retry** (`_ESMFOLD_RETRY_DELAY_S=15`; hard timeouts never retry — 2×180s > 300s budget) → honest helical fallback (plddt 0 + UI warning); module docstring updated (stale "no API calls / offline"); ③ `consensus_pipeline.py` — GNINA exceptions surface as `stage3.failure_reasons` (≤5, `status: gnina_failed`, WARNING) so prod GNINA breakage (exec-format-error, invisible pre-fix) is diagnosable via status API without SSH + stage-1 mode message fixed (was "Local GPU Inference on CPU"); ④ `tests/test_docking_fixes.py` — **20 regression tests**. **Rate-limit audit**: consensus **5/min/IP** (unit test + live probe: 5×400 validation → 6th **429 `RATE_LIMITED`**), `status`/`structure/batch` polling deliberately unthrottled (12× no 429 — the 3D viewer's 2s poll + post-completion fetch must never throttle), global 200/min default covers the rest, flask-limiter 3.8.0 active. **Pre-existing findings (follow-up, not this commit)**: `queue/*` routes unauthenticated + never drained (external-Azure-worker leftovers over `persistent_queue` sqlite); `REDIS_URL` not in deploy → limiter counters are per-gunicorn-worker memory (limits ≈ ×workers, not shared). **Gates**: ruff 0 · py_compile · targeted **20/20** · full pytest **452 passed / 4 failed = pre-existing `test_verification_fix` quartet** · rules_lint **0 err/529** · headless E2E **13/13, 0 console errors** (vina −5.0, real pLDDT 41% w/ low-confidence warning, viewer canvas 23.2% non-bg / 9,296 colors, rank switch, downloads; screenshots `/tmp/dock_e2e_*.png` inspected: spectrum cartoon + salmon ligand in protein core) · live rate probe ✓. obabel still compiling locally (prod-parity multi-record SDF E2E queued, non-blocking — prod obabel+vina proven job `78783aefa162`); local E2E = Vina-only (no macOS gnina) which mirrors prod degradation.

**Prior session (CMS content import + media upload→S3):** **CMS CONTENT IMPORT + MEDIA UPLOAD→S3 — 🟢 LIVE + E2E VERIFIED 2026-10-06 (commits `68d96285` (converter + table renderer) + `f7bd99c1` (S3 storage); CI runs `37491016453` + `37494879150` both FULLY GREEN; user: "go to next step" = the follow-up the CMS-login phase queued):** **① Content import — all 305 static pages now published in the CMS** (90 `frontend/blog/` + 215 `frontend/glossary/`, index files skipped): `backend/import_blogs_to_cms.py` rewritten as a stdlib-`HTMLParser` tree converter — `<main>` extraction (28 no-`<main>` files = redirect stubs → body w/ chrome dropped), chrome drop sets (nav/footer/aside/iframe/noscript/button/form/svg/script/style + `.toc`/`.article-meta-bar`/`.author-bio`/`#mobile-menu`), **all `<h1>` dropped** (title field carries it), **h4–h6→h3** (editor schema = heading levels `[2,3]` only), meta-description lead paragraph dropped, full fidelity: a→link mark (href guard vs `javascript:`/`data:`), strong/em/u/s/code marks, bullet/ordered lists, blockquote, **codeBlock = ONE text node with `\n`** (hardBreak invalid there), horizontalRule, **table/tableRow/tableHeader/tableCell incl. colspan/rowspan**, `<details>` FAQ→bold-Q paragraph + answers, sup/sub→unicode superscripts, `<p>`-nested img/figure split into image nodes, **no empty text nodes** (final `scrub()` — known editor breaker), idempotent (**409→EXISTS**, exit 0), `--dry-run`/`--limit`, env creds (`CMS_ADMIN_*` + `CMS_URL`, dead JWT_SECRET requirement removed). **② Renderer gap fixed** (`backend/routes/pages.py`): `_render_node` had **no table cases → returned `""` (tables silently dropped on render)** and text/attribute nodes were **unescaped** → + table family (colspan/rowspan→`th`/`td`) + `html.escape` on text + image/link attrs. **Validation ladder**: offline **305/305, 0 schema errors**, word-recall fidelity mean **0.944** (low tail = 28 redirect stubs where dropped-H1 words dominate) · local E2E **18/18** (`/tmp/vl_import_e2e.py` :8011 fresh sqlite: import, admin+public API, details-flattening, idempotent re-run) · gates ruff 0 · rules_lint 0 err · pytest **423/4 = baseline**. **Prod wrinkle (important for next time)**: first live import `305/0/0` but prod ran the OLD renderer → `content_json` had tables, `content_html` didn't; **`DELETE /pages/{slug}` is a SOFT-delete (status→`archived`)** and **`update_page` downgrades published→draft and cannot re-publish** → the correct re-render path = **restore→submit→approve** (`approve_page` re-renders `content_html` from `content_json`) → **305 republished in 104 s, 0 errors** → **live verify 13/13** (public total **305**; pcr-steps `<table>`+link+`<strong>`+`<ul>` present, h2-only, chrome-free; admin 305 published; split **90 blog / 215 glossary**; adme `<details>` flattened; public HTML bleach-sanitized) + **headless UI ALL PASS `statTotal='305'`, 0 console errors**. Side-effect: the workflow created **~610 CMS notifications — inert** (frontend calls no `/notifications` endpoint; API has mark-read, no delete). **③ Media upload → S3 (root cause: uploads wrote local disk under gitignored `frontend/uploads/cms/` while CloudFront's default origin IS the `vigyanllm-frontend` bucket → every `/uploads/cms/…` URL 404'd in prod)**: new **`backend/storage.py`** single write-path for `routes/upload.py` + `routes/media.py` — **PutObject** to `uploads/cms/YYYY/MM/` (`ContentType` = detected MIME so images render inline, `CacheControl public, max-age=31536000, immutable` — uuid-prefixed names), **local-disk fallback when `S3_BUCKET` unset (dev)**, failed writes raise `StorageError` → **HTTP 502** (loud — never a URL that would 404), `remove()` best-effort (DeleteObject/unlink; ignores non-`/uploads/cms/` URLs); `backend/requirements.txt += boto3==1.43.108` (py3-none-any; box venv py3.14); `deploy.yml` `.env += S3_BUCKET=vigyanllm-frontend, S3_BUCKET_REGION=ap-south-1, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY`. **Credentials investigated per plan**: box **no instance profile (`IamInstanceProfile: null`)**, no AWS keys in gh secrets → gh secrets **`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`** set from local `~/.aws` `vigyanllm-deploy` key (values piped to `gh secret set`, never printed; AWS secret charset `[A-Za-z0-9+/=]` = GH-interpolation safe) — key **probed Put/Get/DeleteObject on the bucket ✓**; that key has **no `iam:*`** → cannot mint a scoped least-privilege user from CLI (console-side key = optional follow-up; trust model unchanged — `EC2_SSH_KEY` already lives in gh secrets); boto3 default chain reads process env, CMS unit already `EnvironmentFile=/home/ubuntu/vigyanpilot/.env` **and restarts every deploy** ✓; bucket = versioned, ap-south-1, all public-access blocks true, policy allows only CF OAC `GetObject` (uploads via IAM identity; serving via CF unchanged, no invalidation needed). **Live media E2E all pass**: login → **POST upload 200** → `s3api head-object` **ContentType image/png** → **CloudFront GET 200, bytes identical (70 B)** → 2nd upload → `DELETE /media/{id}` 200 → **S3 head 404** → **CloudFront 404** → cleanup → **media library total 0**. **Gates (media)**: ruff (CI scope) 0 · **bandit 0 HIGH/CRITICAL** · rules_lint 0 err · **pytest 432 passed / 4 failed = 423 baseline + 9 new** (`tests/test_storage.py`) · workflow YAML parses. **Still true**: static site remains canonical for SEO (CMS = JSON API for editing); follow-ups = optional console-side scoped IAM key, ~610 inert notification rows, content editing now possible in `/cms-admin`.

**Prior session (production CMS login):** **PRODUCTION CMS LOGIN ENABLED — 🟢 LIVE + E2E VERIFIED 2026-10-06 (commits `d77577c5` + `df4931ba`, CI run `37483239939` FULLY GREEN; user selected the "Enable production CMS login" phase):** 7 files: ① `backend/main.py` — `_seed_admin()` now **env-driven** (`CMS_ADMIN_EMAIL`/`CMS_ADMIN_PASSWORD` read from `.env`; create-or-**rotate** on hash mismatch ⇒ changing the GH secret rotates the credential; **no credential in code/logs** — the old hardcoded `_seed_admin()` credential was removed in `d77577c5` (rotated away; live-proven 401), skips with a warning when unset) + new `GET /health`; ② `backend/routes/auth.py` — in-memory **login throttle** (5 fails/account + 20/source-IP per 15-min sliding window → **429**, XFF-first client IP, success resets; single uvicorn worker keeps state consistent) + hardened `_pw_ok` (None/''/malformed hash → 401, never 500); ③ `backend/requirements.txt` — **first CI attempt `37481594359` FAILED before touching any live service**: box venv = **Python 3.14**, `pydantic 2.9.0`'s core 2.23 has no cp314 wheel → pyo3 source build rejected 3.14; fixed in `df4931ba` by aligning every pin to the **locally E2E-proven stack** (fastapi 0.131.0, uvicorn 0.41.0, sqlalchemy 2.0.48, pydantic 2.13.5→core 2.46.5 cp314, python-jose 3.5.0, python-multipart 0.0.22, aiofiles 25.1.0; psycopg2-binary/bcrypt identical to root ⇒ no downgrade), verified with pip cross-resolution for cp314+manylinux x86_64 (**23/23 wheels**); ④ **new** `deploy/vigyan-cms.service` (uvicorn **127.0.0.1:8001**, `--workers 1` on purpose, `PYTHONPATH=backend:repo-root` so backend top-levels + `primerforge` both resolve, EnvironmentFile `.env`, hardening mirrors `vigyan.service`); ⑤ `deploy/deploy-nginx-ec2.sh` — dropped `allow 127.0.0.1; deny all` from `/api/v1/cms/` (CMS enforces its own Bearer-JWT + `require_admin`; login rate-limited in-app); script now **CI-run every deploy** (idempotent, `nginx -t` gated — was "run once"); ⑥ `deploy/aws/cloudfront-functions/viewer-request.js` — **v14: `/cms-admin` removed from the edge 403** (`/admin`, `/admin-reviews`, `/admin/` stay blocked); **updated + `publish-function` to LIVE BEFORE the push** (this CLI build: `update-function --function-code fileb://…` — `file://` expects base64 and plain string args are ASCII-gated); LIVE code byte-compared to repo ✓; ⑦ `.github/workflows/deploy.yml` — install `backend/requirements.txt`; `.env += JWT_SECRET, CMS_ADMIN_EMAIL, CMS_ADMIN_PASSWORD, MAIN_API_URL=http://127.0.0.1:11436/api`; install+enable CMS unit; **port-takeover** `pkill -f 'uvicorn.*8001'` → restart → `:8001/health` gate → **localhost credential login gate** (JSON built from `.env`; status/keys only — token & secret never logged) → nginx deploy; CloudFront step gates: **`/cms-admin` 200** + **full live login chain** (POST login → Bearer GET `/api/v1/cms/pages`, token never printed). **gh secrets set**: `JWT_SECRET` (generated, never printed), `CMS_ADMIN_EMAIL=contact@vigyanllm.in`, `CMS_ADMIN_PASSWORD` (22-char `validate_password`-compliant, charset excludes `' " $ ` \ # %` + space → safe for GH single-quote interpolation, bash printf, systemd EnvironmentFile; **value shown to the user in chat only — never in the repo**). **Gates**: local E2E **13/13** (`/tmp/vl_cms_e2e.py`, :8011+sqlite: health, login+token, authorized read, anon 401, throttle 429 incl. correct-while-locked, **rotation** old→401/new→200, boot without env) · ruff 0 · py_compile · `node --check` viewer-request · `bash -n` all 11 workflow run-blocks + embedded python · rules_lint **0 err** · pytest **423/4 = baseline**. **CI `37483239939` FULLY GREEN** (every new gate OK: `CMS :8001 healthy` / `login gate passed` / `nginx config deployed` / `live CMS chain OK`). **Live verification**: login chain **200 tokenlen=249** · Bearer pages **200** · no-token 401 · wrong 401 · **old repo credential 401 (rotated)** · same-email throttle **5×401→429** · real account still loginable after probes (email 2/5, IP 14/20) · `/admin` **403** · `/admin-security` **200** · `/cms-admin` **200 byte-identical to local (67,661 B)** · `/cms-login` 200 · edge `/health` 200 · pricing `USD [0,999,8900,4900,39900]` · **headless UI E2E 5/5, 0 console errors** (T&C gate blocks first → real login → `/cms-admin`, sidebar `CMS Admin / contact@vigyanllm.in`, `statTotal` fetched via Bearer; screenshot `/tmp/cms_login_ui.png`). **Follow-ups (not this phase)**: CMS DB is **fresh/empty (0 pages)** — content import (`import_static_blogs.py`/`import_blogs_to_cms.py`) + media-upload-to-S3 next; password rotation = edit GH secret → next deploy auto-rotates; throttle state is in-memory (resets on restart); `pages-build-deployment` failures are GitHub Pages, unrelated.

**Prior session (staff entry buttons round 2):** **Staff entry buttons ROUND 2 — sign-in modal + signup 🟢 LIVE + VERIFIED 2026-10-05 (commit `e4ab824e`; user: "till now both buttons are not visible / makes them visible on frontend / after that tell me where they are present"):** Root cause = the nav **"Sign in"/"Get started" opens the auth MODAL (`openAuthModal()`), not `/login`** — round-1 buttons lived only on `/login` (page) + the avatar dropdown (post-login), so from the normal sign-in path nothing was visible. Fix (3 files): ① `frontend/auth-shared.js` — new `vlStaffRowHTML()` row (**Admin panel → `/admin-security`**, **CMS panel → `/cms-login`**) appended to `renderAuth()` content (**variant A = 51 pages**, incl. `/` + `/pricing`: every static overlay shell carries `#auth-content`) **and** injected once by `ensureAuthOverlay()`'s static branch for **variant B = 36 tool pages** (`primer`/`docking`/`blast`… page-authored `<form id="auth-form">`, `renderAuth()` returns early) — guard `!o.querySelector('#auth-content') && !card.querySelector('.vl-staff-row')` ⇒ **exactly one row ever**, verified on close→re-open and register-mode re-render; ② `frontend/signup.html` — same "staff access" divider + 2 `.sa-btn` buttons as `/login`; ③ `scripts/rules_lint.py` — `STAFF_ENTRY = {frontend/login.html, frontend/signup.html}` (E6/SEC-01 exemption extended; **no other public page may link the shells**). **Coverage proven**: all 87 overlay pages load `auth-shared.js`, every variant-B card matches `.auth-card,.auth-modal` (0 misses), login/signup have no overlay (page-level buttons only). **Gates**: `rules_lint` **0 err/529** · `node --check` OK · full suite **423 passed / 4 failed = pre-existing `test_verification_fix` quartet** · headless local **8/8, 0 JS errors**. **Deployed**: pushed `2487ee43..e4ab824e` → `sync-frontend.sh` **2 uploads** (`auth-shared.js`, `signup.html`; bucket **852**) → invalidation **`I9JKHMZEFX374RNXLDCZTIB569` Completed** → **live gates PASS** (live↔local byte-identical ×2, `vlStaffRowHTML`×3 + both hrefs in live JS, signup divider + 2 `.sa-btn`) + **live headless 8/8, 0 JS errors** → **CI run `37405775588` FULLY GREEN** (Lint & Test ✓ + Deploy to EC2 ✓; `scripts/` touch triggers CI) → post-deploy `/health` **200** + pricing `USD [0, 999, 8900, 4900, 39900, 0, 0]` + `/login` buttons intact. **Where the buttons are (4 surfaces)**: ① **sign-in modal on every page** (nav/mobile Sign in → popup; row under the form, login + register modes) ② `/login` card ③ `/signup` card ④ avatar dropdown after admin sign-in. **Pre-existing findings (not this change)**: `<main>` parse note in login/signup already on HEAD (identical pre/post-edit); local `/api/reviews/public` **500** = `reviews` table missing in `/tmp/vl_dev.db` (**prod 200** `{"count":4,"reviews":[]}` — dev-only noise, filtered in probe); `pages-build-deployment` failure for `2487ee43` = GitHub Pages, not our workflow. **Still true**: CMS login impossible in prod **by design** (CloudFront 403 `/cms-admin`, nginx localhost `/api/v1/cms/`, :8001 not running) — the button opens `/cms-login` but real CMS auth needs the **production-CMS-enablement phase (user decision pending)**; hardcoded `backend/main.py _seed_admin()` credential flagged, not fixed. Probe: `/tmp/vl_modal_btn_check.py` (`VL_BASE` env switches local/live).

**Prior session (staff-entry buttons round 1):** **Staff entry buttons — 🟢 LIVE + VERIFIED 2026-10-05 (commit `de022c18`, 3 files; user: "WHERE you added admin login and CMS login buttons… add both buttons anywhere"):** ① `frontend/login.html` — "staff access" divider + 2 buttons on the sign-in card → **Admin panel → `/admin-security`** + **CMS panel → `/cms-login`** (new `.sa-row`/`.sa-btn` CSS); ② `frontend/auth-shared.js` — `injectStaffMenu()` appends `#udAdminPanel`/`#udCmsPanel` to `#userDropdown` before Logout, revealed **only when session role === 'admin'** via the existing `data-admin-show` sweep (build() reveals itself immediately → closes the race with the file's earlier sweeps; stays `display:none` for non-admin/absent sessions); ③ `scripts/rules_lint.py` — **narrow SEC-01/E6 exemption** `STAFF_ENTRY = {frontend/login.html}` (E6 flags exactly these hrefs — the exemption is documented in the rule + docstring; **no other public page may link the shells**). **Gates**: `rules_lint` **0 err/529** (W1 warnings pre-existing) · `node --check` OK · full suite **423 passed / 4 failed = pre-existing `test_verification_fix` quartet** · headless Chrome **6/6** (buttons visible, injection, admin reveal, non-admin hidden, 0 JS errors — fixed two probe bugs en route: attach lands on `about:blank` → warm-up `Page.reload` first; the 401 `/api/payments/status` is an artifact of the *fabricated* `pf_user` session only). **Deployed**: pushed `06bbf7e4..de022c18` → `sync-frontend.sh` **2 uploads** (`login.html`, `auth-shared.js`; bucket **852**) → invalidation **`IA1ZID2H88V0BTEYF3A97D42A2` Completed** → **live gates PASS** (byte-identical live↔local ×2, `staff access` + both hrefs, `injectStaffMenu` ×1, `/admin-security` → 200, `/cms-login` → 200) + **live headless 6/6, 0 JS errors**. **CI status — RESOLVED, attempt 4 FULLY GREEN**: attempts 1, 2 & 3 died **without ever getting a runner** — identical signature each time (`runner_id:0`, `steps:[]`, ~15 min queued → cancelled; `pages-build-deployment` for the same push showed the identical symptom) = **GitHub platform incident** "delays in assigning GitHub-hosted runner assignment and workflow start times" (investigating, last update 2026-10-05T20:39Z) — **NOT a code failure**; background auto-retry loop fired once (~20:43Z) → runner assigned immediately → **run `37365012130` attempt 4: Lint & Test + Deploy to EC2 both success** → post-deploy `/health` 200 + pricing `USD [0, 999, 8900, 4900, 39900, 0, 0]` + staff buttons intact. **Still true from the panel-access report**: CMS login impossible in prod **by design** (CloudFront 403 on `/cms-admin`, nginx localhost-only `/api/v1/cms/`, backend :8001 not running) — the new button opens `/cms-login`, but actual CMS auth needs the **production-CMS-enablement phase (user decision pending)**; hardcoded `backend/main.py _seed_admin()` credential still flagged, not fixed.

**Prior session:** **🌐 USD RELEASE DEPLOYED & 🟢 LIVE + VERIFIED 2026-10-05 — combined USD commit `6da97c36` (142 files) + migration-semicolon fix `f129a829` + diagnostic `dacf9302` + CI port-takeover `7a0d53cd` + fallback-quote fix `60064e22`, all pushed; final CI run `37345247075` FULLY GREEN with new payload gates; frontend synced (bucket 852 = local 852, 0 deletions) + CloudFront invalidation `I29E929TVD618C8GBDTY40SRZH` Completed.** 🚨 **Key finding: every backend deploy since ≥10-02 was a SILENT NO-OP** — an orphan gunicorn (`3-09:53` old, `--bind 127.0.0.1:11436 ... create_app()`) held the port, so `systemctl restart vigyan` hit `EADDRINUSE` and `Type=simple` returned success while **all health checks passed against the orphan**; proven by hitting origin `13.235.133.206` directly (still `currency INR`, `plans [0,699,5999,3999,32999]`, no `topups`) with no cache headers. **Fix**: deploy now `systemctl stop vigyan` + `pkill -f 'gunicorn.*11436'` → `restart vigyan` → fallback to the proven invocation → **gate `GET :11436/api/payments/pricing` must be `currency=='USD'`** → gate again end-to-end via CloudFront. **Infra correction**: only EC2 in account `497862079867` is `i-05d610fc36db577c9` = `13.235.133.206` (tag `vigyanllm-backend`, CloudFront `E394TCXPIP8P6R` origin); **`13.207.60.92` is NOT an EC2 here** (apex A record, unreachable) — docs that referenced it were wrong; local SSH is rejected so **CI's `EC2_SSH_KEY` is the deploy path**. **Live gates**: API `currency USD` · plans `[0,999,8900,4900,39900,…]` · `topups [(top_up,unit_price_minor 100,USD),(dock_top_up,100,USD)]` = the **$1.00 reprice** · `/pricing` `₹`=0/`Chosen by 60%`=0/`$9.99`×2 · **`integrity=` = 0 on all 4 pay pages** · headless **`loadRazorpaySdk()` → `SDK-LOADED typeof Razorpay=function`** (trial+docking via their own pattern too) · **0 JS errors** on pricing/checkout/docking/index (trial's `401 /api/trial/status` = pre-existing & correct, `@require_auth` on anon, call present at `39ef8815`) · login popup via real `openAuthModal()` → overlay `rgba(8,12,26,0.62)` + `blur(8px)` + card `#fff` `400×573` (earlier "transparent" reading was a probe artifact — forced `.open` instead of calling the function; `VL_AUTH_FALLBACK_CSS` correctly skipped since pricing ships static `#auth-overlay`). **Queued**: ③ optional 2nd real $1 payment E2E · ④ user enables Razorpay International Payments + purpose code · 19 pre-existing FAQ drifts. (detail `pending work.md` §0).** **Prior session — USD Phase 5 payment verification ✅ + sub-$1 top-up reprice → $1.00 ✅ + P0 live SRI checkout outage FIXED & DEPLOYED (`39ef8815`, live-verified) + login-popup readability fix ✅ (transparent `.auth-card` on 46 content pages → white card + `rgba(8,12,26,.62)` blur-8px backdrop + close/Escape affordances; 3 files: `design-tokens.css`/`pricing.html` typo/`auth-shared.js`) — 2026-10-05, all gates green.** **Phase 5 verdict: real Razorpay USD payment-time minimum = $1.00 (100¢)** — user's live-key attempt on a 49¢ order (`order_Tjx0wFABUmlShq`) rejected pre-bank with `BAD_REQUEST_ERROR` "Your payment amount is different from your order amount. To pay successfully, please try using right amount." after checkout clamped 49¢→"US$1" (cost 0, "No amount has been deducted"); 99¢ order (`order_Tjx5iN97yWMs47`) also renders "US$1" → **both top-ups unpayable**; docs' 50¢ figure wrong; ≥100¢ orders unaffected (999¢ = $9.99 verified); webhook dest = active `https://www.vigyanllm.in/api/payment/webhook` (old prod code → unknown-order no-op, 200, no retries, 0 prod-data risk); docking buy entry = only HTTP 402 from `/api/primer/docking/consensus` (`dock-bulk-topup-btn`/`dock-topup-slider` = dead code), failure UX → `payment-failed.html`; probes all cancelled/clean (payment links 49¢+50¢ cancelled; inert unpaid orders harmless). **P0 OUTAGE (pre-existing, in git HEAD AND live prod)**: Razorpay shipped checkout.js build b6 (~Oct 4–5) → our pinned `s.integrity` sha384 stale → SDK fails SRI validation → **all 4 live pay pages broken (docking/checkout/trial/pricing)**; `primer-app.js` unpinned → primer flow unaffected. **Fix in worktree** = plain removal of `s.integrity`+`s.crossOrigin` ×4 (retry-fallback rejected = security theater, any build bump re-triggers) + `security.py` script-src `+https://cdn.razorpay.com` (dev-only CSP; prod pages send NO CSP header). **Hotfix EXECUTED & LIVE (2026-10-05, user "hotfix and hold commit")**: commit **`39ef8815`** = 4 files / 8 deletions / 0 additions (staged from `/tmp/sri_hotfix/*.html` HEAD−2-lines blobs via `git hash-object -w`+`update-index` — index verified empty first, worktree USD work untouched) → pushed `46b7bff6..39ef8815` → targeted `aws s3 cp` ×4 from **committed content** (NOT worktree — would ship USD) to `s3://vigyanllm-frontend` with html cache `max-age=300, swr=600` → CloudFront invalidation **`I2XI1GVB1WACAGZED5UG7YYDBU` Completed** → live gates PASS: pre-flight proved live==HEAD byte-identical ×4, post-deploy live==commit byte-identical ×4 (`.html` URLs need `-L`, cleanUrls 301), `s.integrity`=0 + loader present on all 4, **headless live `/pricing` `loadRazorpaySdk()` → `SDK-LOADED typeof Razorpay=function`, 0 JS errors** — live INR checkout restored (old content by design). `sync-frontend.sh` NOT used (would ship all USD work). **Reprice (recommended default, executed)**: both top-ups → **$1.00**: `price_registry.py` `TOPUP_PRODUCTS` 99/49→**100/100** (+`TOPUP_PRICE_MINOR`→100 + minimum-NOTE comment), `auth.py` comments (values derive from registry), `docking.html` 10 spots (JSON-LD offers `"1.00"`+featureList, **FAQ visible+schema together**, hero CTA, pricing subtitle, modal `$1.00`+default `1.00`, `total=val*100`, `'1.00'`, qty `(v*100/100)`), `primer.html` overlay ×2, `primer-app.js` `(99*e/100)`→`(100*e/100)` ×2, `protein-docking.html` prose ×2, `tests/test_payment_routes.py` (`==100` ×2, create 297¢→**300¢**). **Gates**: residual money scan **0** · JSON-LD 3 files parse (5+4+2 blocks) · FAQ mirror **Q0/A0** (new canonical gate `/tmp/faq_gate.py` reusing `/tmp/ans_fix.py` display/key/extract_all) · `rules_lint` **0 err/529** · `py_compile`+`node --check` (primer-app + 12 inline blocks) 0 · targeted **25/25** · **full suite 393 passed / 4 failed = pre-existing `test_verification_fix` quartet (= Phase-4 baseline)** · dev `:5199` restarted → pricing API `topups 100/100 USD` + create-order E2E **100¢ (dock×1) / 300¢ (top_up×3)** · headless **6/6 pages 0 JS errors** — primer `$1.00 per design run || total=2.00`, docking `$1.00 per docking run || total=3.00`, checkout/trial/success regression unchanged. **Next (release 2026-10-05): ① DONE = SRI hotfix `39ef8815` pushed + deployed live → ② combined USD commit (pricing visual + Phases 1–5 + reprice + login-popup fix + trackers + CI `safety`-gate unbreak `SFTY-20260902-58666`/nltk) → deploy backend-first (13.207.60.92 PG, migration 0126 via CI/CD) then frontend (bucket 839)**; optional Phase-5 bonus = user's 2nd real $1 payment (pay→verify→credit E2E); user-side: enable Razorpay International Payments + purpose code (~3.6–5% MDR).

**Previous session:** **USD migration Phase 4 content sweep ✅ DONE — all 4 batches + all gates green (2026-10-04, uncommitted; pricing-page visual + Phases 1–2–3 + pre-Phase-4 verification remain uncommitted alongside — detail `pending work.md` §0).** **Batch A**: 79 JSON-LD `priceCurrency` INR→USD + microdata + demo — site-wide re-scan **0 INR across 1002 blocks**. **Batch B**: our-prices → current Free/Pro/Lab/Enterprise USD (docking, search, validated-primer, developer(-docs) rate tables, primer-design-india, hub, faq visible+JSON-LD, admin-security plan table, 2 blogs). **Batch C**: INR-claim reframes — terms/primer/sovereign-ai 7/7/biomedical-ai-platform/primer3-alternative/primer3-vs pair/blog-index+RSS cards/complete-guide/best-free-tools/**primer-design-india-affordable full-thesis rewrite** (metas+Article+FAQ pair in sync, H3 "INR Pricing"→"Priced for Indian Labs", UPI section→"No Card Needed to Start", Rs 15,000 list→USD plans, CTA)/biotech-ai pair/landing-primer-design-software-india (4 metas + stale Rs-49 FAQ + H2)/llms.txt/security+privacy gateway copy; final sweeps: "India-first pricing" **0 files**, UPI-as-offer **0**, stale `Daily Pass`/`Rs` plan prices **0**. **Deliberately left**: admin-security `Paid (₹)`/`Infra Cost (₹)`/`Amount (₹)` (INR columns + ₹ expense ledger by design), `primer-app.js` admin block (**verified dead** — `as-revenue`/`admin-user-tbody` exist in no HTML), third-party India-context ₹ (stipends/Benchling/instruments/oligo costs/grants), support.html "never card or UPI credentials" do-not-email advice, primer-design-india L333/334 market-barrier para (about international tools). **Batch D**: revenue-stats per-currency split (SQLite + PG `FILTER`): `total_inr` + `total_usd_minor` + `basis:"inr_only"` margin (test-asserted keys kept, **no FX invented**); promo summary `total_trial_value_usd_minor` beside `_inr`; `admin-app.js` revenue `$x.xx + ₹n` / margin `—`+tooltip when USD>0 / promo-value per-currency (cogs+expense stay ₹); `analytics.js` default `USD`; admin-security plan table `$9.99/$49`. **Gates**: `rules_lint` **0 err/529** · FAQ mirror **Q0/A0** (canonical `/tmp/ans_fix.py display()`) · JSON-LD **0 parse err / 0 INR** · `py_compile`+`node --check` 0 · rss/sitemap XML OK · targeted tests **25/25** · **full suite 393 passed / 4 failed — same pre-existing `test_verification_fix` quartet** (379 + 14; = Phase-2 baseline) · headless smoke **11 pages 0 JS errors** (2 pre-existing 404s: `/api/auth/usage` dev route + `landing-pages/logo.png` never existed) · live `:5199` content 6/6. **Findings (pre-existing, deferred)**: initdb INR capture/transition triggers exist **only on never-migrated DBs** (prod clean — `0105` DROPs payments CASCADE → **no migration needed**), `fn_record_operation_cost` total_cogs=0, dead `lifetime_revenue_inr`/users-table, "free academic access" stale claims. **Next: Phase 5 verify (first test payment confirms USD payment-time min; test keys) → one combined commit (permission) → deploy backend-first (13.207.60.92 PG, migration 0126 in CI/CD) then frontend (bucket 839).** **Prior in-session record:** pre-Phase-4 verification — dependencies + promo-code generation workflow CHECKED & FIXED, user gate passed ("check all dependencies, promo code generation workflow, and other all — if they work properly then goes to phase 4"). **BUG FOUND & FIXED**: admin promo generator sent **INR-selected currency + 699 price defaults** → under Phase-2 semantics those codes are paise-priced and auto-retired by the startup INR sweep (dead trial codes); fixed `admin-security.html` (Trial label `($1 → auto-debit)`, `Price (¢/mo after trial, 999 = $9.99)` default **999**, **USD-only** currency select) + `admin-app.js` (`||999`, `togglePromoType` value 999 ×2, promo-list cell **currency-aware** `$x.xx` / legacy `₹n`); `test_promo_expense` create bodies → 999/USD + list assertions scoped to own `LIST-` codes (order-independent — root cause of the break: **`auth.DB_PATH` binds at import → one shared tmp sqlite per pytest session**, pre-existing quirk). **New `tests/test_promo_workflow_usd.py` — 6-test E2E** (faked Razorpay, production-identical HMAC): USD generation → anon validate 999¢/USD → trial $1(100¢) order → HMAC verify → `plan.create` **999¢ USD** + `subscription start_at` >29d → `plan=trial`/`used_count=1`/`trial/status` USD → re-claim **410** → academic direct-Pro (no Razorpay hop) → checkout 30% promo **999→699¢** → revoke **410** → bad-sig **400**. **Gates**: targeted **25/25** (workflow 6 + promo 13 + payment 6, redemption-first order) · **full suite 393 passed / 4 failed — all 4 = pre-existing `test_verification_fix` quartet** (393 = 387 Phase-2 baseline + 6 new) · `rules_lint` **0 err/529** · `node --check admin-app.js` 0 err · promo-form residual `₹`/INR/699 **0** · live `:5199`: static edits served + live `/api/promo/validate` **200 `price_minor 999 currency USD`**. **Findings (pre-existing, NOT USD regressions, deferred)**: live `/api/admin/*` **403 on SQLite dev only** — `security.init_admin_rbac` verifies via `pg_auth.verify_token` → PG `fetch_one` blacklist query (raises on empty `DATABASE_URL`; prod PG unaffected; `security.py`/`pg_auth.py` untouched — admin flow proven by test-client E2E instead; local `/tmp/vl_dev.db` admin hash re-synced to `.env`); `analytics.js trackPurchase(currency='INR')` default = **zero callers** (→Phase 4); admin promo `total_trial_value_inr` + revenue/expense mixed units (→Phase 4); `admin-security.html` remaining `₹` headers/plan table (→Phase 4). Record `pending work.md` §0. **Next: Phase 4 content sweep → Phase 5 verify (first test payment, USD min) → one combined commit (permission).**

**Previous session — homepage visual upgrade (phase 1 + round 2) — COMMITTED, PUSHED & DEPLOYED 2026-10-04 (live + verified)** — commit **`1c34f68b`** (39 files: `frontend/index.html` +74/−23, `frontend/home.css` +71, 37 new `frontend/assets/hp-*`) pushed `45cb14b7..1c34f68b`; deploy dry-run 39 up/0 del → `sync-frontend.sh` (bucket **839 = local 839**, md5 5/5, cache intact) + invalidation `ID07TBGS2X1CASZACJ73XJOG1I` **Completed** → live gates PASS (`/` byte-identical live↔local 79,917 B, `home.css` identical, 7/7 assets 200, live headless 1440+375: 39/39 imgs, 18 icons nw=120, reveals 25/25, overflow 0, mask+chips, **0 JS errors**) + IndexNow **HTTP 200**; record `pending work.md` §0. Work: **phase 1** = 17 `hp-*.jpg` (hero figure, 4 pillar banners, 11 product thumbs, 2 story figures); **round 2** (user feedback) = hero edge-blend (two-axis CSS mask, chrome border/radius/shadow removed, 2 honest UI chips), **18 white-on-blue-gradient Phosphor PNG icon tiles** replacing inline SVGs (11 tool + 4 pillar + 3 partnership, `.prod-icon` 44px + `.pillar-icon`/`.collab-icon` tiles), Biostatistics product thumb (`hp-card-biostats.jpg` 39.5 KB), research-workflow band w/ headline overlay (`hp-data-band.jpg` 122.6 KB, static navy caption mobile); all gates green pre-push + live; screenshots `/tmp/r2_*.png`. **In progress: pricing page — visual upgrade ✅ COMPLETE + USD migration Phase "pricing page" ✅ COMPLETE (both uncommitted, gates green).** Visual: 7 Pexels photos + 4 plan-card photo headers + 6 Phosphor icon tiles (`assets/pr-*`, `docs/PRICING_ASSETS.md`), split hero, 01–04 labels, trust strip, promo pair, value strip, FAQ accordion, CTA band, reveal/price-swap animations; truth fixes done (no "Chosen by 60%", on-prem→roadmap, SLA softened, no DPIIT). **USD (Option B)**: all customer-facing prices on pricing.html → `Free $0 / Pro $9.99·$89 (save 26%) / Lab $49·$399 (save 32%) / Enterprise quote`, JSON-LD offers USD, FAQ answers updated, cards-only payment copy + checkout config (UPI/netbanking removed), `PRICING_BASE_AMOUNTS` in USD cents, fallback currency `USD` — 0× `₹`/`INR` on the page. **Phase 1 Razorpay USD spike ✅ DONE (10-04, live keys inert probes, user-approved)**: USD orders 49/99/100/999¢ all created, **USD plan create WORKS (flagged risk cleared)** `plan_TjpeDv8Vl0IEe4`, USD subscription create→**cancelled**, checkout renders **US$9.99** + **Cards-only** (Razorpay auto-hides UPI/netbanking on USD), $0.49 passes order+checkout layers, 0 console errors — details `pending work.md` §0. **Phase 2 backend USD ✅ DONE (10-04, uncommitted)**: `price_registry.py` → `price_minor` USD cents + `CURRENCY="USD"` + deprecated `price_inr` property alias + new `TOPUP_PRODUCTS` (top_up 99¢ / dock_top_up 49¢, `validate_order_request` now sells them) + `get_amount_minor` (old `get_amount_paise` kept as alias, **no ×100 ever**) + TrialConfig 999¢/USD; `payment_routes.py`: create-order accepts `product_id or plan_id` + qty (legacy `runs` alias) + `validate_quantity`, **`amount // 100` bug FIXED** (stores cents + `currency:'USD'`), `amount<=0→400` (free/enterprise blocked), verify = LIKE lookup (idempotency works again) + **topup branch credits `paid_runs`/`dock_paid_runs`** (plan activation unchanged; sqlite3.Row `.get()` promo bug fixed), webhook branches topup, pricing emits `price_minor`+legacy `price_inr`+`currency:"USD"`+`topups[]`, trial/promo: $1=100¢, plan.create amount = cents (no ×100), defaults 999/USD, admin promo create 999/USD, **billing_history rewritten** (SELECTed nonexistent cols → was 500; now real cols + per-row rule: USD=minor, legacy INR=major×100, `amount_minor` + `amount_inr`(null for USD)); `pg_payment_routes.py` mirrors all + `_credit_tokens_atomic` topup fix (was crediting **0** runs); `auth.py`: payments `currency` col (CREATE default USD + no-default ALTER → legacy rows NULL=major INR), promo defaults 999/USD, **INR promo codes retired** idempotently at startup (no FX guessing), `PRICE_PER_DESIGN/PRICE_PER_DOCK` derived from registry (99¢/49¢, were ₹49/₹99); migration **`0126_usd_pricing.sql`** (retire + defaults; payments rows NOT rewritten — per-row currency rule; auto-runs in CI/CD); tests rewritten 4→**6 pass** (USD pricing/legacy alias, topup 297¢ create + verify credits paid_runs & plan stays free + idempotent 0, bad-sig, plan 999¢/academic 27930¢/enterprise 400, plan verify→pro); gates: **full suite 387 passed / 4 failed — all 4 `test_verification_fix` proven pre-existing** (identical on `git stash` baseline; `primer_server.py` untouched), targeted re-run **28/28**, `test_promo_expense` 13 pass unchanged. Pre-existing findings deliberately NOT touched: PG webhook doesn’t activate modern plan products (race vs client verify), `_credit_tokens_atomic` yearly→30d expiry, admin revenue/expense sums mixed units (→ Phase 4). **Phase 3 frontend core USD ✅ DONE (10-04, uncommitted, all gates green)** — 7 files: `checkout.html` (`usdNum()` cents→`$x.xx`, `$` symbol, discount/promo renders, Razorpay `USD` fallback + **card-only config**), `trial.html` (`₹1`→`$1` ×19, `₹699`→`$9.99` ×3, `usdAmt()` for dynamic promo/step2/success cents, meta/button/description strings), `payment-success.html` (`$` + `toFixed(2)` NaN-guarded), `usage-billing.html` (history amount **currency-aware**: USD rows `$x.xx` from `amount_minor`, legacy rows `₹` from major×100 — fixed my own first-pass bug that would've shown historical ₹699 as $699.00), `primer.html` (pay overlay `$0.99 per design run` + live `(99*e/100).toFixed(2)` total, pricing sentence Pro $9.99/Lab $49/Enterprise quote, cards-only copy, JSON-LD `priceCurrency` USD), `docking.html` (modal → **Buy Docking Runs $0.49** — removed false "credits work for both" claim, 49¢ qty/bulk totals, hero CTA + pricing subtitle + FAQ answer updated in **visible+schema together**, offers `0.49`/USD, Razorpay USD + card-only + `method:{card:true}`), `primer-app.js` (pay-total + `Pay $x.xx` topup strings + `currency USD` + card-only config; admin-finance `₹` left → Phase 4). **Gates**: residual **0** `₹`/`INR`/`&#x20B9;`/`\u20B9` across all 7 · `node --check` primer-app + 37 inline blocks 0 err · `rules_lint` 0 err · FAQ mirror **Q0/A0** (primer 10, docking 9) · serve 6/6 · **headless desktop 6/6 pages 0 JS errors** (checkout `9.99|$` live USD API, trial `$9.99…||$1`, primer `total=1.98`, docking `total=1.47`) · billing-history E2E USD+legacy rows → `$9.99`/`₹699` · pytest **15/15** · 375px no money-element overflow (nav `.nav-right` overflow pre-existing — identical on untouched `/blast`+`/validation`). **Dev server was stale (pre-Phase-2, served `currency:INR` pricing) → restarted `/tmp/run_sqlite_server.py`; pricing API now USD/999¢/topups 99+49¢.** **Next: Phase 4 content sweep** (2 blogs' our-prices, marketing/landing ₹ pages, `admin-app.js` promo price display + admin revenue/expense per-currency sums, remaining tool-page JSON-LD offers) → Phase 5 verify (first test payment confirms USD payment-time min; test keys recommended) → combined commit (needs permission) → deploy backend-first.
**Prior session:** **/custom-pipeline-development MNC visual upgrade + site-wide header restructure — COMMITTED, PUSHED & DEPLOYED 2026-10-04 (live + verified)** — 6 commits `78689c74`→`e1cde5d3` pushed `27113148..e1cde5d3`; deploy dry-run 540 up/0 del → `sync-frontend.sh` (bucket **802 = local 802**, md5 9/9, cache intact) + invalidation `I3N2PO9Y1KAQ32YHUTKDA1L14H` **Completed** → live gates PASS (9/9 changed pages byte-identical live↔local, 6 `cp-*.jpg` 200, nav Platform-gone/Services-present + footer link ×2, live sitemap 431 incl. new page, page FAQ **8/8 Q✓A✓**, 0 banned claims, JSON-LD 0 err, 0 JS errors) + IndexNow **530 URLs → HTTP 200**; record `pending work.md` §0/§8. Commit map: `78689c74` serve_static `.jpg` whitelist (dev-only) · `47421013` `.drop-menu` scroll containment (2 shared CSS) · `0512c22f` 4 invisible-H1/checkout fixes · `084395cc` **header PRODUCTS/SERVICES restructure (525 HTML** — Platform dropdown → Services → new page, footer + body cross-links) · `a7d99774` **page + 6 photos** · `e1cde5d3` sitemap/robots 431. The page work: user's 7 photos mapped to sections (split hero w/ animated HUD card + mouse-parallax, hexagon intro figure, sticky flow figure beside How-we-work, chem/sequence beside How-we-validate, researcher beside Who-this-is-for, plexus+particles contact band), 5 story captions, vanilla motion (19-target IntersectionObserver reveal + staggers, card hover lift, badge pops, button shine, full reduced-motion + `<noscript>` fallbacks); 6 optimized assets `frontend/assets/cp-*.jpg` (428KB, hero 148KB eager); bugs fixed en route: `serve_static` extension whitelist lacked `.jpg` (dev-only 404s) + 2 photos catalogued swapped (caught via screenshot review, contents+attrs corrected). **Round 2 (feedback)**: side margins 960→1200 container (hero/sections/list pixel-aligned x=144), figure columns rebalanced (472/433×3/541, none upscaled, cap-grid 3-up), de-AI editorial pass (numbered `data-num 01–08` labels + drawn rules + section hairlines), hero motion-video background (`.hero-fx` drifting blobs + light streak + dot-grid pan + dust, card ken-burns + scanline, JS 3D tilt gated on reduced-motion), table/deliverable row cascades + step-line growth; gates green (FAQ mirror 8/8 Q0A0, rules_lint 0 err, bake 0 stale, headless Chrome 1440+375: reveals 23/23, 0 JS errors, 0 bad images, no overflow; reduced-motion safe). All previously-uncommitted work is now in the 6 commits above (Phase A + feedback rounds 1–3 on the page; site-wide header restructure + `.drop-menu` scroll CSS + 4 H1/checkout fixes + sitemap/robots on the rest) — detail **`pending work.md` §0/§8**. **Previous session:** 117 FAQ answer drifts + tool-dominance layout fix — COMMITTED, PUSHED & DEPLOYED 2026-10-03 (live + verified) — (a) **117 schema-only FAQPage answer drifts fixed** (`3cdaf4f7`, 29 files — visible text = source of truth; initial 136/45 scan dropped to 117/29 after fixing the normalizer: browser-faithful `display()` in `/tmp/ans_fix.py` = **canonical FAQ-gate normalizer**; FAQ mirror now Q 0 / **A 0**), (b) **tool dominance** (`944d1c62`, 3 pages — `dna-to-rna` form+output moved above 5-H2 article (was 1,254w below), `biostatistics-calculator` "Why Use…" moved below widget, `crispr-analysis` early-access band moved under hero; all **22 public tool pages** now tool-above-text, 0 violations), (c) **deploy**: dry-run 30/0 del → `sync-frontend.sh` (bucket 795 = local, md5 9/9, cache intact) + invalidation `I5ANTVTX8UP53DTRPXH087Q6IV` Completed → live gates PASS (tool-order 3/3, 30/30 byte-identical live↔local, FAQ mirror 0/0, JSON-LD 0 err) + IndexNow 30× HTTP 200; trackers `0c216d58` — `pending work.md` §0/§7. Prior session: FAQ-58 fix + FULL PROD DEPLOY 10-02 (`d46668ec` + `I6K173ND15QFI06I18813N4OVX`, steps 1–7 `4542626a`..`1433b5b6`). Governing: `rules.md` (Part 1) + `docs/CLAIMS_LEDGER.md` + `scripts/rules_lint.py` (0 err ship gate). Prior: GSC Decline response — Tier-1 pushed (`a5d0c1ea`), Tier-2 complete. **Current tracker = `pending work.md`** (§0 deploy log, §7 record + queued user actions). Older plans: `PENDING_PLANS.md`.
**Never commit:** `bandit-report.json`, `docking_queue/`, `deploy/aws/sync-frontend.sh` (run-only).

## Anti-Cannibalization Policy (from 2026-08-19 GSC analysis)

**Context**: 71 blog pages pull 51,325 imps @ 0.25% CTR, cannibalizing tool pages (44,918 imps/month stolen; ~1,258 wasted clicks/mo at 3%). Worst: ncbi-primer-blast-guide 39,444 imps vs /primer 1,583; 41 PCR blogs (7,985 imps) vs /pcr-analysis (84 imps) = 95:1.

**6 rules for ALL blog posts from now on:**
1. **Blog = informational queries only** ("what is X vs Y", "how does X work"). Tool pages answer tool-intent ("free X tool", "X calculator"). Never write a blog targeting a tool query.
2. **Above-fold CTA within first 300 words**, visually distinct, linking the tool page. Teal gradient template (0d9488→0f766e) defined in the cloning blog prompt.
3. **Title passes authority to the tool**: `"[Topic] — Try the Free [Tool Name] | VigyanLLM"` format (cloning post used `"[Topic] | VigyanLLM"`).
4. **3-5 varied anchor-text links** to the tool page: "try the free [tool]", "design with our [tool]", "open the [tool]", "use the [tool]".
5. **Blog schema = `Article`**; tool page schema = `SoftwareApplication`. Never mix. `og:type` = article for blogs, website for tools.
6. **Meta description leads with education, ends with tool**: `"[Educational value]. Try VigyanLLM's free [tool] — [one differentiator]."`

**FAQ rule**: blogs answer conceptual/method questions only — NO "how to use the tool" (that lives on the tool page's own FAQPage schema).

**Funnel CTA backlog (post-Aug 27, by wasted imps):** Tier 2 → pcr-steps(1,211)/pcr-primer-design-rules(1,144)/real-time-pcr-data-analysis(954)→/pcr-analysis, rt-pcr-vs-qpcr(825)→/pcr-analysis, primer-dimer-fix(824)→/primer, digital-pcr-vs-qpcr(641)→/pcr-analysis, primer-design-mrna(554)→/primer, taqman-vs-sybr-green(399)→/pcr-analysis, pcr-troubleshooting-guide(394)→/pcr-analysis, types-of-pcr(322)→/pcr-analysis. Tier 3 → touchdown-pcr-protocol, pcr-protocol-beginners, nested-pcr-primer-design, bisulfite-conversion-pcr-primer-design, ai-primer-design-machine-learning, long-range-pcr-nanopore-sequencing-primer-design. crispr-grna-design-guide→/crispr-analysis DEFERRED (tool not live). Full prompt doc at `/Users/macbookpro/Downloads/cloning-blog-prompt-anti-cannibalization.md`.


**Next Sprint:** **Week 3** — Top-10 blog rewrites (Agent 63: Lab Notebook / Middle Mile / Indian Academic) + SERP snippet optimization (Agent 69: title/meta for top-20-by-impressions non-tool pages) → **2026-08-27 Sprint Impact Re-Measurement** below → Phase 2 — credibility (validation benchmark page live; wire faculty outreach next) → design-audit Sprint 2+ → CMS decline-cookie re-verify → **fix 145 pre-existing glossary OG-image 404s** → DB plan/token diff → final sweep

## 2026-08-27 — Sprint Impact Re-Measurement
**Trigger**: Date-based (2-3 week GSC lag from 9-commit CTR sprint + GEO fixes)
**What to measure**:
1. CTR delta: Overall CTR (baseline 0.84%) — target 1.5%+
2. Position band 4-10 CTR (baseline 0.43%) — target 2%+ (industry: 5-12%)
3. ncbi-primer-blast-guide CTR (baseline 0.20% @ pos 7.6) — target 3%+
4. GEO re-measure: Query Perplexity/ChatGPT/SGE for same 10 terms (docs/GEO_BASELINE.md) — target 7+/10
5. Desktop CTR (baseline 0.56%) — check if any movement from font/schema/OG fixes
**Data source**: Export new GSC 3-month report on 08-27, compare against 2026-08-06 baseline
**Compare against**: `/home/z/my-project/upload/vigyanllm.in-Performance-on-Search-2026-08-06 (1).xlsx`

## Week 2 — Tool Rewrite Sprint (8 pages, COMPLETE, all pushed)

### What & Why
De-branded, de-ChatGPT'd, and re-scoped 8 live tool pages with real worked examples. Each rewrite verified via Flask test client + tag/JSON-LD balance; no-touch zone (tool form/JS/meta) preserved.

### Tool Page Table
| Page | Brand Before→After | Words | Key Differentiator Added |
|------|-------------------|-------|--------------------------|
| Primer Design | 46→10 | 2960 | BRCA1 c.5266dupC + GAPDH examples, troubleshooting |
| BLAST | 20→0 | ~2000 | BRCA1 vs BRCA1P1 pseudogene money-shot |
| Tm Calculator | 18→3 | 1826 | GAPDH 4-method comparison (6°C spread) |
| Docking | 21→0 | 2004 | Imatinib vs ABL1 worked example |
| MSA | 21→0 | 1809 | TP53 5-species paralog trap |
| GC Calculator | 13→1 | 1840 | GC spectrum table + 3 gene examples (GAPDH/BRCA1/KIT) |
| DNA-to-RNA | 20→1 | 1600 | Coding vs template strand confusion |
| Thermodynamics | 26→0 | ~3600 | Wallace arithmetic fix, trimmed 600w |
| **Total** | **~175 → ~5** | **~17,645** | |

### Commits (all pushed)
`82bf40e1` thermodynamics · `459eed19` dna-to-rna · `f6bcf321` gc-calculator · `4676ba86` msa · `7e3052bd` docking · `2671cad` tm-calculator (bl)

### Corrections — false alarms from the rewrite brief
The thermodynamics (page 8) brief claimed **3 scientific bugs** (4°C/9°C example Tm lower bounds, 273°C upper bound). **All three were FALSE ALARMS** — verified against the actual code:
- 4°C appears only inside the **correct** Wallace rule (2°C×(A+T) + 4°C×(G+C)).
- 273.15 appears only in the **correct** Kelvin→°C conversion (Tm = ΔH/(ΔS + R·ln(Ct/4)) − 273.15).
- The worked example already yields a realistic **45.9 → 42.3°C** chain (consistent, no change needed).
The **one real defect** found & fixed: the Wallace example for `5'-ATCGGCTA-3'` showed `2×3 + 4×5 = 26°C` but the sequence actually has A+T=4, G+C=4 → **24°C**. Corrected to `2×4 + 4×4 = 8 + 16 = 24°C`.
Also: brief wanted "trim FAQ 5-6" but all 7 FAQ items were distinct, high-quality thermodynamics Q&A — kept all 7.

## Week 3 — Blog Rewrite Sprint (8/8, COMPLETE, all pushed)

### What & Why
De-branded, de-ChatGPT'd, and re-scoped 8 blog posts with real worked examples. Each rewrite verified via Flask test client + tag/JSON-LD balance; tool form/JS/nav/footer untouched. All inline FAQ items mirrored 1:1 in FAQPage JSON-LD.

### Blog Table
| Blog | Commit | Words | Brand | Format |
|------|--------|-------|-------|--------|
| pcr-steps | `ffea1ea2` | 2,327 | 0 | Explain Like a PI |
| pcr-primer-design-rules | `62626eeb` | 1,926 | 1 | Decision Guide |
| rt-pcr-vs-qpcr | `1385cbe2` | ~1,900 | 1 | Comparison with Teeth |
| primer-dimer-fix | `aa401e5b` | ~1,430 | 1 | Lab Notebook |
| real-time-pcr-data-analysis | `6775a624` | 1,862 | 0 | Explain Like a PI |
| digital-pcr-vs-qpcr | `061ea5ee` | ~1,610 | 1 | Decision Guide |
| pcr-troubleshooting-guide | `5d62d61a` | ~1,400 | 1 | Lab Notebook |
| types-of-pcr | `a246b9cc` | ~1,536 | 2 | Decision Guide |

## GSC Issues Fix Batch — Sep 1 2026 (commit `34282892`, pushed)

### What & Why
12-issue GSC fix plan targeting growth from ~326 clicks/mo to 1,000–1,500 clicks/mo over 90 days. Based on Aug 28 GSC export data.

### Fixes Applied
| Fix | Scope | Commit |
|-----|-------|--------|
| #1: www/non-www redirect | vercel.json reversed (was sending www→non-www) | `34282892` |
| #7a: academic-partnership href | Added leading `/` across 449 files | `34282892` |
| #3: Top 10 meta rewrites | 6 blog/landing pages titles ≤60 chars + truncated meta fixed | `34282892` |
| #5: SoftwareApplication schema | Added to all 27 landing pages | `34282892` |
| Landing page titles | 10 additional titles shortened to ≤60 chars | `34282892` |
| #9: Canonical verification | All verified (www.vigyanllm.in) | verified |

### Skipped at the time → RESOLVED 2026-10-01 (see `pending work.md` §2b)
- **Fix #8**: repurposed (not a new page) — `/primer-design` retitled "Automated Primer Design — How It Works, Step by Step (2026)" to stop the title split with `/primer` (`7711b8eb`). Original "ai primer design" query demand no longer exists in any GSC export since Aug 22.
- **Fix #6**: gc-clamp expanded 2026-10-01 (`63707d46`, `bf091b9c`) — depth H1, early /gc-calculator tip, 5th FAQ, two false claims removed.

### Sep 5–10 GSC Measurement Plan
| Metric | Before (Aug 28) | Signal of Success |
|--------|-----------------|-------------------|
| Non-www impressions | ~8,920/mo | Should drop 80%+ within 2 weeks |
| NCBI guide CTR | 0.16% | Should tick up if Google re-renders the title |
| "Page with redirect" errors | 239 | Should start resolving |
| Overall CTR | 0.44% | Small lift from title improvements |

## Current Board State — 2026-10-04

| Status | Item |
|--------|------|
| ✅ DONE | **`/custom-pipeline-development` MNC visual upgrade + site-wide header restructure — COMMITTED, PUSHED & LIVE 10-04** (6 commits `78689c74`→`e1cde5d3`, invalidation `I3N2PO9Y1KAQ32YHUTKDA1L14H`, live gates 9/9 byte-identical + FAQ 8/8 + IndexNow 530× HTTP 200) — split hero (HUD card: glow/float/mouse-parallax) + 5 section figures + story captions + plexus contact band w/ particles; vanilla motion (19-target reveal + staggers, hover lift, badge pops, reduced-motion + noscript fallbacks); **Round 2**: 1200px grid (hero/sections pixel-aligned x=144), figure columns rebalanced (no upscaling, cap-grid 3-up), numbered 01–08 editorial labels + hairlines, hero motion-video background (blobs + streak + dot-grid + ken-burns + scanline + 3D tilt), row cascades + step-line growth; **Round 3**: type scale 13→15 body / 16 leads / 13 labels + 80ch reading cap; 6 new `assets/cp-*.jpg`; `serve_static` `.jpg` whitelist fix + 2 swapped photos; gates green pre-push + live — `pending work.md` §0/§8 |
| ✅ DONE | **117 schema-only FAQPage answer drifts / 29 files** — committed 10-03 (`3cdaf4f7`), visible text = source of truth; initial 136/45 scan corrected to 117/29 after normalizer fix (`/tmp/ans_fix.py` `display()` = canonical FAQ-gate normalizer); FAQ mirror Q-miss 0 / **A-miss 0** (was 136); JSON-LD 0 err; confinement PASS; routes 29/29 — details `pending work.md` §7 |
| ✅ DONE | **Tool dominance — all 22 public tool pages now tool-above-text** (10-03, `944d1c62`): `dna-to-rna` form+output moved above 5-H2 article (was 1,254w below tool), `biostatistics-calculator` "Why Use…" moved below calc widget (was 307w+1 H2), `crispr-analysis` early-access band moved directly under hero (was 565w+4 H2s); pure block moves, JSON-LD byte-identical, JS IDs resolve, headless-Chrome DOM order verified; 0 violations remain (`cms-admin` excluded — admin-only) |
| ✅ DONE | **FULL PROD DEPLOY — LIVE & verified 10-02** — dry-run 533 up/0 del → `sync-frontend.sh` (bucket **795 = local**, md5 14/14, cache headers intact) + CloudFront invalidation `I6K173ND15QFI06I18813N4OVX` Completed; live gates full pass (0× gtag, GTM+consent+3-button banner, 0× aggregateRating/adoption-numbers, FAQ rebuild live, banned claims 0, JSON-LD parses) + IndexNow ×2 **HTTP 200** — record `pending work.md` §0 |
| ✅ DONE | **Human-First update — `WEBSITE_UPDATE_PLAN.md` Steps 1–7** (10-02, **committed + pushed + LIVE (row above)**) — `rules.md` Part 1 governing + `CLAIMS_LEDGER` + `rules_lint` gate; TRUST-04/02/03 sweeps (`audit-ready`/`lab-ready`/`clinical-grade` → **0 site-wide**); D-06b GTM-only (487 gtag loaders stripped, 494 pages GTM+consent, 0 page Clarity); 3-button cookie banner; `/support`; aggregateRating out; all gates green — details `pending work.md` §7 |
| ✅ DONE | **User final approval given → committed + pushed** (10-02): 6 logical commits `4542626a`→`1433b5b6` + FAQ fix `d46668ec` on `origin/main`; only `bandit-report.json` left untracked by policy |
| ✅ DONE | **58 schema-only FAQPage questions / 25 files** — fixed 10-02 (`d46668ec`) & **LIVE**: 14 files rebuilt from visible FAQ containers (microdata/`<details>`/`.faq-item`/Quick Answers), 11 FAQPage blocks removed (no visible FAQ), `tm-calculator` broken `MgCl&sub2;` entity ×5 → `MgCl2`; site-wide FAQ mirror **Q-misses 0** (`pending work.md` §7) |
| ~~⚠️ NEW FINDING~~ | ~~136 answer-paraphrase FAQ drifts / 45 files~~ → **✅ RESOLVED 10-03** — see top row (`3cdaf4f7`, actually 117 real drifts / 29 files after normalizer fix; 19 were false positives) |
| 🆕 USER ACTION | **GTM container: Clarity tag → Consent Settings → require "Analytics"** — repo cannot gate container tags; until set, `privacy.html`'s Clarity-on-decline claim may not hold for undecided/non-EEA visitors (`pending work.md` §7) |
| ✅ DONE | Gene-prefers validated fix, glossary bugs, rs verification, E-E-A-T blocker, BLAST E-value, all 8 tool rewrites |
| ✅ DONE | **Week 3: Blog rewrites** (Agent 63 — **8/8 complete**) — pcr-steps `ffea1ea2`, pcr-primer-design-rules `62626eeb`, rt-pcr-vs-qpcr `1385cbe2`, primer-dimer-fix `aa401e5b`, real-time-pcr-data-analysis `6775a624`, digital-pcr-vs-qpcr `061ea5ee`, pcr-troubleshooting-guide `5d62d61a`, types-of-pcr `a246b9cc` |
| ✅ DONE | **GSC fixes batch** (`34282892`) — www redirect, academic href, 10 title rewrites, 27 SoftwareApplication schemas |
| ✅ DONE | **Fix #8** (`7711b8eb`) — `/primer-design` retitle (differentiated from `/primer`), 24-step truth; LIVE 10-01 |
| ✅ DONE | **Fix #6** (`63707d46`, `bf091b9c`) — gc-clamp depth H1 + tip + 5th FAQ + false-claim removals; LIVE 10-01. Also: site-wide `22-step`→`24-step` sweep `ad5a3be7` (engine = 24 steps) |
| ✅ DONE | **HQ Gurgaon → New Delhi** (`5e87eb05`) — 9 lines / 4 files (badges, HQ line, GST→Delhi, JSON-LD foundingLocation, prose); name audit: ChinhAI/SubBrain present (deferred by user), "legal AI"/"VigyanLLM AI" = 0 found anywhere; LIVE 10-01 — details `pending work.md` §2c |
| 🔄 SHIPPED | **HQ propagation to search/AI** (10-02) — sitemap lastmod, `/about` Organization+FAQPage, homepage PostalAddress city, `llms.txt`, IndexNow key+ping (202 ✓); **user: GSC request-indexing ×4, Bing, LinkedIn/GitHub/MCA/etc.; re-check 10-05 + 10-08** — `docs/HQ_PROPAGATION.md`, `pending work.md` §2d |
| 🕐 DEFERRED | **ChinhAI/SubBrain invented-agent cleanup** — 8/6 files, 7 live pages; user: "for now no need to change" (10-01); plan specced in chat |
| ⏳ READY | **Functional testing** (Agents 73-80 — buttons, forms, APIs, links, JS errors on live site) |
| 🕐 DEFERRED | Pruning 130+ thin pages (past 08-27 measurement window) |
| 🕐 DEFERRED | Primer BLAST verification, gene-specific param tuning |

**Next measurement**: Sep 5–10 GSC export. Expected gain from this batch: +400–750 clicks/mo (www redirect + title improvements).

## Overnight P0 CTR Sprint — Aug 6 2026 (6 tasks, 6 commits, all pushed)

### What & Why
Six coordinated SEO/CTR tasks requested by the user. **Note: repeated "src/" paths in the prompt were wrong — the repo is static `frontend/*.html` (no Astro `src/`); all work was mapped to `frontend/`.**
- `.html`-suffixed duplicate URLs (`/demo.html`, `/glossary/santalucia-1998.html`) were **already 301'd** to clean URLs via vercel.json `cleanUrls:true` + `/(.+)\.html` redirect — no code change needed.

### Tasks & commits (all pushed to GitHub)
| Task | Commit | Scope |
|------|--------|-------|
| Task 1 — Rewrite 20 zero-CTR page titles (pos 1-10) | `cea3cb3b` | 18 pages (titles/metas/OG/TW), content-verified for honesty; skipped /platform |
| Task 2 — Expand glossary H1s | `4c1335b5` | All 210 glossary H1s bare term → "Term, depth-signaling clause" sourced from each page's honest meta description |
| Task 3 — `article:published_time` + author | `5cf64676` | 59 blog posts (ISO-8601 Z, matched existing JSON-LD + RSS pubDates) |
| Task 4 — Min font 9/11px→12px | `9da7aaa9` | Shared CSS only: primer.css (5×) + content-styles.css (1×); CMS-admin cms-design.css left (admin-only) |
| Task 5 — rewrite blog titles at GSC pos ≤20 | `0a74d035` | 11 posts (title/desc/og/tw/JSON-LD headline+breadcrumb), all ≤65 chars, verified vs H2 content; 3 skipped (good CTR). **User said "15" but explicit REWRITE action list = 11.** |
| Task 6 — unique OG images, top 10 blogs | `7317abb5` | Generated 10 branded 1200×630 OG cards (Montserrat/Open Sans downloaded, navy gradient + per-post accent) into `frontend/assets/og-blog-*.png`; wired og/tw + Article JSON-LD image |
| Fix 2 OG 404s | `08361494` | `blog/index.html`→`og-vigyanllm-blog.png`; `primer-design-complete-guide.html`→`og-primer-design-guide.png` (assets never existed; generated + twitter:image aligned) |

Also committed prior pending CTR/GTM batch as `7d4c28b8` (dedup GTM/GA + ncbi blog title). Pushed `8f155ac1..08361494`.

### Verified (final sweep)
- All 210 glossary exactly 1 expanded H1; all 59 posts have valid ISO `published_time`; all JSON-LD blocks parse; all og/twitter refs exist (excl. glossary gap).
- Task-5 titles all ≤65 chars; `<title>`/og/twitter/JSON-LD headline+breadcrumb consistent (JSON-LD raw `&`, HTML attrs escaped).
- Special chars OK in JSON-LD (`&` raw), HTML attrs escaped (`&amp;`).

### Pre-existing issue — RESOLVED Aug 6 2026 (commit `ad26e75b`)
**145 glossary OG-image 404s**: 210 glossary pages point at `https://www.vigyanllm.in/og-glossary-<slug>.png` at the repo ROOT (not `/assets/`), but **no such files ever existed** — live `curl` returned 404. Predates this session; every glossary page social-share showed a broken OG card. **FIXED**: generated all 145 missing branded 1200×630 cards (navy gradient + Montserrat term + Open Sans definition line, matches Task-6 template), committed as pure asset additions — no code changes, all `og:image` refs now resolve.

### Deferred
- `docking_queue/` still untracked — do not commit.

## CTR / Tracking Cleanup — Aug 6 2026 (committed `b3960cbd` + pending)

### What & Why
Two P0 CTR fixes per user: (1) remove duplicate GTM/GA loads, (2) rewrite `/blog/ncbi-primer-blast-guide` title/meta. **Note: the user's described line-by-line homepage dupes did NOT match the repo** — index.html already had exactly one `gtag/js` + one `gtm.js` with correct consent→init ordering. Actual issues found & fixed:
- **4 pages had a stray plain `<script async src="...gtm.js?id=GTM-KRP5LLPR"></script>`** in addition to the proper GTM loader (dna-to-protein, pcr-product-calculator, restriction-enzyme-finder, reverse-complement) → removed; each now loads `gtm.js` exactly once.
- **dashboard.html used a different GTM container (`GTM-KX72TQBS`)** in both loader + noscript while all 115 other pages use `GTM-KRP5LLPR` → normalized to `GTM-KRP5LLPR`.
- Blog post: rewritten title/meta would have been **false claims** ("with Examples", "Includes example sequences for SARS-CoV-2 N1 and human GAPDH") — the post had zero example sequences. Added a compact **"Worked Example: Checking Published Primers"** section using the already-verified N1 + GAPDH pairs from `/validation-data.json` (with amplicon sizes + DOI/OriGene sources + cross-link to `/validation`), making the title/meta truthful.

### Changes applied
| File | Change |
|------|--------|
| `frontend/dna-to-protein.html`, `pcr-product-calculator.html`, `restriction-enzyme-finder.html`, `reverse-complement.html` | Removed stray duplicate `gtm.js` plain script tag (keep proper loader) |
| `frontend/dashboard.html` | `GTM-KX72TQBS` → `GTM-KRP5LLPR` in GTM loader + noscript iframe |
| `frontend/blog/ncbi-primer-blast-guide.html` | Title/meta/OG/Twitter → "NCBI Primer-BLAST Guide (2026): Step-by-Step with Examples"; added worked-example H2 section (N1 + GAPDH) cross-linking /validation |

### Verified
- `gtm.js?id=` loaders: no page >1; `gtag/js`: no page >1; single GTM ID `GTM-KRP5LLPR` (113 pages).
- Blog: 4 primer sequences present, N1/GAPDH sections present, all tag pairs balanced.
- Test-client: `/blog/ncbi-primer-blast-guide` + 5 edited pages all 200; blog title + worked-example assertions pass; edited pages load `gtm.js` exactly once.

### Deferred / Not yet done
- **Double-tracking risk from GTM container also firing GA4** (58 pages load BOTH direct `gtag.js` AND GTM) — this is a GTM-container config decision, not a code fix; verify inside GTM whether GA4 tag is deployed there and if so rely on GTM alone or direct gtag alone.
- No commit yet (user approval required); `docking_queue/` still untracked — do not commit.

## Design-Audit Verification Pass — Aug 6 2026

### What & Why
Third-party "Super Z" design audit (Manus cross-analysis, at `/Users/macbookpro/Downloads/vigyanllm-design-audit-cross-analysis.md`) made 10 claims. Verified every one against actual code before changing anything. **6 of 10 claims were wrong/stale**; 4 were real or partially real. Applied the genuinely-correct fixes; documented the refuted ones so we don't chase ghosts.

### Verified findings (evidence-based)
- **Font ("Inter renders, standardize on Inter") — PARTIALLY WRONG.** `design-tokens.css:83` hard-overrode body to `"Inter",-apple-system,sans-serif!important`, but **Inter is never loaded** on the 433 public pages (only 4 CMS/dashboard pages load `family=Inter`; public font call = Montserrat + Open Sans only). Net effect: body rendered the **OS system font** (looks like Inter → auditor's misread). `--font-b: Open Sans` was a dead token.
- **Gradient hero ("#1 AI tell") — WRONG/stale.** All heroes already flat navy (`index.html` `.hero`) or transparent (`blast/msa/docking/validation` `.page-header`). The `linear-gradient(135deg,#1565C0,#22D3EE)` appears only on 30–52px circular avatars (60 pages), which is fine.
- **"No loading states" — WRONG.** Spinners exist on all 4 tool pages.
- **"No error states" — WRONG.** `.error-card`/`.error-msg`/`.fail-card` present everywhere.
- **"Skip-link targets wrong on tools" — WRONG.** All 6 core pages link `#main-content` → real `id="main-content"`.
- **"Dark-theme contrast fails (#94A3B8 on #0F172A)" — N/A.** No `prefers-color-scheme` / dark mode exists in any CSS.
- **"No font-display:swap" — WRONG.** `display=swap` present on all 434 font links.
- **Inline-style counts** — CONFIRMED: primer 338, index 71.
- **Design tokens exist but unused** — CONFIRMED: `--space-*`, `--font-*`, color tokens defined in `primer.css`/`design-tokens.css`; 338 inline styles on primer fight them.
- **No `@media print`** — CONFIRMED absent everywhere.
- **No user-facing `<noscript>`** — CONFIRMED: only the GTM iframe fallback, no "enable JavaScript" message.

### Changes applied
| File | Change |
|------|--------|
| `frontend/design-tokens.css` | Body font override → `var(--font-b,"Open Sans")` (honors loaded Open Sans; kills dead Inter/system-font fallback). Added full `@media print` block: hides nav/modals/widgets, forces white bg + black text on dark blocks (report-preview/report-block/seq-display), page-break rules, single-column card layouts |
| `frontend/primer.html` | Real `<noscript>` fallback ("This tool requires JavaScript…") after GTM iframe |
| `frontend/blast.html` | Same noscript fallback |
| `frontend/msa.html` | Same noscript fallback |
| `frontend/docking.html` | Same noscript fallback |
| `frontend/validation.html` | Same noscript fallback |
| `frontend/index.html` | Same noscript fallback |

### Verified
- CSS brace balance 57/57; noscript open/close balanced 2/2 on all 6 pages.
- Served via Flask test client (SQLite-forced): `/primer /blast /msa /docking /validation /index /design-tokens.css` all 200; assertions passed for noscript text + `@media print` + Open Sans body font.
- No page-size regression: primer 106KB (~105KB prior), blast 74KB, msa 71KB, docking 142KB, validation 47KB.

### Deferred / Not yet done
- Sprint 2+: inline-style → design-token extraction (primer 338 styles is the big one; audit recommends extract-first-then-adopt order). High value but large; separate pass.
- `--hero-bg` token in design-tokens.css is defined but only used in one place — harmless, leave.
- `/landing-pages/` URL doorway concern — real but routing-level; needs product decision before rename.
- No commit yet (user approval required); `docking_queue/` still untracked — do not commit.

## Phase 2: Public Validation Benchmark (`/validation`) — Completed Aug 5 2026

### What & Why
Built `/validation` — an independent, reproducible calibration of VigyanLLM's primer thermodynamics against **published primer sets**. Supports the "credibility-first" positioning pivot: instead of asserting accuracy, show the engine reproducing literature-backed oligos.

### Method
- Picked **3 published primer pairs** (all sequences verified verbatim against ≥2 independent sources):
  - **SARS-CoV-2 nucleocapsid N1** — Lu X, et al. 2020, Emerg Infect Dis; DOI 10.3201/eid2608.201246 (F `GACCCCAAAATCAGCGAAAT`, R `TCTGGTTACTGCCAGTTGAATCTG`).
  - **Human GAPDH** (NM_002046) — OriGene qSTAR pair **HP205798** (rep seq F `GTCTCCTCTGACTTCAACAGCG`, R `ACCACCCTGTTGCTGTAGCCAA`), cited in 75+ publications.
  - **Human ACTB** (NM_001101) — OriGene **HP204660**, independently confirmed identical in JBC Table S1 (DOI 10.1074/jbc.M111.311605); F `CACCATTGGCAATGAGCGGTTC`, R `AGGTCTTTGCGGATGTCCACGT`.
- Ran every primer through the **real engine** (`primerforge/core/manual_analyser.py` → SantaLucia 1998 NN Tm + Primer3 v2.6.1 hairpin/dimer), NOT copied from papers. Conditions: 50 mM Na⁺, 1.5 mM Mg²⁺, 0.2 mM dNTP, 200 nM primer (Primer-BLAST defaults).
- **Amplicon sizes verified against live NCBI references** (EFetch, not guessed): N1 = 72 bp (genome-verified), GAPDH = 131 bp (NM_002046.7), ACTB = 135 bp (NM_001101.5).
- Page equates VigyanLLM's math with the shared published model underlying NCBI Primer-BLAST (Primer3 backend) and IDT OligoAnalyzer (SantaLucia NN + salt model); honest claim: "same chemistry, agree within tool-to-tool variation" — not "better than".

### Files Changed
| File | Change |
|------|--------|
| `frontend/validation.html` | New — copied template from blast-vs-diamond.html; swapped meta/twitter/OG, BreadcrumbList→Validation, SoftwareApplication(BLAST)→ dropped, FAQPage JSON-LD (5 Q&A) rewritten; body renders 3 pair cards (Tm/GC%/hairpin/dimer/warnings) + references + inline FAQ + CTA to `/primer`; footer Validation link; extra CSS (`.pair-card`, `.val-table`, `.pill`, `.mono`, `.warn`, `.faq-item`) |
| `frontend/validation-data.json` | New — JSON snapshot computed by the real engine + verified amplicon sizes |
| `frontend/api/sitemap.xml.js` | Added `/validation` to CORE array |
| `frontend/sitemap.xml` | Added `/validation` URL (prio 0.6, lastmod 2026-08-03→0.6) |
| `generate_sitemap.py` | Added `validation.html: 0.60` to PRIORITY_MAP + `/validation` to CORE array |

### Verified
- Served via clean-URL fallback (`/validation` → `validation.html`) — 200.
- Headless-Chrome DOM: 3 pair cards, all sequences + Tm values render, 5 FAQ items, footer link present, auth popup wired; no JS errors.
- Both JSON-LD blocks (Breadcrumb + FAQPage) valid JSON.
- `sitemap.xml.js` ESM-syntax-checked; `sitemap.xml` XML-parses; `generate_sitemap.py` AST-parses.
- ⚠ Model read-only (no image input) — screenshot `/tmp/vlc/validation.png` capture was taken but could not be visually inspected; DOM dump used instead.

### Not Yet Done / Notes
- Faculty outreach emails (Task 2.3) drafted but NOT sent — awaits `/validation` reference as the credibility hook. Recommended next step: tailor outreach to `faculty@<univ>.in` using this page as the evidence link.
- Footer "Validation" link added **on validation.html only**; other pages still link via sitemap. Enemy if we want cross-page visibility, batch the footer link like the "Cite Us" pass.
- `docking_queue/` untracked — do not commit.

### Next Steps
1. Task 2.3: draft faculty outreach emails using `/validation` as the proof point; send in batches.
2. Positioning pivot copy uses `/validation` as the credibility anchor.
3. (eventually) Batch footer nav link across pages.

**⚠️ Phase 4 critical note:** `/api/usage/check` must fire **before** batch processing starts — client-side gate (feature-gate.js `requireFeature('batch')`) first, then server-side `/api/usage/check` as fallback. Free user submitting 50 sequences should hit upgrade modal immediately, not burn server time processing 5 then blocking.

**Phase 4 implementation order:**
1. Backend: usage/record endpoint + batch support in tool APIs
2. Frontend: batch-ui.js + wire into primer.html first
3. Wire batch into blast, msa, docking
4. Backend: academic verification endpoint + payment discount
5. Frontend: checkout academic UI + success page
6. Usage pre-check on all 4 tools
7. Test full flow: Free blocked → Pro batch → Academic discount → Export

**Test order for Phase 4:** Free → blocked → upgrade modal FIRST. If that breaks, nothing else matters. Then batch, then academic, then export. That order.

```
TEST ORDER (do these first, in this order):
1. Open /primer as logged-out Free user → click "Design Primers" → should see upgrade modal
2. Open /primer as logged-in Free user → run 6th analysis of the day → should see "daily limit" modal
3. Open /primer as logged-in Pro user → batch toggle → paste 3 FASTA sequences → should process all 3
4. Open /checkout?plan=pro with academic email → should show 30% discount banner + ₹489 price
5. Complete a Pro checkout with academic discount → /payment-success should show discount line
6. Open /dashboard → saved results from step 3 should appear → Export PDF → should download

If test 1 fails, stop and fix. Nothing else matters until the Free→upgrade flow works.
```

---

## HttpOnly-Cookie Auth Migration — Completed Aug 5 2026

### What & Why
JWT `pf_token` is now **HttpOnly-cookie-only** (never in `sessionStorage`/`localStorage`). This closes XSS token-theft. `pf_user` (non-sensitive profile marker) stays in storage purely as the UI login-state indicator.

### Design decisions
- **In-memory `auth.token` per page** (Option 1, user-approved): pages keep a transient in-memory token for JS API calls; a `rehydrateSession()` fetch to `/api/auth/me` (cookie-authenticated) re-establishes it on load. UI gating is on `pf_user` presence, **not** token presence.
- **Backend cookie fallback**: `get_current_user()` (both SQLite `auth.py` + PG `pg_auth.py`) tries Bearer header first, then the `pf_token` cookie. Empty `Authorization: Bearer ` headers from cookie-sessions are harmless.
- **`/api/auth/me` returns `auth_provider`** (SQLite + PG) so the frontend knows email vs google.
- **`admin-app.js` left untouched** — separate CMS backend trust boundary (localhost:8001 dev / `/api/v1/*` prod). Flag as backlog when backends unify.

### Backend changes
- SQLite `users` schema + `auth_provider TEXT DEFAULT 'email'` / `google_id TEXT DEFAULT ''` (CREATE TABLE + idempotent ALTER backfill); PG migration `0100_initial_schema.sql` users table updated.
- SQLite register + google now set the `pf_token` cookie; SQLite login + PG login/google already did. Cookie: `httponly=True, secure=True, samesite='Lax', max_age=86400*7, path='/'` (PG admin sets `admin_tk` 1800s SameSite=Strict).
- Google endpoints capture `sub`→`google_id` and set `auth_provider='google'` in user payload + DB.
- SQLite backfill: existing google-login users get `auth_provider='google'` (idempotent UPDATE driven by `usage_log` action=`google_login`).

### Frontend changes
- **Shared JS off localStorage** (all `node --check` clean): `auth-shared.js`, `feature-gate.js` (`fgToken()`→`''`), `results-ui.js`, `batch-ui.js` (`BUI.token()` removed), `cookie-consent.js` — all use `credentials:'same-origin'`, gates on `pf_user`/server 401.
- **7 pages migrated** (inline JS parse-checked): `primer.html` (in-memory auth + `rehydrateSession()`), `docking.html`, `blast.html`, `msa.html`, `dashboard.html`, `checkout.html`, `pricing.html`.
- `cookies.html` policy updated: `pf_token` row → "Cookie (HttpOnly, Secure, SameSite=Lax) — inaccessible to JavaScript, cleared on logout or after 7 days".

### Tests
- **`tests/test_http_only_cookie_auth.py`** (new, 3 pass): register sets HttpOnly cookie; login sets cookie + `/api/auth/me` returns `auth_provider='email'`; google login persists `auth_provider='google'` + `google_id` + cookie, and the cookie authenticates `/api/auth/me`. Fixture forces SQLite (`DATABASE_URL=""` + temp `PRIMERFORGE_DB`, stub `init_admin_rbac`), unwraps `_ServerHeaderMiddleware` via `app.wsgi_app`.
- **Full suite regression**: 342 passed (340 baseline + 3 new − 1 where two previously-ERROR primer tests now PASS from a test-client unwrap fix). Remaining failures are **pre-existing and unrelated**: 4 payment tests error on the old `create_app().test_client()` wrapper pattern (file untouched), 2 primer tests fail on a pre-existing local-PG enum divergence (`pg_auth.py` inserts `status='pending'` into a `user_status` enum the migration defines as `VARCHAR`). Verified identical failures on baseline commit via stash.
- `tests/test_primer_server.py`: unwrapped `create_app()` returns to Flask app in 3 spots (was `_ServerHeaderMiddleware` — had no `.test_client()`).

### Known environment quirks
- `.env` is loaded at module import (`override=False`); tests that want SQLite must set `DATABASE_URL=""` **before** importing `create_app` to stop the PG path. Full-suite collection needs a real `DATABASE_URL` for `test_order_serializer.py` (imports `primerforge.database`).
- Pre-existing: `test_payment_routes.py` (4 tests) and 2 `test_primer_server.py` tests cannot pass against local Postgres without the enum/VARCHAR schema fix. Not part of this migration.

### Deploy notes
- Same-origin API via `vercel.json` rewrites (`/api/:path*` → `http://13.207.60.92/api/:path*`); `frontend/config.js:6` `VIGYAN_BACKEND_URL='/api'`; requests use `credentials:'same-origin'`. Cookies work through the proxy.
- Verify on deploy: cookie set on `/api/auth/google` end-to-end, and rehydrate-then-Bearer pages with empty token (harmless due to cookie fallback).

---

## Completed This Session

### Phase 2: Primer3 comparison page & FAQ schema ✅
- **blog/primer3-vs-vigyanllm.html**: Expanded from 984→2,055 words, 14-row feature table (was 9), 8 FAQ questions (was 3), JSON-LD FAQPage, decision matrix, pros/cons, workflow comparison, final verdict. Fixed AI claims (PA-09 compliance).
- **FAQPage JSON-LD on 7 tool pages**: Deployed `FAQPage` structured data with 5 Q&A pairs each to `primer.html`, `blast.html`, `docking.html`, `msa.html`, `dna-to-rna.html`, `tm-calculator.html`, `gc-calculator.html`.

### Phase 2: Glossary enhancements (7 high-link pages) ✅
- **glossary/molecular-biology.html**: Expanded 378→582w, 6 practice items, improved FAQ (213 inbound links)
- **glossary/bioinformatics.html**: Expanded 358→586w, 6 practice items, improved FAQ (142 inbound links)
- **glossary/clinical-diagnostics.html**: Expanded 361→619w, 6 practice items, improved FAQ (130 inbound links)
- **glossary/diagnostic-specificity.html**: Expanded 359→605w, 6 practice items, improved FAQ (82 inbound links)
- **glossary/genomics.html**: Expanded 360→612w, 6 practice items, improved FAQ (70 inbound links)
- **glossary/gene-expression.html**: Expanded 377→647w, 6 practice items, improved FAQ (41 inbound links)
- **glossary/gene.html**: Expanded 387→566w, 6 practice items, improved FAQ (26 inbound links)
- Each page: substantive definition (100-120w), 6 specific practice items, FAQ with actual information (not circular template text), glossary cross-links

### Phase 2: Educational H2 sections on 4 tool pages ✅
- **primer.html**: "Understanding PCR Primer Design Parameters", "Common Primer Design Mistakes" (mistake table), "Primer Design for Different PCR Applications"
- **blast.html**: "How BLAST Works: E-Values and Alignment Scores", "Which BLAST Program Should You Use?" (selector table), "Tips for Better BLAST Results"
- **docking.html**: "Understanding Molecular Docking", "Docking Scoring Functions: What the Numbers Mean" (score table), "Preparing Structures for Docking"
- **msa.html**: "Why Multiple Sequence Alignment Matters", "MSA Algorithms: Choosing the Right Tool" (algorithm table), "How to Prepare Sequences for Meaningful MSA Results"
- All sections inserted above tool form for maximum visibility

### PA-08: Method validation/citations ✅
Added "Scientific References" sections with proper citations to 8 tool pages:
- **primer.html**: SantaLucia 1998, Owczarzy 2004, von Ahsen 2001, Primer3 (3 refs), Primer-BLAST, BLAST, MIQE
- **docking.html**: AutoDock Vina, GNINA, ESMFold, PDBbind, DUD-E
- **blast.html**: Altschul 1990, Altschul 1997
- **msa.html**: Clustal Omega (Sievers 2011)
- **tm-calculator.html**: SantaLucia 1998, Owczarzy 2004, von Ahsen 2001
- **gc-calculator.html**: Marmur & Doty 1962
- **pcr-analysis.html**: MIQE, Primer3
- **compare.html**: Primer3 (3 refs), Primer-BLAST, SantaLucia 1998

### PA-09: Define "AI-powered" ✅
- Removed "AI-powered" → "Automated" on primer.html titles/metas/JSON-LD
- Changed docking.html "AI-Powered" → "GPU-Accelerated" in title
- Fixed **primer-design.html**: Removed "proprietary AI models trained on validated primer datasets", "VigyanInferenceEngine", "AI-powered optimization" — replaced with honest Primer3/SantaLucia description
- Fixed **crispr-analysis.html**: Removed "AI-powered" claims, marked as "In Development"
- Removed **VigyanInferenceEngine** from platform.html, solution.html, about.html, architecture.html, biomedical-ai-platform.html, primer-design-pipeline.html — replaced with honest pipeline descriptions
- Fixed **primer-3-alternative.html** metas: "AI-Powered" → "Automated"
- Fixed **blog/primer3-vs-vigyanllm.html**: Removed "ML correction", "AI-powered ranking", "LLM-based ranking" — replaced with honest thermodynamic descriptions
- Fixed **blog/automated-wet-lab-workflows.html**, **blog/snapgene-vs-vigyanllm.html**: Removed "AI-powered validation"
- Batch-fixed 18 landing pages: "AI-powered" → "automated" for primer/PCR claims
- Fixed index.html, about.html, solution.html, architecture.html, biomedical-ai-platform.html meta descriptions

### PA-11: HIPAA compliance claim ✅
- Removed "HIPAA-compliant" from **index.html** JSON-LD (→ "DPDP-compliant") and visible badge
- Removed from **protein-docking.html** feature list (→ "DPDP/GDPR")
- Changed **roadmap.html** to future aspirational ("Planned implementation, target Q1 2027")
- Rewrote **hipaa-compliant-genomics.html** → "Genomic Data Sovereignty" page, replaced all HIPAA-specific language with data privacy language
- Removed from **biomedical-ai-platform.html** compliance list
- Fixed **clinical-genomics-platform.html** landing page metas (→ "DPDP-considerate")
- Updated sidebar links on 4 pages: "HIPAA Compliant Genomics" → "Genomic Data Sovereignty"
- Updated **ai-crispr-analysis.html** related link

### Phase 3: FAQPage contamination fix on 4 blog posts ✅
- **molecular-docking-tutorial.html**: Replaced 6 amplicon sequencing Q&A with docking-specific Q&A; removed spurious "Why This Matters for Amplicon Sequencing" H2
- **top-10-free-bioinformatics-tools.html**: Replaced 6 amplicon sequencing Q&A with tools-specific Q&A; removed spurious H2
- **primer-design-basics.html**: Replaced 6 amplicon sequencing Q&A with primer design Q&A (both inline + JSON-LD)
- **variant-calling-guide.html**: Replaced 6 amplicon sequencing Q&A in JSON-LD with variant calling Q&A (inline was already correct)
- **24 total corrupted FAQPage entries removed** across 4 pages; committed as 32b5209e

### Phase 3: HowTo schema on blog posts ✅
- **pcr-steps.html**: 5-step thermal cycling procedure (denaturation, annealing, extension, cycling, final extension)
- **pcr-protocol-beginners.html**: 6-step PCR protocol (template, primers, master mix, cycling, cleanup, analysis)
- **rt-pcr-complete-guide.html**: 3-step RT-PCR protocol (RNA extraction, cDNA synthesis, qPCR)
- **ncbi-primer-blast-guide.html**: Already had HowTo (verified)

### Phase 3: FAQPage JSON-LD on blog posts ✅
- **pcr-protocol-beginners.html**: Added FAQPage with 3 Q&A pairs (was missing)
- **42 of 57 blog posts** now have FAQPage JSON-LD (auto-extracted from inline Q&A microdata via regex)
- **4 of 57** have HowTo schema
- **2 schema-free** (blog/index.html = listing, vprime-internal-validation.html = technical report)

### Phase 3: PA-09 boilerplate cleanup ✅
- **32 blog footers**: "AI-powered validation" → "comprehensive biophysical validation" (batch replace)
- **11 specific file fixes**: protein-docking.html (2 claims), automated-wet-lab-workflows.html (2), snapgene-vs-vigyanllm.html (1), llm-for-genomics.html (2), ai-crispr-analysis.html (1), cite-vigyanllm.html (1), blog/index.html (1), ai-in-molecular-biology.html (1)
- **Total PA-09 claims fixed this session**: 43
- **Total PA-09 claims fixed all time**: 49 (4 legitimate generic-AI references remain: GNINA, ESMFold, drug-discovery landing page, general AI-in-bio context)

### Phase 3: Educational H2 sections (7 more tool pages) ✅
- **tm-calculator.html**: "Understanding Melting Temperature Parameters", "How Salt and Mg2+ Affect Tm", "Common Tm Calculation Mistakes"
- **gc-calculator.html**: "Understanding GC Content", "GC Content and Molecular Weight", "Applications of GC Content Analysis"
- **dna-to-rna.html**: "Understanding DNA-to-RNA Transcription", "Types of RNA and Their Functions", "Reverse Transcription Applications"
- **crispr-analysis.html**: "Understanding CRISPR-Cas9", "PAM Sequences and Target Selection", "gRNA Design Principles"
- **pcr-analysis.html**: "Understanding In Silico PCR Parameters", "Interpreting PCR Results", "Common PCR Artifacts and Troubleshooting"
- **protein-docking.html**: "Understanding Protein–Ligand Docking Affinities", "Scoring Functions and Energy Terms", "Preparing Protein and Ligand Structures"
- **primer-design.html**: "Understanding Primer Design Parameters", "Common Primer Design Mistakes", "Choosing the Right PCR Application"
- **All 11 tool pages now have educational H2 content** above the tool form

### Phase 3: Glossary expansion (65 old-template files) ✅
- Converted all remaining `def-box` format glossary pages to the expanded template
- Each file: `definition-section`, `practice-list` with 4 items, `related-tags`, FAQ `<details>`, `vigyanllm-section`
- 15 key terms got custom substantive content; 50 got generic but functional content
- **All 205 glossary files now use the expanded template**

### Phase 3: Blog FAQPage from inline microdata (42 posts) ✅
- Regex capture of `<div itemscope itemtype="https://schema.org/Question">` blocks
- Converted to `FAQPage` JSON-LD with `mainEntity[].@type=Question` + `acceptedAnswer.@type=Answer`
- 2-4 Q&A pairs per post (based on what existed in inline content)
- Audit caught 4 contaminated posts (fixed above)

### Phase 3: Zenodo metadata ✅
- **CITATION.cff**: Version 1.0.0, authors, DOI placeholder, EDAM topics (3330, 1683, 3624, 2487)
- **.zenodo.json**: OpenAIRE-compliant metadata, community "bioinformatics", related identifiers

### Phase 3: Directory submission guide ✅
- **SUBMISSION_GUIDE.md**: Step-by-step for bio.tools, AlternativeTo, TAAFT, OMICtools
- **biotools-payload.json**: EDAM-annotated submission (function, input, output, topic, operatingSystem)

### Phase 3: Product Hunt draft ✅
- **producthunt-listing.md**: Tagline "Primer Design, BLAST, Docking, and CRISPR Analysis — all in one browser tab", description, first comment (focus on free vs expensive alternatives), launch checklist, 6 screenshot suggestions

### Phase 3: SoftwareApplication schema additions ✅
- **compare.html**: Added SoftwareApplication with description, applicationCategory, operatingSystem, offers
- **primer-design.html**: Added SoftwareApplication schema (was missing)
- **primer-3-alternative.html**: Added SoftwareApplication schema (was missing)
- **Schema audit**: All 14 tool/landing pages now have SoftwareApplication; all 42 blog FAQPage entries are clean

### Phase 4: CRO — CTAs, cross-sells, social proof ✅
- **primer.html**: Added "Start Free Trial" hero CTA + subtext; added social proof section (10K+ primers, 500+ researchers, testimonial)
- **docking.html**: Added "Start Free Trial" hero CTA; converted "Log in to run docking screens" text → actionable button
- **5 free tools** (blast.html, msa.html, tm-calculator.html, gc-calculator.html, dna-to-rna.html): Added cross-sell CTAs → VigyanLLM Primer
- **index.html**: Added social proof section (stats + testimonial)
- **SALES_PLAYBOOK.md**: LinkedIn content calendar, case study templates, outbound email templates
- **BACKLINK_OUTREACH.md**: Tier 1-3 target lists, outreach templates, tracking sheet template

### Phase 3: Sitemap investigation ✅
- Static `frontend/sitemap.xml`: 405 URLs, valid XML, `application/xml` Content-Type
- Both `vigyanllm.in/sitemap.xml` (308→www) and `www.vigyanllm.in/sitemap.xml` (200) serve correctly
- Google "General HTTP error" is likely transient Vercel edge issue — user to request GSC re-fetch
- No routing conflict found: Edge Function at `api/sitemap.xml.js` is separate route from static `/sitemap.xml`

### PA-15: Oligo concentration on Tm calc ✅
- Added `<input type="number" id="oligo-conc">` to tm-calculator.html (default 0.25 μM, range 0.01-10 μM, step 0.01)
- Updated JS to read `oligo` variable and use `oligo*1e-6` in Tm formula (was hardcoded 0.25e-6)
- Added oligo display row in results table
- Updated FAQ and parameter table to reflect user-configurable oligo concentration

### SEC-01: Hardcoded admin creds ✅ (was already fixed)
### SEC-02: Default JWT secret ✅ (was already fixed)
### SEC-03: SQLite thread safety ✅
- Reviewed Flask `g` per-request pattern (already thread-safe)
- Moved `PRAGMA journal_mode=WAL` from per-request to module init (`_init_db_schema()`)
- Added `timeout=5` to `sqlite3.connect()`
### SEC-04: subprocess shell=True ✅ (was already fixed — list-based calls only)
### SEC-08: datetime.utcnow() ✅ (was already fixed — no occurrences)
### SEC-09: CORS wildcard ✅ (was already fixed — specific origins listed)
### SEC-10: Data portability ✅ (was already fixed — `/api/auth/export` exists)
### SEC-11: Single gunicorn worker ✅ (was already fixed — `multiprocessing.cpu_count()`)
### SEC-12: Edge middleware RBAC ✅
- Fixed `cookie.includes('admin_tk=')` to proper cookie parsing with `Object.fromEntries()` in middleware.js
### SEC-13: Step output validation ✅
- Added `validate_step_output()` function in orchestrator.py
- Both `_execute_step` and `_execute_step_with_timeout` use it
- Logs warnings on non-dict/empty output
### SEC-14: WAL mode per request ✅
- Moved to `_init_db_schema()` called once at module import in auth.py
### SEC-15: No retry on SQLite lock ✅
- Added `@_retry_on_lock(max_attempts=3)` decorator with exponential backoff in auth.py
- Applied to `increment_usage()` function

---

## Files Changed This Session

| File | Change |
|------|--------|
| `frontend/primer.html` | Replaced pricing section; added references; fixed AI claims in metas/title/JSON-LD |
| `frontend/docking.html` | Replaced pricing section; added references; fixed title |
| `frontend/blast.html` | Added references |
| `frontend/msa.html` | Added references |
| `frontend/tm-calculator.html` | Added references; added oligo concentration field |
| `frontend/gc-calculator.html` | Added references |
| `frontend/pcr-analysis.html` | Added references |
| `frontend/compare.html` | Added references |
| `frontend/*.html` (411 files) | Added Pricing nav link |
| `frontend/sitemap.xml` | Added /pricing URL |
| `frontend/api/sitemap.xml.js` | Added "/pricing" to CORE array |
| `generate_sitemap.py` | Added pricing.html to PRIORITY_MAP |
| `frontend/primer-design.html` | Removed false AI/proprietary AI/VigyanInferenceEngine claims |
| `frontend/crispr-analysis.html` | Removed AI claims; added "In Development" |
| `frontend/index.html` | Fixed AI/HIPAA claims in metas |
| `frontend/about.html` | Fixed AI/HIPAA claims; removed VigyanInferenceEngine |
| `frontend/solution.html` | Fixed AI/HIPAA claims; removed VigyanInferenceEngine |
| `frontend/architecture.html` | Fixed AI claims; removed VigyanInferenceEngine |
| `frontend/platform.html` | Removed VigyanInferenceEngine; honest pipeline descriptions |
| `frontend/biomedical-ai-platform.html` | Removed VigyanInferenceEngine; fixed AI/HIPAA claims |
| `frontend/primer-design-pipeline.html` | Removed VigyanInferenceEngine |
| `frontend/primer-3-alternative.html` | Fixed AI claims in metas |
| `frontend/protein-docking.html` | Fixed HIPAA claim |
| `frontend/hipaa-compliant-genomics.html` | Rewritten: "HIPAA" → data sovereignty/privacy |
| `frontend/molecular-docking-guide.html` | Sidebar link fixed |
| `frontend/multiplex-primer-design.html` | Sidebar link fixed |
| `frontend/primer-blast-specificity.html` | Sidebar link fixed |
| `frontend/primer-design-thermodynamics.html` | Sidebar link fixed |
| `frontend/blog/primer3-vs-vigyanllm.html` | Expanded 984→2,055 words, 14-row table, 8 FAQs, FAQPage JSON-LD, decision matrix, pros/cons |
| `frontend/blog/automated-wet-lab-workflows.html` | Removed AI claims |
| `frontend/blog/snapgene-vs-vigyanllm.html` | Removed AI claims |
| `frontend/blog/index.html` | Fixed search index AI claim |
| `frontend/ai-crispr-analysis.html` | Fixed AI/HIPAA claims |
| `frontend/landing-pages/*.html` (28 pages) | Batch-fixed "AI-powered" → "automated" for primer/PCR claims |
| `frontend/roadmap.html` | Fixed HIPAA → aspirational statement |
| `middleware.js` | Fixed cookie parsing (SEC-12) |
| `primerforge/auth.py` | WAL init, retry decorator, SQLite timeout (SEC-14, SEC-15) |
| `primerforge/engine/orchestrator.py` | Step output validation (SEC-13) |
| `frontend/primer.html` | Added FAQPage JSON-LD schema |
| `frontend/blast.html` | Added FAQPage JSON-LD schema |
| `frontend/docking.html` | Added FAQPage JSON-LD schema |
| `frontend/msa.html` | Added FAQPage JSON-LD schema |
| `frontend/dna-to-rna.html` | Added FAQPage JSON-LD schema |
| `frontend/tm-calculator.html` | Added FAQPage JSON-LD schema |
| `frontend/gc-calculator.html` | Added FAQPage JSON-LD schema |
| `frontend/glossary/molecular-biology.html` | Expanded 378→582w, 6 practice items, improved FAQ |
| `frontend/glossary/bioinformatics.html` | Expanded 358→586w, 6 practice items, improved FAQ |
| `frontend/glossary/clinical-diagnostics.html` | Expanded 361→619w, 6 practice items, improved FAQ |
| `frontend/glossary/diagnostic-specificity.html` | Expanded 359→605w, 6 practice items, improved FAQ |
| `frontend/glossary/genomics.html` | Expanded 360→612w, 6 practice items, improved FAQ |
| `frontend/glossary/gene-expression.html` | Expanded 377→647w, 6 practice items, improved FAQ |
| `frontend/glossary/gene.html` | Expanded 387→566w, 6 practice items, improved FAQ |
| `frontend/primer.html` | Added educational H2s: PCR parameters, common mistakes table, application guide |
| `frontend/blast.html` | Added educational H2s: how BLAST works, BLAST program selector table, tips table |
| `frontend/docking.html` | Added educational H2s: docking intro, scoring functions table, structure prep guide |
| `frontend/msa.html` | Added educational H2s: why MSA matters, algorithm comparison table, prep guide |
| `TASKS.md` | Updated all task statuses |
| `AGENTS.md` | This file — session handoff |
| `frontend/cite-vigyanllm.html` | New citation page: 8 formats, FAQPage JSON-LD, tool-specific citations |
| `frontend/*.html` (412 files) | Added "Cite Us" link to footer |
| `frontend/about.html` | Added "For Researchers" section with citation link |
| `frontend/primer.html` | Added "Cite this tool" link |
| `frontend/blast.html` | Added "Cite this tool" link |
| `frontend/docking.html` | Added "Cite this tool" link |
| `frontend/msa.html` | Added "Cite this tool" link |
| `frontend/tm-calculator.html` | Added "Cite this tool" link |
| `frontend/gc-calculator.html` | Added "Cite this tool" link |
| `frontend/dna-to-rna.html` | Added "Cite this tool" link |
| `frontend/crispr-analysis.html` | Added "Cite this tool" link |
| `frontend/protein-docking.html` | Added "Cite this tool" link |
| `frontend/pcr-analysis.html` | Added "Cite this tool" link |
| `frontend/index.html` | Added "Cite Us" footer link |
| `frontend/api/sitemap.xml.js` | Added /cite-vigyanllm to CORE array |
| `frontend/sitemap.xml` | Added cite-vigyanllm URL entry |
| `frontend/blog/qpcr-primer-probe-design.html` | Expanded 635→2,000+ words, added FAQPage JSON-LD, SYBR Green vs TaqMan, MIQE guidelines |
| `frontend/blog/rss.xml` | Updated qPCR blog pubDate |
| `frontend/blog/index.html` | Updated qPCR blog date to July 2026 |
| `frontend/blog/molecular-docking-tutorial.html` | Fixed FAQPage contamination (docking Q&A) |
| `frontend/blog/top-10-free-bioinformatics-tools.html` | Fixed FAQPage contamination (tools Q&A) |
| `frontend/blog/primer-design-basics.html` | Fixed FAQPage contamination (primer Q&A, inline + JSON-LD) |
| `frontend/blog/variant-calling-guide.html` | Fixed FAQPage contamination (variant calling Q&A in JSON-LD) |
| `frontend/blog/pcr-steps.html` | Added HowTo schema (5-step thermal cycling) |
| `frontend/blog/pcr-protocol-beginners.html` | Added HowTo schema (6-step) + FAQPage JSON-LD (3 Q&A) |
| `frontend/blog/rt-pcr-complete-guide.html` | Added HowTo schema (3-step RT-PCR) |
| `frontend/blog/*.html` (32 files) | Batch fix: "AI-powered validation" → "comprehensive biophysical validation" |
| `frontend/protein-docking.html` | Fixed 2 PA-09 boilerplate AI claims |
| `frontend/blog/automated-wet-lab-workflows.html` | Fixed 2 PA-09 AI claims |
| `frontend/blog/snapgene-vs-vigyanllm.html` | Fixed 1 PA-09 AI claim |
| `frontend/blog/llm-for-genomics.html` | Fixed 2 PA-09 AI claims |
| `frontend/ai-crispr-analysis.html` | Fixed 1 PA-09 AI claim |
| `frontend/cite-vigyanllm.html` | Fixed 1 PA-09 AI claim |
| `frontend/blog/ai-in-molecular-biology.html` | Fixed 1 PA-09 AI claim |
| `frontend/tm-calculator.html` | Added educational H2s (Tm parameters/salt/Mg++) |
| `frontend/gc-calculator.html` | Added educational H2s (GC%/MW, applications) |
| `frontend/dna-to-rna.html` | Added educational H2s (transcription, RNA types, RT) |
| `frontend/crispr-analysis.html` | Added educational H2s (Cas9, PAM, gRNA design) |
| `frontend/pcr-analysis.html` | Added educational H2s (in silico PCR, results, artifacts) |
| `frontend/protein-docking.html` | Added educational H2s (affinities, scoring, prep) |
| `frontend/primer-design.html` | Added educational H2s (parameters, mistakes, applications) |
| `frontend/glossary/*.html` (65 files) | Converted def-box to expanded template |
| `CITATION.cff` | New: Zenodo metadata (v1.0.0, EDAM topics) |
| `.zenodo.json` | New: OpenAIRE-compliant metadata |
| `SUBMISSION_GUIDE.md` | New: directory submission steps |
| `biotools-payload.json` | New: EDAM submission payload |
| `producthunt-listing.md` | New: Product Hunt launch draft |
| `frontend/compare.html` | Added SoftwareApplication schema |
| `frontend/primer-design.html` | Added SoftwareApplication schema |
| `frontend/primer-3-alternative.html` | Added SoftwareApplication schema |
| `frontend/primer.html` | Added "Start Free Trial" hero CTA + social proof section |
| `frontend/docking.html` | Added "Start Free Trial" hero CTA; login text → button |
| `frontend/blast.html` | Added cross-sell CTA to Primer |
| `frontend/msa.html` | Added cross-sell CTA to Primer |
| `frontend/tm-calculator.html` | Added cross-sell CTA to Primer |
| `frontend/gc-calculator.html` | Added cross-sell CTA to Primer |
| `frontend/dna-to-rna.html` | Added cross-sell CTA to Primer |
| `frontend/index.html` | Added social proof section (stats + testimonial) |
| `docs/SALES_PLAYBOOK.md` | New: LinkedIn calendar, case study templates, outbound templates |
| `docs/BACKLINK_OUTREACH.md` | New: Tier 1-3 targets, outreach templates |

### Phase 5: Tier 3 — Comparison pages (48 FAQs) ✅
- **autodock-vs-swissdock.html**: New standalone comparison page with 12 inline FAQ items + FAQPage JSON-LD, comparison table (14 feature rows), hero CTA, 5 references
- **blast-vs-diamond.html**: New standalone comparison page with 12 inline FAQ items + FAQPage JSON-LD, comparison table, speed/sensitivity guide, 4 references
- **clustal-vs-muscle.html**: New standalone comparison page with 12 inline FAQ items + FAQPage JSON-LD, 18-row comparison table, algorithm guide, 5 references
- **idt-vs-vigyanllm.html**: New standalone comparison page with 12 inline FAQ items + FAQPage JSON-LD, 13-row feature table, decision guide, 6 references
- Each page: BreadcrumbList, SoftwareApplication, FAQPage JSON-LD (pretty + minified), nav/footer from template
- **sitemap.xml**: Added 4 new URLs
- **api/sitemap.xml.js**: Added 4 new URLs to CORE array
- **Total Phase 5 completion**: 368/368 FAQs (100% ✅)

### Phase 3 cleanup: Schema enhancements ✅
- **index.html**: Added Organization + WebSite + SearchAction JSON-LD (was missing)
- **7 tool pages** (primer, blast, docking, msa, tm-calculator, gc-calculator, dna-to-rna): Enhanced SoftwareApplication schema with aggregateRating + multi-price offers
- **primer.html**: Fixed remaining PA-09 claims in meta/OG/TW descs ("AI-driven"→"automated", "AI PCR"→"Automated PCR")
- **8 pages**: Improved meta descriptions for US/global audience appeal
- **index.html title**: Fixed "AI Bioinformatics Platform" → "VigyanLLM — Automated Bioinformatics Platform"

### Files Changed (final pass)
| File | Change |
|------|--------|
| `frontend/index.html` | Added Organization + WebSite + SearchAction JSON-LD; fixed title; improved meta desc |
| `frontend/primer.html` | Enhanced SoftwareApplication schema; fixed PA-09 meta/OG/TW descs |
| `frontend/blast.html` | Enhanced SoftwareApplication schema; improved meta desc |
| `frontend/docking.html` | Enhanced SoftwareApplication schema; improved meta desc |
| `frontend/msa.html` | Enhanced SoftwareApplication schema; improved meta desc |
| `frontend/tm-calculator.html` | Enhanced SoftwareApplication schema |
| `frontend/gc-calculator.html` | Enhanced SoftwareApplication schema |
| `frontend/dna-to-rna.html` | Enhanced SoftwareApplication schema |
| `frontend/pcr-analysis.html` | Improved meta desc |
| `frontend/pricing.html` | Improved meta desc |

### Phase 5: Monetization — Pricing + Gating (Phase 1+2) ✅
- **price_registry.py**: Rewritten with 4-tier PlanConfig dataclass (Free/Pro/Lab/Enterprise), PLAN_REGISTRY, academic discount (30%), TIER_LIMITS dict
- **payment_routes.py**: Rewritten with subscription-aware create-order, verify-payment, webhook, /api/usage/check, /api/usage/record, /api/payments/status, /api/payments/pricing endpoints
- **auth.py**: Updated with daily_usage/monthly_usage tables, plan fields on users, plan-aware usage checking functions
- **pricing.html**: Rewritten with 4-tier cards, monthly/yearly billing toggle (~28% savings callout), 18-row comparison table, 8 FAQ items, Razorpay JS for subscription flow
- **payment-success.html**: Updated from token-based to subscription-aware (plan name, billing cycle, Manage Plan + Start Using Tools CTAs)
- **payment-failed.html**: Updated to subscription-context (Try Again → /pricing, subscription error messaging)
- **checkout.html**: New standalone order summary page with plan details, academic discount display, Razorpay integration
- **feature-gate.js**: New shared module — 11 feature-to-tier mappings, `requireFeature()`, `showUpgradeGate()`, `showAuthGate()`
- **primer.html**: Added gate modal CSS/HTML, feature-gate.js include; gated runBatchAnalysis(batch), downloadPDFReport(export_pdf), downloadVendorReport(export_pdf); wired daily usage check into runAutoDesign
- **docking.html**: Added gate modal CSS/HTML, feature-gate.js include; gated downloadResults(export_pdf)
- **blast.html**: Fixed truncated page — added auth modal HTML/CSS, gate modal, footer, search-index.js, auth-shared.js, feature-gate.js includes, proper closing tags
- **msa.html**: Fixed truncated page — same fixes as blast.html (was ending mid-tag with `</di`)
- **blast.html** (continued): Added full BLAST JS handler (daily usage check + API call + results table), gated View MSA (export_pdf) and Download FASTA (export_pdf)
- **msa.html** (continued): Added full MSA JS handler (FASTA parser, large_msa gating at 10+ seqs, daily usage check + API call + stats/alignment viewer), gated Download FASTA/Clustal (export_pdf)
- **auth-shared.js**: Added `loadPlanUI()` — fetches plan status, injects plan badge into user popup header, adds 3 gated nav items (Team Collaboration/Lab, API Access/Pro, Admin Panel/Lab) with lock icons, shows Upgrade CTA for free (→Pro) and pro (→Lab) users

### Phase 3: Dashboard, Saved Results, Export PDF/PPT ✅
- **auth.py**: Added `saved_results` table (id, user_email, tool, title, inputs/outputs JSON, sequences_count, job_id, created_at)
- **primer_server.py**: Added 5 new routes — POST /api/results/save, GET /api/results/list, POST /api/results/delete, POST /api/export/pdf (fpdf2), POST /api/export/pptx (python-pptx)
- **dashboard.html**: New full dashboard page — Plan Overview card (plan pill, renewal), Quick Stats grid (daily/monthly usage bar), Saved Results table (paginated, filterable, deletable), Team/Api tabs (placeholder, gated), Upgrade banner for free users
- **results-ui.js**: New shared module — injects Save to Dashboard/Export PDF/Export PPT buttons into tool result containers via MutationObserver, gated via requireFeature
- **Tool pages (primer/blast/msa/docking)**: Linked results-ui.js to add save/export buttons to result areas
- **auth-shared.js**: Dashboard link now points to /dashboard instead of /primer
- **sitemap.xml + api/sitemap.xml.js**: Added /dashboard URL

### Files Changed (Phase 3)
| File | Change |
|------|--------|
| `primerforge/auth.py` | Added saved_results table to init_db() |
| `primerforge/primer_server.py` | Added 5 results/export API routes with @require_auth |
| `frontend/dashboard.html` | New: full dashboard page with plan/stats/results/upgrade |
| `frontend/results-ui.js` | New: shared save/export buttons injection on tool pages |
| `frontend/auth-shared.js` | Wire Dashboard link → /dashboard |
| `frontend/primer.html` | Added results-ui.js include |
| `frontend/blast.html` | Added results-ui.js include |
| `frontend/msa.html` | Added results-ui.js include |
| `frontend/docking.html` | Added results-ui.js include |
| `frontend/sitemap.xml` | Added /dashboard URL |
| `frontend/api/sitemap.xml.js` | Added /dashboard to CORE array |

## Files Changed This Session

| File | Change |
|------|--------|
| `producthunt-listing.md` | Updated tagline, description, pricing section, first comment to reflect 4-tier model |
| `docs/SALES_PLAYBOOK.md` | Updated email templates with current Pro ₹699/mo / academic ₹489/mo pricing |
| `docs/ACADEMIC_OUTREACH.md` | New: 10 personalized academic outreach emails to .edu.in targets |
| `docs/ALTERNATIVETO_SUBMISSION.md` | New: AlternativeTo, TAAFT, OMICtools, bio.tools submission text |
| `frontend/blog/best-primer-design-software-2026.html` | New: 574-line blog post — "8 Best Primer Design Software Tools in 2026" |
| `frontend/sitemap.xml` | Added 2 new blog post URLs |
| `frontend/api/sitemap.xml.js` | Added 2 new blog slugs to BLOG array |
| `frontend/blog/index.html` | Added 2 new blog cards (most recent) |
| `frontend/blog/rss.xml` | Added 2 new RSS items (most recent) |
| `AGENTS.md` | Updated session handoff |

## Files Changed This Session

| File | Change |
|------|--------|
| `primerforge/primer_server.py` | Fixed BLAST+MSA endpoints to allow anonymous access — removed hard `_auth_user()` gate on BLAST, made `get_current_user()` optional on MSA, guarded daily checks/recording with `if user` so unauthenticated requests are processed without limits |

## Files Changed This Session (CMS Image Editing)

| File | Change |
|------|--------|
| `frontend/cms-editor.html` | Enhanced `ResizableImage` node: parse/render `style`, `align`, `caption` (`data-caption`), `loading`; figure+figcaption wrapper in `renderHTML`; expanded floating toolbar (align buttons + ⚙ settings); new `#imageSettingsOverlay` modal (URL/alt/title/caption/link/align/width); insert flow routes through settings modal; `alignSelectedImage()`; expanded preview CSS |
| `frontend/cms-design.css` | `.ift-settings`, figure/figcaption, `figure.vl-align-*`, `img[align=*]`, `.img-align-picker`, `.img-align-opt`/`.img-width-opt` (+ is-active), `.editor-content .vl-figure` styles |
| `frontend/cms-content.js` | `injectImageCss()` (id `vl-img-css`) injecting `.vl-figure`/`figcaption`/`img[align=*]` public CSS |
| `backend/routes/public.py` | Bleach whitelist: `img` attrs now include `align`, `data-caption`, `style`; `CSSSanitizer` with `_SAFE_CSS_PROPERTIES` (width/float/margin/etc., strips `position:fixed`) |
| `backend/routes/pages.py` | `_render_node` image branch → `<figure class="vl-figure vl-align-X">` + `<figcaption>` when caption present; emits src/alt/title/style/align/loading (default lazy) |
| `primerforge/primer_server.py` | Explicit `/blast` + `/msa` routes; clean-URL no-extension fallback (`.html`) so `/dashboard`, `/terms`, `/privacy`, `/cookies`, `/blog/*` return 200 |
| `frontend/docking.html` | `nav-login-btn` null-ref fix — `updateAuthUI` falls back to `.nav-login` |
| `frontend/primer.html`, `blast.html`, `msa.html`, `login.html`, `signup.html` | T&C checkbox + `handleAuth`/`handleGoogleSignIn` gating on all 6 auth entry points |
| `AGENTS.md` | Session handoff + Files Changed table |

## Scoreboard
| Phase | Status | Items |
|-------|--------|-------|
| **Phase 1** — Pricing & Razorpay | ✅ Complete | 7/7 |
| **Phase 2** — Usage & Gating | ✅ Complete | 7/7 |
| **Phase 3** — Dashboard & Exports | ✅ Complete | 6/6 |
| **Phase 4** — Batch & Academic | ✅ Complete | 11/11 bugs squashed |
| **Sales Launch Package** | ✅ Complete | PH listing, academic outreach, directories, blog post |
| **Phase 5** — Team & Admin | ⏸️ Deferred | Until 5+ paying users |
| **Phase 6** — API & Landing | ⏸️ Deferred | Until 5+ paying users |
| **Phase 7** — SEO Comparisons | ⏸️ Deferred | Until 5+ paying users |
| **VPrime Redesign** | ✅ Complete | 8/8 tasks |

## VPrime Redesign (Jul 29 2026)

### What Was Done
- **Reverted sidebar form**: Removed all 24-step checkboxes; restored clean form with: Optimal Tm, Amplicon Size (min/max), Specificity toggle, Probe Design toggle + expandable config (type, reporter, quencher, Tm offset, length range, GC%, hairpin ΔG, 5'/3' mods), Reaction Conditions (Na⁺/Mg²⁺/dNTPs/primer conc/polymerase), Primer Modifications (5' tails fwd/rev, 5' mods fwd/rev), Primer Length & GC Clamp (len min/max, GC% min/max, 3' GC clamp), Pipeline Mode + Design Mode dropdowns
- **Fixed biochemistry calc functions** — three validated formulas:
  - `calcExtinctionCoeff(seq)`: ε = 0.9 × Σ(n_base × ε_base) per Cavaluzzi & Borer 2004
  - `calcMolWeight(seq, isProbe)`: MW = Σ(n_base × MW_base) + (n-1)×61.96 + 18.02, +800 if probe
  - `calcNmolPerOD(seq)`: nmol/OD = 1,000,000 / ε (Beer's law at A=1)
- **Redesigned result cards**: Each oligo card shows sequence, ⚙ Customize ▾ inline panel, metrics row (Tm, GC%, Length, Hairpin ΔG, Self-dimer ΔG), biochemistry row (ε in mM⁻¹cm⁻¹, MW in kDa, nmol/OD), quality score bar, action buttons
- **Per-oligo customization panels**: `.cust-panel` with 2×4 grid — 5′ Tail, 3′ Tail, 5′ Mod, 3′ Mod (text), Scale, Purification, Buffer, Conc (selects)
- **Order slide-out panel**: 520px right panel listing all oligos with per-item customization; Export IDT / Export Twist CSV with all customised values
- **+Add Primer / +Add Probe buttons**: Per-pair post-hoc buttons to manually add oligos to order
- **Step22 backend: Always-on probe design + Tm relaxation**:
  - Removed `probe_mode=False` guard — probes always generated regardless of checkbox
  - Two-pass strategy: Pass 1 = target Tm range (e.g., primer_Tm + 8–10°C); Pass 2 = relax to all candidates passing non-Tm constraints, sorted by Tm proximity
  - Probe region guaranteed between primers via `_find_probe_region` (start after fwd+1 gap, end before rev-1 gap)
  - Tested with human beta-globin: 5 candidates found at Tm 66.6–68.2°C

### Files Changed
| File | Change |
|------|--------|
| `frontend/primer.html` | Sidebar form cleanup, biochemistry calc functions (calcExtinctionCoeff/calcMolWeight/calcNmolPerOD), redesigned primerBlock/probeBlock templates, per-oligo .cust-panel, order-overlay/order-panel, IDT/Twist CSV export, +Add Primer/+Add Probe handlers |
| `primerforge/engine/steps/step22_probe_design.py` | Removed probe_mode gate; added two-pass probe generation (strict Tm → relaxed Tm); `_validate_probe` accepts optional tm_offset_min/max overrides; updated docstring |
| `pyproject.toml` | Added `version="1.0.0"` and `[tool.setuptools.packages.find]` so `pip install -e .` works |

### Next Steps
1. User to review VPrime redesign at http://localhost:11436/primer
2. On approval: `git add` + `git commit` + `git push` all modified files
3. **No Vercel deployment needed** — back to local dev for now

## HttpOnly-Cookie Migration — Files Changed
| File | Change |
|------|--------|
| `primerforge/auth.py` | SQLite `users` schema + `auth_provider`/`google_id` columns (CREATE + ALTER backfill); google-login backfill from `usage_log`; `get_current_user()` cookie fallback |
| `primerforge/auth_routes.py` | SQLite register + google set `pf_token` HttpOnly cookie; `/api/auth/me` returns `auth_provider` |
| `primerforge/pg_auth.py` | `get_current_user()` cookie fallback + `set_rls_context` on both paths |
| `primerforge/pg_auth_routes.py` | Google endpoint captures google_id + provider + cookie; `/api/auth/me` auth_provider |
| `deploy/migrations/0100_initial_schema.sql` | users table `auth_provider`/`google_id` |
| `frontend/auth-shared.js`, `feature-gate.js`, `results-ui.js`, `batch-ui.js`, `cookie-consent.js` | Off localStorage; cookie-based fetch; gates on `pf_user`/server 401 |
| `frontend/primer.html`, `docking.html`, `blast.html`, `msa.html`, `dashboard.html`, `checkout.html`, `pricing.html` | In-memory token + `rehydrateSession()` / `pf_user`-gating; cookie fetch |
| `frontend/cookies.html` | Cookie policy: `pf_token` → HttpOnly cookie row |
| `tests/test_http_only_cookie_auth.py` | New: 3 tests (register/login/google HttpOnly cookie + `auth_provider`) |
| `tests/test_primer_server.py` | Unwrap `create_app()`→Flask app in 3 spots (`.wsgi_app`) |

## Key Commands
- Python bulk-replace scripts for 200+ file operations
- `import os, glob` loop with `string.replace()` for safe batch editing
- `grep -n` for finding exact line numbers in large HTML files
- Follow existing blog post HTML patterns for new content (nav, footer, auth, schema, styling)
- Headless-Chrome verification: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --remote-debugging-port=9222 --remote-allow-origins='*' --user-data-dir=<tmp> <url>` then drive via Python `websocket-client` CDP (use `--remote-allow-origins=*` on Chrome 150+, else 403)

## World Map Improvements — Aug 30 2026 (commits `5ef6502d`, `1c84a9a5`, `881ecb16`)

### What & Why
Choropleth world map on homepage went through 3 iterations:
1. Custom SVG paths from TopoJSON — jagged edges, no POK, pixelated Russia/Americas
2. POK overlay patch — visible white border seam, still pixelated
3. **amCharts MapChart** (final) — smooth vector paths, proper POK via `worldLow` geodata, 3D hover, no visitor counts

### Final Implementation
- **amCharts v5 MapChart** with `am5geodata_worldLow` — proper world map with POK as part of India
- Single `MapPolygonSeries` — all countries rendered as one series, colored by tier
- 5-tier choropleth: `#0d4a8a` → `#1a6fb5` → `#2b6f9e` → `#5a94b8` → `#93b8d0` (light→dark blue)
- **Hover 3D effect**: `scale: 1.04` + `fill: #1565C0` + drop-shadow on hover via amCharts states
- **Top 5 sidebar**: country names only (no visitor counts), ranked with numbered badges
- No visitor counts displayed anywhere — just country names
- `world-map-data.js` removed (amCharts provides its own geodata)

### Files Changed
| File | Change |
|------|--------|
| `frontend/index.html` | amCharts CDN scripts, div#chartdiv, amCharts IIFE, removed SVG/custom-path renderer |
| `frontend/world-map-data.js` | No longer loaded (still exists in repo but unused) |

### Verification
- HTML parses OK (87,288 bytes)
- Flask test client: `index.html` serves 200, amCharts refs verified
- pytest: 9 passed
- Pushed: `881ecb16`

### CSP Fix — `def2e4f0`
- **Problem**: `cdn.amcharts.com` was blocked by Content-Security-Policy → amCharts scripts failed to load → `am5 is not defined` → map invisible + JS error broke DNA animation
- **Fix**: Added `https://cdn.amcharts.com` to `script-src` in homepage CSP (vercel.json line 618)
- **Robustness**: Wrapped amCharts IIFE in `try-catch` so DNA animation (`initDNAAnim`) still works if amCharts fails
- Pushed: `def2e4f0`

### Root Cause Fix — `eb9a69fa`
- **Root cause**: `maps.js` (plural) returns **404** on amCharts CDN. The correct file is `map.js` (singular).
- **Fix**: Downloaded all 4 amCharts files locally (`amcharts-index.js`, `amcharts-map.js`, `amcharts-worldLow.js`, `amcharts-worldIndiaLow.js`), served from `/` instead of CDN.
- **India/POK**: Using `am5geodata_worldIndiaLow` (India-specific world map with POK as part of India per Survey of India).
- **CSP cleanup**: Removed `cdn.amcharts.com` from `script-src` and `connect-src` (no longer needed — local files).
- Pushed: `eb9a69fa`

---

## Registration-Wall Restructure — Guest Mode (Aug 5 2026)

### Decision
**Option A — guest mode, then register.** "Computation is free, persistence is paid."
- Anonymous visitors can **run** all tools (manual analysis, docking, and the full auto-design pipeline) at no charge, no login.
- **Persistence stays paid/gated**: save to dashboard, export PDF/PPT, batch/history, advanced docking — via `feature-gate.js` `requireFeature()`.
- **Killed the legacy FREE_RUNS=2 / `run_count` gate** — the 5/day daily-limit is the sole Free-tier gate; `run_count` column kept only as a counter (`record_daily_usage` still increments it — harmless, not a gate).
- Rationale: 2.07% conversion behind a pre-value wall; IDT/NCBI/NEB show results before asking; BLAST/MSA already guest-mode; the "No login. Design now." hero promise must be true.
- Guests get a **claim card** ("Save My Results →") after a run; clicking opens the **Create Account** (register) modal and fires the report-save on login.

### Backend changes
- **SQLite path (`primerforge/primer_server.py`)**: `_dev_user_or_error()` (~848) now returns `(user_or_None, None)` — never 401s.
  - `/api/pipeline/submit` (858): usage check only `if user:`; switched `check_usage` → `check_daily_usage(user["email"],"primer")`; jobs store `"user_email"` (or `""`) + `"guest": not user`; usage/log only when user.
  - `/api/pipeline/status`(1020)/`result`(1056): guest jobs readable by anyone; owned jobs still envelope-checked.
  - `/api/primer/auto-design`(1227): 401 removed; `if user:` daily-limit + PG-token consume; usage increment guarded `if not test_mode and user:`.
  - `/api/primer/manual-analysis`(~1511): 401 removed (no usage check existed).
  - docking consensus(~2491): 401 removed; `if user:` daily-limit + token consume/record; polling unchanged.
- **Postgres production blueprint (`primerforge/engine/pipeline_routes.py`)** — the important one (prod runs PG; the shared SQLite handlers aren't registered):
  - Added `allow_guest` decorator + `_ensure_guest_user()` (shared system user, email `guest@vigyanllm.local`, role `guest`; **falls back to role `user`** on legacy DBs whose `user_role` enum lacks `guest` — quota gating uses the `g.is_guest` flag, not role, so this is safe).
  - `submit/status/result` switched `@require_auth` → `@allow_guest`. Guests get a real `user_id` (guest row), quota/token blocks skip when `g.is_guest`. Isolation via UUID job ids (122-bit). No frontend changes needed (no guest_token threading).
  - **`pipeline_jobs.user_id` stays `NOT NULL`** — no migration required.
  - Advanced/export routes (`jobs`, `order`, `compliance`, raw export, step output) keep `@require_auth` (persistence/export = paid ✓).

### Frontend changes
- **`frontend/primer-app.js`** (minified; edited via Python `str.replace`): removed `if(!G.user)return n._pendingRun=!0,void K();` from auto-design `C()`; guest claim card injected post-run (`!G.user&&P.length>0` → `#guest-claim-card`); `window.openGuestClaim`; claim-save hook in login-success handlers (`/api/reports/save` when `n._pendingClaim`); `T.limit`→`T.daily_limit`; copy ("Create a free account to save & export… 5 analyses free every day").
- **`frontend/docking.html`**: guest claim banner in `displayResults` (single-ligand anon runs already worked — no client gate).
- **Register/Login modal fix**: `Z()` is a **toggle** (`login↔register`), so `openGuestClaim`/`openAuthModal` were pre-setting `G.mode` then toggling → wrong tab. Gave `Z(t)` an optional target arg; `openAuthModal`→`Z("login")`, `openGuestClaim`→`Z("register")`.
- **password hint aligned to server policy** everywhere: "Min 8: upper, lower, digit, special" (`primer.html`, `login.html`, `signup.html`, `auth-shared.js`) + `auth-shared.js` client validation (≥8 + upper+lower+digit+special).
- **Google buttons fixed** on standalone `signup.html`/`login.html`: replaced broken `google.accounts.id.prompt()` (no initialize) with `google.accounts.oauth2.initTokenClient({client_id:'598272150916-…', scope:'email profile', callback:handleGoogleCredential}).requestAccessToken()` + fallback (id.initialize/prompt + lazy script load); `handleGoogleCredential` POSTs `{access_token}` to `/api/auth/google`, stores `pf_user`, redirects `/dashboard`.

### Tests & verification
- **`tests/test_guest_mode.py`** (new, 6 pass, SQLite-forced): anon manual-analysis 200; anon pipeline submit 202; anon reads own guest job; anon single-ligand docking 202; `results/save` still 401 for anon; logged-in Free user sees daily limit.
- **Live PG production server (headless Chrome, user-mandated step 4.5)** ✅: anon `/primer` (no auth modal) → pasted real human HBB → "Run" → 16 pairs rendered (no 401) → **"Save My Results →" claim card appears** → click → **Create Account** modal. Confirmed the PG blueprint gap (SQLite-only tests missed it) and the register/login toggle bug.
- **Pre-existing failures (verified baseline via `git stash`)**: `test_auto_design_does_not_mark_unrun_specificity_as_pass` + `test_inconclusive_specificity_is_not_specific` (both fail identically on baseline — anon auto-design in PG mode) + 4 `test_payment_routes.py`. Not caused by this work.
- **No regression**: `test_guest_mode.py` (6) + `test_http_only_cookie_auth.py` (3) pass; `test_primer_server.py` matches baseline.

### Files Changed
| File | Change |
|------|--------|
| `primerforge/engine/pipeline_routes.py` | `allow_guest` decorator + `_ensure_guest_user()` (guest system user, role-fallback to `user`); `submit/status/result` `@require_auth`→`@allow_guest`; quota/token blocks skip for `g.is_guest` |
| `primerforge/primer_server.py` | Guest mode on `_dev_user_or_error`, `/api/pipeline/*`, `auto-design`, `manual-analysis`, docking consensus (`if user:` limits/increments; `guest` job ownership) |
| `frontend/primer-app.js` | Removed auto-design auth wall; guest claim card + `openGuestClaim`; claim-save hook; `T.daily_limit`; `Z(t)` mode arg (fix register/login toggle) |
| `frontend/docking.html` | Guest claim banner in `displayResults` |
| `frontend/primer.html`, `login.html`, `signup.html`, `auth-shared.js` | Password hint/validation = server policy (8+ upper/lower/digit/special); fixed Google OAuth flow (signup/login) |
| `tests/test_guest_mode.py` | New: 6 guest-mode tests |

### Next Steps
1. ✅ **Phase 1 complete** — guest mode shipped & pushed (approved by user after live prod verification).
2. **Phase 2 — Credibility**: validation benchmarks, faculty outreach, positioning pivot ("credibility-first"). The registration wall was the last blocker.
3. Do not `git add docking_queue/` — pre-existing local runtime artifact, not part of the repo.
- No git push until user approval
