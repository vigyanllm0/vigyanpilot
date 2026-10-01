# HQ Propagation — Gurgaon → New Delhi in Search & AI

**Goal:** make Google, Bing, and AI assistants (AI Overview, ChatGPT, Perplexity, Gemini) show **New Delhi, Delhi, India** instead of Gurgaon.
**Why it's stale:** Google's index still holds the pre-10-01 copy of `/about` (it literally quotes "Headquarters: Gurgaon… Haryana GST" in the SERP), and AI Overview synthesizes that + third-party sources.

## Status board (updated 2026-10-02)

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 1 | Site copy → New Delhi (9 lines, 4 pages) | us | ✅ LIVE 10-01 (`5e87eb05`) |
| 2 | Sitemap `lastmod` bumps (about/sovereign-ai/index → 10-02, team/india → 10-01) | us | ✅ shipped 10-02 |
| 3 | `/about` Organization + FAQPage schema; homepage PostalAddress city/region; sovereign-ai address | us | ✅ shipped 10-02 |
| 4 | `llms.txt` at site root | us | ✅ shipped 10-02 |
| 5 | IndexNow key + `deploy/aws/indexnow_ping.sh` (run after each deploy) | us | ✅ shipped 10-02; first ping → **HTTP 202** (accepted) |
| 6 | **GSC: live-test + Request Indexing ×4** | **you** | ⬜ do today |
| 7 | **Bing Webmaster: verify + submit sitemap** | **you** | ⬜ this week |
| 8 | **LinkedIn company location → New Delhi** | **you** | ⬜ today (2 min) |
| 9 | **X/Twitter bio, Crunchbase location** | **you** | ⬜ this week |
| 10 | **Startup India / DPIIT profile → New Delhi** | **you** | ⬜ this week |
| 11 | **MCA/ROC registered-office change (INC-22)** via CA | **you** | ⬜ when paperwork ready |
| 12 | GitHub profile location | **you** (login as `vigyanllm`) | ⬜ 2 min — see §8–10 |
| 13 | Re-check: SERP + AI Overview + ChatGPT/Perplexity/Gemini | you+us | ⬜ 10-05 and 10-08/09 |

---

## 6. GSC — request indexing (2 minutes, do today)

1. Open <https://search.google.com/search-console> → select property **vigyanllm.in** (or www).
2. Top search bar → paste URL → **Enter** → "URL Inspection".
3. Click **TEST LIVE URL** — confirm it shows the new text ("New Delhi" / no "Gurgaon").
4. Click **REQUEST INDEXING**. Repeat for all 4:
   - `https://www.vigyanllm.in/about` ← **most important** (the Gurgaon snippet page)
   - `https://www.vigyanllm.in/about/sovereign-ai`
   - `https://www.vigyanllm.in/team`
   - `https://www.vigyanllm.in/primer-design-india`
5. Quota ≈ 10/day — 4 is fine. Then Sitemaps → `https://www.vigyanllm.in/sitemap.xml` → Submit (refreshes lastmod hints).

## 7. Bing Webmaster (this week — Bing feeds several AI products)

1. <https://www.bing.com/webmasters> → **Sign in** (Microsoft account).
2. **Add your site** → `https://www.vigyanllm.in` → verification: choose **Import from Google Search Console** (fastest — reuses GSC verification) or add the meta-tag option.
3. Left menu → **Sitemaps** → submit `https://www.vigyanllm.in/sitemap.xml`.
4. Done — Bing recrawl feeds Bing search + Copilot and IndexNow partners.

## 8–10. Off-site profiles (the layer AI answers weigh heavily)

| Platform | Where to edit | Set to |
|---|---|---|
| **LinkedIn** (biggest signal) | Company page → **Edit page** → **Location** (or Admin settings → Page info) | New Delhi, Delhi, India |
| **X / Twitter** | Profile → Edit → location field (bio too if it mentions Gurgaon) | New Delhi, India |
| **Crunchbase** | Organization profile → **Edit profile** → Location | New Delhi, Delhi, India |
| **Startup India / DPIIT** | dpiit.gov.in → startup recognition profile → registered/office address | New Delhi, Delhi, India |
| **GitHub** | github.com/**vigyanllm** → **Edit profile** (it's a *user* account, not an org; log in as `vigyanllm` — the site's sameAs points here; its location field is currently empty) | New Delhi, India |

## 11. MCA/ROC registered-office change (the authoritative record)

- File **Form INC-22** (change of registered office) with the ROC through your CA — after the AGM/annual-return cycle if applicable.
- Once filed, aggregators that business/AI sources trust (**Zauba Corp, Tofler, ClearTax, Ministry data**) update automatically over the following 2–6 weeks — this is the single strongest "official" signal for company-location questions.
- Until then, our own pages + LinkedIn + directories carry the New Delhi signal.

## 13. Monitoring

| Date | Check |
|---|---|
| **2026-10-05** | Google SERP `vigyanllm headquarters` — does the `/about` snippet flip? GSC: "URL is on Google" status for the 4 URLs? |
| **2026-10-08/09** | AI Overview re-check; ask ChatGPT, Perplexity, Gemini: "Where is VigyanLLM headquartered?"; Bing search. Log results in `docs/GEO_BASELINE.md` § HQ question baseline. |
| rolling | Re-run `bash deploy/aws/indexnow_ping.sh` after every frontend deploy (notifies Bing/Yandex/Seznam instantly). |

**Honest expectations:** Google snippet ~3–14 days after request-indexing. AI Overview ~1–3 weeks (faster if off-site items land early). ChatGPT/Perplexity = their own crawl cadence, weeks. Note: the September spam-update rollout finishes ~Oct 8 and may shuffle results meanwhile.
