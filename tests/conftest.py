"""Collection-time environment pins (issue #ENV-ORDER).

primerforge.auth raises RuntimeError at import unless PRIMERFORGE_ADMIN_EMAIL
and PRIMERFORGE_ADMIN_PASSWORD are set, and primerforge.pg_auth raises unless
PRIMERFORGE_SECRET is set. The suite historically passed only because
tests/test_verification_fix.py hard-sets all of them at module import time —
an import-order accident (collection imports every module before any test
runs) that made every isolated file run fail with the env raises.

pytest imports conftest before any test module, so these setdefault pins make
isolated runs deterministic. setdefault never overrides real CI values.

DATABASE_URL is deliberately NOT pinned here: tests select their DB mode
themselves (integration fixtures/monkeypatch force SQLite), mode is read per
create_app() call (primer_server.py:USE_POSTGRES), and test_verification_fix.py
still hard-sets its collection-time dummy PG URL for source-level checks —
changing that would alter full-suite behavior for unrelated modules.

PRIMERFORGE_DB is pinned to a fresh per-invocation temp file (same pattern as
the per-file tmp_path fixtures, but latched before ANY primerforge import, so
it is deterministic instead of import-order luck). Without it, SQLite-mode
tests share the repo-root primerforge.db dev artifact, whose anon_daily_usage
counter (limit 1/day per IP|UA fingerprint) persists across local runs — a
same-day second pytest run then 402s the anon auto-design tests. CI never has
that file (fresh checkout), so this only makes local runs match CI.
"""
import os
import tempfile

os.environ.setdefault("PRIMERFORGE_SECRET", "test-suite-secret-0123456789abcdef")
os.environ.setdefault("PRIMERFORGE_ADMIN_EMAIL", "admin@test.com")
os.environ.setdefault("PRIMERFORGE_ADMIN_PASSWORD", "TestSuite!12345")

_TEST_DB = os.path.join(tempfile.gettempdir(), f"primerforge-pytest-{os.getpid()}.db")
for _suffix in ("", "-wal", "-shm"):
    try:
        os.unlink(_TEST_DB + _suffix)
    except FileNotFoundError:
        pass
os.environ.setdefault("PRIMERFORGE_DB", _TEST_DB)
