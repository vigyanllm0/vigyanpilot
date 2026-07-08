"""
Step 4: Degenerate Base Parsing
================================
Scan for variable positions in viral/microbial targets.
Convert to IUPAC degenerate codes (R=A/G, Y=C/T, etc.).
Generate consensus from MSA, calculate degeneracy folds,
and reject sequences exceeding the 256-fold threshold.
"""

import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)

# IUPAC degenerate base codes: frozenset of nucleotides → IUPAC code
IUPAC_MAP = {
    frozenset({'A', 'G'}): 'R',
    frozenset({'C', 'T'}): 'Y',
    frozenset({'A', 'C'}): 'M',
    frozenset({'G', 'T'}): 'K',
    frozenset({'G', 'C'}): 'S',
    frozenset({'A', 'T'}): 'W',
    frozenset({'C', 'G', 'T'}): 'B',
    frozenset({'A', 'G', 'T'}): 'D',
    frozenset({'A', 'C', 'T'}): 'H',
    frozenset({'A', 'C', 'G'}): 'V',
    frozenset({'A', 'C', 'G', 'T'}): 'N',
}

# Reverse: degenerate code → set of constituent nucleotides
DEGENERATE_EXPAND: Dict[str, Set[str]] = {
    'R': {'A', 'G'},
    'Y': {'C', 'T'},
    'M': {'A', 'C'},
    'K': {'G', 'T'},
    'S': {'G', 'C'},
    'W': {'A', 'T'},
    'B': {'C', 'G', 'T'},
    'D': {'A', 'G', 'T'},
    'H': {'A', 'C', 'T'},
    'V': {'A', 'C', 'G'},
    'N': {'A', 'C', 'G', 'T'},
    'A': {'A'},
    'C': {'C'},
    'G': {'G'},
    'T': {'T'},
}

# Degeneracy fold: how many nucleotides a code represents
DEGENERACY_FOLD: Dict[str, int] = {
    'A': 1, 'C': 1, 'G': 1, 'T': 1,
    'R': 2, 'Y': 2, 'M': 2, 'K': 2, 'S': 2, 'W': 2,
    'B': 3, 'D': 3, 'H': 3, 'V': 3,
    'N': 4,
}

# Valid characters in a sequence (standard bases + IUPAC ambiguity codes)
VALID_CHARS = set('ACGTRYMKSWBDHVN')

# Maximum allowed effective degeneracy per primer window
MAX_DEGENERACY = 256


def _validate_sequence(sequence: str) -> None:
    """
    Check that all characters in the sequence are valid IUPAC codes.

    Raises ValueError with the invalid character and its 0-indexed position
    if any invalid character is found.
    """
    for i, char in enumerate(sequence.upper()):
        if char not in VALID_CHARS:
            raise ValueError(
                f"Invalid character '{char}' at position {i}. "
                f"Only valid nucleotides (A, C, G, T) and IUPAC ambiguity codes "
                f"(R, Y, M, K, S, W, B, D, H, V, N) are allowed."
            )


def _generate_consensus_from_msa(
    target_sequence: str, msa_sequences: List[str]
) -> str:
    """
    Generate a consensus sequence from aligned sequences using IUPAC codes.

    At each position, collect distinct bases observed across the target and
    all MSA sequences. If multiple bases are observed, assign the corresponding
    IUPAC ambiguity code.
    """
    all_sequences = [target_sequence.upper()] + [s.upper() for s in msa_sequences]
    seq_len = min(len(s) for s in all_sequences)

    consensus_chars: List[str] = []
    for i in range(seq_len):
        bases_at_pos: Set[str] = set()
        for seq in all_sequences:
            base = seq[i]
            # Expand any existing IUPAC codes in the input
            if base in DEGENERATE_EXPAND:
                bases_at_pos.update(DEGENERATE_EXPAND[base])
            # Skip gaps and dots
            elif base not in ('-', '.'):
                bases_at_pos.add(base)

        # Remove gap characters if any slipped through
        bases_at_pos.discard('-')
        bases_at_pos.discard('.')

        if not bases_at_pos:
            consensus_chars.append('N')
        elif len(bases_at_pos) == 1:
            consensus_chars.append(bases_at_pos.pop())
        else:
            code = IUPAC_MAP.get(frozenset(bases_at_pos), 'N')
            consensus_chars.append(code)

    return "".join(consensus_chars)


def _find_degenerate_positions(sequence: str) -> List[Dict[str, Any]]:
    """
    Identify all degenerate (non-standard base) positions in the sequence.

    Returns a list of dicts with:
        - position: 0-indexed position
        - code: the IUPAC ambiguity code
        - nucleotides: sorted list of constituent nucleotides
        - fold: degeneracy fold (2, 3, or 4)
    """
    positions: List[Dict[str, Any]] = []
    for i, base in enumerate(sequence.upper()):
        if base not in ('A', 'C', 'G', 'T'):
            nucleotides = sorted(DEGENERATE_EXPAND.get(base, {'A', 'C', 'G', 'T'}))
            fold = DEGENERACY_FOLD.get(base, 4)
            positions.append({
                "position": i,
                "code": base,
                "nucleotides": nucleotides,
                "fold": fold,
            })
    return positions


def _calculate_max_degeneracy_per_window(
    degenerate_positions: List[Dict[str, Any]], seq_length: int, window_size: int = 25
) -> int:
    """
    Calculate the maximum effective degeneracy across all windows of a given size.

    The effective degeneracy for a window is the product of individual folds
    at all degenerate positions within that window.

    Default window_size=25 corresponds to the maximum primer length.
    """
    if not degenerate_positions:
        return 1

    max_degeneracy = 1
    num_windows = max(1, seq_length - window_size + 1)
    for start in range(num_windows):
        end = min(start + window_size, seq_length)
        product = 1
        for dp in degenerate_positions:
            if start <= dp["position"] < end:
                product *= dp["fold"]
        if product > max_degeneracy:
            max_degeneracy = product

    return max_degeneracy


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 4: Parse degenerate bases from MSA or detect ambiguous positions.

    Input keys:
        - target_sequence (str): The target DNA sequence (may contain IUPAC codes)
        - msa_sequences (list[str], optional): List of aligned sequences for consensus

    Output keys:
        - consensus_sequence (str): Final consensus with IUPAC codes
        - degenerate_positions (list[dict]): Each with {position, code, nucleotides, fold}
        - total_degenerate_count (int): Number of degenerate positions
        - max_degeneracy_per_window (int): Maximum effective degeneracy in any primer-sized window

    Raises:
        ValueError: If target_sequence is missing, contains invalid characters,
                    or exceeds the 256-fold degeneracy threshold.
    """
    sequence = input_data.get("target_sequence", "")
    msa_sequences = input_data.get("msa_sequences", [])

    if not sequence:
        raise ValueError("No target_sequence provided")

    # Validate the target sequence for invalid characters
    _validate_sequence(sequence)

    # Also validate MSA sequences if provided
    for idx, msa_seq in enumerate(msa_sequences):
        for i, char in enumerate(msa_seq.upper()):
            if char not in VALID_CHARS and char not in ('-', '.'):
                raise ValueError(
                    f"Invalid character '{char}' at position {i} in MSA sequence {idx}. "
                    f"Only valid nucleotides (A, C, G, T), IUPAC ambiguity codes "
                    f"(R, Y, M, K, S, W, B, D, H, V, N), and gap characters (-, .) are allowed."
                )

    # Generate consensus: from MSA if available, otherwise use target directly
    if msa_sequences:
        consensus_sequence = _generate_consensus_from_msa(sequence, msa_sequences)
    else:
        consensus_sequence = sequence.upper()

    # Identify degenerate positions in the consensus
    degenerate_positions = _find_degenerate_positions(consensus_sequence)
    total_degenerate_count = len(degenerate_positions)

    # Calculate maximum degeneracy per primer-sized window
    max_degeneracy_per_window = _calculate_max_degeneracy_per_window(
        degenerate_positions, len(consensus_sequence)
    )

    # Reject if max degeneracy exceeds 256-fold threshold
    if max_degeneracy_per_window > MAX_DEGENERACY:
        raise ValueError(
            f"Effective degeneracy ({max_degeneracy_per_window}) exceeds the maximum "
            f"allowed threshold of {MAX_DEGENERACY}-fold. The sequence has too many "
            f"degenerate positions within a primer binding region to produce reliable results."
        )

    logger.info(
        "Step 4 complete: %d degenerate positions found, max window degeneracy = %d",
        total_degenerate_count,
        max_degeneracy_per_window,
    )

    return {
        "consensus_sequence": consensus_sequence,
        "degenerate_positions": degenerate_positions,
        "total_degenerate_count": total_degenerate_count,
        "max_degeneracy_per_window": max_degeneracy_per_window,
    }
