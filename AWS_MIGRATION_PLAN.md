# AWS Migration Plan — VigyanLLM Frontend

**Status:** In Progress — Parallel migration (Vercel stays live until AWS verified)
**Strategy:** Build on AWS → test via CloudFront domain → switch DNS only when working
**Vercel:** NO CHANGES — stays live at www.vigyanllm.in throughout

---

## Architecture

```
                    ┌─── Vercel (STAYS LIVE) ─── www.vigyanllm.in
                    │
Browser ────────────┤
                    │
                    └─── CloudFront (TESTING) ── dXXXXXXXXXX.cloudfront.net
                         ├── S3: Static files
                         └── ALB → EC2: API proxy
```

**After verification:** Switch DNS CNAME to CloudFront, then decommission Vercel.

---

## Phase 1: S3 Bucket (Parallel)

| Task | Command/Action |
|------|---------------|
| Create bucket | `aws s3 mb s3://vigyanllm-frontend --region ap-south-1` |
| Enable versioning | `aws s3api put-bucket-versioning --bucket vigyanllm-frontend --versioning-configuration Status=Enabled` |
| Block public access | `aws s3api put-public-access-block --bucket vigyanllm-frontend --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true` |
| Upload files | `aws s3 sync frontend/ s3://vigyanllm-frontend/ --delete` |
| Set cache headers | Per file type (fonts=1yr immutable, images=1d immutable, JS/CSS=1d stale-while-revalidate, HTML=5min) |

---

## Phase 2: SSL Certificate (ACM)

| Task | Details |
|------|---------|
| Request cert | ACM in `us-east-1` (required for CloudFront) |
| Domains | `www.vigyanllm.in` + `vigyanllm.in` |
| Validation | DNS validation via Route53 or manual CNAME |
| Wait for validation | ~5-30 minutes |

---

## Phase 3: CloudFront Distribution

| Setting | Value |
|---------|-------|
| Origin 1 | S3 bucket `vigyanllm-frontend` (OAI for private bucket) |
| Origin 2 | ALB for API proxy (see Phase 4) |
| Alternate domain names | `www.vigyanllm.in`, `vigyanllm.in` |
| SSL certificate | ACM cert from Phase 2 |
| Default root object | `index.html` |
| Custom error pages | 404 → `/404.html`, 403 → `/404.html` |
| Price class | All Edge Locations (or `PriceClass_200` for India+Asia+Europe) |

---

## Phase 4: ALB for API Proxy

```
ALB Listener (443 HTTPS):
  Rule 1: Path = /api/v1/cms/* → Target Group: EC2:8001
  Rule 2: Path = /api/* → Target Group: EC2:80 (→ Gunicorn 11436)
  Rule 3: Path = /health → Target Group: EC2:80
  Rule 4: Default → Forward to S3 (via CloudFront)
```

**Note:** EC2 already has nginx on port 80. ALB can target nginx directly (port 80).

---

## Phase 5: CloudFront Functions

### 5a. Redirects + Rewrites (viewer request)
- Domain canonicalization: `vigyanllm.in` → `www.vigyanllm.in`
- `.html` strip: `/primer.html` → `/primer`
- Clean URL rewrite: `/primer` → `/primer.html`
- Content redirects: ~20 glossary consolidations, blog slug changes, legacy URLs
- Referral redirect: `/r/:code` → `/primer.html?ref=:code`

### 5b. Bot Blocking (viewer request)
- Block: AhrefsBot, SemrushBot, MJ12bot, DotBot, Majestic, Rogerbot, Xovi
- Return 403 for matching User-Agent strings

---

## Phase 6: Lambda@Edge (CSP Headers)

Set Content-Security-Policy header based on request URI:
- **Default:** Full CSP (Google, Razorpay, GTM, Clarity, 3Dmol)
- **primer.html:** Adds YouTube embeds
- **docking.html:** Adds 3Dmol.org
- **index.html:** Adds Tailwind CDN, cdnjs
- **blog/**: Strict CSP (no Razorpay, no Google accounts)
- **admin-security.html**: Strictest CSP

---

## Phase 7: Cache Policies

| Asset | Cache-Control | Policy |
|-------|--------------|--------|
| Fonts | `max-age=31536000, immutable` | CachingOptimized |
| Images | `max-age=86400, immutable` | CachingOptimized |
| JS/CSS | `max-age=86400, stale-while-revalidate=604800` | Custom |
| HTML | `max-age=300, stale-while-revalidate=600` | Custom |
| Sitemap/RSS | `max-age=3600` | Custom |
| sw.js | `max-age=0, must-revalidate` | Custom |

---

## Phase 8: Testing (via CloudFront domain)

Test ALL of these on `dXXXXXXXXXX.cloudfront.net` BEFORE switching DNS:
- [ ] All 522 HTML pages load
- [ ] All CSS/JS/images load
- [ ] Clean URLs work (`/primer`, `/blast`, `/developer`)
- [ ] `.html` redirect works (`/primer.html` → `/primer`)
- [ ] API proxy works (`/api/primer/auto-design`)
- [ ] CMS proxy works (`/api/v1/cms/*`)
- [ ] Health endpoint works (`/health`)
- [ ] Login/Register works (cookie flow)
- [ ] Google OAuth works
- [ ] Razorpay payment works
- [ ] Bot blocking returns 403
- [ ] CSP headers present
- [ ] Cache headers correct
- [ ] Domain redirect works (`vigyanllm.in` → `www.vigyanllm.in`)
- [ ] Sitemap generates correctly
- [ ] Analytics fire (GTM/GA4/Clarity)
- [ ] Mobile responsive

---

## Phase 9: DNS Cutover (Final)

**ONLY when Phase 8 passes:**
1. Change `www.vigyanllm.in` CNAME from `cname.vercel-dns.com` to `dXXXXXXXXXX.cloudfront.net`
2. Change `vigyanllm.in` A record to CloudFront alias
3. Wait for DNS propagation (~5-15 min)
4. Verify live site works
5. Keep Vercel project paused (not deleted) for 7 days as rollback

---

## Cost Estimate (Monthly)

| Service | Cost |
|---------|------|
| S3 storage (115MB) | ~$0.03 |
| S3 requests (100K/mo) | ~$0.04 |
| CloudFront (100GB transfer/mo) | ~$8.50 |
| ALB (already exists) | $0 |
| Lambda@Edge (1M invocations/mo) | ~$0.60 |
| ACM certificate | Free |
| **Total** | **~$9/month** |

Vercel Pro: $20/month → **Savings: ~$11/month**

---

## Rollback Plan

If anything breaks on CloudFront:
1. DNS CNAME back to `cname.vercel-dns.com`
2. Vercel is still live and serving
3. Debug CloudFront issues
4. Re-switch when fixed

**Zero downtime guaranteed** — Vercel stays running throughout.
