/**
 * VigyanLLM Edge Middleware — Vercel Edge Network
 * ==================================================
 * Protects admin paths and blocks malicious crawlers at the
 * edge before requests reach the origin server.
 *
 * Uses only standard Web API primitives (Request/Response) —
 * no Next.js imports required.
 */

const ADMIN_PATHS = ['/admin-security.html', '/admin-security'];
const MALICIOUS_CRAWLERS = /(ahrefsbot|semrushbot|mj12bot|dotbot|majestic|meanpath|rogerbot|xovi)/i;

export default function middleware(request) {
  const url = new URL(request.url);
  const pathname = url.pathname;

  // Block malicious crawlers at the edge
  const ua = request.headers.get('user-agent') || '';
  if (MALICIOUS_CRAWLERS.test(ua)) {
    return new Response('Forbidden', { status: 403 });
  }

  // Admin pages require admin_tk cookie (defense-in-depth alongside backend RBAC)
  // Parse cookies properly to avoid substring matches
  if (ADMIN_PATHS.includes(pathname)) {
    const cookie = request.headers.get('cookie') || '';
    const cookies = Object.fromEntries(
      cookie.split(';').map(c => c.trim().split('=')).filter(([k]) => k).map(([k, ...v]) => [k, v.join('=')])
    );
    if (!cookies['admin_tk']) {
      return new Response('Unauthorized', { status: 401 });
    }
  }

  // Allow all other requests through
  return;
}

export const config = {
  matcher: ['/admin-security.html', '/admin-security'],
};
