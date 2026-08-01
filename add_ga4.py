import glob, os

GTAG_SNIPPET = """<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-PB0XMF4GEH"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-PB0XMF4GEH');
</script>
"""

files = sorted(glob.glob("frontend/**/*.html", recursive=True))
changed, skipped = 0, 0
for f in files:
    with open(f, encoding="utf-8") as fh:
        content = fh.read()
    if "G-PB0XMF4GEH" in content:
        skipped += 1
        continue
    # Replace placeholder in CMS pages that already have gtag stub
    if "G-XXXXXXXXXX" in content:
        content = content.replace("G-XXXXXXXXXX", "G-PB0XMF4GEH")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(content)
        changed += 1
        continue
    # Insert snippet right after <head>
    if "<head>" in content:
        content = content.replace("<head>", "<head>\n" + GTAG_SNIPPET, 1)
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(content)
        changed += 1
    else:
        skipped += 1

print(f"changed={changed} skipped={skipped} total={len(files)}")
