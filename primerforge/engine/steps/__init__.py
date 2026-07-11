"""
VigyanLLM Pipeline — Step Modules
===================================

Step modules (consolidated 24-step order):
  Phase A: Sequence Processing & Consensus (Steps 1-7)
    Step 1:  Transcript Isoform Filter
    Step 2:  Exon-Intron Junction Mapping
    Step 3:  Bisulfite Conversion Simulation
    Step 4:  Degenerate Base Parsing
    Step 5:  Repeat Masking
    Step 6:  Backend MSA & Conservation Scoring  ★ NEW
    Step 7:  Conserved Region Targeting           ★ NEW

  Phase B: Thermodynamic Validation (Steps 8-11)
    Step 8:  Primer3 Parameter Constraints        (was 6)
    Step 9:  Nearest-Neighbor Tm / SantaLucia     (was 7)
    Step 10: Dynamic Buffer & Salt Adjustments    (was 8)
    Step 11: Divalent Cation Mg²+ Scaling         (was 9)

  Phase C: Specificity & Inclusivity (Steps 12-16)
    Step 12: Target Specificity BLAST + Viewer    (was 10, enhanced)
    Step 13: Strain Inclusivity & Discontinuous   ★ NEW
    Step 14: Structural Alignment Bowtie2         (was 11)
    Step 15: Organelle & Pseudogene Screening     (was 12)
    Step 16: Primer Secondary Structure ΔG        (was 13)

  Phase D: Structural & Multiplex Analysis (Steps 17-22)
    Step 17: Amplicon Structural Verification     (was 14)
    Step 18: Population Variant Filter dbSNP      (was 15)
    Step 19: Clinical Hotspot Filter (ClinVar)    (was 16)
    Step 20: 5' Overhang Adapter Tailing          (was 17)
    Step 21: Multiplex Cross-Reaction             (was 18)
    Step 22: Penalty & Ranking Matrix             (was 19)

  Phase E: Profiling & Export (Steps 23-24)
    Step 23: Thermocycling Profile Generation     (was 20)
    Step 24: Probe Design qPCR/TaqMan             (was 22)
    (Step 21 Manufacturing merged into Step 23)
"""

from .base import PipelineStep, StepResult

# Phase A: Sequence Processing & Consensus (Steps 1-7)
from .step01_isoform_filter import execute as step01_execute
from .step02_exon_intron_junction import execute as step02_execute
from .step03_bisulfite_conversion import execute as step03_execute
from .step04_degenerate_bases import execute as step04_execute
from .step05_repeat_masking import execute as step05_execute
from .step06_msa_conservation import execute as step06_execute

# Phase B: Thermodynamic Validation (Steps 8-11)
from .step06_primer3_design import execute as step08_execute
from .step07_conserved_targeting import execute as step07_execute
from .step07_thermodynamic_refinement import execute as step09_execute
from .step08_buffer_salt import execute as step10_execute
from .step09_mg_correction import execute as step11_execute

# Phase C: Specificity & Inclusivity (Steps 12-16)
from .step10_blast_specificity import execute as step12_execute
from .step11_bowtie2_alignment import execute as step14_execute
from .step12_organelle_screening import execute as step15_execute
from .step13_secondary_structure import execute as step16_execute
from .step13_strain_inclusivity import execute as step13_execute

# Phase D: Structural & Multiplex Analysis (Steps 17-22)
from .step14_amplicon_structure import execute as step17_execute
from .step15_dbsnp_filter import execute as step18_execute
from .step16_clinical_hotspots import execute as step19_execute
from .step17_adapter_tailing import execute as step20_execute
from .step18_multiplex_scoring import execute as step21_execute
from .step19_ranking import execute as step22_execute

# Phase E: Profiling & Export (Steps 23-24)
from .step20_thermocycling import execute as step23_execute
from .step22_probe_design import execute as step24_execute

# Step registry mapping step numbers to their execute functions
STEP_REGISTRY = {
    1: step01_execute,
    2: step02_execute,
    3: step03_execute,
    4: step04_execute,
    5: step05_execute,
    6: step06_execute,
    7: step07_execute,
    8: step08_execute,
    9: step09_execute,
    10: step10_execute,
    11: step11_execute,
    12: step12_execute,
    13: step13_execute,
    14: step14_execute,
    15: step15_execute,
    16: step16_execute,
    17: step17_execute,
    18: step18_execute,
    19: step19_execute,
    20: step20_execute,
    21: step21_execute,
    22: step22_execute,
    23: step23_execute,
    24: step24_execute,
}

__all__ = [
    "STEP_REGISTRY",
    "PipelineStep",
    "StepResult",
    "step01_execute",
    "step02_execute",
    "step03_execute",
    "step04_execute",
    "step05_execute",
    "step06_execute",
    "step07_execute",
    "step08_execute",
    "step09_execute",
    "step10_execute",
    "step11_execute",
    "step12_execute",
    "step13_execute",
    "step14_execute",
    "step15_execute",
    "step16_execute",
    "step17_execute",
    "step18_execute",
    "step19_execute",
    "step20_execute",
    "step21_execute",
    "step22_execute",
    "step23_execute",
    "step24_execute",
]
