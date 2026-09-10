"""Structured JSON logging configuration for VigyanLLM."""
import logging
import json
import re
import sys
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    """JSON log formatter with PII masking."""
    _EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    def format(self, record):
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        # Add exception info
        if record.exc_info and record.exc_info[0]:
            log_entry['exception'] = self.formatException(record.exc_info)
        # PII mask
        log_entry['message'] = self._EMAIL_RE.sub('[EMAIL]', log_entry['message'])
        return json.dumps(log_entry, default=str)

def setup_structured_logging(app=None):
    """Configure structured JSON logging for the application."""
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('gunicorn.error').setLevel(logging.INFO)
