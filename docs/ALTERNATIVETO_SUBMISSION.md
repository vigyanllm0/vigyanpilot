# AlternativeTo + TAAFT Submission Guide

---

## AlternativeTo.net Submission

### Step 1: Create Listing

1. Go to https://alternativeto.net/create/
2. Fill in the fields below

### Title
VigyanLLM

### URL
https://www.vigyanllm.in/

### Description (max 500 chars)
VigyanLLM is a comprehensive bioinformatics platform integrating 12+ molecular biology tools — primer design with 22-step biophysical validation, BLAST sequence search, molecular docking (AutoDock Vina / GNINA), multiple sequence alignment (Clustal Omega), PCR analysis, Tm/GC calculators, and more. Free tier available (5 designs/day, all tools). Pro plan at ₹699/mo with unlimited runs, batch processing, and PDF/PPTX exports. 30% academic discount. No installation required — runs entirely in browser on sovereign Indian infrastructure.

### Category
Science & Education > Bioinformatics  
Development > API Tools  
Science & Education > Biology

### Tags
primer design, bioinformatics, BLAST, molecular docking, multiple sequence alignment, PCR analysis, Tm calculator, GC calculator, CRISPR design, protein docking, primer3, sequence analysis, molecular biology, genomics, biotech tools

### License
Freemium (Free Tier + Paid Plans)

### Platforms
Web

### Screenshots
1. VPrime 2.0 primer design interface (frontend/primer.html)
2. BLAST search results with alignment view (frontend/blast.html)
3. Molecular docking visualization (frontend/docking.html)
4. MSA alignment viewer (frontend/msa.html)

### Social Links
- Twitter: https://x.com/vigyanllm
- Blog: https://www.vigyanllm.in/blog/

### Step 2: Alternative To Matching

VigyanLLM is an alternative to these popular tools (select when prompted):

| Tool | Relationship |
|------|-------------|
| Primer3 | Direct alternative — web-based UI + 22-step validation vs Primer3 CLI |
| NCBI Primer-BLAST | Direct alternative — integrated design + specificity in one workflow |
| Benchling | Partial alternative — primer design module (not full platform) |
| SnapGene | Partial alternative — primer design + PCR analysis (not sequence editing) |
| IDT PrimerQuest | Direct alternative — free with academic discount vs IDT's paid tool |
| AutoDock Vina | Complement — GPU-accelerated web UI for the same engine |
| Clustal Omega | Complement — web UI for the same engine |
| BLAST | Complement — web UI for NCBI BLAST with integrated workflow |

---

## TAAFT (There's An AI For That) Submission

### Step 1: Submit Tool

1. Go to https://taaft.com/submit-tool
2. Fill in the fields below

### Tool Name
VigyanLLM

### Tagline
All-in-one bioinformatics platform: primer design, BLAST, docking, MSA, and PCR analysis

### Full Description
VigyanLLM brings together 12+ molecular biology tools in one sovereign platform. Design primers with 22-step biophysical validation (GC content, Tm, hairpins, dimers, specificity), run BLAST searches against NCBI databases, perform GPU-accelerated molecular docking, align sequences with Clustal Omega, and analyze PCR products — all without leaving your browser. Built on Indian infrastructure with DPDP/GDPR compliance. Free tier available; Pro from ₹699/month.

### Category
Bioinformatics / Research Tools

### Pricing Model
Freemium (Free tier + Pro ₹699/mo + Lab ₹3,999/mo)

### Website
https://www.vigyanllm.in/

### Use Case
Molecular biology research, primer design, sequence analysis, protein-ligand docking, clinical diagnostics

### Features
- 22-step primer validation pipeline
- NCBI BLAST integration
- GPU-accelerated molecular docking
- Multiple sequence alignment
- Tm and GC calculators
- PCR analysis with melt curves
- PDF/PPTX export reports
- Batch sequence processing
- Team collaboration (Lab tier)
- Academic discount (30%)

---

## OMICtools Submission

### Step 1: Submit
1. Go to https://omictools.com/submit-tool
2. Reference `biotools-payload.json` in repo root for EDAM annotations

### Key Fields

**Tool name:** VigyanLLM  
**Short description:** Integrated bioinformatics platform for primer design, BLAST, molecular docking, MSA, and PCR analysis  
**EDAM functions:** Primer design, Sequence similarity search, Molecular docking, Multiple sequence alignment, PCR analysis  
**EDAM topics:** Bioinformatics, Molecular biology, Genomics  
**Operating system:** Web-based  
**License:** Freemium  
**Language:** Python (backend), JavaScript (frontend)  
**Homepage:** https://www.vigyanllm.in/  
**Docs:** https://www.vigyanllm.in/blog/

---

## bio.tools Resubmission (EDAM Update)

The `biotools-payload.json` file in the repo root is ready for bio.tools submission. If already submitted, update the following fields:

1. **Add topic**: `http://edamontology.org/topic_3330` (Bioinformatics) — already present
2. **Add function**: `http://edamontology.org/operation_3624` (Primer design) — already present
3. **Add operatingSystem**: "Web" — already present
4. **Update description**: Add pricing model (Freemium, free tier available)

Submit via: https://bio.tools/submit
