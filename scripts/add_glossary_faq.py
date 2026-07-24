#!/usr/bin/env python3
"""Add FAQPage JSON-LD and expand inline FAQ to 10 items on 10 glossary pages."""

import json, re, os

GLOSSARY_DIR = "/Users/macbookpro/Desktop/vigyanpilot/frontend/glossary"

FAQ_DATA = {
    "pcr.html": {
        "page": "PCR",
        "existing": [
            ("What is PCR?",
             "PCR (Polymerase Chain Reaction) is a technique for exponentially amplifying specific DNA sequences through repeated thermal cycling of denaturation, annealing, and extension steps, producing billions of copies. Explore the full definition and applications on this page."),
            ("How does PCR relate to qPCR?",
             "PCR is closely connected to qPCR and other PCR &amp; Amplification concepts. Understanding these relationships is essential for comprehensive knowledge in molecular biology and bioinformatics."),
            ("How does VigyanLLM use PCR in its pipeline?",
             "VigyanLLM's 24-step validated pipeline incorporates PCR as part of its rigorous quality control framework. The platform automates checks related to PCR to ensure primer design accuracy, specificity, and reliability for research and clinical applications."),
        ],
        "additional": [
            ("What are the main components of a PCR reaction?",
             "PCR requires a DNA template containing the target sequence, a pair of oligonucleotide primers flanking the target region, a thermostable DNA polymerase (typically Taq polymerase), deoxynucleotide triphosphates (dNTPs), buffer solution with magnesium chloride, and nuclease-free water. The primers determine specificity while Mg2+ concentration affects polymerase activity and stringency."),
            ("What is the difference between PCR and qPCR?",
             "Standard PCR amplifies DNA and the product is detected at the end via gel electrophoresis — it is qualitative or semi-quantitative. Quantitative PCR (qPCR) monitors amplification in real-time using fluorescent dyes or probes, allowing precise quantification of starting template. qPCR also offers higher sensitivity and a wider dynamic range than endpoint PCR."),
            ("What causes PCR failure and how do I troubleshoot?",
             "Common causes: degraded template, suboptimal annealing temperature, insufficient Mg2+, primer-dimer formation, or polymerase inhibitors in the sample. Troubleshoot by running a temperature gradient, increasing template concentration, adding DMSO for GC-rich templates, or using a different polymerase. Always include positive and negative controls to isolate the problem."),
            ("How many cycles should I run in PCR?",
             "Standard PCR typically runs 30-35 cycles. Too few cycles yields insufficient product; too many cycles increases non-specific amplification and polymerase error accumulation. For low-abundance templates, increase to 35-40 cycles. For qPCR, 40-45 cycles are standard since fluorescence is measured during the exponential phase before plateau."),
            ("What is touchdown PCR and when should I use it?",
             "Touchdown PCR starts with an annealing temperature 5-10°C above the primer Tm and decreases by 0.5-1°C per cycle until reaching the optimal Ta. This reduces non-specific amplification by favoring specific primer-template binding at higher temperatures. Use touchdown PCR when standard PCR produces multiple bands or when primers have suboptimal Tm matching."),
            ("Can I reuse PCR primers after the reaction?",
             "PCR primers are consumed during the reaction but excess primer typically remains. However, reusing primers from a completed reaction is not recommended because the reaction mix contains PCR products, used dNTPs, and potentially degraded components. Always use fresh primers and master mix for each experiment to ensure reproducibility."),
            ("What is the role of magnesium concentration in PCR?",
             "Mg2+ is a critical cofactor for DNA polymerase activity. Too little Mg2+ reduces polymerase activity and yield. Too much Mg2+ increases non-specific amplification by stabilizing mispaired primer-template complexes. The optimal Mg2+ concentration ranges from 1.5-3.0 mM and should be optimized for each primer-template pair using a titration series."),
        ],
    },
    "crispr.html": {
        "page": "CRISPR",
        "existing": [
            ("What is CRISPR?",
             "CRISPR-Cas9 is a genome editing technology using guide RNA to direct Cas9 nuclease to specific DNA sequences for precise modifications through double-strand break repair by NHEJ or HDR. Explore the full definition and applications on this page."),
            ("How does CRISPR relate to Cas9?",
             "CRISPR is closely connected to Cas9 and other Genome Editing concepts. Understanding these relationships is essential for comprehensive knowledge in molecular biology and bioinformatics."),
            ("How does VigyanLLM use CRISPR in its pipeline?",
             "VigyanLLM's 24-step validated pipeline incorporates CRISPR as part of its rigorous quality control framework. The platform automates checks related to CRISPR to ensure primer design accuracy, specificity, and reliability for research and clinical applications."),
        ],
        "additional": [
            ("What is the difference between CRISPR-Cas9 and CRISPR-Cas12a?",
             "Cas9 requires a 20 nt gRNA with an NGG PAM sequence and creates a blunt double-strand break 3 bp upstream of the PAM. Cas12a requires a 23-25 nt crRNA with a TTTV PAM and creates staggered cuts with 5-nt overhangs. Cas12a is smaller, processes its own crRNA, and is better suited for multiplex applications."),
            ("What is a PAM sequence and why is it important?",
             "The protospacer-adjacent motif (PAM) is a short DNA sequence (typically 2-6 bases) adjacent to the target site that is essential for Cas nuclease recognition and cleavage. Different Cas variants recognize different PAM sequences: SpCas9 requires NGG, SaCas9 requires NNGRRT, and Cas12a requires TTTV. Without the correct PAM, Cas nuclease cannot bind or cut."),
            ("How do I design a guide RNA for CRISPR experiments?",
             "Select a 20-nt sequence immediately upstream of the PAM, check for 40-70% GC content, avoid poly-T runs (acts as RNA pol III terminator), and minimize off-target matches in the genome. Use validated scoring algorithms like Azimuth 2.0 or Doench 2016 for on-target efficiency prediction. Design 3-4 gRNAs per target since efficiency varies by locus."),
            ("What is homology-directed repair (HDR) in CRISPR?",
             "HDR is a DNA repair pathway that uses a homologous template to repair double-strand breaks precisely. In CRISPR experiments, researchers supply a donor template with homology arms flanking the desired edit. HDR is more efficient in dividing cells and during S/G2 phase. The efficiency ranges from 1-20% depending on cell type, donor design, and delivery method."),
            ("How do I deliver CRISPR components into cells?",
             "Common delivery methods include: plasmid transfection (expresses Cas9 and gRNA from DNA vectors — standard for cell lines), ribonucleoprotein (RNP) delivery (pre-assembled Cas9 protein + gRNA — lower off-target, suitable for primary cells), viral delivery (AAV or lentivirus — for in vivo), and mRNA electroporation (transient Cas9 expression, minimal DNA integration)."),
            ("What are CRISPR off-target effects and how do I minimize them?",
             "Off-target effects occur when gRNA binds to similar but non-identical genomic sequences, causing unintended edits. Minimize them by using high-fidelity Cas9 variants (eSpCas9, SpCas9-HF1), truncated gRNAs (17-18 nt), computational off-target prediction tools (CFD, MIT scores), and paired nickase approaches. Always validate editing at predicted off-target sites."),
            ("What is the CRISPR knockout workflow?",
             "The typical workflow: (1) select target gene and identify early coding exons, (2) design gRNAs targeting exon 1-3, (3) clone or order gRNAs as synthetic oligos, (4) deliver Cas9 and gRNA into cells via transfection or transduction, (5) harvest DNA 48-72 hours post-delivery, (6) verify editing by Sanger sequencing or T7E1 assay, (7) isolate clonal populations if needed."),
        ],
    },
    "bioinformatics.html": {
        "page": "Bioinformatics",
        "existing": [
            ("What is the difference between bioinformatics and computational biology?",
             "Bioinformatics focuses on developing tools, databases, and algorithms for storing and analyzing biological data (e.g., BLAST for sequence searching, genome browsers for data visualization). Computational biology uses these tools and quantitative methods to answer specific biological questions, such as modeling protein folding, simulating metabolic pathways, or inferring evolutionary trees. Bioinformatics provides the infrastructure; computational biology applies it to make biological discoveries."),
            ("What are the most important bioinformatics databases?",
             "Key bioinformatics databases include: (1) NCBI GenBank for nucleotide sequences, (2) UniProt/Swiss-Prot for protein sequences and annotations, (3) Protein Data Bank (PDB) for 3D protein structures, (4) Ensembl and UCSC Genome Browser for genome assemblies and annotations, (5) dbSNP and ClinVar for genetic variants and clinical significance, (6) Gene Expression Omnibus (GEO) for transcriptomics data, and (7) KEGG and Reactome for pathway information. VigyanLLM integrates several of these databases for primer design validation."),
            ("How is bioinformatics used in clinical diagnostics?",
             "Bioinformatics enables clinical diagnostics through: (1) identifying disease-causing variants from NGS data, (2) designing specific PCR primers and probes for pathogen detection, (3) predicting drug resistance from genomic sequences, (4) analyzing tumor genomes for precision oncology, and (5) interpreting microbial metagenomes for infectious disease diagnosis. VigyanLLM applies bioinformatics principles in its primer design and validation pipeline to ensure clinical-grade specificity and reliability."),
        ],
        "additional": [
            ("What are the main branches of bioinformatics?",
             "The main branches include genomics (DNA sequence analysis, genome assembly, variant calling), transcriptomics (RNA-seq analysis, gene expression quantification), proteomics (protein structure prediction, mass spectrometry analysis), systems biology (pathway analysis, network modeling), and phylogenetics (evolutionary tree reconstruction from molecular data)."),
            ("What programming languages are used in bioinformatics?",
             "Python is the most widely used for bioinformatics due to its rich ecosystem (Biopython, pandas, scikit-learn) and readability. R is essential for statistical analysis and visualization (Bioconductor). Bash/command-line tools are critical for data processing. C/C++ and Rust are used for performance-critical algorithms. SQL is used for database management."),
            ("What is the FASTA format and how is it used?",
             "FASTA is a text-based format for representing nucleotide or amino acid sequences. Each entry starts with a \">\" line containing the sequence identifier and optional description, followed by the sequence data. FASTA is the standard format for sequence databases, BLAST searches, multiple sequence alignment input, and sequence storage."),
            ("What is the difference between BLAST and FASTA algorithms?",
             "Both find sequence similarity but use different approaches. BLAST uses a word-based seeding strategy (breaking query into short words) for faster searches, while FASTA uses a hash-based approach. BLAST is generally faster for large database searches, while FASTA can be more sensitive for detecting distant homologies in protein sequences."),
            ("What bioinformatics databases are essential for molecular biology?",
             "Essential databases include NCBI GenBank (nucleotide sequences), UniProt/SwissProt (curated protein sequences), PDB (protein structures), RefSeq (curated reference sequences), dbSNP (genetic variants), gnomAD (population variation), KEGG (pathways), and Ensembl (genome annotations). Most are freely accessible through web interfaces or APIs."),
            ("What is the role of machine learning in bioinformatics?",
             "Machine learning powers protein structure prediction (AlphaFold, ESMFold), variant effect prediction (CADD, PrimateAI), drug-target interaction prediction, gene expression classification, and biomedical image analysis. Deep learning has revolutionized structural biology, while traditional ML methods remain important for feature-based prediction tasks."),
            ("How do I choose between different bioinformatics tools for the same task?",
             "Consider: (1) accuracy — benchmark performance on relevant datasets, (2) speed — processing time for your data size, (3) ease of use — command-line vs web interface, (4) documentation and community support, (5) cost — free vs licensed, (6) data privacy — local vs cloud processing. Test 2-3 tools on a representative subset of your data before committing."),
        ],
    },
    "genomics.html": {
        "page": "Genomics",
        "existing": [
            ("What is the difference between genetics and genomics?",
             "Genetics studies individual genes, their inheritance patterns, mutations, and functions. Genomics takes a holistic approach, studying all genes and non-coding sequences in the genome simultaneously. For example, genetics might investigate a single BRCA1 mutation in breast cancer, while genomics would sequence the entire tumor genome to identify all mutations, copy number changes, and structural variants contributing to cancer development and treatment response."),
            ("What are the main applications of genomics in medicine?",
             "Medical genomics applications include: (1) diagnosing rare genetic diseases through WES/WGS, (2) oncology — identifying driver mutations for targeted therapy selection, (3) pharmacogenomics — predicting drug response based on genetic variants, (4) prenatal screening through non-invasive prenatal testing (NIPT), (5) carrier screening for recessive disorders, (6) infectious disease genomics — tracking pathogen evolution and drug resistance, and (7) precision public health — population-level genomic surveillance."),
            ("How does genomics relate to primer design?",
             "Genomic information is essential for primer design because primers must be specific to their target within the context of the entire genome. A human genomic template is 3.2 billion base pairs — primers must uniquely amplify the intended region without off-target binding. VigyanLLM's primer design tool uses BLAST alignment against complete reference genomes (NCBI RefSeq) to verify specificity, checks for SNP overlap using dbSNP and gnomAD databases, and masks repetitive elements identified through genomic annotation."),
        ],
        "additional": [
            ("What is the difference between genomics and genetics?",
             "Genetics studies individual genes and their inheritance patterns, focusing on specific traits or diseases caused by single gene variants. Genomics analyzes the entire genome — all genes, regulatory elements, and non-coding DNA — to understand their collective structure, function, and interactions. Genomics uses high-throughput technologies like next-generation sequencing."),
            ("What is next-generation sequencing (NGS)?",
             "NGS is a high-throughput DNA sequencing technology that parallelly sequences millions of DNA fragments simultaneously. Unlike Sanger sequencing which sequences one fragment at a time, NGS enables whole-genome sequencing, targeted sequencing, RNA-seq, and epigenomic profiling in a single run. Illumina sequencing-by-synthesis is the most widely used NGS technology."),
            ("What is a genome assembly?",
             "Genome assembly is the process of reconstructing complete chromosome sequences from short DNA sequencing reads. It involves overlapping reads to form longer contiguous sequences (contigs), ordering contigs into scaffolds, and anchoring scaffolds to chromosomes. Reference-quality assemblies require high coverage (30-60x) and a combination of short-read and long-read sequencing technologies."),
            ("What is the human genome reference sequence?",
             "The human genome reference is a digital representation of the human genome used as a standard for comparison in genomic studies. Current version GRCh38 (hg38) covers approximately 3.1 billion base pairs. It is a composite derived from multiple individuals and continues to be refined with gap-free telomere-to-telomere assemblies from the T2T Consortium."),
            ("How is genomics used in precision medicine?",
             "Genomics enables precision medicine by identifying genetic variants that influence drug response (pharmacogenomics), predicting disease risk from polygenic risk scores, guiding cancer treatment based on tumor mutational profiles, diagnosing rare genetic diseases through whole-exome or whole-genome sequencing, and monitoring treatment response through liquid biopsies."),
            ("What is a genome-wide association study (GWAS)?",
             "GWAS scans the genomes of thousands of individuals to identify single nucleotide polymorphisms (SNPs) associated with a particular trait or disease. It compares SNP frequencies between cases and controls, identifying statistically significant associations. GWAS has discovered thousands of genetic variants linked to complex diseases but typically explains only a fraction of heritability."),
            ("What is the difference between structural variants and SNPs?",
             "Single nucleotide polymorphisms (SNPs) change one DNA base and are the most common type of genetic variation. Structural variants (SVs) are larger changes affecting 50+ base pairs, including deletions, duplications, inversions, insertions, and translocations. SVs affect more total base pairs of the genome than SNPs but are harder to detect with standard short-read sequencing."),
        ],
    },
    "dna.html": {
        "page": "DNA",
        "existing": [
            ("What is DNA?",
             "DNA (deoxyribonucleic acid) is the double-stranded helical molecule storing genetic information through sequences of four bases (A, T, G, C). The human genome contains 3.2 billion base pairs. Explore the full definition and applications on this page."),
            ("How does DNA relate to genome?",
             "DNA is closely connected to genome and other Molecular Biology concepts. Understanding these relationships is essential for comprehensive knowledge in molecular biology and bioinformatics."),
            ("How does VigyanLLM use DNA in its pipeline?",
             "VigyanLLM's 24-step validated pipeline incorporates DNA as part of its rigorous quality control framework. The platform automates checks related to DNA to ensure primer design accuracy, specificity, and reliability for research and clinical applications."),
        ],
        "additional": [
            ("What is the structure of DNA?",
             "DNA is a double helix composed of two polynucleotide strands running antiparallel. Each strand has a sugar-phosphate backbone with four nitrogenous bases: adenine (A), thymine (T), cytosine (C), and guanine (G). A pairs with T via two hydrogen bonds, and C pairs with G via three hydrogen bonds. The sequence of bases encodes genetic information."),
            ("What is the difference between DNA and RNA?",
             "DNA is double-stranded, uses deoxyribose sugar and thymine, and serves as the long-term genetic storage molecule. RNA is typically single-stranded, uses ribose sugar and uracil instead of thymine, and performs various functions including carrying genetic information (mRNA), catalyzing reactions (ribozymes), and regulating gene expression (miRNA, siRNA)."),
            ("How is DNA replicated?",
             "DNA replication is the process by which a cell copies its DNA before division. The double helix unwinds, and DNA polymerase synthesizes new complementary strands using each original strand as a template. The leading strand is synthesized continuously, while the lagging strand is synthesized in short Okazaki fragments that are later joined by DNA ligase."),
            ("What is a gene?",
             "A gene is a segment of DNA that contains the instructions for making a functional product, typically a protein or RNA molecule. Genes include coding regions (exons) that determine the protein sequence and non-coding regions (introns, promoters, enhancers) that regulate when, where, and how much of the product is made. The human genome contains approximately 20,000-25,000 protein-coding genes."),
            ("What is the DNA double helix and who discovered it?",
             "The DNA double helix is the three-dimensional structure of DNA, discovered by James Watson and Francis Crick in 1953 based on X-ray crystallography data from Rosalind Franklin and Maurice Wilkins. The structure explained how genetic information could be stored in the base sequence and accurately copied through complementary base pairing during replication."),
            ("What is mitochondrial DNA and how is it inherited?",
             "Mitochondrial DNA (mtDNA) is a small circular DNA molecule found in mitochondria, inherited exclusively from the mother. It contains 37 genes essential for oxidative phosphorylation. mtDNA is used in evolutionary studies, forensic identification, and diagnosing mitochondrial disorders. It mutates faster than nuclear DNA, making it useful for tracing maternal lineages."),
            ("How is DNA sequenced?",
             "Modern DNA sequencing uses next-generation sequencing (NGS) technology. DNA is fragmented, adapters are ligated, and fragments are sequenced in parallel on a flow cell. Illumina sequencing uses fluorescently labeled reversible terminators that emit a signal when each base is incorporated. Oxford Nanopore sequencing measures electrical current changes as DNA passes through a protein nanopore."),
        ],
    },
    "rna.html": {
        "page": "RNA",
        "existing": [
            ("What is RNA?",
             "RNA (ribonucleic acid) is single-stranded nucleic acid essential for information transfer (mRNA), catalysis (ribozymes), translation (tRNA, rRNA), and gene regulation (miRNA, siRNA, lncRNA). Explore the full definition and applications on this page."),
            ("How does RNA relate to mRNA?",
             "RNA is closely connected to mRNA and other Sequencing concepts. Understanding these relationships is essential for comprehensive knowledge in molecular biology and bioinformatics."),
            ("How does VigyanLLM use RNA in its pipeline?",
             "VigyanLLM's 24-step validated pipeline incorporates RNA as part of its rigorous quality control framework. The platform automates checks related to RNA to ensure primer design accuracy, specificity, and reliability for research and clinical applications."),
        ],
        "additional": [
            ("What are the different types of RNA?",
             "The main types include messenger RNA (mRNA) which carries protein-coding information, transfer RNA (tRNA) which brings amino acids during translation, ribosomal RNA (rRNA) which forms the structural core of ribosomes, microRNA (miRNA) which regulates gene expression post-transcriptionally, small interfering RNA (siRNA) involved in RNA interference, and long non-coding RNA (lncRNA) with diverse regulatory functions."),
            ("What is the difference between mRNA and pre-mRNA?",
             "Pre-mRNA is the initial transcript synthesized from DNA during transcription, containing both exons (coding regions) and introns (non-coding regions). mRNA is the mature form after splicing removes introns and adds a 5-prime cap and poly-A tail. Only mature mRNA is exported from the nucleus to the cytoplasm for translation into protein."),
            ("How is RNA extracted from cells?",
             "RNA is extracted using guanidinium isothiocyanate-phenol-chloroform methods (TRIzol) or silica membrane column-based kits (Qiagen RNeasy). Cells are lysed in a denaturing buffer that inactivates RNases, RNA is separated from DNA and proteins by phase separation or column binding, washed, and eluted in RNase-free water. Samples must be kept on ice and treated with DNase to remove genomic DNA."),
            ("What is reverse transcription and why is it important?",
             "Reverse transcription converts RNA into complementary DNA (cDNA) using the enzyme reverse transcriptase. This is essential for studying RNA by DNA-based methods like PCR and sequencing, since DNA polymerases cannot use RNA as a template. RT-PCR, RNA-seq, and cDNA library construction all depend on reverse transcription. The enzyme was originally discovered in retroviruses."),
            ("What is RNA interference (RNAi)?",
             "RNAi is a biological process where small RNA molecules (siRNA or miRNA) bind to complementary mRNA sequences and trigger their degradation or block translation, thereby silencing gene expression. It is a natural regulatory mechanism conserved across eukaryotes and is harnessed experimentally to knock down specific genes for functional studies or therapeutic applications."),
            ("How is RNA-seq used in transcriptomics?",
             "RNA-seq converts RNA to cDNA, sequences it on a high-throughput platform, and maps the reads to a reference genome or transcriptome. It quantifies gene expression levels, discovers novel transcripts and splice variants, identifies fusion genes, detects allele-specific expression, and reveals non-coding RNA expression. RNA-seq has largely replaced microarrays for transcriptome analysis."),
            ("What causes RNA degradation and how do I prevent it?",
             "RNA is degraded by RNases, which are ubiquitous enzymes present on skin, dust, and lab surfaces. Prevent degradation by using RNase-free water and tubes, wearing gloves, working in a dedicated RNA area, using RNA stabilization reagents (RNAlater), storing RNA at -80°C, and adding RNase inhibitors to reactions. RNA integrity should be verified before downstream applications."),
        ],
    },
    "primer.html": {
        "page": "Primer",
        "existing": [
            ("What is primer?",
             "A primer is a short synthetic DNA oligonucleotide (18-25 nt) complementary to a target DNA sequence, serving as the starting point for DNA polymerase extension during PCR, sequencing, or cloning reactions. Explore the full definition and applications on this page."),
            ("How does primer relate to forward primer?",
             "primer is closely connected to forward primer and other Primer Design concepts. Understanding these relationships is essential for comprehensive knowledge in molecular biology and bioinformatics."),
            ("How does VigyanLLM use primer in its pipeline?",
             "VigyanLLM's 24-step validated pipeline incorporates primer as part of its rigorous quality control framework. The platform automates checks related to primer to ensure primer design accuracy, specificity, and reliability for research and clinical applications."),
        ],
        "additional": [
            ("What makes a good PCR primer?",
             "A good PCR primer has: length of 18-24 nucleotides, melting temperature of 55-65°C (within 2°C of its pair), GC content of 40-60%, a GC clamp at the 3-prime end, minimal self-complementarity and secondary structure, no runs of 4+ identical bases, no significant homology to non-target sequences checked via BLAST, and an amplicon size appropriate for the application."),
            ("What is the difference between forward and reverse primers?",
             "The forward primer binds to the antisense (complementary) strand of DNA at the 5-prime end of the target region and extends in the 3-prime direction along the sense strand. The reverse primer binds to the sense strand at the 3-prime end of the target and extends in the opposite direction toward the forward primer. Together they define the amplified region."),
            ("How is primer melting temperature (Tm) calculated?",
             "Tm is calculated using the nearest-neighbor thermodynamic model, which sums the enthalpy and entropy contributions of each adjacent base pair. The formula accounts for salt concentration, magnesium concentration, and primer concentration. This is more accurate than the basic 4+2(G+C) rule which assumes all base pairs contribute equally to stability."),
            ("What is primer specificity and how is it checked?",
             "Primer specificity is the ability of a primer to bind only to its intended target sequence and not to similar sequences elsewhere in the genome. It is checked by BLASTing the primer sequence against the target genome. High specificity means the primer has no significant matches to off-target sites, especially at the critical 3-prime end where DNA polymerase extends."),
            ("What is a degenerate primer and when is it used?",
             "A degenerate primer contains mixed bases at certain positions (using IUPAC codes like R, Y, N) to allow amplification of related but non-identical sequences. Degenerate primers are used for cross-species PCR (amplifying a gene from multiple species), viral detection (amplifying variable viral genomes), and targeting conserved regions in related gene families."),
            ("How do primer-dimers form and how can I prevent them?",
             "Primer-dimers form when primers bind to each other instead of the template due to complementary 3-prime ends. This creates short PCR artefacts that compete with the target amplicon. Prevent them by checking primer complementarity in design tools, keeping primer concentrations between 200-500 nM, designing primers with non-complementary 3-prime ends, and using hot-start polymerases."),
            ("Can I use the same primers for PCR and qPCR?",
             "Yes, but qPCR requires more stringent primer design: shorter amplicons (70-200 bp), tighter Tm matching (within 1-2°C), and no secondary structures that could quench SYBR Green fluorescence. Standard PCR primers (designed for 300-1000 bp amplicons) may work poorly in qPCR due to inefficient amplification of longer products during the rapid cycling."),
        ],
    },
    "gene-expression.html": {
        "page": "Gene Expression",
        "existing": [
            ("What is the difference between gene expression and transcription?",
             "Transcription is the first step of gene expression — the synthesis of RNA from a DNA template by RNA polymerase. Gene expression is the broader process encompassing transcription, RNA processing, translation, and post-translational modifications. A gene may be transcribed but not translated (due to regulatory mechanisms), meaning transcription alone does not always equal functional gene expression. This is why measuring both mRNA (by RT-qPCR or RNA-seq) and protein (by western blot or mass spectrometry) provides a complete picture."),
            ("How is gene expression quantified by RT-qPCR?",
             "RT-qPCR quantifies gene expression by reverse-transcribing RNA to cDNA, then amplifying specific targets using fluorescent probes or DNA-binding dyes (SYBR Green). The cycle threshold (Ct) value inversely correlates with starting RNA quantity. Relative expression is calculated using the 2^(-delta-delta-Ct) method, normalizing to stable reference genes (e.g., GAPDH, beta-actin, 18S rRNA). VigyanLLM's primer design tool helps design RT-qPCR primers that span exon-exon junctions, ensuring cDNA-specific amplification without genomic DNA contamination."),
            ("What are the main methods for measuring gene expression?",
             "Major methods include: (1) RT-qPCR — gold standard for targeted quantification of specific genes, (2) RNA-seq — unbiased, genome-wide transcriptome analysis, (3) microarrays — targeted hybridization-based profiling of known transcripts, (4) single-cell RNA-seq — gene expression at individual cell resolution, (5) Northern blotting — size-based RNA detection (less common today), (6) in situ hybridization (ISH) — spatial localization of transcripts in tissues, and (7) NanoString nCounter — digital multiplexed counting without amplification. Each method has trade-offs in throughput, sensitivity, cost, and data complexity."),
        ],
        "additional": [
            ("What are the steps of gene expression?",
             "Gene expression involves two main steps: transcription, where DNA is copied into messenger RNA (mRNA) by RNA polymerase in the nucleus, and translation, where mRNA is decoded by ribosomes to synthesize a protein in the cytoplasm. Additional steps include RNA processing (capping, splicing, polyadenylation), mRNA transport, and post-translational modification of the protein."),
            ("What is the difference between gene expression and protein expression?",
             "Gene expression refers to the production of an RNA molecule from a gene (transcription), which may or may not lead to protein synthesis. Protein expression specifically refers to the production of a functional protein through transcription and translation. The correlation between mRNA and protein levels is often poor due to post-transcriptional regulation, alternative splicing, and protein degradation."),
            ("How do transcription factors regulate gene expression?",
             "Transcription factors are proteins that bind to specific DNA sequences (promoters, enhancers) to activate or repress transcription. Activators recruit RNA polymerase and co-activators to initiate transcription. Repressors block polymerase binding or recruit chromatin-modifying enzymes that condense DNA. The combinatorial action of multiple transcription factors creates precise spatial and temporal expression patterns."),
            ("What is the role of epigenetics in gene expression?",
             "Epigenetics studies heritable changes in gene expression that do not involve changes to the DNA sequence. Key mechanisms include DNA methylation (typically represses transcription), histone modifications (acetylation activates, methylation can activate or repress), and chromatin remodeling (changes DNA accessibility). Epigenetic marks can be influenced by environment, diet, and aging."),
            ("How is gene expression measured in the laboratory?",
             "Common methods include qRT-PCR (sensitive, targeted quantification of specific genes), RNA-seq (genome-wide expression profiling), microarrays (targeted genome-wide but lower dynamic range), Northern blot (size-based RNA detection), and in situ hybridization (spatial expression patterns). RNA-seq is now the standard for discovery-based experiments while qRT-PCR is used for validation."),
            ("What is differential gene expression analysis?",
             "Differential expression analysis compares transcript levels between experimental conditions to identify genes that are significantly upregulated or downregulated. Statistical methods (DESeq2, edgeR) model count data and account for sequencing depth and biological variability. Results are typically visualized as volcano plots, heatmaps, and MA plots. Genes with adjusted p-value < 0.05 and fold change > 2 are considered significant."),
            ("How do housekeeping genes differ from regulated genes?",
             "Housekeeping genes are constitutively expressed in all cells and maintain basic cellular functions like metabolism and structure. Their expression is relatively stable across conditions. Examples include GAPDH, ACTB (beta-actin), and 18S rRNA. Regulated genes show variable expression depending on cell type, developmental stage, or environmental conditions. Housekeeping genes are used as normalization controls in qPCR and RNA-seq."),
        ],
    },
    "molecular-biology.html": {
        "page": "Molecular Biology",
        "existing": [
            ("What is the central dogma of molecular biology?",
             "The central dogma describes the flow of genetic information: DNA is transcribed into RNA, which is then translated into protein. Francis Crick first articulated this concept in 1958. While retroviruses can reverse-transcribe RNA into DNA (via reverse transcriptase), and RNA can replicate itself, the core DNA-RNA-protein flow is fundamental to all cellular life."),
            ("What are the key techniques in molecular biology?",
             "Essential molecular biology techniques include: (1) PCR and qPCR for DNA/RNA amplification and quantification, (2) molecular cloning for gene insertion into vectors, (3) DNA sequencing (Sanger and next-generation), (4) gel electrophoresis for size-based separation, (5) blotting methods (Southern, Northern, Western) for detecting specific molecules, and (6) CRISPR-Cas9 for genome editing. VigyanLLM automates several of these workflows through its primer design and PCR validation platform."),
            ("How does molecular biology relate to genomics and bioinformatics?",
             "Molecular biology provides the experimental foundation for genomics (the study of entire genomes) and bioinformatics (computational analysis of biological data). Next-generation sequencing technologies, developed through molecular biology, generate the raw data that bioinformatics tools analyze. VigyanLLM bridges these fields by integrating molecular biology principles into automated computational pipelines for primer design, specificity checking, and PCR optimization."),
        ],
        "additional": [
            ("What is the central dogma of molecular biology?",
             "The central dogma describes the flow of genetic information in cells: DNA is transcribed into RNA, which is translated into protein. Francis Crick first formulated this framework in 1958. While this unidirectional flow is the primary pathway, exceptions exist including reverse transcription (RNA to DNA in retroviruses) and RNA replication (in some viruses)."),
            ("What are the key techniques used in molecular biology?",
             "Essential techniques include PCR (DNA amplification), gel electrophoresis (size-based separation), cloning (inserting DNA into vectors), DNA sequencing (reading base sequences), Southern/Northern/Western blotting (detecting specific DNA/RNA/protein), CRISPR gene editing, recombinant protein expression, and microarrays for genome-wide analysis. Modern molecular biology increasingly relies on high-throughput sequencing."),
            ("What is recombinant DNA technology?",
             "Recombinant DNA technology involves combining DNA from different sources to create novel genetic combinations. Key steps include: isolating the gene of interest, inserting it into a plasmid vector using restriction enzymes and DNA ligase, transforming the recombinant plasmid into host cells (typically E. coli), and selecting successfully transformed cells. This technology underlies genetic engineering and biotechnology."),
            ("What is a plasmid and how is it used in molecular biology?",
             "A plasmid is a small, circular, extrachromosomal DNA molecule that replicates independently in bacteria. Plasmids are used as cloning vectors to carry foreign DNA, express recombinant proteins (expression plasmids), deliver genes for gene therapy, and as tools for CRISPR editing. They contain an origin of replication, selectable marker (antibiotic resistance), and a multiple cloning site."),
            ("What is the difference between prokaryotic and eukaryotic gene expression?",
             "Prokaryotes have coupled transcription and translation in the cytoplasm, no introns, polycistronic mRNA (one mRNA encodes multiple proteins), and simpler regulation. Eukaryotes have separate transcription (nucleus) and translation (cytoplasm), introns requiring splicing, monocistronic mRNA (one gene per mRNA), and complex regulation involving chromatin structure and multiple transcription factors."),
            ("What are restriction enzymes and how are they used?",
             "Restriction enzymes (restriction endonucleases) are bacterial enzymes that cut DNA at specific recognition sequences (typically 4-8 bp palindromic sequences). They are essential tools for molecular cloning — cutting DNA at defined positions for insertion into vectors, generating compatible sticky ends, and analyzing DNA fragment patterns by restriction mapping. Over 3000 restriction enzymes have been characterized."),
            ("What is Sanger sequencing and how does it work?",
             "Sanger sequencing (dideoxy chain termination method) uses DNA polymerase to synthesize new DNA strands with modified nucleotides (ddNTPs) that terminate elongation. The resulting fragments of different lengths are separated by capillary electrophoresis. Each ddNTP is labeled with a different fluorescent dye, and the sequence is read from the fluorescence signal. Though replaced by NGS for large projects, Sanger sequencing remains the gold standard for validating individual sequences up to 1000 bp."),
        ],
    },
    "clinical-diagnostics.html": {
        "page": "Clinical Diagnostics",
        "existing": [
            ("What is the difference between diagnostic sensitivity and specificity?",
             "Diagnostic sensitivity measures a test's ability to correctly identify individuals who have the disease (true positive rate). Specificity measures the ability to correctly identify those without the disease (true negative rate). A highly sensitive test minimizes false negatives (good for screening), while a highly specific test minimizes false positives (important for confirmation). The best diagnostic assays balance both, typically aiming for >95% in each metric. VigyanLLM's primer design pipeline helps optimize assay specificity through BLAST-based off-target detection."),
            ("What are the main types of molecular diagnostic tests?",
             "Major molecular diagnostic test types include: (1) PCR-based tests (conventional PCR, qPCR, digital PCR) for nucleic acid detection and quantification, (2) NGS-based tests (targeted panels, whole-exome, whole-genome) for comprehensive genomic analysis, (3) microarray-based tests for copy number variation and gene expression profiling, (4) isothermal amplification tests (LAMP, RPA) for rapid point-of-care detection, (5) CRISPR-based diagnostics for portable pathogen detection, and (6) mass spectrometry-based tests for protein and metabolite biomarkers."),
            ("How does VigyanLLM support clinical diagnostics workflows?",
             "VigyanLLM supports clinical diagnostics through its validated primer design platform, which checks 24 parameters per primer pair including BLAST specificity against NCBI databases, SNP overlap detection, repeat masking, and multiplex compatibility. The platform generates audit-ready PDF reports suitable for regulatory documentation, making it valuable for clinical laboratories developing in-house molecular diagnostic assays under ISO 15189 or CAP accreditation."),
        ],
        "additional": [
            ("What molecular techniques are used in clinical diagnostics?",
             "Common techniques include PCR and qPCR for pathogen detection and gene expression, next-generation sequencing (NGS) for cancer panels and rare disease diagnosis, Sanger sequencing for single-gene confirmation, fluorescence in situ hybridization (FISH) for chromosomal abnormalities, microarray for copy number variation, and mass spectrometry for protein biomarker analysis."),
            ("What is the difference between diagnostic and screening tests?",
             "Diagnostic tests confirm or rule out a specific disease in symptomatic individuals and typically have high accuracy (sensitivity and specificity > 99%). Screening tests identify apparently healthy individuals who may have a disease, prioritizing sensitivity over specificity to avoid false negatives. Positive screening results require diagnostic confirmation before clinical action."),
            ("How is PCR used in disease diagnosis?",
             "PCR detects pathogen DNA or RNA with high sensitivity and specificity. For infectious diseases, PCR can identify bacteria, viruses, and parasites directly from patient samples. Real-time PCR (qPCR) provides quantitative viral load data. Multiplex PCR detects multiple pathogens in a single reaction. PCR-based testing became central to global health during the COVID-19 pandemic as the standard for SARS-CoV-2 detection."),
            ("What is the role of biomarkers in clinical diagnostics?",
             "Biomarkers are measurable biological indicators of normal or disease states. They are used for screening (PSA for prostate cancer), diagnosis (troponin for heart attack), prognosis (HER2 in breast cancer), treatment selection (EGFR mutations for targeted therapy), and monitoring (HbA1c for diabetes). Valid biomarkers must have analytical validity, clinical validity, and clinical utility."),
            ("What are the regulatory requirements for diagnostic tests?",
             "Diagnostic tests must meet regulatory standards for safety and effectiveness. In India, the CDSCO regulates in-vitro diagnostics (IVDs). International standards include FDA approval (US), CE marking (EU), and ICMR guidelines. Tests are classified by risk: low-risk (general lab tests) to high-risk (HIV, cancer diagnostics). All require validation studies, quality control, and documentation."),
            ("How does next-generation sequencing (NGS) improve clinical diagnostics?",
             "NGS enables comprehensive genomic analysis from a single test, replacing multiple single-gene tests. It detects SNVs, indels, copy number variants, and structural variants simultaneously. Clinical applications include hereditary cancer panel testing, pharmacogenomics, non-invasive prenatal testing (NIPT), and liquid biopsy for circulating tumor DNA. NGS reduces time-to-diagnosis for rare genetic diseases."),
            ("What quality control measures are used in diagnostic laboratories?",
             "Laboratories implement internal quality control (running known positive and negative controls with each batch, monitoring assay performance over time) and external quality assessment (participating in proficiency testing programs). Standard operating procedures, staff training, equipment calibration, and chain-of-custody documentation are mandatory. Accredited labs follow ISO 15189 or CAP standards."),
        ],
    },
}


def build_faq_html(qa_pairs, first_open=False):
    """Build <details> HTML with itemscope/itemprop for a list of (question, answer) tuples."""
    parts = []
    for i, (q, a) in enumerate(qa_pairs):
        open_attr = ' open' if first_open and i == 0 else ''
        parts.append(f'''      <details class="faq-item"{open_attr}>
        <summary class="faq-question" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
          <span itemprop="name">{q}</span>
        </summary>
        <div class="faq-answer" itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
          <p itemprop="text">{a}</p>
        </div>
      </details>''')
    return '\n'.join(parts)


def build_jsonld(qa_pairs):
    """Build minified JSON-LD FAQPage string."""
    entries = []
    for q, a in qa_pairs:
        entries.append({
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": a
            }
        })
    obj = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entries
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def process_file(filepath):
    """Add FAQPage JSON-LD in head and expand inline FAQ to 10 items."""
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    filename = os.path.basename(filepath)
    data = FAQ_DATA[filename]
    all_qa = data["existing"] + data["additional"]

    # Build new FAQ section content (10 items)
    new_faq_content = build_faq_html(all_qa, first_open=True)

    # Replace the inline FAQ section
    # Pattern: <section class="section" id="faq"> ... </section>
    faq_section_pattern = re.compile(
        r'<section class="section" id="faq">.*?</section>',
        re.DOTALL
    )
    new_faq_section = f'''    <section class="section" id="faq">
      <h2>Frequently Asked Questions</h2>
      
{new_faq_content}
    </section>'''

    html = faq_section_pattern.sub(new_faq_section, html)

    # Build JSON-LD script
    jsonld_str = build_jsonld(all_qa)
    jsonld_html = f'  <script type="application/ld+json">{jsonld_str}</script>'

    # Insert JSON-LD after <!-- JSON-LD: RelatedTopic -->
    html = html.replace(
        '  <!-- JSON-LD: RelatedTopic -->',
        f'  <!-- JSON-LD: RelatedTopic -->\n{jsonld_html}'
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    # Count FAQ items
    detail_count = html.count('<details class="faq-item"')
    return detail_count


def main():
    targets = [
        "pcr.html", "crispr.html", "bioinformatics.html", "genomics.html",
        "dna.html", "rna.html", "primer.html", "gene-expression.html",
        "molecular-biology.html", "clinical-diagnostics.html"
    ]

    results = []
    for t in targets:
        path = os.path.join(GLOSSARY_DIR, t)
        if not os.path.exists(path):
            results.append((t, "MISSING", 0))
            continue
        cnt = process_file(path)
        results.append((t, "OK", cnt))

    print("=" * 60)
    print(f"{'PAGE':35s} {'STATUS':10s} {'FAQ COUNT':10s}")
    print("=" * 60)
    for page, status, count in results:
        print(f"{page:35s} {status:10s} {count:d}")
    print("=" * 60)


if __name__ == "__main__":
    main()
