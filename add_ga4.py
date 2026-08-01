import glob, os

GTAG_SNIPPET = """<!-- Google tag (gtag.js) -->
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('consent', 'default', {
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'analytics_storage': 'denied',
    'region': ['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE','IS','LI','NO','GB','CH']
  });
  gtag('consent', 'default', {
    'ad_storage': 'granted',
    'ad_user_data': 'granted',
    'ad_personalization': 'granted',
    'analytics_storage': 'granted'
  });
  try {
    var vlcs = JSON.parse(localStorage.getItem('vigyanllm_cookie_consent') || 'null');
    if (vlcs && vlcs.consent === 'accepted') {
      gtag('consent', 'update', { 'ad_storage': 'granted', 'ad_user_data': 'granted', 'ad_personalization': 'granted', 'analytics_storage': 'granted' });
    } else if (vlcs && vlcs.consent === 'declined') {
      gtag('consent', 'update', { 'ad_storage': 'denied', 'ad_user_data': 'denied', 'ad_personalization': 'denied', 'analytics_storage': 'denied' });
    }
  } catch (e) {}
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-PB0XMF4GEH"></script>
<script>
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
