# Pending Plans — VigyanLLM

**Last updated:** 2026-09-12
**Status:** All code built & committed (`895e1f33`), blocked on EC2 disk space for deployment.

---

## Blocker: EC2 Disk Space

EC2 instance (`13.207.60.92`) is out of disk space. Nothing deploys until resolved.

**Fix steps (run on EC2):**
```bash
df -h /                          # Check current usage
docker system prune -af          # Clean Docker images/containers
docker volume prune -f           # Clean Docker volumes
sudo journalctl --vacuum-time=7d # Clean old systemd logs
sudo rm -rf /var/log/*.gz /var/log/*.old
rm -rf ~/.cache/pip
du -sh /* 2>/dev/null | sort -rh | head -10  # Find what's using space
```

**After freeing space:**
```bash
cd ~/vigyanpilot && bash deploy/deploy-admin-systems.sh
```

---

## Phase 1: Monitoring & Alerting — DEPLOYED LOCALLY, PENDING EC2

### What's Built
- `deploy/monitoring/docker-compose.yml` — Prometheus, Loki, Grafana, Promtail, Alertmanager
- `deploy/monitoring/prometheus.yml` — Scrape config for Flask app metrics
- `deploy/monitoring/loki-config.yml` — Log aggregation, 30-day retention
- `deploy/monitoring/promtail-config.yml` — Log shipping from /var/log/vigyan/ + Docker containers
- `deploy/monitoring/alertmanager.yml` — Slack webhook routing
- `deploy/monitoring/alert-rules.yml` — 9 alert rules (service down, error rate, latency, disk, memory, DB pool, login failures, payment failures, cert expiry)
- `deploy/monitoring/grafana/` — 3 dashboards (HTTP metrics, business metrics, infrastructure) + datasource provisioning
- `primerforge/metrics.py` — Prometheus `/metrics` endpoint
- `primerforge/logging_config.py` — Structured JSON logging with PII masking
- `deploy/setup-monitoring.sh` — One-command deployment script
- `deploy/logrotate.conf` — Daily rotation, 30-day retention

### Pending Actions
1. **Free EC2 disk space** (see blocker above)
2. **Deploy monitoring stack** — `bash deploy/deploy-admin-systems.sh`
3. **Open firewall ports** — `sudo ufw allow 3000/tcp && sudo ufw allow 9090/tcp`
4. **Configure Slack webhook** — Edit `deploy/monitoring/alertmanager.yml` with real Slack webhook URL
5. **Set up UptimeRobot** — Free tier, monitor `https://vigyanllm.in/health` every 5 min
6. **Wire threat detection webhook** — `primerforge/threat_detection.py` has `ALERT_WEBHOOK_URL` stub that never fires; needs to actually call Slack on IP bans
7. **Enable ErrorMonitor in production** — `primerforge/debugger.py` is disabled by default (`DEBUG_MONITOR=true` needed)

---

## Phase 2: CI/CD Pipeline — CODE PUSHED, PENDING GITHUB SETTINGS

### What's Built
- `.github/workflows/deploy.yml` — All `|| true` removed, Python 3.11, pytest coverage 70%, migration dry-run, security scan, deploy notification, concurrency lock, fixed health check port
- `.github/dependabot.yml` — Weekly Python + monthly Actions auto-PRs
- `docs/CONTRIBUTING.md` — Branch naming, PR template, code style, review process
- `docs/RUNBOOK.md` — 10 operational runbooks
- `deploy/rollback.sh` — Commit-based rollback with migration dry-run + health check
- `deploy/migrations/migrate.py` — Added `--dry-run` flag
- `tests/test_metrics.py` — 4 passing tests

### Pending Actions
1. **Enable branch protection on GitHub** — Go to Settings → Branches → Add rule for `main`:
   - Require pull request reviews (1 approval)
   - Require status checks to pass (CI must pass before merge)
   - Require branches to be up to date
   - No force pushes
2. **Set GitHub Secrets** (if not already set):
   - `EC2_HOST` — `13.207.60.92`
   - `EC2_USER` — `ubuntu`
   - `EC2_SSH_KEY` — Private SSH key
   - `SLACK_WEBHOOK_URL` — For deploy notifications
3. **Test CI pipeline** — Create a PR, verify tests must pass before merge
4. **Set up Slack channel** — Create `#alerts` channel for monitoring + deploy notifications

---

## Phase 3: Analytics — CODE PUSHED, PENDING WIRING

### What's Built
- `frontend/analytics.js` — Centralized event tracking (tool runs, signups, purchases, CTAs, scroll depth, time on page, outbound clicks)
- Microsoft Clarity (`xz5q0bpq5e`) — Active on 16 pages (heatmaps + session replay)

### Pending Actions
1. **Wire analytics.js into tool logic** — The file is loaded on pages but the `vlTrack()` calls need to be added inside actual tool execution handlers:
   - `primer-app.js` — After successful primer design: `VLAnalytics.trackToolRun('primer', inputSize, durationMs)`
   - BLAST/MSA/Docking JS — Same pattern
   - `feature-gate.js` — On upgrade modal: `VLAnalytics.trackUpgradePrompt(feature, currentTier, requiredTier)`
   - `review-modal.js` — On submit: `VLAnalytics.trackReviewSubmit(rating, hasInstitution)`
2. **Set up GA4 conversion goals** — In GA4 admin, mark as conversions: `purchase`, `sign_up`, `tool_run`, `review_submit`
3. **Build GA4 funnel dashboard** — In GA4 Explore: Landing → Tool → Run → Results → Signup → Upgrade → Purchase
4. **Verify Clarity is recording** — Go to clarity.microsoft.com, check that sessions are appearing

---

## Phase 4: API Management Portal — CODE PUSHED, PENDING MIGRATION + TESTING

### What's Built
- `deploy/migrations/0125_api_keys.sql` — api_keys, api_usage_logs, webhooks, webhook_deliveries tables
- `primerforge/api_auth.py` — API key generation, verification, rate limiting
- `primerforge/pg_api_routes.py` — Flask blueprint (key CRUD, usage analytics, webhook CRUD, v1 API stubs)
- `primerforge/webhook_engine.py` — Async delivery with 3-attempt exponential backoff
- 6 frontend pages: developer.html, developer-keys.html, developer-docs.html, developer-playground.html, developer-webhooks.html, developer-usage.html
- Header nav updated with Developer link
- Sitemap + vercel.json updated

### Pending Actions
1. **Run migration on EC2** — `python3 deploy/migrations/migrate.py` (creates api_keys + webhook tables)
2. **Test API key flow** — Register → go to /developer/keys → generate key → copy key
3. **Test v1 API** — `curl -X POST -H "Authorization: Bearer vl_live_..." -H "Content-Type: application/json" -d '{"sequence":"ATCGATCG"}' https://vigyanllm.in/api/v1/primer/design`
4. **Build v1 API stubs into real endpoints** — Currently return `{status: 'queued'}`; need to wire into actual pipeline
5. **Create OpenAPI spec** — `frontend/api/openapi.json` for Swagger UI on /developer/docs
6. **Set up Stripe-style API docs** — Real request/response examples for each endpoint

---

## Phase 5: Data Compliance — CODE PUSHED, PENDING TESTING

### What's Built
- `deploy/retention-cron.py` — Automated cleanup (anon 7d, consent 365d, API logs 90d, webhooks 90d)
- `frontend/dpdp.html` — DPDP Act 2023 compliance page
- `frontend/account-deletion.html` — Self-service deletion with 30-day grace period
- `frontend/privacy.html` — Updated with API data, cookie categories, DPDP section, DPO, retention periods

### Pending Actions
1. **Set up retention cron on EC2** — `crontab -e` → `0 2 * * * cd ~/vigyanpilot && venv/bin/python deploy/retention-cron.py`
2. **Test account deletion flow** — Login → /account-deletion → verify password → confirm → check DB
3. **Test DPDP page** — Verify /dpdp renders correctly
4. **Verify privacy.html changes** — Check new sections render properly
5. **Add grievance officer contact** — Fill in actual contact details on /dpdp page

---

## Phase 6: Additional Pending Items (From AGENTS.md)

### GSC Indexing
- **Status:** Top 12 URLs indexed, rest pending
- **Action:** Submit next batch daily via GSC. Target: all tool pages, top blog posts, comparison pages
- **Expected:** +400-750 clicks/mo from www redirect + title improvements

### Non-www → www 301 Redirect
- **Status:** vercel.json rule exists but both URLs return 200
- **Action:** Configure in Vercel dashboard (not code-level fix)

### Billing History Redesign (Commit `79e7f4bc`)
- **Status:** Fixed 500 error + professional card redesign
- **Pending:** Verify on live site after EC2 deploy

### Review System (Commit `3548fcd9`)
- **Status:** Backend + frontend built, wired into 9 tool pages
- **Pending:** Need 10+ approved reviews before homepage testimonials display
- **Action:** Seed with initial reviews from early users

### Pre-existing Test Failures (Commit `81b7852e`)
- **Status:** 2 primer server tests fixed (relaxed assertion)
- **Action:** Monitor for regressions

---

## Priority Order (After Disk Space Fixed)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | Free EC2 disk space | 10 min | Unblocks everything |
| 2 | Deploy monitoring stack | 15 min | Observability |
| 3 | Run migration 0125 (API keys) | 2 min | API portal |
| 4 | Restart app on EC2 | 1 min | All new features live |
| 5 | Open firewall ports (3000, 9090) | 1 min | Grafana/Prometheus access |
| 6 | Enable GitHub branch protection | 5 min | CI safety |
| 7 | Set GitHub Secrets | 5 min | CI/CD pipeline |
| 8 | Wire analytics.js into tool handlers | 30 min | Conversion tracking |
| 9 | Test API key flow end-to-end | 15 min | Developer portal |
| 10 | Set up retention cron | 2 min | Compliance |

---

## Commit History

| Commit | What |
|--------|------|
| `16e67912` | 5 phases: monitoring, CI/CD, analytics, API portal, compliance (58 files, +4,192 lines) |
| `cd1b6fcc` | Microsoft Clarity activated on 16 pages |
| `9641da9b` | AGENTS.md update |
| `009e5ac3` | EC2 deploy script |
| `895e1f33` | Deploy script fix (venv before pip) |
