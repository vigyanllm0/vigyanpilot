import time
from flask import jsonify

RATE_LIMITS_GLOBAL = {}
RATE_LIMITS_HEALTH = {}
RATE_LIMITS_PAYMENTS = {}

def global_rate_limit_hook(request):
    if request.method == "OPTIONS":
        return None
        
    ip = request.remote_addr or request.headers.get("X-Forwarded-For", "unknown")
    if ',' in ip:
        ip = ip.split(',')[0].strip()
        
    now = time.time()
    
    # Health endpoint specific check (10 per minute)
    if request.path == "/health":
        if ip not in RATE_LIMITS_HEALTH:
            RATE_LIMITS_HEALTH[ip] = []
        RATE_LIMITS_HEALTH[ip] = [ts for ts in RATE_LIMITS_HEALTH[ip] if now - ts < 60]
        if len(RATE_LIMITS_HEALTH[ip]) >= 10:
            return jsonify({"error": "Health check rate limit exceeded. Max 10 requests per minute."}), 429
        RATE_LIMITS_HEALTH[ip].append(now)

    if request.path == "/api/payments/verify-payment":
        if ip not in RATE_LIMITS_PAYMENTS:
            RATE_LIMITS_PAYMENTS[ip] = []
        RATE_LIMITS_PAYMENTS[ip] = [ts for ts in RATE_LIMITS_PAYMENTS[ip] if now - ts < 60]
        if len(RATE_LIMITS_PAYMENTS[ip]) >= 5:
            return jsonify({"error": "Payment verification rate limit exceeded. Max 5 requests per minute."}), 429
        RATE_LIMITS_PAYMENTS[ip].append(now)

    # Global limit check (100 per minute)
    if ip not in RATE_LIMITS_GLOBAL:
        RATE_LIMITS_GLOBAL[ip] = []
    RATE_LIMITS_GLOBAL[ip] = [ts for ts in RATE_LIMITS_GLOBAL[ip] if now - ts < 60]
    if len(RATE_LIMITS_GLOBAL[ip]) >= 100:
        return jsonify({"error": "Global rate limit exceeded. Max 100 requests per minute."}), 429
    RATE_LIMITS_GLOBAL[ip].append(now)
    
    return None
