"""Atomicity tests for the retrospective record writer.

Simulates a mid-write crash by monkeypatching os.replace to raise after the
tempfile has been written.  After the crash the canonical file must be either:
  - absent (first write), or
  - unchanged (second write where a prior version existed).

Sibling tempfiles may exist; that is expected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.retrospective.schema import (
    ActorRef,
    MissionIdentity,
    Mode,
    ModeSourceSignal,
    RecordProvenance,
    RetrospectiveRecord,
)
from specify_cli.retrospective.writer import WriterError, _atomic_write_yaml, write_record

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.unit, pytest.mark.fast]

MISSION_ID = "01KQ6YEGT4YBZ3GZF7X680KQ3V"
MISSION_ID_2 = "01KQ6YEGT4YBZ3GZF7X680KQ4C"

AGENT_ACTOR = ActorRef(kind="agent", id="claude-opus-4-7", profile_id="retrospective-facilitator")
HUMAN_ACTOR = ActorRef(kind="human", id="rob@robshouse.net", profile_id=None)

MISSION = MissionIdentity(
    mission_id=MISSION_ID,
    mid8="01KQ6YEG",
    mission_slug="mission-retrospective-learning-loop-01KQ6YEG",
    mission_type="software-dev",
    mission_started_at="2026-04-27T07:46:18.715532+00:00",
    mission_completed_at="2026-04-27T11:00:00+00:00",
)

MODE = Mode(
    value="human_in_command",
    source_signal=ModeSourceSignal(kind="charter_override", evidence="charter:mode-policy:hic-default"),
)

RECORD_PROVENANCE = RecordProvenance(
    authored_by=AGENT_ACTOR,
    runtime_version="3.2.0",
    written_at="2026-04-27T11:00:00+00:00",
    schema_version="1",
)


def make_completed_record(mission_id: str = MISSION_ID) -> RetrospectiveRecord:
    mission = MissionIdentity(
        mission_id=mission_id,
        mid8=mission_id[:8],
        mission_slug="test-mission",
        mission_type="software-dev",
        mission_started_at="2026-04-27T07:46:18.715532+00:00",
        mission_completed_at="2026-04-27T11:00:00+00:00",
    )
    return RetrospectiveRecord(
        schema_version="1",
        mission=mission,
        mode=MODE,
        status="completed",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at="2026-04-27T11:00:00+00:00",
        actor=HUMAN_ACTOR,
        provenance=RECORD_PROVENANCE,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_first_write_crash_leaves_no_canonical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulated crash on first write: canonical file must not exist."""
    canonical = tmp_path / ".kittify" / "missions" / MISSION_ID / "retrospective.yaml"

    import os as _os

    original_replace = _os.replace

    def crashing_replace(src: str, dst: str) -> None:  # type: ignore[misc]
        raise OSError("Simulated crash mid-replace")

    monkeypatch.setattr(_os, "replace", crashing_replace)

    record = make_completed_record()

    with pytest.raises((WriterError, OSError)):
        write_record(record, repo_root=tmp_path)

    # Canonical must be absent — crash happened before the replace.
    assert not canonical.exists(), "Canonical file must not exist after a first-write crash"


def test_second_write_crash_leaves_prior_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulated crash on second write: canonical file must contain the prior version."""
    import os as _os

    record_v1 = make_completed_record()

    # First write succeeds normally.
    canonical = write_record(record_v1, repo_root=tmp_path)
    prior_content = canonical.read_bytes()
    assert len(prior_content) > 0

    # Now simulate a crash during the second write.
    original_replace = _os.replace

    def crashing_replace(src: str, dst: str) -> None:  # type: ignore[misc]
        raise OSError("Simulated crash mid-replace on second write")

    monkeypatch.setattr(_os, "replace", crashing_replace)

    # Second write with a different record.
    record_v2 = RetrospectiveRecord(
        schema_version="1",
        mission=MISSION,
        mode=MODE,
        status="skipped",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at="2026-04-27T10:55:30+00:00",
        actor=HUMAN_ACTOR,
        provenance=RECORD_PROVENANCE,
        skip_reason="second write that should crash",
    )

    with pytest.raises((WriterError, OSError)):
        write_record(record_v2, repo_root=tmp_path)

    # Canonical must still hold the prior version (v1), not v2.
    assert canonical.exists(), "Canonical file must still exist after a second-write crash"
    assert canonical.read_bytes() == prior_content, "Canonical file must be unchanged after crash"


def test_pending_record_rejected(tmp_path: Path) -> None:
    """Writer must refuse status='pending' before doing any I/O."""
    canonical = tmp_path / ".kittify" / "missions" / MISSION_ID / "retrospective.yaml"

    # Build a pending record by bypassing the model validator via model_construct.
    record = RetrospectiveRecord.model_construct(
        schema_version="1",
        mission=MISSION,
        mode=MODE,
        status="pending",
        started_at="2026-04-27T10:55:00+00:00",
        completed_at=None,
        actor=HUMAN_ACTOR,
        helped=[],
        not_helpful=[],
        gaps=[],
        proposals=[],
        provenance=RECORD_PROVENANCE,
    )

    with pytest.raises(WriterError, match="pending"):
        write_record(record, repo_root=tmp_path)

    assert not canonical.exists(), "Canonical must not exist after pending rejection"


def test_tempfile_in_same_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tempfile must be created in the same directory as the canonical file."""
    import os as _os

    captured_src: list[str] = []
    original_replace = _os.replace

    def capturing_replace(src: str, dst: str) -> None:
        captured_src.append(src)
        original_replace(src, dst)

    monkeypatch.setattr(_os, "replace", capturing_replace)

    record = make_completed_record()
    canonical = write_record(record, repo_root=tmp_path)

    assert len(captured_src) == 1
    tmp_used = Path(captured_src[0])
    # Tempfile must be in the same directory as the canonical file.
    assert tmp_used.parent == canonical.parent
    # Tempfile name must contain 'tmp'.
    assert "tmp" in tmp_used.name


def test_mkdir_failure_raises_writer_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """OSError from mkdir raises WriterError with informative message."""
    from pathlib import Path as _Path

    original_mkdir = _Path.mkdir

    def failing_mkdir(self: _Path, **kwargs: object) -> None:
        raise OSError("Simulated permission denied")

    monkeypatch.setattr(_Path, "mkdir", failing_mkdir)

    record = make_completed_record()
    with pytest.raises(WriterError, match="Cannot create target directory"):
        write_record(record, repo_root=tmp_path)


def test_os_write_failure_raises_writer_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """OSError during tempfile write raises WriterError; canonical file not created."""
    import os as _os

    def failing_write(fd: int, data: bytes) -> int:
        raise OSError("Simulated disk full")

    monkeypatch.setattr(_os, "write", failing_write)

    canonical = tmp_path / ".kittify" / "missions" / MISSION_ID / "retrospective.yaml"
    record = make_completed_record()
    with pytest.raises(WriterError, match="IO error"):
        write_record(record, repo_root=tmp_path)

    assert not canonical.exists()


def test_dir_fsync_failure_is_non_fatal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Best-effort dir fsync failure does not propagate; the write still succeeds."""
    import os as _os

    original_fsync = _os.fsync
    fsync_call_count = [0]

    def flaky_fsync(fd: int) -> None:
        fsync_call_count[0] += 1
        # Fail only the second call (the directory fsync, after the file fsync).
        if fsync_call_count[0] >= 2:
            raise OSError("Simulated directory fsync failure")
        original_fsync(fd)

    monkeypatch.setattr(_os, "fsync", flaky_fsync)

    record = make_completed_record()
    # Should not raise despite dir fsync failing.
    canonical = write_record(record, repo_root=tmp_path)
    assert canonical.exists()


# ---------------------------------------------------------------------------
# _atomic_write_yaml unit tests — shared helper contract
# ---------------------------------------------------------------------------


def test_atomic_write_yaml_writes_data_to_canonical(tmp_path: Path) -> None:
    """Helper writes the dict data and produces a readable YAML file at canonical."""
    from ruamel.yaml import YAML

    canonical = tmp_path / "retrospective.yaml"
    data = {"key": "value", "number": 42}

    _atomic_write_yaml(data, canonical, tmp_path)

    assert canonical.exists()
    yaml_safe = YAML(typ="safe")
    loaded = yaml_safe.load(canonical.read_text(encoding="utf-8"))
    assert loaded == data


def test_atomic_write_yaml_strips_trailing_whitespace_from_wrapped_scalars(tmp_path: Path) -> None:
    """Wrapped retrospective details must not leave a whitespace-only suffix."""
    canonical = tmp_path / "retrospective.yaml"
    details = "An analysis-report.md artifact is present for this mission. Review its findings to understand documented issues and decisions."
    data = {
        "not_helpful": [
            {
                "id": "n-001",
                "category": "doc",
                "summary": "analysis-report.md present with findings",
                "evidence_refs": ["e-007"],
                "details": details,
            }
        ]
    }

    # Precondition guard: prove the un-normalized dump genuinely wraps and
    # leaves a trailing-whitespace line, so this test cannot silently go vacuous
    # if a future ruamel stops emitting the artifact.
    import io as _io

    from ruamel.yaml import YAML

    probe = YAML(typ="rt")
    probe.default_flow_style = False
    probe.preserve_quotes = True
    probe.width = 120
    probe_buf = _io.BytesIO()
    probe.dump(data, probe_buf)
    raw = probe_buf.getvalue().decode("utf-8")
    assert any(line.endswith((" ", "\t")) for line in raw.splitlines()), (
        "expected the raw dump to contain a trailing-whitespace line; test is vacuous otherwise"
    )

    _atomic_write_yaml(data, canonical, tmp_path)

    text = canonical.read_text(encoding="utf-8")
    assert all(not line.endswith((" ", "\t")) for line in text.splitlines())

    assert YAML(typ="safe").load(text) == data


def test_atomic_write_yaml_wraps_prose_scalars_at_120_columns(tmp_path: Path) -> None:
    """Free-text fields wrap at width=120 — the #3059 decision, guarded here.

    ``_atomic_write_yaml`` deliberately passes ``width=120`` to the kernel
    primitive (whose own default is 4096) so prose fields such as
    ``GenFinding.details`` stay reviewable in a diff. This test goes RED if that
    width is raised: at 4096 a 199-char scalar is emitted as one line, which
    fails both assertions below. The payload is many short words so ruamel's
    word-boundary wrapping cannot overshoot the column budget.
    """
    from ruamel.yaml import YAML

    canonical = tmp_path / "retrospective.yaml"
    details = " ".join(["word"] * 40)
    assert len(details) > 120, "payload must exceed the wrap width or the test is vacuous"

    _atomic_write_yaml({"details": details}, canonical, tmp_path)

    text = canonical.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) > 1, f"expected the scalar to wrap onto a continuation line; got: {text!r}"
    assert max(len(line) for line in lines) <= 120, f"a line exceeds the 120-column width:\n{text}"
    assert YAML(typ="safe").load(text) == {"details": details}


@pytest.mark.parametrize("trailing", [" ", "\t"])
def test_atomic_write_yaml_preserves_literal_scalar_trailing_whitespace(
    tmp_path: Path, trailing: str
) -> None:
    """Literal scalar content may intentionally end a line with whitespace."""
    from ruamel.yaml import YAML
    from ruamel.yaml.scalarstring import LiteralScalarString

    canonical = tmp_path / "retrospective.yaml"
    details = LiteralScalarString(f"first line ends in semantic whitespace{trailing}\nsecond line")

    _atomic_write_yaml({"details": details}, canonical, tmp_path)

    loaded = YAML(typ="safe").load(canonical.read_text(encoding="utf-8"))
    assert loaded == {"details": str(details)}


def test_atomic_write_yaml_uses_temp_then_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Helper must write to a .tmp file FIRST, then rename it to canonical atomically."""
    import os as _os

    canonical = tmp_path / "retrospective.yaml"
    captured_replace: list[tuple[str, str]] = []
    original_replace = _os.replace

    def capturing_replace(src: str, dst: str) -> None:
        captured_replace.append((src, dst))
        original_replace(src, dst)

    monkeypatch.setattr(_os, "replace", capturing_replace)

    _atomic_write_yaml({"x": 1}, canonical, tmp_path)

    assert len(captured_replace) == 1
    src_path, dst_path = captured_replace[0]
    # Temp file must have been in the same directory as canonical.
    assert Path(src_path).parent == canonical.parent
    # Temp file name must contain '.tmp'.
    assert ".tmp" in Path(src_path).name
    # Destination must be the canonical path.
    assert Path(dst_path) == canonical
    # After rename, canonical holds the data; temp file is gone.
    assert canonical.exists()
    assert not Path(src_path).exists()


def test_atomic_write_yaml_crash_leaves_no_canonical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If os.replace raises, the canonical file must not exist."""
    import os as _os

    def crashing_replace(src: str, dst: str) -> None:  # type: ignore[misc]
        raise OSError("Simulated crash")

    monkeypatch.setattr(_os, "replace", crashing_replace)

    canonical = tmp_path / "retrospective.yaml"
    with pytest.raises(WriterError, match="IO error"):
        _atomic_write_yaml({"x": 1}, canonical, tmp_path)

    assert not canonical.exists()


def test_atomic_write_yaml_cleans_up_tempfile_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tempfile must be removed after an OS error during write."""
    import os as _os

    def failing_write(fd: int, data: bytes) -> int:
        raise OSError("Simulated disk full")

    monkeypatch.setattr(_os, "write", failing_write)

    canonical = tmp_path / "retrospective.yaml"
    with pytest.raises(WriterError):
        _atomic_write_yaml({"x": 1}, canonical, tmp_path)

    # No .tmp sibling files should remain.
    leftover = [f for f in tmp_path.iterdir() if ".tmp" in f.name]
    assert leftover == [], f"Unexpected tempfiles left behind: {leftover}"
