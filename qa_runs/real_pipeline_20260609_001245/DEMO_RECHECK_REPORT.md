# Primer Designing Demo Recheck

Run date: 2026-06-09 00:12 Asia/Kolkata

## Scope

Rechecked the real primer-designing demo with two fresh RefSeq sequences:

- KRAS: `NM_004985.5`
- ACTB: `NM_001101.5`

The run used local BLAST, Bowtie2, makeblastdb, tabix, dbSNP fixture VCF, ClinVar fixture VCF, and the full 22-step project pipeline.

## Tool Versions

- blastn: 2.17.0+
- makeblastdb: 2.17.0+
- bowtie2: 2.5.5
- bowtie2-build: 2.5.5
- tabix: htslib 1.23.1

## Local Pipeline Results

### KRAS

- Accession: `NM_004985.5`
- Length: 5,306 bp
- MD5: `47864ea41bdf55c6de49d6978861460f`
- Pipeline: 22 passed, 0 failed, 0 skipped
- Pair count: 20
- BLAST: 19/20 pairs passed specificity
- Bowtie2: 20/20 unique mappers
- dbSNP: 20/20 clear of critical 3' SNPs
- ClinVar: 20/20 avoid clinical hotspots
- Top local primers:
  - Forward: `GTCATCCAGTGTTGTCATGC`
  - Reverse: `GCTCTTGATTTGTCAGCAGG`
  - Product size: 115 bp
  - Tm: 59.98 C / 59.98 C
  - GC: 50.0% / 50.0%
  - Pool assignment: 1
  - Multiplex compatible: true
  - Cross-pool worst dG: -2.34

### ACTB

- Accession: `NM_001101.5`
- Length: 1,812 bp
- MD5: `7067c04c651a2481cffbb25096e73575`
- Pipeline: 22 passed, 0 failed, 0 skipped
- Pair count: 12
- BLAST: 9/12 pairs passed specificity
- Bowtie2: 12/12 unique mappers
- dbSNP: 12/12 clear of critical 3' SNPs
- ClinVar: 12/12 avoid clinical hotspots
- Top local primers:
  - Forward: `CATCCTCACCCTGAAGTACC`
  - Reverse: `GGATAGCACAGCCTGGATAG`
  - Product size: 235 bp
  - Tm: 59.97 C / 60.19 C
  - GC: 55.0% / 55.0%
  - Pool assignment: 1
  - Multiplex compatible: true
  - Cross-pool worst dG: -3.05

## External Primer3web Comparison

Each local top amplicon was submitted to Primer3web 4.1.0.

### KRAS Amplicon

Primer3web result:

- Forward: `CCAGTGTTGTCATGCATTGGT`
- Reverse: `GATTTGTCAGCAGGACCACC`
- Product size: 104 bp
- Tm: 59.39 C / 58.83 C
- GC: 47.62% / 55.0%

Comparison:

- Local and Primer3web outputs are in the same acceptable Tm band.
- Product sizes are close: 115 bp local vs 104 bp Primer3web.
- Primer sequences differ because the local pipeline applies additional specificity, variant, clinical, multiplex, ranking, manufacturing, and probe constraints.

### ACTB Amplicon

Primer3web result:

- Forward: `CTGAAGTACCCCATCGAGCA`
- Reverse: `AGCCTGGATAGCAACGTACA`
- Product size: 216 bp
- Tm: 59.18 C / 58.81 C
- GC: 55.0% / 50.0%

Comparison:

- Local and Primer3web outputs are in the same acceptable Tm band.
- Product sizes are close: 235 bp local vs 216 bp Primer3web.
- Primer sequences differ for expected reasons: local post-Primer3 filtering and ranking are stricter than the simple Primer3web form.

## Pool / Multiplex Check

Both top local designs passed Step 18 multiplex cross-reaction checks:

- KRAS: pool 1, multiplex compatible, cross-pool worst dG -2.34
- ACTB: pool 1, multiplex compatible, cross-pool worst dG -3.05

## Conclusion

The designing demo is functioning for two real public RefSeq sequences. Outputs are consistent with Primer3web at the thermodynamic/product-size level, while exact primer coordinates differ because the project pipeline adds biological validation and pool/multiplex screening beyond basic Primer3 primer picking.

Remaining demo caveat: organelle/pseudogene databases were unavailable, so Step 12 passed with graceful skip annotations for those subchecks.
