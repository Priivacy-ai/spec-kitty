"""Calibration package: §4.5.1 inequality predicate and mission walker.

Public API:
    from specify_cli.calibration import (
        InequalityResult,
        assert_inequality_holds,
        CalibrationFinding,
        walk_mission,
    )
"""

from __future__ import annotations

from specify_cli.calibration.inequality import InequalityResult, assert_inequality_holds
from specify_cli.calibration.walker import CalibrationFinding, walk_mission

__all__ = [
    "InequalityResult",
    "assert_inequality_holds",
    "CalibrationFinding",
    "walk_mission",
]
