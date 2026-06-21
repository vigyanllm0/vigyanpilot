import { NextResponse } from 'next/server'
import crypto from 'crypto'

export function middleware(request) {
  const { pathname } = request.nextUrl
  
  // Protect admin API endpoints - require valid admin session cookie
  if (pathname.startsWith('/api/admin/') || pathname === '/admin-security.html' || pathname === '/admin-security') {
    const token = request.cookies.get('admin_tk')?.value
    
    if (!token) {
      if (pathname.startsWith('/api/')) {
        return new Response(JSON.stringify({ error: 'Unauthorized', code: 'NO_TOKEN' }), { 
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        })
      } else {
        return new Response('Unauthorized', { status: 401 })
      }
    }
  }
  
  let response = NextResponse.next()

  if (pathname === '/admin-security.html' || pathname === '/admin-security') {
    const nonce = Buffer.from(crypto.randomUUID()).toString('base64')
    const csp = [
      `default-src 'self'`,
      `script-src 'self' 'nonce-${nonce}'`,
      `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`,
      `font-src 'self' https://fonts.gstatic.com`,
      `img-src 'self' data: https:`,
      `connect-src 'self'`,
      `frame-ancestors 'none'`,
      `base-uri 'self'`,
      `object-src 'none'`,
      `worker-src 'self'`
    ].join('; ')
    
    response.headers.set('Content-Security-Policy', csp)
    response.headers.set('x-nonce', nonce)
  }
  
  return response
}

export const config = {
  matcher: ['/api/admin/:path*', '/admin-security.html', '/admin-security']
}