"""Backward-compat shim — canonical home is specify_cli.acceptance.matrix."""

from specify_cli.acceptance.matrix import (  # noqa: F401
    AcceptanceCriterion,
    AcceptanceMatrix,
    NegativeInvariant,
    enforce_negative_invariants,
    read_acceptance_matrix,
    validate_manual_evidence,
    validate_matrix_evidence,
    write_acceptance_matrix,
)
