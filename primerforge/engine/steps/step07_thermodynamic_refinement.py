"""
Step 7: Thermodynamic & Salt Matrix Tuning (Nearest-Neighbor Tm / SantaLucia)
===============================================================================
Recalculate Tm with full SantaLucia NN model + buffer-specific salt corrections.
No GC-content approximations — pure nearest-neighbor physics.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _gc_percent(sequence: str) -> float:
    """Return GC content as a percentage for a primer sequence."""
    if not sequence:
        return 0.0
    seq = sequence.upper()
    return round(((seq.count("G") + seq.count("C")) / len(seq)) * 100.0, 2)


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 7: Refine thermodynamics for all candidate pairs.
    
    Input: candidate_pairs, buffer conditions
    Output: refined_pairs with NN-calculated Tm, salt-adjusted, Mg-adjusted
    """
    from ..thermodynamics import calculate_tm, BufferConditions

    candidate_pairs = input_data.get("candidate_pairs", [])
    if not candidate_pairs:
        return {"refined_pairs": [], "refinement_note": "No candidates to refine"}

    buffer_data = input_data.get("buffer", {})
    buffer = BufferConditions(
        monovalent_mm=buffer_data.get("monovalent_mm", 50.0),
        divalent_mm=buffer_data.get("divalent_mm", 1.5),
        dntp_mm=buffer_data.get("dntp_mm", 0.2),
        oligo_conc_nm=buffer_data.get("oligo_conc_nm", 250.0),
    )

    refined_pairs = []
    for pair in candidate_pairs:
        # Handle both formats: forward can be a string or a dict with 'sequence' key
        fwd_data = pair.get("forward", "")
        rev_data = pair.get("reverse", "")
        
        if isinstance(fwd_data, str):
            fwd_seq = fwd_data
            fwd_dict = {
                "sequence": fwd_data,
                "tm": pair.get("forward_tm", 0),
                "gc": _gc_percent(fwd_data),
                "length": len(fwd_data),
            }
            if pair.get("forward_start") is not None:
                fwd_dict["start"] = pair.get("forward_start")
            if pair.get("forward_start_pos") is not None:
                fwd_dict["start_pos"] = pair.get("forward_start_pos")
            if pair.get("forward_stop_pos") is not None:
                fwd_dict["stop_pos"] = pair.get("forward_stop_pos")
        else:
            fwd_seq = fwd_data.get("sequence", "")
            fwd_dict = dict(fwd_data)
            fwd_dict.setdefault("gc", _gc_percent(fwd_seq))
            fwd_dict.setdefault("length", len(fwd_seq))
        
        if isinstance(rev_data, str):
            rev_seq = rev_data
            rev_dict = {
                "sequence": rev_data,
                "tm": pair.get("reverse_tm", 0),
                "gc": _gc_percent(rev_data),
                "length": len(rev_data),
            }
            if pair.get("reverse_start") is not None:
                rev_dict["start"] = pair.get("reverse_start")
            if pair.get("reverse_start_pos") is not None:
                rev_dict["start_pos"] = pair.get("reverse_start_pos")
            if pair.get("reverse_stop_pos") is not None:
                rev_dict["stop_pos"] = pair.get("reverse_stop_pos")
        else:
            rev_seq = rev_data.get("sequence", "")
            rev_dict = dict(rev_data)
            rev_dict.setdefault("gc", _gc_percent(rev_seq))
            rev_dict.setdefault("length", len(rev_seq))

        if not fwd_seq or not rev_seq:
            continue

        try:
            fwd_thermo = calculate_tm(fwd_seq, buffer)
            rev_thermo = calculate_tm(rev_seq, buffer)

            refined = dict(pair)
            refined["forward"] = fwd_dict
            refined["reverse"] = rev_dict
            refined["forward"]["sequence"] = fwd_seq
            refined["reverse"]["sequence"] = rev_seq
            refined["forward"]["tm_nn"] = fwd_thermo.tm
            refined["forward"]["tm_salt_adjusted"] = fwd_thermo.tm_salt_adjusted
            refined["forward"]["tm_mg_adjusted"] = fwd_thermo.tm_mg_adjusted if hasattr(fwd_thermo, 'tm_mg_adjusted') else fwd_thermo.tm_salt_adjusted
            refined["forward"]["delta_h"] = fwd_thermo.delta_h
            refined["forward"]["delta_s"] = fwd_thermo.delta_s
            refined["forward"]["delta_g_37"] = fwd_thermo.delta_g_37

            refined["reverse"]["sequence"] = rev_seq
            refined["reverse"]["tm_nn"] = rev_thermo.tm
            refined["reverse"]["tm_salt_adjusted"] = rev_thermo.tm_salt_adjusted
            refined["reverse"]["tm_mg_adjusted"] = rev_thermo.tm_mg_adjusted if hasattr(rev_thermo, 'tm_mg_adjusted') else rev_thermo.tm_salt_adjusted
            refined["reverse"]["delta_h"] = rev_thermo.delta_h
            refined["reverse"]["delta_s"] = rev_thermo.delta_s
            refined["reverse"]["delta_g_37"] = rev_thermo.delta_g_37

            refined["delta_tm_nn"] = round(abs(fwd_thermo.tm - rev_thermo.tm), 2)
            refined["thermo_pass"] = refined["delta_tm_nn"] <= 1.5

            refined_pairs.append(refined)
        except Exception as e:
            pair_label = pair.get("pair_id") or pair.get("rank") or pair.get("pair_index", "?")
            logger.warning(f"Thermo calc failed for pair {pair_label}: {e}")
            pair["thermo_pass"] = False
            pair["thermo_error"] = str(e)
            refined_pairs.append(pair)

    # Sort by delta_tm (smallest first — best thermodynamic match)
    refined_pairs.sort(key=lambda p: p.get("delta_tm_nn", 99))

    # Ensure pair_id is preserved for all pairs
    for i, pair in enumerate(refined_pairs):
        if not pair.get("pair_id"):
            pair["pair_id"] = i + 1

    return {
        "refined_pairs": refined_pairs,
        "refinement_note": f"{len(refined_pairs)} pairs refined with NN thermodynamics",
    }
