/**
 * VigyanLLM Edge Middleware — Vercel Edge Network
 * ==================================================
 * Blocks malicious crawlers at the edge before requests reach
 * the origin server.
 *
 * Admin page auth is handled by backend RBAC (admin_tk cookie checked
 * server-side) — no edge middleware needed for HTML protection.
 *
 * Uses only standard Web API primitives (Request/Response) —
 * no Next.js imports required.
 */

const MALICIOUS_CRAWLERS = /(ahrefsbot|semrushbot|mj12bot|dotbot|majestic|meanpath|rogerbot|xovi)/i;

export default function middleware(request) {
  const url = new URL(request.url);

  // Block malicious crawlers at the edge
  const ua = request.headers.get('user-agent') || '';
  if (MALICIOUS_CRAWLERS.test(ua)) {
    return new Response('Forbidden', { status: 403 });
  }

  // Allow all other requests through
  return;
}

export const config = {
  matcher: ['/admin-security.html', '/admin-security'],
};
