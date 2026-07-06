#!/usr/bin/env python3
"""
VigyanLLM Indexing Fix Script
Fixes: canonical/OG URLs, injects JSON-LD schema, adds internal nav to orphaned pages.
"""

import os
import re
import json
import glob

FRONTEND = os.path.join(os.path.dirname(__file__), "frontend")

SITE_NAV_HTML = """
<nav class="seo-internal-nav" style="margin-top:48px;padding-top:32px;border-top:1px solid #E2E8F0">
  <div style="max-width:960px;margin:0 auto">
    <p style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#94A3B8;font-weight:700;margin-bottom:16px">Explore VigyanLLM</p>
    <div style="display:flex;flex-wrap:wrap;gap:8px 20px">
      <a href="/" style="font-size:13px;color:#2563EB">Home</a>
      <a href="/primer" style="font-size:13px;color:#2563EB">VPrime 2.0 — Primer Design</a>
      <a href="/blast" style="font-size:13px;color:#2563EB">BLAST</a>
      <a href="/msa" style="font-size:13px;color:#2563EB">MSA</a>
      <a href="/search" style="font-size:13px;color:#2563EB">Sequence Search</a>
      <a href="/platform" style="font-size:13px;color:#2563EB">Platform</a>
      <a href="/Learning-vigyanllm" style="font-size:13px;color:#2563EB">Learning Hub</a>
      <a href="/academic-partnership" style="font-size:13px;color:#2563EB">Academic Partnership</a>
      <a href="/blog" style="font-size:13px;color:#2563EB">Blog</a>
    </div>
  </div>
</nav>
"""

SCHEMA_SOFTWAREAPP = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "VigyanLLM",
    "applicationCategory": "BioinformaticsApplication",
    "operatingSystem": "Linux, Web",
    "description": "Sovereign biomedical AI platform for primer design, BLAST, MSA, and genomic analysis with zero external API dependency.",
    "url": "https://vigyanllm.in",
    "author": {
        "@type": "Organization",
        "name": "VigyanLLM Private Limited",
        "url": "https://vigyanllm.in"
    },
    "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "INR"
    }
}

SCHEMA_FAQ = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
        {
            "@type": "Question",
            "name": "Is VigyanLLM data secure?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. VigyanLLM runs on secure AWS infrastructure with optional on-premises deployment. Zero external API calls ensure genomic and clinical data never leaves the institution."
            }
        },
        {
            "@type": "Question",
            "name": "Does VigyanLLM use external APIs?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "No. VigyanLLM uses the proprietary VigyanInferenceEngine — a native GGUF inference engine with zero external API dependency. No OpenAI, Anthropic, or Google APIs."
            }
        },
        {
            "@type": "Question",
            "name": "Is VigyanLLM built in India?",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. VigyanLLM is an Indian sovereign AI platform engineered in India for global biomedical research."
            }
        }
    ]
}


def html_path_to_clean_url(filepath):
    rel = os.path.relpath(filepath, FRONTEND)
    if rel == "index.html":
        return ""
    if rel.endswith(".html"):
        no_ext = rel[:-5]
        if no_ext.startswith("blog/"):
            return "/" + no_ext
        if no_ext.startswith("glossary/"):
            return "/" + no_ext
        if no_ext.startswith("gene-prefers/"):
            return "/" + no_ext
        if no_ext.startswith("landing-pages/"):
            return "/" + no_ext
        if no_ext.startswith("tools/"):
            return "/" + no_ext
        if no_ext.startswith("hub/"):
            return "/" + no_ext
        if no_ext.startswith("docs/"):
            return "/" + no_ext
        return "/" + no_ext
    return "/" + rel


def fix_canonical_urls(html, clean_url):
    """Strip .html from canonical and og:url."""
    base = f"https://vigyanllm.in{clean_url}"
    html = re.sub(
        r'<link\s+rel="canonical"\s+href="https://vigyanllm\.in/[^"]*\.html"',
        f'<link rel="canonical" href="{base}"',
        html
    )
    html = re.sub(
        r'<meta\s+property="og:url"\s+content="https://vigyanllm\.in/[^"]*\.html"',
        f'<meta property="og:url" content="{base}"',
        html
    )
    # Also handle twitter urls
    html = re.sub(
        r'<meta\s+name="twitter:url"\s+content="https://vigyanllm\.in/[^"]*\.html"',
        f'<meta name="twitter:url" content="{base}"',
        html
    )
    return html


def inject_jsonld(html, schemas):
    """Inject JSON-LD schema blocks before </head> if not already present."""
    for schema in schemas:
        schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
        # Check if this schema type already exists
        if schema["@type"] in html:
            continue
        block = f'\n<script type="application/ld+json">\n{schema_str}\n</script>\n'
        html = html.replace("</head>", block + "</head>")
    return html


def add_main_wrapper(html):
    """Wrap content in <main> if not present."""
    if "<main" in html:
        return html
    # Find <body> content and wrap in <main>
    body_match = re.search(r'<body[^>]*>', html)
    if body_match:
        insert_pos = body_match.end()
        before = html[:insert_pos]
        after = html[insert_pos:]
        # Don't wrap nav or footer in main
        # Simple approach: wrap everything except nav, footer
        after = "<main>\n" + after
        # Close main before footer
        after = after.replace("</footer>", "</main>\n</footer>")
        html = before + after
    return html


def add_internal_nav(html, filepath):
    """Add internal linking nav to orphaned pages."""
    if '<nav class="seo-internal-nav"' in html:
        return html
    if "</footer>" in html:
        html = html.replace("</footer>", SITE_NAV_HTML + "\n</footer>")
    elif "</body>" in html:
        html = html.replace("</body>", SITE_NAV_HTML + "\n</body>")
    return html


def add_speakable_schema(html):
    """Add SpeakableSpecification for GEO."""
    if "SpeakableSpecification" in html:
        return html
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "VigyanLLM",
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": ["h1", "h2", ".lead", ".section-tag"]
        }
    }
    block = f'\n<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>\n'
    html = html.replace("</head>", block + "</head>")
    return html


def has_schema(html, schema_type):
    """Check if a schema type is already in the HTML."""
    return f'"@type": "{schema_type}"' in html or f'"@type":"{schema_type}"' in html


def main():
    html_files = glob.glob(os.path.join(FRONTEND, "**", "*.html"), recursive=True)
    print(f"Found {len(html_files)} HTML files")

    stats = {"canonical_fixed": 0, "schema_added": 0, "nav_added": 0, "main_added": 0}

    for fp in sorted(html_files):
        rel = os.path.relpath(fp, FRONTEND)
        # Skip files in excluded dirs
        if rel.startswith("admin") or rel.startswith("api/"):
            continue

        clean_url = html_path_to_clean_url(fp)
        with open(fp, "r", encoding="utf-8") as f:
            html = f.read()

        original = html

        # 1. Fix canonical/OG URLs
        html = fix_canonical_urls(html, clean_url)
        if html != original:
            stats["canonical_fixed"] += 1

        # 2. Add JSON-LD schemas
        schemas_to_add = []
        if not has_schema(html, "SoftwareApplication"):
            schemas_to_add.append(SCHEMA_SOFTWAREAPP)
        if not has_schema(html, "FAQPage"):
            schemas_to_add.append(SCHEMA_FAQ)
        if schemas_to_add:
            html = inject_jsonld(html, schemas_to_add)
            stats["schema_added"] += 1

        # 3. Add Speakable schema for GEO
        html = add_speakable_schema(html)

        # 4. Add <main> wrapper
        before_main = html
        html = add_main_wrapper(html)
        if html != before_main:
            stats["main_added"] += 1

        # 5. Add internal nav to orphaned pages
        is_orphaned = any(rel.startswith(p) for p in ["glossary/", "gene-prefers/", "landing-pages/", "hub/", "docs/", "tools/"])
        if is_orphaned:
            before_nav = html
            html = add_internal_nav(html, fp)
            if html != before_nav:
                stats["nav_added"] += 1

        if html != original:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  Updated: {rel}")

    print(f"\nStats: {stats}")
    print("Done.")


if __name__ == "__main__":
    main()
