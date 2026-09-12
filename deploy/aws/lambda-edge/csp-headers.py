"""
Lambda@Edge — Content-Security-Policy header injection

Runs on ORIGIN RESPONSE to set CSP headers based on request URI.
Deployed to us-east-1 (CloudFront requirement).

Policies sourced from vercel.json (7 variants).
"""

import re

# ---------------------------------------------------------------------------
# CSP policies — exact strings from vercel.json
# ---------------------------------------------------------------------------

CSP_POLICIES = {
    # /admin-security.html
    "admin": (
        "default-src 'self'; "
        "script-src 'self' https://www.googletagmanager.com 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; "
        "connect-src 'self' https://www.google-analytics.com https://www.google.com; "
        "frame-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "worker-src 'self'"
    ),
    # /primer.html
    "primer": (
        "default-src 'self'; "
        "script-src 'self' https://accounts.google.com https://checkout.razorpay.com 'unsafe-inline' https://www.googletagmanager.com 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; "
        "connect-src 'self' https://accounts.google.com https://www.googleapis.com https://api.razorpay.com https://lumberjack.razorpay.com https://www.google-analytics.com https://www.google.com; "
        "frame-src https://accounts.google.com https://api.razorpay.com https://checkout.razorpay.com https://www.youtube.com https://www.youtube.com/embed; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "worker-src 'self'"
    ),
    # /demo.html
    "demo": (
        "default-src 'self'; "
        "script-src 'self' https://www.googletagmanager.com 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; "
        "connect-src 'self' https://www.google-analytics.com https://www.google.com; "
        "frame-src https://www.youtube.com https://www.youtube.com/embed; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "worker-src 'self'"
    ),
    # /docking.html
    "docking": (
        "default-src 'self'; "
        "script-src 'self' https://accounts.google.com https://checkout.razorpay.com https://3Dmol.org https://www.googletagmanager.com 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; "
        "connect-src 'self' https://accounts.google.com https://www.googleapis.com https://api.razorpay.com https://lumberjack.razorpay.com https://www.google-analytics.com https://www.google.com; "
        "frame-src https://accounts.google.com https://api.razorpay.com https://checkout.razorpay.com https://www.googletagmanager.com; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "worker-src 'self'"
    ),
    # /index.html
    "index": (
        "default-src 'self'; "
        "script-src 'self' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com 'unsafe-inline' https://www.googletagmanager.com 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; "
        "connect-src 'self' https://accounts.google.com https://www.googleapis.com https://www.google-analytics.com https://www.google.com; "
        "frame-src https://accounts.google.com; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "worker-src 'self'"
    ),
    # /blog(/.*)?
    "blog": (
        "default-src 'self'; "
        "script-src 'self' https://www.googletagmanager.com 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: https://www.googletagmanager.com https://www.google-analytics.com; "
        "connect-src 'self' https://www.google-analytics.com https://www.google.com; "
        "frame-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "worker-src 'self'"
    ),
    # Catch-all fallback (matches /(.*)  in vercel.json)
    "default": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://accounts.google.com https://apis.google.com https://www.googletagmanager.com https://checkout.razorpay.com https://cdn.razorpay.com https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://3Dmol.org https://www.clarity.ms; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' https://www.vigyanllm.in https://accounts.google.com https://www.googleapis.com https://api.razorpay.com https://lumberjack.razorpay.com https://www.google-analytics.com https://www.google.com https://cdn.jsdelivr.net; "
        "frame-src https://api.razorpay.com https://checkout.razorpay.com https://accounts.google.com https://www.youtube.com https://www.youtube.com/embed; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self' https://formspree.io; "
        "object-src 'none'; "
        "upgrade-insecure-requests"
    ),
}

# ---------------------------------------------------------------------------
# URI → policy matching (order matters: specific first, then catch-all)
# ---------------------------------------------------------------------------

URI_RULES = [
    # Exact path matches (clean URLs from Vercel rewrites)
    (re.compile(r"^/admin(?:-security(?:\.html)?)?$"), "admin"),
    (re.compile(r"^/primer(?:\.html)?$"),         "primer"),
    (re.compile(r"^/demo(?:\.html)?$"),           "demo"),
    (re.compile(r"^/docking(?:\.html)?$"),        "docking"),
    (re.compile(r"^/index\.html$"),               "index"),
    # Prefix match for blog
    (re.compile(r"^/blog(?:/.*)?$"),              "blog"),
    # /r/:code → primer (short-link redirect)
    (re.compile(r"^/r/"),                         "primer"),
]


def _get_csp(uri: str) -> str:
    """Return the CSP policy string for a given request URI."""
    for pattern, policy_key in URI_RULES:
        if pattern.match(uri):
            return CSP_POLICIES[policy_key]
    return CSP_POLICIES["default"]


# ---------------------------------------------------------------------------
# Lambda@Edge handler — ORIGIN RESPONSE trigger
# ---------------------------------------------------------------------------

def handler(event, context):
    """
    CloudFront ORIGIN RESPONSE event.

    event['request']  — the original viewer request
    event['response'] — the origin response (we modify headers on this)
    """
    request = event["request"]
    response = event["response"]

    uri = request["uri"]

    # Normalise: strip trailing slash (except root)
    if uri != "/" and uri.endswith("/"):
        uri = uri.rstrip("/")

    csp = _get_csp(uri)

    # Set header (case-insensitive merge; Lambda@Edge lowercases keys)
    response["headers"]["content-security-policy"] = {
        "key": "Content-Security-Policy",
        "value": csp,
    }

    return response
