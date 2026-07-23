# Directory Submission Guide

## 1. Zenodo DOI

**Status:** CITATION.cff and .zenodo.json created ✓

**To complete:**
1. Go to https://zenodo.org and sign in with GitHub/ORCID
2. Click "Upload" → "New Upload"
3. Upload a ZIP of the repo (or link GitHub repo)
4. Metadata will auto-populate from `.zenodo.json`
5. Click "Publish" to get a DOI like `10.5281/zenodo.XXXXXXX`
6. Add the DOI to CITATION.cff (`identifiers` field) and cite page

---

## 2. bio.tools

**URL:** https://bio.tools
**Requires:** Free account (email + password)

**Steps:**
1. Sign up at https://bio.tools
2. Click "Add content"
3. Fill in:
   - Name: `VigyanLLM`
   - Description: Use text from `biotools-payload.json`
   - Homepage: `https://www.vigyanllm.in`
4. Or use API: `curl -X POST -H "Content-Type: application/json" -H "Authorization: Token <your_token>" -d @biotools-payload.json https://bio.tools/api/tool/`

**EDAM topics to tag:**
- Primer design, PCR, Sequence analysis, Molecular docking, Protein interaction

---

## 3. AlternativeTo

**URL:** https://alternativeto.net
**Requires:** Free account

**Steps:**
1. Sign up at https://alternativeto.net
2. Click user icon → "Suggest new application"
3. Fill in:
   - Name: `VigyanLLM`
   - Description: "Sovereign biomedical AI platform for primer design, BLAST, molecular docking, MSA, PCR analysis, and more."
   - Platforms: Web
   - License: Free (with premium)
   - Tags: bioinformatics, primer design, PCR, molecular docking, sequence alignment
4. Suggest alternatives: Add Primer3, SnapGene, NCBI Primer-BLAST, BLAST, AutoDock Vina, Clustal Omega as alternatives
5. Add screenshots (use screenshots of the tool pages)

**Approval time:** 1-3 days

---

## 4. There's An AI For That (TAAFT)

**URL:** https://theresanaiforthat.com/s/submit/
**Requires:** Email verification

**Steps:**
1. Go to https://theresanaiforthat.com/s/submit/
2. Enter URL: `https://www.vigyanllm.in`
3. Complete email verification
4. Wait for manual review

**Note:** TAAFT focuses on AI tools. Position VigyanLLM as "AI-powered bioinformatics platform."

---

## 5. OMICtools

**URL:** https://omictools.com/tool-submission/
**Requires:** Free account

**Steps:**
1. Sign up at https://omictools.com
2. Navigate to "Submit a new tool"
3. Fill in tool details (name, description, category, URL)

---

## 6. Product Hunt Launch

**Preparation checklist:**
- [ ] Create Product Hunt maker account
- [ ] Prepare logo (square, 400x400px minimum)
- [ ] Write tagline: "Sovereign biomedical AI platform for primer design, BLAST, docking, and more — free for researchers"
- [ ] Write description (300-500 words highlighting the problem/solution)
- [ ] Prepare 4-5 screenshots/GIFs of the tools
- [ ] Prepare a demo video (under 3 minutes)
- [ ] Choose launch day (Tuesday-Thursday recommended)
- [ ] Schedule for 12:01 AM PT
- [ ] Notify community: email list, Twitter, LinkedIn, Reddit (r/bioinformatics)
- [ ] Prepare first comment: "Hi PH community! We built VigyanLLM because..."

### Draft tagline options:
1. "Sovereign biomedical AI platform for primer design, BLAST, molecular docking & more — free for researchers worldwide"
2. "Free, India-built bioinformatics suite: primer design, BLAST, docking, MSA, and PCR analysis in one platform"
3. "VigyanLLM: Production-grade primer design (VPrime 2.0) and bioinformatics tools — built in India, free for researchers"

### Key differentiators to highlight:
- 22-step biophysical primer validation pipeline
- GPU-accelerated molecular docking
- Free for academic researchers
- Sovereign Indian infrastructure (DPDP/GDPR compliant)
- 10+ integrated bioinformatics tools
- No AI hype — honest thermodynamic/Primer3-based methods
