"""One fault vocabulary, one meaning per token, across both producers (#3030 C-003).

The two modules that mint :class:`ConfigReadFault` used the same tokens for different
states, one module apart::

    sync/config.py    TOML syntax error      -> "unparseable"
                      OSError                -> "unreadable"
    sync/consent.py   open-OR-parse failure  -> "unreadable"
                      non-mapping top level  -> "unparseable"

So ``unreadable`` meant *could not open* on one surface and *could not open or parse*
on the other, and ``unparseable`` meant *bad syntax* on one and *parsed fine, wrong
shape* on the other. That is the "two representations of one invariant" C-003 forbids,
and it had already produced a false operator message: ``sync doctor`` advised *"it
parsed, but its top level is not a mapping"* over a ``not valid TOML`` fault. **That
wrong text passed the suite**, because an ``or`` across two acceptable wordings let
either satisfy the assertion. Nothing below spans two acceptable strings: each case
asserts the one correct token.

**Four kinds, not three.** The states are distinguished by the operator action that
resolves each, and no two of them share one:

===================================  ===============  ==========================
state                                token            what the operator does
===================================  ===============  ==========================
cannot be opened                     ``unreadable``   fix mode/ownership
opened, syntax does not parse        ``unparseable``  repair the syntax
parsed, top level is not a mapping   ``wrong_shape``  make the document a mapping
right shape, a value is unusable     ``unusable``     correct that field's value
===================================  ===============  ==========================

Collapsing the first two — the old ``consent.py`` reading — is what forced the doctor's
``unreadable`` advice to hedge ("a permission error means fix the mode; a parse error
means repair the syntax"), i.e. to be half wrong for every reader. Collapsing the
middle two — the old ``config.py`` reading of ``unparseable`` versus ``consent.py``'s —
is the divergence itself.

``config.py`` keeps both of its existing tokens with their existing meanings, because
they were already the coherent pair; ``consent.py`` moves onto them. ``config.py`` mints
no ``wrong_shape``: TOML's top level is a table by construction, so ``toml.load`` cannot
return a non-mapping and a branch for it would be unreachable code asserting a state
that cannot occur.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """One private ``SPEC_KITTY_HOME`` per case — the resolver writes on read."""
    root = tmp_path / "home"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(root))
    monkeypatch.setenv("HOME", str(root))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    return root


def _checkout(tmp_path: Path, text: str) -> Path:
    root = tmp_path / "checkout"
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    (root / ".kittify" / "config.yaml").write_text(text, encoding="utf-8")
    return root


def _local_kind(repo_root: Path) -> str | None:
    from specify_cli.sync.consent import project_local_consent_fault

    fault = project_local_consent_fault(repo_root)
    return None if fault is None else fault.kind


def _index_kind() -> str | None:
    from specify_cli.sync.config import SyncConfig

    fault = SyncConfig().read_project_consent(PROJECT).fault
    return None if fault is None else fault.kind


def _write_index(text: str) -> Path:
    from specify_cli.sync.config import SyncConfig

    path = SyncConfig().config_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# The project-local producer: four states, four tokens                         #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("state", "config_text", "expected"),
    [
        (
            "opened, syntax does not parse",
            "project:\n  uuid: [unclosed\n",
            "unparseable",
        ),
        (
            "parsed, top level is not a mapping",
            "- one\n- two\n",
            "wrong_shape",
        ),
        (
            "right shape, an unusable consent value",
            f'project:\n  uuid: {PROJECT}\nsync:\n  enabled: "false"\n',
            "unusable",
        ),
        (
            "right shape, an unusable uuid value",
            "project:\n  uuid: not-a-uuid\n",
            "unusable",
        ),
    ],
)
def test_each_project_local_state_gets_its_own_token(tmp_path: Path, state: str, config_text: str, expected: str) -> None:
    """One token per state, asserted exactly — no ``or`` across two acceptable answers.

    ``unparseable`` and ``wrong_shape`` were the same token before this: a YAML syntax
    error and a top-level list were both reported as things they were not.
    """
    assert _local_kind(_checkout(tmp_path, config_text)) == expected, f"the {state!r} state did not report {expected!r}"


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a chmod 000 file regardless")
def test_a_project_config_that_cannot_be_opened_is_unreadable(tmp_path: Path) -> None:
    """The fourth state, which needs a real permission fault rather than a stub.

    It shared ``unreadable`` with the syntax-error case before, which is why the
    doctor's advice for that token had to name two different remedies and be wrong
    about one of them every time it printed.
    """
    root = _checkout(tmp_path, f"project:\n  uuid: {PROJECT}\n")
    config = root / ".kittify" / "config.yaml"
    config.chmod(0o000)
    try:
        assert _local_kind(root) == "unreadable"
    finally:
        config.chmod(0o600)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a chmod 000 directory regardless")
def test_a_project_config_in_an_unreadable_directory_is_unreadable(tmp_path: Path) -> None:
    """An unreadable ``.kittify`` *directory* is a carried fault, not a raised traceback.

    #3291: the existence probe (``config_path.is_file()``) sat outside the try/except,
    so an unreadable enclosing directory raised ``PermissionError`` (EACCES) straight
    out of a function whose contract is "never raises" -- the verdict still refused
    correctly, but a full traceback printed to stderr. It now carries the same
    ``unreadable`` fault as an unopenable file (same operator remedy: chmod).
    """
    root = _checkout(tmp_path, f"project:\n  uuid: {PROJECT}\n")
    kitdir = root / ".kittify"
    kitdir.chmod(0o000)
    try:
        assert _local_kind(root) == "unreadable"
    finally:
        kitdir.chmod(0o755)


def test_a_readable_project_config_reports_no_fault(tmp_path: Path) -> None:
    """The positive control. Without it every assertion above is satisfiable by a
    producer that reports a fault for absolutely everything."""
    root = _checkout(tmp_path, f"project:\n  uuid: {PROJECT}\nsync:\n  enabled: true\n")

    assert _local_kind(root) is None


@pytest.mark.parametrize(
    ("state", "config_text"),
    [
        ("no sync section and no project section", "other: 1\n"),
        ("an empty document", ""),
        ("a comments-only document", "# nothing here\n"),
        ("a sync section with no enabled key", "sync:\n  auto_start: true\n"),
    ],
)
def test_absence_is_not_a_fault_in_any_of_its_shapes(tmp_path: Path, state: str, config_text: str) -> None:
    """Absence keeps its own answer, which is *no token at all*.

    A vocabulary that grew a token for absence would deny every checkout on the machine
    that has simply not recorded a decision.
    """
    assert _local_kind(_checkout(tmp_path, config_text)) is None, f"{state} was called a fault"


# --------------------------------------------------------------------------- #
# The machine-index producer: the same tokens, the same meanings               #
# --------------------------------------------------------------------------- #


def test_an_unparseable_index_reports_unparseable() -> None:
    """A TOML syntax error. ``config.py`` already called this ``unparseable``; the
    point of the assertion is that ``consent.py`` now agrees rather than using the
    token for a different state."""
    _write_index("[sync\nbroken = ")

    assert _index_kind() == "unparseable"


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a chmod 000 file regardless")
def test_an_index_that_cannot_be_opened_reports_unreadable() -> None:
    _write_index("[sync]\n")
    from specify_cli.sync.config import SyncConfig

    path = SyncConfig().config_file
    path.chmod(0o000)
    try:
        assert _index_kind() == "unreadable"
    finally:
        path.chmod(0o600)


def test_an_unusable_index_entry_reports_unusable() -> None:
    """Right shape, a value that records nothing — the same state the project-local
    producer calls ``unusable``."""
    _write_index(f'[sync.project_consent."{PROJECT}"]\nenabled = "true"\n')

    assert _index_kind() == "unusable"


def test_a_readable_index_reports_no_fault() -> None:
    """The machine-index positive control."""
    _write_index(f'[sync.project_consent."{PROJECT}"]\nenabled = true\n')

    assert _index_kind() is None


# --------------------------------------------------------------------------- #
# The two producers, held against each other                                   #
# --------------------------------------------------------------------------- #


def test_the_two_producers_agree_on_what_unparseable_means(tmp_path: Path) -> None:
    """A syntax error is ``unparseable`` on both surfaces, in one run.

    Before the unification these two inputs — a broken TOML index and a broken YAML
    project config — produced *different* tokens for the same state, which is what made
    one kind-keyed advice string unable to be true for both.
    """
    _write_index("[sync\nbroken = ")
    root = _checkout(tmp_path, "project:\n  uuid: [unclosed\n")

    assert _index_kind() == "unparseable"
    assert _local_kind(root) == "unparseable"


def test_a_wrong_shape_is_not_reported_as_a_syntax_error(tmp_path: Path) -> None:
    """The discriminating half: a document that parses is not a document that does not.

    This is the case the old vocabulary got wrong in the operator's own output — a
    non-mapping top level was reported with the token reserved for bad syntax.
    """
    root = _checkout(tmp_path, "- one\n- two\n")

    assert _local_kind(root) == "wrong_shape"


def test_the_declared_vocabulary_is_exactly_the_four_states() -> None:
    """The set is closed and named in one place, so a fifth cannot appear unnoticed.

    A token minted by a producer that the vocabulary does not declare is how the two
    modules drifted apart the first time.
    """
    from specify_cli.sync.config import CONFIG_FAULT_KINDS

    assert CONFIG_FAULT_KINDS == ("unreadable", "unparseable", "wrong_shape", "unusable")


def test_every_minted_kind_is_a_declared_kind(tmp_path: Path) -> None:
    """Both producers, every branch reachable from a file on disk, checked against the
    declaration rather than against a hand-written list that can fall behind."""
    from specify_cli.sync.config import CONFIG_FAULT_KINDS

    _write_index("[sync\nbroken = ")
    minted = {_index_kind()}
    for text in (
        "project:\n  uuid: [unclosed\n",
        "- one\n- two\n",
        f'project:\n  uuid: {PROJECT}\nsync:\n  enabled: "false"\n',
    ):
        minted.add(_local_kind(_checkout(tmp_path, text)))
    _write_index(f'[sync.project_consent."{PROJECT}"]\nenabled = "true"\n')
    minted.add(_index_kind())

    assert minted <= set(CONFIG_FAULT_KINDS)
    assert None not in minted, "a fault case reported no fault at all"
