"""
Gunicorn configuration for VigyanLLM
======================================
"""
import multiprocessing

bind = "0.0.0.0:11436"
workers = multiprocessing.cpu_count()  # auto-detect cores; 4 on EC2 t3.medium
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
