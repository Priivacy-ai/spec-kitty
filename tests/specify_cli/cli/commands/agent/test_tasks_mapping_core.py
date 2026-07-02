"""Per-branch unit tests for the pure requirement-mapping core (WP04 / T018).

RED-first artifact (charter C-011): these tests import
``specify_cli.cli.commands.agent.tasks_mapping_core`` — which does NOT exist on
the lane base — so the whole module fails to collect (red) until :func:`plan_mapping`
is implemented (T019). Once green, every named branch of the ``MappingPlan``
decision entity (``data-model.md`` §MappingPlan) is exercised with ``--cov-branch``:
the offender buckets (malformed / unknown_spec_id), each mode (wp_refs / batch /
tracker_only), the replace-vs-union merge fork, the tasks.md union fallback, and
the ``unmapped_fr`` coverage projection over untouched WPs.

``plan_mapping`` is PURE (INV-4): every input here is an in-memory fact — no
filesystem, git, or clock access — so a Fake reader is unnecessary; the injected
reads ARE the request fields.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks as tasks_module
from specify_cli.cli.commands.agent.tasks import app
from specify_cli.cli.commands.agent.tasks_mapping_core import (
    MappingOffenders,
    MappingPlan,
    MappingRequest,
    plan_mapping,
)
from tests.mocked_env import setup_mocked_env

pytestmark = pytest.mark.fast


def _req(
    *,
    new_mappings: dict[str, list[str]],
    mode: str,
    replace: bool = False,
    spec_all_ids: frozenset[str] = frozenset({"FR-001", "FR-002", "NFR-001", "C-001"}),
    spec_functional_ids: frozenset[str] = frozenset({"FR-001", "FR-002"}),
    existing_all_refs: dict[str, list[str]] | None = None,
    tasks_md_refs: dict[str, list[str]] | None = None,
) -> MappingRequest:
    return MappingRequest(
        spec_all_ids=spec_all_ids,
        spec_functional_ids=spec_functional_ids,
        new_mappings=new_mappings,
        existing_all_refs=existing_all_refs or {},
        tasks_md_refs=tasks_md_refs or {},
        mode=mode,
        replace=replace,
    )


# ---------------------------------------------------------------------------
# Merge decision: union vs replace vs tasks.md fallback
# ---------------------------------------------------------------------------


def test_individual_union_merges_existing_and_new() -> None:
    plan = plan_mapping(
        _req(
            new_mappings={"WP01": ["FR-002"]},
            mode="wp_refs",
            replace=False,
            existing_all_refs={"WP01": ["FR-001"]},
        )
    )
    assert plan.to_write == {"WP01": ["FR-001", "FR-002"]}
    assert plan.offenders == MappingOffenders(malformed=(), unknown_spec_id=())


def test_individual_replace_overwrites_existing() -> None:
    plan = plan_mapping(
        _req(
            new_mappings={"WP01": ["FR-002"]},
            mode="wp_refs",
            replace=True,
            existing_all_refs={"WP01": ["FR-001"]},
        )
    )
    # replace drops the pre-existing FR-001 rather than unioning it in.
    assert plan.to_write == {"WP01": ["FR-002"]}


def test_union_falls_back_to_tasks_md_when_frontmatter_empty() -> None:
    plan = plan_mapping(
        _req(
            new_mappings={"WP01": ["FR-002"]},
            mode="wp_refs",
            replace=False,
            existing_all_refs={"WP01": []},
            tasks_md_refs={"WP01": ["FR-001"]},
        )
    )
    assert plan.to_write == {"WP01": ["FR-001", "FR-002"]}


def test_union_ignores_tasks_md_when_frontmatter_present() -> None:
    plan = plan_mapping(
        _req(
            new_mappings={"WP01": ["FR-002"]},
            mode="wp_refs",
            replace=False,
            existing_all_refs={"WP01": ["FR-001"]},
            tasks_md_refs={"WP01": ["NFR-001"]},
        )
    )
    # Frontmatter is present so the tasks.md fallback is NOT consulted.
    assert plan.to_write == {"WP01": ["FR-001", "FR-002"]}


def test_to_write_values_sorted_and_deduped() -> None:
    plan = plan_mapping(
        _req(
            new_mappings={"WP01": ["FR-002", "FR-001", "FR-002"]},
            mode="wp_refs",
            replace=True,
        )
    )
    assert plan.to_write == {"WP01": ["FR-001", "FR-002"]}


# ---------------------------------------------------------------------------
# Modes: batch + tracker_only
# ---------------------------------------------------------------------------


def test_batch_mode_maps_multiple_wps() -> None:
    plan = plan_mapping(
        _req(
            new_mappings={"WP01": ["FR-001"], "WP02": ["FR-002"]},
            mode="batch",
            replace=True,
        )
    )
    assert plan.to_write == {"WP01": ["FR-001"], "WP02": ["FR-002"]}


def test_tracker_only_mode_yields_empty_to_write() -> None:
    plan = plan_mapping(
        _req(
            new_mappings={"WP01": []},
            mode="tracker_only",
        )
    )
    # tracker-only touches tracker_refs (shell concern), never requirement_refs.
    assert plan.to_write == {}
    assert plan.offenders == MappingOffenders(malformed=(), unknown_spec_id=())


# ---------------------------------------------------------------------------
# Offenders: malformed + unknown_spec_id
# ---------------------------------------------------------------------------


def test_malformed_offender_detected() -> None:
    plan = plan_mapping(
        _req(new_mappings={"WP01": ["FR-1A"]}, mode="wp_refs", replace=True)
    )
    assert plan.offenders.malformed == ("FR-1A",)
    # Faithful to the live command: the spec-membership check is computed over the
    # SAME refs, so a malformed token is ALSO not in spec → it appears in the
    # unknown bucket too. The shell gates malformed FIRST, so only the malformed
    # arm is ever surfaced when both are present.
    assert plan.offenders.unknown_spec_id == ("FR-1A",)


def test_unknown_spec_id_offender_detected() -> None:
    plan = plan_mapping(
        _req(new_mappings={"WP01": ["FR-999"]}, mode="wp_refs", replace=True)
    )
    # Well-formed but not declared in spec.md → unknown_spec_id (not malformed).
    assert plan.offenders.malformed == ()
    assert plan.offenders.unknown_spec_id == ("FR-999",)


def test_both_offender_buckets_populated() -> None:
    plan = plan_mapping(
        _req(new_mappings={"WP01": ["FR-1A", "FR-999"]}, mode="wp_refs", replace=True)
    )
    # Mirrors the live command: format-check yields FR-1A; the spec-membership
    # check (computed over the same refs) rejects both. The shell gates malformed
    # FIRST, so only the malformed arm is surfaced when both are present.
    assert plan.offenders.malformed == ("FR-1A",)
    assert plan.offenders.unknown_spec_id == ("FR-1A", "FR-999")


def test_offenders_preserve_input_order_and_case_folding() -> None:
    plan = plan_mapping(
        _req(new_mappings={"WP01": ["fr-002", "bogus", "fr-001"]}, mode="wp_refs", replace=True)
    )
    # validate_ref_format uppercases; "BOGUS" is the sole malformed token.
    assert plan.offenders.malformed == ("BOGUS",)


# ---------------------------------------------------------------------------
# unmapped_fr coverage projection
# ---------------------------------------------------------------------------


def test_unmapped_fr_lists_uncovered_functional_ids() -> None:
    plan = plan_mapping(
        _req(new_mappings={"WP01": ["FR-001"]}, mode="wp_refs", replace=True)
    )
    # FR-002 is functional but unmapped after the write.
    assert plan.unmapped_fr == ["FR-002"]


def test_unmapped_fr_empty_when_all_functional_mapped() -> None:
    plan = plan_mapping(
        _req(
            new_mappings={"WP01": ["FR-001", "FR-002"]},
            mode="batch",
            replace=True,
        )
    )
    assert plan.unmapped_fr == []


def test_unmapped_fr_counts_untouched_wps() -> None:
    # WP02 is NOT in the new mapping but already covers FR-002 on disk; the
    # coverage projection must union it so FR-002 counts as mapped.
    plan = plan_mapping(
        _req(
            new_mappings={"WP01": ["FR-001"]},
            mode="wp_refs",
            replace=True,
            existing_all_refs={"WP02": ["FR-002"]},
        )
    )
    assert plan.unmapped_fr == []


def test_nonfunctional_refs_do_not_affect_unmapped_fr() -> None:
    # Mapping only NFR-001 / C-001 leaves both functional FRs unmapped.
    plan = plan_mapping(
        _req(new_mappings={"WP01": ["NFR-001", "C-001"]}, mode="wp_refs", replace=True)
    )
    assert plan.unmapped_fr == ["FR-001", "FR-002"]


def test_returns_mapping_plan_instance() -> None:
    plan = plan_mapping(_req(new_mappings={"WP01": ["FR-001"]}, mode="wp_refs", replace=True))
    assert isinstance(plan, MappingPlan)
    assert isinstance(plan.offenders, MappingOffenders)


# ---------------------------------------------------------------------------
# T021 -- fake-core sentinel: the plan's RETURN VALUE drives the command.
# ---------------------------------------------------------------------------
#
# The anti-shadow-code guard (FR-002): a "called-but-result-discarded" core would
# pass a grep-for-callers check while the old inline mapping/validation logic still
# ran. These tests inject a SENTINEL ``MappingPlan`` that CONTRADICTS what the real
# ``plan_mapping`` would produce and assert the command's observable result follows
# the sentinel — proving the core genuinely DRIVES ``map_requirements``.

_MID8 = "01KWF08S"


def _mapping_mission(root: Path, slug: str) -> Path:
    feature_dir = root / "kitty-specs" / slug
    (feature_dir / "tasks").mkdir(parents=True)
    (root / ".kittify").mkdir(exist_ok=True)
    (feature_dir / "tasks" / "WP01-fixture.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Fixture WP01\n"
        "execution_mode: code_change\n"
        "agent: testbot\n"
        "---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Work Packages\n\n## WP01 - fixture\n- [ ] T001 do a thing\n", encoding="utf-8"
    )
    (feature_dir / "spec.md").write_text(
        "# Spec\n\nFR-001 do a thing.\nFR-002 do another.\n", encoding="utf-8"
    )
    return feature_dir


def test_sentinel_offenders_drive_the_command_to_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sentinel ``offenders.malformed`` flips a would-succeed mapping to exit 1.

    The real ``plan_mapping`` on ``--wp WP01 --refs FR-001`` returns NO offenders
    (FR-001 is well-formed and declared), so the command would exit 0. The sentinel
    injects a malformed offender — the command refuses with exit 1 and the
    sentinel's token ONLY because the plan drives the pre-write gate.
    """
    fd = _mapping_mission(tmp_path, f"sentinel-map-refuse-{_MID8}")

    def _fake(_req: MappingRequest) -> MappingPlan:
        return MappingPlan(
            to_write={},
            offenders=MappingOffenders(malformed=("SENTINEL-BAD-9c1f",), unknown_spec_id=()),
            unmapped_fr=[],
        )

    monkeypatch.setattr(tasks_module, "plan_mapping", _fake)
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name):
        result = CliRunner().invoke(
            app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001",
             "--mission", fd.name, "--no-auto-commit", "--json"],
        )
    assert result.exit_code == 1, result.output
    assert "SENTINEL-BAD-9c1f" in result.output


def test_sentinel_to_write_drives_the_written_refs_and_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sentinel ``to_write`` / ``unmapped_fr`` drives the write + the envelope.

    The operator asks to map WP01 → FR-001, but the sentinel plan writes FR-002 and
    reports FR-001 as unmapped. The command's observable result FOLLOWS the plan:

    * ``mapped`` (echoing the operator INPUT) stays ``FR-001``,
    * ``total_mappings`` (re-read from disk AFTER the write) is ``FR-002`` — proving
      the sentinel ``to_write`` drove the frontmatter write, not the input, and
    * ``coverage.unmapped_functional`` is ``FR-001`` — proving ``unmapped_fr`` drove
      the reported coverage.
    """
    fd = _mapping_mission(tmp_path, f"sentinel-map-write-{_MID8}")

    def _fake(_req: MappingRequest) -> MappingPlan:
        return MappingPlan(
            to_write={"WP01": ["FR-002"]},
            offenders=MappingOffenders(malformed=(), unknown_spec_id=()),
            unmapped_fr=["FR-001"],
        )

    monkeypatch.setattr(tasks_module, "plan_mapping", _fake)
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name):
        result = CliRunner().invoke(
            app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001",
             "--mission", fd.name, "--no-auto-commit", "--json"],
        )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["mapped"]["WP01"] == ["FR-001"]
    assert payload["total_mappings"]["WP01"] == ["FR-002"]
    assert payload["coverage"]["unmapped_functional"] == ["FR-001"]

    # The written frontmatter itself follows the sentinel ``to_write``.
    body = (fd / "tasks" / "WP01-fixture.md").read_text(encoding="utf-8")
    assert "FR-002" in body and "FR-001" not in body
