#!/usr/bin/env python3
"""
VigyanLLM — Screening Worker subprocess.

Thin entry point spawned by the queue (or API) to run a virtual screening
campaign.  Imports only pipeline modules (no Flask/auth) to keep the address
space small.  Acquires 1 CPU slot, runs the campaign, releases the slot.

Usage:
    python3 screening_worker.py --campaign <campaign_id>
    echo '{"campaign_id": "..."}' | python3 screening_worker.py
"""

import asyncio
import json
import logging
import os
import sys
import time

# Ensure project root is on sys.path BEFORE any primerforge import.
# gunicorn runs wsgi:app, which bootstraps its own sys.path, but this script
# is spawned as `python primerforge/screening_worker.py --campaign <id>` with
# the parent's env — and prod's venv does NOT have primerforge pip-installed.
# Without this line the worker dies on `import primerforge` and, because the
# error handler below needs the very same import, the campaign would be
# stranded at status=pending forever (observed on prod 2026-10-11).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("screening_worker")


def _queue_base() -> str:
    return os.environ.get(
        "DOCKING_QUEUE_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docking_queue"),
    )


def _mark_failed_raw(campaign_id: str, message: str) -> bool:
    """Record status=failed with stdlib only (no primerforge import).

    Returns True when the write landed. Used when the import chain itself is
    what broke, so the campaign still reaches a terminal state the UI can
    render (and the user can resume) instead of sitting at 'pending' forever.
    """
    if not campaign_id or not campaign_id.replace("-", "").isalnum() or len(campaign_id) > 64:
        return False
    path = os.path.join(_queue_base(), "screen", campaign_id, "campaign.json")
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False
    if data.get("status") in ("completed", "cancelled", "failed"):
        return True  # already terminal — nothing to write, don't touch it
    data["status"] = "failed"
    data.setdefault("progress", {}).update(
        {"stage": "failed", "message": message[:300]})
    data["updated_at"] = time.time()
    try:
        tmp = f"{path}.tmp{os.getpid()}"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=None, separators=(",", ":"))
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--campaign":
        campaign_id = sys.argv[2]
    else:
        try:
            data = json.loads(sys.stdin.read())
            campaign_id = data["campaign_id"]
        except (ValueError, KeyError):
            print(json.dumps({"error": "No campaign_id provided"}))
            sys.exit(1)

    logger.info("Screening worker started for campaign %s (pid %d)", campaign_id, os.getpid())

    # Acquire 1 CPU slot (patient — wait up to 120s for an interactive job
    # to finish; allow=1 means we proceed with 1 core if 2 aren't free).
    lease = None
    try:
        from primerforge.docking_queue import acquire_slots
        lease = acquire_slots(1, wait_s=120.0, allow=1)
        lanes = max(1, lease.slots) if lease else 1
    except Exception as exc:
        logger.warning("Slot acquisition failed (%s) — using all cores", exc)
        lanes = max(1, (os.cpu_count() or 1))

    # Update campaign config with actual lanes
    try:
        from primerforge.pipelines.virtual_screening import get_campaign, update_campaign
        c = get_campaign(campaign_id)
        if c:
            cfg = c.get("config", {})
            cfg["lanes"] = lanes
            update_campaign(campaign_id, {"config": cfg})
    except Exception:
        pass

    logger.info("Running campaign %s with %d lanes", campaign_id, lanes)

    # Progress callback: update campaign.json (throttled to ~2/s by the
    # engine's own atomic write path).
    _last_progress = {"t": 0.0}

    async def _progress_cb(stage, message, metadata=None):
        now = time.time()
        if now - _last_progress["t"] < 0.5:
            return
        _last_progress["t"] = now
        # Progress is already written by the engine's _report(); this callback
        # exists for future extensions (e.g., stdout streaming).

    try:
        from primerforge.pipelines.virtual_screening import run_campaign
        result = asyncio.run(run_campaign(campaign_id, progress_callback=_progress_cb))
        status = result.get("status", "unknown")
        logger.info("Campaign %s finished: status=%s", campaign_id, status)
    except Exception as exc:
        logger.error("Campaign %s crashed: %s", campaign_id, exc, exc_info=True)
        # Mark as failed if the engine didn't already. The import may be the
        # very thing that failed, so fall back to a raw file write — the
        # campaign must never be left stranded at status=pending (that is what
        # made prod campaign 51f38dcc73b6483e spin forever on 2026-10-11).
        if not _mark_failed_raw(campaign_id, str(exc)):
            try:
                from primerforge.pipelines.virtual_screening import update_campaign
                update_campaign(campaign_id, {
                    "status": "failed",
                    "progress": {"stage": "failed", "message": str(exc)[:300]},
                })
            except Exception:
                logger.error("Could not record failure for %s", campaign_id)
    finally:
        if lease:
            lease.release()

    logger.info("Screening worker exiting for campaign %s", campaign_id)


if __name__ == "__main__":
    main()
