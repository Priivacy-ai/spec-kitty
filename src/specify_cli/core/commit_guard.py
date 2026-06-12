"""Commit-guard policy module — the ONE protection decision (ADR 2026-06-03-2, IC-02, D1).

Mission ``tooling-stability-guard-coherence-01KTRC04`` (FR-001, FR-008,
contracts C-GUARD-1 / C-GUARD-2 / C-GUARD-3a). This module is the **Shared
Kernel** policy seam: a single pure function, :func:`evaluate`, decides whether
a commit may land on its declared destination. Every commit-creating surface
routes its protection decision here and *nowhere else* (C-GUARD-1).

Mechanism / policy split
------------------------

``safe_commit`` (``git/commit_helpers.py``) is the *mechanism* — it stages,
backstops, and creates the commit. The *policy* — "is this destination allowed?"
— is decided solely by :func:`evaluate`. The split is what makes the guard
auditable: the decision is a pure function of explicit, typed inputs.

Capability is asserted-at-the-surface (FR-008 / C-GUARD-2)
----------------------------------------------------------

:class:`GuardCapability` is a **parameter** the caller passes explicitly. It is
NEVER derived from commit-message text, committed-file content, or ambient
environment. Its value is *auditability* for the LLM-agent threat model — a
greppable, typed authorization at the call site — not unforgeability. The
default is :attr:`GuardCapability.STANDARD`, which authorizes only the
placement-matched commit and no protected-branch bookkeeping flow.

Each non-standard capability authorizes exactly ONE bookkeeping flow onto a
protected ref; no capability authorizes a different flow, and **no capability
can grant a direct push to ``origin/main``** — pushing is outside this guard's
reach entirely (it never pushes; see ``test_commit_helpers_module_performs_no_push``).

Destination authority (C-GUARD-3a)
----------------------------------

:func:`evaluate` ECHOES :attr:`CommitTarget.ref` as the resolved destination —
it never re-derives a destination from any other source. ``--to-branch`` and
context resolution flow INTO the :class:`CommitTarget` *before* evaluation, so
there is exactly one destination authority.

Naming note
-----------

:class:`GuardVerdict` is intentionally DISTINCT from
``policy.merge_gates.GateVerdict`` / ``GateResult``: near-twin shape, different
domain (commit protection vs merge gating). Do not unify them.

Operator escape hatch
---------------------

The ambient env hatch ``SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`` is the ONE
retained operator channel (solo-fork operators who own ``main``). It is
consumed in ``git/commit_helpers.py`` by the protected-branch pre-checks and by
``safe_commit``'s :class:`ProtectionState` input computation — the operator
declares the branch unprotected for this repo. It never reaches this module:
:func:`evaluate` is environment-free and decides purely on the typed inputs it
is handed.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from mission_runtime import CommitTarget

__all__ = [
    "GuardCapability",
    "GuardVerdict",
    "ProtectionState",
    "evaluate",
]


class GuardCapability(enum.Enum):
    """Asserted-at-the-surface authorization for a commit (FR-008 / C-GUARD-2).

    The caller passes the capability explicitly; it is NEVER derived from
    message text, file content, or env. ``STANDARD`` is the default and grants
    only the placement-matched commit (no protected-branch bookkeeping). Each
    other member authorizes exactly ONE bookkeeping flow onto a protected ref.

    No member can authorize a direct push to ``origin/main`` — pushing is
    outside this guard's reach (the guard only ever commits locally).
    """

    STANDARD = "standard"
    RELEASE_FLOW = "release_flow"
    UPGRADE_BOOKKEEPING = "upgrade_bookkeeping"
    MERGE_BOOKKEEPING = "merge_bookkeeping"
    TEST_MODE = "test_mode"


# Capabilities that authorize landing a bookkeeping commit on a *protected* ref.
# STANDARD is intentionally absent: a standard commit to a protected ref is only
# allowed when the ref is the resolved placement (i.e. not protected here).
_PROTECTED_FLOW_CAPABILITIES = frozenset(
    {
        GuardCapability.RELEASE_FLOW,
        GuardCapability.UPGRADE_BOOKKEEPING,
        GuardCapability.MERGE_BOOKKEEPING,
        GuardCapability.TEST_MODE,
    }
)


@dataclass(frozen=True)
class ProtectionState:
    """Whether the destination ref is a protected branch.

    A pure value object so :func:`evaluate` stays free of I/O: the caller probes
    the repository (``protected_branches`` in ``git/commit_helpers.py``) and
    hands the result in. ``evaluate`` makes no git/env/filesystem calls.
    """

    is_protected: bool


@dataclass(frozen=True)
class GuardVerdict:
    """The result of :func:`evaluate` — distinct from ``merge_gates.GateVerdict``.

    ``resolved_destination`` always echoes :attr:`CommitTarget.ref` (C-GUARD-3a);
    ``reason`` names that destination on refusal so the operator sees where the
    commit *would* have gone — never a pre-lanes "switch to the lane branch"
    instruction.
    """

    allowed: bool
    resolved_destination: str
    reason: str


def evaluate(
    target: CommitTarget,
    protection_state: ProtectionState,
    capability: GuardCapability = GuardCapability.STANDARD,
) -> GuardVerdict:
    """Decide whether a commit to ``target`` is allowed — the ONLY protection decision.

    Pure: no I/O beyond the inputs provided. The resolved destination is ALWAYS
    :attr:`target.ref` (echoed, never re-derived — C-GUARD-3a).

    Decision:

    * If the destination is NOT protected → allowed (the placement is the
      resolved destination; this covers every ordinary lane/coord commit).
    * If the destination IS protected → allowed ONLY when ``capability`` is one
      of the protected-flow bookkeeping capabilities. ``STANDARD`` is refused;
      message text, file content, and env play no part.

    No capability can authorize a direct push to ``origin/main`` — this function
    never decides a push, and ``safe_commit`` never performs one.

    Args:
        target: The single resolved destination (``mission_runtime.context``).
        protection_state: Whether ``target.ref`` is a protected branch.
        capability: Asserted-at-the-surface authorization. Defaults to
            :attr:`GuardCapability.STANDARD`.

    Returns:
        A :class:`GuardVerdict` whose ``resolved_destination`` echoes
        ``target.ref``.
    """
    destination = target.ref

    if not protection_state.is_protected:
        return GuardVerdict(
            allowed=True,
            resolved_destination=destination,
            reason=(
                f"destination {destination!r} is the resolved placement and is "
                f"not a protected branch"
            ),
        )

    if capability in _PROTECTED_FLOW_CAPABILITIES:
        return GuardVerdict(
            allowed=True,
            resolved_destination=destination,
            reason=(
                f"capability {capability.value!r} authorizes the bookkeeping "
                f"flow onto protected branch {destination!r}"
            ),
        )

    return GuardVerdict(
        allowed=False,
        resolved_destination=destination,
        reason=(
            f"refusing to commit to protected branch {destination!r}: capability "
            f"{capability.value!r} authorizes no protected-branch flow. Land the "
            f"commit on the resolved placement ({destination!r}) only when it is "
            f"not protected, or pass an explicit bookkeeping capability for the "
            f"release / upgrade / merge flow."
        ),
    )
