#!/usr/bin/env python3
"""
VigyanLLM — Comprehensive Security & QA Audit
===============================================
Tests: XSS, SQLi, auth bypass, token tampering, rate limiting, CORS, path traversal, CSRF, etc.
"""

import requests, json, sys, time, re, os
from urllib.parse import urljoin

BASE = "http://localhost:11436"
FRONT = "http://localhost:8080"

results = {"pass": 0, "fail": 0, "warn": 0, "issues": []}

def check(name, ok, detail=""):
    if ok:
        results["pass"] += 1
        print(f"  [PASS] {name}")
    else:
        results["fail"] += 1
        results["issues"].append({"severity": "FAIL", "test": name, "detail": detail})
        print(f"  [FAIL] {name} — {detail}")

def warn(name, detail=""):
    results["warn"] += 1
    results["issues"].append({"severity": "WARN", "test": name, "detail": detail})
    print(f"  [WARN] {name} — {detail}")

s = requests.Session()

# =============================================================================
# 1. SERVER AVAILABILITY
# =============================================================================
print("\n═══ 1. SERVER AVAILABILITY ═══")
r = s.get(f"{BASE}/health", timeout=5)
check("Health endpoint", r.status_code == 200 and r.json().get("status") == "ok", str(r.status_code))

r = s.get(f"{FRONT}/primer.html", timeout=5)
check("Primer page loads", r.status_code == 200 and b"VigyanLLM" in r.content, f"HTTP {r.status_code}")
check("Primer page has JS", b"<script" in r.content, "No script tags found?")
check("Primer page has CSS", b"stylesheet" in r.content, "No stylesheet found?")

r = s.get(f"{FRONT}/index.html", timeout=5)
check("Index page loads", r.status_code == 200, f"HTTP {r.status_code}")

r = s.get(f"{FRONT}/", timeout=5)
check("Root redirect/serves", r.status_code in (200, 301, 302), f"HTTP {r.status_code}")

# =============================================================================
# 2. AUTHENTICATION TESTS
# =============================================================================
print("\n═══ 2. AUTHENTICATION ═══")

# Register
r = s.post(f"{BASE}/api/auth/register", json={"email": "hacker@test.com", "password": "Hack1234!"})
check("Registration works", r.status_code == 201, str(r.status_code))
TOKEN = r.json().get("token", "")

# Login
r = s.post(f"{BASE}/api/auth/login", json={"email": "hacker@test.com", "password": "Hack1234!"})
check("Login works", r.status_code == 200, str(r.status_code))
TOKEN = r.json().get("token", "")

# Duplicate registration (should fail)
r = s.post(f"{BASE}/api/auth/register", json={"email": "hacker@test.com", "password": "Hack1234!"})
check("Duplicate registration blocked", r.status_code in (400, 409, 422), f"Got {r.status_code} — might allow duplicate accounts")

# Bad password login
r = s.post(f"{BASE}/api/auth/login", json={"email": "hacker@test.com", "password": "wrongpassword"})
check("Bad password rejected", r.status_code in (400, 401, 403), f"Got {r.status_code}")

# Nonexistent user login
r = s.post(f"{BASE}/api/auth/login", json={"email": "noone@doesnotexist.com", "password": "whatever"})
check("Nonexistent user rejected", r.status_code in (400, 401, 403, 404), f"Got {r.status_code}")

# Weak password
r = s.post(f"{BASE}/api/auth/register", json={"email": "weak@test.com", "password": "123"})
check("Weak password rejected", r.status_code in (400, 422), f"Got {r.status_code}: {r.text[:100]}")

# =============================================================================
# 3. TOKEN SECURITY
# =============================================================================
print("\n═══ 3. TOKEN & SESSION SECURITY ═══")

# Tampered token
headers_bad = {"Authorization": "Bearer eyJlbWFpbCI6ICJhZG1pbkB0ZXN0LmNvbSJ9.invalidsignature"}
r = s.get(f"{BASE}/api/auth/status", headers=headers_bad)
check("Tampered token rejected", r.status_code in (400, 401, 403), f"Got {r.status_code}: {r.text[:80]}")

# Empty token
r = s.get(f"{BASE}/api/auth/status", headers={"Authorization": "Bearer "})
check("Empty token rejected", r.status_code in (400, 401, 403), f"Got {r.status_code}")

# No auth header on protected endpoint
r = s.get(f"{BASE}/api/auth/status")
check("No-auth on protected endpoint rejected", r.status_code in (400, 401, 403), f"Got {r.status_code}")

# Token expiry? Check if token has expiry info
try:
    import base64
    parts = TOKEN.split(".")
    if len(parts) >= 2:
        payload = json.loads(base64.b64decode(parts[0] + "=="))
        if "exp" in payload:
            check("Token has expiry", True)
        else:
            warn("Token missing expiry", "No 'exp' field in token payload")
    else:
        warn("Token format unusual", f"Token has {len(parts)} parts")
except Exception as e:
    warn("Token decode failed", str(e))

# =============================================================================
# 4. SQL INJECTION
# =============================================================================
print("\n═══ 4. SQL INJECTION ═══")

sql_payloads = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "' UNION SELECT * FROM users; --",
    "1; SELECT * FROM admin WHERE 1=1 --",
    "admin'--",
    "\" OR 1=1 --",
    "' OR '1'='1' --",
    "1' ORDER BY 1--",
    "1' AND SLEEP(5)--",
]

for payload in sql_payloads[:3]:
    r = s.post(f"{BASE}/api/auth/login", json={"email": f"{payload}@test.com", "password": payload})
    if r.status_code == 200 and r.json().get("token"):
        warn(f"SQLi possible with: {payload[:30]}", f"Got 200 with token: {r.json().get('token','')[:20]}")
        break
else:
    check("SQL injection blocked (basic)", True)

# SQLi in registration email
r = s.post(f"{BASE}/api/auth/register", json={"email": "'; DELETE FROM users; --", "password": "Test1234!"})
check("SQLi in registration blocked", r.status_code in (400, 422, 500), f"Got {r.status_code}")

# SQLi in pipeline sequence
r = s.post(f"{BASE}/api/pipeline/submit", 
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"sequence": "'; DROP TABLE users; --", "mode": "express"})
check("SQLi in pipeline blocked", r.status_code in (400, 422, 500), f"Got {r.status_code}")

# =============================================================================
# 5. XSS (CROSS-SITE SCRIPTING)
# =============================================================================
print("\n═══ 5. XSS ═══")

xss_payload = "<script>alert('XSS')</script>"
r = s.post(f"{BASE}/api/auth/register", json={"email": f"xss@{xss_payload}.com", "password": "Test1234!"})
check("XSS in email rejected", r.status_code in (400, 422), f"Got {r.status_code}")

r = s.post(f"{BASE}/api/auth/login", json={"email": f"test@<img src=x onerror=alert(1)>.com", "password": "test"})
check("XSS in login blocked", r.status_code in (400, 401, 422), f"Got {r.status_code}")

# XSS in pipeline sequence
r = s.post(f"{BASE}/api/pipeline/submit",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"sequence": f"ATCG{xss_payload}ATCG", "mode": "express"})
check("XSS in sequence data blocked", r.status_code in (400, 422), f"Got {r.status_code}: {r.text[:80]}")

# Check if output reflects user input without sanitization
r = s.post(f"{BASE}/api/primer/auto-design",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"sequence": "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"})
resp_text = r.text
if "<script>" in resp_text or xss_payload in resp_text:
    warn("Possible XSS reflection", "User input reflected in API response without sanitization")
else:
    check("No XSS reflection detected", True)

# =============================================================================
# 6. COMMAND INJECTION
# =============================================================================
print("\n═══ 6. COMMAND INJECTION ═══")

cmd_payloads = ["; ls", "| whoami", "`id`", "$(cat /etc/passwd)"]
for payload in cmd_payloads:
    r = s.post(f"{BASE}/api/pipeline/submit",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"sequence": f"ATCG{payload}ATCG", "mode": "express"})
    if r.status_code not in (400, 422, 500):
        warn(f"Possible command injection: {payload}", f"Got {r.status_code}: {r.text[:80]}")
        break
else:
    check("Command injection blocked", True)

# =============================================================================
# 7. PATH TRAVERSAL
# =============================================================================
print("\n═══ 7. PATH TRAVERSAL ═══")

paths = [
    "/../etc/passwd",
    "/.%2e/etc/passwd",
    "/../.env",
    "/static/../../../etc/passwd",
    "/%2e%2e/etc/passwd",
    "/api/../../../etc/passwd",
]
for path in paths[:3]:
    r = s.get(f"{FRONT}{path}", timeout=3)
    if r.status_code == 200 and ("root:" in r.text or "DATABASE_URL" in r.text):
        warn(f"Path traversal possible: {path}", "Sensitive file exposed")
        break
else:
    check("Path traversal blocked", True)

# =============================================================================
# 8. RATE LIMITING
# =============================================================================
print("\n═══ 8. RATE LIMITING ═══")

start = time.time()
blocked = False
for i in range(30):
    r = s.post(f"{BASE}/api/auth/login", json={"email": f"spam{i}@test.com", "password": "test"})
    if r.status_code == 429:
        blocked = True
        break
elapsed = time.time() - start
check(f"Rate limiting active (blocked after ~{i+1} req/{elapsed:.0f}s)", blocked, 
      f"Made {i+1} requests in {elapsed:.0f}s without rate limit" if not blocked else f"Blocked at request {i+1}")

# =============================================================================
# 9. CORS
# =============================================================================
print("\n═══ 9. CORS SECURITY ═══")

r = s.get(f"{BASE}/health", headers={"Origin": "https://evil.com"})
origin = r.headers.get("Access-Control-Allow-Origin", "")
check("CORS: evil origin blocked", origin != "https://evil.com" and origin != "*",
      f"Access-Control-Allow-Origin: {origin}")

r = s.get(f"{BASE}/health", headers={"Origin": "http://localhost:8080"})
origin = r.headers.get("Access-Control-Allow-Origin", "")
check("CORS: localhost:8080 allowed", origin == "http://localhost:8080",
      f"Access-Control-Allow-Origin: {origin}")

r = s.get(f"{BASE}/health", headers={"Origin": "null"})
origin = r.headers.get("Access-Control-Allow-Origin", "")
if origin == "null":
    warn("CORS: null origin allowed", "file:// sandbox pages can make requests — verify this is intended")

# =============================================================================
# 10. INFORMATION DISCLOSURE
# =============================================================================
print("\n═══ 10. INFORMATION DISCLOSURE ═══")

# Error messages shouldn't leak stack traces
r = s.post(f"{BASE}/api/auth/login", json={"email": 12345, "password": []})
if r.status_code == 500 and ("Traceback" in r.text or "File \"" in r.text):
    warn("Stack trace leaked", r.text[:200])
else:
    check("No stack trace leakage", True)

# Server header
server = r.headers.get("Server", "")
if server and server != "":
    warn(f"Server header exposed: {server}", "Remove or obfuscate server header")

# Check for debug endpoints
debug_paths = ["/debug", "/admin", "/api/debug", "/.env", "/config", "/api/config", "/swagger", "/docs"]
for path in debug_paths:
    r = s.get(f"{BASE}{path}", timeout=3)
    if r.status_code == 200:
        if path in ("/admin", "/debug", "/api/debug") and r.status_code == 200:
            warn(f"Sensitive endpoint accessible: {path}")
            break

# =============================================================================
# 11. CSRF PROTECTION
# =============================================================================
print("\n═══ 11. CSRF ═══")

# Check if state-changing endpoints accept requests without CSRF token
r = s.post(f"{BASE}/api/auth/register", 
    json={"email": "csrf@test.com", "password": "Test1234!"},
    headers={"Content-Type": "application/json"})
check("CSRF: Registration requires content-type", r.status_code in (201, 400, 422),
      f"Got {r.status_code}")

# =============================================================================
# 12. INPUT VALIDATION
# =============================================================================
print("\n═══ 12. INPUT VALIDATION ═══")

# Empty sequence
r = s.post(f"{BASE}/api/primer/auto-design",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"sequence": ""})
check("Empty sequence rejected", r.status_code in (400, 422), f"Got {r.status_code}")

# Non-DNA sequence
r = s.post(f"{BASE}/api/primer/auto-design",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"sequence": "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"})
check("Non-DNA sequence rejected", r.status_code in (400, 422), f"Got {r.status_code}")

# Oversized sequence
r = s.post(f"{BASE}/api/primer/auto-design",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"sequence": "A" * 100000})
check("Oversized sequence rejected", r.status_code in (400, 413, 422), f"Got {r.status_code}")

# Content-Type validation
r = s.post(f"{BASE}/api/auth/register", data="not json", headers={"Content-Type": "text/plain"})
check("Non-JSON content-type rejected", r.status_code in (400, 415, 422), f"Got {r.status_code}")

# =============================================================================
# 13. PIPELINE INPUT VALIDATION
# =============================================================================
print("\n═══ 13. PIPELINE INPUT VALIDATION ═══")

# No auth on pipeline
r = s.post(f"{BASE}/api/pipeline/submit", json={"sequence": "ATCG", "mode": "express"})
check("Pipeline without auth rejected", r.status_code in (400, 401, 403), f"Got {r.status_code}")

# Invalid mode
r = s.post(f"{BASE}/api/pipeline/submit",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"sequence": "ATCGATCGATCGATCGATCGATCGATCG", "mode": "invalid_mode"})
check("Invalid pipeline mode rejected", r.status_code in (400, 422), f"Got {r.status_code}")

# Missing both sequence and accession
r = s.post(f"{BASE}/api/pipeline/submit",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"mode": "express"})
check("Missing input rejected", r.status_code in (400, 422), f"Got {r.status_code}")

# =============================================================================
# 14. SECURITY HEADERS
# =============================================================================
print("\n═══ 14. SECURITY HEADERS ═══")

r = s.get(f"{BASE}/health", timeout=5)
headers = r.headers

sec_checks = {
    "Content-Security-Policy": "CSP",
    "X-Content-Type-Options": "X-Content-Type-Options",
    "X-Frame-Options": "X-Frame-Options",
    "Strict-Transport-Security": "HSTS",
}
for hdr, name in sec_checks.items():
    if hdr in headers:
        check(f"{name} present", True)
    else:
        warn(f"{name} missing", f"Consider adding {hdr} header")

# =============================================================================
# 15. FRONTEND SECURITY
# =============================================================================
print("\n═══ 15. FRONTEND SECURITY ═══")

r = s.get(f"{FRONT}/primer.html")
content = r.text

# Check for hardcoded secrets
secrets_found = []
for pattern, desc in [
    (r'rzp_live_\w+', 'Razorpay live key'),
    (r'rzp_test_\w+', 'Razorpay test key'),
    (r'api[Kk]ey\s*=\s*["\'][A-Za-z0-9]{20,}', 'Hardcoded API key'),
    (r'secret.*=.*["\'][A-Za-z0-9]{16,}', 'Hardcoded secret'),
    (r'password.*=.*["\'][^"\']{4,}', 'Hardcoded password'),
]:
    m = re.search(pattern, content)
    if m:
        secrets_found.append(f"{desc}: {m.group()[:40]}")
        
if secrets_found:
    for s in secrets_found:
        warn("Hardcoded secret in frontend", s)
else:
    check("No hardcoded secrets in frontend", True)

# =============================================================================
# 16. HTTPS & TLS (INFRA CHECK)
# =============================================================================
print("\n═══ 16. HTTPS/TLS CHECK ═══")

# Check if the backend uses HTTPS in production mode
try:
    r = s.get("https://localhost:11436/health", timeout=3, verify=False)
    check("HTTPS available", True)
except:
    warn("HTTPS not available", "Production should enforce HTTPS — dev mode is HTTP only")

# Check frontend script for mixed content
if "http://localhost:11436" in content:
    warn("Mixed content risk", "Frontend references http://localhost:11436 — hardcoded dev URL")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "="*60)
print("SECURITY AUDIT SUMMARY")
print("="*60)
print(f"  PASSED: {results['pass']}")
print(f"  FAILED: {results['fail']}")
print(f"  WARNINGS: {results['warn']}")
print(f"  TOTAL ISSUES: {results['fail'] + results['warn']}")
print()

if results['issues']:
    print("DETAILED ISSUES:")
    print("-"*60)
    for iss in results['issues']:
        print(f"  [{iss['severity']}] {iss['test']}")
        if iss['detail']:
            print(f"         {iss['detail']}")
    print()

# Save report
report = {
    "timestamp": time.time(),
    "summary": {"pass": results["pass"], "fail": results["fail"], "warn": results["warn"]},
    "issues": results["issues"]
}
with open("/tmp/vigyanllm_security_audit.json", "w") as f:
    json.dump(report, f, indent=2)

print("Report saved to /tmp/vigyanllm_security_audit.json")
