import json
from pathlib import Path

import pytest

from specify_cli.dashboard import scanner
from specify_cli.dashboard.charter_path import resolve_project_charter_path
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import materialize
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _set_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"TEST{wp_id}{lane.upper()}0000000000000000"[:26],
            mission_slug=feature_dir.name,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=Lane(lane),
            at="2026-03-31T09:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="direct_repo",
        ),
    )
    materialize(feature_dir)


def _create_feature_at(feature_dir: Path, *, lane: str = "planned") -> Path:
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    prompt = """---
work_package_id: WP01
subtasks: ["T1"]
agent: codex
---
# Work Package Prompt: Demo

Body
    """
    (feature_dir / "tasks" / "WP01-demo.md").write_text(prompt, encoding="utf-8")
    _set_wp_lane(feature_dir, "WP01", lane)
    return feature_dir


def _create_feature(tmp_path: Path, slug: str = "001-demo-feature", *, lane: str = "planned") -> Path:
    return _create_feature_at(tmp_path / "kitty-specs" / slug, lane=lane)


def test_scan_all_features_detects_feature(tmp_path):
    feature_dir = _create_feature(tmp_path)
    features = scanner.scan_all_features(tmp_path)
    assert features, "Expected at least one feature"
    assert features[0]["id"] == feature_dir.name
    assert features[0]["artifacts"]["spec"]


def test_scan_all_features_tolerates_unreadable_event_log(tmp_path):
    feature_dir = tmp_path / "kitty-specs" / "001-demo-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (tasks_dir / "WP01-demo.md").write_text(
        """---
work_package_id: WP01
---
# Work Package Prompt: Demo
""",
        encoding="utf-8",
    )
    (feature_dir / "status.events.jsonl").write_text(
        json.dumps(
            {
                "event_id": "TESTBAD00000000000000000000",
                "mission_slug": feature_dir.name,
                "wp_id": "WP01",
                "from_lane": "planned",
                "to_lane": "doing",
                "at": "2026-04-05T12:00:00+00:00",
                "actor": "test-agent",
                "force": False,
                "execution_mode": "worktree",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    features = scanner.scan_all_features(tmp_path)

    assert len(features) == 1
    assert features[0]["id"] == feature_dir.name
    assert features[0]["kanban_stats"]["total"] == 0
    assert "Event log unreadable" in features[0]["kanban_stats"]["error"]


def test_scan_all_features_builds_switcher_display_name(tmp_path):
    feature_dir = _create_feature(tmp_path)
    (feature_dir / "meta.json").write_text(
        json.dumps({"friendly_name": "Demo Feature"}),
        encoding="utf-8",
    )

    features = scanner.scan_all_features(tmp_path)

    assert features[0]["name"] == "Demo Feature"
    assert features[0]["display_name"] == "001 - Demo Feature"


def test_scan_all_features_display_name_avoids_duplicate_prefix(tmp_path):
    feature_dir = _create_feature(tmp_path)
    (feature_dir / "meta.json").write_text(
        json.dumps({"friendly_name": "001 - Demo Feature"}),
        encoding="utf-8",
    )

    features = scanner.scan_all_features(tmp_path)

    assert features[0]["display_name"] == "001 - Demo Feature"


def test_scan_all_features_orders_selector_rows_by_recency(tmp_path):
    older = _create_feature(tmp_path, "aaa-older-mission")
    newer = _create_feature(tmp_path, "zzz-newer-mission")
    (older / "meta.json").write_text(
        json.dumps(
            {
                "friendly_name": "Older Mission",
                "created_at": "2026-04-01T10:00:00+00:00",
                "mission_id": "01KOLDER000000000000000000",
            }
        ),
        encoding="utf-8",
    )
    (newer / "meta.json").write_text(
        json.dumps(
            {
                "friendly_name": "Newer Mission",
                "created_at": "2026-04-02T10:00:00+00:00",
                "mission_id": "01KNEWER000000000000000000",
            }
        ),
        encoding="utf-8",
    )

    features = scanner.scan_all_features(tmp_path)

    assert [feature["id"] for feature in features[:2]] == [
        "zzz-newer-mission",
        "aaa-older-mission",
    ]


def test_feature_recency_helpers_cover_timestamp_and_legacy_fallbacks():
    assert scanner._parse_created_at(None) is None
    assert scanner._parse_created_at("") is None
    assert scanner._parse_created_at("not-a-date") is None
    assert scanner._parse_created_at("2026-04-02T10:00:00Z") == scanner._parse_created_at("2026-04-02T10:00:00+00:00")
    assert scanner._parse_created_at("2026-04-02T10:00:00") == scanner._parse_created_at("2026-04-02T10:00:00+00:00")

    assert scanner._coerce_sort_mission_number(True) is None
    assert scanner._coerce_sort_mission_number(42) == 42
    assert scanner._coerce_sort_mission_number("042") == 42
    assert scanner._coerce_sort_mission_number("WP42") is None

    fallback_key = scanner._feature_recency_sort_key({"id": "legacy-mission", "meta": "not-a-dict"})
    assert fallback_key == (False, float("-inf"), False, "", False, -1, "legacy-mission")


def test_read_dashboard_feature_meta_ignores_malformed_and_non_object_json(tmp_path):
    invalid = tmp_path / "kitty-specs" / "001-invalid-meta"
    invalid.mkdir(parents=True)
    (invalid / "meta.json").write_text("{bad json", encoding="utf-8")

    assert scanner._read_dashboard_feature_meta(invalid) == ("001-invalid-meta", None)

    non_object = tmp_path / "kitty-specs" / "002-non-object-meta"
    non_object.mkdir(parents=True)
    (non_object / "meta.json").write_text('["not", "an", "object"]', encoding="utf-8")

    assert scanner._read_dashboard_feature_meta(non_object) == ("002-non-object-meta", None)


def test_build_legacy_kanban_stats_counts_lane_directories(tmp_path):
    tasks_dir = tmp_path / "tasks"
    (tasks_dir / "planned").mkdir(parents=True)
    (tasks_dir / "done" / "nested").mkdir(parents=True)
    (tasks_dir / "planned" / "WP01-demo.md").write_text("# WP01\n", encoding="utf-8")
    (tasks_dir / "done" / "nested" / "WP02-demo.md").write_text("# WP02\n", encoding="utf-8")

    stats = scanner._build_legacy_kanban_stats(tasks_dir)

    assert stats["planned"] == 1
    assert stats["done"] == 1
    assert stats["total"] == 2


def test_build_event_log_kanban_stats_surfaces_missing_event_log(tmp_path):
    feature_dir = tmp_path / "kitty-specs" / "001-missing-event-log"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-demo.md").write_text(
        "---\nwork_package_id: WP01\n---\n# Work Package Prompt: Demo\n",
        encoding="utf-8",
    )

    stats = scanner._build_event_log_kanban_stats(feature_dir, tasks_dir)

    assert stats["total"] == 0
    assert "Event log not found" in stats["error"]


def test_build_event_log_kanban_stats_tolerates_weighted_progress_failure(tmp_path, monkeypatch):
    import specify_cli.status as status_facade

    feature_dir = _create_feature(tmp_path, "001-progress-fallback")

    def fail_materialize(_feature_dir):
        raise RuntimeError("progress unavailable")

    # WP11: the dashboard read path resolves the *read-only* snapshot through
    # the status facade (`from specify_cli.status import materialize_snapshot`),
    # so patch the facade name it actually looks up — patching the reducer
    # submodule would not be seen.
    monkeypatch.setattr(status_facade, "materialize_snapshot", fail_materialize)

    stats = scanner._build_event_log_kanban_stats(feature_dir, feature_dir / "tasks")

    assert stats["total"] == 1
    assert stats["planned"] == 1
    assert "weighted_percentage" not in stats


def test_build_event_log_kanban_stats_excludes_unseeded_wps(tmp_path):
    feature_dir = tmp_path / "kitty-specs" / "001-unseeded"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-demo.md").write_text(
        """---
work_package_id: WP01
---
# Work Package Prompt: Demo
""",
        encoding="utf-8",
    )
    (feature_dir / "status.events.jsonl").write_text("", encoding="utf-8")

    stats = scanner._build_event_log_kanban_stats(feature_dir, tasks_dir)

    assert stats["total"] == 0
    assert stats["planned"] == 0


@pytest.mark.fast
def test_process_wp_file_uses_frontmatter_title_without_prompt_header(tmp_path):
    feature_dir = tmp_path / "kitty-specs" / "001-frontmatter-title"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    prompt_file = tasks_dir / "WP01-demo.md"
    prompt_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Frontmatter Demo Title\n"
        "---\n\n"
        "Body without a Work Package Prompt header.\n",
        encoding="utf-8",
    )
    _set_wp_lane(feature_dir, "WP01", "planned")

    task = scanner._process_wp_file(prompt_file, tmp_path, "planned")

    assert task is not None
    assert task["title"] == "Frontmatter Demo Title"


@pytest.mark.fast
def test_process_wp_file_falls_back_to_stem_without_title_or_prompt_header(tmp_path):
    feature_dir = tmp_path / "kitty-specs" / "001-stem-title"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    prompt_file = tasks_dir / "WP01-demo.md"
    prompt_file.write_text(
        "---\nwork_package_id: WP01\n---\n\nBody without a Work Package Prompt header.\n",
        encoding="utf-8",
    )
    _set_wp_lane(feature_dir, "WP01", "planned")

    task = scanner._process_wp_file(prompt_file, tmp_path, "planned")

    assert task is not None
    assert task["title"] == "WP01-demo"


def test_process_wp_file_raises_without_canonical_log_for_nonlegacy(tmp_path, monkeypatch):
    """A non-legacy WP with no canonical event log surfaces CanonicalStatusNotFoundError."""
    from specify_cli.status import CanonicalStatusNotFoundError

    feature_dir = tmp_path / "kitty-specs" / "001-no-canonical-log"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    prompt_file = tasks_dir / "WP01-demo.md"
    prompt_file.write_text(
        "---\nwork_package_id: WP01\n---\n# Work Package Prompt: Demo\n",
        encoding="utf-8",
    )
    # No status.events.jsonl anywhere; force the non-legacy branch.
    monkeypatch.setattr(scanner, "is_legacy_format", lambda _feature_dir: False)

    with pytest.raises(CanonicalStatusNotFoundError):
        scanner._process_wp_file(prompt_file, tmp_path, "planned")


def test_build_kanban_stats_handles_absent_and_legacy_paths(tmp_path, monkeypatch):
    feature_dir = tmp_path / "kitty-specs" / "001-legacy"
    tasks_dir = feature_dir / "tasks"
    (tasks_dir / "doing").mkdir(parents=True)
    (tasks_dir / "doing" / "WP01-demo.md").write_text("# WP01\n", encoding="utf-8")

    assert scanner._build_kanban_stats(feature_dir, {"kanban": {}})["total"] == 0

    monkeypatch.setattr(scanner, "is_legacy_format", lambda _feature_dir: True)
    stats = scanner._build_kanban_stats(feature_dir, {"kanban": {"exists": True}})

    assert stats["doing"] == 1
    assert stats["total"] == 1


def test_scan_all_features_keeps_purpose_summary_in_meta_only(tmp_path):
    feature_dir = _create_feature(tmp_path)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "friendly_name": "Demo Feature",
                "purpose_tldr": "  Build   dashboard copy  ",
                "purpose_context": " Ship\nconsistent mission wording. ",
            }
        ),
        encoding="utf-8",
    )

    features = scanner.scan_all_features(tmp_path)

    assert "purpose_tldr" not in features[0]
    assert "purpose_context" not in features[0]
    assert features[0]["meta"]["purpose_tldr"] == "Build dashboard copy"
    assert features[0]["meta"]["purpose_context"] == "Ship consistent mission wording."


def test_scan_feature_kanban_returns_prompt(tmp_path):
    feature_dir = _create_feature(tmp_path)
    lanes = scanner.scan_feature_kanban(tmp_path, feature_dir.name)
    assert "planned" in lanes
    assert lanes["planned"], "planned lane should contain prompt data"
    task = lanes["planned"][0]
    assert task["id"] == "WP01"
    assert "prompt_markdown" in task


def test_resolve_active_feature_requires_explicit_selection(tmp_path):
    """resolve_active_feature returns None — auto-detection was removed.

    Since feature_detection was deleted (WP02), the dashboard no longer
    auto-detects the active feature.  Callers must provide an explicit
    --feature flag.  This test confirms the contract: without heuristics,
    resolve_active_feature always returns None.
    """
    resolved = scanner.resolve_active_feature(tmp_path)
    assert resolved is None, (
        "resolve_active_feature must return None after removal of auto-detection"
    )


def test_project_charter_propagates_to_all_features(tmp_path):
    _create_feature(tmp_path, "001-demo-feature")
    _create_feature(tmp_path, "002-another-feature")
    charter = tmp_path / ".kittify" / "charter" / "charter.md"
    charter.parent.mkdir(parents=True)
    charter.write_text("# Project Charter\n", encoding="utf-8")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 2
    assert all(feature["artifacts"]["charter"]["exists"] for feature in features)


def test_feature_local_charter_is_ignored_without_project_charter(tmp_path):
    first = _create_feature(tmp_path, "001-demo-feature")
    _create_feature(tmp_path, "002-another-feature")
    (first / "charter.md").write_text("# Legacy Feature Charter\n", encoding="utf-8")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 2
    assert all(not feature["artifacts"]["charter"]["exists"] for feature in features)


def test_legacy_memory_path_not_resolved(tmp_path):
    """Legacy .kittify/memory/ path is NOT resolved — user must run spec-kitty upgrade."""
    _create_feature(tmp_path, "001-demo-feature")
    _create_feature(tmp_path, "002-another-feature")
    legacy = tmp_path / ".kittify" / "memory" / "charter.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("# Legacy Project Charter\n", encoding="utf-8")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 2
    assert all(not feature["artifacts"]["charter"]["exists"] for feature in features)


def test_only_canonical_path_resolved(tmp_path):
    """Only .kittify/charter/charter.md is resolved."""
    _create_feature(tmp_path)
    new_path = tmp_path / ".kittify" / "charter" / "charter.md"
    new_path.parent.mkdir(parents=True)
    new_path.write_text("canonical", encoding="utf-8")

    resolved = resolve_project_charter_path(tmp_path)
    assert resolved == new_path


def test_scan_feature_kanban_approved_lane(tmp_path):
    """WPs with canonical lane approved should land in the approved column."""
    _create_feature(tmp_path, "001-demo", lane="approved")
    lanes = scanner.scan_feature_kanban(tmp_path, "001-demo")
    assert len(lanes["approved"]) == 1
    assert len(lanes["planned"]) == 0
    assert lanes["approved"][0]["id"] == "WP01"


def test_scan_feature_kanban_lane_mapping(tmp_path):
    """claimed and in_progress both map to doing."""
    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    (feature_dir / "tasks").mkdir(parents=True)
    for wp_id, lane in [("WP01", "claimed"), ("WP02", "in_progress")]:
        (feature_dir / "tasks" / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\n---\n# Work Package Prompt: {wp_id}\n",
            encoding="utf-8",
        )
        _set_wp_lane(feature_dir, wp_id, lane)
    lanes = scanner.scan_feature_kanban(tmp_path, "001-demo")
    assert len(lanes["planned"]) == 0
    assert len(lanes["doing"]) == 2


@pytest.mark.fast
def test_scan_feature_kanban_structured_agent_metadata(tmp_path):
    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "tasks" / "WP01-agent.md").write_text(
        """---
work_package_id: WP01
agent:
  tool: codex
  model: gpt-5.4
---
# Work Package Prompt: Agent Metadata
""",
        encoding="utf-8",
    )
    _set_wp_lane(feature_dir, "WP01", "planned")

    lanes = scanner.scan_feature_kanban(tmp_path, "001-demo")

    task = lanes["planned"][0]
    assert task["agent"] == "codex"
    assert task["model"] == "gpt-5.4"


def test_dashboard_scans_prefer_coord_worktree_over_root_checkout(tmp_path):
    slug = "001-demo-feature"

    # The coordination copy only outranks the primary checkout when it is a
    # *registered* git worktree — name proposes coord-ness, the git registry
    # disposes (C-SEAM-1). A bare ``-coord``-named directory is a husk and must
    # NOT shadow the primary surface. Register the worktree on a clean seed
    # commit so this exercises the real coord-preference path.
    _git(["init", "--initial-branch=main"], tmp_path)
    _git(["config", "user.email", "scanner@example.com"], tmp_path)
    _git(["config", "user.name", "Scanner Test"], tmp_path)
    _git(["config", "commit.gpgsign", "false"], tmp_path)
    (tmp_path / "README.md").write_text("seed\n", encoding="utf-8")
    _git(["add", "README.md"], tmp_path)
    _git(["commit", "-q", "-m", "seed"], tmp_path)
    coord_worktree = tmp_path / ".worktrees" / f"{slug}-coord"
    _git(
        ["worktree", "add", "-q", "-b", f"kitty/mission-{slug}", str(coord_worktree)],
        tmp_path,
    )

    _create_feature(tmp_path, slug, lane="planned")

    coord_feature_dir = coord_worktree / "kitty-specs" / slug
    _create_feature_at(coord_feature_dir, lane="approved")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 1
    feature = features[0]

    assert feature["path"] == f".worktrees/{slug}-coord/kitty-specs/{slug}"
    assert feature["worktree"]["exists"] is True
    assert feature["worktree"]["path"] == scanner.format_path_for_display(
        str(coord_feature_dir.parents[1])
    )
    assert feature["kanban_stats"]["approved"] == 1
    assert feature["kanban_stats"]["planned"] == 0

    lanes = scanner.scan_feature_kanban(tmp_path, slug)
    assert len(lanes["approved"]) == 1
    assert len(lanes["planned"]) == 0
    assert lanes["approved"][0]["id"] == "WP01"


@pytest.mark.fast
def test_dashboard_husk_coord_dir_does_not_shadow_primary(tmp_path):
    """F-005 adversarial: a ``-coord``-NAMED directory that git does NOT
    register is a husk and must NOT outrank the primary checkout.

    Name proposes coord-ness; the git registry disposes (C-SEAM-1). Before the
    topology seam, the name-only ``endswith("-coord")`` predicate let this husk
    silently shadow the live primary surface — the split-brain this WP kills.
    """
    slug = "001-demo-feature"

    _git(["init", "--initial-branch=main"], tmp_path)
    _git(["config", "user.email", "scanner@example.com"], tmp_path)
    _git(["config", "user.name", "Scanner Test"], tmp_path)
    _git(["config", "commit.gpgsign", "false"], tmp_path)
    (tmp_path / "README.md").write_text("seed\n", encoding="utf-8")
    _git(["add", "README.md"], tmp_path)
    _git(["commit", "-q", "-m", "seed"], tmp_path)

    # Primary checkout: the authoritative, current state.
    _create_feature(tmp_path, slug, lane="planned")

    # A husk: a ``-coord``-named plain dir that was NEVER `git worktree add`-ed.
    husk_feature_dir = tmp_path / ".worktrees" / f"{slug}-coord" / "kitty-specs" / slug
    _create_feature_at(husk_feature_dir, lane="approved")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 1
    feature = features[0]
    # The husk's stale "approved" must NOT win; the primary "planned" stands.
    assert feature["path"] == f"kitty-specs/{slug}"
    assert feature["kanban_stats"]["planned"] == 1
    assert feature["kanban_stats"]["approved"] == 0


@pytest.mark.no_git_tmp_path
def test_dashboard_scan_degrades_when_registry_unreadable_in_non_git_project(
    tmp_path: Path,
) -> None:
    """WP03 seam degradation: when ``.worktrees/`` exists but the project is NOT
    a git repo, ``read_worktree_registry`` fails closed with
    ``WorktreeRegistryUnavailable``. The scanner must degrade gracefully —
    treat every worktree dir as non-coord rather than crashing the whole
    dashboard scan (covers ``scanner.py`` lines 332/336).

    Behavioural contract: a ``-coord``-named directory has no readable registry
    to consult, so it cannot be classified as a coord worktree and therefore
    must NOT outrank/shadow the primary ``kitty-specs/`` surface. The scan
    succeeds and the primary copy wins.
    """
    slug = "001-demo-feature"

    # Deliberately NO `git init`: the project dir is not a git repo, so the
    # `git worktree list --porcelain` read inside `gather_feature_paths` raises
    # WorktreeRegistryUnavailable. This is the real trigger, not a mock.
    assert not (tmp_path / ".git").exists()

    # Primary checkout surface (authoritative when the registry is unreadable).
    _create_feature(tmp_path, slug, lane="planned")

    # A ``-coord``-named directory sitting under .worktrees/. With no registry
    # it cannot be promoted to coord topology.
    husk_feature_dir = tmp_path / ".worktrees" / f"{slug}-coord" / "kitty-specs" / slug
    _create_feature_at(husk_feature_dir, lane="approved")

    # The scan completes (no crash) despite the unreadable registry.
    paths = scanner.gather_feature_paths(tmp_path)

    # The husk did NOT win: the resolved path is the primary surface, not the
    # ``.worktrees/...-coord`` copy.
    assert paths[slug] == tmp_path / "kitty-specs" / slug
    assert paths[slug] != husk_feature_dir

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 1
    feature = features[0]
    assert feature["path"] == f"kitty-specs/{slug}"
    # Primary "planned" stands; the degraded coord dir's "approved" is ignored.
    assert feature["kanban_stats"]["planned"] == 1
    assert feature["kanban_stats"]["approved"] == 0


# ── scan_feature_kanban error-handling paths ───────────────────────────────


def test_scan_feature_kanban_canonical_status_not_found_returns_empty_lanes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CanonicalStatusNotFoundError aborts WP iteration and returns empty lanes.

    Covers scanner.py lines 872-877: the except-branch warning log and the
    early ``return lanes`` that short-circuits the rest of the loop when the
    feature's event log has not yet been seeded by finalize-tasks.
    """
    from specify_cli.status import CanonicalStatusNotFoundError

    feature_dir = tmp_path / "kitty-specs" / "001-no-event-log"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-demo.md").write_text(
        "---\nwork_package_id: WP01\n---\n# Work Package Prompt: Demo\n",
        encoding="utf-8",
    )

    def _raise_canonical(*_args: object, **_kwargs: object) -> None:
        raise CanonicalStatusNotFoundError("no event log seeded")

    monkeypatch.setattr(scanner, "_process_wp_file", _raise_canonical)

    lanes = scanner.scan_feature_kanban(tmp_path, "001-no-event-log")

    assert all(len(v) == 0 for v in lanes.values()), (
        "all lanes must be empty when CanonicalStatusNotFoundError is raised "
        "during WP processing"
    )


def test_scan_feature_kanban_generic_exception_is_logged_and_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A generic Exception from _process_wp_file is logged and the WP is skipped.

    Covers scanner.py lines 878-880: the broad except-branch logger.error call
    and the ``continue`` that keeps the loop alive for subsequent WP files.
    """
    feature_dir = tmp_path / "kitty-specs" / "001-bad-wp"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-broken.md").write_text(
        "---\nwork_package_id: WP01\n---\n# Work Package Prompt: Broken\n",
        encoding="utf-8",
    )

    def _raise_generic(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated unexpected processing error")

    monkeypatch.setattr(scanner, "_process_wp_file", _raise_generic)

    # Must not propagate — the broad except catches it and continues.
    lanes = scanner.scan_feature_kanban(tmp_path, "001-bad-wp")

    assert all(len(v) == 0 for v in lanes.values()), (
        "all lanes must be empty after a broken WP is skipped via the generic "
        "exception handler"
    )


# ── NFR-006: Dashboard kanban bucketing identity ───────────────────────────


@pytest.mark.fast
def test_display_category_matches_kanban_columns():
    """All lanes produce the expected dashboard kanban column labels (NFR-006).

    Verifies that WPState.display_category() returns the correct label for
    every canonical lane, ensuring the dashboard kanban bucketing is
    consistent with the WPState model.
    """
    from specify_cli.status import wp_state_for

    expected_mapping = {
        "planned": "Planned",
        "claimed": "In Progress",
        "in_progress": "In Progress",
        "for_review": "Review",
        "in_review": "In Progress",
        "approved": "Approved",
        "done": "Done",
        "blocked": "Blocked",
        "canceled": "Canceled",
    }
    for lane, expected_label in expected_mapping.items():
        state = wp_state_for(lane)
        assert state.display_category() == expected_label, (
            f"Lane {lane}: expected {expected_label!r}, got {state.display_category()!r}"
        )


@pytest.mark.fast
def test_kanban_column_map_covers_all_lanes():
    """_KANBAN_COLUMN_FOR_LANE covers every display Lane enum member (NFR-006).

    'genesis' is a non-display lane (pre-finalize state); it is never the
    current lane of a materialized WP and has no kanban column by design, so
    it is excluded from the column map.
    """
    from specify_cli.dashboard.scanner import _KANBAN_COLUMN_FOR_LANE

    for member in Lane:
        if member is Lane.GENESIS:
            assert member not in _KANBAN_COLUMN_FOR_LANE, (
                "genesis is non-display and must not have a kanban column"
            )
            continue
        assert member in _KANBAN_COLUMN_FOR_LANE, (
            f"Lane.{member.name} missing from _KANBAN_COLUMN_FOR_LANE"
        )


# ---------------------------------------------------------------------------
# WP11 / FR-014(a) / SC-6a — dashboard reads are write-free, even during a git
# op. The dashboard MUST NOT clobber tracked status.json when serving a kanban
# request while a long-running git operation (e.g. rebase) is in progress.
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_dashboard_read_does_not_write_status_json(tmp_path):
    """The dashboard read path never writes tracked status.json (FR-014a).

    Seed an event log but no status.json, then exercise the dashboard kanban
    read. The read-only snapshot must compute progress without materializing
    the tracked status.json artifact.
    """
    feature_dir = _create_feature(tmp_path, "001-readonly-no-write")
    status_json = feature_dir / "status.json"
    # _create_feature seeds via materialize(); remove the artifact so we can
    # prove the dashboard read path does NOT recreate it.
    if status_json.exists():
        status_json.unlink()

    stats = scanner._build_event_log_kanban_stats(feature_dir, feature_dir / "tasks")

    assert "weighted_percentage" in stats, "payload unchanged: progress still computed"
    assert not status_json.exists(), (
        "dashboard read wrote tracked status.json (FR-014a clobber)"
    )


@pytest.mark.fast
def test_read_only_weighted_percentage_matches_materialize_payload(tmp_path):
    """The read-only snapshot yields the same weighted % the writer would (C-004).

    Switching from materialize() to materialize_snapshot() must not change the
    rendered kanban payload — only remove the write side-effect.
    """
    from specify_cli.status import compute_weighted_progress

    feature_dir = _create_feature(tmp_path, "001-payload-parity")

    writer_snapshot = materialize(feature_dir)
    writer_pct = round(compute_weighted_progress(writer_snapshot).percentage, 1)

    read_only_pct = scanner.read_only_weighted_percentage(feature_dir)

    assert read_only_pct == writer_pct, (
        "read-only snapshot diverged from the writing materialize() payload"
    )


def _git(args, cwd) -> None:
    import subprocess

    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.fast
def test_sc6a_dashboard_no_status_clobber_during_real_rebase(tmp_path):
    """SC-6a: a real ``git rebase`` with the dashboard serving kanban does not
    clobber tracked status.json.

    Mirrors WP07's SC-5 style with a genuine (non-mocked) conflicted rebase.
    While the rebase is paused mid-operation, the dashboard kanban read path
    must NOT write tracked status — sharing WP07's single git-op detection
    (``git_operation_in_progress``) rather than duplicating it (C-005).
    """
    import subprocess

    from specify_cli.status import git_operation_in_progress

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    _git(["init", "--initial-branch=main"], repo_root)
    _git(["config", "user.email", "wp11@example.com"], repo_root)
    _git(["config", "user.name", "WP11 Test"], repo_root)
    _git(["config", "commit.gpgsign", "false"], repo_root)

    slug = "001-dashboard-rebase"
    feature_dir = repo_root / "kitty-specs" / slug
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "tasks" / "WP01-demo.md").write_text(
        "---\nwork_package_id: WP01\nsubtasks: [\"T1\"]\n---\n# Work Package Prompt: Demo\n",
        encoding="utf-8",
    )
    append_event(
        feature_dir,
        StatusEvent(
            event_id="TESTWP01PLANNED00000000000"[:26],
            mission_slug=slug,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.PLANNED,
            at="2026-03-31T09:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="direct_repo",
        ),
    )

    status_json = feature_dir / "status.json"
    # status.json is a tracked artifact; the dashboard must never write it.
    # .gitignore keeps the rebase replay clean of any derived noise.
    (repo_root / ".gitignore").write_text("", encoding="utf-8")

    _git(["add", "."], repo_root)
    _git(["commit", "-m", "chore: baseline"], repo_root)
    # Remove status.json so we can prove the dashboard read does not recreate it.
    if status_json.exists():
        status_json.unlink()
        _git(["add", "-A"], repo_root)
        _git(["commit", "-m", "chore: drop status.json"], repo_root)

    # Diverge main vs mission branch on the same file to force a conflicted,
    # paused rebase (the long-op window).
    conflict = repo_root / "conflict.txt"
    _git(["checkout", "-b", f"kitty/mission-{slug}"], repo_root)
    conflict.write_text("mission-line\n", encoding="utf-8")
    _git(["add", "conflict.txt"], repo_root)
    _git(["commit", "-m", "feat: mission change"], repo_root)

    _git(["checkout", "main"], repo_root)
    conflict.write_text("main-line\n", encoding="utf-8")
    _git(["add", "conflict.txt"], repo_root)
    _git(["commit", "-m", "feat: main change"], repo_root)

    _git(["checkout", f"kitty/mission-{slug}"], repo_root)

    rebase = subprocess.run(
        ["git", "rebase", "main"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert rebase.returncode != 0, "rebase should pause on conflict"
    assert git_operation_in_progress(repo_root) is True

    # The dashboard serves a kanban request mid-rebase.
    stats = scanner._build_event_log_kanban_stats(feature_dir, feature_dir / "tasks")

    assert "weighted_percentage" in stats, "payload unchanged: progress still served"
    assert not status_json.exists(), (
        "dashboard clobbered tracked status.json during an active rebase "
        "(FR-014a / SC-6a violation)"
    )

    # Clean up the rebase so the worktree is not left mid-operation.
    subprocess.run(
        ["git", "rebase", "--abort"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
