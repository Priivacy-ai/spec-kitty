"""Anti-regression ratchet for the built-in pack-location authority (WP04, #3039).

Mission ``doctrine-built-in-seam-consolidation-01KYW3TX`` centralizes "where does
built-in kind K live" and "where is the built-in root" into exactly two
callables in :mod:`doctrine.pack_paths` -- :func:`~doctrine.pack_paths.built_in_dir`
and :func:`~doctrine.pack_paths.built_in_root`. WP01 created the authorities;
WP02/WP03/WP05 rerouted every production reader onto them; WP04 (this file)
drops the fail-open ``DoctrineService.built_in_root`` param that made the old
nested shape constructable, and makes the single-authority invariant a CI gate
so a sixth resolver cannot be quietly born (NFR-002).

This file is deliberately its OWN module -- NOT folded into
``test_no_dead_doctrine_paths.py`` (cf. #3039's planned split; C3.4). It covers
three independent contract clauses:

* **C3.1 / C3.1b -- the joins-only AST ratchet.** AST-scans ``src/`` for a
  built-in path *join* -- a ``resolve_pack_root("built-in") / …`` ``BinOp``
  (direct or **variable-indirected**: ``x = resolve_pack_root("built-in"); x /
  …``), or a ``<path> / "built-in"`` filesystem join. Both limbs are
  load-bearing: a ``BinOp``-only scan would false-green the indirected form
  paula flagged as the exact drift class (MAJOR-2); a naive *constant* scan
  would false-red the ~20 legitimate bare ``"built-in"`` string markers used as
  layer/provenance tags. This gate is **join-only, not a constant-scan** --
  it only inspects ``ast.BinOp`` nodes, so a bare string literal used as a
  dict key, docstring text, or comparison operand never trips it, with no
  per-site marker allowlist required. A bare ``resolve_pack_root("built-in")``
  root call (the sanctioned ``built_in_root()`` seam) is likewise permitted --
  it is never the ``.left`` of a ``Div`` ``BinOp`` at any of its call sites, so
  it never matches either limb.
* **C3.2 / NFR-003/005 -- positive per-kind coverage + the #3091 marker.** Every
  kind WITH a ``packs/built-in/<plural>/`` content dir (the 9) resolves inside
  an *existing* directory, asserted **through** :func:`resolve_pack_root`
  (never a raw repo-relative ``.exists()`` -- cf. #3036, survives the future
  wheel-split). The derived complement ``{mission_step_contract, template,
  anti_pattern}`` -- computed from :attr:`~doctrine.artifact_kinds.ArtifactKind.has_built_in_content_dir`,
  never hand-listed -- raises :class:`~doctrine.pack_paths.BuiltInContentDirNotAvailable`.
* **C3.3 / NFR-003 -- anti-vacuity.** The shipped ``agent_profiles`` set
  resolved through the authority is non-empty, so a stale/misconfigured root
  fails loudly instead of passing vacuously (the exact latent false-green this
  mission exists to kill; US2 acceptance #2).

Known pre-existing exemption (read before extending ``_KNOWN_JOIN_ALLOWLIST``)
--------------------------------------------------------------------------------
Exactly one non-authority join site currently exists in ``src/``:
``src/charter/kind_vocabulary.py``'s ``_scan_roots`` iterates ``org_roots`` and
joins ``root / kind.plural / "built-in"`` -- syntactically a filesystem join
(C3.1's third limb), but *semantically* it is the **ORG tier's** own legacy
nested-pack contract (``<org_root>/<plural>/built-in``, documented in-file:
"this nested layout is still live for org packs (unaffected by the built-in
relocation)"). It does not call ``resolve_pack_root("built-in")`` or
``built_in_dir``/``built_in_root`` at all, and it is out of scope for this
mission (built-in-tier consolidation only -- WP02's own Definition of Done
covers the OTHER two joins in this file, which were built-in-tier and are
gone). A pure syntax scan cannot distinguish "root walks an org pack" from
"root walks the built-in tier" -- both would look identical -- so this ONE
site is allowlisted by exact ``(file, lineno)``, not by file, so any FUTURE
join added to this file (e.g. a resurrected built-in-tier dual-read) still
fails the gate. Reintroducing a similar org-tier convention elsewhere requires
a deliberate allowlist edit naming the new site's rationale, mirroring
``tests/architectural/test_protection_resolver_call_sites.py``.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

import pytest

from doctrine.artifact_kinds import ArtifactKind
from doctrine.pack_paths import BuiltInContentDirNotAvailable, built_in_dir, resolve_pack_root
from doctrine.service import DoctrineService
from tests.architectural.conftest import SourceFile

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The single-authority module: only file permitted to construct a built-in
#: path join (both `built_in_dir` and `built_in_root` live here -- C2.1/C3.1).
_AUTHORITY_FILE = Path("src/doctrine/pack_paths.py")

#: Narrow, exact (file, lineno) allowlist for the ONE known pre-existing
#: non-authority join -- see the module docstring "Known pre-existing
#: exemption" section above for the full rationale. Extending this requires a
#: deliberate, documented policy decision naming the ONE site and WHY it is
#: not a built-in-tier reconstruction.
_KNOWN_JOIN_ALLOWLIST: frozenset[tuple[Path, int]] = frozenset(
    {
        # src/charter/kind_vocabulary.py::_scan_roots -- org-tier legacy
        # nested-pack join (`root / kind.plural / "built-in"`), NOT a
        # built-in-tier reconstruction. See module docstring.
        (Path("src/charter/kind_vocabulary.py"), 183),
    }
)

_RESOLVE_PACK_ROOT_BUILTIN = "resolve_pack_root"
_BUILT_IN_LITERAL = "built-in"
_BUILT_IN_ROOT_FUNC = "built_in_root"


def _is_resolve_pack_root_builtin_call(node: ast.AST) -> bool:
    """Return whether *node* is a bare ``resolve_pack_root("built-in")`` call."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == _RESOLVE_PACK_ROOT_BUILTIN
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == _BUILT_IN_LITERAL
    )


def _is_built_in_root_call(node: ast.AST) -> bool:
    """Return whether *node* is a bare ``built_in_root()`` call (no args).

    Covers both ``built_in_root()`` (``ast.Name`` callee, the normal
    ``from doctrine.pack_paths import built_in_root`` import shape) and
    ``<module-or-obj>.built_in_root()`` (``ast.Attribute`` callee). The
    sanctioned bare-root seam is legitimate on its own (C3.1b); joining its
    result with ``/`` to reconstruct a per-kind path is the drift this limb
    exists to catch (see :func:`_is_builtin_root_seam_call`).
    """
    return (
        isinstance(node, ast.Call)
        and not node.args
        and not node.keywords
        and (
            (isinstance(node.func, ast.Name) and node.func.id == _BUILT_IN_ROOT_FUNC)
            or (isinstance(node.func, ast.Attribute) and node.func.attr == _BUILT_IN_ROOT_FUNC)
        )
    )


def _is_builtin_root_seam_call(node: ast.AST) -> bool:
    """Return whether *node* is either sanctioned bare-root seam call.

    ``resolve_pack_root("built-in")`` and ``built_in_root()`` are the two
    call shapes that hand back the built-in root without a per-kind segment
    -- either one becoming the base of a ``/`` join is the "reconstruct a
    per-kind path locally" drift this gate exists to catch.
    """
    return _is_resolve_pack_root_builtin_call(node) or _is_built_in_root_call(node)


def _names_bound_to_builtin_root_call(tree: ast.AST) -> set[str]:
    """Return every bare name assigned directly from a sanctioned root-seam call.

    Backs the variable-indirected limb (``x = resolve_pack_root("built-in")``
    or ``x = built_in_root()``; later ``x / …``) -- a ``BinOp``-only scan of
    the assignment's later use would miss this, since the call itself never
    appears at the join site.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_builtin_root_seam_call(node.value):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return names


def _join_base(node: ast.AST) -> ast.AST:
    """Walk down the left spine of a ``/``-chain to its base operand.

    ``a / b / c`` parses as ``BinOp(BinOp(a, b), c)``; the base is ``a``,
    reached by following ``.left`` through every nested ``Div`` ``BinOp``.
    """
    while isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        node = node.left
    return node


def _find_builtin_joins(tree: ast.AST) -> set[int]:
    """Return the line numbers of every built-in path-join ``BinOp`` in *tree*.

    Flags (C3.1):
      * a ``resolve_pack_root("built-in") / …`` join, direct or
        variable-indirected;
      * a ``built_in_root() / …`` join, direct or variable-indirected -- the
        sanctioned bare-root seam reused to reconstruct a per-kind path
        locally, the most natural future drift once callers stop spelling
        ``resolve_pack_root("built-in")`` directly;
      * a ``<path> / "built-in"`` filesystem join (any base).
    Permits (C3.1b): a bare ``resolve_pack_root("built-in")`` or
    ``built_in_root()`` call that is never the base of a ``/`` join (the
    sanctioned seams themselves), and any bare ``"built-in"`` string literal
    that never appears as the right-hand operand of a ``/`` ``BinOp`` (the
    ~20 layer/provenance markers) -- both are structurally invisible to this
    join-only scan.
    """
    indirected_names = _names_bound_to_builtin_root_call(tree)
    offenders: set[int] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            continue
        base = _join_base(node)
        is_direct_or_indirected = _is_builtin_root_seam_call(base) or (
            isinstance(base, ast.Name) and base.id in indirected_names
        )
        is_filesystem_join = isinstance(node.right, ast.Constant) and node.right.value == _BUILT_IN_LITERAL
        if is_direct_or_indirected or is_filesystem_join:
            offenders.add(node.lineno)
    return offenders


def _rel(path: Path) -> Path:
    return path.relative_to(_REPO_ROOT)


def test_no_builtin_path_joins_outside_pack_paths_authority(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """C3.1/C3.1b/NFR-002: only ``pack_paths.py`` may join a built-in path.

    Any other ``src/`` module constructing a ``resolve_pack_root("built-in")
    / …`` join (direct or variable-indirected) or a ``<path> / "built-in"``
    filesystem join is a sixth resolver being reborn -- the exact regression
    class this gate exists to prevent. See the module docstring for the ONE
    documented, narrowly-allowlisted exception.
    """
    violations: dict[str, list[int]] = {}

    for abs_path, entry in sorted(src_source_tree.items()):
        rel = _rel(abs_path)
        if rel == _AUTHORITY_FILE:
            continue
        offending_lines = _find_builtin_joins(entry.tree)
        remaining = sorted(
            lineno for lineno in offending_lines if (rel, lineno) not in _KNOWN_JOIN_ALLOWLIST
        )
        if remaining:
            violations[rel.as_posix()] = remaining

    if violations:
        details = "\n".join(f"  {path}: lines {lines}" for path, lines in sorted(violations.items()))
        pytest.fail(
            "Found built-in path join(s) outside the doctrine.pack_paths authority.\n"
            "Route through built_in_dir(kind) (per-kind) or built_in_root() (bare root)\n"
            "instead of composing resolve_pack_root(\"built-in\") / ... or <path> / \"built-in\"\n"
            "locally -- that reintroduces a scattered, fail-open resolver "
            "(NFR-002).\n\n"
            f"Violations:\n{details}"
        )


def test_negative_bite_direct_and_variable_indirected_joins_are_caught() -> None:
    """NFR-002 anti-vacuity: prove the gate actually flags both join limbs.

    Without this, a gate that always passes (e.g. an empty offender set from a
    typo'd AST match) would be indistinguishable from a correct, strict gate.
    Two synthetic snippets are parsed directly (never written to ``src/``):
    one direct ``resolve_pack_root("built-in") / …`` join, one
    variable-indirected join. Both must be flagged.
    """
    direct_source = (
        "from doctrine.pack_paths import resolve_pack_root\n"
        "\n"
        "def sneaky_direct(kind):\n"
        "    return resolve_pack_root('built-in') / kind.plural\n"
    )
    indirected_source = (
        "from doctrine.pack_paths import resolve_pack_root\n"
        "\n"
        "def sneaky_indirected(kind):\n"
        "    root = resolve_pack_root('built-in')\n"
        "    return root / kind.plural\n"
    )
    filesystem_join_source = (
        "def sneaky_filesystem_join(some_root, kind):\n"
        "    return some_root / kind.plural / 'built-in'\n"
    )

    direct_hits = _find_builtin_joins(ast.parse(direct_source))
    indirected_hits = _find_builtin_joins(ast.parse(indirected_source))
    filesystem_hits = _find_builtin_joins(ast.parse(filesystem_join_source))

    assert direct_hits, "Direct resolve_pack_root('built-in') / ... join must be flagged"
    assert indirected_hits, "Variable-indirected join (x = resolve_pack_root('built-in'); x / ...) must be flagged"
    assert filesystem_hits, "<path> / 'built-in' filesystem join must be flagged"

    # And the permitted forms must NOT be flagged (proves the gate is
    # join-only, not a constant-scan -- C3.1b).
    bare_root_call_source = (
        "from doctrine.pack_paths import resolve_pack_root\n"
        "\n"
        "def permitted_bare_root_call():\n"
        "    return resolve_pack_root('built-in')\n"
    )
    bare_marker_source = (
        "def permitted_bare_marker(layer):\n"
        "    return {'built-in': 'built-in', 'org': 'org'}.get(layer, layer)\n"
    )
    assert not _find_builtin_joins(ast.parse(bare_root_call_source))
    assert not _find_builtin_joins(ast.parse(bare_marker_source))


def test_negative_bite_built_in_root_call_joins_are_caught() -> None:
    """NFR-002 anti-vacuity, ``built_in_root()``-join limb (FOLD 6 widening).

    The most natural future drift is not re-spelling
    ``resolve_pack_root("built-in")`` -- it is reusing the *sanctioned*
    ``built_in_root()`` seam and then joining a per-kind segment onto it
    locally, e.g. ``built_in_root() / kind.plural``, instead of calling
    :func:`doctrine.pack_paths.built_in_dir`. Both the direct and
    variable-indirected shapes must be flagged, while a bare
    ``built_in_root()`` call -- the sanctioned form itself -- must stay
    permitted (mirrors the ``resolve_pack_root("built-in")`` proof above).
    """
    direct_source = (
        "from doctrine.pack_paths import built_in_root\n"
        "\n"
        "def sneaky_direct(kind):\n"
        "    return built_in_root() / kind.plural\n"
    )
    indirected_source = (
        "from doctrine.pack_paths import built_in_root\n"
        "\n"
        "def sneaky_indirected(kind):\n"
        "    root = built_in_root()\n"
        "    return root / kind.plural\n"
    )
    attribute_call_source = (
        "from doctrine import pack_paths\n"
        "\n"
        "def sneaky_attribute_call(kind):\n"
        "    return pack_paths.built_in_root() / kind.plural\n"
    )

    direct_hits = _find_builtin_joins(ast.parse(direct_source))
    indirected_hits = _find_builtin_joins(ast.parse(indirected_source))
    attribute_hits = _find_builtin_joins(ast.parse(attribute_call_source))

    assert direct_hits, "Direct built_in_root() / ... join must be flagged"
    assert indirected_hits, "Variable-indirected join (x = built_in_root(); x / ...) must be flagged"
    assert attribute_hits, "Attribute-call join (mod.built_in_root() / ...) must be flagged"

    # The sanctioned bare call itself -- with no join -- must stay permitted.
    bare_built_in_root_source = (
        "from doctrine.pack_paths import built_in_root\n"
        "\n"
        "def permitted_bare_built_in_root():\n"
        "    return built_in_root()\n"
    )
    assert not _find_builtin_joins(ast.parse(bare_built_in_root_source))


# ---------------------------------------------------------------------------
# C3.2 / NFR-003 / NFR-005 -- positive per-kind coverage + the #3091 marker
# ---------------------------------------------------------------------------

#: The 9 kinds WITH a shipped `packs/built-in/<plural>/` content directory
#: (derived from `has_built_in_content_dir`, asserted below -- not hand-listed
#: independently of that attribute).
_CONTENT_DIR_KINDS: tuple[ArtifactKind, ...] = tuple(k for k in ArtifactKind if k.has_built_in_content_dir)

#: #3091 marker (NFR-005): the DERIVED complement of `_CONTENT_DIR_KINDS` --
#: `{mission_step_contract, template, anti_pattern}` -- package-resource/
#: graph-only kinds with no shipped content dir (relocation deferred to
#: mission #3091). This assertion is the single place that must be edited if
#: a fourth kind joins the carve-out, or if one of these three kinds later
#: GAINS a content dir: either change is a deliberate, reviewed edit here, not
#: a silent drift, because the set below is compared against the LIVE
#: `ArtifactKind` complement rather than repeated as an independent literal.
_DERIVED_COMPLEMENT_KINDS: tuple[ArtifactKind, ...] = tuple(k for k in ArtifactKind if not k.has_built_in_content_dir)


def test_content_dir_kinds_and_complement_partition_all_kinds() -> None:
    """Sanity: the 9 content-dir kinds + the 3-kind complement cover every kind exactly once."""
    assert len(_CONTENT_DIR_KINDS) == 9  # golden-count: cardinality-is-contract
    assert set(_DERIVED_COMPLEMENT_KINDS) == {
        ArtifactKind.MISSION_STEP_CONTRACT,
        ArtifactKind.TEMPLATE,
        ArtifactKind.ANTI_PATTERN,
    }  # 3091: the derived carve-out set -- edit here if it ever changes.
    assert set(_CONTENT_DIR_KINDS) | set(_DERIVED_COMPLEMENT_KINDS) == set(ArtifactKind)
    assert set(_CONTENT_DIR_KINDS).isdisjoint(_DERIVED_COMPLEMENT_KINDS)


@pytest.mark.parametrize("kind", _CONTENT_DIR_KINDS)
def test_built_in_dir_resolves_inside_existing_packaged_content_dir(kind: ArtifactKind) -> None:
    """C3.2/NFR-003: every content-dir kind resolves via resolve_pack_root(...), not a raw .exists().

    Asserting through :func:`resolve_pack_root` (rather than a repo-relative
    ``Path("packs/built-in/...").exists()``) means this survives the future
    wheel-split (#3036): the same code path this test exercises is what
    production calls, so packaging the built-in tier differently keeps this
    test meaningful instead of hard-coding a source-tree-only assumption.
    """
    resolved = built_in_dir(kind)
    expected_root = resolve_pack_root("built-in")

    assert resolved == expected_root / kind.plural
    assert resolved.is_dir(), f"{kind.name}'s built-in content dir must exist: {resolved}"


@pytest.mark.parametrize("kind", _DERIVED_COMPLEMENT_KINDS)
def test_built_in_dir_refuses_derived_complement_kinds(kind: ArtifactKind) -> None:
    """C1.4/C3.2/NFR-005 (#3091 marker): the derived complement raises, never silently resolves."""
    with pytest.raises(BuiltInContentDirNotAvailable):
        built_in_dir(kind)


# ---------------------------------------------------------------------------
# C3.3 / NFR-003 -- anti-vacuity
# ---------------------------------------------------------------------------


def test_shipped_agent_profiles_are_non_empty() -> None:
    """C3.3/NFR-003: the shipped agent_profiles set must be non-empty (anti-vacuity).

    A stale, empty, or misconfigured built-in root would otherwise let
    ``DoctrineService().agent_profiles`` resolve to an empty set and pass
    every downstream check vacuously -- the exact latent false-green US2
    acceptance #2 exists to kill.
    """
    service = DoctrineService()
    profiles = service.agent_profiles.list_all()

    assert profiles, "Shipped agent_profiles set must be non-empty (anti-vacuity gate)"
