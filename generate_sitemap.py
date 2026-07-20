#!/usr/bin/env python3
"""
Generate comprehensive sitemap.xml and update robots.txt for VigyanLLM.
Includes ALL pages with clean URLs (no .html), proper priorities, and changefreq.
"""

import os
import glob
import datetime

FRONTEND = os.path.join(os.path.dirname(__file__), "frontend")
BRAND_URL = "https://vigyanllm.in"
TODAY = datetime.date.today().isoformat()

# ── Page classification for prioritization ──────────────────────────────────
PRIORITY_MAP = {
    # Tier 1: Core product pages (1.0)
    "index.html": 1.0,
    "primer.html": 1.0,
    "primer-design.html": 0.95,
    "primer-design-pipeline.html": 0.95,
    "blast.html": 0.95,
    "msa.html": 0.95,
    "search.html": 0.90,
    # Tier 2: Important tools
    "pcr-analysis.html": 0.90,
    "crispr-analysis.html": 0.90,
    "protein-docking.html": 0.90,
    "tm-calculator.html": 0.85,
    "gc-calculator.html": 0.85,
    "dna-to-rna.html": 0.85,
    "tools/dna-to-rna.html": 0.80,
    # Tier 3: Platform/Info pages
    "platform.html": 0.85,
    "solution.html": 0.85,
    "architecture.html": 0.80,
    "problem.html": 0.80,
    "compare.html": 0.80,
    "roadmap.html": 0.80,
    "pricing.html": 0.90,
    "validated-primer-design.html": 0.90,
    "validated-primer-design-report.html": 0.70,
    "security.html": 0.80,
    "privacy.html": 0.70,
    "terms.html": 0.70,
    "faq.html": 0.85,
    "about.html": 0.75,
    "contact.html": 0.65,
    "cite.html": 0.85,
    "academic-partnership.html": 0.85,
    "Learning-vigyanllm.html": 0.85,
    "sitemap.html": 0.70,
    "demo.html": 0.75,
    # Tier 4: SEO landing pages
    "primer-design-india.html": 0.85,
    "primer-3-alternative.html": 0.85,
    "primer3-alternative.html": 0.85,
    "primer-blast-alternative.html": 0.85,
    "primer-blast-specificity.html": 0.80,
    "primer-design-best-practices.html": 0.80,
    "primer-design-thermodynamics.html": 0.80,
    "biomedical-ai-platform.html": 0.80,
    "ai-crispr-analysis.html": 0.80,
    "hipaa-compliant-genomics.html": 0.80,
    "molecular-docking-guide.html": 0.80,
    "multiplex-primer-design.html": 0.80,
    "qpcr-primer-design.html": 0.80,
    "dna-3d.html": 0.70,
    "login.html": 0.30,
    "cookies.html": 0.40,
    "refund.html": 0.40,
    "changelog.html": 0.50,
    "db-redirect.html": 0.10,
    "p.html": 0.20,
    "404.html": 0.10,
    "payment-success.html": 0.20,
    "payment-failed.html": 0.20,
}

# Pages that should have noindex or be excluded from sitemap
EXCLUDE_PAGES = {
    "404.html", "db-redirect.html", "p.html",
    "payment-success.html", "payment-failed.html",
    "admin-security.html", "blog-post.html", "login.html",
}

EXCLUDE_DIR_PREFIXES = {"admin/", "api/"}

CHANGEFREQ_MAP = {
    "index.html": "weekly",
    "primer.html": "weekly",
}

BLOG_CHANGEFREQ = "monthly"
GLOSSARY_CHANGEFREQ = "monthly"
GENE_CHANGEFREQ = "monthly"
HUB_CHANGEFREQ = "weekly"
LANDING_CHANGEFREQ = "monthly"
DEFAULT_CHANGEFREQ = "monthly"


def get_clean_url(filepath):
    """Convert file path to clean URL."""
    rel = os.path.relpath(filepath, FRONTEND)
    # Remove .html
    if rel.endswith(".html"):
        rel = rel[:-5]
    # Map index to root
    if rel == "index" or rel.endswith("/index"):
        if rel == "index":
            return BRAND_URL
        # Keep the path but remove /index
        rel = rel[:-6] if rel.endswith("/index") else rel
    return f"{BRAND_URL}/{rel}"


def get_priority(filepath, rel):
    """Determine priority for a page."""
    fname = os.path.basename(rel)
    base = rel  # relative path without extension used as key
    
    # Check exact match
    if fname in PRIORITY_MAP:
        return PRIORITY_MAP[fname]
    
    # Check by directory
    if rel.startswith("blog/"):
        return 0.75
    if rel.startswith("glossary/"):
        return 0.65
    if rel.startswith("gene-prefers/"):
        return 0.70
    if rel.startswith("hub/"):
        return 0.80
    if rel.startswith("landing-pages/"):
        return 0.75
    if rel.startswith("docs/"):
        return 0.60
    
    return 0.50


def get_changefreq(filepath, rel):
    """Determine change frequency for a page."""
    fname = os.path.basename(rel)
    if fname in CHANGEFREQ_MAP:
        return CHANGEFREQ_MAP[fname]
    if rel.startswith("blog/"):
        return BLOG_CHANGEFREQ
    if rel.startswith("glossary/"):
        return GLOSSARY_CHANGEFREQ
    if rel.startswith("gene-prefers/"):
        return GENE_CHANGEFREQ
    if rel.startswith("hub/"):
        return HUB_CHANGEFREQ
    if rel.startswith("landing-pages/"):
        return LANDING_CHANGEFREQ
    return DEFAULT_CHANGEFREQ


def generate_sitemap_xml():
    """Generate complete sitemap.xml with ALL pages."""
    html_files = sorted(glob.glob(os.path.join(FRONTEND, "**", "*.html"), recursive=True))
    
    urls = []
    for fp in html_files:
        rel = os.path.relpath(fp, FRONTEND)
        
        # Skip excluded
        fname = os.path.basename(rel)
        if fname in EXCLUDE_PAGES:
            continue
        if any(rel.startswith(p) for p in EXCLUDE_DIR_PREFIXES):
            continue
        
        clean_url = get_clean_url(fp)
        priority = get_priority(fp, rel)
        changefreq = get_changefreq(fp, rel)
        
        urls.append(f'  <url>\n'
                    f'    <loc>{clean_url}</loc>\n'
                    f'    <lastmod>{TODAY}</lastmod>\n'
                    f'    <changefreq>{changefreq}</changefreq>\n'
                    f'    <priority>{priority:.1f}</priority>\n'
                    f'  </url>')
    
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
{chr(10).join(urls)}
</urlset>
'''
    return xml, len(urls)


def generate_robots_txt(url_count):
    """Generate comprehensive robots.txt."""
    robots = f'''# robots.txt — VigyanLLM
# https://vigyanllm.in/robots.txt
# Generated: {TODAY}

# ── Default rules ────────────────────────────────────────────────────────
User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /login/
Disallow: /login.html
Disallow: /dashboard/
Disallow: /admin-security.html
Disallow: /db-redirect.html
Disallow: /payment-failed.html
Disallow: /payment-success.html

Crawl-delay: 2

Sitemap: https://vigyanllm.in/sitemap.xml

# ── Search engines ───────────────────────────────────────────────────────
User-agent: Googlebot
Allow: /
Crawl-delay: 0

User-agent: Googlebot-Image
Allow: /

User-agent: Googlebot-News
Allow: /

User-agent: Bingbot
Allow: /
Crawl-delay: 2

User-agent: Slurp
Allow: /
Crawl-delay: 2

User-agent: DuckDuckBot
Allow: /

User-agent: YandexBot
Allow: /
Crawl-delay: 2

User-agent: Baiduspider
Allow: /
Crawl-delay: 2

# ── AI / LLM crawlers (GEO/LLMO strategy — allow for visibility) ────────
User-agent: GPTBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Meta-ExternalAgent
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: Anthropic-AI
Allow: /

User-agent: Cohere-AI
Allow: /

User-agent: Applebot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

# ── SEO analysis tools — block (no indexing value, bandwidth waste) ──────
User-agent: AhrefsBot
Disallow: /

User-agent: SemrushBot
Disallow: /

User-agent: MJ12bot
Disallow: /

User-agent: Dotbot
Disallow: /

User-agent: Majestic-12
Disallow: /

User-agent: rogerbot
Disallow: /

User-agent: exabot
Disallow: /

User-agent: ia_archiver
Disallow: /

User-agent: Screaming Frog SEO Spider
Disallow: /

# ── Bad bots / scrapers ───────────────────────────────────────────────────
User-agent: Bytespider
Disallow: /

User-agent: DataForSeoBot
Disallow: /

User-agent: PetalBot
Disallow: /

User-agent: AspiegelBot
Disallow: /

# ── Sitemap details ──────────────────────────────────────────────────────
# Total URLs in sitemap: {url_count}
# Coverage: Core tools, platform pages, blog (60), glossary ({url_count - 60 - 30}), gene-prefers pages, landing pages, hub pages
'''
    return robots


def update_sitemap_edge_function(blog_slugs, glossary_slugs, gene_slugs, landing_slugs):
    """Update the Vercel Edge Function sitemap.xml.js with clean URLs."""
    import json
    edge_path = os.path.join(FRONTEND, "api", "sitemap.xml.js")
    
    blog_json = json.dumps(blog_slugs)
    glossary_json = json.dumps(glossary_slugs)
    gene_json = json.dumps(gene_slugs)
    landing_json = json.dumps(landing_slugs)
    
    code = f'''// Vercel Edge Function: Dynamic Sitemap Generator
// Auto-generated — {TODAY}
export const config = {{ runtime: "edge" }};

const BASE_URL = "https://vigyanllm.in";

const CORE = [
  "/","/primer","/blast","/msa","/search","/primer-design","/primer-design-pipeline",
  "/pcr-analysis","/crispr-analysis","/protein-docking","/tm-calculator","/gc-calculator",
  "/dna-to-rna","/tools/dna-to-rna",
  "/platform","/solution","/architecture","/problem","/compare","/roadmap",
  "/validated-primer-design","/security","/privacy","/terms","/faq","/about","/contact","/cite",
  "/academic-partnership","/Learning-vigyanllm","/demo","/sitemap","/cookies","/refund","/changelog",
  "/primer-design-india","/primer-3-alternative","/primer3-alternative","/primer-blast-alternative",
  "/primer-blast-specificity","/primer-design-best-practices","/primer-design-thermodynamics",
  "/biomedical-ai-platform","/ai-crispr-analysis","/hipaa-compliant-genomics",
  "/molecular-docking-guide","/multiplex-primer-design","/qpcr-primer-design",
  "/validated-primer-design-report","/dna-3d",
  "/docs/getting-started","/docs/pipeline-config",
];

const BLOG = {blog_json};
const GLOSSARY = {glossary_json};
const GENE = {gene_json};
const LANDING = {landing_json};

const HUB = [
  "/hub/primer-design","/hub/molecular-docking","/hub/pcr-amplification",
  "/hub/genomics-research","/hub/crispr-genome-editing","/hub/bioinformatics-tools",
  "/hub/protein-structure","/hub/drug-discovery","/hub/gene-expression",
  "/hub/sequencing-technologies","/hub/cancer-biology","/hub/cell-biology",
];

function prio(u) {{
  if (u === "/" || u === "/primer") return "1.0";
  if (u.startsWith("/hub")) return "0.80";
  if (u.startsWith("/blog")) return "0.75";
  if (u.startsWith("/glossary")) return "0.65";
  if (u.startsWith("/gene-prefers")) return "0.70";
  if (u.startsWith("/landing-pages")) return "0.75";
  return "0.80";
}}
function freq(u) {{
  if (u === "/" || u === "/primer") return "weekly";
  if (u.startsWith("/hub")) return "weekly";
  return "monthly";
}}

function generateSitemap() {{
  const today = new Date().toISOString().split("T")[0];
  const all = [
    ...CORE.map(u => ({{ url: u, priority: prio(u), changefreq: freq(u) }})),
    ...BLOG.map(s => ({{ url: "/blog/" + s, priority: "0.75", changefreq: "monthly" }})),
    ...GLOSSARY.map(s => ({{ url: "/glossary/" + s, priority: "0.65", changefreq: "monthly" }})),
    ...GENE.map(s => ({{ url: "/gene-prefers/" + s, priority: "0.70", changefreq: "monthly" }})),
    ...LANDING.map(s => ({{ url: "/landing-pages/" + s, priority: "0.75", changefreq: "monthly" }})),
    ...HUB.map(u => ({{ url: u, priority: "0.80", changefreq: "weekly" }})),
  ];

  const urls = all.map(p =>
    `  <url>\\n    <loc>${{BASE_URL}}${{p.url}}</loc>\\n    <lastmod>${{today}}</lastmod>\\n    <changefreq>${{p.changefreq}}</changefreq>\\n    <priority>${{p.priority}}</priority>\\n  </url>`
  ).join("\\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${{urls}}
</urlset>`;
}}

export default function handler(request) {{
  return new Response(generateSitemap(), {{
    headers: {{ "Content-Type": "application/xml", "Cache-Control": "public, max-age=3600, s-maxage=3600" }},
  }});
}}
'''
    with open(edge_path, "w", encoding="utf-8") as f:
        f.write(code)


def main():
    # 1. Generate sitemap.xml
    xml_content, url_count = generate_sitemap_xml()
    sitemap_path = os.path.join(FRONTEND, "sitemap.xml")
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"✓ sitemap.xml generated — {url_count} URLs")

    # 2. Generate robots.txt
    robots_content = generate_robots_txt(url_count)
    robots_path = os.path.join(FRONTEND, "robots.txt")
    with open(robots_path, "w", encoding="utf-8") as f:
        f.write(robots_content)
    print(f"✓ robots.txt generated")

    # 3. Update edge function with clean URLs
    blog_slugs = sorted([
        os.path.relpath(fp, FRONTEND).replace("blog/", "").replace(".html", "")
        for fp in glob.glob(os.path.join(FRONTEND, "blog", "*.html"))
        if os.path.relpath(fp, FRONTEND).replace("blog/", "").replace(".html", "") != "index"
    ])
    glossary_slugs = sorted([
        os.path.relpath(fp, FRONTEND).replace("glossary/", "").replace(".html", "")
        for fp in glob.glob(os.path.join(FRONTEND, "glossary", "*.html"))
    ])
    gene_slugs = sorted([
        os.path.relpath(fp, FRONTEND).replace("gene-prefers/", "").replace(".html", "")
        for fp in glob.glob(os.path.join(FRONTEND, "gene-prefers", "*.html"))
    ])
    landing_slugs = sorted([
        os.path.relpath(fp, FRONTEND).replace("landing-pages/", "").replace(".html", "")
        for fp in glob.glob(os.path.join(FRONTEND, "landing-pages", "*.html"))
    ])
    update_sitemap_edge_function(blog_slugs, glossary_slugs, gene_slugs, landing_slugs)
    print(f"✓ api/sitemap.xml.js updated ({len(blog_slugs)} blog, {len(glossary_slugs)} glossary, {len(gene_slugs)} gene, {len(landing_slugs)} landing)")

    print(f"\nTotal URLs in sitemap: {url_count}")
    print("Done.")


if __name__ == "__main__":
    main()
