"""REDIS_URL split: rate-limiter storage vs Celery dispatch gate.

The P0 audit found two coupled hazards:

1. `security._get_rate_limit_storage()` returned REDIS_URL unprobed — a
   configured-but-dead Redis only failed on flask-limiter's first request,
   500-ing every route. It now TCP-probes at startup and degrades to
   per-worker `memory://` with a warning (never crash, never request-time
   failure).

2. `pipeline_routes._celery_broker_available()` gated run_pipeline.delay()
   on REDIS_URL — so wiring REDIS_URL for the limiter would have handed every
   pipeline job to Celery with no worker running in production (job queued
   into a black hole, the fallback thread never used). Dispatch now reads a
   dedicated CELERY_BROKER_URL that stays unset by default: no broker, no
   dispatch — same ThreadPoolExecutor path as today.
"""

import os
import socket

import pytest


def _listening_addr():
    """A TCP endpoint that accepts connections (stands in for live Redis)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(8)
    return s, f"redis://127.0.0.1:{s.getsockname()[1]}/0"


def _closed_addr():
    """A port that refuses connections (stands in for a dead Redis)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    addr = s.getsockname()
    s.close()
    return f"redis://127.0.0.1:{addr[1]}/0"


@pytest.fixture
def security_mod():
    import primerforge.security as security

    return security


def test_limiter_stays_memory_when_unset(security_mod, monkeypatch):
    monkeypatch.setattr(security_mod, "REDIS_URL", "")
    assert security_mod._get_rate_limit_storage() == "memory://"


def test_limiter_uses_redis_when_reachable(security_mod, monkeypatch):
    srv, url = _listening_addr()
    try:
        monkeypatch.setattr(security_mod, "REDIS_URL", url)
        assert security_mod._get_rate_limit_storage() == url
    finally:
        srv.close()


def test_limiter_degrades_to_memory_when_dead(security_mod, monkeypatch):
    """The request-time-500 hazard: configured but unreachable."""
    monkeypatch.setattr(security_mod, "REDIS_URL", _closed_addr())
    assert security_mod._get_rate_limit_storage() == "memory://"


def test_limiter_probe_never_raises_on_garbage(security_mod, monkeypatch):
    for bad in ("not-a-url", "redis://", "http://example.com:99999/x", ""):
        monkeypatch.setattr(security_mod, "REDIS_URL", bad)
        result = security_mod._get_rate_limit_storage()
        assert result in {"memory://", bad}


def test_celery_gate_ignores_redis_url(monkeypatch):
    """THE stranding guard: reachable REDIS_URL must NOT enable dispatch.

    This is the production shape after this change: REDIS_URL set for the
    limiter, no CELERY_BROKER_URL, no Celery worker.
    """
    from primerforge.engine.pipeline_routes import _celery_broker_available

    srv, url = _listening_addr()
    try:
        monkeypatch.setenv("REDIS_URL", url)
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        assert _celery_broker_available() is False
    finally:
        srv.close()


def test_celery_gate_false_when_broker_dead(monkeypatch):
    from primerforge.engine.pipeline_routes import _celery_broker_available

    monkeypatch.setenv("CELERY_BROKER_URL", _closed_addr())
    assert _celery_broker_available() is False


def test_celery_gate_true_when_explicit_and_reachable(monkeypatch):
    from primerforge.engine.pipeline_routes import _celery_broker_available

    srv, url = _listening_addr()
    try:
        monkeypatch.setenv("CELERY_BROKER_URL", url)
        assert _celery_broker_available() is True
    finally:
        srv.close()


def test_celery_gate_false_on_non_redis_scheme(monkeypatch):
    from primerforge.engine.pipeline_routes import _celery_broker_available

    monkeypatch.setenv("CELERY_BROKER_URL", "amqp://localhost:5672//")
    assert _celery_broker_available() is False


def test_celery_app_prefers_explicit_broker_url(monkeypatch):
    """celery_app must read the same variable as the gate — otherwise a
    dispatch could fire against a broker the app didn't configure."""
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://127.0.0.1:6399/7")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    import importlib

    import primerforge.celery_app as ca

    importlib.reload(ca)
    try:
        assert ca.REDIS_URL == "redis://127.0.0.1:6399/7"
        assert ca.celery_app.conf.broker_url == "redis://127.0.0.1:6399/7"
    finally:
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        importlib.reload(ca)
