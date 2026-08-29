"""#3030 fold-in: a corrupt ``owner.json`` is not "no daemon owns sync".

FR-003 — *inability to determine X is never permission for X* — found for the
fourth time in this mission, here on the sync preflight gate.

``owner.read_owner_record`` returned ``None`` for two different facts: the file
is **absent** (no daemon has ever registered — a normal state) and the file is
**present but unreadable** (truncated write, hand-edit, EACCES). The preflight
read that one ``None`` as ``daemon_status == "absent"``, emitted no mismatch and
no orphan row, and ``BoundaryFailureSet.ok`` stayed **True** — the gate passed
while a live daemon could be holding the port under a different auth scope.

The two facts are now separate values (``owner.classify_owner_record``), and
only the second is a boundary failure. Which side absence lands on is decided
by the data, not by symmetry: a genuinely absent record means no daemon has
ever registered, so it stays permissive and is regression-pinned below.

Test shape, in the order the bar asks for it:

1. ``test_the_corrupt_record_is_genuinely_unparseable`` — the condition under
   test is real, so the consequence test below cannot pass for the wrong reason.
2. ``test_a_corrupt_owner_record_refuses_the_whole_preflight`` — the
   consequence, against a genuinely live process and a bound loopback socket:
   ``ok`` False, a **named** failure, ``daemon_status`` not ``"absent"``.
3. ``test_a_valid_owner_record_still_passes_the_preflight`` — the positive
   control. A probe that answered "refuse" to everything would fail here.
4. ``test_an_absent_owner_record_still_passes_the_preflight`` — the regression
   pin on absence: the permissive side is deliberate and must not drift closed.

See ``kitty-specs/journal-project-consent-3030-01KYKWQS/spec.md`` (FR-003) and
commit ``c9e33dda62`` (the same three-state classification on the evidence-mode
gate, whose undetermined value likewise carries *why* it could not be read).
"""

from __future__ import annotations

import json
import os
import socket
import stat
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


_TOKEN = "deadbeefcafebabe-owner-token"  # noqa: S105 - fixture value, asserted never rendered


@pytest.fixture(autouse=True)
def _scoped_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin HOME so ``<sync_root>/daemon/owner.json`` lands in a scratch dir.

    Each test gets its own tmp_path, so cases never share a sync root.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    return tmp_path


def _build_record(**overrides: Any) -> Any:
    from specify_cli.sync.owner import DaemonOwnerRecord

    defaults: dict[str, Any] = {
        "pid": os.getpid(),
        "port": 9400,
        "token": _TOKEN,
        "package_version": "3.2.0",
        "executable_path": sys.executable,
        "source_checkout_path": str(Path(__file__).resolve().parents[2]),
        "server_url": "https://spec-kitty-dev.fly.dev",
        "auth_principal": "tester@example.com",
        "auth_team": "t-private",
        "auth_scope": "https://spec-kitty-dev.fly.dev|tester@example.com|t-private",
        "queue_db_path": str(Path.home() / ".spec-kitty" / "queues" / "queue-aaaaaaaa.db"),
        "started_at": "2026-05-17T16:42:00+00:00",
    }
    defaults.update(overrides)
    return DaemonOwnerRecord(**defaults)


def _install_owner_file(payload: str | bytes | None) -> Path:
    """Write the daemon dir + ``owner.json``; *payload* ``None`` writes a valid record.

    Always goes through ``write_owner_record`` first so the directory layout is
    the real one, then overwrites the bytes for the malformed cases.
    """
    from specify_cli.sync.owner import owner_record_path, write_owner_record

    write_owner_record(_build_record())
    path = owner_record_path()
    if payload is None:
        return path
    if isinstance(payload, bytes):
        path.write_bytes(payload)
    else:
        path.write_text(payload, encoding="utf-8")
    return path


def _stub_boundary_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub only what is neither a decision nor under test.

    The foreground identity (otherwise it reads the operator's live auth) and
    the legacy-row count (otherwise it opens the queue DB). The owner-record
    read, the classification and ``ok`` all run for real.
    """
    from specify_cli.sync import preflight as preflight_mod

    record = _build_record()
    foreground = preflight_mod.ForegroundIdentity(
        package_version=record.package_version,
        executable_path=Path(record.executable_path),
        source_path=Path(record.source_checkout_path),
        server_url=record.server_url,
        team_or_user=f"{record.auth_principal}/{record.auth_team}",
        queue_db_path=Path(record.queue_db_path),
        pid=os.getpid(),
    )
    monkeypatch.setattr(preflight_mod, "collect_foreground_identity", lambda repo_root: foreground)  # noqa: ARG005
    monkeypatch.setattr(preflight_mod, "_count_legacy_rows_for_scope", lambda fg: (0, 0))  # noqa: ARG005
    monkeypatch.setattr(preflight_mod, "_project_store_layout_diagnostic", lambda repo_root: None)  # noqa: ARG005


@pytest.fixture
def live_daemon_process() -> Iterator[tuple[int, int]]:
    """A genuinely running process holding a bound loopback port.

    Not a mock: this is what makes the corrupt-record case dangerous rather
    than academic — something IS listening, and the foreground has just lost
    every means of telling whether it is the daemon it is entitled to talk to.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))  # ephemeral: never touches the [9401, 9425) daemon band
    sock.listen(1)
    port = sock.getsockname()[1]
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])  # noqa: S603
    try:
        deadline = time.monotonic() + 5.0
        while proc.poll() is not None and time.monotonic() < deadline:  # pragma: no cover - startup race
            time.sleep(0.01)
        assert proc.poll() is None, "the stand-in daemon process died before the assertion"
        yield proc.pid, port
    finally:
        proc.kill()
        proc.wait(timeout=5)
        sock.close()


# ---------------------------------------------------------------------------
# 1. The condition under test is real
# ---------------------------------------------------------------------------


_TRUNCATED_RECORD = '{"pid": 4242, "port": 9400, "token": "' + _TOKEN + '", "package_ver'


def test_the_corrupt_record_is_genuinely_unparseable() -> None:
    """The payload really is unparseable JSON, at the parser, not by assertion.

    Without this, a consequence test could go green because the fixture wrote
    something the reader happened to accept (or nothing at all).
    """
    with pytest.raises(json.JSONDecodeError):
        json.loads(_TRUNCATED_RECORD)


def test_the_corrupt_record_file_is_present_on_disk() -> None:
    """And the file exists — the state is *present but unreadable*, not absent."""
    path = _install_owner_file(_TRUNCATED_RECORD)
    assert path.exists(), "the malformed-owner fixture must leave a file behind"
    assert path.read_text(encoding="utf-8") == _TRUNCATED_RECORD


# ---------------------------------------------------------------------------
# 2. The consequence: the preflight refuses
# ---------------------------------------------------------------------------


def test_a_corrupt_owner_record_refuses_the_whole_preflight(
    monkeypatch: pytest.MonkeyPatch,
    live_daemon_process: tuple[int, int],
) -> None:
    """A truncated ``owner.json`` + a live process ⇒ ``ok`` False, named failure.

    This is the fail-open the fix closes: before it, the unreadable file read
    as "no daemon owns sync", ``daemon_status`` was ``"absent"``, no mismatch
    and no orphan row were emitted, and every sync mutating command proceeded.
    """
    from specify_cli.sync import owner as owner_mod
    from specify_cli.sync import preflight as preflight_mod

    _install_owner_file(_TRUNCATED_RECORD)
    _stub_boundary_inputs(monkeypatch)
    daemon_pid, _port = live_daemon_process

    failure_set = preflight_mod.build_boundary_failure_set(repo_root=Path.cwd())

    assert failure_set.ok is False, (
        f"an owner.json that cannot be read is not permission to sync: a daemon (e.g. pid {daemon_pid}) may hold the port under another auth scope"
    )
    assert failure_set.daemon_status != "absent", "a present-but-unreadable record must never render as 'absent'"
    fault = failure_set.unreadable_owner_record
    assert fault is not None, "the refusal must be named, not merely a False"
    assert fault.reason == "invalid_json", f"unexpected fault classification: {fault!r}"
    assert fault.path == owner_mod.owner_record_path()
    assert fault.detail, "the undetermined value must carry why it could not be read"


def test_the_corrupt_record_refusal_reaches_run_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """``run_preflight`` — the entry point every mutating command calls — refuses too."""
    from specify_cli.sync import preflight as preflight_mod

    _install_owner_file(_TRUNCATED_RECORD)
    _stub_boundary_inputs(monkeypatch)

    result = preflight_mod.run_preflight(repo_root=Path.cwd(), require_auth=False)

    assert result.ok is False
    assert result.unreadable_owner_record is not None
    assert result.to_dict()["unreadable_owner_record"] is not None


def test_the_refusal_names_the_record_without_echoing_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rendered refusal explains the fault and never leaks the bearer token.

    ``owner.json`` carries the daemon's control-plane token, and this module's
    redaction rule applies to every surface that renders it. The undetermined
    value therefore carries the *reason*, not the file bytes.
    """
    from rich.console import Console

    from specify_cli.sync import preflight as preflight_mod

    _install_owner_file(_TRUNCATED_RECORD)
    _stub_boundary_inputs(monkeypatch)

    result = preflight_mod.run_preflight(repo_root=Path.cwd(), require_auth=False)
    console = Console(record=True, width=100, soft_wrap=True)
    result.render(console)
    rendered = console.export_text()

    assert "owner.json" in rendered, f"the refusal must name the record it could not read:\n{rendered}"
    assert _TOKEN not in rendered, "the refusal must not echo owner.json's bearer token"
    assert _TOKEN not in json.dumps(result.to_dict()), "the JSON surface must not echo owner.json's bearer token"


@pytest.mark.parametrize(
    ("payload", "expected_reason"),
    [
        pytest.param(_TRUNCATED_RECORD, "invalid_json", id="truncated-json"),
        pytest.param("not json at all", "invalid_json", id="not-json"),
        pytest.param("", "invalid_json", id="empty-file"),
        pytest.param("[1, 2, 3]", "not_an_object", id="json-array"),
        pytest.param("null", "not_an_object", id="json-null"),
        pytest.param('{"pid": 1}', "invalid_fields", id="missing-fields"),
        pytest.param('{"pid": "not-a-pid", "port": 9400}', "invalid_fields", id="wrong-typed-field"),
        pytest.param(b"\xff\xfe\x00bad", "unreadable_file", id="undecodable-bytes"),
    ],
)
def test_every_shape_of_malformation_refuses(
    monkeypatch: pytest.MonkeyPatch,
    payload: str | bytes,
    expected_reason: str,
) -> None:
    """Each way the record can be unreadable is a boundary failure, and is named.

    The reasons differ so the operator is told *what* was wrong; the verdict
    does not.
    """
    from specify_cli.sync import preflight as preflight_mod

    _install_owner_file(payload)
    _stub_boundary_inputs(monkeypatch)

    failure_set = preflight_mod.build_boundary_failure_set(repo_root=Path.cwd())

    assert failure_set.ok is False, f"{expected_reason}: an unreadable owner record must refuse"
    assert failure_set.unreadable_owner_record is not None
    assert failure_set.unreadable_owner_record.reason == expected_reason


def test_an_unreadable_owner_file_refuses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """EACCES on the record itself is undetermined, not absent.

    Real permissions, not a patched ``open`` — a monkeypatched reader would
    prove only that the mock was installed.
    """
    if os.name != "posix":
        pytest.skip("POSIX file permissions required to produce EACCES")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("running as root: file mode bits do not deny reads")

    from specify_cli.sync import preflight as preflight_mod

    path = _install_owner_file(None)
    path.chmod(0o000)
    _stub_boundary_inputs(monkeypatch)
    try:
        with pytest.raises(PermissionError):
            path.read_text(encoding="utf-8")  # the condition is real at the syscall layer

        failure_set = preflight_mod.build_boundary_failure_set(repo_root=Path.cwd())
    finally:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    assert failure_set.ok is False, "a record we are not allowed to read is not permission to sync"
    assert failure_set.unreadable_owner_record is not None
    assert failure_set.unreadable_owner_record.reason == "unreadable_file"


# ---------------------------------------------------------------------------
# 3. Positive control — the gate still passes when it should
# ---------------------------------------------------------------------------


def test_a_valid_owner_record_still_passes_the_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """A readable record matching the foreground ⇒ ``ok`` True, ``present``.

    The control for every refusal above: they share this code path, so a
    failure set that refused unconditionally fails here.
    """
    from specify_cli.sync import preflight as preflight_mod

    _install_owner_file(None)
    _stub_boundary_inputs(monkeypatch)

    failure_set = preflight_mod.build_boundary_failure_set(repo_root=Path.cwd())

    assert failure_set.unreadable_owner_record is None
    assert failure_set.daemon_status == "present"
    assert failure_set.mismatches == (), f"unexpected identity mismatches: {failure_set.mismatches}"
    assert failure_set.ok is True, "a coherent, readable owner record must not be refused"


# ---------------------------------------------------------------------------
# 4. Regression pin — absence stays on the permissive side
# ---------------------------------------------------------------------------


def test_an_absent_owner_record_still_passes_the_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """No ``owner.json`` at all ⇒ ``ok`` True, ``absent``.

    Absence is not malformation. A genuinely missing record means no daemon
    has ever registered on this host, which is a normal state — the very first
    ``spec-kitty sync`` on a fresh machine. Refusing on it would block every
    cold start, so absence keeps its permissive meaning and this pin is what
    stops a later symmetry argument from flipping it.
    """
    from specify_cli.sync import owner as owner_mod
    from specify_cli.sync import preflight as preflight_mod

    _stub_boundary_inputs(monkeypatch)
    assert not owner_mod.owner_record_path().exists(), "this case requires no record on disk"

    failure_set = preflight_mod.build_boundary_failure_set(repo_root=Path.cwd())

    assert failure_set.unreadable_owner_record is None
    assert failure_set.daemon_status == "absent"
    assert failure_set.ok is True, "a host where no daemon has ever registered must not be refused"


def test_a_record_deleted_between_stat_and_read_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """A record that vanishes mid-read is absence, not malformation.

    The old caller asked ``owner_record_path().exists()`` and then read —
    a daemon shutting down in that window would have produced a phantom
    fault. The classifier reads once and lets ``FileNotFoundError`` mean
    what it says.
    """
    from specify_cli.sync import owner as owner_mod

    real_read_text = Path.read_text

    def _vanish(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == owner_mod.owner_record_path():
            raise FileNotFoundError(2, "No such file or directory", str(self))
        return real_read_text(self, *args, **kwargs)

    _install_owner_file(None)
    monkeypatch.setattr(Path, "read_text", _vanish)

    assert owner_mod.classify_owner_record() is None


# ---------------------------------------------------------------------------
# The distinction itself
# ---------------------------------------------------------------------------


def test_classify_owner_record_separates_absent_from_unreadable() -> None:
    """The three states are three values at the classifier.

    ``read_owner_record`` still collapses two of them onto ``None`` — it is
    the lossy convenience for callers that only want "a usable record or
    nothing" — so a permission decision must read the classifier instead.
    """
    from specify_cli.sync.owner import (
        DaemonOwnerRecord,
        UnreadableOwnerRecord,
        classify_owner_record,
        read_owner_record,
    )

    assert classify_owner_record() is None  # absent
    assert read_owner_record() is None

    _install_owner_file(None)
    assert isinstance(classify_owner_record(), DaemonOwnerRecord)  # readable
    assert isinstance(read_owner_record(), DaemonOwnerRecord)

    _install_owner_file(_TRUNCATED_RECORD)
    fault = classify_owner_record()
    assert isinstance(fault, UnreadableOwnerRecord)  # undetermined
    assert read_owner_record() is None, "the lossy wrapper keeps its documented contract"
    assert _TOKEN not in repr(fault), "the fault value must not carry the record's bytes"
