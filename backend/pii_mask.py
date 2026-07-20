import logging
import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_REPLACE = "[EMAIL REDACTED]"

class PIIMaskFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _EMAIL_RE.sub(_REPLACE, record.msg)
        if record.args:
            record.args = tuple(
                _EMAIL_RE.sub(_REPLACE, str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        return True

def install_pii_mask() -> None:
    for handler in logging.root.handlers:
        handler.addFilter(PIIMaskFilter())
