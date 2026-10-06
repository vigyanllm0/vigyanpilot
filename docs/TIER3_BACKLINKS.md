# Tier-3 Backlinks — 3–5 real links (GSC decline plan, Oct 13–26 window; started Oct 1)

Rule: **no buying links.** Every target below was verified live (HTTP 200) before submission.
Status log maintained in `pending work.md` §2.

## Status board

| # | Target | Type | Status |
|---|--------|------|--------|
| 1 | [danielecook/Awesome-Bioinformatics](https://github.com/danielecook/Awesome-Bioinformatics) | awesome-list PR | ✅ **PR #172 OPEN** (2026-10-01) — new `## Primer Design` section (Primer3, Primer-BLAST, PrimerBank, VigyanLLM) |
| 2 | [brandonhimpfen/awesome-bioinformatics](https://github.com/brandonhimpfen/awesome-bioinformatics) | awesome-list PR | ❌ **PR #29 CLOSED w/o merge** (2026-10-01 — maintainer pass, independent-validation bar; reason logged below, no re-litigating) |
| 3 | Medford Lab, Colorado State — *Molecular Biology Web Tools* | university outreach | 📝 draft ready — **user sends** (see below) |
| 4 | BYU DNA Sequencing Center — *Resources* (`Primers & Primer Design`) | university outreach | 📝 draft ready — **user sends** |
| 5 | Arizona State LibGuides — *Bioinformatics Resources and Tools* | university outreach | 📝 draft ready — **user sends** |

**Accepted & already live (pre-existing, not counted):** bio.tools (sends ~7 referral sessions/mo).

### PR details
- **#172** — branch `vigyanllm0:add-primer-design-section` → `danielecook:master`.
  New section between *Data Processing* and *NGS* + TOC line (doctoc CI may regenerate TOC — expected).
  Disclosure included in PR body ("I maintain VigyanLLM — happy to drop it"). Watch the
  `Check URLs` workflow; all 8 links pre-verified 200.
- **#29** — branch `vigyanllm0:add-vigyanllm` → `brandonhimpfen:main`. Single objective entry
  (their CONTRIBUTING bans multi-link self-promotion — kept to one).
  **Outcome (re-check 2026-10-06):** closed **2026-10-01 by the maintainer without merge**.
  Reason given ([comment](https://github.com/brandonhimpfen/awesome-bioinformatics/pull/29#issuecomment-5923368880)):
  (a) *Data Analysis & Visualization* is only a partial fit — VigyanLLM is an integrated
  analysis platform, not a visualization tool; (b) maintainer "could not establish sufficient
  independent evidence for the project's broader adoption, recognition, or scientific
  validation" — they want independently observable validation, not self-published claims;
  the project "may be reconsidered in the future as that independent footprint develops".
  → Revisit only after third-party citations/validation accumulate (e.g. `/validation`
  referenced by external sites, published citations). Do not re-open now.
- Re-check **#172** on **Oct 8** (Oct-3 slot performed 2026-10-06: still OPEN, MERGEABLE,
  0 comments/reviews since opening 10-01); respond to review comments promptly; if closed
  without merge, note the reason and move on (no re-litigating).

### Considered & rejected (fit/quality — don't re-chase)
- Leeds Omics (leeds.ac.uk): *Tools* page = RNA-Seq sample-size tools only; *Useful Links* = courses — poor fit.
- `bioinformatics2.pitt.edu` — dead (connection refused).
- UMass RNA Web Tools — 403 to automated fetch; no clean contact path.

---

## Outreach drafts (user sends from own email)

### Draft 1 — Medford Lab (Colorado State University)
- **To:** `June.Medford@colostate.edu` (publicly listed on https://medford.colostate.edu/about/)
- **Page:** https://medford.colostate.edu/molecular-biology-web-tools/ (alphabetical molecular-bio
  web-tool list: Finnzymes Tm Calculator, Gibson Calculator, Oligocalc, Restriction Mapper, Reverse Complement…)
- **Subject:** Suggestion for your Molecular Biology Web Tools list — VigyanLLM primer design

```
Hello,

Your lab's Molecular Biology Web Tools page is one I recommend as a quick reference — the
alphabetical format makes it easy to find the right calculator in seconds.

I'd like to suggest adding VigyanLLM to the primer/oligo section:

  VigyanLLM — free online primer design and PCR parameter calculators
  https://www.vigyanllm.in/
  Public repo: https://github.com/vigyanllm0/vigyanpilot

What it covers (all free, no login to run analyses):
  - PCR primer design with Tm, GC%, length, hairpin and dimer checks, off-target screening
  - Standalone calculators: melting temperature (nearest-neighbour, SantaLucia 1998),
    GC content, DNA-to-RNA, reverse complement
  - BLAST and multiple-sequence-alignment tools in the same browser tab

Suggested line for your existing format:
  VigyanLLM — Free online primer design and PCR parameter calculators

Full disclosure: I'm the developer. The engine reproduces published primer sets — a
reproducible benchmark against three literature-validated primer pairs (SARS-CoV-2 N1,
GAPDH, ACTB) is at https://www.vigyanllm.in/validation

If it fits the list, I'd be grateful for the addition — and if anything (documentation,
citation details) would help review, happy to provide it.

Thank you for maintaining the compilation,
[Your name]
VigyanLLM — vigyanllm.in
```

### Draft 2 — BYU DNA Sequencing Center
- **To:** `dnasc@byu.edu` (from https://biology.byu.edu/dnasc/contact-us)
- **Page:** https://biology.byu.edu/dnasc/resources — section **"Primers & Primer Design"**
  (currently: Primer 3, OligoCalc, NetPrimer/Beacon Designer)
- **Subject:** Suggestion for the DNASC Resources page — VigyanLLM primer design

```
Hello DNASC team,

Your Resources page is a genuinely useful reference — the "Primers & Primer Design" section
is exactly where students land before ordering oligos.

May I suggest adding VigyanLLM alongside Primer3 and OligoCalc?

  VigyanLLM — free browser-based primer design with Tm/GC, hairpin and dimer checks and
  off-target screening (no login required to run analyses)
  https://www.vigyanllm.in/   (repo: https://github.com/vigyanllm0/vigyanpilot)

It uses the same SantaLucia 1998 nearest-neighbour thermodynamics as Primer3, and we
publish a reproducible engine benchmark against three published primer sets:
https://www.vigyanllm.in/validation

Full disclosure: I'm the developer. Happy to send anything needed for review (methods,
citations). If the BYU Library's Molecular Biology Web Tools guide would be a better fit
for it, that's welcome too.

Thank you for maintaining the resource list,
[Your name]
VigyanLLM — vigyanllm.in
```

### Draft 3 — Arizona State University LibGuides
- **Where to send:** guide-owner email box on https://libguides.asu.edu/bioinformatics
  (Bioinformatics Resources and Tools guide — open the guide owner's profile contact box)
- **Subject:** Tool suggestion for the Bioinformatics Resources and Tools guide — VigyanLLM

```
Hello,

I'm the maintainer of VigyanLLM (https://www.vigyanllm.in/), a free browser-based suite
for primer design and sequence analysis — Primer3/SantaLucia thermodynamics, Tm and GC
calculators, BLAST, and multiple sequence alignment, with no login required to run analyses.

I found your Bioinformatics Resources and Tools guide and wondered whether VigyanLLM
would fit under the tools section, particularly for primer design / oligo analysis:

  VigyanLLM — https://www.vigyanllm.in/
  Public repo — https://github.com/vigyanllm0/vigyanpilot
  Engine benchmark vs published primer sets — https://www.vigyanllm.in/validation

Full disclosure: I develop the tool. Happy to provide anything your selection criteria
need (methods, citations, accessibility notes).

Thank you for the curation work,
[Your name]
VigyanLLM — vigyanllm.in
```

---

## Tracking

| Date | Action | Result |
|------|--------|--------|
| 2026-10-01 | PR #172 opened (danielecook) | open |
| 2026-10-01 | PR #29 opened (brandonhimpfen) | open |
| 2026-10-01 | PR #29 closed by maintainer (no merge) | declined — partial fit + no independent validation evidence |
| 2026-10-06 | Re-check #172 (Oct-3 slot, overdue) | **still OPEN**, MERGEABLE, 0 comments / 0 reviews, 1 file +10 |
| 2026-10-06 | Re-check #29 (Oct-3 slot, overdue) | **CLOSED w/o merge** (see reason above) |
| | Drafts 1–3 prepared | awaiting send |

Next check: **Oct 8** — PR #172 state/any review comments (log referral sessions in
GSC → Settings → Links if it merges). #29 is closed; not re-chased.
