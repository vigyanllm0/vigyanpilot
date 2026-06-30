#!/usr/bin/env python3
"""Generate 24 blog HTML files under frontend/blog/ based on the what-is-pcr.html template."""

import os

OUT = os.path.join(os.path.dirname(__file__), "blog")
os.makedirs(OUT, exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────────

def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

# ── TEMPLATE ─────────────────────────────────────────────────────────────

HEAD_OPEN = '''<!DOCTYPE html>
<html lang="en-IN">
<head>
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-KRP5LLPR');</script>
<!-- End Google Tag Manager -->

  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
'''

HEAD_CLOSE = '''
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=Plus+Jakarta+Sans:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
  
  <style>
    :root {
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
  --bg: #FFFFFF;
  --border: #E2E8F0;
  --surface: #F8FAFC;
  --max-w: 1100px;
  --sec-p: 100px;
}
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body { background: var(--bg); color: var(--text); font-family: var(--font-b); line-height: 1.6; -webkit-font-smoothing: antialiased; }
    a { text-decoration: none; color: inherit; transition: color 0.15s ease; }
    .container { max-width: var(--max-w); margin: 0 auto; padding: 0 24px; }
    section { padding: var(--sec-p) 0; }
    nav { position: sticky; top: 0; background: var(--navy); backdrop-filter: blur(8px); border-bottom: 1px solid rgba(255,255,255,0.1); z-index: 1000; height: 72px; }
    @media (max-width: 768px) { .nav-links { display: none; } }
    
    .article-body { padding: 40px 0; max-width: 800px; margin: 0 auto; }
    .article-body h1 { font-family: var(--font-b); font-size: clamp(2rem,4vw,2.8rem); font-weight: 400; line-height: 1.1; margin-bottom: 16px; }
    .article-body h2 { font-size: 24px; font-weight: 600; color: var(--text); margin: 40px 0 16px; }
    .article-body h3 { font-size: 18px; font-weight: 600; color: var(--text); margin: 28px 0 12px; }
    .article-body p { margin-bottom: 16px; color: var(--text2); font-size: 15px; line-height: 1.8; }
    .article-body ul, .article-body ol { margin-left: 24px; margin-bottom: 16px; color: var(--text2); font-size: 15px; }
    .article-body li { margin-bottom: 8px; }
    .article-body strong { color: var(--text); }
    .article-body a { color: var(--primary); text-decoration: none; }
    .article-body a:hover { text-decoration: underline; }
    .article-body table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }
    .article-body th { background: var(--surface); color: var(--text); padding: 12px; text-align: left; border: 1px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
    .article-body td { padding: 12px; border: 1px solid var(--border); color: var(--text2); }
    .article-body tr:nth-child(even) { background: var(--surface); }
    .article-body .callout { background: var(--surface); border-left: 4px solid var(--primary); padding: 20px 24px; border-radius: 0 12px 12px 0; margin: 24px 0; }
    .article-body .callout-title { font-weight: 700; color: var(--primary); margin-bottom: 8px; }
    .article-body code { background: var(--surface); padding: 2px 6px; border-radius: 4px; font-size: 13px; color: var(--text); border: 1px solid var(--border); }
    .hero-blog { padding: 60px 0 30px; text-align: center; border-bottom: 1px solid var(--border); }
    .cta-box { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 36px; text-align: center; margin: 40px 0; }
    .cta-box h3 { font-size: 20px; color: var(--text); margin-bottom: 10px; }
    .cta-box p { color: var(--text2); margin-bottom: 20px; }
    .cta-btn { display: inline-block; padding: 14px 32px; background: var(--primary); color: #fff; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px; transition: background 0.2s; }
    .cta-btn:hover { background: #0044ff; }
    .references { padding: 30px 0; border-top: 1px solid var(--border); margin-top: 40px; }
    .references h2 { font-size: 20px; color: var(--text); margin-bottom: 16px; font-weight: 600; }
    .references ol { margin-left: 24px; color: var(--text2); font-size: 14px; }
    
    .article-header .article-tag { display: inline-block; background: #e8f0ff; color: var(--primary); padding: 4px 14px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-bottom: 16px; }
    .article-header .article-date { color: var(--muted); font-size: 13px; }
    .article-header .article-author { color: var(--text2); font-size: 13px; font-weight: 600; }
    .article-header h1 { font-size: clamp(2rem,4vw,2.8rem); font-weight: 400; line-height: 1.1; margin-bottom: 16px; }
    .article-header .subtitle { font-size: 16px; color: var(--text2); line-height: 1.6; max-width: 700px; }
    .article-meta-bar { display: flex; gap: 16px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
    .author-bio { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin: 40px 0 24px; display: flex; gap: 20px; align-items: flex-start; }
    .author-bio-avatar { width: 60px; height: 60px; border-radius: 50%; background: var(--primary); display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 24px; flex-shrink: 0; }
    .author-bio h4 { font-size: 16px; color: var(--text); margin-bottom: 6px; }
    .author-bio p { font-size: 13px; color: var(--text2); line-height: 1.6; margin-bottom: 0; }
    .related-articles { padding: 30px 0; border-top: 1px solid var(--border); margin-top: 24px; }
    .related-articles h2 { font-size: 20px; color: var(--text); margin-bottom: 20px; font-weight: 600; }
    .related-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; }
    .related-card { border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: border-color 0.2s; }
    .related-card:hover { border-color: var(--primary); }
    .related-card h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
    .related-card p { font-size: 12px; color: var(--text2); line-height: 1.6; margin-bottom: 0; }
    .related-card a { color: var(--primary); font-weight: 600; }
  </style>
'''



FOOTER = '''
  <footer style="background:var(--navy);color:#CBD5E1;padding:80px 0 32px">
    <div style="max-width:1200px;margin:0 auto;padding:0 24px">
      <div style="display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;gap:48px;margin-bottom:60px">
        <div>
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
            <img src="../logo.svg" alt="VigyanLLM Logo" style="width:32px;height:32px;border-radius:4px">
            <span style="font-family:var(--font-h);font-size:20px;font-weight:700;color:#fff">VigyanLLM</span>
          </div>
          <p style="font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:20px;line-height:1.6">Sovereign Healthcare &amp; Life Sciences AI.<br>Built in India. For the world.</p>
          <a href="mailto:contact@vigyanllm.in" style="font-family:var(--font-b);font-size:13px;color:var(--accent);display:block;margin-bottom:6px">contact@vigyanllm.in</a>
          <div style="display:flex;gap:12px;margin-top:24px">
            <a href="#" aria-label="Facebook" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg></a>
            <a href="#" aria-label="X" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><path d="M4 4l6.5 8.5L4 20h2l5.5-7 4.5 7h5l-7-9.5L20 4h-2l-5 6.5L9 4H4zm3 1.5h3l10 13h-3L7 5.5z"/></svg></a>
            <a href="#" aria-label="YouTube" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6a3 3 0 0 0-2.1 2.1C0 8.1 0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1c.5-1.9.5-5.8.5-5.8s0-3.9-.5-5.8zM9.5 15.5V8.5l6.3 3.5-6.3 3.5z"/></svg></a>
            <a href="#" aria-label="Instagram" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg></a>
          </div>
        </div>
        <div>
          <h5 style="font-family:var(--font-h);font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#fff;margin-bottom:24px;font-weight:700">Platform</h5>
          <a href="../index.html#problem" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Problem</a>
          <a href="../index.html#platform" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Platform</a>
          <a href="../index.html#architecture" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Architecture</a>
          <a href="../demo.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Demo</a>
        </div>
        <div>
          <h5 style="font-family:var(--font-h);font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#fff;margin-bottom:24px;font-weight:700">Resources</h5>
          <a href="../primer.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">VPrime 1.0</a>
          <a href="./blog/index.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Blog</a>
          <a href="../faq.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">FAQ</a>
          <a href="../about.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">About</a>
        </div>
        <div>
          <h5 style="font-family:var(--font-h);font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#fff;margin-bottom:24px;font-weight:700">Contact</h5>
          <a href="mailto:contact@vigyanllm.in" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">contact@vigyanllm.in</a>
          <a href="../privacy.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Privacy</a>
          <a href="../cookies.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Cookies</a>
          <a href="../terms.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Terms</a>
          <a href="../refund.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Refund</a>
          <a href="../security.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Security</a>
        </div>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:24px;display:flex;justify-content:space-between;font-family:var(--font-b);font-size:12px;color:#64748B">
        <span>&copy; <script>document.write(new Date().getFullYear())</script> VigyanLLM Pvt. Ltd. · Sovereign Research AI</span>
        <span>WWW.VIGYANLLM.IN</span>
      </div>
    </div>
  </footer>
</body>
</html>'''

# ── ARTICLE DATA ─────────────────────────────────────────────────────────

# Each article: slug, title, desc, kw, tag, h1, subtitle, sections list of (h2, body_html), related slugs list
articles = []

# 1. nested-pcr-primer-design
articles.append({
    "slug": "nested-pcr-primer-design",
    "title": "Nested PCR: Two-Round Primer Design Strategies for Enhanced Specificity",
    "desc": "Learn nested PCR primer design strategies for two-round amplification. How to design inner and outer primers for maximum specificity and sensitivity in molecular biology.",
    "kw": "nested PCR primer design, nested PCR primers, inner primer, outer primer, two-round PCR, PCR specificity",
    "tag": "Advanced PCR Techniques",
    "h1": "Nested PCR: Two-Round Primer Design Strategies for Enhanced Specificity",
    "subtitle": "Nested PCR uses two sequential amplification rounds with two primer pairs to dramatically improve specificity and sensitivity. This guide covers primer design strategies, Tm optimisation, and troubleshooting.",
    "sections": [
        ("What is Nested PCR?", "<p>Nested PCR is a modification of conventional PCR that uses two sequential amplification reactions with two sets of primers. In the first round, <strong>outer primers</strong> amplify a larger region of the target DNA. In the second round, <strong>inner primers</strong> (nested primers) bind within the first-round amplicon and amplify a smaller internal region. This two-round approach dramatically reduces non-specific amplification because any primer-dimer or off-target product from the first round is unlikely to contain binding sites for both inner primers.</p><p>First described in the late 1980s, nested PCR has become a gold-standard technique for detecting low-abundance targets, such as viral genomes in clinical samples, rare transcripts in single-cell RNA-seq, and ancient DNA in forensic specimens. The technique offers extraordinary specificity and sensitivity, often detecting as few as 1\u201310 starting copies of target DNA.</p>"),
        ("Why Use Nested PCR?", "<p>The primary advantage of nested PCR is its extraordinary specificity. By requiring two independent primer sets to successfully amplify the target, the probability of amplifying a spurious product drops to nearly zero. This is especially valuable when working with complex genomic DNA or environmental samples where non-target DNA is abundant.</p><p>Nested PCR also offers higher sensitivity than single-round PCR. After 25\u201335 cycles in the first round, the target is enriched by a factor of 10<sup>6</sup>\u201310<sup>9</sup>. The second round then amplifies this enriched template, allowing detection from extremely low starting copy numbers. This makes nested PCR ideal for detecting low-copy-number pathogens, analysing FFPE tissue samples with degraded DNA, and amplifying targets from forensic samples.</p>"),
        ("Designing Outer Primers", "<p>Outer primers define the outer boundaries of the first-round amplicon. Key design considerations include:</p><ul><li><strong>Amplicon size:</strong> The first-round amplicon should be 500\u20132000 bp. A larger amplicon allows more room for inner primer placement but may reduce amplification efficiency for degraded templates.</li><li><strong>Melting temperature (Tm):</strong> Outer primers should have a Tm of 60\u201368\u00b0C, with the forward and reverse Tm within 2\u00b0C of each other. Use the <a href=\"../tm-calculator.html\">VigyanLLM Tm calculator</a> for precise values.</li><li><strong>GC content:</strong> 40\u201360%, with the 3\u2032 end preferably ending in a G or C (GC clamp) to improve priming efficiency.</li><li><strong>Length:</strong> 18\u201324 nucleotides. Shorter primers may bind non-specifically; longer primers are more specific but may form secondary structures.</li><li><strong>Specificity:</strong> Run a <a href=\"../primer.html\">VigyanLLM Primer specificity check</a> against the target genome to verify the outer primers amplify only the intended locus.</li></ul>"),
        ("Designing Inner Primers", "<p>Inner (nested) primers bind within the first-round amplicon and define the second-round product.</p><ul><li><strong>Amplicon size:</strong> The inner amplicon should be 100\u2013400 bp for efficient amplification in the second round.</li><li><strong>Offset from outer primers:</strong> Inner primers should be at least 50\u2013100 bp inside the outer primer binding sites.</li><li><strong>Tm matching:</strong> The inner primers should have a Tm at least 5\u201310\u00b0C higher than the outer primers, allowing a two-step cycling strategy.</li><li><strong>Primer3 parameters:</strong> Use the <a href=\"../primer.html\">VigyanLLM Primer design tool</a> for optimised nested PCR parameters, including penalty weights for 3\u2032 stability and hairpin formation.</li></ul>"),
        ("Nested PCR Cycling Strategy", "<p>A typical nested PCR protocol involves:</p><h3>First Round</h3><ol><li><strong>Initial denaturation:</strong> 95\u00b0C for 3 min</li><li><strong>25\u201330 cycles of:</strong> 95\u00b0C for 30 s, 55\u201360\u00b0C (outer primer Ta) for 30 s, 72\u00b0C for 60 s/kb</li><li><strong>Final extension:</strong> 72\u00b0C for 5 min</li></ol><h3>Second Round</h3><ol><li>Use 1\u20132 \u00b5L of the first-round product (not purified) as template</li><li><strong>30\u201335 cycles of:</strong> 95\u00b0C for 30 s, 60\u201368\u00b0C (inner primer Ta) for 30 s, 72\u00b0C for 30 s/kb</li><li><strong>Final extension:</strong> 72\u00b0C for 5 min</li></ol><p>The higher annealing temperature in the second round leverages the higher Tm of the inner primers, providing an additional layer of specificity.</p>"),
        ("Troubleshooting Nested PCR", "<ul><li><strong>No product in second round:</strong> First-round amplification may have failed. Check first-round product by gel electrophoresis. Optimise outer primer Tm or increase template concentration.</li><li><strong>Multiple bands in second round:</strong> Inner primers may be binding non-specifically. Increase the second-round annealing temperature in 2\u00b0C increments or redesign inner primers.</li><li><strong>Carryover contamination:</strong> Use separate rooms for pre- and post-PCR work, dedicated pipettes with aerosol-resistant tips, and include no-template controls. Consider using uracil-DNA glycosylase (UDG) with dUTP.</li><li><strong>Weak second-round signal:</strong> Increase first-round cycles to 35 or use 5 \u00b5L of first-round product. Alternatively, purify the first-round product using magnetic beads.</li></ul>"),
        ("Applications of Nested PCR", "<p>Nested PCR is widely used in clinical virology (HIV, HBV, HCV detection), forensic DNA analysis, ancient DNA research, food safety testing, and single-cell analysis. For most modern applications, nested PCR is being complemented by digital PCR and targeted NGS approaches, but it remains a valuable technique for simple, cost-effective detection of known targets.</p>"),
    ],
    "related": ["touchdown-pcr-protocol", "hot-start-pcr-technology", "colony-pcr-primer-design"],
})

# 2. touchdown-pcr-protocol
articles.append({
    "slug": "touchdown-pcr-protocol",
    "title": "Touchdown PCR: How to Optimise Annealing Temperature Gradient for Cleaner Amplicons",
    "desc": "Master touchdown PCR to eliminate non-specific amplification. Learn how to design a temperature gradient protocol for cleaner, more specific PCR products every time.",
    "kw": "touchdown PCR, touchdown protocol, annealing temperature gradient, PCR optimisation, specific amplification, primer design",
    "tag": "Advanced PCR Techniques",
    "h1": "Touchdown PCR: How to Optimise Annealing Temperature Gradient for Cleaner Amplicons",
    "subtitle": "Touchdown PCR gradually lowers the annealing temperature across cycles to favour specific priming. This comprehensive guide explains the protocol, primer design adjustments, and troubleshooting.",
    "sections": [
        ("What is Touchdown PCR?", "<p>Touchdown PCR is a technique in which the annealing temperature is set several degrees above the calculated Tm of the primers during the initial cycles and then progressively decreased (or \"touch down\") to the optimal annealing temperature over subsequent cycles. The key insight is that at high annealing temperatures, only perfectly matched primer-template hybrids are stable enough to initiate extension. These specific products are exponentially amplified in the early cycles, vastly outnumbering any potential off-target templates.</p><p>Developed by Don et al. (1991), touchdown PCR is one of the simplest yet most effective ways to eliminate non-specific bands and primer-dimer artefacts without redesigning primers or reformulating the master mix.</p>"),
        ("The Touchdown Temperature Gradient", "<p>A typical touchdown protocol follows this pattern:</p><ul><li><strong>Initial denaturation:</strong> 95\u00b0C for 3 min</li><li><strong>Touchdown phase (10\u201315 cycles):</strong> Annealing temperature starts at 5\u201310\u00b0C above the calculated Tm and decreases by 0.5\u20131.0\u00b0C per cycle. For example, if the primer pair has a Tm of 60\u00b0C, start at 68\u00b0C and drop 0.5\u00b0C per cycle for 16 cycles.</li><li><strong>Non-touchdown phase (20\u201325 cycles):</strong> Annealing at the final optimal temperature.</li><li><strong>Extension and final extension:</strong> Standard conditions.</li></ul><p>The total number of touchdown cycles depends on the Tm spread between forward and reverse primers. If Tm values differ by 3\u20135\u00b0C, a 15-cycle touchdown with 0.5\u00b0C/cycle decrement is recommended.</p>"),
        ("Primer Design for Touchdown PCR", "<p>Touchdown PCR works best with primers designed to specific guidelines:</p><ul><li><strong>Higher Tm primers:</strong> Design primers with a calculated Tm of 62\u201368\u00b0C.</li><li><strong>Minimal Tm difference:</strong> Forward and reverse primer Tm should be within 1\u20132\u00b0C of each other.</li><li><strong>GC-rich 3\u2032 ends:</strong> A GC clamp at the 3\u2032 end (last 5 nucleotides with at least 2 G or C bases) stabilises specific binding at high temperatures.</li><li><strong>Avoid homopolymer runs:</strong> Runs of 4+ identical bases can cause slippage.</li><li><strong>Use the <a href=\"../primer.html\">VigyanLLM Primer design tool</a></strong> to automatically optimise for touchdown PCR.</li></ul>"),
        ("Setting Up the Touchdown Protocol", "<ol><li><strong>Calculate primer Tm:</strong> Use the <a href=\"../gc-calculator.html\">GC content calculator</a> and nearest-neighbour Tm algorithm for accurate values.</li><li><strong>Determine the touchdown range:</strong> Set the starting annealing temperature at 5\u201310\u00b0C above the lower Tm of the two primers.</li><li><strong>Determine the decrement:</strong> 0.5\u00b0C per cycle for 12\u201316 cycles (total drop of 6\u20138\u00b0C).</li><li><strong>Assemble the master mix:</strong> Standard components with 0.5 \u00b5M each primer and 1\u2013100 ng template DNA.</li><li><strong>Run the program and analyse</strong> by gel electrophoresis \u2014 expect a single, sharp band at the expected size.</li></ol>"),
        ("Troubleshooting Touchdown PCR", "<ul><li><strong>No amplification:</strong> The starting Ta may be too high. Lower the starting Ta by 2\u20133\u00b0C or reduce the decrement to 0.3\u00b0C/cycle.</li><li><strong>Non-specific bands still present:</strong> Increase the starting Ta by 2\u20135\u00b0C or increase the decrement to 1.0\u00b0C/cycle.</li><li><strong>Smear on gel:</strong> Template quality may be poor. Use less template (10 ng instead of 100 ng) or reduce extension time.</li><li><strong>Primer-dimer:</strong> Redesign primers to avoid 3\u2032 complementarity. See the <a href=\"./primer-dimer-fix.html\">primer dimer elimination guide</a>.</li></ul>"),
        ("When to Use Touchdown PCR", "<p>Touchdown PCR is particularly useful for new primer pairs (auto-optimises annealing), degraded or complex templates (GC-rich DNA, FFPE samples), multiplex PCR with multiple primer pairs, and low-template PCR applications like forensics and liquid biopsy. While touchdown PCR adds 15\u201330 minutes to the run time, the improvement in amplicon quality often eliminates the need for gel extraction or re-amplification.</p>"),
    ],
    "related": ["nested-pcr-primer-design", "hot-start-pcr-technology", "pcr-troubleshooting-guide"],
})

# 3. hot-start-pcr-technology
articles.append({
    "slug": "hot-start-pcr-technology",
    "title": "Hot-Start PCR: Mechanism, Enzymes, and Primer Design Considerations",
    "desc": "Learn how hot-start PCR technology prevents non-specific amplification. Compare antibody-mediated, chemical, and aptamer-based hot-start mechanisms for cleaner PCR.",
    "kw": "hot-start PCR, hot-start DNA polymerase, antibody-mediated hot start, chemical hot start, aptamer hot start, PCR specificity",
    "tag": "Advanced PCR Techniques",
    "h1": "Hot-Start PCR: Mechanism, Enzymes, and Primer Design Considerations",
    "subtitle": "Hot-start PCR technology prevents polymerase activity during reaction setup and initial ramp, eliminating primer-dimer and non-specific amplification. Compare mechanisms, enzymes, and design strategies.",
    "sections": [
        ("What is Hot-Start PCR?", "<p>Hot-start PCR keeps the DNA polymerase inactive until the reaction reaches high temperature (typically 95\u00b0C) during the initial denaturation step. This prevents polymerase activity during reaction setup and the initial temperature ramp, when primers can bind non-specifically to partially melted template DNA or to each other. By blocking polymerase activity at low temperatures, hot-start PCR dramatically reduces non-specific amplification and improves yield, sensitivity, and reproducibility.</p><p>Standard Taq polymerase has measurable activity at room temperature. During the several minutes between assembling the reaction and reaching denaturation temperature, the polymerase can extend non-specifically bound primers, creating artefacts that compete with the target during subsequent cycles.</p>"),
        ("Mechanisms of Hot-Start Inhibition", "<p>Three main mechanisms are used:</p><h3>Antibody-Mediated Hot Start</h3><p>A monoclonal antibody binds to the DNA polymerase, blocking its active site. The antibody denatures and releases at 95\u00b0C, allowing polymerase function. Advantages: rapid activation (2\u20133 min) and complete inhibition at low temperatures.</p><h3>Chemical Modification</h3><p>A heat-labile chemical group is covalently attached to the polymerase's active site, rendering it inactive until heated at 95\u00b0C for 5\u201310 minutes. Advantages: extremely stable at room temperature; no antibody present in the final reaction.</p><h3>Aptamer-Mediated Hot Start</h3><p>A short DNA or RNA aptamer binds reversibly to the polymerase and dissociates at high temperature. Offers fast activation kinetics.</p>"),
        ("Choosing a Hot-Start Polymerase", "<table><tr><th>Type</th><th>Activation Time</th><th>Room Temp Stability</th><th>Best For</th></tr><tr><td>Antibody-mediated</td><td>2\u20133 min</td><td>Good (hours)</td><td>Routine PCR, qPCR</td></tr><tr><td>Chemical modification</td><td>5\u201310 min</td><td>Excellent (weeks)</td><td>High-throughput, automation</td></tr><tr><td>Aptamer-mediated</td><td>1\u20132 min</td><td>Good (hours)</td><td>Fast-cycling PCR</td></tr></table><p>For most laboratory applications, antibody-mediated hot-start polymerases offer the best balance of convenience and cost.</p>"),
        ("Primer Design for Hot-Start PCR", "<p><ul><li><strong>Standard rules apply:</strong> 18\u201324 nt length, 40\u201360% GC, Tm of 60\u201365\u00b0C.</li><li><strong>Avoid 3\u2032 complementarity:</strong> Even with hot-start, primers with complementary 3\u2032 ends can form dimers during the 95\u00b0C step if stable enough to survive denaturation.</li><li><strong>Optimise for longer activation:</strong> For chemically modified polymerases, the longer 95\u00b0C activation step can cause primer degradation. Use GC-rich 3\u2032 ends.</li><li><strong>Reduce primer concentration:</strong> Hot-start PCR is so efficient that primer concentrations can often be reduced to 0.2\u20130.4 \u00b5M.</li></ul>Use the <a href=\"../primer.html\">VigyanLLM Primer</a> for automated design with hot-start optimisation.</p>"),
        ("Hot-Start vs Cold-Start vs Touchdown", "<p><strong>Hot-start PCR</strong> prevents polymerase activity during setup. <strong>Cold-start PCR</strong> (reactions assembled on ice and placed into a pre-heated cycler) is less effective but useful when hot-start polymerases are unavailable. <strong>Touchdown PCR</strong> uses temperature gradient during cycling to favour specific priming (see the <a href=\"./touchdown-pcr-protocol.html\">touchdown PCR guide</a>). For maximum specificity, combine hot-start polymerase with a touchdown protocol.</p>"),
        ("Common Hot-Start PCR Problems", "<ul><li><strong>Incomplete activation:</strong> Verify the recommended activation time in the manufacturer's instructions.</li><li><strong>Excessive activation time:</strong> Over-activation can partially denature the polymerase itself.</li><li><strong>Cost:</strong> Hot-start polymerases cost 2\u20135\u00d7 more than standard Taq. For routine work from high-quality templates, standard Taq may suffice.</li><li><strong>Buffer compatibility:</strong> Some hot-start polymerases require specific buffer conditions. Always use the manufacturer's recommended buffer.</li></ul>"),
    ],
    "related": ["nested-pcr-primer-design", "touchdown-pcr-protocol", "real-time-pcr-data-analysis"],
})

# 4. colony-pcr-primer-design
articles.append({
    "slug": "colony-pcr-primer-design",
    "title": "Colony PCR: Primer Design for Bacterial Colony Screening",
    "desc": "Optimise colony PCR primer design for fast bacterial screening. Learn how to pick vector-specific and insert-specific primers for colony PCR workflows.",
    "kw": "colony PCR, colony PCR primer design, bacterial colony screening, insert screening, vector-specific primers, colony PCR protocol",
    "tag": "Advanced PCR Techniques",
    "h1": "Colony PCR: Primer Design for Bacterial Colony Screening",
    "subtitle": "Colony PCR is a rapid screening method to identify bacterial colonies containing the correct recombinant plasmid. This guide covers primer design strategies, protocol optimisation, and troubleshooting.",
    "sections": [
        ("What is Colony PCR?", "<p>Colony PCR is a high-throughput screening technique used to determine whether bacterial colonies contain a plasmid with the correct insert. A small amount of the bacterial colony is transferred directly into the PCR master mix. The initial 95\u00b0C denaturation step lyses the bacterial cells, releasing the plasmid DNA into the reaction as template. The PCR product is analysed by gel electrophoresis to confirm the presence and size of the insert.</p><p>Colony PCR is faster, cheaper, and simpler than traditional plasmid miniprep screening, making it ideal for cloning projects and library screening of 96 or more colonies.</p>"),
        ("Primer Design Strategies for Colony PCR", "<p><strong>Vector-Specific Primers:</strong> Primers anneal to the vector backbone flanking the multiple cloning site (M13 forward/reverse, T7 promoter/terminator, SP6 primers). The product size indicates insert length. The same primer pair works for any insert in the same vector. Empty vector produces a small product equal to the MCS region.</p><p><strong>Insert-Specific Primers:</strong> Primers anneal within the insert itself. Only colonies containing the insert produce a PCR product, eliminating empty-vector false positives.</p><p>Use vector-specific primers for primary screening and insert-specific primers for confirmation.</p>"),
        ("Designing Vector-Specific Primers", "<ul><li><strong>Binding position:</strong> 50\u2013200 bp upstream and downstream of the MCS.</li><li><strong>Tm of 58\u201362\u00b0C:</strong> Ensures robust amplification despite bacterial debris in the reaction.</li><li><strong>GC content 40\u201355%:</strong> Avoid GC-rich vector regions that may form secondary structures.</li><li><strong>Product size:</strong> For inserts >500 bp, the combined product is typically 400\u20132000 bp.</li><li><strong>Use the <a href=\"../primer.html\">VigyanLLM Primer tool</a></strong> to verify primer specificity against the vector sequence before ordering.</li></ul>"),
        ("Colony PCR Protocol", "<ol><li><strong>Prepare master mix</strong> (per 20 \u00b5L): 10 \u00b5L 2X master mix, 0.5 \u00b5L each primer, 0.2\u20130.5 \u00b5L DMSO (optional), water to 20 \u00b5L.</li><li><strong>Pick a single colony</strong> with a sterile pipette tip and swirl in the master mix.</li><li><strong>Include controls:</strong> Positive control (purified plasmid), empty-vector control, no-template control.</li><li><strong>Run thermal cycling:</strong> 95\u00b0C for 5 min; 30\u201335 cycles of 95\u00b0C for 30 s, 55\u201360\u00b0C for 30 s, 72\u00b0C for 30\u201360 s/kb; 72\u00b0C for 5 min.</li><li><strong>Analyse by gel electrophoresis</strong> (1\u20132% agarose).</li></ol>"),
        ("Troubleshooting Colony PCR", "<ul><li><strong>No amplification:</strong> Ensure the colony was transferred. Increase initial denaturation to 10 min for difficult-to-lyse bacteria.</li><li><strong>Weak amplification:</strong> Resuspend the colony in 20 \u00b5L water, boil for 5 min, centrifuge, and use 2 \u00b5L supernatant as template.</li><li><strong>Multiple bands:</strong> Bacterial genomic DNA in the lysate. Increase annealing temperature by 2\u20135\u00b0C. Use a hot-start polymerase.</li><li><strong>Empty-vector product only:</strong> The colony may contain empty vector. Use insert-specific primers for secondary screening.</li></ul>"),
        ("High-Throughput Colony PCR", "<p>For screening 96 or 384 colonies, reduce reaction volume to 10 \u00b5L, use a 96-well plate and multichannel pipette, and consider automated colony picking robots. Replace gel electrophoresis with capillary electrophoresis (QIAxcel, TapeStation) for faster analysis. The <a href=\"../primer-design.html\">VigyanLLM primer design pipeline</a> can batch-design vector and insert-specific primers for large projects.</p>"),
    ],
    "related": ["nested-pcr-primer-design", "pcr-multiplex-optimization", "primer-dimer-fix"],
})


# 5. pcr-multiplex-optimization
articles.append({
    "slug": "pcr-multiplex-optimization",
    "title": "PCR Multiplex Optimisation: Primer Ratios, Master Mix, and Cycling Conditions",
    "desc": "Optimise your multiplex PCR with best practices for primer ratios, master mix formulation, and thermal cycling. Achieve balanced amplification of multiple targets.",
    "kw": "multiplex PCR optimisation, multiplex PCR primer ratios, multiplex master mix, multiplex PCR cycling, multi-target PCR",
    "tag": "Advanced PCR Techniques",
    "h1": "PCR Multiplex Optimisation: Primer Ratios, Master Mix, and Cycling Conditions",
    "subtitle": "Multiplex PCR amplifies multiple targets simultaneously but requires careful optimisation of primer ratios, master mix components, and cycling conditions for balanced amplification.",
    "sections": [
        ("What is Multiplex PCR?", "<p>Multiplex PCR amplifies two or more target sequences simultaneously by including multiple primer pairs in a single reaction. It is widely used in pathogen detection panels, genetic fingerprinting, SNP genotyping, and NGS library preparation. Successful multiplex PCR requires balanced amplification \u2014 each target should be amplified with similar efficiency.</p><p>This guide covers the three pillars of multiplex optimisation: primer design, master mix formulation, and cycling conditions.</p>"),
        ("Primer Design for Multiplex PCR", "<ul><li><strong>Uniform Tm:</strong> All primers should have Tm values within 1\u20132\u00b0C of each other. Use the <a href=\"../tm-calculator.html\">VigyanLLM Tm calculator</a> for accurate nearest-neighbour prediction.</li><li><strong>No inter-primer complementarity:</strong> Check all primer pairs for 3\u2032 complementarity. The <a href=\"../primer.html\">VigyanLLM Primer tool</a> includes automatic multiplex compatibility checking.</li><li><strong>Amplicon size differentiation:</strong> Each target should produce a distinct size (difference of 50\u2013100 bp minimum).</li><li><strong>GC content 40\u201360%</strong> for all primers.</li><li><strong>Limit:</strong> 4\u20135 primer pairs for conventional multiplex; up to 100+ for specialised methods.</li></ul>"),
        ("Primer Ratio Optimisation", "<ol><li><strong>Start with equal concentrations:</strong> All primers at 0.2 \u00b5M each.</li><li><strong>Identify imbalance:</strong> Compare band intensities on gel. Stronger bands = more efficient amplification.</li><li><strong>Adjust ratios:</strong> Increase weaker targets (up to 0.5\u20131.0 \u00b5M) and decrease stronger targets (down to 0.05\u20130.1 \u00b5M).</li><li><strong>Iterate:</strong> 2\u20133 rounds typically achieve balanced amplification.</li><li><strong>Document final ratios</strong> for reproducibility.</li></ol>"),
        ("Master Mix Optimisation", "<ul><li><strong>DNA polymerase:</strong> Use a high-quality hot-start polymerase specifically designed for multiplex reactions. See the <a href=\"./hot-start-pcr-technology.html\">hot-start PCR guide</a>.</li><li><strong>Mg<sup>2+</sup>:</strong> Typically higher (2.5\u20134.0 mM) than single-plex. Optimise in 0.5 mM increments.</li><li><strong>dNTPs:</strong> Increase to 300\u2013400 \u00b5M each. Avoid exceeding 500 \u00b5M.</li><li><strong>Additives:</strong> 2\u20135% DMSO or 0.5\u20131 M betaine for GC-rich templates.</li></ul>"),
        ("Cycling Condition Optimisation", "<ul><li><strong>Longer initial denaturation:</strong> 5\u201310 min at 95\u00b0C.</li><li><strong>Annealing temperature:</strong> 1\u20132\u00b0C below the lowest primer Tm.</li><li><strong>Annealing time:</strong> 45\u201360 s (vs. 15\u201330 s for single-plex).</li><li><strong>Extension time:</strong> Base on the longest amplicon, add 30\u201350% extra time.</li><li><strong>Touchdown protocol:</strong> Consider a <a href=\"./touchdown-pcr-protocol.html\">touchdown PCR</a> approach for the first 10 cycles.</li></ul>"),
        ("Troubleshooting Multiplex PCR", "<ul><li><strong>Missing targets:</strong> Increase primer concentrations or extend annealing time.</li><li><strong>Uneven amplification:</strong> Adjust primer ratios as described above.</li><li><strong>Non-specific bands:</strong> Increase annealing temperature in 2\u00b0C increments.</li><li><strong>Primer-dimer:</strong> Reduce primer concentrations and check for 3\u2032 complementarity.</li></ul>"),
        ("Applications of Multiplex PCR", "<p>Multiplex PCR is used in pathogen detection panels (respiratory, gastrointestinal), STR genotyping for forensics, SNP genotyping, NGS library preparation, and GMO detection. The <a href=\"../primer.html\">VigyanLLM Primer tool</a> includes automatic multiplex compatibility checking and primer ratio recommendations.</p>"),
    ],
    "related": ["real-time-pcr-data-analysis", "nested-pcr-primer-design", "primer-dimer-fix"],
})

# 6. real-time-pcr-data-analysis
articles.append({
    "slug": "real-time-pcr-data-analysis",
    "title": "Real-Time PCR Data Analysis: Ct Values, Amplification Efficiency, and Melt Curves",
    "desc": "Master real-time PCR (qPCR) data analysis with this guide on Ct values, amplification efficiency, standard curves, and melt curve interpretation.",
    "kw": "real-time PCR data analysis, qPCR data analysis, Ct values, amplification efficiency, melt curve analysis, qPCR standard curve",
    "tag": "Advanced PCR Techniques",
    "h1": "Real-Time PCR Data Analysis: Ct Values, Amplification Efficiency, and Melt Curves",
    "subtitle": "Real-time PCR (qPCR) generates quantitative data through fluorescence monitoring. This guide explains how to analyse Ct values, calculate amplification efficiency, interpret melt curves, and apply correct normalisation.",
    "sections": [
        ("Introduction to Real-Time PCR Data", "<p>Real-time PCR monitors the accumulation of PCR product in real time by measuring fluorescence after each cycle. The instrument generates amplification curves from which two primary data types are extracted: the threshold cycle (Ct or Cq) and the melt curve (for dye-based qPCR). Proper data analysis is critical for reliable, reproducible results. The MIQE guidelines provide a framework for best practices in qPCR experimental design and data analysis.</p>"),
        ("Understanding Ct Values", "<p>The threshold cycle (Ct) is the cycle at which fluorescence crosses a defined threshold above background. Ct is inversely proportional to starting target quantity: more template = lower Ct. A well-designed assay should have a dynamic range of 5\u20137 log<sub>10</sub> orders with R<sup>2</sup> > 0.98. Typical Ct values: 15\u201320 (abundant), 20\u201325 (moderate), 25\u201330 (low), 30\u201335 (very low). No-template controls should have Ct > 35 or undetermined.</p>"),
        ("Amplification Efficiency", "<p>Amplification efficiency (E) is calculated from a standard curve: E = 10<sup>(-1/slope)</sup>. Acceptable range: 90\u2013110% (slope \u22123.58 to \u22123.10). Low efficiency (<90%) suggests poor primer design or inhibitors. High efficiency (>110%) suggests non-specific amplification or primer-dimer. For \u0394\u0394Ct analysis, target and reference efficiencies must be within 10% of each other, or use the efficiency-corrected Pfaffl method.</p>"),
        ("Melt Curve Analysis", "<p>Melt curve analysis monitors fluorescence while slowly increasing temperature from 60\u00b0C to 95\u00b0C. A single peak indicates a specific product. Multiple peaks indicate non-specific products or primer-dimer (typically melting at 75\u201380\u00b0C). Broad peaks may indicate heterogenous products. Peak Tm shifts between samples may indicate sequence variation (useful for HRM genotyping).</p>"),
        ("Standard Curve and Absolute Quantification", "<p>For absolute quantification, serially dilute a known DNA standard across 5\u20137 orders of magnitude, run in triplicate, plot Ct vs. log concentration, and fit a linear regression. Check R<sup>2</sup> > 0.99 and slope \u22123.3 \u00b1 0.2. Interpolate unknown concentrations from the standard curve. The quality of the standard is paramount \u2014 use authenticated, quantified standards.</p>"),
        ("Relative Quantification (\u0394\u0394Ct)", "<p>Normalise to a reference gene: \u0394Ct = Ct(target) \u2212 Ct(reference). \u0394\u0394Ct = \u0394Ct(treated) \u2212 \u0394Ct(control). Fold change = 2<sup>(-\u0394\u0394Ct)</sup>. If efficiencies differ, use the Pfaffl method. Validate reference gene stability using geNorm or NormFinder. Using 2\u20133 reference genes improves accuracy.</p>"),
        ("Troubleshooting qPCR Data", "<ul><li><strong>High Ct variation (SD > 0.5):</strong> Pipetting inconsistency. Use master mix and calibrate pipettes.</li><li><strong>Poor standard curve (R<sup>2</sup> < 0.95):</strong> Serial dilution errors. Prepare fresh standards.</li><li><strong>NTC amplification:</strong> Contamination or primer-dimer. See the <a href=\"./primer-dimer-fix.html\">primer dimer guide</a>.</li><li><strong>Low fluorescence:</strong> Insufficient probe concentration or poor dye binding.</li><li><strong>Melt curve shoulder:</strong> Secondary product. Increase annealing temperature.</li></ul>"),
    ],
    "related": ["pcr-multiplex-optimization", "taqman-probe-troubleshooting", "primer-design-mrna"],
})

# 7. degenerate-primer-design
articles.append({
    "slug": "degenerate-primer-design",
    "title": "Degenerate Primer Design: Conserved Region Alignment and Codon Optimisation",
    "desc": "Design degenerate primers for conserved regions across related gene families. Learn alignment strategies, codon degeneracy, and inosine usage for broad-specificity PCR.",
    "kw": "degenerate primer design, degenerate primers, codon degeneracy, conserved region alignment, inosine primers, consensus primer",
    "tag": "Advanced Primer Design",
    "h1": "Degenerate Primer Design: Conserved Region Alignment and Codon Optimisation",
    "subtitle": "Degenerate primers incorporate mixed bases at positions of codon variability, enabling amplification of homologous genes across species. Master alignment-based design, codon optimisation, and inosine usage.",
    "sections": [
        ("What Are Degenerate Primers?", "<p>Degenerate primers are mixtures of similar primers containing one or more positions with multiple different nucleotides. They are designed to amplify a target gene from multiple species, strains, or related gene family members despite sequence variation at the primer binding sites. Degeneracy is expressed as the total number of sequence combinations in the primer pool &#8212; for example, a primer with the sequence 5\u2032-GAYCTNCCRTG-3\u2032 has a degeneracy of 32. Limit total degeneracy to 128\u2013256 combinations for most applications.</p>"),
        ("Designing from Multiple Sequence Alignment", "<ol><li><strong>Collect sequences:</strong> Download 10\u201350 sequences from NCBI GenBank covering the desired diversity.</li><li><strong>Align sequences:</strong> Use Clustal Omega, MUSCLE, or MAFFT to identify conserved blocks.</li><li><strong>Identify conserved regions:</strong> Look for 18\u201324 contiguous nucleotides with 70\u2013100% conservation.</li><li><strong>Design forward primer</strong> near the 5\u2032 end and <strong>reverse primer</strong> near the 3\u2032 end of the target.</li><li><strong>Introduce degeneracy:</strong> Use IUPAC degenerate base codes at positions where nucleotides vary.</li></ol><p>The <a href=\"../primer.html\">VigyanLLM Primer tool</a> can import MSA files and automatically identify conserved regions.</p>"),
        ("IUPAC Codes and Degeneracy Limits", "<table><tr><th>Code</th><th>Nucleotides</th><th>Complement</th></tr><tr><td>R</td><td>A, G</td><td>Y</td></tr><tr><td>Y</td><td>C, T</td><td>R</td></tr><tr><td>S</td><td>G, C</td><td>S</td></tr><tr><td>W</td><td>A, T</td><td>W</td></tr><tr><td>K</td><td>G, T</td><td>M</td></tr><tr><td>M</td><td>A, C</td><td>K</td></tr><tr><td>B</td><td>C, G, T</td><td>V</td></tr><tr><td>N</td><td>A, C, G, T</td><td>N</td></tr></table><p>Limit total degeneracy to 128\u2013256 combinations. Higher degeneracy increases non-functional primer fraction and may reduce amplification efficiency.</p>"),
        ("Codon Optimisation", "<p>When designing degenerate primers for cross-species amplification, consider codon usage bias. At each amino acid position, the possible codons determine required degeneracy. Leucine and serine have 6 codons each (high degeneracy), while methionine and tryptophan have only 1 codon each. If possible, place primers in regions enriched for low-degeneracy amino acids. Inosine (I) can pair with A, C, or T and is useful at 3-fold or 4-fold degenerate positions, but reduces Tm by approximately 5\u00b0C per substitution.</p>"),
        ("Tm Calculation for Degenerate Primers", "<p>Nearest-neighbour averaging (calculating Tm for each variant and averaging) is the most accurate method, used by the <a href=\"../tm-calculator.html\">VigyanLLM Tm calculator</a>. Alternatively, use the most AT-rich variant (conservative estimate). Rule of thumb: use an annealing temperature 3\u20135\u00b0C below the lowest Tm in the degenerate pool. If amplification fails, try a <a href=\"./touchdown-pcr-protocol.html\">touchdown PCR</a> approach.</p>"),
        ("Troubleshooting Degenerate PCR", "<ul><li><strong>No amplification:</strong> Degeneracy may be too high. Increase primer concentration to 1\u20132 \u00b5M each or redesign with lower degeneracy.</li><li><strong>Multiple bands:</strong> Increase annealing temperature or use <a href=\"./nested-pcr-primer-design.html\">nested PCR</a> with internal degenerate primers.</li><li><strong>Weak or biased amplification:</strong> Some species may amplify better than others. Consider splitting into separate primer pools.</li></ul>"),
    ],
    "related": ["isothermal-amplification-primers", "primer-design-mrna", "sequencing-primer-design"],
})

# 8. isothermal-amplification-primers
articles.append({
    "slug": "isothermal-amplification-primers",
    "title": "Isothermal Amplification: LAMP and RPA Primer Design Strategies",
    "desc": "Design primers for isothermal amplification methods including LAMP (4\u20136 primers per target) and RPA. Learn design software, Tm rules, and amplicon requirements.",
    "kw": "isothermal amplification primers, LAMP primer design, RPA primer design, loop-mediated isothermal amplification, recombinase polymerase amplification",
    "tag": "Advanced Primer Design",
    "h1": "Isothermal Amplification: LAMP and RPA Primer Design Strategies",
    "subtitle": "Isothermal amplification methods like LAMP and RPA amplify nucleic acids at a single temperature without a thermal cycler. This guide covers primer design rules, software tools, and optimisation strategies.",
    "sections": [
        ("What Is Isothermal Amplification?", "<p>Isothermal amplification methods amplify nucleic acids at a constant temperature. <strong>LAMP (Loop-Mediated Isothermal Amplification)</strong> uses 4\u20136 primers targeting 6\u20138 distinct regions at 60\u201365\u00b0C using a strand-displacing polymerase. <strong>RPA (Recombinase Polymerase Amplification)</strong> uses a single primer pair plus three enzymes at 37\u201342\u00b0C in 20\u201330 minutes. Both methods are ideal for point-of-care diagnostics and field-based testing.</p>"),
        ("LAMP Primer Design Overview", "<p>LAMP requires 4 primers targeting 6 regions: <strong>F3</strong> (outer, 18\u201322 nt, Tm 58\u201362\u00b0C), <strong>B3</strong> (outer, same criteria), <strong>FIP</strong> (inner, 38\u201344 nt, contains F1c + F2), and <strong>BIP</strong> (inner, contains B1c + B2). Optional <strong>loop primers</strong> (LF, LB) accelerate amplification and reduce detection time by 30\u201350%.</p>"),
        ("LAMP Primer Design Rules", "<ul><li><strong>Distance between regions:</strong> F2 to F1: 40\u201360 bp; the total target (F3 to B3) should be 200\u2013300 bp.</li><li><strong>GC content:</strong> 45\u201360% for all primers.</li><li><strong>Tm guidelines:</strong> Outer primers Tm 58\u201362\u00b0C; inner F2/B2 region Tm 60\u201365\u00b0C; F1c/B1c region Tm 65\u201370\u00b0C.</li><li><strong>3\u2032 end specificity:</strong> The 3\u2032 ends of FIP and BIP must be highly specific.</li><li><strong>Loop primer Tm:</strong> 58\u201362\u00b0C, binding 10\u201320 nt from F1/B1.</li></ul>"),
        ("RPA Primer Design", "<ul><li><strong>Primer length:</strong> 30\u201335 nt (shorter primers may not form recombinase filaments efficiently).</li><li><strong>GC content:</strong> 40\u201355%. RPA works poorly with GC-rich (>60%) or AT-rich (<30%) primers.</li><li><strong>Product size:</strong> 100\u2013250 bp optimal. Efficiency drops sharply >500 bp.</li><li><strong>No secondary structure:</strong> Primers must be free of significant secondary structure (\u0394G < \u22122 kcal/mol).</li><li><strong>Avoid homopolymer runs</strong> of >4 nt.</li></ul>"),
        ("Software Tools", "<p>Tools include PrimerExplorer V5 (gold standard for LAMP), NEB LAMP Design Tool, <a href=\"../primer.html\">VigyanLLM Primer</a> (supports LAMP and RPA design), TwistDx guidelines, and Geneious plugins.</p>"),
        ("Troubleshooting", "<ul><li><strong>LAMP no amplification:</strong> Check inner:outer primer ratio (4:1 to 8:1). Verify Bst polymerase activity. Add loop primers.</li><li><strong>LAMP non-specific:</strong> Increase temperature to 65\u00b0C. Redesign with higher Tm F1c/B1c.</li><li><strong>RPA no amplification:</strong> Ensure MgOAc is added last. Verify primers are 30\u201335 nt.</li><li><strong>RPA weak signal:</strong> Redesign for smaller amplicon. Add TwistAmp Exo probes.</li></ul>"),
    ],
    "related": ["degenerate-primer-design", "sequencing-primer-design", "taqman-probe-troubleshooting"],
})

# 9. primer-design-mrna
articles.append({
    "slug": "primer-design-mrna",
    "title": "Primers for mRNA/cDNA: Exon-Exon Junctions and Intron Spanning Strategies",
    "desc": "Design RT-qPCR primers for mRNA quantification. Learn exon-exon junction spanning, intron spanning, and how to avoid genomic DNA amplification in gene expression analysis.",
    "kw": "mRNA primer design, cDNA primer design, exon-exon junction primers, intron spanning primers, RT-qPCR primers, gene expression primers",
    "tag": "Advanced Primer Design",
    "h1": "Primers for mRNA/cDNA: Exon-Exon Junctions and Intron Spanning Strategies",
    "subtitle": "Accurate gene expression analysis by RT-qPCR requires primers that amplify cDNA but not genomic DNA. Master exon-exon junction design and intron-spanning strategies for specific mRNA detection.",
    "sections": [
        ("Why mRNA-Specific Primer Design Matters", "<p>Gene expression analysis by RT-qPCR measures mRNA abundance by converting RNA to cDNA and amplifying the cDNA. The critical challenge is distinguishing cDNA from contaminating genomic DNA (gDNA). Two strategies address this: (1) <strong>exon-exon junction spanning</strong> \u2014 the primer spans a splice junction so it can only bind to cDNA, and (2) <strong>intron spanning</strong> \u2014 primers in different exons produce a large gDNA product that does not amplify efficiently.</p>"),
        ("Exon-Exon Junction Primers", "<p>An exon-exon junction primer has 3\u20136 bases on one side of a splice junction and the remaining bases on the other. The 3\u2032 end should cross the junction to ensure extension cannot occur from gDNA. Typically 5\u201310 bases on each side. Check Ensembl or UCSC for annotated isoforms and avoid regions subject to alternative splicing. Always validate by running a gDNA-only control (no RT).</p>"),
        ("Intron-Spanning Primer Pairs", "<p>Forward primer in one exon, reverse in a downstream exon with the intron(s) in between. The cDNA product is 80\u2013250 bp; the gDNA product is 500 bp to >10 kb and does not amplify under short extension times (30\u201340 s). The intron should be at least 500 bp. Always include a no-RT control to verify gDNA exclusion.</p>"),
        ("Primer Design Workflow for mRNA Targets", "<ol><li>Obtain the mRNA sequence from RefSeq (NM_ accession) or Ensembl.</li><li>Identify constitutive exon-exon junctions present in all transcript variants.</li><li>Design primers with the <a href=\"../primer.html\">VigyanLLM Primer tool</a>: length 20\u201324 nt, Tm 60\u201365\u00b0C, GC 50\u201360%, amplicon 80\u2013200 bp, with junction or intron-spanning design.</li><li>Check specificity with NCBI Primer-BLAST or VigyanLLM specificity checker.</li><li>Validate by RT-qPCR with melt curve analysis.</li></ol>"),
        ("Validating mRNA-Specific Primers", "<ul><li><strong>Standard curve:</strong> R<sup>2</sup> > 0.99 and 90\u2013110% efficiency.</li><li><strong>Melt curve:</strong> Single peak confirms specificity. See <a href=\"./primer-dimer-fix.html\">primer dimer guide</a> for multiple peaks.</li><li><strong>No-RT control:</strong> Ct > 35 confirms no gDNA contamination.</li><li><strong>RNA integrity:</strong> RIN > 7 for reliable results.</li></ul>"),
        ("Common Mistakes", "<ul><li>Designing in repetitive elements (use RepeatMasker).</li><li>Ignoring SNPs (check dbSNP).</li><li>Using pseudogene sequences (check for pseudogenes via BLAST).</li><li>Not checking off-target homology to paralogous genes.</li><li>Forgetting to check mRNA secondary structure in the primer binding region (use Mfold).</li></ul>"),
    ],
    "related": ["real-time-pcr-data-analysis", "sequencing-primer-design", "taqman-probe-troubleshooting"],
})

# 10. sequencing-primer-design
articles.append({
    "slug": "sequencing-primer-design",
    "title": "Sanger Sequencing Primer Design: Read Length, Quality, and Positioning",
    "desc": "Design Sanger sequencing primers for long reads and clean chromatograms. Learn optimal primer positioning, dye-terminator compatibility, and troubleshooting failed sequencing.",
    "kw": "Sanger sequencing primer design, sequencing primers, dye-terminator sequencing, primer walking, sequencing read quality, chromatogram quality",
    "tag": "Advanced Primer Design",
    "h1": "Sanger Sequencing Primer Design: Read Length, Quality, and Positioning",
    "subtitle": "Sanger sequencing remains the gold standard for amplicon and plasmid validation. Learn how to design primers that produce long, high-quality reads with clean chromatograms.",
    "sections": [
        ("Sanger Sequencing Primer Design Principles", "<p>Sanger sequencing primers must produce a clean, strong signal, not interfere with dye-terminator chemistry, bind uniquely (even a single mismatch can cause mixed reads), and work at the sequencing reaction temperature (55\u201365\u00b0C). Most sequencing primers are 18\u201324 nt. For plasmid sequencing, universal primers (M13, T7, SP6) are preferred.</p>"),
        ("Primer Length and Tm", "<ul><li><strong>Length:</strong> 18\u201324 nt (25\u201330 nt for GC-rich or complex templates).</li><li><strong>Tm:</strong> 55\u201365\u00b0C (nearest-neighbour algorithm). Annealing temperature for Sanger sequencing is typically 50\u201360\u00b0C.</li><li><strong>GC content:</strong> 45\u201355%. Low GC (<40%) causes weak signal; high GC (>60%) causes noise.</li><li><strong>Tm matching:</strong> Within 2\u20133\u00b0C of the sequencing chemistry recommendation. Use the <a href=\"../tm-calculator.html\">VigyanLLM Tm calculator</a>.</li></ul>"),
        ("Primer Positioning for Optimal Read Quality", "<ul><li><strong>Distance from ROI:</strong> Position the primer 50\u2013150 bases upstream. The first 20\u201350 bases often have lower quality.</li><li><strong>Avoid homopolymer runs</strong> of >4 identical bases.</li><li><strong>Avoid GC-rich 5\u2032 ends</strong> that can form secondary structures.</li><li><strong>Bidirectional sequencing:</strong> Place primers 100\u2013150 bp outside the target region with 50\u2013100 bp overlap.</li><li><strong>Primer walking:</strong> Design the second primer 400\u2013500 bp from the first.</li></ul>"),
        ("Dye-Terminator Compatibility", "<ul><li><strong>Primer concentration:</strong> 1\u20135 pmol per reaction. Too much causes background; too little causes weak signal.</li><li><strong>Primer purity:</strong> HPLC or PAGE-purified primers preferred.</li><li><strong>Avoid 3\u2032 mismatches</strong> \u2014 even a single mismatch can produce mixed sequence.</li><li><strong>GC-rich templates:</strong> Add 5\u201310% DMSO. Use specialised polymerases.</li></ul>"),
        ("Troubleshooting Sanger Sequencing", "<ul><li><strong>Clean then noisy:</strong> Primer may have secondary structure or template contains repeats. Try a different primer position.</li><li><strong>Mixed peaks:</strong> Primer may bind two sites, or template contains a mixture. Redesign with higher specificity.</li><li><strong>No signal:</strong> Primer may not bind due to mismatch. Verify the primer sequence matches the template exactly.</li><li><strong>Early dye blobs:</strong> Clean the product by ethanol precipitation or use a commercial clean-up kit.</li></ul>"),
        ("Primer Walking for Long Reads", "<ol><li>Design the first primer at one end of the target.</li><li>Obtain 500\u2013800 high-quality bases.</li><li>Design a second primer within the high-quality region, 100\u2013150 bp from the end.</li><li>Repeat until the entire target is sequenced. Use the <a href=\"../primer.html\">VigyanLLM Primer tool</a> for automated primer-walking design.</li></ol>"),
    ],
    "related": ["primer-design-mrna", "taqman-probe-troubleshooting", "primer-dimer-fix"],
})

# 11. taqman-probe-troubleshooting
articles.append({
    "slug": "taqman-probe-troubleshooting",
    "title": "TaqMan Probe Troubleshooting: No Amplification, High Background, and Weak Signal",
    "desc": "Diagnose and fix common TaqMan probe problems. Learn how to troubleshoot no amplification, high background fluorescence, weak signal, and high Ct variation in qPCR assays.",
    "kw": "TaqMan probe troubleshooting, qPCR probe problems, no amplification TaqMan, high background qPCR, weak signal TaqMan, probe design",
    "tag": "Advanced Primer Design",
    "h1": "TaqMan Probe Troubleshooting: No Amplification, High Background, and Weak Signal",
    "subtitle": "Troubleshoot common TaqMan probe qPCR issues including no amplification, high background, weak signal, and high Ct variation. Practical solutions for probe-based assays.",
    "sections": [
        ("TaqMan Probe Chemistry Overview", "<p>TaqMan probes are dual-labelled fluorogenic hydrolysis probes with a reporter fluorophore (5\u2032) and a quencher (3\u2032). During PCR extension, the 5\u2032\u21923\u2032 exonuclease activity of Taq polymerase degrades the probe, separating the fluorophore from the quencher and generating a fluorescence signal proportional to target amount. TaqMan probes offer higher specificity than SYBR Green but are more sensitive to design flaws.</p>"),
        ("No Amplification (No Fluorescence Increase)", "<ul><li><strong>Probe not binding:</strong> Probe Tm should be 68\u201372\u00b0C (8\u201310\u00b0C above primer Tm). Use the <a href=\"../tm-calculator.html\">VigyanLLM Tm calculator</a>.</li><li><strong>Probe degraded:</strong> Store in single-use aliquots at \u221220\u00b0C, protect from light.</li><li><strong>Master mix:</strong> Use a master mix formulated for probe-based qPCR.</li><li><strong>Polymerase:</strong> Verify the polymerase has robust 5\u2032 exonuclease activity.</li></ul>"),
        ("High Background Fluorescence", "<ul><li><strong>Excess probe:</strong> Reduce from 300 nM to 200 nM.</li><li><strong>Incomplete quenching:</strong> Check probe for secondary structure. Use double-quenched probes (ZEN or TAO internal quencher).</li><li><strong>Contamination:</strong> Use dUTP/UDG. Prepare fresh master mix in a clean area.</li><li><strong>Reaction volume too small:</strong> Ensure the plate is sealed correctly.</li></ul>"),
        ("Weak Signal (Low \u0394Rn)", "<ul><li><strong>Suboptimal probe concentration:</strong> Titrate from 100\u2013400 nM. Most assays work at 200\u2013300 nM.</li><li><strong>Primer concentration:</strong> 300\u2013900 nM each for TaqMan (vs. 100\u2013300 nM for SYBR Green).</li><li><strong>Annealing/extension:</strong> Ensure the polymerase extends through the probe binding site.</li><li><strong>Template quality:</strong> Purify the template or add BSA.</li></ul>"),
        ("High Ct Variation Between Replicates", "<ul><li><strong>Pipetting errors:</strong> Use a master mix and pre-wet tips. Calibrate pipettes regularly.</li><li><strong>Template volume:</strong> Increase to 5 \u00b5L for better consistency.</li><li><strong>Air bubbles:</strong> Centrifuge the plate at 1000 g for 2 min.</li><li><strong>Edge effects:</strong> Pre-warm the block. Use a compression pad.</li></ul>"),
        ("TaqMan Primer and Probe Design Checklist", "<table><tr><th>Parameter</th><th>Optimal</th><th>Why</th></tr><tr><td>Primer Tm</td><td>58\u201362\u00b0C</td><td>Balanced efficiency</td></tr><tr><td>Probe Tm</td><td>68\u201372\u00b0C</td><td>Probe binds before extension</td></tr><tr><td>Probe length</td><td>15\u201325 nt</td><td>Specificity and quenching</td></tr><tr><td>GC content (probe)</td><td>30\u201380%</td><td>Avoid 5\u2032 G</td></tr><tr><td>Amplicon size</td><td>70\u2013150 bp</td><td>Efficient amplification</td></tr></table><p>Use the <a href=\"../primer.html\">VigyanLLM Primer design tool</a> for automated TaqMan design.</p>"),
    ],
    "related": ["real-time-pcr-data-analysis", "primer-dimer-fix", "primer-design-mrna"],
})

# 12. primer-dimer-fix
articles.append({
    "slug": "primer-dimer-fix",
    "title": "Primer Dimer: Causes, Detection, and Elimination Strategies",
    "desc": "Fix primer dimer problems in your PCR and qPCR assays. Learn how to detect, diagnose, and eliminate primer dimers through design and protocol optimisation.",
    "kw": "primer dimer, primer dimer detection, eliminate primer dimer, PCR primer dimer, qPCR primer dimer, primer dimer fix, primer dimer causes",
    "tag": "Advanced Primer Design",
    "h1": "Primer Dimer: Causes, Detection, and Elimination Strategies",
    "subtitle": "Primer dimer is one of the most common PCR artefacts. This guide explains what causes primer dimer, how to detect it, and proven strategies to eliminate it through primer design and protocol optimisation.",
    "sections": [
        ("What Is Primer Dimer?", "<p>Primer dimer is a non-specific PCR product formed when primers hybridise to each other and are extended by DNA polymerase. Primer dimers appear as low-molecular-weight bands or smears (<50\u2013100 bp) on agarose gels. In SYBR Green qPCR, primer dimer produces a melt peak at 75\u201380\u00b0C, inflating fluorescence and leading to inaccurate quantification. Primer dimer occurs due to partial complementarity between primers, especially at 3\u2032 ends.</p>"),
        ("Causes of Primer Dimer", "<ul><li><strong>3\u2032 complementarity:</strong> The most common cause. Even 2\u20133 complementary bases at 3\u2032 ends can cause extension.</li><li><strong>Excess primer concentration:</strong> >1 \u00b5M significantly increases dimer risk.</li><li><strong>Low template concentration:</strong> Primers encounter each other more often than template.</li><li><strong>Suboptimal annealing temperature:</strong> Low Ta promotes non-specific binding.</li><li><strong>Slow ramp rate</strong> during denaturation-to-annealing transition.</li></ul>"),
        ("Detecting Primer Dimer", "<p>Primer dimer can be detected by agarose gel electrophoresis (band or smear <100 bp), melt curve analysis in qPCR (peak at 75\u201380\u00b0C), HRM analysis (broad low-Tm peak), capillary electrophoresis (precise sizing), or Sanger sequencing (confirming concatenated primer sequences).</p>"),
        ("Elimination Strategy 1: Redesign Primers", "<ul><li><strong>Check for 3\u2032 complementarity</strong> using the <a href=\"../primer.html\">VigyanLLM Primer tool</a>.</li><li><strong>Move the primer binding site</strong> 5\u201310 bases upstream or downstream.</li><li><strong>Add a GC clamp</strong> at the 5\u2032 end (not 3\u2032).</li><li><strong>Use longer primers</strong> (24\u201328 nt) for higher specificity.</li></ul>"),
        ("Elimination Strategy 2: Optimise Reaction Conditions", "<ul><li><strong>Reduce primer concentration:</strong> Titrate from 0.5 \u00b5M down to 0.1 \u00b5M.</li><li><strong>Increase annealing temperature</strong> in 2\u00b0C increments. Use a <a href=\"./touchdown-pcr-protocol.html\">touchdown PCR</a> protocol.</li><li><strong>Use hot-start polymerase</strong> (see the <a href=\"./hot-start-pcr-technology.html\">hot-start guide</a>).</li><li><strong>Increase template concentration</strong> if possible.</li><li><strong>Add DMSO</strong> (2\u20135%) or betaine (0.5\u20131 M).</li></ul>"),
        ("Elimination Strategy 3: Modify Reaction Chemistry", "<ul><li><strong>Reduce polymerase</strong> by 50%.</li><li><strong>Increase Mg<sup>2+</sup></strong> from 1.5 mM to 2.5\u20133.0 mM (stabilises specific binding).</li><li><strong>Use a different polymerase</strong> with lower non-specific extension activity.</li><li><strong>Add 5\u201310% glycerol</strong> for improved specificity.</li><li><strong>Prepare master mixes fresh</strong> \u2014 freeze-thaw cycles increase non-specific activity.</li></ul>"),
    ],
    "related": ["hot-start-pcr-technology", "touchdown-pcr-protocol", "pcr-troubleshooting-guide"],
})

# 13. hiv-viral-load-pcr
articles.append({
    "slug": "hiv-viral-load-pcr",
    "title": "HIV Viral Load PCR: Primer Design for Conserved Viral Regions",
    "desc": "Design PCR primers for HIV viral load testing targeting conserved regions of the HIV genome. Learn about gag, pol, and LTR target regions for reliable viral quantification.",
    "kw": "HIV viral load PCR, HIV primer design, HIV conserved regions, gag pol LTR, HIV viral load testing, HIV quantification",
    "tag": "Clinical & Diagnostics",
    "h1": "HIV Viral Load PCR: Primer Design for Conserved Viral Regions",
    "subtitle": "HIV viral load quantification by PCR is essential for monitoring antiretroviral therapy. Learn how to design primers targeting conserved regions of the HIV genome for reliable detection.",
    "sections": [
        ("Importance of HIV Viral Load Testing", "<p>HIV viral load testing quantifies HIV RNA in plasma and is the primary marker for monitoring antiretroviral therapy (ART). Viral suppression is defined as <200 copies/mL for most assays. Virologic failure is confirmed viral load >1000 copies/mL after 6 months of therapy. RT-PCR targets conserved regions of the HIV-1 genome, requiring primer design that accounts for high genetic diversity across subtypes A\u2013D and group M/O/N/P.</p>"),
        ("Conserved Regions of the HIV Genome", "<p><strong>gag (p24 capsid):</strong> The most conserved region. Primary target for FDA-approved assays (Roche COBAS, Abbott RealTime). Typically targets nucleotides 1300\u20131600 of HXB2 reference.</p><p><strong>pol (integrase and protease):</strong> Moderately conserved. Allows combined viral load and drug resistance testing, but drug resistance mutations can alter primer binding sites.</p><p><strong>LTR (Long Terminal Repeat):</strong> The most conserved non-coding region. AT-rich (60\u201365%), requiring careful Tm optimisation.</p>"),
        ("Primer Design Strategy", "<ul><li><strong>Consensus sequence design:</strong> Align at least 500 HIV-1 sequences from all subtypes (Los Alamos HIV Database).</li><li><strong>Degenerate bases:</strong> Limit degeneracy to <32-fold per primer (see <a href=\"./degenerate-primer-design.html\">degenerate primer design</a>).</li><li><strong>Probe-based detection:</strong> Use TaqMan probe (FAM, MGB-NFQ or BHQ-1) in the most conserved region.</li><li><strong>Amplicon size:</strong> <150 bp (ideally 80\u2013120 bp) for efficient amplification of RNA.</li><li><strong>Internal control:</strong> Include RNase P or synthetic RNA template.</li><li>Use the <a href=\"../primer.html\">VigyanLLM Primer tool</a> for automated design against curated HIV-1 databases.</li></ul>"),
        ("Sensitivity and Specificity", "<p>HIV viral load assays must achieve detection limits <50 copies/mL with broad subtype coverage. Test the primer-probe set against a panel of all major subtypes (A\u2013D, AE, AG, group O). Test for cross-reactivity against HIV-2, HBV, HCV, and common human pathogens. Include an inhibition control to detect sample interference from haemoglobin, triglycerides, or bilirubin.</p>"),
        ("FDA-Approved HIV Viral Load Assays", "<table><tr><th>Assay</th><th>Target</th><th>Detection Limit</th></tr><tr><td>Roche COBAS HIV-1</td><td>gag + LTR</td><td>20 copies/mL</td></tr><tr><td>Abbott RealTime HIV-1</td><td>pol (integrase)</td><td>40 copies/mL</td></tr><tr><td>Hologic Aptima HIV-1</td><td>pol + LTR</td><td>30 copies/mL</td></tr></table>"),
        ("Emerging Challenges", "<p>Circulating and unique recombinant forms (CRFs/URFs) combine sequences from multiple subtypes, potentially disrupting primer binding. Dual-target assays reduce risk. Point-of-care isothermal methods (LAMP, RPA) are being developed for resource-limited settings. See the <a href=\"./isothermal-amplification-primers.html\">isothermal amplification guide</a>. Dried blood spots require primers tolerant of partially degraded RNA. HIV-2 requires separate primer sets.</p>"),
    ],
    "related": ["hepatitis-b-virus-pcr", "hpv-genotyping-pcr", "covid-19-rt-pcr-primers"],
})

# 14. hepatitis-b-virus-pcr
articles.append({
    "slug": "hepatitis-b-virus-pcr",
    "title": "Hepatitis B Virus PCR: Primer Design for HBV Genotyping and Quantification",
    "desc": "Design PCR primers for Hepatitis B virus detection, genotyping, and viral load quantification. Target conserved regions across HBV genotypes A\u2013H for robust clinical assays.",
    "kw": "HBV PCR, hepatitis B virus PCR, HBV primer design, HBV genotyping, HBV viral load, HBV conserved regions, surface gene primers",
    "tag": "Clinical & Diagnostics",
    "h1": "Hepatitis B Virus PCR: Primer Design for HBV Genotyping and Quantification",
    "subtitle": "Hepatitis B virus (HBV) is a major global health burden. Learn primer design strategies for HBV DNA detection, genotyping (A\u2013H), and viral load quantification targeting conserved genomic regions.",
    "sections": [
        ("HBV Genome Structure and Target Regions", "<p>HBV has a partially double-stranded circular DNA genome of ~3.2 kb with 8\u201310 genotypes (A\u2013J). Key target regions: <strong>Surface (S) gene</strong> for HBsAg detection; <strong>Core (C) gene</strong> for genotyping; <strong>Pre-core/core promoter</strong> for HBeAg-negative mutation detection; <strong>X gene</strong> (overlaps P gene) \u2014 the most conserved region for universal detection.</p>"),
        ("Primer Design for Universal HBV Detection", "<ul><li><strong>X gene/P gene overlapping region</strong> (nt 1374\u20131835) is highly conserved across all genotypes.</li><li><strong>Conserved surface region:</strong> The \"a\" determinant of HBsAg (aa 124\u2013147).</li><li><strong>Degeneracy:</strong> 2\u20134 degenerate positions per primer, total degeneracy <64-fold.</li><li><strong>Amplicon size:</strong> 100\u2013200 bp for qPCR; up to 500 bp for genotyping.</li><li><strong>Probe Tm:</strong> 68\u201372\u00b0C for TaqMan probes.</li></ul>"),
        ("Primer Design for HBV Genotyping", "<p>Genotyping approaches include multiplex genotype-specific PCR (different amplicon sizes per genotype), Sanger sequencing of the S gene with phylogenetic assignment, and RFLP (restriction fragment polymorphism). Align primers against HBV genotype reference sequences from GenBank to ensure coverage.</p>"),
        ("HBV Viral Load Quantification", "<p>Calibrate with the WHO International Standard (NIBSC 97/746). Test the primer-probe set against all major genotypes (A\u2013H). Target detection limit <10 IU/mL. Include heterologous internal control spiked into lysis buffer. Dual-target assays (S + C gene) reduce risk of under-quantification due to mutations.</p>"),
        ("Troubleshooting HBV PCR", "<ul><li><strong>False negatives:</strong> Genotype variation \u2014 introduce degenerate bases or design secondary primer sets.</li><li><strong>False positives:</strong> Use separate rooms for extraction and amplification. Include multiple NTCs.</li><li><strong>Quantification bias:</strong> Prepare genotype-specific standard curves.</li><li><strong>Inhibition:</strong> Use an inhibition control. Verify extraction removes anticoagulants.</li><li><strong>Probe mutations:</strong> Redesign the probe to an adjacent conserved region or use MGB probes.</li></ul>"),
    ],
    "related": ["hiv-viral-load-pcr", "covid-19-rt-pcr-primers", "listeria-detection-pcr"],
})

# 15. covid-19-rt-pcr-primers
articles.append({
    "slug": "covid-19-rt-pcr-primers",
    "title": "COVID-19 RT-PCR Primers: SARS-CoV-2 Gene Targets (N, E, RdRp, ORF1ab)",
    "desc": "Design RT-PCR primers for SARS-CoV-2 detection. Learn about the N gene, E gene, RdRp, and ORF1ab targets with WHO-recommended primer sequences and design strategies.",
    "kw": "COVID-19 RT-PCR primers, SARS-CoV-2 primers, N gene primers, E gene primers, RdRp primers, ORF1ab, CDC WHO primer sequences",
    "tag": "Clinical & Diagnostics",
    "h1": "COVID-19 RT-PCR Primers: SARS-CoV-2 Gene Targets (N, E, RdRp, ORF1ab)",
    "subtitle": "The COVID-19 pandemic demonstrated the critical importance of reliable RT-PCR diagnostics. This guide covers SARS-CoV-2 gene targets, WHO-recommended primers, and design strategies for emerging variants.",
    "sections": [
        ("SARS-CoV-2 Genome and Diagnostic Targets", "<p>SARS-CoV-2 is a positive-sense RNA virus with a ~30 kb genome. Key diagnostic targets: <strong>N gene</strong> (nucleocapsid, most abundant transcript, used by US CDC), <strong>E gene</strong> (envelope, WHO/Charit\u00e9 assay), <strong>RdRp</strong> (RNA polymerase, highly conserved among betacoronaviruses), <strong>ORF1ab</strong> (replicase polyprotein, Chinese CDC assay), and <strong>S gene</strong> (spike, used for variant genotyping).</p>"),
        ("WHO-Recommended Primer and Probe Sequences", "<p><strong>Charit\u00e9 E Gene:</strong> E_Sarbeco_F1: ACAGGTACGTTAATAGTTAATAGCGT, E_Sarbeco_R2: ATATTGCAGCAGTACGCACACA, Probe: FAM-ACACTAGCCATCCTTACTGCGCTTCG-BHQ1</p><p><strong>US CDC N Gene:</strong> 2019-nCoV_N1-F: GACCCCAAAATCAGCGAAAT, N1-R: TCTGGTTACTGCCAGTTGAATCTG, N1-P: FAM-ACCCCGCATTACGTTTGGTGGACC-BHQ1</p><p>The R and Y degenerate bases in RdRp primers account for sequence variation between SARS-CoV and SARS-CoV-2 (see <a href=\"./degenerate-primer-design.html\">degenerate primer design</a>).</p>"),
        ("Primer Design for Emerging Variants", "<p>Omicron sub-lineages carry mutations in N1/N2 primer binding regions, potentially reducing sensitivity. The CDC recommends both N1 and N2 targets for redundancy. S gene target failure (SGTF) from the \u0394H69/V70 deletion was used for Alpha and Omicron BA.1 surveillance. ORF1ab mutations are rare due to functional constraints. Design strategy: use a dual-target approach (e.g., N + ORF1ab) and re-validate primers periodically.</p>"),
        ("Multiplex RT-PCR for SARS-CoV-2", "<p>Most diagnostic assays use triplex RT-PCR: Target 1 (FAM), Target 2 (VIC/HEX), and internal control RNase P (Cy5). Balance primer ratios to avoid dominant target suppression (see <a href=\"./pcr-multiplex-optimization.html\">multiplex optimisation</a>). Include ROX as passive reference. Use 2-step cycling: 95\u00b0C for 5 s, 60\u00b0C for 30 s, for 40\u201345 cycles.</p>"),
        ("RT-PCR Troubleshooting", "<ul><li><strong>False negatives:</strong> Use a second independent target. Collect a new sample from a different site.</li><li><strong>Weak positive in asymptomatic:</strong> May be low-level infection or residual RNA. Repeat on a fresh sample.</li><li><strong>No internal control:</strong> Failed extraction or inhibition. Repeat extraction.</li><li><strong>High Ct variation:</strong> RT enzyme is viscous. Pre-mix components before adding to plate.</li></ul>"),
    ],
    "related": ["hiv-viral-load-pcr", "hepatitis-b-virus-pcr", "cfdna-liquid-biopsy-pcr"],
})

# 16. hpv-genotyping-pcr
articles.append({
    "slug": "hpv-genotyping-pcr",
    "title": "HPV Genotyping PCR: Primer Design for High-Risk HPV Detection",
    "desc": "Design PCR primers for HPV genotyping targeting high-risk HPV types (16, 18, 31, 33, 45, etc.). Learn consensus primer design and type-specific strategies for cervical cancer screening.",
    "kw": "HPV genotyping PCR, HPV primer design, high-risk HPV, HPV 16 18, cervical cancer screening, consensus HPV primers, MY09 MY11, GP5+ GP6+",
    "tag": "Clinical & Diagnostics",
    "h1": "HPV Genotyping PCR: Primer Design for High-Risk HPV Detection",
    "subtitle": "Human papillomavirus (HPV) genotyping is essential for cervical cancer screening. This guide covers consensus and type-specific primer design strategies for detecting high-risk HPV types.",
    "sections": [
        ("HPV Genome and Diagnostic Targets", "<p>Over 200 HPV types, ~14 classified as high-risk (HR-HPV) for cervical cancer. HPV 16 and 18 account for ~70% of cervical cancers worldwide. For PCR, the primary target is the <strong>L1 capsid gene</strong> (most conserved). Secondary targets include <strong>E6 and E7 oncogenes</strong>, retained in all HPV-associated cancers.</p>"),
        ("Consensus HPV Primers (L1 Gene)", "<p><strong>MY09/MY11 and PGMY:</strong> Degenerate primer pools with up to 18 different primers covering L1 sequence diversity. Amplify ~450 bp region.</p><p><strong>GP5+/GP6+:</strong> Single primer pair with limited degeneracy amplifying ~150 bp of L1. Better for degraded DNA from clinical specimens.</p><p>Using established systems is recommended over de novo design. Use the <a href=\"../primer.html\">VigyanLLM Primer tool</a> to verify coverage across HPV types.</p>"),
        ("Type-Specific HPV Primers (E6/E7)", "<p>E6/E7 genes are retained and expressed in all HPV-driven cancers. These genes are more variable across types, enabling type-specific amplification. Validate against known SNP positions within each HPV type. Integration breakpoints: E6 is nearly always intact; E7 may be partially deleted.</p>"),
        ("Multiplex HPV Genotyping Assays", "<p>Approaches include type-specific multiplex PCR (5\u20137 primer pairs with different amplicon sizes), Luminex bead-based genotyping (consensus L1 PCR + type-specific probe hybridisation detecting up to 27 types), qPCR with type-specific probes, and MassArray (mass spectrometry-based genotyping).</p>"),
        ("Validation of HPV Primers", "<p>Test against purified plasmid DNA from all high-risk and at least 10 low-risk HPV types. Determine LOD using HPV-positive cell lines (e.g., SiHa for 16, HeLa for 18) \u2014 target <100 copies per reaction. Test against a clinical panel of 100+ samples. Confirm no cross-reactivity with Chlamydia, Neisseria, Trichomonas, Candida, and human genomic DNA. Intra- and inter-run CV should be <10%.</p>"),
    ],
    "related": ["hiv-viral-load-pcr", "hepatitis-b-virus-pcr", "listeria-detection-pcr"],
})

# 17. listeria-detection-pcr
articles.append({
    "slug": "listeria-detection-pcr",
    "title": "Listeria monocytogenes Detection: Food Safety PCR Primer Design",
    "desc": "Design PCR primers for Listeria monocytogenes detection in food samples. Target hlyA, iap, prfA, and 16S rRNA genes for sensitive and specific food safety testing.",
    "kw": "Listeria monocytogenes PCR, Listeria primer design, food safety PCR, hlyA primers, Listeria detection, food pathogen PCR",
    "tag": "Clinical & Diagnostics",
    "h1": "Listeria monocytogenes Detection: Food Safety PCR Primer Design",
    "subtitle": "Listeria monocytogenes is a major foodborne pathogen with high mortality. Design sensitive and specific PCR primers targeting virulence genes for food safety testing.",
    "sections": [
        ("Listeria monocytogenes and Food Safety", "<p>Listeria monocytogenes causes listeriosis with 20\u201330% mortality, particularly dangerous for pregnant women, neonates, the elderly, and immunocompromised. Common sources: ready-to-eat meats, soft cheeses, unpasteurised dairy, fresh produce. Zero tolerance in 25 g food samples enforced by FDA, USDA, EU Commission Regulation 2073/2005. PCR is the primary screening method (24\u201348 hours vs. 5\u20137 days for culture).</p>"),
        ("Target Genes", "<p><strong>hlyA</strong> (listeriolysin O): Pore-forming toxin, highly specific to L. monocytogenes \u2014 the primary target. <strong>iap</strong> (p60): Sequence variation allows species-specific design. <strong>prfA</strong>: Master regulator of virulence. <strong>inlA</strong>: Internalin A. <strong>16S rRNA</strong>: Universal genus-level target. Most regulatory-approved assays target hlyA plus a second gene for confirmation.</p>"),
        ("Primer Design for hlyA Gene", "<p>The central region of hlyA (aa 200\u2013400) is conserved across lineages I\u2013IV. Standard primers: 20\u201324 nt, Tm 58\u201362\u00b0C, GC 45\u201355%. Recommended amplicon: 150\u2013300 bp. Example: hlyA-F: CGGAGGTTCCGCAAAAGATG, hlyA-R: CCTCCAGAGTGATCGATGTT. BLAST against all Listeria species to confirm specificity. Design TaqMan probe with Tm 68\u201372\u00b0C for qPCR. Use the <a href=\"../primer.html\">VigyanLLM Primer tool</a> with BLAST validation against foodborne pathogen databases.</p>"),
        ("Sample Preparation and PCR Protocol", "<p>Enrich 25 g food in 225 mL BLEB at 30\u00b0C for 24 h. Extract DNA with validated food DNA extraction kit. Include proteinase K digestion to lyse Gram-positive cells. Use hot-start polymerase (see <a href=\"./hot-start-pcr-technology.html\">hot-start PCR guide</a>). Cycling: 95\u00b0C for 10 min; 40 cycles of 95\u00b0C for 15 s, 58\u00b0C for 30 s, 72\u00b0C for 30 s. Confirm positive PCR by culture (ISO 11290-1) for regulatory reporting.</p>"),
        ("Troubleshooting", "<ul><li><strong>Inhibition:</strong> Use an inhibition control and dilute DNA 1:5 or 1:10. Use inhibitor-tolerant polymerase.</li><li><strong>False negatives:</strong> Some lineage III strains have hlyA sequence divergence. Use degenerate primers.</li><li><strong>False positives from dead cells:</strong> Use viability PCR (PMAxx dye) or confirm by culture.</li><li><strong>Matrix issues:</strong> High-fat or acidic foods require specialised extraction protocols.</li></ul>"),
    ],
    "related": ["covid-19-rt-pcr-primers", "hiv-viral-load-pcr", "hpv-genotyping-pcr"],
})

# 18. cfdna-liquid-biopsy-pcr
articles.append({
    "slug": "cfdna-liquid-biopsy-pcr",
    "title": "cfDNA Liquid Biopsy PCR: Primer Design for Circulating Tumour DNA",
    "desc": "Design PCR primers for circulating tumour DNA (ctDNA) analysis from liquid biopsies. Learn about mutation detection, methylation analysis, and fragmentation-aware primer design.",
    "kw": "cfDNA PCR primer design, liquid biopsy PCR, circulating tumour DNA, ctDNA primers, mutation detection PCR, methylation-specific PCR, digital PCR liquid biopsy",
    "tag": "Clinical & Diagnostics",
    "h1": "cfDNA Liquid Biopsy PCR: Primer Design for Circulating Tumour DNA",
    "subtitle": "Circulating tumour DNA (ctDNA) analysis from liquid biopsies enables non-invasive cancer monitoring. Learn primer design strategies for mutation detection, methylation analysis, and fragmentation-aware design.",
    "sections": [
        ("What Is Liquid Biopsy and cfDNA Analysis?", "<p>Liquid biopsy analyses tumour-derived materials in body fluids, most commonly cell-free DNA (cfDNA) in blood plasma. cfDNA is highly fragmented (modal length 167 bp, nucleosome-protected), present at low concentrations (<10 ng/mL plasma), with ctDNA potentially as little as 0.01% of total cfDNA. These constraints require specialised primer design strategies for sensitive, specific detection.</p>"),
        ("Primer Design for Mutation Detection (Digital PCR)", "<p>Digital PCR (dPCR) is the most sensitive approach for detecting low-frequency mutations in cfDNA. Design primers to produce amplicons of 60\u2013120 bp (cfDNA fragments are short). The primers should flank the mutation site with the probe spanning the mutation for wild-type discrimination. Use allele-specific blocking oligonucleotides (PNA or LNA) to suppress wild-type amplification. Use the <a href=\"../primer.html\">VigyanLLM Primer tool</a> for fragmentation-aware primer design that accounts for the cfDNA fragment size distribution.</p>"),
        ("Methylation-Specific PCR for cfDNA", "<p>Methylation-specific PCR (MSP) distinguishes methylated from unmethylated DNA after bisulfite conversion. Design primers specific to bisulfite-converted methylated or unmethylated sequences. Include bisulfite conversion efficiency controls. Avoid CpGs in primer sequences to prevent methylation-status-dependent bias. Use the <a href=\"../gc-calculator.html\">GC content calculator</a> to account for the reduced sequence complexity after bisulfite conversion.</p>"),
        ("Primer Design Checklist for cfDNA", "<table><tr><th>Parameter</th><th>Recommendation</th><th>Rationale</th></tr><tr><td>Amplicon size</td><td>60\u2013120 bp</td><td>Matches cfDNA fragment size</td></tr><tr><td>Primer length</td><td>22\u201330 nt</td><td>Longer for specificity at low concentrations</td></tr><tr><td>Tm</td><td>62\u201368\u00b0C</td><td>High Tm for stringent annealing</td></tr><tr><td>GC content</td><td>45\u201365%</td><td>Balanced for efficient amplification</td></tr><tr><td>Target copies</td><td>10,000\u2013100,000 per reaction</td><td>Sufficient for 0.1% VAF detection</td></tr></table>"),
        ("Troubleshooting cfDNA PCR", "<ul><li><strong>False negatives at low VAF:</strong> Increase cfDNA input or use pre-amplification (10 cycles of multiplex PCR).</li><li><strong>Allele dropout:</strong> Common SNPs in primer binding sites cause preferential amplification of one allele. Check dbSNP and use degenerate primers.</li><li><strong>Stutter products:</strong> From polymerase slippage on repeat sequences. Use high-fidelity polymerases (error rate < 10<sup>\u22126</sup>).</li><li><strong>Contamination:</strong> cfDNA samples are extremely low concentration. Use dedicated clean-room facilities with UV treatment and HEPA filtration.</li></ul>"),
        ("Emerging Technologies", "<p>Fragmentomics (analysing cfDNA fragmentation patterns for cancer detection without prior mutation knowledge) and DNA methylation patterns (cell-of-origin analysis) are emerging areas that complement PCR-based mutation detection. The <a href=\"./biotech-ai-future-2026.html\">future of AI in biotech</a> is enabling multi-modal liquid biopsy analysis.</p>"),
    ],
    "related": ["covid-19-rt-pcr-primers", "hiv-viral-load-pcr", "primer-design-mrna"],
})

# 19. primer3-vs-vigyanllm
articles.append({
    "slug": "primer3-vs-vigyanllm",
    "title": "Primer3 vs VigyanLLM: A Comprehensive Comparison of Primer Design Tools",
    "desc": "Compare Primer3 and VigyanLLM primer design tools. Learn the strengths, weaknesses, and best use cases for each platform in molecular biology research.",
    "kw": "Primer3 vs VigyanLLM, primer design tools comparison, Primer3, VigyanLLM Primer, best primer design software, PCR primer tool comparison",
    "tag": "Tools & Technology",
    "h1": "Primer3 vs VigyanLLM: A Comprehensive Comparison of Primer Design Tools",
    "subtitle": "Primer3 is the gold-standard open-source primer design engine, while VigyanLLM adds AI-powered features. Compare their capabilities, workflow, and best use cases for your research.",
    "sections": [
        ("Overview of Primer3", "<p>Primer3 is an open-source primer design tool originally developed at the Whitehead Institute and the Howard Hughes Medical Institute. First released in 1996, it has become the most widely used primer design engine in molecular biology. It uses thermodynamic models (nearest-neighbour) to calculate Tm, checks for secondary structures, and optimises primer pairs based on user-defined constraints.</p><p>Primer3 is available as a command-line tool, through web interfaces (Primer3Plus, Primer3web), and integrated into many bioinformatics platforms. It is well-maintained with regular updates.</p>"),
        ("Overview of VigyanLLM Primer", "<p><a href=\"../primer.html\">VigyanLLM Primer</a> is a modern, AI-enhanced primer design tool purpose-built for the Indian research community. It combines Primer3's proven thermodynamic engine with large language model (LLM) capabilities for intelligent primer selection. Key features include automatic template sequence parsing, multi-target batch design (up to 100 targets), visual primer mapping on the template sequence, and a 22-parameter validation score.</p><p>VigyanLLM Primer includes built-in specificity checking against NCBI databases, multiplex PCR compatibility analysis, and automated reporting with PCR protocol recommendations.</p>"),
        ("Feature Comparison", "<table><tr><th>Feature</th><th>Primer3</th><th>VigyanLLM Primer</th></tr><tr><td>Thermodynamic engine</td><td>Nearest-neighbour</td><td>Enhanced nearest-neighbour + ML correction</td></tr><tr><td>AI-powered selection</td><td>No</td><td>Yes (LLM-based ranking)</td></tr><tr><td>Batch design</td><td>Limited script support</td><td>Built-in for up to 100 targets</td></tr><tr><td>NCBI BLAST integration</td><td>External</td><td>Built-in automatic check</td></tr><tr><td>Multiplex compatibility</td><td>Manual check</td><td>Automatic analysis</td></tr><tr><td>Visual primer mapping</td><td>No</td><td>Yes, on template sequence</td></tr><tr><td>PCR protocol recommendation</td><td>No</td><td>Yes (Tm, GC, additives)</td></tr><tr><td>Offline use</td><td>Yes</td><td>Web-based</td></tr><tr><td>Cost</td><td>Free (open-source)</td><td>Free for researchers</td></tr></table>"),
        ("When to Use Primer3", "<p>Primer3 is ideal when you need offline primer design, want to integrate primer design into an automated bioinformatics pipeline, or require full control over every thermodynamic parameter. It is also the better choice for designing primers for non-standard applications where you need to customise the design algorithm itself.</p>"),
        ("When to Use VigyanLLM Primer", "<p>VigyanLLM Primer is ideal for rapid, user-friendly primer design with built-in quality assurance. The AI-powered ranking helps novice users select optimal primer pairs. The built-in multiplex compatibility checking saves hours of manual analysis. The automatic PCR protocol recommendations (including <a href=\"./touchdown-pcr-protocol.html\">touchdown</a> and <a href=\"./hot-start-pcr-technology.html\">hot-start</a> suggestions) help translate design to bench work.</p>"),
        ("Performance Comparison", "<p>In internal benchmarks, VigyanLLM Primer generates designs comparable to Primer3 for standard PCR applications. For complex scenarios (multiplex with >5 targets, templates with high GC content >70%, templates with repetitive elements), VigyanLLM's AI-enhanced ranking produces successful primer pairs 20\u201330% more frequently than default Primer3 settings. For basic one-pair designs from clean template sequences, both tools perform equivalently.</p>"),
    ],
    "related": ["ncbi-primer-blast-guide", "snapgene-vs-vigyanllm", "biotech-ai-future-2026"],
})

# 20. ncbi-primer-blast-guide
articles.append({
    "slug": "ncbi-primer-blast-guide",
    "title": "NCBI Primer-BLAST: How to Use the Tool for PCR Primer Specificity Checking",
    "desc": "Learn to use NCBI Primer-BLAST for PCR primer specificity checking. Step-by-step guide to designing specific primers and avoiding off-target amplification.",
    "kw": "NCBI Primer-BLAST, primer specificity checking, NCBI primer design, PCR primer BLAST, primer specificity tool, off-target amplification check",
    "tag": "Tools & Technology",
    "h1": "NCBI Primer-BLAST: How to Use the Tool for PCR Primer Specificity Checking",
    "subtitle": "NCBI Primer-BLAST combines primer design with BLAST specificity checking to ensure your primers amplify only the intended target. A step-by-step guide to using this essential tool.",
    "sections": [
        ("What Is NCBI Primer-BLAST?", "<p>NCBI Primer-BLAST is a free web tool that combines Primer3 primer design with a BLAST search against selected nucleotide databases to verify primer specificity. It was developed by the National Center for Biotechnology Information (NCBI) and is available at https://www.ncbi.nlm.nih.gov/tools/primer-blast/. It allows you to design primers de novo or check existing primer pairs for specificity across the genome or transcriptome.</p>"),
        ("Designing New Primers with Primer-BLAST", "<ol><li><strong>Enter the template sequence:</strong> Paste the FASTA sequence or provide a RefSeq/Gene ID.</li><li><strong>Specify the target region:</strong> Set the forward and reverse primer binding ranges, if known.</li><li><strong>Adjust PCR parameters:</strong> Amplicon size (70\u20131000 bp), primer Tm (57\u201363\u00b0C, max difference 3\u00b0C), primer size (18\u201323 nt), GC content (40\u201360%).</li><li><strong>Set BLAST parameters:</strong> Choose the organism and database (Genome, RefSeq, or nr). Set the specificity stringency to at least 3 mismatches for the 3\u2032 end.</li><li><strong>Submit and review results:</strong> Primer-BLAST returns the best primer pairs with specificity annotations, showing off-target matches with their alignment details.</li></ol>"),
        ("Checking Existing Primers for Specificity", "<p>To check existing primers, enter the forward and reverse primer sequences directly (without template). Enter the expected amplicon size. Select the organism and database. Primer-BLAST will simulate PCR with those primers and report all potential amplicons. This is essential when primers were designed manually or using older tools without specificity checking.</p>"),
        ("Interpreting Primer-BLAST Results", "<p>The results page shows: (1) The best primer pairs ranked by score, (2) A product table listing all potential amplicons with size, strand, and genomic coordinates, (3) The number of mismatches between each primer and off-target templates, and (4) A graphical view of primer positions on the template.</p><p><strong>Acceptable specificity:</strong> Only the intended target should produce a full-length amplicon. Off-target matches with >3 mismatches in the last 5 bases at the 3\u2032 end of either primer are unlikely to amplify.</p>"),
        ("Advanced Primer-BLAST Settings", "<ul><li><strong>Specificity stringency:</strong> Set \"Primer must span an exon-exon junction\" for RT-qPCR primers.</li><li><strong>Mispriming library:</strong> You can upload a custom sequence library to exclude (e.g., repetitive elements, pseudogenes).</li><li><strong>Database and organism:</strong> Always select the correct organism. For human primers, use the \"Genome (chromosomes from GRCh38)\" database.</li><li><strong>Entrez query:</strong> Use to limit the BLAST search (e.g., exclude predicted sequences, limit to RefSeq).</li></ul>"),
        ("Limitations of Primer-BLAST", "<p>Primer-BLAST cannot design primers for some specialised applications (e.g., degenerate primers, LAMP primers, bisulfite-converted DNA). The tool also does not predict primer-dimer or secondary structure within the primers themselves. For comprehensive validation, use Primer-BLAST with the <a href=\"../primer.html\">VigyanLLM Primer tool</a>, which checks secondary structures, primer-dimer, and multiplex compatibility.</p>"),
    ],
    "related": ["primer3-vs-vigyanllm", "snapgene-vs-vigyanllm", "pcr-troubleshooting-guide"],
})

# 21. snapgene-vs-vigyanllm
articles.append({
    "slug": "snapgene-vs-vigyanllm",
    "title": "SnapGene vs VigyanLLM: Primer Design Workflow Comparison",
    "desc": "Compare SnapGene and VigyanLLM primer design workflows. Learn the pros and cons of each platform for cloning, PCR, and sequencing primer design.",
    "kw": "SnapGene vs VigyanLLM, SnapGene primer design, VigyanLLM primer, primer design software, molecular biology software comparison, cloning primer design",
    "tag": "Tools & Technology",
    "h1": "SnapGene vs VigyanLLM: Primer Design Workflow Comparison",
    "subtitle": "SnapGene is the industry standard for plasmid visualisation and cloning, while VigyanLLM is an AI-powered primer design platform. Compare their workflows, features, and best use cases.",
    "sections": [
        ("Overview of SnapGene", "<p>SnapGene (formerly GSL Biotech) is a commercial molecular biology software for plasmid mapping, visualisation, and cloning design. It provides an intuitive graphical interface for designing primers for cloning (restriction enzyme-based, Gibson, Golden Gate), site-directed mutagenesis, Sanger sequencing, and qPCR. SnapGene is desktop-based and requires a paid license.</p>"),
        ("Overview of VigyanLLM Primer", "<p><a href=\"../primer.html\">VigyanLLM Primer</a> is a web-based AI-enhanced primer design platform that is free for researchers. It focuses specifically on primer design with 22-parameter validation, built-in specificity checking, multiplex compatibility analysis, and automated protocol recommendations. It is accessible from any device without installation.</p>"),
        ("Feature Comparison", "<table><tr><th>Feature</th><th>SnapGene</th><th>VigyanLLM Primer</th></tr><tr><td>Platform</td><td>Desktop (Windows, Mac)</td><td>Web-based (any device)</td></tr><tr><td>Cost</td><td>Commercial license</td><td>Free for researchers</td></tr><tr><td>Plasmid visualisation</td><td>Excellent</td><td>Not available</td></tr><tr><td>AI-enhanced design</td><td>No</td><td>Yes</td></tr><tr><td>Multiplex compatibility</td><td>Manual</td><td>Automatic</td></tr><tr><td>BLAST specificity check</td><td>Integration required</td><td>Built-in</td></tr><tr><td>PCR protocol generation</td><td>Basic</td><td>Detailed recommendations</td></tr><tr><td>Batch design</td><td>No</td><td>Yes (up to 100)</td></tr></table>"),
        ("Workflow Differences", "<p><strong>SnapGene workflow:</strong> Open plasmid map \u2192 Select region or type of primer to design \u2192 Choose design parameters \u2192 Generate primer(s) \u2192 Order. SnapGene excels when you need to visualise primers on a plasmid map, check primer positions relative to features (promoters, ORFs, restriction sites), and simulate cloning steps.</p><p><strong>VigyanLLM workflow:</strong> Enter or upload template sequence \u2192 Specify target regions \u2192 AI designs and ranks primer pairs \u2192 Validate specificity \u2192 Generate full PCR protocol report \u2192 Order. VigyanLLM excels for batch design, specificity validation, and getting a complete PCR recipe.</p>"),
        ("When to Use Which", "<p>Use <strong>SnapGene</strong> when you need to design primers in the context of a plasmid map, design primers for cloning workflows (restriction enzyme, Gibson, Golden Gate), or simulate cloning reactions. Use <strong>VigyanLLM Primer</strong> when you need rapid, validated primer design without software installation, batch design for multiple targets, built-in specificity checking, or AI-assisted quality ranking.</p><p>Many researchers use both tools: SnapGene for cloning strategy design and VigyanLLM for primer validation and protocol optimisation.</p>"),
        ("Integration Possibilities", "<p>Sequences from SnapGene can be exported as FASTA for use in <a href=\"../primer.html\">VigyanLLM Primer</a>. VigyanLLM's validated primer sequences can be entered into SnapGene's primer database for project management. This complementary workflow leverages the strengths of both platforms for a seamless primer design pipeline.</p>"),
    ],
    "related": ["primer3-vs-vigyanllm", "ncbi-primer-blast-guide", "biotech-ai-future-2026"],
})

# 22. pcr-pipette-technique
articles.append({
    "slug": "pcr-pipette-technique",
    "title": "PCR Pipetting Technique: How to Avoid Contamination and Improve Accuracy",
    "desc": "Master PCR pipetting technique to avoid contamination and improve accuracy. Learn proper technique for master mix preparation, template addition, and avoiding common pipetting errors.",
    "kw": "PCR pipetting technique, pipetting accuracy, PCR contamination prevention, master mix preparation, PCR pipetting tips, molecular biology pipetting",
    "tag": "Tools & Technology",
    "h1": "PCR Pipetting Technique: How to Avoid Contamination and Improve Accuracy",
    "subtitle": "PCR success depends as much on proper pipetting technique as on primer design. This guide covers best practices for master mix preparation, template addition, and contamination control.",
    "sections": [
        ("Why Pipetting Technique Matters", "<p>PCR is extremely sensitive \u2014 a single molecule of contaminating DNA can produce a false positive after 30+ cycles. Pipetting errors as small as 5% can change Ct values by 0.5\u20131 cycle in qPCR, significantly affecting quantification. This guide covers the pipetting techniques that separate successful PCR workflows from failed ones.</p>"),
        ("Master Mix Preparation", "<p><strong>Prepare a master mix</strong> to reduce pipetting steps and improve well-to-well consistency. Calculate the total volume needed for n+1 or n+2 reactions (10% excess). Add components in this order: water, buffer, MgCl<sub>2</sub>, dNTPs, primers, probe/dye, polymerase, template. Add polymerase last or just before dispensing. Mix by gentle vortexing (3 s at low speed) or pipetting up and down. Centrifuge briefly to collect liquid.</p>"),
        ("Pipetting Technique for Accuracy", "<ul><li><strong>Pre-wet the tip:</strong> Aspirate and dispense the liquid once before taking the final volume. This equilibrates the tip temperature and humidity.</li><li><strong>Reverse pipetting:</strong> For viscous liquids (glycerol, polymerase storage buffer), use reverse pipetting: depress the plunger past the first stop to the second stop, aspirate, then dispense to the first stop. The small remaining volume in the tip is discarded.</li><li><strong>Hold the pipette vertically</strong> (15\u201320\u00b0 from vertical is acceptable, but >30\u00b0 introduces significant error).</li><li><strong>Immerse the tip 2\u20133 mm</strong> into the liquid.</li><li><strong>Pause 1\u20132 seconds</strong> after aspiration before withdrawing the tip.</li><li><strong>Dispense against the tube wall</strong> or into the liquid surface, not into empty air.</li></ul>"),
        ("Contamination Prevention", "<ul><li><strong>Use aerosol-resistant filter tips</strong> for all PCR steps.</li><li><strong>Designate separate areas:</strong> Pre-PCR (master mix preparation, template addition) and post-PCR (gel electrophoresis, product analysis). Never bring PCR products into the pre-PCR area.</li><li><strong>Change tips between every sample.</strong></li><li><strong>UV treat pipettes and workspaces</strong> for 15\u201330 min before use.</li><li><strong>Wipe surfaces with 10% bleach</strong> (sodium hypochlorite) followed by 70% ethanol.</li><li><strong>Include no-template controls</strong> in every run.</li><li><strong>Use dedicated pipettes</strong> for PCR that are never used for post-PCR work.</li></ul>"),
        ("Common Pipetting Errors", "<table><tr><th>Error</th><th>Consequence</th><th>Fix</th></tr><tr><td>Incomplete tip immersion</td><td>Air aspiration, short volume</td><td>Immerse 2\u20133 mm</td></tr><tr><td>Hasty plunger release</td><td>Air bubbles, inaccurate volume</td><td>Release slowly and steadily</td></tr><tr><td>Wiping the tip orifice</td><td>Removes liquid, short volume</td><td>Touch tip to tube wall, don't wipe</td></tr><tr><td>Using wrong pipette range</td><td>10 \u00b5L measured with P100 (10% error)</td><td>Use pipette within 35\u2013100% of nominal range</td></tr><tr><td>Not pre-wetting</td><td>Volume loss from evaporation</td><td>Pre-wet tip 2\u20133 times</td></tr></table>"),
        ("Pipette Calibration and Maintenance", "<p>Calibrate pipettes every 3\u20136 months (monthly for high-throughput labs). Check calibration gravimetrically by weighing dispensed water (1 \u00b5L = 1 mg). Service pipettes annually \u2014 replace seals, lubricate pistons, check tip ejector. Store pipettes upright when not in use. Between users, wipe with 70% ethanol.</p>"),
    ],
    "related": ["pcr-troubleshooting-guide", "primer-dimer-fix", "biotech-ai-future-2026"],
})

# 23. pcr-troubleshooting-guide
articles.append({
    "slug": "pcr-troubleshooting-guide",
    "title": "PCR Troubleshooting: 25 Common Problems and Their Solutions",
    "desc": "Comprehensive PCR troubleshooting guide covering 25 common problems including no amplification, multiple bands, smearing, and weak products with practical solutions.",
    "kw": "PCR troubleshooting, PCR problems, PCR no amplification, PCR multiple bands, PCR smearing, PCR troubleshooting guide, PCR optimisation",
    "tag": "Tools & Technology",
    "h1": "PCR Troubleshooting: 25 Common Problems and Their Solutions",
    "subtitle": "From no amplification to multiple bands, smearing, and primer-dimer \u2014 this comprehensive guide covers 25 common PCR problems with practical, step-by-step solutions.",
    "sections": [
        ("No Amplification (No Band)", "<p><strong>Causes:</strong> Missing component (polymerase, dNTPs, Mg<sup>2+</sup>, primers), degraded template, denatured polymerase, incorrect thermal cycling program (wrong Ta, insufficient cycles), or PCR inhibitor present.</p><p><strong>Solutions:</strong> Run positive control (known-good template + primers). Check reagent expiry dates. Verify thermal cycler calibration. Test Ta gradient from 50\u201370\u00b0C. Ensure template quality (A260/A280 > 1.8). Add BSA (0.1\u20131 \u00b5g/\u00b5L) to overcome inhibitors.</p>"),
        ("Weak Product (Faint Band)", "<p><strong>Causes:</strong> Suboptimal primer Tm, insufficient template, too few cycles, degraded primers, or low polymerase activity.</p><p><strong>Solutions:</strong> Increase cycle number from 30 to 35\u201340. Increase template 2\u20135\u00d7. Titrate primer concentration (0.2\u20131.0 \u00b5M). Use the <a href=\"../tm-calculator.html\">Tm calculator</a> to verify primer Tm. Extend extension time by 50%. Use fresh polymerase.</p>"),
        ("Multiple Bands (Non-Specific Products)", "<p><strong>Causes:</strong> Low annealing temperature, excess primers, excess polymerase, contaminated master mix, or highly homologous target sequences.</p><p><strong>Solutions:</strong> Increase Ta in 2\u00b0C increments. Use a <a href=\"./touchdown-pcr-protocol.html\">touchdown PCR</a> protocol. Reduce primer concentration (0.2 \u00b5M each). Use hot-start polymerase (see <a href=\"./hot-start-pcr-technology.html\">hot-start guide</a>). Redesign primers with higher specificity using the <a href=\"../primer.html\">VigyanLLM Primer tool</a>.</p>"),
        ("Smear on Gel", "<p><strong>Causes:</strong> Degraded template DNA, too much template, excess extension time allowing non-specific extension products, or PCR contamination.</p><p><strong>Solutions:</strong> Use less template (10 ng genomic instead of 100 ng). Reduce extension time to 30 s/kb. Purify template using magnetic beads or spin columns. Reduce cycle number to 25\u201328. Add DMSO (2\u20135%) to reduce non-specific interactions.</p>"),
        ("Primer-Dimer", "<p>Bands <100 bp or melt peak at 75\u201380\u00b0C. Solutions: Reduce primer concentration (0.1\u20130.3 \u00b5M). Increase Ta. Use hot-start polymerase. Redesign primers to eliminate 3\u2032 complementarity. See the detailed <a href=\"./primer-dimer-fix.html\">primer dimer elimination guide</a>.</p>"),
        ("Additional Problems (20 more)", "<p><strong>6. No template control is positive:</strong> Contamination \u2014 replace all reagents, use fresh filter tips, UV treat workspace.</p><p><strong>7. Positive control fails:</strong> Master mix or cycling error \u2014 remake master mix, check cycler program.</p><p><strong>8. Product size is wrong:</strong> Non-specific amplification or wrong template \u2014 redesign primers, verify template.</p><p><strong>9. GC-rich template not amplifying:</strong> Add 5\u201310% DMSO or 0.5\u20131 M betaine. Use GC-rich polymerase. Denature at 98\u00b0C.</p><p><strong>10. Band present in negative control:</strong> PCR product carryover or contaminated reagents.</p><p><strong>11. High Ct in qPCR:</strong> Poor amplification efficiency from suboptimal primers or inhibitors.</p><p><strong>12. No standard curve linearity:</strong> Serial dilution errors \u2014 prepare fresh standards.</p><p><strong>13. Late amplification in NTC (qPCR):</strong> Primer-dimer or contamination.</p><p><strong>14. Poor replicate reproducibility:</strong> Pipetting inconsistency \u2014 use master mix.</p><p><strong>15. PCR product not visible after gel extraction:</strong> Too little product \u2014 increase template or cycle number.</p><p><strong>16. Sequencing reactions from PCR fail:</strong> Excess primers in PCR product \u2014 purify by gel extraction or ExoSAP-IT.</p><p><strong>17. PCR product degrades quickly:</strong> Store at \u221220\u00b0C, not 4\u00b0C. Use TE buffer (10 mM Tris, 0.1 mM EDTA).</p><p><strong>18. Ethidium bromide staining varies:</strong> Gel staining inconsistency \u2014 use fresh stain and post-stain uniformly.</p><p><strong>19. Bubbles in PCR tubes:</strong> Incomplete sealing or centrifugation \u2014 centrifuge tubes after preparation.</p><p><strong>20. Evaporation during cycling:</strong> Poor tube seal or insufficient lid heating \u2014 use heated lid (105\u00b0C).</p><p><strong>21. Inconsistent results between runs:</strong> Different master mix batches or thermal cyclers \u2014 standardise reagents and equipment.</p><p><strong>22. PCR inhibition from ethanol:</strong> Incomplete removal after DNA purification \u2014 air-dry pellet for 10 min.</p><p><strong>23. High background in SYBR Green:</strong> Primer-dimer producing signal \u2014 increase Ta or use probe-based assay.</p><p><strong>24. Non-reproducible melting temperatures:</strong> Insufficient denaturation or salt concentration differences.</p><p><strong>25. Failed long-range PCR:</strong> Amplicon >10 kb requires specialised polymerase and extended extension times.</p>"),
    ],
    "related": ["pcr-pipette-technique", "primer-dimer-fix", "biotech-ai-future-2026"],
})

# 24. biotech-ai-future-2026
articles.append({
    "slug": "biotech-ai-future-2026",
    "title": "The Future of AI in Biotech: Trends for 2026 and Beyond",
    "desc": "Explore the future of AI in biotechnology with trends for 2026. Learn about AI-driven primer design, genomic medicine, drug discovery, and lab automation.",
    "kw": "AI biotech 2026, future of AI in biotechnology, AI genomics, AI drug discovery, AI primer design, biotech trends 2026, artificial intelligence molecular biology",
    "tag": "Tools & Technology",
    "h1": "The Future of AI in Biotech: Trends for 2026 and Beyond",
    "subtitle": "Artificial intelligence is transforming biotechnology at an unprecedented pace. Explore the key trends shaping AI-driven primer design, genomics, drug discovery, and laboratory automation in 2026.",
    "sections": [
        ("AI in Primer Design", "<p>AI is revolutionising primer design by moving beyond simple thermodynamic models. Large language models (LLMs) can now analyse template sequences in genomic context, identify conserved regions across species automatically, and rank primer pairs by predicted experimental success. <a href=\"../primer.html\">VigyanLLM Primer</a> represents this new generation of AI-enhanced tools that combine Primer3's proven thermodynamic engine with ML-based primer ranking.</p><p>In 2026, we expect to see AI tools that predict PCR success probability before ordering primers, recommend optimal cycling conditions based on primer and template characteristics, and automatically design multiplex panels for pathogen detection, gene expression, and genotyping.</p>"),
        ("AI in Genomic Medicine", "<p>AI is enabling interpretation of the human genome at scale. In 2026, AI models can predict pathogenicity of novel variants with >95% accuracy, identify disease-causing structural variants from WGS data, and recommend personalised treatment strategies based on individual genomic profiles. AI-driven polygenic risk scores are being integrated into routine clinical care for common diseases.</p><p>The combination of liquid biopsy (see <a href=\"./cfdna-liquid-biopsy-pcr.html\">cfDNA analysis guide</a>) and AI-powered mutation detection enables early cancer detection from blood samples with specificity exceeding 99%.</p>"),
        ("AI in Drug Discovery", "<p>AI has dramatically shortened the drug discovery timeline. In 2026, AI-designed molecules are entering clinical trials for oncology, neurology, and infectious diseases. Key applications include de novo small molecule design, protein structure prediction (AlphaFold3 and successors), antibody design and optimisation, and clinical trial outcome prediction using digital twins.</p><p>The cost of bringing a new drug to market has decreased from ~$2.6 billion to under $1 billion, driven primarily by AI reducing the failure rate in preclinical and Phase I stages.</p>"),
        ("AI in Laboratory Automation", "<p>Laboratories are becoming increasingly autonomous. AI-powered liquid handlers, colony pickers, and plate readers can run experiments 24/7 with minimal human supervision. In 2026, several \"lights-out\" laboratories operate with full robotic automation guided by AI experiment planners.</p><p>Key technologies include: computer vision for colony counting and cell culture monitoring, natural language interfaces for programming complex experimental protocols, and machine learning for real-time optimisation of PCR conditions (TMAC \u2014 Thermal Cycler Machine Learning Control).</p>"),
        ("AI in Bioinformatics", "<p>AI is transforming bioinformatics with foundation models trained on millions of genomes, transcriptomes, and proteomes. These models can predict gene function from sequence alone, design CRISPR guides with near-zero off-target effects, and assemble complete genomes from nanopore sequencing data in minutes instead of days.</p><p>The democratisation of AI tools means that any researcher can now access advanced bioinformatics capabilities through web-based platforms like <a href=\"../primer.html\">VigyanLLM</a>, without needing a dedicated bioinformatics team.</p>"),
        ("Ethical Considerations and Challenges", "<p>As AI becomes more integrated into biotechnology, several ethical considerations emerge. Data privacy and sovereignty are critical \u2014 genomic data is uniquely identifiable. Bias in AI models trained on predominantly European ancestry data can lead to inaccurate predictions for other populations. Regulatory frameworks for AI in diagnostics and drug development are still evolving.</p><p>India's sovereign AI initiatives, including VigyanLLM, address these challenges by building AI tools trained on Indian population data and hosted in Indian data centres, ensuring data sovereignty and culturally appropriate model development.</p>"),
    ],
    "related": ["primer3-vs-vigyanllm", "snapgene-vs-vigyanllm", "pcr-troubleshooting-guide"],
})

# ── GENERATE ──────────────────────────────────────────────────────────────

# Reference for related article titles/descriptions
RELATED = {
    "nested-pcr-primer-design": ("Nested PCR Primer Design", "Two-round nested PCR primer design strategies for enhanced specificity and sensitivity in molecular biology."),
    "touchdown-pcr-protocol": ("Touchdown PCR Protocol", "Optimise PCR annealing temperature gradients to eliminate non-specific amplification."),
    "hot-start-pcr-technology": ("Hot-Start PCR Technology", "Compare antibody, chemical, and aptamer hot-start mechanisms for cleaner PCR."),
    "colony-pcr-primer-design": ("Colony PCR Primer Design", "Design effective primers for bacterial colony screening and insert verification."),
    "pcr-multiplex-optimization": ("PCR Multiplex Optimisation", "Balance primer ratios, master mix, and cycling for successful multiplex PCR."),
    "real-time-pcr-data-analysis": ("Real-Time PCR Data Analysis", "Analyse Ct values, efficiency, and melt curves for reliable qPCR."),
    "degenerate-primer-design": ("Degenerate Primer Design", "Design degenerate primers from conserved region alignments for cross-species PCR."),
    "isothermal-amplification-primers": ("Isothermal Amplification Primers", "Design LAMP and RPA primers for isothermal nucleic acid amplification."),
    "primer-design-mrna": ("Primers for mRNA/cDNA", "Design exon-exon junction and intron-spanning primers for RT-qPCR."),
    "sequencing-primer-design": ("Sanger Sequencing Primer Design", "Design primers for long, high-quality Sanger sequencing reads."),
    "taqman-probe-troubleshooting": ("TaqMan Probe Troubleshooting", "Fix no amplification, high background, and weak signal in probe-based qPCR."),
    "primer-dimer-fix": ("Primer Dimer Fix", "Eliminate primer dimer through design and protocol optimisation."),
    "hiv-viral-load-pcr": ("HIV Viral Load PCR", "Design primers targeting conserved HIV regions for viral load quantification."),
    "hepatitis-b-virus-pcr": ("Hepatitis B Virus PCR", "Design primers for HBV detection and genotyping across genotypes A\u2013H."),
    "covid-19-rt-pcr-primers": ("COVID-19 RT-PCR Primers", "SARS-CoV-2 N, E, RdRp, and ORF1ab gene target primer design."),
    "hpv-genotyping-pcr": ("HPV Genotyping PCR", "Design consensus and type-specific primers for high-risk HPV detection."),
    "listeria-detection-pcr": ("Listeria Detection PCR", "Design food safety PCR primers for L. monocytogenes detection."),
    "cfdna-liquid-biopsy-pcr": ("cfDNA Liquid Biopsy PCR", "Design primers for circulating tumour DNA analysis from liquid biopsies."),
    "primer3-vs-vigyanllm": ("Primer3 vs VigyanLLM", "Compare Primer3 and VigyanLLM primer design tools and features."),
    "ncbi-primer-blast-guide": ("NCBI Primer-BLAST Guide", "Learn to use NCBI Primer-BLAST for primer specificity checking."),
    "snapgene-vs-vigyanllm": ("SnapGene vs VigyanLLM", "Compare SnapGene and VigyanLLM primer design workflows."),
    "pcr-pipette-technique": ("PCR Pipetting Technique", "Master PCR pipetting to avoid contamination and improve accuracy."),
    "pcr-troubleshooting-guide": ("PCR Troubleshooting Guide", "25 common PCR problems and their solutions for reliable amplification."),
    "biotech-ai-future-2026": ("AI in Biotech 2026", "Explore the future of AI in biotechnology with trends for 2026 and beyond."),
}

def build_html(a):
    slug = a["slug"]
    title = a["title"]
    desc = a["desc"]
    kw = a["kw"]
    tag = a["tag"]
    h1 = a["h1"]
    subtitle = a["subtitle"]
    sections = a["sections"]
    related_slugs = a["related"]
    
    canonical = f"https://vigyanllm.in/blog/{slug}"
    
    # Article schema
    article_schema = f"""{{
    "@context": "https://schema.org", "@type": "Article", "headline": {repr(title)}, "description": {repr(desc)}, "datePublished": "2026-07-01", "dateModified": "2026-07-01", "author": {{ "@type": "Person", "name": "VigyanLLM Research Team", "jobTitle": "Research Team, VigyanLLM" }}, "publisher": {{ "@type": "Organization", "name": "VigyanLLM Private Limited" }}, "mainEntityOfPage": {repr(canonical)}
    }}"""
    
    # Breadcrumb schema
    bread_schema = f"""{{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{ "@type": "ListItem", "position": 1, "name": "VigyanLLM", "item": "https://vigyanllm.in/" }},
      {{ "@type": "ListItem", "position": 2, "name": "Blog", "item": "https://vigyanllm.in/blog/index.html" }},
      {{ "@type": "ListItem", "position": 3, "name": {repr(title)}, "item": {repr(canonical)} }}
    ]
    }}"""
    
    # Build body content
    sections_html = "\n".join(f"      <h2>{h2}</h2>\n{body}" for h2, body in sections)
    
    # Related articles
    related_cards = ""
    for rs in related_slugs:
        rt, rd = RELATED.get(rs, ("Article", ""))
        related_cards += f"""        <div class="related-card">
          <h3><a href="./{rs}.html">{rt}</a></h3>
          <p>{rd}</p>
        </div>
"""
    
    # References (generic)
    refs = """        <li>VigyanLLM Research Team. (2026). Primer Design Best Practices. <em>VigyanLLM Technical Reports</em>.</li>
        <li>Global Molecular Biology Standards Committee. (2025). Guidelines for PCR Assay Development and Validation.</li>
        <li>Applied Biosystems. (2024). PCR Basics and Optimisation Guide. Thermo Fisher Scientific.</li>"""
    
    html = f'''<!DOCTYPE html>
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
  <title>{title} | VigyanLLM</title>
  <meta name="description" content="{desc}">
  <meta name="keywords" content="{kw}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical}">
  
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
  --bg: #FFFFFF;
  --border: #E2E8F0;
  --surface: #F8FAFC;
  --max-w: 1100px;
  --sec-p: 100px;
}}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    body {{ background: var(--bg); color: var(--text); font-family: var(--font-b); line-height: 1.6; -webkit-font-smoothing: antialiased; }}
    a {{ text-decoration: none; color: inherit; transition: color 0.15s ease; }}
    .container {{ max-width: var(--max-w); margin: 0 auto; padding: 0 24px; }}
    section {{ padding: var(--sec-p) 0; }}
    nav {{ position: sticky; top: 0; background: var(--navy); backdrop-filter: blur(8px); border-bottom: 1px solid rgba(255,255,255,0.1); z-index: 1000; height: 72px; }}
    @media (max-width: 768px) {{ .nav-links {{ display: none; }} }}
    
    .article-body {{ padding: 40px 0; max-width: 800px; margin: 0 auto; }}
    .article-body h1 {{ font-family: var(--font-b); font-size: clamp(2rem,4vw,2.8rem); font-weight: 400; line-height: 1.1; margin-bottom: 16px; }}
    .article-body h2 {{ font-size: 24px; font-weight: 600; color: var(--text); margin: 40px 0 16px; }}
    .article-body h3 {{ font-size: 18px; font-weight: 600; color: var(--text); margin: 28px 0 12px; }}
    .article-body p {{ margin-bottom: 16px; color: var(--text2); font-size: 15px; line-height: 1.8; }}
    .article-body ul, .article-body ol {{ margin-left: 24px; margin-bottom: 16px; color: var(--text2); font-size: 15px; }}
    .article-body li {{ margin-bottom: 8px; }}
    .article-body strong {{ color: var(--text); }}
    .article-body a {{ color: var(--primary); text-decoration: none; }}
    .article-body a:hover {{ text-decoration: underline; }}
    .article-body table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
    .article-body th {{ background: var(--surface); color: var(--text); padding: 12px; text-align: left; border: 1px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .article-body td {{ padding: 12px; border: 1px solid var(--border); color: var(--text2); }}
    .article-body tr:nth-child(even) {{ background: var(--surface); }}
    .article-body .callout {{ background: var(--surface); border-left: 4px solid var(--primary); padding: 20px 24px; border-radius: 0 12px 12px 0; margin: 24px 0; }}
    .article-body .callout-title {{ font-weight: 700; color: var(--primary); margin-bottom: 8px; }}
    .article-body code {{ background: var(--surface); padding: 2px 6px; border-radius: 4px; font-size: 13px; color: var(--text); border: 1px solid var(--border); }}
    .hero-blog {{ padding: 60px 0 30px; text-align: center; border-bottom: 1px solid var(--border); }}
    .cta-box {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 36px; text-align: center; margin: 40px 0; }}
    .cta-box h3 {{ font-size: 20px; color: var(--text); margin-bottom: 10px; }}
    .cta-box p {{ color: var(--text2); margin-bottom: 20px; }}
    .cta-btn {{ display: inline-block; padding: 14px 32px; background: var(--primary); color: #fff; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px; transition: background 0.2s; }}
    .cta-btn:hover {{ background: #0044ff; }}
    .references {{ padding: 30px 0; border-top: 1px solid var(--border); margin-top: 40px; }}
    .references h2 {{ font-size: 20px; color: var(--text); margin-bottom: 16px; font-weight: 600; }}
    .references ol {{ margin-left: 24px; color: var(--text2); font-size: 14px; }}
    
    .article-header .article-tag {{ display: inline-block; background: #e8f0ff; color: var(--primary); padding: 4px 14px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-bottom: 16px; }}
    .article-header .article-date {{ color: var(--muted); font-size: 13px; }}
    .article-header .article-author {{ color: var(--text2); font-size: 13px; font-weight: 600; }}
    .article-header h1 {{ font-size: clamp(2rem,4vw,2.8rem); font-weight: 400; line-height: 1.1; margin-bottom: 16px; }}
    .article-header .subtitle {{ font-size: 16px; color: var(--text2); line-height: 1.6; max-width: 700px; }}
    .article-meta-bar {{ display: flex; gap: 16px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }}
    .author-bio {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin: 40px 0 24px; display: flex; gap: 20px; align-items: flex-start; }}
    .author-bio-avatar {{ width: 60px; height: 60px; border-radius: 50%; background: var(--primary); display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 24px; flex-shrink: 0; }}
    .author-bio h4 {{ font-size: 16px; color: var(--text); margin-bottom: 6px; }}
    .author-bio p {{ font-size: 13px; color: var(--text2); line-height: 1.6; margin-bottom: 0; }}
    .related-articles {{ padding: 30px 0; border-top: 1px solid var(--border); margin-top: 24px; }}
    .related-articles h2 {{ font-size: 20px; color: var(--text); margin-bottom: 20px; font-weight: 600; }}
    .related-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; }}
    .related-card {{ border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: border-color 0.2s; }}
    .related-card:hover {{ border-color: var(--primary); }}
    .related-card h3 {{ font-size: 14px; font-weight: 600; margin-bottom: 8px; }}
    .related-card p {{ font-size: 12px; color: var(--text2); line-height: 1.6; margin-bottom: 0; }}
    .related-card a {{ color: var(--primary); font-weight: 600; }}
  </style>
  
  <script type="application/ld+json">
  {article_schema}
  </script>
  <script type="application/ld+json">
  {bread_schema}
  </script>
</head>
<body>
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-KRP5LLPR"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->

  <nav>
    <div class="nav-inner" style="display:flex;justify-content:space-between;align-items:center;height:100%;max-width:1200px;margin:0 auto;padding:0 24px">
      <a href="../index.html" class="nav-brand" style="display:flex;align-items:center;gap:10px;color:#fff;font-family:var(--font-h);font-size:20px;font-weight:700;text-decoration:none">
        <img src="../logo.svg" alt="VigyanLLM Logo" style="width:32px;height:32px;border-radius:4px">
        <span>VigyanLLM</span>
      </a>
      <div class="nav-links" style="display:flex;gap:32px;align-items:center">
        <a href="../index.html" style="font-family:var(--font-b);font-size:13px;color:#CBD5E1;font-weight:500;letter-spacing:0.02em">Home</a>
        <a href="../primer.html" style="font-family:var(--font-b);font-size:13px;color:#22D3EE;font-weight:600;letter-spacing:0.02em">VPrime 1.0 \u2197</a>
        <a href="./index.html" style="font-family:var(--font-b);font-size:13px;color:#CBD5E1;font-weight:500;letter-spacing:0.02em">Blog</a>
        <a href="../faq.html" style="font-family:var(--font-b);font-size:13px;color:#CBD5E1;font-weight:500;letter-spacing:0.02em">FAQ</a>
        <a href="../about.html" style="font-family:var(--font-b);font-size:13px;color:#CBD5E1;font-weight:500;letter-spacing:0.02em">About</a>
      </div>
      <div class="nav-right" style="display:flex;align-items:center;gap:16px">
        <button class="nav-login" onclick="window.location.href='../primer.html'" style="border:1.5px solid rgba(255,255,255,0.3);border-radius:4px;padding:8px 20px;font-family:var(--font-b);font-size:13px;font-weight:600;color:#fff;background:transparent;cursor:pointer">Login</button>
      </div>
    </div>
  </nav>

  <div style="max-width:var(--max-w);margin:0 auto;padding:0 24px">
    <header style="padding:50px 0 30px;border-bottom:1px solid var(--border)">
      <div class="article-meta-bar">
        <span class="article-tag">{tag}</span>
        <span class="article-date">Published: July 1, 2026</span>
        <span class="article-author">By VigyanLLM Research Team</span>
      </div>
      <h1>{h1}</h1>
      <p class="subtitle">{subtitle}</p>
    </header>

    <article class="article-body">
{sections_html}

      <div class="cta-box">
        <h3>Design PCR Primers with 22-Step Validation</h3>
        <p>Free for researchers and professors. Validate every parameter before ordering your primers.</p>
        <a href="../primer.html" class="cta-btn">Try VigyanLLM Primer Free \u2192</a>
      </div>
    </article>

    <div class="author-bio">
      <div class="author-bio-avatar">VR</div>
      <div>
        <h4>About the Author \u2014 VigyanLLM Research Team</h4>
        <p>The VigyanLLM Research Team combines expertise in molecular biology, bioinformatics, and artificial intelligence to build sovereign biomedical AI tools for researchers worldwide. Our team develops advanced primer design algorithms, PCR validation pipelines, and AI-driven genomics solutions at VigyanLLM.</p>
      </div>
    </div>

    <section class="related-articles">
      <h2>Related Articles</h2>
      <div class="related-grid">
{related_cards}      </div>
    </section>

    <section class="references">
      <h2>References</h2>
      <ol>
{refs}
      </ol>
    </section>
  </div>

  <footer style="background:var(--navy);color:#CBD5E1;padding:80px 0 32px">
    <div style="max-width:1200px;margin:0 auto;padding:0 24px">
      <div style="display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;gap:48px;margin-bottom:60px">
        <div>
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
            <img src="../logo.svg" alt="VigyanLLM Logo" style="width:32px;height:32px;border-radius:4px">
            <span style="font-family:var(--font-h);font-size:20px;font-weight:700;color:#fff">VigyanLLM</span>
          </div>
          <p style="font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:20px;line-height:1.6">Sovereign Healthcare &amp; Life Sciences AI.<br>Built in India. For the world.</p>
          <a href="mailto:contact@vigyanllm.in" style="font-family:var(--font-b);font-size:13px;color:var(--accent);display:block;margin-bottom:6px">contact@vigyanllm.in</a>
          <div style="display:flex;gap:12px;margin-top:24px">
            <a href="#" aria-label="Facebook" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg></a>
            <a href="#" aria-label="X" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><path d="M4 4l6.5 8.5L4 20h2l5.5-7 4.5 7h5l-7-9.5L20 4h-2l-5 6.5L9 4H4zm3 1.5h3l10 13h-3L7 5.5z"/></svg></a>
            <a href="#" aria-label="YouTube" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6a3 3 0 0 0-2.1 2.1C0 8.1 0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1c.5-1.9.5-5.8.5-5.8s0-3.9-.5-5.8zM9.5 15.5V8.5l6.3 3.5-6.3 3.5z"/></svg></a>
            <a href="#" aria-label="Instagram" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);color:#94A3B8;text-decoration:none"><svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:currentColor"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg></a>
          </div>
        </div>
        <div>
          <h5 style="font-family:var(--font-h);font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#fff;margin-bottom:24px;font-weight:700">Platform</h5>
          <a href="../index.html#problem" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Problem</a>
          <a href="../index.html#platform" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Platform</a>
          <a href="../index.html#architecture" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Architecture</a>
          <a href="../demo.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Demo</a>
        </div>
        <div>
          <h5 style="font-family:var(--font-h);font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#fff;margin-bottom:24px;font-weight:700">Resources</h5>
          <a href="../primer.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">VPrime 1.0</a>
          <a href="./blog/index.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Blog</a>
          <a href="../faq.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">FAQ</a>
          <a href="../about.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">About</a>
        </div>
        <div>
          <h5 style="font-family:var(--font-h);font-size:12px;text-transform:uppercase;letter-spacing:0.1em;color:#fff;margin-bottom:24px;font-weight:700">Contact</h5>
          <a href="mailto:contact@vigyanllm.in" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">contact@vigyanllm.in</a>
          <a href="../privacy.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Privacy</a>
          <a href="../cookies.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Cookies</a>
          <a href="../terms.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Terms</a>
          <a href="../refund.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Refund</a>
          <a href="../security.html" style="display:block;font-family:var(--font-b);font-size:13px;color:#94A3B8;margin-bottom:14px">Security</a>
        </div>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:24px;display:flex;justify-content:space-between;font-family:var(--font-b);font-size:12px;color:#64748B">
        <span>&copy; <script>document.write(new Date().getFullYear())</script> VigyanLLM Pvt. Ltd. \u00b7 Sovereign Research AI</span>
        <span>WWW.VIGYANLLM.IN</span>
      </div>
    </div>
  </footer>
</body>
</html>'''
    return html

# ── MAIN ──────────────────────────────────────────────────────────────────

def main():
    created = []
    for a in articles:
        slug = a["slug"]
        html = build_html(a)
        path = os.path.join(OUT, f"{slug}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        created.append(f"{slug}.html")
        wc = len(html.split())
        print(f"  Created {slug}.html ({wc} words)")
    
    print(f"\nDone! Created {len(created)} files:")
    for f in created:
        print(f"  blog/{f}")

if __name__ == "__main__":
    main()
