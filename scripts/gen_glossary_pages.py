#!/usr/bin/env python3
"""Generate 5 new glossary pages by cloning the gene-expression template."""
import re, os

BASE = 'frontend/glossary/gene-expression.html'
OUT = 'frontend/glossary/'

PAGES = {}

PAGES['sanger-sequencing'] = {
    'slug': 'sanger-sequencing',
    'title': 'Sanger Sequencing: Definition, How It Works &amp; Applications',
    'meta_desc': 'Sanger sequencing is the gold-standard first-generation DNA sequencing method using chain-terminating dideoxynucleotides. Learn how it works and its applications.',
    'keywords': 'VigyanLLM, sanger sequencing, dideoxy sequencing, chain termination, capillary electrophoresis, DNA sequencing, first generation sequencing, fluorescence, bioinformatics, sequence analysis',
    'badge': 'Genomics &amp; Sequencing',
    'h1': 'Sanger sequencing',
    'breadcrumb': 'Sanger sequencing',
    'definition': '''<p><a href="/glossary/sanger-sequencing">Sanger sequencing</a>, also called chain-termination sequencing, is the classic first-generation method for reading DNA sequence. It uses DNA polymerase to copy a single-stranded template while incorporating a small fraction of fluorescently labeled <a href="/glossary/nucleotide">dideoxynucleotides</a> (ddNTPs). When a ddNTP is added, chain elongation stops, producing a nested set of fragments differing by one base. Size-based separation by capillary electrophoresis reveals the terminal base of each fragment, and the fluorescence signature reconstructs the exact order of bases. Modern instruments read up to ~1,000 bases per run with &gt;99.9% per-base accuracy, making Sanger sequencing the reference standard for validating variants found by high-throughput sequencing.</p>''',
    'practice': [
        'Confirming single-nucleotide variants (SNVs) and indels discovered by NGS before publication or clinical reporting',
        'Validating CRISPR edits, plasmid clones, and site-directed mutagenesis products for cloning workflows',
        'Sequencing amplicons of 300&ndash;1,000 bp from Sanger primers designed with balanced Tm and specificity checks',
        'Reading insert sequences in plasmids or PCR products when assembly of short reads is ambiguous',
        'Producing high-accuracy reference sequences for taxonomically novel organisms or barcoding (16S, COI) studies',
    ],
    'related': [('next-generation-sequencing','next-generation sequencing'), ('dna','DNA'), ('primer','primer'), ('nucleotide','nucleotide')],
    'faq': [
        ('What is Sanger sequencing?', 'Sanger sequencing is a DNA sequencing method based on chain-terminating dideoxynucleotides. DNA polymerase synthesizes complementary strands while randomly incorporating fluorescently labeled ddNTPs that stop extension. Separation by capillary electrophoresis generates a series of fragments whose terminal fluorescence reveals the DNA sequence base by base.'),
        ('What is the difference between Sanger sequencing and next-generation sequencing?', 'Sanger sequencing reads one ~300-1,000 base fragment at a time with very high accuracy, ideal for validating specific regions. Next-generation sequencing (NGS) processes millions of fragments in parallel for whole genomes or transcriptomes but at lower per-base accuracy. Sanger is often used to confirm NGS findings.'),
        ('Why is Sanger sequencing called the gold standard?', 'Sanger sequencing achieves greater than 99.9% per-base accuracy for single amplicons and is the method used to validate clinical variants. Its simplicity, low cost per reaction for targeted regions, and decades of benchmark data make it the reference against which other methods are measured.'),
        ('How does VigyanLLM support Sanger sequencing workflows?', 'VigyanLLM&#x27;s primer design pipeline produces Sanger-sequencing primers with optimized Tm balance, GC clamp, and specificity checks, and its PCR analysis tools help verify amplicons before capillary electrophoresis.'),
    ],
}

PAGES['sybr-green'] = {
    'slug': 'sybr-green',
    'title': 'SYBR Green: Definition, How It Works &amp; Applications in qPCR',
    'meta_desc': 'SYBR Green is a fluorescent DNA-binding dye used for real-time PCR detection of double-stranded DNA. Learn how it works, its advantages, and its limitations.',
    'keywords': 'VigyanLLM, SYBR green, qPCR, real-time PCR, DNA binding dye, intercalating dye, melt curve, fluorescence detection, gene expression, molecular biology',
    'badge': 'qPCR &amp; Detection',
    'h1': 'SYBR Green',
    'breadcrumb': 'SYBR Green',
    'definition': '''<p><a href="/glossary/sybr-green">SYBR Green</a> is a cyanine-based fluorescent dye that binds the minor groove of double-stranded DNA. In its unbound state the dye fluoresces weakly, but when it intercalates into double-stranded DNA its fluorescence increases by over 1,000-fold. In quantitative real-time PCR (<a href="/glossary/qpcr">qPCR</a>), SYBR Green fluorescence rises proportionally with each amplification cycle, allowing the reaction to be monitored in real time. Because the dye binds any double-stranded product — not just the specific target — primer specificity must be confirmed with a melt curve, where fluorescence is plotted against temperature to distinguish the intended amplicon from primer-dimers or non-specific products.</p>''',
    'practice': [
        'Quantifying gene expression by RT-qPCR using SYBR Green and the 2^(-delta-delta-Ct) method with validated reference genes',
        'Verifying primer specificity with dissociation (melt) curve analysis to detect primer-dimers and off-target amplicons',
        'Running high-throughput screening assays where SYBR Green offers a cheaper, probe-free alternative to hydrolysis probes',
        'Confirming pathogen detection in diagnostic PCR where a single sharp melt peak validates the target amplicon',
        'Designing qPCR primers that produce a single specific product with Tm 58-62 &deg;C for reliable SYBR Green quantification',
    ],
    'related': [('qpcr','qPCR'), ('taqman-probe','TaqMan probe'), ('primer','primer'), ('melting-temperature','melting temperature')],
    'faq': [
        ('What is SYBR Green in PCR?', 'SYBR Green is a fluorescent DNA-binding dye used in real-time PCR to detect double-stranded DNA. It emits strong fluorescence when bound to dsDNA and weak fluorescence when free in solution, allowing amplification to be monitored cycle by cycle.'),
        ('Why do SYBR Green assays require a melt curve?', 'SYBR Green binds any double-stranded DNA, including primer-dimers and non-specific amplicons. A melt curve distinguishes the specific product by its characteristic melting temperature, since different products melt at different temperatures. A single sharp peak confirms a clean, specific reaction.'),
        ('What is the difference between SYBR Green and TaqMan probes?', 'SYBR Green binds all double-stranded DNA non-specifically, is cheaper and simpler, but requires melt-curve validation. TaqMan probes hybridize to a specific internal sequence and are cleaved by Taq polymerase, providing sequence-specific detection without melt curves and enabling better multiplexing.'),
        ('How does VigyanLLM help with SYBR Green experiments?', 'VigyanLLM&#x27;s primer design tool generates qPCR primers with balanced Tm, GC clamp, and specificity checks, and its PCR analysis tools help verify that primer pairs produce a single specific product suitable for SYBR Green detection.'),
    ],
}

PAGES['taqman'] = {
    'slug': 'taqman',
    'title': 'TaqMan: Definition, How It Works &amp; Applications in qPCR',
    'meta_desc': 'TaqMan is a hydrolysis probe chemistry for sequence-specific qPCR detection. Learn how TaqMan assays work, their multiplexing power, and applications.',
    'keywords': 'VigyanLLM, TaqMan, hydrolysis probe, qPCR, real-time PCR, FRET, reporter dye, quencher, Taq polymerase, molecular diagnostics',
    'badge': 'qPCR &amp; Probes',
    'h1': 'TaqMan',
    'breadcrumb': 'TaqMan',
    'definition': '''<p><a href="/glossary/taqman">TaqMan</a> is a probe-based detection chemistry used in quantitative real-time PCR. A TaqMan probe is a short oligonucleotide labeled with a 5&#x27; fluorescent reporter dye and a 3&#x27; quencher that hybridizes to an internal region of the target amplicon. While the probe is intact, the quencher suppresses reporter fluorescence via FRET. During extension, <a href="/glossary/taq-polymerase">Taq polymerase</a>&#x27;s 5&#x27; to 3&#x27; exonuclease activity cleaves the probe, separating reporter from quencher and producing fluorescence proportional to amplified target. Because cleavage requires specific probe hybridization, TaqMan assays are more specific than DNA-binding dyes and support multiplexing of multiple targets in a single reaction.</p>''',
    'practice': [
        'Detecting pathogens such as SARS-CoV-2, HIV-1, and HBV with TaqMan-based viral load assays in clinical diagnostics',
        'Genotyping single-nucleotide polymorphisms (SNPs) using two allele-specific TaqMan probes with distinct reporter dyes',
        'Multiplexing up to 5-6 targets in one qPCR well using spectrally distinct fluorophores with cross-talk compensation',
        'Quantifying gene expression with high sensitivity, detecting as few as 1-10 target copies per reaction',
        'Measuring copy number variation (CNV) by comparing target TaqMan signal to a reference locus such as RNase P',
    ],
    'related': [('taqman-probe','TaqMan probe'), ('qpcr','qPCR'), ('sybr-green','SYBR Green'), ('probe-design','probe design')],
    'faq': [
        ('What is TaqMan assay?', 'A TaqMan assay is a real-time PCR method using a hydrolysis probe labeled with a reporter dye and quencher. Taq polymerase cleaves the probe during extension, generating fluorescence only when the specific target sequence is amplified, enabling highly specific quantification.'),
        ('How is TaqMan different from SYBR Green?', 'TaqMan uses a sequence-specific probe that must hybridize to the target, so it detects only the intended amplicon and needs no melt curve. SYBR Green binds any double-stranded DNA, is cheaper, but requires melt-curve validation for specificity.'),
        ('Why is TaqMan used for multiplexing?', 'TaqMan probes can carry spectrally distinct reporter dyes (FAM, VIC, ROX, etc.) while maintaining sequence specificity. This allows several targets to be measured simultaneously in a single reaction by separating fluorescence signals across channels.'),
        ('How does VigyanLLM design TaqMan assays?', 'VigyanLLM&#x27;s 24-step validated pipeline includes dedicated TaqMan probe design with Tm 5-10 &deg;C above primers, avoidance of 5&#x27; guanine, and purity requirements, generating audit-ready assay reports.'),
    ],
}

PAGES['alignment'] = {
    'slug': 'alignment',
    'title': 'Sequence Alignment: Definition, Algorithms &amp; Applications',
    'meta_desc': 'Sequence alignment is the process of arranging DNA, RNA, or protein sequences to identify regions of similarity. Learn about global and local alignment algorithms.',
    'keywords': 'VigyanLLM, sequence alignment, multiple sequence alignment, BLAST, global alignment, local alignment, Needleman-Wunsch, Smith-Waterman, bioinformatics, homology',
    'badge': 'Bioinformatics &amp; Analysis',
    'h1': 'Alignment',
    'breadcrumb': 'Sequence alignment',
    'definition': '''<p><a href="/glossary/alignment">Sequence alignment</a> is the arrangement of DNA, RNA, or protein sequences to identify regions of similarity that may reflect functional, structural, or evolutionary relationships. Alignments introduce gaps (insertions/deletions) to maximize matching positions and are scored using substitution matrices. Global alignment (Needleman-Wunsch) aligns entire sequences end to end, while local alignment (Smith-Waterman) finds the best matching substring, which is how <a href="/glossary/blast">BLAST</a> finds short homologous regions in large databases. Multiple sequence alignment (MSA) extends pairwise alignment to three or more sequences using progressive algorithms such as Clustal Omega or MUSCLE, and is fundamental to phylogenetics, conserved-region discovery, and primer design.</p>''',
    'practice': [
        'Finding homologous genes or proteins by running BLAST searches against nucleotide and protein databases',
        'Constructing multiple sequence alignments with Clustal Omega or MUSCLE to identify conserved domains and design degenerate primers',
        'Building phylogenetic trees from aligned sequences to infer evolutionary relationships between species',
        'Assessing conservation across species to predict functional importance of specific residues or nucleotides',
        'Checking primer specificity by aligning candidate primers against reference genomes to detect off-target matches',
    ],
    'related': [('blast','BLAST'), ('msa','MSA'), ('penalty-matrix','penalty matrix'), ('homology','homology')],
    'faq': [
        ('What is sequence alignment?', 'Sequence alignment arranges two or more DNA, RNA, or protein sequences to maximize matching positions while inserting gaps. It reveals similarity that reflects shared ancestry, structure, or function, and underpins BLAST searches, phylogenetics, and conserved-region analysis.'),
        ('What is the difference between global and local alignment?', 'Global alignment (Needleman-Wunsch) aligns entire sequences end to end and suits closely related, equal-length sequences. Local alignment (Smith-Waterman) finds the highest-scoring local match and suits divergent sequences with conserved regions, like domains shared between proteins.'),
        ('Why is multiple sequence alignment important?', 'Multiple sequence alignment (MSA) reveals positions conserved across many sequences, identifying functional domains, active sites, and motifs. It is essential for phylogenetic analysis, structural prediction, and designing primers or probes that work across species.'),
        ('How does VigyanLLM use sequence alignment?', 'VigyanLLM&#x27;s BLAST and MSA tools perform local and multiple sequence alignment for specificity checking and homology analysis, and its primer design pipeline aligns primers against reference genomes to flag off-target binding.'),
    ],
}

PAGES['e-value'] = {
    'slug': 'e-value',
    'title': 'E-value: Definition, Interpretation &amp; How to Use It in BLAST',
    'meta_desc': 'The E-value (expect value) reports the number of database hits expected by chance when searching a sequence. Learn how to interpret E-values in BLAST.',
    'keywords': 'VigyanLLM, E-value, expect value, BLAST, statistical significance, sequence similarity, bioinformatics, bit score, homology',
    'badge': 'Bioinformatics &amp; Statistics',
    'h1': 'E-value',
    'breadcrumb': 'E-value',
    'definition': '''<p>The <a href="/glossary/e-value">E-value</a> (expect value) is a statistical measure reported by <a href="/glossary/blast">BLAST</a> and other database search tools that estimates how many matches with a given score would be expected by chance alone in a database of the searched size. For example, an E-value of 1 means one such hit is expected by chance, while an E-value of 1&times;10&#8315;&#8309; means such a match would be expected less than once in a million equivalent searches. Lower E-values indicate more significant, less likely-to-be-random matches. The E-value depends on the query length, database size, and the substitution matrix used, so a match that is significant in a small database may be less so in a larger one.</p>''',
    'practice': [
        'Interpreting BLAST results by setting an E-value threshold (e.g., 1e-5) to separate homologous hits from random matches',
        'Comparing E-values across hits to rank candidate homologs by statistical confidence in database searches',
        'Adjusting E-value cutoffs for short queries, which need more stringent thresholds to avoid false positives',
        'Using E-value alongside bit score and percent identity to judge biological relevance, not just statistical significance',
        'Reporting E-values in publication-ready BLAST descriptions so readers can assess hit confidence',
    ],
    'related': [('blast','BLAST'), ('alignment','alignment'), ('bit-score','bit score'), ('homology','homology')],
    'faq': [
        ('What does E-value mean?', 'The E-value is the expected number of database hits with the same or better score that would occur by chance. An E-value of 0.05 means roughly 5 in 100 such matches are expected randomly; lower values mean greater significance.'),
        ('What is a good E-value for BLAST?', 'For most homology searches, an E-value threshold of 1e-5 or lower indicates a statistically significant match. Very strong homologs often give E-values near 0. Thresholds should be more stringent for short queries or very large databases.'),
        ('What is the difference between E-value and bit score?', 'The bit score is a normalized, database-independent measure of alignment quality. The E-value converts that score into a chance probability that accounts for database size. The bit score lets you compare matches across different databases, while the E-value reflects significance within a specific search.'),
        ('How does VigyanLLM report E-values?', 'VigyanLLM&#x27;s BLAST tool reports E-values, bit scores, and percent identity for every hit and uses E-value thresholds to highlight statistically significant matches in its specificity checks.'),
    ],
}

# ---- Build each page ----
for slug, data in PAGES.items():
    h = open(BASE, encoding='utf-8').read()

    # Title / meta
    h = h.replace('<title>Gene expression: Definition, How It Works &amp; Applications</title>',
                  '<title>%s</title>' % data['title'])
    h = h.replace('content="Gene expression converts genetic information into functional products (proteins or RNA), regulated at transcriptional,... Learn how VigyanLLM addresses."',
                  'content="%s"' % data['meta_desc'])
    h = h.replace('<meta name="keywords" content="VigyanLLM, molecular biology, amino acid chain, ribonucleic acid, coding sequence, gene transcript, bioinformatics, messenger rna, gene product, applications, polypeptide, definition, expression, transcript, receptor" />',
                  '<meta name="keywords" content="%s" />' % data['keywords'])
    h = h.replace('<meta property="og:title" content="Gene expression: Definition, How It Works &amp; Applications">',
                  '<meta property="og:title" content="%s">' % data['title'])
    h = h.replace('<meta property="og:description" content="Gene expression converts genetic information into functional products (proteins or RNA), regulated at transcriptional,... Learn how VigyanLLM addresses......">',
                  '<meta property="og:description" content="%s">' % data['meta_desc'])
    h = h.replace('<meta name="twitter:title" content="Gene expression: Definition, How It Works &amp; Applications">',
                  '<meta name="twitter:title" content="%s">' % data['title'])
    h = h.replace('<meta name="twitter:description" content="Gene expression converts genetic information into functional products (proteins or RNA), regulated at transcriptional,... Learn how VigyanLLM addresses......">',
                  '<meta name="twitter:description" content="%s">' % data['meta_desc'])

    # URLs
    for attr in ['canonical href', 'hreflang="en" href', 'hreflang="en-IN" href', 'hreflang="x-default" href', 'og:url" content']:
        h = h.replace('%s="https://www.vigyanllm.in/glossary/gene-expression"' % attr.split('"')[0],
                      '%s="https://www.vigyanllm.in/glossary/%s"' % (attr.split('"')[0], slug))
    h = h.replace('og-glossary-gene-expression.png', 'og-glossary-%s.png' % slug)
    h = h.replace('twitter:image" content="https://www.vigyanllm.in/og-glossary-%s.png' % slug,
                  'twitter:image" content="https://www.vigyanllm.in/og-glossary-%s.png' % slug)

    # Breadcrumb JSON-LD
    h = re.sub(r'"name": "Gene expression", "item": "https://www\.vigyanllm\.in/glossary/gene-expression"',
               '"name": "%s", "item": "https://www.vigyanllm.in/glossary/%s"' % (data['h1'], slug), h)
    h = h.replace('<span aria-current="page">gene expression</span>',
                  '<span aria-current="page">%s</span>' % data['breadcrumb'])

    # Term header
    h = h.replace('<h1>Gene expression</h1>', '<h1>%s</h1>' % data['h1'])
    h = h.replace('<span class="badge">Genetics &amp; Genomics</span>',
                  '<span class="badge">%s</span>' % data['badge'])

    # Definition section
    h = re.sub(r'<section class="section" id="definition">.*?</section>\n', 
               '<section class="section" id="definition">\n      <h2>Definition</h2>\n      %s\n    </section>\n' % data['definition'],
               h, count=1, flags=re.S)

    # In-practice section
    practice_items = ''.join('<li>%s</li>' % it for it in data['practice'])
    practice = ('<section class="section" id="in-practice">\n      <h2>In Practice</h2>\n'
                '<p style="margin-bottom:1rem;">%s is widely used in molecular biology and bioinformatics research. Key use cases include:</p>\n'
                '<ul class="practice-list">%s</ul>\n    </section>\n') % (data['h1'], practice_items)
    h = re.sub(r'<section class="section" id="in-practice">.*?</section>\n',
               practice, h, count=1, flags=re.S)

    # Related terms
    tags = ''.join('<a href="%s" class="related-tag">%s</a>\n' % (r[0], r[1]) for r in data['related'])
    rel = ('<section class="section" id="related-terms">\n      <h2>Related Terms</h2>\n'
           '      <div class="related-tags">\n%s      </div>\n    </section>\n') % tags
    h = re.sub(r'<section class="section" id="related-terms">.*?</section>\n',
               rel, h, count=1, flags=re.S)

    # FAQ section
    faq = '<section class="section" id="faq">\n      <h2>Frequently Asked Questions</h2>\n'
    for i, (q, a) in enumerate(data['faq']):
        faq += ('\n      <details class="faq-item"%s>\n'
                '        <summary class="faq-question" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">\n'
                '          <span itemprop="name">%s</span>\n'
                '        </summary>\n'
                '        <div class="faq-answer" itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">\n'
                '          <p itemprop="text">%s</p>\n'
                '        </div>\n'
                '      </details>\n') % (' open' if i == 0 else '', q, a)
    faq += '    </section>\n'
    h = re.sub(r'<section class="section" id="faq">.*?</section>\n',
               faq, h, count=1, flags=re.S)

    # VigyanLLM section
    h = re.sub(r'<p>VigyanLLM\'s validated pipeline addresses[^<]*</p>',
               '<p>VigyanLLM&#x27;s validated pipeline addresses %s through automated computational checks. Explore how the platform handles %s across its 24-step framework:</p>' % (data['h1'], data['h1']),
               h, count=1)

    # Build FAQPage JSON-LD from the inline FAQ
    faq_entities = []
    for q, a in data['faq']:
        faq_entities.append('{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer","text":"%s"}}' % (q, a))
    jsonld = '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[%s]}' % ','.join(faq_entities)
    # Replace the existing FAQPage JSON-LD script (first one)
    m = re.search(r'<script type="application/ld\+json">\{"@context":"https://schema.org","@type":"FAQPage".*?</script>', h, re.S)
    if m:
        h = h[:m.start()] + '<script type="application/ld+json">' + jsonld + '</script>' + h[m.end():]

    out = OUT + slug + '.html'
    open(out, 'w', encoding='utf-8').write(h)
    print('Generated', out)

print('Done.')
