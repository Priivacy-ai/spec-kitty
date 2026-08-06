"""Single-source + scope-fence guards for the resolution/activation foundation.

Mission ``resolution-activation-foundation-01KZ9FKG``, WP05 (T023/T024/T025).
Governing: ``spec.md`` NFR-001/NFR-002/NFR-005, SC-001/SC-005; constraints
C-001/C-003; ``contracts/resolution-and-activation-contracts.md`` C-R1, C-S1.

These are *durable regression guards*, not one-off acceptance tests: they must
stay red if a future change reintroduces a second resolution/activation
source or crosses the scope fence WP01/WP02/WP04 drew.

Design pivot this file is written against (WP04)
--------------------------------------------------
The mission-type fail-closed ("a project needs at least one activated mission
type to create a mission") now lives at the mission-**create** boundary --
``specify_cli.core.mission_creation.create_mission_core`` -- NOT at
``PackContext`` construction. ``charter.pack_context._read_activated_mission_types``
is now **total**: an absent ``mission_type_activations`` key resolves to
``frozenset()``, the same as an authored empty list, and never backfills the
built-in four/all roster. T023(c) pins the absence of that backfill; T023(d)
pins that the fail-closed did not silently vanish in the pivot -- it moved,
it did not disappear.

Layer note: this file lives in ``tests/architectural`` and is read-only
against ``src/`` -- it asserts structure, it does not import anything that
would create a new dependency edge from a lower layer.
"""

from __future__ import annotations

import ast
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from tests.architectural.conftest import SourceFile

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"


def _rel(path: Path) -> str:
    """Return *path* relative to ``src/``, forward-slashed, as a lookup key."""
    return path.resolve().relative_to(_SRC).as_posix()


def _entry_for(src_source_tree: Mapping[Path, SourceFile], rel_path: str) -> SourceFile:
    """Return the cached :class:`SourceFile` for ``src/<rel_path>``."""
    for path, entry in src_source_tree.items():
        if _rel(path) == rel_path:
            return entry
    raise LookupError(f"no cached src_source_tree entry for {rel_path!r}")


def _single_function_named(tree: ast.AST, name: str) -> ast.FunctionDef:
    """Return the one ``def <name>(...)`` in *tree* (module-level or nested).

    Raises (via tuple-unpacking, deliberately not a ``len(...) == 1`` compare
    -- see ``tests/architectural/test_golden_count_ban.py``) if *name* is
    absent or ambiguous, so a rename or duplication fails loudly instead of
    silently scanning the wrong function.
    """
    matches = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    (only,) = matches
    return only


def _is_docstring_stmt(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


# ---------------------------------------------------------------------------
# T023(a) -- exactly one SPEC_KITTY_PACKS_ROOT env READ across src/ (NFR-001,
# SC-001, C-R1). Scoped to actual reads (os.environ.get / os.getenv /
# os.environ[...]), never a raw string-literal scan -- the retained docstring
# prose (pack_paths.py) and the constant name ``_PACKS_ROOT_ENV`` itself
# (kernel/paths.py) must not false-trip a bare-string scanner.
# ---------------------------------------------------------------------------

_PACKS_ROOT_ENV_VALUE = "SPEC_KITTY_PACKS_ROOT"
_ENVIRON_ATTR = "environ"
_GETENV_ATTR = "getenv"
_OS_MODULE = "os"


def _module_level_string_constants(tree: ast.AST) -> dict[str, str]:
    """Map every module-level ``NAME = "literal"`` assignment to its value.

    Resolves the real-world indirection ``kernel/paths.py`` uses:
    ``os.environ.get(_PACKS_ROOT_ENV)`` where ``_PACKS_ROOT_ENV =
    "SPEC_KITTY_PACKS_ROOT"`` is a module constant, not a re-typed literal at
    the call site. Cross-module indirection is out of scope (mirrors
    ``test_kernel_no_doctrine_import.py``'s own documented scope limits).
    """
    constants: dict[str, str] = {}
    body = getattr(tree, "body", [])
    for node in body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1  # golden-count: cardinality-is-contract
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            constants[node.targets[0].id] = node.value.value
    return constants


def _resolve_string(node: ast.expr | None, constants: Mapping[str, str]) -> str | None:
    """Resolve a call/subscript key argument to its literal string, if resolvable."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _is_os_environ_base(node: ast.expr) -> bool:
    """True for the ``os.environ`` attribute access or a bare ``environ`` name."""
    if isinstance(node, ast.Attribute) and node.attr == _ENVIRON_ATTR:
        return isinstance(node.value, ast.Name) and node.value.id == _OS_MODULE
    return isinstance(node, ast.Name) and node.id == _ENVIRON_ATTR


def _is_getenv_func(node: ast.expr) -> bool:
    """True for ``os.getenv`` or a bare (``from os import getenv``) reference."""
    if isinstance(node, ast.Attribute) and node.attr == _GETENV_ATTR:
        return isinstance(node.value, ast.Name) and node.value.id == _OS_MODULE
    return isinstance(node, ast.Name) and node.id == _GETENV_ATTR


def _env_read_key_node(node: ast.Call | ast.Subscript) -> ast.expr | None:
    """Return the key-argument node of an env-read call/subscript, else ``None``.

    Matches exactly the three shapes T023(a) names: ``os.environ.get(<key>)``,
    ``os.getenv(<key>)``, and ``os.environ[<key>]`` (plus the bare-import
    forms). Anything else (``.keys()``, an unrelated dict's ``.get``, a
    string literal sitting in a docstring or comment) is invisible to this
    matcher by construction.
    """
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "get" and _is_os_environ_base(func.value):
            return node.args[0] if node.args else None
        if _is_getenv_func(func):
            return node.args[0] if node.args else None
        return None
    if _is_os_environ_base(node.value):
        return node.slice
    return None


def find_packs_root_env_reads(tree: ast.AST) -> list[int]:
    """Return the line numbers of every resolved ``SPEC_KITTY_PACKS_ROOT`` env read in *tree*."""
    constants = _module_level_string_constants(tree)
    reads: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Call, ast.Subscript)):
            continue
        key_node = _env_read_key_node(node)
        if key_node is not None and _resolve_string(key_node, constants) == _PACKS_ROOT_ENV_VALUE:
            reads.append(node.lineno)
    return reads


def test_packs_root_env_read_lives_only_in_kernel_paths(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """NFR-001/SC-001/C-R1: exactly one src/ module reads SPEC_KITTY_PACKS_ROOT.

    After WP01 (kernel primitive) and WP02 (doctrine delegation), the one
    legitimate read lives in ``kernel/paths.py``; ``doctrine/pack_paths.py``
    no longer forks its own read (it delegates wholesale to
    ``kernel.paths.get_built_in_pack_root``). A second reader appearing
    anywhere else in ``src/`` is exactly the split-brain regression this
    mission exists to close.
    """
    files_with_reads = {
        _rel(path) for path, entry in src_source_tree.items() if find_packs_root_env_reads(entry.tree)
    }

    assert files_with_reads == {"kernel/paths.py"}, (
        "SPEC_KITTY_PACKS_ROOT must be read via os.environ.get/os.getenv/"
        "os.environ[...] in exactly one src/ module -- the kernel primitive "
        f"(NFR-001/SC-001/C-R1). Found reads in: {sorted(files_with_reads)}"
    )


@pytest.mark.parametrize(
    "source",
    [
        'value = os.environ.get("SPEC_KITTY_PACKS_ROOT")\n',
        'value = os.getenv("SPEC_KITTY_PACKS_ROOT")\n',
        'value = os.environ["SPEC_KITTY_PACKS_ROOT"]\n',
    ],
    ids=["environ-get", "getenv", "environ-subscript"],
)
def test_scanner_catches_every_named_read_shape(source: str) -> None:
    """Non-vacuity: each of the three literal shapes T023(a) names is caught."""
    tree = ast.parse(source)

    assert find_packs_root_env_reads(tree) == [1]


def test_scanner_resolves_local_constant_indirection() -> None:
    """Non-vacuity: the real ``kernel/paths.py`` shape (constant indirection) is caught.

    ``os.environ.get(_PACKS_ROOT_ENV)`` where ``_PACKS_ROOT_ENV`` is a
    module-level string constant assigned the literal env-var name -- the
    exact indirection ``kernel/paths.py`` uses -- must resolve, not be
    invisible to the scanner.
    """
    tree = ast.parse(
        '_PACKS_ROOT_ENV = "SPEC_KITTY_PACKS_ROOT"\n'
        "\n"
        "\n"
        "def read() -> str | None:\n"
        "    return os.environ.get(_PACKS_ROOT_ENV)\n"
    )

    assert find_packs_root_env_reads(tree) == [5]


def test_scanner_ignores_docstrings_constant_definition_and_unrelated_calls() -> None:
    """No false positives: the constant *name*, prose, and other ``.get()`` calls are silent.

    Mirrors the exact false-trip traps named in T023(a): the retained
    docstring prose in ``pack_paths.py`` and the bare constant-name literal
    ``_PACKS_ROOT_ENV = "SPEC_KITTY_PACKS_ROOT"`` (an assignment, not a read)
    must not themselves count as a read.
    """
    tree = ast.parse(
        '"""Docstring mentioning SPEC_KITTY_PACKS_ROOT is not a read."""\n'
        "\n"
        '_PACKS_ROOT_ENV = "SPEC_KITTY_PACKS_ROOT"\n'
        "\n"
        "\n"
        "def unrelated() -> None:\n"
        '    config = {"SPEC_KITTY_PACKS_ROOT": 1}\n'
        '    config.get("SPEC_KITTY_PACKS_ROOT")\n'
        '    os.environ.get("SPEC_KITTY_TEMPLATE_ROOT")\n'
    )

    assert find_packs_root_env_reads(tree) == []


# ---------------------------------------------------------------------------
# T023(b) -- exactly one ``get_package_asset_root`` implementation body
# (NFR-001, SC-001, C-R1). ``specify_cli/runtime/home.py`` must stay a thin
# delegate, never a second forked resolver body.
# ---------------------------------------------------------------------------

_DELEGATE_CALL_MARKER = "kernel.paths.get_package_asset_root()"


def _function_defs_named(tree: ast.AST, name: str) -> list[ast.FunctionDef]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]


def _is_delegate_only_body(func: ast.FunctionDef) -> bool:
    """True if *func*'s non-docstring body is exactly one delegating ``return``.

    A "delegate" here means: a single statement, ``return <expr>``, whose
    unparsed source contains the exact ``kernel.paths.get_package_asset_root()``
    call -- i.e. it forwards wholesale rather than re-implementing resolution.
    """
    body = [stmt for stmt in func.body if not _is_docstring_stmt(stmt)]
    if len(body) != 1 or not isinstance(body[0], ast.Return) or body[0].value is None:
        return False
    return _DELEGATE_CALL_MARKER in ast.unparse(body[0].value)


def test_get_package_asset_root_has_exactly_one_implementation_body(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """NFR-001/SC-001/C-R1: one real body (kernel), one known thin delegate.

    Pins both halves precisely: the real resolution logic lives ONLY in
    ``kernel/paths.py``, and the ``specify_cli/runtime/home.py`` re-export
    shim is still a pure delegate (not a second forked body) -- both facts
    matter, so both are asserted by name rather than by count alone.
    """
    real_bodies: set[str] = set()
    delegate_bodies: set[str] = set()
    for path, entry in src_source_tree.items():
        for func in _function_defs_named(entry.tree, "get_package_asset_root"):
            rel = _rel(path)
            if _is_delegate_only_body(func):
                delegate_bodies.add(rel)
            else:
                real_bodies.add(rel)

    assert real_bodies == {"kernel/paths.py"}, (
        f"expected exactly one real get_package_asset_root() body, in "
        f"kernel/paths.py; found real (non-delegate) bodies in: {sorted(real_bodies)}"
    )
    assert delegate_bodies == {"specify_cli/runtime/home.py"}, (
        "expected the specify_cli/runtime/home.py re-export shim to still be a "
        f"thin delegate to kernel.paths.get_package_asset_root(); found delegate "
        f"bodies in: {sorted(delegate_bodies)}"
    )


# ---------------------------------------------------------------------------
# T023(c) -- 0 implicit config-absent ``mission_type_activations`` all-four
# backfill (NFR-001, C-A1). Scoped STRICTLY to
# ``charter.pack_context._read_activated_mission_types`` -- the sibling
# ``_read_activated_kinds`` three-state fallback is a different, legitimate
# contract (FR-039) and MUST NOT be flagged.
# ---------------------------------------------------------------------------

_PACK_CONTEXT_REL_PATH = "charter/pack_context.py"
_MISSION_TYPE_READER = "_read_activated_mission_types"
_KINDS_READER = "_read_activated_kinds"
_BUILTIN_MISSION_TYPE_BACKFILL_CALLEE = "builtin_mission_type_id_set"


def _call_target_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _called_names(func: ast.AST) -> set[str]:
    """Return every callee name/attr invoked anywhere inside *func*."""
    names: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and (name := _call_target_name(node)) is not None:
            names.add(name)
    return names


def test_read_activated_mission_types_has_no_implicit_builtin_backfill(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """C-A1/NFR-001: the mission-type reader never calls the builtin-roster backfill.

    Construction is total (WP04): an absent ``mission_type_activations`` key
    resolves to ``frozenset()`` here, never the all-four/all-built-in roster.
    """
    entry = _entry_for(src_source_tree, _PACK_CONTEXT_REL_PATH)
    reader = _single_function_named(entry.tree, _MISSION_TYPE_READER)

    assert _BUILTIN_MISSION_TYPE_BACKFILL_CALLEE not in _called_names(reader), (
        f"{_MISSION_TYPE_READER} must not call "
        f"{_BUILTIN_MISSION_TYPE_BACKFILL_CALLEE}() on the config-absent path "
        "-- that is exactly the implicit all-four backfill FR-008 removed."
    )


def test_sibling_kinds_fallback_stays_out_of_scope_and_untouched(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """Scope precision: the sibling ``_read_activated_kinds`` three-state fallback
    is a different, legitimate contract (FR-039) and is untouched by this
    mission -- proving the guard above is scoped narrowly rather than
    accidentally also asserting (or masking a change to) this sibling.
    """
    entry = _entry_for(src_source_tree, _PACK_CONTEXT_REL_PATH)
    kinds_reader = _single_function_named(entry.tree, _KINDS_READER)

    assert "_BUILTIN_ARTIFACT_KINDS" in ast.unparse(kinds_reader), (
        f"{_KINDS_READER} is expected to keep its own three-state "
        "_BUILTIN_ARTIFACT_KINDS fallback (FR-039, out of scope for this "
        "mission) -- if this fails, the sibling contract changed and this "
        "guard's scope note needs re-review, not silent widening."
    )


def test_backfill_scanner_catches_a_synthetic_builtin_call() -> None:
    """Non-vacuity: the ``_called_names`` scanner does detect the forbidden callee.

    Reproduces the exact pre-WP04 shape (a config-absent branch backfilling
    via ``builtin_mission_type_id_set()``) so a regression of this kind would
    be caught by the assertion above, not silently missed by a scanner that
    never actually inspects call targets.
    """
    tree = ast.parse(
        "def _read_activated_mission_types(data):\n"
        "    activated = data.get('mission_type_activations')\n"
        "    if activated is None:\n"
        "        return builtin_mission_type_id_set()\n"
        "    return frozenset(activated)\n"
    )
    reader = _single_function_named(tree, _MISSION_TYPE_READER)

    assert _BUILTIN_MISSION_TYPE_BACKFILL_CALLEE in _called_names(reader)


# ---------------------------------------------------------------------------
# T023(d) -- positive invariant of the WP04 pivot: the mission-type
# fail-closed EXISTS at the mission-create boundary
# (specify_cli.core.mission_creation.create_mission_core). Pins that
# construction-total did NOT silently drop the fail-closed -- it moved.
# ---------------------------------------------------------------------------

_MISSION_CREATION_REL_PATH = "specify_cli/core/mission_creation.py"
_CREATE_MISSION_CORE = "create_mission_core"
_ACTIVATION_READ_CALLEE = "existing_mission_types"
_CONFIG_ERROR_CALLEE = "CharterPackConfigError"


def _has_activation_fail_closed_gate(func: ast.FunctionDef) -> bool:
    """True if *func* contains ``if not <existing_mission_types(...)>: raise <CharterPackConfigError(...)>``.

    Matches the exact create-boundary shape WP04 introduced: an ``if`` whose
    test is ``not <call to existing_mission_types>`` and whose body raises
    ``CharterPackConfigError``.
    """
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)):
            continue
        operand = test.operand
        if not (isinstance(operand, ast.Call) and _call_target_name(operand) == _ACTIVATION_READ_CALLEE):
            continue
        raises_config_error = any(
            isinstance(stmt, ast.Raise)
            and isinstance(stmt.exc, ast.Call)
            and _call_target_name(stmt.exc) == _CONFIG_ERROR_CALLEE
            for stmt in ast.walk(node)
        )
        if raises_config_error:
            return True
    return False


def test_create_mission_core_has_the_activation_fail_closed_gate(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """Static proof the pivot's fail-closed still guards mission creation.

    ``PackContext`` construction is total (T023(c)); this is the narrowest
    funnel every mission-create path passes through, so the "provision your
    charter" error must fire HERE, not nowhere.
    """
    entry = _entry_for(src_source_tree, _MISSION_CREATION_REL_PATH)
    func = _single_function_named(entry.tree, _CREATE_MISSION_CORE)

    assert _has_activation_fail_closed_gate(func), (
        f"{_CREATE_MISSION_CORE} must gate on "
        f"`if not {_ACTIVATION_READ_CALLEE}(...): raise {_CONFIG_ERROR_CALLEE}(...)` "
        "-- the WP04 mission-create-boundary fail-closed appears to have moved "
        "or been dropped."
    )


def test_gate_scanner_does_not_match_an_unrelated_if_raise() -> None:
    """Non-vacuity: an unrelated ``if``/``raise`` pair does not false-positive."""
    tree = ast.parse(
        "def create_mission_core():\n"
        "    if not some_other_check():\n"
        "        raise ValueError('unrelated')\n"
    )
    func = _single_function_named(tree, _CREATE_MISSION_CORE)

    assert _has_activation_fail_closed_gate(func) is False


def _init_minimal_git_repo(repo: Path) -> None:
    """Initialize a minimal ``.kittify``/``kitty-specs`` git repo for the drive below."""
    (repo / ".kittify").mkdir(parents=True, exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "wp05@test.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "WP05"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=repo, check=True)


@pytest.mark.git_repo
def test_create_mission_core_raises_on_empty_activation_set(tmp_path: Path) -> None:
    """Behavioral companion to the static gate above: drive an empty-activation
    repo through the real function and expect the raise.

    The full acceptance matrix for this contract (absent key / authored `[]`
    / provisioned) already lives in
    ``tests/core/test_mission_create_activation_gate.py`` (WP04's own suite);
    this single drive keeps the WP05 architectural file self-contained proof
    that the pivot's fail-closed is live code, not merely present in source.
    """
    from charter.pack_context import CharterPackConfigError
    from specify_cli.core.mission_creation import create_mission_core

    _init_minimal_git_repo(tmp_path)
    (tmp_path / ".kittify" / "config.yaml").write_text("vcs:\n  type: git\n", encoding="utf-8")

    with pytest.raises(CharterPackConfigError):
        create_mission_core(tmp_path, "wp05-activation-fence-guard", allow_worktree_context=True)


# ---------------------------------------------------------------------------
# T024 -- scope fence (C-001, C-003, C-S1, SC-005): mission-type is still not
# an ArtifactKind; the universe extension is intact; the availability readers
# stay filesystem-based (never consulting the activation set); the
# specify_cli/missions tree is not deleted.
# ---------------------------------------------------------------------------

_MISSION_TYPE_TOKEN = "mission-type"
_LIST_AVAILABLE_MISSIONS_REL_PATH = "specify_cli/mission.py"
_LIST_AVAILABLE_MISSIONS = "list_available_missions"
_DISCOVERY_CONTEXT_REL_PATH = "runtime/next/runtime_bridge_io.py"
_BUILD_DISCOVERY_CONTEXT = "_build_discovery_context"

#: Identifiers whose presence inside an availability reader would mean it
#: consults the activation authority -- exactly what C-003/SC-005 forbids
#: these two readers from doing (this mission prepares the authority; #2659
#: is the repoint, not this one).
_ACTIVATION_VOCABULARY = frozenset(
    {
        "activated_mission_types",
        "existing_mission_types",
        "mission_type_activations",
        "PackContext",
        "pack_context",
    }
)


def test_mission_type_is_not_promoted_to_an_artifact_kind() -> None:
    """C-001/SC-005: ``MissionTypeNotAnArtifactKind`` is still raised for "mission-type"."""
    from doctrine.artifact_kinds import ArtifactKind, MissionTypeNotAnArtifactKind

    with pytest.raises(MissionTypeNotAnArtifactKind):
        ArtifactKind.from_operator_token(_MISSION_TYPE_TOKEN)


def test_mission_type_universe_extension_is_intact() -> None:
    """C-001/SC-005: ``_MISSION_TYPE_UNIVERSE_EXTENSION`` still names ``mission_types``."""
    from doctrine.drg.org_pack_loader import _MISSION_TYPE_UNIVERSE_EXTENSION

    assert frozenset({"mission_types"}) == _MISSION_TYPE_UNIVERSE_EXTENSION


def test_built_in_dir_gains_no_mission_type_kind_entry() -> None:
    """Optional C-002/C-004 review-only-fence guard: no MISSION_TYPE ArtifactKind member exists.

    C-002 (nested-vs-flat) and C-004 (keystone/schema) are review-only fences
    with no positive code marker to assert -- this is the one cheap, real
    signal available: the kind enum itself gained no mission-type member.
    """
    from doctrine.artifact_kinds import ArtifactKind

    assert "MISSION_TYPE" not in {member.name for member in ArtifactKind}


def _identifier_and_string_tokens(node: ast.AST) -> set[str]:
    """Return every ``Name``/``Attribute`` identifier and string literal in *node*."""
    tokens: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            tokens.add(child.id)
        elif isinstance(child, ast.Attribute):
            tokens.add(child.attr)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            tokens.add(child.value)
    return tokens


def test_list_available_missions_does_not_consult_the_activation_set(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """C-003/SC-005: ``list_available_missions`` stays filesystem-based, unchanged."""
    entry = _entry_for(src_source_tree, _LIST_AVAILABLE_MISSIONS_REL_PATH)
    func = _single_function_named(entry.tree, _LIST_AVAILABLE_MISSIONS)

    touched = _identifier_and_string_tokens(func) & _ACTIVATION_VOCABULARY
    assert not touched, (
        f"{_LIST_AVAILABLE_MISSIONS} must stay filesystem-based and must not "
        f"consult the activation authority (C-003/SC-005 -- that repoint is "
        f"#2659, out of scope here); found: {sorted(touched)}"
    )


def test_build_discovery_context_does_not_consult_the_activation_set(
    src_source_tree: Mapping[Path, SourceFile],
) -> None:
    """C-003/SC-005: ``_build_discovery_context`` (runtime_bridge_io) stays filesystem-based, unchanged."""
    entry = _entry_for(src_source_tree, _DISCOVERY_CONTEXT_REL_PATH)
    func = _single_function_named(entry.tree, _BUILD_DISCOVERY_CONTEXT)

    touched = _identifier_and_string_tokens(func) & _ACTIVATION_VOCABULARY
    assert not touched, (
        f"{_BUILD_DISCOVERY_CONTEXT} must stay filesystem-based and must not "
        f"consult the activation authority (C-003/SC-005 -- that repoint is "
        f"#2659, out of scope here); found: {sorted(touched)}"
    )


def test_activation_vocabulary_scanner_catches_a_synthetic_consult() -> None:
    """Non-vacuity: a synthetic function that DOES consult the activation set is caught."""
    tree = ast.parse(
        "def list_available_missions(kittify_dir=None):\n"
        "    return existing_mission_types(kittify_dir)\n"
    )
    func = _single_function_named(tree, _LIST_AVAILABLE_MISSIONS)

    touched = _identifier_and_string_tokens(func) & _ACTIVATION_VOCABULARY
    assert touched == {"existing_mission_types"}


def test_specify_cli_missions_tree_is_still_present_on_disk() -> None:
    """C-003/SC-005: ``src/specify_cli/missions/`` is not deleted by this mission."""
    assert (_SRC / "specify_cli" / "missions").is_dir()


# ---------------------------------------------------------------------------
# T025 -- layer + terminology gates (NFR-002, NFR-005): the three named gates
# already provide full coverage for this mission's own claims (kernel<-doctrine
# import boundary, the general layer-rule pytestarch checks, and the
# terminology canon). No mission-specific angle is missing -- this suite adds
# no duplicate assertion here; it is verified green from the primary checkout
# and cited in the WP05 report/PR notes:
#
#   * tests/architectural/test_kernel_no_doctrine_import.py
#   * tests/architectural/test_layer_rules.py
#   * tests/architectural/test_no_legacy_terminology.py
# ---------------------------------------------------------------------------
