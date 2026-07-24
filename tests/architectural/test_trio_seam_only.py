"""Load-bearing architectural guards for the WP02-04 trio decomposition (WP05).

coord-authority-trio-degod-01KX7094 split three god-modules
(``agent/workflow.py``, ``cli/commands/implement.py``,
``acceptance/__init__.py``) into shell + pure-core(s) + executor triples:

* ``agent/workflow.py``            -> ``agent/workflow_cores.py`` + ``agent/workflow_executor.py``
* ``cli/commands/implement.py``    -> ``cli/commands/implement_cores.py``
* ``acceptance/__init__.py``       -> ``acceptance/summary_core.py`` + ``acceptance/gates_core.py``

This module pins the two invariants the decomposition exists to protect
(FR-004 / FR-007 / SC-002), so a future edit cannot silently reopen either
without failing CI:

T027 -- seam-only read-path imports
------------------------------------
Every one of the eight trio modules composes a mission's on-disk location
ONLY through the blessed seam wrappers -- ``mission_runtime.placement_seam``
(write/read placement) and the small, explicitly-documented set of names the
trio currently imports from ``specify_cli.missions._read_path_resolver``
(the single read-SELECTION seam, WP01 01KVN754 / mission
``single-mission-surface-resolver-01KVGCE8``). Importing any OTHER
FS-path-composing primitive -- a raw ``KITTY_SPECS_DIR`` constant, a
different resolver function from ``_read_path_resolver.py``, or one of
``mission_runtime``'s lower-level placement building blocks
(``resolve_placement_only`` / ``artifact_home_for`` / ``mission_context_for``
/ ``kind_for_mission_file``) -- bypasses the seam and is a regression.

The allowlist below pins the CURRENT, live set of blessed names (mirroring
the ``_ALLOWLISTED_RAW_JOINS`` discipline in
``test_single_mission_surface_resolver.py``): a name not already on the list
is a leaf-primitive bypass and MUST fail this guard, forcing a deliberate,
reviewed addition rather than a silent widening.

T028 -- pure cores perform no I/O
-----------------------------------
The four extracted "cores" modules (``workflow_cores.py``,
``implement_cores.py``, ``summary_core.py``, ``gates_core.py``) exist so the
trio's decision/parsing logic can be unit-tested without a real repository,
git process, or filesystem. An AST classifier bans the literal I/O syntax
patterns FR-007 targets: ``open(...)``, ``Path.read_text/write_text/
read_bytes/write_bytes``, ``subprocess.*``, ``os.system``, ``sqlite3.*``, and
common network calls (``socket.*``, ``urllib.request.urlopen``,
``requests.*``, ``httpx.*``).

Two of the four cores modules carry a small number of ALREADY-DOCUMENTED,
intentional I/O call sites (their own module docstrings say so explicitly):

* ``gates_core.py::_workflow_evidence_missing`` reads one small, already-
  scoped evidence file -- the same class of "lightweight, already-scoped
  filesystem read" ``workflow_cores.py``'s own docstring carves out for its
  status-event read (``.exists()`` / ``.glob()`` are not banned either, for
  the same reason).
* ``implement_cores.py``'s ``_SubprocessGitPort`` class is, by its own
  docstring, "the ONE git-subprocess I/O boundary in this module -- a thin
  adapter, not decision logic"; its working-tree comparison reads
  (``_is_self_write_only_diff`` / ``_files_changed_vs_ref``) are the
  injected-``GitPort`` pattern's filesystem twin.

These five sites are allowlisted below with a content-anchored composite key
(DIR-041 discipline -- never a raw ``file.py:NNN`` locator) and an explicit
rationale, exactly like ``_ALLOWLISTED_RAW_JOINS``. Any NEW I/O call site in
these four files that is not on this list fails the guard.
"""

from __future__ import annotations

import ast
import functools
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.contracts.anchoring import composite_key
from tests.architectural._ratchet_keys import (
    CompositeKey,
    ContentDescriptor,
    resolve_descriptor,
)

pytestmark = [pytest.mark.architectural]

# ---------------------------------------------------------------------------
# Repo / source roots.
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
_SRC_SPECIFY_CLI = _SRC_ROOT / "specify_cli"

# ---------------------------------------------------------------------------
# The eight trio modules (T027 scope).
# ---------------------------------------------------------------------------
_WORKFLOW_PY = _SRC_SPECIFY_CLI / "cli" / "commands" / "agent" / "workflow.py"
_WORKFLOW_CORES_PY = _SRC_SPECIFY_CLI / "cli" / "commands" / "agent" / "workflow_cores.py"
_WORKFLOW_EXECUTOR_PY = _SRC_SPECIFY_CLI / "cli" / "commands" / "agent" / "workflow_executor.py"
_IMPLEMENT_PY = _SRC_SPECIFY_CLI / "cli" / "commands" / "implement.py"
_IMPLEMENT_CORES_PY = _SRC_SPECIFY_CLI / "cli" / "commands" / "implement_cores.py"
_ACCEPTANCE_INIT_PY = _SRC_SPECIFY_CLI / "acceptance" / "__init__.py"
_ACCEPTANCE_SUMMARY_CORE_PY = _SRC_SPECIFY_CLI / "acceptance" / "summary_core.py"
_ACCEPTANCE_GATES_CORE_PY = _SRC_SPECIFY_CLI / "acceptance" / "gates_core.py"

_TRIO_FILES: tuple[Path, ...] = (
    _WORKFLOW_PY,
    _WORKFLOW_CORES_PY,
    _WORKFLOW_EXECUTOR_PY,
    _IMPLEMENT_PY,
    _IMPLEMENT_CORES_PY,
    _ACCEPTANCE_INIT_PY,
    _ACCEPTANCE_SUMMARY_CORE_PY,
    _ACCEPTANCE_GATES_CORE_PY,
)

# The subset that are the extracted PURE cores (T028 scope). Deliberately
# excludes the shells (workflow.py / implement.py / acceptance/__init__.py)
# and the I/O-heavy executor (workflow_executor.py) -- those are the
# I/O-and-wiring layer the split exists to isolate FROM the cores.
_CORE_FILES: tuple[Path, ...] = (
    _WORKFLOW_CORES_PY,
    _IMPLEMENT_CORES_PY,
    _ACCEPTANCE_SUMMARY_CORE_PY,
    _ACCEPTANCE_GATES_CORE_PY,
)


# ===========================================================================
# T027 -- seam-only read-path import scanner
# ===========================================================================

#: The single read-SELECTION seam module (WP01 01KVN754). Only these names
#: -- the ones the trio ACTUALLY imports today -- are blessed. Anything else
#: exported by ``_read_path_resolver.py`` (``read_primary_meta``,
#: ``coord_feature_dir``, ``resolve_feature_dir_for_slug``, the internal
#: ``_canonicalize_*`` cascade steps, etc.) is a leaf primitive the trio must
#: never import directly.
_READ_PATH_RESOLVER_MODULE = "specify_cli.missions._read_path_resolver"
_SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES: frozenset[str] = frozenset(
    {
        "primary_feature_dir_for_mission",
        "resolve_handle_to_read_path",
        "_canonicalize_primary_read_handle",
        "candidate_feature_dir_for_mission",
        "resolve_planning_read_dir",
    }
)

#: ``mission_runtime`` is a broad runtime-port package (types, predicates,
#: context helpers) -- only ``placement_seam`` is the blessed path-composing
#: wrapper. The names below are ``mission_runtime``'s OTHER placement/path
#: building blocks (defined in ``mission_runtime.resolution`` /
#: ``mission_runtime.artifacts``) that a trio caller could import to bypass
#: ``placement_seam`` -- explicitly forbidden regardless of which trio file.
_MISSION_RUNTIME_MODULE = "mission_runtime"
_SEAM_ALLOWED_MISSION_RUNTIME_NAME = "placement_seam"
_FORBIDDEN_MISSION_RUNTIME_PATH_PRIMITIVES: frozenset[str] = frozenset(
    {
        "resolve_placement_only",
        "artifact_home_for",
        "mission_context_for",
        "kind_for_mission_file",
    }
)

#: Blanket-forbidden regardless of the module it is imported from: the raw
#: KITTY_SPECS_DIR path segment is the primitive every raw-bypass join in
#: ``test_single_mission_surface_resolver.py`` is built from. A trio module
#: importing it at all is latent bypass capability, even before any join is
#: composed.
_FORBIDDEN_RAW_NAMES: frozenset[str] = frozenset({"KITTY_SPECS_DIR"})


@dataclass(frozen=True)
class _SeamViolation:
    lineno: int
    name: str
    module: str
    reason: str

    def describe(self, filename: str) -> str:
        return f"{filename}:{self.lineno}  import {self.name!r} from {self.module!r} -- {self.reason}"


def _scan_seam_violations(source: str) -> list[_SeamViolation]:
    """AST-import-scan: every mission-read-path import must route through the seam.

    Operates on raw source text (not a live file) so the same function backs
    both the real-file assertion and the synthetic plant-and-catch self-checks
    below -- there is exactly one code path for "is this import a bypass".
    """
    tree = ast.parse(source)
    violations: list[_SeamViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        for alias in node.names:
            name = alias.name
            if name in _FORBIDDEN_RAW_NAMES:
                violations.append(
                    _SeamViolation(
                        node.lineno, name, module, "raw KITTY_SPECS_DIR-family primitive; never import directly"
                    )
                )
                continue
            if module == _READ_PATH_RESOLVER_MODULE:
                if name not in _SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES:
                    violations.append(
                        _SeamViolation(
                            node.lineno,
                            name,
                            module,
                            "not on the blessed read-path-resolver allowlist "
                            "(_SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES)",
                        )
                    )
            elif module == _MISSION_RUNTIME_MODULE and name in _FORBIDDEN_MISSION_RUNTIME_PATH_PRIMITIVES:
                violations.append(
                    _SeamViolation(
                        node.lineno,
                        name,
                        module,
                        "a mission_runtime placement primitive other than placement_seam",
                    )
                )
    return violations


def _scan_file_seam_violations(path: Path) -> list[_SeamViolation]:
    return _scan_seam_violations(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# T027(a) -- anti-vacuous: the trio file list resolves to real files.
# ---------------------------------------------------------------------------


def test_trio_files_exist() -> None:
    """Every path in ``_TRIO_FILES`` is a real file on the current tree.

    A stale/typo'd path would silently vacuous-pass every downstream
    assertion below (an empty/missing file contributes zero violations).
    """
    missing = [str(p) for p in _TRIO_FILES if not p.is_file()]
    assert not missing, f"Trio module paths do not exist on the current tree: {missing}"


# ---------------------------------------------------------------------------
# T027(b) -- the real assertion: zero seam bypasses on the live tree.
# ---------------------------------------------------------------------------


def test_trio_imports_route_only_through_seam_wrappers() -> None:
    """FR-004/FR-007: every trio module's read-path imports are seam-only.

    Every ``ImportFrom`` in every trio module that references a mission-path
    primitive (``_read_path_resolver`` names, ``mission_runtime`` placement
    building blocks, or the raw ``KITTY_SPECS_DIR`` constant) must be on the
    blessed allowlist. A regression here means a trio module started
    composing (or gained the latent capability to compose) a mission
    directory path outside the canonical seam.
    """
    all_violations: list[str] = []
    for path in _TRIO_FILES:
        violations = _scan_file_seam_violations(path)
        all_violations.extend(v.describe(str(path.relative_to(_REPO_ROOT))) for v in violations)

    assert not all_violations, (
        "Trio modules import mission-read-path primitives outside the seam:\n"
        + "\n".join(f"  {line}" for line in all_violations)
        + "\n\nRoute through mission_runtime.placement_seam or the blessed "
        "resolve_handle_to_read_path / primary_feature_dir_for_mission family "
        "(_SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES), or justify a deliberate "
        "allowlist addition."
    )


# ---------------------------------------------------------------------------
# T027(c) -- anti-false-positive control: the blessed names themselves are clean.
# ---------------------------------------------------------------------------


def test_blessed_seam_imports_are_not_flagged() -> None:
    """A file importing ONLY the blessed names produces zero violations.

    Guards the scanner against being accidentally too broad (e.g. flagging
    the whole ``_read_path_resolver`` module rather than specific names).
    """
    source = textwrap.dedent(
        """
        from specify_cli.missions._read_path_resolver import (
            primary_feature_dir_for_mission,
            resolve_handle_to_read_path,
            _canonicalize_primary_read_handle,
            candidate_feature_dir_for_mission,
            resolve_planning_read_dir,
        )
        from mission_runtime import placement_seam
        """
    )
    assert _scan_seam_violations(source) == []


# ---------------------------------------------------------------------------
# T027(d) -- non-vacuous self-checks: a planted leaf-primitive import is caught.
# ---------------------------------------------------------------------------


def test_planted_read_path_resolver_leaf_primitive_is_caught() -> None:
    """A direct import of a non-blessed ``_read_path_resolver`` name FAILS.

    ``resolve_feature_dir_for_slug`` is a real, exported name from the seam
    module that the trio does NOT currently import -- exactly the shape of a
    future accidental bypass.
    """
    source = "from specify_cli.missions._read_path_resolver import resolve_feature_dir_for_slug\n"
    violations = _scan_seam_violations(source)
    assert violations, "The scanner failed to catch a non-blessed _read_path_resolver import -- vacuous guard."
    assert violations[0].name == "resolve_feature_dir_for_slug"


def test_planted_mission_runtime_leaf_primitive_is_caught() -> None:
    """A direct import of a non-``placement_seam`` mission_runtime placement primitive FAILS."""
    source = "from mission_runtime import artifact_home_for\n"
    violations = _scan_seam_violations(source)
    assert violations, "The scanner failed to catch a non-blessed mission_runtime placement import -- vacuous guard."
    assert violations[0].name == "artifact_home_for"


def test_planted_raw_kitty_specs_dir_import_is_caught() -> None:
    """A direct import of the raw ``KITTY_SPECS_DIR`` constant FAILS, from any module."""
    source = "from specify_cli.core.constants import KITTY_SPECS_DIR\n"
    violations = _scan_seam_violations(source)
    assert violations, "The scanner failed to catch a raw KITTY_SPECS_DIR import -- vacuous guard."
    assert violations[0].name == "KITTY_SPECS_DIR"


# ---------------------------------------------------------------------------
# T027(e) -- allowlist integrity: forbidden mission_runtime names are still live.
# ---------------------------------------------------------------------------


def test_forbidden_mission_runtime_names_are_live_exports() -> None:
    """Every name in ``_FORBIDDEN_MISSION_RUNTIME_PATH_PRIMITIVES`` is a real export.

    If one of these were renamed/removed upstream, the forbidden-name check
    would silently stop matching anything -- this keeps the negative list
    honest against the live ``mission_runtime.__all__``.
    """
    import mission_runtime

    missing = sorted(_FORBIDDEN_MISSION_RUNTIME_PATH_PRIMITIVES - set(mission_runtime.__all__))
    assert not missing, (
        f"_FORBIDDEN_MISSION_RUNTIME_PATH_PRIMITIVES references names no longer "
        f"exported by mission_runtime: {missing}. Update the forbidden set to "
        "match the live API (or confirm the primitive was retired and drop it)."
    )


def test_allowed_read_path_resolver_names_are_currently_used() -> None:
    """Every blessed name is actually imported by at least one trio module.

    Keeps the allowlist minimal and honest (mirrors
    ``test_allowlist_entries_are_not_stale`` in the sibling resolver guard):
    a blessed-but-unused name would silently widen the seam for no reason.
    ``resolve_handle_to_read_path`` is the one exception -- it is the named
    seam entry point itself (WP05 prompt), blessed even though the current
    trio snapshot routes through ``primary_feature_dir_for_mission`` instead.
    """
    used: set[str] = set()
    for path in _TRIO_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == _READ_PATH_RESOLVER_MODULE:
                used.update(alias.name for alias in node.names)

    unused = sorted(_SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES - used - {"resolve_handle_to_read_path"})
    assert not unused, (
        f"Blessed _read_path_resolver names not imported by any trio module: {unused}. "
        "Drop them from _SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES to keep the allowlist precise."
    )


# ===========================================================================
# T028 -- pure cores perform no I/O
# ===========================================================================

_BANNED_PATH_METHODS: frozenset[str] = frozenset({"read_text", "write_text", "read_bytes", "write_bytes"})
_BANNED_ROOT_MODULES: frozenset[str] = frozenset({"subprocess", "sqlite3", "socket", "requests", "httpx"})
_BANNED_NAME_CALLS: frozenset[str] = frozenset({"open"})


@dataclass(frozen=True)
class _IoViolation:
    lineno: int
    description: str


def _import_aliases(tree: ast.Module) -> dict[str, str]:
    """Map local alias -> real root module name for ``import x[.y] [as z]`` statements."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                aliases[local] = alias.name.split(".")[0]
    return aliases


def _attribute_root_name(node: ast.expr) -> str | None:
    """The leftmost ``Name`` id of a (possibly chained) attribute access, if any."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def find_banned_io_calls(source: str) -> list[_IoViolation]:
    """AST classifier: literal I/O call-syntax banned from a pure core (FR-007).

    Operates on raw source text so the same function backs both the real
    four-cores-file assertion and the synthetic "fake core string"
    plant-and-catch self-checks below.
    """
    tree = ast.parse(source)
    aliases = _import_aliases(tree)
    violations: list[_IoViolation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func

        # open(...)
        if isinstance(func, ast.Name) and func.id in _BANNED_NAME_CALLS:
            violations.append(_IoViolation(node.lineno, f"{func.id}(...)"))
            continue

        if not isinstance(func, ast.Attribute):
            continue

        # <expr>.read_text()/.write_text()/.read_bytes()/.write_bytes()
        if func.attr in _BANNED_PATH_METHODS:
            violations.append(_IoViolation(node.lineno, f".{func.attr}(...)"))
            continue

        root = _attribute_root_name(func)
        if root is None:
            continue
        real_module = aliases.get(root, root)

        if real_module == "os" and func.attr == "system":
            violations.append(_IoViolation(node.lineno, "os.system(...)"))
        elif real_module in _BANNED_ROOT_MODULES:
            violations.append(_IoViolation(node.lineno, f"{real_module}.{func.attr}(...)"))
        elif real_module == "urllib" and func.attr == "urlopen":
            violations.append(_IoViolation(node.lineno, "urllib.request.urlopen(...)"))

    return violations


# ---------------------------------------------------------------------------
# Allowlist: the five already-documented, intentional I/O sites (T028).
#
# Content-descriptor seeded (rel_path, qualname, token_substring, occurrence,
# rationale) -- IC-DESCRIPTOR, #2564. NOT a raw (rel_path, int_line, rationale)
# seed tuple: that shape stored a bare int line-number directly in a
# module-level seed constant, and even though the composite key was *derived*
# live via composite_key_from_file, the int itself reached that call's 2nd
# positional arg only after being laundered through the dict-comprehension's
# ``line`` loop variable -- invisible to both the direct int-literal predicate
# (``_is_composite_key_line_arg``) and the ``file.py:NNN``-string grep (the
# seed spanned multiple source lines). Every entry below is now qualname +
# normalized-token-substring addressed and resolved to its composite key LIVE
# at import time via :func:`resolve_descriptor` (never a hand-authored line
# number), exactly like ``_ALLOWLISTED_RAW_JOINS``
# (test_single_mission_surface_resolver.py) and ``_ALLOW_LIST_SEED``
# (test_no_write_side_rederivation.py).
# ---------------------------------------------------------------------------
_IO_ALLOWLIST_SITES: tuple[ContentDescriptor, ...] = (
    ContentDescriptor(
        rel_path="specify_cli/acceptance/gates_core.py",
        qualname="_workflow_evidence_missing",
        token_substring="evidence_path . read_text",
        occurrence=None,
        rationale=(
            "_workflow_evidence_missing reads ONE small, already-scoped local "
            "evidence file (workflow-evidence.md) -- the same class of "
            "'lightweight, already-scoped filesystem read' workflow_cores.py's "
            "own docstring carves out for its status-event read (.exists()/"
            ".glob() are likewise not banned). Not a subprocess/worktree/network "
            "operation."
        ),
    ),
    ContentDescriptor(
        rel_path="specify_cli/cli/commands/implement_cores.py",
        qualname="_SubprocessGitPort.status_porcelain",
        token_substring="subprocess . run (",
        occurrence=None,
        rationale=(
            "_SubprocessGitPort.status_porcelain -- the module docstring names "
            "this class 'the ONE git-subprocess I/O boundary in this module -- "
            "a thin adapter, not decision logic', isolated behind the injectable "
            "GitPort Protocol so every decision function above it can be tested "
            "with a fake port."
        ),
    ),
    ContentDescriptor(
        rel_path="specify_cli/cli/commands/implement_cores.py",
        qualname="_SubprocessGitPort.show_blob",
        token_substring="subprocess . run (",
        occurrence=None,
        rationale=(
            "_SubprocessGitPort.show_blob -- same injected-port I/O boundary as "
            "status_porcelain above; the second (and last) subprocess call in "
            "the module."
        ),
    ),
    ContentDescriptor(
        rel_path="specify_cli/cli/commands/implement_cores.py",
        qualname="_is_self_write_only_diff",
        token_substring="source . read_bytes ( )",
        occurrence=None,
        rationale=(
            "_is_self_write_only_diff (WP14 / IC-07d merge of the retired "
            "_drop_vcs_lock_only_meta / _drop_runtime_frontmatter_only_wp "
            "twins) reads the CALLER-supplied working-tree meta.json path to "
            "compare it against the committed baseline (via the injected "
            "GitPort) -- the filesystem twin of the GitPort pattern above, not "
            "a subprocess/worktree/placement decision."
        ),
    ),
    ContentDescriptor(
        rel_path="specify_cli/cli/commands/implement_cores.py",
        qualname="_is_self_write_only_diff",
        token_substring="source . read_text ( encoding =",
        occurrence=None,
        rationale=(
            "_is_self_write_only_diff's WP##.md leg reads the CALLER-supplied "
            "working-tree path to compare its frontmatter against the "
            "committed baseline (via the injected GitPort) -- the exact "
            "filesystem twin of its own meta.json leg above (WP01/#2570.1), "
            "same lightweight already-scoped read, not a subprocess/worktree/"
            "placement decision."
        ),
    ),
    ContentDescriptor(
        rel_path="specify_cli/cli/commands/implement_cores.py",
        qualname="_files_changed_vs_ref",
        token_substring="source . read_bytes ( )",
        occurrence=None,
        rationale=(
            "_files_changed_vs_ref reads the CALLER-supplied working-tree path "
            "to test idempotency against the committed ref (via the injected "
            "GitPort) -- same rationale as _is_self_write_only_diff above."
        ),
    ),
)


@functools.cache
def _io_allowlist_source(rel_path: str) -> str:
    """Read (and cache) an ``_IO_ALLOWLIST_SITES`` descriptor's source file,
    once. Two descriptors (the ``_SubprocessGitPort`` pair) share a file --
    caching avoids re-reading it once per descriptor.
    """
    return (_SRC_ROOT / rel_path).read_text(encoding="utf-8")


#: Every ``_IO_ALLOWLIST_SITES`` descriptor resolved ONCE at import time to its
#: live full ``(rel_path, qualname, token_line)`` composite key (NFR-004:
#: never hand-author the key literal). RAISES ``DescriptorResolutionError`` at
#: import time if a descriptor is already ambiguous or dangling -- the
#: earliest possible surfacing of a mis-authored ``token_substring``.
_IO_ALLOWLIST_SEEDED_KEYS: dict[ContentDescriptor, CompositeKey] = {
    descriptor: resolve_descriptor(_io_allowlist_source(descriptor.rel_path), descriptor)
    for descriptor in _IO_ALLOWLIST_SITES
}


def _build_io_allowlist() -> dict[tuple[str, str], str]:
    """Narrow ``_IO_ALLOWLIST_SEEDED_KEYS`` to the ``(qualname, token_line)``
    shape.

    ``_unallowlisted_io_violations`` / ``test_io_allowlist_entries_are_not_stale``
    key discovered/live sites via ``composite_key(source, lineno)`` -- a bare
    2-tuple with no ``rel_path`` component -- so the allowlist they consult
    must match that shape (mirrors
    ``test_single_mission_surface_resolver.py``'s ``_build_allowlisted_raw_joins``).
    """
    return {
        (qualname, token_line): descriptor.rationale
        for descriptor, (_rel_path, qualname, token_line) in _IO_ALLOWLIST_SEEDED_KEYS.items()
    }


#: Composite-keyed allowlist: ``(qualname, token_line) -> rationale``.
_IO_ALLOWLIST: dict[tuple[str, str], str] = _build_io_allowlist()


def _unallowlisted_io_violations(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    rel_path = path.relative_to(_SRC_ROOT).as_posix()
    out: list[str] = []
    for violation in find_banned_io_calls(source):
        key = composite_key(source, violation.lineno)
        if key in _IO_ALLOWLIST:
            continue
        out.append(f"{rel_path}:{violation.lineno}  {violation.description}  key={key!r}")
    return out


# ---------------------------------------------------------------------------
# T028(a) -- anti-vacuous: the cores file list resolves to real files.
# ---------------------------------------------------------------------------


def test_core_files_exist() -> None:
    missing = [str(p) for p in _CORE_FILES if not p.is_file()]
    assert not missing, f"Pure-core module paths do not exist on the current tree: {missing}"


# ---------------------------------------------------------------------------
# T028(b) -- the real assertion: zero unallowlisted I/O in the pure cores.
# ---------------------------------------------------------------------------


def test_cores_perform_no_unallowlisted_io() -> None:
    """FR-007: the four pure-core modules contain no I/O outside the allowlist.

    ``open``, ``Path.read_text/write_text/read_bytes/write_bytes``,
    ``subprocess.*``, ``os.system``, ``sqlite3.*``, and network calls are
    banned everywhere in these four files except the five documented sites
    in ``_IO_ALLOWLIST_SITES``.
    """
    all_violations: list[str] = []
    for path in _CORE_FILES:
        all_violations.extend(_unallowlisted_io_violations(path))

    assert not all_violations, (
        "Unallowlisted I/O call(s) found in a pure-core module:\n"
        + "\n".join(f"  {line}" for line in all_violations)
        + "\n\nEither invert the dependency (inject the I/O as a port, mirroring "
        "implement_cores.py's GitPort) or, if this is a genuinely lightweight, "
        "already-scoped read in the spirit of the five documented exceptions, "
        "add a justified entry to _IO_ALLOWLIST_SITES."
    )


def test_io_allowlist_entries_have_rationale() -> None:
    empty = [k for k, v in _IO_ALLOWLIST.items() if not v.strip()]
    assert not empty, f"IO allowlist entries with empty rationale: {empty}"


def test_io_allowlist_entries_are_not_stale() -> None:
    """Every allowlisted composite key still corresponds to a live banned call.

    A stale entry (line drifted, or the call was removed) would silently
    widen the allowlist without covering anything real.
    """
    live_keys: set[tuple[str, str]] = set()
    for path in _CORE_FILES:
        source = path.read_text(encoding="utf-8")
        for violation in find_banned_io_calls(source):
            live_keys.add(composite_key(source, violation.lineno))

    stale = sorted(k for k in _IO_ALLOWLIST if k not in live_keys)
    assert not stale, (
        f"Stale _IO_ALLOWLIST_SITES entries (no longer a live banned-call site): {stale}. "
        "Update the seed line/qualname or remove the entry."
    )


# ---------------------------------------------------------------------------
# T028(c) -- non-vacuous self-checks: a REAL I/O call in a FAKE core string is caught.
# ---------------------------------------------------------------------------


def test_clean_fake_core_has_no_violations() -> None:
    """A pure fake core (no I/O syntax at all) produces zero violations.

    Anti-false-positive control -- proves the classifier is not simply
    flagging every function call.
    """
    fake_core = textwrap.dedent(
        """
        from dataclasses import dataclass

        @dataclass
        class Result:
            ok: bool

        def decide(flag: bool) -> Result:
            return Result(ok=flag and not flag is None)
        """
    )
    assert find_banned_io_calls(fake_core) == []


def test_planted_read_text_call_is_caught() -> None:
    fake_core = textwrap.dedent(
        """
        from pathlib import Path

        def leaky_core(p: Path) -> str:
            return p.read_text()
        """
    )
    violations = find_banned_io_calls(fake_core)
    assert violations, "The classifier failed to catch a planted Path.read_text() call -- vacuous guard."
    assert "read_text" in violations[0].description


def test_planted_write_bytes_call_is_caught() -> None:
    fake_core = textwrap.dedent(
        """
        from pathlib import Path

        def leaky_core(p: Path, data: bytes) -> None:
            p.write_bytes(data)
        """
    )
    violations = find_banned_io_calls(fake_core)
    assert violations, "The classifier failed to catch a planted Path.write_bytes() call -- vacuous guard."
    assert "write_bytes" in violations[0].description


def test_planted_open_call_is_caught() -> None:
    fake_core = textwrap.dedent(
        """
        def leaky_core(path: str) -> str:
            with open(path) as fh:
                return fh.read()
        """
    )
    violations = find_banned_io_calls(fake_core)
    assert violations, "The classifier failed to catch a planted open(...) call -- vacuous guard."
    assert "open" in violations[0].description


def test_planted_subprocess_call_is_caught() -> None:
    fake_core = textwrap.dedent(
        """
        import subprocess

        def leaky_core() -> str:
            return subprocess.run(["git", "status"], capture_output=True).stdout
        """
    )
    violations = find_banned_io_calls(fake_core)
    assert violations, "The classifier failed to catch a planted subprocess.run(...) call -- vacuous guard."
    assert "subprocess" in violations[0].description


def test_planted_os_system_call_is_caught() -> None:
    fake_core = textwrap.dedent(
        """
        import os

        def leaky_core(cmd: str) -> int:
            return os.system(cmd)
        """
    )
    violations = find_banned_io_calls(fake_core)
    assert violations, "The classifier failed to catch a planted os.system(...) call -- vacuous guard."
    assert "os.system" in violations[0].description


def test_planted_sqlite3_call_is_caught() -> None:
    fake_core = textwrap.dedent(
        """
        import sqlite3

        def leaky_core(db_path: str):
            return sqlite3.connect(db_path)
        """
    )
    violations = find_banned_io_calls(fake_core)
    assert violations, "The classifier failed to catch a planted sqlite3.connect(...) call -- vacuous guard."
    assert "sqlite3" in violations[0].description


def test_planted_network_call_is_caught() -> None:
    fake_core = textwrap.dedent(
        """
        import requests

        def leaky_core(url: str):
            return requests.get(url)
        """
    )
    violations = find_banned_io_calls(fake_core)
    assert violations, "The classifier failed to catch a planted requests.get(...) call -- vacuous guard."
    assert "requests" in violations[0].description
