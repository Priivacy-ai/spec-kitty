"""Mode-aware safety predicates for ``dashboard`` and ``doctor`` commands.

This module registers predicates that classify ``dashboard`` and ``doctor``
invocations as SAFE or UNSAFE based on the presence of mutating flags in
``raw_args``.  Read-only invocations (no mutating flags) are always SAFE;
write/kill/fix invocations are UNSAFE under schema mismatch.

Flag discovery (2026-04-27)
---------------------------
``dashboard`` flags inspected:
  - ``--port``   (read-like, selects server port — SAFE)
  - ``--open``   (read-like, opens browser — SAFE)
  - ``--json``   (read-only output — SAFE)
  - ``--kill``   (UNSAFE: stops the running dashboard and clears its metadata
                  on disk, i.e. a write/mutation operation)

``doctor`` subcommands and flags inspected:
  - ``command-files``              read-only — SAFE
  - ``state-roots``                read-only — SAFE
  - ``identity``                   read-only — SAFE
    - ``--json``                   read-only output — SAFE
    - ``--mission``                scoping — SAFE
    - ``--fail-on``                read-only exit-code control — SAFE
  - ``shim-registry``              read-only — SAFE
    - ``--json``                   read-only output — SAFE
  - ``sparse-checkout``            read-only in detection-only mode — SAFE
    - ``--fix``                    UNSAFE: applies git remediation to disk

Adding new mutating flags in the future
---------------------------------------
If a future version of ``dashboard`` or ``doctor`` adds new mutating flags,
append them to the appropriate frozenset below:
  - ``_DASHBOARD_UNSAFE_FLAGS``  for dashboard flags
  - ``_DOCTOR_UNSAFE_FLAGS``     for doctor (sparse-checkout) flags

The predicate is non-breaking by default: an invocation without any of the
listed flags returns SAFE, preserving today's gate behaviour.

Doctor subcommand registration (FIX B, P2)
------------------------------------------
Each doctor subcommand is registered explicitly so that the full command path
(e.g. ``("doctor", "identity")``) matches in the SAFETY_REGISTRY.  Without
explicit entries a subcommand invocation falls through to UNSAFE (fail-closed),
which broke read-only diagnostics under schema mismatch.

``dashboard`` has no subcommands so a single entry for ``("dashboard",)``
with ``_dashboard_predicate`` is sufficient.

Idempotent registration
-----------------------
``register_mode_predicates()`` can be called multiple times safely.
``register_safety`` stores predicates in a plain ``dict``; re-registering a
command path replaces the prior entry without duplication.
"""

from __future__ import annotations

from .safety import Safety, SafetyPredicate, _InvocationProtocol, register_safety

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
# --kill stops the running dashboard and clears its metadata on disk.
# All other dashboard flags (--port, --open, --json) are read-like.
_DASHBOARD_UNSAFE_FLAGS: frozenset[str] = frozenset(
    {
        "--kill",
    }
)


def _dashboard_predicate(invocation: _InvocationProtocol) -> Safety:
    """Return UNSAFE if any dashboard mutating flag is present, else SAFE."""
    if any(flag in invocation.raw_args for flag in _DASHBOARD_UNSAFE_FLAGS):
        return Safety.UNSAFE
    return Safety.SAFE


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------
# sparse-checkout --fix applies git remediation (disk mutation).
# All other doctor flags are read-only diagnostic output controls.
_DOCTOR_UNSAFE_FLAGS: frozenset[str] = frozenset(
    {
        "--fix",
    }
)


def _doctor_predicate(invocation: _InvocationProtocol) -> Safety:
    """Return UNSAFE if any doctor mutating flag is present, else SAFE.

    Used for bare ``doctor`` invocations (no subcommand — prints help/version
    and exits; no disk mutation).  Each subcommand is registered separately
    via ``register_mode_predicates()`` so the full command path matches.
    """
    if any(flag in invocation.raw_args for flag in _DOCTOR_UNSAFE_FLAGS):
        return Safety.UNSAFE
    return Safety.SAFE


def _sparse_checkout_predicate(invocation: _InvocationProtocol) -> Safety:
    """Return UNSAFE if ``--fix`` is present (disk mutation), else SAFE.

    ``doctor sparse-checkout`` without ``--fix`` is detection-only (read-only).
    ``doctor sparse-checkout --fix`` applies git remediation to disk.
    """
    if "--fix" in invocation.raw_args:
        return Safety.UNSAFE
    return Safety.SAFE


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_mode_predicates() -> None:
    """Register dashboard and doctor mode-aware safety predicates.

    Replaces the unconditional ``None`` (always-SAFE) entries seeded in
    ``SAFETY_REGISTRY`` by WP04 with predicates that inspect ``raw_args``
    at classify-time.  Safe by default (no mutating flags → SAFE); only
    the flags listed in ``_DASHBOARD_UNSAFE_FLAGS`` / ``_DOCTOR_UNSAFE_FLAGS``
    trigger UNSAFE classification.

    Doctor subcommands are registered explicitly (FIX B, P2) so that the full
    command path (e.g. ``("doctor", "identity")``) matches in the registry.
    Without these entries a subcommand invocation falls through to UNSAFE
    (fail-closed), blocking read-only diagnostics under schema mismatch.

    ``dashboard`` has no subcommands so a single entry is sufficient.

    Calling this function multiple times is safe: each call replaces the
    prior predicate in-place (no duplicate registrations).
    """
    register_safety(("dashboard",), predicate=_dashboard_predicate)
    # Bare ``doctor`` (no subcommand — prints help, no disk mutation)
    register_safety(("doctor",), predicate=_doctor_predicate)
    # Doctor subcommands — all read-only except sparse-checkout --fix
    register_safety(("doctor", "command-files"), predicate=None)  # read-only
    register_safety(("doctor", "state-roots"), predicate=None)  # read-only
    register_safety(("doctor", "identity"), predicate=None)  # read-only
    register_safety(("doctor", "shim-registry"), predicate=None)  # read-only
    register_safety(("doctor", "sparse-checkout"), predicate=_sparse_checkout_predicate)  # mode-aware


# Public re-exports for callers that want to import from this module directly.
__all__ = [
    "_DASHBOARD_UNSAFE_FLAGS",
    "_DOCTOR_UNSAFE_FLAGS",
    "_sparse_checkout_predicate",
    "register_mode_predicates",
    "SafetyPredicate",
]
