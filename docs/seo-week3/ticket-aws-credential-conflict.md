# TICKET-AWS-CRED — AWS credential conflict: Bedrock key shadows vigyanllm-deploy

- **Priority:** P1 (operational risk — any deploy from this machine 403s or,
  worse, an operator improvises without the identity gate)
- **Owner:** dev team / infra
- **Raised:** 2026-11-05 (found during Sprint 1 deploy — the deploy itself
  succeeded after manually loading the correct key from CSV)
- **Status:** mitigated 2026-11-05 (profile restored + identity gate added);
  **target state DECIDED 2026-11-05: option (b) profile migration — deadline Nov 19**
  (Sprint 1 Day-14); interim = option (a): keep `.zshrc` exports, run
  `scripts/pre_s3_check.sh` before every S3 op

## What happened

On **2026-11-02** three things were overwritten with an **`amazon-bedrock_deploy-1`**
key (account `497862079867` — same account, **different IAM user**):

1. `~/.aws/credentials` — rewritten at 01:28; now contains only the Bedrock
   key under `[default]` (the old `vigyanllm-deploy` entry is gone).
2. `~/.zshrc` lines **76–77** — `export AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
   with the Bedrock key (file mtime 01:35 same night).
3. `~/Downloads/amazon-bedrock_deploy-1_accessKeys.csv` — the source CSV.

**Effect:** env credentials **shadow every AWS profile** in every new shell.
On 2026-11-05 every `aws s3`/`s3api` call failed:

```
403 Forbidden (HeadObject)
AccessDenied … user/amazon-bedrock_deploy-1 is not authorized … s3:ListBucket
```

while the correct key still exists at `~/Downloads/vigyanllm-deploy_accessKeys.csv`
(identity verified: `arn:aws:iam::497862079867:user/vigyanllm-deploy`,
can List/Head/Put the bucket + create CloudFront invalidations).

**Impact if not fixed:** the next operator hits the same 403 mid-deploy and
either fails silently, wastes an hour debugging, or — worst case — treats the
403 as "the bucket is gone" and reaches for a different credential path with
unknown permissions. CI deploys are **unaffected** (GH secrets hold the
original `vigyanllm-deploy` keys).

## Mitigation applied (2026-11-05)

1. **`[vigyanllm-deploy]` profile restored** in `~/.aws/credentials`
   (appended alongside `[default]`; file mode 600 preserved).
   Verified: `AWS_PROFILE=vigyanllm-deploy aws s3 ls s3://vigyanllm-frontend/`
   → listing OK, `uploads/` = 8/8.
2. **`scripts/pre_s3_check.sh`** — identity gate to run before any
   `aws s3` / `aws cloudfront` op. Resolves the identity that would *actually*
   be used (env first — because env shadows profiles), compares against
   `user/vigyanllm-deploy`, refuses on mismatch with the exact `env -u …`
   workaround. Exit 0/1.

## DECIDED 2026-11-05 — option (b), deadline Nov 19 (Sprint 1 Day-14)

**(b) Move Bedrock to a profile, clean `.zshrc`.** Rationale (owner): the `.zshrc` exports are
how this bug happened — every new shell inherits Bedrock credentials and shadows every profile;
the gate is a mitigation, not a cure (voluntary — only works if remembered); profiles are the
AWS-standard mechanism.

**Interim (now → Nov 19):** option (a) in effect — Bedrock stays in `.zshrc`, every vigyanllm
S3 deploy runs `bash scripts/pre_s3_check.sh` first. Sprint 1 measurement is not blocked.

**Migration checklist (due Nov 19):**

- [ ] Remove the Bedrock key exports from `~/.zshrc` (lines 76–77)
- [ ] Add a `[bedrock]` profile to `~/.aws/credentials`
- [ ] `aws sts get-caller-identity --profile bedrock` → returns the Bedrock identity
      (`arn:aws:iam::497862079867:user/amazon-bedrock_deploy-1`)
- [ ] `aws sts get-caller-identity --profile vigyanllm-deploy` → returns
      `arn:aws:iam::497862079867:user/vigyanllm-deploy`
- [ ] Open a NEW shell: `aws sts get-caller-identity` (no profile/env) returns the configured
      default (or nothing) — **never** a silent foreign identity
- [ ] `pre_s3_check.sh` exits 0 in the new shell without any `env -u` workaround

## Acceptance criteria

- [x] `[vigyanllm-deploy]` profile present and working (`aws s3 ls` OK)
- [x] `scripts/pre_s3_check.sh` exits 0 on correct identity, 1 on shadowed/wrong
- [x] Owner decision recorded — **option (b), deadline Nov 19** (see DECIDED section)
- [ ] **Nov 19 migration checklist complete** (`.zshrc` cleaned, `[bedrock]` profile,
      both identities verified, fresh-shell default clean, gate passes with no workaround)
- [x] Deploy checklist references `pre_s3_check.sh` as Step 0 (v3 banner ops gates + §10)

## Notes

- The 2026-11-05 Sprint 1 deploy used the CSV key directly (profile did not
  exist yet); object + invalidation + IndexNow all completed normally.
- `aws configure list-profiles` still shows only `default` in some shells —
  profile list caches are irrelevant; `AWS_PROFILE=vigyanllm-deploy` works.
- GH secrets `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (CI path) are the
  same `vigyanllm-deploy` user — CI unaffected by this incident.
