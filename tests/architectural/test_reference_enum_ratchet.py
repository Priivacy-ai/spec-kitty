"""Reference-kind enum ratchet — pins ADR FR-006 / NFR-001 / SC-005.

WP06 of mission ``doctrine-silence-guards-01KYFV7Q``.

Why this exists
----------------
Four doctrine schemas each declare a ``<kind>_reference`` definition whose
``properties.type.enum`` names every doctrine artefact kind that definition's
artefact may reference: :data:`_REFERENCE_TARGETS` below. The enum is meant to be
frozen — widening it re-opens exactly the kind-vocabulary drift the doctrine layer
exists to close (DIRECTIVE_043) — but before this module the freeze was **only a
comment**. Nothing re-read the schemas and compared them against anything, so a
member added to any of the four enums shipped green. That is the silence this
mission closes; a comment did not stop the enum-widening attempt that started this
programme, which is the direct motivation for FR-006.

The four targets, derived once from the shipped schemas (WP05, ``remediation/
doctrine-silence-guards`` @ the commit this baseline was pinned from) and never
re-derived at test time:

* ``directive.schema.yaml`` :: ``directive_reference`` — 12 members
* ``tactic.schema.yaml``    :: ``tactic_reference``     — 7 members
* ``procedure.schema.yaml`` :: ``procedure_reference``  — 12 members
* ``paradigm.schema.yaml``  :: ``paradigm_reference``   — 7 members

⚠️ **The 12-vs-7 split is a generator artifact, not a reference-legality policy.**
An earlier revision of this docstring said a paradigm "cannot legally reference"
``agent_profile``/``mission_step_contract``, so the narrower set was intentional.
**That is false**, and review traced it:

* ``paradigms/models.py`` declares ``ParadigmReference.type: ArtifactKind`` and its
  own docstring says *"``type`` accepts the full ``ArtifactKind`` vocabulary, so a
  paradigm may reference a tactic, procedure, agent profile, etc."* The model
  permits exactly what the generated schema forbids.
* ``scripts/generate_schemas.py`` picks the inlining path with
  ``enum_defs - {"ArtifactKind"}`` — i.e. on whether the model happens to declare
  some **unrelated** ``StrEnum``. ``Directive`` has ``Enforcement`` and
  ``Procedure`` has ``ActorRole`` (2 declarations each) → full 12. ``Tactic`` and
  ``Paradigm`` have none → routed through ``_inline_artifact_kind_refs`` and its
  7-member ``_REFERENCE_KINDS``. Nothing about reference semantics enters that
  decision.
* ``tactic_reference`` was already 7 before this mission and WP05 never touched it —
  same quirk, pre-existing.

So the split has **never been adjudicated**. This ratchet freezes it on one side,
which is the safe direction under C-001 (never widen), but a future reader must
not read the 7 as a decision. Tracked upstream as
`#2976 <https://github.com/Priivacy-ai/spec-kitty/issues/2976>`_; resolving it
means either making the generator consistent across all four kinds or getting an
actual ruling on what paradigms and tactics may reference.

A frozen baseline, not a live re-derivation
--------------------------------------------
:data:`_BASELINE` is a **literal, committed** dict of the member sets above. A
ratchet that re-reads the same schemas at test time and compares them to
themselves cannot fail — the charter's ``frozen-baseline-shrink-only-ratchet``
tactic is explicit that the baseline must be a committed value, not derived from
the thing being checked. Growth (a member present in the schema but absent from
the committed baseline) fails the gate outright, mirroring the tactic's
"growth fails" rule applied at the granularity of set membership rather than a
bare count — a swap-one-member-for-another edit keeps the count constant while
still being exactly the drift this gate exists to catch. Shrinkage (a baseline
member no longer present in the schema) only warns, exactly as the tactic
specifies, so legitimate narrowing (like WP05's paradigm-enum trim above) is not
blocked.

Non-vacuity (NFR-001)
----------------------
:class:`TestRatchetNonVacuity` plants a real violation — the frozen baseline plus
one smuggled member, written to a ``tmp_path`` schema fixture — and asserts the
gate rejects it. It calls **the same** :func:`_enum_members` /
:func:`_grown_members` pair the shipped-tree assertion below uses, differing only
in which schema path it is pointed at. A self-mutation test that reimplements the
walk inline would stay green forever while this walk rotted; this is the WP01
rejection finding this mission carries forward.

Concrete floor
--------------
An absence assertion (``not grown``) passes vacuously on a parse that silently
found nothing, so :func:`_enum_members` returning an empty set must itself be
loud. ``test_enum_resolves_to_a_non_empty_set`` asserts each of the four targets
resolves to a non-empty member set *before* any growth comparison runs, and
``test_ratchet_covers_exactly_four_distinct_targets`` asserts the target list
itself has not silently collapsed to fewer than four distinct schema/definition
pairs.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "src" / "doctrine" / "schemas"

#: (schema filename, ``definitions`` key) for each of the four ``<kind>_reference.type``
#: enums. Order matches the docstring table above.
_REFERENCE_TARGETS: tuple[tuple[str, str], ...] = (
    ("directive.schema.yaml", "directive_reference"),
    ("tactic.schema.yaml", "tactic_reference"),
    ("procedure.schema.yaml", "procedure_reference"),
    ("paradigm.schema.yaml", "paradigm_reference"),
)

#: Frozen baseline. Literal, committed member sets — never re-derived from the
#: schemas at test time (frozen-baseline-shrink-only-ratchet tactic). Widening any
#: of these sets is a deliberate edit requiring an ADR amendment, not a schema PR.
_BASELINE: dict[str, frozenset[str]] = {
    "directive_reference": frozenset(
        {
            "directive",
            "tactic",
            "styleguide",
            "toolguide",
            "paradigm",
            "procedure",
            "agent_profile",
            "mission_step_contract",
            "template",
            "asset",
            "glossary_pack",
            "anti_pattern",
        }
    ),
    "tactic_reference": frozenset(
        {
            "directive",
            "tactic",
            "styleguide",
            "toolguide",
            "paradigm",
            "procedure",
            "template",
        }
    ),
    "procedure_reference": frozenset(
        {
            "directive",
            "tactic",
            "styleguide",
            "toolguide",
            "paradigm",
            "procedure",
            "agent_profile",
            "mission_step_contract",
            "template",
            "asset",
            "glossary_pack",
            "anti_pattern",
        }
    ),
    "paradigm_reference": frozenset(
        {
            "directive",
            "tactic",
            "styleguide",
            "toolguide",
            "paradigm",
            "procedure",
            "template",
        }
    ),
}


def _enum_members(schema_path: Path, definition_key: str) -> frozenset[str]:
    """Return the ``<definition_key>.properties.type.enum`` member set from *schema_path*.

    This is the **only** extraction path in this module. Both the shipped-tree
    assertion below and the self-mutation proof in :class:`TestRatchetNonVacuity`
    call this same function, differing only in which *schema_path* they point at
    (NFR-001).

    Returns an empty set for any shape mismatch (missing key, wrong type at any
    level) rather than raising, so a malformed fixture is a clean negative case in
    the non-vacuity tests. The shipped-tree assertion separately asserts this never
    returns empty for a real target, which is what keeps that leniency from being a
    silent vacuous-pass path.
    """
    raw: object = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return frozenset()
    definitions = raw.get("definitions")
    if not isinstance(definitions, dict):
        return frozenset()
    definition = definitions.get(definition_key)
    if not isinstance(definition, dict):
        return frozenset()
    properties = definition.get("properties")
    if not isinstance(properties, dict):
        return frozenset()
    type_property = properties.get("type")
    if not isinstance(type_property, dict):
        return frozenset()
    enum = type_property.get("enum")
    if not isinstance(enum, list):
        return frozenset()
    return frozenset(str(member) for member in enum)


def _grown_members(current: frozenset[str], baseline: frozenset[str]) -> frozenset[str]:
    """Members present in *current* but absent from *baseline* — real enum growth."""
    return current - baseline


def _shrunk_members(current: frozenset[str], baseline: frozenset[str]) -> frozenset[str]:
    """Members present in *baseline* but absent from *current* — legitimate narrowing."""
    return baseline - current


class TestRatchetTargetsAreWellFormed:
    """Positive floor: prove the ratchet is actually looking at four distinct places.

    A parametrized test that silently collapsed to fewer entries (a copy-paste
    duplicate, a typo'd definition key shadowing another target) would still show
    green on every remaining case. Assert the target list's own shape before
    trusting anything it drives.
    """

    def test_ratchet_covers_exactly_four_distinct_targets(self) -> None:
        assert {filename for filename, _ in _REFERENCE_TARGETS} == {
            "directive.schema.yaml",
            "tactic.schema.yaml",
            "procedure.schema.yaml",
            "paradigm.schema.yaml",
        }, "a schema file is duplicated or missing — one of the four enums is not being checked"
        assert {key for _, key in _REFERENCE_TARGETS} == {
            "directive_reference",
            "tactic_reference",
            "procedure_reference",
            "paradigm_reference",
        }, (
            "two targets share a definition key, or one is misspelled — a "
            "misspelled key resolves to zero members in a schema that is then "
            "never checked"
        )
        # A wholesale swap (`directive.schema.yaml` paired with
        # `tactic_reference` and vice versa) keeps both sets above intact while
        # every enum is read out of the wrong file, so pin the pairing too.
        assert all(
            key == f"{filename.removesuffix('.schema.yaml')}_reference"
            for filename, key in _REFERENCE_TARGETS
        ), f"a target pairs a schema file with another kind's key: {_REFERENCE_TARGETS}"

    def test_baseline_has_an_entry_for_every_target(self) -> None:
        target_keys = {key for _, key in _REFERENCE_TARGETS}
        assert set(_BASELINE) == target_keys, (
            f"baseline keys {sorted(_BASELINE)} do not match ratchet targets "
            f"{sorted(target_keys)}"
        )


class TestShippedEnumsAreFrozen:
    """The shipped-tree assertion: each enum must match its frozen baseline."""

    @pytest.mark.parametrize("filename, definition_key", _REFERENCE_TARGETS)
    def test_enum_resolves_to_a_non_empty_set(self, filename: str, definition_key: str) -> None:
        """Concrete floor: a broken parse returns an empty set, which must be loud,
        not a silent pass on the growth check below."""
        current = _enum_members(_SCHEMAS_DIR / filename, definition_key)
        assert current, f"{filename}::{definition_key} resolved to zero enum members"

    @pytest.mark.parametrize("filename, definition_key", _REFERENCE_TARGETS)
    def test_enum_has_not_grown_past_the_frozen_baseline(
        self, filename: str, definition_key: str
    ) -> None:
        current = _enum_members(_SCHEMAS_DIR / filename, definition_key)
        baseline = _BASELINE[definition_key]
        grown = _grown_members(current, baseline)
        assert not grown, (
            f"{definition_key} enum grew past its frozen baseline: {sorted(grown)}. "
            "Widening a reference-kind enum requires a deliberate baseline edit "
            "with an ADR amendment, not a schema PR alone."
        )
        shrunk = _shrunk_members(current, baseline)
        if shrunk:
            warnings.warn(
                f"{definition_key} enum shrank from its frozen baseline "
                f"(missing: {sorted(shrunk)}); consider locking in the narrower "
                "set in this module's _BASELINE.",
                stacklevel=2,
            )


class TestRatchetNonVacuity:
    """Self-mutation proofs (NFR-001): plant the real violation shape and prove RED.

    Every test here calls :func:`_enum_members` / :func:`_grown_members` — the same
    functions :class:`TestShippedEnumsAreFrozen` calls against the real schemas —
    against a planted ``tmp_path`` fixture instead. Only the input changes.
    """

    def _write_schema(self, tmp_path: Path, definition_key: str, members: list[str]) -> Path:
        path = tmp_path / "planted.schema.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "definitions": {
                        definition_key: {
                            "properties": {"type": {"enum": members}},
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_planted_smuggled_member_is_flagged_as_growth(self, tmp_path: Path) -> None:
        definition_key = "directive_reference"
        baseline = _BASELINE[definition_key]
        planted = self._write_schema(
            tmp_path, definition_key, [*sorted(baseline), "smuggled_kind"]
        )
        current = _enum_members(planted, definition_key)
        assert _grown_members(current, baseline) == frozenset({"smuggled_kind"})

    def test_planted_baseline_exact_match_is_not_flagged(self, tmp_path: Path) -> None:
        """The gate must not always fire — an unchanged enum must pass cleanly."""
        definition_key = "tactic_reference"
        baseline = _BASELINE[definition_key]
        planted = self._write_schema(tmp_path, definition_key, sorted(baseline))
        current = _enum_members(planted, definition_key)
        assert _grown_members(current, baseline) == frozenset()

    def test_planted_narrowed_enum_is_shrinkage_not_growth(self, tmp_path: Path) -> None:
        """Removing a member is legitimate narrowing (warn), never a growth failure."""
        definition_key = "procedure_reference"
        baseline = _BASELINE[definition_key]
        narrowed = sorted(baseline)[:-1]
        planted = self._write_schema(tmp_path, definition_key, narrowed)
        current = _enum_members(planted, definition_key)
        assert _grown_members(current, baseline) == frozenset()
        assert _shrunk_members(current, baseline) == {sorted(baseline)[-1]}

    def test_malformed_schema_resolves_to_empty_not_a_silent_pass(self, tmp_path: Path) -> None:
        """A schema shape :func:`_enum_members` cannot parse returns empty — and the
        shipped-tree floor test is what turns that into a loud failure rather than a
        vacuous pass. Prove the empty-return half here."""
        definition_key = "paradigm_reference"
        path = tmp_path / "malformed.schema.yaml"
        path.write_text(yaml.safe_dump({"definitions": {}}), encoding="utf-8")
        assert _enum_members(path, definition_key) == frozenset()
