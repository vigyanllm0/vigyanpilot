"""
Pipeline Step Base Classes
===========================
Abstract base class and result dataclass for all pipeline steps.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class StepResult:
    """Structured result returned by each pipeline step execution."""
    status: str  # passed | failed | skipped
    output_data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    error_msg: Optional[str] = None


class PipelineStep(ABC):
    """
    Abstract base class for all 15 pipeline steps.

    Subclass and implement `execute()` to define step logic.
    """

    name: str = "unnamed_step"
    step_number: int = 0

    def __init__(self, name: str, step_number: int):
        self.name = name
        self.step_number = step_number

    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run this step's logic.

        Args:
            input_data: Dictionary of input parameters (accumulated from prior steps).

        Returns:
            Dictionary of output data to merge into the pipeline context.

        Raises:
            Any exception to signal step failure.
        """
        ...

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Check whether required keys are present in input_data.

        Override in subclasses to enforce specific input requirements.
        Default implementation always returns True.

        Args:
            data: The input data dictionary.

        Returns:
            True if input is valid, False otherwise.
        """
        return True

    def __repr__(self) -> str:
        return f"<PipelineStep {self.step_number}: {self.name}>"
