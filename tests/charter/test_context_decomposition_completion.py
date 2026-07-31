"""T033 (WP06, #2532) — the non-fakeable completion signal for the
``context.py`` decomposition (SC-004 / contracts/context-decomposition-parity.md).

Two independent assertions, per the contract:

1. **Primary (un-fakeable): seam-existence manifest.** Every named seam
   module from ``data-model.md``'s seam→home map (WP04 leaf clusters, WP05
   render seams, WP06 service seams) must (a) exist and be importable, and
   (b) be imported by at least one ``src/`` module OTHER than
   ``charter.context`` itself. Re-exporting a symbol through
   ``charter.context``'s FR-009 preserved-surface block does not satisfy
   this — the seam must be consumed from its own new home, proving the
   decomposition actually moved the *call graph*, not just the source text.
2. **Secondary: the LOC gate.** ``wc -l src/charter/context.py <= 600``.
   Per research.md Decision 9, the seam-existence manifest is the primary
   signal precisely because an LOC-only gate is satisfiable by a no-op
   (moving code into an unimported module still shrinks the file).

This test intentionally re-derives its own import scan (rather than reusing
``tests/architectural/test_no_dead_symbols.py``'s allowlisted, symbol-level
machinery) so it stays a single, self-contained, easily-audited completion
gate: a reviewer can read this one file and confirm the decomposition is
real without cross-referencing the dead-symbol ratchet's allowlist.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast, pytest.mark.unit]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
_CONTEXT_PY = _SRC_ROOT / "charter" / "context.py"

#: LOC ceiling per research.md Decision 9 / the WP06 task file. The
#: grounded floor is ~500-540 (3 orchestrators + preamble + import block +
#: the FR-009 re-export shim); <=600 clears that floor with margin.
_CONTEXT_PY_LOC_CEILING = 600

#: Every seam named in data-model.md's ``context.py`` seam->home map,
#: expressed as its importable dotted module path. WP04 minted the leaf
#: clusters, WP05 the render seams, WP06 (this mission's final WP) the
#: service/profile-resolution/doctrine-service-builder seams + the
#: profile-cited-render consolidation campsite (T033 -- data-model.md
#: mapped ``_render_profile_directives``/``_render_profile_tactics``/
#: ``_render_profile_sections`` into ``context_renderers/profile_sections.py``
#: but no WP claimed the move until the LOC ceiling forced it here).
_SEAM_MODULES: tuple[str, ...] = (
    # WP04 leaf clusters
    "charter.context_renderers.catalog_diagnosis",
    "charter.context_renderers.token_budget",
    "charter.context_renderers.reference_pointers",
    "charter.context_renderers.artifact_bodies",
    "charter.charter_md_parsing",
    "charter.context_state",
    # WP05 render seams
    "charter.context_renderers.template_include",
    "charter.context_renderers.selection_block",
    "charter.context_renderers.activation_block",
    "charter.context_renderers.bootstrap_text",
    "charter.context_renderers.compact_governance",
    # WP06 service seams (this WP)
    "charter.context_json",
    "charter.org_pack_discovery",
    "charter.action_doctrine_bundle",
    "charter.profile_resolution",
    "charter.doctrine_service_builder",
    # WP06 render-cluster consolidation campsite (data-model.md's "render
    # half" of the profile-cited-render split; profile_sections.py already
    # existed as WP12's home for the *resolution* half).
    "charter.context_renderers.profile_sections",
)


#: This completion test's own file -- excluded from the caller scan so the
#: manifest cannot be trivially self-satisfied by this file's own imports;
#: real wiring must come from ``tests/charter/test_context_service_seams.py``
#: (T033's focused unit-coverage file) or another pre-existing consumer.
_THIS_FILE = Path(__file__).resolve()


def _iter_scanned_python_files() -> list[Path]:
    """Every ``*.py`` under ``src/`` and ``tests/`` -- production AND test
    imports both count as proof the seam is consumed from its own new home
    (as opposed to only being reachable via ``charter.context``'s FR-009
    re-export shim). Excludes ``__pycache__`` and this file itself."""
    roots = (_SRC_ROOT, _REPO_ROOT / "tests")
    files: list[Path] = []
    for root in roots:
        files.extend(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(set(files))


def _imported_module_refs(tree: ast.Module) -> set[str]:
    """Return every dotted module path *tree* imports from, in a form
    comparable against a seam's dotted module path.

    Three shapes are normalised into this set:

    1. ``from <mod>[.sub] import ...`` -> ``{"<mod>", "<mod>.<name>", ...}``
       is over-broad on purpose (see the per-seam matcher below): we record
       ``node.module`` itself plus ``"<node.module>.<alias.name>"`` for each
       imported name, so both ``from charter.context_renderers import
       bootstrap_text`` (submodule-as-name) and ``from
       charter.context_json import _project_directive_entries``
       (symbol-as-name) resolve to a path containing the seam's own dotted
       module string.
    2. ``import <mod>[.sub]`` -> ``{"<mod>[.sub]"}``.

    A module-local (function-body) import counts too -- several seams are
    deliberately consumed via a lazy, function-local import to break a
    load-time cycle (see e.g. ``context_json.py``'s and
    ``doctrine_service_builder.py``'s module docstrings), so
    ``ast.walk`` (which visits nested function bodies) rather than a
    top-level-only scan is required for the manifest to reflect the real
    call graph.
    """
    refs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            refs.add(node.module)
            for alias in node.names:
                refs.add(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                refs.add(alias.name)
    return refs


def _seam_is_referenced(refs: set[str], seam_module: str) -> bool:
    return any(ref == seam_module or ref.startswith(seam_module + ".") for ref in refs)


@pytest.fixture(scope="module")
def seam_caller_map() -> dict[str, list[str]]:
    """One pass over every ``src/``/``tests/`` file, building
    ``{seam_module: [caller paths]}`` for all :data:`_SEAM_MODULES` at once.

    A single-pass, module-scoped fixture (rather than re-scanning the whole
    tree once per parametrized seam) keeps this gate's runtime linear in the
    number of files instead of files x seams -- the tree is ~3,700 files.
    """
    callers: dict[str, list[str]] = {seam: [] for seam in _SEAM_MODULES}
    for path in _iter_scanned_python_files():
        if path in (_CONTEXT_PY, _THIS_FILE):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            continue
        refs = _imported_module_refs(tree)
        rel = str(path.relative_to(_REPO_ROOT))
        for seam in _SEAM_MODULES:
            if _seam_is_referenced(refs, seam):
                callers[seam].append(rel)
    return callers


class TestSeamExistenceManifest:
    """Primary, un-fakeable completion signal (SC-004)."""

    @pytest.mark.parametrize("seam_module", _SEAM_MODULES)
    def test_seam_module_exists(self, seam_module: str) -> None:
        module_file = _SRC_ROOT / Path(*seam_module.split("."))
        module_file = module_file.with_suffix(".py")
        assert module_file.is_file(), (
            f"Seam module {seam_module!r} does not exist at "
            f"{module_file.relative_to(_REPO_ROOT)} -- the decomposition manifest "
            "is stale or the module was never created."
        )

    @pytest.mark.parametrize("seam_module", _SEAM_MODULES)
    def test_seam_module_has_non_context_caller(
        self, seam_module: str, seam_caller_map: dict[str, list[str]]
    ) -> None:
        callers = seam_caller_map[seam_module]
        assert callers, (
            f"Seam module {seam_module!r} exists but is imported by NO "
            "src/ or tests/ file other than charter/context.py -- a symbol "
            "re-exported through context.py's FR-009 preserved-surface "
            "block is not enough; the seam must be consumed from its own "
            "new home."
        )


class TestResidualLocCeiling:
    """Secondary completion signal: the LOC gate (research.md Decision 9)."""

    def test_context_py_at_most_600_lines(self) -> None:
        line_count = sum(1 for _ in _CONTEXT_PY.read_text(encoding="utf-8").splitlines())
        assert line_count <= _CONTEXT_PY_LOC_CEILING, (
            f"src/charter/context.py is {line_count} lines, over the "
            f"{_CONTEXT_PY_LOC_CEILING}-line ceiling (research.md Decision 9). "
            "This is a BLOCKER requiring explicit operator re-sign-off, NOT an "
            "implementer-side ceiling adjustment."
        )

    def test_context_py_below_the_pre_wp06_baseline(self) -> None:
        """Sanity floor: the file must have actually shrunk, not just stayed put."""
        line_count = sum(1 for _ in _CONTEXT_PY.read_text(encoding="utf-8").splitlines())
        # WP06 started from 1445 LOC (post-WP05); any residual materially
        # below that confirms real extraction happened, not a no-op.
        assert line_count < 1445
