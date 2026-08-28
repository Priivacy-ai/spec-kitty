"""Shrink-only transition guard for the retired governing term (M1, FR-006/SC-004).

Mission ``charter-authority-flip-01M14RB3`` (wave M1 of
``retire-doctrine-term-01M0JMK9``) retires the *governing-term* sense of the
polysemous token — the glossary authority surface, the Charter-Bundle
``governance`` selection key, and the ``docs/context/`` authority-3 doc path —
while deliberately KEEPING every other sense (the ``src/`` package/path, the
``drg`` / "…​ reference graph" / "…​ artifact" / "…​ pack" domain concepts, the
``…SelectionConfig`` value class, and proper-noun mission slugs). This guard is
armed LAST so the authority graph can never regress: the retired governing term
cannot be re-introduced into an authority surface without an explicit, auditable
widening.

**Governing-sense census, not a raw-token census (the load-bearing scoping
decision).** A naive whole-tree census of the raw token would false-*fail* on
M1's own legitimate additions — the renamed authority-3 doc carries KEPT domain
vocabulary ("… Domain", "… Catalog", "… artifact"), the new ``### charter``
Terminology-Canon entry references sibling domain terms, the migration script
carries the proper-noun slug ``…​-catfooding-2196``, and the new ATDD tests name
the retired term as *test data*. None of those are governing re-introductions.
So this census matches only the crisp **governing markers** (see
``_GOVERNING_MATCHERS``): the glossary term whose surface/id is exactly the
retired token, a bare ``<token>:`` selection-key mapping line, and the retired
``context/<token>.md`` authority-3 path token. On the current tree those markers
shrank from a non-empty baseline to zero on the authority surfaces (both the
seed and pack glossaries lose their ``surface: <token>`` line; the Charter
Bundle key flips), while every KEPT domain occurrence is left untouched.

**Baseline: M1's own OPENING four-root fingerprint, computed from git at run
time — never a committed token-bearing fixture (C-COR-4 / spec.md:61).** The
baseline is the census taken at the mission base commit
:data:`_MISSION_BASE_REV` (the pre-WP01 state). It is derived live via
``git grep`` at that rev rather than stored, so no token-bearing baseline file
lives under ``kitty-specs/`` (or anywhere tracked) — M6's later deletion of the
guard therefore never surfaces as a ``D`` entry under an archive root, keeping
``test_archive_root_byte_identical`` green at M6.

**Four fixed exclusion roots** (``DM-01M0P6C8C7Q6SPBT412V39RPN0``): the immutable
historical-record roots ``kitty-specs/``,
``.kittify/migrations/mission-state/quarantine/``, ``kitty-ops/`` and
``.kittify/missions/`` are audit boundaries, never scanned.

**Shrink-only rule** (methodology.md §2.1): per ``(path, line-hash)`` coordinate
— with the OC-40 rename ``docs/context/<token>.md`` → ``docs/context/charter.md``
normalized so the legitimate move is not read as a "moved hit" — the current
tree may only shrink or hold: no new path, no per-path count increase, and no new
``(path, line-hash)`` pair, **except** coordinates in
:data:`_CR01_CONTROL_PATHS` — the CR-01 / ATDD *control* test files that name the
retired term as test data (the methodology's ``control_record`` exception). The
≤3 CR-01 *products* proper — the warn-compat legacy-key reader in
``src/charter/sync.py`` (``_LEGACY_GOVERNANCE_SELECTION_KEY``) — are a string
literal, not a governing marker, so they never enter this census; they are
audited separately by ``tests/charter/test_governance_key_compat.py`` and the
mission's closing audit.

Four assertions close the non-vacuity gap (mirroring
``test_bare_prose_corpus_ratchet.py``, read directly as this module's precedent):

1. **No widening** (``test_governing_term_footprint_does_not_widen``): the real
   gate — every current governing coordinate is in the baseline or a registered
   control path.
2. **Concrete floor / anchored baseline**
   (``test_baseline_detects_real_governing_occurrences``): the baseline census is
   non-empty AND detects the authority-surface governing markers — what a
   collapsed, always-empty census would fail.
3. **Shrink actually happened** (``test_authority_footprint_shrank``): the
   governing footprint is strictly smaller than the baseline and zero on the
   authority glossaries — proving WP01–WP03 truly removed the governing term, not
   a no-op.
4. **Self-mutation teeth** (``test_guard_has_teeth``): stubbing the census empty
   makes the floor RAISE, and injecting a synthetic governing coordinate into a
   non-control authority path makes the gate RAISE — proving both are
   load-bearing, not merely present.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter

import pytest

from charter.hasher import hash_content

from tests.utils import REPO_ROOT

# Scans docs/ + reads the wheel-shipped/authoritative corpus data
# (``.kittify/glossaries/**``, ``.kittify/charter/**``, ``packs/**``), so a
# corpus- or docs-only change re-widening the governing term must re-run this
# gate on the trimmed CI poles: carry ``corpus`` (registered in
# ``test_ci_corpus_trigger_completeness.py``'s curated registry) and
# ``docs_scoped``. It shells out to ``git grep`` so it also carries ``git_repo``.
pytestmark = [pytest.mark.architectural, pytest.mark.git_repo, pytest.mark.docs_scoped, pytest.mark.corpus]

# The retired governing token, assembled from fragments so this guard module can
# never flag itself (mirrors ``_FORBIDDEN_TERMS`` in
# ``test_no_legacy_terminology.py``).
_TOKEN = "doc" + "trine"

# M1's opening four-root fingerprint base: the pre-WP01 mission base commit. The
# baseline census is derived live from this rev at run time — never stored.
_MISSION_BASE_REV = "fc4acaa897"

# Immutable historical-record roots — audit boundaries, never scanned.
_EXCLUSION_ROOTS: tuple[str, ...] = (
    "kitty-specs/",
    ".kittify/migrations/mission-state/quarantine/",
    "kitty-ops/",
    ".kittify/missions/",
)

# OC-40 rename normalization: the one M1-owned path move. Comparing the moved
# file by its authority slot (not its old name) keeps a legitimate rename from
# reading as a forbidden "moved hit".
_OC40_OLD_PATH = f"docs/context/{_TOKEN}.md"
_OC40_NEW_PATH = "docs/context/charter.md"

# Governing-sense markers. A ``doctrine``-bearing line is a *governing* occurrence
# ONLY if it is (a) a glossary term whose surface/id is exactly the retired token,
# (b) a bare ``<token>:`` selection-key mapping line, or (c) the retired
# authority-3 ``context/<token>.md`` path token. Every other sense (``src/``
# path, ``… artifact`` / ``… pack`` / ``… reference graph`` domain concepts,
# prose mentions) is intentionally NOT matched.
_SURFACE_MARKER = re.compile(rf"^\s*(?:-\s*)?surface:\s*{_TOKEN}\s*$")
_SELECTION_KEY_MARKER = re.compile(rf"^\s*{_TOKEN}:\s*$")
_PATH_TOKEN = f"context/{_TOKEN}.md"


def _is_governing_line(content: str) -> bool:
    """True when a line carries the retired token in a *governing* sense."""
    return bool(
        _SURFACE_MARKER.match(content)
        or _SELECTION_KEY_MARKER.match(content)
        or _PATH_TOKEN in content
    )


# CR-01 / ATDD *control* paths: the test files that legitimately name the retired
# governing term as test data / assertions verifying the flip (e.g. asserting the
# OC-40 doc no longer exists, or re-pointing ``context/<token>.md`` →
# ``context/charter.md`` in a fixture). New governing coordinates are tolerated
# ONLY here — the methodology's registered ``control_record`` exception. This set
# is a ceiling to shrink (M6 deletes the guard and its controls), never a floor
# to grow.
_CR01_CONTROL_PATHS: frozenset[str] = frozenset(
    {
        "tests/architectural/test_charter_owner_map_executed.py",
        "tests/architectural/test_glossary_authority_parity.py",
        "tests/charter/test_answers_migration.py",
        "tests/glossary/test_canonical_promotion.py",
    }
)

# The authority glossaries whose ``surface: <token>`` governing line M1 retires.
# Anchors assertion 2 (baseline is real) and assertion 3 (shrank to zero).
_AUTHORITY_GLOSSARIES: tuple[str, ...] = (
    ".kittify/glossaries/spec_kitty_core.yaml",
    "packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml",
)

# This guard and its sibling WP04 test must never be scanned (belt-and-suspenders
# on top of the fragment-built token: neither file carries a governing marker).
_SELF_EXCLUDE: frozenset[str] = frozenset(
    {
        "tests/architectural/test_transition_guard_shrink_only.py",
        "tests/architectural/test_archive_root_byte_identical.py",
    }
)

# A per-path multiset of governing line-hashes.
Census = dict[str, Counter[str]]


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ``git`` at the repo root, capturing text output."""
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _baseline_is_reachable() -> bool:
    """True when the mission base commit is present in this checkout's object DB."""
    return _run_git(["cat-file", "-e", f"{_MISSION_BASE_REV}^{{commit}}"]).returncode == 0


def _census(rev: str | None) -> Census:
    """Governing-marker census as a ``{path: Counter(line-hash)}`` map.

    ``rev`` names a tree-ish to scan; ``None`` scans the working tree. The four
    exclusion roots and the WP04 self-exclusions are dropped, only governing
    lines are kept, and the OC-40 rename is normalized to the new authority slot.
    """
    args = ["grep", "-I", "--line-number", "--extended-regexp", _TOKEN]
    if rev is not None:
        args.append(rev)
    args += ["--", ":(top)"]
    result = _run_git(args)
    # git grep exits 1 on no matches, 0 on matches, >1 on error.
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"git grep failed (rev={rev!r}): exit={result.returncode} stderr={result.stderr!r}"
        )
    prefix = f"{rev}:" if rev is not None else ""
    census: Census = {}
    for raw in result.stdout.splitlines():
        line = raw[len(prefix):] if prefix and raw.startswith(prefix) else raw
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        path, _lineno, content = parts
        if any(path.startswith(root) for root in _EXCLUSION_ROOTS):
            continue
        if path in _SELF_EXCLUDE:
            continue
        if not _is_governing_line(content):
            continue
        normalized = _OC40_NEW_PATH if path == _OC40_OLD_PATH else path
        line_hash = hash_content(content)
        census.setdefault(normalized, Counter())[line_hash] += 1
    return census


def _total(census: Census) -> int:
    """Total governing coordinates across all paths."""
    return sum(sum(counter.values()) for counter in census.values())


def _widening_violations(
    baseline: Census, current: Census, control_paths: frozenset[str]
) -> list[str]:
    """Every current governing coordinate absent from the baseline and not under a
    registered control path — a pure seam so the teeth test can drive it with a
    doctored census without a git subprocess."""
    violations: list[str] = []
    for path, counter in current.items():
        if path in control_paths:
            continue
        base_counter = baseline.get(path, Counter())
        for line_hash, count in counter.items():
            if count > base_counter.get(line_hash, 0):
                violations.append(f"{path} [{line_hash}] current={count} baseline={base_counter.get(line_hash, 0)}")
    return violations


def _assert_baseline_detects_governing_occurrences(baseline: Census) -> None:
    """Concrete floor (assertion 2), factored out so the teeth test can re-invoke
    it under a stubbed-empty census and prove it goes RED."""
    assert _total(baseline) > 0, (
        "the baseline governing-term census is EMPTY — a collapsed census would "
        "pass the no-widening gate vacuously; the mission base MUST carry the "
        "retired governing term on its authority surfaces"
    )
    on_authority = sum(len(baseline.get(path, Counter())) for path in _AUTHORITY_GLOSSARIES)
    assert on_authority > 0, (
        "the baseline census detected no governing marker on the authority "
        f"glossaries {_AUTHORITY_GLOSSARIES} — the census is not actually "
        "detecting the retired governing surface, so shrink is meaningless"
    )


@pytest.mark.skipif(
    not _baseline_is_reachable(),
    reason=f"mission base commit {_MISSION_BASE_REV} not reachable in this checkout",
)
def test_governing_term_footprint_does_not_widen() -> None:
    """Assertion 1 (the real gate): no governing coordinate outside the baseline
    or a registered CR-01/control path."""
    baseline = _census(_MISSION_BASE_REV)
    current = _census(None)
    violations = _widening_violations(baseline, current, _CR01_CONTROL_PATHS)
    assert not violations, (
        "The retired governing term was re-introduced into a non-control surface "
        "(a widening of the authority graph). Canonical governing term is "
        "'charter' (see docs/context/charter.md; mission "
        "retire-doctrine-term-01M0JMK9). If a coordinate is a genuine, auditable "
        "CR/control record, register it explicitly — do not let it widen the "
        "footprint silently:\n  " + "\n  ".join(sorted(violations))
    )


@pytest.mark.skipif(
    not _baseline_is_reachable(),
    reason=f"mission base commit {_MISSION_BASE_REV} not reachable in this checkout",
)
def test_baseline_detects_real_governing_occurrences() -> None:
    """Assertion 2 (concrete floor): the baseline is non-empty and detects the
    authority-surface governing markers — see
    :func:`_assert_baseline_detects_governing_occurrences`."""
    _assert_baseline_detects_governing_occurrences(_census(_MISSION_BASE_REV))


@pytest.mark.skipif(
    not _baseline_is_reachable(),
    reason=f"mission base commit {_MISSION_BASE_REV} not reachable in this checkout",
)
def test_authority_footprint_shrank() -> None:
    """Assertion 3 (shrink actually happened): the governing footprint is strictly
    smaller than the baseline and zero on the authority glossaries — proving
    WP01–WP03 truly removed the governing term rather than no-op'd."""
    baseline = _census(_MISSION_BASE_REV)
    current = _census(None)
    assert _total(current) < _total(baseline), (
        f"the governing footprint did not shrink (baseline={_total(baseline)}, "
        f"current={_total(current)}) — WP01–WP03 were expected to remove the "
        "governing term from the authority graph"
    )
    surviving = {
        path: dict(current.get(path, Counter()))
        for path in _AUTHORITY_GLOSSARIES
        if current.get(path)
    }
    assert not surviving, (
        "the retired governing surface still survives on an authority glossary: "
        f"{surviving} — the M1 flip (T005/T005a) did not fully retire it"
    )


def test_guard_has_teeth() -> None:
    """Assertion 4 (self-mutation teeth): both the floor and the gate are
    load-bearing.

    (a) A stubbed-empty baseline makes the concrete floor RAISE.
    (b) A synthetic governing coordinate injected into a NON-control authority
        path makes the gate RAISE.
    """
    # (a) empty census -> floor raises a real AssertionError, not an error/skip.
    with pytest.raises(AssertionError, match="EMPTY"):
        _assert_baseline_detects_governing_occurrences({})

    # (b) a synthetic widening on an authority surface must be flagged.
    baseline: Census = {_AUTHORITY_GLOSSARIES[0]: Counter({"basehash": 1})}
    doctored: Census = {
        _AUTHORITY_GLOSSARIES[0]: Counter({"basehash": 1, "reintroduced": 1}),
    }
    violations = _widening_violations(baseline, doctored, _CR01_CONTROL_PATHS)
    assert violations, (
        "the no-widening gate did not flag a synthetic governing coordinate "
        "re-introduced into an authority surface — the gate is vacuous"
    )


def test_cr01_control_allowlist_is_a_ceiling_not_a_floor() -> None:
    """The registered control allowlist is a ceiling to shrink (M6 deletes the
    guard and its controls), never a floor to grow — mirrors
    ``test_lane_consolidation_baseline_does_not_grow``."""
    assert len(_CR01_CONTROL_PATHS) <= 6, (
        f"_CR01_CONTROL_PATHS grew to {len(_CR01_CONTROL_PATHS)} entries (was 4 at "
        "M1 arming). Widening it re-grandfathers new governing drift instead of "
        "fixing it — widen deliberately with a documented rationale, never to "
        "force green."
    )


@pytest.mark.skipif(
    not _baseline_is_reachable(),
    reason=f"mission base commit {_MISSION_BASE_REV} not reachable in this checkout",
)
def test_cr01_control_paths_are_currently_real() -> None:
    """Every registered control path exists AND still carries a governing
    coordinate — a stale entry (fixed/deleted) must be REMOVED, not left masking
    the ratchet (the staleness half of the ceiling guard above)."""
    current = _census(None)
    for control in sorted(_CR01_CONTROL_PATHS):
        assert (REPO_ROOT / control).is_file(), (
            f"registered control path {control!r} does not exist on disk — remove it"
        )
        assert current.get(control), (
            f"registered control path {control!r} no longer carries any governing "
            "coordinate — it has been fixed and MUST be removed from "
            "_CR01_CONTROL_PATHS (shrink-only), not left in it"
        )
