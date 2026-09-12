# INFRASTRUCTURE.md — VigyanLLM Current State & Next Steps

**Last updated:** September 12, 2026

---

## 1. Production Architecture

```
                          ┌─────────────────────────────────────────┐
                          │          Vercel (Frontend)               │
                          │   507 static HTML pages                 │
                          │   www.vigyanllm.in                      │
                          └──────────────┬──────────────────────────┘
                                         │ /api/* rewrites
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          EC2 Instance (ap-south-1)                           │
│                     i-05d610fc36db577c9 — t3.medium 30GB                     │
│                                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────────┐     │
│  │   nginx      │───▶│   gunicorn    │───▶│  Flask (primer_server.py)   │     │
│  │   :80/:443   │    │   :11436      │    │  22-step primer pipeline    │     │
│  └─────────────┘    │  2 workers    │    │  + API routes (auth, CRUD,  │     │
│                     │  120s timeout  │    │  payments, reviews, export)  │     │
│                     └──────────────┘    └──────────────┬──────────────┘     │
│                                                         │                    │
│                              ┌───────────────────────────┼──────────┐        │
│                              │                           │          │        │
│                              ▼                           ▼          ▼        │
│                     ┌──────────────┐           ┌──────────┐  ┌──────────┐  │
│                     │  PostgreSQL   │           │  Redis    │  │  Azure   │  │
│                     │  16 (local)   │           │  7 Alpine │  │  Worker  │  │
│                     │  :5432        │           │  :6379    │  │  (ESM+   │  │
│                     │  vigyan_prod  │           │  AUTH req  │  │  Vina+   │  │
│                     └──────────────┘           └──────────┘  │  GNINA)   │  │
│                                                              └──────────┘  │
│  ┌──────────────────── Monitoring Stack (Docker) ────────────────────────┐  │
│  │ Grafana :3000 │ Prometheus :9090 │ Loki :3100 │ Alertmanager :9093   │  │
│  │ 3 dashboards  │ 2 targets       │ TSDB+v3    │ null receiver (ready)│  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

### 2.1 Frontend (Vercel)
| Technology | Purpose | Status |
|---|---|---|
| Static HTML (507 pages) | Tool pages, blogs, glossary, landing pages | ✅ Live |
| `includes.js` | Shared header/footer partials | ✅ Active |
| `design-tokens.css` | Canonical CSS (nav, footer, mobile, modals) | ✅ Active |
| `auth-shared.js` | Auth state, Google redirect flow, user popup | ✅ Active |
| `feature-gate.js` | Plan-based gating (free/pro/lab) | ✅ Active |
| `results-ui.js` | Save/export buttons on tool results | ✅ Active |
| `review-modal.js` | Review collection system (star rating + banner) | ✅ Active |
| `search-index.js` | Client-side search | ✅ Active |
| `cookie-consent.js` | GDPR/DPDP consent banner | ✅ Active |
| `amCharts v5` | World map choropleth (loaded locally) | ✅ Active |
| Microsoft Clarity | Session recording (`xz5q0bpq5e`) | ✅ Active on 16 pages |
| Google Analytics | GA4 via GTM (GTM-KRP5LLPR) | ✅ Active |

### 2.2 Backend (EC2)
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11 | Runtime |
| Flask | 3.1.3 | Web framework |
| Gunicorn | 22.0.0 | WSGI server (2 workers, 120s timeout) |
| PostgreSQL | 16 | Primary database (local on EC2) |
| Redis | 7 Alpine | Rate limiting, Celery broker, session store |
| psycopg2-binary | 2.9.10 | PostgreSQL driver |
| Biopython | 1.87 | Sequence analysis |
| primer3-py | 2.3.0 | Primer thermodynamics (SantaLucia 1998 NN) |
| Razorpay SDK | 1.4.2 | Payment processing (subscriptions) |
| Celery | 5.4.0 | Background job processing |
| fpdf2 | 2.8.2 | PDF export |
| python-pptx | 1.0.2 | PPT export |
| bleach | 6.4.0 | HTML sanitization |
| cryptography | 44.0.2 | Fernet AES-256 encryption at rest |
| prometheus_client | 0.21.1 | /metrics endpoint |
| rdkit | ≥2024.3.1 | Molecular chemistry (docking prep) |
| meeko | ≥0.7.1 | Vina docking prep |

### 2.3 Azure Worker (Separate)
| Technology | Purpose |
|---|---|
| ESMFold | Protein structure prediction |
| AutoDock Vina | Molecular docking |
| GNINA | CNN-based docking scoring |
| torch, transformers, fair-esm | ML dependencies |

### 2.4 Monitoring Stack (Docker on EC2)
| Service | Image | Port | Purpose | Memory Limit |
|---|---|---|---|---|
| **Grafana** | grafana/grafana:latest | 3000 | Dashboards, visualization | 512MB |
| **Prometheus** | prom/prometheus:latest | 9090 | Metrics scraping, alerting | 2GB |
| **Loki** | grafana/loki:2.9.0 | 3100 | Log aggregation (TSDB v3) | 1GB |
| **Promtail** | grafana/promtail:2.9.0 | - | Log shipping to Loki | 512MB |
| **Alertmanager** | prom/alertmanager:latest | 9093 | Alert routing (null receiver) | 256MB |

### 2.5 Infrastructure
| Component | Technology | Details |
|---|---|---|
| **EC2 Instance** | t3.medium | ap-south-1, 30GB NVMe, Ubuntu 26.04 |
| **Frontend CDN** | Vercel | Static hosting, edge functions |
| **Domain** | vigyanllm.in | DNS via Hostinger |
| **SSL** | Let's Encrypt | Auto-renewal via certbot |
| **Email** | Hostinger SMTP | noreply@vigyanllm.in (SPF/DKIM/DMARC) |
| **Payments** | Razorpay | Subscriptions (Free/Pro/Lab/Enterprise) |
| **CI/CD** | GitHub Actions | Lint → Test → Deploy to EC2 |
| **Service Manager** | systemd | `vigyanllm.service` (gunicorn) |

### 2.6 Database Schema (PostgreSQL)
| Table | Purpose |
|---|---|
| `users` | Auth, plan, billing, trial, academic status |
| `saved_results` | User-saved tool results (JSON) |
| `pipeline_jobs` | Primer design pipeline jobs |
| `feedback_submissions` | Reviews/testimonials (approved/featured) |
| `usage_log` | Daily/monthly usage tracking |
| `payments` | Payment transactions |
| `promo_codes` | Promo codes (trial/academic) |
| `subscriptions` | Subscription tracking |
| `api_keys` | Developer API keys |
| `api_usage_logs` | API usage tracking |
| `webhooks` | Webhook configurations |
| `webhook_deliveries` | Webhook delivery logs |
| `schema_version` | Migration tracking |

---

## 3. What Was Deployed Today (Sept 12, 2026)

### 3.1 EC2 Upgrade
- ✅ Instance type: t3.small → **t3.medium** (2 vCPU, 4GB RAM)
- ✅ Root volume: 6.6GB → **30GB** NVMe
- ✅ Filesystem extended (growpart + resize2fs)

### 3.2 Database Migrations (7 applied)
| Migration | Purpose |
|---|---|
| 0119 | Academic promo type + pro_expires_at column |
| 0120 | Promo discount percentage |
| 0121 | Users plan columns |
| 0122 | Trial/promo columns (17 statements) |
| 0123 | Anonymous rate limiting |
| 0124 | Review system (9 statements) |
| 0125 | API keys, webhooks, API usage logs (11 statements) |

### 3.3 Monitoring Stack
- ✅ **Prometheus**: 2 targets scraping (app + node)
- ✅ **Grafana**: 3 dashboards imported (HTTP metrics, business, infrastructure)
- ✅ **Loki**: v3 config (inmemory ring, TSDB store, schema v13)
- ✅ **Promtail**: Shipping system + Docker logs to Loki
- ✅ **Alertmanager**: Null receiver (ready for Slack webhook)
- ✅ **9 alert rules**: service down, error rate, latency, disk, memory, DB, login, payment, cert

### 3.4 Service Management
- ✅ Disabled broken `vigyan.service` (auto-restart loop)
- ✅ `vigyanllm.service` confirmed active (gunicorn, 2 workers)
- ✅ Log rotation configured (`/etc/logrotate.d/vigyanllm`)

### 3.5 Bugs Fixed
- ✅ Migration runner: SQL comment-only statements (migrate.py)
- ✅ Loki config: v2 → v3 format (tsdb_shipper, inmemory ring)
- ✅ Alertmanager: null receiver (was crashing without Slack URL)
- ✅ Promtail: healthcheck (kill -0 instead of wget), positions mount

### 3.6 Access URLs
| Service | URL | Credentials |
|---|---|---|
| App Health | `http://13.207.60.92/health` | - |
| Grafana | `http://13.207.60.92:3000` | admin / vigyan-2026 |
| Prometheus | `http://13.207.60.92:9090` | - |
| Loki | `localhost:3100` | - |

---

## 4. Security Posture

| Control | Status | Details |
|---|---|---|
| HttpOnly cookies | ✅ | `pf_token` — no JS access |
| CSRF protection | ✅ | SameSite=Lax cookies |
| XSS prevention | ✅ | bleach HTML sanitization, CSP headers |
| SQL injection | ✅ | Parameterized queries (psycopg2 `%s`) |
| Rate limiting | ✅ | Flask-Limiter + Redis-backed |
| Auth hardened | ✅ | T&C checkbox, password validation, Google redirect |
| Admin RBAC | ✅ | Cookie-based, IP-restricted |
| Encryption at rest | ✅ | Fernet AES-256 (pipeline results) |
| Docker security | ✅ | cap_drop ALL, no-new-privileges, read_only root |
| systemd hardening | ✅ | ProtectSystem=strict, PrivateTmp, NoNewPrivileges |
| SSL/TLS | ✅ | Let's Encrypt, TLS 1.2/1.3 |
| Email security | ✅ | SPF, DKIM, DMARC records |
| Dependencies | ✅ | 358 tests pass, security scanning in CI |

---

## 5. Current Limits & Known Issues

| Issue | Severity | Impact |
|---|---|---|
| Non-www → www redirect not firing | Medium | SEO: duplicate content (both return 200) |
| Alertmanager has null receiver | Low | Alerts visible in Grafana but not sent anywhere |
| Promtail Docker API version mismatch | Low | Docker service discovery disabled (file-based works) |
| `vigyan.service` disabled | Low | Old service still on disk, should be removed |
| EC2 has no AWS CLI | Medium | Can't manage AWS resources from instance |
| EC2 SSH from local Mac fails | Medium | All deploys must run from EC2 console |
| No automated backups | High | PostgreSQL data not backed up to S3 |
| No autoscaling | Medium | Single instance, no failover |
| Grafana on public IP :3000 | High | Unauthenticated access risk (password set but open port) |

---

## 6. Next Steps

### Priority 1 — Security & Reliability (This Week)
1. **Restrict Grafana port** — close :3000 to public, access via SSH tunnel only
   ```bash
   # On EC2: bind Grafana to localhost only
   # Edit docker-compose monitoring: change "3000:3000" to "127.0.0.1:3000:3000"
   ```
2. **Setup automated PostgreSQL backups** — pg_dump to S3 daily
3. **Remove old `vigyan.service`** — `sudo rm /etc/systemd/system/vigyan.service && sudo systemctl daemon-reload`
4. **Fix non-www → www redirect** — Vercel dashboard config (not in vercel.json)

### Priority 2 — AWS Migration (Next Week)
5. **Configure AWS CLI on EC2** — `sudo snap install aws-cli --classic && aws configure` (needs IAM user with access keys)
6. **Deploy S3 + CloudFront** — All code committed in `deploy/aws/`:
   - `setup-s3.sh` → create bucket, versioning, CORS, lifecycle
   - `sync-frontend.sh` → upload with per-type cache headers
   - `create-cloudfront.sh` → OAC + distribution (S3 + ALB origins)
   - `grant-s3-access.sh` → bucket policy for CloudFront OAC
7. **Test CloudFront** — verify on *.cloudfront.net before DNS cutover
8. **DNS cutover** — point `www.vigyanllm.in` CNAME to CloudFront distribution

### Priority 3 — Monitoring Improvements (Week 2)
9. **Connect Alertmanager to Slack** — get Slack webhook URL, update `alertmanager.yml`
10. **Add app-specific Prometheus metrics** — primer design count, payment success rate, API latency p99
11. **Setup CloudWatch** as backup monitoring (lightweight, no local disk)

### Priority 4 — Infrastructure Hardening (Week 3)
12. **Migrate to RDS** — move PostgreSQL off EC2 to managed RDS (automated backups, Multi-AZ)
13. **Add Redis auth rotation** — periodic password rotation
14. **Setup staging environment** — separate EC2 or Docker Compose profile
15. **Containerize the app** — `Dockerfile` exists, move to full Docker Compose stack (app + postgres + redis)

### Priority 5 — Scalability (Month 2)
16. **Load balancer** — ALB in front of EC2 for zero-downtime deploys
17. **Auto Scaling Group** — scale EC2 based on CPU/memory
18. **CDN for backend API** — CloudFront API caching for public endpoints
19. **Database read replicas** — for analytics queries
20. **Redis cluster** — for distributed rate limiting

---

## 7. Quick Reference Commands

```bash
# ── Service Management ──
sudo systemctl status vigyanllm          # Check app status
sudo systemctl restart vigyanllm         # Restart app
sudo journalctl -u vigyanllm -n 50       # View app logs

# ── Monitoring ──
cd ~/vigyanpilot/deploy/monitoring
docker ps --format 'table {{.Names}}\t{{.Status}}'   # Container status
docker compose logs -f grafana                        # Grafana logs
docker compose logs -f prometheus                     # Prometheus logs
docker compose logs -f loki                           # Loki logs

# ── Database ──
psql -U postgres -d vigyan_prod -c "SELECT count(*) FROM users;"
python deploy/migrations/migrate.py --dry-run         # Preview migrations
python deploy/migrations/migrate.py                   # Apply migrations

# ── Deployment ──
cd ~/vigyanpilot && git fetch origin && git reset --hard origin/main
bash deploy/deploy-admin-systems.sh                   # Full deploy

# ── Disk Management ──
df -h /                                                # Check disk usage
docker system prune -af                                # Clean Docker images
sudo journalctl --vacuum-size=100M                     # Clean journal logs
```

---

## 8. Cost Breakdown (Monthly)

| Service | Cost | Notes |
|---|---|---|
| EC2 t3.medium | ~$30 | ap-south-1 |
| EBS 30GB | ~$3 | gp3 volume |
| Vercel (Hobby) | $0 | Static hosting |
| PostgreSQL (local) | $0 | On EC2 |
| Redis (local) | $0 | On EC2 |
| Domain (vigyanllm.in) | ~$1 | Hostinger |
| Razorpay | 2% per transaction | Payment processing |
| **Total** | **~$34/mo** | + payment fees |

---

## 9. File Structure Reference

```
deploy/
├── aws/                          # AWS S3+CloudFront migration
│   ├── setup-s3.sh               # S3 bucket creation
│   ├── sync-frontend.sh          # Frontend upload
│   ├── create-cloudfront.sh      # CloudFront distribution
│   ├── grant-s3-access.sh        # Bucket policy
│   ├── cloudfront-functions/     # URL redirects, security headers
│   └── lambda-edge/              # CSP headers
├── monitoring/                   # Docker monitoring stack
│   ├── docker-compose.yml        # Prometheus, Loki, Grafana, etc.
│   ├── prometheus.yml            # Scrape config
│   ├── loki-config.yml           # Loki v3 config
│   ├── promtail-config.yml       # Log shipping config
│   ├── alertmanager.yml          # Alert routing
│   ├── alert-rules.yml           # 9 alert rules
│   └── grafana/dashboards/       # 3 dashboard JSON files
├── migrations/                   # Database migrations (0119-0125)
├── deploy-admin-systems.sh       # Interactive EC2 deploy script
├── nginx.conf                    # Reverse proxy config
├── gunicorn.conf.py              # WSGI config
├── logrotate.conf                # Log rotation
├── vigyan.service                # systemd service (OLD — disabled)
├── healthcheck.sh                # App health check
├── retention-cron.py             # Data retention cleanup
└── rollback.sh                   # Commit-based rollback
```
