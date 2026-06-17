# Primer Pipeline Production Readiness Report

Run date: 2026-06-09 00:01 Asia/Kolkata
Workspace: `/Users/macbookpro/Desktop/vigyanpilot`

## Verdict

Status: staging-ready, not yet production-ready.

The primer design pipeline now completes full 22-step real-sequence runs with local BLAST, Bowtie2, tabix-backed VCF checks, and the corrected public database routing. It is not production-ready until the deployment uses a production WSGI/server process, real indexed reference databases are installed under `/opt/postgres_data`, production secrets are configured outside `.env` inspection, and monitoring/backups are validated.

## Changes Completed

- Removed direct UCSC and GISAID retrieval hooks from the primer sequence retrieval path.
- Replaced chromosome-coordinate sequence fetching with Ensembl region sequence retrieval.
- Added explicit NCBI Virus routing via open NCBI Nucleotide records.
- Removed COSMIC query hooks from Step 16; clinical hotspot filtering is now ClinVar-only.
- Removed remote UCSC RepeatMasker querying from Step 5; repeat masking now uses local Dfam-style TSV annotations when present and falls back to local sequence-complexity scanning.
- Updated UI database buttons to NCBI Nucleotide, NCBI Gene, Ensembl/GENCODE, and NCBI Virus for the requested direct browser database checks.
- Removed visible UI references to UCSC, GISAID, COSMIC, NUPACK, and RepeatMasker.
- Updated Dockerfile to install open-source native tools: BLAST+, Bowtie2, Primer3, samtools/tabix, and ViennaRNA.
- Confirmed primer design per-run price is ₹49 across active payment/auth code and fixed old ₹99 fallbacks in payment success and migration code.

## Automated Tests

- Focused regression suite: 134 passed.
- Full project suite: 306 passed, 0 failed.
- Python compile check passed for changed backend, retrieval, repeat, clinical, and QA files.

## Native Tool Verification

- blastn: 2.17.0+
- makeblastdb: 2.17.0+
- bowtie2: 2.5.5
- bowtie2-build: 2.5.5
- tabix: htslib 1.23.1

## Real Sequence Runs

Two fresh sequences were used, different from the previous BRCA1/TP53 run.

### EGFR

- Accession: NM_005228.5
- Length: 9,905 bp
- MD5: f8baf0e7ef19149ff286299906be5bb5
- Pipeline status: 22 passed, 0 failed, 0 skipped
- Final pair count: 20
- BLAST specificity: 19/20 pairs passed
- Bowtie2: 20/20 unique mappers
- dbSNP check: 20/20 clear of critical 3' SNPs
- ClinVar check: 20/20 avoid clinical hotspots

### CFTR

- Accession: NM_000492.4
- Length: 6,070 bp
- MD5: d2d9c18c7d08c3f34e3b95d9a97d0a0b
- Pipeline status: 22 passed, 0 failed, 0 skipped
- Final pair count: 20
- BLAST specificity: 14/20 pairs passed
- Bowtie2: 20/20 unique mappers
- dbSNP check: 20/20 clear of critical 3' SNPs
- ClinVar check: 20/20 avoid clinical hotspots

## Browser Database Checks

The primer page loaded at:

`http://127.0.0.1:8080/primer.html?qa=final-dbfix-20260609`

Direct database buttons resolved successfully:

- NCBI Nucleotide: `https://www.ncbi.nlm.nih.gov/nuccore/`
- NCBI Gene: `https://www.ncbi.nlm.nih.gov/gene/`
- Ensembl/GENCODE: `https://www.gencodegenes.org/`
- NCBI Virus: `https://www.ncbi.nlm.nih.gov/labs/virus/vssi/#/`

Backend smoke checks:

- `/health`: ready true, 22 pipeline steps, strict mode true.
- Restricted viral identifiers now return a validation error directing users to NCBI Virus or NCBI Nucleotide accessions.
- Ensembl coordinate route returned `source: ensembl_region` and sequence from Ensembl REST.

## Third-Party Primer3web Comparison

A 239 bp CFTR amplicon from the local pipeline run was submitted to Primer3web 4.1.0 at `https://primer3.ut.ee/cgi-bin/primer3/primer3web_results.cgi`.

Primer3web top result:

- Left primer: AAAGGATACAGACAGCGCCT
- Right primer: GGCTGTACTGCTTTGGTGAC
- Product size: 221 bp
- Tm: 59.09 C / 59.12 C
- GC: 50.00% / 55.00%

Local pipeline top CFTR result:

- Left primer: GACCAAAATCATCTGTGCCC
- Right primer: CTTCCCAGTAAGAGAGGCTG
- Product size: 239 bp
- Tm: 59.98 C / 59.97 C
- GC: 50.00% / 55.00%

Interpretation: Primer3web and the local pipeline both selected valid 20-mer primers in the same small CFTR template with close Tm/GC characteristics. Different primer coordinates are expected because the local pipeline applies additional 22-step filters, BLAST/Bowtie2 specificity checks, SNP/ClinVar checks, ranking penalties, and manufacturing/probe constraints beyond the simple Primer3web form.

## Production Blockers

- The current local backend is the Flask development server. Production should run Gunicorn/uWSGI behind HTTPS and a reverse proxy.
- Real dbSNP, ClinVar, Dfam, BLAST, and Bowtie2 reference datasets must be installed and indexed under `/opt/postgres_data`; the real run used generated QA fixtures for dbSNP/ClinVar availability.
- Organelle/pseudogene databases are still optional and were unavailable in the real run, so Step 12 skipped those subchecks gracefully.
- Some designed primer candidates produced low annealing-temperature warnings before final ranking. Final top pairs still passed, but production UX should surface warnings clearly.
- Production secrets and admin credentials must be configured; `.env` was not opened or modified.

## Recommendation

Promote to staging for user acceptance testing. Hold production release until real reference databases, production process management, HTTPS, secrets, monitoring, backup/restore, and operational runbooks are validated.
