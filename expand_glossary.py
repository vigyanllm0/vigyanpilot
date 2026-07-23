#!/usr/bin/env python3
"""Expand 65 old-template glossary pages to match the expanded template."""
import os, glob, re, html

GLOSSARY_DIR = 'frontend/glossary'

# Read an expanded file to use as structural template
with open(os.path.join(GLOSSARY_DIR, 'molecular-biology.html')) as f:
    EXPANDED_TEMPLATE = f.read()

def extract_section(content, start_marker, end_marker):
    """Extract text between markers."""
    start = content.find(start_marker)
    if start == -1:
        return ""
    start += len(start_marker)
    end = content.find(end_marker, start)
    if end == -1:
        return content[start:].strip()
    return content[start:end].strip()

def get_term_content(term, category, existing_def):
    """Generate content for a specific term."""
    t = term.lower().replace('-', ' ').replace('_', ' ')
    
    practice_items = {
        'adme': [
            'Predicting drug absorption and bioavailability in early-stage drug development',
            'Evaluating tissue distribution and protein binding of candidate compounds',
            'Assessing metabolic stability and identifying major metabolic pathways',
            'Characterizing elimination half-life and clearance rates in preclinical models',
            'Optimising lead compounds for improved pharmacokinetic properties',
            'Informing dose selection and dosing intervals for clinical trials',
        ],
        'alternative-splicing': [
            'Identifying tissue-specific splice variants in RNA-seq data',
            'Designing exon-junction spanning primers for RT-PCR validation',
            'Analyzing disease-associated splicing mutations in genetic disorders',
            'Characterising cancer-specific alternative splicing isoforms',
            'Predicting functional consequences of splicing alterations on protein domains',
            'Designing antisense oligonucleotides to correct aberrant splicing',
        ],
        'antibiotic-resistance': [
            'Detecting resistance genes in bacterial genomes using sequence alignment',
            'Designing PCR primers for multiplex resistance gene screening',
            'Tracking the spread of resistance plasmids in hospital outbreaks',
            'Predicting resistance from genomic data using machine learning classifiers',
            'Designing surveillance primers for wastewater monitoring of resistance genes',
            'Validating phenotypic resistance with genotypic marker detection',
        ],
        'antibody': [
            'Designing primers for antibody variable region cloning and sequencing',
            'Analyzing antibody-antigen binding interfaces using molecular docking',
            'Engineering recombinant antibodies with improved affinity and specificity',
            'Designing primers for monoclonal antibody expression construct assembly',
            'Predicting antibody CDR regions from sequence data',
            'Characterising antibody glycoprofiles using mass spectrometry',
        ],
        'bacteriophage': [
            'Designing primers for phage genome amplification and sequencing',
            'Analyzing phage-host interaction dynamics using genomic tools',
            'Designing phage therapy cocktails for antibiotic-resistant infections',
            'Characterising phage structural proteins using proteomics workflows',
            'Engineering phages for targeted bacterial killing in therapy',
            'Using phage display libraries for antibody discovery',
        ],
        'base-editing': [
            'Designing guide RNAs for cytosine base editors (CBE) with target windows',
            'Predicting off-target editing sites using computational tools',
            'Designing primers for Sanger sequencing validation of editing outcomes',
            'Optimising base editor construct delivery for cell-type-specific editing',
            'Analyzing editing efficiency and product purity by amplicon sequencing',
            'Designing adenine base editors (ABE) for A>G conversions in disease models',
        ],
        'bioavailability': [
            'Calculating oral bioavailability from pharmacokinetic data analysis',
            'Predicting intestinal absorption using in silico Caco-2 permeability models',
            'Assessing first-pass metabolism effects on systemic drug exposure',
            'Designing prodrug strategies to improve low-bioavailability compounds',
            'Evaluating food effects on drug absorption in clinical studies',
            'Optimising formulation strategies for enhanced solubility and dissolution',
        ],
        'cas12': [
            'Designing guide RNAs for Cas12a (Cpf1) with TTTV PAM requirements',
            'Using Cas12a for multi-target editing with a single CRISPR array',
            'Developing Cas12a-based DETECTR diagnostics for viral RNA detection',
            'Comparing Cas12a vs Cas9 editing efficiency for different genomic targets',
            'Designing primers for on-target editing validation by PCR and sequencing',
            'Applying Cas12a ribonucleoprotein complexes for reduced off-target editing',
        ],
        'cas13': [
            'Designing guide RNAs for Cas13a RNA targeting and knockdown',
            'Developing Cas13-based SHERLOCK diagnostic assays for pathogen detection',
            'Designing primers for isothermal amplification coupled with Cas13 detection',
            'Using Cas13 for programmable RNA editing without DNA modification',
            'Applying Cas13d for transcript knockdown in mammalian cells',
            'Quantifying Cas13 collateral cleavage activity for signal amplification',
        ],
        'cdna-library': [
            'Constructing full-length cDNA libraries from mRNA using reverse transcriptase',
            'Designing primers for library screening by colony PCR',
            'Normalising cDNA libraries to enrich for rare transcripts',
            'Preparing cDNA libraries for next-generation sequencing (RNA-seq)',
            'Designing vector-specific primers for library amplification and sequencing',
            'Characterising library complexity and insert size distribution',
        ],
        'cell-differentiation': [
            'Designing qPCR primers for lineage-specific marker gene expression analysis',
            'Profiling transcription factor networks driving differentiation using RNA-seq',
            'Analyzing chromatin accessibility changes during differentiation by ATAC-seq',
            'Designing guide RNAs for CRISPR-based perturbation of differentiation genes',
            'Characterising cell surface markers by flow cytometry during differentiation',
            'Designing primers for bisulfite PCR to study DNA methylation in differentiation',
        ],
        'cell-membrane': [
            'Designing primers for membrane protein expression construct cloning',
            'Analyzing membrane protein structures using molecular dynamics simulations',
            'Predicting transmembrane domains from amino acid sequences',
            'Designing primers for targeting signals and membrane localisation sequences',
            'Studying membrane fluidity and composition using lipidomics workflows',
            'Characterising receptor-ligand interactions at the cell membrane surface',
        ],
    }
    
    # Get practice items or generate generic ones
    items = practice_items.get(term, [])
    if not items:
        items = [
            f'Designing primers for {t} gene amplification and expression analysis by PCR',
            f'Analyzing {t} sequence conservation across species using multiple sequence alignment',
            f'Characterising {t} structural features using molecular modelling tools',
            f'Designing specificity-checking BLAST queries for {t} sequence identification',
            f'Studying {t} functional interactions using computational prediction methods',
            f'Validating {t} sequence variants by Sanger sequencing and primer extension',
        ]
    
    return items


def expand_page(filepath):
    """Expand a single old-template glossary page."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Skip if already expanded
    if 'id="in-practice"' in content and 'practice-list' in content:
        return False
    
    # Extract term name
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content)
    if not title_match:
        return False
    term = title_match.group(1).strip().lower()
    term_slug = term.replace(' ', '-')
    
    # Extract category
    cat_match = re.search(r'<span class="cat">(.*?)</span>', content)
    category = cat_match.group(1).strip() if cat_match else 'Molecular Biology'
    
    # Extract existing definition
    def_match = re.search(r'<div class="def-box">\s*<h2>Definition</h2>\s*<p>(.*?)</p>', content, re.DOTALL)
    existing_def = def_match.group(1).strip() if def_match else ''
    
    # Extract existing tags for related terms
    tag_links = re.findall(r'<a href="[^"]*glossary/([^"]+)"[^>]*class="tag"[^>]*>([^<]+)</a>', content)
    existing_related = [link.replace('https://www.vigyanllm.in/', '/') for _, link in tag_links]
    
    # Generate expanded definition (100-120 words)
    word_count = len(existing_def.split())
    if word_count < 80:
        # Expand the definition
        expanded_def = existing_def.rstrip('.')
        if term == 'adme':
            expanded_def = f'ADME (Absorption, Distribution, Metabolism, Excretion) describes the pharmacokinetic profile of a drug compound within an organism. Absorption refers to how a drug enters the bloodstream from its administration site. Distribution describes how the drug travels through body tissues and organs. Metabolism covers enzymatic biotransformation, primarily in the liver, that converts drugs into metabolites. Excretion eliminates the drug and its metabolites, mainly through urine or bile. Together, ADME properties determine drug bioavailability, half-life, dosing frequency, and potential toxicity — making ADME optimisation a critical phase in drug discovery and development pipelines.'
        elif term == 'cell-membrane':
            expanded_def = 'The cell membrane (plasma membrane) is a selectively permeable phospholipid bilayer that surrounds all living cells, separating the intracellular environment from the extracellular space. It is composed of phospholipids, cholesterol, proteins, and carbohydrates arranged in a fluid mosaic structure. The cell membrane regulates molecular transport through passive diffusion, facilitated transport, and active transport via membrane proteins. It also functions in cell signalling through receptor proteins, cell-cell recognition through glycoproteins, and structural support via the cytoskeleton. Membrane fluidity, maintained by cholesterol and unsaturated fatty acids, is essential for proper cellular function and adaptability to environmental changes.'
        elif term == 'dna-polymerase':
            expanded_def = 'DNA polymerase is an essential enzyme that synthesises new DNA strands by adding nucleotides complementary to a template DNA strand. It catalyses the formation of phosphodiester bonds between the 3\' hydroxyl group of the growing strand and the 5\' phosphate of the incoming dNTP. DNA polymerases require a primer with a free 3\' hydroxyl to initiate synthesis and always extend in the 5\' to 3\' direction. Many DNA polymerases also possess 3\'→5\' exonuclease (proofreading) activity that removes misincorporated nucleotides. In PCR, thermostable DNA polymerases such as Taq (Thermus aquaticus), Pfu, KAPA HiFi, and Q5 are used for their ability to withstand the high denaturation temperatures required for thermal cycling.'
        elif term == 'nested-pcr':
            expanded_def = 'Nested PCR is a modification of conventional PCR that uses two successive amplification reactions with two sets of primers to improve specificity and sensitivity. The first reaction uses outer primers flanking the target region. The second reaction uses inner primers (nested primers) that anneal within the first amplicon, amplifying a shorter internal fragment. This two-round approach dramatically reduces non-specific amplification because any products generated from off-target priming in the first round are unlikely to contain binding sites for the nested primers. Nested PCR is widely used for detecting low-abundance targets, ancient DNA analysis, pathogen detection in clinical samples, and single-cell gene expression studies where template quantity is limited.'
        elif term == 'real-time-pcr':
            expanded_def = 'Real-time PCR (quantitative PCR, qPCR) monitors DNA amplification during each thermal cycle using fluorescent reporter molecules, enabling quantification of starting template without post-PCR processing. Fluorescence increases proportionally with amplicon accumulation and is measured at each cycle to generate an amplification curve. SYBR Green dye binds double-stranded DNA non-specifically, while TaqMan probes use sequence-specific hydrolysis for higher specificity. The cycle at which fluorescence crosses a threshold (Cq or Ct) correlates inversely with initial template quantity. Absolute quantification uses standard curves while relative quantification compares target expression to reference genes using the ΔΔCt method. Real-time PCR is the gold standard for gene expression analysis, pathogen quantification, and GMO detection.'
        elif term == 'rna-polymerase':
            expanded_def = 'RNA polymerase is the enzyme responsible for transcribing DNA into RNA, catalysing the formation of phosphodiester bonds between ribonucleotides complementary to the DNA template strand. In eukaryotes, three RNA polymerases perform specialised functions: RNA polymerase I transcribes ribosomal RNA (rRNA), RNA polymerase II transcribes messenger RNA (mRNA) and most non-coding RNAs, and RNA polymerase III transcribes transfer RNA (tRNA) and 5S rRNA. RNA polymerase II requires a complex set of transcription factors to initiate transcription at promoter regions. In molecular biology, bacteriophage RNA polymerases (T7, SP6, T3) are widely used for in vitro transcription because they are highly processive and promoter-specific, enabling efficient synthesis of RNA probes, guide RNAs, and mRNA for therapeutic applications.'
        elif term == 'pcr':
            expanded_def = 'The polymerase chain reaction (PCR) is a molecular biology technique that exponentially amplifies a specific DNA sequence through repeated thermal cycling. PCR requires template DNA, two oligonucleotide primers flanking the target region, thermostable DNA polymerase, deoxynucleotide triphosphates (dNTPs), and buffer containing magnesium ions. Each cycle consists of denaturation (94–98°C, separates double-stranded DNA), annealing (50–65°C, primers bind complementary sequences), and extension (68–72°C, polymerase synthesises new strands). After 30–40 cycles, a single template molecule can generate over one billion copies. PCR has revolutionised molecular biology with applications in cloning, sequencing, genotyping, diagnostics, forensic analysis, and infectious disease detection.'
        elif term == 'plasmid':
            expanded_def = 'A plasmid is a small, circular, double-stranded DNA molecule that replicates independently of chromosomal DNA, primarily found in bacteria and some eukaryotes. Plasmids carry non-essential genes that can provide selective advantages such as antibiotic resistance, virulence factors, or metabolic capabilities. In molecular biology, plasmids are engineered as versatile cloning vectors containing key elements: an origin of replication (ori) for autonomous replication, a multiple cloning site (MCS) for inserting foreign DNA, a selectable marker (usually antibiotic resistance) for maintaining the plasmid in host cells, and often reporter genes for visual screening. Plasmids are the foundation of recombinant DNA technology, enabling gene cloning, protein expression, gene therapy, and DNA vaccine development.'
        elif term == 'reverse-transcriptase':
            expanded_def = 'Reverse transcriptase is an RNA-dependent DNA polymerase that converts single-stranded RNA into complementary DNA (cDNA), enabling the study of RNA molecules through DNA-based techniques. The enzyme possesses RNA-dependent DNA polymerase activity, which synthesises a DNA strand complementary to an RNA template, and RNase H activity, which degrades the RNA strand in RNA-DNA hybrids. Reverse transcriptase is essential for RT-PCR, enabling detection and quantification of RNA viruses including HIV and SARS-CoV-2, gene expression analysis, and cDNA library construction. Common reverse transcriptases include Moloney Murine Leukemia Virus (MMLV) reverse transcriptase, Avian Myeloblastosis Virus (AMV) reverse transcriptase, and engineered variants with improved thermostability, processivity, and reduced RNase H activity.'
        elif term == 'reverse-primer' or term == 'forward-primer':
            direction = 'reverse' if 'reverse' in term else 'forward'
            opp = 'forward' if direction == 'reverse' else 'reverse'
            expanded_def = f'The {direction} primer is one of two oligonucleotides required for PCR amplification, designed to anneal to the {direction} strand of the target DNA. In conventional PCR, the {direction} primer binds to the antisense strand and extends toward the {opp} primer binding site during each extension phase. The {direction} primer defines one end of the PCR amplicon and must be designed with careful attention to melting temperature (Tm), GC content, and 3\' stability. For successful PCR, the {direction} and {opp} primers should have similar Tm values (within 2–5°C), minimal self-complementarity to prevent hairpins and primer-dimer formation, and high specificity for the intended target sequence verified by BLAST analysis.'
        elif term == 'homologous-recombination':
            expanded_def = 'Homologous recombination (HR) is a conserved DNA repair mechanism that uses a homologous DNA template to precisely repair double-strand breaks (DSBs) with high fidelity. HR requires the presence of a sister chromatid or homologous template and is primarily active during the S and G2 phases of the cell cycle. The key catalytic protein is RAD51, which facilitates strand invasion and homology search. In CRISPR genome editing, HR can be harnessed for precise gene knock-in by supplying an exogenous donor repair template with homology arms flanking the edit site — a process called homology-directed repair (HDR). HDR efficiency varies by cell type and genomic locus, typically ranging from 1–20% in mammalian cells, making optimisation of donor template design and delivery critical.'
        else:
            expanded_def = f'{existing_def.rstrip(".")}. In molecular biology research, {term.replace("-", " ")} plays a crucial role in experimental design, data interpretation, and understanding fundamental biological processes. Researchers working with {term.replace("-", " ")} apply computational tools and molecular techniques to investigate its structure, function, and interactions within cellular systems.'
    else:
        expanded_def = existing_def
    
    # Generate the In Practice section
    items = get_term_content(term, category, existing_def)
    practice_items_html = '\n'.join(f'            <li>{item}</li>' for item in items)
    
    # Generate FAQ items
    faq_items = generate_faq(term, expanded_def)
    faq_html = '\n'.join(faq_items)
    
    # Generate related terms
    related = generate_related(term)
    related_html = '\n'.join(f'            <a href="../glossary/{r[0]}" class="related-tag">{r[1]}</a>' for r in related[:8])
    
    # Generate VigyanLLM application
    vigyanllm_text = generate_vigyanllm_app(term)
    
    # Build the new content
    new_content = build_expanded_page(term, term_slug, category, expanded_def.strip(), 
                                      practice_items_html, faq_html, related_html, vigyanllm_text)
    
    # Preserve nav, footer, head from original
    old_head_match = re.search(r'(.*?)<body', content, re.DOTALL)
    old_nav_match = re.search(r'(<header><nav.*?</nav></header>)', content, re.DOTALL)
    old_footer_match = re.search(r'(<footer>.*?</footer>)', content, re.DOTALL)
    
    if old_head_match and old_nav_match and old_footer_match:
        old_head = old_head_match.group(1)
        old_nav = old_nav_match.group(1)
        old_footer = old_footer_match.group(1)
        
        # Get scripts after footer
        after_footer = content.split('</footer>', 1)[1] if '</footer>' in content else ''
        
        result = old_head + '<body>\n' + old_nav + '\n' + new_content + '\n' + old_footer + after_footer
        with open(filepath, 'w') as f:
            f.write(result)
        return True
    
    return False


def generate_faq(term, definition):
    """Generate 3 FAQ Q&A pairs."""
    t = term.replace('-', ' ')
    
    if term == 'adme':
        return [
            '          <details class="faq-item" open>\n            <summary class="faq-question">Why is ADME important in drug discovery?</summary>\n            <div class="faq-answer"><p>ADME profiling is critical because poor pharmacokinetics account for approximately 40% of drug candidate failures in clinical development. Understanding absorption, distribution, metabolism, and excretion early in discovery helps select compounds with favourable drug-like properties, reducing late-stage attrition and development costs.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">What is the difference between ADME and pharmacokinetics?</summary>\n            <div class="faq-answer"><p>ADME describes the four processes that determine drug disposition, while pharmacokinetics (PK) is the quantitative study of these processes over time. PK parameters like Cmax, Tmax, half-life, AUC, and clearance are derived from measuring drug concentrations in biological samples at multiple time points following administration.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">How are ADME properties predicted computationally?</summary>\n            <div class="faq-answer"><p>Computational ADME prediction uses quantitative structure-activity relationship (QSAR) models trained on experimental data to predict properties like Caco-2 permeability, human intestinal absorption, plasma protein binding, CYP450 inhibition, and P-glycoprotein substrate status. Lipinski\'s Rule of Five provides a simple filter for oral bioavailability prediction.</p></div>\n          </details>',
        ]
    elif term == 'cell-membrane':
        return [
            '          <details class="faq-item" open>\n            <summary class="faq-question">What is the fluid mosaic model of the cell membrane?</summary>\n            <div class="faq-answer"><p>The fluid mosaic model, proposed by Singer and Nicolson in 1972, describes the cell membrane as a two-dimensional fluid of phospholipids and cholesterol in which proteins are embedded and can diffuse laterally. The membrane is asymmetric, with different lipid and protein compositions in the inner and outer leaflets. This fluidity is essential for membrane fusion, vesicle trafficking, and protein function.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">How do molecules cross the cell membrane?</summary>\n            <div class="faq-answer"><p>Small non-polar molecules (O2, CO2) diffuse freely across the membrane. Small polar molecules (water, ethanol) pass through with some restriction. Ions and large polar molecules require transport proteins: channel proteins form aqueous pores for passive diffusion, carrier proteins undergo conformational changes for facilitated diffusion, and pumps use ATP for active transport against concentration gradients.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">What is membrane potential and how is it maintained?</summary>\n            <div class="faq-answer"><p>Membrane potential is the electrical voltage difference across the cell membrane, typically -60 to -80 mV in animal cells (inside negative). It is maintained by the Na+/K+-ATPase pump, which exports 3 Na+ and imports 2 K+ per ATP hydrolysed, and by selective ion channels that allow K+ to leak down its concentration gradient. Membrane potential is critical for nerve impulse transmission and ion-coupled transport.</p></div>\n          </details>',
        ]
    elif term == 'dna-polymerase':
        return [
            '          <details class="faq-item" open>\n            <summary class="faq-question">What is the difference between Taq and high-fidelity DNA polymerases?</summary>\n            <div class="faq-answer"><p>Taq polymerase has no proofreading (3\'→5\' exonuclease) activity and an error rate of ~3 × 10⁻⁵ per base, while high-fidelity polymerases like Pfu, KAPA HiFi, and Q5 possess proofreading activity with error rates of 1 × 10⁻⁶ to 5 × 10⁻⁷ per base. For cloning and sequencing applications where accuracy is critical, high-fidelity polymerases are recommended, while Taq is suitable for routine genotyping PCR.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">Why do DNA polymerases require a primer?</summary>\n            <div class="faq-answer"><p>DNA polymerases require a free 3\' hydroxyl group to add nucleotides because they catalyse nucleophilic attack of the 3\' OH on the alpha phosphate of the incoming dNTP. They cannot initiate DNA synthesis de novo from free nucleotides. This is why PCR uses oligonucleotide primers that provide the necessary 3\' hydroxyl for polymerase extension.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">What is the optimal extension temperature for different DNA polymerases?</summary>\n            <div class="faq-answer"><p>Most DNA polymerases have optimal extension at 72°C, but there are exceptions: Taq works optimally at 72°C with an extension rate of ~1 kb/min, Pfu at 72°C at ~0.5 kb/min, KAPA HiFi at 72°C at ~1 kb/min, and LongAmp at 68°C at ~1.5 kb/min. Extension time should be calculated based on polymerase extension rate and target amplicon length.</p></div>\n          </details>',
        ]
    elif term == 'nested-pcr':
        return [
            '          <details class="faq-item" open>\n            <summary class="faq-question">When should nested PCR be used instead of conventional PCR?</summary>\n            <div class="faq-answer"><p>Nested PCR is preferred when template quantity is very low (single-cell analysis, ancient DNA, liquid biopsies), when sample quality is poor (formalin-fixed paraffin-embedded tissue), or when high specificity is essential despite potential cross-reactivity. It is also valuable for detecting low-abundance pathogens in clinical samples where conventional PCR may produce false negatives.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">What are the limitations of nested PCR?</summary>\n            <div class="faq-answer"><p>Nested PCR has increased contamination risk due to the two-round amplification requiring tube opening between rounds, longer total run time (3-4 hours vs 1-2 hours for conventional PCR), and higher reagent costs. These limitations have led many laboratories to replace nested PCR with real-time PCR using probe-based detection for quantitative applications.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">How should nested PCR primers be designed?</summary>\n            <div class="faq-answer"><p>Outer primers should amplify a product of 500-1500 bp with standard design parameters. Inner (nested) primers should amplify a product of 150-400 bp positioned within the outer amplicon, ideally with at least 50 bp overlap from each outer primer binding site. All four primers should be checked for cross-dimer formation, particularly between outer and inner primer pairs.</p></div>\n          </details>',
        ]
    elif term == 'real-time-pcr':
        return [
            '          <details class="faq-item" open>\n            <summary class="faq-question">What is the difference between SYBR Green and TaqMan qPCR?</summary>\n            <div class="faq-answer"><p>SYBR Green is a double-stranded DNA binding dye that fluoresces when bound to any dsDNA, including primer-dimers and non-specific products. TaqMan probes are sequence-specific hydrolysis probes that release a fluorescent signal only when the specific target is amplified, providing higher specificity. SYBR Green is cheaper and simpler, while TaqMan enables multiplexing with different fluorophores.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">What is the ΔΔCt method for relative quantification?</summary>\n            <div class="faq-answer"><p>The ΔΔCt method calculates relative gene expression by normalising the target gene Ct to a reference (housekeeping) gene Ct (ΔCt), then comparing treated vs control groups (ΔΔCt = ΔCt_treated − ΔCt_control). Fold change = 2^(−ΔΔCt). This method assumes both target and reference genes have approximately 100% amplification efficiency. For efficiency-corrected quantification, standard curves for each primer pair are required.</p></div>\n          </details>',
            '          <details class="faq-item">\n            <summary class="faq-question">What are the MIQE guidelines for qPCR?</summary>\n            <div class="faq-answer"><p>The Minimum Information for Publication of Quantitative Real-Time PCR Experiments (MIQE) guidelines, published by Bustin et al. in 2009, establish standards for qPCR experimental design and reporting. Key requirements include: reporting of reference gene stability validation, amplification efficiency for each primer pair, proper sample size and statistical methods, RNA integrity numbers, and complete reagent and cycling conditions for reproducibility.</p></div>\n          </details>',
        ]
    else:
        # Generic FAQ generation
        return [
            f'          <details class="faq-item" open>\n            <summary class="faq-question">What is {t} and why is it important in molecular biology?</summary>\n            <div class="faq-answer"><p>{definition[:200].rstrip(".")}. Researchers must understand {t} principles when designing experiments and interpreting results in genomics, transcriptomics, and molecular diagnostics.</p></div>\n          </details>',
            f'          <details class="faq-item">\n            <summary class="faq-question">How is {t} used in bioinformatics workflows?</summary>\n            <div class="faq-answer"><p>In bioinformatics, {t} is applied in sequence analysis, structural prediction, and functional annotation workflows. Computational tools for {t} analysis include sequence alignment algorithms, machine learning classifiers, and molecular modelling packages that help researchers interpret biological data at scale.</p></div>\n          </details>',
            f'          <details class="faq-item">\n            <summary class="faq-question">What are common challenges when working with {t}?</summary>\n            <div class="faq-answer"><p>Common challenges include data quality issues, standardisation across platforms, interpretation of complex results, and integration of {t} data with other omics layers. Best practices include using validated protocols, including appropriate controls, and applying statistical methods appropriate for the specific experimental design and data type.</p></div>\n          </details>',
        ]


def generate_related(term):
    """Generate related terms."""
    related_map = {
        'alternative-splicing': [('exon', 'exon'), ('intron', 'intron'), ('rna-splicing', 'RNA splicing'), ('transcriptome', 'transcriptome'), ('mrna', 'mRNA'), ('gene-expression', 'gene expression')],
        'antibiotic-resistance': [('plasmid', 'plasmid'), ('mutation', 'mutation'), ('horizontal-gene-transfer', 'horizontal gene transfer'), ('pcr', 'PCR'), ('bacteriophage', 'bacteriophage'), ('genome', 'genome')],
        'cell-membrane': [('cell', 'cell'), ('protein', 'protein'), ('lipid-bilayer', 'lipid bilayer'), ('receptor', 'receptor'), ('signal-transduction', 'signal transduction'), ('endocytosis', 'endocytosis')],
        'dna-polymerase': [('taq-polymerase', 'Taq polymerase'), ('pcr', 'PCR'), ('primer', 'primer'), ('dna', 'DNA'), ('proofreading', 'proofreading'), ('extension', 'extension')],
        'nested-pcr': [('pcr', 'PCR'), ('primer-design', 'primer design'), ('annealing-temperature', 'annealing temperature'), ('taq-polymerase', 'Taq polymerase'), ('amplicon', 'amplicon'), ('touchdown-pcr', 'touchdown PCR')],
        'real-time-pcr': [('qpcr', 'qPCR'), ('taqman-probe', 'TaqMan probe'), ('melting-temperature', 'melting temperature'), ('rt-pcr', 'RT-PCR'), ('digital-pcr', 'digital PCR'), ('gene-expression', 'gene expression')],
        'rna-polymerase': [('transcription', 'transcription'), ('promoter', 'promoter'), ('mrna', 'mRNA'), ('rna', 'RNA'), ('dna', 'DNA'), ('translation', 'translation')],
        'pcr': [('primer', 'primer'), ('taq-polymerase', 'Taq polymerase'), ('annealing-temperature', 'annealing temperature'), ('amplicon', 'amplicon'), ('thermal-cycler', 'thermal cycler'), ('gel-electrophoresis', 'gel electrophoresis')],
        'plasmid': [('cloning', 'cloning'), ('transformation', 'transformation'), ('antibiotic-resistance', 'antibiotic resistance'), ('origin-of-replication', 'origin of replication'), ('vector', 'vector'), ('recombinant-dna', 'recombinant DNA')],
    }
    default = [
        ('pcr', 'PCR'), ('primer-design', 'primer design'), ('dna', 'DNA'), 
        ('rna', 'RNA'), ('gene-expression', 'gene expression'), ('sequencing', 'sequencing')
    ]
    return related_map.get(term, default)


def generate_vigyanllm_app(term):
    """Generate VigyanLLM application text."""
    t = term.replace('-', ' ')
    return f'<p>VigyanLLM supports researchers working with {t} through its integrated suite of bioinformatics tools. The platform provides automated primer design with 22-step biophysical validation, BLAST sequence search for specificity checking, and a comprehensive PCR analysis module. Researchers can design, validate, and order primers for {t} applications using the VigyanLLM pipeline, with audit-ready reporting for publication and compliance.</p>'


def build_expanded_page(term, term_slug, category, definition, practice_html, faq_html, related_html, vigyanllm_text):
    """Build the expanded content section."""
    return f'''
<div class="page-content" style="max-width:var(--max-w);margin:0 auto;padding:0 24px">
  
  <nav class="breadcrumb" aria-label="Breadcrumb">
    <a href="/index">Home</a>
    <span class="sep">/</span>
    <a href="/glossary">Glossary</a>
    <span class="sep">/</span>
    <span>{term}</span>
  </nav>
  
  <header class="term-header">
    <h1>{term}</h1>
    <div class="term-meta">
      <span class="badge">{category}</span>
      <span class="badge">Schema: DefinedTerm</span>
    </div>
  </header>
  
  <section class="section" id="definition">
    <h2>Definition</h2>
    <p>{definition}</p>
  </section>
  
  <section class="section" id="in-practice">
    <h2>In Practice</h2>
    <p style="margin-bottom:1rem;">{category} is central to molecular biology research and clinical applications. Key use cases include:</p>
    <ul class="practice-list">
{practice_html}
    </ul>
  </section>
  
  <section class="section" id="related-terms">
    <h2>Related Terms</h2>
    <div class="related-tags">
{related_html}
    </div>
  </section>
  
  <section class="section" id="faq">
    <h2>Frequently Asked Questions</h2>
{faq_html}
  </section>
  
  <section class="section vigyanllm-section" id="vigyanllm-application">
    <h2>VigyanLLM Application</h2>
    {vigyanllm_text}
    <div class="hub-links">
      <a href="../biomedical-ai-platform" class="hub-link primary-hub">Explore on VigyanLLM &rarr;</a>
      <a href="../primer" class="hub-link">Primer Design Tool &rarr;</a>
      <a href="../primer-design-best-practices" class="hub-link">Primer Design Best Practices &rarr;</a>
    </div>
  </section>

</div>
'''


def main():
    files = sorted(glob.glob(os.path.join(GLOSSARY_DIR, '*.html')))
    count = 0
    for filepath in files:
        if expand_page(filepath):
            count += 1
            print(f"  Expanded: {os.path.basename(filepath)}")
    print(f"\nTotal expanded: {count} / {len(files)}")


if __name__ == '__main__':
    main()
