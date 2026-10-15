"""Durable ring-buffer log of outbound mail (Brevo) send attempts.

Why: when Brevo rejects a send, the app used to swallow the provider error into
a generic "couldn't send" — invisible without SSHing the box or digging the
Brevo dashboard. This keeps the last N attempts (timestamp, purpose, recipient
domain only, HTTP status, error body) so an admin can read the real provider
status + body straight from the site.

Design:
  * File-backed (atomic tmp + os.replace) so all gunicorn workers on the box
    share one log — an in-memory buffer would be written by one worker and read
    by another. No DB migration needed.
  * Stores the recipient DOMAIN only (never the full address) and NEVER the API
    key. Error body is truncated.
  * record() never raises: a logging failure must never break an email send.
"""
import json
import os
import tempfile
import threading
import time

_LOCK = threading.Lock()
_MAX = 10


def _path() -> str:
    return os.environ.get("MAIL_LOG_PATH", "/var/tmp/vigyanllm_mail_log.json")


def _read() -> list:
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _domain(email: str) -> str:
    if not email:
        return "(none)"
    email = str(email)
    if "@" in email:
        return email.rsplit("@", 1)[1].lower()[:80]
    return "(no-at)"


def record(purpose, recipient_email, http_status=None, ok=False, error="", attempts=1):
    """Append one send outcome to the ring buffer. Never raises."""
    try:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "epoch": int(time.time()),
            "purpose": str(purpose)[:40],
            "recipient_domain": _domain(recipient_email),
            "http_status": http_status,
            "ok": bool(ok),
            "attempts": int(attempts),
            "error": str(error or "")[:500],
        }
        with _LOCK:
            rows = _read()
            rows.append(entry)
            rows = rows[-_MAX:]
            _atomic_write(rows)
        return entry
    except Exception:
        return None


def _atomic_write(rows) -> None:
    p = _path()
    d = os.path.dirname(p) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".maillog_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1, ensure_ascii=False)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


def recent(limit: int = _MAX) -> list:
    """Return the most recent entries, newest last. Never raises."""
    with _LOCK:
        try:
            return _read()[-int(limit):]
        except Exception:
            return []
