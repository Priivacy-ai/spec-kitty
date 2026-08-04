"""Gate 1 (FR-001/FR-007, WP09): zero raw ``AgentProfileRepository``
construction outside the charter sole door.

Mission ``charter-sole-door-bypass-closure-01KZ3WAA``, WP09 / T037. First of the
three mission-wide durability gates this work package ships; Gate 4 lives in
``test_charter_sole_door_hardcoded_paths.py`` (WP06) and Gate 5 in
``test_charter_sole_door_inner_reacharound.py`` (WP04).

What it proves
--------------
NFR-001 requires that every ``AgentProfileRepository(`` call site in ``src/``
resolve its **bound qualname** to the originating module, and that zero of them
resolve to ``doctrine.agent_profiles.repository.AgentProfileRepository`` outside
the sole door (``src/charter/resolver.py``), the one unified builder
(``src/charter/doctrine_service_builder.py``, FR-008), and the named,
composite-key-anchored exclusions below.

**Why a text grep is not acceptable here** (NFR-001, verbatim: "explicitly NOT a
text-only grep"): the class is re-exported through several facades, so the same
class is spelled ``charter.profiles.AgentProfileRepository`` in
``tool_surface/profiles/projection.py`` and
``doctrine.agent_profiles.AgentProfileRepository`` in
``charter/profile_resolution.py`` — both resolve to the single originating
``doctrine.agent_profiles.repository.AgentProfileRepository``. Conversely, a
future ``AgentProfileRepository`` defined in some unrelated module would share
the literal substring while being an entirely different class. This gate
resolves each call site's bound name to a real ``(module, name)`` pair by AST
import analysis — module-level **and** function-local **and** nested
``try``/``except`` imports, plus ``as``-aliases, module-qualified calls and
module-level re-bindings — and then asks Python itself where the object came
from via ``__module__``/``__qualname__``. A rename, a new facade re-export or an
alias therefore cannot slip past it, and a same-named unrelated class cannot
false-positive into it.

Structural exemptions (directory/file keyed, never line keyed)
---------------------------------------------------------------
* ``src/doctrine/`` — the doctrine layer *owns* this class and the raw
  ``doctrine.service.DoctrineService`` that composes it
  (``doctrine/service.py``'s ``DoctrineService.agent_profiles`` cache). That
  construction is the thing the sole door wraps, not a bypass of it — the same
  shape as Gate 5's ``src/charter/`` exemption.
* ``src/charter/resolver.py`` — the sole door itself (NFR-001).
* ``src/charter/doctrine_service_builder.py`` — the ONE unified builder
  (FR-008/NFR-001).

Named exclusions are **composite-key anchored, never whole-file**
------------------------------------------------------------------
Each entry below is a :class:`ContentDescriptor` resolving to exactly one live
site, keyed on ``(rel_path, enclosing_qualname, token_line)``. Sanctioning one
construction in a module does NOT waive the module: a genuinely new bypass added
to ``registry.py`` still reds because its qualname/token differ — proven by
:func:`test_excluding_one_site_does_not_waive_its_module`.

**Why the key is ``(file, qualname, token)`` rather than the
``(file, qualname, line)`` spec.md NFR-001 phrases.** A raw line number is
banned as an authoritative comparand anywhere under ``tests/architectural/`` by
the standing gate ``test_ratchet_positional_anchor_ban.py`` (DIR-041 / #2077,
mission ``content-address-ratchet-allowlists-01KX8M4D``); an allow-list seeded
with ``(rel, N)`` rows reds it. The canonical repo primitive is
``composite_key``'s drift-proof ``(qualname, token_line)`` pair, with the line
kept only as a non-authoritative locator. This is strictly stronger, not a
weakening: this mission *empirically* demonstrated the drift — every line number
spec.md pinned had already moved by the time this gate was written
(``registry.py`` 48→73, ``projection.py`` 84→115, ``profile_resolution.py``
81→95, and Gate 2's four ``_doctrine_collect.py`` sites 193/283/420/828 →
209/314/468/920). Using the canonical primitive is also the repo rule (never
improvise a second key-builder).

The four named exclusions, and their provenance
-------------------------------------------------
1. ``invocation/registry.py`` (``ProfileRegistry.__init__``) — C-006: builds
   against ``.kittify/profiles``, a local-override directory outside the
   doctrine activation model, explicitly out of scope by operator decision.
   **Pre-sanctioned** by spec.md FR-001/C-006.
2. ``cli/commands/profiles_cmd.py`` (``_profile_catalog``) — C-006, same
   ``.kittify/profiles`` rationale. **Pre-sanctioned** by spec.md FR-001/C-006.
3. ``charter/profile_resolution.py`` (``_default_agent_profile_repository``) —
   FR-001's *confirmed bootstrap carve-out*: a zero-argument, module-level
   cached built-in-only repository with no ``repo_root`` from which to build a
   factory. spec.md FR-001 directs, verbatim, "document it as a genuine C-002
   bootstrap case, do not attempt to route it through the factory".
   **Pre-sanctioned.**
4. ``tool_surface/profiles/projection.py`` (``default_profile_repository``) —
   **NOT pre-sanctioned; added by WP09 as an escalated C-002 finding, and a
   tracked follow-up rather than a permanent carve-out.** WP02 named this site
   as an in-scope FR-001 migration target and then could not close it: the
   factory's ``agent_profile_repository`` accessor is built from a raw service
   whose project-overlay directory comes from
   ``charter._doctrine_paths.resolve_project_root``'s three fixed candidates
   (``.kittify/doctrine``, ``src/doctrine``, ``doctrine``), none of which is
   ``.kittify/agent_profiles``, and ``build_activation_aware_doctrine_service``
   exposes no parameter to retarget it. Both WP02's implementer and its reviewer
   independently forced the naive migration and reproduced three real test
   breakages (project-overlay profiles silently dropped). Closing it correctly
   needs a builder-level change on WP01's already-approved surface — new scope,
   outside WP09's write scope. That function's own docstring carries the full
   evidence trail. **This entry must be DELETED, not renewed, once the builder
   gains a project-overlay override.**

No other exclusion may be added without the same standard of written
justification (C-002: no shrink-only escape hatch, zero exceptions).
"""

from __future__ import annotations

import ast
import functools
import importlib
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.architectural._ratchet_keys import (
    CompositeKey,
    ContentDescriptor,
    composite_key,
    resolve_descriptor,
)

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"

#: The originating qualname every sanctioned and unsanctioned spelling of the
#: agent-profile repository collapses to. Named verbatim by spec.md NFR-001.
AGENT_PROFILE_REPOSITORY_QUALNAME = (
    "doctrine.agent_profiles.repository.AgentProfileRepository"
)

#: Gate 1 watches exactly one canonical class.
AGENT_PROFILE_TARGETS = frozenset({AGENT_PROFILE_REPOSITORY_QUALNAME})

#: Simple names a call site may spell to reach the class. Only calls whose
#: callee resolves to one of these *original* names (pre-``as``-alias) get a
#: canonical lookup, keeping the scan's dynamic-import surface tiny.
AGENT_PROFILE_CANDIDATE_NAMES = frozenset({"AgentProfileRepository"})

#: The sole door (NFR-001).
SOLE_DOOR_REL_PATH = "src/charter/resolver.py"
#: The ONE unified builder (FR-008).
UNIFIED_BUILDER_REL_PATH = "src/charter/doctrine_service_builder.py"
#: The doctrine layer owns the wrapped subject; see module docstring.
DOCTRINE_LAYER_PREFIX = "src/doctrine/"

#: Files entitled to construct a watched doctrine class natively. Shared with
#: Gate 2, which polices the sibling ``doctrine.service.DoctrineService`` class
#: against the same two authorities.
SOLE_DOOR_EXEMPT_FILES = frozenset({SOLE_DOOR_REL_PATH, UNIFIED_BUILDER_REL_PATH})
SOLE_DOOR_EXEMPT_PREFIXES = (DOCTRINE_LAYER_PREFIX,)

_MIN_RATIONALE_CHARS = 80


# =========================================================================== #
# Reusable qualname-resolution machinery.
#
# Gate 2 (``test_charter_sole_door_doctrine_service.py``) imports these
# primitives instead of forking a second copy. They live in this module because
# WP09's ``owned_files`` are exactly the three gate files — a shared
# ``_charter_sole_door_qualnames.py`` helper would be a fourth file outside this
# work package's declared write scope. Sibling gate modules importing each
# other's primitives is established practice here (see
# ``test_coord_read_residuals_closeout.py`` importing from
# ``test_gate_read_literal_ban.py``).
# =========================================================================== #


@dataclass(frozen=True)
class ConstructionSite:
    """One resolved construction call of a watched class.

    ``rel_path``/``qualname``/``token`` form the authoritative composite key.
    ``lineno`` is a **non-authoritative** locator carried for jump-to
    diagnostics only — nothing in this module or Gate 2 compares, counts, or
    keys on it.
    """

    rel_path: str
    qualname: str
    token: str
    lineno: int
    canonical: str

    @property
    def key(self) -> CompositeKey:
        """The authoritative ``(rel_path, qualname, token)`` composite key."""
        return (self.rel_path, self.qualname, self.token)

    def describe(self) -> str:
        return f"{self.rel_path}:{self.lineno} ({self.qualname}) -> {self.canonical}"


@dataclass(frozen=True)
class ScanResult:
    """Resolved construction sites plus the sites resolution could not decide."""

    sites: list[ConstructionSite]
    unresolved: list[ConstructionSite]


@dataclass
class _Bindings:
    """Names bound in one lexical scope to an importable ``(module, name)``."""

    #: local name -> (module, original_name)
    from_imports: dict[str, tuple[str, str]] = field(default_factory=dict)
    #: local alias -> real dotted module path
    module_aliases: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class _Origin:
    """Where a callee name came from.

    ``local`` marks a class defined in the scanned file itself, whose canonical
    qualname is derived statically (``<module_of_file>.<name>``) rather than by
    import — so the scanner works on scratch modules that are not importable.
    """

    module: str
    name: str
    local: bool


def iter_source_files(src_root: Path) -> list[Path]:
    """Every ``*.py`` under *src_root*, ``__pycache__`` excluded.

    Derived wholesale from ``rglob`` — no hardcoded package list that a newly
    added subpackage could silently fall outside of.
    """
    return [p for p in sorted(src_root.rglob("*.py")) if "__pycache__" not in p.parts]


def rel_to_repo(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def module_name_for(rel_path: str) -> str:
    """Dotted module name for a repo-relative ``src/`` path."""
    stem = rel_path.removeprefix("src/").removesuffix(".py").removesuffix("/__init__")
    return stem.replace("/", ".")


@functools.cache
def resolve_canonical(module: str, name: str) -> str | None:
    """Return ``"<obj.__module__>.<obj.__qualname__>"`` for ``module.name``.

    This is the qualname resolution NFR-001 demands: it asks the interpreter
    where the object actually came from, so any depth of facade re-export
    (``charter.profiles`` -> ``doctrine.agent_profiles`` ->
    ``doctrine.agent_profiles.repository``) collapses to one canonical answer.

    Returns ``None`` when the module or attribute does not exist. Callers must
    treat ``None`` as an unresolved blind spot, never as "clean" — see
    :func:`test_no_unresolved_agent_profile_candidates`.
    """
    try:
        mod = importlib.import_module(module)
    except Exception:  # noqa: BLE001 - any import failure means "unresolved"
        return None
    obj = getattr(mod, name, None)
    obj_module = getattr(obj, "__module__", None)
    obj_qualname = getattr(obj, "__qualname__", None)
    if not isinstance(obj_module, str) or not isinstance(obj_qualname, str):
        return None
    return f"{obj_module}.{obj_qualname}"


def _scope_nodes(tree: ast.Module) -> list[ast.AST]:
    scopes: list[ast.AST] = [tree]
    scopes.extend(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    return scopes


def _own_scope_statements(scope: ast.AST) -> list[ast.AST]:
    """Nodes lexically inside *scope*, not descending into nested scopes.

    A ``try:``/``if:``/``with:`` block inside a function still belongs to that
    function's scope — exactly the shape the real violations use (``org_layer.py``
    imports the wrapper inside a ``try``/``except ImportError``). Only a nested
    ``def``/``class`` starts a new scope.
    """
    out: list[ast.AST] = []
    stack: list[ast.AST] = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        out.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return out


def _bindings_for_scope(scope: ast.AST) -> _Bindings:
    bindings = _Bindings()
    for node in _own_scope_statements(scope):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                bindings.from_imports[alias.asname or alias.name] = (
                    node.module,
                    alias.name,
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bindings.module_aliases[alias.asname or alias.name] = alias.name
    return bindings


def parent_map(tree: ast.Module) -> dict[int, ast.AST]:
    parents: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def enclosing_scope(
    parents: dict[int, ast.AST], node: ast.AST, tree: ast.Module
) -> ast.AST:
    """The innermost ``def``/``class`` containing *node*, else the module."""
    cur: ast.AST | None = node
    while cur is not None:
        cur = parents.get(id(cur))
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return cur
    return tree


def _scope_chain(
    parents: dict[int, ast.AST], node: ast.AST, tree: ast.Module
) -> list[ast.AST]:
    """Scopes containing *node*, innermost first, module scope last."""
    chain: list[ast.AST] = []
    cur: ast.AST | None = node
    while cur is not None:
        cur = parents.get(id(cur))
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            chain.append(cur)
    chain.append(tree)
    return chain


def _dotted_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _lookup_module(dotted: str, chain: list[_Bindings]) -> str:
    """Resolve an attribute-chain base to a real dotted module path."""
    for bindings in chain:
        alias = bindings.module_aliases.get(dotted)
        if alias is not None:
            return alias
        # ``from pkg import sub`` then ``sub.Cls(...)``
        from_hit = bindings.from_imports.get(dotted)
        if from_hit is not None:
            return f"{from_hit[0]}.{from_hit[1]}"
    head, _, tail = dotted.partition(".")
    if tail:
        for bindings in chain:
            alias = bindings.module_aliases.get(head)
            if alias is not None:
                return f"{alias}.{tail}"
    return dotted


def _module_level_rebinds(
    tree: ast.Module, candidate_names: frozenset[str]
) -> dict[str, tuple[str, str]]:
    """``Alias = AgentProfileRepository`` style module-level re-bindings.

    Closes the "rename it into a module constant, then call the constant"
    evasion vector — exercised by
    :func:`test_detector_follows_module_level_rebinding`.
    """
    module_bindings = _bindings_for_scope(tree)
    rebinds: dict[str, tuple[str, str]] = {}
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        origin = module_bindings.from_imports.get(_dotted_name(node.value) or "")
        if origin is not None and origin[1] in candidate_names:
            rebinds[target.id] = origin
    return rebinds


def _locally_defined_names(tree: ast.Module) -> frozenset[str]:
    return frozenset(
        node.name
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    )


def callee_simple_name(call: ast.Call) -> str | None:
    """The trailing identifier of ``call``'s callee, ignoring any dotted base."""
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def _resolve_callee(
    call: ast.Call,
    chain: list[_Bindings],
    rebinds: dict[str, tuple[str, str]],
    self_module: str,
    locally_defined: frozenset[str],
) -> _Origin | None:
    """Resolve ``call``'s callee to an importable or file-local origin."""
    func = call.func
    if isinstance(func, ast.Name):
        for bindings in chain:
            hit = bindings.from_imports.get(func.id)
            if hit is not None:
                return _Origin(hit[0], hit[1], local=False)
        rebound = rebinds.get(func.id)
        if rebound is not None:
            return _Origin(rebound[0], rebound[1], local=False)
        if func.id in locally_defined:
            return _Origin(self_module, func.id, local=True)
        return None
    if isinstance(func, ast.Attribute):
        base = _dotted_name(func.value)
        if base is None:
            return None
        return _Origin(_lookup_module(base, chain), func.attr, local=False)
    return None


def _canonical_for(origin: _Origin) -> str | None:
    """Canonical qualname for *origin* — statically for file-local classes."""
    if origin.local:
        return f"{origin.module}.{origin.name}"
    return resolve_canonical(origin.module, origin.name)


@dataclass(frozen=True)
class FileScan:
    """A parsed file plus everything needed to resolve calls inside it.

    ``matches`` pairs each flagged :class:`ast.Call` node with its resolved
    site. Consumers that need to reason about a call's *surroundings* (Gate 2's
    wrap-flow analysis) must key off these node objects — never off
    ``(lineno, qualname)``, which is ambiguous when two watched constructions
    share a line (``Wrapper(Raw(...))`` in ``charter/compiler.py``).
    """

    rel_path: str
    source: str
    tree: ast.Module
    parents: dict[int, ast.AST]
    matches: tuple[tuple[ast.Call, ConstructionSite], ...]
    result: ScanResult


def scan_file_constructions(
    path: Path,
    rel_path: str,
    *,
    candidate_names: frozenset[str],
    target_qualnames: frozenset[str],
) -> FileScan | None:
    """Resolve every construction call of any *target_qualnames* in one file.

    Passing more than one target lets a caller classify sibling classes that
    share a source spelling in a **single parse**, so the resulting node
    identities are comparable (Gate 2 needs exactly that for
    ``doctrine.service.DoctrineService`` vs ``charter.resolver.DoctrineService``).

    Returns ``None`` only when the file cannot be parsed at all.
    """
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return None

    parents = parent_map(tree)
    bindings_by_scope = {
        id(scope): _bindings_for_scope(scope) for scope in _scope_nodes(tree)
    }
    rebinds = _module_level_rebinds(tree, candidate_names)
    self_module = module_name_for(rel_path)
    locally_defined = _locally_defined_names(tree)

    matches: list[tuple[ast.Call, ConstructionSite]] = []
    unresolved: list[ConstructionSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        simple_name = callee_simple_name(node)
        if simple_name is None:
            continue
        chain = [
            bindings_by_scope[id(scope)]
            for scope in _scope_chain(parents, node, tree)
            if id(scope) in bindings_by_scope
        ]
        origin = _resolve_callee(node, chain, rebinds, self_module, locally_defined)
        # Only names that could possibly be a watched class are worth a
        # canonical lookup. The check is on the *original* imported name so an
        # ``as``-alias cannot dodge it (every live site aliases the import).
        if (origin.name if origin else simple_name) not in candidate_names:
            continue
        qualname, token = composite_key(source, node.lineno)
        if origin is None:
            unresolved.append(
                ConstructionSite(rel_path, qualname, token, node.lineno, "<unbound>")
            )
            continue
        canonical = _canonical_for(origin)
        if canonical is None:
            unresolved.append(
                ConstructionSite(
                    rel_path,
                    qualname,
                    token,
                    node.lineno,
                    f"<unimportable {origin.module}.{origin.name}>",
                )
            )
            continue
        if canonical in target_qualnames:
            matches.append(
                (node, ConstructionSite(rel_path, qualname, token, node.lineno, canonical))
            )
    return FileScan(
        rel_path,
        source,
        tree,
        parents,
        tuple(matches),
        ScanResult([site for _, site in matches], unresolved),
    )


def scan_constructions(
    src_root: Path, *, candidate_names: frozenset[str], target_qualnames: frozenset[str]
) -> ScanResult:
    """Whole-tree census of *target_qualnames* constructions under *src_root*.

    Returns **every** site, exemptions included, so a caller can first prove the
    scanner really sees the sanctioned ones (anti-vacuity) and only then filter.
    """
    sites: list[ConstructionSite] = []
    unresolved: list[ConstructionSite] = []
    for path in iter_source_files(src_root):
        scan = scan_file_constructions(
            path,
            rel_to_repo(path),
            candidate_names=candidate_names,
            target_qualnames=target_qualnames,
        )
        if scan is None:
            continue
        sites.extend(scan.result.sites)
        unresolved.extend(scan.result.unresolved)
    return ScanResult(sites, unresolved)


def structurally_exempt(rel_path: str) -> bool:
    """True for the sole door, the unified builder, and the doctrine layer."""
    return rel_path in SOLE_DOOR_EXEMPT_FILES or rel_path.startswith(
        SOLE_DOOR_EXEMPT_PREFIXES
    )


def resolve_exclusion_keys(
    descriptors: tuple[ContentDescriptor, ...],
) -> dict[CompositeKey, ContentDescriptor]:
    """Resolve each descriptor against the live tree to its composite key.

    :func:`resolve_descriptor` RAISES unless a descriptor matches **exactly
    one** live site, so a stale entry (site closed, moved, or edited) fails
    loudly instead of silently widening the exclusion set. That is the staleness
    half of the twin-guard.
    """
    return {
        resolve_descriptor(
            (REPO_ROOT / descriptor.rel_path).read_text(encoding="utf-8"), descriptor
        ): descriptor
        for descriptor in descriptors
    }


def assert_rationales_are_substantive(descriptors: tuple[ContentDescriptor, ...]) -> None:
    """C-002: an exclusion without a written justification is a silent allowlist."""
    for descriptor in descriptors:
        assert len(descriptor.rationale.strip()) > _MIN_RATIONALE_CHARS, descriptor


# =========================================================================== #
# Gate 1 policy
# =========================================================================== #

#: Named, individually-justified exclusions — composite-key anchored via a
#: content descriptor, never a whole file and never a line number. Read the
#: module docstring's "four named exclusions" section before touching this.
AGENT_PROFILE_EXCLUSIONS: tuple[ContentDescriptor, ...] = (
    ContentDescriptor(
        rel_path="src/specify_cli/invocation/registry.py",
        qualname="ProfileRegistry.__init__",
        token_substring="AgentProfileRepository (",
        occurrence=None,
        rationale=(
            "C-006: constructs against .kittify/profiles, a local-override "
            "directory outside the doctrine activation model; explicitly out of "
            "scope by operator decision (spec.md FR-001/C-006). Do not route it "
            "through the factory and do not fold its rework into this mission."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/profiles_cmd.py",
        qualname="_profile_catalog",
        token_substring="AgentProfileRepository (",
        occurrence=None,
        rationale=(
            "C-006: the same .kittify/profiles local-override rationale as "
            "invocation/registry.py; explicitly out of scope by operator "
            "decision (spec.md FR-001/C-006), slated for separate future rework."
        ),
    ),
    ContentDescriptor(
        rel_path="src/charter/profile_resolution.py",
        qualname="_default_agent_profile_repository",
        token_substring="AgentProfileRepository ( )",
        occurrence=None,
        rationale=(
            "FR-001 confirmed bootstrap carve-out: a zero-argument, "
            "module-level cached built-in-only repository with no repo_root "
            "from which to build a factory. spec.md FR-001 directs documenting "
            "it as a genuine C-002 bootstrap case rather than routing it "
            "through the factory."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/tool_surface/profiles/projection.py",
        qualname="default_profile_repository",
        token_substring="AgentProfileRepository ( project_dir = project_dir )",
        occurrence=None,
        rationale=(
            "ESCALATED C-002 FINDING, TRACKED FOLLOW-UP AT #3176 - NOT A "
            "PERMANENT CARVE-OUT. The .kittify/agent_profiles project-overlay "
            "directory is unreachable through the unified builder: the factory's inner "
            "service derives its project directory from "
            "charter._doctrine_paths.resolve_project_root's three fixed "
            "candidates (.kittify/doctrine, src/doctrine, doctrine), and "
            "build_activation_aware_doctrine_service exposes no parameter to "
            "retarget it. WP02's implementer and reviewer independently forced "
            "the naive migration and reproduced three real test breakages "
            "(project-overlay profiles silently dropped). Closing it needs a "
            "builder-level change on WP01's already-approved surface, outside "
            "WP09's write scope. DELETE this entry - do not renew it - once the "
            "builder gains a project-overlay override."
        ),
    ),
)


@functools.cache
def agent_profile_census() -> ScanResult:
    """Every resolved ``AgentProfileRepository`` construction under ``src/``.

    Memoised for the test session: the scan is a pure function of an unchanging
    working tree, and several tests below need it. Nothing mutates the returned
    lists.
    """
    return scan_constructions(
        SRC_ROOT,
        candidate_names=AGENT_PROFILE_CANDIDATE_NAMES,
        target_qualnames=AGENT_PROFILE_TARGETS,
    )


def check_agent_profile_gate(sites: list[ConstructionSite]) -> list[str]:
    """Return violation strings for *sites* — zero-tolerance, no wildcards."""
    excluded = resolve_exclusion_keys(AGENT_PROFILE_EXCLUSIONS)
    return [
        f"{site.describe()} constructs the raw agent-profile repository outside "
        "the charter sole door (FR-001/NFR-001) — obtain it from "
        "charter.resolver.DoctrineService.agent_profile_repository instead"
        for site in sites
        if not structurally_exempt(site.rel_path) and site.key not in excluded
    ]


# =========================================================================== #
# Anti-vacuity: the scan really walks the tree and really resolves facades
# =========================================================================== #


def test_scan_reaches_a_broad_slice_of_src() -> None:
    """The ``rglob`` walk must not silently narrow to a subtree."""
    scanned = {rel_to_repo(p) for p in iter_source_files(SRC_ROOT)}
    representative = {
        "src/charter/resolver.py",
        "src/charter/profile_resolution.py",
        "src/doctrine/service.py",
        "src/specify_cli/invocation/registry.py",
        "src/specify_cli/cli/commands/profiles_cmd.py",
        "src/specify_cli/tool_surface/profiles/projection.py",
    }
    assert not representative - scanned, sorted(representative - scanned)
    assert len(scanned) > 200


def test_census_is_non_empty_and_includes_the_doctrine_owner() -> None:
    """The resolver must actually find the known live constructions.

    A gate whose scanner silently resolves nothing would pass its
    zero-violation assertion vacuously. This pins the opposite: the census finds
    sites, and specifically finds ``doctrine/service.py``'s own construction
    (the structurally exempt owner), proving the resolution path works end to
    end rather than short-circuiting.
    """
    census = agent_profile_census()
    assert len(census.sites) >= 5, [s.describe() for s in census.sites]
    assert any(s.rel_path == "src/doctrine/service.py" for s in census.sites), [
        s.describe() for s in census.sites
    ]
    assert all(s.canonical == AGENT_PROFILE_REPOSITORY_QUALNAME for s in census.sites)


def test_facade_spellings_collapse_to_one_canonical_origin() -> None:
    """``charter.profiles`` and ``doctrine.agent_profiles`` are the same class.

    The concrete proof that this gate resolves *qualnames* and not text: two
    different import spellings used by two real call sites both canonicalise to
    the single originating module NFR-001 names.
    """
    for module in ("charter.profiles", "doctrine.agent_profiles"):
        assert (
            resolve_canonical(module, "AgentProfileRepository")
            == AGENT_PROFILE_REPOSITORY_QUALNAME
        ), module


def test_no_unresolved_agent_profile_candidates() -> None:
    """No ``AgentProfileRepository(``-shaped call may go unresolved.

    An unresolved candidate is a blind spot, not a pass: the gate could not
    decide whether the site is the watched class. Treating those as clean is
    exactly how a "zero violations" gate goes vacuous, so they fail here.
    """
    unresolved = agent_profile_census().unresolved
    assert unresolved == [], [s.describe() for s in unresolved]


def test_every_exclusion_resolves_to_exactly_one_live_site() -> None:
    """Staleness twin-guard: no exclusion may be a dangling entry."""
    resolved = resolve_exclusion_keys(AGENT_PROFILE_EXCLUSIONS)
    assert len(resolved) == len(AGENT_PROFILE_EXCLUSIONS)


def test_every_exclusion_carries_a_written_rationale() -> None:
    """C-002: an exclusion without a justification is a silent allowlist entry."""
    assert_rationales_are_substantive(AGENT_PROFILE_EXCLUSIONS)


def test_exclusions_match_real_census_sites() -> None:
    """Each exclusion must correspond to a site the census actually flagged.

    Prevents an exclusion that quietly stops mapping to a real construction
    (e.g. the site was migrated after all) from lingering as dead weight.
    """
    census_keys = {site.key for site in agent_profile_census().sites}
    for key, descriptor in resolve_exclusion_keys(AGENT_PROFILE_EXCLUSIONS).items():
        assert key in census_keys, f"{descriptor.rel_path} ({descriptor.qualname})"


# =========================================================================== #
# The gate
# =========================================================================== #


def test_no_raw_agent_profile_repository_construction_outside_the_sole_door() -> None:
    """Zero-tolerance (C-002): nothing beyond the four named exclusions."""
    violations = check_agent_profile_gate(agent_profile_census().sites)
    assert violations == [], "\n".join(violations)


# =========================================================================== #
# NFR-003 self-mutation proofs — function-local and nested scope, never
# module-level-only (the WP10 lesson from doctrine-charter-split-unification).
# =========================================================================== #


def scratch_scan(
    tmp_path: Path,
    rel_name: str,
    source: str,
    *,
    candidate_names: frozenset[str],
    target_qualnames: frozenset[str],
) -> FileScan:
    """Write *source* to a scratch module and scan it. Never touches ``src/``."""
    module = tmp_path / Path(rel_name).name
    module.write_text(source, encoding="utf-8")
    scan = scan_file_constructions(
        module,
        rel_name,
        candidate_names=candidate_names,
        target_qualnames=target_qualnames,
    )
    assert scan is not None, f"scratch module {rel_name} failed to parse"
    return scan


def _agent_profile_scratch(tmp_path: Path, rel_name: str, source: str) -> ScanResult:
    return scratch_scan(
        tmp_path,
        rel_name,
        source,
        candidate_names=AGENT_PROFILE_CANDIDATE_NAMES,
        target_qualnames=AGENT_PROFILE_TARGETS,
    ).result


def test_injected_function_local_construction_is_flagged(tmp_path: Path) -> None:
    """A reintroduced bypass with a **function-local** import is caught.

    This is the real violation shape: every live site in this codebase imports
    the class inside a function body, not at module level. A gate that only
    inspected module-level imports would pass this vacuously (NFR-003).
    """
    result = _agent_profile_scratch(
        tmp_path,
        "regressed_local.py",
        "def build(project_dir):\n"
        "    from charter.profiles import AgentProfileRepository\n"
        "\n"
        "    return AgentProfileRepository(project_dir=project_dir)\n",
    )
    assert result.unresolved == [], [s.describe() for s in result.unresolved]
    assert len(result.sites) == 1, [s.describe() for s in result.sites]
    site = result.sites[0]
    assert site.qualname == "build"
    assert site.canonical == AGENT_PROFILE_REPOSITORY_QUALNAME
    violations = check_agent_profile_gate(result.sites)
    assert violations, "the gate must bite on a function-local reintroduction"
    assert "regressed_local.py" in violations[0]
    assert "build" in violations[0]


def test_injected_nested_try_except_construction_is_flagged(tmp_path: Path) -> None:
    """A bypass hidden in a nested ``try``/``except ImportError`` is caught.

    Mirrors the shape ``org_layer.py`` used before FR-002 closed it — an import
    nested two blocks deep inside a method, which a scope-blind scanner misses.
    """
    result = _agent_profile_scratch(
        tmp_path,
        "regressed_nested.py",
        "class Sneaky:\n"
        "    def load(self, project_dir):\n"
        "        try:\n"
        "            from doctrine.agent_profiles import AgentProfileRepository\n"
        "        except ImportError:\n"
        "            return None\n"
        "        if project_dir is not None:\n"
        "            return AgentProfileRepository(project_dir=project_dir)\n"
        "        return None\n",
    )
    assert len(result.sites) == 1, [s.describe() for s in result.sites]
    assert result.sites[0].qualname == "Sneaky.load"
    assert check_agent_profile_gate(result.sites)


def test_injected_closure_construction_resolves_via_the_enclosing_scope(
    tmp_path: Path,
) -> None:
    """A closure constructing with its *parent's* import is caught.

    Exercises the scope-chain walk specifically: the import is bound in the
    outer function, the construction happens in the nested one. Resolving only
    the innermost scope (or only the module scope) misses this; the gate must
    walk innermost -> outermost.
    """
    result = _agent_profile_scratch(
        tmp_path,
        "regressed_closure.py",
        "def outer(project_dir):\n"
        "    from charter.profiles import AgentProfileRepository\n"
        "\n"
        "    def inner():\n"
        "        return AgentProfileRepository(project_dir=project_dir)\n"
        "\n"
        "    return inner\n",
    )
    assert result.unresolved == [], [s.describe() for s in result.unresolved]
    assert len(result.sites) == 1, [s.describe() for s in result.sites]
    assert result.sites[0].qualname == "outer.inner"
    assert check_agent_profile_gate(result.sites)


def test_detector_follows_as_alias(tmp_path: Path) -> None:
    """An ``as``-aliased import cannot launder the construction past the gate."""
    result = _agent_profile_scratch(
        tmp_path,
        "regressed_alias.py",
        "def build():\n"
        "    from charter.profiles import AgentProfileRepository as _Repo\n"
        "\n"
        "    return _Repo()\n",
    )
    assert len(result.sites) == 1, [s.describe() for s in result.sites]
    assert check_agent_profile_gate(result.sites)


def test_detector_follows_module_qualified_call(tmp_path: Path) -> None:
    """``import charter.profiles as p`` then ``p.AgentProfileRepository()``."""
    result = _agent_profile_scratch(
        tmp_path,
        "regressed_modqual.py",
        "import charter.profiles as p\n"
        "\n"
        "\n"
        "def build():\n"
        "    return p.AgentProfileRepository()\n",
    )
    assert len(result.sites) == 1, [s.describe() for s in result.sites]
    assert check_agent_profile_gate(result.sites)


def test_detector_follows_module_level_rebinding(tmp_path: Path) -> None:
    """``_Repo = AgentProfileRepository`` then ``_Repo()`` still reds."""
    result = _agent_profile_scratch(
        tmp_path,
        "regressed_rebind.py",
        "from charter.profiles import AgentProfileRepository\n"
        "\n"
        "_Repo = AgentProfileRepository\n"
        "\n"
        "\n"
        "def build():\n"
        "    return _Repo()\n",
    )
    assert len(result.sites) == 1, [s.describe() for s in result.sites]
    assert check_agent_profile_gate(result.sites)


def test_detector_ignores_a_same_named_unrelated_class(tmp_path: Path) -> None:
    """A different class that merely shares the name must NOT be flagged.

    The true-negative half of the qualname requirement: a text grep for
    ``AgentProfileRepository(`` flags this; resolving the bound qualname does
    not, because the canonical origin differs.
    """
    result = _agent_profile_scratch(
        tmp_path,
        "unrelated_same_name.py",
        "class AgentProfileRepository:\n"
        "    def __init__(self, project_dir=None):\n"
        "        self.project_dir = project_dir\n"
        "\n"
        "\n"
        "def build():\n"
        "    return AgentProfileRepository()\n",
    )
    assert result.sites == [], [s.describe() for s in result.sites]
    assert result.unresolved == [], [s.describe() for s in result.unresolved]


def test_excluding_one_site_does_not_waive_its_module(tmp_path: Path) -> None:
    """Composite-key keying, proven: a NEW bypass in an excluded file still reds.

    Injects a second construction into a copy of ``projection.py`` — the file
    carrying the escalated ``default_profile_repository`` exclusion — inside a
    *different* function. The excluded site stays excluded; the new one is
    reported. A whole-file exclusion would have swallowed both.
    """
    original = (
        REPO_ROOT / "src/specify_cli/tool_surface/profiles/projection.py"
    ).read_text(encoding="utf-8")
    scratch = tmp_path / "projection_mutant.py"
    scratch.write_text(
        original
        + (
            "\n\n"
            "def sneaky_second_door(project_root):\n"
            "    return AgentProfileRepository(project_dir=project_root)\n"
        ),
        encoding="utf-8",
    )
    scan = scan_file_constructions(
        scratch,
        "src/specify_cli/tool_surface/profiles/projection.py",
        candidate_names=AGENT_PROFILE_CANDIDATE_NAMES,
        target_qualnames=AGENT_PROFILE_TARGETS,
    )
    assert scan is not None
    qualnames = {site.qualname for site in scan.result.sites}
    assert {"default_profile_repository", "sneaky_second_door"} <= qualnames, qualnames

    violations = check_agent_profile_gate(scan.result.sites)
    assert len(violations) == 1, violations
    assert "sneaky_second_door" in violations[0]
    assert "default_profile_repository" not in violations[0]


def test_gate_runs_under_fast_tier_budget() -> None:
    """The whole-tree scan stays well inside the 30 s fast-tier ceiling.

    Calls :func:`scan_constructions` directly rather than the memoised
    :func:`agent_profile_census` — timing a cache hit would be a vacuous
    measurement.
    """
    start = time.monotonic()
    scan_constructions(
        SRC_ROOT,
        candidate_names=AGENT_PROFILE_CANDIDATE_NAMES,
        target_qualnames=AGENT_PROFILE_TARGETS,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 30.0, f"agent-profile construction scan took {elapsed:.2f}s"
