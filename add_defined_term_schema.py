#!/usr/bin/env python3
"""Inject DefinedTerm JSON-LD schema into all glossary HTML files."""

import json
import os
import re
import html

GLOSSARY_DIR = "/Users/macbookpro/Desktop/vigyanpilot/frontend/glossary"
SKIP_FILES = {"gc-clamp.html"}
PLACEHOLDER = "<!-- JSON-LD: DefinedTerm -->"


def extract_term_name(content: str) -> str | None:
    m = re.search(r"<h1>(.*?)</h1>", content, re.DOTALL)
    if not m:
        return None
    raw = m.group(1).strip()
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html.unescape(raw)
    if "," in raw:
        raw = raw.split(",")[0].strip()
    return raw


def extract_definition(content: str) -> str | None:
    m = re.search(
        r'<section[^>]+id="definition"[^>]*>.*?<p>(.*?)</p>',
        content,
        re.DOTALL,
    )
    if not m:
        return None
    text = re.sub(r"<[^>]+>", "", m.group(1))
    text = html.unescape(text).strip()
    return text


def extract_canonical(content: str) -> str | None:
    m = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', content)
    return m.group(1) if m else None


def build_schema(term: str, definition: str, url: str) -> str:
    desc = definition[:150]
    if len(definition) > 150:
        desc = desc[: desc.rfind(" ")] + "..."
    schema = {
        "@context": "https://schema.org",
        "@type": "DefinedTerm",
        "name": term,
        "description": desc,
        "url": url,
        "inLanguage": "en",
        "definedTermSet": {
            "@type": "DefinedTermSet",
            "name": "VigyanLLM Molecular Biology Glossary",
            "url": "https://www.vigyanllm.in/glossary",
        },
    }
    return json.dumps(schema, indent=2, ensure_ascii=False)


def process_file(filepath: str) -> str:
    filename = os.path.basename(filepath)
    if filename in SKIP_FILES:
        return "skipped-exists"

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if PLACEHOLDER not in content:
        return "no-placeholder"

    term = extract_term_name(content)
    if not term:
        return "no-h1"

    definition = extract_definition(content)
    if not definition:
        return "no-definition"

    canonical = extract_canonical(content)
    if not canonical:
        return "no-canonical"

    schema_json = build_schema(term, definition, canonical)
    inject = f'{PLACEHOLDER}\n<script type="application/ld+json">\n{schema_json}\n</script>'
    content = content.replace(PLACEHOLDER, inject, 1)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return "ok"


def main():
    files = sorted(
        f for f in os.listdir(GLOSSARY_DIR) if f.endswith(".html")
    )
    processed = 0
    skipped = 0
    warnings = 0

    for fname in files:
        filepath = os.path.join(GLOSSARY_DIR, fname)
        result = process_file(filepath)

        if result == "ok":
            processed += 1
            print(f"  OK  {fname}")
        elif result == "skipped-exists":
            skipped += 1
            print(f"  SKIP {fname} (already has DefinedTerm)")
        elif result == "no-placeholder":
            warnings += 1
            print(f"  WARN {fname} (no placeholder comment)")
        elif result == "no-h1":
            warnings += 1
            print(f"  WARN {fname} (no H1 found)")
        elif result == "no-definition":
            warnings += 1
            print(f"  WARN {fname} (no definition section)")
        elif result == "no-canonical":
            warnings += 1
            print(f"  WARN {fname} (no canonical URL)")

    print(f"\nSummary: {processed} processed, {skipped} skipped, {warnings} warnings, {len(files)} total")


if __name__ == "__main__":
    main()
