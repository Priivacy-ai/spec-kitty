"""Architectural guardrail (WP10 / #1355): the C-GUARD-1 import boundary.

After missions 01KTPKST + 01KTRC04 converted every commit-creating surface
onto the blessed entry point, this ratchet becomes the *permanent* C-GUARD-1
enforcement (FR-009, contracts/C-GUARD-1, NFR-004):

1.  **Single decision authority.** The protected-branch decision lives in
    exactly one place — ``core.commit_guard.evaluate`` — and is imported by
    exactly two production surfaces: the ``git.commit_helpers`` facade (which
    runs it on every commit path) and ``coordination.policy`` (which
    legitimately delegates its protected-branch verdict to the same function).
    Any third importer either re-implements the decision or smuggles it into a
    new surface — both are regressions.

2.  **No resurrected privilege channels.** WP03 DELETED the five legacy
    privilege channels that derived authorization from message text, file
    content, env, or completed-op records. They must not reappear anywhere in
    ``src/``; the asserted-at-the-surface ``GuardCapability`` replaced them.

3.  **No new two-arg compat callers.** ``safe_commit`` retains a ``destination_ref=``
    string compat shim (it builds a ``CommitTarget`` internally). Exactly one
    production call site still uses that shim — ``cli/commands/merge.py`` — a
    documented WP03-review deferral. Every other caller passes the canonical
    ``target=CommitTarget(...)``. A NEW ``destination_ref=`` caller must fail
    this ratchet so the shim cannot regrow a userbase before it is retired.

Spec source: FR-009, NFR-004, contracts/C-GUARD-1; ticket #1355; ADR
``architecture/3.x/adr/2026-06-03-2-executioncontext-owner-and-committarget.md``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"


# ---------------------------------------------------------------------------
# (1) Blessed importers of the ONE decision: ``core.commit_guard.evaluate``.
# ---------------------------------------------------------------------------
#
# ``GuardCapability`` / ``ProtectionState`` / ``GuardVerdict`` are public value
# types and may be imported freely (they carry no decision). It is the
# ``evaluate`` *function* — the actual protected-branch verdict — whose import
# surface is locked down to the blessed set below.
_COMMIT_GUARD_MODULE = "specify_cli.core.commit_guard"
_DECISION_SYMBOL = "evaluate"
_BLESSED_EVALUATE_IMPORTERS: frozenset[str] = frozenset(
    {
        # The C-GUARD-1 facade: runs evaluate on every safe_commit() path.
        "src/specify_cli/git/commit_helpers.py",
        # Coordination policy legitimately delegates its protected-branch
        # verdict to the same evaluate() (commit_helpers comment + policy.py
        # line ~201 document the delegation). It does NOT re-implement.
        "src/specify_cli/coordination/policy.py",
    }
)


# ---------------------------------------------------------------------------
# (2) Five legacy privilege channels DELETED by WP03. Zero references in src/.
# ---------------------------------------------------------------------------
_DELETED_CHANNEL_SYMBOLS: tuple[str, ...] = (
    "_is_protected_branch_exception",
    "allow_protected_branch_in_test_mode",
    "allow_completed_op_on_protected_branch",
    "_is_completed_op_record_exception",
    "_test_mode_allows_protected_branch",
)


# ---------------------------------------------------------------------------
# (3) Allowlisted legacy ``safe_commit(destination_ref=...)`` shim call sites.
# ---------------------------------------------------------------------------
#
# WP03-review documented deferral: these sites still pass the two-arg
# ``destination_ref=`` string instead of ``target=CommitTarget(...)``. The shim
# builds a PRIMARY CommitTarget internally. Follow-up: migrate to ``target=``
# and delete the shim (tracked alongside #1355 spine closure). Any NEW
# ``destination_ref=`` caller is a regression and must fail this ratchet.
#
# NOTE: ``cli/commands/implement.py`` ALSO passes ``destination_ref=`` — but to
# ``BookkeepingTransaction.acquire(...)``, NOT to ``safe_commit``. The transaction
# layer's ``destination_ref=`` is its canonical parameter and is out of scope
# here; this ratchet only inspects direct ``safe_commit`` calls.
_ALLOWLISTED_DESTINATION_REF_SAFE_COMMIT_SITES: frozenset[str] = frozenset(
    {
        # Relocated from cli/commands/merge.py to the merge/executor.py seam in
        # mission #2057's behavior-preserving god-module decomposition.
        "src/specify_cli/merge/executor.py",
    }
)


def _iter_src_python_files() -> list[Path]:
    return sorted(p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _module_imports_evaluate(path: Path) -> bool:
    """True iff ``path`` imports ``evaluate`` from ``core.commit_guard``.

    Catches both ``from ... import evaluate`` and the
    ``from ... import evaluate as evaluate_commit_guard`` alias form.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != _COMMIT_GUARD_MODULE:
            continue
        for alias in node.names:
            if alias.name == _DECISION_SYMBOL:
                return True
    return False


def _safe_commit_destination_ref_call_sites(path: Path) -> bool:
    """True iff ``path`` calls ``safe_commit(..., destination_ref=...)``.

    Only direct ``safe_commit`` calls are inspected; calls to other functions
    that happen to take a ``destination_ref`` keyword (e.g.
    ``BookkeepingTransaction.acquire``) are deliberately ignored.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Name)
            and func.id == "safe_commit"
            and any(kw.arg == "destination_ref" for kw in node.keywords)
        ):
            return True
    return False


def test_evaluate_has_exactly_the_blessed_importers() -> None:
    """``core.commit_guard.evaluate`` is imported only by the blessed surfaces.

    A new importer means either a re-implemented decision or the decision
    smuggled into a new commit surface — both regress C-GUARD-1's
    single-authority guarantee.
    """
    actual: set[str] = set()
    for path in _iter_src_python_files():
        if _module_imports_evaluate(path):
            actual.add(_rel(path))

    blessed = set(_BLESSED_EVALUATE_IMPORTERS)
    unexpected = actual - blessed
    missing = blessed - actual

    assert not unexpected, (
        "Unexpected importer(s) of core.commit_guard.evaluate: "
        f"{sorted(unexpected)}. The protected-branch decision (C-GUARD-1) has "
        "exactly one authority; new surfaces must call the git.commit_helpers "
        "facade (safe_commit), not evaluate() directly. If this is a "
        "legitimate new delegate, add it to _BLESSED_EVALUATE_IMPORTERS with a "
        "rationale comment."
    )
    assert not missing, (
        "Blessed importer(s) of core.commit_guard.evaluate disappeared: "
        f"{sorted(missing)}. If a surface was intentionally removed, drop it "
        "from _BLESSED_EVALUATE_IMPORTERS."
    )


@pytest.mark.parametrize("symbol", _DELETED_CHANNEL_SYMBOLS)
def test_deleted_privilege_channels_have_zero_references(symbol: str) -> None:
    """None of WP03's five deleted privilege channels reappear in ``src/``.

    These channels derived authorization from message text, file content, env,
    or completed-op records. They were replaced by the asserted-at-the-surface
    ``GuardCapability`` (FR-008). Any textual reference — import, call, or
    definition — is a resurrection and a C-GUARD-2 regression.
    """
    offenders: list[str] = []
    for path in _iter_src_python_files():
        if symbol in path.read_text(encoding="utf-8"):
            offenders.append(_rel(path))
    assert not offenders, (
        f"Deleted privilege channel {symbol!r} reappears in: {sorted(offenders)}. "
        "WP03 deleted the five legacy channels; authorization is now an "
        "explicit GuardCapability asserted by the caller. Do not reintroduce "
        "content/message/env/op-record derived authorization."
    )


def test_safe_commit_destination_ref_shim_is_allowlisted() -> None:
    """Only allowlisted sites may call ``safe_commit(destination_ref=...)``.

    Every other caller passes ``target=CommitTarget(...)``. A new
    ``destination_ref=`` caller must fail so the legacy shim cannot regrow a
    userbase before it is retired.
    """
    actual: set[str] = set()
    for path in _iter_src_python_files():
        if _safe_commit_destination_ref_call_sites(path):
            actual.add(_rel(path))

    allowlist = set(_ALLOWLISTED_DESTINATION_REF_SAFE_COMMIT_SITES)
    unexpected = actual - allowlist
    stale = allowlist - actual

    assert not unexpected, (
        "Unexpected safe_commit(destination_ref=...) call site(s): "
        f"{sorted(unexpected)}. Pass target=CommitTarget(ref=..., kind=...) "
        "instead — the two-arg destination_ref shim is a documented WP03-review "
        "deferral and is being retired, not extended."
    )
    assert not stale, (
        "Allowlisted destination_ref shim site(s) no longer use the shim: "
        f"{sorted(stale)}. Remove them from "
        "_ALLOWLISTED_DESTINATION_REF_SAFE_COMMIT_SITES — the shim is one "
        "caller closer to deletion."
    )
