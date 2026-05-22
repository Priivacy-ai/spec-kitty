"""Central CLI startup readiness coordinator.

Public surface (consumed by the root CLI callback and by subcommands that
need to read the readiness verdict):

    from specify_cli.readiness import (
        AuthStatus,
        OutputPolicy,
        ReadinessResult,
        evaluate_readiness,
        get_readiness,
    )

See ``kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/contracts/readiness-api.md``
for the stability contract.

Tracking issue: https://github.com/Priivacy-ai/spec-kitty/issues/1093
"""

from __future__ import annotations

from specify_cli.readiness.coordinator import (
    AuthStatus,
    OutputPolicy,
    ReadinessResult,
    evaluate_readiness,
    get_readiness,
)

__all__ = [
    "AuthStatus",
    "OutputPolicy",
    "ReadinessResult",
    "evaluate_readiness",
    "get_readiness",
]
