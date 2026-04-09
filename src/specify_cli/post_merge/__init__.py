"""Post-merge reliability utilities for spec-kitty.

Public API:
  - run_check: compare two git refs and return stale-assertion findings
  - StaleAssertionFinding: a single suspect assertion
  - StaleAssertionReport: aggregated results of a run_check call
"""

from .stale_assertions import (
    StaleAssertionFinding,
    StaleAssertionReport,
    run_check,
)

__all__ = ["run_check", "StaleAssertionFinding", "StaleAssertionReport"]
