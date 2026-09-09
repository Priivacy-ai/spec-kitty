"""Outcome value objects for ``spec-kitty upgrade`` (FR-007, D-3, D-9).

``UpgradeOutcome`` is the single object the finalizer produces and every
renderer + the exit code derive from (D-5): it *composes* the existing
``UpgradeResult`` (``runner.py``) as a field rather than replacing it, so
JSON and human renderers keep the fields they already consume
(``from_version``, ``to_version``, ``migrations_applied`` and friends).

``RepairOutcome`` is the return contract for the scoped mission-state repair
gate (``_teamspace_mission_state_gate.offer_teamspace_mission_state_migration``,
D-9) — it replaces the three ``typer.Exit(1)`` raises that function used to
perform. ``declined`` is set ONLY on the post-consent-decision deny path;
``pending`` is set by the gate's pre-consent early returns instead. This
distinction is what makes a consent spy test non-fakeable (contracts C3):
"repair not called" alone proves nothing when the fixture never reached the
consent decision in the first place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.tool_surface.operations import Diagnostic

from .runner import UpgradeResult


@dataclass(frozen=True)
class RepairOutcome:
    """Return contract for the scoped mission-state repair gate (D-9)."""

    pending: bool = False
    declined: bool = False
    ran: bool = False
    failed: bool = False
    message: str = ""


@dataclass
class UpgradeOutcome:
    """The single object every renderer + the exit code derive from (D-3/D-5).

    Composes ``UpgradeResult`` rather than replacing it (see module docstring).
    """

    result: UpgradeResult
    manual_review_paths: list[Path] = field(default_factory=list)
    worktree_failures: list[str] = field(default_factory=list)
    activation_errors: list[str] = field(default_factory=list)
    surface_drift_failed: bool = False
    repair: RepairOutcome = field(default_factory=RepairOutcome)
    committed: bool = False
    exit_code: int = 0
    #: Non-error diagnostics carried generically on the outcome (#4032/WP02,
    #: ownership-map leeway -- ``outcome.py`` is unowned by WP01, which owns
    #: only ``cli/commands/upgrade.py``, and sits inside WP02's
    #: ``src/specify_cli/upgrade/`` authoritative surface). Consumed by
    #: ``cli.commands.upgrade._print_non_error_diagnostics`` (human ``Note:``
    #: lines) and by ``deferred_provisioning_payload`` below (JSON). Never
    #: contains ``error``-severity diagnostics -- those flow through
    #: ``result.errors``/``activation_errors`` instead.
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)

    @property
    def deferred_provisioning_payload(self) -> dict[str, object] | None:
        """JSON contract (contracts/deferred-provisioning-diagnostic.md).

        ``None`` when no ``deferred_provisioning`` diagnostic is present.
        Otherwise a small dict carrying actual content (not a bare `True`
        sentinel) so a presence-only assertion cannot be satisfied without
        the real signal (RT5).
        """
        for diagnostic in self.diagnostics:
            if diagnostic.code == "deferred_provisioning":
                return {"deferred": True, "reason": "no_config_authority"}
        return None

    @property
    def effective_success(self) -> bool:
        """True iff the migration result AND every finalizer-owned signal succeeded.

        A ``repair`` failure never enters this computation (FR-014) — mission-
        state repair is an optional, separately-consented step that must not
        sink an otherwise-completed upgrade.
        """
        return self.result.success and not self.worktree_failures and not self.surface_drift_failed and not self.activation_errors

    def derive_exit_code(self) -> int:
        """Compute, store, and return ``exit_code`` from ``effective_success``.

        This is the ONLY site that computes the upgrade exit code (D-5) —
        callers must not derive it independently from ``result.success`` or
        any other formula.
        """
        self.exit_code = 0 if self.effective_success else 1
        return self.exit_code
