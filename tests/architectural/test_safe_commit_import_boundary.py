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
``docs/adr/3.x/2026-06-03-2-executioncontext-owner-and-committarget.md``.

coord-write-placement-closure-01KYCF83 WP06 (T028 / FR-001) adds a fourth
guarantee: every ``target=CommitTarget(...)`` (or ``CommitTarget(ref=...)``
built standalone) construction, anywhere in ``src/``, is seam-derived. This
file reuses the SAME whole-tree scanner and AST grammar
``test_no_write_side_rederivation.py`` defines (never a second, divergent
implementation) so the C-GUARD-1 import-boundary perspective and the
placement-enforcement gate agree on one detector.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.architectural._placement_whole_tree_scan import is_sanctioned
from tests.architectural._placement_whole_tree_scan import iter_src_modules as _iter_placement_modules
from tests.architectural._placement_whole_tree_scan import rel_path as _placement_rel_path
from tests.architectural.test_no_write_side_rederivation import (
    _CHECKOUT_GRAMMAR_ALLOW_LIST,
    _scan_checkout_grammar,
)

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
_SAFE_COMMIT_MODULE = "specify_cli.git.commit_helpers"
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
_ALLOWLISTED_DESTINATION_REF_SAFE_COMMIT_SITES: frozenset[str] = frozenset()
# Previously held cli/commands/merge.py → merge/executor.py. The last production
# `safe_commit(destination_ref=...)` caller (the merge done-transitions
# bookkeeping) was migrated to `target=CommitTarget(...)` when it was factored
# into the shared `git/bookkeeping_commit.py` seam (#2280 / PR #2281). No
# production caller uses the two-arg shim anymore; the empty allowlist means ANY
# new `destination_ref=` caller now fails this ratchet.


def _iter_src_python_files() -> list[Path]:
    return sorted(p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _dotted_name(node: ast.expr) -> str | None:
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _source_imports_or_calls_evaluate(source: str) -> bool:
    """Detect direct and module-aliased access to commit-guard ``evaluate``."""
    tree = ast.parse(source)
    module_aliases: set[str] = set()
    decision_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == _COMMIT_GUARD_MODULE:
                decision_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name in {_DECISION_SYMBOL, "*"}
                )
            elif node.module == "specify_cli.core":
                module_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "commit_guard"
                )
        elif isinstance(node, ast.Import):
            module_aliases.update(
                alias.asname
                for alias in node.names
                if alias.name == _COMMIT_GUARD_MODULE and alias.asname
            )
    if decision_aliases:
        return True
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        dotted = _dotted_name(node)
        if dotted is None:
            continue
        if dotted == f"{_COMMIT_GUARD_MODULE}.{_DECISION_SYMBOL}":
            return True
        prefix, _, symbol = dotted.rpartition(".")
        if symbol == _DECISION_SYMBOL and prefix in module_aliases:
            return True
    return False


def _module_imports_evaluate(path: Path) -> bool:
    return _source_imports_or_calls_evaluate(path.read_text(encoding="utf-8"))


def _safe_commit_import_aliases(tree: ast.Module) -> tuple[set[str], set[str]]:
    module_aliases: set[str] = set()
    safe_commit_aliases: set[str] = {"safe_commit"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == _SAFE_COMMIT_MODULE:
                safe_commit_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "safe_commit"
                )
            elif node.module == "specify_cli.git":
                module_aliases.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "commit_helpers"
                )
        elif isinstance(node, ast.Import):
            module_aliases.update(
                alias.asname
                for alias in node.names
                if alias.name == _SAFE_COMMIT_MODULE and alias.asname
            )
    return module_aliases, safe_commit_aliases


def _is_safe_commit_ref(
    expr: ast.expr, module_aliases: set[str], safe_commit_aliases: set[str]
) -> bool:
    dotted = _dotted_name(expr)
    if dotted in safe_commit_aliases:
        return True
    if dotted == f"{_SAFE_COMMIT_MODULE}.safe_commit":
        return True
    if dotted is None:
        return False
    prefix, _, symbol = dotted.rpartition(".")
    return symbol == "safe_commit" and prefix in module_aliases


def _propagate_safe_commit_rebindings(
    tree: ast.Module, module_aliases: set[str], safe_commit_aliases: set[str]
) -> None:
    def is_ref(expr: ast.expr) -> bool:
        return _is_safe_commit_ref(expr, module_aliases, safe_commit_aliases)

    while True:
        rebound: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and is_ref(node.value):
                rebound.update(
                    target.id for target in node.targets if isinstance(target, ast.Name)
                )
            elif (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.value is not None
                and is_ref(node.value)
            ):
                rebound.add(node.target.id)
        rebound -= safe_commit_aliases
        if not rebound:
            break
        safe_commit_aliases |= rebound


def _source_calls_safe_commit_destination_ref(source: str) -> bool:
    """Detect direct, module-aliased, and rebound legacy ``safe_commit`` calls."""
    tree = ast.parse(source)
    module_aliases, safe_commit_aliases = _safe_commit_import_aliases(tree)
    _propagate_safe_commit_rebindings(tree, module_aliases, safe_commit_aliases)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not any(kw.arg == "destination_ref" for kw in node.keywords):
            continue
        if _is_safe_commit_ref(node.func, module_aliases, safe_commit_aliases):
            return True
    return False


def _safe_commit_destination_ref_call_sites(path: Path) -> bool:
    """True iff ``path`` calls ``safe_commit(..., destination_ref=...)``.

    Direct imports, aliases, and module-qualified calls are inspected; other
    functions that take ``destination_ref`` remain out of scope.
    """
    return _source_calls_safe_commit_destination_ref(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "source",
    [
        "from specify_cli.core.commit_guard import evaluate as decide\ndecide(None)",
        "import specify_cli.core.commit_guard as guard\nguard.evaluate(None)",
        "from specify_cli.core import commit_guard as guard\nguard.evaluate(None)",
        "import specify_cli.core.commit_guard\nspecify_cli.core.commit_guard.evaluate(None)",
        "import specify_cli.core.commit_guard as guard\n"
        "decide = guard.evaluate\ndecide(None)",
    ],
)
def test_evaluate_scanner_rejects_every_supported_import_shape(source: str) -> None:
    assert _source_imports_or_calls_evaluate(source)


@pytest.mark.parametrize(
    "source",
    [
        "import specify_cli.git.commit_helpers as commits\n"
        "commits.safe_commit(repo, destination_ref='main')",
        "from specify_cli.git import commit_helpers as commits\n"
        "commits.safe_commit(repo, destination_ref='main')",
        "from specify_cli.git.commit_helpers import safe_commit as commit\n"
        "commit(repo, destination_ref='main')",
        "import specify_cli.git.commit_helpers as commits\n"
        "commit = commits.safe_commit\ncommit(repo, destination_ref='main')",
        "from specify_cli.git.commit_helpers import safe_commit as commit\n"
        "rebound = commit\nrebound(repo, destination_ref='main')",
    ],
)
def test_safe_commit_scanner_rejects_attribute_and_alias_forms(source: str) -> None:
    assert _source_calls_safe_commit_destination_ref(source)


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


def test_safe_commit_target_argument_is_seam_derived() -> None:
    """WP06 / T028 / FR-001: every ``target=CommitTarget(...)`` construction is
    seam-derived, not checkout-derived.

    Reuses the SHARED whole-tree scanner (``_placement_whole_tree_scan``) and
    the shared AST grammar (``test_no_write_side_rederivation._scan_checkout_grammar``
    + its ``_CHECKOUT_GRAMMAR_ALLOW_LIST``) — this is a companion assertion
    from the C-GUARD-1 import-boundary file's perspective, not a second,
    divergent detector. A ``CommitTarget(...)``/``safe_commit(...,
    destination_ref=...)`` construction that is neither seam-derived nor
    allow-listed is exactly the split-brain root C-GUARD-1 and the placement
    seam both exist to close.
    """
    offenders: list[str] = []
    for module in _iter_placement_modules():
        rel = _placement_rel_path(module)
        if is_sanctioned(rel):
            continue
        source = module.read_text(encoding="utf-8")
        for finding in _scan_checkout_grammar(source, module):
            if finding.as_allow_key() in _CHECKOUT_GRAMMAR_ALLOW_LIST:
                continue
            offenders.append(
                f"{rel}:{finding.lineno} {finding.callee}(...) constructs a ref "
                "from a non-seam-derived expression — route it through "
                "placement_seam(...).write_target(kind) or allow-list it in "
                "test_no_write_side_rederivation.py with a tracked rationale"
            )

    assert not offenders, (
        "safe_commit(target=CommitTarget(...)) construction not seam-derived "
        "(WP06 / T028 / FR-001). Offenders:\n" + "\n".join(offenders)
    )
