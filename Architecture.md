# VigyanLLM — Architecture & Detailed Project Report (DPR)

> **Version:** 2.0.0 | **Last Updated:** August 2026
> **Platform:** VigyanLLM — Sovereign Bioinformatics Platform
> **Company:** VigyanLLM Private Limited

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Backend Architecture](#4-backend-architecture)
5. [Database Architecture](#5-database-architecture)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Payment & Subscription System](#7-payment--subscription-system)
8. [Pipeline Engine](#8-pipeline-engine)
9. [Deployment & DevOps](#9-deployment--devops)
10. [Security Architecture](#10-security-architecture)
11. [Tech Stack Summary](#11-tech-stack-summary)
12. [Data Flow Diagrams](#12-data-flow-diagrams)
13. [API Reference](#13-api-reference)
14. [Development Setup](#14-development-setup)

---

## 1. Project Overview

### 1.1 What is VigyanLLM?

VigyanLLM is a sovereign bioinformatics platform offering 15+ web-based computational biology tools including primer design, BLAST search, multiple sequence alignment (MSA), CRISPR analysis, codon optimization, ORF finding, and thermodynamic calculators. It serves researchers, students, and labs in India and globally with a freemium subscription model.

### 1.2 Core Capabilities

- **Primer Design Pipeline** — 24-step automated pipeline (Primer3 + SantaLucia NN thermodynamics)
- **BLAST Search** — Local NCBI BLAST 2.17.0+ with sequence database
- **Multiple Sequence Alignment** — Clustal Omega backend
- **CRISPR gRNA Design** — In development
- **Codon Optimization** — E. coli, human, yeast expression optimization
- **ORF Finding** — Open reading frame detection in nucleotide sequences
- **Protein Analysis** — Molecular weight, pI, amino acid composition
- **Tool Suite** — Tm calculator, GC calculator, DNA→RNA transcription, PCR analysis, restriction enzymes

### 1.3 Business Model

| Plan | Price (INR) | Daily Limit | Batch | API | Seats |
|------|------------|-------------|-------|-----|-------|
| Free | ₹0 | 5 analyses | 1 seq | — | 1 |
| Pro Monthly | ₹699/mo | 100 | 50 seq | 1,000/mo | 1 |
| Pro Yearly | ₹5,999/yr | 100 | 50 seq | 1,000/mo | 1 |
| Lab Monthly | ₹3,999/mo | 500 | 200 seq | 10,000/mo | 5 |
| Lab Yearly | ₹32,999/yr | 500 | 200 seq | 10,000/mo | 5 |
| Enterprise | Custom | Unlimited | Unlimited | Unlimited | Unlimited |

**Academic Discount:** 30% off for verified `.edu` / `.ac.in` / `.edu.in` email holders.

---

## 2. System Architecture

### 2.1 High-Level Overview

```
                         ┌──────────────────────────────┐
                         │         Vercel Edge           │
                         │  ┌────────────────────────┐  │
                         │  │   Edge Middleware.js    │  │
                         │  │  (crawler blocks,      │  │
                         │  │   admin RBAC)           │  │
                         │  └────────────────────────┘  │
                         │                              │
                         │  Static: frontend/ (410+ pg) │
                         │  Dynamic: Edge Functions     │
                         │  Rewrite: /api/* → EC2       │
                         └───────────┬──────────────────┘
                                     │ HTTPS
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
     ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
     │   AWS EC2       │   │  AWS RDS /      │   │  Docker Redis   │
     │   t3.medium     │   │  Local PG       │   │  7-alpine       │
     │                 │   │  (localhost)     │   │                │
     │  ┌───────────┐  │   │                 │   │  Rate limits    │
     │  │  Nginx    │  │   │  Users          │   │  Celery MQ      │
     │  │  (proxy)  │  │   │  Payments       │   │  Session cache  │
     │  └─────┬─────┘  │   │  Jobs           │   └────────────────┘
     │        │        │   │  Audit          │
     │  ┌─────▼─────┐  │   │  Webhooks       │
     │  │ Gunicorn  │  │   │  Docking Jobs   │
     │  │ Flask App │  │   └────────────────┘
     │  │ :11436    │  │
     │  └───────────┘  │
     └─────────────────┘
```

### 2.2 Infrastructure Components

| Component | Technology | Hosting | Purpose |
|-----------|-----------|---------|---------|
| **Static Frontend** | HTML, CSS, Vanilla JS | Vercel (CDN) | ~410 tool/blog/glossary pages |
| **Edge Middleware** | JavaScript (Vercel Edge) | Vercel | Crawler blocking, admin RBAC |
| **Edge Functions** | Node.js | Vercel | `/api/sitemap.xml.js`, BLAST proxy |
| **API Backend** | Flask 3.1.3 / Gunicorn | AWS EC2 t3.medium | Auth, payments, pipeline engine |
| **Database** | PostgreSQL 16 (primary) / SQLite (dev) | AWS (localhost:5432) | User data, payments, jobs, docking |
| **Cache/Queue** | Redis 7 | Docker (EC2) | Rate limits, Celery broker, sessions |
| **Payment** | Razorpay | SaaS | Indian payment gateway |
| **Email** | Brevo API + SMTP fallback | Brevo (Hostinger SMTP) | Verification, password reset |
| **CI/CD** | GitHub Actions | GitHub | Lint, test, deploy to EC2 |

---

## 3. Frontend Architecture

### 3.1 Technology Choices

- **Framework:** None — pure static HTML5 with vanilla JavaScript
- **CSS:** Custom properties (`design-tokens.css`), Montserrat + Open Sans fonts
- **Deployment:** Vercel (output directory: `frontend/`)
- **PWA:** Service worker (`sw.js`) + manifest (`manifest.json`)
- **No build step** — HTML, CSS, JS served as-is

### 3.2 Directory Structure

```
frontend/
├── index.html                    # Landing page
├── primer.html                   # Primer design tool
├── blast.html                    # BLAST search tool
├── msa.html                      # Multiple sequence alignment
├── tm-calculator.html            # Melting temperature calculator
├── gc-calculator.html            # GC content calculator
├── dna-to-rna.html               # Transcription tool
├── dna-to-protein.html           # Translation tool
├── crispr-analysis.html          # CRISPR design (in development)
├── pcr-analysis.html             # In silico PCR
├── pcr-product-calculator.html   # PCR product size calculator
├── restriction-enzyme-finder.html # Restriction enzyme search
├── reverse-complement.html       # Reverse complement tool
├── compare.html                  # Primer3 comparison
├── codon-optimizer.html          # Codon optimization (NEW)
├── orf-finder.html               # Open reading frame finder (NEW)
├── protein-mw-calculator.html    # Protein molecular weight (NEW)
├── cloning-planner.html          # Cloning strategy planner (NEW)
├── restriction-digest.html       # Restriction digest simulator (NEW)
├── qpcr-standard-curve.html      # qPCR standard curve calculator (NEW)
├── primer.html                   # Primer design info page
├── pricing.html                  # Subscription plans
├── checkout.html                 # Order summary + Razorpay
├── payment-success.html          # Post-payment success
├── payment-failed.html           # Post-payment failure
├── dashboard.html                # User dashboard
├── auth-shared.js                # Auth UI (login/register modal, Google OAuth)
├── feature-gate.js               # Feature access control (11 features)
├── batch-ui.js                   # Batch processing UI (FASTA/CSV parser, progress)
├── results-ui.js                 # Save/export buttons (MutationObserver)
├── search-index.js               # Client-side search (~100 entries)
├── config.js                     # API base URL (gitignored)
├── design-tokens.css             # CSS custom properties
├── blog/                         # 57+ blog posts
├── glossary/                     # 205 glossary pages
├── landing-pages/                # 28 marketing landing pages
├── compare/                      # Comparison pages
├── admin/                        # Admin panel pages
├── docs/                         # Documentation pages
├── hub/                          # Educational hub pages
└── api/                          # Vercel Edge Functions
```

### 3.3 Key JavaScript Modules

#### `auth-shared.js` (263 lines)
Central auth UI manager included on all pages. Handles:
- Nav bar toggling (login buttons vs user profile avatar)
- Login/register modal overlay (email/password + Google OAuth)
- User popup menu (plan badge, gated nav items, upgrade CTA)
- Token storage (sessionStorage + localStorage fallback)
- Auto-fetch `/api/payments/status` on load to inject plan UI

#### `feature-gate.js` (81 lines)
Shared gating module that maps features to required plan tiers:

```javascript
FEATURE_TIER = {
  batch:           'pro',    // Batch processing
  export_pdf:      'pro',    // PDF export
  export_ppt:      'pro',    // PPT export
  saved_results:   'pro',    // Save to dashboard
  api_access:      'pro',    // API access
  large_msa:       'pro',    // MSA >10 sequences
  crispr_offtarget:'pro',    // CRISPR off-target analysis
  collaboration:   'lab',    // Team collaboration
  admin_panel:     'lab',    // Admin panel
  lims_hooks:      'lab',    // LIMS integration
}
```

Functions: `requireFeature(featureId)` → shows upgrade modal if insufficient tier.

#### `batch-ui.js` (120 lines)
Shared batch processing module:
- FASTA/CSV parser (identifies sequences by header)
- Sequence counter (`BUI.count()`)
- Size checker (`BUI.checkSize()` gated via `requireFeature`)
- Progress bar injection
- CSV download (`BUI.downloadCSV()`)
- File upload handler

#### `results-ui.js` (90 lines)
Injects Save/Export buttons into tool result containers via `MutationObserver`:
- "Save to Dashboard" — calls `POST /api/results/save`
- "Export PDF" — calls `POST /api/export/pdf`
- "Export PPT" — calls `POST /api/export/pptx`
- All buttons gated via `requireFeature('export_pdf')` / `requireFeature('saved_results')`

### 3.4 Page Structure (Tool Pages)

Every tool page follows the same layout pattern:
1. **Nav** — Sticky navy bar with logo, search, auth controls
2. **Breadcrumb** — `BreadcrumbList` JSON-LD
3. **Educational H2 sections** — Above the tool form (3 per tool page)
4. **Tool form** — User inputs
5. **Result container** — Dynamic results display
6. **Scientific references** — PubMed-citable citations
7. **FAQ section** — Inline FAQ + `FAQPage` JSON-LD
8. **Footer** — Standardized with all legal links

### 3.5 Vercel Configuration (`vercel.json`)

Key features:
- `cleanUrls: true` — No `.html` extensions
- `outputDirectory: frontend/`
- **Rewrites:** `/api/:path*` → `http://13.207.60.92/api/:path*` (proxy to EC2)
- **Redirects:** 36 URL aliases (blog migration, tool renames, `.html` stripping)
- **Per-page CSP headers:** Different CSP for index, primer, docking, blog, admin-security
- **Global security headers:** HSTS (1 year preload), X-Frame-Options (DENY), CORS validation
- **Cache control:** Fonts (1 year immutable), images (1 day), JSON/XML (1 hour)

### 3.6 Edge Middleware (`middleware.js`)

Blocks malicious crawlers (AhrefsBot, SemrushBot, MJ12bot, DotBot, etc.) and protects admin paths via cookie-based RBAC (`admin_tk` cookie parsed with `Object.fromEntries()`).

---

## 4. Backend Architecture

### 4.1 Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Web Framework** | Flask | 3.1.3 |
| **WSGI Server** | Gunicorn | 22.0.0 |
| **Database** | PostgreSQL 16 (prod) / SQLite (dev) | — |
| **DB Driver** | psycopg2-binary (PG) / sqlite3 (stdlib) | 2.9.10 |
| **ORM** | None — raw SQL with cursor-based access | — |
| **Auth Tokens** | HMAC-SHA256 (custom) | — |
| **Password Hashing** | bcrypt | 5.0.0 |
| **Payment Gateway** | Razorpay | 1.4.2 |
| **Task Queue** | Celery + Redis | 5.4.0 |
| **Caching** | Redis 7 | — |
| **Rate Limiting** | Flask-Limiter (Redis backend) | 3.8.0 |
| **Security Headers** | Flask-Talisman | 1.1.0 |
| **CORS** | Flask-CORS | 6.0.5 |
| **Encryption** | cryptography (Fernet AES-256) | 44.0.2 |
| **Export** | fpdf2 (PDF), python-pptx (PPT) | 2.8.2 / 1.0.2 |
| **Bioinformatics** | Biopython, primer3-py, RDKit | 1.87 / 2.3.0 |
| **Input Sanitization** | bleach | 6.4.0 |
| **Env Management** | python-dotenv | 1.2.2 |

### 4.2 Application Structure

```
primerforge/
├── __init__.py                        # PATH setup for BLAST binaries
├── primer_server.py                   # Flask app factory (2773 lines)
├── wsgi.py                            # Gunicorn entry point
│
├── auth.py                            # SQLite auth module (578 lines)
├── auth_routes.py                     # SQLite auth API routes (388 lines)
├── pg_auth.py                         # PostgreSQL auth module (889 lines)
├── pg_auth_routes.py                  # PostgreSQL auth routes (943 lines)
│
├── payment_routes.py                  # SQLite payment routes (472 lines)
├── pg_payment_routes.py               # PostgreSQL payment routes (700 lines)
├── price_registry.py                  # 4-tier PlanConfig + limits (365 lines)
│
├── database.py                        # PostgreSQL connection pool
├── security.py                        # Flask-Talisman, CORS, rate limits (465 lines)
├── crypto_utils.py                    # Fernet AES-256 encryption
├── pii_mask.py                        # PII masking utilities
├── threat_detection.py                # Threat detection middleware
├── debugger.py                        # Debug mode utilities
├── file_scanner.py                    # File upload security scanner
│
├── engine/                            # Pipeline engine
│   ├── orchestrator.py                # PipelineOrchestrator (456 lines)
│   ├── pipeline_routes.py             # Pipeline API endpoints (908 lines)
│   ├── tasks.py                       # Celery async tasks (163 lines)
│   ├── steps/                         # 24 pipeline step implementations
│   │   ├── __init__.py                # STEP_REGISTRY dict (134 lines)
│   │   ├── base.py                    # PipelineStep ABC
│   │   └── step_*.py                  # Individual step files
│   ├── blast_viewer.py                # BLAST result visualization
│   ├── msa_viewer.py                  # MSA visualization
│   ├── branding.py                    # Branded report generation
│   ├── compliance.py                  # Biosecurity compliance
│   ├── order_serializer.py            # Order/serialization
│   ├── sequence_cache.py              # Sequence caching
│   ├── sequence_retrieval.py          # NCBI/Ensembl fetching
│   └── thermodynamics.py              # Thermodynamic calculations
│
├── core/                              # Core bioinformatics logic
│   ├── auto_designer.py               # AutoPrimerDesigner class
│   ├── manual_analyser.py             # Manual primer analysis
│   ├── sequence_fetcher.py            # NCBI/Ensembl/UniProt fetcher
│   ├── thermodynamics.py              # SantaLucia NN thermodynamics
│   └── pipeline_validator.py          # Input validation
│
├── pipelines/                         # Pipeline modules
│   ├── warmup.py
│   └── (consensus pipeline removed)

├── reports_routes.py                  # PostgreSQL reports API
├── reports_routes_sqlite.py           # SQLite reports API
├── consent_routes.py                  # DPDP consent routes
├── celery_app.py                      # Celery configuration
└── admin-*.py                         # Admin route files
```

### 4.3 App Factory (`create_app()`)

The application uses a Flask factory pattern with two database modes:

```
create_app()
├── Set SECRET_KEY (from env or random)
├── Register global error handler
├── Initialize security layers
│   ├── Flask-Talisman (CSP/HSTS)
│   ├── CORS (allowlist-validated origins)
│   ├── Rate limiting (Redis-backed)
│   └── Admin RBAC middleware
│
├── Database mode detection (DATABASE_URL env)
│
├── IF PostgreSQL (USE_POSTGRES=True):
│   ├── Import pg_auth, pg_auth_routes, pg_payment_routes
│   ├── Register auth, payment, pipeline, reports blueprints
│   ├── Call ensure_admin_exists()
│   └── Usage tracking: token-based (consume_token)
│
├── ELSE SQLite:
│   ├── Import auth, auth_routes, payment_routes, reports_routes_sqlite
│   ├── Register auth, payment (optional), reports blueprints
│   └── Usage tracking: daily_usage table
│
├── Register shared blueprints
│   ├── pipeline_bp (engine.pipeline_routes)
│   └── consent_bp (consent_routes)

├── Register core tool endpoints
│   ├── POST /api/primer/auto_design
│   ├── POST /api/blast/search
│   ├── POST /api/msa/align
│   ├── POST /api/thermodynamics/tm
│   ├── POST /api/thermodynamics/gc
│   ├── POST /api/tools/codon-optimize
│   ├── POST /api/tools/orf-find
│   └── POST /api/tools/protein-mw
│
├── Register result/export endpoints
│   ├── POST /api/results/save
│   ├── GET /api/results/list
│   ├── POST /api/results/delete
│   ├── POST /api/export/pdf
│   └── POST /api/export/pptx
│
└── Register /health endpoint
```

### 4.4 Gunicorn Configuration

```python
bind = "0.0.0.0:11436"
workers = multiprocessing.cpu_count()    # Auto-detect cores
timeout = 120
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
accesslog = "/var/log/vigyan/access.log"
errorlog = "/var/log/vigyan/error.log"
loglevel = "info"
```

### 4.5 Django vs Flask Decision

Flask was chosen over Django because:
1. **Lightweight API server** — No need for Django's full-stack ORM/admin
2. **Raw SQL control** — Complex bioinformatics queries benefit from hand-tuned SQL
3. **Two database modes** — SQLite for dev, PostgreSQL for prod — Flask's loose coupling makes this trivial
4. **Minimal overhead** — Only 26 dependencies in requirements.txt

---

## 5. Database Architecture

### 5.1 Dual Database Mode

| Aspect | Development | Production |
|--------|------------|------------|
| **Engine** | SQLite 3 | PostgreSQL 16 |
| **Connection** | `sqlite3.connect(primerforge.db)` | `psycopg2.pool.ThreadedConnectionPool` |
| **File/Path** | `./primerforge.db` | Azure Flexible Server |
| **ORM** | None (raw SQL) | None (raw SQL + connection pool) |
| **Tables** | 12 | 25+ (including partitions, views) |
| **Usage tracking** | `daily_usage` table | Token balance + subscription quota |

### 5.2 SQLite Schema (12 tables)

```sql
-- Users & Auth
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT DEFAULT '',
  role TEXT DEFAULT 'user',
  run_count INTEGER DEFAULT 0,
  paid_runs INTEGER DEFAULT 0,
  dock_run_count INTEGER DEFAULT 0,
  dock_paid_runs INTEGER DEFAULT 0,
  plan TEXT DEFAULT 'free',
  billing_cycle TEXT DEFAULT 'monthly',
  plan_activated_at TEXT,
  plan_expires_at TEXT,
  is_academic INTEGER DEFAULT 0,
  academic_discount INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  last_login TEXT,
  locked_until TEXT,
  failed_attempts INTEGER DEFAULT 0
);

-- Usage & Limits
CREATE TABLE daily_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_email TEXT NOT NULL,
  date TEXT NOT NULL,
  tool TEXT NOT NULL,
  sequences_count INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Payments
CREATE TABLE payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_email TEXT NOT NULL,
  amount REAL NOT NULL,
  upi_ref TEXT,
  status TEXT DEFAULT 'pending',
  runs_purchased INTEGER DEFAULT 0,
  product_type TEXT,
  plan_id TEXT,
  billing_cycle TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  verified_at TEXT
);

-- Saved Results
CREATE TABLE saved_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_email TEXT NOT NULL,
  tool TEXT NOT NULL,
  title TEXT,
  inputs TEXT,            -- JSON
  outputs TEXT,           -- JSON
  sequences_count INTEGER DEFAULT 0,
  job_id TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Additional tables: token_blacklist, usage_log, monthly_usage,
-- user_reports, academic_claims, referrals, feedback_submissions, login_logs
```

### 5.3 PostgreSQL Schema (25+ tables)

In addition to the SQLite-equivalent tables, PostgreSQL has:

**Extended Entities:**
- `token_balances` — Per-user balance with lifetime revenue/cost tracking
- `subscriptions` — Active subscription with quota, seat count, Razorpay subscription ID
- `payments` — Full payment tracking with gateway IDs, metadata JSON
- `email_verifications` — Email verification tokens with 24h expiry
- `password_resets` — Password reset tokens
- `gateway_webhooks` — Raw Razorpay webhook payloads for audit
- `system_events` — System-level event log with severity/module tagging
- `cost_ledger` — Per-operation cost tracking (CPU seconds, tokens, revenue)
- `audit_logs` — Comprehensive audit trail with user_id, job_id, accession, action

**Views:**
- `v_monthly_pnl` — Monthly profit/loss
- `v_roi_dashboard` — ROI dashboard
- `v_token_economics` — Token economics
- `v_admin_cost_breakdown` — Admin cost breakdown
- `v_user_profitability` — Per-user profitability

**Functions:**
- `fn_record_operation_cost()` — Records cost after pipeline completion
- `fn_user_financial_summary()` — User-level financial aggregation

### 5.4 Connection Pool (PostgreSQL)

```python
pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=2, maxconn=10,
    timeout=15,
    database=DB_NAME, host=DB_HOST, port=DB_PORT,
    user=DB_USER, password=DB_PASSWORD,
    sslmode=DB_SSL_MODE
)
```

- Session timeouts: `statement_timeout='30s'`, `idle_in_transaction_session_timeout='30s'`
- Row-Level Security: `SET app.current_user_id = %s` on each session
- All queries use parameterized statements (no string interpolation)

---

## 6. Authentication & Authorization

### 6.1 Authentication Methods

| Method | Endpoint | Use Case |
|--------|----------|----------|
| Email + Password | `POST /api/auth/register`, `/login` | Primary auth |
| Google OAuth 2.0 | `POST /api/auth/google` | Social login |
| Token Refresh | `POST /api/auth/refresh` | Session extension (PG only) |

### 6.2 Token System

```
Format: base64url(payload) || "." || HMAC-SHA256(payload, SECRET_KEY)

Payload: { email, user_id?, exp (7 days), iat }
```

- Tokens stored in `sessionStorage` (session) + `localStorage` (persist) via frontend
- 7-day expiry with refresh token option (30 days) in PostgreSQL mode
- Blacklisted tokens tracked in `token_blacklist` table (SQLite) or in-memory cache + DB `token_blacklist` table (PG) for server-restart safety

### 6.3 Progressive Lockout

Failed login attempts trigger escalating lockout:
- 3 failures → 60s lockout
- 5 failures → 300s lockout
- 10 failures → 3600s lockout
- 20 failures → 86400s lockout (24 hours)

### 6.4 Auth Decorators

- `@require_auth` — Validates token, sets `g.user`, rejects with 401 if invalid
- `@require_admin` — Extends `@require_auth`, checks `role == 'admin'`
- Session limit (PG): `MAX_SESSIONS=5` — oldest session evicted on excess

### 6.5 Frontend Auth Flow

```
Page Load
  └─ auth-shared.js IIFE runs
      ├─ updateAuthUI() — Shows login buttons or user profile
      └─ loadPlanUI() — Fetches /api/payments/status
          ├─ Inject plan badge into user popup
          ├─ Add gated nav items (Team, API, Admin)
          └─ Add Upgrade CTA (Free→Pro, Pro→Lab)

User clicks "Subscribe to Pro" (no token):
  └─ purchasePlan() → openAuthModal() → renderAuth()
      ├─ Email/password form
      ├─ Google OAuth button (GSI SDK loaded on-demand)
      └─ submitAuth() → POST /api/auth/register|login
          ├─ Success: store token, close modal, retry purchasePlan
          └─ Failure: show error message
```

### 6.6 Email Verification System (Aug 2026, Hardened)

Complete email verification flow with security hardening and transport reliability:

#### Overview

```
User registers → Backend creates user (status: pending) →
Backend generates token → Token SHA-256 hashed + stored in DB →
Verification email sent via Brevo API (3x retry + SMTP fallback) →
User clicks link → Frontend reads token from URL →
Sends POST to /api/auth/verify-email →
Backend hashes token → DB lookup → Activate user + grant tokens
```

#### Token Security

| Property | Value | Rationale |
|----------|-------|-----------|
| **Generation** | `secrets.token_urlsafe(48)` | 384-bit entropy, cryptographically secure |
| **Format** | 64-char URL-safe base64 | Validated via regex `^[A-Za-z0-9_-]{64}$` |
| **Storage** | SHA-256 hash (`_hash_token()`) | DB breach ≠ token compromise |
| **Hash input** | `PRIMERFORGE_SECRET + "_token_hash"` + token | Prevents rainbow table attacks |
| **Expiry** | 24 hours (`INTERVAL '24 hours'`) | Time-limited verification window |
| **Uniqueness** | UNIQUE constraint on `user_id` | One active token per user |
| **Idempotency** | Consumed token + active user → `True` | Fixes Brevo pre-fetch race condition |

#### Verification Flow (3 Cases)

```
verify_email_with_token(token):
  1. Validate token format (reject malformed tokens early)
  2. Hash token with SHA-256
  3. DB lookup: WHERE token = hash AND verified_at IS NULL
     ├─ FOUND + not expired + user pending →
     │   Atomic transaction: mark consumed + activate user + grant 2 tokens
     │   Returns True
     ├─ FOUND + not expired + user already active →
     │   Returns True (idempotent — Brevo pre-fetch fix)
     └─ NOT FOUND →
         Check consumed tokens: WHERE token = hash AND verified_at IS NOT NULL
         ├─ Found + user active → Returns True (idempotent)
         └─ Not found → Returns False
```

#### Email Transport (Hardened with 3x Retry)

```
send_verification_email(email, token):
  Priority 1: Brevo API (if BREVO_API_KEY set)
    POST https://api.brevo.com/v3/smtp/email
    Headers: api-key: xkeysib-...
    Body: { sender, to, subject, htmlContent }
    Retry: 3 attempts with exponential backoff (2s, 4s, 8s)
    
  Priority 2: SMTP fallback (if SMTP_HOST/USER/PASSWORD set)
    smtp-relay.brevo.com:587 (STARTTLS)
    Login: b02500001@smtp-brevo.com
    Retry: 3 attempts with exponential backoff
    
  Failure Handling:
    - register_user() returns email_sent: bool
    - If both transports fail → user created but email_sent=False
    - Frontend shows yellow warning: "Account created but verification email failed"
    - Frontend displays inline "Resend Verification" button
    - User can resend via POST /api/auth/resend-verification
    
  Dev mode: Log token to console (VIGYANLLM_ENV=development)
```

#### Registration Response

```
POST /api/auth/register
Response (201):
{
  "message": "Account created. Check your email to verify.",
  "token": "...",           // Auth token (for immediate login)
  "email_sent": true        // Whether verification email was sent
}

If email fails:
{
  "message": "Account created but verification email could not be sent. Use resend.",
  "token": "...",
  "email_sent": false
}
```

#### Frontend Implementation

```
verify-email.html:
  - Reads token from URL: ?token=...
  - Sends POST to /api/auth/verify-email { token }
  - Prevents token from appearing in:
    • Browser history (GET URLs logged)
    • Server access logs (query strings logged)
    • Referrer headers
  - Idempotent UI: success OR "Try signing in" (never "failed")
  - Resend section: email input → POST /api/auth/resend-verification

auth-shared.js (submitAuth):
  - On register success: checks email_sent field
  - If email_sent=false: shows yellow warning banner with inline resend button
  - resendVerif() → POST /api/auth/resend-verification { email }
  - Shows success/error feedback without page reload
```

#### Rate Limits

| Action | Limit | Window | Scope |
|--------|-------|--------|-------|
| Registration | 5 accounts | 1 hour | Per IP |
| Verify email | 10 requests | 1 minute | Per endpoint |
| Resend verification | 5 emails | 24 hours | Per email |
| Password reset | 3 requests | 1 hour | Per email |
| Login | 5 failures → 15 min lockout | — | Per account |
| IP login brute force | 20 failures | 15 minutes | Per IP |

---

## 7. Payment & Subscription System

### 7.1 Price Registry (`price_registry.py`)

The canonical pricing source using a `PlanConfig` dataclass:

```python
@dataclass(frozen=True)
class PlanConfig:
    plan_id: str              # e.g., "pro-monthly"
    tier: PlanTier            # FREE, PRO, LAB, ENTERPRISE
    display_name: str         # "Pro"
    billing: BillingCycle     # MONTHLY, YEARLY, ONETIME, CUSTOM
    price_inr: int            # 699 (in INR)
    daily_analyses: int       # 100
    batch_max_seq: int        # 50
    api_calls_per_month: int  # 1000
    max_seats: int            # 1
    has_export_pdf: bool
    has_export_ppt: bool
    has_saved_results: bool
    has_advanced_docking: bool
    has_collaboration: bool
    has_admin_panel: bool
    # ... 22 feature flags total
```

### 7.2 Razorpay Integration

Subscription flow:

```
Frontend                          Backend                        Razorpay
   │                                │                              │
   ├─ purchasePlan(planId)          │                              │
   │  └─ POST /api/payments/        │                              │
   │     create-order               │                              │
   │     { plan_id: "pro-monthly" } │                              │
   │                                ├─ validate_plan(planId)       │
   │                                ├─ get_amount_paise()          │
   │                                ├─ Check academic discount     │
   │                                ├─ razorpay.order.create() ────┤
   │                                │    { amount, currency,       │
   │                                │      receipt, notes }        │
   │                                ├─ Store order in DB           │
   │                                ├─ Return { order_id,          │
   │                                │    amount, key_id }          │
   │                                │                              │
   ├─ loadRazorpaySdk()             │                              │
   ├─ rzp.open() ────────────────────────────────────────────────┤
   │  (Razorpay Checkout)           │                              │
   │                                │                              │
   ├─ Payment success callback      │                              │
   │  └─ POST /api/payments/        │                              │
   │     verify-payment             │                              │
   │     { razorpay_payment_id,     │                              │
   │       razorpay_order_id,       │                              │
   │       razorpay_signature }     │                              │
   │                                ├─ HMAC-SHA256 verification    │
   │                                ├─ GET /payments/:id (PG only) │
   │                                ├─ Activate plan on users      │
   │                                ├─ Return success              │
   │                                │                              │
   ├─ Redirect to /payment-success.html                            │
```

### 7.3 Payment Routes Comparison

| Feature | SQLite (`payment_routes.py`) | PostgreSQL (`pg_payment_routes.py`) |
|---------|------------------------------|-------------------------------------|
| **Plan activation** | `UPDATE users SET plan, plan_expires_at` | `INSERT INTO subscriptions` with monthly quota |
| **Token/top-up model** | Not supported | Full support via `token_balances` table |
| **Server-side payment confirm** | HMAC only | HMAC + Razorpay GET /payments/:id API |
| **Webhook secret** | Single `RAZORPAY_WEBHOOK_SECRET` | Must be set independently (no fallback) |
| **Admin financials** | Basic | Full P&L, ROI, user profitability, revenue stats |
| **Subscription webhooks** | Not supported | `subscription.charged`, `.halted`, `.cancelled` |

### 7.4 Academic Discount

- Auto-detected on registration (`.edu` / `.ac.in` / `.edu.in` email domains)
- 30% discount applied at checkout
- Discount reflected in both frontend display and backend pricing
- Manual verification endpoint: `POST /api/auth/verify-academic`

---

## 8. Pipeline Engine

### 8.1 Overview

The primer design pipeline is a 24-step sequential workflow that transforms a gene accession/sequence into validated, ranked primer pairs. It's the most complex subsystem in the platform.

### 8.2 Step Structure

```
Phase A: Sequence Processing & Consensus (Steps 1–7)
  ├── 1.  Transcript Isoform Filter
  ├── 2.  Exon-Intron Junction Mapping
  ├── 3.  Bisulfite Conversion Simulation
  ├── 4.  Degenerate Base Parsing
  ├── 5.  Repeat Masking
  ├── 6.  Backend MSA & Conservation Scoring
  └── 7.  Conserved Region Targeting

Phase B: Thermodynamic Validation (Steps 8–11)
  ├── 8.  Primer3 Parameter Constraints
  ├── 9.  Nearest-Neighbor Tm (SantaLucia 1998)
  ├── 10. Dynamic Buffer & Salt Adjustments
  └── 11. Divalent Cation Mg2+ Scaling

Phase C: Specificity & Inclusivity (Steps 12–16)
  ├── 12. Target Specificity BLAST + Viewer
  ├── 13. Strain Inclusivity & Discontinuous
  ├── 14. Structural Alignment (Bowtie2)
  ├── 15. Organelle & Pseudogene Screening
  └── 16. Primer Secondary Structure dG

Phase D: Structural & Multiplex Analysis (Steps 17–22)
  ├── 17. Amplicon Structural Verification
  ├── 18. Population Variant Filter (dbSNP)
  ├── 19. Clinical Hotspot Filter (ClinVar)
  ├── 20. 5' Overhang Adapter Tailing
  ├── 21. Multiplex Cross-Reaction Scoring
  └── 22. Penalty & Ranking Matrix

Phase E: Profiling & Export (Steps 23–24)
  ├── 23. Thermocycling Profile Generation
  └── 24. Probe Design (qPCR/TaqMan)
```

### 8.3 Modes

| Mode | Steps | Use Case |
|------|-------|----------|
| **Full** | All 24 | Comprehensive primer design |
| **Express** | 1, 6, 7, 10, 19, 22 | Quick results (standard tools) |

### 8.4 Orchestrator (`orchestrator.py`)

```python
class PipelineOrchestrator:
    """Sequential step executor with timeout, validation, and error recovery."""

    def __init__(self, config: PipelineConfig):
        self.config = config          # Target sequence, params
        self.context = {}             # Shared step context
        self.step_results = {}         # Per-step results
        self.errors = []               # Error collection

    def run(self) -> PipelineOutcome:
        for step in self.steps:
            if not self._should_run(step):
                continue              # Skip optional steps
            result = self._execute_step_with_timeout(step)
            validate_step_output(result)  # SEC-13 validation
            self.step_results[step.id] = result
        return PipelineOutcome(self.step_results)

    def _execute_step_with_timeout(self, step, timeout=120):
        """Execute a pipeline step with a timeout guard."""
```

### 8.5 Celery Integration

```python
@celery_app.task(base=FlaskTask, bind=True, time_limit=600, max_retries=2)
def run_pipeline(self, job_id: str, config: dict):
    orchestrator = PipelineOrchestrator(PipelineConfig(**config))
    outcome = orchestrator.run()
    return outcome.to_dict()
```

- Broker: Redis (password-protected)
- Task time limit: 600 seconds (10 minutes)
- Prefetch: 1 task at a time per worker
- Flask application context injected via `FlaskTask` base class

### 8.6 Bioinformatics Dependencies

| Tool | Purpose | Integration |
|------|---------|-------------|
| **Primer3** | Primer design core | `primer3-py` Python bindings |
| **NCBI BLAST** | Sequence similarity search | Local binaries (`tools/ncbi-blast-2.17.0+`) |
| **Bowtie2** | Structural alignment | Local binary |
| **Clustal Omega** | Multiple sequence alignment | System binary |
| **ViennaRNA** | RNA secondary structure | System package |
| **OpenBabel** | Chemical file format conversion | System package |

---

## 9. Deployment & DevOps

### 10.1 Deployment Architecture

```
GitHub (main branch)
    │
    ├── Push → GitHub Actions
    │       │
    │       ├── Quality Job
    │       │   ├── ruff lint
    │       │   ├── syntax check
    │       │   ├── bandit security scan
    │       │   ├── safety check
    │       │   └── pytest
    │       │
    │       └── Deploy Job (on lint pass)
    │           ├── SSH into EC2
    │           ├── git pull
    │           ├── .venv + pip install
    │           ├── Write .env from secrets
    │           ├── Start PostgreSQL + Redis
    │           ├── Run migrations
    │           ├── Restart vigyan.service
    │           └── Health check via Vercel proxy
    │
    └── Vercel Auto-Deploy (frontend/ only)
        ├── Static site deploy
        ├── Edge Functions deploy
        └── Edge Middleware deploy
```

### 10.2 Vercel Deployment

- **Trigger:** Push to `main` branch
- **Output directory:** `frontend/`
- **Excluded:** Python files, Docker files, database files, env files (via `.vercelignore`)
- **Edge Functions:** `/api/sitemap.xml.js` generates dynamic sitemap
- **Clean URLs:** Enabled — no `.html` extensions

### 10.3 EC2 Backend Deployment

- **Server:** AWS EC2 t3.medium
- **Process Manager:** systemd (`vigyan.service`)
- **Health Check:** Cron job every 5 min (`deploy/healthcheck.sh`)
- **Auto-restart:** systemd `Restart=on-failure` with backoff (5s → 30s max)
- **Logs:** `/var/log/vigyan/access.log`, `/var/log/vigyan/error.log`

### 10.4 SystemD Service (`vigyan.service`)

```ini
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/vigyanpilot
Environment=PATH=/home/ubuntu/vigyanpilot/.venv/bin:/usr/bin
EnvironmentFile=/home/ubuntu/vigyanpilot/.env
ExecStartPre=/home/ubuntu/vigyanpilot/.venv/bin/python \
    /home/ubuntu/vigyanpilot/deploy/migrations/migrate.py
ExecStart=/home/ubuntu/vigyanpilot/.venv/bin/gunicorn \
    -c /home/ubuntu/vigyanpilot/deploy/gunicorn.conf.py \
    wsgi:app
Restart=on-failure
RestartSec=5
RestartSteps=3
RestartMaxDelaySec=30
LimitNOFILE=65536
LimitNPROC=4096
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/home/ubuntu/vigyanpilot /var/log/vigyan /tmp
PrivateTmp=true
```

### 10.5 Docker Compose (Docker-based Alternative)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    deploy: { resources: { limits: { memory: 512M, cpus: '1' } } }
  redis:
    image: redis:7-alpine
    deploy: { resources: { limits: { memory: 192M, cpus: '0.5' } } }
  app:
    build: .
    deploy: { resources: { limits: { memory: 1G, cpus: '2' } } }
    read_only: true
    tmpfs: /tmp
  nginx:
    image: nginx:alpine
    ports: [80, 443]
    deploy: { resources: { limits: { memory: 256M, cpus: '0.5' } } }
```

---

## 11. Security Architecture

### 11.1 Defense Layers

```
Layer 1: Vercel Edge
├── Malicious crawler blocking (middleware.js)
├── Admin path protection (cookie-based RBAC)
└── CSP headers (per-page configuration)

Layer 2: Nginx (Docker)
├── SSL termination (TLSv1.2/1.3)
├── Request size limit (10MB)
├── Security headers (X-Frame-Options, X-Content-Type-Options)
└── CORS validation

Layer 3: Flask Application
├── Flask-Talisman (CSP, HSTS 1 year, X-Frame-Options DENY)
├── Flask-Limiter (200/min default, 5000/hour)
│   ├── auth.login: 5/min
│   ├── auth.register: 3/min
│   └── payments.*: 10/min
├── CORS with origin allowlist
├── Custom error handlers (no stack traces)
├── Admin RBAC before_request middleware
├── Server header suppression
└── Production env validation (fail-fast)

Layer 4: Application Code
├── bcrypt password hashing
├── HMAC-SHA256 token signing
├── Token hashing at rest (SHA-256 with secret prefix)
├── Persistent token blacklist (survives server restarts)
├── Progressive login lockout (5 fails → 15 min)
├── IP brute-force protection (20 failures → 15 min)
├── Constant-time bcrypt dummy hash (prevents user enumeration)
├── Parameterized SQL queries (no injection)
├── bleach HTML sanitization
├── Fernet AES-256 encryption for stored results
├── Input validation: email (RFC-5321), password (complexity), token format, quantity (reject floats/NaN)
├── File scan on uploads
├── Step output validation in pipeline engine
├── Atomic DB transactions (email verification)
└── Registration IP rate limiting (5/hour per IP)

Layer 5: System
├── systemd security hardening (NoNewPrivileges, ProtectSystem, PrivateTmp)
├── Docker read-only rootfs with tmpfs
├── Non-root user (vigyan) in container
├── Redis requires AUTH password
├── PostgreSQL SSL enforced
└── Regular security audits (bandit, safety)
```

### 11.2 Compliance

| Standard | Status | Key Measures |
|----------|--------|--------------|
| **DPDP (India)** | Compliant | Consent requirement, right to erasure (`DELETE /api/auth/account`), data portability (`GET /api/auth/export`), data correction (`PUT /api/auth/profile`), PII masking |
| **GDPR** | Considerate | Data export, account deletion, cookie consent |
| **HIPAA** | Not claimed | Actively removed from all marketing materials |

### 11.3 Rate Limit Endpoint Map

| Endpoint Pattern | Rate Limit | Window | Source |
|-----------------|------------|--------|--------|
| `/api/auth/register` | 5 | 1 hour | `pg_auth_routes.py` + `security.py` |
| `/api/auth/login` | 5 failures → 15 min lockout | per account | `pg_auth.py` |
| `/api/auth/login` (IP) | 20 failures | 15 min | `pg_auth.py` |
| `/api/auth/forgot-password` | 3 | 1 hour | `security.py` + `pg_auth_routes.py` |
| `/api/auth/resend-verification` | 5 | 24 hours | `pg_auth_routes.py` |
| `/api/payments/verify-payment` | 10/minute | — | `security.py` |
| `/api/payments/create-order` | 10/minute | — | `security.py` |
| All other `/api/*` | 30/minute | — | `security.py` |

### 11.4 Token Security (Aug 2026)

| Measure | Implementation | Protection |
|---------|----------------|-------------|
| **Token generation** | `secrets.token_urlsafe(48)` = 64 chars, 384 bits | Cryptographically secure |
| **Token hashing** | SHA-256 with `PRIMERFORGE_SECRET + "_token_hash"` prefix | DB breach ≠ token compromise |
| **Persistent blacklist** | `token_blacklist` table (SQLite) + in-memory (PG) | Revoked tokens stay invalid across restarts |
| **Format validation** | `^[A-Za-z0-9_-]{64}$` regex | Reject malformed tokens before DB lookup |
| **Atomic verification** | `db.cursor()` transaction with rollback | Prevents partial activation on DB failure |
| **POST verify-email** | Frontend sends token via POST body | Prevents browser history / server log leakage |
| **Idempotent verification** | Consumed token + active user → True | Safe for Brevo pre-fetch / email clients |
| **Expiry** | 24 hours | Time-limited verification window |
| **Uniqueness** | UNIQUE constraint on `user_id` | One active token per user |

### 11.5 Encryption

- **At Rest:** Fernet AES-256 (`cryptography` library) for pipeline result storage; SHA-256 for verification tokens
- **In Transit:** TLS 1.2/1.3 (Let's Encrypt SSL)
- **Passwords:** bcrypt with work factor 12
- **API Tokens:** HMAC-SHA256 signed
- **Verification Tokens:** SHA-256 hashed with secret prefix before DB storage

---

## 12. Tech Stack Summary

### 12.1 Complete Technology Map

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Frontend** | HTML5 / CSS3 | — | Static pages (410+) |
| | Vanilla JavaScript | ES2022 | Client-side logic |
| | Vercel | — | CDN + Edge Functions |
| **Backend** | Python | 3.11+ | Application language |
| | Flask | 3.1.3 | Web framework |
| | Gunicorn | 22.0.0 | WSGI server |
| | Celery | 5.4.0 | Async task queue |
| | Redis | 7 | Cache + MQ |
| **Database** | PostgreSQL | 16 | Production DB |
| | SQLite | 3 | Development DB |
| **Payment** | Razorpay | 1.4.2 | Payment gateway |
| **Auth** | bcrypt | 5.0.0 | Password hashing |
| | Google OAuth | GSI | Social login |
| | HMAC-SHA256 | — | Token signing |
| **Bioinformatics** | Biopython | 1.87 | Sequence I/O |
| | primer3-py | 2.3.0 | Primer design |
| | RDKit | 2024.03 | Cheminformatics |
| | NCBI BLAST | 2.17.0 | Sequence search |
| | Bowtie2 | — | Structural alignment |
| | Clustal Omega | — | MSA |
| | ViennaRNA | — | RNA structure |
| **Security** | Flask-Talisman | 1.1.0 | Security headers |
| | Flask-Limiter | 3.8.0 | Rate limiting |
| | bleach | 6.4.0 | Input sanitization |
| | cryptography | 44.0.2 | Encryption |
| **CI/CD** | GitHub Actions | — | Lint + deploy |
| | Ruff | — | Python linter |
| | bandit | — | Security scanner |
| | pytest | — | Test runner |
| **Cloud** | Vercel | — | Frontend hosting |
| | AWS EC2 | t3.medium | Backend hosting |
| | AWS RDS / Local PG | 16 | Database |
| **Monitoring** | systemd | — | Process supervision |
| | Cron | — | Health checks (5min) |
| | journald | — | Log aggregation |

### 12.2 Dependency Count

- **requirements.txt:** 22 direct dependencies
- **Node.js (backend/):** ~15 dependencies (legacy CMS, not actively used)
- **System packages:** ~12 bioinformatics tools

---

## 13. Data Flow Diagrams

### 13.1 User Registration Flow

```
User                        Frontend                      Backend                     Database
 │                            │                              │                          │
 ├─ Click "Sign in"           │                              │                          │
 │  └─ openAuthModal()        │                              │                          │
 │                            ├─ renderAuth()                │                          │
 │                            │  └─ Email/password form      │                          │
 ├─ Fill form + Submit        │                              │                          │
 │  └─ submitAuth()           │                              │                          │
 │                            ├─ POST /api/auth/register ────┤                          │
 │                            │  { email, password, name }    │                          │
 │                            │                              ├─ Validate input            │
 │                            │                              ├─ Check email uniqueness    │
 │                            │                              ├─ Hash password (bcrypt)    │
 │                            │                              ├─ Detect academic email     │
 │                            │                              ├─ Generate token            │
 │                            │                              ├─ INSERT user (pending) ───┤
 │                            │                              ├─ Send verification email   │
 │                            │                              │  (Brevo API 3x retry)     │
 │                            │                              ├─ Return { token,           │
 │                            │                              │    email_sent: bool }      │
 │                            │                              │                          │
 │                            ├─ Store token in sessionStorage│                          │
 │                            ├─ IF email_sent=false:         │                          │
 │                            │  └─ Show yellow warning       │                          │
 │                            │     + inline resend button    │                          │
 │                            ├─ closeAuth()                  │                          │
 │                            ├─ updateAuthUI()               │                          │
 │                            │  └─ Show user profile avatar  │                          │
 │                            │                              │                          │
 ├─ Check email inbox         │                              │                          │
 │  └─ Click verification link│                              │                          │
 │                            ├─ verify-email.html            │                          │
 │                            │  └─ POST /api/auth/           │                          │
 │                            │     verify-email ────────────┤                          │
 │                            │     { token }                 │                          │
 │                            │                              ├─ Hash token               │
 │                            │                              ├─ DB lookup                │
 │                            │                              ├─ Activate user ──────────┤
 │                            │                              ├─ Grant tokens             │
 │                            │                              ├─ Return success           │
 │                            │                              │                          │
 ├─ See profile popup         │                              │                          │
 │  └─ Plan badge: Free       │                              │                          │
 │  └─ Upgrade CTA            │                              │                          │
```

### 13.2 Subscription Payment Flow

```
User                        Frontend                      Backend                     Razorpay
 │                            │                              │                          │
 ├─ Click "Subscribe to Pro"  │                              │                          │
 │  └─ purchasePlan('pro-monthly')                           │                          │
 │                            ├─ getToken()                  │                          │
 │                            │  (if no token → openAuthModal)│                          │
 │                            ├─ showLoading(true)           │                          │
 │                            ├─ POST /api/payments/create   │                          │
 │                            │  -order ────────────────────┤                          │
 │                            │  { plan_id: 'pro-monthly' }  │                          │
 │                            │                              ├─ Validate plan             │
 │                            │                              ├─ Get price from registry   │
 │                            │                              ├─ Check academic discount   │
 │                            │                              ├─ razorpay.order.create() ──┤
 │                            │                              │  { amount: 69900,          │
 │                            │                              │    currency: INR,           │
 │                            │                              │    receipt, notes }         │
 │                            │                              ├─ INSERT payment ────────► DB
 │                            │                              ├─ Return order details      │
 │                            │                              │                          │
 │                            ├─ loadRazorpaySdk()           │                          │
 │                            ├─ openRazorpayCheckout(order)  │                          │
 │                            │  └─ rzp.open() ──────────────────────────────────────┤
 │                            │                              │        Razorpay Checkout  │
 ├─ Complete payment (UPI/Card/NB)                          │                          │
 │                            │                              │                          │
 │                            ├─ handler callback            │                          │
 │                            │  └─ POST /api/payments/      │                          │
 │                            │     verify-payment ─────────┤                          │
 │                            │     { razorpay_payment_id,   │                          │
 │                            │       razorpay_order_id,     │                          │
 │                            │       razorpay_signature }   │                          │
 │                            │                              ├─ HMAC-SHA256 verify        │
 │                            │                              ├─ GET /payments/:id (PG) ──┤
 │                            │                              ├─ Activate plan on user    │
 │                            │                              │  ──────────────────────► DB
 │                            │                              ├─ Return success            │
 │                            │                              │                          │
 │                            ├─ Redirect to                 │                          │
 │                            │  /payment-success.html       │                          │
```

### 13.3 Primer Design Pipeline Flow

```
User                     Frontend                    Flask Backend           Celery Worker
 │                          │                            │                      │
 ├─ Enter gene accession    │                            │                      │
 ├─ Click "Design Primers"  │                            │                      │
 │                          ├─ POST /api/primer/         │                      │
 │                          │  auto_design ─────────────┤                      │
 │                          │  { accession, params }     │                      │
 │                          │                            ├─ validate_inputs()    │
 │                          │                            ├─ check_usage()        │
 │                          │                            │  (plan-aware limits)  │
 │                          │                            ├─ Generate job_id      │
 │                          │                            ├─ Return job_id +      │
 │                          │                            │  status: queued       │
 │                          │                            │                      │
 │                          │                            ├─ Celery: run_pipeline │
 │                          │                            │  .delay(job_id, conf)  │
 │                          │                            │         │             │
 │                          │                            │    ┌────┘             │
 │                          │                            │    ▼                  │
 │                          │                            ├─ PipelineOrchestrator │
 │                          │                            │  .run()               │
 │                          │                            │  ├─ Step 1: Isoform   │
 │                          │                            │  ├─ Step 2: Junction  │
 │                          │                            │  ├─ ... (24 steps)    │
 │                          │                            │  │                    │
 │                          │                            │  ├─ Step 22: Ranking  │
 │                          │                            │  └─ Step 24: Probe    │
 │                          │                            │                      │
 │                          │                            ├─ record_daily_usage() │
 │                          │                            ├─ Store result ─────► DB
 │                          │                            │                      │
 ├─ Poll for status         │                            │                      │
 │  └─ GET /api/primer/     │                            │                      │
 │     status/{job_id} ─────┤                            │                      │
 │                          ├─ Return { result }         │                      │
 │                          │                            │                      │
 ├─ View primer pairs       │                            │                      │
 ├─ "Save to Dashboard"     │                            │                      │
 │  └─ POST /api/results/   │                            │                      │
 │     save ───────────────┤                            │                      │
 │                          ├─ INSERT saved_results ───► DB                    │
 │                          │                            │                      │
 ├─ "Export PDF"            │                            │                      │
 │  └─ POST /api/export/pdf────────────────────────────┤                      │
 │                          │                            ├─ Generate PDF (fpdf2)│
 │                          │                            ├─ Return file          │
```

---

## 14. API Reference

### 14.1 Auth Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/auth/register` | Create account (auto-detects academic email) | No |
| `POST` | `/api/auth/login` | Login with progressive lockout | No |
| `POST` | `/api/auth/google` | Google OAuth2 (ID token or access token) | No |
| `GET` | `/api/auth/verify-email` | Verify email (GET for email links) | No |
| `POST` | `/api/auth/verify-email` | Verify email (POST for frontend) | No |
| `POST` | `/api/auth/resend-verification` | Resend verification email (5/24h per email) | No |
| `POST` | `/api/auth/forgot-password` | Request password reset | No |
| `POST` | `/api/auth/reset-password` | Reset password with token | No |
| `GET` | `/api/auth/me` | Current user profile + usage | Yes |
| `GET` | `/api/auth/check-usage` | Usage status | Yes |
| `POST` | `/api/auth/logout` | Revoke token | Yes |
| `POST` | `/api/auth/verify-academic` | Verify academic email | Yes |
| `POST` | `/api/auth/refresh` | Refresh token exchange (PG only) | Yes |
| `POST` | `/api/auth/change-password` | Change password + invalidate sessions | Yes |
| `GET` | `/api/auth/export` | DPDP data portability (full JSON export) | Yes |
| `DELETE` | `/api/auth/account` | DPDP right to erasure (anonymize) | Yes |

### 14.2 Payment Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/payments/create-order` | Create Razorpay order | Yes |
| `POST` | `/api/payments/verify-payment` | Verify HMAC + activate plan | Yes |
| `GET` | `/api/payments/status` | Current plan + usage status | Yes |
| `GET` | `/api/payments/pricing` | Public pricing data | No |
| `POST` | `/api/payments/webhook` | Razorpay webhooks | Webhook secret |
| `GET` | `/api/usage/check` | Daily usage limits check | Yes |
| `POST` | `/api/usage/record` | Record completed analysis | Yes |

### 14.3 Tool Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/primer/auto-design` | Run primer design pipeline | Yes |
| `POST` | `/api/primer/manual-analyze` | Analyze manual primers | Yes |
| `POST` | `/api/blast/search` | BLAST sequence search | Yes |
| `POST` | `/api/msa/align` | Multiple sequence alignment | Yes |
| `POST` | `/api/docking/run` | Molecular docking | Yes |
| `POST` | `/api/thermodynamics/tm` | Tm calculation | Yes |
| `POST` | `/api/thermodynamics/gc` | GC content calculation | Yes |

### 14.4 Results & Export Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/results/save` | Save result to dashboard | Yes |
| `GET` | `/api/results/list` | List saved results (paginated) | Yes |
| `POST` | `/api/results/delete` | Delete saved result | Yes |
| `POST` | `/api/export/pdf` | Export result as PDF | Yes |
| `POST` | `/api/export/pptx` | Export result as PPTX | Yes |

### 14.5 Admin Endpoints (PG only)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/admin/users` | List all users | Admin |
| `GET` | `/api/admin/logs` | Usage logs | Admin |
| `GET` | `/api/admin/payments` | Payment history | Admin |
| `GET` | `/api/admin/stats` | System statistics | Admin |
| `POST` | `/api/admin/users/:id/block` | Block user | Admin |
| `POST` | `/api/admin/users/:id/unblock` | Unblock user | Admin |
| `POST` | `/api/admin/users/:id/role` | Change user role | Admin |
| `GET` | `/api/payments/financial-summary` | P&L + ROI dashboard | Admin |

### 14.6 System Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | No |
| `GET` | `/api/config/public` | Public configuration | No |
| `GET` | `/api/sitemap.xml` | Dynamic sitemap (Edge Function) | No |

---

## 15. Development Setup

### 15.1 Prerequisites

- Python 3.11+
- PostgreSQL 16 (optional, SQLite works for development)
- Redis 7 (optional, in-memory fallback for rate limiting)
- Node.js 18+ (for Vercel Edge Functions testing)

### 15.2 Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/vigyanllm0/vigyanpilot.git
cd vigyanpilot

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings (Razorpay test keys, etc.)

# 5. Set up frontend config
echo 'window.VIGYAN_BACKEND_URL = "";' > frontend/config.js
# Empty string = same-origin (/api/* prefix)

# 6. Run database migration
python deploy/migrations/migrate.py

# 7. Start development server
python start.sh
# Or directly:
gunicorn -c deploy/gunicorn.conf.py wsgi:app

# 8. Start frontend (separate terminal)
cd frontend && python3 -m http.server 8080
```

### 15.3 Environment Variables

```bash
# Required (app fails without these)
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
PRIMERFORGE_SECRET=<64-char-hex>     # Session/token signing
PRIMERFORGE_ADMIN_EMAIL=admin@...
PRIMERFORGE_ADMIN_PASSWORD=...

# Database (SQLite used if DATABASE_URL not set)
DATABASE_URL=postgresql://user:pass@localhost:5432/vigyan_prod
DB_SSL_MODE=require

# Redis (in-memory fallback if not set)
REDIS_URL=redis://:password@localhost:6379/0
REDIS_PASSWORD=...

# Email (Brevo API preferred, SMTP fallback)
BREVO_API_KEY=xkeysib-...           # Brevo API key
SMTP_HOST=smtp-relay.brevo.com      # SMTP fallback
SMTP_PORT=587
SMTP_USER=b02500001@smtp-brevo.com
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=noreply@vigyanllm.in

# Optional
GOOGLE_CLIENT_ID=...                 # Google OAuth
NCBI_API_KEY=...                     # NCBI E-utilities (higher rate limit)
DATA_ENCRYPTION_KEY=...              # Fernet key for result encryption
```

### 15.4 Code Quality

```bash
# Lint
ruff check .

# Type check
mypy primerforge/

# Security scan
bandit -r primerforge/

# Tests
pytest
```

---

## Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| **CSP** | Content Security Policy — HTTP header controlling allowed resources |
| **DPDP** | Digital Personal Data Protection Act (India 2023) |
| **GSI** | Google Sign-In — OAuth 2.0 / OpenID Connect library |
| **HMAC** | Hash-based Message Authentication Code |
| **MSA** | Multiple Sequence Alignment |
| **NN** | Nearest-Neighbor — thermodynamic model for DNA melting temperature |
| **PG** | PostgreSQL |
| **RBAC** | Role-Based Access Control |

### B. Key File Locations

| Resource | Path |
|----------|------|
| Frontend root | `frontend/` |
| Flask app factory | `primerforge/primer_server.py` |
| Price registry | `primerforge/price_registry.py` |
| Payment routes (SQLite) | `primerforge/payment_routes.py` |
| Payment routes (PG) | `primerforge/pg_payment_routes.py` |
| Auth routes (SQLite) | `primerforge/auth_routes.py` |
| Auth routes (PG) | `primerforge/pg_auth_routes.py` |
| Pipeline orchestrator | `primerforge/engine/orchestrator.py` |
| Token blacklist migration | `deploy/migrations/0113_token_blacklist.sql` |
| Gunicorn config | `deploy/gunicorn.conf.py` |
| Systemd service | `deploy/vigyan.service` |
| Docker Compose | `deploy/docker-compose.yml` |
| Nginx config | `deploy/nginx.conf` |
| Vercel config | `vercel.json` |
| Edge middleware | `middleware.js` |
| GitHub Actions | `.github/workflows/deploy.yml` |

### C. Port Reference

| Port | Service | Environment |
|------|---------|-------------|
| 80 | Nginx HTTP | Production |
| 443 | Nginx HTTPS | Production |
| 5432 | PostgreSQL | Both |
| 6379 | Redis | Both |
| 8080 | HTTP dev server (frontend) | Development |
| 11436 | Gunicorn (Flask) | Production |

---

*This document is maintained as part of the VigyanLLM codebase. Update it when architectural changes are made.*
