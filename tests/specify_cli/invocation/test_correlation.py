"""FR-007 — append_correlation_link + ref normalisation unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.invocation.record import InvocationRecord
from specify_cli.invocation.writer import InvocationWriter, normalise_ref


# ---------------------------------------------------------------------------
# normalise_ref unit tests
# ---------------------------------------------------------------------------


def test_normalise_ref_in_checkout(tmp_path: Path) -> None:
    """A path inside repo_root is returned as a POSIX-style repo-relative string."""
    inside = tmp_path / "subdir" / "file.txt"
    inside.parent.mkdir(parents=True)
    inside.write_text("x")
    result = normalise_ref(str(inside), tmp_path)
    assert result == str(Path("subdir") / "file.txt")


def test_normalise_ref_outside_checkout(tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    """A path outside repo_root is returned as an absolute path."""
    elsewhere = tmp_path_factory.mktemp("elsewhere") / "out.log"
    elsewhere.write_text("x")
    result = normalise_ref(str(elsewhere), tmp_path)
    assert Path(result).is_absolute()


def test_normalise_ref_verbatim_fallback(tmp_path: Path) -> None:
    """A path with a null byte cannot be resolved and is returned verbatim."""
    weird = "not/a/real/path\x00"
    result = normalise_ref(weird, tmp_path)
    assert result == weird


def test_normalise_ref_repo_relative_path_uses_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Repo-relative refs must resolve from repo_root, not the caller's cwd."""
    repo_root = tmp_path / "repo"
    artifact = repo_root / "docs" / "output.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("x")
    nested_cwd = repo_root / "nested" / "child"
    nested_cwd.mkdir(parents=True)

    monkeypatch.chdir(nested_cwd)

    result = normalise_ref("docs/output.md", repo_root)

    assert result == str(Path("docs") / "output.md")


# ---------------------------------------------------------------------------
# append_correlation_link full fixture test
# ---------------------------------------------------------------------------


def _write_started(writer: InvocationWriter, invocation_id: str) -> None:
    """Write a minimal started record directly via writer."""
    record = InvocationRecord(
        event="started",
        invocation_id=invocation_id,
        profile_id="test-profile",
        action="implement",
        request_text="test request",
        started_at="2026-04-23T06:00:00Z",
    )
    writer.write_started(record)


def test_append_artifact_link_writes_event(tmp_path: Path) -> None:
    """append_correlation_link with ref writes an artifact_link JSONL event."""
    writer = InvocationWriter(tmp_path)
    inv_id = "01KPWA5X00000000000000TEST"
    _write_started(writer, inv_id)

    writer.append_correlation_link(inv_id, ref="src/specify_cli/foo.py")

    path = writer.invocation_path(inv_id)
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    # started (1) + artifact_link (1)
    assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}: {lines}"
    link_event = json.loads(lines[1])
    assert link_event["event"] == "artifact_link"
    assert link_event["ref"] == "src/specify_cli/foo.py"
    assert link_event["kind"] == "artifact"
    assert link_event["invocation_id"] == inv_id


def test_append_commit_link_writes_event(tmp_path: Path) -> None:
    """append_correlation_link with sha writes a commit_link JSONL event."""
    writer = InvocationWriter(tmp_path)
    inv_id = "01KPWA5X00000000000000SH01"
    _write_started(writer, inv_id)

    writer.append_correlation_link(inv_id, sha="abc123def456")

    path = writer.invocation_path(inv_id)
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2
    link_event = json.loads(lines[1])
    assert link_event["event"] == "commit_link"
    assert link_event["sha"] == "abc123def456"
    assert link_event["invocation_id"] == inv_id


def test_append_correlation_link_raises_on_missing_invocation(tmp_path: Path) -> None:
    """append_correlation_link raises InvocationError for an unknown invocation_id."""
    from specify_cli.invocation.errors import InvocationError

    writer = InvocationWriter(tmp_path)
    with pytest.raises(InvocationError, match="not found"):
        writer.append_correlation_link("NONEXISTENT0000000000000000", ref="foo.txt")


def test_append_correlation_link_raises_on_both_ref_and_sha(tmp_path: Path) -> None:
    """Both ref and sha supplied raises ValueError."""
    writer = InvocationWriter(tmp_path)
    inv_id = "01KPWA5X00000000000000BRS1"
    _write_started(writer, inv_id)
    with pytest.raises(ValueError, match="Exactly one"):
        writer.append_correlation_link(inv_id, ref="foo.txt", sha="abc123")


def test_append_correlation_link_raises_on_neither_ref_nor_sha(tmp_path: Path) -> None:
    """Neither ref nor sha raises ValueError."""
    writer = InvocationWriter(tmp_path)
    inv_id = "01KPWA5X00000000000000BRS2"
    _write_started(writer, inv_id)
    with pytest.raises(ValueError, match="Exactly one"):
        writer.append_correlation_link(inv_id)
