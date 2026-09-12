"""The R1a guard VERDICT seam: ``discovered == census u E`` plus the hash/tombstone limb.

Why this is a module and not a few helpers inside the guard's test file
------------------------------------------------------------------------
The verdict is a **shared primitive**. WP04 proves it over materialised trees; WP05 applies it to
the real tree; R1b drives the burn-down through its tombstone path. A primitive with three
consumers living in a leaf ``test_*.py`` is a **DIR-001 boundary violation**, and a peer work
package importing another work package's test module **inverts the dependency** — WP05 would take a
build-order edge on WP04's test file to reach a function that is not a test. That is the whole
reason; it is sufficient on its own.

*(Recorded correction. WP04's first pass justified leaving these helpers in the test module by
claiming an importer would inherit that module's ``pytestmark`` and fixtures. That claim is
**false** — importing a name from a module applies neither — and it should not be repeated. The
boundary argument above never depended on it.)*

The seam this parallels
------------------------
``_home_pin_scan.py`` exists because ``_sole_door_scan.py:13-27`` records Gates 4 and 5 each
rolling an independent, drifting copy of the same primitives as a **live incident**. That module
prevents a second copy of the *scanner*. This one prevents a second copy of the *verdict*, which is
the same failure one level up: nothing in the anti-drift rule bans duplicating the comparison, so
the ban would have been satisfied while the census/hash/tombstone semantics were re-derived from
scratch in WP05.

The two limbs, and why both are needed
---------------------------------------
``discovered == census u E`` alone does **not** close SC-006. Transition (7) — a 41st member
**accompanied by a new census row** — satisfies the equality by construction; the absorption path
walks straight through it. What refuses the addition is the **key-set hash pinned in the baseline**,
which no census edit can restore. FR-004 says this directly: exact accounting is the primary
ratchet, and "the hash pin and the tombstone list exist to catch the one thing exact accounting
cannot see, a removal with no adjudication behind it".

The tombstone rule, and exactly how much of it is normative
-------------------------------------------------------------
**The PROPERTY is spec-normative.** FR-004(b) requires "a checked-in hash of the sorted freeze-time
key set, plus an explicit tombstone list, so **removals require a tombstone and additions are not
expressible**", and ``spec.md:420`` requires that the guard "recomputes the baseline hash from the
census and compares, and every delta must be accounted for by a tombstone — so a co-edit that
removes a row *and* re-pins the hash still reds unless a tombstone explains it, while a legitimate
adjudication passes."

**The FORMULA is this module's choice**, and a downstream consumer should know that it is choosing
to inherit it: :func:`evaluate` spells the rule as

    ``hash_of_key_set(census_keys | tombstoned_keys) == baseline["census_key_set_sha256"]``

so the pinned hash is over the **freeze-time** key set and the census plus its tombstones must
reconstruct it. That satisfies all four of T018(ii)'s cases — an ``owed_to`` re-point and a header
edit pass, a row removed without a tombstone reds, the same removal with a matching tombstone
passes — but the spec does not mandate this particular arithmetic, and an equally faithful
mechanisation could pin differently. **WP05 and R1b inherit the caveat with the code.**

``E`` gets **no tombstone path at all**: any delta to ``E`` or its hash reds unconditionally,
because ``E`` never legitimately changes in R1a or R1b (FR-004(3)). That asymmetry is deliberate
and is asserted, not merely documented.

No pytest dependency
--------------------
This module is a seam, not a test. It imports ``_home_pin_scan``, ``yaml`` and the standard
library, and nothing else — so WP05, R1b and any future consumer can import it without taking on a
test-framework dependency. ``ast.parse`` and ``NodeVisitor`` are banned here as in every module
importing the seam; the verdict never parses anything itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from tests.architectural import _home_pin_scan as scan

__all__ = [
    "GuardVerdict",
    "evaluate",
    "hash_of_key_set",
    "census_rows",
    "census_keys",
    "tombstone_keys",
    "as_key",
    "with_rows",
    "drop_row",
    "add_row",
    "edit_header",
    "with_tombstones",
]


@dataclass(frozen=True)
class GuardVerdict:
    """Both limbs of one guard run. ``ok`` is the conjunction; the fields say WHICH limb spoke.

    Keeping the limbs separate rather than collapsing to a bool is what lets transition (7) assert
    the shape it actually has — equality clean, hash red — instead of only "something failed".
    """

    #: ``discovered - (census u E)`` — a member the frozen class does not know about.
    unexpected: frozenset[scan.MemberKey]
    #: ``(census u E) - discovered`` — a row whose definition is gone. SC-004 reds here.
    stale: frozenset[scan.MemberKey]
    #: The census key set, plus any tombstoned keys, still hashes to the pinned baseline value.
    census_hash_ok: bool
    #: ``E``'s key set still hashes to the pinned baseline value. **No tombstone path.**
    exempt_hash_ok: bool

    @property
    def ok(self) -> bool:
        return not self.unexpected and not self.stale and self.census_hash_ok and self.exempt_hash_ok

    def __str__(self) -> str:
        return (
            f"unexpected={sorted(self.unexpected)} stale={sorted(self.stale)} "
            f"census_hash_ok={self.census_hash_ok} exempt_hash_ok={self.exempt_hash_ok}"
        )


def evaluate(
    root: Path, census_text: str, baseline_text: str, exempt: scan.ExemptSet
) -> GuardVerdict:
    """Run both guard limbs against a tree and its census/baseline artefacts.

    ``root`` is a parameter (FR-009), so this is the same function whether the tree is materialised
    into ``tmp_path`` or is the real ``tests/``.

    ``scan.discover`` propagates ``SyntaxError`` (SC-013) and **nothing on this call path catches
    it**. ``except SyntaxError: continue`` narrows the walk with nothing firing and buys budget
    headroom, which is NFR-001's defeat wearing an exception handler.
    """
    discovered = {member.key for member in scan.discover(root)}
    census = census_keys(census_text)
    exempt_key_set = frozenset(entry.key for entry in exempt)
    known = census | exempt_key_set
    baseline = yaml.safe_load(baseline_text)
    return GuardVerdict(
        unexpected=frozenset(discovered - known),
        stale=frozenset(known - discovered),
        census_hash_ok=(
            hash_of_key_set(census | tombstone_keys(baseline_text))
            == baseline["census_key_set_sha256"]
        ),
        exempt_hash_ok=hash_of_key_set(exempt_key_set) == baseline["exempt_set_sha256"],
    )


def hash_of_key_set(keys: frozenset[scan.MemberKey]) -> str:
    """Recompute a key-set hash **through the seam's own generator**, never a second hash here.

    ``render_baseline`` is the single place the payload format lives, and it hashes the **sorted
    key set** — never the file bytes, which would move under an ``owed_to`` re-point and a comment
    edit alike. Feeding it records whose only meaningful field is ``key`` is what "the guard
    RECOMPUTES the key-set hash from the census" means; a private ``sha256`` here would be the drift
    ``_sole_door_scan.py:13-27`` records as a live incident, at the smallest possible scale.

    Fails safe if ``render_baseline`` ever widens: the pinned side and this side would then disagree
    and every hash limb would red, rather than agreeing with itself on a stale format.
    """
    members = [
        scan.Member(
            key=key,
            lineno=0,
            home_partition="A",
            relpath=key[0],
            kind="fixture",
            params=frozenset(),
            resolved_value=None,
        )
        for key in keys
    ]
    return str(yaml.safe_load(scan.render_baseline(members, exempt=()))["census_key_set_sha256"])


# ---------------------------------------------------------------------------
# Census / baseline artefact reading
# ---------------------------------------------------------------------------


def census_rows(text: str) -> list[dict[str, object]]:
    """The census's ``rows`` list, each row a plain dict."""
    rows = yaml.safe_load(text)["rows"]
    return [dict(row) for row in rows]


def census_keys(text: str) -> frozenset[scan.MemberKey]:
    """The census's key set — the thing the equality and the hash are both stated over."""
    return frozenset(as_key(row["key"]) for row in census_rows(text))


def tombstone_keys(text: str) -> frozenset[scan.MemberKey]:
    """The baseline's tombstoned keys: rows R1b has adjudicated away, with the adjudication recorded.

    Absent or empty is the R1a state and yields the empty set, which makes the hash limb a plain
    equality against the freeze-time key set.
    """
    document = yaml.safe_load(text)
    return frozenset(as_key(entry) for entry in document.get("tombstones", []))


def as_key(raw: object) -> scan.MemberKey:
    """A YAML three-element list back into a :data:`MemberKey`.

    Spelled out rather than ``tuple(raw)`` so a wrong arity raises here, instead of producing a
    tuple that compares unequal to everything and silently reds every set operation downstream.
    """
    if not isinstance(raw, list):
        raise TypeError(f"a MemberKey column must be a list, got {type(raw).__name__}: {raw!r}")
    if len(raw) != 3:
        raise ValueError(f"a MemberKey is a 3-tuple (relpath, qualname, token_line), got {raw!r}")
    relpath, qualname, token_line = raw
    return (str(relpath), str(qualname), str(token_line))


# ---------------------------------------------------------------------------
# Census / baseline artefact writing — the doctoring the transitions drive, and
# the tombstone path R1b will drive for real.
# ---------------------------------------------------------------------------


def with_rows(text: str, rows: list[dict[str, object]]) -> str:
    """Rewrite a census with a different row list, header untouched."""
    document = yaml.safe_load(text)
    document["rows"] = rows
    return _dump(document)


def drop_row(text: str, key: scan.MemberKey) -> str:
    """Remove one census row. Its definition stays in the tree unless the caller removes it too."""
    return with_rows(text, [row for row in census_rows(text) if as_key(row["key"]) != key])


def add_row(text: str, key: scan.MemberKey) -> str:
    """Absorb a new member into the census — transition (7)'s repair, which must still red.

    ``lineno`` is explicitly non-authoritative and never part of the key, so the placeholder here
    changes nothing the guard compares.
    """
    rows = census_rows(text)
    rows.append({"key": list(key), "lineno": 1, "kind": "fixture", "home_partition": "A"})
    return with_rows(text, rows)


def edit_header(text: str, **fields: str) -> str:
    """Change header scalars only. The key set — and therefore the hash — is untouched."""
    document = yaml.safe_load(text)
    document["header"].update(fields)
    return _dump(document)


def with_tombstones(text: str, keys: frozenset[scan.MemberKey]) -> str:
    """Record adjudicated-away keys in the baseline. R1b's legitimate path — for the CENSUS only.

    There is deliberately no ``E`` equivalent: :func:`evaluate` gives ``exempt_hash_ok`` no
    tombstone path, so this cannot excuse an ``E`` delta.
    """
    document = yaml.safe_load(text)
    document["tombstones"] = [list(key) for key in sorted(keys)]
    return _dump(document)


def _dump(document: object) -> str:
    """The single YAML emission style, matching ``render_census`` / ``render_baseline``."""
    return yaml.safe_dump(document, sort_keys=False, default_flow_style=False, allow_unicode=True)
