"""Shared-package boundary invariants for the runtime / events / tracker cutover.

These tests enforce the boundary constraints documented in
``kitty-specs/shared-package-boundary-cutover-01KQ22DS/spec.md``:

* **R1 / C-001 / FR-001, FR-002**: No production module under ``src/`` may
  import :mod:`spec_kitty_runtime` (top-level, sub-module, or lazy). The
  runtime PyPI surface is retired in this mission; the internalized runtime
  at ``src/specify_cli/next/_internal_runtime/`` is the only authoritative
  source.

* **R2 / C-002 / FR-003, FR-004**: No production module under ``src/`` may
  import :mod:`specify_cli.spec_kitty_events`. The vendored tree was deleted
  in WP05 (``src/specify_cli/spec_kitty_events/`` no longer exists); all
  consumers import :mod:`spec_kitty_events` from the PyPI package. The rule
  guards against any future re-introduction of the vendored path.

* **R3 / C-003 / FR-005**: ``specify_cli.tracker`` is the CLI-internal
  adapter package; it MUST NOT re-export the public PyPI tracker surface.
  Consumers must import ``from spec_kitty_tracker import X`` directly at
  the call site (see ``contracts/tracker_consumer_surface.md``).

NFR-006 caps total architectural-test runtime at ≤30 seconds. These rules
run in well under that budget on the post-WP02 tree.

See ADR 2026-03-27-1 for the pytestarch infrastructure rationale, and
``tests/architectural/test_layer_rules.py`` for the canonical layer-rule
patterns used here.
"""
from __future__ import annotations

import ast
import importlib.util
import textwrap
from pathlib import Path

import pytest
from pytestarch import Rule, get_evaluable_architecture
from pytestarch.eval_structure.exceptions import ImpossibleMatch

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"

# Production package roots that MUST stay free of retired imports. Mirrors
# the layer definitions in tests/architectural/conftest.py::landscape.
_PRODUCTION_PACKAGE_REGEX = r"^src\.(specify_cli|charter|doctrine|kernel)(\..*)?$"

# Historical exclusion regex retained for reference only: the vendored tree
# under ``src/specify_cli/spec_kitty_events/`` was deleted in WP05, so the
# subtree-suppression term in the regex is now a no-op (no files match).
_PRODUCTION_OUTSIDE_VENDORED_EVENTS_REGEX = (
    r"^src\.(charter|doctrine|kernel|specify_cli(?!\.spec_kitty_events)(\..*)?)$"
)


# ---------------------------------------------------------------------------
# R1 -- C-001 -- FR-001, FR-002
# ---------------------------------------------------------------------------


class TestNoProductionImportsOfSpecKittyRuntime:
    """R1: production modules MUST NOT import :mod:`spec_kitty_runtime`."""

    def test_pytestarch_rule(self, evaluable) -> None:
        """Import-graph rule: nothing under src/ imports spec_kitty_runtime.

        pytestarch raises ``ImpossibleMatch`` when the rule subject is not
        present in the evaluable graph at all -- i.e. when no module under
        ``src/`` references ``spec_kitty_runtime`` even transitively. That
        outcome IS the rule passing (the package is absent from the import
        graph because there are zero importers), so we treat it as success.
        """
        rule = (
            Rule()
            .modules_that()
            .have_name_matching(r"^spec_kitty_runtime(\..*)?$")
            .should_not()
            .be_imported_by_modules_that()
            .have_name_matching(_PRODUCTION_PACKAGE_REGEX)
        )
        try:
            rule.assert_applies(evaluable)
        except ImpossibleMatch:
            # Subject absent from the graph -> no importers -> rule satisfied.
            pass

    def test_ast_scan_catches_lazy_imports(self) -> None:
        """AST scan: catch lazy / function-scoped imports pytestarch may miss.

        Per ADR 2026-03-27-1, pytestarch handles top-level imports via the
        import graph; for lazy patterns (``def f(): import X``) we double up
        with an AST walk so the rule catches every form.
        """
        offenders = _ast_scan_for_imports(
            roots=[_SRC / "specify_cli", _SRC / "charter", _SRC / "doctrine", _SRC / "kernel"],
            forbidden_prefix="spec_kitty_runtime",
            # The internalized runtime documents (in module docstrings and
            # comments) that it replaces ``spec_kitty_runtime``; those are
            # docstring matches, not real imports, and the AST walker only
            # inspects ``Import`` / ``ImportFrom`` nodes so they are
            # naturally excluded.
        )
        assert not offenders, (
            "Production modules import the retired spec_kitty_runtime PyPI "
            f"surface (R1 / C-001 violation):\n  - "
            + "\n  - ".join(f"{path}:{lineno} -> {target}" for path, lineno, target in offenders)
            + "\nUse src/specify_cli/next/_internal_runtime/ instead."
        )

    def test_injection_proves_rule_is_real(self, tmp_path: Path) -> None:
        """Inject a real import and confirm the AST scan catches it.

        Proves the R1 enforcement is not a no-op: when a synthetic
        ``from spec_kitty_runtime import _x`` is planted in a temp module,
        the AST scan reports the offender. This is the regression-trap
        called out in ADR 2026-03-27-1 risks.
        """
        injected_file = tmp_path / "synthetic_violation.py"
        injected_file.write_text(
            textwrap.dedent(
                """
                # Synthetic R1 violator -- proves the rule has teeth.
                from spec_kitty_runtime import _read_snapshot  # noqa: F401
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        offenders = _ast_scan_for_imports(
            roots=[tmp_path],
            forbidden_prefix="spec_kitty_runtime",
        )
        assert offenders, "Injection test failed: AST scanner did not catch the violation."
        assert any(target.startswith("spec_kitty_runtime") for _, _, target in offenders)


# ---------------------------------------------------------------------------
# R2 -- C-002 -- FR-003, FR-004
# ---------------------------------------------------------------------------


class TestNoProductionImportsOfVendoredEvents:
    """R2: production modules outside the vendored tree MUST NOT import it."""

    def test_ast_scan_catches_vendored_imports(self) -> None:
        """AST scan: production code must not import
        ``specify_cli.spec_kitty_events.*``.

        After WP04's consumer cutover and WP05's tree deletion, every CLI
        module reaches events through the public ``spec_kitty_events`` PyPI
        package and the vendored path no longer exists on disk. This rule
        guards against any future re-introduction of the deleted tree.

        We use AST scanning (rather than pytestarch's ``be_imported_by``
        matcher) because pytestarch's importer-side regex filter does not
        give exact path-rooted coverage in the rule-violation report.
        """
        production_roots = [
            _SRC / "charter",
            _SRC / "doctrine",
            _SRC / "kernel",
        ]
        offenders: list[tuple[str, int, str]] = []
        for path, lineno, target in _ast_scan_for_imports(
            roots=production_roots,
            forbidden_prefix="specify_cli.spec_kitty_events",
        ):
            offenders.append((path, lineno, target))

        specify_cli_root = _SRC / "specify_cli"
        vendored_root = specify_cli_root / "spec_kitty_events"
        if specify_cli_root.exists():
            for py_file in specify_cli_root.rglob("*.py"):
                if "__pycache__" in py_file.parts:
                    continue
                try:
                    py_file.relative_to(vendored_root)
                    continue
                except ValueError:
                    pass
                try:
                    source = py_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                try:
                    tree = ast.parse(source, filename=str(py_file))
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if _matches_dotted_prefix(
                                alias.name, "specify_cli.spec_kitty_events"
                            ):
                                offenders.append((str(py_file), node.lineno, alias.name))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and _matches_dotted_prefix(
                            node.module, "specify_cli.spec_kitty_events"
                        ):
                            offenders.append((str(py_file), node.lineno, node.module))

        assert not offenders, (
            "Production modules outside the vendored events tree import "
            "specify_cli.spec_kitty_events (R2 / C-002 violation):\n  - "
            + "\n  - ".join(f"{path}:{lineno} -> {target}" for path, lineno, target in offenders)
            + "\nUse the spec_kitty_events PyPI package instead."
        )

    def test_injection_proves_rule_is_real(self, tmp_path: Path) -> None:
        """Inject a vendored-events import and confirm the AST scanner flags it.

        Proves the AST detection works regardless of the live import-graph
        state, so the rule still has teeth after the vendored tree's deletion.
        """
        injected_file = tmp_path / "synthetic_violation.py"
        injected_file.write_text(
            textwrap.dedent(
                """
                # Synthetic R2 violator -- proves the rule has teeth.
                from specify_cli.spec_kitty_events.models import Event  # noqa: F401
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        offenders = _ast_scan_for_imports(
            roots=[tmp_path],
            forbidden_prefix="specify_cli.spec_kitty_events",
        )
        assert offenders, "Injection test failed: AST scanner did not catch the violation."
        assert any(target.startswith("specify_cli.spec_kitty_events") for _, _, target in offenders)


# ---------------------------------------------------------------------------
# R3 -- C-003 -- FR-005
# ---------------------------------------------------------------------------


# Sample of tracker public symbols kept in sync with
# kitty-specs/shared-package-boundary-cutover-01KQ22DS/contracts/tracker_consumer_surface.md.
# This is intentionally a narrow, stable subset; expansion happens when the
# upstream spec_kitty_tracker mission's public-surface doc finalizes
# (tracker mission ``tracker-pypi-sdk-independence-hardening-01KQ1ZKK``).
_TRACKER_PUBLIC_SURFACE: frozenset[str] = frozenset(
    {
        "FieldOwner",
        "OwnershipMode",
        "OwnershipPolicy",
        "SyncEngine",
        "ExternalRef",
    }
)


class TestSpecifyCliTrackerDoesNotReexportTrackerSurface:
    """R3: ``specify_cli.tracker`` MUST NOT re-export tracker public symbols.

    The CLI-internal adapter package owns lock management, fixture handling,
    and local-service shims. Public tracker symbols MUST flow through the
    PyPI package's own import path so tests, type-checkers, and reviewers
    can see the dependency edge cleanly.
    """

    def test_specify_cli_tracker_init_has_no_overlap_with_tracker_public_surface(self) -> None:
        cli_tracker = importlib.import_module("specify_cli.tracker")
        cli_tracker_all = set(getattr(cli_tracker, "__all__", []))
        overlap = cli_tracker_all & _TRACKER_PUBLIC_SURFACE
        assert not overlap, (
            f"specify_cli.tracker re-exports tracker public symbols: {sorted(overlap)}. "
            "Per C-003, the CLI-internal tracker module must not re-export the "
            "public PyPI tracker surface. Use direct `from spec_kitty_tracker "
            "import X` at the call site instead. See "
            "kitty-specs/shared-package-boundary-cutover-01KQ22DS/contracts/tracker_consumer_surface.md."
        )

    def test_specify_cli_tracker_init_does_not_alias_tracker_attributes(self) -> None:
        """Belt-and-braces: even if a symbol is missing from ``__all__``, it
        must not be present as a module attribute that *aliases* the tracker
        public surface (e.g. ``OwnershipMode = spec_kitty_tracker.OwnershipMode``).

        The check imports both modules and walks the CLI-internal tracker's
        attribute dict, comparing identity / equality against the corresponding
        tracker attribute.
        """
        cli_tracker = importlib.import_module("specify_cli.tracker")
        tracker = importlib.import_module("spec_kitty_tracker")
        aliased: list[str] = []
        for name in _TRACKER_PUBLIC_SURFACE:
            tracker_obj = getattr(tracker, name, None)
            cli_obj = getattr(cli_tracker, name, None)
            if tracker_obj is not None and cli_obj is tracker_obj:
                aliased.append(name)
        assert not aliased, (
            f"specify_cli.tracker aliases tracker public symbols: {sorted(aliased)}. "
            "Per C-003, the CLI-internal tracker module must not alias the public "
            "PyPI tracker surface. Use direct `from spec_kitty_tracker import X` at "
            "the call site instead."
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ast_scan_for_imports(
    *,
    roots: list[Path],
    forbidden_prefix: str,
) -> list[tuple[str, int, str]]:
    """Walk ``.py`` files under ``roots`` and return offending imports.

    Returns a list of ``(file, lineno, target_module)`` triples for every
    ``import X`` / ``from X import ...`` whose module path begins with
    ``forbidden_prefix`` (matched as a dotted-prefix, so ``spec_kitty_runtime``
    matches ``spec_kitty_runtime`` and ``spec_kitty_runtime.engine`` but
    NOT ``spec_kitty_runtime_other``).

    Both module-level and function-scoped (lazy) imports are caught, since
    we walk the entire AST tree.
    """
    offenders: list[tuple[str, int, str]] = []
    for root in roots:
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            # Skip __pycache__ / build artifacts (rglob does not yield .pyc).
            if "__pycache__" in py_file.parts:
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _matches_dotted_prefix(alias.name, forbidden_prefix):
                            offenders.append((str(py_file), node.lineno, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and _matches_dotted_prefix(node.module, forbidden_prefix):
                        offenders.append((str(py_file), node.lineno, node.module))
    return offenders


def _matches_dotted_prefix(target: str, prefix: str) -> bool:
    """Return True if ``target`` equals ``prefix`` or starts with ``prefix.``."""
    return target == prefix or target.startswith(prefix + ".")


# ---------------------------------------------------------------------------
# Custom-evaluable injection helper (used by the R1 pytestarch live-injection
# extension test, kept separate so it does not pay the session-fixture cost).
# ---------------------------------------------------------------------------


class TestPytestArchCanScanInjectedTree:
    """Sanity check: pytestarch can scan a custom path with a synthetic
    violation, proving the rule mechanism (not just the AST helper) is real.

    This complements the AST-scan injection test above by exercising the
    pytestarch import-graph layer end-to-end.
    """

    def test_pytestarch_detects_injected_runtime_import(self, tmp_path: Path) -> None:
        package_root = tmp_path / "src"
        synthetic_pkg = package_root / "synthetic_pkg"
        synthetic_pkg.mkdir(parents=True)
        (synthetic_pkg / "__init__.py").write_text("", encoding="utf-8")
        (synthetic_pkg / "violator.py").write_text(
            "from spec_kitty_runtime import _read_snapshot  # noqa: F401\n",
            encoding="utf-8",
        )
        evaluable = get_evaluable_architecture(
            root_path=str(package_root),
            module_path=str(package_root),
            exclude_external_libraries=False,
            exclusions=("*__pycache__*",),
        )
        rule = (
            Rule()
            .modules_that()
            .have_name_matching(r"^spec_kitty_runtime(\..*)?$")
            .should_not()
            .be_imported_by_modules_that()
            .have_name_matching(r"^src\.synthetic_pkg(\..*)?$")
        )
        with pytest.raises(AssertionError):
            rule.assert_applies(evaluable)
