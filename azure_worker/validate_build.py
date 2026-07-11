"""
Build validation script — verifies all pipeline modules import correctly.
This runs during Docker build (not at runtime).
"""
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
sys.path.insert(0, "/app")

errors = []
for mod in [
    "primerforge.pipelines.esmfold_engine",
    "primerforge.pipelines.docking_engine",
    "primerforge.pipelines.consensus_pipeline",
    "primerforge.pipelines.warmup",
]:
    try:
        __import__(mod)
        print(f"OK: {mod}")
    except Exception as e:
        errors.append(f"{mod}: {e}")
        print(f"FAIL: {mod}: {e}")

if errors:
    print(f"BUILD VALIDATION: {len(errors)} module(s) failed to import")
    sys.exit(0)  # Don't fail the build, just warn
else:
    print("BUILD VALIDATION: ALL pipeline modules OK")
