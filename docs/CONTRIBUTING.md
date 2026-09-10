# Contributing to VigyanLLM

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Node.js 18+ (for frontend development)
- Git

## Setup

```bash
git clone https://github.com/<org>/vigyanpilot.git
cd vigyanpilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
```

For frontend development, no build step is needed — the site is static HTML.

## Branch Naming

| Prefix | Purpose |
|--------|---------|
| `feature/*` | New functionality |
| `fix/*` | Bug fixes |
| `chore/*` | Maintenance, deps, config |

## Pull Request Template

```markdown
## Description
<!-- What does this PR do? -->

## Changes
- 

## Testing done
- [ ] `ruff check primerforge/ backend/`
- [ ] `pytest tests/ -x --timeout=30`
- [ ] Manual testing (if UI change)

## Screenshots (if UI change)
```

## Code Style

- **Python**: enforced by `ruff`. Run `ruff check primerforge/ backend/` before pushing.
- No comments in code unless explicitly requested.
- Follow existing patterns — check neighboring files before introducing new conventions.

## Review Process

- 1 approval required before merge.
- CI (lint, test, security scan) must pass.
- Address all review comments before merging.

## Merge Strategy

Squash and merge. Keep commit messages concise and descriptive.
