"""Gate 5 (FR-007/FR-010, WP04): zero-tolerance `._inner` reach-around on
``charter.resolver.DoctrineService`` outside ``src/charter/**``.

A post-plan squad delegate found that ``src/specify_cli/invocation/registry.py``
and ``src/specify_cli/invocation/org_profiles.py`` both read
``service._inner.agent_profiles`` directly -- reaching straight past the
wrapper's own charter-activation filtering to the raw, unfiltered
``AgentProfileRepository``. Left open, this defeats every gate the sibling
FR-001-006/008 work ships: a "sole door" factory with a documented side door
is not a sole door. FR-010 closes the two known sites onto the pinned
``DoctrineService.agent_profile_repository`` accessor (WP01, FR-001); this
module is the durable, non-fakeable proof that closure holds and cannot be
silently reopened anywhere else in the codebase (C-002: zero-tolerance, no
shrink-only allowlist -- see NFR-001/C-002 in
``kitty-specs/charter-sole-door-bypass-closure-01KZ3WAA/spec.md``).

Detection strategy
-------------------
A bare ``grep -r "._inner"`` is too broad: ``src/specify_cli/auth/transport.py``
and ``src/specify_cli/events/decision_log.py`` both hold unrelated, legitimate
``self._inner`` wrapper attributes (an ``OAuthHttpClient`` wrapper and a
decision-log delegate, respectively) that have nothing to do with
``DoctrineService`` -- a bare scan would false-positive on both (debugger-debbie
finding, post-tasks squad). This gate instead resolves, per file, which local
names are bound (directly or by import alias) to a *construction* of a
``charter.resolver.DoctrineService`` -- either the sanctioned factory
(``build_activation_aware_doctrine_service``, FR-008's unified builder) or the
wrapper's own constructor (``charter.resolver.DoctrineService``) -- and flags a
reach-around only when its receiver is one of those tainted names, or an
inline construction call. ``self._inner`` on an untainted receiver (the two
false-positive risks above) is never flagged, because ``self`` is never
assigned from either constructor.

Landing-fold gate hardening: three widenings (A2/A3/A4)
------------------------------------------------------------
Adversarial-review injection probes measured this gate at a 3/11 real catch
rate. Three structural root causes accounted for almost every miss:

* **A2 -- ``_tainted_names`` only recognised ``ast.Assign`` with a bare
  ``ast.Name`` target.** Missed: ``service: DoctrineService = ...``
  (``ast.AnnAssign`` -- the *default* spelling in a mypy-clean codebase),
  walrus (``ast.NamedExpr``), and tuple-unpack targets of ``ast.Assign``.
  :func:`_tainted_names` now handles all four shapes.
* **A3 -- the ``ast.Attribute`` branch of the sanctioned-origin check consulted
  only ``module_aliases``, never ``from_imports``.** So ``from charter import
  resolver`` then ``resolver.DoctrineService(...)`` never tainted. Fixed by
  reusing :func:`tests.architectural._sole_door_scan._lookup_module` (which
  already resolves "``from pkg import sub`` then ``sub.Cls(...)``") instead of
  the local ``module_aliases.get(dotted, dotted)`` -- the same primitive Gates
  1-3 already share, via the promoted :class:`_Bindings` type.
* **A4 -- attribute-spelling alternatives were structurally invisible.**
  Detection required an ``ast.Attribute`` literally spelled ``.attr ==
  "_inner"``. Missed: ``getattr(svc, "_inner")``,
  ``object.__getattribute__(svc, "_inner")``, and ``svc.__dict__["_inner"]`` --
  the reach-around reopens in one line with any of these. Now flagged
  alongside the original ``.attr`` shape; receiver taint logic is unchanged.

Known limitation (documented, not hidden): this is a static, per-file,
name-based approximation -- not full dataflow/type inference. A caller that
threads a ``DoctrineService`` through an unconventional indirection (e.g. a
dict of services, or a return value re-assigned across module boundaries)
could in principle evade detection. This is the same class of tradeoff
``test_mission_resolver_walker_gate.py`` already accepts for its own taint
heuristic. Extending the taint model is a deliberate, reviewed edit to this
file, not silent scope creep.

Zero-tolerance (C-002): no allowlist. Only ``src/charter/**`` -- the
wrapper's own implementation module, where ``._inner`` access *is* the sole
door's construction -- is exempt, keyed by directory prefix, never by
individual file or line.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.architectural._sole_door_scan import _Bindings, _lookup_module

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

# The wrapper's own implementation lives here; ._inner access inside it is
# the sole door's construction, not a reach-around. Directory-prefix keyed
# (G-2 style), never per-file/per-line.
_EXEMPT_DIR_PREFIX = "src/charter/"

# The one sanctioned construction path for a charter.resolver.DoctrineService
# outside src/charter/** (FR-008's unified builder).
_FACTORY_FUNC_NAME = "build_activation_aware_doctrine_service"
_FACTORY_MODULES = frozenset(
    {"specify_cli.doctrine_service_factory", "charter.doctrine_service_builder"}
)

# The wrapper's own constructor -- tracked too so the taint heuristic stays
# correct even though NFR-001's sibling gate independently forbids
# constructing it directly outside src/charter/**.
_CTOR_NAME = "DoctrineService"
_CTOR_MODULE = "charter.resolver"


def _collect_import_aliases(tree: ast.AST) -> _Bindings:
    aliases = _Bindings()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local = alias.asname or alias.name
                aliases.from_imports[local] = (node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name
                aliases.module_aliases[local] = alias.name
    return aliases


def _dotted_prefix(node: ast.expr) -> str | None:
    """Return the dotted-name string of a Name/Attribute chain, else None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_prefix(node.value)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _matches_sanctioned_origin(module: str, name: str) -> bool:
    return (module in _FACTORY_MODULES and name == _FACTORY_FUNC_NAME) or (
        module == _CTOR_MODULE and name == _CTOR_NAME
    )


def _call_constructs_doctrine_service(call: ast.Call, aliases: _Bindings) -> bool:
    """True if *call* invokes the factory or the wrapper constructor.

    Resolves by import alias (``from module import name as local``), by
    module-qualified reference (``module.name(...)``), or by module import
    alias (``import module as m`` then ``m.name(...)``) -- never by bare
    text matching (mirrors NFR-001's qualname-resolution requirement for the
    sibling raw-construction gate).

    A3 fix (landing-fold gate hardening): the module-qualified branch now
    resolves *dotted* through :func:`_lookup_module` -- the SAME primitive
    Gates 1-3 use -- instead of a local ``module_aliases.get(dotted, dotted)``
    that only ever recognised ``import module as alias``. ``_lookup_module``
    additionally resolves ``from pkg import sub`` then ``sub.Cls(...)``, so
    ``from charter import resolver`` followed by
    ``resolver.DoctrineService(...)`` now taints too.
    """
    func = call.func
    if isinstance(func, ast.Name):
        origin = aliases.from_imports.get(func.id)
        return origin is not None and _matches_sanctioned_origin(*origin)
    if isinstance(func, ast.Attribute):
        dotted = _dotted_prefix(func.value)
        if dotted is None:
            return False
        resolved_module = _lookup_module(dotted, [aliases])
        return _matches_sanctioned_origin(resolved_module, func.attr)
    return False


def _taint_if_construction(
    tainted: set[str],
    target: ast.expr,
    value: ast.expr,
    aliases: _Bindings,
) -> None:
    if (
        isinstance(target, ast.Name)
        and isinstance(value, ast.Call)
        and _call_constructs_doctrine_service(value, aliases)
    ):
        tainted.add(target.id)


def _tainted_names(tree: ast.AST, aliases: _Bindings) -> set[str]:
    """Names (file-wide, flow-insensitive -- deliberately coarse, mirrors
    ``test_mission_resolver_walker_gate.py``) assigned from a construction
    call.

    A2 fix (landing-fold gate hardening): the predecessor only recognised
    ``ast.Assign`` with a bare ``ast.Name`` target. Real code frequently binds
    a ``DoctrineService`` via annotated assignment (``service:
    DoctrineService = ...`` -- the default spelling in a mypy-clean codebase),
    walrus (``:=``), or tuple-unpack (``service, flag = ctor(), True``); all
    four shapes are handled here.
    """
    tainted: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, (ast.Tuple, ast.List)) and isinstance(
                    node.value, (ast.Tuple, ast.List)
                ):
                    for sub_target, sub_value in zip(
                        target.elts, node.value.elts, strict=False
                    ):
                        _taint_if_construction(tainted, sub_target, sub_value, aliases)
                else:
                    _taint_if_construction(tainted, target, node.value, aliases)
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None:
                _taint_if_construction(tainted, node.target, node.value, aliases)
        elif isinstance(node, ast.NamedExpr):
            _taint_if_construction(tainted, node.target, node.value, aliases)
    return tainted


def _is_string_literal(node: ast.expr, value: str) -> bool:
    return isinstance(node, ast.Constant) and node.value == value


def _is_inner_getattr_call(call: ast.Call) -> bool:
    """True for ``getattr(recv, "_inner")`` or
    ``object.__getattribute__(recv, "_inner")``.

    A4 fix (landing-fold gate hardening): both spellings reach the identical
    attribute as ``recv._inner`` and are just as capable of reopening the
    reach-around; a gate that only pattern-matches ``ast.Attribute`` is blind
    to them.
    """
    func = call.func
    is_getattr = isinstance(func, ast.Name) and func.id == "getattr"
    is_object_getattribute = (
        isinstance(func, ast.Attribute)
        and func.attr == "__getattribute__"
        and isinstance(func.value, ast.Name)
        and func.value.id == "object"
    )
    if not (is_getattr or is_object_getattribute):
        return False
    return len(call.args) >= 2 and _is_string_literal(call.args[1], "_inner")


def _is_inner_dict_subscript(node: ast.Subscript) -> bool:
    """True for ``<recv>.__dict__["_inner"]`` (A4 fix)."""
    value = node.value
    if not (isinstance(value, ast.Attribute) and value.attr == "__dict__"):
        return False
    return _is_string_literal(node.slice, "_inner")


def _receiver_is_tainted(
    receiver: ast.expr, tainted: set[str], aliases: _Bindings
) -> bool:
    if isinstance(receiver, ast.Name) and receiver.id in tainted:
        return True
    return isinstance(receiver, ast.Call) and _call_constructs_doctrine_service(
        receiver, aliases
    )


def _find_inner_reacharounds(path: Path) -> list[int]:
    """Return line numbers of flagged reach-around accesses in *path*.

    Covers three spellings (A4 fix): direct ``.attr == "_inner"`` access,
    ``getattr(recv, "_inner")`` / ``object.__getattribute__(recv, "_inner")``,
    and ``recv.__dict__["_inner"]``.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []

    aliases = _collect_import_aliases(tree)
    tainted = _tainted_names(tree, aliases)
    violations: list[int] = []

    for node in ast.walk(tree):
        receiver: ast.expr
        if isinstance(node, ast.Attribute) and node.attr == "_inner":
            receiver = node.value
        elif isinstance(node, ast.Call) and _is_inner_getattr_call(node):
            receiver = node.args[0]
        elif isinstance(node, ast.Subscript) and _is_inner_dict_subscript(node):
            assert isinstance(node.value, ast.Attribute)
            receiver = node.value.value
        else:
            continue
        if _receiver_is_tainted(receiver, tainted, aliases):
            violations.append(node.lineno)

    return violations


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _scan_tree_for_violations(src_root: Path) -> dict[str, list[int]]:
    """Scan every ``*.py`` under *src_root*, skipping the exempt directory.

    Scope is derived from ``src_root.rglob("*.py")`` wholesale -- no
    hardcoded subdirectory list a new package could silently fall outside
    of (mirrors ``test_mission_resolver_walker_gate.py``'s G-3 guarantee).
    """
    violations: dict[str, list[int]] = {}
    for py_file in sorted(src_root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        rel = _rel(py_file)
        if rel.startswith(_EXEMPT_DIR_PREFIX):
            continue
        hits = _find_inner_reacharounds(py_file)
        if hits:
            violations[rel] = hits
    return violations


# ---------------------------------------------------------------------------
# Scope-derivation sanity check
# ---------------------------------------------------------------------------


def test_gate_scan_scope_reaches_known_files() -> None:
    """The gate must not silently go blind to any part of ``src/``.

    Asserts the wholesale ``rglob("*.py")`` scan reaches representative
    files scattered across distinct subpackages, including both known
    false-positive-risk files -- proving the scan actually visits them
    rather than skipping them by accident.
    """
    scanned = {_rel(p) for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts}

    representative_sample = {
        "src/specify_cli/invocation/registry.py",
        "src/specify_cli/invocation/org_profiles.py",
        "src/specify_cli/auth/transport.py",
        "src/specify_cli/events/decision_log.py",
        "src/charter/resolver.py",
    }
    missing = representative_sample - scanned
    assert not missing, (
        f"Gate scan scope did not reach: {sorted(missing)} -- "
        "the src/ walk may have silently narrowed."
    )
    assert len(scanned) > 200


# ---------------------------------------------------------------------------
# Known false-positive risks stay clean (debugger-debbie finding)
# ---------------------------------------------------------------------------


def test_gate_does_not_flag_unrelated_inner_attributes() -> None:
    """``auth/transport.py`` and ``events/decision_log.py`` must stay clean.

    Both hold legitimate ``self._inner`` wrapper attributes unrelated to
    ``DoctrineService`` (an ``OAuthHttpClient`` wrapper and a decision-log
    delegate). A gate broad enough to flag these would be too broad to ship
    (review guidance in the WP04 task file).
    """
    for rel in (
        "src/specify_cli/auth/transport.py",
        "src/specify_cli/events/decision_log.py",
    ):
        hits = _find_inner_reacharounds(_REPO_ROOT / rel)
        assert hits == [], f"{rel} unexpectedly flagged at lines {hits}"


# ---------------------------------------------------------------------------
# The main gate
# ---------------------------------------------------------------------------


def test_no_inner_reacharound_on_doctrine_service_outside_charter() -> None:
    """Zero reach-around access on a ``charter.resolver.DoctrineService``
    outside ``src/charter/**`` (FR-010, NFR-001).

    Zero-tolerance (C-002): no allowlist. To fix a violation, use
    ``DoctrineService.agent_profile_repository`` (for ``agent_profiles``
    lineage/provenance operations) or ``DoctrineService.raw_repository(kind)``
    (for any other gated kind's raw repository operations) instead of
    reaching past the sole door.
    """
    violations = _scan_tree_for_violations(_SRC_ROOT)

    if violations:
        details = "\n".join(f"  {path}: lines {lines}" for path, lines in sorted(violations.items()))
        pytest.fail(
            "Found `._inner` attribute access (or an equivalent getattr/__dict__ "
            "reach-around) on a charter.resolver.DoctrineService "
            "outside src/charter/** (FR-010). Use the `agent_profile_repository` "
            "accessor (or `raw_repository(kind)` for other gated kinds) instead of "
            "reaching past the sole door.\n\n"
            f"Violations:\n{details}"
        )


# ---------------------------------------------------------------------------
# Self-mutation proof (NFR-003): the gate must actually bite, in both
# directions -- true positive AND true negative, at function-local scope.
# ---------------------------------------------------------------------------


def test_planted_reacharound_at_function_local_scope_is_detected(tmp_path: Path) -> None:
    """A planted ``._inner`` reach-around on a tainted variable is caught.

    Reproduces the exact real-violation shape (``service = <factory>(...)``
    then ``service._inner.<kind>``) at function-local scope -- not
    module-level-only, matching the actual shape of the real violations
    (spec.md NFR-003).
    """
    planted = tmp_path / "planted_reacharound.py"
    planted.write_text(
        "from specify_cli.doctrine_service_factory import (\n"
        "    build_activation_aware_doctrine_service,\n"
        ")\n"
        "\n"
        "\n"
        "def build_catalog(repo_root):\n"
        "    service = build_activation_aware_doctrine_service(repo_root)\n"
        "    inner_repo = service._inner.agent_profiles\n"
        "    return inner_repo\n",
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [8], (
        "Anti-mutant test failed to detect a planted ._inner reach-around on a "
        f"doctrine-service-typed variable; got {hits!r}. The gate does not bite "
        "-- investigate the taint heuristic before trusting the green main gate."
    )


def test_planted_unrelated_inner_attribute_is_not_detected(tmp_path: Path) -> None:
    """A planted, unrelated ``._inner`` attribute must NOT be flagged.

    Mirrors the real ``auth/transport.py``/``events/decision_log.py`` shape:
    a scratch class with its own, wholly unrelated ``._inner`` wrapper
    attribute. Proves the gate's scoping is neither too broad (this test)
    nor too narrow (the sibling true-positive test above) -- both
    assertions required by the WP04 risk mitigation.
    """
    planted = tmp_path / "planted_unrelated_inner.py"
    planted.write_text(
        "class ScratchWrapper:\n"
        "    def __init__(self, inner):\n"
        "        self._inner = inner\n"
        "\n"
        "    def call(self):\n"
        "        return self._inner.request()\n",
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [], (
        f"Gate falsely flagged an unrelated ._inner attribute access: {hits!r}. "
        "The taint heuristic is too broad."
    )


def test_planted_inline_construction_reacharound_is_detected(tmp_path: Path) -> None:
    """An inline (no intermediate variable) construction + ``._inner`` chain
    is also caught -- covers the module-qualified-call resolution tier, not
    just the assigned-variable tier exercised above.
    """
    planted = tmp_path / "planted_inline_reacharound.py"
    planted.write_text(
        "import specify_cli.doctrine_service_factory as dsf\n"
        "\n"
        "\n"
        "def peek(repo_root):\n"
        "    return dsf.build_activation_aware_doctrine_service(repo_root)._inner.agent_profiles\n",
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [5]


def test_annotated_assign_reacharound_is_flagged(tmp_path: Path) -> None:
    """A2 widening: ``service: DoctrineService = <ctor>(...)`` still taints.

    ``ast.AnnAssign`` is the *default* spelling in a mypy-clean codebase; the
    predecessor's ``_tainted_names`` only recognised bare ``ast.Assign``, so
    this exact shape evaded detection. Injected at function-local scope
    (NFR-003).
    """
    planted = tmp_path / "annotated_reacharound.py"
    planted.write_text(
        "from charter.resolver import DoctrineService\n"
        "\n"
        "\n"
        "def build(inner):\n"
        "    service: DoctrineService = DoctrineService(inner, pack_context=None)\n"
        "    return service._inner.tactics\n",
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [6], hits


def test_walrus_reacharound_is_flagged(tmp_path: Path) -> None:
    """A2 widening: a walrus-bound (``:=``) construction still taints.

    ``ast.NamedExpr`` was another shape the predecessor's ``ast.Assign``-only
    check could not see. Injected at function-local scope (NFR-003).
    """
    planted = tmp_path / "walrus_reacharound.py"
    planted.write_text(
        "from charter.resolver import DoctrineService\n"
        "\n"
        "\n"
        "def build(inner):\n"
        "    if (service := DoctrineService(inner, pack_context=None)) is not None:\n"
        "        return service._inner.procedures\n"
        "    return None\n",
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [6], hits


def test_tuple_unpack_reacharound_is_flagged(tmp_path: Path) -> None:
    """A2 widening: a tuple-unpack target of ``ast.Assign`` still taints.

    ``service, ready = DoctrineService(...), True`` pairs the construction
    call element-wise against its tuple target; the predecessor's
    single-``ast.Name``-target check missed this shape entirely. Injected at
    function-local scope (NFR-003).
    """
    planted = tmp_path / "tuple_unpack_reacharound.py"
    planted.write_text(
        "from charter.resolver import DoctrineService\n"
        "\n"
        "\n"
        "def build(inner):\n"
        "    service, ready = DoctrineService(inner, pack_context=None), True\n"
        "    return service._inner.glossary_packs if ready else None\n",
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [6], hits


def test_injected_from_package_import_module_is_flagged(tmp_path: Path) -> None:
    """A3 widening: ``from charter import resolver`` then
    ``resolver.DoctrineService(...)`` still taints.

    The predecessor's module-qualified branch resolved ONLY
    ``module_aliases`` (``import module as alias``), never ``from_imports``
    (``from pkg import sub``). Reusing the shared ``_lookup_module`` primitive
    closes both. Injected at function-local scope (NFR-003).
    """
    planted = tmp_path / "frompkg_reacharound.py"
    planted.write_text(
        "def build(inner):\n"
        "    from charter import resolver\n"
        "\n"
        "    service = resolver.DoctrineService(inner, pack_context=None)\n"
        "    return service._inner.styleguides\n",
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [5], hits


def test_getattr_string_reach_around_is_flagged(tmp_path: Path) -> None:
    """A4 widening: ``getattr(service, "_inner")`` reaches the same attribute.

    A gate that only pattern-matches ``ast.Attribute`` with ``attr ==
    "_inner"`` is structurally blind to this one-line reach-around reopening.
    Injected at function-local scope (NFR-003).
    """
    planted = tmp_path / "getattr_reacharound.py"
    planted.write_text(
        "from specify_cli.doctrine_service_factory import (\n"
        "    build_activation_aware_doctrine_service,\n"
        ")\n"
        "\n"
        "\n"
        "def build_catalog(repo_root):\n"
        "    service = build_activation_aware_doctrine_service(repo_root)\n"
        '    return getattr(service, "_inner").agent_profiles\n',
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [8], hits


def test_dunder_getattribute_reach_around_is_flagged(tmp_path: Path) -> None:
    """A4 widening: ``object.__getattribute__(service, "_inner")`` also reds."""
    planted = tmp_path / "dunder_getattribute_reacharound.py"
    planted.write_text(
        "from specify_cli.doctrine_service_factory import (\n"
        "    build_activation_aware_doctrine_service,\n"
        ")\n"
        "\n"
        "\n"
        "def build_catalog(repo_root):\n"
        "    service = build_activation_aware_doctrine_service(repo_root)\n"
        '    return object.__getattribute__(service, "_inner").tactics\n',
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [8], hits


def test_dict_subscript_reach_around_is_flagged(tmp_path: Path) -> None:
    """A4 widening: ``service.__dict__["_inner"]`` also reopens the reach-around."""
    planted = tmp_path / "dict_subscript_reacharound.py"
    planted.write_text(
        "from specify_cli.doctrine_service_factory import (\n"
        "    build_activation_aware_doctrine_service,\n"
        ")\n"
        "\n"
        "\n"
        "def build_catalog(repo_root):\n"
        "    service = build_activation_aware_doctrine_service(repo_root)\n"
        '    return service.__dict__["_inner"].mission_step_contracts\n',
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [8], hits


def test_getattr_on_untainted_receiver_is_not_flagged(tmp_path: Path) -> None:
    """True negative: ``getattr(x, "_inner")`` on an unrelated object is clean.

    Mirrors ``test_planted_unrelated_inner_attribute_is_not_detected`` for the
    A4 getattr spelling specifically -- the widening must not become
    overbroad.
    """
    planted = tmp_path / "getattr_unrelated.py"
    planted.write_text(
        "class ScratchWrapper:\n"
        "    def __init__(self, inner):\n"
        "        self._inner = inner\n"
        "\n"
        "    def call(self):\n"
        '        return getattr(self, "_inner").request()\n',
        encoding="utf-8",
    )

    hits = _find_inner_reacharounds(planted)
    assert hits == [], hits
