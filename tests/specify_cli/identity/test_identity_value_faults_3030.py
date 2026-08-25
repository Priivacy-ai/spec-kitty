"""An unusable recorded identity *value* must not crash the policy read (#3030 FR-024).

FR-023 fenced the top-level *shape* of ``.kittify/config.yaml``. A perfectly valid
mapping whose ``project.uuid`` cannot be parsed sailed straight past that fence,
because ``ProjectIdentity.from_dict`` called ``UUID(uuid_str)`` **outside**
``load_identity``'s ``try/except`` — which wrapped only the YAML parse. A merge
conflict marker in a tracked, hand-edited file is a realistic route to it.

Probed as a *set* (not the three shapes that were reported), across every field
``from_dict`` reads, through read, write and both routing entry points, with a
valid-config positive control that must pass. Measured **before** the fix:

============  ====================================================  ==========================
``project.``  before                                                after
============  ====================================================  ==========================
``uuid``      11 of 13 shapes RAISED out of ``load_identity``,       no identity, no raise
              ``resolve_identity``, ``ensure_identity`` and BOTH     (or the value, where it
              routing entry points, in three flavours:               is understandable:
              ``ValueError`` (``not-a-uuid``, ``<<<<<<< HEAD``,      a padded uuid is
              a padded uuid, whitespace-only), ``AttributeError``    accepted, whitespace-
              (``42``, ``1.5``, ``true``, mapping, sequence, an      only is absence)
              all-digit int), ``TypeError`` (``2026-07-30``).
              ``""``/``~`` were already absence.
``repo_slug`` ``load_identity`` did NOT raise — it handed a         no identity (container)
              non-``str`` onward, and **both routing entry points**  or text (scalar); the
              then died in someone else's code: ``TypeError:         gate answers
              argument of type 'int' is not iterable`` and
              ``TypeError: unhashable type: 'CommentedMap'``.
              7 of 13 shapes. **Not previously reported.**
``slug``,     no crash on any probed path, but a ``dict`` /          None-or-``str``,
``node_id``,  ``list`` / ``date`` / ``int`` was stored in a field    always
``build_id``  annotated ``str | None`` and written back to disk
============  ====================================================  ==========================

The fix is at the parse — one site for ``load_identity``'s seven production callers —
and it gives the FR-022/FR-023 answer rather than a fourth one: **reading** a record
that cannot be understood yields no identity and never raises, **writing** over it is
refused with ``ConfigNotUnderstoodError``, which ``ensure_identity`` degrades.

Two decisions this file pins, both deliberate:

* A uuid is **accepted after stripping** (and after YAML's implicit typing is undone),
  not treated as a fault. ``sync/consent.py`` already reads the same key as
  ``str(raw).strip() or None``; making identity call it a fault would leave the two
  modules disagreeing about which uuid a config declares — the two-notions-one-
  function-apart pathology (C-003). Whitespace-only and ``""`` stay *absence* for the
  same reason, and the parse still keeps ``''``/whitespace unpersistable (FR-017).
* YAML's implicit typing is undone rather than rejected: ``node_id: 123456789012``
  and a dash-less 32-hex ``uuid`` are legitimate values that YAML resolves to ``int``.
  Containers are a genuine fault — no text was recorded there, and ``str()`` of a
  ``CommentedMap`` would ship a Python repr upstream as the project's identity.
"""
from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest

from specify_cli.identity.project import (
    ConfigNotUnderstoodError,
    ProjectIdentity,
    atomic_write_config,
    ensure_identity,
    load_identity,
    resolve_identity,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_UUID = "11111111-1111-1111-1111-111111111111"

#: Values that cannot be understood as a uuid. YAML renders on the right.
UNUSABLE_UUIDS = {
    "malformed_hex": '"not-a-uuid"',
    "conflict_marker": '"<<<<<<< HEAD"',
    "integer": "42",
    "float": "1.5",
    "bool": "true",
    "date_scalar": "2026-07-30",
    "nested_mapping": "{a: b}",
    "sequence": "[a, b]",
    "digits_only": "123456789012",
}

#: Absence, not a fault: nothing was recorded. Must keep minting (a denial on
#: absence would deny every delivery on the machine).
ABSENT_UUIDS = {
    "empty_string": '""',
    "whitespace_only": '"   "',
    "null": "~",
}

#: Understandable after stripping / after undoing YAML's implicit typing.
ACCEPTED_UUIDS = {
    "padded": f'" {_UUID} "',
    "uppercase": _UUID.upper(),
    "dashless_32_hex_read_as_int": "11111111111111111111111111111111",
}

#: The text fields. ``uuid`` is excluded: it has its own tables above.
TEXT_FIELDS = ("slug", "node_id", "repo_slug", "build_id")

#: No text was recorded — a fault for every field, ``uuid`` included.
CONTAINER_VALUES = {
    "nested_mapping": "{a: b}",
    "sequence": "[a, b]",
}

#: YAML resolved the operator's text to another scalar type; ``str`` recovers it.
COERCED_TEXT = {
    "integer": ("42", "42"),
    "digits_only": ("123456789012", "123456789012"),
    "float": ("1.5", "1.5"),
    "date_scalar": ("2026-07-30", "2026-07-30"),
    "bool": ("true", None),  # ``str(True)`` mangles the text; only the type is pinned
}

VALID = (
    "project:\n"
    f"  uuid: {_UUID}\n"
    "  slug: demo\n"
    "  node_id: abc123abc123\n"
    "  build_id: 22222222-2222-2222-2222-222222222222\n"
)


def _config(tmp_path: Path, case: str, body: str) -> Path:
    """Write *body* to a config.yaml in a directory of its own.

    Per-case directories are load-bearing, not hygiene: ``ensure_identity`` WRITES,
    so one case's regeneration in a shared directory would mask the next case's
    defect (FR-023's fixture made the same point).
    """
    kittify = tmp_path / case / ".kittify"
    kittify.mkdir(parents=True)
    path = kittify / "config.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _project(field: str, value: str, *, with_uuid: bool = True) -> str:
    """A config whose ``project`` section records *field* as *value*."""
    body = "project:\n"
    if with_uuid and field != "uuid":
        body += f"  uuid: {_UUID}\n"
    return body + f"  {field}: {value}\n"


class TestReadingAnUnusableUuid:
    @pytest.mark.parametrize("case", sorted(UNUSABLE_UUIDS))
    def test_load_identity_yields_no_identity_rather_than_raising(
        self, tmp_path: Path, case: str
    ) -> None:
        """Its docstring promises graceful handling; nine shapes raised instead."""
        path = _config(tmp_path, case, _project("uuid", UNUSABLE_UUIDS[case]))

        assert load_identity(path) == ProjectIdentity(), (
            "a recorded identity that cannot be understood carries no identity"
        )

    @pytest.mark.parametrize("case", sorted(UNUSABLE_UUIDS))
    def test_the_read_only_resolver_answers_and_writes_nothing(
        self, tmp_path: Path, case: str
    ) -> None:
        """``resolve_identity`` is on side-effect-free paths (sync, accept)."""
        path = _config(tmp_path, case, _project("uuid", UNUSABLE_UUIDS[case]))
        before = path.read_bytes()

        identity = resolve_identity(path.parent.parent)

        assert identity.project_uuid is None, "no identity can be resolved from it"
        assert path.read_bytes() == before, "the read-only resolver must not write"

    @pytest.mark.parametrize("case", sorted(ABSENT_UUIDS))
    def test_an_unrecorded_uuid_stays_absence(self, tmp_path: Path, case: str) -> None:
        """Regression guard. Absence must never become a fault.

        ``sync/consent.py`` reads the same key as ``str(raw).strip() or None``, so
        blank and whitespace-only mean "nothing recorded" in both modules.
        """
        path = _config(tmp_path, case, _project("uuid", ABSENT_UUIDS[case]))

        assert load_identity(path) == ProjectIdentity()

    @pytest.mark.parametrize("case", sorted(ACCEPTED_UUIDS))
    def test_an_understandable_uuid_is_accepted_and_canonicalised(
        self, tmp_path: Path, case: str
    ) -> None:
        path = _config(tmp_path, case, _project("uuid", ACCEPTED_UUIDS[case]))

        assert load_identity(path).project_uuid == UUID(_UUID)

    def test_a_valid_config_still_loads(self, tmp_path: Path) -> None:
        """Positive control. Without it, "no crash" is indistinguishable from
        "the harness never reached the code" — which is exactly how FR-024's first
        probe produced five meaningless OKs."""
        path = _config(tmp_path, "valid", VALID)

        identity = load_identity(path)

        assert identity.project_uuid == UUID(_UUID)
        assert identity.project_slug == "demo"
        assert identity.node_id == "abc123abc123"
        assert identity.build_id == "22222222-2222-2222-2222-222222222222"


class TestEveryRecordedFieldIsTextOrAbsent:
    """``uuid`` was not the only field that could be handed a hostile type.

    ``repo_slug`` was the one that mattered: ``load_identity`` accepted a non-``str``
    happily and both routing entry points then died on it in code that had every
    right to assume a string.
    """

    @pytest.mark.parametrize("field", TEXT_FIELDS)
    @pytest.mark.parametrize("case", sorted(CONTAINER_VALUES))
    def test_a_container_where_text_belongs_is_a_fault(
        self, tmp_path: Path, field: str, case: str
    ) -> None:
        path = _config(
            tmp_path, f"{field}-{case}", _project(field, CONTAINER_VALUES[case])
        )

        assert load_identity(path) == ProjectIdentity(), (
            "a Python repr is not the project's identity"
        )

    @pytest.mark.parametrize("field", TEXT_FIELDS)
    @pytest.mark.parametrize("case", sorted(COERCED_TEXT))
    def test_yaml_implicit_typing_is_undone_rather_than_rejected(
        self, tmp_path: Path, field: str, case: str
    ) -> None:
        """An all-digit ``node_id`` is a legitimate value YAML resolves to ``int``.

        Rejecting it would deny a healthy checkout; ``str`` recovers the operator's
        text exactly for the realistic cases.
        """
        yaml_value, expected = COERCED_TEXT[case]
        path = _config(tmp_path, f"{field}-{case}", _project(field, yaml_value))

        value = getattr(
            load_identity(path),
            {"slug": "project_slug", "node_id": "node_id"}.get(field, field),
        )

        assert isinstance(value, str), f"{field} is annotated str | None"
        if expected is not None:
            assert value == expected

    @pytest.mark.parametrize("field", ("uuid", *TEXT_FIELDS))
    @pytest.mark.parametrize(
        "index,yaml_value",
        list(
            enumerate(
                sorted(
                    {
                        *UNUSABLE_UUIDS.values(),
                        *CONTAINER_VALUES.values(),
                        *ABSENT_UUIDS.values(),
                    }
                )
            )
        ),
    )
    def test_no_shape_of_any_field_produces_a_wrongly_typed_identity(
        self, tmp_path: Path, field: str, index: int, yaml_value: str
    ) -> None:
        """The class-closing invariant, asserted over the whole probed matrix.

        Whatever a config records, an identity that comes back has a ``UUID``
        ``project_uuid`` and ``str`` text fields, or ``None``. Nothing else may leave
        this parse — a wrongly typed field is the shape that killed routing from
        inside someone else's function.
        """
        path = _config(tmp_path, f"{field}-{index}", _project(field, yaml_value))

        identity = load_identity(path)

        assert identity.project_uuid is None or isinstance(identity.project_uuid, UUID)
        for attr in ("project_slug", "node_id", "repo_slug", "build_id"):
            value = getattr(identity, attr)
            assert value is None or isinstance(value, str), f"{attr} is {type(value)}"


# ``TestThePolicyGateAnswersInsteadOfCrashing`` retired with its subject: its two
# entry points (``sync.routing.is_sync_enabled_for_checkout`` /
# ``resolve_checkout_sync_routing``) were the hosted-sync consent gate, deleted with
# the sync transport in issue #5. The parse-level fault classes above survive — a
# broken value still yields a typed-or-None identity rather than a crash.


class TestWritingOverAnUnusableIdentityRecord:
    @pytest.mark.parametrize("case", sorted(UNUSABLE_UUIDS))
    def test_atomic_write_refuses_rather_than_replacing_the_record(
        self, tmp_path: Path, case: str
    ) -> None:
        """Overwriting a corrupt uuid is not harmless: the uuid is the key other
        stores reference. The journal's ``project_uuid`` rows, the ledger and the
        machine consent index all keep the OLD value, so silently minting a new one
        orphans the project's own events — including from the purge that is supposed
        to erase them (FR-016/FR-017).
        """
        path = _config(tmp_path, case, _project("uuid", UNUSABLE_UUIDS[case]))
        before = path.read_bytes()

        with pytest.raises(ConfigNotUnderstoodError) as excinfo:
            atomic_write_config(path, ProjectIdentity().with_defaults(path.parent.parent))

        assert "config.yaml" in str(excinfo.value), "the operator needs the path"
        assert path.read_bytes() == before, "the record they could not read survives"
        assert [p.name for p in path.parent.iterdir()] == ["config.yaml"], (
            "no temp file may be left behind: the refusal happens before mkstemp"
        )

    @pytest.mark.parametrize("field", TEXT_FIELDS)
    def test_atomic_write_refuses_over_an_unusable_text_field_too(
        self, tmp_path: Path, field: str
    ) -> None:
        path = _config(tmp_path, f"write-{field}", _project(field, "{a: b}"))
        before = path.read_bytes()

        with pytest.raises(ConfigNotUnderstoodError):
            atomic_write_config(path, ProjectIdentity().with_defaults(path.parent.parent))

        assert path.read_bytes() == before

    @pytest.mark.parametrize("case", sorted(UNUSABLE_UUIDS))
    def test_ensure_identity_degrades_instead_of_crashing(
        self, tmp_path: Path, case: str
    ) -> None:
        """``ensure_identity``'s callers (``init``, ``tracker``, history-import) may
        not learn a new exception — a new error nobody catches is a crash moved.
        """
        path = _config(tmp_path, case, _project("uuid", UNUSABLE_UUIDS[case]))
        before = path.read_bytes()

        identity = ensure_identity(path.parent.parent)

        assert identity.is_complete, "callers depend on a usable identity"
        assert path.read_bytes() == before, "the file they could not read survives"
        assert [p.name for p in path.parent.iterdir()] == ["config.yaml"]

    def test_the_operator_is_told_the_cause_and_the_field(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A denial whose reported cause is wrong sends the operator to the wrong
        remedy — the misdirected-cause class this mission keeps closing. The file
        here is perfectly writable, so "not writable" would be a lie, and naming the
        field is what turns "fix your config" into an actionable line number.
        """
        path = _config(tmp_path, "cause", _project("uuid", '"<<<<<<< HEAD"'))

        with caplog.at_level("WARNING"):
            ensure_identity(path.parent.parent)

        stderr = capsys.readouterr().err
        assert "could not be understood" in stderr
        assert "not writable" not in stderr
        assert "project.uuid" in caplog.text, "the operator needs the field, not just the file"

    @pytest.mark.parametrize("case", sorted(ABSENT_UUIDS))
    def test_an_unrecorded_uuid_still_mints_and_persists(
        self, tmp_path: Path, case: str
    ) -> None:
        """Absence must stay absence in the write direction too — and the minted
        value must be a real uuid. ``''`` and whitespace uuids are the populations
        FR-017 found unreachable by any purge; they stay unpersistable because the
        parse never lets a blank through as a value.
        """
        path = _config(tmp_path, case, _project("uuid", ABSENT_UUIDS[case]))

        identity = ensure_identity(path.parent.parent)

        assert identity.is_complete
        persisted = load_identity(path).project_uuid
        assert persisted == identity.project_uuid
        assert isinstance(persisted, UUID), "a blank uuid may never be persisted"
        assert str(persisted).strip() == str(persisted)

    def test_a_padded_uuid_is_persisted_canonically(self, tmp_path: Path) -> None:
        """Accepted-after-stripping, so the write path proceeds and canonicalises —
        it does not refuse, and it does not round-trip the whitespace."""
        path = _config(tmp_path, "padded-write", f'project:\n  uuid: " {_UUID} "\n')

        identity = ensure_identity(path.parent.parent)

        assert identity.project_uuid == UUID(_UUID)
        assert f"uuid: {_UUID}\n" in path.read_text(encoding="utf-8"), (
            "the persisted value carries neither the padding nor its quotes"
        )
        assert load_identity(path).project_uuid == UUID(_UUID)

    def test_atomic_write_still_merges_into_a_valid_document(self, tmp_path: Path) -> None:
        """Regression guard: the ordinary merge must be untouched."""
        path = _config(
            tmp_path, "merge", f"sync:\n  enabled: false\nproject:\n  uuid: {_UUID}\n"
        )

        atomic_write_config(
            path, load_identity(path).with_defaults(path.parent.parent)
        )

        text = path.read_text(encoding="utf-8")
        assert "enabled: false" in text, "an unrelated section must survive"
        assert _UUID in text, "the uuid that WAS understandable is kept"
