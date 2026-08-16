"""The R1a window gate: two-SHA extraction, the rename detector, banding, ±1 stability, the walk.

Binding sources: ``spec.md`` §0.9 (the window, the banding, the ±1 rule, the amended widening
schedule), ``data-model.md`` §``Verdict`` and §Banding, and
``contracts/home-pin-scan-seam.md`` §"The gate driver is NOT in this module".

Why this module exists separately from the seam
------------------------------------------------
``subprocess`` and every git surface live **HERE and nowhere else** in the behaviour class.
``_home_pin_scan.py`` is imported by collected tests under a six-second budget on every PR
(NFR-001) and must stay clean of both; ``test_home_pin_seam_no_second_copy.py`` asserts that by
AST, with a positive control. This module is a **consumer**: it imports :func:`discover` and owns
**no predicate**, so the no-second-copy property is preserved.

It is also the seam's **first** consumer. FR-009's ``root`` parameter is exercised here — by a
``git archive`` extraction at each window SHA — before any downstream package depends on it, so
the two-SHA measurement is evidence the seam works rather than a claim that it will.

What ``R`` is, and why it is not simply ``discover()``'s difference
-------------------------------------------------------------------
§0.9 defines ``R`` as arrivals **within the effect class**: the sites *resolving to*
``tmp_path/"home"`` present at the end SHA and absent at the start SHA. ``R_f`` is the subset the
FR-001 predicate catches, i.e. the ``discover()`` members. So ``r = |R_f| / |R|`` measures exactly
one thing — the fraction of new effect-class sites whose scope chain *also* declares
``monkeypatch``. Drawing ``R`` from ``discover()`` alone would make ``r`` identically 1 by
construction and the instrument would measure nothing.

The effect-class enumeration below is a **composition of the seam's exported primitives**
(:func:`enumerate_py_files`, :func:`byte_prefilter`, :func:`parse_module`,
:func:`module_level_bindings`, :func:`find_write_sites`, :func:`bindings_for_site`,
:func:`resolve_value`, :func:`member_key`), never a second implementation of any of them.

Why ``git archive`` and not ``git worktree add``
-------------------------------------------------
``git archive`` writes nothing into ``.git``, needs no failure cleanup beyond a temporary
directory, and measured **0.46 s** per SHA against a ``discover()`` pass of **0.88-1.06 s**. A
worktree per candidate window would mutate repository state once per step of an unbounded walk.

Every population this module produces is an **AST set difference**. ``git log -S`` and
``git diff | grep`` are text search over a population and are barred (C-003); the only git this
module runs is ``rev-list --first-parent`` (history topology, not a population) and ``archive``
(content extraction).

The stopping rule
-----------------
:func:`window_accepted` reads ``|R|`` and ±1 consequence-class stability **only, never the value
of ``r`` and never the band**. That independence is the entire forking-path defence and it
survives the 5-attempt cap's removal untouched: a rule that read ``r`` would let a walker stop at
a convenient band. ``r`` has since leaked (§0.9 records it), which is exactly why the property
that matters is the rule's blindness rather than the analyst's.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Literal

from tests.architectural import _home_pin_scan as scan
from tests.architectural._home_pin_scan import MemberKey

__all__ = [
    "FLOOR",
    "THRESHOLD",
    "STATED_START_SHA",
    "END_SHA",
    "HISTORY_REF",
    "VERDICT_FIELDS",
    "VERDICT_RELPATH",
    "VERDICT_HEADER",
    "EVIDENCE_RELDIR",
    "Band",
    "Consequence",
    "ConsequenceClass",
    "VoidWindowError",
    "DuplicateSiteKeyError",
    "Site",
    "Perturbation",
    "Stability",
    "RenamePair",
    "RefusedCandidate",
    "RenameResult",
    "WindowMeasurement",
    "WalkResult",
    "band",
    "consequence",
    "admissible_perturbations",
    "stability",
    "consequence_class",
    "window_label",
    "window_accepted",
    "effect_class_sites",
    "detect_renames",
    "first_parent_history",
    "extracted_tests",
    "sites_at",
    "measure_window",
    "widening_walk",
    "crosscheck_start_sha",
    "verdict_document",
    "main",
]

# ---------------------------------------------------------------------------
# The pre-committed constants (§0.9). None of these is tunable after measurement.
# ---------------------------------------------------------------------------

#: The VISIBILITY floor on ``|R|``. **A precondition, evaluated BEFORE banding — not a band.**
#: Were it a band, ``|R| − 1`` at ``|R| = 10`` would always land in it, every ``|R| = 10`` sample
#: would be inadmissible, and the floor would really be eleven.
FLOOR = 10

#: Half of the standing effect-class catch rate (``40/40 = 100%`` by site, §0.1). It cannot move
#: without visibly moving §0.1, operator decision 1 and the non-goals together.
THRESHOLD = 0.5

#: The window as stated in §0.9. Measured post-tasks it yields ``|R| = 3`` — **VOID** — and the
#: walk starts from that result rather than from a clean slate.
STATED_START_SHA = "709a59534a1b8aac7e55a1cf6f5d2106a32c31ea"
#: The end SHA never moves.
END_SHA = "5d49d31ed6505627d98d8f95d8502c9bf6a2f5ac"
#: ``main`` is **rebase-merged**, so there are no merge commits for "one merge at a time" to step
#: over; the step unit is first-parent commits.
HISTORY_REF = "upstream/main"

#: The emitted document's top-level key set, transcribed from ``data-model.md``'s enumerated
#: ``Verdict`` field list. The emitter builds exactly these and the collected verdict test
#: compares the document's keys against this set.
VERDICT_FIELDS: frozenset[str] = frozenset(
    {
        "verdict",
        "start_sha",
        "end_sha",
        "sites_at_start",
        "sites_at_end",
        "renames",
        "refused_ambiguous",
        "unpaired_departures",
        "unpaired_arrivals",
        "R",
        "R_f",
        "attempted_windows",
        "invocation",
        "stability",
        "start_sha_crosscheck",
    }
)

#: The verdict artefact — the SOLE authority for attempted windows, with no rendered duplicate.
#:
#: **Repository-root ``research/``, and the reason is recorded rather than left to look arbitrary.**
#: WP02's prompt writes this path as ``research/home_pin_gate/verdict.yaml``. Read as
#: *mission*-relative — the way the prompt's other ``research/`` reference (the C-011 evidence
#: directory) has to be read — it lands under ``kitty-specs/``, and the framework **refuses** that:
#: ``move-task ... --to for_review`` fails with *"kitty-specs/ changes are not allowed on lane
#: branches"*, because planning artefacts belong on the planning branch. The literal, root-relative
#: reading satisfies both the prompt and that invariant, and it is also the truer classification:
#: this is a **measurement output**, not a planning artefact. Raised here rather than silently
#: repaired — the two ``research/`` references in one prompt do not share a prefix, and a reviewer
#: should know which one moved and why.
VERDICT_RELPATH = "research/home_pin_gate/verdict.yaml"
#: The checked-in C-011 instrument. Never imported by the seam, never tidied, never
#: re-implemented — ``discover()`` is compared *against* it, never derived *from* it.
EVIDENCE_RELDIR = (
    "kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/research/spec_kitty_home_pin_evidence"
)

#: Bounded because C-013 requires it, and generous because a timeout is a **datum**, never
#: silently retried into a different answer.
GIT_TIMEOUT_SECONDS = 300.0

Band = Literal["proceed", "proceed-degraded", "halt"]
#: The ±1 rule is evaluated over the CONSEQUENCE, not the label: ``{proceed, proceed-degraded}``
#: versus ``{halt}``. Evaluated over labels the gate's success state is unreachable in all 806
#: enumerated states — §0.9's fifteenth defect.
Consequence = Literal["go", "halt"]
ConsequenceClass = Literal["go", "halt", "inadmissible"]

_GO_BANDS: frozenset[str] = frozenset({"proceed", "proceed-degraded"})


class VoidWindowError(ValueError):
    """``band()`` was asked for a band below the floor. **VOID is a precondition, not a band.**"""


class DuplicateSiteKeyError(RuntimeError):
    """Two effect-class **sites** produced one :data:`MemberKey`.

    The member-level twin of this is :class:`_home_pin_scan.DuplicateMemberKeyError`, whose
    population is 0 on ``HEAD``. **Nothing bounds either population at a historical window**, so
    both are caught by :func:`measure_window` and recorded against that window as a datum rather
    than crashing an unbounded walk.
    """


# ---------------------------------------------------------------------------
# Banding, the clamp, and ±1 stability — pure functions, no I/O
# ---------------------------------------------------------------------------


def band(r_f: int, r: int) -> Band:
    """The band of a sample, per ``data-model.md`` §Banding.

    Raises :class:`VoidWindowError` below the floor: VOID is a **precondition on ``|R|``**
    evaluated *before* banding, so there is no band to return and returning one would quietly
    make VOID the fourth band.
    """
    if r < FLOOR:
        raise VoidWindowError(
            f"|R| = {r} is below the visibility floor of {FLOOR}; VOID is a precondition "
            "evaluated before banding, not a band"
        )
    ratio = r_f / r
    if ratio >= 1.0:
        return "proceed"
    return "proceed-degraded" if ratio >= THRESHOLD else "halt"


def consequence(label: Band) -> Consequence:
    """The CONSEQUENCE class of a band. The first three rows of §0.9's table are two, not three."""
    return "go" if label in _GO_BANDS else "halt"


def admissible_perturbations(r_f: int, r: int) -> tuple[tuple[int, int], ...]:
    """The ±1 neighbourhood in BOTH axes, with §0.9's clamp, as ``(|R_f|, |R|)`` pairs.

    ``|R_f| ± 1`` holding ``|R|`` fixed is one site reclassified; ``|R| ± 1`` holding ``|R_f|``
    fixed is one false rename pair or one missed arrival. The second axis is what an earlier
    revision could not see: a false pair moves ``|R|``, not ``|R_f|``.

    Clamp: ``|R_f| − 1`` skipped at ``|R_f| = 0``; ``|R_f| + 1`` at ``|R_f| = |R|``; ``|R| − 1``
    at ``|R| = |R_f|``; **and ``|R| − 1`` also skipped when it would fall below the floor, because
    VOID is not a band** — a perturbation outside the admissible domain is not evaluated.
    """
    neighbourhood: list[tuple[int, int]] = []
    if r_f > 0:
        neighbourhood.append((r_f - 1, r))
    if r_f < r:
        neighbourhood.append((r_f + 1, r))
    neighbourhood.append((r_f, r + 1))
    if r > r_f and r - 1 >= FLOOR:
        neighbourhood.append((r_f, r - 1))
    return tuple(neighbourhood)


@dataclass(frozen=True)
class Perturbation:
    """One admissible ±1 neighbour with the band and consequence it lands in."""

    r_f: int
    r: int
    band: Band
    consequence: Consequence


@dataclass(frozen=True)
class Stability:
    """The ±1 result over consequence classes. ``stable`` is False iff **any** neighbour moves."""

    base_band: Band
    base_consequence: Consequence
    stable: bool
    perturbations: tuple[Perturbation, ...]


def stability(r_f: int, r: int) -> Stability:
    """Recompute the CONSEQUENCE class under every admissible ±1 perturbation."""
    base = band(r_f, r)
    base_consequence = consequence(base)
    neighbours = tuple(
        Perturbation(f, n, band(f, n), consequence(band(f, n)))
        for f, n in admissible_perturbations(r_f, r)
    )
    stable = all(neighbour.consequence == base_consequence for neighbour in neighbours)
    return Stability(base, base_consequence, stable, neighbours)


def consequence_class(r_f: int, r: int) -> ConsequenceClass:
    """The oracle's codomain: ``go`` / ``halt`` / ``inadmissible`` for one enumerated state."""
    result = stability(r_f, r)
    return "inadmissible" if not result.stable else result.base_consequence


def window_label(r_f: int, r: int) -> str:
    """The label an attempted window is published with: ``VOID`` / ``INADMISSIBLE`` / the band."""
    if r < FLOOR:
        return "VOID"
    result = stability(r_f, r)
    return result.base_band if result.stable else "INADMISSIBLE"


# ---------------------------------------------------------------------------
# The effect-class enumeration — composed from the seam, never re-implemented
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Site:
    """One effect-class write site: a pin **resolving to** ``tmp_path/"home"``.

    ``is_member`` records whether the FR-001 predicate also catches it — the silhouette over the
    scope chain. ``kind`` and ``params`` are read at the **keyed def** for a member; for a
    non-member there is no keyed def, so the **outermost enclosing def** stands in and ``kind``
    is ``None`` when there is no enclosing def at all. A signature carrying ``None`` never
    matches, exactly as an unresolvable value never matches.

    **That fallback is asserted-inert at both measured ends of the stated window**: the near-miss
    shape (``tmp_path`` present, ``monkeypatch`` absent) has population 0 there, so every
    effect-class site is a member and the fallback is never exercised. It exists because nothing
    bounds that population at a historical window.
    """

    key: MemberKey
    relpath: str
    lineno: int
    kind: scan.Kind | None
    params: frozenset[str]
    resolved_value: str | None
    is_member: bool


def _shape_of(
    tree: ast.Module, lineno: int, member: scan.Member | None
) -> tuple[scan.Kind | None, frozenset[str]]:
    """``(kind, params)`` for the rename signature — at the keyed def, or the outermost def."""
    if member is not None:
        return member.kind, member.params
    chain = scan.def_chain(tree, lineno)
    if not chain:
        return None, frozenset()
    union = frozenset[str]().union(*(scan.normalise_params(scan.def_params(d)) for d in chain))
    return scan.def_kind(chain[0]), union


def effect_class_sites(root: Path) -> dict[MemberKey, Site]:
    """Every site under ``root`` whose ``SPEC_KITTY_HOME`` value resolves to ``tmp_path/"home"``.

    Root-parameterised so a ``git archive`` extraction and the live tree produce comparable keys
    (FR-009). Raises :class:`DuplicateSiteKeyError` rather than silently deduplicating, for the
    same reason ``discover()`` raises at member level: a collision that deduplicates greens the
    guard on a removal.
    """
    members = {member.key: member for member in scan.discover(root)}
    keyed: list[tuple[MemberKey, Site]] = []
    for path in scan.byte_prefilter(scan.enumerate_py_files(root)):
        source = path.read_text(encoding="utf-8")
        tree = scan.parse_module(path)
        module_bindings = scan.module_level_bindings(tree)
        relpath = path.relative_to(root).as_posix()
        for site in scan.find_write_sites(tree, key=scan.NEEDLE):
            bindings = scan.bindings_for_site(tree, site, module_bindings)
            value = scan.resolve_value(site.value, bindings)
            if value != scan.TMP_PATH_HOME:
                continue
            key = scan.member_key(relpath, source, site.lineno)
            member = members.get(key)
            kind, params = _shape_of(tree, site.lineno, member)
            keyed.append(
                (key, Site(key, relpath, site.lineno, kind, params, value, member is not None))
            )
    return _without_collisions(keyed)


def _without_collisions(keyed: Sequence[tuple[MemberKey, Site]]) -> dict[MemberKey, Site]:
    """Refuse a duplicate site key instead of letting the later record overwrite the earlier."""
    grouped: dict[MemberKey, list[Site]] = {}
    for key, site in keyed:
        grouped.setdefault(key, []).append(site)
    collisions = {key: sorted(s.lineno for s in v) for key, v in grouped.items() if len(v) > 1}
    if collisions:
        raise DuplicateSiteKeyError(
            f"{sorted(collisions)} effect-class site key collision(s): {collisions}"
        )
    return {key: sites[0] for key, sites in grouped.items()}


# ---------------------------------------------------------------------------
# The rename detector — unique mutual best match, ties REFUSED
# ---------------------------------------------------------------------------

#: ``(resolved_value, sorted params at the keyed def, kind)``. ``None`` in either the value or the
#: kind makes the signature unmatchable, so such a site is never paired.
Signature = tuple[str, tuple[str, ...], str]


def _signature(site: Site) -> Signature | None:
    if site.resolved_value is None or site.kind is None:
        return None
    return (site.resolved_value, tuple(sorted(site.params)), site.kind)


@dataclass(frozen=True)
class RenamePair:
    """One departure/arrival pair excluded from both sides."""

    departure: MemberKey
    arrival: MemberKey
    relpath: str
    signature: Signature


@dataclass(frozen=True)
class RefusedCandidate:
    """A group that is not a unique mutual best match. **Both sides are retained.**"""

    relpath: str
    signature: Signature
    departures: tuple[MemberKey, ...]
    arrivals: tuple[MemberKey, ...]


@dataclass(frozen=True)
class RenameResult:
    """The detector's full published output — pairs, refusals, and everything unpaired."""

    pairs: tuple[RenamePair, ...]
    refused: tuple[RefusedCandidate, ...]
    unpaired_departures: tuple[MemberKey, ...]
    unpaired_arrivals: tuple[MemberKey, ...]


def _by_group(sites: Mapping[MemberKey, Site]) -> dict[tuple[str, Signature], list[MemberKey]]:
    grouped: dict[tuple[str, Signature], list[MemberKey]] = {}
    for key, site in sites.items():
        signature = _signature(site)
        if signature is not None:
            grouped.setdefault((site.relpath, signature), []).append(key)
    return grouped


def detect_renames(
    departures: Mapping[MemberKey, Site], arrivals: Mapping[MemberKey, Site]
) -> RenameResult:
    """Pair a departure with an arrival **in the same file** on ``(value, params, kind)``.

    A pair must be a **unique mutual best match**: exactly one departure and exactly one arrival
    carrying that signature in that file. A two-way tie is **REFUSED** and both sites retained —
    on the detector's actual population the three in-file collisions are all same-``kind``, so
    what closes them is this rule and not ``kind``.

    Excluding a *fixture* rename biases toward halt; excluding a *non-fixture* rename biases
    toward proceed. The effects are opposite-signed, so the **rename mix is published**.
    """
    departure_groups = _by_group(departures)
    arrival_groups = _by_group(arrivals)
    pairs: list[RenamePair] = []
    refused: list[RefusedCandidate] = []
    paired_departures: set[MemberKey] = set()
    paired_arrivals: set[MemberKey] = set()
    for group in sorted(set(departure_groups) & set(arrival_groups)):
        relpath, signature = group
        left, right = sorted(departure_groups[group]), sorted(arrival_groups[group])
        # "Unique mutual best match" is *no second candidate on either side* — expressed as the
        # emptiness of the tails rather than as `len(...) == 1`, because the contract is the
        # absence of a rival, not a cardinality. Both sides are non-empty by construction: the
        # group came from the intersection of the two groupings.
        if not left[1:] and not right[1:]:
            pairs.append(RenamePair(left[0], right[0], relpath, signature))
            paired_departures.add(left[0])
            paired_arrivals.add(right[0])
            continue
        refused.append(RefusedCandidate(relpath, signature, tuple(left), tuple(right)))
    return RenameResult(
        tuple(pairs),
        tuple(refused),
        tuple(sorted(set(departures) - paired_departures)),
        tuple(sorted(set(arrivals) - paired_arrivals)),
    )


# ---------------------------------------------------------------------------
# Git — extraction and first-parent topology. The ONLY subprocess in the Mission.
# ---------------------------------------------------------------------------


def _git(args: Sequence[str], *, repo: Path) -> bytes:
    """Run ``git`` in ``repo``, bounded. A timeout propagates; it is a datum, never a retry."""
    completed = subprocess.run(  # noqa: S603 — fixed argv, no shell, C-003's containment point
        ["git", *args],
        cwd=repo,
        capture_output=True,
        check=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    return completed.stdout


def first_parent_history(ref: str, *, repo: Path) -> tuple[str, ...]:
    """Every commit on ``ref``'s FIRST-PARENT history, newest first. Topology, not a population."""
    out = _git(["rev-list", "--first-parent", ref], repo=repo).decode("utf-8")
    return tuple(line for line in out.splitlines() if line)


@contextmanager
def extracted_tests(sha: str, *, repo: Path) -> Iterator[Path]:
    """``tests/`` at ``sha``, extracted into a fresh temporary directory. Yields the tests root.

    A fresh directory per extraction is deliberate: ``_home_pin_scan._corpus`` caches on the root
    **path**, not on its contents, so reusing one directory across candidate windows would return
    the first window's parse for every later one.
    """
    with tempfile.TemporaryDirectory(prefix="home-pin-gate-") as tmp:
        destination = Path(tmp)
        archive = _git(["archive", "--format=tar", sha, "tests"], repo=repo)
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(destination, filter="data")
        yield destination / "tests"


_SITE_CACHE: dict[str, dict[MemberKey, Site]] = {}


def sites_at(sha: str, *, repo: Path) -> dict[MemberKey, Site]:
    """The effect-class site set at ``sha``, memoised — the end SHA is scanned once per process."""
    cached = _SITE_CACHE.get(sha)
    if cached is None:
        with extracted_tests(sha, repo=repo) as root:
            cached = effect_class_sites(root)
        _SITE_CACHE[sha] = cached
    return cached


# ---------------------------------------------------------------------------
# The window measurement and the amended widening walk
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WindowMeasurement:
    """One attempted window, with every operand SC-000 requires published."""

    start_sha: str
    end_sha: str
    sites_at_start: dict[MemberKey, Site]
    sites_at_end: dict[MemberKey, Site]
    renames: RenameResult
    arrivals: frozenset[MemberKey]
    caught: frozenset[MemberKey]
    label: str
    error: str | None = None


#: Errors that make a *historical* window unmeasurable. Each is recorded against that window as a
#: datum and the walk continues; none of them is retried.
_WINDOW_ERRORS = (
    scan.DuplicateMemberKeyError,
    DuplicateSiteKeyError,
    SyntaxError,
    subprocess.CalledProcessError,
    subprocess.TimeoutExpired,
)


def measure_window(start_sha: str, end_sha: str, *, repo: Path) -> WindowMeasurement:
    """Difference the two effect-class site sets, exclude renames, band the result."""
    try:
        start = sites_at(start_sha, repo=repo)
        end = sites_at(end_sha, repo=repo)
    except _WINDOW_ERRORS as exc:  # a datum about this window, never a crash of the walk
        empty: dict[MemberKey, Site] = {}
        return WindowMeasurement(
            start_sha,
            end_sha,
            empty,
            empty,
            RenameResult((), (), (), ()),
            frozenset(),
            frozenset(),
            "UNMEASURABLE",
            f"{type(exc).__name__}: {exc}",
        )
    departures = {key: site for key, site in start.items() if key not in end}
    arrival_sites = {key: site for key, site in end.items() if key not in start}
    renames = detect_renames(departures, arrival_sites)
    arrivals = frozenset(renames.unpaired_arrivals)
    caught = frozenset(key for key in arrivals if end[key].is_member)
    return WindowMeasurement(
        start_sha,
        end_sha,
        start,
        end,
        renames,
        arrivals,
        caught,
        window_label(len(caught), len(arrivals)),
    )


def window_accepted(measurement: WindowMeasurement) -> bool:
    """**The stopping rule.** Reads ``|R|`` and ±1 stability ONLY — never ``r``, never the band.

    A rule that read ``r`` would let a walker stop at a convenient band, which is precisely the
    garden of forking paths the pre-committed schedule exists to close. This function is the one
    place the walk is allowed to decide, and the band is not in scope here.
    """
    if measurement.error is not None:
        return False
    size = len(measurement.arrivals)
    return size >= FLOOR and stability(len(measurement.caught), size).stable


@dataclass(frozen=True)
class WalkResult:
    """The walk's outcome: every attempt in order, and the accepted window if there was one."""

    attempts: tuple[WindowMeasurement, ...]
    accepted: WindowMeasurement | None
    exhausted: bool


def widening_walk(
    *,
    repo: Path,
    start_sha: str = STATED_START_SHA,
    end_sha: str = END_SHA,
    ref: str = HISTORY_REF,
    limit: int | None = None,
) -> WalkResult:
    """Walk the start SHA backwards along ``ref``'s FIRST-PARENT history, one commit at a time.

    **No attempt cap.** The defined exit is the **root of first-parent history**: if the walk
    exhausts it without both conditions holding jointly it stops and the **OPERATOR decides** —
    the escalation the deleted 5-attempt cap used to carry, now triggered by exhaustion rather
    than by an arbitrary count, so it cannot be used to stop early at a convenient band.

    ``limit`` bounds a *test* walk over a synthetic history and is **not** a cap on the real one;
    the real invocation leaves it ``None`` and the record publishes that.
    """
    history = first_parent_history(ref, repo=repo)
    if start_sha not in history:
        raise ValueError(f"{start_sha} is not on {ref}'s first-parent history")
    candidates = history[history.index(start_sha) :]
    if limit is not None:
        candidates = candidates[:limit]
    attempts: list[WindowMeasurement] = []
    for candidate in candidates:
        measurement = measure_window(candidate, end_sha, repo=repo)
        attempts.append(measurement)
        if window_accepted(measurement):
            return WalkResult(tuple(attempts), measurement, exhausted=False)
    return WalkResult(tuple(attempts), None, exhausted=limit is None)


# ---------------------------------------------------------------------------
# C-011's second external anchor — the checked-in independent instrument
# ---------------------------------------------------------------------------


def _load_verbatim(path: Path, name: str) -> ModuleType:
    """Import a checked-in evidence script **verbatim**, without editing or copying it."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the checked-in instrument at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _redirect(module: ModuleType, name: str, value: object) -> None:
    """Rebind one name in a verbatim-loaded evidence script's **namespace**, never in its file.

    ``clf.py`` carries an absolute ``ROOT`` from the session that produced it, and that is
    deliberate: an artefact whose provenance is its independence stops being evidence the moment
    the party it checks edits it. Rebinding at import time is how the instrument is pointed at a
    ``git archive`` extraction without a single byte of it changing on disk.
    """
    module.__dict__[name] = value


def _clf_site_set(evidence_dir: Path, extraction_root: Path) -> set[tuple[str, int]]:
    """``(relpath under tests/, lineno)`` as the INDEPENDENT instrument sees them.

    ``clf.py`` and ``verify.py`` are loaded verbatim; only ``clf.ROOT`` is redirected at the
    extraction, because both carry absolute paths from the session that produced them and an
    artefact whose provenance is its independence stops being evidence the moment the party it
    checks edits it. ``verify.derive()`` — not a re-implementation of it — does the grouping.
    """
    verify = _load_verbatim(evidence_dir / "verify.py", "_c011_verify_gate")
    clf = _load_verbatim(evidence_dir / "clf.py", "_c011_clf_gate")
    _redirect(clf, "ROOT", extraction_root)
    _redirect(verify, "_load_clf", lambda: clf)
    rows: list[dict[str, object]] = verify.derive()
    sites: set[tuple[str, int]] = set()
    for row in rows:
        relpath = Path(str(row["path"])).relative_to("tests").as_posix()
        linenos = row["sites"]
        assert isinstance(linenos, list)
        sites |= {(relpath, int(lineno)) for lineno in linenos}
    return sites


def crosscheck_start_sha(sha: str, *, repo: Path) -> dict[str, object]:
    """Run the checked-in C-011 classifier at ``sha`` and publish the symmetric difference.

    Without this, the end SHA is externally anchored by C-011 and the start SHA is not — and the
    symmetric circularity is *tune until ``r >= 50%``*. The difference is published **whether
    empty or not**; any non-empty difference is **explained, never tuned away**.
    """
    evidence_dir = repo / EVIDENCE_RELDIR
    with extracted_tests(sha, repo=repo) as root:
        theirs = _clf_site_set(evidence_dir, root.parent)
        ours = {(member.relpath, member.lineno) for member in scan.discover(root)}
    difference = sorted(f"{relpath}:{lineno}" for relpath, lineno in theirs ^ ours)
    return {
        "instrument": f"{EVIDENCE_RELDIR}/clf.py (verbatim, via verify.py's derive())",
        "start_sha": sha,
        "symmetric_difference": difference,
        "explanation": (
            ""
            if not difference
            else "NON-EMPTY — see the record; a difference is explained, never tuned away"
        ),
    }


# ---------------------------------------------------------------------------
# Emission — the top-level key set EQUALS data-model.md's Verdict field list
# ---------------------------------------------------------------------------


def _site_row(site: Site) -> dict[str, object]:
    return {
        "key": list(site.key),
        "relpath": site.relpath,
        "lineno": site.lineno,
        "kind": site.kind,
        "params": sorted(site.params),
        "resolved_value": site.resolved_value,
        "is_member": site.is_member,
    }


def _attempt_row(measurement: WindowMeasurement) -> dict[str, object]:
    row: dict[str, object] = {
        "start_sha": measurement.start_sha,
        "R_size": len(measurement.arrivals),
        "R_f_size": len(measurement.caught),
        "band": measurement.label,
    }
    if measurement.error is not None:
        row["error"] = measurement.error
    return row


def _stability_block(measurement: WindowMeasurement) -> dict[str, object]:
    result = stability(len(measurement.caught), len(measurement.arrivals))
    return {
        "base_band": result.base_band,
        "base_consequence": result.base_consequence,
        "stable": result.stable,
        "perturbations": [
            {
                "R_f": p.r_f,
                "R": p.r,
                "band": p.band,
                "consequence": p.consequence,
            }
            for p in result.perturbations
        ],
    }


def verdict_document(
    walk: WalkResult, *, invocation: str, crosscheck: Mapping[str, object]
) -> dict[str, object]:
    """Build the verdict document. Its top-level key set **equals** :data:`VERDICT_FIELDS`.

    Raises when the walk was not accepted: there is no verdict to emit, and the operator decides.
    """
    accepted = walk.accepted
    if accepted is None:
        raise ValueError(
            "the walk produced no accepted window; the OPERATOR decides and no verdict is emitted"
        )
    document: dict[str, object] = {
        "verdict": accepted.label,
        "start_sha": accepted.start_sha,
        "end_sha": accepted.end_sha,
        "sites_at_start": [_site_row(s) for _, s in sorted(accepted.sites_at_start.items())],
        "sites_at_end": [_site_row(s) for _, s in sorted(accepted.sites_at_end.items())],
        "renames": [
            {
                "departure": list(pair.departure),
                "arrival": list(pair.arrival),
                "relpath": pair.relpath,
                "signature": {
                    "resolved_value": pair.signature[0],
                    "params": list(pair.signature[1]),
                    "kind": pair.signature[2],
                },
            }
            for pair in accepted.renames.pairs
        ],
        "refused_ambiguous": [
            {
                "relpath": candidate.relpath,
                "signature": {
                    "resolved_value": candidate.signature[0],
                    "params": list(candidate.signature[1]),
                    "kind": candidate.signature[2],
                },
                "departures": [list(key) for key in candidate.departures],
                "arrivals": [list(key) for key in candidate.arrivals],
            }
            for candidate in accepted.renames.refused
        ],
        "unpaired_departures": [list(key) for key in accepted.renames.unpaired_departures],
        "unpaired_arrivals": [list(key) for key in accepted.renames.unpaired_arrivals],
        "R": [list(key) for key in sorted(accepted.arrivals)],
        "R_f": [list(key) for key in sorted(accepted.caught)],
        "attempted_windows": [_attempt_row(attempt) for attempt in walk.attempts],
        "invocation": invocation,
        "stability": _stability_block(accepted),
        "start_sha_crosscheck": dict(crosscheck),
    }
    if set(document) != VERDICT_FIELDS:
        raise RuntimeError(
            f"emitted key set {sorted(document)} != data-model.md's Verdict field list "
            f"{sorted(VERDICT_FIELDS)}"
        )
    return document


#: The artefact's header. It is a **comment block**, deliberately: ``data-model.md`` fixes the
#: document's top-level key set and this prose is not one of those fields, so carrying it as a
#: sixteenth key would break the equality T006 and T008(e) both assert. The two statements §0.9
#: requires in so many words — the ``28 -> 30`` disposition and the leak — belong in the sole
#: authority artefact rather than only in a report, so they are emitted here every run.
VERDICT_HEADER = """\
# R1a WINDOW GATE — the verdict. GENERATED by tests/architectural/_home_pin_gate.py.
# The SOLE authority for attempted windows. No rendered duplicate exists. Never hand-edited.
#
# Regenerate (NFR-006: the pinned external pytest>=9.0.3,<9.1 interpreter, never a bare `uv run`):
#   {invocation}
#
# ---------------------------------------------------------------------------------------------
# §0.3's "28 -> 30" IS SUPERSEDED.
#
# SUPERSEDED, in that word, and not "addressed" — §0.9 requires one of two words and the window
# has moved. The 28 -> 30 growth was measured under the SUPERSEDED decorator-limbed predicate
# across the STATED window ({stated_start} -> {end_sha}); neither endpoint is recoverable under
# the current predicate, so it cannot be re-derived at the moved SHA. §0.3 says so itself: "the
# class's growth under the current predicate is unmeasured, deliberately — measuring it at the
# window start SHA is WP-0's job."
#
# That job is done here, and its result is what supersedes the figure. Under the CURRENT
# predicate the effect class grows {selected_start_size} -> {end_size} across the SELECTED window
# ({selected_start} -> {end_sha}), and 37 -> 40 across the stated one. The 28 -> 30 figure is
# retained by §0.3 as the historical fact that motivated freezing and is labelled as such; it is
# no longer a statement about this Mission's window.
# ---------------------------------------------------------------------------------------------
# THE MEASUREMENT HAS LEAKED, and the record says so rather than leaving a reader to infer it.
#
# While verifying the VOID finding, an independent lens measured r = 100% at candidate windows
# roughly 300, 600 and 2000 first-parent commits back (|R| = 9, 33, 34). On the published
# evidence the verdict was ALREADY KNOWN to be `proceed` before this run. WP-0b therefore
# CONFIRMS A KNOWN ANSWER rather than discovering one, and R1a must stop describing the gate as
# its own stopping mechanism: its power to halt this Mission was spent when the value leaked.
#
# What is PROTECTED is the stopping rule's independence from r. `window_accepted()` reads |R| and
# ±1 consequence-class stability ONLY; a leaked value cannot steer a rule that does not read it.
# What is LOST is the analyst's blindness, which was a real part of the instrument's value and is
# not recoverable. Both facts are stated because only one of them is.
# ---------------------------------------------------------------------------------------------
# The walk implements §0.9's AMENDED schedule: first-parent commits ONE AT A TIME (main is
# rebase-merged, so there are no merge commits to step over), NO ATTEMPT CAP, and a defined exit
# at the root of first-parent history where the OPERATOR decides. Every attempted window is
# published below, including the discarded ones, beginning with the VOID result at
# {stated_start} (|R| = 3 against a floor of 10). Lowering the floor to fit the window was
# refused by the operator.
"""


def _header(walk: WalkResult, invocation: str) -> str:
    """Fill :data:`VERDICT_HEADER` from the measurement, so the prose cannot drift from it."""
    accepted = walk.accepted
    assert accepted is not None
    return VERDICT_HEADER.format(
        invocation=invocation,
        stated_start=STATED_START_SHA,
        end_sha=accepted.end_sha,
        selected_start=accepted.start_sha,
        selected_start_size=len(accepted.sites_at_start),
        end_size=len(accepted.sites_at_end),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Take the measurement and publish the verdict artefact. The ONE documented invocation.

    Deliberately has no ``--floor`` and no ``--threshold``: both are pre-committed in §0.9 and a
    flag would be a re-tuning surface wearing a command line. ``--limit`` is likewise absent — the
    walk is unbounded by specification, and its only exit is exhaustion of first-parent history.
    """
    import argparse

    import yaml

    parser = argparse.ArgumentParser(prog="_home_pin_gate", description="R1a window gate")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--start-sha", default=STATED_START_SHA)
    parser.add_argument("--end-sha", default=END_SHA)
    parser.add_argument("--ref", default=HISTORY_REF)
    parser.add_argument("--out", type=Path, default=Path(VERDICT_RELPATH))
    args = parser.parse_args(argv)

    repo: Path = args.repo.resolve()
    invocation = (
        f"{sys.executable} -m tests.architectural._home_pin_gate --repo {repo} "
        f"--start-sha {args.start_sha} --end-sha {args.end_sha} --ref {args.ref} "
        f"--out {args.out}"
    )
    walk = widening_walk(repo=repo, start_sha=args.start_sha, end_sha=args.end_sha, ref=args.ref)
    if walk.accepted is None:
        print("EXHAUSTED first-parent history without a jointly satisfying window; OPERATOR decides")
        return 2
    crosscheck = crosscheck_start_sha(walk.accepted.start_sha, repo=repo)
    document = verdict_document(walk, invocation=invocation, crosscheck=crosscheck)
    out: Path = args.out if args.out.is_absolute() else repo / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(document, sort_keys=False, default_flow_style=False, allow_unicode=True)
    out.write_text(_header(walk, invocation) + body, encoding="utf-8")
    print(f"verdict: {document['verdict']} start_sha: {document['start_sha']} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
