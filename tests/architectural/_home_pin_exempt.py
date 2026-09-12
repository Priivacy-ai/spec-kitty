"""``E`` — the enumerated exemption set, declared where its content is determined (WP03/T014).

Binding contracts:
``kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/contracts/home-pin-scan-seam.md`` (the key
space) and ``.../contracts/canonical-home-owner.md`` (the two definitions).

``E`` lives here because **both of its keys are determined by WP03's own two artefacts and nothing
else**: the canonical owner (T011, ``tests/conftest.py``) and the retained-pin probe (T013a,
``tests/architectural/test_home_owner_never_wins.py``). WP04 tests the exemption **mechanism** over
materialised tuples; WP05 asserts the **real** hash and runs ``mypy --strict`` over this file. No
package edits another's.

``E`` fails the reviewer test, and that is the point
-----------------------------------------------------
An entry here entitles its definition to exist **forever** with no ``owed_to``, no
``frozen_at_sha`` and no tombstone — strictly more than a census row. No honest answer of
"nothing" is available, because the owner must exist forever. **What closes ``E`` is mechanism, not
prose**: fixed arity **by type**, so a third entry is a ``mypy --strict`` error and not a one-line
literal; plus a hash of its sorted entry set held **outside** this module (FR-004(b), WP05). Any
delta to ``E`` or its hash reds unconditionally — ``E`` never legitimately changes, in R1a or R1b.

``Exempt`` and ``MemberKey`` are imported from ``_home_pin_scan``, **never re-declared locally**.
A local stand-in would type-check against itself and silently fall out of the key space every
downstream set operation runs over.

Why there is not a single line number in this file
---------------------------------------------------
``tests/architectural/test_ratchet_positional_anchor_ban.py::
test_no_int_line_sink_in_architectural_python_seeds`` walks every ``tests/architectural/**/*.py``
and flags an int literal reaching ``composite_key_from_file(path, N)``'s second positional
argument — **including, per its #2564 clause, a module-level seed constant of ``(rel, int, ...)``
rows whose int is unpacked into a loop variable that then reaches the sink.** That is exactly the
naive shape of ``E``, and nobody had named it.

The compliant form is the one the key space already mandates: a :data:`MemberKey` is the
content-addressed 3-tuple ``(relpath_posix, enclosing_qualname, normalized_token_line)``, and the
token line has its string literals **stripped**, so these keys survive every benign edit that moves
the lines. Any ``lineno`` needed to *recompute* one comes from ``discover()`` **at runtime** — see
``test_home_owner_never_wins.py::test_every_exempt_key_is_recomputable_from_the_file_at_a_runtime_
lineno``, which also ships the forged-key control proving the recomputation can tell a wrong key
apart.
"""

from __future__ import annotations

from tests.architectural._home_pin_scan import Exempt, MemberKey

__all__ = ["OWNER_KEY", "RETAINED_PIN_PROBE_KEY", "E"]

#: The canonical owner (FR-005), ``tests/conftest.py::canonical_home``.
OWNER_KEY: MemberKey = (
    "conftest.py",
    "canonical_home",
    "monkeypatch . setenv ( , str ( home ) )",
)

#: The single retained-pin probe (FR-011), ``test_home_owner_never_wins.py::retained_pin_home``.
RETAINED_PIN_PROBE_KEY: MemberKey = (
    "architectural/test_home_owner_never_wins.py",
    "retained_pin_home",
    "monkeypatch . setenv ( , str ( home ) )",
)

#: **Fixed arity BY TYPE.** ``tuple[Exempt, Exempt]`` — a third entry is a ``mypy --strict`` error,
#: not a one-line literal (FR-004, SC-005). ``why`` is prose and entitles nothing the type does not
#: already grant.
E: tuple[Exempt, Exempt] = (
    Exempt(
        key=OWNER_KEY,
        why=(
            "The canonical owner is itself a member of the behaviour class it exists to own "
            "(FR-005), so `discovered == census u E` is the only correct accounting: excluding it "
            "by predicate would require narrowing the silhouette, which C-004 forbids. It is kept "
            "out of the census because C-007 makes the census monotonically non-increasing and "
            "the owner must exist forever."
        ),
    ),
    Exempt(
        key=RETAINED_PIN_PROBE_KEY,
        why=(
            "The one real-tree probe that must keep its OWN pin to demonstrate the owner never "
            "wins (FR-011, SC-012 limb 2). Keeping the pin is what makes it a class member; "
            "removing the pin would remove the demonstration. Its non-member sibling "
            "`probe_home_pin` carries the falsifiability and costs no slot."
        ),
    ),
)
