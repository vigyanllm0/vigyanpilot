// CloudFront Function — Viewer Request v19
// (numbering follows the AWS function Config Comment, not this header;
//  drifted to "v6" while AWS was at v14 — kept in sync since v15. SIZE CAP 10 KB.)
// Bot blocking, domain canonicalization, .html strip,
// redirects, trailing-slash normalization, clean URL rewrites.
// v19: /blog-post → /blog 301 (SPA blog scaffold: noindex + canonical=/blog,
//      unlinked — a soft-404 at a URL crawlers still hold).
// v18: /hub/primer-design redirect removed (page restored: real content + sitemap).
// v17: schema-junk ?q={search_term...} 301s; .html strip preserves query string.
// v16: /r/:code real 301 (bare-string querystring caused 503 FunctionValidationError).
// v15: +11 redirects for GSC-404 URLs (map below; invalidate after publish —
//      redirect rules ship cache-control max-age=86400).
function handler(event) {
  var r = event.request;
  var u = r.uri;
  var h = r.headers;

  // 0a. SCHEMA-TEMPLATE JUNK URLs — 301 to the bare path.
  // A Jun-2026 SearchAction schema shipped "target": ".../primer.html?q={search_term_string}"
  // (commit 43194385); Google still re-crawls those literal-template URLs from its
  // discovery table and they returned 200 forever = "Crawled – not indexed" squatting.
  // Any query containing the literal marker "search_term" (encoded %7B or raw {)
  // is template junk no human can type — terminate re-crawls with a redirect.
  var qsIn = r.querystring;
  for (var qk in qsIn) {
    if ((qk + qv(qsIn[qk])).indexOf('search_term') !== -1) {
      var tp = u;
      if (tp.length > 5 && tp.substring(tp.length - 5) === '.html') tp = tp.substring(0, tp.length - 5);
      return redir(tp === '/index' ? '/' : tp);
    }
  }

  // 0. .HTML STRIP — /primer.html → /primer (before file ext check).
  // Query string is preserved (was dropped: /primer.html?ref=CODE lost ?ref=).
  if (u.length > 5 && u.substring(u.length - 5) === '.html') {
    var s = u.substring(0, u.length - 5);
    if (s.length > 1) return redir(s + qsSuffix(qsIn));
  }

  // 1. NON-HTML FILE EXTENSION — serve as-is (css, js, xml, txt, png, etc.)
  if (u.match(/\.\w{1,5}$/)) return r;

  // 1b. API + HEALTH + ACME — pass through to EC2 origin untouched
  if (u.indexOf('/api/') === 0 || u === '/health' || u.indexOf('/.well-known/') === 0) return r;

  // 1c. LEGACY ADMIN PAGES - block directly (no forwarding to EC2).
  // /cms-admin is deliberately NOT blocked: production CMS login serves the
  //   shell from S3; the API behind it enforces Bearer-JWT auth + require_admin.
  if (u === '/admin' || u === '/admin-reviews'
      || u.indexOf('/admin/') === 0) {
    return { statusCode: 403, statusDescription: 'Forbidden',
      headers: { 'content-type': { value: 'text/plain' } }, body: 'Forbidden' };
  }

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
    // Duplicate URL variants of the home page / blog index (GSC Tier 2:
    // consolidate duplicate clusters — one canonical URL per page).
    '/index': '/',
    '/blog/index': '/blog',
    // v19: SPA blog scaffold blog-post.html (noindex + canonical=/blog, unlinked)
    //      = soft-404 at /blog-post → redirect to the live hub.
    '/blog-post': '/blog',
    // Root-level header.html/footer.html are unbaked partial fragments,
    // not pages — send crawlers to the home page instead of a raw fragment.
    '/header': '/',
    '/footer': '/',
    '/tools/dna-to-rna': '/dna-to-rna',
    '/primer-3-alternative': '/primer3-alternative',
    '/Learning-vigyanllm': '/learning-vigyanllm',
    '/crispr': '/crispr-analysis',
    '/cloning': '/cloning-simulator',
    '/sequence-search': '/primer',
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
    '/glossary/penalty-matrix': '/glossary/alignment',
    // --- URLs Google still holds that 404 (GSC 404 cleanup; derived without a
    // GSC export: internal links + 58 sitemap revisions + deleted files) →
    // each target below is a canonical live page, never a 404. ---
    '/contact': '/support',
    // Glossary hub is /glossary (linked from 9 pages); the old index page is gone.
    '/glossary-index': '/glossary',
    // "-for-beginners" URLs appeared in historical sitemaps but were never
    // built. Consolidate onto each tool's canonical page (one URL per tool).
    '/blast-for-beginners': '/blast',
    '/docking-for-beginners': '/docking',
    '/msa-for-beginners': '/msa',
    '/pcr-for-beginners': '/pcr-analysis',
    '/primer-design-for-beginners': '/primer',
    // Unbaked partial fragments (same treatment as /header and /footer above).
    '/header_template': '/',
    '/footer_template': '/',
    '/nav': '/',
    // Deleted test page — no content value, send crawlers home.
    '/tools/test': '/'
  };
  if (redirects[u]) return redir(redirects[u]);

  // 7. 410 GONE
  if (u === '/cite') {
    return { statusCode: 410, statusDescription: 'Gone',
      headers: { location: { value: '/' }, 'content-type': { value: 'text/plain' } }, body: 'Gone' };
  }

  // 8. CLEAN URL REWRITES (explicit mappings)
  var rewrites = {
    '/blog': '/blog/index.html',
    '/developer': '/developer.html',
    '/developer/docs': '/developer-docs.html',
    '/developer/keys': '/developer-keys.html',
    '/developer/playground': '/developer-playground.html',
    '/developer/webhooks': '/developer-webhooks.html',
    '/developer/usage': '/developer-usage.html',
    '/api/sitemap.xml': '/sitemap.xml'
  };
  if (rewrites[u]) { r.uri = rewrites[u]; return r; }

  // /r/:code → 301 /primer?ref=:code   (referral short link)
  // MUST be a client 301, not an internal rewrite: primer-app.js reads ?ref=
  // from location.search, which only the browser sees. Assigning a bare string
  // to r.querystring also violates CloudFront's schema (querystring values must
  // be {value:...} objects) -> FunctionValidationError -> 503 on every share link.
  var ref = u.match(/^\/r\/([A-Za-z0-9_-]+)$/);
  if (ref) {
    return redir('/primer?ref=' + encodeURIComponent(ref[1]));
  }

  // 9. FALLBACK — try .html for clean URLs (/primer → /primer.html)
  r.uri = u + '.html';
  return r;
}

function redir(loc) {
  return { statusCode: 301, statusDescription: 'Moved Permanently',
    headers: { location: { value: loc }, 'cache-control': { value: 'public, max-age=86400' } }, body: '' };
}

// Query-param value accessor: the CloudFront input event carries plain strings,
// while this harness (and the *output* request schema) uses {value:...} objects.
function qv(x) {
  return (x !== null && typeof x === 'object' && 'value' in x) ? String(x.value) : String(x);
}

// Rebuild "?k=v&..." from the input querystring for client redirects.
function qsSuffix(qs) {
  var parts = [];
  for (var k in qs) parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(qv(qs[k])));
  return parts.length ? '?' + parts.join('&') : '';
}
