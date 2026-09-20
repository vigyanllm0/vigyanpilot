# RUNSHEET — VigyanLLM Complete Project Guide

> **Last updated:** Sep 15 2026
> **Purpose:** Everything a new team member needs to understand the project, architecture, what changed, and why.

---

## TABLE OF CONTENTS

1. [What Is VigyanLLM?](#1-what-is-vigyanllm)
2. [Project Architecture (Big Picture)](#2-project-architecture-big-picture)
3. [Directory Structure](#3-directory-structure)
4. [Frontend — The Website](#4-frontend--the-website)
5. [Backend — The API Server](#5-backend--the-api-server)
6. [Database — Where Data Lives](#6-database--where-data-lives)
7. [Deployment — How It Goes Live](#7-deployment--how-it-goes-live)
8. [API Routes — Every Endpoint Explained](#8-api-routes--every-endpoint-explained)
9. [Authentication System](#9-authentication-system)
10. [Payment & Subscription System](#10-payment--subscription-system)
11. [The 22-Step Primer Design Pipeline](#11-the-22-step-primer-design-pipeline)
12. [Blog System](#12-blog-system)
13. [Glossary System](#13-glossary-system)
14. [SEO & Sitemap](#14-seo--sitemap)
15. [Security](#15-security)
16. [What Changed and Why](#16-what-changed-and-why)
17. [How to Run Locally](#17-how-to-run-locally)
18. [Key Terms Glossary](#18-key-terms-glossary)
19. [Common Tasks](#19-common-tasks)
20. [Known Issues & Gotchas](#20-known-issues--gotchas)

---

## 1. What Is VigyanLLM?

VigyanLLM is a **bioinformatics platform** that runs in a browser. It helps researchers design PCR primers, run BLAST searches, do molecular docking, and perform sequence alignment — all from a single website.

**The core product is a 22-step primer design pipeline** that takes a gene name and produces validated, publication-ready PCR primers with thermodynamic analysis, specificity checks, and manufacturing order sheets.

**Business model:** Freemium. Free users get 5 analyses/day. Pro users (₹699/mo) get unlimited access. Academic researchers get 30% discount. Lab teams get collaboration features.

**Target audience:** Indian academic researchers, biotech companies, molecular biology labs.

---

## 2. Project Architecture (Big Picture)

```
                        ┌─────────────────────────────────┐
                        │         INTERNET USERS           │
                        └──────────────┬──────────────────┘
                                       │
                          ┌────────────▼────────────┐
                          │    CLOUDFRONT (CDN)      │
                          │  Static files + SSL       │
                          └────┬───────────────┬─────┘
                               │               │
                    Static HTML/JS/CSS    /api/* proxy
                               │               │
                 ┌─────────────▼──┐    ┌───────▼────────┐
                 │   S3 BUCKET    │    │   EC2 SERVER    │
                 │  (frontend/)   │    │  (13.207.60.92) │
                 └────────────────┘    │                 │
                                       │  ┌───────────┐ │
                                       │  │  NGINX    │ │
                                       │  │  :443/80  │ │
                                       │  └─────┬─────┘ │
                                       │        │       │
                                       │  ┌─────▼─────┐ │
                                       │  │ GUNICORN  │ │
                                       │  │  :5000    │ │
                                       │  └─────┬─────┘ │
                                       │        │       │
                                       │  ┌─────▼─────┐ │
                                       │  │  FLASK    │ │
                                       │  │  (Python) │ │
                                       │  └─────┬─────┘ │
                                       │        │       │
                              ┌────────▼────────▼──────┐│
                              │                         ││
                    ┌─────────▼──────┐  ┌──────────────▼┤
                    │  POSTGRESQL    │  │    REDIS       │
                    │  :5432         │  │    :6379       │
                    │  (user data,   │  │  (caching,     │
                    │   jobs, etc.)  │  │   sessions)    │
                    └────────────────┘  └────────────────┘
```

**In plain English:**
1. User opens `www.vigyanllm.in` in their browser
2. CloudFront serves static HTML/CSS/JS from an S3 bucket (fast, cached worldwide)
3. When the user clicks "Run Analysis", the frontend sends an API request to `/api/...`
4. CloudFront proxies that request to the EC2 server
5. Nginx on EC2 routes it to Gunicorn (Python app server)
6. Flask (Python framework) processes the request, runs the analysis, stores results in PostgreSQL
7. Results come back to the browser and display in the UI

---

## 3. Directory Structure

```
vigyanpilot/
│
├── frontend/                    # THE WEBSITE (all HTML, JS, CSS)
│   ├── index.html               # Homepage
│   ├── primer.html              # Main primer design tool (flagship)
│   ├── blast.html               # BLAST tool
│   ├── docking.html             # Molecular docking tool
│   ├── msa.html                 # Multiple Sequence Alignment tool
│   ├── tm-calculator.html       # Melting temperature calculator
│   ├── gc-calculator.html       # GC content calculator
│   ├── dna-to-rna.html          # DNA to RNA converter
│   ├── pricing.html             # Pricing page (4 tiers)
│   ├── dashboard.html           # User dashboard
│   ├── login.html / signup.html # Auth pages
│   ├── blog/                    # 90 blog posts (static HTML)
│   │   ├── index.html           # Blog listing page
│   │   ├── rss.xml              # RSS feed
│   │   └── *.html               # Individual blog posts
│   ├── glossary/                # 215 glossary terms (static HTML)
│   ├── landing-pages/           # 42 SEO landing pages
│   ├── hub/                     # 12 topic hub pages
│   ├── gene-prefers/            # Gene-specific primer design pages
│   ├── assets/                  # Images, OG cards, fonts
│   ├── partials/                # Shared header/footer HTML
│   ├── config.js                # Backend URL config
│   ├── auth-shared.js           # Shared auth functions
│   ├── feature-gate.js          # Feature gating by subscription tier
│   ├── results-ui.js            # Save/Export button injection
│   ├── batch-ui.js              # Batch processing UI
│   ├── cookie-consent.js        # GDPR/DPDP consent
│   ├── primer-app.js            # Main primer tool JS (114KB, minified)
│   ├── *.css                    # Stylesheets (6 files)
│   └── *.js                     # JavaScript files (29 files)
│
├── primerforge/                 # THE BACKEND (Python Flask API)
│   ├── __init__.py              # Package init (adds BLAST to PATH)
│   ├── primer_server.py         # Main Flask app (3,141 lines) — THE entry point
│   ├── auth.py                  # SQLite authentication
│   ├── pg_auth.py               # PostgreSQL authentication (production)
│   ├── auth_routes.py           # SQLite auth endpoints
│   ├── pg_auth_routes.py        # PostgreSQL auth endpoints (production)
│   ├── database.py              # PostgreSQL connection pool
│   ├── payment_routes.py        # SQLite payment endpoints
│   ├── pg_payment_routes.py     # PostgreSQL payment endpoints (production)
│   ├── price_registry.py        # Pricing plans (Free/Pro/Lab/Enterprise)
│   ├── security.py              # Rate limiting, IP blocking, CSP
│   ├── csrf.py                  # CSRF protection
│   ├── metrics.py               # Prometheus metrics
│   ├── reports_routes.py        # Save/export reports
│   ├── pg_api_routes.py         # Developer API routes
│   ├── visitor_routes.py        # Visitor geo-tracking
│   ├── engine/                  # THE PIPELINE
│   │   ├── pipeline_routes.py   # Pipeline API endpoints
│   │   ├── orchestrator.py      # Step execution engine
│   │   ├── thermodynamics.py    # SantaLucia 1998 NN calculations
│   │   ├── sequence_retrieval.py# NCBI/Ensembl fetching
│   │   ├── blast_viewer.py      # BLAST result parser
│   │   ├── msa_viewer.py        # MSA result viewer
│   │   ├── order_serializer.py  # Oligo order sheets
│   │   ├── compliance.py        # MIQE/CLIA compliance
│   │   └── steps/               # 22 individual pipeline steps
│   │       ├── step01_isoform_filter.py
│   │       ├── step02_exon_intron_junction.py
│   │       ├── ... (22 steps total)
│   │       └── step22_probe_design.py
│   ├── core/                    # Analysis modules
│   │   ├── auto_designer.py     # Automated primer design
│   │   ├── manual_analyser.py   # Manual primer analysis
│   │   ├── thermodynamics.py    # Tm calculations
│   │   └── sequence_fetcher.py  # Sequence retrieval
│   └── pipelines/               # External engines
│       ├── docking_engine.py    # AutoDock Vina
│       ├── consensus_pipeline.py# Vina + GNINA consensus
│       └── esmfold_engine.py    # ESMFold structure prediction
│
├── backend/                     # CMS BACKEND (separate FastAPI app)
│   ├── main.py                  # CMS entry point (port 8001)
│   ├── routes/                  # CMS API routes
│   │   ├── auth.py              # CMS admin auth
│   │   ├── pages.py             # Page management
│   │   ├── blocks.py            # Content blocks
│   │   ├── review.py            # Content review workflow
│   │   ├── upload.py            # Image upload
│   │   ├── public.py            # Public content rendering
│   │   └── ...
│   ├── cms.db                   # CMS database (SQLite)
│   └── import_static_blogs.py   # Import HTML blogs into CMS
│
├── deploy/                      # DEPLOYMENT CONFIG
│   ├── docker-compose.yml       # Docker services
│   ├── Dockerfile               # App container
│   ├── nginx.conf               # Nginx config
│   ├── migrations/              # 26 PostgreSQL migration files
│   │   ├── 0001_initial_schema.sql
│   │   ├── 0100_initial_schema.sql
│   │   └── ...
│   └── gunicorn.conf.py         # Gunicorn config
│
├── tests/                       # TEST SUITE (21 files)
│   ├── test_primer_server.py    # Main app tests
│   ├── test_guest_mode.py       # Anonymous access tests
│   ├── test_http_only_cookie_auth.py
│   └── ...
│
├── scripts/                     # UTILITY SCRIPTS
│   ├── gen_glossary_pages.py    # Generate glossary HTML
│   ├── add_glossary_faq.py      # Add FAQ to glossary
│   ├── qa_real_pipeline.py      # QA testing
│   └── redesign.py              # Template redesign
│
├── docs/                        # DOCUMENTATION
│   ├── SALES_PLAYBOOK.md        # Sales strategy
│   ├── BACKLINK_OUTREACH.md     # SEO backlink strategy
│   └── ACADEMIC_OUTREACH.md     # University outreach
│
├── infra/                       # INFRASTRUCTURE
│   ├── docker-compose.yml       # Production Docker
│   ├── nginx.conf               # Production Nginx
│   └── initdb/                  # DB init scripts
│
├── wsgi.py                      # Production WSGI entry
├── start.sh                     # Dev startup script
├── secure_frontend.py           # Dev static file server
├── generate_sitemap.py          # Sitemap generator
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Project config + linting
├── .env.example                 # Environment variables template
├── vercel.json                  # Vercel routing (legacy)
├── middleware.js                # Edge middleware (legacy)
├── AGENTS.md                    # Agent session handoff
└── RUNSHEET.md                  # THIS FILE
```

---

## 4. Frontend — The Website

### What is it?
The frontend is a **static website** — plain HTML files with JavaScript. No React, no build step, no npm. Just HTML + vanilla JS + CSS.

### How it works
1. Each page is a standalone `.html` file (e.g., `primer.html`, `blast.html`)
2. Shared elements (header, footer, nav) are injected by `includes.js` from `partials/`
3. When a user clicks a button (e.g., "Run Analysis"), JavaScript sends a fetch request to `/api/...`
4. The backend processes the request and returns JSON
5. JavaScript updates the page with the results

### Key JavaScript Files

| File | What it does | Why it matters |
|------|-------------|----------------|
| `config.js` | Sets `window.VIGYAN_BACKEND_URL = '/api'` | Tells JS where the backend is |
| `auth-shared.js` | Login/register modals, Google OAuth, user menu, plan badge | Every page uses this for auth |
| `feature-gate.js` | Checks if user's plan allows a feature (e.g., batch, export) | Prevents free users from accessing paid features |
| `results-ui.js` | Injects "Save to Dashboard" / "Export PDF" buttons into results | Uses MutationObserver to watch for new results |
| `primer-app.js` | Main primer design tool logic (114KB minified) | The flagship product — handles the entire 22-step pipeline UI |
| `batch-ui.js` | Batch sequence processing UI | Lets Pro users paste multiple sequences |
| `cookie-consent.js` | GDPR/DPDP cookie consent banner | Legal compliance |
| `search-index.js` | Client-side search index | Powers the site-wide search |

### Why no build step?
The team chose static HTML for:
- **Speed**: No JavaScript bundle to download (pages load fast)
- **SEO**: Search engines can read every page directly
- **Simplicity**: No webpack, no React, no node_modules
- **Hosting**: S3 + CloudFront is cheap and fast

---

## 5. Backend — The API Server

### What is it?
A **Python Flask** application that handles all the computation. When the frontend says "design primers for BRCA1", the backend:
1. Fetches the gene sequence from NCBI
2. Runs the 22-step pipeline
3. Returns validated primers with Tm, GC%, hairpin checks, etc.

### How it starts
```bash
# Production:
python -m gunicorn "primerforge.primer_server:create_app()" --bind 127.0.0.1:5000

# Development:
./start.sh  # Starts gunicorn on :11436 + frontend on :8080
```

### `create_app()` — The Main Entry Point
Located in `primerforge/primer_server.py`, this function:
1. Detects if PostgreSQL or SQLite is available (based on `DATABASE_URL` env var)
2. Registers different blueprints (route groups) depending on the database
3. Initializes security (rate limiting, CSP, admin RBAC)
4. Starts the docking worker if needed
5. Returns the Flask app

### Dual Database Support
The backend supports **two databases simultaneously**:

| Database | When used | Files |
|----------|-----------|-------|
| **PostgreSQL** | Production (has `DATABASE_URL` set) | `pg_auth.py`, `pg_auth_routes.py`, `pg_payment_routes.py`, `pg_api_routes.py`, `database.py` |
| **SQLite** | Development (no `DATABASE_URL`) | `auth.py`, `auth_routes.py`, `payment_routes.py` |

The code checks `os.environ.get("DATABASE_URL")` at startup and registers the appropriate routes.

---

## 6. Database — Where Data Lives

### PostgreSQL (Production)

**Connection pool:** `psycopg2.ThreadedConnectionPool` (min=2, max=10 connections)

**Key tables:**

| Table | What it stores |
|-------|---------------|
| `users` | Email, password hash, name, role (user/admin/guest), plan (free/pro/lab), auth_provider (email/google) |
| `daily_usage` | How many analyses each user ran today (for daily limits) |
| `monthly_usage` | Monthly usage counters |
| `pipeline_jobs` | Submitted primer design jobs (status, inputs, outputs, guest flag) |
| `pipeline_results` | Step-by-step results for each job |
| `pipeline_step_cache` | Cached step outputs (avoids re-computation) |
| `saved_results` | User-saved analysis results (for dashboard) |
| `payments` | Razorpay payment records |
| `subscriptions` | Subscription status |
| `api_keys` | Developer API keys |
| `reviews` | User reviews (moderated) |
| `audit_logs` | Security audit trail |

**Migrations:** 26 SQL files in `deploy/migrations/` — run sequentially by `migrate.py`.

### SQLite (Development)

**Path:** `primerforge.db` (project root)

**Simplified schema:** Same tables as PostgreSQL but without RLS, connection pooling, or some advanced features. Good enough for local development.

---

## 7. Deployment — How It Goes Live

### Production Architecture

```
User → CloudFront (CDN) → S3 (static files)
                        → EC2 (API via /api/*)
                           ├── Nginx (SSL, rate limiting)
                           ├── Gunicorn (Python app server)
                           ├── Flask (the app)
                           ├── PostgreSQL (data)
                           └── Redis (caching)
```

### The Flow

1. **Static files** (HTML, CSS, JS, images) are in an S3 bucket, served by CloudFront
2. **API requests** (`/api/*`) are proxied by CloudFront to the EC2 server
3. **EC2** runs Nginx which:
   - Terminates SSL (Let's Encrypt)
   - Rate-limits auth endpoints (5 req/min)
   - Proxies to Gunicorn on port 5000
4. **Gunicorn** runs the Flask app with multiple workers
5. **Flask** processes requests and talks to PostgreSQL + Redis

### Why this architecture?
- **CloudFront** = fast global CDN, DDoS protection
- **S3** = cheap static hosting, no server needed for HTML
- **EC2** = full control for Python backend (needs BLAST, Vina, etc.)
- **Nginx** = SSL termination, rate limiting, security headers
- **Gunicorn** = production Python app server (handles concurrency)

### Alternative: Local Development
```bash
./start.sh
# Backend: http://localhost:11436
# Frontend: http://localhost:8080
```

---

## 8. API Routes — Every Endpoint Explained

### Authentication (`/api/auth/*`)

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/api/auth/register` | POST | Create new account (email+password) |
| `/api/auth/login` | POST | Login with email+password |
| `/api/auth/logout` | POST | Clear session |
| `/api/auth/me` | GET | Get current user info |
| `/api/auth/google` | POST | Login with Google OAuth |
| `/api/auth/verify-email` | GET | Verify email address |
| `/api/auth/forgot-password` | POST | Request password reset |
| `/api/auth/change-password` | POST | Change password |
| `/api/auth/verify-academic` | POST | Submit academic discount application |
| `/api/auth/account` | DELETE | Delete account (GDPR) |
| `/api/auth/export` | GET | Export all user data (GDPR) |

### Payments (`/api/payments/*`)

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/api/payments/pricing` | GET | Get plan details |
| `/api/payments/create-order` | POST | Create Razorpay order |
| `/api/payments/verify-payment` | POST | Verify payment succeeded |
| `/api/payments/webhook` | POST | Razorpay webhook (auto-confirm) |
| `/api/payments/status` | GET | Current user's plan + usage |
| `/api/usage/check` | GET | Check daily usage limit |
| `/api/usage/record` | POST | Record a usage event |

### Primer Design Pipeline (`/api/pipeline/*`)

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/api/pipeline/submit` | POST | Submit a new primer design job (guests allowed) |
| `/api/pipeline/status/:job_id` | GET | Poll job progress |
| `/api/pipeline/result/:job_id` | GET | Get full results |
| `/api/pipeline/result/:job_id/step/:n` | GET | Get specific step output |
| `/api/pipeline/order/:job_id` | POST | Generate oligo order sheet |

### Tool Endpoints

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/api/primer/auto-design` | POST | Automated primer design (guests allowed) |
| `/api/primer/manual-analysis` | POST | Manual primer analysis |
| `/api/blast/search` | POST | BLAST sequence search |
| `/api/msa/align` | POST | Multiple sequence alignment |
| `/api/docking/consensus` | POST | Molecular docking |
| `/api/docking/status/:job_id` | GET | Poll docking job |
| `/api/results/save` | POST | Save results to dashboard |
| `/api/export/pdf` | POST | Export PDF report |
| `/api/export/pptx` | POST | Export PowerPoint report |

### Developer API (`/api/v1/*`)

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/api/v1/primer/design` | POST | API: primer design (requires API key) |
| `/api/v1/blast/search` | POST | API: BLAST search |
| `/api/v1/msa/align` | POST | API: MSA alignment |
| `/api/v1/openapi.json` | GET | OpenAPI specification |

---

## 9. Authentication System

### How Login Works

```
User enters email + password
         │
         ▼
Frontend sends POST /api/auth/login
         │
         ▼
Backend checks email in PostgreSQL users table
         │
         ▼
Backend verifies password with bcrypt
         │
         ▼
Backend creates HttpOnly cookie (pf_token)
         │
         ▼
Backend returns user data (stored in sessionStorage as pf_user)
         │
         ▼
Frontend shows user menu, hides login button
```

### Key Concepts

- **`pf_token`** (HttpOnly cookie): The auth token. HttpOnly = JavaScript can't read it (prevents XSS theft). Secure = only sent over HTTPS. SameSite=Lax = sent on same-site requests.
- **`pf_user`** (sessionStorage): Non-sensitive user info (email, name, role). Used by the UI to know if user is logged in. NOT used for auth — the cookie handles that.
- **`rehydrateSession()`**: On page load, frontend calls `/api/auth/me` to verify the cookie is still valid and get fresh user data.

### Guest Mode

Anonymous users can:
- Run primer design
- Run BLAST
- Run MSA
- Run docking (single ligand)

They CANNOT:
- Save results
- Export PDF/PPT
- Batch process
- Access API

After running a tool, guests see a "Save My Results →" claim card that prompts them to create an account.

### Admin Mode

Admin users (role='admin') bypass all feature gates. They can:
- Access `/admin-security.html`
- See admin-only nav items
- Manage users, reviews, promo codes

---

## 10. Payment & Subscription System

### Pricing Tiers

| Tier | Price | Daily Limit | Features |
|------|-------|-------------|----------|
| **Free** | ₹0 | 5 analyses/day | Basic tools, manual analysis |
| **Trial** | ₹0 (14 days) | 50 analyses/day | Batch, export PDF, saved results |
| **Pro** | ₹699/mo | Unlimited | All tools, API access, PPT export |
| **Lab** | Custom | Unlimited | Team collaboration, admin panel |

### How Payment Works

1. User clicks "Upgrade" → goes to `/pricing`
2. User selects plan → goes to `/checkout`
3. Frontend calls `/api/payments/create-order` → backend creates Razorpay order
4. User pays via Razorpay popup
5. Razorpay sends webhook to `/api/payments/webhook`
6. Backend verifies payment, updates user's plan
7. Frontend refreshes → user now has Pro features

### Academic Discount

1. User submits `.edu.in` email + student ID via `/api/auth/verify-academic`
2. Admin reviews in admin panel
3. On approval: 30% discount applied (Pro = ₹489/mo instead of ₹699)

### Feature Gating

`feature-gate.js` maps features to required tiers:
```javascript
var FEATURE_TIER = {
  batch: { tier: 'trial' },      // Need trial+ for batch
  export_pdf: { tier: 'trial' }, // Need trial+ for PDF
  export_ppt: { tier: 'pro' },   // Need Pro for PPT
  api_access: { tier: 'pro' },   // Need Pro for API
  collaboration: { tier: 'lab' },// Need Lab for teams
};
```

When a user tries a gated feature:
1. `requireFeature('batch')` is called
2. It fetches `/api/payments/status` to get user's plan
3. If plan is too low → shows upgrade modal
4. If plan is high enough → allows the action

---

## 11. The 22-Step Primer Design Pipeline

This is the core product. Here's what each step does:

| Step | Name | What it does | Why it matters |
|------|------|-------------|----------------|
| 1 | Isoform Filter | Selects the right gene transcript from NCBI/Ensembl | Different transcripts → different exons → different primers |
| 2 | Exon/Intron Junction | Maps exon boundaries | Primers should span junctions for cDNA-specific amplification |
| 3 | Bisulfite Conversion | Handles methylation-specific PCR | Needed for epigenetics studies |
| 4 | Degenerate Bases | Handles ambiguous nucleotides (R, Y, N, etc.) | Some genes have known variants |
| 5 | Repeat Masking | Filters out repetitive regions (Dfam) | Primers in repeats → non-specific binding |
| 6 | Primer3 Design | Core primer design with sliding window | The actual primer selection algorithm |
| 7 | Thermodynamic Refinement | SantaLucia 1998 nearest-neighbor Tm | Accurate melting temperature calculation |
| 8 | Buffer/Salt Optimization | Adjusts for actual PCR conditions | Tm changes with salt concentration |
| 9 | Mg²⁺ Correction | Magnesium ion concentration adjustment | Mg²⁺ affects primer binding and polymerase activity |
| 10 | BLAST Specificity | Checks primers against NCBI BLAST | Ensures primers bind only to the target gene |
| 11 | Bowtie2 Alignment | Whole-genome alignment | Catches off-target binding sites BLAST might miss |
| 12 | Organelle Screening | Checks for mitochondrial binding | Primers shouldn't amplify mitochondrial DNA |
| 13 | Secondary Structure | Filters hairpins and self-dimers | Secondary structure prevents primer binding |
| 14 | Amplicon Structure | Analyzes the PCR product | Ensures amplifiable, correct-size product |
| 15 | dbSNP Filter | Checks for known SNPs in primer region | SNPs in primer region → allele dropout |
| 16 | Clinical Hotspots | Screens clinical mutation hotspots | Avoids primers that span diagnostic regions |
| 17 | Adapter Tailing | Adds NGS adapter sequences | Needed for sequencing library preparation |
| 18 | Multiplex Scoring | Tests compatibility for multiplex PCR | Multiple primer pairs must work together |
| 19 | Ranking | Final scoring and ranking | Ranks all candidate primers by overall quality |
| 20 | Thermocycling | Generates PCR protocol | Tells the user what temperatures to use |
| 21 | Manufacturing | Generates order sheet | IDT/Twist format for ordering primers |
| 22 | Probe Design | Designs TaqMan probes (always-on) | For qPCR applications, probes increase specificity |

### How the Pipeline Runs

1. User submits job via `/api/pipeline/submit`
2. `pipeline_routes.py` creates a job record in `pipeline_jobs` table
3. `orchestrator.py` runs each step sequentially
4. Each step reads from the previous step's output
5. Results are stored in `pipeline_results` table
6. Frontend polls `/api/pipeline/status/:job_id` for progress
7. When complete, frontend fetches `/api/pipeline/result/:job_id`

---

## 12. Blog System

### How It Works

- **90 static HTML files** in `frontend/blog/`
- Each post is a complete HTML page with:
  - Full `<head>` (title, meta, OG tags, JSON-LD schemas)
  - Navigation header
  - Article content
  - Inline FAQ section
  - Footer with CTAs
  - FAQPage JSON-LD schema (for Google rich results)
  - Article JSON-LD schema (for Google News/Discover)

### Blog Index & RSS

- `frontend/blog/index.html` — listing page with cards
- `frontend/blog/rss.xml` — RSS feed for syndication

### Anti-Cannibalization Policy

Blogs target **informational queries** ("what is PCR vs qPCR"), while tool pages target **tool queries** ("free primer design tool"). This prevents the blog from stealing search traffic from the money pages.

**Rules:**
1. Blog = educational content only
2. Above-fold CTA within 300 words linking to tool page
3. Title passes authority to tool: "Try the Free [Tool Name]"
4. 3-5 varied anchor-text links to tool page
5. Blog schema = Article, tool page schema = SoftwareApplication

---

## 13. Glossary System

### How It Works

- **215 HTML files** in `frontend/glossary/`
- Each page follows an expanded template:
  - Definition section (100-120 words)
  - 4-6 practice items
  - Related terms (cross-links)
  - FAQ section (HTML `<details>`)
  - VigyanLLM tool links

### Generation

Glossary pages are generated by:
1. `scripts/gen_glossary_pages.py` — creates base HTML from term definitions
2. `scripts/add_glossary_faq.py` — adds FAQ sections
3. `scripts/redesign.py` — converts old template to new format

### SEO

Each glossary page has:
- `BreadcrumbList` JSON-LD schema
- Expanded H1 (e.g., "GC Content, the percentage of guanine and cytosine...")
- Canonical URL
- Meta description
- Cross-linked via "Related Terms"

---

## 14. SEO & Sitemap

### Sitemap Generation

`generate_sitemap.py` does three things:

1. **Generates `sitemap.xml`** — static XML with all URLs, priorities, and change frequencies
2. **Generates `robots.txt`** — tells crawlers which pages to visit/avoid
3. **Generates `api/sitemap.xml.js`** — Vercel Edge Function for dynamic sitemap (legacy)

### Sitemap Structure

| URL Pattern | Priority | Change Freq |
|-------------|----------|-------------|
| `/` (homepage) | 1.0 | weekly |
| `/primer` (flagship tool) | 1.0 | weekly |
| `/blast`, `/msa`, `/docking` | 0.9 | monthly |
| `/blog/*` | 0.75 | monthly |
| `/glossary/*` | 0.65 | monthly |
| `/gene-prefers/*` | 0.70 | monthly |
| `/landing-pages/*` | 0.75 | monthly |

### robots.txt Rules

- **Allow**: Googlebot, Bingbot, GPTBot, ClaudeBot, PerplexityBot (AI crawlers for GEO/LLMO)
- **Disallow**: AhrefsBot, SemrushBot, MJ12bot (SEO tools — waste bandwidth)
- **Disallow**: `/api/`, `/admin/`, `/dashboard/`

### Current Issue

The `sitemap.xml.js` edge function exists in `vigyanpilot/frontend/api/` but NOT in the main `frontend/api/` directory. The static `sitemap.xml` is up-to-date (Sep 13 2026) but the edge function is missing from the production path.

---

## 15. Security

### Key Security Measures

| Measure | Implementation |
|---------|---------------|
| **HttpOnly cookies** | `pf_token` cookie is HttpOnly + Secure + SameSite=Lax — prevents XSS token theft |
| **CSRF protection** | `csrf.py` generates tokens for form submissions |
| **Rate limiting** | Flask-Limiter: 5 req/min for auth, 200 req/min for API |
| **IP blocking** | `security.py` blocks suspicious IPs |
| **Password hashing** | bcrypt with salt |
| **Admin RBAC** | Role-based access control for admin endpoints |
| **CSP headers** | Content Security Policy prevents XSS |
| **CORS** | Only allows requests from `vigyanllm.in` |
| **SSL** | Let's Encrypt on Nginx, forced HTTPS |
| **PII masking** | Logs mask emails, IPs, tokens |
| **Input sanitization** | Bleach library sanitizes HTML |
| **Malware scanning** | `file_scanner.py` scans uploads |
| **Threat detection** | `threat_detection.py` detects suspicious patterns |

### Pen Test Findings (Fixed)

61 security findings were remediated across CRITICAL/HIGH/MEDIUM/LOW severity levels. Key fixes:
- Admin pages protected with `admin_tk` cookie check
- CloudFront function blocks admin pages with 403 directly
- `.env` credentials sanitized
- All Azure dependencies removed (AWS-only now)

---

## 16. What Changed and Why

### Recent Changes (Last 5 Commits)

| Commit | What Changed | Why |
|--------|-------------|-----|
| `9eba5687` | Added biostatistics calculator tool | New tool: 20+ statistical calculators for researchers |
| `4278cece` | Added `biostatistics-calculator.html` + `biostat-stats.js` | New tool page (85KB HTML, 34KB JS) |
| `1c67aa03` | Removed gc-clamp redirect that blocked glossary page | The redirect was intercepting `/glossary/gc-clamp` requests |
| `d361372f` | Glossary gc-clamp expansion, primer-design landing page rewrite, blog 404 fix | SEO improvements — expanded thin content, fixed broken links |
| `f68bf546` | CloudFront function blocks admin pages with 403 | Security hardening — admins can only be accessed via EC2 |

### Earlier Changes (Infrastructure Migration)

| Commit | What Changed | Why |
|--------|-------------|-----|
| `61d67fbf` | PEN-04 — CloudFront function blocks admin pages | Pen test fix |
| `488392bc` | Comprehensive audit fix — 34 issues | Security audit remediation |
| `15cbaa64` | Clean CI/CD pipeline — removed Azure refs | Moving from Azure to AWS |
| `a99803a3` | Removed all Azure dependencies | Codebase is now AWS-only |
| `93764914` | Removed Vercel — site fully on AWS | CloudFront + S3 + EC2 deployment |
| `eb7af969` | AWS S3+CloudFront migration | Parallel deployment, zero downtime |
| `b98cd87f` | EC2 nginx + Let's Encrypt SSL | Production SSL setup |

### Why the Migration?

The project moved from **Vercel** to **AWS** because:
1. Vercel can't run BLAST, Vina, or other native binaries
2. EC2 gives full control over Python backend
3. CloudFront provides better DDoS protection
4. S3 is cheaper for static file hosting
5. PostgreSQL runs better on EC2 than serverless alternatives

### What Was Changed in Frontend

| Change | Why |
|--------|-----|
| Removed "AI-powered" claims → "automated" | Honesty — the tool uses Primer3/SantaLucia, not AI |
| Removed HIPAA claims → "DPDP-compliant" | HIPAA is US law, DPDP is Indian law |
| Added FAQPage JSON-LD to 42 blog posts | Google rich results (FAQ dropdowns in search) |
| Added HowTo schema to 4 blog posts | Google rich results (step-by-step in search) |
| Expanded glossary pages (65 files) | More content = better SEO rankings |
| Added educational H2 sections to 11 tool pages | More content above the fold = better engagement |
| Added pricing page | Monetization — 4-tier subscription model |
| Added citation page | Academic credibility — researchers can cite the tool |
| Added validation page | Trust building — shows published primer verification |

---

## 17. How to Run Locally

### Prerequisites

- Python 3.10+
- PostgreSQL (optional — falls back to SQLite)
- BLAST+ binary (included in repo at `tools/ncbi-blast-2.17.0+`)

### Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-org/vigyanpilot.git
cd vigyanpilot

# 2. Set up environment
cp .env.example .env
# Edit .env with your settings (or leave defaults for SQLite mode)

# 3. Run the dev server
./start.sh

# 4. Open in browser
# Frontend: http://localhost:8080
# Backend: http://localhost:11436/health
```

### What happens behind the scenes

1. `start.sh` creates a virtual environment (`.venv/`)
2. Installs dependencies from `requirements.txt`
3. Detects if `DATABASE_URL` is set (PostgreSQL) or not (SQLite)
4. Starts Gunicorn on port 11436 (backend only)
5. Starts `secure_frontend.py` on port 8080 (serves HTML, proxies `/api/*` to backend)
6. Waits for backend to be ready, then prints "Frontend ready"

### Running Tests

```bash
# Activate venv
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_guest_mode.py -v
```

---

## 18. Key Terms Glossary

| Term | Meaning |
|------|---------|
| **Tm** | Melting Temperature — the temperature at which 50% of DNA strands are double-stranded vs single-stranded |
| **GC Content** | Percentage of G+C nucleotides in a sequence (affects Tm) |
| **Primer** | Short DNA sequence (20-30bp) that starts PCR amplification |
| **Amplicon** | The DNA fragment produced by PCR |
| **BLAST** | Basic Local Alignment Search Tool — finds similar sequences in databases |
| **MSA** | Multiple Sequence Alignment — aligns 3+ sequences to find conserved regions |
| **Docking** | Predicts how a molecule (ligand) binds to a protein |
| **SantaLucia 1998** | The standard nearest-neighbor thermodynamic model for Tm calculation |
| **Primer3** | The industry-standard primer design algorithm |
| **AutoDock Vina** | Molecular docking software |
| **GNINA** | Deep-learning-based docking software |
| **ESMFold** | Protein structure prediction by Meta |
| **Razorpay** | Indian payment gateway |
| **GEO** | Generative Engine Optimization — how AI assistants (ChatGPT, Perplexity) find and recommend content |
| **LLMO** | Large Language Model Optimization — similar to GEO |
| **Anti-cannibalization** | Preventing blog posts from stealing search traffic from tool pages |
| **HttpOnly cookie** | Cookie that JavaScript can't read (prevents XSS theft) |
| **RLS** | Row-Level Security — PostgreSQL feature that restricts which rows a user can see |
| **MIQE** | Minimum Information for Publication of qPCR Experiments — a reporting standard |
| **Pipeline** | The 22-step primer design workflow |

---

## 19. Common Tasks

### Adding a New Blog Post

1. Create `frontend/blog/your-slug.html` (copy an existing post as template)
2. Update the `<title>`, `<meta>`, JSON-LD, and content
3. Add above-fold CTA linking to `/primer` (within 300 words)
4. Add 3-5 varied anchor-text links to tool page
5. Add FAQPage JSON-LD schema
6. Run `python generate_sitemap.py` to update sitemaps
7. Add to `frontend/blog/index.html` (listing page)
8. Add to `frontend/blog/rss.xml`

### Adding a New Glossary Term

1. Run `python scripts/gen_glossary_pages.py` (or create manually)
2. Add definition, practice items, related terms, FAQ
3. Link to relevant tool (e.g., gc-content → `/gc-calculator`)
4. Run `python generate_sitemap.py`

### Adding a New Tool Page

1. Create `frontend/your-tool.html` (copy `primer.html` as template)
2. Add tool form + JavaScript handler
3. Add backend endpoint in `primerforge/primer_server.py`
4. Add to `vercel.json` CSP if needed
5. Add to sitemap
6. Add `SoftwareApplication` JSON-LD schema
7. Add educational H2 sections above the form

### Modifying the Pipeline

1. Edit the relevant step in `primerforge/engine/steps/stepNN_*.py`
2. Each step must:
   - Accept input from previous step
   - Return output as a dict
   - Handle errors gracefully
3. Update `orchestrator.py` if adding/removing steps
4. Add tests in `tests/`

---

## 20. Known Issues & Gotchas

### Current Issues

| Issue | Status | Impact |
|-------|--------|--------|
| `sitemap.xml.js` edge function missing from `frontend/api/` | Open | Vercel dynamic sitemap won't work (but static sitemap.xml is fine) |
| No running server processes | Info | Backend is not currently running locally |
| `design-tokens.css` has uncommitted changes | Open | Minor CSS changes pending |
| 4 payment test failures | Pre-existing | Tests use old `create_app().test_client()` pattern |
| CMS backend not running | Info | CMS requires separate FastAPI app on port 8001 |

### Gotchas

1. **Dual database**: Always check which database mode you're in. PostgreSQL = production, SQLite = dev. Code paths are different.
2. **Minified JS**: `primer-app.js` is 114KB minified. Don't edit it directly — find the source or use the editor carefully.
3. **No build step**: Changes to HTML/JS are live immediately. No compilation needed.
4. **Config.js is gitignored**: `frontend/config.js` might differ between local and production. The git version has `/api` (relative URL).
5. **BLAST binary**: The BLAST+ binary is at `tools/ncbi-blast-2.17.0+`. Make sure it's executable.
6. **Guest mode**: Anonymous users can run tools but can't save. The guest user is `guest@vigyanllm.local` in the database.
7. **Anti-cannibalization**: Don't write blogs targeting tool queries. Blogs = information, tool pages = tools.
8. **Security headers**: CSP is per-page in `vercel.json`. Adding a new page? Add its CSP rules.
9. **Migrations**: Always run `python deploy/migrations/migrate.py` after pulling new code.
10. **Port conflicts**: `start.sh` kills processes on ports 11436 and 8080 before starting.

---

*This runsheet covers everything a new team member needs. For the latest session handoff, see `AGENTS.md`.*
