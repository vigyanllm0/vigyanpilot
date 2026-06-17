"""
VigyanLLM 22-Step Pipeline — Step Modules
==========================================

Step modules (renumbered to match 22-step order):
  Step 1:  Transcript Isoform Filter
  Step 2:  Exon-Intron Junction Mapping
  Step 3:  Bisulfite Conversion Simulation
  Step 4:  Degenerate Base Parsing
  Step 5:  Repeat Masking
  Step 6:  Primer3 Parameter Constraints
  Step 7:  Nearest-Neighbor Tm / SantaLucia
  Step 8:  Dynamic Buffer & Salt Adjustments
  Step 9:  Divalent Cation Mg²+ Scaling
  Step 10: Target Specificity BLAST
  Step 11: Structural Alignment Bowtie2
  Step 12: Organelle & Pseudogene Screening
  Step 13: Primer Secondary Structure ΔG
  Step 14: Amplicon Structural Verification
  Step 15: Population Variant Filter dbSNP
  Step 16: Clinical Hotspot Filter (ClinVar)
  Step 17: 5' Overhang Adapter Tailing
  Step 18: Multiplex Cross-Reaction PrimerPooler
  Step 19: Automated Penalty & Ranking Matrix
  Step 20: Thermocycling Profile Generation
  Step 21: Manufacturing Feasibility Screening
  Step 22: Probe Design qPCR/TaqMan
"""

from .base import PipelineStep, StepResult

# Phase A: Sequence Processing (Steps 1-5)
from .step01_isoform_filter import execute as step01_execute
from .step02_exon_intron_junction import execute as step02_execute
from .step03_bisulfite_conversion import execute as step03_execute
from .step04_degenerate_bases import execute as step04_execute
from .step05_repeat_masking import execute as step05_execute

# Phase B: Thermodynamic Validation (Steps 6-9)
from .step06_primer3_design import execute as step06_execute
from .step07_thermodynamic_refinement import execute as step07_execute
from .step08_buffer_salt import execute as step08_execute
from .step09_mg_correction import execute as step09_execute

# Phase C: Specificity & Variant Filtering (Steps 10-12)
from .step10_blast_specificity import execute as step10_execute
from .step11_bowtie2_alignment import execute as step11_execute
from .step12_organelle_screening import execute as step12_execute

# Phase D: Structural & Multiplex Analysis (Steps 13-18)
from .step13_secondary_structure import execute as step13_execute
from .step14_amplicon_structure import execute as step14_execute
from .step15_dbsnp_filter import execute as step15_execute
from .step16_clinical_hotspots import execute as step16_execute
from .step17_adapter_tailing import execute as step17_execute
from .step18_multiplex_scoring import execute as step18_execute

# Phase E: Ranking, Profiling & Export (Steps 19-22)
from .step19_ranking import execute as step19_execute
from .step20_thermocycling import execute as step20_execute
from .step21_manufacturing import execute as step21_execute
from .step22_probe_design import execute as step22_execute

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
}

__all__ = [
    "PipelineStep",
    "StepResult",
    "STEP_REGISTRY",
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
]
