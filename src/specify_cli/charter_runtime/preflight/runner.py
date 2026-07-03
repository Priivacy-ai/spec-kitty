"""Runner for ``spec-kitty charter preflight`` (FR-006, FR-007, FR-008).

This module exposes a single public callable :func:`run_charter_preflight`
that:

1. Asks WP02's :func:`specify_cli.charter_runtime.freshness.compute_freshness` for
   the current freshness payload.
2. Translates each :class:`FreshnessSubState` into a
   :class:`CharterPreflightCheck`.
3. Optionally runs the safe refresh sequence
   (``charter sync`` → ``charter synthesize`` → ``charter bundle
   validate``) when the caller passes ``auto_refresh=True`` AND the
   worktree has no uncommitted generated artifacts (FR-008).
4. Returns a frozen :class:`CharterPreflightResult` whose
   ``blocked_reason`` always points the operator at one exact recovery
   command.

Performance contract (NFR-001):

* warm path (everything fresh) — < 300 ms;
* cold path (refresh runs) — < 1 s;
* dirty-detection (``git status --porcelain -- .kittify/charter/
  .kittify/doctrine/``) — < 100 ms on a clean tree.

The runner MUST NOT raise on filesystem or subprocess errors — every
failure produces a result with a sensible ``blocked_reason``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from specify_cli.charter_runtime.freshness import compute_freshness

from .result import CharterPreflightCheck, CharterPreflightResult

if TYPE_CHECKING:  # pragma: no cover — used only for type hints.
    from specify_cli.charter_runtime.freshness import CharterFreshness

__all__ = ["run_charter_preflight"]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# Layer ordering is part of the contract — consumers MAY index by name but
# humans scanning ``--json`` output rely on this order.
_LAYER_ORDER: tuple[tuple[str, str], ...] = (
    ("charter_source", "charter source"),
    ("synced_bundle", "synced bundle"),
    ("synthesized_drg", "synthesized DRG"),
)

# Passing states — see contracts/charter-preflight-json.md "State semantics".
_PASS_STATES: frozenset[str] = frozenset({"fresh", "skipped", "built_in_only"})

_FRESH_PROJECT_MISSING_CHARTER_WARNING = (
    "project charter is not initialized; run `spec-kitty charter generate` "
    "when this project is ready for charter-governed workflows"
)

# Refresh-step timeout.  Overridable via env so very slow CI runners can
# extend the deadline without code changes (risk note in WP03 spec).
_REFRESH_TIMEOUT_ENV = "SPEC_KITTY_PREFLIGHT_TIMEOUT_SECS"
_REFRESH_TIMEOUT_DEFAULT = 30.0

# git-status timeout — kept tight; NFR-001 wants this <100 ms on a clean
# tree, so a 5 s ceiling is purely a defensive cap against frozen FUSE
# mounts / hung antivirus hooks.
_GIT_STATUS_TIMEOUT_SECS = 5.0

# Paths whose dirty-state blocks auto-refresh.  Per FR-008 we name the
# directories rather than individual files so future additions under
# ``.kittify/charter/`` or ``.kittify/doctrine/`` are covered automatically.
_DIRTY_SCOPE_PATHS: tuple[str, ...] = (
    ".kittify/charter/",
    ".kittify/doctrine/",
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_charter_preflight(
    repo_root: Path,
    *,
    auto_refresh: bool = False,
    allow_missing_charter: bool = False,
    strict: bool = False,  # noqa: ARG001 — surfaced for caller symmetry; consumed by CLI exit-code mapping, not by the runner itself.
) -> CharterPreflightResult:
    """Compute charter freshness, optionally refresh, return a result.

    Args:
        repo_root: Path to the repository root.  Must contain ``.kittify/``
            for non-trivial results; missing artifacts produce ``missing``
            checks rather than exceptions.
        auto_refresh: When ``True`` AND the worktree has no uncommitted
            generated artifacts, attempt the safe refresh sequence.
        allow_missing_charter: Treat a fully absent charter stack as advisory.
            Read-only/dashboard consumers may enable this for fresh projects;
            mutation gates leave it disabled so missing governance still fails
            closed when the workflow requires charter-derived state.
        strict: Accepted for API symmetry with the CLI flag.  The runner
            itself does not change behaviour based on ``strict`` — the CLI
            wrapper translates ``passed=False`` + ``strict=True`` into exit
            code 1.  Kept in the signature so callers (``spec-kitty next``,
            ``implement``, dashboard) can forward their own ``strict``
            config without an extra branch.

    Returns:
        A frozen :class:`CharterPreflightResult`.  Never raises.
    """
    freshness = compute_freshness(repo_root)
    checks = _build_checks(freshness)

    if allow_missing_charter and _is_optional_missing_charter_fresh_project(checks):
        return CharterPreflightResult(
            passed=True,
            checks=[
                CharterPreflightCheck(
                    name=c.name,
                    state="skipped",
                    detail="project charter is not initialized",
                    remediation=None,
                )
                for c in checks
            ],
            auto_refresh_applied=False,
            auto_refresh_actions=[],
            blocked_reason=None,
            warnings=[_FRESH_PROJECT_MISSING_CHARTER_WARNING],
        )

    passed = all(c.state in _PASS_STATES for c in checks)

    if passed:
        return CharterPreflightResult(
            passed=True,
            checks=checks,
            auto_refresh_applied=False,
            auto_refresh_actions=[],
            blocked_reason=None,
        )

    # Failure path.  Either refresh, or block.
    if auto_refresh:
        return _attempt_auto_refresh(repo_root, freshness, checks)

    blocked_reason = _derive_blocked_reason(checks)
    return CharterPreflightResult(
        passed=False,
        checks=checks,
        auto_refresh_applied=False,
        auto_refresh_actions=[],
        blocked_reason=blocked_reason,
    )


# ---------------------------------------------------------------------------
# Helpers — check construction
# ---------------------------------------------------------------------------


def _build_checks(freshness: CharterFreshness) -> list[CharterPreflightCheck]:
    """Convert the WP02 freshness payload into preflight checks.

    Mapping rules:

    * ``state`` is copied through directly.
    * ``detail`` is the WP02 ``detail`` when present, otherwise a synthesised
      human-readable string of the form ``"<layer> is <state>"``.
    * ``remediation`` is copied from WP02 (``None`` when no action is
      required).
    """
    result: list[CharterPreflightCheck] = []
    payload = freshness.to_dict()
    for layer_key, layer_label in _LAYER_ORDER:
        sub = payload[layer_key]
        state = str(sub.get("state", "missing"))
        detail = sub.get("detail") or _default_detail(layer_label, state, sub.get("last_change"))
        remediation = sub.get("remediation")
        result.append(
            CharterPreflightCheck(
                name=layer_key,
                state=state,  # type: ignore[arg-type]
                detail=str(detail),
                remediation=str(remediation) if remediation else None,
            )
        )
    return result


def _is_optional_missing_charter_fresh_project(checks: list[CharterPreflightCheck]) -> bool:
    """Return True for a never-initialized charter stack.

    Missing project charter is optional in a fresh project.  Treat only the
    fully absent stack as advisory; partial/generated residue still blocks so
    stale charter state remains visible.
    """
    states = {c.name: c.state for c in checks}
    return states == {
        "charter_source": "missing",
        "synced_bundle": "missing",
        "synthesized_drg": "missing",
    }


def _default_detail(label: str, state: str, last_change: str | None) -> str:
    """Build a fallback detail string when WP02 does not supply one."""
    base = f"{label} is {state}"
    if last_change:
        return f"{base} (last_change={last_change})"
    return base


def _derive_blocked_reason(checks: list[CharterPreflightCheck]) -> str:
    """Pick the first non-passing check and build a blocked_reason.

    The returned string MUST include an actionable command (per the
    contract) — we use the check's own ``remediation`` when present, or
    fall back to ``spec-kitty charter status`` so the operator at least
    sees the diagnostic.
    """
    for check in checks:
        if check.state in _PASS_STATES:
            continue
        remediation = check.remediation or "spec-kitty charter status"
        return f"{check.name} {check.state}; run `{remediation}`"
    # Should not happen — callers only enter this path when passed=False.
    return "charter preflight failed; run `spec-kitty charter status`"


# ---------------------------------------------------------------------------
# Helpers — uncommitted-artifact detection (FR-008 / T018)
# ---------------------------------------------------------------------------


def _detect_dirty_artifacts(repo_root: Path) -> tuple[bool, list[str], str | None]:
    """Return ``(is_dirty, dirty_paths, error_reason)``.

    Implements the binding detection mechanism documented in
    ``contracts/charter-preflight-json.md`` §"Detection mechanism": a
    single ``git status --porcelain`` invocation scoped to the two
    directories we care about, parsed line-by-line.

    Failure-mode handling:

    * ``FileNotFoundError`` (git missing) → ``error_reason`` =
      ``"git CLI not available; cannot determine worktree cleanliness"``;
      ``is_dirty=False``.
    * ``returncode != 0`` → ``error_reason`` =
      ``"git status failed (exit N): <first stderr line>"``;
      ``is_dirty=False``.
    * Non-empty stdout → ``is_dirty=True``; ``dirty_paths`` lists every
      pathname reported (path component starts at column 4 in porcelain
      v1 output).
    """
    try:
        result = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--",
                *_DIRTY_SCOPE_PATHS,
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=_GIT_STATUS_TIMEOUT_SECS,
            check=False,
        )
    except FileNotFoundError:
        return False, [], "git CLI not available; cannot determine worktree cleanliness"
    except subprocess.TimeoutExpired:
        return False, [], "git status timed out; cannot determine worktree cleanliness"

    if result.returncode != 0:
        stderr_first = ""
        if result.stderr:
            stderr_first = result.stderr.splitlines()[0] if result.stderr.splitlines() else ""
        return (
            False,
            [],
            f"git status failed (exit {result.returncode}): {stderr_first}".rstrip(": "),
        )

    if not result.stdout.strip():
        return False, [], None

    dirty_paths: list[str] = []
    for raw_line in result.stdout.splitlines():
        # Porcelain v1: ``XY <path>`` where ``XY`` is exactly two status
        # chars + a space.  Slicing at index 3 is the documented contract.
        if len(raw_line) <= 3:
            continue
        dirty_paths.append(raw_line[3:].strip())
    return True, dirty_paths, None


# ---------------------------------------------------------------------------
# Helpers — auto-refresh (T019)
# ---------------------------------------------------------------------------


def _refresh_timeout_secs() -> float:
    """Resolve the per-step refresh timeout from env, falling back to 30 s."""
    raw = os.environ.get(_REFRESH_TIMEOUT_ENV)
    if not raw:
        return _REFRESH_TIMEOUT_DEFAULT
    try:
        value = float(raw)
    except ValueError:
        return _REFRESH_TIMEOUT_DEFAULT
    if value <= 0:
        return _REFRESH_TIMEOUT_DEFAULT
    return value


def _attempt_auto_refresh(
    repo_root: Path,
    freshness: CharterFreshness,
    initial_checks: list[CharterPreflightCheck],
) -> CharterPreflightResult:
    """Run the safe refresh sequence, honouring FR-008 cleanliness.

    The sequence is:

    1. ``spec-kitty charter sync`` — skipped iff both ``charter_source``
       and ``synced_bundle`` are already ``fresh``.
    2. ``spec-kitty charter synthesize`` — skipped iff ``synthesized_drg``
       is already ``fresh``.
    3. ``spec-kitty charter bundle validate`` — always run when we reach
       this branch.

    On any non-zero exit, we stop, surface the failing command's first
    stderr line via ``blocked_reason``, and mark
    ``auto_refresh_applied=True`` so callers know an attempt was made
    even when it failed.
    """
    is_dirty, dirty_paths, dirty_error = _detect_dirty_artifacts(repo_root)

    if dirty_error is not None:
        return CharterPreflightResult(
            passed=False,
            checks=initial_checks,
            auto_refresh_applied=False,
            auto_refresh_actions=[],
            blocked_reason=dirty_error,
        )

    if is_dirty:
        annotated = _annotate_dirty(initial_checks, dirty_paths)
        return CharterPreflightResult(
            passed=False,
            checks=annotated,
            auto_refresh_applied=False,
            auto_refresh_actions=[],
            blocked_reason="uncommitted generated artifacts; commit or stash and retry",
        )

    # Worktree is clean — run the sequence.
    actions: list[str] = []
    timeout_secs = _refresh_timeout_secs()

    source_fresh = freshness.charter_source.state == "fresh"
    bundle_fresh = freshness.synced_bundle.state == "fresh"
    drg_fresh = freshness.synthesized_drg.state == "fresh"

    if not (source_fresh and bundle_fresh):
        sync_cmd = ["spec-kitty", "charter", "sync"]
        ok, reason = _run_refresh_step(sync_cmd, repo_root, timeout_secs)
        actions.append(" ".join(sync_cmd))
        if not ok:
            return CharterPreflightResult(
                passed=False,
                checks=initial_checks,
                auto_refresh_applied=True,
                auto_refresh_actions=actions,
                blocked_reason=reason,
            )

    if not drg_fresh:
        synth_cmd = ["spec-kitty", "charter", "synthesize"]
        ok, reason = _run_refresh_step(synth_cmd, repo_root, timeout_secs)
        actions.append(" ".join(synth_cmd))
        if not ok:
            return CharterPreflightResult(
                passed=False,
                checks=initial_checks,
                auto_refresh_applied=True,
                auto_refresh_actions=actions,
                blocked_reason=reason,
            )

    validate_cmd = ["spec-kitty", "charter", "bundle", "validate"]
    ok, reason = _run_refresh_step(validate_cmd, repo_root, timeout_secs)
    actions.append(" ".join(validate_cmd))
    if not ok:
        return CharterPreflightResult(
            passed=False,
            checks=initial_checks,
            auto_refresh_applied=True,
            auto_refresh_actions=actions,
            blocked_reason=reason,
        )

    # Refresh succeeded — recompute freshness and rebuild checks so
    # callers see the post-refresh state.
    post_freshness = compute_freshness(repo_root)
    post_checks = _build_checks(post_freshness)
    post_passed = all(c.state in _PASS_STATES for c in post_checks)

    return CharterPreflightResult(
        passed=post_passed,
        checks=post_checks,
        auto_refresh_applied=True,
        auto_refresh_actions=actions,
        blocked_reason=None if post_passed else _derive_blocked_reason(post_checks),
    )


def _annotate_dirty(
    checks: list[CharterPreflightCheck],
    dirty_paths: list[str],
) -> list[CharterPreflightCheck]:
    """Append the dirty pathnames to the matching check's ``detail``.

    Per FR-008 and the contract's Safety-rule section: each affected file
    MUST be named in the ``detail`` of the corresponding check.  We bucket
    by directory prefix so ``.kittify/charter/...`` lands on the
    ``charter_source`` / ``synced_bundle`` rows and ``.kittify/doctrine/...``
    on ``synthesized_drg``.
    """
    charter_dirty = [p for p in dirty_paths if p.startswith(".kittify/charter/")]
    doctrine_dirty = [p for p in dirty_paths if p.startswith(".kittify/doctrine/")]

    annotated: list[CharterPreflightCheck] = []
    for c in checks:
        suffix: str | None = None
        if c.name in ("charter_source", "synced_bundle") and charter_dirty:
            suffix = "uncommitted: " + ", ".join(charter_dirty)
        elif c.name == "synthesized_drg" and doctrine_dirty:
            suffix = "uncommitted: " + ", ".join(doctrine_dirty)
        if suffix:
            annotated.append(
                CharterPreflightCheck(
                    name=c.name,
                    state=c.state,
                    detail=f"{c.detail}; {suffix}",
                    remediation=c.remediation,
                )
            )
        else:
            annotated.append(c)
    return annotated


def _run_refresh_step(
    cmd: list[str],
    repo_root: Path,
    timeout_secs: float,
) -> tuple[bool, str | None]:
    """Run one refresh subprocess.

    Returns ``(ok, blocked_reason_or_none)``.  On non-zero exit, the reason
    is the first stderr line, prefixed with the command's tail (e.g.
    ``"charter synthesize failed: <stderr>"``) so the operator can copy the
    fix straight into a terminal.
    """
    label = " ".join(cmd[1:]) if len(cmd) > 1 else cmd[0]
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_secs,
            check=False,
        )
    except FileNotFoundError:
        return False, f"{cmd[0]} not on PATH; cannot run `{' '.join(cmd)}`"
    except subprocess.TimeoutExpired:
        return False, f"`{' '.join(cmd)}` timed out after {timeout_secs:.0f}s"

    if result.returncode == 0:
        return True, None

    stderr_first = ""
    if result.stderr:
        lines = result.stderr.splitlines()
        if lines:
            stderr_first = lines[0]
    if not stderr_first and result.stdout:
        stdout_lines = result.stdout.splitlines()
        if stdout_lines:
            stderr_first = stdout_lines[-1]
    return False, f"{label} failed (exit {result.returncode}): {stderr_first}".rstrip(": ")
