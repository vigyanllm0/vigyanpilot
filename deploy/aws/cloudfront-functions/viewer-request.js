// CloudFront Function — Viewer Request v6
// Bot blocking, domain canonicalization, .html strip,
// redirects, trailing-slash normalization, clean URL rewrites.
function handler(event) {
  var r = event.request;
  var u = r.uri;
  var h = r.headers;

  // 0. .HTML STRIP FIRST — /primer.html → /primer (before file ext check)
  if (u.length > 5 && u.substring(u.length - 5) === '.html') {
    var s = u.substring(0, u.length - 5);
    if (s.length > 1) return redir(s);
  }

  // 1. NON-HTML FILE EXTENSION — serve as-is (css, js, xml, txt, png, etc.)
  if (u.match(/\.\w{1,5}$/)) return r;

  // 2. BOT BLOCKING (excludes /api/, /_next/, /assets/, /partials/)
  if (u.indexOf('/api/') !== 0 && u.indexOf('/_next/') !== 0 &&
      u.indexOf('/assets/') !== 0 && u.indexOf('/partials/') !== 0) {
    var ua = h['user-agent'] ? h['user-agent'].value : '';
    if (/(ahrefsbot|semrushbot|mj12bot|dotbot|majestic|meanpath|rogerbot|xovi)/i.test(ua)) {
      return { statusCode: 403, statusDescription: 'Forbidden',
        headers: { 'content-type': { value: 'text/plain' } }, body: 'Forbidden' };
    }
  }

  // 3. DOMAIN CANONICALIZATION — vigyanllm.in → www
  if (h.host ? h.host.value === 'vigyanllm.in' : false) {
    return redir('https://www.vigyanllm.in' + u);
  }

  // 4. ROOT → /index.html
  if (u === '/') { r.uri = '/index.html'; return r; }

  // 5. TRAILING-SLASH NORMALIZATION — /path/ → /path
  if (u.length > 1 && u.charAt(u.length - 1) === '/') {
    return redir(u.substring(0, u.length - 1));
  }

  // 6. CONTENT REDIRECTS (before clean URL rewrite)
  var redirects = {
    '/tools/dna-to-rna': '/dna-to-rna',
    '/primer-3-alternative': '/primer3-alternative',
    '/Learning-vigyanllm': '/learning-vigyanllm',
    '/crispr': '/crispr-analysis',
    '/cloning': '/cloning-simulator',
    '/sequence-search': '/primer',
    '/hub/primer-design': '/primer',
    '/blog/pcr-cycling-conditions': '/blog/pcr-steps',
    '/blog/taq-polymerase-vs-high-fidelity': '/blog/hot-start-pcr-technology',
    '/blog/allele-specific-pcr-primer-design': '/blog/colony-pcr-primer-design',
    '/blog/nested-pcr-primer-design-guide': '/blog/colony-pcr-primer-design',
    '/blog/real-time-pcr-primer-design': '/blog/real-time-pcr-data-analysis',
    '/blog/reverse-transcription-pcr-primer-design': '/blog/rt-pcr-vs-qpcr',
    '/blog/gene-expression-analysis-qpcr': '/blog/digital-pcr-vs-qpcr',
    '/blog/sanger-sequencing-primer-design': '/blog/primer-design-rules',
    '/glossary/cytokinesis': '/glossary/cell',
    '/glossary/cell-membrane': '/glossary/cell',
    '/glossary/cell-differentiation': '/glossary/cell',
    '/glossary/nucleus': '/glossary/cell',
    '/glossary/lysosome': '/glossary/cell',
    '/glossary/golgi-apparatus': '/glossary/cell',
    '/glossary/endoplasmic-reticulum': '/glossary/cell',
    '/glossary/endocytosis': '/glossary/cell',
    '/glossary/exocytosis': '/glossary/cell',
    '/glossary/cytoskeleton': '/glossary/cell',
    '/glossary/forward-primer': '/glossary/primer',
    '/glossary/reverse-primer': '/glossary/primer',
    '/glossary/nearest-neighbor-model': '/glossary/melting-temperature',
    '/glossary/salt-correction': '/glossary/melting-temperature',
    '/glossary/mg2-correction': '/glossary/melting-temperature',
    '/glossary/rychlik-formula': '/glossary/melting-temperature',
    '/glossary/delta-g': '/glossary/melting-temperature',
    '/glossary/gc-clamp': '/glossary/primer-design',
    '/glossary/thermocycling-profile': '/glossary/pcr',
    '/glossary/mass-spectrometry-proteomics': '/glossary/mass-spectrometry',
    '/glossary/blast-specificity': '/glossary/blast',
    '/glossary/bowtie2-alignment': '/glossary/alignment',
    '/glossary/real-time-pcr': '/glossary/qpcr',
    '/glossary/snp-filtering': '/glossary/snp',
    '/glossary/pathogenic-variant': '/glossary/genetic-variant',
    '/glossary/haplotype': '/glossary/genetic-variant',
    '/glossary/proteasome': '/glossary/protein',
    '/glossary/retrotransposon': '/glossary/transposon',
    '/glossary/penalty-matrix': '/glossary/alignment'
  };
  if (redirects[u]) return redir(redirects[u]);

  // 7. 410 GONE
  if (u === '/cite') {
    return { statusCode: 410, statusDescription: 'Gone',
      headers: { location: { value: '/' }, 'content-type': { value: 'text/plain' } }, body: 'Gone' };
  }

  // 8. CLEAN URL REWRITES (explicit mappings)
  var rewrites = {
    '/admin': '/admin-security.html',
    '/developer': '/developer.html',
    '/developer/docs': '/developer-docs.html',
    '/developer/keys': '/developer-keys.html',
    '/developer/playground': '/developer-playground.html',
    '/developer/webhooks': '/developer-webhooks.html',
    '/developer/usage': '/developer-usage.html',
    '/api/sitemap.xml': '/sitemap.xml'
  };
  if (rewrites[u]) { r.uri = rewrites[u]; return r; }

  // /r/:code → /primer.html?ref=:code
  var ref = u.match(/^\/r\/([A-Za-z0-9_-]+)$/);
  if (ref) {
    r.uri = '/primer.html';
    r.querystring.ref = ref[1];
    return r;
  }

  // 9. FALLBACK — try .html for clean URLs (/primer → /primer.html)
  r.uri = u + '.html';
  return r;
}

function redir(loc) {
  return { statusCode: 301, statusDescription: 'Moved Permanently',
    headers: { location: { value: loc }, 'cache-control': { value: 'public, max-age=86400' } }, body: '' };
}
