#!/usr/bin/env python3
"""
Comprehensive SEO/AEO/GEO/LLMO Fix Script
==========================================
Per-page audit and fix for all 412+ HTML files.
"""

import os, re, json, glob, copy
from collections import defaultdict

FRONTEND = os.path.join(os.path.dirname(__file__), "frontend")
BRAND = "VigyanLLM"
BRAND_URL = "https://vigyanllm.in"

# ── NLP Synonym Database (domain-specific) ────────────────────────────────
TOPIC_SYNONYMS = {
    "pcr": {"polymerase chain reaction", "dna amplification", "target enrichment", "molecular copying", "thermal cycling", "gene amplification", "nucleic acid amplification"},
    "primer": {"oligonucleotide", "primer pair", "forward primer", "reverse primer", "oligo", "synthetic dna", "pcr primer"},
    "primer design": {"primer design", "oligo design", "primer selection", "assay design", "pcr assay design", "primer engineering", "primer optimization"},
    "blast": {"basic local alignment search tool", "sequence alignment", "homology search", "sequence similarity", "alignment search", "nucleotide blast", "blastn"},
    "msa": {"multiple sequence alignment", "sequence alignment", "phylogenetic alignment", "multi-sequence comparison", "protein alignment", "nucleotide alignment"},
    "crispr": {"clustered regularly interspaced short palindromic repeats", "genome editing", "gene editing", "crispr-cas9", "grna design", "genome engineering"},
    "docking": {"molecular docking", "ligand-protein binding", "drug docking", "protein-ligand interaction", "binding affinity", "virtual screening"},
    "qpcr": {"quantitative pcr", "real-time pcr", "gene expression analysis", "rt-qpcr", "pcr quantification", "dna quantification"},
    "dna": {"deoxyribonucleic acid", "genetic material", "double helix", "nucleotide sequence", "genome", "genetic code"},
    "rna": {"ribonucleic acid", "messenger rna", "transcript", "coding sequence", "gene transcript", "mrna"},
    "protein": {"polypeptide", "amino acid chain", "gene product", "peptide", "enzyme", "receptor"},
    "bioinformatics": {"computational biology", "genomic analysis", "sequence analysis", "biological data science", "computational genomics", "in silico biology"},
    "genomics": {"genome analysis", "genomic sequencing", "dna sequencing", "whole genome", "genomic data", "genome research"},
    "ai": {"artificial intelligence", "machine learning", "deep learning", "neural network", "llm", "large language model", "multi-agent system", "intelligent system"},
    "thermodynamics": {"delta g", "free energy", "melting temperature", "tm calculation", "nearest neighbor", "santalucia", "gibbs free energy", "enthalpy", "entropy"},
    "snp": {"single nucleotide polymorphism", "genetic variant", "point mutation", "snv", "single nucleotide variant", "variation", "polymorphism"},
    "pipeline": {"workflow", "analysis pipeline", "computational pipeline", "bioinformatics pipeline", "validation pipeline", "processing workflow"},
    "gguf": {"gpt-generated unified format", "quantized model", "local inference", "onnx", "tensor rt", "model optimization", "inference engine"},
    "docker": {"container", "containerization", "docker container", "docker image", "docker deployment", "containerized deployment"},
    "sovereign": {"data sovereignty", "self-hosted", "on-premise", "on-premises", "self-contained", "air-gapped", "offline", "local deployment"},
    "molecular biology": {"molecular genetics", "biochemistry", "cell biology", "gene regulation", "molecular science", "genetic engineering"},
    "ngs": {"next-generation sequencing", "high-throughput sequencing", "massively parallel sequencing", "deep sequencing", "targeted sequencing", "amplicon sequencing"},
    "variant": {"mutation", "genetic variation", "sequence variant", "genomic variant", "somatic mutation", "germline mutation"},
    "pharmacogenomics": {"pgx", "drug-gene interaction", "personalized medicine", "precision medicine", "pharmacogenetics", "drug response genetics"},
    "biomarker": {"biological marker", "molecular marker", "genetic marker", "diagnostic marker", "prognostic marker", "biomarker discovery"},
    "clinical": {"diagnostic", "clinical testing", "medical genetics", "molecular diagnostics", "clinical genomics", "pathology"},
    "validated": {"certified", "verified", "tested", "qualified", "approved", "benchmarked", "proven"},
    "multiplex": {"multi-target", "multiplex assay", "panel design", "multi-analyte", "high-plex", "multiplexed pcr"},
    "hipaa": {"health insurance portability and accountability act", "data privacy", "compliance", "phi protection", "health data privacy", "patient data protection"},
    "gdpr": {"general data protection regulation", "data privacy", "eu privacy", "data protection", "privacy regulation"},
    "dpdp": {"digital personal data protection act", "india data protection", "indian privacy law", "data protection act 2023"},
}

# ── Page classification ───────────────────────────────────────────────────
def classify_page(filepath):
    rel = os.path.relpath(filepath, FRONTEND)
    fname = os.path.basename(rel)
    if rel.startswith("glossary/"):
        return "glossary_def"
    if rel.startswith("blog/"):
        return "blog_article"
    if rel.startswith("gene-prefers/"):
        return "gene_tool"
    if rel.startswith("landing-pages/"):
        return "landing"
    if rel.startswith("hub/"):
        return "hub"
    if rel.startswith("tools/"):
        return "tool"
    if rel.startswith("docs/"):
        return "docs"
    if fname in {"primer.html", "blast.html", "msa.html", "search.html",
                  "pcr-analysis.html", "crispr-analysis.html", "protein-docking.html",
                  "tm-calculator.html", "gc-calculator.html", "dna-to-rna.html",
                  "primer-design.html", "primer-design-pipeline.html",
                  "multiplex-primer-design.html", "primer3-alternative.html",
                  "primer-blast-alternative.html"}:
        return "tool"
    if fname in {"platform.html", "architecture.html", "problem.html",
                  "solution.html", "compare.html", "roadmap.html"}:
        return "platform"
    if fname in {"validated-primer-design.html", "validated-primer-design-report.html",
                  "security.html", "privacy.html", "terms.html", "faq.html",
                  "about.html", "cite.html", "contact.html", "login.html",
                  "changelog.html", "sitemap.html", "cookies.html", "refund.html",
                  "payment-success.html", "payment-failed.html",
                  "academic-partnership.html", "Learning-vigyanllm.html",
                  "hipaa-compliant-genomics.html", "molecular-docking-guide.html",
                  "biomedical-ai-platform.html", "demo.html",
                  "primer-design-best-practices.html", "primer-design-thermodynamics.html",
                  "primer-design-india.html", "primer-blast-specificity.html",
                  "primer-3-alternative.html", "dna-3d.html",
                  "qpcr-primer-design.html", "ai-crispr-analysis.html",
                  "404.html", "db-redirect.html", "p.html"}:
        return "info"
    return "webpage"


def page_title(rel):
    """Derive a human-readable title from the file path."""
    base = os.path.basename(rel).replace(".html", "").replace("-", " ").title()
    return base.replace("Dna", "DNA").replace("Rna", "RNA") \
               .replace("Pcr", "PCR").replace("Qpcr", "qPCR") \
               .replace("Tm ", "Tm ").replace("Gc ", "GC ") \
               .replace("Msa", "MSA").replace("Blast", "BLAST") \
               .replace("Crispr", "CRISPR").replace("Snp", "SNP") \
               .replace("Ngs", "NGS").replace("Hipaa", "HIPAA") \
               .replace("Gdpr", "GDPR").replace("Ai ", "AI ")


# ── Keyword Extraction ────────────────────────────────────────────────────
def extract_keywords(title, description, content_lower):
    """Generate NLP-enriched keyword list from page content."""
    keywords = set()
    title_lower = title.lower()
    desc_lower = (description or "").lower()
    combined = f"{title_lower} {desc_lower} {content_lower[:2000]}"

    # Add brand
    keywords.add("VigyanLLM")
    keywords.add("bioinformatics")
    keywords.add("molecular biology")
    keywords.add("AI")

    # Match topics from synonym database
    for topic, syns in TOPIC_SYNONYMS.items():
        if topic in combined:
            keywords.add(topic)
            keywords.update(syns)

    # Extract capitalized technical terms
    for match in re.finditer(r'\b([A-Z]{2,10})\b', title):
        keywords.add(match.group(1))

    # Add page-specific terms from title
    words = re.findall(r'[A-Za-z][a-z]+', title)
    for w in words[:5]:
        if len(w) > 3:
            keywords.add(w.lower())

    # Ensure brand is first
    result = ["VigyanLLM"]
    for k in sorted(keywords - {"VigyanLLM"}, key=lambda x: -len(x)):
        result.append(k)
    return result[:20]


def get_page_nlp_tags(filepath, title, description):
    """Get NLP-enriched keywords for a specific page."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    content_lower = content.lower()
    return extract_keywords(title, description, content_lower)


# ── URL helpers ────────────────────────────────────────────────────────────
def get_clean_url(filepath):
    rel = os.path.relpath(filepath, FRONTEND)
    if rel == "index.html":
        return BRAND_URL
    no_ext = rel[:-5] if rel.endswith(".html") else rel
    return f"{BRAND_URL}/{no_ext}"


def get_og_image(filepath, title=""):
    """Derive page-specific OG image."""
    rel = os.path.relpath(filepath, FRONTEND)
    fname = os.path.basename(rel).replace(".html", "")
    # Try page-specific og image first
    candidate = f"{BRAND_URL}/og-{fname}.png"
    return candidate


# ── Individual Fix Functions ───────────────────────────────────────────────
def fix_step_count(html):
    """Replace 22-step with 24-step in all visible and meta content."""
    # Meta tags
    html = re.sub(r'22-?[Ss]tep', '24-step', html)
    html = re.sub(r'22[-\s]step', '24-step', html)
    html = re.sub(r'\b22[\s-]?step\b', '24-step', html)
    # "22 step" without hyphen
    html = re.sub(r'\b22 step\b', '24-step', html)
    return html


def fix_main_wrapper(html):
    """Properly position <main> around content, excluding <footer>."""
    body_match = re.search(r'<body[^>]*>', html)
    if not body_match:
        return html
    body_end = body_match.end()

    # ── Step 1: Strip ALL existing <main> and </main> tags ──
    html = re.sub(r'<main[^>]*>', '', html)
    html = re.sub(r'</main>', '', html)

    # ── Step 2: Remove stray '>' between <body> and first real tag ──
    # Pattern: <body> followed by whitespace, a lone '>', then more whitespace
    html = re.sub(r'(<body[^>]*>)\s*>\s*', r'\1\n', html, count=1)

    # ── Step 3: Recalculate positions ──
    body_end = re.search(r'<body[^>]*>', html).end()
    has_footer = "</footer>" in html

    # ── Step 4: Reinsert <main> tags properly ──
    if has_footer:
        last_footer_close = html.rfind("</footer>")
        footer_open = html.rfind("<footer", 0, last_footer_close)
        if footer_open != -1:
            html = html[:body_end] + "<main>\n" + html[body_end:footer_open] + "\n</main>\n" + html[footer_open:]
        else:
            html = html[:body_end] + "<main>\n" + html[body_end:last_footer_close] + "\n</main>\n" + html[last_footer_close:]
    else:
        html = html[:body_end] + "<main>\n" + html[body_end:] + "\n</main>"

    return html


def ensure_meta_tags(html, filepath, keywords_list):
    """Ensure all required meta tags exist with proper values."""
    clean_url = get_clean_url(filepath)
    rel = os.path.relpath(filepath, FRONTEND)

    # Extract existing title
    title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    title = title_match.group(1).strip() if title_match else page_title(rel)

    # Extract existing description
    desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
    description = desc_match.group(1) if desc_match else ""

    # Ensure meta description exists
    if not desc_match and description:
        html = re.sub(r'</title>', f'</title>\n<meta name="description" content="{description}">', html)

    # Ensure canonical (clean URL)
    if not re.search(r'<link\s+rel="canonical"', html):
        html = re.sub(r'<link\s+rel="canonical"[^>]*>', '', html)
        html = re.sub(r'</title>', f'</title>\n<link rel="canonical" href="{clean_url}">', html)

    # Ensure OG tags
    og_tags = {
        "og:type": "website",
        "og:url": clean_url,
        "og:title": title,
        "og:description": description or title,
        "og:image": f"{BRAND_URL}/poster.png",
        "og:site_name": BRAND,
    }
    for prop, content in og_tags.items():
        pattern = rf'<meta\s+property="{re.escape(prop)}"\s+content="[^"]*"'
        if not re.search(pattern, html):
            html = re.sub(r'</title>', f'</title>\n<meta property="{prop}" content="{content}">', html)

    # Ensure Twitter tags
    twitter_tags = {
        "twitter:card": "summary_large_image",
        "twitter:title": title,
        "twitter:description": description or title,
        "twitter:image": f"{BRAND_URL}/poster.png",
    }
    for name, content in twitter_tags.items():
        pattern = rf'<meta\s+name="{re.escape(name)}"\s+content="[^"]*"'
        if not re.search(pattern, html):
            html = re.sub(r'</title>', f'</title>\n<meta name="{name}" content="{content}">', html)

    # Ensure meta keywords
    if not re.search(r'<meta\s+name="keywords"', html):
        kw_str = ", ".join(keywords_list[:15])
        html = re.sub(r'<meta\s+name="description"', f'<meta name="keywords" content="{kw_str}" />\n<meta name="description"', html)

    # Ensure robots
    if not re.search(r'<meta\s+name="robots"', html):
        html = re.sub(r'<meta\s+name="description"',
                      f'<meta name="robots" content="index, follow" />\n<meta name="description"', html)

    # Ensure author
    if not re.search(r'<meta\s+name="author"', html):
        html = re.sub(r'<meta\s+name="description"',
                      f'<meta name="author" content="{BRAND} Private Limited" />\n<meta name="description"', html)

    return html


def inject_schemas(html, filepath, page_type):
    """Inject missing JSON-LD schemas."""
    clean_url = get_clean_url(filepath)
    rel = os.path.relpath(filepath, FRONTEND)
    title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    title = title_match.group(1).strip() if title_match else page_title(rel)

    # SoftwareApplication (inject if missing)
    if '"SoftwareApplication"' not in html:
        schema = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": BRAND,
            "applicationCategory": "BioinformaticsApplication",
            "operatingSystem": "Linux, Web",
            "description": "Sovereign biomedical AI platform for primer design, BLAST, MSA, and genomic analysis with zero external API dependency.",
            "url": BRAND_URL,
            "author": {"@type": "Organization", "name": f"{BRAND} Private Limited", "url": BRAND_URL},
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"}
        }
        block = f'\n<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>\n'
        html = html.replace("</head>", block + "</head>")

    # SpeakableSpecification (inject if missing)
    if "SpeakableSpecification" not in html:
        schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "speakable": {"@type": "SpeakableSpecification", "cssSelector": ["h1", "h2", ".lead", ".section-tag"]}
        }
        block = f'\n<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>\n'
        html = html.replace("</head>", block + "</head>")

    # FAQPage (for tools, platform, info pages)
    if page_type in ("tool", "platform", "info") and '"FAQPage"' not in html:
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": "Is VigyanLLM data secure?",
                 "acceptedAnswer": {"@type": "Answer", "text": "Yes. VigyanLLM runs on secure AWS infrastructure with optional on-premises deployment via Docker. Zero external API calls ensure data never leaves your institution."}},
                {"@type": "Question", "name": "Does VigyanLLM use external APIs?",
                 "acceptedAnswer": {"@type": "Answer", "text": "No. VigyanLLM uses the proprietary VigyanInferenceEngine — a native GGUF inference engine with zero external API dependency. No OpenAI, Anthropic, or Google APIs."}},
                {"@type": "Question", "name": "What makes VigyanLLM's 24-step pipeline unique?",
                 "acceptedAnswer": {"@type": "Answer", "text": "The 24-step validated pipeline includes nearest-neighbour thermodynamic modelling (SantaLucia 1998), BLAST specificity, SNP screening, repeat masking, multiplex cross-dimer scoring, and final verification via the ChinhAI agent."}},
            ]
        }
        block = f'\n<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>\n'
        html = html.replace("</head>", block + "</head>")

    # BreadcrumbList (for deep pages)
    depth = rel.count("/")
    if depth >= 1 and '"BreadcrumbList"' not in html:
        items = [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BRAND_URL}
        ]
        if depth >= 2:
            parent = os.path.dirname(rel)
            items.append({"@type": "ListItem", "position": 2, "name": parent.replace("-", " ").title(), "item": f"{BRAND_URL}/{parent}"})
        items.append({"@type": "ListItem", "position": len(items) + 1, "name": title, "item": clean_url})
        schema = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}
        block = f'\n<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>\n'
        html = html.replace("</head>", block + "</head>")

    # Article schema for blog
    if page_type == "blog_article" and '"Article"' not in html and '"BlogPosting"' not in html:
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": title,
            "author": {"@type": "Organization", "name": f"{BRAND} Private Limited"},
            "publisher": {"@type": "Organization", "name": BRAND, "url": BRAND_URL},
            "mainEntityOfPage": {"@type": "WebPage", "@id": clean_url}
        }
        block = f'\n<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>\n'
        html = html.replace("</head>", block + "</head>")

    return html


def fix_meta_urls(html, filepath):
    """Fix any remaining .html extensions in canonical/OG/twitter URLs."""
    clean_url = get_clean_url(filepath)
    # Canonical
    html = re.sub(
        r'(<link\s+rel="canonical"\s+href=")https://vigyanllm\.in/[^"]*\.html(")',
        rf'\g<1>{clean_url}\g<2>',
        html
    )
    # OG URL
    html = re.sub(
        r'(<meta\s+property="og:url"\s+content=")https://vigyanllm\.in/[^"]*\.html(")',
        rf'\g<1>{clean_url}\g<2>',
        html
    )
    # Twitter URL
    html = re.sub(
        r'(<meta\s+name="twitter:url"\s+content=")https://vigyanllm\.in/[^"]*\.html(")',
        rf'\g<1>{clean_url}\g<2>',
        html
    )
    return html


def process_file(filepath):
    """Run all fixes on a single HTML file."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    rel = os.path.relpath(filepath, FRONTEND)
    original = html
    page_type = classify_page(filepath)

    # 1. Fix step count (22→24)
    html = fix_step_count(html)

    # 2. Extract title for keyword generation
    title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    title = title_match.group(1).strip() if title_match else page_title(rel)
    desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
    description = desc_match.group(1) if desc_match else ""

    # 3. Generate NLP-enriched keywords
    keywords = get_page_nlp_tags(filepath, title, description)

    # 4. Ensure meta tags (title, description, canonical, OG, Twitter, keywords, author, robots)
    html = ensure_meta_tags(html, filepath, keywords)

    # 5. Fix <main> wrapper positioning
    html = fix_main_wrapper(html)

    # 6. Inject JSON-LD schemas
    html = inject_schemas(html, filepath, page_type)

    # 7. Fix canonical/OG/twitter URLs (strip .html)
    html = fix_meta_urls(html, filepath)

    if html != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return True, rel
    return False, rel


def audit_file(filepath):
    """Check all required SEO/AEO/GEO/LLMO elements on a single page."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    rel = os.path.relpath(filepath, FRONTEND)
    checks = {}

    # SEO checks
    title_m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    checks["title"] = bool(title_m) and len(title_m.group(1).strip()) > 0

    desc_m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
    checks["meta_description"] = bool(desc_m) and len(desc_m.group(1)) > 10

    checks["canonical"] = bool(re.search(r'<link\s+rel="canonical"', html))
    checks["canonical_clean"] = not bool(re.search(r'<link\s+rel="canonical"[^>]*\.html"', html))

    checks["og_title"] = bool(re.search(r'<meta\s+property="og:title"', html))
    checks["og_desc"] = bool(re.search(r'<meta\s+property="og:description"', html))
    checks["og_url"] = bool(re.search(r'<meta\s+property="og:url"', html))
    checks["og_image"] = bool(re.search(r'<meta\s+property="og:image"', html))
    checks["og_type"] = bool(re.search(r'<meta\s+property="og:type"', html))

    checks["twitter_card"] = bool(re.search(r'<meta\s+name="twitter:card"', html))
    checks["twitter_title"] = bool(re.search(r'<meta\s+name="twitter:title"', html))
    checks["twitter_desc"] = bool(re.search(r'<meta\s+name="twitter:description"', html))

    checks["robots"] = bool(re.search(r'<meta\s+name="robots"', html))
    checks["keywords"] = bool(re.search(r'<meta\s+name="keywords"', html))
    checks["author"] = bool(re.search(r'<meta\s+name="author"', html))

    # AEO/GEO/LLMO checks
    checks["jsonld_softwareapp"] = '"SoftwareApplication"' in html
    checks["jsonld_speakable"] = "SpeakableSpecification" in html
    checks["jsonld_faq"] = '"FAQPage"' in html
    checks["jsonld_breadcrumb"] = '"BreadcrumbList"' in html

    # Semantic HTML
    checks["nav_elem"] = bool(re.search(r'<nav[\s>]', html))
    checks["main_elem"] = bool(re.search(r'<main[\s>]', html))
    checks["footer_elem"] = bool(re.search(r'<footer[\s>]', html))
    checks["h1"] = bool(re.search(r'<h1[\s>]', html))

    # Step count correctness
    checks["no_22_step"] = "22-step" not in html and "22 step" not in html

    return checks


def main():
    html_files = sorted(glob.glob(os.path.join(FRONTEND, "**", "*.html"), recursive=True))
    print(f"Total files: {len(html_files)}\n")

    # ── Phase 1: Audit ──
    print("=" * 60)
    print("PHASE 1: COMPREHENSIVE AUDIT")
    print("=" * 60)

    audit_results = {}
    for fp in html_files:
        rel = os.path.relpath(fp, FRONTEND)
        if rel.startswith("admin/") or rel.startswith("api/"):
            continue
        checks = audit_file(fp)
        audit_results[rel] = checks

    # Summarize
    total = len(audit_results)
    passed_counts = defaultdict(int)
    failed_counts = defaultdict(int)
    for rel, checks in audit_results.items():
        for check, passed in checks.items():
            if passed:
                passed_counts[check] += 1
            else:
                failed_counts[check] += 1

    print(f"\n{'Check':<30} {'Pass':>6} {'Fail':>6} {'Pass %':>8}")
    print("-" * 52)
    for check in sorted(passed_counts.keys() | failed_counts.keys()):
        p = passed_counts.get(check, 0)
        f = failed_counts.get(check, 0)
        pct = (p / total * 100) if total else 0
        status = "✅" if pct >= 90 else ("⚠️" if pct >= 50 else "❌")
        print(f"{status} {check:<27} {p:>6} {f:>6} {pct:>7.1f}%")

    # ── Phase 2: Fix ──
    print(f"\n{'=' * 60}")
    print("PHASE 2: APPLYING FIXES")
    print(f"{'=' * 60}")

    fixed_count = 0
    for fp in html_files:
        rel = os.path.relpath(fp, FRONTEND)
        if rel.startswith("admin/") or rel.startswith("api/"):
            continue
        fixed, path = process_file(fp)
        if fixed:
            fixed_count += 1
            print(f"  ✓ {path}")

    print(f"\nFixed: {fixed_count} / {total} files")

    # ── Phase 3: Re-audit ──
    print(f"\n{'=' * 60}")
    print("PHASE 3: POST-FIX AUDIT")
    print(f"{'=' * 60}")

    post_audit = {}
    for fp in html_files:
        rel = os.path.relpath(fp, FRONTEND)
        if rel.startswith("admin/") or rel.startswith("api/"):
            continue
        post_audit[rel] = audit_file(fp)

    post_passed = defaultdict(int)
    post_failed = defaultdict(int)
    for rel, checks in post_audit.items():
        for check, passed in checks.items():
            if passed:
                post_passed[check] += 1
            else:
                post_failed[check] += 1

    print(f"\n{'Check':<30} {'Pass':>6} {'Fail':>6} {'Pass %':>8} {'Δ':>6}")
    print("-" * 60)
    for check in sorted(post_passed.keys() | post_failed.keys()):
        p = post_passed.get(check, 0)
        f = post_failed.get(check, 0)
        pct = (p / total * 100) if total else 0
        pre_p = passed_counts.get(check, 0)
        delta = p - pre_p
        status = "✅" if pct >= 90 else ("⚠️" if pct >= 50 else "❌")
        print(f"{status} {check:<27} {p:>6} {f:>6} {pct:>7.1f}% {delta:+5d}")

    print(f"\n{'=' * 60}")
    print(f"DONE. {fixed_count} files fixed.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
