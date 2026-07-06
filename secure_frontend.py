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
from urllib.request import Request, urlopen
from urllib.parse import urlparse


BACKEND = os.environ.get("VIGYAN_BACKEND_URL", "http://127.0.0.1:11436")


class SecureHandler(SimpleHTTPRequestHandler):
    """Static file handler with API proxying and security headers."""

    # Path traversal defence — reject any request containing '..' or encoded variants
    PATH_TRAVERSAL_RE = re.compile(r'(?:\.\.|%2e%2e|%252e%252e|\.\x00\.)')
    # API paths to proxy to backend
    API_PREFIXES = ("/api/", "/health")

    def _is_api_path(self, path):
        clean = path.split("?")[0].split("#")[0]
        for p in self.API_PREFIXES:
            if clean.startswith(p):
                return True
        return False

    def _proxy_request(self, method):
        if self.PATH_TRAVERSAL_RE.search(self.path):
            self.send_error(403, "Forbidden")
            return
        target = BACKEND + self.path.split("?")[0] if "?" in self.path else BACKEND + self.path
        if self.path.find("?") != -1:
            target += "?" + self.path.split("?", 1)[1]
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        try:
            req = Request(target, data=body, method=method)
            for k, v in self.headers.items():
                skip = ("Host", "Connection", "Transfer-Encoding")
                if k not in skip:
                    req.add_header(k, v)
            resp = urlopen(req, timeout=120)
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                skip = ("Transfer-Encoding", "Content-Encoding", "Content-Length")
                if k.lower() not in ("transfer-encoding", "content-encoding", "content-length"):
                    self.send_header(k, v)
            self.end_headers()
            chunk = resp.read(8192)
            while chunk:
                self.wfile.write(chunk)
                chunk = resp.read(8192)
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Proxy error: {exc}".encode())

    def do_GET(self):
        if self._is_api_path(self.path):
            self._proxy_request("GET")
            return
        if self.PATH_TRAVERSAL_RE.search(self.path):
            self.send_error(403, "Forbidden")
            return
        if not self.path.startswith("/"):
            self.send_error(400, "Bad Request")
            return
        super().do_GET()

    def do_POST(self):
        if self._is_api_path(self.path):
            self._proxy_request("POST")
            return
        self.send_error(404, "Not Found")

    def do_PUT(self):
        if self._is_api_path(self.path):
            self._proxy_request("PUT")
            return
        self.send_error(404, "Not Found")

    def do_DELETE(self):
        if self._is_api_path(self.path):
            self._proxy_request("DELETE")
            return
        self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        if self._is_api_path(self.path):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()
            return
        self.send_error(404, "Not Found")

    def do_HEAD(self):
        if self._is_api_path(self.path):
            self._proxy_request("HEAD")
            return
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
        if parts and "?" in parts[-1]:
            parts[-1] = parts[-1].split("?")[0]
        stripped = [p for p in parts if p and p != "."]
        if ".." in stripped:
            self.send_error(403, "Forbidden")
            return ""
        safe = os.path.join(self.server.frontend_root, *stripped)
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
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' https://accounts.google.com https://cdn.tailwindcss.com https://checkout.razorpay.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' http://localhost:11436 https://*.ngrok-free.dev; frame-src https://accounts.google.com https://checkout.razorpay.com")
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
