"""Tests for deterministic mission-state repair."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from packaging.version import Version

from specify_cli.migration.mission_state import (
    MissionStateDryRunError,
    _repo_slug,
    deterministic_ulid,
    repair_repo,
    teamspace_dry_run,
)


def _has_events_5() -> bool:
    import spec_kitty_events

    return Version(spec_kitty_events.__version__) >= Version("5.0.0")


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, object], data)


def _init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "repair-test@spec-kitty.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "repair test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=repo, check=True)


def test_repair_canonicalizes_historical_meta_and_status_events(tmp_path: Path) -> None:
    repo = tmp_path
    mission = repo / "kitty-specs" / "042-historical-shape"
    mission.mkdir(parents=True)
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "feature_number": "042",
            "feature_slug": "042-historical-shape",
            "friendly_name": "Historical Shape",
            "mission": "software-dev",
            "slug": "042-historical-shape",
            "target_branch": "main",
        },
    )
    status_row = {
        "actor": "Claude Code",
        "at": "2026-01-01T00:00:00+00:00",
        "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGR",
        "execution_mode": "worktree",
        "feature_slug": "042-historical-shape",
        "force": False,
        "from_lane": "doing",
        "legacy_aggregate_id": "feature:042-historical-shape",
        "to_lane": "in_review",
        "work_package_id": "WP01",
    }
    duplicate_row = dict(status_row)
    typed_row = {
        "at": "2026-01-01T00:00:01+00:00",
        "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
        "event_type": "DecisionPointOpened",
        "payload": {"decision_point_id": "DP01"},
    }
    (mission / "status.events.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in (status_row, duplicate_row, typed_row)) + "\n",
        encoding="utf-8",
    )
    (mission / "mission-events.jsonl").write_text(
        json.dumps({"event_type": "MissionNextInvoked", "payload": {"mission_slug": "042-historical-shape"}}) + "\n",
        encoding="utf-8",
    )

    report = repair_repo(repo)

    report_dict = cast(dict[str, Any], report.to_dict())
    assert report_dict["summary"]["missions_updated"] == 1
    result = report.missions[0]
    assert result.status == "updated"
    assert result.quarantined_rows == 1
    meta = _read_json(mission / "meta.json")
    assert meta["mission_id"] == deterministic_ulid(
        json.dumps(
            {
                "first_event_at": "2026-01-01T00:00:00+00:00",
                "first_event_id": "01KQHRB8GCFJAX7HM4ZY52AQGR",
                "meta": {
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "friendly_name": "Historical Shape",
                    "mission_slug": "042-historical-shape",
                    "mission_type": "software-dev",
                    "slug": "042-historical-shape",
                    "target_branch": "main",
                },
            },
            sort_keys=True,
        )
    )
    assert meta["mission_number"] == 42
    assert meta["mission_slug"] == "042-historical-shape"
    assert meta["mission_type"] == "software-dev"
    assert "feature_slug" not in meta
    assert "feature_number" not in meta
    assert "mission" not in meta

    rows = [
        json.loads(line)
        for line in (mission / "status.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row["mission_slug"] == "042-historical-shape"
    assert row["mission_id"] == meta["mission_id"]
    assert row["wp_id"] == "WP01"
    assert row["from_lane"] == "in_progress"
    assert row["to_lane"] == "in_review"
    assert row["actor"] == "claude-code"
    assert "feature_slug" not in row
    assert "work_package_id" not in row
    assert "legacy_aggregate_id" not in row

    status = _read_json(mission / "status.json")
    status_summary = cast(dict[str, object], status["summary"])
    assert status_summary["in_review"] == 1
    quarantine = repo / ".kittify" / "migrations" / "mission-state" / "quarantine" / report.run_id / "042-historical-shape" / "status.events.jsonl"
    assert "DecisionPointOpened" in quarantine.read_text(encoding="utf-8")

    if not _has_events_5():
        with pytest.raises(MissionStateDryRunError, match="requires spec-kitty-events >= 5.0.0"):
            teamspace_dry_run(repo, mission="042-historical-shape")
        return

    dry_run = teamspace_dry_run(repo, mission="042-historical-shape")

    assert dry_run.valid
    assert dry_run.schema_version == "3.0.0"
    assert dry_run.events_package_version == "5.0.0"
    assert dry_run.envelope_count == 1
    assert dry_run.errors == ()
    assert len(dry_run.row_mappings) == 1
    mapping = dry_run.row_mappings[0].to_dict()
    assert mapping["mission_slug"] == "042-historical-shape"
    assert mapping["artifact_path"] == "kitty-specs/042-historical-shape/status.events.jsonl"
    assert mapping["line_number"] == 1
    assert mapping["source_event_id"] == "01KQHRB8GCFJAX7HM4ZY52AQGR"
    assert mapping["synthesized_event_id"] == "01KQHRB8GCFJAX7HM4ZY52AQGR"
    assert mapping["synthesized_event_type"] == "WPStatusChanged"
    assert mapping["aggregate_id"] == "WP01"
    assert isinstance(mapping["row_sha256"], str)
    assert isinstance(mapping["envelope_sha256"], str)
    assert {
        warning["code"]
        for warning in dry_run.context_warnings
    } == {
        "TEAMSPACE_PROJECT_CONTEXT_MISSING",
        "TEAMSPACE_TEAM_CONTEXT_NOT_VALIDATED",
    }
    assert dry_run.side_logs == (
        {
            "artifact_path": "kitty-specs/042-historical-shape/mission-events.jsonl",
            "disposition": "skipped_local_side_log",
            "reason": "out_of_scope_for_launch_import",
            "row_count": 1,
        },
    )


def test_repair_is_idempotent_after_first_canonicalization(tmp_path: Path) -> None:
    repo = tmp_path
    mission = repo / "kitty-specs" / "001-modern"
    mission.mkdir(parents=True)
    mission_id = "01KQHRB8GCFJAX7HM4ZY52AQGR"
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Modern",
            "mission_id": mission_id,
            "mission_number": 1,
            "mission_slug": "001-modern",
            "mission_type": "software-dev",
            "slug": "001-modern",
            "target_branch": "main",
        },
    )
    (mission / "status.events.jsonl").write_text(
        json.dumps(
            {
                "actor": "codex",
                "at": "2026-01-01T00:00:00+00:00",
                "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
                "execution_mode": "worktree",
                "force": False,
                "from_lane": "planned",
                "mission_id": mission_id,
                "mission_slug": "001-modern",
                "policy_metadata": None,
                "reason": None,
                "review_ref": None,
                "evidence": None,
                "to_lane": "claimed",
                "wp_id": "WP01",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    first = repair_repo(repo)
    second = repair_repo(repo)

    assert first.missions[0].status == "updated"
    assert second.missions[0].status == "unchanged"
    assert second.missions[0].row_transformations == []


def test_deterministic_repair_ids_follow_fork_seed_material(tmp_path: Path) -> None:
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    mission_a = repo_a / "kitty-specs" / "001-historical"
    mission_b = repo_b / "kitty-specs" / "001-historical"
    mission_a.mkdir(parents=True)
    mission_b.mkdir(parents=True)
    for mission, event_id in (
        (mission_a, "01KQHRB8GCFJAX7HM4ZY52AQGR"),
        (mission_b, "01KQHRB8GCFJAX7HM4ZY52AQGS"),
    ):
        _write_json(
            mission / "meta.json",
            {
                "created_at": "2026-01-01T00:00:00+00:00",
                "feature_number": "001",
                "feature_slug": "001-historical",
                "friendly_name": "Historical",
                "mission": "software-dev",
                "target_branch": "main",
            },
        )
        (mission / "status.events.jsonl").write_text(
            json.dumps(
                {
                    "actor": "codex",
                    "at": "2026-01-01T00:00:00+00:00",
                    "event_id": event_id,
                    "from_lane": "planned",
                    "to_lane": "claimed",
                    "work_package_id": "WP01",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    repair_repo(repo_a)
    repair_repo(repo_b)

    assert _read_json(mission_a / "meta.json")["mission_id"] != _read_json(mission_b / "meta.json")["mission_id"]


def test_teamspace_dry_run_fails_when_status_rows_still_contain_legacy_keys(tmp_path: Path) -> None:
    if not _has_events_5():
        pytest.skip("TeamSpace dry-run validation requires spec-kitty-events >= 5.0.0")

    repo = tmp_path
    mission = repo / "kitty-specs" / "001-needs-repair"
    mission.mkdir(parents=True)
    mission_id = "01KQHRB8GCFJAX7HM4ZY52AQGR"
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Needs Repair",
            "mission_id": mission_id,
            "mission_number": 1,
            "mission_slug": "001-needs-repair",
            "mission_type": "software-dev",
            "slug": "001-needs-repair",
            "target_branch": "main",
        },
    )
    (mission / "status.events.jsonl").write_text(
        json.dumps(
            {
                "actor": "codex",
                "at": "2026-01-01T00:00:00+00:00",
                "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
                "execution_mode": "worktree",
                "force": False,
                "from_lane": "planned",
                "mission_id": mission_id,
                "mission_slug": "001-needs-repair",
                "to_lane": "claimed",
                "wp_id": "WP01",
                "nested": {"feature_slug": "001-needs-repair"},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    dry_run = teamspace_dry_run(repo, mission="001-needs-repair")

    assert not dry_run.valid
    assert dry_run.envelope_count == 0
    assert dry_run.errors == (
        {
            "artifact_path": "kitty-specs/001-needs-repair/status.events.jsonl",
            "error": "FORBIDDEN_LEGACY_KEY",
            "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
            "key": "feature_slug",
            "line_number": 1,
            "mission_slug": "001-needs-repair",
            "path": "$.nested.feature_slug",
        },
    )


def test_teamspace_dry_run_synthesizes_repo_evidence_for_historical_done_rows(tmp_path: Path) -> None:
    if not _has_events_5():
        pytest.skip("TeamSpace dry-run validation requires spec-kitty-events >= 5.0.0")

    repo = tmp_path
    mission = repo / "kitty-specs" / "001-historical-done"
    mission.mkdir(parents=True)
    mission_id = "01KQHRB8GCFJAX7HM4ZY52AQGR"
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Historical Done",
            "mission_id": mission_id,
            "mission_number": 1,
            "mission_slug": "001-historical-done",
            "mission_type": "software-dev",
            "slug": "001-historical-done",
            "target_branch": "main",
        },
    )
    (mission / "status.events.jsonl").write_text(
        json.dumps(
            {
                "actor": "codex",
                "at": "2026-01-01T00:00:00+00:00",
                "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
                "execution_mode": "worktree",
                "force": False,
                "from_lane": "approved",
                "mission_id": mission_id,
                "mission_slug": "001-historical-done",
                "policy_metadata": None,
                "reason": None,
                "review_ref": "review://historical",
                "evidence": {
                    "review": {
                        "reviewer": "historical-reviewer",
                        "verdict": "approved",
                        "reference": "review://historical",
                    }
                },
                "to_lane": "done",
                "wp_id": "WP01",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    dry_run = teamspace_dry_run(repo, mission="001-historical-done")

    assert dry_run.valid
    assert dry_run.envelope_count == 1
    assert dry_run.errors == ()
    assert len(dry_run.row_mappings) == 1


def test_teamspace_dry_run_synthesizes_missing_historical_approval_evidence(tmp_path: Path) -> None:
    if not _has_events_5():
        pytest.skip("TeamSpace dry-run validation requires spec-kitty-events >= 5.0.0")

    repo = tmp_path
    mission = repo / "kitty-specs" / "001-historical-approval"
    mission.mkdir(parents=True)
    mission_id = "01KQHRB8GCFJAX7HM4ZY52AQGR"
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Historical Approval",
            "mission_id": mission_id,
            "mission_number": 1,
            "mission_slug": "001-historical-approval",
            "mission_type": "software-dev",
            "slug": "001-historical-approval",
            "target_branch": "main",
        },
    )
    rows = [
        {
            "actor": "codex",
            "at": "2026-01-01T00:00:00+00:00",
            "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
            "execution_mode": "worktree",
            "force": False,
            "from_lane": "for_review",
            "mission_id": mission_id,
            "mission_slug": "001-historical-approval",
            "policy_metadata": None,
            "reason": None,
            "review_ref": None,
            "evidence": None,
            "to_lane": "approved",
            "wp_id": "WP01",
        },
        {
            "actor": "codex",
            "at": "2026-01-01T00:00:01+00:00",
            "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGT",
            "execution_mode": "worktree",
            "force": False,
            "from_lane": "approved",
            "mission_id": mission_id,
            "mission_slug": "001-historical-approval",
            "policy_metadata": None,
            "reason": None,
            "review_ref": "review://historical",
            "evidence": None,
            "to_lane": "done",
            "wp_id": "WP01",
        },
    ]
    (mission / "status.events.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

    dry_run = teamspace_dry_run(repo, mission="001-historical-approval")

    assert dry_run.valid
    assert dry_run.envelope_count == 2
    assert dry_run.errors == ()
    assert len(dry_run.row_mappings) == 2


def test_repo_slug_preserves_https_remote_colon(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class _Result:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_git(repo_root: Path, *args: str, check: bool = False) -> _Result:
        assert repo_root == tmp_path
        assert args == ("config", "--get", "remote.origin.url")
        assert check is False
        return _Result("https://github.com/Priivacy-ai/spec-kitty.git\n")

    monkeypatch.setattr("specify_cli.migration.mission_state._git", fake_git)

    assert _repo_slug(tmp_path) == "Priivacy-ai/spec-kitty"


def test_repair_refuses_when_common_git_lock_is_held(tmp_path: Path) -> None:
    repo = tmp_path
    mission = repo / "kitty-specs" / "001-modern"
    mission.mkdir(parents=True)
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Modern",
            "mission_id": "01KQHRB8GCFJAX7HM4ZY52AQGR",
            "mission_number": 1,
            "mission_slug": "001-modern",
            "mission_type": "software-dev",
            "slug": "001-modern",
            "target_branch": "main",
        },
    )
    _init_git_repo(repo)
    lock = repo / ".git" / "spec-kitty-mission-state.lock"
    lock.write_text("held", encoding="ascii")

    with pytest.raises(Exception, match="Another mission-state repair appears to be running"):
        repair_repo(repo)


def test_repair_checks_dirty_relevant_paths_in_linked_worktrees(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    mission = repo / "kitty-specs" / "001-modern"
    mission.mkdir(parents=True)
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Modern",
            "mission_id": "01KQHRB8GCFJAX7HM4ZY52AQGR",
            "mission_number": 1,
            "mission_slug": "001-modern",
            "mission_type": "software-dev",
            "slug": "001-modern",
            "target_branch": "main",
        },
    )
    _init_git_repo(repo)
    linked = tmp_path / "linked"
    subprocess.run(["git", "worktree", "add", "-q", "-b", "linked-branch", str(linked)], cwd=repo, check=True)
    (linked / "kitty-specs" / "001-modern" / "meta.json").write_text(
        json.dumps({"mission_slug": "dirty"}, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="dirty relevant paths"):
        repair_repo(repo)

    report = repair_repo(repo, allow_dirty=True)
    assert report.missions[0].status == "unchanged"


# ---------------------------------------------------------------------------
# Mission 8 (#930) — secret scrubber for repair manifest command_args
# ---------------------------------------------------------------------------


class TestScrubSecretArgs:
    """``_scrub_secret_args`` must redact every documented secret shape so
    the manifest ``command_args`` field never leaks credentials."""

    def _scrub(self, *argv: str) -> list[str]:
        from specify_cli.migration.mission_state import _scrub_secret_args

        return _scrub_secret_args(list(argv))

    def test_benign_argv_passes_through_unchanged(self) -> None:
        argv = ["doctor", "mission-state", "--fix", "--json"]
        assert self._scrub(*argv) == argv

    def test_secret_flag_value_is_redacted_pair_form(self) -> None:
        assert self._scrub("doctor", "--token", "abc123") == [
            "doctor",
            "--token",
            "<redacted>",
        ]

    def test_secret_flag_value_is_redacted_equals_form(self) -> None:
        assert self._scrub("doctor", "--token=abc123") == [
            "doctor",
            "--token=<redacted>",
        ]

    def test_api_key_flag_redacted(self) -> None:
        assert self._scrub("--api-key", "sk-real-value") == [
            "--api-key",
            "<redacted>",
        ]

    def test_auth_password_secret_flags_redacted(self) -> None:
        out = self._scrub("--auth", "u:p", "--password", "hunter2", "--secret=top")
        assert out == ["--auth", "<redacted>", "--password", "<redacted>", "--secret=<redacted>"]

    def test_authorization_header_redacted(self) -> None:
        argv = ["curl", "-H", "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def"]
        out = self._scrub(*argv)
        assert "<redacted>" in out
        # The header itself is redacted as a standalone item
        assert "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def" not in out

    def test_github_token_redacted(self) -> None:
        token = "ghp_" + "A" * 40
        assert self._scrub("--repo", token) == ["--repo", "<redacted>"]

    def test_slack_token_redacted(self) -> None:
        token = "xoxb-1234-5678-abcdef0123456789"
        assert self._scrub(token) == ["<redacted>"]

    def test_jwt_shape_redacted(self) -> None:
        jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
            ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        assert self._scrub(jwt) == ["<redacted>"]

    def test_bare_bearer_redacted(self) -> None:
        out = self._scrub("Bearer abcdefghijklmnopqrstuvwxyz")
        assert out == ["<redacted>"]

    def test_pure_function(self) -> None:
        """Same input list yields equal output every call (no hidden state)."""
        argv = ["--token", "abc123", "ghp_" + "B" * 40]
        a = self._scrub(*argv)
        b = self._scrub(*argv)
        assert a == b

    # ---------------------------------------------------------------------
    # PR #1031 follow-up: broadened flag set + env-var-style argv items.
    # Each test below covers a real-world pattern that the original WP02
    # helper missed.
    # ---------------------------------------------------------------------

    def test_access_token_flag_pair_form_redacted(self) -> None:
        assert self._scrub("--access-token", "sk-abc123") == [
            "--access-token",
            "<redacted>",
        ]

    def test_refresh_token_flag_equals_form_redacted(self) -> None:
        assert self._scrub("--refresh-token=xyz") == ["--refresh-token=<redacted>"]

    def test_id_token_flag_redacted(self) -> None:
        assert self._scrub("--id-token", "oidc-jwt-value") == [
            "--id-token",
            "<redacted>",
        ]

    def test_client_secret_flag_redacted(self) -> None:
        assert self._scrub("--client-secret", "shh") == [
            "--client-secret",
            "<redacted>",
        ]

    def test_client_id_flag_passes_through(self) -> None:
        """``--client-id`` is a public OAuth identifier, not a secret."""
        assert self._scrub("--client-id", "public-client-123") == [
            "--client-id",
            "public-client-123",
        ]

    def test_private_key_flag_redacted(self) -> None:
        assert self._scrub("--private-key", "-----BEGIN----") == [
            "--private-key",
            "<redacted>",
        ]

    def test_ssh_key_flag_redacted(self) -> None:
        assert self._scrub("--ssh-key=/path/to/id_rsa") == ["--ssh-key=<redacted>"]

    def test_aws_secret_access_key_flag_redacted(self) -> None:
        assert self._scrub("--aws-secret-access-key", "AKIA...") == [
            "--aws-secret-access-key",
            "<redacted>",
        ]

    def test_gh_token_flag_redacted(self) -> None:
        assert self._scrub("--gh-token", "ghp_xyz") == ["--gh-token", "<redacted>"]

    def test_flag_match_is_case_insensitive_pair_form(self) -> None:
        """Mixed-case secret flags must also be redacted; casing preserved."""
        assert self._scrub("--Access-Token", "sk-abc123") == [
            "--Access-Token",
            "<redacted>",
        ]

    def test_flag_match_is_case_insensitive_equals_form(self) -> None:
        assert self._scrub("--TOKEN=abc") == ["--TOKEN=<redacted>"]

    def test_env_var_style_token_redacted(self) -> None:
        assert self._scrub("SPEC_KITTY_TOKEN=foo") == ["SPEC_KITTY_TOKEN=<redacted>"]

    def test_env_var_style_github_token_redacted(self) -> None:
        assert self._scrub("GITHUB_TOKEN=bar") == ["GITHUB_TOKEN=<redacted>"]

    def test_env_var_style_api_key_redacted(self) -> None:
        assert self._scrub("OPENAI_API_KEY=sk-live-zzz") == [
            "OPENAI_API_KEY=<redacted>",
        ]

    def test_env_var_style_secret_redacted(self) -> None:
        assert self._scrub("DJANGO_SECRET=shh") == ["DJANGO_SECRET=<redacted>"]

    def test_env_var_style_password_redacted(self) -> None:
        assert self._scrub("DB_PASSWORD=hunter2") == ["DB_PASSWORD=<redacted>"]

    def test_env_var_style_passphrase_redacted(self) -> None:
        assert self._scrub("GPG_PASSPHRASE=open-sesame") == [
            "GPG_PASSPHRASE=<redacted>",
        ]

    def test_env_var_style_non_secret_passes_through(self) -> None:
        """Control case: env-style items that don't end in a sensitive
        suffix must NOT be redacted. ``GITHUB_USERNAME`` is public."""
        assert self._scrub("GITHUB_USERNAME=robert") == ["GITHUB_USERNAME=robert"]

    def test_combined_real_world_argv(self) -> None:
        """End-to-end check from the PR #1031 acceptance criterion."""
        out = self._scrub(
            "--access-token",
            "sk-abc123",
            "--refresh-token=xyz",
            "SPEC_KITTY_TOKEN=foo",
            "GITHUB_TOKEN=bar",
            "GITHUB_USERNAME=robert",
        )
        assert out == [
            "--access-token",
            "<redacted>",
            "--refresh-token=<redacted>",
            "SPEC_KITTY_TOKEN=<redacted>",
            "GITHUB_TOKEN=<redacted>",
            "GITHUB_USERNAME=robert",
        ]


# ---------------------------------------------------------------------------
# Mission 8 (#930) — expanded repair manifest fields
# ---------------------------------------------------------------------------


def _minimal_mission(repo: Path, slug: str = "999-mini") -> None:
    """Create a minimal mission directory the repair_repo will accept."""
    mission = repo / "kitty-specs" / slug
    mission.mkdir(parents=True, exist_ok=True)
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Mini",
            "mission_number": int(slug.split("-")[0]),
            "mission_slug": slug,
            "mission_type": "software-dev",
            "slug": slug,
            "target_branch": "main",
        },
    )
    (mission / "status.events.jsonl").write_text("", encoding="utf-8")


def test_manifest_includes_cli_version_command_args_generated_ids_policy(
    tmp_path: Path,
) -> None:
    """All four Mission-8 manifest fields must be present, typed correctly,
    and round-trip through to_json/JSON parse."""
    repo = tmp_path
    _minimal_mission(repo, "001-fields")
    _init_git_repo(repo)

    report = repair_repo(repo)

    # In-memory shape
    assert isinstance(report.cli_version, str)
    assert report.cli_version  # non-empty
    assert isinstance(report.command_args, list)
    assert all(isinstance(item, str) for item in report.command_args)
    assert isinstance(report.generated_ids, list)
    assert all(isinstance(item, str) for item in report.generated_ids)
    assert report.run_id in report.generated_ids
    assert isinstance(report.policy, dict)
    assert set(report.policy.keys()) == {"tracked", "optional", "ignored"}
    for key, value in report.policy.items():
        assert isinstance(value, list), f"policy[{key!r}] must be a list"
        assert value == sorted(value), f"policy[{key!r}] must be sorted"

    # On-disk manifest matches the in-memory report
    manifest_files = sorted((repo / ".kittify" / "migrations" / "mission-state").glob("*.json"))
    assert manifest_files, "manifest file must be written to disk"
    persisted = _read_json(manifest_files[-1])

    assert persisted["cli_version"] == report.cli_version
    assert persisted["command_args"] == report.command_args
    assert persisted["generated_ids"] == report.generated_ids
    assert persisted["policy"] == report.policy

    # Pre-existing keys still present and shaped correctly
    for key in (
        "schema_version",
        "run_id",
        "repo_head",
        "target_missions",
        "manifest_path",
        "summary",
        "missions",
    ):
        assert key in persisted, f"pre-existing manifest key {key!r} missing"
    assert isinstance(persisted["summary"], dict)
    assert isinstance(persisted["missions"], list)


def test_manifest_command_args_are_scrubbed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Hostile sys.argv must never make it into the manifest verbatim."""
    repo = tmp_path
    _minimal_mission(repo, "002-scrub")
    _init_git_repo(repo)

    hostile = [
        "spec-kitty",
        "doctor",
        "mission-state",
        "--fix",
        "--token",
        "supersecret",
        "--api-key=sk-live-AAAAAAAAAAAAAAAA",
        "ghp_" + "C" * 40,
    ]
    monkeypatch.setattr("sys.argv", hostile)

    report = repair_repo(repo)

    # No raw secret should appear anywhere in command_args
    joined = "\n".join(report.command_args)
    assert "supersecret" not in joined
    assert "sk-live-AAAAAAAAAAAAAAAA" not in joined
    assert "ghp_CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC" not in joined
    # The scrubbed marker must be present in at least one slot
    assert any("<redacted>" in arg for arg in report.command_args)
    # The flag names themselves are preserved so reviewers know what was passed
    assert "--token" in report.command_args
    assert any(arg.startswith("--api-key") for arg in report.command_args)


def test_manifest_top_level_keys_remain_sorted(tmp_path: Path) -> None:
    """``to_json`` must emit top-level keys in sorted order."""
    repo = tmp_path
    _minimal_mission(repo, "003-sortkeys")
    _init_git_repo(repo)

    report = repair_repo(repo)
    rendered = report.to_json()
    parsed = json.loads(rendered)
    assert list(parsed.keys()) == sorted(parsed.keys())
