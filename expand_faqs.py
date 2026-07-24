import re, os

BLOG_DIR = "/Users/macbookpro/Desktop/vigyanpilot/frontend/blog"

def make_inline_item(q, a):
    return f'        <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question" style="margin-bottom:16px">\n          <h3 itemprop="name">{q}</h3>\n          <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n            <p itemprop="text" style="color:#475569">{a}</p>\n          </div>\n        </div>'

def make_jsonld_item(q, a):
    return f'{{"@type":"Question","name":"{q}","acceptedAnswer":{{"@type":"Answer","text":"{a}"}}}}'

def make_inline_section(items):
    lines = ['      <div itemscope itemtype="https://schema.org/FAQPage">']
    for q, a in items:
        lines.append(make_inline_item(q, a))
    lines.append('      </div>')
    return '\n'.join(lines)

def make_jsonld_line(items):
    entities = ','.join(make_jsonld_item(q, a) for q, a in items)
    return f'<script type="application/ld+json">{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{entities}]}}</script>'

PAGES = {

    "amplicon-sequencing-guide.html": {
        "keep": [
            ("What is amplicon sequencing?", "Amplicon sequencing is a targeted next-generation sequencing method that uses PCR to amplify specific genomic regions before sequencing. It enriches target regions by multiplex PCR, enabling deep sequencing of selected loci at lower cost than whole-genome sequencing."),
            ("What is the difference between amplicon sequencing and whole-genome sequencing?", "Amplicon sequencing targets specific genomic regions by PCR, while WGS sequences the entire genome. Amplicon sequencing is cheaper, faster, and achieves higher depth (1000x+) on target regions but only covers preselected loci. WGS provides unbiased coverage of the entire genome at lower depth (30x typical)."),
            ("How do you design primers for amplicon sequencing panels?", "Primers for amplicon sequencing should have Tm 58-62\u00b0C, amplicon size 150-300 bp for Illumina or 200-1000 bp for Ion Torrent, minimal cross-dimerization between primer pairs, and uniform Tm across the panel. Primers should span exon-exon junctions for RNA targets."),
            ("What is amplicon sequencing used for?", "Amplicon sequencing is used for 16S rRNA metagenomics (microbiome analysis), targeted cancer gene panels, inherited disease mutation screening, viral whole-genome sequencing, HLA typing, and liquid biopsy ctDNA detection."),
            ("What is the difference between amplicon and capture-based sequencing?", "Amplicon sequencing uses PCR to amplify target regions with primers. Capture-based sequencing uses hybridization probes to enrich targets from a DNA library. Amplicon is faster and cheaper but prone to PCR bias and allele dropout. Capture provides more uniform coverage and can target larger regions (up to 100 Mb)."),
            ("What are the limitations of amplicon sequencing?", "Key limitations include PCR bias (GC-rich regions may underamplify), allele dropout from primer-binding site mismatches, limited target region size compared to capture-based methods, primer-dimer artefacts, and inability to detect structural variants or repeat expansions."),
        ],
        "add": [
            ("What depth should I target for amplicon sequencing?", "The required depth depends on the application: 500-1000x for SNV detection in solid tumors, 5000x+ for ctDNA liquid biopsy, and 10000x+ for rare variant detection below 1% allele frequency. Higher depth improves sensitivity but increases cost. Most amplicon panels achieve 500-2000x mean depth across targeted regions."),
            ("How long are typical amplicon sequencing reads?", "For Illumina platforms, amplicon size is typically 150-300 bp with paired-end reads of 150-300 bp. For Ion Torrent, amplicons range from 200-1000 bp. The amplicon size must match the sequencing platform's read length capability, and overlapping paired-end reads improve variant calling accuracy."),
            ("Can amplicon sequencing detect structural variants?", "Amplicon sequencing has limited capability for structural variant detection because PCR amplification destroys breakpoint information. Structural variants, copy number changes, and repeat expansions are better detected by whole-genome sequencing or specific capture-based methods designed for SV detection."),
            ("What is PCR bias in amplicon sequencing?", "PCR bias occurs when certain amplicons amplify more efficiently than others due to GC content, secondary structure, or primer efficiency differences. This leads to uneven coverage across targets. GC-rich regions typically underamplify, while GC-balanced regions amplify well. Multiplex PCR optimization and unique molecular identifiers (UMIs) help reduce bias."),
            ("How do I design a multiplex amplicon panel?", "Design primers with uniform Tm (58-62\u00b0C), amplicon sizes within a narrow range (150-200 bp for Illumina), minimal cross-dimerization, and no stable secondary structures. Use primer design software with multiplex compatibility checking. Test primer pools in small batches before full panel assembly."),
            ("What is the role of UMIs in amplicon sequencing?", "Unique Molecular Identifiers (UMIs) are random oligonucleotide barcodes attached to each DNA molecule before PCR amplification. UMIs allow bioinformatic removal of PCR duplicates and polymerase errors by grouping reads with the same UMI. This significantly improves variant detection accuracy, especially for low-frequency variants below 5% allele frequency."),
        ],
    },

    "rt-pcr-complete-guide.html": {
        "keep": [
            ("What is RT-PCR used for?", "RT-PCR is used for gene expression analysis (quantifying mRNA levels), viral RNA detection (including SARS-CoV-2, HIV, hepatitis viruses), cancer biomarker detection, microRNA analysis, and single-cell transcriptomics."),
            ("What is the difference between RT-PCR and qPCR?", "RT-PCR converts RNA to cDNA and amplifies it for detection. qPCR measures DNA amplification in real time using fluorescent probes. RT-qPCR combines both."),
            ("How do you design primers for RT-PCR?", "RT-PCR primers should span exon-exon junctions to avoid genomic DNA amplification. Amplicon size: 70-150 bp for qPCR, 200-1000 bp for standard RT-PCR. Primer Tm should be 58-62\u00b0C with less than 2\u00b0C difference between forward and reverse primers."),
            ("Why is my RT-PCR not working?", "Common causes: degraded RNA (most common), inactive reverse transcriptase, genomic DNA contamination, incorrect primer design, or suboptimal annealing temperature. Use RNA integrity checks and DNase treatment."),
            ("What is the difference between one-step and two-step RT-PCR?", "In one-step RT-PCR, reverse transcription and PCR occur in a single tube with combined enzymes, reducing contamination risk. In two-step RT-PCR, cDNA synthesis is performed separately, allowing the same cDNA to be used for multiple target assays."),
        ],
        "add": [
            ("What is the best RNA extraction method for RT-PCR?", "Column-based silica membrane kits (like Qiagen RNeasy) give the purest RNA with minimal DNA contamination. TRIzol-based extraction yields higher quantity but may leave phenol traces. For low-input samples, magnetic bead-based methods work well. Always include DNase treatment to remove genomic DNA contamination."),
            ("How do I prevent genomic DNA contamination in RT-PCR?", "Design primers that span exon-exon junctions so they cannot amplify genomic DNA. Treat RNA samples with DNase I before reverse transcription. Include a no-reverse-transcriptase control (no-RT control) in every experiment to check for gDNA contamination. Use intron-spanning primers when possible."),
            ("What is the optimal annealing temperature for RT-PCR?", "The optimal annealing temperature is typically 3-5\u00b0C below the lower primer Tm, usually 55-60\u00b0C for standard RT-PCR. For qPCR, use 60\u00b0C with a two-step cycling protocol (annealing and extension at same temperature). Perform a temperature gradient PCR to find the optimal Ta for your specific primer pair."),
            ("How do I choose between SYBR Green and TaqMan for RT-qPCR?", "SYBR Green is cheaper and simpler -- it binds any double-stranded DNA, requiring melt curve analysis for specificity verification. TaqMan probes are more specific (hybridization probe required) and allow multiplexing with different fluorophores. For gene expression panels with many targets, SYBR Green is often preferred for its lower cost."),
            ("What controls should I include in RT-PCR experiments?", "Include a no-template control (NTC) to check reagent contamination, a no-reverse-transcriptase control (no-RT) to check gDNA contamination, a positive control with known expression, and reference genes (housekeeping genes like GAPDH, ACTB, or 18S rRNA) for normalization. For qPCR, include a standard curve for absolute quantification."),
            ("How do I analyze RT-qPCR data?", "Use the delta-delta-Ct (\u0394\u0394Ct) method for relative quantification after confirming similar amplification efficiencies between target and reference genes. Normalize target Ct values to reference gene Ct values, then compare to a calibrator sample. For absolute quantification, use a standard curve with known template concentrations."),
            ("What causes high Ct values in RT-qPCR?", "High Ct values indicate low target abundance. Common causes: degraded RNA template (check RNA integrity), inefficient reverse transcription (verify enzyme activity and incubation conditions), suboptimal primer design (check Tm and secondary structure), or too little input RNA. For low-expression targets, increase cDNA input or use preamplification."),
        ],
    },

    "variant-calling-guide.html": {
        "keep": [
            ("What is variant calling in bioinformatics?", "Variant calling is the process of identifying differences between a sample genome and a reference genome from next-generation sequencing (NGS) data. It detects single nucleotide variants (SNVs), insertions, deletions (indels), and structural variants. Tools like GATK HaplotypeCaller, FreeBayes, and DeepVariant compare aligned reads to a reference to identify genomic variations."),
            ("What is the difference between SNVs, indels, and structural variants?", "SNVs (single nucleotide variants) are changes to a single base pair, such as A to G. Indels are small insertions or deletions of 1-50 base pairs. Structural variants are larger rearrangements involving 50+ base pairs, including duplications, inversions, translocations, and copy number variations. Each type requires different detection algorithms."),
            ("What tools are used for variant calling?", "GATK HaplotypeCaller is the most widely used tool for germline variant calling and is the industry standard for clinical genomics. FreeBayes is a popular open-source alternative for haplotype-based calling. DeepVariant uses deep learning for variant detection. For somatic variants, Mutect2 (GATK) and VarScan2 are commonly used. Strelka2 handles both germline and somatic calling."),
            ("What is VCF format and how is it used in variant calling?", "VCF (Variant Call Format) is the standard file format for storing variant calls. It contains a header section with metadata (reference genome, caller info, filter descriptions) and a data section with tab-delimited columns: CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, and FORMAT plus sample genotypes. VCF files can be compressed to .vcf.gz and indexed with .tbi for efficient querying."),
            ("How much sequencing depth is needed for accurate variant calling?", "For germline variant calling, 30x coverage is considered the minimum standard for whole-genome sequencing. Clinical applications typically require 60-100x for reliable heterozygous variant detection. For somatic variant calling in cancer, 200x or higher tumor coverage is recommended due to tumor heterogeneity and contamination with normal cells."),
            ("What is the GATK Best Practices pipeline?", "The GATK Best Practices pipeline is a step-by-step workflow for variant calling developed by the Broad Institute. Key steps include: BWA-MEM alignment to reference, MarkDuplicates to remove PCR duplicates, Base Quality Score Recalibration (BQSR), HaplotypeCaller for variant calling, Variant Quality Score Recalibration (VQSR) for filtering, and joint genotyping for multi-sample analysis."),
        ],
        "add": [
            ("What is variant allele frequency (VAF)?", "Variant allele frequency is the proportion of sequencing reads supporting a variant allele divided by total reads at that position. A VAF of 50% suggests a heterozygous germline variant, while low VAF (1-5%) indicates a somatic or subclonal variant. The minimum VAF detectable depends on sequencing depth and base quality."),
            ("How do I filter false-positive variant calls?", "Filter variants by read depth (min 20x for germline, min 100x for somatic), base quality (min Q20), mapping quality (min 30), strand bias (Fisher test p > 0.05), and variant allele frequency. Remove variants in homopolymer runs and repetitive regions. Use population frequency databases (gnomAD) to filter common polymorphisms."),
            ("What is the difference between SNPs and indels in variant calling?", "Single nucleotide polymorphisms (SNPs) change one base and are easier to call accurately. Insertions and deletions (indels) are harder to call because they require realignment around the variant site. GATK's HaplotypeCaller uses local de novo assembly to improve indel calling, but indels still have higher false-positive and false-negative rates than SNPs."),
            ("How do I call variants from RNA-seq data?", "RNA-seq variant calling requires a splice-aware aligner (STAR or HISAT2) to handle exon-exon junctions. Use GATK's HaplotypeCaller in RNA-seq mode which accounts for splicing. Filter variants in splice sites and consider allele-specific expression bias. RNA-seq variant calling is less sensitive than DNA-seq due to expression level variation."),
            ("What is the importance of panel of normals (PoN) in somatic calling?", "A Panel of Normals (PoN) is a collection of sequencing data from normal samples that captures systematic sequencing artifacts and recurrent false positives. Using a PoN with Mutect2 dramatically reduces false-positive somatic calls by modeling site-specific error rates. Build a PoN from at least 30 normal samples processed identically to your tumor samples."),
        ],
    },

    "primer-design-basics.html": {
        "keep": [
            ("What are the basic principles of primer design?", "The core principles of primer design include: length of 18-25 nucleotides, melting temperature (Tm) of 55-65\u00b0C with less than 5\u00b0C difference between primer pairs, GC content of 40-60%, avoidance of self-complementarity and primer-dimer formation, and a GC clamp (2-3 G or C bases) at the 3\u2032 end for stable annealing."),
            ("What is the ideal melting temperature for PCR primers?", "The ideal Tm for standard PCR primers is 58-62\u00b0C. Both primers in a pair should have Tm values within 2-3\u00b0C of each other. For qPCR, tighter Tm matching (within 1\u00b0C) is recommended. The nearest-neighbor thermodynamic model provides the most accurate Tm calculation compared to the basic 4+2(G+C) rule."),
            ("How do I avoid primer dimers?", "To avoid primer dimers: check for complementary regions at the 3\u2032 ends of primers (especially the last 4-5 bases), avoid runs of identical nucleotides, limit GC content to 40-60%, use a primer design tool that screens for self-complementarity and cross-dimer potential, and keep primer concentration low in the reaction (200-500 nM)."),
            ("What is the difference between forward and reverse primers?", "Forward primers bind to the antisense (complementary) strand of DNA at the 5\u2032 end of the target region and extend in the 3\u2032 to 5\u2032 direction along the sense strand. Reverse primers bind to the sense strand at the 3\u2032 end of the target and extend in the opposite direction. Together, they define the amplicon boundaries."),
            ("Can I design primers for qPCR the same way as standard PCR?", "qPCR primers require tighter specifications: amplicon length should be shorter (80-200 bp for optimal efficiency), Tm matching between primers should be within 1\u00b0C, and you must avoid secondary structures that could interfere with probe binding. Additionally, qPCR often uses TaqMan probes which require their own design considerations including no G at the 5\u2032 end."),
            ("What tools can I use to design primers online for free?", "VigyanLLM offers free primer design with 24-step biophysical validation in the browser. NCBI Primer-BLAST integrates primer design with database specificity checking. Primer3Plus provides a web interface for the Primer3 engine. IDT's PrimerQuest is free for basic design. Benchling also includes primer design in its free tier."),
        ],
        "add": [
            ("What is the 3-prime GC clamp and why does it matter?", "A GC clamp is the presence of one or two G or C bases in the last 5 bases at the 3-prime end of a primer. It improves amplification specificity by requiring stronger binding at the extension start site. Without a GC clamp, AT-rich 3-prime ends may cause mispriming and non-specific amplification. Most good primer design tools automatically enforce this."),
            ("How do I design primers for GC-rich templates?", "For GC-rich templates (above 65% GC), increase primer length to 25-30 nt, use higher annealing temperatures (60-65\u00b0C), and add PCR enhancers like DMSO (3-5%) or betaine. Avoid long GC stretches in the primer itself. Design primers in less GC-rich flanking regions when possible."),
            ("What is the difference between degenerate and specific primers?", "Specific primers have a single defined sequence that matches exactly one target. Degenerate primers contain mixed bases (IUPAC codes like R, Y, N) at positions where the target sequence varies across species or alleles. Degenerate primers are used for cross-species PCR, viral quasispecies detection, and conserved region amplification but have lower efficiency."),
            ("How do I check primer specificity before ordering?", "BLAST your primer sequence against the target genome and related genomes using NCBI Primer-BLAST. Check that both forward and reverse primers have unique matches to the intended target. Avoid primers with significant homology to off-target sites, especially at the 3-prime end."),
            ("What amplicon size should I target for different PCR applications?", "For standard PCR: 300-1000 bp. For qPCR/SYBR Green: 70-200 bp. For TaqMan qPCR: 50-150 bp. For Sanger sequencing: 400-700 bp. For NGS amplicon panels: 150-300 bp (Illumina) or 200-1000 bp (Ion Torrent). Shorter amplicons amplify more efficiently and are preferred for quantitative applications."),
            ("How do I design primers for allele-specific PCR?", "For allele-specific PCR, place the variant base at the 3-prime end of one primer where DNA polymerase is most discriminatory. Add an intentional mismatch at position -2 or -3 from the 3-prime end to further reduce amplification of the non-target allele. Optimize annealing temperature carefully since allele specificity is highly temperature-sensitive."),
        ],
    },

    "molecular-docking-tutorial.html": {
        "keep": [
            ("What is molecular docking and how does it work?", "Molecular docking is a computational technique that predicts the preferred orientation and binding affinity of a small molecule (ligand) when bound to a macromolecular target (usually a protein). It works by exploring the conformational space of the ligand within the protein's binding site, scoring each pose using energy-based scoring functions that estimate binding free energy."),
            ("What software is best for molecular docking?", "AutoDock Vina is the most widely used free docking software, offering good accuracy and speed. SwissDock provides a user-friendly web interface for beginners. VigyanLLM offers GPU-accelerated consensus docking online. For advanced users, GOLD, Glide, and HADDOCK provide additional scoring functions and flexibility modeling."),
            ("How do you interpret docking scores?", "Docking scores are typically reported as negative values in kcal/mol, where more negative scores indicate stronger predicted binding. A score below -7.0 kcal/mol generally suggests good binding affinity, though thresholds vary by scoring function. Scores should be compared relative to known binders rather than taken as absolute values."),
            ("What file formats are needed for molecular docking?", "The protein receptor is typically prepared in PDB format, with water molecules and unwanted ligands removed. The ligand is prepared in PDB, MOL2, or SDF format. AutoDock Vina also requires PDBQT format for both receptor and ligand, which can be generated using Open Babel or AutoDockTools."),
            ("What are the limitations of molecular docking?", "Key limitations include: protein flexibility is often simplified (most methods use a rigid receptor), scoring functions are approximations that may not capture all interaction types, solvation effects are modeled simplistically, and docking does not predict actual binding kinetics (on/off rates). Results should always be validated experimentally."),
            ("Can I run molecular docking online for free?", "Yes. VigyanLLM offers free GPU-accelerated molecular docking directly in the browser with no account required. SwissDock provides free web-based docking using the EADock DSS engine. Other free options include HDOCK for protein-protein docking and the CB-Dock2 web server for cavity detection and blind docking."),
        ],
        "add": [
            ("What file formats are needed for molecular docking?", "Protein structures should be in PDB format (from X-ray crystallography or cryo-EM) or PDBQT format (with added hydrogens and charges). Ligands should be in SDF, MOL2, or PDB format. VigyanLLM's docking pipeline accepts PDB and FASTA for proteins and SDF, MOL2, SMILES for ligands, with automatic format conversion."),
            ("How do I select the binding site for docking?", "Use known active site residues from literature or co-crystal structures when available. For blind docking (unknown binding site), set the grid box to cover the entire protein surface. The search space should be large enough to include all possible binding pockets but small enough to maintain computational efficiency. A box size of 20-30 angstroms is typical for known binding sites."),
            ("What exhaustiveness setting should I use for docking?", "Exhaustiveness controls how thoroughly the docking algorithm searches for binding poses. For quick screening of many compounds, use exhaustiveness of 8-16. For final validation of top hits, use exhaustiveness of 32-64. Higher exhaustiveness increases run time linearly but improves reproducibility of results."),
            ("How do I validate docking results with known compounds?", "The best validation is redocking: remove the co-crystallized ligand from a protein structure and dock it back. The top predicted pose should match the experimental pose with RMSD below 2 angstroms. You can also dock known active and inactive compounds to check that your protocol correctly ranks active compounds higher (enrichment factor calculation)."),
            ("What is the difference between pose prediction and virtual screening?", "Pose prediction focuses on accurately predicting how a specific ligand binds to a target (binding mode and orientation). Virtual screening applies docking to large compound libraries to identify which molecules are most likely to bind. Both use the same docking algorithms but virtual screening emphasizes speed and ranking accuracy over exact pose prediction."),
            ("How do scoring functions rank docking results?", "Scoring functions estimate binding free energy (\u0394G) by summing contributions from van der Waals interactions, electrostatic forces, hydrogen bonding, desolvation, and entropy loss. More negative scores indicate stronger predicted binding. Consensus scoring (averaging scores from multiple functions) improves reliability by reducing individual scoring function biases."),
        ],
    },

    "top-10-free-bioinformatics-tools.html": {
        "keep": [
            ("What are the best free bioinformatics tools in 2026?", "The top free bioinformatics tools in 2026 include VigyanLLM for primer design, NCBI BLAST for sequence similarity search, Clustal Omega for multiple sequence alignment, AutoDock Vina for molecular docking, BioPython for scripting, and Benchling for molecular biology project management. Each excels in a specific research workflow step."),
            ("Which bioinformatics tool is best for beginners?", "For beginners, NCBI BLAST is the most accessible starting point for sequence analysis. VigyanLLM's suite of tools requires no installation and runs entirely in the browser, making it ideal for students. Benchling provides an intuitive visual interface for DNA sequence design. Clustal Omega's web interface is also beginner-friendly for sequence alignment."),
            ("Are free bioinformatics tools reliable for published research?", "Yes. Many free tools are widely cited in peer-reviewed publications. NCBI BLAST, Clustal Omega, and AutoDock Vina each have thousands of citations. VigyanLLM uses validated thermodynamic models for primer design. The key is to understand each tool's methodology and limitations, and to validate critical results experimentally."),
            ("What is the difference between VigyanLLM and Primer3?", "Primer3 is a command-line primer design engine that requires technical setup. VigyanLLM builds on similar principles but adds a browser-based interface, 24-step biophysical validation, built-in BLAST verification, multiplex primer design, qPCR probe design, and visual primer mapping without requiring installation or command-line knowledge."),
            ("Can I use these tools without programming knowledge?", "Most tools on this list offer web-based interfaces that require no programming. VigyanLLM, NCBI BLAST, Clustal Omega, SwissDock, and Benchling all run in the browser. BioPython is the exception -- it requires Python programming but is the most flexible option for automating repetitive bioinformatics analyses."),
            ("How do these bioinformatics tools work together in a research workflow?", "A typical workflow starts with BLAST to identify homologous sequences, followed by Clustal Omega for multiple sequence alignment and phylogenetic analysis. VigyanLLM designs primers for the target region, which are then used in PCR experiments. For drug discovery, AutoDock Vina or VigyanLLM docking screens compound libraries against protein targets."),
        ],
        "add": [
            ("What is the best free primer design tool?", "VigyanLLM Primer offers free 24-step validated primer design with BLAST specificity checking, secondary structure analysis, and SNP filtering. Primer3 is another excellent free option for basic primer design. Primer-BLAST (NCBI) combines primer design with BLAST specificity checking. For advanced qPCR design, IDT's PrimerQuest has free online access."),
            ("What free tools are available for protein structure prediction?", "The top free tools include AlphaFold2/3 (DeepMind) with the EBI server for academic users, ESMFold (Meta) for rapid structure prediction, and RoseTTAFold (Baker lab) for complex prediction tasks. Docking can be performed with AutoDock Vina (free, open-source) or GNINA (free for academic use with deep learning scoring)."),
            ("Are there free alternatives to SnapGene?", "Benchling offers a free cloud-based molecular biology platform with plasmid mapping, primer design, and sequence alignment. UGENE is a free, open-source desktop alternative with comprehensive sequence analysis tools. SnapGene Viewer is free for viewing and sharing annotated sequences (but editing requires a paid license)."),
            ("What free tools help with CRISPR guide RNA design?", "CRISPick (Broad Institute) provides free gRNA design with Doench 2016/2019 scoring. CHOPCHOP offers an intuitive web interface for gRNA design across multiple species. CRISPRdirect is a simple tool for SpCas9 gRNA design. Benchling's free tier includes CRISPR design with off-target scoring."),
            ("Which free alignment tools support large sequence datasets?", "Clustal Omega (EBI) aligns up to 10,000 sequences for free. MAFFT is excellent for large alignments with its FFT-NS-2 algorithm. MUSCLE is fast and accurate for medium datasets. For extremely large datasets (100K+ sequences), use the MAFFT or Clustal Omega command-line versions on your own hardware."),
            ("How do I choose between free and paid bioinformatics tools?", "Free tools are excellent for academic research, teaching, and occasional use. Choose paid tools when you need: (1) integrated workflows (primer design + BLAST + validation in one interface), (2) batch processing for high-throughput projects, (3) audit-ready reports for regulated environments, or (4) guaranteed uptime and support for production pipelines."),
        ],
    },

    "qpcr-primer-probe-design.html": {
        "keep": [
            ("What is the difference between SYBR Green and TaqMan qPCR?", "SYBR Green binds any double-stranded DNA, detecting all amplification products including non-specific ones and primer dimers. TaqMan probes are sequence-specific, generating signal only when the target sequence is amplified, providing higher specificity. SYBR Green is cheaper and simpler; TaqMan is more specific and enables multiplexing with multiple fluorophores."),
            ("What is the optimal amplicon size for qPCR?", "The optimal amplicon size for qPCR is 80-200 bp, with 100-150 bp as the sweet spot. Shorter amplicons amplify more efficiently due to the limited extension time in each cycle, but must be long enough to design specific primers and probes."),
            ("How do I choose between SYBR Green and TaqMan for my qPCR assay?", "Choose SYBR Green when: you are measuring a single target per reaction, have validated primers, or are screening many targets cost-effectively. Choose TaqMan when: you need multiplexing (multiple targets per reaction), require maximum specificity, are working with low-abundance targets, or need consistent results across many samples."),
            ("Why should TaqMan probes have a Tm 5-10\u00b0C higher than primers?", "A higher Tm ensures the probe remains stably bound to the target during primer annealing and extension, while being efficiently displaced by Taq polymerase during polymerization. This maintains the fluorescence signal generation mechanism and prevents the probe from competing with primers for binding."),
            ("What are the MIQE guidelines for qPCR?", "The MIQE (Minimum Information for Publication of Quantitative Real-Time PCR Experiments) guidelines established by Bustin et al. (2009) set standards for qPCR experimental design, including: reporting primer sequences, validation of reference genes, showing amplification efficiency (90-110%), standard curve data, and melt curve analysis. Following MIQE guidelines is essential for publication in peer-reviewed journals."),
            ("How do I design primers for multiplex qPCR?", "For multiplex qPCR, ensure all primer pairs have Tm within 2\u00b0C of each other, use probes with spectrally distinct fluorophores (FAM, VIC, ROX, Cy5), check all primer-probe combinations for cross-dimerization, and optimize individual primer concentrations before combining in the multiplex reaction."),
        ],
        "add": [
            ("What is the ideal amplicon size for qPCR?", "The ideal qPCR amplicon size is 70-150 bp. Short amplicons amplify more efficiently, require less extension time, and produce more consistent results across different master mixes. For SYBR Green assays, amplicons up to 200 bp are acceptable. For TaqMan probe assays, keep amplicons between 50-150 bp for optimal probe hydrolysis efficiency."),
            ("How do I design TaqMan probes for qPCR?", "TaqMan probes should be 18-25 nt long with Tm 5-10\u00b0C above the primer Tm (65-70\u00b0C). Avoid a G at the 5-prime end (quenches reporter fluorescence). Place the probe within 50 bp of the forward primer, spanning an exon-exon junction for RNA targets. Use the minor groove binder (MGB) modification for shorter, more specific probes."),
            ("What is the difference between SYBR Green and TaqMan chemistry?", "SYBR Green binds any double-stranded DNA, detecting all amplified products including primer-dimers and non-specific amplicons. It requires melt curve analysis for specificity verification. TaqMan uses a sequence-specific probe that fluoresces only when hydrolyzed during extension, providing higher specificity and enabling multiplex detection with different fluorophores."),
            ("How do I optimize qPCR primer concentration?", "Start with 200-500 nM of each primer. Too little primer reduces amplification efficiency; too much promotes primer-dimer formation. For SYBR Green assays, perform a primer concentration matrix (50-900 nM) to find the minimum concentration that gives the lowest Ct without primer-dimer. For TaqMan, use 300-500 nM primers and 200-250 nM probe."),
            ("What reference genes should I use for qPCR normalization?", "Common reference genes include GAPDH (moderate expression), ACTB/beta-actin (high expression), 18S rRNA (very high, may not reflect mRNA), B2M, HPRT1, and TBP (low-moderate expression). The ideal reference gene should have stable expression across your experimental conditions. Test 3-5 candidates and use geNorm or NormFinder to select the most stable one."),
            ("How do I calculate qPCR amplification efficiency?", "Amplification efficiency is calculated from a standard curve using serial dilutions of template (typically 5-fold). Plot Ct vs log template concentration: efficiency = 10^(-1/slope) - 1. Perfect efficiency is 100% (slope = -3.32). Acceptable efficiency is 90-110% (slope -3.6 to -3.1). Low efficiency indicates suboptimal primers or inhibitors. Report efficiency for each primer pair."),
        ],
    },

    "primer3-vs-vigyanllm.html": {
        "keep": [
            ("Which tool is better for PCR primer design: Primer3 or VigyanLLM?", "Primer3 is excellent for basic offline primer design and pipeline integration. VigyanLLM adds built-in specificity checking, multiplex compatibility analysis, visual primer mapping, and automated PCR protocol recommendations on top of Primer3's proven thermodynamic engine. For one-off simple designs, both work well. For complex workflows, VigyanLLM provides comprehensive validation."),
            ("Is Primer3 accurate enough for clinical PCR applications?", "Primer3's thermodynamic model is scientifically sound, but it lacks the built-in specificity checking, documentation, and regulatory features required for clinical workflows. VigyanLLM adds these as an integrated layer on top of Primer3's design engine."),
            ("Does VigyanLLM use Primer3 under the hood?", "Yes, VigyanLLM Primer uses a Primer3-compatible nearest-neighbor algorithm as its core thermodynamic engine, augmented with extended validation parameters and comprehensive post-design checks that go beyond Primer3's default capabilities."),
            ("Which tool is better for Indian research labs?", "Primer3 is free and excellent for basic needs. VigyanLLM adds India-specific advantages: INR pricing, on-premise deployment for DPDP Act compliance, free academic tiers, and support for regionally relevant pathogen genomes."),
            ("Can I use Primer3 offline?", "Yes, Primer3 is a command-line tool that runs entirely offline. It is available as source code that you can compile and run on any Linux, macOS, or Windows system without internet access."),
            ("Does VigyanLLM support batch primer design for multiple targets?", "Yes, VigyanLLM Primer supports batch design for up to 100 targets simultaneously. Each primer pair undergoes the full 24-step validation pipeline, including BLAST specificity checking, SNP screening, and multiplex compatibility scoring."),
            ("How do the costs compare between Primer3 and VigyanLLM?", "Primer3 is completely free open-source software. VigyanLLM Primer is also free for academic researchers. For commercial use, VigyanLLM offers paid tiers with enterprise features including priority support, audit-ready PDF reports, and on-premise deployment."),
            ("Can I export VigyanLLM primer designs for use in the lab?", "Yes, VigyanLLM Primer generates detailed PDF reports with all primer parameters (Tm, GC content, amplicon size), PCR protocol recommendations, and ordering-ready sequences. Primers can also be exported in CSV format for LIMS integration."),
        ],
        "add": [
            ("Can VigyanLLM be used as a Primer3 alternative?", "Yes, VigyanLLM is a comprehensive alternative that uses Primer3 as its core engine and adds 18 additional validation steps. It offers a web-based GUI, automated BLAST integration, batch processing, and PDF audit reports. For researchers who need more than basic primer candidates from a command-line tool, VigyanLLM provides a complete workflow."),
            ("Which tool supports better degenerate primer design?", "Both Primer3 and VigyanLLM support degenerate primers with IUPAC codes. VigyanLLM provides additional coverage analysis for degenerate pools, thermodynamic calculations accounting for mixed bases, and multiplex compatibility scoring across multiple degenerate primer pairs -- features not available in command-line Primer3 alone."),
        ],
    },
}

# For amplicon-sequencing-guide: 6 keep + 6 add = 12 (already correct)
# For rt-pcr-complete-guide: 5 keep + 7 add = 12 (already correct)
# For variant-calling-guide: 6 keep + 5 add = 11. Need one more unique question.
# For primer-design-basics: 6 keep + 6 add = 12 (correct)
# For molecular-docking-tutorial: 6 keep + 6 add = 12. But Q4 (file formats) appears in both keep and add. Need to handle.
# For top-10-free-bioinformatics-tools: 6 keep + 6 add = 12 (correct)
# For qpcr-primer-probe-design: 6 keep + 6 add = 12 (correct)
# For primer3-vs-vigyanllm: 8 keep + 2 add = 10 (correct)

# Fix variant-calling-guide: add a 6th unique question to reach 12 total
PAGES["variant-calling-guide.html"]["add"].append(
    ("What is the difference between germline and somatic variant calling?", "Germline variant calling detects inherited variants present in all cells, typically using paired normal samples and requiring 30-100x depth. Somatic variant calling identifies mutations present only in tumor or diseased cells, requiring matched normal-tumor pairs and higher depth (200x+) to distinguish true somatic variants from sequencing noise and germline polymorphisms.")
)

# Fix molecular-docking-tutorial: Q4 "What file formats are needed for molecular docking?" appears in both keep and add.
# Rename the keep version to keep it, and rename the add version
# Actually, looking at the two questions more carefully:
# Keep Q4: "What file formats are needed for molecular docking?" - answer about PDB, MOL2, SDF, PDBQT
# Add Q7: "What file formats are needed for molecular docking?" - answer about PDB, PDBQT, SDF, MOL2, FASTA, SMILES
# These are essentially the same question with slightly different answers. I'll keep the existing and replace the add version with a different question.
PAGES["molecular-docking-tutorial.html"]["add"][0] = (
    "How do I prepare a protein structure for docking?", "Prepare the protein by: (1) removing water molecules and co-factors unless they are critical for ligand binding, (2) adding hydrogens at the correct pH (typically 7.4), (3) assigning atom types and charges, (4) repairing missing side chains and loops, and (5) optimizing hydrogen bond networks. Tools like AutoDockTools, PyMOL, and Chimera can automate protein preparation.")
# That's 6 keep + 6 add = 12, but Q4 in keep and Q7 now are different questions. Good.

# Handle rt-pcr: keep has "How to Perform RT-PCR" which is NOT in the user's keep list. Let me check...
# Actually the user's keep list for rt-pcr is: "What is RT-PCR used for?", "What is the difference between RT-PCR and qPCR?", "How do you design primers for RT-PCR?", "Why is my RT-PCR not working?", "What is the difference between one-step and two-step RT-PCR?"
# But the actual file also has: "How to Perform RT-PCR (Reverse Transcription PCR)", "RNA Extraction and Quality Control", "Reverse Transcription (cDNA Synthesis)", "PCR Amplification of cDNA"
# Looking at the JSON-LD output from the file, it only has 5 items. The extra 3 might be HowTo steps, not FAQ items.
# Let me check the inline section to be sure...

success = True
for filename, data in PAGES.items():
    filepath = os.path.join(BLOG_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR reading {filename}: {e}")
        success = False
        continue

    all_items = data["keep"] + data["add"]
    expected_count = 12 if filename != "primer3-vs-vigyanllm.html" else 10
    actual_count = len(all_items)

    if actual_count != expected_count:
        print(f"WARNING: {filename} has {actual_count} items but expected {expected_count}")
        # Continue anyway

    new_inline = make_inline_section(all_items)
    new_jsonld = make_jsonld_line(all_items)

    # ---- Replace JSON-LD FAQPage ----
    # Pattern: <script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage",...}</script>
    jsonld_pattern = r'<script type="application/ld\+json">\{"@context":"https://schema\.org","@type":"FAQPage","mainEntity":\[.*?\]\}</script>'
    match = re.search(jsonld_pattern, content, re.DOTALL)
    if match:
        content = content.replace(match.group(0), new_jsonld)
        print(f"OK {filename}: replaced JSON-LD ({actual_count} entries)")
    else:
        print(f"ERROR {filename}: could not find JSON-LD FAQPage pattern")
        success = False
        continue

    # ---- Replace/Insert Inline FAQ section ----
    inline_start_marker = '<div itemscope itemtype="https://schema.org/FAQPage">'
    faq_h2_pos = content.find('<h2>Frequently Asked Questions</h2>')
    if faq_h2_pos == -1:
        # No inline FAQ section exists — insert one before the References section
        ref_pos = content.find('<section class="references">')
        if ref_pos == -1:
            print(f"ERROR {filename}: could not find 'Frequently Asked Questions' heading or References section")
            success = False
            continue
        faq_html = f'\n      <h2>Frequently Asked Questions</h2>\n{new_inline}\n\n'
        content = content[:ref_pos] + faq_html + content[ref_pos:]
        print(f"OK {filename}: inserted inline FAQ ({actual_count} entries) before References")
    else:
        # Find the start of the FAQ div after the h2
        div_start = content.find(inline_start_marker, faq_h2_pos)
        if div_start == -1:
            print(f"ERROR {filename}: could not find inline FAQPage div")
            success = False
            continue

        # Find the matching closing </div> - track nesting
        pos = div_start + len(inline_start_marker)
        depth = 1
        while depth > 0 and pos < len(content):
            next_open = content.find('<div ', pos)
            next_close = content.find('</div>', pos)
            if next_close == -1:
                print(f"ERROR {filename}: unmatched div in FAQ section")
                success = False
                break
            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + 5
            else:
                depth -= 1
                pos = next_close + 6
        
        if depth == 0:
            div_end = pos
            old_inline = content[div_start:div_end]
            content = content.replace(old_inline, new_inline.strip())
            print(f"OK {filename}: replaced inline FAQ ({actual_count} entries)")
        else:
            print(f"ERROR {filename}: couldn't find closing div of FAQ section")
            success = False
            continue

    # Write back
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"OK {filename}: written back")
    except Exception as e:
        print(f"ERROR writing {filename}: {e}")
        success = False

if success:
    print("\nAll files updated successfully.")
else:
    print("\nSome errors occurred. Check above.")