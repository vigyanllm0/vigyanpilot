#!/usr/bin/env python3
"""Secure static file server for VigyanLLM frontend (localhost:8080).

Replaces `python -m http.server` which is vulnerable to path traversal.
Blocks all `..` traversal attempts, adds security headers, and binds only to localhost.
Uses environment variables only — no .env file reading.
"""

import os
import sys
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler


class SecureHandler(SimpleHTTPRequestHandler):
    """Static file handler that blocks directory traversal and adds security headers."""

    # Path traversal defence — reject any request containing '..' or encoded variants
    PATH_TRAVERSAL_RE = re.compile(r'(?:\.\.|%2e%2e|%252e%252e|\.\x00\.)')

    def do_GET(self):
        if self.PATH_TRAVERSAL_RE.search(self.path):
            self.send_error(403, "Forbidden")
            return
        # Must be exactly at / or begin with / (but not /..)
        if not self.path.startswith("/"):
            self.send_error(400, "Bad Request")
            return
        super().do_GET()

    def do_HEAD(self):
        if self.PATH_TRAVERSAL_RE.search(self.path):
            self.send_error(403, "Forbidden")
            return
        if not self.path.startswith("/"):
            self.send_error(400, "Bad Request")
            return
        super().do_HEAD()

    def translate_path(self, path):
        """Override to prevent serving files outside the frontend directory."""
        parts = path.split("/")
        # Strip query string from last part
        if parts and "?" in parts[-1]:
            parts[-1] = parts[-1].split("?")[0]
        stripped = [p for p in parts if p and p != "."]
        if ".." in stripped:
            self.send_error(403, "Forbidden")
            return ""
        # Normalise: join relative to frontend directory
        safe = os.path.join(self.server.frontend_root, *stripped)
        # Ensure we're still inside the frontend root
        real_root = os.path.realpath(self.server.frontend_root)
        real_path = os.path.realpath(safe)
        if not real_path.startswith(real_root + os.sep) and real_path != real_root:
            self.send_error(403, "Forbidden")
            return ""
        return safe

    def send_error(self, code, message=None):
        """Send error with security headers."""
        super().send_error(code, message)

    def version_string(self):
        return "VigyanLLM"

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' https://accounts.google.com https://cdn.tailwindcss.com https://checkout.razorpay.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' http://localhost:11436; frame-src https://accounts.google.com https://checkout.razorpay.com")
        super().end_headers()


class SecureServer(HTTPServer):
    """HTTP server that knows the frontend root directory."""

    def __init__(self, server_address, RequestHandlerClass, frontend_root):
        self.frontend_root = os.path.realpath(frontend_root)
        super().__init__(server_address, RequestHandlerClass)


def main():
    frontend_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "frontend"
    )
    if not os.path.isdir(frontend_dir):
        print(f"ERROR: Frontend directory not found: {frontend_dir}", file=sys.stderr)
        sys.exit(1)

    port = int(os.environ.get("FRONTEND_PORT", "8080"))
    host = os.environ.get("FRONTEND_HOST", "127.0.0.1")

    server = SecureServer((host, port), SecureHandler, frontend_dir)
    print(f"[SecureFrontend] Serving {frontend_dir} on http://{host}:{port}")
    print(f"[SecureFrontend] Path traversal blocked, security headers enabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SecureFrontend] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
