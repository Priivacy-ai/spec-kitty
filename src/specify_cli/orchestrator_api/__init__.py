"""Machine-contract API for external orchestrators.

Provides a stable JSON-contract CLI for external orchestrators to integrate
with spec-kitty workflow state. The core CLI owns workflow state; external
orchestrators integrate exclusively via these subcommands.
"""

from .commands import app

__all__ = ["app"]
