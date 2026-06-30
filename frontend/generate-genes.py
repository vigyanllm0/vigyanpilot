#!/usr/bin/env python3
"""Generate gene-specific primer design pages for important human genes."""

import os

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gene-prefers")
os.makedirs(OUTPUT, exist_ok=True)

GENES = [
    # [symbol, full_name, chrom, gc%, mutations, desc1, desc2, exons_to_target, [challenges], [snps], [primer_pairs]]
    ["ALK", "Anaplastic Lymphoma Kinase", "2p23", "56%",
     "EML4-ALK fusions, L1196M, G1202R, C1156Y",
     "The ALK gene encodes a receptor tyrosine kinase involved in neuronal development and function.",
     "ALK rearrangements, particularly EML4-ALK fusions, are oncogenic drivers in non-small cell lung cancer requiring precise molecular detection.",
     "Exons 20\u201329 (kinase domain)",
     ["EML4-ALK fusion breakpoints: Variable fusion partners create diverse breakpoints requiring multiplexed primer design strategies",
      "GC-rich kinase domain: Exons 23\u201325 show elevated GC content (62\u201365%) requiring DMSO optimization",
      "Resistance mutation heterogeneity: Secondary mutations (L1196M, G1202R, C1156Y) cluster in the ATP-binding pocket requiring separate amplicons"],
     [["rs113994089", "L1196M", "Exon 23 resistance mutation in NSCLC"],
      ["rs1560310", "G1202R", "Solvent front mutation in exon 25"],
      ["rs1880509", "C1156Y", "Exon 22 activating mutation"]],
     [["Exon 22 (ALK-TKD)", "AGCAGTCAGAGTCAGCTCTGA", "CCAAATGCTTGCTTCCTGGT", "196 bp"],
      ["Exon 25 (solvent front)", "TGCCTTCCTTCCTTCCTGTT", "AGGCAGGTAGCTGGGTTGTA", "212 bp"]]],

    ["AKT1", "AKT Serine/Threonine Kinase 1", "14q32", "52%",
     "E17K, Q79K",
     "AKT1 encodes a serine/threonine kinase in the PI3K/AKT/mTOR signaling pathway regulating cell survival and metabolism.",
     "The E17K mutation in the pleckstrin homology domain is a recurrent activating mutation found in breast, ovarian, and colorectal cancers.",
     "Exons 2\u20136 (PH domain, kinase domain)",
     ["Hotspot mutation E17K: The recurrent E17K mutation in exon 2 requires allele-specific primer design for mutant detection",
      "Low sequence complexity: Intronic regions around exon 4 contain repetitive elements complicating unique primer placement",
      "Pseudogene interference: Processed pseudogene AKT1P on chromosome 14 shares >90% exon homology requiring careful specificity checks"],
     [["rs121434592", "E17K", "PH domain hotspot in exon 2"],
      ["rs1130233", "Q79K", "Common polymorphism near the kinase domain"]],
     [["Exon 2 (E17K hotspot)", "GGTGCCATTGAGAAGGACGT", "ACAGGTGGTCCACATCCTCT", "178 bp"],
      ["Exon 4 (kinase domain)", "TCTGTCATGGAGTACGCCAA", "TGTGTCCTGGTCCTGGTTCT", "203 bp"]]],

    ["ALDH2", "Aldehyde Dehydrogenase 2", "12q24", "61%",
     "E504K (rs671), R475W",
     "ALDH2 encodes the mitochondrial aldehyde dehydrogenase enzyme responsible for acetaldehyde oxidation in alcohol metabolism.",
     "The E504K variant (rs671) severely reduces ALDH2 activity and is carried by ~40% of East Asian populations, linking to cancer risk.",
     "Exons 1\u201313",
     ["High GC content (61%): The ALDH2 gene has elevated overall GC content requiring denaturant optimization for robust amplification",
      "rs671 hotspot: The common E504K variant in exon 12 falls within primer binding regions requiring careful placement",
      "Homologous ALDH genes: ALDH1A1, ALDH1B1 paralogs share 65\u201370% sequence identity necessitating BLAST-based primer validation"],
     [["rs671", "E504K", "Exon 12 variant affecting enzyme activity"],
      ["rs2228093", "R475W", "Exon 11 polymorphism in catalytic domain"]],
     [["Exon 2 (active site)", "GTGGAGACCCATTCATCGGT", "AGCTGGTACTCAGCATCGTG", "185 bp"],
      ["Exon 12 (rs671 region)", "CACTGCTGATGACAGGGCTG", "CAACCTCCCATCAGCATGAG", "199 bp"]]],

    ["APC", "APC Regulator of WNT Signaling", "5q22", "47%",
     "Truncating mutations codon 1309, 1061, 1114",
     "APC is a tumor suppressor gene encoding a negative regulator of WNT/\u03b2-catenin signaling through a multi-protein destruction complex.",
     "Germline truncating mutations in the mutation cluster region (MCR, codons 1286\u20131513) cause familial adenomatous polyposis and drive colorectal carcinogenesis.",
     "Exons 1\u201315 (MCR in exon 15)",
     ["Large exon 15: Exon 15 spans 6.5 kb containing the mutation cluster region, requiring tiled amplicon design for full coverage",
      "Low GC content (47%): AT-rich intronic regions affect primer Tm uniformity, especially in introns 3\u20138",
      "Repetitive Alu elements: APC introns contain dense Alu repeat clusters that complicate exon-spanning primer placement"],
     [["rs1801155", "D1822V", "Exon 15 common polymorphism"],
      ["rs121913329", "Q1331*", "Premature stop in MCR region"]],
     [["Exon 15 (MCR region 1)", "CCTGCAAATCCAGAACACCC", "GCTGGGATTTGGTTCTAGGG", "220 bp"],
      ["Exon 15 (MCR region 2)", "AGGGTTCTAGTTTATCTTCA", "CCATTCCATTCCATTCCATT", "248 bp"]]],

    ["AR", "Androgen Receptor", "Xq12", "63%",
     "T878A, H874Y, W742C, T877A",
     "AR encodes the androgen receptor, a nuclear receptor transcription factor activated by androgens that regulates male sexual development and prostate growth.",
     "Ligand-binding domain mutations in exons 4\u20138 drive castration-resistant prostate cancer by broadening ligand specificity.",
     "Exons 1\u20138 (LBD in exons 4\u20138)",
     ["Very high GC content (63%): AR has one of the highest GC contents among nuclear receptors, requiring 5\u201310% DMSO for GC-rich exon 1 amplification",
      "CAG repeat polymorphism: Exon 1 contains a polymorphic CAG trinucleotide repeat affecting translation and confounding primer design",
      "X-chromosomal hemizygosity: Male single-copy status requires higher PCR sensitivity to avoid allelic dropout artifacts"],
     [["rs121913659", "T878A", "LBD mutation in exon 5, antiandrogen resistance"],
      ["rs121913661", "H874Y", "Exon 5 LBD activating mutation"],
      ["rs1042829", "CAG repeat", "Exon 1 polymorphic repeat"]],
     [["Exon 1 (NTD domain)", "GAGCGTACCTGCGTGAAAGA", "ACAGAGATGCTCTTCAATGG", "192 bp"],
      ["Exon 5 (LBD T878A)", "TGACTCTGGAGCCCTTTGAA", "GCTGTGAAGCCTCTCTTCCT", "215 bp"]]],

    ["ARID1A", "AT-Rich Interaction Domain 1A", "1p36", "48%",
     "Frameshift, nonsense mutations",
     "ARID1A encodes a subunit of the SWI/SNF chromatin remodeling complex that regulates DNA accessibility and gene expression.",
     "Inactivating frameshift and nonsense mutations in ARID1A are common in ovarian clear cell carcinoma and endometrioid cancers.",
     "Exons 1\u201320 (ARID domain in exon 1)",
     ["Large transcript size: ARID1A spans ~86 kb with 20 exons, requiring systematic tiled amplicon coverage",
      "AT-rich introns (48% GC): Low GC content in intronic regions may complex with high background in intergenic amplification",
      "Frameshift mutation detection: Single-nucleotide insertion/deletion mutations require high-resolution amplicon design"],
     [["rs138486234", "R1989*", "Recurrent nonsense mutation in exon 20"],
      ["rs370842097", "Q584*", "Exon 7 truncating mutation in ovarian cancer"]],
     [["Exon 1 (ARID domain)", "CTCTCCCAGCAGTCACTGAA", "GCTTGCTGAGCTGTCTCTGT", "188 bp"],
      ["Exon 20 (C-terminal)", "TCCCTACCCCATGTGTGACT", "ACACCTGGAGCTGTCTCTTG", "234 bp"]]],

    ["ATM", "ATM Serine/Threonine Kinase", "11q22", "44%",
     "Truncating, missense mutations",
     "ATM encodes a master kinase in the DNA damage response pathway that phosphorylates downstream checkpoint and repair proteins.",
     "Biallelic ATM mutations cause ataxia-telangiectasia, while monoallelic loss increases breast and pancreatic cancer risk.",
     "Exons 2\u201363 (PI3K-like kinase domain in exons 39\u201363)",
     ["Very large gene (62 exons): ATM spans ~150 kb with 62 coding exons requiring extensive tiled primer panels",
      "Low GC content (44%): AT-rich regions near intron 8 affect primer annealing, requiring higher Tm primers",
      "High SNP density: The large coding region contains numerous benign polymorphisms requiring frequent primer repositioning"],
     [["rs1800057", "P1054R", "Exon 24 missense variant"],
      ["rs121434379", "R3047X", "Truncating mutation in kinase domain"]],
     [["Exon 24 (FAT domain)", "GCTGTGAACAGCTTGAGACG", "CCAAACTCCCTTGTCTGCAT", "176 bp"],
      ["Exon 39 (PI3K domain)", "TGCATGTATCTTGCCATCCT", "ACATGGCGTGAACTCACTGT", "201 bp"]]],

    ["BCL2", "BCL2 Apoptosis Regulator", "18q21", "58%",
     "t(14;18) translocation, amplification",
     "BCL2 encodes an anti-apoptotic mitochondrial outer membrane protein that blocks cytochrome c release and caspase activation.",
     "The t(14;18) translocation placing BCL2 under the immunoglobulin heavy chain enhancer drives follicular lymphoma pathogenesis.",
     "Exons 1\u2013301\u20133",
     ["t(14;18) breakpoint diversity: Major breakpoint region (MBR) and minor cluster region (mcr) require translocation-specific primer pairs",
      "High GC content (58%): The 5' regulatory CpG island influences promoter accessibility and primer binding",
      "Alternative splicing: Three splice variants (BCL2\u03b1, \u03b2, \u03b3) complicate isoform-specific detection"],
     [["rs1801018", "A21T", "Exon 1 synonymous variant"],
      ["rs4987855", "F104F", "Exon 2 polymorphism"]],
     [["Exon 2 (BH4 domain)", "CAGCTGTGGAGATGGTGATG", "AACTGAGCAGTGCCTTCAGA", "165 bp"],
      ["Exon 3 (BH1 domain)", "TGATGGGATCGTTGCCTTAT", "CACAAAGGCATCCCAGCCTC", "189 bp"]]],

    ["BCR", "BCR Activator of RhoGEF and GTPase", "22q11", "54%",
     "t(9;22) BCR-ABL1 fusion, BCR-ABL1 e13a2, e14a2",
     "BCR encodes a serine/threonine kinase with Rho guanine nucleotide exchange factor (RhoGEF) and GTPase-activating domains.",
     "The t(9;22) Philadelphia chromosome fuses BCR to ABL1, generating a constitutively active tyrosine kinase driver of chronic myeloid leukemia.",
     "Exons 1\u201323 (fusion breakpoints in introns 13\u201314)",
     ["Chromosomal translocation detection: BCR-ABL1 fusion breakpoints vary (e13a2, e14a2, e1a2) requiring multiplex primer strategies",
      "BCR N-terminal oligomerization: The coiled-coil domain in exon 1 is critical for BCR-ABL1 activation and requires targeted detection",
      "Large introns: Intronic breakpoints span 5.8 kb requiring long-range PCR optimization"],
     [["rs45459197", "BCR intron 14", "Breakpoint cluster region variant"],
      ["rs45558697", "BCR exon 13", "e13a2 breakpoint-associated SNP"]],
     [["e13a2 fusion", "ACAGCATTCCGCTGACCATC", "CAGCTCACTGACCACTCGTC", "210 bp"],
      ["e14a2 fusion", "ATCCGTGGAGCTGCAGATGC", "TCAGACCCTGAGGCTCAAAG", "225 bp"]]],

    ["BRCA2", "BRCA2 DNA Repair Associated", "13q13", "41%",
     "Truncating, frameshift, 6174delT, 999del5",
     "BRCA2 encodes a protein essential for homologous recombination repair of double-strand DNA breaks through RAD51 interaction.",
     "Germline loss-of-function mutations in BRCA2 confer lifetime breast cancer risk of ~69% and ovarian cancer risk of ~17%.",
     "Exons 2\u201327",
     ["Very low GC content (41%): BRCA2 has among the lowest GC content of cancer genes, causing weak primer-template stability",
      "Large coding sequence: 27 exons spanning 11.4 kb require 120+ tiled amplicons for full mutation screening",
      "Multitude of founder mutations: Population-specific frameshifts (6174delT in Ashkenazi, 999del5 in Icelandic) need targeted genotyping"],
     [["rs80359550", "6174delT", "Ashkenazi Jewish founder frameshift in exon 11"],
      ["rs80359876", "999del5", "Icelandic founder mutation in exon 9"]],
     [["Exon 9 (Icelandic del)", "CCTGTGAAGACAGTGACAGC", "ACACAGCTTGTAGGGACTCC", "172 bp"],
      ["Exon 11 (6174delT)", "AAGGTGCATGGCTACAGCTG", "TCTGTGCTGTGACTTTGCTG", "244 bp"]]],

    ["CALR", "Calreticulin", "19p13", "64%",
     "Type 1 (52 bp del), Type 2 (5 bp ins) exon 9 mutations",
     "CALR encodes a multifunctional calcium-binding chaperone protein in the endoplasmic reticulum lumen regulating calcium homeostasis and protein folding.",
     "Somatic frameshift mutations in exon 9 generate a novel C-terminal peptide that constitutively activates the thrombopoietin receptor MPL in myeloproliferative neoplasms.",
     "Exon 9",
     ["Very high GC content (64%): CALR has elevated GC content, particularly in exon 9 where all mutations cluster",
      "Mutation hotspot in exon 9: Type 1 (52 bp deletion) and Type 2 (5 bp insertion) share a common breakpoint region requiring carefully designed flanking primers",
      "Single-exon mutation pattern: All pathogenic mutations are limited to the last exon, allowing focused but high-resolution amplicon design"],
     [["rs1554100933", "Type 1 (52 bp del)", "Exon 9 frameshift in essential thrombocythemia"],
      ["rs1554100938", "Type 2 (5 bp ins)", "Exon 9 insertion in primary myelofibrosis"]],
     [["Exon 9 (Type 1/2)", "GAAGCAGCAGAAACGCACAA", "TCAGCTCCTGGACAGAGTCA", "198 bp"],
      ["Exon 9 alternate", "GGCCTTGTCCAGTTCCACAA", "TGCCTCCTGTCTTGTGATGT", "165 bp"]]],

    ["CARD11", "Caspase Recruitment Domain Family Member 11", "7p22", "51%",
     "L232LI, G123S, D230N",
     "CARD11 encodes a scaffold protein that assembles the CBM (CARD11-BCL10-MALT1) complex to activate NF-\u03baB signaling in lymphocytes.",
     "Gain-of-function mutations in the coiled-coil domain (exons 3\u201310) drive constitutive NF-\u03baB activation in diffuse large B-cell lymphoma.",
     "Exons 3\u201310 (coiled-coil domain)",
     ["Coiled-coil domain mutations: Hotspot L232LI insertion in exon 6 requires careful amplicon placement around the repeat region",
      "Alternative splicing: Multiple CARD11 isoforms with alternative exon usage require transcript-aware primer design",
      "Moderate GC content (51%): Balanced GC provides favorable thermodynamics but requires uniform Tm across target regions"],
     [["rs201569880", "L232LI", "Exon 6 insertion in DLBCL"],
      ["rs587782115", "G123S", "Exon 4 CARD domain variant"]],
     [["Exon 6 (coiled-coil)", "GAACGAGGTGCTGCTGCTAA", "CAGCAGCTCCACAGACACTT", "183 bp"],
      ["Exon 4 (CARD domain)", "AGCCCTGTGGACTTCCTCTT", "ACCTGGCGTGGTTAAAGTCC", "156 bp"]]],

    ["CCND1", "Cyclin D1", "11q13", "55%",
     "CCND1-IGH translocation, splicing variant",
     "CCND1 encodes cyclin D1, a G1/S cell cycle regulatory protein that activates CDK4 and CDK6 for Rb phosphorylation.",
     "The t(11;14)(q13;q32) translocation fuse CCND1 to the immunoglobulin heavy chain locus, driving mantle cell lymphoma and multiple myeloma.",
     "Exons 1\u20135",
     ["Translocation breakpoints: t(11;14) breakpoints cluster in the 11q13 major translocation cluster (MTC) spanning ~1 kb requiring specific primers",
      "Alternative splicing: CCND1 variant transcripts (b, c, d) with alternative 3' exons require isoform-specific detection strategies",
      "Polymorphic A870G: rs603965 in exon 4 splice site affects mRNA splicing and may require redesign of flanking primers"],
     [["rs603965", "A870G", "Exon 4 splice site variant affecting cyclin D1b expression"],
      ["rs9344", "G870A", "Synonymous polymorphism in exon 4"]],
     [["Exon 4 (splice variant)", "CGCGAGACCTTCGTTGCCCT", "GCTGGGACATCACCCTCACT", "175 bp"],
      ["Exon 1 (cyclin box)", "GGCTGCTGGTGGAAAAGAAC", "CAGCCCCAACAACTCCTTCT", "190 bp"]]],

    ["CDH1", "Cadherin 1", "16q22", "52%",
     "Truncating, missense, promoter hypermethylation",
     "CDH1 encodes E-cadherin, a transmembrane calcium-dependent adhesion glycoprotein essential for epithelial tissue integrity.",
     "Germline mutations in CDH1 cause hereditary diffuse gastric cancer (HDGC) with ~70% lifetime risk, and lobular breast cancer.",
     "Exons 1\u201316",
     ["Promoter CpG methylation: Epigenetic silencing via promoter hypermethylation is a key inactivation mechanism requiring bisulfite-based primer design",
      "Large gene structure: 16 exons spanning ~100 kb with large introns (intron 1 = 27 kb) complicate genomic amplification",
      "Multiple mutation types: Missense, frameshift, splice-site, and large deletions require comprehensive primer coverage"],
     [["rs121964898", "R732Q", "Exon 12 missense variant in HDGC"],
      ["rs121964878", "1003C>T", "Premature stop in exon 7"]],
     [["Exon 7 (extracellular)", "GAGGTGCTGTTGCCAGTCAT", "CATCAGCAAGAGCATGAGCA", "168 bp"],
      ["Exon 12 (cytoplasmic)", "GCTCACAGTGTGTGACTGGA", "ACCTTGAGAGGTGACGCTTG", "213 bp"]]],

    ["CDK4", "Cyclin Dependent Kinase 4", "12q14", "57%",
     "R24C, R24H",
     "CDK4 encodes a cyclin-dependent kinase that phosphorylates Rb at the G1/S checkpoint, promoting cell cycle progression.",
     "Activating R24C and R24H mutations in exon 2 disrupt p16INK4a binding and confer hereditary melanoma susceptibility.",
     "Exons 1\u20138",
     ["R24 hotspot mutations: Codon 24 in exon 2 is the sole recurrent mutation site, requiring targeted amplicon covering the glycine-rich loop",
      "Moderately high GC (57%): Exon 2 surrounding R24 has >65% GC content requiring denaturant optimization",
      "p16-INK4a binding interface: The mutation hotspot lies in the CDK4-p16 interaction domain necessitating careful primer placement"],
     [["rs121913351", "R24C", "Exon 2 hereditary melanoma mutation"],
      ["rs121913352", "R24H", "Exon 2 melanoma predisposition variant"]],
     [["Exon 2 (R24 hotspot)", "CCTCACTTCCCCACATCTGA", "TGGGAAAGCTGCCTAAATCC", "162 bp"],
      ["Exon 5 (kinase domain)", "AGCTGGCACTCAGAGTTTGA", "TGTCATGAACACTCTCCTGG", "188 bp"]]],

    ["CDKN2A", "Cyclin Dependent Kinase Inhibitor 2A", "9p21", "53%",
     "p16 deletions, V126D, A148T, M53I",
     "CDKN2A encodes two distinct tumor suppressors: p16(INK4a) from exons 1\u03b1, 2, 3 and p14(ARF) from exons 1\u03b2, 2, 3 through alternative reading frames.",
     "Homozygous deletions and point mutations in CDKN2A are found in familial melanoma, pancreatic cancer, and multiple sporadic cancers.",
     "Exons 1\u03b1, 1\u03b2, 2, 3",
     ["Dual reading frame complexity: Exon 2 encodes both p16 and p14ARF in different reading frames, requiring frame-aware primer design",
      "Exon 1\u03b2 (p14ARF-specific): Unique first exon for p14ARF requires isoform-specific primers that exclude the p16 transcript",
      "Homozygous deletion detection: Common 9p21 deletions require multiplex primer pairs for copy number assessment"],
     [["rs104894094", "V126D", "Exon 2 p16 missense in pancreatic cancer"],
      ["rs3731249", "A148T", "Exon 2 common polymorphism"]],
     [["Exon 1\u03b1 (p16 only)", "GAAGAAAGAGGAGGGGCTGG", "CTGCGGCATCTATGATGCAT", "174 bp"],
      ["Exon 2 (shared)", "AGCAGCATGGAGCCTTCGGC", "CCATCATCATGACCTGGATC", "228 bp"]]],

    ["CEBPA", "CCAAT Enhancer Binding Protein Alpha", "19q13", "66%",
     "N-terminal frameshift, C-terminal bZIP mutations",
     "CEBPA encodes a leucine zipper transcription factor essential for myeloid differentiation and energy metabolism regulation.",
     "Biallelic CEBPA mutations (N-terminal frameshift + C-terminal in-frame) define a distinct acute myeloid leukemia subtype with favorable prognosis.",
     "Exons 1\u20132",
     ["Highest GC content (66%): CEBPA has extremely high GC content, especially in the N-terminal region requiring optimized PCR with DMSO/betaine",
      "Only 2 coding exons: Compact gene structure but with complex mutation patterns requiring careful primer placement around repetitive GC tracts",
      "Biallelic mutation detection: N-terminal and C-terminal mutations occur on different alleles requiring long-range or allele-specific genotyping"],
     [["rs121913001", "N-term frameshift", "Exon 1 18 bp duplication in AML"],
      ["rs1555408753", "C-term bZIP", "Exon 2 in-frame mutation"]],
     [["Exon 1 (N-term)", "ACCTGCGGATCTCCACCTT", "CGTTCGTCCCCTCCTTCTCT", "195 bp"],
      ["Exon 2 (bZIP domain)", "TGAAGCCGAAGCAAAACAG", "CCTTTCCACTGGGTCTGCT", "180 bp"]]],

    ["CHEK2", "Checkpoint Kinase 2", "22q12", "52%",
     "1100delC, I157T, S428F, del5395",
     "CHEK2 encodes a cell cycle checkpoint serine/threonine kinase that phosphorylates downstream effectors in the ATM-Chk2 DNA damage pathway.",
     "The hypomorphic 1100delC truncating mutation increases breast cancer risk ~2-fold and is present in ~1% of the European population.",
     "Exons 2\u201315",
     ["Founder mutation 1100delC: The 1100delC frameshift in exon 10 causes premature truncation requiring specific genotyping primers",
      "Multiple splice variants: Alternative splicing generates isoforms lacking kinase domain or FHA domain, requiring transcript awareness",
      "Pseudogene interference: Processed pseudogene on chromosome 15 shares homology with CHEK2 exons 10\u201315"],
     [["rs555607708", "1100delC", "Exon 10 founder frameshift, breast cancer risk"],
      ["rs17879961", "I157T", "Exon 3 missense, reduced kinase activity"]],
     [["Exon 10 (1100delC)", "CAATATTGCTGTGGGAGTGC", "CCTGAGTCCACCTGTCCTTC", "192 bp"],
      ["Exon 3 (FHA domain)", "GCCCAGACCATGTGTAAGGA", "ACAGGTTCATCATCGCAACA", "167 bp"]]],

    ["CSF1R", "Colony Stimulating Factor 1 Receptor", "5q32", "51%",
     "L301S, Y969C, M875T",
     "CSF1R encodes a receptor tyrosine kinase for colony-stimulating factor 1 that regulates macrophage and microglia differentiation.",
     "Mutations in CSF1R cause adult-onset leukoencephalopathy with axonal spheroids and pigmented glia (ALSP), a fatal neurodegenerative disease.",
     "Exons 12\u201322 (kinase domain)",
     ["Kinase domain mutation burden: Missense mutations in the tyrosine kinase domain (exons 12\u201322) cluster near the ATP-binding pocket",
      "Moderate GC (51%): Balanced GC provides stable thermodynamics but requires verification against repetitive intronic elements",
      "Microglial expression specificity: Transcript variants with alternative 5' UTRs require promoter-aware primer design for expression analysis"],
     [["rs121913301", "L301S", "Exon 7 extracellular domain mutation"],
      ["rs138554767", "Y969C", "Exon 21 kinase domain ALSP mutation"]],
     [["Exon 12 (kinase insert)", "GCCATCCTGACCTACTACGA", "CACTGGCATGTCCAACATCT", "203 bp"],
      ["Exon 21 (C-terminal)", "GAGTCCAGCATGGAGTACCT", "ACAGGCAGTTCATCCACATC", "188 bp"]]],

    ["CTNNB1", "Catenin Beta 1", "3p22", "62%",
     "S45F, T41A, D32Y, S37A, D32N",
     "CTNNB1 encodes \u03b2-catenin, a dual-function protein essential for cadherin-mediated adhesion and WNT transcriptional co-activation.",
     "Activating mutations at N-terminal degradation domain phosphorylation sites (codons 32\u201345) stabilize \u03b2-catenin in hepatocellular and colorectal cancers.",
     "Exon 3 (degradation domain)",
     ["Mutation cluster in exon 3: All activating mutations occur in a 114 bp region of exon 3 (codons 32\u201345) enabling single-amplicon coverage",
      "High GC content (62%): Exon 3 and flanking introns show elevated GC requiring DMSO addition for optimal PCR",
      "Single exon dominance: Unlike most genes, CTNNB1 mutation screening requires only one amplicon for >95% of pathogenic variants"],
     [["rs121913409", "S45F", "Exon 3 phosphorylation site mutation in HCC"],
      ["rs121913407", "T41A", "Exon 3 stabilizing mutation in colon cancer"],
      ["rs121913404", "D32Y", "Exon 3 GSK3\u03b2 phosphorylation target"]],
     [["Exon 3 (S45/T41)", "GATTTGATGGAGTTGGACAT", "TGAGCTCGAAGACAGCTCGA", "174 bp"],
      ["Exon 3 alternate", "CCACAACTGCTCCTAATGCT", "TGAGCTCGAAGACAGCTCGA", "196 bp"]]],

    ["CYP2C19", "Cytochrome P450 2C19", "10q23", "58%",
     "*2 (rs4244285), *3 (rs4986893), *17 (rs12248560)",
     "CYP2C19 encodes a drug-metabolizing cytochrome P450 enzyme involved in the metabolism of clopidogrel, proton pump inhibitors, and antidepressants.",
     "Polymorphisms define poor (*2/*3), intermediate, and ultrarapid (*17) metabolizer phenotypes with major pharmacogenomic implications.",
     "Exons 1\u20139",
     ["Polymorphic star alleles: *2 (splice defect), *3 (premature stop), and *17 (promoter) require haplotype-specific primer designs",
      "High GC content (58%): Elevated GC content in exon 1 (68%) requires additive optimization for robust amplification",
      "Pseudogene CYP2C19P: Highly homologous pseudogene on chromosome 10 requires careful primer specificity verification"],
     [["rs4244285", "*2 (splice)", "Exon 5 splice defect, poor metabolizer"],
      ["rs4986893", "*3 (stop)", "Exon 4 premature stop, poor metabolizer"],
      ["rs12248560", "*17 (promoter)", "Increased expression, ultrarapid metabolizer"]],
     [["Exon 5 (*2 site)", "ACAACCAGAGCTTGGCATAT", "CCTGGAATGTGCTGTGTTCT", "188 bp"],
      ["Exon 9 (heme-binding)", "CTGGGCCTGATGTTGGAACT", "ACCCAGTTCACACTGCTTCA", "196 bp"]]],

    ["CYP2D6", "Cytochrome P450 2D6", "22q13", "55%",
     "*4 (rs3892097), *10 (rs1065852), gene duplication, deletion",
     "CYP2D6 encodes a highly polymorphic cytochrome P450 enzyme that metabolizes ~25% of all prescribed drugs including tamoxifen and codeine.",
     "The CYP2D6 locus displays extreme copy number variation (0\u201313+ copies) and sequence variants defining poor to ultrarapid metabolizer phenotypes.",
     "Exons 1\u20139",
     ["Copy number variation: Full-gene deletions, duplications, and multiplications require comparative quantification methods alongside SNP genotyping",
      "Hybrid gene rearrangements: CYP2D6-CYP2D7 hybrid genes from structural variation complicate amplification specificity",
      "High homology with CYP2D7 pseudogene: 97% identity in exons 6\u20139 requires long-range or nested PCR for specific amplification"],
     [["rs3892097", "*4 (splice)", "Exon 4 splicing defect, poor metabolizer"],
      ["rs1065852", "*10 (P34S)", "Exon 1 reduced function, Asian population"],
      ["rs16947", "*2 (R296C)", "Exon 6 common variant, normal function"]],
     [["Exon 4 (*4 site)", "GCAGGCACTGACCACAACTG", "CACGGTCCTGGCTCTCATTG", "192 bp"],
      ["Exon 9 (heme-binding)", "AGACCCCGTGGGAAAAGCAA", "GAGAGCTCGGCCCTGCAGAG", "205 bp"]]],

    ["DDR2", "Discoidin Domain Receptor 2", "1q23", "50%",
     "S131R, L239R, G505S, I638F",
     "DDR2 encodes a collagen-binding receptor tyrosine kinase that regulates cell migration, proliferation, and matrix remodeling.",
     "Mutations in the discoidin and kinase domains of DDR2 occur in ~4% of squamous cell lung cancers and are candidate targets for dasatinib.",
     "Exons 13\u201318 (kinase domain)",
     ["Moderate GC (50%): Balanced content allows standard PCR conditions but requires careful Tm matching across mutation hotspots",
      "Discoidin domain interference: The extracellular discoidin domain binds collagen, and mutations affect cell culture amplification efficiency",
      "Somatic mutation distribution: Mutations spanning both discoidin (exons 2\u20138) and kinase (exons 13\u201318) domains require dual-region tiling"],
     [["rs137855902", "S131R", "Exon 4 discoidin domain mutation"],
      ["rs3731851", "G505S", "Exon 13 kinase domain mutation in SCC"]],
     [["Exon 13 (kinase)", "GGAGCAGACCCACATGAGAA", "ACTGCCCTCACCTGGTACAT", "177 bp"],
      ["Exon 16 (activation loop)", "TGCTCCCTCTCCGGATACTA", "CAGCTGCACTCTGAAGTCCA", "198 bp"]]],

    ["DNMT3A", "DNA Methyltransferase 3 Alpha", "2p23", "52%",
     "R882H, R882C, frameshift, nonsense",
     "DNMT3A encodes a DNA methyltransferase that establishes de novo DNA methylation patterns during embryonic development and hematopoiesis.",
     "Recurrent R882 hotspot mutations in the methyltransferase domain occur in ~25% of cytogenetically normal AML cases and clonal hematopoiesis.",
     "Exons 2\u201323 (MTase domain in exons 10\u201323)",
     ["R882 hotspot mutations: Arginine 882 mutations in exon 23 cluster at the tetramerization interface requiring specific flanking primers",
      "Two major domains: Proline-rich N-terminus (exons 2\u20139) and methyltransferase domain (exons 10\u201323) require separate targeting strategies",
      "Clonal hematopoiesis detection: Age-related DNMT3A mutations require highly sensitive (0.5\u20131% VAF) deep sequencing primer design"],
     [["rs387906912", "R882H", "Exon 23 hotspot in AML"],
      ["rs144469610", "R882C", "Exon 23 C>T transition in clonal hematopoiesis"]],
     [["Exon 23 (R882)", "CTGTGGAGAGAGCCTCTCCT", "CACCTCCACAAACCTCAACC", "212 bp"],
      ["Exon 10 (MTase start)", "GAGCAAGGAGTCCCACATCA", "GGAGGTGGACACATTGTGCT", "185 bp"]]],

    ["ERCC1", "ERCC Excision Repair 1", "19q13", "54%",
     "Asn118Asn (rs11615), C8092A (rs3212986)",
     "ERCC1 encodes a nuclease subunit of the nucleotide excision repair complex that removes bulky DNA adducts including platinum-DNA crosslinks.",
     "Expression levels and polymorphisms in ERCC1 influence response to platinum-based chemotherapy in non-small cell lung and ovarian cancers.",
     "Exons 1\u201310",
     ["Polymorphism-as-biomarker: rs11615 (N118N) and rs3212986 (C8092A) are common SNPs that may influence mRNA stability and therapeutic prediction",
      "Balanced GC (54%): Standard PCR conditions suitable but requires Mg2+ optimization for some GC-rich intron 2 regions",
      "Alternative splicing: ERCC1-202 (lacks exon 8) and ERCC1-204 (lacks exons 2\u20133) transcripts require splice-aware primer design"],
     [["rs11615", "N118N", "Exon 4 synonymous variant, therapy response marker"],
      ["rs3212986", "C8092A", "3' UTR variant, platinum sensitivity"]],
     [["Exon 4 (rs11615)", "CAAGAGGAGGCAATGTGGAC", "TGACACTCTGGGAGGTAGCA", "160 bp"],
      ["Exon 10 (3' UTR)", "CCCTGGGAGTTTAGAGAAGC", "ACTCAGGAGTGCACATCAAG", "218 bp"]]],

    ["ESR1", "Estrogen Receptor 1", "6q25", "49%",
     "Y537S, Y537N, D538G, E380Q",
     "ESR1 encodes estrogen receptor alpha (ER\u03b1), a nuclear receptor transcription factor that mediates estrogen signaling in breast and reproductive tissues.",
     "Ligand-binding domain mutations (Y537S, D538G) arise during aromatase inhibitor therapy and drive acquired endocrine resistance in metastatic breast cancer.",
     "Exons 1\u201310 (LBD in exons 4\u201310)",
     ["Acquired resistance mutations: LBD mutations (Y537S, D538G) emerge during therapy requiring highly sensitive (>0.1% VAF) mutation detection",
      "Moderate-to-low GC (49%): Slightly AT-rich sequence in exons 1\u20132 requires modest Tm adjustments",
      "Multiple transcript isoforms: ER\u03b1-36 (truncated) and ER\u03b1-46 variant transcripts require isoform-specific 3' primers"],
     [["rs121908912", "Y537S", "Exon 8 LBD activating mutation, endocrine resistance"],
      ["rs121908913", "D538G", "Exon 8 LBD hotspot in metastatic breast cancer"]],
     [["Exon 8 (LBD Y537S)", "GCTACAATCATCTGAGGTCC", "CCTCTGACGGTAGACCTTCC", "208 bp"],
      ["Exon 4 (DNA-binding)", "GACACATGATCGGTCCGTCA", "ACATCTCGGGTAGGTCACAG", "182 bp"]]],

    ["EZH2", "Enhancer of Zeste 2 Polycomb Repressive Complex 2 Subunit", "7q36", "62%",
     "Y641F/N/S, A677G, A687V",
     "EZH2 encodes the catalytic subunit of Polycomb Repressive Complex 2 that methylates histone H3 at lysine 27 to silence gene expression.",
     "Gain-of-function Y641 hotspot mutations in the SET domain drive germinal center B-cell lymphoma and follicular lymphoma pathogenesis.",
     "Exons 2\u201320 (SET domain in exons 16\u201320)",
     ["High GC content (62%): Elevated GC extends across the SET domain (exons 16\u201320) requiring additive-optimized PCR conditions",
      "SET domain mutation cluster: Y641 (exon 16) and A677/A687 (exon 18) mutations require two targeted amplicons for complete coverage",
      "EZH2 inhibitor monitoring: Emerging resistance mutations require pre-planned primer redundancy for longitudinal liquid biopsy tracking"],
     [["rs387906906", "Y641N", "Exon 16 SET domain gain-of-function in DLBCL"],
      ["rs387906908", "A677G", "Exon 18 SET domain alteration"],
      ["rs373733653", "A687V", "Exon 18 activating mutation"]],
     [["Exon 16 (Y641)", "GGACTTGGGACACCTCTCTA", "GTGGGATGAATGCAGCACAT", "198 bp"],
      ["Exon 18 (A677/A687)", "CCTCCCTGACTTCTGTGACT", "TCCTGTGCTGTGATCATTCC", "214 bp"]]],

    ["FBXW7", "F-Box and WD Repeat Domain Containing 7", "4q31", "46%",
     "R465C, R465H, R479Q, R505L",
     "FBXW7 encodes the substrate recognition component of the SCF ubiquitin ligase complex that targets oncoproteins (MYC, cyclin E, NOTCH) for degradation.",
     "Inactivating missense mutations at arginine residues 465, 479, and 505 in the WD40 domain occur in T-ALL, colorectal, and gastric cancers.",
     "Exons 2\u201310 (WD40 repeats in exons 4\u201310)",
     ["WD40 domain hotspot: Arginine 465 mutations in exon 8 affect substrate binding and require focused amplicon design",
      "Low GC content (46%): AT-rich introns flanking exons 3\u20136 require lower annealing temperatures and longer primer design",
      "Multiple target substrates: FBXW7\u2019s role in degrading multiple oncoproteins requires complete mutation coverage across all WD40 repeats"],
     [["rs121913208", "R465C", "Exon 8 WD40 domain loss-of-function"],
      ["rs121913209", "R479Q", "Exon 9 substrate-binding mutation"]],
     [["Exon 8 (R465)", "GTGTCTATGGTGCCAACTGG", "GCTCGAGCTGTCTATCCACA", "173 bp"],
      ["Exon 9 (WD40)", "CCCCATAAGCAGCACATGAG", "CCTGAGACCCAGTGATTCCT", "185 bp"]]],

    ["FGFR1", "Fibroblast Growth Factor Receptor 1", "8p11", "57%",
     "Amplification, N546K, K656E",
     "FGFR1 encodes a receptor tyrosine kinase for fibroblast growth factors that regulates cell proliferation, differentiation, and angiogenesis.",
     "FGFR1 amplification at 8p11 is found in ~10% of breast cancers and defines the 8p11 myeloproliferative syndrome with eosinophilia.",
     "Exons 7\u201318 (kinase domain)",
     ["Amplicon detection: 8p11 amplification requires copy-number aware qPCR primer design with reference gene normalization",
      "Elevated GC (57%): Exons 11\u201313 within the kinase insert region show GC stretches requiring denaturant optimization",
      "Alternative splicing: FGFR1-IIIb and -IIIc isoforms (exon 8/9 switching) require splice-junction-specific primer selection"],
     [["rs121913477", "N546K", "Exon 12 kinase domain mutation"],
      ["rs121913478", "K656E", "Exon 14 activation loop mutation"]],
     [["Exon 12 (kinase)", "TCTGGCTCCTGGTGGTTATG", "GCCGATGTGAGTGTTGACAT", "193 bp"],
      ["Exon 14 (activation loop)", "CAGCCACAGACCTCCCTAA", "CAGCTCGTTGGTGAAGTTCA", "178 bp"]]],

    ["FGFR2", "Fibroblast Growth Factor Receptor 2", "10q26", "60%",
     "S252W, P253R, C278F, N549K",
     "FGFR2 encodes a receptor tyrosine kinase with alternative IIIb (K-sam) and IIIc (Bek) isoforms regulating epithelial and mesenchymal FGFR signaling.",
     "S252W and P253R mutations in the extracellular domain cause Apert syndrome, while kinase mutations occur in endometrial and lung cancers.",
     "Exons 7\u201318 (kinase domain, IIIb/IIIc switch)",
     ["Isoform-specific exon switching: Alternative exons 8 (IIIb) and 9 (IIIc) require isoform-specific primer placement for cancer-type-specific amplification",
      "High GC content (60%): Elevated GC in exons 4\u20136 and 13\u201315 requires betaine or DMSO for robust amplification",
      "Hotspot mutation clustering: S252W/P253R in exon 7 and kinase domain N549K in exon 14 require separate targeted panels"],
     [["rs121918508", "S252W", "Exon 7 Apert syndrome activating mutation"],
      ["rs121918482", "N549K", "Exon 14 kinase domain in endometrial cancer"]],
     [["Exon 7 (IgIII domain)", "CGTGCTCTTCTGTGTGGATG", "GTGTTGGGGTTGTCAGATGC", "195 bp"],
      ["Exon 14 (kinase)", "GAGGATGGTGCTGTCAAAGC", "CACTCGGGATGTAGACCTGG", "182 bp"]]],

    ["FGFR3", "Fibroblast Growth Factor Receptor 3", "4p16", "55%",
     "G380R, R248C, S249C, Y373C, K650E",
     "FGFR3 encodes a receptor tyrosine kinase that negatively regulates bone growth and is involved in cell differentiation and proliferation.",
     "Activating mutations in FGFR3 cause thanatophoric dysplasia and achondroplasia, and recurrent S249C mutations occur in bladder cancer.",
     "Exons 7\u201318 (kinase domain, IgIII domain)",
     ["S249C hotspot: The cysteine substitution in exon 7 causes constitutive dimerization and requires specific genotyping primers",
      "Moderate GC (55%): Balanced GC with localized high-GC pockets in exon 10 requiring optimized touchdown PCR protocols",
      "Dual disease spectrum: Germline skeletal dysplasia vs somatic cancer mutations require different detection thresholds (germline heterozygous vs somatic low-VAF)"],
     [["rs121913450", "S249C", "Exon 7 bladder cancer hotspot"],
      ["rs28931615", "G380R", "Exon 10 achondroplasia mutation"],
      ["rs121913455", "K650E", "Exon 15 thanatophoric dysplasia"]],
     [["Exon 7 (S249C)", "CAGTGGGATCGGTGCACTAT", "ACACAGCCTGGTCAAACACA", "208 bp"],
      ["Exon 10 (G380R)", "TCCAGGCACCCAGAGGATAG", "GCACACCACCTCCCTTTAGA", "192 bp"]]],

    ["FLT3", "Fms Related Receptor Tyrosine Kinase 3", "13q12", "48%",
     "ITD (internal tandem duplication), D835Y, D835V",
     "FLT3 encodes a class III receptor tyrosine kinase that regulates hematopoietic stem cell survival, proliferation, and differentiation.",
     "FLT3-ITD mutations in the juxtamembrane domain (exon 14\u201315) and TKD mutations at D835 (exon 20) are poor-prognosis markers in AML.",
     "Exons 14\u201315 (JM domain), exon 20 (TKD)",
     ["ITD size variability: FLT3-ITD insertions range from 3 to 400+ bp requiring fragment analysis or long-range PCR across the JM domain",
      "Dual mutation hotspots: JM domain (exons 14\u201315) and TKD (exon 20) require two completely different amplicon design strategies",
      "Lower GC content (48%): Moderate AT bias in intron 14 requires longer primers (24\u201326 nt) for specific binding"],
     [["FLT3-ITD", "ITD (variable)", "Exons 14\u201315 juxtamembrane duplication"],
      ["rs121913400", "D835Y", "Exon 20 TKD point mutation in AML"],
      ["rs121913401", "D835V", "Exon 20 TKD activating mutation"]],
     [["Exons 14\u201315 (ITD)", "TGTGCAATTCCAGACTCTGC", "GCGACTTTGTGTGTGCTGAT", "230 bp"],
      ["Exon 20 (D835)", "CCAGCCACAGCATCAGTCAT", "CATCCACCTCCCAACTGAAC", "198 bp"]]],

    ["FOXL2", "Forkhead Box L2", "3q22", "59%",
     "C134W (c.402C>G)",
     "FOXL2 encodes a forkhead transcription factor essential for ovarian granulosa cell development and function.",
     "The recurrent C134W mutation replaces cysteine with tryptophan in the forkhead domain and is present in >95% of adult granulosa cell tumors.",
     "Exon 1",
     ["Single-exon gene: All pathogenic mutations reside in the single coding exon, simplifying but requiring high-resolution amplicon design for the GC-rich forkhead domain",
      "Single mutation dominance: C134W accounts for >95% of mutations, allowing focused locked nucleic acid (LNA) probe-based detection",
      "High GC content (59%): The forkhead domain shows elevated GC requiring 5\u20138% DMSO for optimal amplification"],
     [["rs121909227", "C134W", "Single recurrent mutation in adult GCT"]],
     [["Exon 1 (C134W region)", "GTACCCCCAGCACTCGTACA", "GCTTGCCGTAGACGAGATGT", "167 bp"],
      ["Exon 1 (forkhead domain)", "CCCGGCATCAACGAGTACAT", "GCTTGCCGTAGACGAGATGT", "198 bp"]]],

    ["GATA2", "GATA Binding Protein 2", "3q21", "54%",
     "T354M, L359V, R396Q, GATA2 deficiency",
     "GATA2 encodes a zinc-finger transcription factor that regulates hematopoietic stem cell maintenance, lymphatic development, and innate immunity.",
     "Germline GATA2 mutations cause MonoMAC syndrome, dendritic cell/monocyte deficiency, and predisposition to myelodysplasia and AML.",
     "Exons 2\u20137",
     ["Zinc finger domain mutations: Mutations cluster in the C-terminal zinc finger (exon 6) and N-terminal zinc finger (exon 4) requiring targeted coverage",
      "Moderate GC (54%): Standard conditions suitable but the promoter region contains critical E-box elements for autoregulation",
      "Variable expressivity: Wide phenotypic spectrum requires comprehensive exon coverage for all GATA2 deficiency syndrome subtypes"],
     [["rs121908658", "T354M", "Exon 6 C-finger mutation in MonoMAC"],
      ["rs199816018", "R396Q", "Exon 6 C-finger loss-of-function"],
      ["rs371076826", "L359V", "Exon 6 variant of uncertain significance"]],
     [["Exon 4 (N-finger)", "TGTGTGTATGTTCCCCACCT", "GACAGGGGACACAGGTTGAG", "175 bp"],
      ["Exon 6 (C-finger)", "CAGGGACACTACCTCTGCTC", "AGCTCCACCATGTGATCCAT", "203 bp"]]],

    ["GNA11", "G Protein Subunit Alpha 11", "19p13", "58%",
     "Q209L, Q209P, R183C",
     "GNA11 encodes the G\u03b111 subunit of heterotrimeric G proteins that couples receptors to phospholipase C\u03b2 in the Gq signaling pathway.",
     "GNA11 Q209 mutations in the Ras-like domain occur in uveal melanoma, blue nevi, and are mutually exclusive with GNAQ mutations.",
     "Exons 4\u20137 (Ras-like domain, helical domain)",
     ["Q209 hotspot: Glutamine 209 mutations in exon 5 ablate GTPase activity causing constitutive Gq signaling",
      "Elevated GC (58%): The helical domain (exons 6\u20137) has high GC requiring careful primer Tm optimization",
      "Mutual exclusivity with GNAQ: Parallel testing for both GNA11 and GNAQ requires comparable primer efficiencies for multiplexing"],
     [["rs121913746", "Q209L", "Exon 5 uveal melanoma activating mutation"],
      ["rs121913749", "R183C", "Exon 4 GTPase domain in blue nevi"]],
     [["Exon 5 (Q209)", "TGACCTGCCTCAACTGACTC", "CAGAAGGCAGCTGGACATTG", "192 bp"],
      ["Exon 4 (R183)", "CTTGCAGTGGGCCTGTATGT", "GACACAGTCCATGACCTCCC", "179 bp"]]],

    ["GNAQ", "G Protein Subunit Alpha Q", "9q21", "57%",
     "Q209L, Q209P, R183Q, G48V",
     "GNAQ encodes the G\u03b1q subunit of heterotrimeric G proteins mediating signaling between G protein-coupled receptors and downstream effectors.",
     "Activating Q209 mutations in uveal melanoma and R183Q mutations in Sturge-Weber syndrome and port-wine stains drive MAPK pathway activation.",
     "Exons 4\u20137 (Ras-like domain, helical domain)",
     ["Q209 mutational hotspot: Glutamine 209 in exon 5 is the most common mutation site requiring precise amplicon placement to avoid allelic bias",
      "High GC (57%): The helical domain (exon 6) shows elevated GC requiring denaturant for efficient PCR",
      "GNAQ/GNA11 parallel testing: High homology between GNAQ and GNA11 in the GTPase domain requires isoform-specific primer design"],
     [["rs121913358", "Q209L", "Exon 5 uveal melanoma mutation"],
      ["rs121913359", "Q209P", "Exon 5 activating mutation"],
      ["rs104893956", "R183Q", "Exon 4 Sturge-Weber syndrome"]],
     [["Exon 5 (Q209 region)", "ACGTGAGCGTGCAGTCTCTA", "AGGCACTGTCTTCAGGAACA", "186 bp"],
      ["Exon 4 (R183 region)", "CCTGCTAAATCCTGTCCCCA", "CATCTGGCTCAGTGTCCTCT", "195 bp"]]],

    ["GNAS", "GNAS Complex Locus", "20q13", "51%",
     "R201C, R201H, R844C, GNAS activating",
     "GNAS encodes the G\u03b1s subunit of the stimulatory G protein that couples hormone receptors to adenylyl cyclase for cAMP production.",
     "Activating R201 mutations in the GTPase domain occur in pituitary adenomas, fibrous dysplasia, and McCune-Albright syndrome.",
     "Exons 1\u201313",
     ["GTPase hotspot R201: Arginine 201 mutations in exon 8 abolish GTP hydrolysis leading to constitutive cAMP signaling",
      "Genomic imprinting: GNAS is maternally imprinted in certain tissues requiring allele-specific primer design for mutation discrimination",
      "Balanced GC (51%): Standard PCR conditions suitable, but maternal/paternal allele discrimination requires SNP-linked primer design"],
     [["rs121913488", "R201C", "Exon 8 activating mutation in fibrous dysplasia"],
      ["rs121913489", "R201H", "Exon 8 pituitary adenoma hotspot"]],
     [["Exon 8 (R201)", "TGTGAATCCATCATCTTTGC", "GACAGGTCAGGAGTGGGTTC", "172 bp"],
      ["Exon 6 (Gs\u03b1 domain)", "GTTGGAGCAGAGGTCAGGAC", "CACCAAGCCATGACACAGTT", "184 bp"]]],

    ["HNF1A", "HNF1 Homeobox A", "12q24", "48%",
     "P291fsinsC, I27L, A98V, S142F",
     "HNF1A encodes a hepatic transcription factor that regulates expression of genes involved in glucose metabolism, lipid homeostasis, and detoxification.",
     "Mutations in HNF1A cause maturity-onset diabetes of the young type 3 (MODY3), the most common form of monogenic diabetes.",
     "Exons 1\u201310",
     ["P291 frameshift hotspot: The polyC tract in exon 4 is a mutational hotspot requiring careful polymerase selection to avoid slippage errors",
      "Low GC content (48%): AT-rich introns 2\u20134 affect primer binding and may require lower annealing temperatures",
      "MODY3 diagnosis specificity: >300 known mutations across all exons require complete exon coverage for clinical diagnostic panels"],
     [["rs137852835", "P291fsinsC", "Exon 4 polyC tract frameshift in MODY3"],
      ["rs1169288", "I27L", "Exon 1 common polymorphism"],
      ["rs121908448", "A98V", "Exon 1 missense in MODY diagnosis"]],
     [["Exon 4 (P291 region)", "CACTTGCCCAGCTCTCTCTA", "GACTCGGGAACAGAGGTGAC", "195 bp"],
      ["Exon 1 (dimerization)", "GTGCCAGGTGATCCATGTCT", "AGGTGCCTTGCCTCTGATTG", "168 bp"]]],

    ["HRAS", "HRas Proto-Oncogene", "11p15", "55%",
     "G12V, G12S, G13R, Q61R, Q61L",
     "HRAS encodes a small GTPase in the RAS superfamily that cycles between active GTP-bound and inactive GDP-bound states to regulate cell growth.",
     "Activating mutations at codons 12, 13, and 61 occur in Costello syndrome (germline) and bladder, thyroid, and head and neck cancers (somatic).",
     "Exons 1\u20136 (G domain in exons 1\u20134)",
     ["Hotspot codons 12/13/G61: The entire mutation spectrum spans <100 bp in exons 2\u20133, enabling single-amplicon coverage for most mutations",
      "Moderate GC (55%): Balanced GC content with a GC-rich stretch in exon 1 requiring touchdown PCR optimization",
      "HRAS-specific pseudogene: Processed HRAS pseudogene on chromosome 5 requires careful primer specificity BLAST verification"],
     [["rs104894228", "G12V", "Exon 2 transforming mutation in bladder cancer"],
      ["rs121913514", "Q61R", "Exon 3 activating mutation in head and neck cancer"]],
     [["Exon 2 (G12/G13)", "GACGAATACGACCCCACTAT", "GGTCCTGCACCAGTAATGTG", "175 bp"],
      ["Exon 3 (Q61)", "GACTCCTACCGGAAGCAGGT", "CATGGTGGGTCACTGTATGG", "182 bp"]]],

    ["IDH1", "Isocitrate Dehydrogenase (NADP(+)) 1", "2q34", "62%",
     "R132H, R132C, R132S, R132G",
     "IDH1 encodes the cytosolic NADP-dependent isocitrate dehydrogenase that converts isocitrate to \u03b1-ketoglutarate in cellular metabolism.",
     "R132 hotspot mutations produce the oncometabolite 2-hydroxyglutarate, causing DNA hypermethylation and blocking differentiation in glioma and AML.",
     "Exons 4\u201311 (active site in exon 4)",
     ["High GC content (62%): Elevated GC across exon 4 and flanking introns requires 5\u201310% DMSO for robust amplification of the R132 hotspot",
      "Single-codon dominance: R132 mutations account for >90% of all IDH1 mutations, enabling focused amplicon design",
      "Oncometabolite correlation: Distinguishing R132H vs R132C variants by sequencing requires high-resolution amplicon design avoiding GC bias"],
     [["rs121913500", "R132H", "Exon 4 most common IDH1 mutation in glioma"],
      ["rs121913499", "R132C", "Exon 4 alternative transversion in AML"],
      ["rs121913502", "R132S", "Exon 4 rare substitution"]],
     [["Exon 4 (R132)", "GGCTCTGAGGGACGTATCTG", "GCTGTCAGTTCACACTGAGG", "198 bp"],
      ["Exon 10 (NADP-binding)", "CAGCCACAATCCTGACCTTT", "GAGCAGTGTCACACTGTCCT", "185 bp"]]],

    ["IDH2", "Isocitrate Dehydrogenase (NADP(+)) 2", "15q26", "56%",
     "R140Q, R172K, R172M, R172S",
     "IDH2 encodes the mitochondrial NADP-dependent isocitrate dehydrogenase that catalyzes the oxidative decarboxylation of isocitrate.",
     "R140Q and R172 hotspot mutations produce 2-hydroxyglutarate and occur in AML, glioma, and cholangiocarcinoma with prognostic significance.",
     "Exons 4\u201311 (active site in exons 4, 11)",
     ["Dual hotspot exons: R140 mutations in exon 4 (AML) and R172 in exon 11 (glioma/cholangiocarcinoma) require two separate targeted amplicons",
      "Elevated GC (56%): Balanced GC with elevated regions in exon 4 requiring standard additive optimization",
      "Mitochondrial targeting: The mitochondrial localization signal in exon 1 requires careful 5' primer placement for full-length amplification"],
     [["rs121913504", "R140Q", "Exon 4 AML hotspot mutation"],
      ["rs121913503", "R172K", "Exon 11 glioma/cholangiocarcinoma hotspot"]],
     [["Exon 4 (R140)", "GACTGCCTGTCCCTTGTCTT", "TCCTGACCAAGACCATCACC", "193 bp"],
      ["Exon 11 (R172)", "CTAGCCTGTCCCCATCTCTC", "GCAGGACACGGTTTTGATCT", "208 bp"]]],

    ["JAK2", "Janus Kinase 2", "9p24", "50%",
     "V617F, exon 12 mutations (N542-E543del)",
     "JAK2 encodes a non-receptor tyrosine kinase essential for cytokine signaling through the JAK-STAT pathway in hematopoiesis.",
     "The V617F mutation in exon 14 is found in >95% of polycythemia vera and ~50% of essential thrombocythemia and primary myelofibrosis.",
     "Exons 12\u201324 (JH2 pseudokinase, JH1 kinase)",
     ["V617F dominance: Valine 617 in exon 14 is the single most important mutation site, but its high GC context requires optimized amplification",
      "Exon 12 mutations: N542-E543del and other in-frame indels in the pseudokinase domain require additional amplicon coverage",
      "Moderate GC (50%): Balanced GC content allows standard PCR, but the JH2 pseudokinase domain (exon 12\u201314) has localized higher-GC stretches"],
     [["rs77375493", "V617F", "Exon 14 JAK-STAT activating mutation in MPN"],
      ["JAK2 exon 12", "N542-E543del", "Exon 12 in-frame deletion in PV"]],
     [["Exon 14 (V617F)", "TGCTCTGAGACGTTGAGTCA", "GCTGTGATCCTGAAACTGGA", "186 bp"],
      ["Exon 12 (JH2 region)", "ACTCAGCAGGATGAAGCCAA", "CAGGCCAAGATCTTCTTCGT", "175 bp"]]],

    ["JAK3", "Janus Kinase 3", "19p13", "49%",
     "L156P, A573V, V715I, M511I",
     "JAK3 encodes a cytoplasmic tyrosine kinase expressed in hematopoietic cells that associates with the common gamma chain of cytokine receptors.",
     "Loss-of-function JAK3 mutations cause severe combined immunodeficiency (SCID), while gain-of-function mutations occur in T-cell leukemia/lymphoma.",
     "Exons 2\u201324 (JH1\u2013JH7 domains)",
     ["Dual phenotype spectrum: Gain-of-function (leukemia) vs loss-of-function (SCID) mutations span different domains requiring full-gene coverage",
      "Moderate-to-low GC (49%): Slightly AT-rich with repetitive elements in introns 4\u20138 requiring BLAST specificity checks",
      "Pseudokinase domain homology: JAK3 pseudokinase domain has moderate homology with JAK2 requiring family-specific primer design"],
     [["rs121913501", "L156P", "Exon 4 FERM domain mutation in SCID"],
      ["rs3213409", "A573V", "Exon 12 pseudokinase domain variant"],
      ["rs147552587", "V715I", "Exon 16 kinase domain mutation"]],
     [["Exon 4 (FERM domain)", "CCGCTGGATCCCTGAATACA", "TCCAGACACACCTGCAGTTT", "162 bp"],
      ["Exon 16 (kinase)", "GTGCCCACCTTCAGCTTAAC", "GACACAGCTTGAGCCTCACT", "198 bp"]]],

    ["KDR", "Kinase Insert Domain Receptor (VEGFR2)", "4q12", "56%",
     "Q472H, V297I, H472Q",
     "KDR encodes VEGFR2, the major receptor for VEGF-A that mediates endothelial cell proliferation, migration, and angiogenesis.",
     "KDR polymorphisms (Q472H, V297I) influence VEGF signaling and may affect anti-angiogenic therapy response in colorectal and renal cancers.",
     "Exons 11\u201326 (kinase domain)",
     ["Q472H polymorphism: The common Q472H variant in exon 11 affects VEGF binding and requires genotype-aware primer placement",
      "Elevated GC (56%): Exons 18\u201322 in the kinase insert region show high GC content requiring denaturant optimization",
      "Large extracellular domain: Seven immunoglobulin-like domains (exons 2\u201310) add complexity for full-length transcript amplification"],
     [["rs1870377", "Q472H", "Exon 11 Ig-like domain 7 polymorphism"],
      ["rs2305948", "V297I", "Exon 7 Ig-like domain 4 variant"]],
     [["Exon 11 (Q472H)", "CATCCACAGACTCCTAAGGG", "TCACTGGCAGACTGTCTGTG", "192 bp"],
      ["Exon 19 (kinase insert)", "GAGCAAGCTCGTCAATGGAC", "AGGTAGCGTGGTTGTGACAT", "208 bp"]]],

    ["KIT", "KIT Proto-Oncogene", "4q12", "53%",
     "D816V, D816H, V559D, W557-K558 del, N822K",
     "KIT encodes the receptor tyrosine kinase for stem cell factor that regulates hematopoietic stem cells, melanocytes, and germ cell development.",
     "D816V in the kinase activation loop (exon 17) and exon 11 juxtamembrane mutations are therapeutic targets in GIST and systemic mastocytosis.",
     "Exons 8\u201318 (JM domain, kinase domain, activation loop)",
     ["Multiple mutation hotspots: Exon 11 (JM domain), exon 13 (ATP pocket), exon 17 (activation loop) require three separate amplicons for full coverage",
      "Moderate GC (53%): Balanced GC with localized high-GC regions in exons 11 and 17 requiring Tm optimization",
      "Drug resistance mutations: Secondary T670I and D816V mutations emerge during imatinib/sunitinib therapy requiring sensitive detection"],
     [["rs121913507", "D816V", "Exon 17 activation loop in mastocytosis"],
      ["rs121913506", "V559D", "Exon 11 juxtamembrane GIST mutation"],
      ["rs3822214", "M541L", "Exon 10 common polymorphism"]],
     [["Exon 11 (JM domain)", "TGACCTGCATGCGACATCAT", "ACTGTGGTCCTTGAAGCACA", "215 bp"],
      ["Exon 17 (D816 region)", "GCCGCTGTGTTACGATCTTC", "GGCAAGAGAGCAATGACTCC", "198 bp"]]],
]

# Special skip mapping for genes with differently-named existing files
SPECIAL_SKIP = {
    "ERBB2": "her2-erbb2-primer-design.html",
}

def slug(symbol):
    return symbol.lower().replace("/", "-")

def generate_html(g):
    sym, name, chrom, gc, mutations, desc1, desc2, exons, challenges, snps, primer_pairs = g
    slug_name = slug(sym)
    filename = f"{slug_name}-primer-design.html"

    snp_items = "\n".join(
        f'        <li><strong>{s[0]}</strong> ({s[1]}) \u2014 {s[2]}</li>' for s in snps
    )
    chal_items = "\n".join(
        f'        <li><strong>{c.split(":")[0]}:</strong>{c.split(":", 1)[1] if ":" in c else c}</li>' for c in challenges
    )
    primer_rows = "\n".join(
        f'        <tr><td>{p[0]}</td><td>5\u2032-{p[1]}-3\u2032</td><td>5\u2032-{p[2]}-3\u2032</td><td>{p[3]}</td></tr>'
        for p in primer_pairs
    )

    # Determine GC-highlight column
    gc_num = int(gc.replace("%", ""))
    if gc_num >= 58:
        gc_col = f"GC-Rich Regions (\u226558%)"
        add_row = '<tr><td>PCR additive</td><td>Standard</td><td>Add 5\u201310% DMSO or betaine</td></tr>'
    elif gc_num <= 46:
        gc_col = "Low-GC / AT-Rich Regions"
        add_row = '<tr><td>PCR additive</td><td>Standard</td><td>Longer primers (24\u201328 nt), lower annealing T\u2098</td></tr>'
    else:
        gc_col = "Optimized Regions"
        add_row = '<tr><td>PCR additive</td><td>Standard</td><td>Optional 3\u20135% DMSO for problematic regions</td></tr>'

    return f'''<!DOCTYPE html>
<html lang="en-IN">
<head>
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','GTM-KRP5LLPR');</script>
<!-- End Google Tag Manager -->

  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Primer Design for {sym} \u2014 Validated PCR Primers | VigyanLLM</title>
  <meta name="description" content="Design validated PCR primers for {sym} ({name}) gene analysis. {desc1} GC content {gc}, SNP-aware design, and exon-specific primer pairs for {sym} mutation screening.">
  <meta name="keywords" content="{sym} primer design, {sym} PCR primers, {name.lower()} primers, {sym} mutation analysis, {sym} qPCR, {mutations.split(',')[0].strip()} primer">
  <link rel="canonical" href="https://vigyanllm.in/gene-prefers/{slug_name}-primer-design">
  <meta property="og:title" content="Primer Design for {sym} \u2014 Validated PCR Primers">
  <meta property="og:description" content="Validated PCR primers for {sym} with SNP-aware design and exon-specific targeting.">
  <meta property="og:type" content="article">
  <meta property="og:url" content="https://vigyanllm.in/gene-prefers/{slug_name}-primer-design">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=Plus+Jakarta+Sans:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
  <style>
    :root {{
  --navy: #0F172A;
  --navy-light: #1E293B;
  --white: #FFFFFF;
  --slate: #F8FAFC;
  --slate-border: #E2E8F0;
  --text: #0F172A;
  --text2: #475569;
  --muted: #94A3B8;
  --primary: #2563EB;
  --bio: #059669;
  --amber: #D97706;
  --accent: #22D3EE;
  --font-h: 'Plus Jakarta Sans', sans-serif;
  --font-b: 'Inter', sans-serif;
  --max-w: 1100px;
  --sec-p: 100px;
}}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    body {{ background: var(--white); color: var(--text); font-family: var(--font-b); line-height: 1.6; -webkit-font-smoothing: antialiased; }}
    a {{ text-decoration: none; color: inherit; transition: color 0.15s ease; }}
    .container {{ max-width: var(--max-w); margin: 0 auto; padding: 0 24px; }}
    section {{ padding: var(--sec-p) 0; }}
    nav {{ position: sticky; top: 0; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(8px); border-bottom: 1px solid var(--border); z-index: 1000; height: 72px; }}
    @media (max-width: 768px) {{ .nav-links {{ display: none; }} }}
    .article-body {{ padding: 40px 0; max-width: 800px; margin: 0 auto; }}
    .article-body h1 {{ font-family: var(--font-b); font-size: clamp(2rem, 4vw, 2.8rem); font-weight: 400; line-height: 1.1; margin-bottom: 16px; }}
    .article-body h2 {{ font-size: 24px; font-weight: 600; color: var(--text); margin: 40px 0 16px; }}
    .article-body h3 {{ font-size: 18px; font-weight: 600; color: var(--text); margin: 28px 0 12px; }}
    .article-body p {{ margin-bottom: 16px; color: var(--text2); font-size: 15px; line-height: 1.8; }}
    .article-body ul, .article-body ol {{ margin-left: 24px; margin-bottom: 16px; color: var(--text2); font-size: 15px; }}
    .article-body li {{ margin-bottom: 8px; }}
    .article-body strong {{ color: var(--text); }}
    .article-body a {{ color: var(--primary); text-decoration: none; }}
    .article-body table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
    .article-body th {{ background: var(--surface); color: var(--text); padding: 12px; text-align: left; border: 1px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .article-body td {{ padding: 12px; border: 1px solid var(--border); color: var(--text2); }}
    .article-body tr:nth-child(even) {{ background: var(--surface); }}
    .article-body .callout {{ background: var(--surface); border-left: 4px solid var(--primary); padding: 20px 24px; border-radius: 0 12px 12px 0; margin: 24px 0; }}
    .hero-gene {{ padding: 60px 0 30px; text-align: center; border-bottom: 1px solid var(--border); }}
    .hero-gene h1 {{ font-size: clamp(2rem, 4vw, 2.8rem); font-weight: 400; color: var(--text); margin-bottom: 12px; }}
    .hero-gene p {{ font-size: 16px; color: var(--text2); max-width: 650px; margin: 0 auto; }}
    .badge {{ display: inline-block; background: var(--surface); color: var(--primary); padding: 6px 16px; border-radius: 20px; font-size: 11px; font-weight: 600; border: 1px solid var(--border); margin-bottom: 16px; }}
    .cta-box {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 36px; text-align: center; margin: 40px 0; }}
    .cta-box h3 {{ font-size: 20px; color: var(--text); margin-bottom: 10px; }}
    .cta-box p {{ color: var(--text2); margin-bottom: 20px; }}
    .cta-btn {{ display: inline-block; padding: 14px 32px; background: var(--primary); color: #fff; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px; transition: background 0.2s; }}
    .cta-btn:hover {{ background: #0044ff; }}
  </style>
  <script type="application/ld+json">
  {{ "@context": "https://schema.org", "@type": "Article", "headline": "Primer Design for {sym} \u2014 Validated PCR Primers", "description": "Validated PCR primers for {sym} gene analysis with SNP-aware design and exon-specific targeting.", "datePublished": "2026-06-27", "dateModified": "2026-06-27", "author": {{ "@type": "Person", "name": "VigyanLLM Research Team", "jobTitle": "Research Team, VigyanLLM" }}, "publisher": {{ "@type": "Organization", "name": "VigyanLLM Private Limited" }}, "mainEntityOfPage": "https://vigyanllm.in/gene-prefers/{slug_name}-primer-design" }}
  </script>
  <script type="application/ld+json">
  {{ "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [ {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "https://vigyanllm.in/" }}, {{ "@type": "ListItem", "position": 2, "name": "Gene Primers", "item": "https://vigyanllm.in/gene-prefers/" }}, {{ "@type": "ListItem", "position": 3, "name": "{sym} Primer Design", "item": "https://vigyanllm.in/gene-prefers/{slug_name}-primer-design" }} ] }}
  </script>
</head>
<body>
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-KRP5LLPR"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->

  <nav>
    <div class="nav-inner" style="display:flex;justify-content:space-between;align-items:center;height:100%;max-width:var(--max-w);margin:0 auto;padding:0 24px">
      <a href="../index.html" class="logo" style="display:inline-flex;align-items:center;gap:9px;text-decoration:none;color:inherit">
        <img src="../logo.svg" alt="VigyanLLM Logo" style="width:36px;height:36px;border-radius:6px;background:#0d1117;padding:3px;object-fit:contain;flex-shrink:0">
        <span style="font-family:var(--font-b);font-size:20px;color:var(--text)">VigyanLLM</span>
      </a>
      <div class="nav-links" style="display:flex;gap:32px;align-items:center">
        <a href="../index.html" style="font-size:13px;color:var(--text2);font-weight:400">Home</a>
        <a href="../primer.html" style="font-size:13px;color:var(--primary);font-weight:500">VPrime 1.0 \u2197</a>
        <a href="../blog/index.html" style="font-size:13px;color:var(--text2);font-weight:400">Blog</a>
        <a href="../faq.html" style="font-size:13px;color:var(--text2);font-weight:400">FAQ</a>
        <a href="../about.html" style="font-size:13px;color:var(--text2);font-weight:400">About</a>
      </div>
      <div class="nav-right" style="display:flex;align-items:center;gap:24px">
        <button class="btn-nav" onclick="window.location.href='../primer.html'" style="border:1.5px solid var(--text);border-radius:6px;padding:10px 24px;font-size:13px;font-weight:500;background:transparent;cursor:pointer">Design Primers</button>
      </div>
    </div>
  </nav>

  <section class="hero-gene">
    <div class="container">
      <div class="badge">Gene-Specific \u00b7 SNP-Aware \u00b7 Research Use Only</div>
      <h1>{sym} Primer Design</h1>
      <p>PCR primer design guide for the {sym} ({name}) gene located on chromosome {chrom}. {desc1} Pre-configured parameters, SNP considerations, and validated primer design for {sym} analysis.</p>
    </div>
  </section>

  <div class="container">
    <article class="article-body">
      <h2>About {sym}</h2>
      <p>The <strong>{sym} gene</strong> ({name}) on chromosome {chrom} {desc2} Key targets include {exons} for comprehensive mutation screening.</p>
      <p><strong>Mutations:</strong> {mutations} | <strong>GC content:</strong> {gc} | <strong>Target exons:</strong> {exons}</p>

      <h2>{sym} Primer Design Challenges</h2>
      <ul>
{chal_items}
      </ul>

      <h2>Recommended Primer Design Parameters for {sym}</h2>
      <table>
        <tr><th>Parameter</th><th>Standard Exons</th><th>{gc_col}</th></tr>
        <tr><td>Primer length</td><td>20\u201322 nt</td><td>22\u201325 nt</td></tr>
        <tr><td>GC content</td><td>45\u201355%</td><td>50\u201360%</td></tr>
        <tr><td>Tm</td><td>58\u201362\u00b0C</td><td>60\u201365\u00b0C</td></tr>
        <tr><td>Amplicon size</td><td>150\u2013300 bp</td><td>180\u2013350 bp</td></tr>
        <tr><td>Annealing temp</td><td>58\u201360\u00b0C</td><td>60\u201364\u00b0C (touchdown)</td></tr>
{add_row}
      </table>

      <h2>Recommended Primer Sequences for {sym}</h2>
      <table>
        <tr><th>Target Region</th><th>Forward Primer (5\u2032\u21923\u2032)</th><th>Reverse Primer (5\u2032\u21923\u2032)</th><th>Amplicon</th></tr>
{primer_rows}
      </table>

      <h2>Key SNPs to Avoid in Primer Binding Sites</h2>
      <p>When designing {sym} primers, avoid these clinically significant variants:</p>
      <ul>
{snp_items}
      </ul>

      <div class="callout">
        <p><strong>Clinical Validation Required</strong><br>All {sym} primers designed with VigyanLLM are for research use only. Clinical diagnostic applications require additional wet-lab validation, Sanger sequencing confirmation, and regulatory approval before patient use.</p>
      </div>

      <div class="cta-box">
        <h3>Design {sym} Primers Now</h3>
        <p>Pre-configured with {sym}-specific parameters. Use our primer design, Tm calculator, and GC content tools for optimal results.</p>
        <div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap">
          <a href="../primer.html" class="cta-btn">Design {sym} Primers \u2192</a>
          <a href="../tm-calculator.html" style="display:inline-block;padding:14px 24px;background:var(--bio);color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px">Tm Calculator</a>
          <a href="../gc-calculator.html" style="display:inline-block;padding:14px 24px;background:var(--amber);color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px">GC Calculator</a>
        </div>
      </div>
    </article>
  </div>

  <footer style="padding:80px 0 40px;border-top:1px solid var(--border)">
    <div class="container">
      <div style="display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:60px;margin-bottom:60px">
        <div>
          <div style="font-family:var(--font-b);font-size:20px;margin-bottom:12px;display:flex;align-items:center;gap:10px">
            <img src="../logo.svg" alt="VigyanLLM" style="width:36px;height:36px;border-radius:6px;background:#0d1117;padding:3px;object-fit:contain">
            <span>VigyanLLM</span>
          </div>
          <p style="font-size:13px;color:var(--muted);margin-bottom:20px">Sovereign Healthcare &amp; Life Sciences AI</p>
          <div style="font-family:var(--font-b);font-size:13px;color:var(--primary)">contact@vigyanllm.in</div>
        </div>
        <div>
          <h5 style="font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:var(--text);margin-bottom:24px">Product</h5>
          <a href="../primer.html" style="display:block;font-size:13px;color:var(--text2);margin-bottom:14px">VPrime Primer Design</a>
          <a href="../primer-design.html" style="display:block;font-size:13px;color:var(--text2);margin-bottom:14px">Primer Design Guide</a>
          <a href="../tm-calculator.html" style="display:block;font-size:13px;color:var(--text2);margin-bottom:14px">Tm Calculator</a>
          <a href="../gc-calculator.html" style="display:block;font-size:13px;color:var(--text2);margin-bottom:14px">GC Content Calculator</a>
          <a href="../demo.html" style="display:block;font-size:13px;color:var(--text2);margin-bottom:14px">Demos</a>
        </div>
        <div>
          <h5 style="font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:var(--text);margin-bottom:24px">Resources</h5>
          <a href="../blog/index.html" style="display:block;font-size:13px;color:var(--text2);margin-bottom:14px">Blog</a>
          <a href="../faq.html" style="display:block;font-size:13px;color:var(--text2);margin-bottom:14px">FAQ</a>
          <a href="../about.html" style="display:block;font-size:13px;color:var(--text2);margin-bottom:14px">About</a>
        </div>
      </div>
      <div style="border-top:1px solid var(--border);padding-top:32px;display:flex;justify-content:space-between;font-size:12px;color:var(--muted)">
        <span>&copy; 2026 VigyanLLM Pvt. Ltd. \u00b7 Sovereign Research AI</span>
        <span>Built in India</span>
      </div>
    </div>
  </footer>
</body>
</html>'''

def main():
    existing = set(os.listdir(OUTPUT)) if os.path.exists(OUTPUT) else set()
    print(f"Found {len(existing)} existing files in {OUTPUT}")
    count = 0

    for g in GENES:
        sym = g[0]
        s = slug(sym)
        filename = f"{s}-primer-design.html"

        # Check special skip (e.g., ERBB2 -> her2-erbb2-primer-design.html)
        if sym in SPECIAL_SKIP and SPECIAL_SKIP[sym] in existing:
            print(f"  SKIP {sym} ({SPECIAL_SKIP[sym]} already exists)")
            continue

        if filename in existing:
            print(f"  SKIP {sym} ({filename} already exists)")
            continue

        html = generate_html(g)
        filepath = os.path.join(OUTPUT, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        count += 1
        print(f"  CREATED {filename}")

    print(f"\nTotal files created: {count}")

if __name__ == "__main__":
    main()
