# Real sequence primer pipeline QA

Run directory: qa_runs/real_pipeline_20260607_233817

## Native tools
- blastn: blastn: 2.17.0+
- makeblastdb: makeblastdb: 2.17.0+
- bowtie2: /usr/local/bin/../Cellar/bowtie2/2.5.5/bin/bowtie2-align-s-v256 version 2.5.5
- bowtie2-build: /usr/local/Cellar/bowtie2/2.5.5/bin/bowtie2-build-s version 2.5.5
- tabix: tabix (htslib) 1.23.1

## Sequences
- BRCA1: NM_007294.4, length 7088, md5 473545f73fab5fcff320d0c2254a9f14
- TP53: NM_000546.6, length 2512, md5 57ef37f4bac5653cc0f5b30fb8de77cb

## 22-step pipeline results
### BRCA1
- Steps: {'passed': 22, 'failed': 0, 'skipped': 0}
- Pairs: 20
- Availability: {'blast_available': True, 'bowtie2_available': True, 'dbsnp_available': True, 'clinvar_available': True, 'cosmic_available': True}
- BLAST: 17/20 pairs passed BLAST specificity filter.
- Bowtie2: 20/20 pairs are unique mappers without pseudogene hits.
- dbSNP/tabix: 20/20 pairs clear of critical 3' SNPs. 0 total variants annotated.
- Clinical VCF/tabix: 20/20 pairs avoid clinical hotspots. 0 flagged with clinical_hotspot_overlap (soft penalty).
- Top pair: CAATTGGGCAGATGTGTGAG / GACTGAAGAGTGAGAGGAGC, amplicon 220, status PASS, score 99.95

### TP53
- Steps: {'passed': 22, 'failed': 0, 'skipped': 0}
- Pairs: 18
- Availability: {'blast_available': True, 'bowtie2_available': True, 'dbsnp_available': True, 'clinvar_available': True, 'cosmic_available': True}
- BLAST: 18/18 pairs passed BLAST specificity filter.
- Bowtie2: 18/18 pairs are unique mappers without pseudogene hits.
- dbSNP/tabix: 18/18 pairs clear of critical 3' SNPs. 0 total variants annotated.
- Clinical VCF/tabix: 18/18 pairs avoid clinical hotspots. 0 flagged with clinical_hotspot_overlap (soft penalty).
- Top pair: CTCTGACTGTACCACCATCC / AGATTCTCTTCCTCTGTGCG, amplicon 189, status PASS, score 99.95

## Primer3Web comparison
- BRCA1 local first pair: {'forward': 'AGTATGGGCTACAGAAACCG', 'reverse': 'ACACTGAGACTGGTTTCCTG', 'product_size': 83, 'penalty': 0.072, 'forward_tm': 59.97, 'reverse_tm': 60.04, 'delta_tm': 0.07}
- BRCA1 Primer3Web first pair: {'forward': {'start': 538, 'length': 20, 'tm': 59.98, 'gc': 50.0, 'sequence': 'CCGAAAATCCTTCCTTGCAG'}, 'reverse': {'start': 758, 'length': 20, 'tm': 59.82, 'gc': 50.0, 'sequence': 'TTCATCCCTGGTTCCTTGAG'}, 'product_size': 221}
- Exact same pair: forward=False, reverse=False
- TP53 local first pair: {'forward': 'TGGAAGGAAATTTGCGTGTG', 'reverse': 'GGATGGTGGTACAGTCAGAG', 'product_size': 108, 'penalty': 0.145, 'forward_tm': 60.12, 'reverse_tm': 59.97, 'delta_tm': 0.15}
- TP53 Primer3Web first pair: {'forward': {'start': 224, 'length': 20, 'tm': 60.12, 'gc': 50.0, 'sequence': 'GAAAACAACGTTCTGTCCCC'}, 'reverse': {'start': 339, 'length': 20, 'tm': 59.97, 'gc': 50.0, 'sequence': 'ATTCTGGGAGCTTCATCTGG'}, 'product_size': 116}
- Exact same pair: forward=False, reverse=False

## Interpretation
- Local and Primer3Web both produced valid primers in the requested length/Tm/GC/product-size ranges, but first-ranked pairs are not identical. That is expected because Primer3Web defaults and objective weights differ from the local step06 post-filter/ranking configuration.
- Full 22-step local runs now complete with native BLAST/Bowtie/tabix available.
- Pseudogene/organelle screening still reports optional reference DBs missing; production should install real pseudogene and mitochondrial reference datasets.