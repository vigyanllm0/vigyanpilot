# VigyanLLM Docking — Complete Features & Pricing Plan

**Version:** 2.0
**Date:** September 2026
**Status:** Implementation Phase

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Audit](#2-current-state-audit)
3. [Feature Roadmap](#3-feature-roadmap)
4. [Pricing Model](#4-pricing-model)
5. [Competitor Analysis](#5-competitor-analysis)
6. [Technical Architecture](#6-technical-architecture)
7. [Revenue Projections](#7-revenue-projections)
8. [Implementation Timeline](#8-implementation-timeline)

---

## 1. Executive Summary

VigyanLLM Docking is a molecular docking platform that combines ESMFold protein structure prediction, AutoDock Vina physics-based screening, and GNINA CNN deep-learning re-scoring into a single consensus pipeline. The platform targets Indian researchers who currently rely on free but basic tools (SwissDock, CB-Dock2) or expensive commercial tools (Schrodinger at $10K+/year).

**Unique Differentiators:**
1. Broken Protein Analysis Engine — detects structural defects before docking
2. Regenerative Protein Folding — fixes broken regions using AI
3. Consensus Scoring — Vina + GNINA for more reliable predictions
4. Indian Pricing — ₹49-3,999/month vs $10K+/year for commercial tools

**Goal:** Build the best molecular docking platform for Indian researchers at 10% of commercial tool pricing.

---

## 2. Current State Audit

### What Works ✅
- ESMFold Engine (local model + web API fallback + helical bundle fallback)
- AutoDock Vina Engine (PDB→PDBQT, SMILES→3D, score parsing)
- GNINA Engine (CNN re-scoring)
- Consensus Pipeline (ESMFold → Vina → GNINA)
- Job Queue (file-based, local worker)
- Auth & Payments (Razorpay, daily limits)
- API Routes (submit, poll, structure retrieval)
- Frontend (3Dmol.js viewer, pipeline progress, results table)

### What's Broken ❌
- EC2 RAM = 908MB, ESMFold needs 8.4GB (can't run locally)
- "GPU-Accelerated" claim is false (no GPU on EC2)
- Protein-protein docking doesn't exist (false claims on protein-docking.html)
- No file upload (only text input for sequence and SMILES)
- No interaction analysis (H-bonds, hydrophobic, salt bridges)
- No result export (CSV, PDB, SDF)
- No binding site selection (auto-blind only)
- False confidence score (hardcoded 92/85)
- No pose clustering (redundant poses)
- No ligand drawing (must know SMILES)
- No ligand efficiency calculation
- No result saving to dashboard

### What's Missing for World-Class
- PDB/SDF/MOL2 file upload
- Binding site selection (click on protein)
- Grid box customization
- Flexible receptor docking
- Protein preparation wizard (add H, charges, repair)
- pH-dependent protonation
- Water/ion handling
- Interaction analysis (H-bonds, hydrophobic, salt bridges)
- Interaction 2D diagram (LigPlot-style)
- Pose clustering (RMSD-based)
- Multiple scoring functions
- Virtual screening mode (batch)
- Redocking validation
- Enrichment metrics (ROC-AUC)
- Broken Protein Analysis Engine
- Regenerative Protein Folding
- Result caching (ESMFold)
- Redis job queue
- Monitoring/alerting

---

## 3. Feature Roadmap

### Phase 0: Stop the Bleeding (✅ COMPLETE)
| # | Task | Why | Effort | Status |
|---|------|-----|--------|--------|
| 0.1 | Remove protein-protein docking false claims | False advertising | 2h | ✅ Done |
| 0.2 | Fix confidence score (remove hardcoded 92/85) | Misleading metric | 1h | ✅ Done |
| 0.3 | Add helical bundle fallback warning | Meaningless results without warning | 1h | ✅ Done |
| 0.4 | Mark dead Azure endpoints deprecated | Security surface, dead code | 1h | ✅ Done |
| 0.5 | Add input validation (frontend + backend) | Bad inputs → Vina crashes | 2h | ✅ Done |

### Phase 1: Core Input/Output (✅ COMPLETE)
| # | Task | Why | Effort | Status |
|---|------|-----|--------|--------|
| 1.1 | PDB file upload | Users have PDB files | 1d | ✅ Done |
| 1.2 | SDF ligand upload | Users have compound libraries | 1d | ✅ Done |
| 1.3 | FASTA input detection | Convenience | 0.5d | ✅ Done |
| 1.4 | SMILES → 2D preview | Verify ligand identity | 0.5d | ⏳ Next |
| 1.5 | CSV result export | Users need results downstream | 1d | ✅ Already exists |
| 1.6 | PDB/SDF pose download | Structure analysis in PyMOL | 1d | ✅ Already exists |
| 1.7 | Save results to dashboard | Pro users expect persistence | 1d | ⏳ Next |

### Phase 2: Broken Protein Analysis ✅ (commit `30787c25`)
| # | Task | Why | Status |
|---|------|-----|--------|
| 2.1 | pLDDT confidence map | Visual quality assessment | ✅ |
| 2.2 | Missing residue detection | Structural gaps | ✅ |
| 2.3 | Steric clash detection | Structural errors | ✅ |
| 2.4 | Ramachandran outlier detection | Backbone quality | ✅ |
| 2.5 | Unsatisfied H-bond analysis | Packing quality | ✅ |
| 2.6 | Overall quality score | One-click assessment | ✅ |
| 2.7 | HTML defect report | Detailed analysis | ✅ |

### Phase 3: Interaction Analysis ✅ (commit `a199208d`)
| # | Task | Why | Status |
|---|------|-----|--------|
| 3.1 | Hydrogen bond detection | Core interaction | ✅ |
| 3.2 | Hydrophobic contact detection | Binding assessment | ✅ |
| 3.3 | Salt bridge detection | Electrostatic interactions | ✅ |
| 3.4 | Binding site residue identification | Which residues matter | ✅ |
| 3.5 | 3D interaction visualization | Visual understanding | ⏳ Phase 5 |
| 3.6 | Interaction 2D diagram | Standard in drug discovery | ⏳ Phase 5 |

### Phase 4: Binding Site Control ✅ (commit `2ec8c7ac`)
| # | Task | Why | Status |
|---|------|-----|--------|
| 4.1 | Grid box UI | User control | ✅ |
| 4.2 | Click-to-select binding site | Intuitive UX | ✅ (via pocket cards) |
| 4.3 | Binding site presets | Speed for common targets | ✅ (6 presets) |
| 4.4 | Auto-binding pocket detection | fpocket integration | ✅ (simplified Voronoi) |
| 4.5 | Protein preparation wizard | Critical for accuracy | ✅ |
| 4.6 | pH-dependent protonation | Affects binding | ✅ |
| 4.7 | Flexible receptor option | Induced-fit docking | ⏳ Deferred |

### Phase 5: Regenerative Folding (2-3 weeks)
| # | Task | Why | Effort |
|---|------|-----|--------|
| 5.1 | Missing loop modeling | Rebuild gaps | 3d |
| 5.2 | Side-chain repair | Fix clashes | 2d |
| 5.3 | Terminal cleanup | Fix disorder | 1d |
| 5.4 | pLDDT-guided re-folding | Improve quality | 2d |
| 5.5 | Before/after comparison | Show improvement | 2d |

### Phase 6: Advanced Features (2-3 weeks)
| # | Task | Why | Effort |
|---|------|-----|--------|
| 6.1 | Parallel Vina (4 concurrent) | 4× throughput | 2d |
| 6.2 | Pose clustering | Remove redundant poses | 1d |
| 6.3 | Ligand efficiency calculation | Standard metric | 0.5d |
| 6.4 | Virtual screening mode | Batch processing | 3d |
| 6.5 | ESMFold result caching | Avoid re-folding | 1d |
| 6.6 | Redis job queue | Crash resilience | 2d |
| 6.7 | Monitoring/alerting | Operational visibility | 1d |
| 6.8 | GPU instance deployment | Production infrastructure | 1d |

---

## 4. Pricing Model

### 4A. Pricing Philosophy
Every docking run is paid. No free tier. Low barrier to entry (₹49 first run). Indian academic pricing (90% cheaper than Schrodinger).

### 4B. Pricing Tiers

| Tier | Price | Runs | Ligands | Exhaustiveness | Features |
|------|-------|------|---------|----------------|----------|
| **First Run** | ₹49 (one-time) | 1 | 10 | 8 | Full pipeline, no export |
| **Starter** | ₹99/run | Pack: 5/10/25/50 | 50 | 8 | Full analysis, CSV+PDB export |
| **Academic** | ₹399/mo | 50/day | 100 | 8 | All Pro features, .ac.in required |
| **Pro** | ₹699/mo | 100/day | 200 | 16 | Full + regen fold + 3D viz |
| **Lab** | ₹3,999/mo | 500/day | 500 | 32 | Full + team + API + LIMS |
| **Enterprise** | ₹15K-50K+/mo | Unlimited | Unlimited | Custom | On-premise, SLA, training |

### 4C. Token Packs

| Pack | Price | Per-Run Cost | Savings |
|------|-------|-------------|---------|
| 5 runs | ₹449 | ₹90 | 9% |
| 10 runs | ₹799 | ₹80 | 19% |
| 25 runs | ₹1,799 | ₹72 | 27% |
| 50 runs | ₹2,999 | ₹60 | 39% |

### 4D. Add-Ons

| Add-On | Price | Available To |
|--------|-------|-------------|
| Regenerative Folding | ₹149/run | Starter, First Run |
| Extended Screen (200+ ligands) | ₹199/run | Starter |
| Interaction Report (standalone) | ₹29/run | Starter |
| Redocking Validation | ₹19/run | Starter |
| Priority Queue | ₹49/run | Starter |
| Custom Scoring Function | ₹999/month | Pro+ |
| Dedicated GPU | ₹4,999/month | Pro+ |

### 4E. Money-Back Guarantee
- Full refund if pipeline fails
- 50% refund if unsatisfied (within 24 hours)
- No refund for wrong input

---

## 5. Competitor Analysis

### 5A. Commercial Tools

| Tool | Annual Price | Key Features | Our Advantage |
|------|-------------|-------------|---------------|
| Schrodinger Maestro | $15K-$50K/yr | Gold standard, FEP+, protein prep | We're 90% cheaper |
| MOE | $8K-$20K/yr | Full suite, desktop | Web-based, no install |
| Cresset Flare | $5K-$12K/yr | FEP, AI copilot | Indian pricing |
| Discovery Studio | $10K-$30K/yr | CDOCKER, ADMET | Affordable |

### 5B. Free Tools

| Tool | Limitations | Our Advantage |
|------|-----------|---------------|
| SwissDock | No GNINA, no ESMFold, slow, no export | Faster, better scoring, full analysis |
| CB-Dock2 | Auto-blind, no user control | Manual binding site, full pipeline |
| AutoDock Vina | Desktop only, no GUI, no cloud | Web-based, one-click |

### 5C. Feature Comparison

| Feature | Free Tools | Schrodinger | VigyanLLM |
|---------|-----------|-------------|-----------|
| ESMFold Structure | ❌ | ❌ | ✅ |
| Broken Protein Analysis | ❌ | ✅ (separate tool) | ✅ (integrated) |
| Regenerative Folding | ❌ | ❌ | ✅ |
| Consensus Scoring | ❌ | ❌ | ✅ (Vina + GNINA) |
| Web-Based | ✅ | ❌ (desktop) | ✅ |
| Indian Pricing | ✅ | ❌ | ✅ |
| Interaction Analysis | Basic | ✅ | ✅ |
| Export | ❌ | ✅ | ✅ |
| API Access | ❌ | ✅ | ✅ |

---

## 6. Technical Architecture

### 6A. Current Architecture
```
Frontend (S3/CF) → EC2 t3.micro (API) → File Queue → Local Worker
Problem: No GPU, 908MB RAM, ESMFold can't run locally
```

### 6B. Proposed Architecture
```
Frontend (S3/CF) → EC2 t3.medium (API + Auth) → Redis (Job Queue) → g4dn.xlarge (GPU Worker)
                                                          ↓
                                                    EBS (Model Cache)
```

### 6C. Job Flow
```
1. User submits → API validates → Redis job → returns job_id
2. GPU worker claims job → stages:
   a. Broken Protein Analysis (5s)
   b. ESMFold / Load cached (0-30s)
   c. Optional: Regenerative folding (0-45s)
   d. Vina screening (parallel, 4 concurrent) (125s)
   e. GNINA re-scoring (top 20) (200s)
   f. Interaction analysis (10s)
   g. Store results → mark complete
3. Frontend polls → displays results progressively
```

### 6D. Infrastructure Costs

| Component | Specification | Monthly Cost |
|-----------|--------------|-------------|
| GPU Worker | g4dn.xlarge reserved | ₹11,340 |
| GPU Worker (spot) | g4dn.xlarge spot | ₹3,990 |
| Main Server | t3.medium reserved | ₹2,520 |
| EBS Storage | 100GB gp3 | ₹672 |
| S3 | ~10GB | ₹84 |
| CloudFront | ~1TB transfer | ₹840 |
| RDS PostgreSQL | db.t3.micro | ₹1,260 |
| Redis | ElastiCache t3.micro | ₹1,260 |
| Monitoring | CloudWatch basic | ₹420 |
| **Total** | | **₹22,386/mo** |

---

## 7. Revenue Projections (100K Users)

### 7A. User Distribution

| Tier | Users | Monthly Revenue (₹) |
|------|-------|-------------------|
| First Run (one-time) | 40,000 | ₹19.6L |
| Starter | 25,000 | ₹17.5L |
| Pro | 15,000 | ₹104.9L |
| Academic | 10,000 | ₹39.9L |
| Lab | 5,000 | ₹199.9L |
| Enterprise | 1,500 | ₹45L |
| **Total** | **96,500** | **₹426.8L/mo** |

### 7B. Financial Summary

| Metric | Value |
|--------|-------|
| Monthly Revenue | ₹426.8L (~$5.1M) |
| Monthly Cost | ₹55.1L (~$656K) |
| Monthly Profit | ₹371.7L (~$4.4M) |
| Annual Revenue | ₹51.2 Cr (~$61M) |
| Gross Margin | 87% |

---

## 8. Implementation Timeline

| Phase | Scope | Time | Milestone |
|-------|-------|------|-----------|
| Phase 0 | Stop false claims | 2 days | Clean up existing code |
| Phase 1 | File upload + export | 1 week | Users can upload files |
| Phase 2 | Broken protein analysis | 1-2 weeks | Quality scoring engine |
| Phase 3 | Interaction analysis | 1-2 weeks | Full interaction reports |
| Phase 4 | Binding site control | 1-2 weeks | Click-to-select |
| Phase 5 | Regenerative folding | 2-3 weeks | Auto-repair proteins |
| Phase 6 | Advanced + production | 2-3 weeks | GPU deployment |
| **Total** | | **8-12 weeks** | **World-class docking** |

---

## 9. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| First run conversion | 15% of landing page visitors | /docking → checkout |
| First run → Starter | 30% within 30 days | Email campaign |
| Starter → Pro | 20% within 60 days | In-app upgrades |
| Pro churn | <5%/month | Cancellations |
| Refund rate | <1% | Razorpay logs |
| Avg revenue per user | ₹427/month | Revenue / active users |
| Payback period | <3 months | CAC / monthly revenue |

---

*This document is the master plan for VigyanLLM Docking v2.0. Implementation begins with Phase 0 (stop false claims) immediately.*
