"""
Pipeline Orchestrator v2
=========================
Runs the 22-step VigyanLLM biophysical primer/probe design pipeline sequentially.
Each step updates job status in the database, records its result,
and handles errors gracefully (soft failures incur penalty; hard failures abort).

Supports:
- Full mode: all 22 steps executed in Phase A–E order
- Express mode: only steps {1, 6, 7, 10, 19, 22} executed; others skipped
- Per-step timeout enforcement (default 120s)
- Phase-based step grouping (A–E)
"""

import time
import logging
import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Steps included in express mode (subset execution)
EXPRESS_STEPS: Set[int] = {1, 6, 7, 10, 19, 22}


@dataclass
class PipelineConfig:
    """Configuration for a pipeline execution run."""

    mode: str = "full"  # "full" | "express"
    step_timeout_seconds: int = 300
    total_steps: int = 22
    soft_failure_penalty: float = 10.0


@dataclass
class StepRegistration:
    """A registered pipeline step."""

    step_number: int
    step_name: str
    step_function: Callable[[Dict[str, Any]], Dict[str, Any]]
    hard_failure: bool = False  # If True, failure aborts the entire pipeline
    phase: str = "A"  # A, B, C, D, E
    express_included: bool = False  # True for steps 1, 6, 7, 10, 19, 22


@dataclass
class StepOutcome:
    """Result of executing a single pipeline step."""

    step_number: int
    step_name: str
    status: str  # passed | failed | skipped
    phase: str = "A"
    output_data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    error_msg: Optional[str] = None
    penalty: float = 0.0


class PipelineOrchestrator:
    """
    Sequential orchestrator for the 22-step VigyanLLM pipeline.

    Usage:
        config = PipelineConfig(mode="full")
        orchestrator = PipelineOrchestrator(config=config)
        # Steps are pre-registered or registered dynamically
        results = orchestrator.run(job_id, input_params)
    """

    def __init__(self, db_session=None, config: Optional[PipelineConfig] = None):
        """
        Args:
            db_session: Optional database session for persisting job/step status.
                        If None, status updates are logged but not persisted.
            config: Pipeline configuration. If None, uses default PipelineConfig.
        """
        self._steps: List[StepRegistration] = []
        self._db_session = db_session
        self._config = config or PipelineConfig()

    @property
    def config(self) -> PipelineConfig:
        """Return the pipeline configuration."""
        return self._config

    def register_step(
        self,
        step_number: int,
        step_name: str,
        step_function: Callable[[Dict[str, Any]], Dict[str, Any]],
        hard_failure: bool = False,
        phase: str = "A",
        express_included: bool = False,
    ) -> None:
        """Register a step function to the pipeline."""
        self._steps.append(
            StepRegistration(
                step_number=step_number,
                step_name=step_name,
                step_function=step_function,
                hard_failure=hard_failure,
                phase=phase,
                express_included=express_included,
            )
        )
        # Keep steps sorted by step_number
        self._steps.sort(key=lambda s: s.step_number)

    @property
    def steps(self) -> List[StepRegistration]:
        """Return the ordered list of registered steps."""
        return list(self._steps)

    def _should_skip_in_express(self, registration: StepRegistration) -> bool:
        """
        Determine if a step should be skipped in express mode.

        Returns True if the pipeline is in express mode and the step is
        not in the express step set.
        """
        if self._config.mode != "express":
            return False
        return not registration.express_included

    def run(
        self,
        job_id: str,
        input_params: Dict[str, Any],
    ) -> List[StepOutcome]:
        """
        Execute all registered pipeline steps sequentially.

        Args:
            job_id: Unique identifier for this pipeline run.
            input_params: Initial parameters passed to the first step.

        Returns:
            List of StepOutcome objects (one per registered step).
        """
        outcomes: List[StepOutcome] = []
        current_data = dict(input_params)
        aborted = False

        self._update_job_status(job_id, "running")
        logger.info(
            "VigyanLLM: Pipeline %s started with %d steps (mode=%s)",
            job_id,
            len(self._steps),
            self._config.mode,
        )

        for registration in self._steps:
            # If pipeline was aborted by a hard failure, skip remaining steps
            if aborted:
                outcome = StepOutcome(
                    step_number=registration.step_number,
                    step_name=registration.step_name,
                    status="skipped",
                    phase=registration.phase,
                    error_msg="Pipeline aborted due to prior hard failure",
                )
                outcomes.append(outcome)
                self._record_step_result(job_id, outcome)
                continue

            # Express mode: skip steps not in the express subset
            if self._should_skip_in_express(registration):
                outcome = StepOutcome(
                    step_number=registration.step_number,
                    step_name=registration.step_name,
                    status="skipped",
                    phase=registration.phase,
                )
                outcomes.append(outcome)
                self._record_step_result(job_id, outcome)
                continue

            self._update_job_status(
                job_id, f"step_{registration.step_number}", phase=registration.phase
            )
            outcome = self._execute_step_with_timeout(registration, current_data)
            outcomes.append(outcome)
            self._record_step_result(job_id, outcome)

            if outcome.status == "passed":
                # Merge step output into pipeline data for next step
                current_data.update(outcome.output_data)
            elif outcome.status == "failed":
                if registration.hard_failure:
                    logger.error(
                        "VigyanLLM: Pipeline %s: hard failure at step %d (%s): %s",
                        job_id,
                        registration.step_number,
                        registration.step_name,
                        outcome.error_msg,
                    )
                    aborted = True
                else:
                    # Soft failure — continue with penalty
                    logger.warning(
                        "VigyanLLM: Pipeline %s: soft failure at step %d (%s): %s",
                        job_id,
                        registration.step_number,
                        registration.step_name,
                        outcome.error_msg,
                    )

        # Final status + flush all pending step-result inserts
        final_status = "failed" if aborted else "completed"
        self._update_job_status(job_id, final_status)
        if self._db_session is not None:
            try:
                self._db_session.commit()
            except Exception:
                logger.exception("VigyanLLM: Failed to flush step results for %s", job_id)
        logger.info(
            "VigyanLLM: Pipeline %s finished with status: %s", job_id, final_status
        )

        return outcomes

    def _execute_step_with_timeout(
        self,
        registration: StepRegistration,
        input_data: Dict[str, Any],
    ) -> StepOutcome:
        """Execute a single step with timeout enforcement and error handling."""
        result_container: List[StepOutcome] = []
        exception_container: List[Exception] = []

        def _run_step():
            try:
                output = registration.step_function(input_data)
                result_container.append(output)
            except Exception as exc:
                exception_container.append(exc)

        start_ns = time.perf_counter_ns()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(_run_step)
        except RuntimeError as exc:
            executor.shutdown(wait=False)
            return StepOutcome(
                step_number=registration.step_number,
                step_name=registration.step_name,
                status="failed",
                phase=registration.phase,
                duration_ms=0,
                error_msg=f"Executor error: {exc}",
                penalty=self._config.soft_failure_penalty,
            )
        try:
            future.result(timeout=self._config.step_timeout_seconds)
        except concurrent.futures.TimeoutError:
            duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            error_msg = (
                f"Step {registration.step_number} ({registration.step_name}) "
                f"exceeded {self._config.step_timeout_seconds}s timeout"
            )
            logger.warning("VigyanLLM: %s", error_msg)
            executor.shutdown(wait=False)
            return StepOutcome(
                step_number=registration.step_number,
                step_name=registration.step_name,
                status="failed",
                phase=registration.phase,
                duration_ms=duration_ms,
                error_msg=error_msg,
                penalty=self._config.soft_failure_penalty,
            )
        finally:
            executor.shutdown(wait=False)

        duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000

        # Check if step raised an exception
        if exception_container:
            exc = exception_container[0]
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error(
                "VigyanLLM: Step %d (%s) raised an exception: %s",
                registration.step_number,
                registration.step_name,
                error_msg,
            )
            return StepOutcome(
                step_number=registration.step_number,
                step_name=registration.step_name,
                status="failed",
                phase=registration.phase,
                duration_ms=duration_ms,
                error_msg=error_msg,
                penalty=self._config.soft_failure_penalty,
            )

        # Step completed successfully
        output = result_container[0] if result_container else {}
        return StepOutcome(
            step_number=registration.step_number,
            step_name=registration.step_name,
            status="passed",
            phase=registration.phase,
            output_data=output if isinstance(output, dict) else {},
            duration_ms=duration_ms,
        )

    # ─── Backward Compatibility ───────────────────────────────────────────

    def _execute_step(
        self,
        registration: StepRegistration,
        input_data: Dict[str, Any],
    ) -> StepOutcome:
        """Execute a single step with timing and error handling (no timeout).

        Retained for backward compatibility. Prefer _execute_step_with_timeout.
        """
        start_ns = time.perf_counter_ns()

        try:
            output = registration.step_function(input_data)
            duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000

            return StepOutcome(
                step_number=registration.step_number,
                step_name=registration.step_name,
                status="passed",
                phase=registration.phase,
                output_data=output if isinstance(output, dict) else {},
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "VigyanLLM: Step %d (%s) raised an exception",
                registration.step_number,
                registration.step_name,
            )

            return StepOutcome(
                step_number=registration.step_number,
                step_name=registration.step_name,
                status="failed",
                phase=registration.phase,
                duration_ms=duration_ms,
                error_msg=error_msg,
                penalty=self._config.soft_failure_penalty,
            )

    # ─── Database Interaction ─────────────────────────────────────────────

    def _update_job_status(
        self, job_id: str, status: str, phase: Optional[str] = None
    ) -> None:
        """Update the pipeline_jobs row with current status and phase."""
        if self._db_session is None:
            logger.debug(
                "VigyanLLM: Job %s → status: %s, phase: %s (no DB session)",
                job_id,
                status,
                phase,
            )
            return

        try:
            if phase:
                self._db_session.execute(
                    "UPDATE pipeline_jobs SET status = :status, phase = :phase, "
                    "mode = :mode, "
                    "started_at = COALESCE(started_at, NOW()) "
                    "WHERE id = :job_id",
                    {
                        "status": status,
                        "phase": phase,
                        "mode": self._config.mode,
                        "job_id": job_id,
                    },
                )
            else:
                self._db_session.execute(
                    "UPDATE pipeline_jobs SET status = :status, "
                    "mode = :mode, "
                    "started_at = COALESCE(started_at, NOW()) "
                    "WHERE id = :job_id",
                    {
                        "status": status,
                        "mode": self._config.mode,
                        "job_id": job_id,
                    },
                )
            self._db_session.commit()
        except Exception:
            logger.exception(
                "VigyanLLM: Failed to update job status for %s", job_id
            )

    def _record_step_result(self, job_id: str, outcome: StepOutcome) -> None:
        """Insert a row into pipeline_results for this step."""
        if self._db_session is None:
            logger.debug(
                "VigyanLLM: Job %s step %d → %s (no DB session)",
                job_id,
                outcome.step_number,
                outcome.status,
            )
            return

        try:
            import json

            self._db_session.execute(
                "INSERT INTO pipeline_results "
                "(job_id, step_number, step_name, status, output_data, "
                "duration_ms, phase) "
                "VALUES (:job_id, :step_number, :step_name, :status, "
                ":output_data, :duration_ms, :phase)",
                {
                    "job_id": job_id,
                    "step_number": outcome.step_number,
                    "step_name": outcome.step_name,
                    "status": outcome.status,
                    "output_data": json.dumps(outcome.output_data),
                    "duration_ms": outcome.duration_ms,
                    "phase": outcome.phase,
                },
            )
        except Exception:
            logger.exception(
                "VigyanLLM: Failed to record step result for job %s step %d",
                job_id,
                outcome.step_number,
            )
