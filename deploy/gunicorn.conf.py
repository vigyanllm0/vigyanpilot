"""
Gunicorn configuration for VigyanLLM
======================================
"""
import multiprocessing

bind = "0.0.0.0:5000"
workers = 1
timeout = 120
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
capture_output = True
accesslog = "/var/log/vigyan/access.log"
errorlog = "/var/log/vigyan/error.log"
loglevel = "info"


def post_fork(server, worker):
    pass
