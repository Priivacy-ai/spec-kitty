"""Falsity guards G1-G6 for the tracker-egress refusal Mission (#3108), plus G7 and G8.

These guards make the Mission's *preconditions* structural rather than test-dependent. Each
one states a property that, if a future change silently broke it, would reopen either `#3030`'s
P0 hosted-egress boundary or `#3108`'s local gap -- and would do so with the behavioural suite
still green.

How these guards are built, and why that shape is mandatory
--------------------------------------------------------------

**(a) Every guard is an analyzer callable, invoked twice; no source is ever edited.** The plan
forbids source edits during a verification run and requires mutations to be injected rather than
written to disk. For a guard whose *subject is the source tree* that rules out the obvious
approach. So each guard is a pure analyzer taking source text (or a root path) and returning a
``Findings`` object; its test invokes it once against the real tree (the **real run**, reporting
the real input count) and once against **synthetic mutated source held in this file as a string**
(the **mutant run**, reporting the killed-pin count). Nothing on disk is touched, and no test in
this file writes a file, monkeypatches a module, or shells out.

**(b) Every matcher resolves BOTH ``ast.Name`` and ``ast.Attribute`` func nodes -- this is the
measured blind spot, not a stylistic preference.** A sixth, ungated call site written
module-qualified::

    from specify_cli.tracker import egress_verdict as ev
    ev.tracker_egress_verdict(root, destination=ev.EgressDestination.LOCAL_SUBPROCESS)

was measured to **pass both G4 and G5** with G4's input count merely *rising*, because a matcher
inspecting only ``ast.Name`` func nodes never sees it. Both of the originally specified mutants
kept the ``ast.Name`` form, so a guard with this hole killed 2/2 and reported itself healthy.
*A guard that survives its own mutants while blind to its subject is worse than no guard*: it
converts an unexamined property into an examined one that is false. Hence
:func:`_callee_trailing_name`, used by every call matcher here, and hence the module-qualified
third mutant carried by G4, G5 and G8.

Relatedly: **matching is always AST-structural, never substring.** ``cli/commands/tracker.py``
mentions ``tracker_egress_verdict`` in two docstrings while holding zero imports and zero calls
of it. Mentioning is not doing; a substring matcher mis-flags that file.

**(c) Neither G4 nor G5 decides polarity for a new transport.** G5 **passes** when a third
transport simply reuses ``HOSTED_SERVICE`` -- the argument is still a literal ``Attribute`` on
the enum, the literal set is still the two members, and G5's per-site clause names only the sites
that already exist. G4 fires (its exact counts move), but only as a *prompt* whose obvious
resolution is to edit the expected numbers in this file. **A passing G5 is not an answered
question about polarity.** That requirement lives in :class:`EgressDestination`'s own docstring
(FR-004/FR-017) and nowhere else; see preconditions section 1.6(7) of the Mission handoff.

**(d) Bundle B must UPDATE these counts, not let them fall to zero.** Sibling Bundle B moves
``tracker_egress_verdict``, ``EgressDestination`` and all of these call sites into
``specify_cli.egress``. When it does, the membership sets below are a **rename**, not a
rediscovery. Every count here is asserted with ``==``, never ``<=`` -- a ``<=`` assertion is not
a weaker guard, it is a guard that reports healthy after its subject has been deleted, which is
exactly what a file move produces.

**(e) An aliased import of ``EgressDestination`` produces a FALSE RED on G5.** G5 resolves the
``destination`` argument as an ``ast.Attribute`` whose value resolves to the name
``EgressDestination``. ``import ... as ED`` turns every call-site argument into an ``Attribute``
on ``ED``, which G5 reports as non-literal. That is loud rather than silent, but the failure
message leads with the hint so the next reader does not lose an afternoon to it. Note that
*module*-qualified access (``ev.EgressDestination.LOCAL_SUBPROCESS``) is still a literal member
-- the enum is reached under its own name -- and is deliberately classified as such, so that G5's
module-qualified mutant kills via the per-site mapping clause (the clause that carries G5) rather
than via an incidental mis-classification of its argument.

Guards in this file
----------------------

=====  ==========================================================================  =============
Guard  Property                                                                    Mutants killed
=====  ==========================================================================  =============
G1     ``factory.SUPPORTED_PROVIDERS`` is exactly ``("beads", "fp")``               3
G2     ``build_connector`` has exactly one call site, in ``_build_engine``          2
G3     ``_build_engine``'s callers are exactly the three gated methods, and the     5
       gate is the first *executable* statement of each
G4     exactly 6 enclosing functions and exactly 7 call expressions                 3
G5     every ``destination`` is a literal member, and the per-site mapping holds    3
G6     the verdict *body* never reads the provider (expected set empty)             2
G7     WP03's polarity map is exhaustive over ``config._EGRESS_LEGAL_VALUES``       1
G8     the ``_build_engine`` patch census over ``tests/`` is exact                  2
=====  ==========================================================================  =============

G7 and G8 are additions beyond FR-015's G1-G6, each closing a gap routed here from a review of
another work package. They are labelled distinctly so a reader is never misled about which
guards FR-015 actually specifies.

**SC-017's own accounting is unchanged and still holds: G4 kills three, G5 kills three, G6 kills
the reintroduced provider read.** G1 (1 -> 3), G3 (3 -> 5) and G6 (1 -> 2) carry *additional*
mutants added at review for holes measured after the spec was written -- G1's two silent-pass
shapes, G3's two non-leading gate shapes, and G6's string-indirected read. None replaces a
spec-named mutant; each is listed beside the one it supplements in its own test.

Honest limits -- recorded, not papered over
----------------------------------------------

1. **Precondition 1.6(4) -- "the tracker path stays operator-invoked" -- has no executable
   guard, and none is invented here.** If any daemon, sweep, hook or ``next``-loop ever reaches
   ``LocalTrackerService``, the attribution precondition in ``specify_cli/egress.py`` is
   violated: a valid root for the *wrong project*, which is the cross-project substitution
   ``#3030`` exists to close. That is prose. It is carried as a residual, and a Mission adding an
   automatic caller must re-check it by reading, because nothing here will fire.
2. **Precondition 1.6(7) -- a third transport reusing ``HOSTED_SERVICE`` -- is not caught by G5
   and only prompted by G4**, as spelled out in (c) above. Neither guard decides polarity.
3. **G8 pins a census, not a prohibition.** The three ``_build_engine`` patch sites in
   ``tests/sync/tracker/test_local_service.py`` are a documented, legitimate escape hatch (that
   file avoids a hard dependency on the ``spec_kitty_tracker`` package). G8 does not ban them --
   it pins them exactly, so a *fourth* site anywhere under ``tests/`` reds.
4. **Every matcher here is syntactic, so a call reached through a binding is invisible.**
   ``_fn = tracker_egress_verdict`` followed by ``_fn(root, destination=...)``, and
   ``getattr(ev, "tracker_egress_verdict")(...)``, are resolved by **no** matcher in this file
   (measured: 0 calls found for both). This is inherent to AST matching without dataflow
   analysis, and it is **not** the hazard that was actually measured on this Mission -- that was
   the module-qualified form, which *is* resolved. It is recorded because a file that states
   four limits to this standard should not leave a fifth implicit. The same limit applies to G6
   (a provider read through a renamed local is undecidable here) and to G8.
5. **The egress-consent boundary scanner cannot substitute for G2/G3.**
   ``tests/architectural/test_egress_consent_boundary.py`` is untouched by this file and cannot
   help: ``local_service.py`` holds **zero** HTTP sinks, so it cannot be allowlisted there (that
   suite deletes allowlist entries which guard nothing), and that suite's own recorded limit 4
   means a ``subprocess`` invoked via a variable command name -- precisely this Mission's local
   gap -- was never in its view. No ``_baselines.yaml`` bump is made or needed here.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import pytest

from specify_cli.tracker import config as tracker_config
from specify_cli.tracker.egress_verdict import EgressDestination, _JOIN, _LEGAL_CHANNEL2_VALUES

#: Without a module-level marker this file is selected by **zero** CI gates, so every guard below
#: would be invisible on a push to ``main`` -- a falsity guard that cannot turn the branch red is
#: not a guard. Measured: omitting this reddened
#: ``test_pytest_marker_convention::test_every_test_file_declares_a_pytestmark_marker``,
#: ``test_gate_coverage::test_no_new_orphan_surfaces``,
#: ``test_same_tier_uniqueness::test_split_preserves_zero_orphans`` and
#: ``test_ci_collection_completeness::test_every_test_node_is_collected_on_a_push_to_main``,
#: all four naming this file, with all eight guards listed as orphaned node ids.
pytestmark = [pytest.mark.architectural]

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
TESTS_ROOT = REPO_ROOT / "tests"

#: The verdict function every call-site guard is about.
VERDICT_FN = "tracker_egress_verdict"
#: The enum whose members are the only legal ``destination`` argument (see module docstring (e)).
DESTINATION_ENUM = "EgressDestination"


# ===========================================================================
# T037 -- the shared harness: matcher, scope resolution, input counts
# ===========================================================================


def _callee_trailing_name(node: ast.Call) -> str | None:
    """Return the trailing name of *node*'s callee, resolving **both** func-node forms.

    ``f(...)``            -> ``ast.Name``      -> ``"f"``
    ``mod.f(...)``        -> ``ast.Attribute`` -> ``"f"``
    ``a.b.c.f(...)``      -> ``ast.Attribute`` -> ``"f"``
    ``obj[0](...)``       -> neither           -> ``None``

    This single function is the module docstring's point (b) made executable. Every call matcher
    in this file goes through it; none of them inspects ``node.func`` directly.
    """
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _name_only_callee_trailing_name(node: ast.Call) -> str | None:
    """The **deliberately blind** ``ast.Name``-only matcher, kept for one purpose only.

    This is the matcher shape that was measured to pass a module-qualified sixth call site while
    reporting itself healthy. It exists here so the guards can demonstrate the blind spot
    *red-then-green* against their own module-qualified mutants (see
    :func:`test_g5_module_qualified_mutant_observed_red_then_green`) rather than merely asserting
    that the correct matcher works. **No guard uses it.**
    """
    func = node.func
    return func.id if isinstance(func, ast.Name) else None


@dataclass(frozen=True)
class Scope:
    """One lexical scope on the enclosing stack."""

    kind: str  # "class" | "func"
    name: str


def _outermost_qualname(scopes: list[Scope]) -> str:
    """Qualify a call by its **outermost enclosing function**, prefixed by enclosing classes.

    This is load-bearing and was measured. The three ``_build_engine`` calls in
    ``local_service.py`` sit inside nested ``_run`` closures::

        _build_engine call inside: ['sync_pull', '_run']
        _build_engine call inside: ['sync_push', '_run']
        _build_engine call inside: ['sync_run',  '_run']

    A naive *immediately*-enclosing resolver yields ``{_run, _run, _run}`` -- one element, not
    three -- and G3 reds on correct code. Stopping at the **first** function in the scope stack
    collapses every nested closure onto the method that owns it, so the three calls attribute to
    ``LocalTrackerService.sync_pull`` / ``.sync_push`` / ``.sync_run`` as intended.

    Classes preceding that function are kept, so a same-named function elsewhere in the tree
    cannot satisfy a membership assertion (``LocalTrackerService.sync_push``, never ``sync_push``).
    """
    parts: list[str] = []
    for scope in scopes:
        parts.append(scope.name)
        if scope.kind == "func":
            break
    return ".".join(parts) if parts else "<module>"


@dataclass
class Call:
    """One matched call expression, attributed to its outermost enclosing function."""

    module: str
    qualname: str
    lineno: int
    #: ``"Name"`` or ``"Attribute"`` -- which func-node form the call was written in. Recorded so
    #: a guard's report can show that it saw a module-qualified site, not merely that a count moved.
    func_form: str
    node: ast.Call = field(repr=False)

    def __str__(self) -> str:
        return f"{self.module}::{self.qualname} (L{self.lineno}, {self.func_form}-form)"


class _CallCollector(ast.NodeVisitor):
    """Collect every call to *target* in one module, attributed by outermost enclosing function."""

    def __init__(self, module: str, target: str) -> None:
        self.module = module
        self.target = target
        self.scopes: list[Scope] = []
        self.calls: list[Call] = []

    def _descend(self, node: ast.AST, scope: Scope) -> None:
        self.scopes.append(scope)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._descend(node, Scope("func", node.name))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._descend(node, Scope("func", node.name))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._descend(node, Scope("class", node.name))

    def visit_Call(self, node: ast.Call) -> None:
        if _callee_trailing_name(node) == self.target:
            self.calls.append(
                Call(
                    module=self.module,
                    qualname=_outermost_qualname(self.scopes),
                    lineno=node.lineno,
                    func_form=type(node.func).__name__,
                    node=node,
                )
            )
        self.generic_visit(node)


@dataclass
class CallFindings:
    """What a call-site analyzer found, including the input count that makes it non-vacuous."""

    #: Files scanned (tree analyzers) or 1 (source-text analyzers). Asserted non-zero by every test.
    input_count: int
    calls: list[Call]

    @property
    def call_count(self) -> int:
        """Number of **call expressions**. Deliberately distinct from :attr:`enclosing`."""
        return len(self.calls)

    @property
    def enclosing(self) -> set[str]:
        """Set of **outermost enclosing function** qualnames. Deliberately distinct from count."""
        return {call.qualname for call in self.calls}

    def describe(self) -> str:
        return "\n".join(f"    {call}" for call in sorted(map(str, self.calls))) or "    (none)"


def _parse_path(path_str: str) -> ast.Module | None:
    """Parse one file. **Deliberately not cached** -- each tree is released after it is visited.

    An earlier revision cached this with ``@cache`` to save one re-walk of ``src/``. Measured, that
    trade was badly wrong: retaining the ASTs of 3,862 modules cost **+1,116 MB** of peak RSS
    (guard suite peak 1,205,972 kB, against 92,924 kB for the same file with the tree-scanning
    guards removed, and 94,124 kB for ``test_golden_count_ban.py``, which walks the same ``tests/``
    tree without retaining). On a 4-vCPU ``-n auto`` runner that is not a saving, it is an OOM
    risk. **Findings are cached instead** (see :func:`_calls_in_tree` and
    :func:`_patch_sites_in_tree`): they are a few hundred bytes each, and they are what the guards
    actually reuse.
    """
    try:
        return ast.parse(Path(path_str).read_text(encoding="utf-8"), filename=path_str)
    except (SyntaxError, UnicodeDecodeError):
        return None


def analyze_calls_in_source(source: str, target: str, *, module: str = "<synthetic>") -> CallFindings:
    """Source-text entry point: find every *target* call in one module held as a string.

    This is the entry point every mutant run uses -- the synthetic module never reaches disk.
    """
    collector = _CallCollector(module, target)
    collector.visit(ast.parse(source, filename=module))
    return CallFindings(input_count=1, calls=collector.calls)


@cache
def _calls_in_tree(root_str: str, target: str) -> CallFindings:
    """Cached findings (not cached trees -- see :func:`_parse_path`)."""
    root = Path(root_str)
    calls: list[Call] = []
    scanned = 0
    for path in sorted(root.rglob("*.py")):
        tree = _parse_path(str(path))
        if tree is None:
            continue
        scanned += 1
        collector = _CallCollector(str(path.relative_to(root)), target)
        collector.visit(tree)
        calls.extend(collector.calls)
        del tree  # release this module's AST before parsing the next one
    return CallFindings(input_count=scanned, calls=calls)


def analyze_calls_in_tree(root: Path, target: str) -> CallFindings:
    """Root-path entry point: find every *target* call under *root*, reporting files scanned."""
    return _calls_in_tree(str(root), target)


def _announce(guard: str, input_count: int, **facts: object) -> None:
    """Print the input count and interpreter beside every result, and assert it is non-zero.

    *"Print the input count alongside any 'all checks passed' -- a gate that ran on zero files
    passes vacuously."* That happened during ``#3030`` and hid a real error. The interpreter
    version is printed too, because *a zero count is a statement about the environment, not about
    the code*: a branch unreachable on the local interpreter but live on CI's would otherwise read
    as dead code.
    """
    print(f"[{guard}] INPUT COUNT: {input_count}   interpreter: {sys.version.split()[0]}")
    for key, value in facts.items():
        print(f"[{guard}]   {key}: {value}")
    assert input_count > 0, (
        f"{guard} scanned ZERO inputs -- this result is vacuous, not a pass. "
        f"If Bundle B moved this guard's subject, re-point it; do not let it scan nothing."
    )


# ---------------------------------------------------------------------------
# T037 exit -- the matcher's own falsification probe
# ---------------------------------------------------------------------------

_PROBE_BOTH_FORMS = '''
from specify_cli.tracker.egress_verdict import tracker_egress_verdict
from specify_cli.tracker import egress_verdict as ev

def written_as_a_bare_name(root):
    return tracker_egress_verdict(root, destination=None)

def written_module_qualified(root):
    return ev.tracker_egress_verdict(root, destination=None)
'''


def test_matcher_resolves_both_name_and_attribute_func_nodes() -> None:
    """Control the diagnostic before trusting it: a matcher you have not falsified is not a matcher.

    The probe module holds **exactly one** ``ast.Name`` call and **exactly one** ``ast.Attribute``
    call. The correct matcher must find 2. The deliberately-blind ``ast.Name``-only matcher must
    find 1 -- asserted as the **negative control**, because "the matcher found 2" proves nothing
    unless a matcher with the known hole demonstrably finds fewer on the same input.
    """
    found = analyze_calls_in_source(_PROBE_BOTH_FORMS, VERDICT_FN, module="<probe>")
    _announce(
        "T037-probe",
        found.input_count,
        calls_found=found.call_count,
        forms=sorted(call.func_form for call in found.calls),
    )
    assert found.call_count == 2, f"matcher is blind to one of the two func-node forms:\n{found.describe()}"
    assert sorted(call.func_form for call in found.calls) == ["Attribute", "Name"]

    blind = [
        node
        for node in ast.walk(ast.parse(_PROBE_BOTH_FORMS))
        if isinstance(node, ast.Call) and _name_only_callee_trailing_name(node) == VERDICT_FN
    ]
    assert len(blind) == 1, (  # golden-count: cardinality-is-contract
        "NEGATIVE CONTROL FAILED: the ast.Name-only matcher was expected to miss the "
        f"module-qualified call and see exactly 1, but saw {len(blind)}. The probe no longer "
        "discriminates, so this file's 'both forms resolved' claim is unproven."
    )


# ===========================================================================
# T038 -- G1: the connector perimeter stays ("beads", "fp")
# ===========================================================================

EXPECTED_SUPPORTED_PROVIDERS = frozenset({"beads", "fp"})
_FACTORY_PATH = SRC_ROOT / "specify_cli" / "tracker" / "factory.py"


@dataclass
class ProviderFindings:
    """What G1's analyzer found. ``input_count`` is AST nodes scanned."""

    input_count: int
    providers: frozenset[str] | None
    #: Every assignment to ``SUPPORTED_PROVIDERS`` this analyzer could NOT read as a literal
    #: sequence of string constants, unparsed. Review LOW-1: an earlier revision skipped such
    #: assignments silently and kept whatever an *earlier* literal had said, so
    #: ``SUPPORTED_PROVIDERS = SUPPORTED_PROVIDERS + ("jira",)`` read as exactly ``{beads, fp}``
    #: and G1 passed. Asserted empty, so an unreadable form is a loud red rather than a stale
    #: answer. (A computed ``tuple(...)`` or a set literal already redded loudly; these were the
    #: only two silent shapes.)
    unreadable_assignments: list[str] = field(default_factory=list)
    #: Elements of the literal that are not string ``Constant``s -- e.g. ``("beads","fp",JIRA)``,
    #: where an earlier revision silently filtered ``JIRA`` out and again read ``{beads, fp}``.
    non_constant_elements: list[str] = field(default_factory=list)
    #: Total elements in the literal, so a *count* change is caught even if every element it can
    #: read happens to match. Asserted against the expected membership's own size.
    element_count: int = 0


def analyze_supported_providers(source: str) -> ProviderFindings:
    """Read ``SUPPORTED_PROVIDERS``'s literal members out of *source* by AST, never by import.

    By AST rather than by importing ``factory``: the mutant run must be able to analyze a
    synthetic ``factory`` source that is never placed on ``sys.path``, and an import-based reader
    could not.
    """
    tree = ast.parse(source)
    findings = ProviderFindings(input_count=0, providers=None)
    for node in ast.walk(tree):
        findings.input_count += 1
        value = _supported_providers_assignment(node)
        if value is None:
            continue
        if not isinstance(value, (ast.Tuple, ast.List)):
            # LOW-1: an unreadable form (a BinOp such as ``SUPPORTED_PROVIDERS + ("jira",)``,
            # a computed ``tuple(...)``, a set literal) must not leave a stale earlier answer
            # standing. Record it; the test asserts this list is empty.
            findings.unreadable_assignments.append(ast.unparse(value))
            continue
        findings.element_count = len(value.elts)
        findings.non_constant_elements = [
            ast.unparse(e) for e in value.elts if not (isinstance(e, ast.Constant) and isinstance(e.value, str))
        ]
        findings.providers = frozenset(
            e.value for e in value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)
        )
    return findings


def _supported_providers_assignment(node: ast.AST) -> ast.expr | None:
    """Return the value expression assigned to ``SUPPORTED_PROVIDERS`` by *node*, if any."""
    if isinstance(node, ast.AnnAssign):
        targets: list[ast.expr] = [node.target]
        value = node.value
    elif isinstance(node, ast.Assign):
        targets = list(node.targets)
        value = node.value
    else:
        return None
    if value is None:
        return None
    if not any(isinstance(t, ast.Name) and t.id == "SUPPORTED_PROVIDERS" for t in targets):
        return None
    return value


_G1_MUTANT_THIRD_PROVIDER = '''
SUPPORTED_PROVIDERS: tuple[str, ...] = ("beads", "fp", "jira")
'''

#: Review LOW-1, silent hole (a): the widening is a ``BinOp``, so the literal reader sees nothing
#: and an earlier revision kept the first assignment's answer -- reading exactly ``{beads, fp}``.
_G1_MUTANT_WIDENED_BY_BINOP = '''
SUPPORTED_PROVIDERS: tuple[str, ...] = ("beads", "fp")
SUPPORTED_PROVIDERS = SUPPORTED_PROVIDERS + ("jira",)
'''

#: Review LOW-1, silent hole (b): a non-``Constant`` element was silently filtered out, so
#: ``("beads", "fp", JIRA)`` also read as exactly ``{beads, fp}``.
_G1_MUTANT_NON_CONSTANT_ELEMENT = '''
JIRA = "jira"
SUPPORTED_PROVIDERS: tuple[str, ...] = ("beads", "fp", JIRA)
'''


def test_g1_build_connector_perimeter_is_exactly_beads_and_fp() -> None:
    """G1 -- ``SUPPORTED_PROVIDERS`` is exactly ``{"beads", "fp"}``, so ``LocalTrackerService``
    cannot become a second, differently-gated route to a hosted destination.

    **Note what this precondition no longer carries.** An earlier revision called G1 the sharpest
    failure this Mission could have, because a widened ``SUPPORTED_PROVIDERS`` combined with a
    **config-derived** polarity would mis-classify a hosted destination as local. With the
    destination supplied as a caller literal at every site, that failure mode is *structurally
    impossible* and G1 now guards only the gate-divergence half: two routes to a hosted
    destination, gated by two different gates, free to disagree. **The sharpest failure moved,
    and it is guarded by G5.**
    """
    real = analyze_supported_providers(_FACTORY_PATH.read_text(encoding="utf-8"))
    _announce(
        "G1",
        real.input_count,
        file=str(_FACTORY_PATH.relative_to(REPO_ROOT)),
        providers_found=sorted(real.providers or ()),
        literal_elements=real.element_count,
    )
    assert real.providers is not None, f"SUPPORTED_PROVIDERS not found in {_FACTORY_PATH} -- moved or renamed?"
    # LOW-1: both of these close a *silent* pass. Neither can be folded into the membership
    # assertion below, because in both mutant shapes the membership still reads exactly {beads, fp}.
    assert not real.unreadable_assignments, (
        "G1: SUPPORTED_PROVIDERS is assigned by a form this analyzer cannot read as a literal "
        f"sequence of string constants: {real.unreadable_assignments}. Refusing to report the "
        "membership from an earlier assignment -- that is how `SUPPORTED_PROVIDERS + ('jira',)` "
        "would read as exactly {'beads', 'fp'} and pass."
    )
    assert not real.non_constant_elements, (
        f"G1: SUPPORTED_PROVIDERS holds non-literal element(s) {real.non_constant_elements}, which "
        "an earlier revision silently filtered out -- so a widened perimeter read clean."
    )
    assert real.element_count == len(EXPECTED_SUPPORTED_PROVIDERS), (
        f"G1: SUPPORTED_PROVIDERS holds {real.element_count} element(s), expected "
        f"{len(EXPECTED_SUPPORTED_PROVIDERS)}. A count change is caught even when every element "
        "this analyzer can read happens to match."
    )
    assert real.providers == EXPECTED_SUPPORTED_PROVIDERS, (
        f"G1: build_connector's provider perimeter changed.\n"
        f"  expected: {sorted(EXPECTED_SUPPORTED_PROVIDERS)}\n"
        f"  found:    {sorted(real.providers)}\n"
        f"  added:    {sorted(real.providers - EXPECTED_SUPPORTED_PROVIDERS)}\n"
        f"If a SAAS_PROVIDERS member was added, LocalTrackerService is now a second route to a "
        f"hosted destination with its own gate, and the two gates can disagree (precondition 1.6.1)."
    )

    killed = 0

    mutant = analyze_supported_providers(_G1_MUTANT_THIRD_PROVIDER)
    assert mutant.providers != EXPECTED_SUPPORTED_PROVIDERS, "G1 MUTANT SURVIVED: a third provider was not detected"
    killed += 1
    print(f"[G1] mutant killed (literal third provider): added {sorted((mutant.providers or frozenset()) - EXPECTED_SUPPORTED_PROVIDERS)}")

    # LOW-1 (a): the widening is a BinOp. The literal reader cannot resolve it, and the earlier
    # revision silently kept the first assignment's answer -- reading exactly {beads, fp}.
    binop = analyze_supported_providers(_G1_MUTANT_WIDENED_BY_BINOP)
    assert binop.providers == EXPECTED_SUPPORTED_PROVIDERS, (
        "G1 harness note: this mutant's whole point is that the *membership* clause still reads "
        f"{sorted(binop.providers or ())} -- if that changed, re-derive which clause now kills it."
    )
    assert binop.unreadable_assignments, "G1 MUTANT SURVIVED (BinOp widening): the unreadable assignment was not recorded"
    killed += 1
    print(
        f"[G1] mutant killed (BinOp widening) via the unreadable-assignment clause: {binop.unreadable_assignments} "
        f"(membership clause alone still read {sorted(binop.providers or ())})"
    )

    # LOW-1 (b): a non-Constant element was silently filtered out, so the membership read clean.
    non_const = analyze_supported_providers(_G1_MUTANT_NON_CONSTANT_ELEMENT)
    assert non_const.providers == EXPECTED_SUPPORTED_PROVIDERS, "G1 harness note: see above -- membership alone is expected to still read clean here"
    assert non_const.non_constant_elements, "G1 MUTANT SURVIVED (non-Constant element): the element was silently filtered"
    killed += 1
    print(f"[G1] mutant killed (non-Constant element) via the element clauses: elements={non_const.element_count}, non-constant={non_const.non_constant_elements}")
    print(f"[G1] KILLED-PIN COUNT: {killed}/3")


# ===========================================================================
# T038 -- G2: build_connector has exactly one call site
# ===========================================================================

EXPECTED_BUILD_CONNECTOR_SITES = frozenset({"LocalTrackerService._build_engine"})
EXPECTED_BUILD_CONNECTOR_COUNT = 1

#: The **control** every G2 mutant is measured against: the correct shape, one call site in
#: ``_build_engine``. Each mutant below is this control plus one extra site, so the kill can be
#: attributed to the added site rather than to the synthetic base merely differing from ``src/``.
_G2_CONTROL = '''
from specify_cli.tracker.factory import build_connector

class LocalTrackerService:
    def _build_engine(self, config, credentials, store):
        return build_connector(provider="beads", workspace="w", credentials=credentials)
'''

_G2_MUTANT_SECOND_SITE = _G2_CONTROL + '''
def some_other_helper(config, credentials):
    return build_connector(provider="beads", workspace="w", credentials=credentials)
'''

_G2_MUTANT_SECOND_SITE_QUALIFIED = _G2_CONTROL + '''
from specify_cli.tracker import factory

def some_other_helper(config, credentials):
    return factory.build_connector(provider="beads", workspace="w", credentials=credentials)
'''


def test_g2_build_connector_has_exactly_one_call_site() -> None:
    """G2 -- ``build_connector``'s call sites are exactly ``{LocalTrackerService._build_engine}``,
    count exactly **1**, never ``<=``.

    A second construction site bypasses the gate silently **and is invisible to
    ``tests/architectural/test_egress_consent_boundary.py``**, because ``local_service.py`` holds
    zero HTTP sinks and therefore cannot be allowlisted there at all. Nothing else in the tree is
    watching this.
    """
    real = analyze_calls_in_tree(SRC_ROOT, "build_connector")
    _announce("G2", real.input_count, call_expressions=real.call_count, sites=sorted(real.enclosing))
    assert real.call_count == EXPECTED_BUILD_CONNECTOR_COUNT, (
        f"G2: expected exactly {EXPECTED_BUILD_CONNECTOR_COUNT} build_connector call expression, "
        f"found {real.call_count}:\n{real.describe()}"
    )
    assert real.enclosing == EXPECTED_BUILD_CONNECTOR_SITES, (
        f"G2: build_connector's call-site set changed.\n"
        f"  expected: {sorted(EXPECTED_BUILD_CONNECTOR_SITES)}\n"
        f"  found:    {sorted(real.enclosing)}\n"
        f"  symmetric difference: {sorted(real.enclosing ^ EXPECTED_BUILD_CONNECTOR_SITES)}\n"
        f"A second connector-construction site bypasses the egress gate and is invisible to the "
        f"egress-consent boundary test (local_service.py holds no HTTP sink). If Bundle B moved "
        f"this site, update the expected set -- do not let it fall to zero."
    )

    control = analyze_calls_in_source(_G2_CONTROL, "build_connector", module="<g2-control>")
    assert control.call_count == 1 and control.enclosing == EXPECTED_BUILD_CONNECTOR_SITES, (
        f"G2 MUTANT HARNESS MISBUILT: the control must itself be the correct shape (1 site in "
        f"_build_engine), otherwise every 'kill' below is attributable to the synthetic base rather "
        f"than to the mutant. Control found {control.call_count} call(s) in {sorted(control.enclosing)}."
    )

    killed = 0
    for label, mutant_source in (("bare-name second site", _G2_MUTANT_SECOND_SITE), ("module-qualified second site", _G2_MUTANT_SECOND_SITE_QUALIFIED)):
        mutant = analyze_calls_in_source(mutant_source, "build_connector", module="<g2-mutant>")
        added = mutant.enclosing - control.enclosing
        assert len(added) == 1 and mutant.call_count == control.call_count + 1, (  # golden-count: cardinality-is-contract
            f"G2 MUTANT MISBUILT ({label}): expected exactly one added site, got added={sorted(added)} "
            f"and {mutant.call_count} calls against the control's {control.call_count}."
        )
        # The consequence for the real guard: fold the mutant's delta onto the real tree's findings.
        assert (real.enclosing | added) != EXPECTED_BUILD_CONNECTOR_SITES, f"G2 MUTANT SURVIVED ({label}) on membership"
        assert real.call_count + 1 != EXPECTED_BUILD_CONNECTOR_COUNT, f"G2 MUTANT SURVIVED ({label}) on call count"
        killed += 1
        print(f"[G2] mutant killed ({label}): control 1 site -> mutant {mutant.call_count} sites, added {sorted(added)}")
    print(f"[G2] KILLED-PIN COUNT: {killed}/2")


# ===========================================================================
# T039 -- G3: the gate is the first executable statement of exactly three methods
# ===========================================================================

_LOCAL_SERVICE_PATH = SRC_ROOT / "specify_cli" / "tracker" / "local_service.py"

EXPECTED_BUILD_ENGINE_CALLERS = frozenset(
    {"LocalTrackerService.sync_pull", "LocalTrackerService.sync_push", "LocalTrackerService.sync_run"}
)


@dataclass
class GateFindings:
    """What G3's analyzer found. ``input_count`` is AST nodes scanned in the module."""

    input_count: int
    callers: set[str]
    #: qualname -> whether the first *executable* statement contains a ``tracker_egress_verdict``
    #: call (docstring tolerated as a leading node, nothing else tolerated ahead of the gate).
    gate_is_first: dict[str, bool]
    #: qualname -> ``ast.unparse`` of whatever the first executable statement actually was,
    #: so the failure message can name what displaced the gate rather than asserting a bare bool.
    first_statement: dict[str, str]


def _first_executable_statement(body: list[ast.stmt]) -> ast.stmt | None:
    """Return the first statement of *body*, **tolerating a leading docstring** and nothing else.

    A naive implementation either rejects a docstring (false red on correct code) or accepts an
    arbitrary statement before the gate (false green). Only ``Expr(Constant(str))`` is skipped.
    """
    for stmt in body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            continue
        return stmt
    return None


def _statement_calls_verdict(stmt: ast.stmt) -> bool:
    """Whether *stmt* **is** the gate: a plain statement whose own value is the verdict call.

    Not "some call" and not "a call to any helper". FR-003: *"a helper would let G3's 'first
    statement' property be satisfied by a call to the helper, which stops pinning
    ``tracker_egress_verdict`` at all."* There is deliberately no ``_require_egress`` helper in
    this Mission, and this predicate is what keeps it that way.

    **And not "a call anywhere in the statement's subtree" either** -- review MEDIUM-2. An earlier
    revision used ``ast.walk(stmt)``, which accepted both of these as "the gate is first"::

        result = self._open_credential_store(tracker_egress_verdict(root, destination=...))
        if True:
            verdict = tracker_egress_verdict(root, destination=...)

    The first runs a **machine-global credential-store read before the gate** -- precisely the
    C-018 consequence G3 exists to prevent, since that read plus the ``TrackerSqliteStore``
    construction is what leaves a SQLite file with three tables behind on a *refused* command. The
    second makes the gate skippable. Both passed.

    So the statement must be an ``Assign`` / ``AnnAssign`` / ``Expr`` / ``Return`` whose **value
    node is itself** the verdict call. Every compound wrapper (``If``, ``Try``, ``With``, ``For``,
    ``While``, ``Match``) is rejected by falling through to ``False``, and a call nested as an
    *argument* is rejected because the outer call's own callee is not ``tracker_egress_verdict``.
    This still admits the real shape, ``verdict = tracker_egress_verdict(...)``.
    """
    if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.Expr, ast.Return)):
        value = stmt.value
    else:
        return False
    return value is not None and isinstance(value, ast.Call) and _callee_trailing_name(value) == VERDICT_FN


def analyze_gate_placement(source: str) -> GateFindings:
    """Find ``_build_engine``'s callers in *source* and check the gate leads each of their bodies."""
    tree = ast.parse(source)
    nodes = sum(1 for _ in ast.walk(tree))
    collector = _CallCollector("<analyzed>", "_build_engine")
    collector.visit(tree)
    callers = {call.qualname for call in collector.calls}

    gate_is_first: dict[str, bool] = {}
    first_statement: dict[str, str] = {}
    for qualname, func in _functions_by_outermost_qualname(tree).items():
        if qualname not in callers:
            continue
        stmt = _first_executable_statement(func.body)
        gate_is_first[qualname] = stmt is not None and _statement_calls_verdict(stmt)
        first_statement[qualname] = "<empty body>" if stmt is None else ast.unparse(stmt).splitlines()[0]
    return GateFindings(input_count=nodes, callers=callers, gate_is_first=gate_is_first, first_statement=first_statement)


def _functions_by_outermost_qualname(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Map each **outermost** function's qualname to its node (nested closures excluded).

    Excluding nested functions is deliberate: G3 asks whether the gate leads ``sync_pull``'s body,
    not whether it leads the ``_run`` closure that ``sync_pull`` defines further down.
    """
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    def walk(node: ast.AST, scopes: list[Scope]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, [*scopes, Scope("class", child.name)])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[_outermost_qualname([*scopes, Scope("func", child.name)])] = child
                # Deliberately not descending: nested closures belong to this function.
            else:
                walk(child, scopes)

    walk(tree, [])
    return found


_G3_POSITIVE_CONTROL = '''
class LocalTrackerService:
    def sync_pull(self, *, limit=100):
        """A docstring is tolerated as the first NODE."""
        verdict = tracker_egress_verdict(self._repo_root, destination=EgressDestination.LOCAL_SUBPROCESS)
        if verdict.refused:
            raise LocalTrackerEgressRefusedError(verdict)
        config, credentials, store = self._load_runtime()
        async def _run():
            connector, engine = self._build_engine(config, credentials, store)
            return connector
        return self._run_async(_run())
'''

_G3_MUTANT_FOURTH_CALLER = _G3_POSITIVE_CONTROL + '''
    def sync_sideways(self, *, limit=100):
        config, credentials, store = self._load_runtime()
        connector, engine = self._build_engine(config, credentials, store)
        return connector
'''

_G3_MUTANT_STATEMENT_BEFORE_GATE = '''
class LocalTrackerService:
    def sync_pull(self, *, limit=100):
        """Docstring, then a harmless-looking statement, then the gate."""
        logger.debug("about to sync")
        verdict = tracker_egress_verdict(self._repo_root, destination=EgressDestination.LOCAL_SUBPROCESS)
        if verdict.refused:
            raise LocalTrackerEgressRefusedError(verdict)
        config, credentials, store = self._load_runtime()
        async def _run():
            connector, engine = self._build_engine(config, credentials, store)
            return connector
        return self._run_async(_run())
'''

_G3_MUTANT_HELPER_STANDS_IN = '''
class LocalTrackerService:
    def sync_pull(self, *, limit=100):
        """The gate is now behind a helper, which stops pinning tracker_egress_verdict."""
        self._require_egress(EgressDestination.LOCAL_SUBPROCESS)
        config, credentials, store = self._load_runtime()
        async def _run():
            connector, engine = self._build_engine(config, credentials, store)
            return connector
        return self._run_async(_run())
'''

#: Review MEDIUM-2, mutant (iv): the gate call is an **argument** to another call, so a
#: credential-store read happens *before* the verdict is even computed. This is the C-018
#: consequence in its exact shape -- the statement "contains" the gate while not being it.
_G3_MUTANT_GATE_NESTED_AS_ARGUMENT = '''
class LocalTrackerService:
    def sync_pull(self, *, limit=100):
        """The gate is buried as an argument, behind a credential-store read."""
        result = self._open_credential_store(tracker_egress_verdict(self._repo_root, destination=EgressDestination.LOCAL_SUBPROCESS))
        config, credentials, store = self._load_runtime()
        async def _run():
            connector, engine = self._build_engine(config, credentials, store)
            return connector
        return self._run_async(_run())
'''

#: Review MEDIUM-2, mutant (v): the gate is real and unwrapped, but sits inside an ``If``, so it
#: is **skippable**. "First executable statement" must mean unconditional.
_G3_MUTANT_GATE_INSIDE_CONDITIONAL = '''
class LocalTrackerService:
    def sync_pull(self, *, limit=100):
        """The gate is now conditional, so some path reaches the connector ungated."""
        if self._egress_checks_enabled:
            verdict = tracker_egress_verdict(self._repo_root, destination=EgressDestination.LOCAL_SUBPROCESS)
            if verdict.refused:
                raise LocalTrackerEgressRefusedError(verdict)
        config, credentials, store = self._load_runtime()
        async def _run():
            connector, engine = self._build_engine(config, credentials, store)
            return connector
        return self._run_async(_run())
'''


def test_g3_build_engine_callers_are_the_three_gated_methods() -> None:
    """G3 -- ``_build_engine``'s callers are exactly the three gated methods, and in each of them
    the ``tracker_egress_verdict`` call is the **first executable statement**.

    This is the structural half of a named risk: *the gate is quietly moved back into
    ``_build_engine`` by a later reader, because it produces no egress and therefore looks
    harmless.* It is not harmless. Moving it back reintroduces, **on a refused command**, a
    machine-global credential-store read and a ``TrackerSqliteStore`` construction that ``mkdir``s
    and creates a SQLite file with three tables. A refusal must leave no trace on disk.

    The three calls sit inside nested ``_run`` closures; see :func:`_outermost_qualname` for why a
    naive immediately-enclosing resolver reds on correct code here.
    """
    real = analyze_gate_placement(_LOCAL_SERVICE_PATH.read_text(encoding="utf-8"))
    _announce(
        "G3",
        real.input_count,
        file=str(_LOCAL_SERVICE_PATH.relative_to(REPO_ROOT)),
        callers=sorted(real.callers),
        gate_is_first_statement=real.gate_is_first,
    )
    assert len(real.callers) == len(EXPECTED_BUILD_ENGINE_CALLERS), (
        f"G3: expected exactly {len(EXPECTED_BUILD_ENGINE_CALLERS)} _build_engine callers, "
        f"found {len(real.callers)}: {sorted(real.callers)}"
    )
    assert real.callers == EXPECTED_BUILD_ENGINE_CALLERS, (
        f"G3: the set of _build_engine callers changed.\n"
        f"  expected: {sorted(EXPECTED_BUILD_ENGINE_CALLERS)}\n"
        f"  found:    {sorted(real.callers)}\n"
        f"  symmetric difference: {sorted(real.callers ^ EXPECTED_BUILD_ENGINE_CALLERS)}\n"
        f"A fourth caller is an ungated path to the connector."
    )
    displaced = {q: real.first_statement[q] for q, ok in real.gate_is_first.items() if not ok}
    assert not displaced, (
        "G3: the tracker_egress_verdict call is no longer the first executable statement of:\n"
        + "\n".join(f"    {q}: first executable statement is `{s}`" for q, s in sorted(displaced.items()))
        + "\nA docstring is tolerated ahead of the gate; nothing else is -- not a log line, not a "
        "local assignment, and not a `_require_egress`-style helper (a helper satisfies 'first "
        "statement' while pinning nothing)."
    )

    control = analyze_gate_placement(_G3_POSITIVE_CONTROL)
    assert control.gate_is_first == {"LocalTrackerService.sync_pull": True}, (
        f"G3 POSITIVE CONTROL FAILED: docstring -> gate -> rest must PASS, got {control.gate_is_first}. "
        "The analyzer is rejecting a leading docstring, which would red correct code."
    )
    print("[G3] positive control (docstring -> gate -> rest): PASSES")

    killed = 0
    fourth = analyze_gate_placement(_G3_MUTANT_FOURTH_CALLER)
    added = fourth.callers - control.callers
    assert len(added) == 1, (  # golden-count: cardinality-is-contract
        f"G3 MUTANT MISBUILT (fourth caller): expected exactly one caller added to the control, "
        f"got added={sorted(added)} (control {sorted(control.callers)}, mutant {sorted(fourth.callers)})."
    )
    # The consequence for the real guard: fold the mutant's delta onto the real caller set.
    assert (real.callers | added) != EXPECTED_BUILD_ENGINE_CALLERS, f"G3 MUTANT SURVIVED (fourth caller): {sorted(added)} was already an expected caller"
    killed += 1
    print(f"[G3] mutant killed (extra caller): control {len(control.callers)} caller(s) -> mutant {len(fourth.callers)}, added {sorted(added)}")

    placement_mutants = (
        ("statement before gate", _G3_MUTANT_STATEMENT_BEFORE_GATE),
        ("_require_egress helper stands in", _G3_MUTANT_HELPER_STANDS_IN),
        ("gate nested as an ARGUMENT, behind a credential-store read", _G3_MUTANT_GATE_NESTED_AS_ARGUMENT),
        ("gate inside a conditional, therefore skippable", _G3_MUTANT_GATE_INSIDE_CONDITIONAL),
    )
    for label, mutant_source in placement_mutants:
        mutant = analyze_gate_placement(mutant_source)
        # Attributable: the control (same method, gate leading) is True; only the mutation flips it.
        assert control.gate_is_first == {"LocalTrackerService.sync_pull": True}, "G3 control regressed mid-test"
        assert mutant.gate_is_first == {"LocalTrackerService.sync_pull": False}, f"G3 MUTANT SURVIVED ({label}): {mutant.gate_is_first}"
        killed += 1
        print(f"[G3] mutant killed ({label}): control's first statement is the gate; mutant's is `{mutant.first_statement['LocalTrackerService.sync_pull']}`")
    print(f"[G3] KILLED-PIN COUNT: {killed}/5")


# ===========================================================================
# T040 / T041 -- G4 and G5: the call-site census and the per-site polarity mapping
# ===========================================================================

EXPECTED_ENCLOSING_FUNCTIONS = frozenset(
    {
        "LocalTrackerService.sync_pull",
        "LocalTrackerService.sync_push",
        "LocalTrackerService.sync_run",
        "SaaSTrackerClient._request",
        "_check_sync_readiness",
        "_render_tracker_egress",
    }
)
EXPECTED_ENCLOSING_COUNT = 6
#: Seven, not six: ``sync doctor``'s renderer calls the verdict **twice**, once per destination
#: row. Both numbers are asserted separately and both are exact. An implementer who reads "six
#: call sites" as "six call expressions" writes a renderer that loops over ``EgressDestination``,
#: which G5 then rejects because the loop variable is an ``ast.Name``, not a literal member.
#:
#: **Landing-pass audited chokepoint (2026-08-10, PR #3135, HIGH-1 / #3108 follow-up):**
#: ``cli/commands/tracker.py::_check_sync_readiness`` is the sixth enclosing function and
#: contributes the seventh call expression. Before this call site existed, the hosted
#: (SaaS-backed) branch of ``_check_sync_readiness`` called
#: ``_check_readiness(..., probe_reachability=True)`` as its first act -- which, once auth and
#: host-config both resolve, issues a real network HEAD probe
#: (``saas/readiness.py:_probe_reachability``) *before* ``SaaSTrackerClient._request``'s own
#: ``tracker_egress_verdict`` gate (this file's own G3 subject) ever ran. A refusing project's
#: hosted-egress verdict is now consulted here too, ahead of that probe, so "refusal precedes
#: any HTTP attempt" holds at the CLI's own pre-flight and not only one layer below it. This is
#: precisely the kind of new call site this guard exists to catch when it is *not* audited --
#: it is audited (this comment, plus the guard's own re-pinned census), so the guard's job here
#: is only to keep the numbers honest, not to raise an alarm.
EXPECTED_CALL_EXPRESSION_COUNT = 7

#: The load-bearing half of G5 (its set-equality clause carries almost nothing on its own, because
#: the doctor renderer supplies both members by itself). Per site, the **sorted members actually
#: passed** -- so the renderer's "exactly one of each" is pinned, not merely "both appear".
EXPECTED_PER_SITE_DESTINATIONS: dict[str, tuple[str, ...]] = {
    "LocalTrackerService.sync_pull": ("LOCAL_SUBPROCESS",),
    "LocalTrackerService.sync_push": ("LOCAL_SUBPROCESS",),
    "LocalTrackerService.sync_run": ("LOCAL_SUBPROCESS",),
    "SaaSTrackerClient._request": ("HOSTED_SERVICE",),
    "_check_sync_readiness": ("HOSTED_SERVICE",),
    "_render_tracker_egress": ("HOSTED_SERVICE", "LOCAL_SUBPROCESS"),
}
EXPECTED_LITERAL_MEMBERS = frozenset({"LOCAL_SUBPROCESS", "HOSTED_SERVICE"})

_ALIAS_HINT = (
    "If `EgressDestination` was imported under an alias, this is a FALSE RED -- import it under "
    "its own name (FR-015 G5, data-model.md section 2). "
)


@dataclass(frozen=True)
class DestinationArg:
    """How one call site supplies its ``destination`` argument."""

    #: ``"literal_member"`` | ``"name"`` | ``"call"`` | ``"other"`` | ``"missing"``
    kind: str
    member: str | None
    source: str


def _classify_destination_arg(node: ast.Call) -> DestinationArg:
    """Classify a call's ``destination`` argument.

    ``destination`` is **keyword-only**, so it is always in ``node.keywords``; a positional
    ``destination`` is a ``mypy`` error before it is a guard error, and is reported as ``missing``.

    A literal member is an ``ast.Attribute`` whose value **resolves to the name
    ``EgressDestination``** -- which accepts ``EgressDestination.X`` and the module-qualified
    ``ev.EgressDestination.X`` (the enum reached under its own name through a module), and rejects
    an aliased ``ED.X``. See module docstring (e): rejecting the alias is the documented false red;
    accepting the module-qualified form is what makes G5's third mutant kill via the **per-site
    mapping** clause rather than by an incidental mis-classification of its argument.

    An ``ast.Name`` is what a loop variable or a config-derived local looks like. An ``ast.Call``
    is what a derivation looks like. Neither is acceptable.
    """
    keyword = next((k for k in node.keywords if k.arg == "destination"), None)
    if keyword is None:
        return DestinationArg("missing", None, "<no destination= keyword>")
    value = keyword.value
    source = ast.unparse(value)
    if isinstance(value, ast.Attribute) and _resolves_to_destination_enum(value.value):
        return DestinationArg("literal_member", value.attr, source)
    if isinstance(value, ast.Name):
        return DestinationArg("name", None, source)
    if isinstance(value, ast.Call):
        return DestinationArg("call", None, source)
    return DestinationArg("other", None, source)


def _resolves_to_destination_enum(node: ast.expr) -> bool:
    """Whether *node* names ``EgressDestination`` -- bare, or reached through a module."""
    if isinstance(node, ast.Name):
        return node.id == DESTINATION_ENUM
    if isinstance(node, ast.Attribute):
        return node.attr == DESTINATION_ENUM
    return False


def _per_site_destinations(findings: CallFindings) -> dict[str, tuple[str, ...]]:
    """Map each call site's qualname to the sorted literal members it passes."""
    mapping: dict[str, list[str]] = {}
    for call in findings.calls:
        arg = _classify_destination_arg(call.node)
        mapping.setdefault(call.qualname, []).append(arg.member or f"<non-literal:{arg.kind}>")
    return {qualname: tuple(sorted(members)) for qualname, members in mapping.items()}


def _non_literal_sites(findings: CallFindings) -> list[str]:
    """Every call whose ``destination`` argument is not a literal enum member."""
    out: list[str] = []
    for call in findings.calls:
        arg = _classify_destination_arg(call.node)
        if arg.kind != "literal_member":
            out.append(f"{call} -> destination={arg.source} ({arg.kind})")
    return out


# --- the six shared mutants -------------------------------------------------

_MUTANT_ADDED_CONFIG_DERIVED = '''
from specify_cli.tracker.egress_verdict import tracker_egress_verdict, EgressDestination

def _dest_from_config(root):
    return EgressDestination.LOCAL_SUBPROCESS

def newly_added_ungated_path(root):
    dest = _dest_from_config(root)
    return tracker_egress_verdict(root, destination=dest)
'''

_MUTANT_ADDED_SWAPPED_LITERAL = '''
from specify_cli.tracker.egress_verdict import tracker_egress_verdict, EgressDestination

def sync_sideways_local_path(root):
    """A new LOCAL-side function passing the HOSTED literal -- wrong polarity for its position."""
    return tracker_egress_verdict(root, destination=EgressDestination.HOSTED_SERVICE)
'''

_MUTANT_ADDED_MODULE_QUALIFIED = '''
from specify_cli.tracker import egress_verdict as ev

def newly_added_ungated_path(root):
    return ev.tracker_egress_verdict(root, destination=ev.EgressDestination.LOCAL_SUBPROCESS)
'''

#: G5's mutant (ii): the two literals swapped **IN PLACE** -- no site added, no site removed.
#: This is the exact defect that would reopen `#3030`: ``_request`` (which sends to spec-kitty's
#: own hosted service) evaluated under the LOCAL polarity, where ``tracker.egress: permitted``
#: **grants independently of Channel 1**. It moves **no count**, which is precisely why G4's third
#: mutant had to become an *added* site instead. Two guards, two different mutants, one shared
#: literal-swap idea -- do not copy one into the other.
_MUTANT_INPLACE_SWAP = '''
from specify_cli.tracker.egress_verdict import tracker_egress_verdict, EgressDestination

class LocalTrackerService:
    def sync_pull(self, *, limit=100):
        return tracker_egress_verdict(self._repo_root, destination=EgressDestination.HOSTED_SERVICE)

class SaaSTrackerClient:
    def _request(self, method, path):
        return tracker_egress_verdict(self._project_root, destination=EgressDestination.LOCAL_SUBPROCESS)
'''

_UNSWAPPED_CONTROL = '''
from specify_cli.tracker.egress_verdict import tracker_egress_verdict, EgressDestination

class LocalTrackerService:
    def sync_pull(self, *, limit=100):
        return tracker_egress_verdict(self._repo_root, destination=EgressDestination.LOCAL_SUBPROCESS)

class SaaSTrackerClient:
    def _request(self, method, path):
        return tracker_egress_verdict(self._project_root, destination=EgressDestination.HOSTED_SERVICE)
'''


@cache
def _real_verdict_calls() -> CallFindings:
    """The real ``src/`` scan shared by G4 and G5, computed once.

    Cached only to avoid re-walking 1200 modules twice; the result is never mutated by a caller.
    """
    return analyze_calls_in_tree(SRC_ROOT, VERDICT_FN)


def test_g4_exactly_six_enclosing_functions_and_seven_call_expressions() -> None:
    """G4 -- **two** exact assertions, never collapsed into one and never ``<=``.

    Exactly **6** enclosing functions (``sync_pull``, ``sync_push``, ``sync_run``,
    ``SaaSTrackerClient._request``, ``_check_sync_readiness``, and ``sync doctor``'s renderer)
    and exactly **7** call expressions (the renderer calls twice, once per destination row).

    Originally "exactly 5 / exactly 6" (FR-015); re-pinned to 6/7 at the 2026-08-10 landing pass
    (PR #3135, HIGH-1 / #3108 follow-up) when ``_check_sync_readiness`` gained its own audited
    ``tracker_egress_verdict`` call site -- see :data:`EXPECTED_CALL_EXPRESSION_COUNT`'s own
    comment for why.

    A rejected draft of this Mission said "exactly three" while its own requirements demanded
    three local sites, a fourth and a fifth -- arithmetically impossible, and repeated five times.
    Both numbers here were re-derived from the tree, not transcribed.

    ``<=`` is not a weaker form of this guard. ``<=`` **passes on a zero-call scan**, which is
    exactly what a sibling Mission's file move produces.
    """
    real = _real_verdict_calls()
    _announce(
        "G4",
        real.input_count,
        enclosing_functions=len(real.enclosing),
        call_expressions=real.call_count,
        membership=sorted(real.enclosing),
        func_forms=sorted({call.func_form for call in real.calls}),
    )
    bundle_b = (
        "\nIf Bundle B moved these call sites, update this membership set -- do not let it fall to zero."
    )
    assert real.enclosing == EXPECTED_ENCLOSING_FUNCTIONS, (
        f"G4: the enclosing-function set changed.\n"
        f"  expected ({EXPECTED_ENCLOSING_COUNT}): {sorted(EXPECTED_ENCLOSING_FUNCTIONS)}\n"
        f"  found ({len(real.enclosing)}):    {sorted(real.enclosing)}\n"
        f"  symmetric difference: {sorted(real.enclosing ^ EXPECTED_ENCLOSING_FUNCTIONS)}\n"
        f"  call expressions: {real.call_count} (expected {EXPECTED_CALL_EXPRESSION_COUNT})\n"
        f"{real.describe()}{bundle_b}"
    )
    assert len(real.enclosing) == EXPECTED_ENCLOSING_COUNT, f"G4: expected {EXPECTED_ENCLOSING_COUNT} enclosing functions, found {len(real.enclosing)}{bundle_b}"
    assert real.call_count == EXPECTED_CALL_EXPRESSION_COUNT, (
        f"G4: expected exactly {EXPECTED_CALL_EXPRESSION_COUNT} call expressions "
        f"(the doctor renderer contributes two, one per destination row), found {real.call_count}:\n"
        f"{real.describe()}{bundle_b}"
    )

    # Every kill below is measured as a DELTA against a control that is itself correctly shaped,
    # then folded onto the real tree's findings. Asserting only "the synthetic mutant's set differs
    # from the expected set" would be no evidence at all -- the two-site control differs from the
    # expected set as well, so such a 'kill' fires whether or not the mutant is present. That is
    # recorded mutation-lie #1 (the mutant is a no-op and all-green reads as "your pin is fine").
    control = analyze_calls_in_source(_UNSWAPPED_CONTROL, VERDICT_FN, module="<g4-control>")
    assert control.call_count == 2 and len(control.enclosing) == 2, (  # golden-count: cardinality-is-contract
        f"G4 MUTANT HARNESS MISBUILT: control is {len(control.enclosing)}/{control.call_count}, expected 2/2"
    )

    killed = 0
    for label, mutant_source in (
        ("added site, config-derived destination", _MUTANT_ADDED_CONFIG_DERIVED),
        ("ADDED sixth site with swapped literal", _MUTANT_ADDED_SWAPPED_LITERAL),
        ("added sixth site, MODULE-QUALIFIED", _MUTANT_ADDED_MODULE_QUALIFIED),
    ):
        combined = analyze_calls_in_source(_UNSWAPPED_CONTROL + mutant_source, VERDICT_FN, module="<g4-mutant>")
        added = combined.enclosing - control.enclosing
        delta_calls = combined.call_count - control.call_count
        assert len(added) == 1 and delta_calls == 1, (  # golden-count: cardinality-is-contract
            f"G4 MUTANT MISBUILT ({label}): expected exactly one added enclosing function and one "
            f"added call expression against the control, got added={sorted(added)} delta_calls={delta_calls}."
        )
        # Fold the measured delta onto the REAL tree: this is what G4 would see with the mutant present.
        assert (real.enclosing | added) != EXPECTED_ENCLOSING_FUNCTIONS, f"G4 MUTANT SURVIVED ({label}) on membership: {sorted(added)} was already expected"
        assert real.call_count + delta_calls != EXPECTED_CALL_EXPRESSION_COUNT, f"G4 MUTANT SURVIVED ({label}) on call count"
        killed += 1
        forms = sorted({c.func_form for c in combined.calls})
        print(
            f"[G4] mutant killed ({label}): control 2/2 -> mutant {len(combined.enclosing)}/{combined.call_count}; "
            f"folded onto src/ that is {len(real.enclosing) + 1} enclosing / {real.call_count + delta_calls} calls "
            f"vs expected {EXPECTED_ENCLOSING_COUNT}/{EXPECTED_CALL_EXPRESSION_COUNT}; forms={forms}"
        )
    print(f"[G4] KILLED-PIN COUNT: {killed}/3")


def test_g4_inplace_literal_swap_does_NOT_move_its_counts() -> None:
    """The correction to SC-017's shared mutant list, asserted rather than merely written down.

    SC-017 describes G4's and G5's three mutants with one shared list whose item (ii) is *"a call
    site with the two literals swapped"*. **That mutant kills G5 and cannot kill G4.** An in-place
    swap changes no enclosing function and no call-expression count, so G4 -- which asserts exactly
    those two numbers -- passes against it.

    This test pins that fact so nobody "fixes" G4's third mutant back into a permutation and
    reports 3/3 while one of the three kills is imaginary. G4's third mutant is therefore an
    **ADDED** site with a swapped literal; G5's stays the in-place swap.
    """
    control = analyze_calls_in_source(_UNSWAPPED_CONTROL, VERDICT_FN, module="<control>")
    swapped = analyze_calls_in_source(_MUTANT_INPLACE_SWAP, VERDICT_FN, module="<swapped>")
    _announce(
        "G4-correction",
        control.input_count + swapped.input_count,
        control=f"{len(control.enclosing)}/{control.call_count}",
        swapped=f"{len(swapped.enclosing)}/{swapped.call_count}",
    )
    assert control.enclosing == swapped.enclosing, "the in-place swap was expected to move no enclosing function"
    assert control.call_count == swapped.call_count, "the in-place swap was expected to move no call count"
    print("[G4-correction] confirmed: an in-place literal swap moves NEITHER of G4's counts -- G4 cannot kill it; G5 does.")


def test_g5_every_destination_is_a_literal_member_with_the_per_site_mapping_intact() -> None:
    """G5 -- the P0 guard. Its clauses, in the order of their worth.

    **1. The per-site mapping (load-bearing).** ``SaaSTrackerClient._request`` always
    ``HOSTED_SERVICE``; the three local sites always ``LOCAL_SUBPROCESS``; the doctor renderer
    exactly one of each. *This is the clause whose mutant must kill.*

    **2. The node-shape clause.** Every ``destination`` argument is an ``ast.Attribute`` on
    ``EgressDestination``. No ``ast.Name`` (a loop variable or a config-derived local), no
    ``ast.Call`` (a derivation).

    **3. The set-equality clause.** Kept, but record honestly that *it carries almost nothing on
    its own, because the doctor renderer supplies both members by itself.*

    Why this is P0: ``TrackerService._resolve_saas_backend_for_provider`` overrides the on-disk
    provider **in memory** and never rewrites the file, so three operator-reachable commands drive
    the **hosted** transport from a repo whose committed config says ``beads``. A config-derived
    polarity would therefore read ``beads``, apply the local (two-way) polarity, and turn
    ``tracker.egress: permitted`` into an **affirmative grant to spec-kitty's hosted service with
    Channel 1 absent** -- for exactly the operator this design exists to serve, the one who
    refuses hosted sync and writes ``permitted`` to keep ``beads`` alive.
    """
    real = _real_verdict_calls()
    per_site = _per_site_destinations(real)
    members = {m for members in per_site.values() for m in members}
    _announce("G5", real.input_count, per_site_mapping=per_site, literal_members=sorted(members))

    non_literal = _non_literal_sites(real)
    assert not non_literal, _ALIAS_HINT + "G5: a destination argument is not a literal EgressDestination member:\n" + "\n".join(f"    {s}" for s in non_literal)

    assert per_site == EXPECTED_PER_SITE_DESTINATIONS, (
        _ALIAS_HINT
        + "G5: the PER-SITE destination mapping changed -- this is the clause that carries G5.\n"
        + f"  expected: {EXPECTED_PER_SITE_DESTINATIONS}\n"
        + f"  found:    {per_site}\n"
        + "A site evaluated under the wrong polarity is the defect that reopens #3030."
    )
    assert members == EXPECTED_LITERAL_MEMBERS, f"G5: literal member set is {sorted(members)}, expected {sorted(EXPECTED_LITERAL_MEMBERS)}"
    print("[G5] positive control: the real src/ tree PASSES all three clauses")

    # As with G4, each kill is a DELTA against a correctly-shaped control, then folded onto the real
    # mapping -- and each is additionally attributed to the specific clause it is supposed to break,
    # so a mutant cannot be recorded as killed by the wrong clause (recorded mutation-lie #2).
    control = analyze_calls_in_source(_UNSWAPPED_CONTROL, VERDICT_FN, module="<g5-control>")
    control_map = _per_site_destinations(control)
    assert control_map == {"LocalTrackerService.sync_pull": ("LOCAL_SUBPROCESS",), "SaaSTrackerClient._request": ("HOSTED_SERVICE",)}, (
        f"G5 MUTANT HARNESS MISBUILT: the control must itself have the correct per-site polarity, got {control_map}"
    )
    assert not _non_literal_sites(control), "G5 MUTANT HARNESS MISBUILT: the control must have no non-literal destination"

    killed = 0

    # (i) node-shape clause: a destination bound from a config read is an ast.Name.
    mutant_i = analyze_calls_in_source(_UNSWAPPED_CONTROL + _MUTANT_ADDED_CONFIG_DERIVED, VERDICT_FN, module="<g5-mutant-i>")
    non_literal = _non_literal_sites(mutant_i)
    assert len(non_literal) == 1, (  # golden-count: cardinality-is-contract
        f"G5 MUTANT SURVIVED (config-derived name): control had 0 non-literal sites, mutant has {non_literal}"
    )
    assert "(name)" in non_literal[0], f"G5 mutant (i) killed by the wrong clause -- expected a Name node, got {non_literal[0]}"
    killed += 1
    print(f"[G5] mutant killed (added site, config-derived name) via CLAUSE 2 node-shape: control had 0 non-literal sites, mutant has {non_literal}")

    # (ii) per-site mapping clause: the two literals swapped IN PLACE, moving no count.
    mutant_ii = analyze_calls_in_source(_MUTANT_INPLACE_SWAP, VERDICT_FN, module="<g5-mutant-ii>")
    swapped_map = _per_site_destinations(mutant_ii)
    assert len(swapped_map) == len(control_map) and swapped_map != control_map, f"G5 MUTANT SURVIVED (in-place swap): {swapped_map}"
    folded = {**EXPECTED_PER_SITE_DESTINATIONS, **swapped_map}
    assert folded != EXPECTED_PER_SITE_DESTINATIONS, "G5 MUTANT SURVIVED (in-place swap) when folded onto the real mapping"
    assert not _non_literal_sites(mutant_ii), "G5 mutant (ii) killed by the wrong clause -- it must break the mapping, not the node shape"
    killed += 1
    print(f"[G5] mutant killed (IN-PLACE literal swap) via CLAUSE 1 per-site mapping (the clause that carries G5): control {control_map} -> mutant {swapped_map}")

    # (iii) the blind spot: a sixth site the matcher must see at all before any clause can fire.
    mutant_iii = analyze_calls_in_source(_UNSWAPPED_CONTROL + _MUTANT_ADDED_MODULE_QUALIFIED, VERDICT_FN, module="<g5-mutant-iii>")
    qualified_map = _per_site_destinations(mutant_iii)
    added_sites = set(qualified_map) - set(control_map)
    assert len(added_sites) == 1, f"G5 MUTANT MISBUILT (module-qualified): added {sorted(added_sites)}"  # golden-count: cardinality-is-contract
    assert any(call.func_form == "Attribute" for call in mutant_iii.calls), (
        "G5 MUTANT SURVIVED (module-qualified): the matcher never resolved the Attribute-form call"
    )
    folded_iii = {**EXPECTED_PER_SITE_DESTINATIONS, **{q: qualified_map[q] for q in added_sites}}
    assert folded_iii != EXPECTED_PER_SITE_DESTINATIONS, "G5 MUTANT SURVIVED (module-qualified) when folded onto the real mapping"
    killed += 1
    print(
        "[G5] mutant killed (added sixth site, MODULE-QUALIFIED) via CLAUSE 1, reached only "
        f"because the matcher resolves Attribute func nodes: added {sorted(added_sites)}"
    )
    print(f"[G5] KILLED-PIN COUNT: {killed}/3")


def test_g5_module_qualified_mutant_observed_red_then_green() -> None:
    """**The specific pin.** The module-qualified mutant, observed red under an ``ast.Name``-only
    matcher and green under this file's matcher -- same input, two matchers, never a source edit.

    This is the fifth measured mechanism for producing a green suite with no gate: a sixth,
    ungated call site written ``ev.tracker_egress_verdict(...)`` passed both G4 and G5 with the
    input count merely *rising*, while killing every other specified mutant. The blind matcher's
    2/2 was not evidence of health; it was evidence that both of its mutants shared its blind spot.
    """
    source = _UNSWAPPED_CONTROL + _MUTANT_ADDED_MODULE_QUALIFIED
    tree = ast.parse(source)
    blind = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and _name_only_callee_trailing_name(n) == VERDICT_FN]
    seeing = analyze_calls_in_source(source, VERDICT_FN, module="<red-then-green>")
    _announce("G5-red-then-green", seeing.input_count, ast_Name_only_matcher_sees=len(blind), both_forms_matcher_sees=seeing.call_count)

    assert len(blind) == 2, (  # golden-count: cardinality-is-contract
        f"the ast.Name-only matcher was expected to miss the qualified site and see 2, saw {len(blind)}"
    )
    assert seeing.call_count == 3, f"the both-forms matcher was expected to see all 3, saw {seeing.call_count}"

    blind_map = {q: v for q, v in _per_site_destinations(seeing).items() if q in {c.qualname for c in seeing.calls if c.func_form == "Name"}}
    full_map = _per_site_destinations(seeing)
    print(f"[G5-red-then-green] RED  (ast.Name-only): sees 2 calls, mapping {blind_map} -- the ungated qualified site is INVISIBLE, guard reports healthy")
    print(f"[G5-red-then-green] GREEN(both forms)   : sees 3 calls, mapping {full_map} -- the ungated qualified site is CAUGHT")
    assert full_map != blind_map, "the two matchers produced the same mapping -- the blind spot is not demonstrated"
    assert any(call.func_form == "Attribute" for call in seeing.calls), "no Attribute-form call was resolved; the matcher is blind"


# ===========================================================================
# T042 -- G6: the verdict body never reads the provider
# ===========================================================================

_VERDICT_PATH = SRC_ROOT / "specify_cli" / "tracker" / "egress_verdict.py"
_FORBIDDEN_BODY_NAMES = frozenset({"provider", "LOCAL_PROVIDERS", "SAAS_PROVIDERS"})


@dataclass(frozen=True)
class Offence:
    """One forbidden provider reference found in the verdict module."""

    node_type: str
    name: str
    lineno: int

    def __str__(self) -> str:
        return f"{self.node_type} `{self.name}` at line {self.lineno}"


@dataclass
class BodyFindings:
    """What G6's analyzer found. The expected set is EMPTY, so ``input_count`` is the whole proof."""

    #: **AST nodes scanned.** An empty-set assertion over zero nodes is exactly the vacuity the
    #: input-count rule exists to prevent, and G6 is the guard where that risk is real.
    input_count: int
    byte_length: int
    offences: list[Offence]
    #: The specific form the requirement words: ``load_tracker_config(...).provider``, asserted
    #: explicitly as well as via the general ``.provider`` rule, so the wording itself is pinned.
    chained_config_reads: list[Offence]


def _offence_for(node: ast.AST) -> Offence | None:
    """Classify one AST node as a forbidden provider reference, or ``None``.

    Deliberately broader than "a ``Name`` or an ``Attribute``": an ``import`` of
    ``SAAS_PROVIDERS`` (an ``ast.alias``), a parameter named ``provider`` (an ``ast.arg``) and a
    ``provider=`` keyword argument are all references, and each is a way to reintroduce the read.
    """
    if isinstance(node, ast.Name) and node.id in _FORBIDDEN_BODY_NAMES:
        return Offence("Name", node.id, node.lineno)
    if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_BODY_NAMES:
        return Offence("Attribute", node.attr, node.lineno)
    if isinstance(node, ast.alias) and (node.name in _FORBIDDEN_BODY_NAMES or (node.asname or "") in _FORBIDDEN_BODY_NAMES):
        return Offence("import alias", node.name, getattr(node, "lineno", 0))
    if isinstance(node, ast.arg) and node.arg in _FORBIDDEN_BODY_NAMES:
        return Offence("parameter", node.arg, node.lineno)
    if isinstance(node, ast.keyword) and node.arg in _FORBIDDEN_BODY_NAMES:
        return Offence("keyword argument", node.arg or "", getattr(node, "lineno", 0))
    return _string_indirected_offence(node)


def _string_indirected_offence(node: ast.AST) -> Offence | None:
    """Provider reads that reach the attribute through a **string**, not an identifier (LOW-3).

    ``getattr(cfg, "provider")`` and ``cfg["provider"]`` both re-derive the destination from the
    on-disk provider while producing no ``ast.Attribute`` named ``provider`` at all, so the
    identifier-based clauses above score them zero. Closing them costs two checks.

    What remains open, and is recorded rather than papered over: a **renamed local**
    (``key = "provi" + "der"; getattr(cfg, key)``) is undecidable without dataflow analysis. See
    the module docstring's limits section.
    """
    if (
        isinstance(node, ast.Call)
        and _callee_trailing_name(node) == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value in _FORBIDDEN_BODY_NAMES
    ):
        return Offence("getattr(..., <str>)", str(node.args[1].value), node.lineno)
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value in _FORBIDDEN_BODY_NAMES:
        return Offence("subscript [<str>]", str(node.slice.value), node.lineno)
    return None


def analyze_verdict_body(source: str) -> BodyFindings:
    """Source-text analyzer: every forbidden provider reference in the verdict module."""
    tree = ast.parse(source)
    offences: list[Offence] = []
    chained: list[Offence] = []
    nodes = 0
    for node in ast.walk(tree):
        nodes += 1
        offence = _offence_for(node)
        if offence is not None:
            offences.append(offence)
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "provider"
            and isinstance(node.value, ast.Call)
            and _callee_trailing_name(node.value) == "load_tracker_config"
        ):
            chained.append(Offence("load_tracker_config(...).provider", "provider", node.lineno))
    return BodyFindings(input_count=nodes, byte_length=len(source.encode("utf-8")), offences=offences, chained_config_reads=chained)


_G6_MUTANT_PROVIDER_READ = '''
from specify_cli.tracker.config import LOCAL_PROVIDERS, load_tracker_config

def tracker_egress_verdict(root, *, destination):
    cfg = load_tracker_config(root)
    if cfg.provider in LOCAL_PROVIDERS:
        destination = EgressDestination.LOCAL_SUBPROCESS
    return destination
'''

_G6_MUTANT_CHAINED_READ = '''
from specify_cli.tracker.config import load_tracker_config

def tracker_egress_verdict(root, *, destination):
    if load_tracker_config(root).provider in ("beads", "fp"):
        destination = EgressDestination.LOCAL_SUBPROCESS
    return destination
'''

#: Review LOW-3: the same body-side derivation reached through a **string** rather than an
#: identifier. Neither shape produces an ``ast.Attribute`` named ``provider``, so the
#: identifier-based clauses scored both zero before this was closed.
_G6_MUTANT_STRING_INDIRECTED_READS = '''
from specify_cli.tracker.config import load_tracker_config

def tracker_egress_verdict(root, *, destination):
    cfg = load_tracker_config(root)
    if getattr(cfg, "provider") in ("beads", "fp"):
        destination = EgressDestination.LOCAL_SUBPROCESS
    if cfg.to_dict()["provider"] == "jira":
        destination = EgressDestination.HOSTED_SERVICE
    return destination
'''


def test_g6_verdict_body_never_reads_the_provider() -> None:
    """G6 -- the body, not just the call sites. **Expected set empty; the input count is the proof.**

    G5 guards *where the destination comes from*; the original defect lived **inside** the verdict.
    A future change reading *"if the on-disk provider is local, treat this as local regardless of
    the argument"* passes G5 at all six call expressions and would be caught by exactly one
    behavioural test.

    Detection signal for that defect: **G6 red; or SC-005a red with G5 green -- the signature of a
    body-side derivation.**

    Because the expected set is empty, this assertion is worthless without its input count: an
    empty-set assertion over zero nodes is precisely the vacuity the rule exists to prevent. The
    AST-node count and the file's byte length are both printed.
    """
    source = _VERDICT_PATH.read_text(encoding="utf-8")
    real = analyze_verdict_body(source)
    _announce(
        "G6",
        real.input_count,
        note="input count is AST NODES SCANNED (expected offence set is empty)",
        byte_length=real.byte_length,
        offences_found=len(real.offences),
    )
    assert real.byte_length > 0, "G6 read an empty file -- vacuous"
    assert real.offences == [], (
        "G6: the verdict body references the provider again -- a body-side derivation ignores the "
        "caller's destination and reopens the P0 boundary:\n"
        + "\n".join(f"    {o}" for o in real.offences)
    )
    assert real.chained_config_reads == [], "G6: a load_tracker_config(...).provider read is present:\n" + "\n".join(f"    {o}" for o in real.chained_config_reads)
    print(f"[G6] positive control: the real egress_verdict.py PASSES with {real.input_count} AST nodes scanned and 0 offences")

    mutant = analyze_verdict_body(_G6_MUTANT_PROVIDER_READ)
    names = {o.name for o in mutant.offences}
    assert {"provider", "LOCAL_PROVIDERS"} <= names, f"G6 MUTANT SURVIVED: offences {sorted(names)} did not name both `provider` and `LOCAL_PROVIDERS`"
    assert any(o.node_type == "Attribute" and o.name == "provider" for o in mutant.offences), "G6 mutant did not report the `.provider` attribute access"
    print(f"[G6] mutant killed (reintroduced provider read): {len(mutant.offences)} offences, naming {sorted(names)}")

    chained = analyze_verdict_body(_G6_MUTANT_CHAINED_READ)
    assert chained.chained_config_reads, "G6's explicit load_tracker_config(...).provider clause did not fire on the chained form"

    indirect = analyze_verdict_body(_G6_MUTANT_STRING_INDIRECTED_READS)
    kinds = {o.node_type for o in indirect.offences}
    assert "getattr(..., <str>)" in kinds, f"G6 MUTANT SURVIVED (getattr indirection): offence kinds {sorted(kinds)}"
    assert "subscript [<str>]" in kinds, f"G6 MUTANT SURVIVED (subscript indirection): offence kinds {sorted(kinds)}"
    print(f"[G6] mutant killed (string-indirected provider reads, LOW-3): {len(indirect.offences)} offences, kinds {sorted(kinds)}")
    print(f"[G6] KILLED-PIN COUNT: 2/2  (plus the requirement's own chained form pinned separately: {chained.chained_config_reads[0]})")


# ===========================================================================
# G7 -- routed here from WP02's review: the polarity map must be exhaustive
# ===========================================================================


@dataclass
class PolarityFindings:
    """What G7's analyzer found. ``input_count`` is the number of (value, destination) cells checked."""

    input_count: int
    uncovered: set[tuple[str, str]]
    legal_values: frozenset[str]


def analyze_polarity_exhaustiveness(legal_values: frozenset[str], join_keys: set[tuple[str, EgressDestination]]) -> PolarityFindings:
    """Every legal Channel-2 value must have a mapped outcome at **every** destination.

    Written as a pure function over its two inputs so the mutant run can pass a *third* legal value
    without touching ``tracker/config.py`` -- no source edit, no ``sys.path`` manipulation.
    """
    destinations = tuple(EgressDestination)
    uncovered = {
        (value, dest.name)
        for value in legal_values
        for dest in destinations
        if (value, dest) not in join_keys
    }
    return PolarityFindings(input_count=len(legal_values) * len(destinations), uncovered=uncovered, legal_values=legal_values)


def test_g7_polarity_map_is_exhaustive_over_the_legal_channel2_values() -> None:
    """G7 (routed from WP02's review; **not** one of FR-015's six) -- WP03's polarity mapping is
    exhaustive over ``tracker/config.py``'s ``_EGRESS_LEGAL_VALUES``.

    The exported ``EGRESS_REFUSED`` / ``EGRESS_PERMITTED`` constants close duplicate **spelling**
    -- ``egress_verdict`` and ``TrackerProjectConfig.egress_fault`` cannot disagree about how a
    legal value is written. **They do not close arity.** If a *third* legal value is added to
    ``_EGRESS_LEGAL_VALUES``, ``egress_fault`` immediately reports "not a fault" for it while
    ``_JOIN`` has no branch for it -- a fault that no longer refuses at the reporting surface even
    though the verdict still refuses it. That is a two-site change, and the raw-value mandate rules
    out making it a ``mypy`` exhaustiveness error, so it can only be made to fail loudly here.
    WP03 was told to keep its mapping introspectable for exactly this guard.
    """
    legal = tracker_config._EGRESS_LEGAL_VALUES
    join_keys = set(_JOIN.keys())
    real = analyze_polarity_exhaustiveness(legal, join_keys)
    _announce(
        "G7",
        real.input_count,
        note="input count is (legal value x destination) cells checked",
        legal_values=sorted(legal),
        destinations=[d.name for d in EgressDestination],
        join_cells=len(join_keys),
    )
    assert legal == _LEGAL_CHANNEL2_VALUES, (
        f"G7: egress_verdict._LEGAL_CHANNEL2_VALUES {sorted(_LEGAL_CHANNEL2_VALUES)} has drifted from "
        f"config._EGRESS_LEGAL_VALUES {sorted(legal)} -- the two-site change was made at one site."
    )
    assert not real.uncovered, (
        f"G7: WP03's polarity map is not exhaustive over the legal Channel-2 values.\n"
        f"  unmapped cells: {sorted(real.uncovered)}\n"
        f"A legal-elsewhere-but-unmapped-here value makes `egress_fault` report 'not a fault' while "
        f"_JOIN has no branch for it. Update `_LEGAL_CHANNEL2_VALUES` and `_JOIN` in the same change."
    )

    mutant = analyze_polarity_exhaustiveness(legal | {"deferred"}, join_keys)
    assert mutant.uncovered, "G7 MUTANT SURVIVED: a third legal value left the polarity map with no unmapped cell"
    print(f"[G7] KILLED-PIN COUNT: 1/1  (mutant third legal value 'deferred' left {sorted(mutant.uncovered)} unmapped)")


# ===========================================================================
# G8 -- routed here from WP04's review (MEDIUM-2) and WP01's F7 residual
# ===========================================================================

#: Exact census, pinned by ``<relpath>::<qualname>`` -- **never by line number**, which benign
#: edits move. Measured: exactly three, all in the one file whose docstring documents the escape
#: hatch ("we mock `_build_engine` to avoid needing the spec_kitty_tracker package").
EXPECTED_BUILD_ENGINE_PATCH_SITES = frozenset(
    {
        "sync/tracker/test_local_service.py::TestSyncOperations.test_sync_pull_delegates_to_connector",
        "sync/tracker/test_local_service.py::TestSyncOperations.test_sync_push_delegates_to_connector",
        "sync/tracker/test_local_service.py::TestSyncOperations.test_sync_run_delegates_to_connector",
    }
)


def _is_patch_call(node: ast.Call) -> bool:
    """Whether *node* is a monkeypatch/mock patching call, matched by **trailing attribute name**.

    This is WP01's ``_iter_patch_call_sites`` with its F7 residual closed. That matcher requires
    the base of a ``patch``/``patch.object`` call to be a bare ``ast.Name``, so it is blind to
    ``mock.patch``, ``mock.patch.object``, ``mocker.patch`` and ``unittest.mock.patch``. Measured
    at the time of writing: **31 such occurrences already under ``tests/``**, none of them touching
    ``_build_engine`` -- so the residual hides nothing today, and this matcher is what keeps that
    true tomorrow.

    ``setattr`` is matched **only** as an attribute access (``monkeypatch.setattr``, ``mp.setattr``).
    A bare ``setattr(obj, name, value)`` is the Python **builtin**, not a fixture; treating it as a
    patch call over-matched by 23 occurrences on the first pass of this matcher and would have made
    the census noisy rather than exact.
    """
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "setattr":
        return True
    if _callee_trailing_name(node) == "patch":
        return True
    return isinstance(func, ast.Attribute) and func.attr == "object" and _callee_trailing_name_of(func.value) == "patch"


def _callee_trailing_name_of(node: ast.expr) -> str | None:
    """Trailing name of an arbitrary expression (``patch`` in ``mock.patch.object``)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _wp01_is_patch_call(node: ast.Call) -> bool:
    """WP01's matcher, reproduced verbatim, used **only** to demonstrate the F7 blind spot."""
    func = node.func
    return (
        (isinstance(func, ast.Attribute) and func.attr == "setattr")
        or (isinstance(func, ast.Attribute) and func.attr == "object" and isinstance(func.value, ast.Name) and func.value.id == "patch")
        or (isinstance(func, ast.Name) and func.id == "patch")
    )


@dataclass
class PatchFindings:
    """What G8's analyzer found. ``input_count`` is test files scanned."""

    input_count: int
    sites: set[str]
    #: Same scan under WP01's matcher, so the report can state what the residual would have missed.
    sites_visible_to_wp01_matcher: set[str]


def _collect_patch_sites(tree: ast.Module, label: str, target: str) -> tuple[set[str], set[str]]:
    """Return (sites seen by the fixed matcher, sites seen by WP01's matcher) for one module."""
    fixed: set[str] = set()
    naive: set[str] = set()

    def walk(node: ast.AST, scopes: list[Scope]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, [*scopes, Scope("class", child.name)])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(child, [*scopes, Scope("func", child.name)])
            else:
                # Order matters for cost, not for correctness: the two matcher predicates are
                # cheap structural checks, while ``ast.unparse`` is expensive and was measured at
                # 69s when run against every Call node under ``tests/``. Only patch-shaped calls
                # are ever unparsed. Both predicates are still evaluated on every Call, so the
                # WP01-blind-spot comparison below is unaffected.
                if isinstance(child, ast.Call):
                    by_fixed = _is_patch_call(child)
                    by_naive = _wp01_is_patch_call(child)
                    if (by_fixed or by_naive) and target in ast.unparse(child):
                        site = f"{label}::{_full_qualname(scopes)}"
                        if by_fixed:
                            fixed.add(site)
                        if by_naive:
                            naive.add(site)
                walk(child, scopes)

    walk(tree, [])
    return fixed, naive


def _full_qualname(scopes: list[Scope]) -> str:
    """Full nested qualname -- unlike :func:`_outermost_qualname`, closures are kept.

    A patch site is attributed to the test that performs it, which is the enclosing method itself.
    """
    return ".".join(scope.name for scope in scopes) or "<module>"


def analyze_patch_sites_in_source(source: str, *, label: str = "<synthetic>", target: str = "_build_engine") -> PatchFindings:
    """Source-text entry point for G8's mutant runs."""
    fixed, naive = _collect_patch_sites(ast.parse(source, filename=label), label, target)
    return PatchFindings(input_count=1, sites=fixed, sites_visible_to_wp01_matcher=naive)


@cache
def _patch_sites_in_tree(root_str: str, target: str) -> PatchFindings:
    """Cached findings (not cached trees -- see :func:`_parse_path`)."""
    root = Path(root_str)
    fixed: set[str] = set()
    naive: set[str] = set()
    scanned = 0
    for path in sorted(root.rglob("*.py")):
        tree = _parse_path(str(path))
        if tree is None:
            continue
        scanned += 1
        f, n = _collect_patch_sites(tree, str(path.relative_to(root)), target)
        fixed |= f
        naive |= n
        del tree  # release this module's AST before parsing the next one
    return PatchFindings(input_count=scanned, sites=fixed, sites_visible_to_wp01_matcher=naive)


def analyze_patch_sites_in_tree(root: Path, *, target: str = "_build_engine") -> PatchFindings:
    """Root-path entry point: census of *target* patch sites across the whole ``tests/`` tree."""
    return _patch_sites_in_tree(str(root), target)


#: The **control**: structurally identical to the mutants below, but patching something that is
#: not ``_build_engine``. Without it, "the mutant produced a site" would not distinguish a matcher
#: that detects ``_build_engine`` patches from one that flags every ``patch.object`` it sees.
_G8_CONTROL_PATCHES_SOMETHING_ELSE = '''
from unittest import mock
from unittest.mock import patch

class TestSomethingNew:
    def test_a_new_shortcut(self):
        with patch.object(svc, "_load_runtime", return_value=(None, None, None)):
            with mock.patch.object(svc, "_resolve_db_path", return_value=None):
                svc.sync_push()
'''

_G8_MUTANT_FOURTH_SITE = '''
from unittest.mock import patch

class TestSomethingNew:
    def test_a_new_shortcut(self):
        with patch.object(svc, "_build_engine", return_value=(None, None)):
            svc.sync_push()
'''

_G8_MUTANT_FOURTH_SITE_MOCK_QUALIFIED = '''
from unittest import mock

class TestSomethingNew:
    def test_a_new_shortcut(self):
        with mock.patch.object(svc, "_build_engine", return_value=(None, None)):
            svc.sync_push()
'''


def test_g8_build_engine_patch_census_over_all_tests_is_exact() -> None:
    """G8 (routed from WP04's review MEDIUM-2 and WP01's F7 residual; **not** one of FR-015's six).

    **What this closes.** WP01's SC-020 pin scans ``tests/**/*_3108*.py``. That glob **excludes**
    ``tests/sync/tracker/test_local_service.py`` -- the very file whose
    ``patch.object(svc, "_build_engine", ...)`` measured *"bind count 0 with 519 tests green"*, and
    which SC-020's own docstring cites as its motivating evidence. Patching out ``_build_engine`` is
    the second of the four measured mechanisms that produce a green suite with no gate. WP01's file
    cannot be edited by this work package, so the coverage is completed here instead.

    **This is a census, not a prohibition.** Those three sites are a documented, legitimate escape
    hatch (that file avoids a hard dependency on ``spec_kitty_tracker``); banning them would red on
    correct committed code. G8 pins them **exactly**, so a *fourth* site anywhere under ``tests/``
    reds -- exact membership, never ``<=``.

    **Pinned by qualname, never by line number** -- a line-number ratchet moves on benign edits and
    teaches the next reader to re-baseline it without thinking.
    """
    real = analyze_patch_sites_in_tree(TESTS_ROOT)
    _announce("G8", real.input_count, note="input count is TEST FILES scanned", patch_sites_found=len(real.sites), sites=sorted(real.sites))
    assert real.sites == EXPECTED_BUILD_ENGINE_PATCH_SITES, (
        f"G8: the _build_engine patch census changed.\n"
        f"  expected ({len(EXPECTED_BUILD_ENGINE_PATCH_SITES)}): {sorted(EXPECTED_BUILD_ENGINE_PATCH_SITES)}\n"
        f"  found ({len(real.sites)}):    {sorted(real.sites)}\n"
        f"  symmetric difference: {sorted(real.sites ^ EXPECTED_BUILD_ENGINE_PATCH_SITES)}\n"
        f"Patching out _build_engine was measured to produce a bind count of 0 with 519 tests green. "
        f"A NEW site here means a test is exercising the sync path with the egress gate's own "
        f"downstream construction stubbed out. If the new site is legitimate, add it to this census "
        f"deliberately -- do not widen the assertion to `<=`."
    )
    print(f"[G8] positive control: the census matches exactly {len(real.sites)} known escape-hatch sites")

    # Control the diagnostic: patch calls that do NOT name _build_engine must produce no site,
    # or "the mutant produced a site" would prove only that the matcher flags patching in general.
    control = analyze_patch_sites_in_source(_G8_CONTROL_PATCHES_SOMETHING_ELSE, label="<g8-control>")
    assert control.sites == set(), f"G8 NEGATIVE CONTROL FAILED: patching non-_build_engine seams produced {sorted(control.sites)}"
    print("[G8] negative control: two patch calls naming other seams produce 0 census sites")

    killed = 0
    g8_mutants = (
        ("fourth site, bare patch.object", _G8_MUTANT_FOURTH_SITE),
        ("fourth site, mock.patch.object (the F7 blind spot)", _G8_MUTANT_FOURTH_SITE_MOCK_QUALIFIED),
    )
    for label, mutant_source in g8_mutants:
        mutant = analyze_patch_sites_in_source(mutant_source, label="<g8-mutant>")
        assert mutant.sites, f"G8 MUTANT SURVIVED ({label}): the fixed matcher saw no patch site"
        # Fold onto the real census: a fourth site breaks the exact-membership assertion.
        assert (real.sites | mutant.sites) != EXPECTED_BUILD_ENGINE_PATCH_SITES, f"G8 MUTANT SURVIVED ({label}) when folded onto the real census"
        killed += 1
        print(f"[G8] mutant killed ({label}): fixed matcher saw {sorted(mutant.sites)}, WP01's matcher saw {sorted(mutant.sites_visible_to_wp01_matcher)}")
    print(f"[G8] KILLED-PIN COUNT: {killed}/2")


def test_g8_f7_residual_blind_spot_is_real_and_closed_here() -> None:
    """The F7 residual, measured rather than asserted: WP01's matcher requires the base of a
    ``patch`` / ``patch.object`` call to be a bare ``ast.Name``, so it never sees ``mock.patch``,
    ``mock.patch.object``, ``mocker.patch`` or ``unittest.mock.patch``.

    Red-then-green on the same input, two matchers -- the same demonstration shape as G5's
    module-qualified pin. The mutant is a ``_build_engine`` patch written in the blind form: WP01's
    matcher reports zero (**a guard reporting healthy**) and this file's matcher catches it.
    """
    mutant = analyze_patch_sites_in_source(_G8_MUTANT_FOURTH_SITE_MOCK_QUALIFIED, label="<f7>")
    _announce("G8-F7", mutant.input_count, wp01_matcher_sees=len(mutant.sites_visible_to_wp01_matcher), trailing_name_matcher_sees=len(mutant.sites))
    assert mutant.sites_visible_to_wp01_matcher == set(), (
        "NEGATIVE CONTROL FAILED: WP01's matcher was expected to be blind to `mock.patch.object`. "
        f"It saw {sorted(mutant.sites_visible_to_wp01_matcher)}. If WP01's matcher has since been "
        "fixed, this demonstration is obsolete -- delete it rather than weakening it."
    )
    assert mutant.sites, "the trailing-name matcher failed to see `mock.patch.object` -- F7 is not closed"
    print("[G8-F7] RED  (WP01's ast.Name-base matcher): 0 sites -- an ungated `_build_engine` patch is INVISIBLE")
    print(f"[G8-F7] GREEN(trailing-name matcher)       : {sorted(mutant.sites)} -- CAUGHT")
