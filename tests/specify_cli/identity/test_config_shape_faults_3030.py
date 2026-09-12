"""A structurally invalid ``config.yaml`` must not crash identity (#3030 FR-022 follow-up).

``load_identity`` did ``config.get("project", {})`` on whatever YAML returned. YAML
documents are not all mappings, so every non-mapping top level raised
``AttributeError`` out of a function whose docstring promises it "handles malformed
config gracefully". Found while fencing ``sync/routing.py`` off from it: a list-shaped
config crashed the sync policy gate instead of answering a boolean.

Probed before fixing, and it was not one shape but four — any non-mapping node:

===================  ==========================================  ============================
top-level YAML       ``load_identity`` before                    write path before
===================  ==========================================  ============================
``- a\\n- list``      ``AttributeError`` (``CommentedSeq``)        ``AttributeError``
``hello``            ``AttributeError`` (``str``)                 ``AttributeError``
``42``               ``AttributeError`` (``int``)                 ``AttributeError``
``"a string"``       ``AttributeError`` (``str``)                 ``AttributeError``
empty file           already handled (``or {}``)                  rewritten (mints)
comments only        already handled (``or {}``)                  rewritten (mints)
unparseable YAML     already handled (``except``)                 ``ParserError`` escapes
``project: scalar``  already handled (``isinstance``)             rewritten (mints)
===================  ==========================================  ============================

Two properties follow, and they are the same rule in the two directions:

* **Reading** a file that cannot be understood yields *no identity*, never an
  exception — the answer ``load_identity`` already gave for a parse error, and the
  same notion ``sync/consent.py`` encodes as ``ConfigReadFault(kind="unparseable",
  detail="top-level content is not a mapping")``. One notion, not two.
* **Writing** over a file that could not be understood is refused. An identity
  regenerated onto an unreadable file would replace the operator's ``sync.enabled:
  false``, their comments and every other section with an identity-only document —
  destroying exactly what could not be read.
"""
from __future__ import annotations

from pathlib import Path

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

#: Every non-mapping top-level shape found by probing, plus the two that already
#: worked. Kept as one table so a fifth shape is added here rather than in a fifth
#: near-duplicate test.
NON_MAPPING_SHAPES = {
    "sequence": "- just\n- a\n- list\n",
    "bare_scalar_string": "hello\n",
    "scalar_int": "42\n",
    "quoted_string_document": '"a string document"\n',
}

ALREADY_ABSENCE_SHAPES = {
    "empty_file": "",
    "comments_only": "# nothing but a comment\n",
}

_VALID = "project:\n  uuid: 11111111-1111-1111-1111-111111111111\n  slug: s\n  node_id: n\n"


def _config(tmp_path: Path, case: str, body: str) -> Path:
    """Write *body* to a config.yaml in a directory of its own.

    Per-case directories are load-bearing, not hygiene: ``ensure_identity`` WRITES,
    so one case's regeneration in a shared directory would mask the next case's
    defect.
    """
    kittify = tmp_path / case / ".kittify"
    kittify.mkdir(parents=True)
    path = kittify / "config.yaml"
    path.write_text(body, encoding="utf-8")
    return path


class TestReadingAStructurallyInvalidConfig:
    @pytest.mark.parametrize("case", sorted(NON_MAPPING_SHAPES))
    def test_a_non_mapping_document_yields_no_identity_rather_than_raising(
        self, tmp_path: Path, case: str
    ) -> None:
        """Its docstring promises graceful handling; four shapes did not get it."""
        path = _config(tmp_path, case, NON_MAPPING_SHAPES[case])

        identity = load_identity(path)

        assert identity == ProjectIdentity(), (
            "a file that exists and cannot be understood carries no identity"
        )

    @pytest.mark.parametrize("case", sorted(ALREADY_ABSENCE_SHAPES))
    def test_an_empty_document_is_absence_and_keeps_working(
        self, tmp_path: Path, case: str
    ) -> None:
        """Regression guard: ``yaml.load() or {}`` already handled these."""
        path = _config(tmp_path, case, ALREADY_ABSENCE_SHAPES[case])

        assert load_identity(path) == ProjectIdentity()

    def test_a_valid_config_still_loads(self, tmp_path: Path) -> None:
        path = _config(tmp_path, "valid", _VALID)

        assert str(load_identity(path).project_uuid) == (
            "11111111-1111-1111-1111-111111111111"
        )

    @pytest.mark.parametrize("case", sorted(NON_MAPPING_SHAPES))
    def test_the_read_only_resolver_answers_instead_of_crashing(
        self, tmp_path: Path, case: str
    ) -> None:
        """``resolve_identity`` is on side-effect-free policy paths (sync, accept).

        This is the shape that reached ``sync/routing.py``: a policy read that must
        answer must not raise. It also must not have written anything on the way.
        """
        path = _config(tmp_path, case, NON_MAPPING_SHAPES[case])
        before = path.read_bytes()

        identity = resolve_identity(path.parent.parent)

        assert identity.project_uuid is None, "no identity can be resolved from it"
        assert path.read_bytes() == before, "the read-only resolver must not write"


class TestWritingOverAConfigThatCouldNotBeRead:
    @pytest.mark.parametrize("case", sorted(NON_MAPPING_SHAPES))
    def test_atomic_write_refuses_rather_than_replacing_the_document(
        self, tmp_path: Path, case: str
    ) -> None:
        """Refuse with a typed error, not an opaque ``AttributeError``/``TypeError``.

        ``atomic_write_config`` merges ``config["project"]`` into the loaded
        document. On a non-mapping document that subscript is meaningless — and the
        only way to "succeed" would be to discard the document, which is the
        operator's ``sync.enabled: false`` and everything else in the file.
        """
        path = _config(tmp_path, case, NON_MAPPING_SHAPES[case])
        before = path.read_bytes()

        with pytest.raises(ConfigNotUnderstoodError) as excinfo:
            atomic_write_config(path, ProjectIdentity().with_defaults(path.parent.parent))

        assert "config.yaml" in str(excinfo.value), "the operator needs the path"
        assert path.read_bytes() == before, "the unreadable document must survive"
        assert [p.name for p in path.parent.iterdir()] == ["config.yaml"], (
            "no temp file may be left behind"
        )

    def test_atomic_write_refuses_on_unparseable_yaml_too(self, tmp_path: Path) -> None:
        """The fifth crash, on the write path only.

        ``load_identity`` swallows a parse error, so ``ensure_identity`` decided the
        identity was missing and went on to write — where ``yaml.load`` raised
        ``ParserError`` straight through ``ensure_identity``'s ``except OSError``.
        """
        path = _config(tmp_path, "unparseable", "sync:\n  enabled: false\n  broken: [x\n")
        before = path.read_bytes()

        with pytest.raises(ConfigNotUnderstoodError):
            atomic_write_config(path, ProjectIdentity().with_defaults(path.parent.parent))

        assert path.read_bytes() == before

    def test_atomic_write_still_merges_into_a_valid_document(
        self, tmp_path: Path
    ) -> None:
        """Regression guard: the ordinary merge must be untouched.

        Other sections have to survive an identity write — that is the whole reason
        this function re-loads the file instead of overwriting it.
        """
        path = _config(
            tmp_path, "merge", "sync:\n  enabled: false\nproject:\n  slug: old\n"
        )

        atomic_write_config(
            path, ProjectIdentity(project_slug="new").with_defaults(path.parent.parent)
        )

        text = path.read_text(encoding="utf-8")
        assert "enabled: false" in text, "an unrelated section must survive"
        assert "slug: new" in text


class TestTheWriteBoundaryDegradesInsteadOfCrashing:
    @pytest.mark.parametrize("case", sorted(NON_MAPPING_SHAPES))
    def test_ensure_identity_returns_an_in_memory_identity(
        self, tmp_path: Path, case: str
    ) -> None:
        """``ensure_identity`` has four production callers (``init``, ``tracker``,
        history-import). None of them may learn a new exception — a new error nobody
        catches is a crash moved, not fixed. It degrades down the path it already
        has for an unwritable config: in-memory identity, file untouched, warned.
        """
        path = _config(tmp_path, case, NON_MAPPING_SHAPES[case])
        before = path.read_bytes()

        identity = ensure_identity(path.parent.parent)

        assert identity.is_complete, "callers depend on a usable identity"
        assert path.read_bytes() == before, "the file they could not read survives"

    def test_ensure_identity_degrades_on_unparseable_yaml_too(
        self, tmp_path: Path
    ) -> None:
        path = _config(tmp_path, "unparseable-ensure", "a: [unclosed\n")
        before = path.read_bytes()

        identity = ensure_identity(path.parent.parent)

        assert identity.is_complete
        assert path.read_bytes() == before

    def test_ensure_identity_still_persists_over_a_readable_config(
        self, tmp_path: Path
    ) -> None:
        """Regression guard: minting onto an understandable file still happens."""
        path = _config(tmp_path, "mintable", "project:\n  slug: keep-me\n")

        identity = ensure_identity(path.parent.parent)

        assert identity.is_complete
        assert "uuid:" in path.read_text(encoding="utf-8"), "identity was persisted"

    def test_atomic_write_preserves_operator_comments(self, tmp_path: Path) -> None:
        """The merge loads a ruamel ``CommentedMap``; it must not be rebuilt as a dict.

        Guarding a decision made while fixing the shape fault: the natural
        ``dict(loaded)`` normalisation would have satisfied the type annotation and
        silently stripped every comment in the operator's config on the next identity
        write. Nothing else in the suite would have noticed.
        """
        path = _config(
            tmp_path,
            "comments",
            "# keep me: this file is reviewed in diffs\nsync:\n  enabled: false\n",
        )

        atomic_write_config(
            path, ProjectIdentity().with_defaults(path.parent.parent)
        )

        text = path.read_text(encoding="utf-8")
        assert "# keep me: this file is reviewed in diffs" in text
        assert "enabled: false" in text

    def test_the_operator_is_told_the_real_cause_not_unwritable(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """"Config not writable" would send them to chmod; the fix is a YAML error.

        The file here IS writable. Reporting the wrong cause is the misdirected-denial
        class this mission keeps closing, so the in-memory warning names which of the
        two causes applies.
        """
        path = _config(tmp_path, "cause", "- a\n- list\n")

        ensure_identity(path.parent.parent)

        stderr = capsys.readouterr().err
        assert "could not be understood" in stderr
        assert "not writable" not in stderr
