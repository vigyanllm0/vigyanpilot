// CloudFront Function: Viewer Response
// Adds security headers, CORS headers, and cache-control headers
// to all responses before they reach the viewer.
// Max 10 KB script, 2 ms runtime, no network access.

function handler(event) {
  var response = event.response;
  var headers = response.headers;
  var request = event.request;
  var uri = request.uri;

  // ──────────────────────────────────────────────────────────────────────
  // 1. SECURITY HEADERS — all responses (from vercel.json catch-all)
  // ──────────────────────────────────────────────────────────────────────
  headers['x-content-type-options'] = { value: 'nosniff' };
  headers['x-frame-options']        = { value: 'DENY' };
  headers['cross-origin-opener-policy']     = { value: 'same-origin' };
  headers['referrer-policy']       = { value: 'strict-origin-when-cross-origin' };
  headers['strict-transport-security'] = {
    value: 'max-age=31536000; includeSubDomains; preload'
  };
  headers['permissions-policy']    = { value: 'camera=(), microphone=(), geolocation=()' };
  headers['server']                = { value: '' };
  headers['x-powered-by']          = { value: '' };

  // ──────────────────────────────────────────────────────────────────────
  // 2. CORS HEADERS — /api/* responses
  // ──────────────────────────────────────────────────────────────────────
  if (uri.indexOf('/api/') === 0) {
    headers['access-control-allow-origin']  = { value: 'https://www.vigyanllm.in' };
    headers['access-control-allow-credentials'] = { value: 'true' };
    headers['access-control-allow-methods'] = { value: 'GET, POST, OPTIONS' };
    headers['access-control-allow-headers'] = { value: 'Content-Type, Authorization' };
    headers['access-control-max-age']       = { value: '86400' };

    // Preflight: return 200 with CORS headers only
    if (request.method === 'OPTIONS') {
      return {
        statusCode: 200,
        statusDescription: 'OK',
        headers: headers,
        body: ''
      };
    }
  }

  // ──────────────────────────────────────────────────────────────────────
  // 3. CACHE-CONTROL — static assets (from vercel.json headers)
  // ──────────────────────────────────────────────────────────────────────

  // Fonts: 1 year immutable
  if (uri.indexOf('/fonts/') === 0 ||
      uri.match(/\.(woff|woff2|ttf|otf|eot)$/)) {
    headers['cache-control'] = { value: 'public, max-age=31536000, immutable' };
  }
  // Images: 1 day stale-while-revalidate
  else if (uri.indexOf('/images/') === 0 ||
           uri.match(/\.(svg|png|jpe?g|gif|webp|ico)$/)) {
    headers['cache-control'] = { value: 'public, max-age=86400, stale-while-revalidate=604800' };
  }
  // JS/CSS: 1 day stale-while-revalidate
  else if (uri.match(/\.(js|css)$/)) {
    headers['cache-control'] = { value: 'public, max-age=86400, stale-while-revalidate=604800' };
  }
  // HTML: 5 min stale-while-revalidate
  else if (uri.match(/\.html$/)) {
    headers['cache-control'] = { value: 'public, max-age=300, stale-while-revalidate=600' };
  }
  // Special files
  else if (uri === '/sitemap.xml' || uri === '/robots.txt' ||
           uri === '/security.txt' || uri.indexOf('/.well-known/') === 0) {
    headers['content-type'] = { value: 'text/plain; charset=utf-8' };
    headers['cache-control'] = { value: 'public, max-age=3600' };
  }
  else if (uri === '/manifest.json') {
    headers['content-type'] = { value: 'application/json' };
    headers['cache-control'] = { value: 'public, max-age=86400' };
  }
  else if (uri === '/rss.xml' || uri.indexOf('/blog/rss') === 0) {
    headers['cache-control'] = { value: 'public, max-age=3600' };
  }
  // Default: no-cache (HTML pages not caught above)
  else if (uri.match(/\/$/) || !uri.match(/\.[a-zA-Z0-9]+$/)) {
    headers['cache-control'] = { value: 'public, max-age=0, must-revalidate' };
  }

  // ──────────────────────────────────────────────────────────────────────
  // 4. PER-PAGE CSP — override the global CSP for pages that need it.
  //    In production, move CSP to Lambda@Edge origin-request for full
  //    flexibility. This is the viewer-response fallback.
  // ──────────────────────────────────────────────────────────────────────
  var csp = null;

  if (uri === '/primer.html' || uri === '/primer' ||
      uri === '/docking.html' || uri === '/docking') {
    csp = "default-src 'self'; script-src 'self' https://accounts.google.com https://checkout.razorpay.com https://3Dmol.org 'unsafe-inline' https://www.googletagmanager.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; connect-src 'self' https://accounts.google.com https://www.googleapis.com https://api.razorpay.com https://lumberjack.razorpay.com https://www.google-analytics.com https://www.google.com; frame-src https://accounts.google.com https://api.razorpay.com https://checkout.razorpay.com https://www.googletagmanager.com https://www.youtube.com https://www.youtube.com/embed; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'; worker-src 'self'";
  }
  else if (uri === '/index.html' || uri === '/' ||
           uri === '/demo.html' || uri === '/demo') {
    csp = "default-src 'self'; script-src 'self' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com 'unsafe-inline' https://www.googletagmanager.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; connect-src 'self' https://accounts.google.com https://www.googleapis.com https://www.google-analytics.com https://www.google.com; frame-src https://accounts.google.com https://www.youtube.com https://www.youtube.com/embed; base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'; worker-src 'self'";
  }
  else if (uri.indexOf('/blog') === 0) {
    csp = "default-src 'self'; script-src 'self' https://www.googletagmanager.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; connect-src 'self' https://www.google-analytics.com https://www.google.com; frame-src 'none'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'; worker-src 'self'";
  }
  else if (uri === '/admin-security.html' || uri === '/admin') {
    csp = "default-src 'self'; script-src 'self' https://www.googletagmanager.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; connect-src 'self' https://www.google-analytics.com https://www.google.com; frame-src 'none'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'; worker-src 'self'";
  }
  else {
    // Global fallback CSP
    csp = "default-src 'self'; script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com https://www.googletagmanager.com https://checkout.razorpay.com https://cdn.razorpay.com https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://3Dmol.org https://www.clarity.ms; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://www.vigyanllm.in https://accounts.google.com https://www.googleapis.com https://api.razorpay.com https://lumberjack.razorpay.com https://www.google-analytics.com https://www.google.com https://cdn.jsdelivr.net; frame-src https://api.razorpay.com https://checkout.razorpay.com https://accounts.google.com https://www.youtube.com https://www.youtube.com/embed; frame-ancestors 'none'; base-uri 'self'; form-action 'self' https://formspree.io; object-src 'none'; upgrade-insecure-requests";
  }

  headers['content-security-policy'] = { value: csp };

  return response;
}
