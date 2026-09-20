"""
VigyanLLM — Docking Monitoring & Health Check

Operational monitoring for the docking pipeline:
1. Health check endpoint (all services)
2. Job queue metrics (pending/running/complete/failed)
3. Resource usage (memory, disk, CPU)
4. Performance metrics (avg dock time, throughput)
5. Alert thresholds (queue depth, failure rate, latency)
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Alert Thresholds ─────────────────────────────────────────────────────────

ALERT_THRESHOLDS = {
    'queue_depth_warning': 20,
    'queue_depth_critical': 50,
    'failure_rate_warning': 0.10,   # 10%
    'failure_rate_critical': 0.25,  # 25%
    'avg_time_warning': 120,        # seconds
    'avg_time_critical': 300,       # seconds
    'disk_usage_warning': 0.80,     # 80%
    'disk_usage_critical': 0.95,    # 95%
    'memory_usage_warning': 0.80,
    'memory_usage_critical': 0.95,
}


@dataclass
class HealthStatus:
    """System health status."""
    status: str             # 'healthy', 'degraded', 'unhealthy'
    timestamp: str
    services: dict          # Service health checks
    metrics: dict           # Operational metrics
    alerts: list            # Active alerts
    uptime: float           # Seconds since module load


# Module load time
_module_load_time = time.time()


def check_docking_queue() -> dict:
    """Check docking queue status."""
    try:
        from primerforge.docking_queue import list_pending_jobs, list_running_jobs

        pending = list_pending_jobs()
        running = list_running_jobs()

        return {
            'status': 'ok',
            'pending': len(pending),
            'running': len(running),
            'pending_jobs': [j.get('job_id', '?') for j in pending[:5]],
            'running_jobs': [j.get('job_id', '?') for j in running[:5]],
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def check_file_system() -> dict:
    """Check file system health."""
    checks = {}

    # Check docking queue directories
    try:
        from primerforge.docking_queue import PENDING_DIR, RUNNING_DIR, COMPLETE_DIR, FAILED_DIR
        for name, path in [('pending', PENDING_DIR), ('running', RUNNING_DIR),
                           ('complete', COMPLETE_DIR), ('failed', FAILED_DIR)]:
            p = Path(path)
            if p.exists():
                count = len(list(p.glob('*.json')))
                checks[name] = {'status': 'ok', 'count': count, 'path': str(p)}
            else:
                checks[name] = {'status': 'missing', 'path': str(p)}
    except Exception as e:
        checks['error'] = str(e)

    # Check disk usage
    try:
        stat = os.statvfs('/')
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used_pct = 1 - (free / total)
        checks['disk'] = {
            'status': 'ok',
            'total_gb': round(total / 1073741824, 1),
            'free_gb': round(free / 1073741824, 1),
            'used_percent': round(used_pct * 100, 1),
        }
    except Exception as e:
        checks['disk'] = {'status': 'error', 'error': str(e)}

    return checks


def check_memory() -> dict:
    """Check memory usage."""
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # Max RSS in bytes (macOS: bytes, Linux: KB)
        import sys
        if sys.platform == 'darwin':
            rss_mb = usage.ru_maxrss / 1048576
        else:
            rss_mb = usage.ru_maxrss / 1024

        return {
            'status': 'ok',
            'rss_mb': round(rss_mb, 1),
            'user_time': round(usage.ru_utime, 2),
            'system_time': round(usage.ru_stime, 2),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def check_recent_jobs() -> dict:
    """Check recent job completion stats."""
    try:
        from primerforge.docking_queue import COMPLETE_DIR, FAILED_DIR

        complete_path = Path(COMPLETE_DIR)
        failed_path = Path(FAILED_DIR)

        now = time.time()
        last_hour = now - 3600
        last_day = now - 86400

        completed_1h = 0
        completed_24h = 0
        failed_1h = 0
        failed_24h = 0
        total_times = []

        if complete_path.exists():
            for f in complete_path.glob('*.json'):
                try:
                    mtime = f.stat().st_mtime
                    if mtime > last_hour:
                        completed_1h += 1
                    if mtime > last_day:
                        completed_24h += 1
                        # Try to extract processing time
                        with open(f) as fh:
                            data = json.load(fh)
                            if 'processing_time' in data:
                                total_times.append(data['processing_time'])
                except Exception:
                    continue

        if failed_path.exists():
            for f in failed_path.glob('*.json'):
                mtime = f.stat().st_mtime
                if mtime > last_hour:
                    failed_1h += 1
                if mtime > last_day:
                    failed_24h += 1

        total_24h = completed_24h + failed_24h
        failure_rate = failed_24h / max(1, total_24h)
        avg_time = sum(total_times) / max(1, len(total_times))

        return {
            'status': 'ok',
            'completed_1h': completed_1h,
            'completed_24h': completed_24h,
            'failed_1h': failed_1h,
            'failed_24h': failed_24h,
            'failure_rate_24h': round(failure_rate, 3),
            'avg_processing_time': round(avg_time, 1),
            'throughput_24h': completed_24h,
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def check_esm_cache() -> dict:
    """Check ESMFold cache health."""
    try:
        from primerforge.pipelines.esm_cache import cache_stats
        stats = cache_stats()
        return {
            'status': 'ok',
            'entries': stats['entries'],
            'size_mb': stats['total_size_mb'],
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def generate_alerts(services: dict) -> list:
    """Generate alerts based on service status and thresholds."""
    alerts = []

    # Queue depth
    queue = services.get('queue', {})
    if queue.get('pending', 0) >= ALERT_THRESHOLDS['queue_depth_critical']:
        alerts.append({
            'severity': 'critical',
            'message': f"Queue depth critical: {queue['pending']} pending jobs",
            'component': 'queue',
        })
    elif queue.get('pending', 0) >= ALERT_THRESHOLDS['queue_depth_warning']:
        alerts.append({
            'severity': 'warning',
            'message': f"Queue depth elevated: {queue['pending']} pending jobs",
            'component': 'queue',
        })

    # Failure rate
    jobs = services.get('recent_jobs', {})
    if jobs.get('failure_rate_24h', 0) >= ALERT_THRESHOLDS['failure_rate_critical']:
        alerts.append({
            'severity': 'critical',
            'message': f"High failure rate: {jobs['failure_rate_24h']*100:.1f}% (24h)",
            'component': 'jobs',
        })
    elif jobs.get('failure_rate_24h', 0) >= ALERT_THRESHOLDS['failure_rate_warning']:
        alerts.append({
            'severity': 'warning',
            'message': f"Elevated failure rate: {jobs['failure_rate_24h']*100:.1f}% (24h)",
            'component': 'jobs',
        })

    # Latency
    if jobs.get('avg_processing_time', 0) >= ALERT_THRESHOLDS['avg_time_critical']:
        alerts.append({
            'severity': 'critical',
            'message': f"High latency: {jobs['avg_processing_time']:.0f}s average",
            'component': 'performance',
        })

    # Disk
    disk = services.get('filesystem', {}).get('disk', {})
    if disk.get('used_percent', 0) >= ALERT_THRESHOLDS['disk_usage_critical']:
        alerts.append({
            'severity': 'critical',
            'message': f"Disk usage critical: {disk['used_percent']:.1f}%",
            'component': 'filesystem',
        })

    # Memory
    mem = services.get('memory', {})
    if mem.get('rss_mb', 0) > 2000:  # >2GB RSS
        alerts.append({
            'severity': 'warning',
            'message': f"High memory usage: {mem['rss_mb']:.0f} MB RSS",
            'component': 'memory',
        })

    # Service errors
    for name, check in services.items():
        if isinstance(check, dict) and check.get('status') == 'error':
            alerts.append({
                'severity': 'warning',
                'message': f"Service error in {name}: {check.get('error', 'unknown')}",
                'component': name,
            })

    return alerts


def health_check() -> HealthStatus:
    """
    Run comprehensive health check.

    Returns:
        HealthStatus with all service checks and alerts
    """
    services = {
        'queue': check_docking_queue(),
        'filesystem': check_file_system(),
        'memory': check_memory(),
        'recent_jobs': check_recent_jobs(),
        'esm_cache': check_esm_cache(),
    }

    alerts = generate_alerts(services)

    # Determine overall status
    has_critical = any(a['severity'] == 'critical' for a in alerts)
    has_warning = any(a['severity'] == 'warning' for a in alerts)
    has_error = any(
        isinstance(v, dict) and v.get('status') == 'error'
        for v in services.values()
    )

    if has_critical or has_error:
        status = 'unhealthy'
    elif has_warning:
        status = 'degraded'
    else:
        status = 'healthy'

    return HealthStatus(
        status=status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=services,
        metrics={
            'queue_depth': services.get('queue', {}).get('pending', 0),
            'running_jobs': services.get('queue', {}).get('running', 0),
            'completed_24h': services.get('recent_jobs', {}).get('completed_24h', 0),
            'failure_rate': services.get('recent_jobs', {}).get('failure_rate_24h', 0),
            'avg_processing_time': services.get('recent_jobs', {}).get('avg_processing_time', 0),
            'rss_mb': services.get('memory', {}).get('rss_mb', 0),
        },
        alerts=alerts,
        uptime=round(time.time() - _module_load_time, 1),
    )


def health_to_dict(status: HealthStatus) -> dict:
    """Convert to JSON-serializable dict."""
    return {
        'status': status.status,
        'timestamp': status.timestamp,
        'uptime': status.uptime,
        'services': status.services,
        'metrics': status.metrics,
        'alerts': status.alerts,
        'alert_count': {
            'critical': sum(1 for a in status.alerts if a['severity'] == 'critical'),
            'warning': sum(1 for a in status.alerts if a['severity'] == 'warning'),
        },
    }
