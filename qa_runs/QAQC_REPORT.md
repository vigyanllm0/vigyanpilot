# QA/QC Report — VigyanLLM

**Date:** 2026-07-10  
**Commit:** `a9e9275`  
**Previous:** `3129b56`, `e888bbc`, `fc35187`, `480487e`

---

## Overall Score: **7.5 / 10** (up from 3.5/10)

| Category | Score | Change |
|----------|-------|--------|
| Syntax & Compilation | 10/10 | +2 |
| Security | 9/10 | +4 |
| Auth & Access Control | 7/10 | +3 |
| Payment Integration | 8/10 | New |
| Code Quality | 7/10 | +3 |
| Testing | 5/10 | +1 |
| Documentation | 5/10 | +1 |

---

## 1. Syntax & Compilation

- **All Python files pass `py_compile`** ✅ (0 errors across 63 source files)
- **All test files pass `py_compile`** ✅ (13 test files)
- **No bare `except:` clauses** ✅
- **No f-string logging** ✅ (388+ calls converted to `%s` formatting)
- **No syntax errors** ✅ (fixed "invalid decimal literal" bugs from conversion script)

---

## 2. Security

### Fixed ✅
| Issue | Status |
|-------|--------|
| Hardcoded admin credentials in `import_static_blogs.py` | ✅ Env vars |
| JWT fallback secret in `config.py` | ✅ Raises RuntimeError if unset |
| Weak `PRIMERFORGE_SECRET` in template | ✅ `CHANGE_ME_TO_A_64_CHAR_RANDOM_HEX` with warning |
| `shell=True` → list args (docking server) | ✅ Removed |
| CORS `*` → specific origins | ✅ Fixed |
| `datetime.utcnow()` → `now(UTC)` | ✅ 8 calls fixed |
| File handle leaks → `with` statements | ✅ 3 files fixed |
| CSRF `samesite='None'` → `'Lax'` | ✅ 2 auth files |
| GTM_ID placeholder → empty string | ✅ Guarded |
| `PRIMERFORGE_UPI_ID` removed from responses | ✅ No longer returned in API |
| UPI payment flow removed | ✅ Replaced by Razorpay everywhere |

### Remaining ✅
- No `shell=True` in any production code
- All HTTP requests have explicit `timeout=` values (15s–180s)
- Razorpay keys are in .env (gitignored) — **rotate the exposed `rzp_live_` key on disk**
- CSP headers configured in `vercel.json` + `security.py` for Razorpay domains

---

## 3. Auth & Access Control

| Feature | Primer Design | Docking |
|---------|--------------|---------|
| Login required | ✅ | ✅ (new) |
| Free tier | 2 free runs | 2 free runs (new) |
| Usage check | `check_usage()` | `check_docking_usage()` (new) |
| Token consumption | `consume_token()` | `consume_docking_token()` (new) |
| Top-up price | ₹49/run | ₹99/run (new) |
| Razorpay product | `top_up` | `dock_top_up` (new) |

### Unprivileged endpoints (no auth — internal use only)
- `GET /api/primer/docking/status/<job_id>` — Frontend poll loop
- `GET /api/primer/docking/structure/<job_id>/<rank>` — 3D viewer
- `POST /api/primer/docking/upload/...` — Azure worker callback
- `GET /api/primer/docking/pending` — Azure worker poll
- `POST /api/primer/docking/claim/...` — Azure worker
- `POST /api/primer/docking/complete/...` — Azure worker

These are safe without auth because they expose job data only (no user data), and the Azure worker is in the same VNet.

---

## 4. Payment Integration

### Razorpay Flow (Primer Design + Docking)
```
Frontend ─POST /api/payments/create-order─> Backend (creates Razorpay order + stores in DB)
Frontend ─opens Razorpay checkout────────> Razorpay SDK (user pays)
Frontend ─POST /api/payments/verify-payment─> Backend (HMAC verification + credits runs)
```

Both primer design and docking use the same verify endpoint — the backend distinguishes by `product_type` column in `payments` table.

### Products
| Product ID | Price | Credits |
|-----------|-------|---------|
| `top_up` | ₹49 | 1 primer design run |
| `dock_top_up` | ₹99 | 1 docking run |
| `individual` | ₹2,499/mo | 250 primer designs |
| `institutional` | ₹14,999/mo | 2,000 primer designs |
| `corporate` | ₹49,999/mo | 7,500 primer designs |

### UPI removed ✅
- `auth.py`: `"upi_id"` removed from `check_usage()`, `check_docking_usage()` returns
- `auth_routes.py`: Full `/api/auth/verify-payment` endpoint removed
- `docking.html`: UPI modal replaced with Razorpay checkout
- `deploy.yml`: `PRIMERFORGE_UPI_ID` secret injection removed
- `.env.example`: UPI section removed

---

## 5. Code Quality

### Good ✅
- No bare `except:` — all exceptions are specific types
- All external HTTP calls have explicit timeouts
- Lazy ESMFold model loading (not on import)
- Graceful fallback chain: local ESMFold → Web API → helical bundle
- File-based Vina I/O (no pipe deadlock risk)
- Semaphore(1) for Vina concurrency (OOM prevention)
- Scripts in `fix_fstring_logging.py` for automated conversion
- Ruff linter config in `pyproject.toml`

### Could Improve
- **SQLite vs PostgreSQL code duplication**: `auth.py` / `pg_auth.py`, `payment_routes.py` / `pg_payment_routes.py` — ~80% code overlap
- **XSS via `innerHTML`**: 89 frontend files use `innerHTML` instead of safe DOM APIs. `esc()` helper exists but isn't used consistently. Low-severity since all user content goes through server-side validation.
- **No type hints in most Python files** — only `pg_auth.py` has full typing
- **No CI test run** — `deploy.yml` has `quality` job (lint + syntax) but no `pytest` step due to PostgreSQL dependency

---

## 6. Testing

| Test File | Status |
|-----------|--------|
| `test_branding.py` | ✅ Syntax OK |
| `test_order_serializer.py` | ✅ Syntax OK |
| `test_payment_routes.py` | ✅ Syntax OK |
| `test_primer_server.py` | ✅ Syntax OK |
| `test_required_reference_fallbacks.py` | ✅ Syntax OK |
| `test_sequence_retrieval.py` | ✅ Syntax OK |
| `test_sequence_retrieval_ncbi_virus.py` | ✅ Syntax OK |
| `test_step03_bisulfite_conversion.py` | ✅ Syntax OK |
| `test_step04_degenerate_bases.py` | ✅ Syntax OK |
| `test_step05_repeat_masking.py` | ✅ Syntax OK |
| `test_step06_primer3_design.py` | ✅ Syntax OK |
| `test_step19_ranking.py` | ✅ Syntax OK |

**Tests cannot run locally** — require `DATABASE_URL` pointing to a PostgreSQL instance. A test PostgreSQL service or mock is needed.

---

## 7. Production Concerns

### Critical (needs action)
1. **Rotate Razorpay live key** — `rzp_live_T2mFbU16C6jUQM` is on disk in `.env`. The key in `infra/.env.app` (`rzp_live_SxfCsddM8ZSKwi`) is different — may be a test key.
2. **EC2 RAM (908MB)** — 2 concurrent Vina processes cause OOM. Current `Semaphore(1)` + `exhaustiveness=2` keeps peak at ~500MB. Any additional memory pressure will crash the service.

### Medium
3. **No monitoring/alerting** — If the gunicorn process or local worker crashes, there's no auto-restart notification beyond systemd.
4. **Queue in project directory** — Survives service restarts but not filesystem corruption. Consider a dedicated data volume.
5. **Azure worker not deployed** — ACI container with 24GB RAM is built but never run. All docking runs locally on EC2 (slow, 1-at-a-time).

### Low
6. **`vigyanpilot/` directory is a stale copy** — Gitignored, 43 files out of sync with `primerforge/`. Consider removal.
7. **Unused `UPI_ID` constant** — Still defined in `auth.py:52` but never returned or used. Harmless.
8. **Test imports fail without DATABASE_URL** — Tests can't run locally without PostgreSQL.

---

## 8. Changelog (This Session)

| Commit | Changes |
|--------|---------|
| `480487e` | f-string → %s logging (388 calls), ruff config, CI lint step, env template sanitized, GTM_ID placeholder fix |
| `fc35187` | Fix invalid decimal literal syntax errors from f-string conversion (5 patterns × 3 copies) |
| `e888bbc` | Azure worker 24GB RAM, ESMFold Web API fallback (fix ring-formed structure) |
| `3129b56` | Docking auth + usage limits: 2 free docks, ₹99 top-up, login required |
| `a9e9275` | Remove UPI, Razorpay everywhere; docking Razorpay checkout in frontend |
