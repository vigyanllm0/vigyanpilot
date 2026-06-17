"""
Step 20: Thermocycling Profile Generation (Rychlik Formula)
=============================================================
Generates optimized PCR cycling parameters using the Rychlik formula for
annealing temperature calculation. Produces complete cycling protocols
including touchdown profiles when primer Tm asymmetry is detected.

Validates: Requirements 20.1-20.6
"""

import logging
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from primerforge.engine.steps.base import PipelineStep

logger = logging.getLogger(__name__)


@dataclass
class CyclingProfile:
    """Complete PCR cycling protocol."""

    initial_denat_temp: float = 95.0
    initial_denat_time_s: int = 180
    denat_temp: float = 95.0
    denat_time_s: int = 30
    annealing_temp: float = 60.0
    annealing_time_s: int = 30
    extension_temp: float = 72.0
    extension_time_s: int = 60
    final_extension_temp: float = 72.0
    final_extension_time_s: int = 300
    cycles: int = 30
    is_touchdown: bool = False
    touchdown_start_temp: Optional[float] = None
    touchdown_decrement: float = 0.5
    touchdown_cycles: int = 10
    warnings: List[str] = field(default_factory=list)


class ThermocyclingProfileStep(PipelineStep):
    """Generates optimized PCR cycling parameters using Rychlik formula."""

    def __init__(self):
        super().__init__(name="Thermocycling Profile Generation", step_number=20)

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate thermocycling profiles for ranked primer pairs.

        Input keys:
            ranked_pairs: list of primer pair dicts with Tm values
            polymerase_type: str ('taq' or 'hifi'), default 'taq'
            template_ng: float, template concentration in nanograms
            monovalent_mm: float, monovalent cation concentration in mM

        Output keys:
            cycling_profiles: list of protocol dicts (one per ranked pair)
        """
        ranked_pairs = input_data.get("ranked_pairs", [])
        polymerase_type = input_data.get("polymerase_type", "taq").lower()
        template_ng = input_data.get("template_ng", 0.0)
        monovalent_mm = input_data.get("monovalent_mm", 50.0)

        if not ranked_pairs:
            return {
                "cycling_profiles": [],
                "thermocycling_note": "No ranked pairs available for profile generation",
            }

        # Convert monovalent concentration from mM to M for product Tm formula
        na_conc_m = monovalent_mm / 1000.0

        cycling_profiles = []

        for pair in ranked_pairs:
            profile = self._generate_profile(
                pair, polymerase_type, template_ng, na_conc_m
            )
            cycling_profiles.append(asdict(profile))

        return {
            "cycling_profiles": cycling_profiles,
            "thermocycling_note": (
                f"Generated {len(cycling_profiles)} cycling profile(s). "
                f"Polymerase: {polymerase_type}, Template: {template_ng}ng"
            ),
        }

    def _generate_profile(
        self,
        pair: Dict[str, Any],
        polymerase_type: str,
        template_ng: float,
        na_conc_m: float,
    ) -> CyclingProfile:
        """Generate a complete cycling profile for a single primer pair."""
        profile = CyclingProfile()

        # Extract Tm values from pair
        tm_fwd = self._get_primer_tm(pair, "forward")
        tm_rev = self._get_primer_tm(pair, "reverse")

        # Tm(primer) = min of forward and reverse Tms (Rychlik formula)
        tm_primer = min(tm_fwd, tm_rev)

        # Compute amplicon properties for product Tm
        amplicon_seq = pair.get("amplicon_sequence", "")
        amplicon_length = pair.get("amplicon_length", 0) or len(amplicon_seq)

        if amplicon_seq:
            gc_percent = self._compute_gc_percent(amplicon_seq)
        else:
            # Fall back to average of primer GC contents if amplicon not available
            gc_fwd = pair.get("forward", {}).get("gc_percent", 50.0)
            gc_rev = pair.get("reverse", {}).get("gc_percent", 50.0)
            gc_percent = (gc_fwd + gc_rev) / 2.0

        if amplicon_length == 0:
            product_size = pair.get("amplicon_size") or pair.get("product_size")
            if product_size:
                amplicon_length = int(product_size)
            else:
                raise ValueError("Amplicon length unavailable for thermocycling profile")

        # Calculate product Tm
        tm_product = self._product_tm(gc_percent, amplicon_length, na_conc_m)

        # Calculate annealing temperature using Rychlik formula
        ta = self._rychlik_annealing_temp(tm_primer, tm_product)

        # Calculate extension time
        ext_time = self._extension_time(amplicon_length, polymerase_type)

        # Determine cycle count based on template concentration
        cycles = self._determine_cycles(template_ng)

        # Check for touchdown requirement
        delta_tm = abs(tm_fwd - tm_rev)
        is_touchdown = delta_tm > 2.0

        # Populate profile
        profile.annealing_temp = round(ta, 1)
        profile.extension_time_s = ext_time
        profile.cycles = cycles

        # Touchdown protocol
        if is_touchdown:
            td_profile = self._touchdown_profile(ta, delta_tm)
            profile.is_touchdown = True
            profile.touchdown_start_temp = td_profile["start_temp"]
            profile.touchdown_decrement = td_profile["decrement"]
            profile.touchdown_cycles = td_profile["touchdown_cycles"]
            # Remaining cycles at standard Ta
            profile.cycles = cycles - profile.touchdown_cycles

        # Warnings for out-of-range annealing temperature (Req 20.6)
        if ta < 45.0:
            warning = (
                f"Annealing temperature {ta:.1f}°C is below optimal range "
                f"(45–72°C). Consider redesigning primers."
            )
            profile.warnings.append(warning)
            logger.warning("VigyanLLM: %s", warning)

        if ta > 72.0:
            warning = (
                f"Annealing temperature {ta:.1f}°C is above optimal range "
                f"(45–72°C). Consider redesigning primers."
            )
            profile.warnings.append(warning)
            logger.warning("VigyanLLM: %s", warning)

        return profile

    def _rychlik_annealing_temp(self, tm_primer: float, tm_product: float) -> float:
        """
        Calculate optimal annealing temperature using the Rychlik formula.

        Ta = 0.3·Tm(primer) + 0.7·Tm(product) - 14.9

        where Tm(primer) = min(Tm_fwd, Tm_rev)

        Validates: Requirement 20.1
        """
        return 0.3 * tm_primer + 0.7 * tm_product - 14.9

    def _product_tm(
        self, gc_percent: float, length: int, na_conc_m: float
    ) -> float:
        """
        Calculate product (amplicon) melting temperature.

        Tm(product) = 81.5 + 16.6·log₁₀([Na+]) + 0.41·(%GC) - 600/length

        Args:
            gc_percent: GC content as percentage (0-100)
            length: Amplicon length in base pairs
            na_conc_m: Monovalent cation concentration in Molar

        Validates: Requirement 20.1
        """
        if length == 0:
            length = 1  # Prevent division by zero

        # Ensure [Na+] > 0 for log calculation
        if na_conc_m <= 0:
            na_conc_m = 0.05  # Default to 50mM

        tm = 81.5 + 16.6 * math.log10(na_conc_m) + 0.41 * gc_percent - 600.0 / length

        return tm

    def _extension_time(self, amplicon_length: int, polymerase: str) -> int:
        """
        Calculate extension time based on amplicon length and polymerase type.

        Taq: 60 seconds per 1000bp (1 min/kb)
        HiFi: 30 seconds per 1000bp (30s/kb)
        Minimum: 15 seconds

        Validates: Requirement 20.2
        """
        if polymerase in ("hifi", "high-fidelity", "phusion", "q5"):
            seconds_per_kb = 30.0
        else:
            # Default to Taq rate
            seconds_per_kb = 60.0

        ext_time = (amplicon_length / 1000.0) * seconds_per_kb

        # Minimum extension time of 15 seconds
        return max(15, int(round(ext_time)))

    def _determine_cycles(self, template_ng: float) -> int:
        """
        Determine recommended cycle count based on template concentration.

        >= 10ng template: 25-30 cycles (use 30)
        < 10ng template or unspecified: 30-35 cycles (use 35)

        Validates: Requirement 20.4
        """
        if template_ng >= 10.0:
            return 30
        else:
            return 35

    def _touchdown_profile(self, ta: float, delta_tm: float) -> Dict[str, Any]:
        """
        Generate touchdown protocol parameters.

        Touchdown is used when |Tm_fwd - Tm_rev| > 2°C.
        Start at Ta + 5°C, decrement 0.5°C per cycle for 10 cycles.

        Validates: Requirement 20.5
        """
        return {
            "start_temp": round(ta + 5.0, 1),
            "decrement": 0.5,
            "touchdown_cycles": 10,
        }

    def _get_primer_tm(self, pair: Dict[str, Any], direction: str) -> float:
        """Extract Tm for a primer from the pair dict, trying multiple keys."""
        primer_data = pair.get(direction, {}) or pair.get(f"{direction}_primer", {})

        if isinstance(primer_data, dict):
            # Try Tm keys in priority order
            for key in ("tm_mg_adjusted", "tm_salt_adjusted", "tm_nn", "tm", "tm_basic"):
                val = primer_data.get(key)
                if val is not None:
                    return float(val)

        # Try flat keys on the pair itself
        for key in (f"{direction}_tm", f"tm_{direction}"):
            val = pair.get(key)
            if val is not None:
                return float(val)

        raise ValueError(f"{direction} primer Tm unavailable for thermocycling profile")

    def _compute_gc_percent(self, sequence: str) -> float:
        """Calculate GC percentage of a DNA sequence."""
        if not sequence:
            return 50.0
        seq_upper = sequence.upper()
        gc_count = seq_upper.count("G") + seq_upper.count("C")
        return (gc_count / len(seq_upper)) * 100.0


# ---------------------------------------------------------------------------
# Module-level execute function (required by pipeline orchestrator)
# ---------------------------------------------------------------------------

_step_instance = ThermocyclingProfileStep()


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Module-level entry point for the pipeline orchestrator.

    Step 20: Thermocycling Profile Generation using the Rychlik formula.

    Input keys:
        ranked_pairs: list of primer pair dicts
        polymerase_type: str ('taq' or 'hifi')
        template_ng: float, template concentration in nanograms
        monovalent_mm: float, monovalent cation concentration in mM

    Output keys:
        cycling_profiles: list of protocol dicts
    """
    return _step_instance.execute(input_data)
