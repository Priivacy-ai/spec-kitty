"""Architectural gate: the unfiltered journal read may only be named by a listed consumer.

Issue Priivacy-ai/spec-kitty#3030 (P0 confidentiality). On 2026-07-27 a sync
delivered 1,322 events belonging to five never-opted-in projects alongside 7,811
from the intended one, because the drain's read carried **no project predicate**.

The mission's fix made ``EventJournal.read_identity_projection`` take a mandatory
``project_uuids`` filter with no "all projects" spelling, so the dangerous
unfiltered scan became *unwritable* — a capability removed, not merely forbidden.
Operator reporting genuinely needs the unfiltered read (FR-015/SC-004: it must
name the projects **not yet known to consent**, so the uuid set cannot be supplied
up front, and it must surface the ``project_uuid IS NULL`` rows of FR-011 that the
filtered read drops), so ``read_identity_projection_for_report`` was added
alongside it, documented "operator REPORTING only (#3030 T021)".

Why this gate exists: the convention lasted six hours
-----------------------------------------------------
Both consumers landed on 2026-07-30. ``82db736899`` (07:36) added the reporting
one. ``0ded9e79a3`` (13:31), 46 commits later, added
``cli/commands/sync.py::_purge_resolve_project`` — a **selector resolver, not a
report**. A reviewer then wrote the pre-fix unfiltered drain read as **one
substituted call inside ``delivery/``** and nothing objected, because "REPORTING
only" is a docstring and a docstring does not fail a build. ``models.py`` records
the retraction: NFR-003's *cost* property still rests on structure, but keeping
the report reader out of a delivery path is **convention**. This gate is the
structure that convention lacked.

What counts as "a delivery path" — and why the package-level rule fails
----------------------------------------------------------------------
The naive rule is "no reference from ``delivery/``". It cannot work here: the one
**legitimate** consumer, ``build_per_project_store_report``, lives in
``delivery/status_report.py``. A package rule would either red the legitimate
report or exempt the whole package — and ``delivery/`` is exactly where the
dangerous one-line read was written.

A **file**-keyed rule (the shape ``test_egress_consent_boundary.py`` uses) fails
for the same reason one step down: exempting ``delivery/status_report.py`` for
the sake of ``build_per_project_store_report`` would exempt every one of its
other functions too, in an 800-line module under concurrent edit. That is
precisely the evasion the egress guard names as its own cheapest (its limit 7:
"a file may hold more than one sink, and an allowance covers them all").

So the key here is **per-symbol**: ``<path relative to src/>::<enclosing
qualname>``. A reference is permitted only inside a function that is named in
:data:`_UNFILTERED_READ_ALLOWLIST`. Adding the read to a *new* function in an
already-listed file is a red build.

Two consequences worth stating, because they are the design and not an accident:

* The scan covers **all** of ``src/``, not just ``delivery/``. "Is this file a
  delivery path?" is the question the package rule proved undecidable at
  directory level, so the gate does not ask it: every reference anywhere must be
  named by a human. That is a superset of the requirement and needs no taxonomy.
* The key is ``path::qualname``, never a line number — DIR-041, and explicitly
  outside the ``test_ratchet_positional_anchor_ban`` int-to-line-sink ban. A
  blank line above the call does not move the key; renaming or relocating the
  consuming function does, which is the point.

Shape (modelled on ``tests/architectural/test_egress_consent_boundary.py``)
---------------------------------------------------------------------------
1. AST-scan every ``.py`` under ``src/`` for a *reference* to either target
   symbol, resolving the enclosing qualname of each hit.
2. Permit a reference only where an explicit :data:`_UNFILTERED_READ_ALLOWLIST`
   entry names the consumer **and its justification**.
3. Meta-tests: no stale entry, no inert entry, every entry proven to red on its
   own removal, and a non-vacuity check so a zero-site scan fails rather than
   passes.
4. Negative controls that exercise the real collection path and assert the
   failure text — including the file-rule falsification (a new function added to
   an allowlisted file still reds).

The target symbols
------------------
* ``read_identity_projection_for_report`` — the public, no-argument method. This
  is the one a drain can substitute for the filtered read in a single line.
* ``SELECT_IDENTITY_PROJECTION_ALL_SQL`` — the statement it executes. Named
  separately because a consumer that opens its own connection and runs the SQL
  bypasses the method entirely, and ``models.py``'s own docstring offers both
  spellings as "a visible choice in a review diff". This gate is what makes that
  sentence true.

Definitions are not references: ``def read_identity_projection_for_report``, the
``SELECT_... = (...)`` assignment, and the ``__all__`` string are all skipped, so
the module that *owns* the capability is not accused of consuming it. What the
owning module still holds — the ``from ... import`` at module scope and the use
inside the implementation — **is** listed, so its entries are live and cannot rot
into a permanent silent exemption.

What this gate does not judge
-----------------------------
An allowance asserts that a consumer was **named and reasoned about**, not that
it is *correct*. ``_purge_resolve_project`` is the standing proof: it is
allowlisted, and it is not a report. The gate can tell you a new consumer
appeared; it cannot tell you the rows it read are then filtered, nor that the
consumer is bounded to an explicit operator command rather than a drain tick.
That is a reviewer's job.

Completeness limits — stated rather than implied
------------------------------------------------
A claim that names its gaps is the only defensible kind. This gate sees a
reference written as a ``Name``, an ``Attribute`` or an ``import`` alias, in a
file under ``src/``. It does **not** see:

1. **``getattr``-by-string.** ``getattr(journal, "read_identity_projection_for_
   report")()`` is a string literal, and a string literal is not a reference.
   ``src/`` contains hundreds of string-literal ``getattr`` calls; the egress
   guard inherits the identical blind spot and it is the cheapest evasion of any
   AST name scan.
2. **A consumer reached through an allowlisted helper — the analogue of the
   egress guard's limit 7, and here it is not hypothetical.**
   ``build_per_project_store_report`` is allowlisted and *returns* a value
   derived from every row in the store. Anything that calls it inherits the
   unfiltered universe without ever naming a target symbol, so this gate is
   blind to it. The allowance is per *reference site*, not per *reachability*.
   The structural fence that still holds under that shape is
   ``delivery.consent_gate.ConsentedBatch`` — a receiver's ``deliver`` takes one,
   it is unforgeable outside ``consented_batch()``, and that factory refuses any
   event it cannot attribute to a granted project. This gate closes the "one
   substituted call" hole and nothing more.
3. **A local alias called later.** ``from ... import read_identity_projection_for_
   report as _read`` reds **at the import site**, so the alias evasion costs a
   red — but the ``_read(...)`` calls that follow are not separately located, so
   the failure names the import's qualname rather than each caller's.
4. **Anything outside ``src/``.** Tests, scripts and templates are not scanned.
   A delivery path implemented in ``tests/`` is not a delivery path.
5. **Dynamic import, entry-point plugins, ``exec``.** Not audited. Such a
   consumer is still a reference *in some file*, so it reds only if that file's
   enclosing function is unlisted — which is the point, but reachability is not
   what is checked.
6. **A second, unrelated read in an allowlisted function.** The key is the
   enclosing function, so a listed consumer that grows a second call to the same
   symbol is covered by the one allowance. This is the residual of the egress
   guard's limit 7 after moving from file keying to symbol keying: it shrinks the
   exempt surface from a whole module to a single function body, it does not
   eliminate it.
7. **A hand-rolled unfiltered ``SELECT``, and this is a name scan.** The egress
   guard chose to key on a *sink* precisely because its predecessor keyed on two
   literal names and went blind to a third. This gate keys on names, and cannot
   do otherwise: the thing being guarded is a *capability spelled two ways*, not
   an observable primitive — an unfiltered read has no syntactic signature beyond
   the absence of a ``WHERE``. A consumer that writes ``SELECT event_id, ... FROM
   events ORDER BY created_at`` inline under its own constant name is invisible
   here. What makes that a materially larger step than the one-line substitution
   this gate closes: ``EventJournal`` exposes no raw-execute seam (``_connect`` is
   private and there is no public ``execute``), so a hand-rolled scan must open
   its own ``sqlite3`` connection to the journal path — a new import and a new
   connection in a review diff, not a changed method name on a journal the caller
   already holds.

Registered in ``tests/architectural/_baselines.yaml`` as
``test_unfiltered_journal_read_boundary.unfiltered_read_allowlist_sites``, so
adding a consumer costs a second visible diff with a written justification —
following the egress guard's precedent that the allowlist is itself the surface
an author would edit to silence the gate.

Spec: FR-011, FR-015, NFR-001, NFR-003, SC-004, C-003.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pytest

from specify_cli.contracts.anchoring import enclosing_qualname

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"

#: The unfiltered-read vocabulary. The method is what a drain substitutes in one
#: line; the SQL constant is what a consumer that opens its own connection would
#: run instead, bypassing the method entirely.
_TARGET_SYMBOLS: frozenset[str] = frozenset(
    {
        # ``SELECT_IDENTITY_PROJECTION_ALL_SQL`` was retired with the #3262
        # per-project store cutover — the machine-global statement no longer
        # exists in src/, so the method is the one remaining spelling.
        "read_identity_projection_for_report",
    }
)

#: What an unlisted consumer must do instead. The actionable half of the failure
#: message: "call this other thing" beats "you are not allowed".
_GUIDANCE = (
    "Use EventJournal.read_identity_projection(project_uuids=...) — its filter is "
    "mandatory precisely so a drain cannot ask the journal for a scan (NFR-003), and "
    "delivery/selection.py::select_consented already computes the consented uuid set. "
    "The unfiltered read exists for operator REPORTING only (FR-015/SC-004): it names "
    "projects not yet known to consent and surfaces the NULL-identity rows of FR-011, "
    "neither of which the filtered read can answer. If this really is such a report, "
    "add an entry to _UNFILTERED_READ_ALLOWLIST in this file naming the consumer and "
    "why it is not a delivery path, and record the growth in "
    "tests/architectural/_baselines.yaml with a justification."
)


@dataclass(frozen=True)
class ReadSite:
    """One reference to an unfiltered-read symbol, located by file + qualname.

    ``lineno`` is carried for the failure message only — it is never a comparand
    and never part of :meth:`key`, so a blank line above the call cannot move
    this site (DIR-041).
    """

    relpath: str
    qualname: str
    symbol: str
    lineno: int  # diagnostic-locator

    @property
    def key(self) -> str:
        """The allowlist key: ``<path relative to src/>::<enclosing qualname>``."""
        return f"{self.relpath}::{self.qualname}"


def _is_definition(node: ast.AST) -> bool:
    """True for a node that *creates* a target symbol rather than consuming one.

    The owning module must not be accused of consuming its own capability:
    ``def read_identity_projection_for_report``, the ``SELECT_... = (...)``
    assignment and the ``__all__`` string are all creation, not use. (The
    ``__all__`` entry is an ``ast.Constant`` and is never a candidate in the first
    place — a string literal is not a reference, which is also limit 1.)
    """
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return node.name in _TARGET_SYMBOLS
    if isinstance(node, ast.Name):
        return isinstance(node.ctx, ast.Store | ast.Del)
    return False


def _referenced_symbol(node: ast.AST) -> str | None:
    """The target symbol *node* references, or ``None``.

    Three shapes, deliberately: an attribute access (``journal.read_...``), a bare
    name (the SQL constant after a ``from ... import``), and an import alias — the
    last so that ``import X as _read`` reds at the import rather than letting the
    local alias slip past unseen (limit 3).
    """
    if _is_definition(node):
        return None
    if isinstance(node, ast.Attribute) and node.attr in _TARGET_SYMBOLS:
        return node.attr
    if isinstance(node, ast.Name) and node.id in _TARGET_SYMBOLS:
        return node.id
    if isinstance(node, ast.alias) and node.name in _TARGET_SYMBOLS:
        return node.name
    return None


def _find_sites(path: Path, root: Path) -> list[ReadSite]:
    """Every unfiltered-read reference in *path*, keyed by enclosing qualname."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - defensive
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - a louder problem than this rule
        return []

    relpath = path.relative_to(root).as_posix()
    sites: list[ReadSite] = []
    for node in ast.walk(tree):
        symbol = _referenced_symbol(node)
        if symbol is None:
            continue
        lineno = getattr(node, "lineno", 0)
        sites.append(
            ReadSite(
                relpath=relpath,
                qualname=enclosing_qualname(source, lineno),
                symbol=symbol,
                lineno=lineno,
            )
        )
    return sites


def _scan(root: Path) -> list[ReadSite]:
    """Every unfiltered-read reference under *root*, excluding ``__pycache__``."""
    sites: list[ReadSite] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        sites.extend(_find_sites(path, root))
    return sites


# ---------------------------------------------------------------------------
# The allowlist
# ---------------------------------------------------------------------------


class ConsumerKind(StrEnum):
    """Closed vocabulary of reasons a symbol may name the unfiltered read.

    Closed on purpose: without it, "needed here" becomes the escape hatch that
    turns the allowlist back into the docstring convention it replaces.
    """

    #: The journal module that defines and executes the statement.
    OWNER = "owner"
    #: An operator diagnostic answering FR-015/SC-004 — the intended consumer.
    OPERATOR_REPORT = "operator-report"
    #: Resolves an operator-supplied selector; not a report, and not delivery.
    OPERATOR_SELECTOR = "operator-selector"


@dataclass(frozen=True)
class Allowance:
    """Why one function is permitted to name an unfiltered-read symbol."""

    kind: ConsumerKind
    #: Why this consumer cannot be served by ``read_identity_projection`` — the
    #: sentence a future reviewer has to disagree with to remove the entry.
    note: str
    #: For ``OPERATOR_SELECTOR``: the commit that made this a precedent, so the
    #: entry records *why this gate exists* rather than merely permitting itself.
    precedent: str | None = None


#: Functions permitted to name an unfiltered-read symbol, keyed
#: ``<path relative to src/>::<enclosing qualname>``. See the module docstring for
#: why the key is per-symbol rather than per-file or per-package.
_UNFILTERED_READ_ALLOWLIST: dict[str, Allowance] = {
    # -- The owning module ----------------------------------------------------
    # No owner entries: since the #3262 per-project cutover the implementation
    # (`EventJournal.read_identity_projection_for_report`) holds no counted
    # reference — its `def` line is a definition and the per-store SQL it runs
    # is inline (the retired machine-global constant is gone from src/), so an
    # owner allowance here would be inert and the inert check would red it.
    # -- The intended consumer: FR-015/SC-004's operator report ---------------
    "specify_cli/delivery/status_report.py::build_per_project_store_report": Allowance(
        kind=ConsumerKind.OPERATOR_REPORT,
        note=(
            "FR-015/SC-004, and the reason this gate cannot be keyed on a package. It "
            "lives under `delivery/` and is nonetheless the legitimate consumer: the "
            "report must name the projects NOT yet known to consent (so no uuid set "
            "exists to pass to the filtered read) and must surface `project_uuid IS "
            "NULL` rows, which FR-011 exists to make visible and which the filtered "
            "read drops by construction. Read-only by design — `resolve_project_"
            "consent` is called without repo_root/checkout_roots so its writing branch "
            "is unreachable (C-001). Cost is bounded by call site: once per explicit "
            "`sync doctor`/`sync status`/`sync migrate`, never on a drain tick."
        ),
    ),
    # -- The awkward case, allowlisted and labelled as the precedent ----------
    "specify_cli/sync/sync_purge_exec.py::_purge_resolve_project": Allowance(
        kind=ConsumerKind.OPERATOR_SELECTOR,
        note=(
            "**This entry is the reason this gate exists.** It is a real consumer, it "
            "is NOT a report, and it is not a delivery path either: it resolves an "
            "operator's `sync purge --project <name>` selector against every name the "
            "machine has a record of. It genuinely cannot use the filtered read — the "
            "operator supplies a NAME and the uuid is the answer, so the uuid set the "
            "filter demands is exactly what is unknown, and refusing an unrecognised "
            "name is the point ('0 rows removed' is indistinguishable from 'wrong "
            "selector'). Bounded to one interactive command, like the report. It is "
            "allowlisted, and labelled OPERATOR_SELECTOR rather than OPERATOR_REPORT, "
            "so the drift is recorded as a fact instead of being smoothed over: the "
            "'REPORTING only' convention was already false six hours after it was "
            "written, and the next such consumer is now a visible diff in two files "
            "rather than a docstring nobody re-reads."
        ),
        precedent=(
            "0ded9e79a3 (2026-07-30 13:31), 46 commits and six hours after "
            "82db736899 (07:36) introduced the method as 'operator REPORTING only'."
        ),
    ),
    # -- The purge measurement reads (#3262 WP10 cutover tooling) -------------
    "specify_cli/sync/sync_purge_exec.py::_purge_journal_census": Allowance(
        kind=ConsumerKind.OPERATOR_REPORT,
        note=(
            "`sync purge`'s pre/post differential census. It needs the stored "
            "identity values VERBATIM — blank and whitespace uuids each as their "
            "own bucket, plus the FR-011 NULL rows — which the filtered read drops "
            "by construction and retention._journal_census (which filters falsy "
            "uuids) cannot supply. Measurement only: the deletion itself still "
            "selects through the primitives. Bounded to one explicit operator "
            "command, never a drain tick."
        ),
    ),
    "specify_cli/sync/sync_purge_exec.py::_purge_journal_ids": Allowance(
        kind=ConsumerKind.OPERATOR_REPORT,
        note=(
            "`sync purge`'s ledger-half measurement: the ids the operator's "
            "selector covers, including `project_uuid IS NULL` (FR-011) which the "
            "filtered read cannot name. Read-only measurement of what WOULD be "
            "purged — the destructive path selects through the primitives, not "
            "through this read. Bounded to one explicit operator command."
        ),
    ),
}

#: Ratcheted in ``_baselines.yaml`` as
#: ``test_unfiltered_journal_read_boundary.unfiltered_read_allowlist_sites``.
#: Growth fails ``test_ratchet_baselines.py`` — a different test in a different
#: file — so silencing this gate by adding a consumer requires a second edit with
#: a written justification.
_UNFILTERED_READ_ALLOWLIST_SITES: frozenset[str] = frozenset(_UNFILTERED_READ_ALLOWLIST)


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def _collect_offenders(root: Path, allowed: frozenset[str]) -> list[ReadSite]:
    """Reference sites under *root* whose enclosing function is not allowlisted.

    Parameterised over *root* and the permission set so the negative controls
    exercise **this** function — the one the boundary test calls — rather than
    only the leaf matcher. A guard whose collection path has never been observed
    to fail is decoration.
    """
    return [site for site in _scan(root) if site.key not in allowed]


def _vacuity_problems(sites: list[ReadSite]) -> list[str]:
    """Ways a scan result proves the scanner never ran rather than the tree is clean.

    A zero-site scan of ``src/`` is not a clean repo — the operator report and
    the purge tooling call the method by name, so at minimum those consumer
    sites must be present. Without this, deleting the symbol name from
    :data:`_TARGET_SYMBOLS` (or a typo in it) would turn every assertion below
    green. (The owning module itself holds no *counted* reference since the
    #3262 cutover: the method's ``def`` line is a definition, and the retired
    machine-global SQL constant it used to execute is gone from src/.)
    """
    problems: list[str] = []
    if not sites:
        problems.append("the scan found no reference to any unfiltered-read symbol anywhere under src/ — the scanner is broken, not the tree clean")
        return problems
    found_symbols = {site.symbol for site in sites}
    for symbol in sorted(_TARGET_SYMBOLS - found_symbols):
        problems.append(f"no site references {symbol} — it was renamed or removed from src/, so this gate no longer guards it")
    return problems


def _format(sites: list[ReadSite]) -> str:
    ordered = sorted(sites, key=lambda s: (s.relpath, s.lineno))
    return "\n".join(f"  {site.relpath}:{site.lineno}  in {site.qualname}() -> references {site.symbol}\n      key: {site.key}" for site in ordered)


# ---------------------------------------------------------------------------
# The boundary
# ---------------------------------------------------------------------------


class TestUnfilteredJournalReadBoundary:
    """#3030: the unfiltered read may only be named where a human named it first."""

    def test_no_unlisted_consumer_names_the_unfiltered_read(self) -> None:
        """A new reference from any un-allowlisted function fails the build."""
        offenders = _collect_offenders(_SRC, _UNFILTERED_READ_ALLOWLIST_SITES)
        if offenders:
            keys = sorted({site.key for site in offenders})
            pytest.fail(
                "#3030 unfiltered-read boundary violation: the project-unfiltered "
                f"journal read is named by {len(keys)} function(s) with no recorded "
                f"justification:\n{_format(offenders)}\n\n"
                f"{_GUIDANCE}\n\n"
                "The 2026-07-27 incident shipped 1,322 events from five never-opted-in "
                "projects because the drain's read carried no project predicate. The "
                "filtered read's mandatory `project_uuids` is what makes that "
                "unwritable; naming the reporting read puts it back in reach."
            )

    def test_the_scan_is_not_vacuous(self) -> None:
        """A zero-site scan must fail rather than pass.

        Every other assertion in this module is satisfied by a scanner that finds
        nothing. This is the one that distinguishes "nothing is violating" from
        "the scanner never ran" — the failure shape this mission recorded five
        distinct times.
        """
        problems = _vacuity_problems(_scan(_SRC))
        assert not problems, "This gate is not measuring anything:\n  " + "\n  ".join(problems)


class TestAllowlistIntegrity:
    """Meta-tests: the allowlist must not rot into a second 'REPORTING only' docstring."""

    def test_allowlisted_files_exist(self) -> None:
        """No stale entry may silently permit a consumer whose file has moved."""
        missing = sorted(key for key in _UNFILTERED_READ_ALLOWLIST_SITES if not (_SRC / key.split("::", 1)[0]).is_file())
        assert not missing, (
            "Stale unfiltered-read entries — these files no longer exist, so their "
            f"allowance permits nothing and hides nothing: {missing}. Remove them and "
            "shrink the matching baseline in tests/architectural/_baselines.yaml."
        )

    def test_no_entry_is_inert(self) -> None:
        """Every entry must still cover a live reference, or it is a blank cheque.

        An entry whose reference was refactored away keeps a function name
        permanently exempt — including a *future*, different read added to that
        same function. This is the half that stops an allowlist rotting without
        anyone editing it.
        """
        live = {site.key for site in _scan(_SRC)}
        inert = sorted(_UNFILTERED_READ_ALLOWLIST_SITES - live)
        assert not inert, (
            f"Unfiltered-read entries covering no live reference: {inert}. The "
            "exemption now permits nothing while still exempting that function from "
            "every future unfiltered read added to it — delete the entry and shrink "
            "the baseline."
        )

    def test_removing_any_entry_reds_exactly_its_own_key(self) -> None:
        """Each entry is individually load-bearing, and blames only its own consumer.

        Named, not counted: a tally of "N entries are live" passes just as happily
        when one entry accounts for every site and the rest are dead. This asserts
        the per-entry mapping — remove entry K and the offenders are exactly the
        sites keyed K, no more (it does not over-blame) and no fewer (it is not
        inert).
        """
        blame: dict[str, list[str]] = {}
        for key in sorted(_UNFILTERED_READ_ALLOWLIST_SITES):
            offenders = _collect_offenders(_SRC, _UNFILTERED_READ_ALLOWLIST_SITES - {key})
            blame[key] = sorted({site.key for site in offenders})
        expected = {key: [key] for key in sorted(_UNFILTERED_READ_ALLOWLIST_SITES)}
        assert blame == expected, (
            "Removing an allowlist entry did not red exactly its own consumer. An "
            "entry blaming nothing is inert (it exempts a reference that no longer "
            "exists); an entry blaming somebody else means the key is not "
            f"discriminating.\n  got:      {blame}\n  expected: {expected}"
        )

    def test_every_allowance_carries_a_reason(self) -> None:
        """An entry with no stated justification is an exemption, not an allowance."""
        for key, allowance in sorted(_UNFILTERED_READ_ALLOWLIST.items()):
            assert allowance.note.strip(), f"{key}: allowance carries no rationale — a future reviewer has nothing to disagree with."
            assert "::" in key, f"{key}: allowlist keys must be `<relpath>::<qualname>`, not a bare path — a path-keyed entry would exempt the whole file."

    def test_operator_selector_allowances_record_their_precedent(self) -> None:
        """The awkward case must record *why* it is awkward, or the drift is lost.

        ``OPERATOR_SELECTOR`` is the kind that says "this is neither a report nor a
        delivery path". That is exactly the category whose first member broke the
        convention six hours after it was written, so an entry claiming it must
        name the commit — otherwise the kind becomes the new soft escape hatch.
        """
        selectors = {key: allowance for key, allowance in _UNFILTERED_READ_ALLOWLIST.items() if allowance.kind is ConsumerKind.OPERATOR_SELECTOR}
        assert selectors, (
            "No OPERATOR_SELECTOR entry exists, so this check proves nothing — if "
            "_purge_resolve_project was reclassified or removed, delete this test with it."
        )
        for key, allowance in sorted(selectors.items()):
            assert allowance.precedent and allowance.precedent.strip(), f"{key}: an OPERATOR_SELECTOR allowance must name the commit that made it a precedent."


class TestGuardBites:
    """Negative controls. A guard never observed to fail is decoration.

    This mission recorded five distinct ways a check can silently pass while
    proving nothing, so these controls exercise the real collection path and
    assert the failure text rather than a boolean.
    """

    @pytest.mark.parametrize(
        ("source", "expected_symbol", "expected_qualname"),
        [
            pytest.param(
                "def drain(journal):\n    return journal.read_identity_projection_for_report()\n",
                "read_identity_projection_for_report",
                "drain",
                id="attribute-call",
            ),
            pytest.param(
                "class Drain:\n    def run(self, journal):\n        return journal.read_identity_projection_for_report()\n",
                "read_identity_projection_for_report",
                "Drain.run",
                id="attribute-call-in-method",
            ),
            pytest.param(
                "from specify_cli.event_journal.journal import read_identity_projection_for_report as _read\n",
                "read_identity_projection_for_report",
                "<module>",
                id="aliased-import-reds-at-the-import",
            ),
        ],
    )
    def test_scanner_detects_each_reference_shape(self, tmp_path: Path, source: str, expected_symbol: str, expected_qualname: str) -> None:
        """Every shape in the vocabulary is detected, so none can go blind unnoticed."""
        module = tmp_path / "consumer.py"
        module.write_text(source, encoding="utf-8")
        sites = _find_sites(module, tmp_path)
        assert sites, f"scanner went blind to {expected_symbol} in the {expected_qualname} scope"
        assert (sites[0].symbol, sites[0].qualname) == (expected_symbol, expected_qualname)

    def test_the_incident_shape_is_reported_with_its_replacement(self, tmp_path: Path) -> None:
        """The whole collection path reds on the pre-fix unfiltered drain read.

        This is the one line a reviewer wrote inside ``delivery/`` that nothing
        objected to: substituting the reporting read for the filtered one in a
        drain. The failure must name the file, the symbol and what to do instead.
        """
        pkg = tmp_path / "specify_cli" / "delivery"
        pkg.mkdir(parents=True)
        (pkg / "drain.py").write_text(
            "def build_window(journal, limit):\n    rows = journal.read_identity_projection_for_report()\n    return rows[:limit]\n",
            encoding="utf-8",
        )
        offenders = _collect_offenders(tmp_path, _UNFILTERED_READ_ALLOWLIST_SITES)
        assert [site.key for site in offenders] == ["specify_cli/delivery/drain.py::build_window"]
        assert offenders[0].symbol == "read_identity_projection_for_report"
        report = _format(offenders)
        assert "specify_cli/delivery/drain.py" in report
        assert "read_identity_projection_for_report" in report
        assert "read_identity_projection(project_uuids=...)" in _GUIDANCE

    def test_a_new_function_in_an_allowlisted_file_still_reds(self, tmp_path: Path) -> None:
        """The falsification of the file-keyed rule, and of the package rule with it.

        ``delivery/status_report.py`` holds the *legitimate* consumer, so any rule
        coarser than a symbol would exempt this whole module — and this module is
        under concurrent edit by two other agents. Here the allowlisted report and
        an unlisted drain-shaped read sit in the same file: only the second reds.
        """
        pkg = tmp_path / "specify_cli" / "delivery"
        pkg.mkdir(parents=True)
        (pkg / "status_report.py").write_text(
            "def build_per_project_store_report(journal):\n"
            "    return journal.read_identity_projection_for_report()\n"
            "\n"
            "\n"
            "def _drain_window(journal):\n"
            "    return journal.read_identity_projection_for_report()\n",
            encoding="utf-8",
        )
        offenders = _collect_offenders(tmp_path, _UNFILTERED_READ_ALLOWLIST_SITES)
        assert [site.key for site in offenders] == ["specify_cli/delivery/status_report.py::_drain_window"]

    def test_allowlisting_the_same_consumer_clears_it(self, tmp_path: Path) -> None:
        """Positive control: the guard is discriminating, not unconditionally red.

        Without this, an always-red collector would satisfy every control above
        while telling us nothing about the allowlist mechanism.
        """
        pkg = tmp_path / "specify_cli" / "delivery"
        pkg.mkdir(parents=True)
        (pkg / "drain.py").write_text(
            "def build_window(journal):\n    return journal.read_identity_projection_for_report()\n",
            encoding="utf-8",
        )
        cleared = _collect_offenders(tmp_path, _UNFILTERED_READ_ALLOWLIST_SITES | {"specify_cli/delivery/drain.py::build_window"})
        assert cleared == []

    def test_definitions_are_not_references(self, tmp_path: Path) -> None:
        """The owning module must not be accused of consuming its own capability.

        A ``def``, the ``SELECT_... = (...)`` assignment and the ``__all__`` string
        all create the symbol. Counting them would force a blanket exemption on
        ``event_journal/``, which is the coarse rule this gate exists to avoid.
        """
        module = tmp_path / "models.py"
        module.write_text(
            'SELECT_IDENTITY_PROJECTION_ALL_SQL = "SELECT a, b FROM events ORDER BY created_at"\n'
            "\n"
            '__all__ = ["SELECT_IDENTITY_PROJECTION_ALL_SQL"]\n'
            "\n"
            "\n"
            "class Journal:\n"
            "    def read_identity_projection_for_report(self):\n"
            "        return []\n",
            encoding="utf-8",
        )
        assert _find_sites(module, tmp_path) == []

    def test_the_filtered_read_is_not_flagged(self, tmp_path: Path) -> None:
        """No false positives on the read every drain is supposed to use.

        A gate that reds on the correct call is a gate somebody weakens. The
        filtered read shares a name prefix with the target, which is exactly the
        collision a substring scan would get wrong.
        """
        module = tmp_path / "selection.py"
        module.write_text(
            "def select(journal, consented):\n"
            "    rows = journal.read_identity_projection(project_uuids=sorted(consented))\n"
            "    sql = select_identity_projection_sql(len(consented))\n"
            "    return rows, sql\n",
            encoding="utf-8",
        )
        assert _find_sites(module, tmp_path) == []

    def test_a_zero_site_scan_fails_rather_than_passes(self) -> None:
        """Non-vacuity is itself falsifiable: an empty scan must produce a problem.

        ``test_the_scan_is_not_vacuous`` asserts the real tree yields no problem,
        which is a pass. This exercises the other branch, so the check cannot rot
        into a function that returns ``[]`` unconditionally.
        """
        assert _vacuity_problems([]) == [
            "the scan found no reference to any unfiltered-read symbol anywhere under src/ — the scanner is broken, not the tree clean"
        ]
        # A non-empty scan whose sites cover none of the target symbols must
        # still red per missing symbol (e.g. after a rename the scanner keeps
        # finding an old spelling somewhere while the guarded name goes dark).
        partial = [
            ReadSite(
                relpath="specify_cli/delivery/status_report.py",
                qualname="build_per_project_store_report",
                symbol="a_renamed_spelling_the_gate_does_not_guard",
                lineno=1,
            )
        ]
        assert _vacuity_problems(partial) == [
            "no site references read_identity_projection_for_report — it was renamed or removed from src/, so this gate no longer guards it",
        ]
