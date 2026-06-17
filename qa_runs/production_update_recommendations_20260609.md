# VigyanLLM Production Website Update Recommendations

Generated: 2026-06-09  
Scope: website, product, pricing quota, competitor advantage, security, payment readiness, launch operations, SEO, customer trust, and production release checklist.  
Input report reviewed: `qa_runs/market_security_launch_report_20260609.md`  
Secrets note: `.env` was not opened or read.

## Executive Recommendation

Keep the current prices. Do not reduce pricing.

Instead, strengthen the plans by increasing included designs/month, then make the website clearly prove why VigyanLLM is more valuable than free primer tools and broader paid molecular biology software.

Updated launch verdict after recommended updates:

| Area | Current Readiness | After Recommended Updates |
|---|---:|---:|
| Website positioning | 62/100 | 88/100 |
| Competitor differentiation | 65/100 | 90/100 |
| Pricing appeal | 72/100 | 86/100 |
| Payment trust | 76/100 | 90/100 |
| Security readiness | 68/100 | 88/100 |
| Production operations | 58/100 | 86/100 |
| Overall public-launch readiness | 68/100 | 88/100 |

Final target state: **public production launch-ready after P0 and P1 items are completed and verified**.

## Current Website Audit Summary

Live page audited: `http://127.0.0.1:8080/primer.html?qa=razorpay-final-20260609`

Observed positives:

- Frontend loaded successfully.
- Browser console had no errors during the audit.
- Backend status badge showed "Backend connected".
- Razorpay pricing buttons were present and mapped to product IDs.
- Top-up price is now INR 49.
- Browser database buttons exist for NCBI, GENCODE, NCBI Virus, ENA, DDBJ, UniProt, Primer-BLAST, and dbSNP.
- Meta description exists and describes the 22-step pipeline.

Observed gaps:

- The page says "Enterprise-grade", but does not show enough proof above the fold.
- The page says "Full 10-step pipeline" in pricing, while the app claims a 22-step pipeline elsewhere. This weakens trust.
- There is no direct comparison table against Primer3, NCBI Primer-BLAST, IDT PrimerQuest, SnapGene, Geneious, or Benchling.
- The website does not explain why someone should pay when Primer3, Primer-BLAST, and IDT are free.
- No visible production trust area: uptime, security, payment verification, data privacy, research-use disclaimer, refund policy, support SLA, or Razorpay webhook status.
- No visible sample output/report preview before payment.
- No strong "audit-ready report" selling point.
- No clear batch design story, even though this is the most direct way to beat manual tools.
- Admin/security controls are visible in the same primer page UI; these should not be visible to ordinary public users.
- Pricing section mentions "70%+ cheaper than legacy tools" but does not show the math.

## Pricing Quota Recommendation

User direction: keep prices and increase designs/month for all subscriptions.

Recommended quota update:

| Plan | Current Price | Current Quota | Recommended Quota | New Effective Cost |
|---|---:|---:|---:|---:|
| Individual / Researcher | INR 2,499/mo | 130 designs | 250 designs | ~INR 10/design |
| Lab / Academic Institute | INR 14,999/mo | 1,000 designs | 2,000 designs | ~INR 7.50/design |
| Corporate R&D | INR 49,999/mo | 4,000 designs | 7,500 designs | ~INR 6.67/design |
| Top-up | INR 49/run | 1 design | 1 design | INR 49/design |

Why this works:

- Keeps revenue per subscription unchanged.
- Makes plans look dramatically stronger against free tools.
- Makes the institutional plan more attractive for labs doing batch work.
- Gives the website a strong claim: "From INR 6.67/design on annualized lab-scale usage."

Required guardrails:

- Add fair-use policy.
- Add monthly quota reset rules.
- Add queue limits by plan.
- Add max concurrent jobs by plan.
- Add API rate limits by plan.
- Add large-run batch review for abuse prevention.

Recommended plan positioning:

| Plan | Best Message |
|---|---|
| Individual | For solo researchers who need validated designs and reports without manual cross-checking |
| Lab | Best value for academic labs running weekly qPCR, cloning, assay validation, and student projects |
| Corporate | High-throughput assay design, API access, priority queue, SLA, and dedicated support |

## Website Updates Required Before Production

### P0: Must Update Before Public Launch

1. Replace weak hero messaging.

Current hero is technical but not proof-driven. Recommended hero:

```text
Validated Primer and Probe Design in 22 Checks
Design PCR, qPCR, probe, and multiplex assays with specificity, SNP, repeat, thermodynamic, and manufacturing checks in one report.
```

Primary CTA:

```text
Run 2 Free Validated Designs
```

Secondary CTA:

```text
View Sample Report
```

2. Add a competitor comparison table above pricing.

Required columns:

- Feature
- VigyanLLM
- Primer3
- NCBI Primer-BLAST
- IDT PrimerQuest
- Thermo tools
- SnapGene/Geneious/Benchling

Recommended rows:

- 22-step automated pipeline
- Primer3 baseline design
- BLAST specificity evidence
- Bowtie2 local off-target screening
- dbSNP overlap filtering
- ClinVar / hotspot awareness
- Repeat masking
- Mitochondrial/organelle screen
- Multiplex pooling support
- Probe design
- Manufacturing feasibility
- Exportable audit report
- Batch design
- India-first Razorpay payments
- API / institutional workflow

3. Fix all "10-step pipeline" wording.

Every visible user-facing area should say "22-step pipeline" unless a specific submodule is truly 10 steps.

4. Add sample report preview.

The website should show:

- Top-ranked primer pair
- Specificity result
- SNP overlap status
- Hairpin/dimer risk
- Amplicon size
- Thermocycling profile
- Manufacturing recommendation
- Probe candidates if enabled
- Final verdict: Pass / Risk / Reject

This is the biggest conversion improvement because it shows what users pay for.

5. Hide admin/security controls from public users.

Public users should not see:

- Admin Panel
- Threats
- Users
- File Scanner
- Errors
- Performance
- IP Bans
- Finance
- Malware scan
- Integrity baseline controls

These should move to `/admin-security.html` and require admin authentication.

6. Add trust/security/payment section near pricing.

Required copy blocks:

- Razorpay-secured UPI, cards, net banking.
- Server-authoritative pricing.
- Payment signature verification.
- Webhook reconciliation.
- Research-use-only disclaimer.
- No card data stored by VigyanLLM.
- HTTPS-only production.
- Data retention policy.

7. Add legal/support pages or sections.

Minimum:

- Terms of Use
- Privacy Policy
- Refund Policy
- Research Use Only disclaimer
- Contact/support SLA
- Security disclosure email

8. Add production deployment banner logic.

If backend is not connected, payment buttons and run buttons should show a clear disabled state:

```text
Backend unavailable. Please try again later.
```

No paid checkout should start if backend health fails.

### P1: Strongly Recommended Before Production

1. Add "Why not just Primer3?" section.

Recommended message:

```text
Primer3 designs candidate primers. VigyanLLM turns that into a validated assay workflow: specificity, SNP, repeats, thermodynamics, multiplex risk, probe options, manufacturing checks, and an exportable report.
```

2. Add batch design workflow.

Direct competitor advantage:

- IDT supports batch entries up to 50 sequences.
- VigyanLLM should advertise batch design plus deeper validation.

Recommended feature:

- Upload CSV/FASTA.
- Run multiple accessions.
- Export ranked report per sequence.
- Show batch progress.
- Add "Select all best designs" output.

3. Add saved projects and design history.

Paid users expect:

- Previous designs.
- Repeatable parameters.
- Download history.
- Team/project folders.
- Versioned reports.

4. Add "Assay Confidence Score".

One score can make complex bioinformatics digestible:

```text
Assay Confidence: 94/100
Specificity: Pass
SNP Risk: Low
Dimer Risk: Low
Manufacturing: Ready
```

5. Add side-by-side output comparison.

For example:

```text
VigyanLLM vs Primer3 vs Primer-BLAST for ACTB, KRAS, EGFR, TP53
```

Show where VigyanLLM adds checks beyond primer picking.

6. Add "Database Health" status panel.

Users had earlier issues with database links. Add a visible status widget:

- NCBI Nucleotide: Available
- NCBI Gene: Available
- GENCODE: Available
- UCSC: Available
- NCBI Virus: Available
- ENA: Available
- dbSNP: Available

Include last checked timestamp.

7. Add synthesis ordering story.

The page says IDT/Twist ordering, but the workflow is not yet obvious. Add:

- Export for IDT order
- Export for Twist order
- Copy primer sequences
- Purification recommendation
- Scale recommendation
- Probe dye/quencher recommendation

8. Add "Data Privacy for Labs" section.

Paid labs care about proprietary sequences. Add:

- No public sharing of sequences.
- Optional deletion after design.
- Private project history.
- Enterprise private deployment.
- On-prem option for institutions.

9. Add annual plan benefits without changing monthly pricing.

Suggested:

- Annual billing gets priority queue or extra designs.
- Do not discount heavily yet.
- Use annual plans for cash flow.

10. Add onboarding path.

The site should have:

- "Use accession"
- "Paste FASTA"
- "Upload batch"
- "Analyze existing primers"
- "Compare with database"

This reduces friction for non-technical users.

### P2: Advantage-Building Updates

1. Publish validation studies.

Create pages:

- ACTB qPCR design validation
- KRAS assay design validation
- EGFR assay design validation
- Viral target design validation
- Multiplex panel validation

2. Add lab-ready PDF exports.

Users should be able to download:

- PDF report
- CSV
- JSON
- IDT ordering file
- Twist ordering file
- Methods text for publication

3. Add API docs.

Corporate users need:

- Authentication
- Submit job
- Poll status
- Retrieve report
- Webhook callback
- Rate limits

4. Add "Institution Admin" dashboard.

For lab plans:

- Seats
- Usage
- User-level quotas
- Reports generated
- Failed jobs
- Payment invoices

5. Add scientific citations.

Add citations for:

- Primer3
- SantaLucia thermodynamics
- BLAST
- Bowtie2
- dbSNP / ClinVar
- IGSC screening if used

This improves trust with researchers.

6. Add wet-lab feedback workflow.

After a design:

- User marks amplification result.
- User records Ct, melt curve, gel image.
- Platform learns which designs succeeded.
- This creates a proprietary quality dataset competitors do not have.

## Competitor Upper-Hand Strategy

### Against NCBI Primer-BLAST

NCBI Primer-BLAST is strong because it combines Primer3 and BLAST specificity checking. It is free and trusted.

How VigyanLLM gets upper hand:

- Faster user workflow.
- Batch jobs with saved reports.
- Adds dbSNP, repeat, organelle, multiplex, manufacturing, and probe checks.
- Gives a ranked "use this design" answer instead of making users interpret long forms.
- Stores reusable project history.
- Provides paid support for labs.

Website update needed:

```text
Primer-BLAST is excellent for specificity. VigyanLLM adds assay-level validation, batch reporting, multiplex/probe readiness, and lab workflow exports.
```

### Against Primer3 / Primer3Plus

Primer3 is the scientific baseline.

How VigyanLLM gets upper hand:

- Use Primer3 as one step, not the whole product.
- Show all 22 checks around Primer3 output.
- Make "Primer3-powered, VigyanLLM-validated" a trust message.

Website update needed:

```text
Built on Primer3-style constraints, extended with 21 additional validation and reporting checks.
```

### Against IDT PrimerQuest

IDT PrimerQuest offers PCR/qPCR/probe design, around 45 customizable parameters, and batch entries up to 50 sequences.

How VigyanLLM gets upper hand:

- Offer deeper independent validation.
- Offer vendor-neutral reports.
- Export to multiple synthesis vendors, not only one buying flow.
- Add local database checks and audit reports.
- Add India-first payment and support.

Website update needed:

```text
Design vendor-neutral assays, validate risk, then export to IDT, Twist, or your preferred synthesis vendor.
```

### Against Thermo Fisher Tools

Thermo has strong primer analysis tools and instant dimer/Tm feedback.

How VigyanLLM gets upper hand:

- Go beyond analysis into full assay design.
- Include real pipeline status, database checks, and report output.
- Add batch + history + payment + team workflow.

### Against SnapGene and Geneious

SnapGene and Geneious are broader molecular biology tools with strong sequence visualization and paid subscriptions.

How VigyanLLM gets upper hand:

- Be narrower but deeper for primer/probe assay design.
- Lower India-first entry cost.
- Web-first, no desktop install.
- More focused automated reports.
- Faster for labs that only need assay design rather than full sequence-analysis software.

### Against Benchling

Benchling is broad R&D cloud infrastructure, not a primer-only tool.

How VigyanLLM gets upper hand:

- Much faster to adopt.
- Much lower starting cost.
- Purpose-built for primer/probe design.
- Can become a specialist add-on rather than a Benchling replacement.

Best message:

```text
Use VigyanLLM as a specialist assay-design engine alongside your ELN/LIMS.
```

## Required Security and Payment Updates

### Payment Gateway

Must complete before public production:

- Validate Razorpay webhook on staging public HTTPS endpoint.
- Confirm webhook raw-body signature validation.
- Store and deduplicate `x-razorpay-event-id`.
- Handle out-of-order webhook events.
- Add webhook failure alerting.
- Run a live INR 49 payment.
- Run a refund test.
- Verify invoice/GST flow.
- Add payment success and failure reconciliation in admin dashboard.

Razorpay documentation emphasizes testing webhooks before use, validating signatures with HMAC-SHA256, handling duplicate events, and not assuming event order.

### Application Security

Must complete before production:

- Run app under Gunicorn/uWSGI behind Nginx.
- Set `FORCE_HTTPS=true`.
- Set production `CORS_ORIGINS`.
- Use Redis for rate limiting and token/session state.
- Move admin routes behind admin auth.
- Remove public admin controls from primer page.
- Tighten CSP and reduce `unsafe-inline`.
- Use dependency scanning in CI.
- Add WAF or proxy-level abuse limits.
- Add logging and alerting.
- Add backup/restore runbook.

### Scientific Safety

Must complete before production:

- Make Research Use Only visible.
- Add prohibited-use policy for unsafe biological designs.
- Keep IGSC/biosecurity screening visible where applicable.
- Add support escalation for flagged designs.
- Add audit log for restricted/blocked requests.

## Production Readiness Checklist

### P0 Release Gate

The website is production-launch ready only after all are true:

- Full automated tests pass.
- 20+ real sequence runs complete across multiple use cases.
- Live frontend has no console errors.
- Backend health endpoint returns ready.
- Razorpay test mode order, verify, webhook, duplicate webhook, and refund are tested.
- Razorpay live mode small payment and refund are tested.
- Public HTTPS deployment works.
- HSTS and secure cookies enabled.
- Admin tools hidden from public users.
- Pricing quota is consistent across frontend, backend, and database.
- "10-step" wording fixed everywhere.
- Privacy, terms, refund, RUO, and support pages are published.
- Sample report is visible before purchase.
- Competitor comparison page/section is live.
- Backup and restore tested.
- Monitoring and alerting enabled.

### P1 Launch Quality Gate

- Batch design workflow is live.
- Report PDF export is live.
- Project history is live.
- Database health status is live.
- Team/lab seat management is live or clearly marked as coming soon.
- API documentation exists for corporate plan.
- Annual plan terms are clear.

## Recommended Website Structure

Recommended `primer.html` page order:

1. Hero: "Validated Primer and Probe Design in 22 Checks"
2. Input tool: Auto design / manual analysis / fetch sequence
3. Sample report preview
4. 22-step pipeline explanation
5. Competitor comparison
6. Batch design workflow
7. Database coverage and health
8. Security and privacy
9. Pricing with increased quotas
10. FAQ
11. RUO/legal/support footer

Recommended homepage update:

- Use the homepage for the whole VigyanLLM platform.
- Add a clear "Primer Design" product card linking to `primer.html`.
- Keep primer pricing on the primer page, but avoid conflicting homepage prices.

## Copy Updates to Make the Website Stronger

### Pricing Section

Replace:

```text
Disruptively Affordable Primer Design
```

With:

```text
Validated Assay Design at India-First Pricing
```

Replace:

```text
70%+ cheaper than legacy tools
```

With:

```text
From INR 6.67/design in high-throughput plans, with specificity, SNP, multiplex, thermodynamic, and manufacturing checks included.
```

### Trust Section

Recommended text:

```text
Payments are processed by Razorpay. VigyanLLM does not store card details. Pricing is calculated on the server, payment signatures are verified before credits are added, and webhook events are reconciled for duplicate or delayed delivery.
```

### Competitor Section

Recommended headline:

```text
More Than Primer Picking
```

Recommended body:

```text
Primer3 and Primer-BLAST are excellent scientific tools. VigyanLLM uses primer-design best practices as part of a larger assay-validation workflow: specificity, SNP risk, repeat masking, multiplex scoring, probe design, manufacturing checks, and exportable lab reports.
```

## Suggested Plan Quota Copy

Individual:

```text
250 validated designs/month
Full 22-step pipeline
Sample report export
NCBI/Ensembl fetch included
Single researcher seat
```

Lab:

```text
2,000 validated designs/month
5 researcher seats
Batch design and shared history
Priority queue
Lab report exports
```

Corporate:

```text
7,500 validated designs/month
Unlimited seats
Dedicated API throughput
SLA and dedicated support
Private deployment option
```

## Success Probability After Updates

| Scenario | Current Estimate | After Updates |
|---|---:|---:|
| Generic primer tool | 10-20% | 15-25% |
| India-first validated assay workflow | 35-55% | 55-70% |
| Lab/institution subscription product | 40-60% | 60-75% |
| Enterprise/API assay-design engine | 45-65% | 65-80% |

These are business estimates, not guarantees. The biggest drivers will be pilot lab feedback, wet-lab success evidence, support quality, and how quickly the website communicates the difference between "primer picking" and "validated assay design".

## Final Production Recommendation

Keep prices fixed.

Increase monthly designs to:

- Individual: 250 designs/month
- Lab: 2,000 designs/month
- Corporate: 7,500 designs/month

Then implement the P0 website, security, and payment updates before public launch.

If P0 and P1 are completed, VigyanLLM can credibly launch with an upper hand over direct primer tools because it will offer:

- Free-tool compatibility with paid workflow value.
- 22-step automated validation.
- Vendor-neutral assay reports.
- Batch capability.
- India-first pricing.
- Razorpay payment accessibility.
- Security/privacy trust for labs.
- Saved project/report workflow.
- A path to enterprise API and private deployment.

## Sources Reviewed

- NCBI Primer-BLAST: https://www.ncbi.nlm.nih.gov/tools/primer-blast/
- Primer3: https://primer3.org/
- IDT PrimerQuest: https://www.idtdna.com/pages/tools/primerquest
- Thermo Fisher Multiple Primer Analyzer: https://www.thermofisher.com/us/en/home/brands/thermo-scientific/molecular-biology/molecular-biology-learning-center/molecular-biology-resource-library/thermo-scientific-web-tools/multiple-primer-analyzer.html
- Benchling pricing/platform positioning: https://www.benchling.com/pricing
- SnapGene pricing: https://www.snapgene.com/pricing
- Geneious Prime pricing: https://www.geneious.com/pricing
- Razorpay webhook validation/testing: https://razorpay.com/docs/webhooks/validate-test/
- Razorpay security documentation: https://razorpay.com/docs/security/
