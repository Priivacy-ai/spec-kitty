"""Pure-core unit tests for ``runtime_bridge_cores`` (#2531 WP06, T024).

Three independent concerns, all in-memory / no I/O (NFR-003, SC-004):

1. **Non-vacuousness / compat-guard checks** — the seam actually defines the
   relocated tasks.md parse family and the guard-evaluation cluster;
   ``_check_cli_guards`` / ``_check_composed_action_guard`` stay NATIVE
   ``def`` statements on ``runtime_bridge`` (thin delegates forwarding to
   :func:`runtime_bridge_cores.evaluate_guards`), never a plain re-export —
   the same discipline WP03-WP05 already apply, required because
   ``test_bridge_compat_surface.py::test_guard_b_identity_reexport_for_
   relocated_symbols`` (frozen) hardcodes the tolerated cross-module
   identity-baseline to 3 pre-existing ``runtime.next.decision``-origin
   names. The five UNTRACKED parse-family helpers (nothing patches them) ARE
   plain re-exports and DO satisfy the identity check.

2. **Parse family** — realistic tasks.md fragments (production-shaped WP ids
   / headings / requirement refs) -> assert parsed structures, exercised
   directly against ``runtime_bridge_cores`` (no filesystem).

3. **``evaluate_guards`` fixtures** — one ``ArtifactPresenceSnapshot`` per
   mission family x guard branch (SC-007: content AND order asserted),
   including the two SC-007 highest-risk fixtures the WP prompt names
   explicitly: **both fail-closed defaults** (research's and documentation's
   unknown-action branches) and the **4-way ``tasks`` ``legacy_step_id``
   union** (``tasks_outline`` / ``tasks_packages`` / ``tasks_finalize`` /
   ``None``, all composed-vocabulary, contrasted against the CLI-native
   vocabulary for the same three substeps — the two vocabularies produce
   DIFFERENT messages for the same substep; see
   ``test_cli_native_and_composed_tasks_vocabularies_diverge``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from runtime.next import runtime_bridge as rb
from runtime.next import runtime_bridge_cores as cores
from runtime.next.runtime_bridge_io import ArtifactPresenceSnapshot

# ---------------------------------------------------------------------------
# 1. Non-vacuousness / compat-guard checks
# ---------------------------------------------------------------------------

_UNTRACKED_PLAIN_REEXPORTS = (
    "_extract_wp_heading",
    "_collect_requirement_refs_for_section",
    "_iter_requirement_refs",
    "_requirement_inline_refs_suffix",
    "_is_requirement_heading",
)

_TRACKED_NATIVE_DELEGATES = (
    "_check_cli_guards",
    "_check_composed_action_guard",
    "_parse_wp_sections_from_tasks_md",
    "_parse_requirement_refs_from_tasks_md",
    "_check_requirement_mapping_ready",
)


def test_untracked_parse_helpers_are_identity_reexports() -> None:
    """Nothing patches these five (grep-verified against
    ``test_bridge_compat_surface.py``), so a plain re-export is both correct
    and required by that frozen guard's exact-baseline assertion."""
    for name in _UNTRACKED_PLAIN_REEXPORTS:
        assert getattr(rb, name) is getattr(cores, name), f"{name} is not an identity re-export"


def test_tracked_guard_and_parse_symbols_are_native_delegates() -> None:
    """These five are WP02 compat-tracked (patched directly) -- each MUST be
    a real ``def`` on ``runtime_bridge`` (``__module__ == "runtime.next.
    runtime_bridge"``), never a copy of the cores object, or
    ``test_guard_b_identity_reexport_for_relocated_symbols`` (frozen) would
    trip its hardcoded 3-symbol baseline."""
    for name in _TRACKED_NATIVE_DELEGATES:
        obj = getattr(rb, name)
        assert obj.__module__ == rb.__name__, f"{name} is not natively defined on runtime_bridge"
        assert callable(obj)


def test_evaluate_guards_is_a_real_function_on_cores() -> None:
    assert callable(cores.evaluate_guards)
    assert cores.evaluate_guards.__module__ == cores.__name__


# ---------------------------------------------------------------------------
# 2. Parse family — realistic tasks.md fragments
# ---------------------------------------------------------------------------

_REALISTIC_TASKS_MD = """\
## WP01: Writeside placement strangler

### Requirement Refs
- FR-001
- FR-002, NFR-003

Some prose in between.

## WP02 - Rawjoin adoption

Requirement: FR-004

## WP03: Docs

No requirement refs here.
"""


def test_extract_wp_heading_recognizes_wp_prefixed_heading() -> None:
    # matched_prefix_len is the offset of the char just past the WP digits
    # (here: "## WP01" is 7 chars -- '#','#',' ','W','P','0','1').
    assert cores._extract_wp_heading("## WP01: Writeside placement strangler\n") == ("WP01", 7)


def test_extract_wp_heading_rejects_non_wp_heading() -> None:
    assert cores._extract_wp_heading("## Overview\n") is None


def test_parse_wp_sections_from_tasks_md_splits_on_headings() -> None:
    sections = cores._parse_wp_sections_from_tasks_md(_REALISTIC_TASKS_MD)
    assert set(sections) == {"WP01", "WP02", "WP03"}
    assert "Requirement Refs" in sections["WP01"]
    assert "WP03" not in sections["WP01"]


def test_parse_requirement_refs_from_tasks_md_collects_per_wp_refs() -> None:
    refs = cores._parse_requirement_refs_from_tasks_md(_REALISTIC_TASKS_MD)
    assert refs["WP01"] == ["FR-001", "FR-002", "NFR-003"]
    assert refs["WP02"] == ["FR-004"]
    assert refs["WP03"] == []


def test_bridge_parse_requirement_refs_delegate_reaches_cores_wp_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression pin for the intra-seam live-lookup fix (research.md
    §Compat): the bridge's native ``_parse_requirement_refs_from_tasks_md``
    delegate must call through ITS OWN ``_parse_wp_sections_from_tasks_md``
    (patchable), not the cores-internal one -- verified behaviorally by
    monkeypatching the bridge-level symbol and observing the delegate's
    output change."""
    sentinel_sections = {"WP99": "sentinel body"}

    def _fake(_tasks_content: str) -> dict[str, str]:
        return sentinel_sections

    monkeypatch.setattr(rb, "_parse_wp_sections_from_tasks_md", _fake)
    result = rb._parse_requirement_refs_from_tasks_md("irrelevant content")
    assert set(result) == {"WP99"}


# ---------------------------------------------------------------------------
# 3. RequirementMappingFacts / _evaluate_requirement_mapping
# ---------------------------------------------------------------------------


def test_evaluate_requirement_mapping_all_satisfied_returns_empty() -> None:
    facts = cores.RequirementMappingFacts(
        spec_requirement_ids=frozenset({"FR-001", "FR-002"}),
        functional_requirement_ids=frozenset({"FR-001", "FR-002"}),
        wp_ids=("WP01", "WP02"),
        wp_requirement_refs={"WP01": ("FR-001",), "WP02": ("FR-002",)},
        feature_dir_name="042-compat-guard",
    )
    assert cores._evaluate_requirement_mapping(facts) == []


def test_evaluate_requirement_mapping_reports_missing_unknown_and_unmapped_in_order() -> None:
    facts = cores.RequirementMappingFacts(
        spec_requirement_ids=frozenset({"FR-001", "FR-002"}),
        functional_requirement_ids=frozenset({"FR-001", "FR-002"}),
        wp_ids=("WP01", "WP02", "WP03"),
        wp_requirement_refs={
            "WP01": (),  # missing
            "WP02": ("FR-999",),  # unknown
            # WP03 absent entirely from the mapping -> also missing
        },
        feature_dir_name="042-compat-guard",
    )
    [message] = cores._evaluate_requirement_mapping(facts)
    assert message.startswith("Requirement mapping incomplete before finalize-tasks: ")
    assert "missing refs for WPs: WP01, WP03" in message
    assert "unknown refs: WP02: FR-999" in message
    assert "unmapped FRs: FR-001, FR-002" in message
    assert "--mission 042-compat-guard --json" in message
    # Order: missing, then unknown, then unmapped (verbatim port of the
    # pre-extraction ``details`` append order).
    missing_idx = message.index("missing refs")
    unknown_idx = message.index("unknown refs")
    unmapped_idx = message.index("unmapped FRs")
    assert missing_idx < unknown_idx < unmapped_idx


# ---------------------------------------------------------------------------
# 4. evaluate_guards — software-dev family (CLI-native vocabulary)
# ---------------------------------------------------------------------------


def _snapshot(
    *,
    present_artifacts: frozenset[str] = frozenset(),
    status_facts: Mapping[str, Any] | None = None,
    mission_family: str = "software-dev",
    step_id: str,
    legacy_step_id: str | None = None,
    wp_advance_ready: bool | None = None,
) -> ArtifactPresenceSnapshot:
    base_status_facts: dict[str, Any] = {
        "tasks_dir_is_dir": False,
        "wp_ids": (),
        "wp_lane_raw": {},
        "wp_dependencies_present": {},
        "wp_dependency_records": (),
        "requirement_mapping_failures": (),
        "occurrence_gate_failures": (),
        "source_documented_count": 0,
        "publication_approved": False,
        "has_generated_docs": False,
    }
    if status_facts:
        base_status_facts.update(status_facts)
    return ArtifactPresenceSnapshot(
        present_artifacts=present_artifacts,
        status_facts=base_status_facts,
        mission_family=mission_family,
        step_id=step_id,
        legacy_step_id=legacy_step_id,
        wp_advance_ready=wp_advance_ready,
    )


def test_specify_guard_missing_and_present() -> None:
    assert cores.evaluate_guards(_snapshot(step_id="specify")) == ["Required artifact missing: spec.md"]
    assert cores.evaluate_guards(_snapshot(present_artifacts=frozenset({"spec.md"}), step_id="specify")) == []


def test_plan_guard_missing_and_present() -> None:
    assert cores.evaluate_guards(_snapshot(step_id="plan")) == ["Required artifact missing: plan.md"]
    assert cores.evaluate_guards(_snapshot(present_artifacts=frozenset({"plan.md"}), step_id="plan")) == []


def test_cli_native_tasks_outline_only_checks_tasks_md() -> None:
    assert cores.evaluate_guards(_snapshot(step_id="tasks_outline")) == ["Required artifact missing: tasks.md"]
    assert (
        cores.evaluate_guards(_snapshot(present_artifacts=frozenset({"tasks.md"}), step_id="tasks_outline")) == []
    )


def test_cli_native_tasks_packages_missing_files_message() -> None:
    assert cores.evaluate_guards(_snapshot(step_id="tasks_packages")) == [
        "Required: at least one tasks/WP*.md file"
    ]


def test_cli_native_tasks_packages_extends_requirement_mapping_failures() -> None:
    snapshot = _snapshot(
        present_artifacts=frozenset({"tasks_wp_files"}),
        status_facts={
            "tasks_dir_is_dir": True,
            "requirement_mapping_failures": ("missing refs for WPs: WP01",),
        },
        step_id="tasks_packages",
    )
    assert cores.evaluate_guards(snapshot) == ["missing refs for WPs: WP01"]


def test_cli_native_tasks_finalize_dir_missing_message_distinct_from_packages() -> None:
    """The dir-missing message for tasks_finalize differs from the
    tasks_packages/composed 'at least one WP*.md file' message -- do not
    unify these two strings."""
    assert cores.evaluate_guards(_snapshot(step_id="tasks_finalize")) == [
        "Required: tasks/ directory with finalized WP files"
    ]


def test_cli_native_tasks_finalize_empty_wp_files_message() -> None:
    snapshot = _snapshot(status_facts={"tasks_dir_is_dir": True}, step_id="tasks_finalize")
    assert cores.evaluate_guards(snapshot) == ["Required: at least one tasks/WP*.md file"]


def test_cli_native_tasks_finalize_missing_dependency_uses_full_stem_breaks_on_first() -> None:
    snapshot = _snapshot(
        present_artifacts=frozenset({"tasks_wp_files"}),
        status_facts={
            "tasks_dir_is_dir": True,
            "wp_dependency_records": (("WP01-writeside", True), ("WP02-rawjoin", False), ("WP03-docs", False)),
        },
        step_id="tasks_finalize",
    )
    assert cores.evaluate_guards(snapshot) == [
        "WP WP02-rawjoin missing 'dependencies' in frontmatter (run 'spec-kitty agent mission finalize-tasks')"
    ]


def test_cli_native_tasks_finalize_occurrence_gate_always_appended() -> None:
    snapshot = _snapshot(
        present_artifacts=frozenset({"tasks_wp_files"}),
        status_facts={
            "tasks_dir_is_dir": True,
            "wp_dependency_records": (("WP01-writeside", True),),
            "occurrence_gate_failures": ("occurrence classification incomplete",),
        },
        step_id="tasks_finalize",
    )
    assert cores.evaluate_guards(snapshot) == ["occurrence classification incomplete"]


def test_implement_and_review_use_wp_advance_ready() -> None:
    assert cores.evaluate_guards(_snapshot(step_id="implement", wp_advance_ready=True)) == []
    assert cores.evaluate_guards(_snapshot(step_id="implement", wp_advance_ready=False)) == [
        "Not all work packages have required status (for_review, approved, or done)"
    ]
    assert cores.evaluate_guards(_snapshot(step_id="review", wp_advance_ready=True)) == []
    assert cores.evaluate_guards(_snapshot(step_id="review", wp_advance_ready=False)) == [
        "Not all work packages are approved or done"
    ]


def test_unmatched_step_id_returns_empty() -> None:
    assert cores.evaluate_guards(_snapshot(step_id="not-a-real-step")) == []


# ---------------------------------------------------------------------------
# 5. evaluate_guards — the composed ``tasks`` vocabulary + the 4-way
#    legacy_step_id union (SC-007 highest-risk fixture, named explicitly)
# ---------------------------------------------------------------------------


def test_composed_tasks_legacy_outline_only_checks_tasks_md() -> None:
    snapshot = _snapshot(step_id="tasks", legacy_step_id="tasks_outline")
    assert cores.evaluate_guards(snapshot) == ["Required artifact missing: tasks.md"]


def test_composed_tasks_legacy_packages_checks_tasks_md_and_requirement_mapping() -> None:
    # tasks.md IS present here, so only the requirement-mapping fact surfaces.
    snapshot = _snapshot(
        present_artifacts=frozenset({"tasks.md", "tasks_wp_files"}),
        status_facts={
            "tasks_dir_is_dir": True,
            "requirement_mapping_failures": ("unmapped FRs: FR-009",),
        },
        step_id="tasks",
        legacy_step_id="tasks_packages",
    )
    assert cores.evaluate_guards(snapshot) == ["unmapped FRs: FR-009"]


def test_composed_tasks_legacy_packages_missing_tasks_md_and_wp_files_both_appended() -> None:
    """Composed tasks_packages appends BOTH the tasks.md-missing message AND
    the WP-files-missing message (two independent checks, not else-if) --
    unlike the CLI-native tasks_packages branch, which only ever emits ONE
    of these two."""
    snapshot = _snapshot(step_id="tasks", legacy_step_id="tasks_packages")
    assert cores.evaluate_guards(snapshot) == [
        "Required artifact missing: tasks.md",
        "Required: at least one tasks/WP*.md file",
    ]


@pytest.mark.parametrize("legacy_step_id", ["tasks_finalize", None])
def test_composed_tasks_terminal_union_of_all_three_legacy_checks(legacy_step_id: str | None) -> None:
    """The 4-way legacy_step_id union's terminal branch (tasks_finalize OR
    the composition-only None) -- SC-007 highest-risk fixture. Demands the
    UNION: tasks.md check + WP-files check + requirement-mapping +
    dependency-field check + occurrence-gate, all in the pinned order."""
    snapshot = _snapshot(
        status_facts={
            "requirement_mapping_failures": ("missing refs for WPs: WP01",),
            "wp_dependency_records": (("WP01-writeside", False),),
            "occurrence_gate_failures": ("occurrence classification incomplete",),
        },
        step_id="tasks",
        legacy_step_id=legacy_step_id,
    )
    assert cores.evaluate_guards(snapshot) == [
        "Required artifact missing: tasks.md",
        "Required: at least one tasks/WP*.md file",
        "occurrence classification incomplete",
    ]


def test_composed_tasks_terminal_ready_reports_requirement_and_dependency_then_occurrence() -> None:
    snapshot = ArtifactPresenceSnapshot(
        present_artifacts=frozenset({"tasks.md", "tasks_wp_files"}),
        status_facts={
            "tasks_dir_is_dir": True,
            "requirement_mapping_failures": ("missing refs for WPs: WP02",),
            "wp_dependency_records": (("WP01-writeside", True), ("WP02-rawjoin", False)),
            "occurrence_gate_failures": ("occurrence classification incomplete",),
        },
        mission_family="software-dev",
        step_id="tasks",
        legacy_step_id=None,
    )
    assert cores.evaluate_guards(snapshot) == [
        "missing refs for WPs: WP02",
        "WP WP02-rawjoin missing 'dependencies' in frontmatter (run 'spec-kitty agent mission finalize-tasks')",
        "occurrence classification incomplete",
    ]


def test_cli_native_and_composed_tasks_vocabularies_diverge_for_same_substep() -> None:
    """tasks_finalize (CLI-native) and tasks/legacy_step_id=tasks_finalize
    (composed) are NOT interchangeable -- the composed branch also checks
    tasks.md existence and requirement-mapping; the CLI-native branch does
    neither. Pinning both distinctly guards against a future "helpful"
    unification that would silently change guard_failures."""
    empty_tasks_dir_status = {"tasks_dir_is_dir": False}
    cli_native = cores.evaluate_guards(_snapshot(status_facts=empty_tasks_dir_status, step_id="tasks_finalize"))
    composed = cores.evaluate_guards(
        _snapshot(status_facts=empty_tasks_dir_status, step_id="tasks", legacy_step_id="tasks_finalize")
    )
    assert cli_native == ["Required: tasks/ directory with finalized WP files"]
    assert composed == [
        "Required artifact missing: tasks.md",
        "Required: at least one tasks/WP*.md file",
    ]
    assert cli_native != composed


# ---------------------------------------------------------------------------
# 6. evaluate_guards — research mission family (incl. its fail-closed default)
# ---------------------------------------------------------------------------


def test_research_scoping_methodology_synthesis_single_artifact_checks() -> None:
    assert cores.evaluate_guards(_snapshot(mission_family="research", step_id="scoping")) == [
        "Required artifact missing: spec.md"
    ]
    assert cores.evaluate_guards(_snapshot(mission_family="research", step_id="methodology")) == [
        "Required artifact missing: plan.md"
    ]
    assert cores.evaluate_guards(_snapshot(mission_family="research", step_id="synthesis")) == [
        "Required artifact missing: findings.md"
    ]


def test_research_gathering_both_conditions_independently_appended() -> None:
    snapshot = _snapshot(mission_family="research", step_id="gathering")
    assert cores.evaluate_guards(snapshot) == [
        "Required artifact missing: source-register.csv",
        "Insufficient sources documented (need >=3)",
    ]
    ready = _snapshot(
        present_artifacts=frozenset({"source-register.csv"}),
        status_facts={"source_documented_count": 3},
        mission_family="research",
        step_id="gathering",
    )
    assert cores.evaluate_guards(ready) == []


def test_research_output_both_conditions_independently_appended() -> None:
    snapshot = _snapshot(mission_family="research", step_id="output")
    assert cores.evaluate_guards(snapshot) == [
        "Required artifact missing: report.md",
        "Publication approval gate not passed",
    ]


def test_research_unknown_action_fail_closed_default() -> None:
    """SC-007 highest-risk fixture #1 -- the research fail-closed default
    (v1 P1 silent-pass fix): ANY unrecognized action must produce a
    non-empty failures list, never an empty (silent-pass) one."""
    snapshot = _snapshot(
        present_artifacts=frozenset(
            {"spec.md", "plan.md", "tasks.md", "source-register.csv", "findings.md", "report.md"}
        ),
        status_facts={"source_documented_count": 5, "publication_approved": True},
        mission_family="research",
        step_id="not-a-real-research-action",
    )
    assert cores.evaluate_guards(snapshot) == [
        "No guard registered for research action: not-a-real-research-action"
    ]


# ---------------------------------------------------------------------------
# 7. evaluate_guards — documentation mission family (its fail-closed default)
# ---------------------------------------------------------------------------


def test_documentation_single_artifact_checks() -> None:
    assert cores.evaluate_guards(_snapshot(mission_family="documentation", step_id="discover")) == [
        "Required artifact missing: spec.md"
    ]
    assert cores.evaluate_guards(_snapshot(mission_family="documentation", step_id="audit")) == [
        "Required artifact missing: gap-analysis.md"
    ]
    assert cores.evaluate_guards(_snapshot(mission_family="documentation", step_id="design")) == [
        "Required artifact missing: plan.md"
    ]
    assert cores.evaluate_guards(_snapshot(mission_family="documentation", step_id="validate")) == [
        "Required artifact missing: audit-report.md"
    ]
    assert cores.evaluate_guards(_snapshot(mission_family="documentation", step_id="publish")) == [
        "Required artifact missing: release.md"
    ]


def test_documentation_generate_custom_message() -> None:
    snapshot = _snapshot(mission_family="documentation", step_id="generate")
    assert cores.evaluate_guards(snapshot) == [
        "Required artifact missing: docs/**/*.md (no Markdown files found under docs/)"
    ]
    ready = _snapshot(
        status_facts={"has_generated_docs": True}, mission_family="documentation", step_id="generate"
    )
    assert cores.evaluate_guards(ready) == []


def test_documentation_accept_is_terminal_noop() -> None:
    assert cores.evaluate_guards(_snapshot(mission_family="documentation", step_id="accept")) == []


def test_documentation_unknown_action_fail_closed_default() -> None:
    """SC-007 highest-risk fixture #2 -- the documentation fail-closed
    default."""
    snapshot = _snapshot(mission_family="documentation", step_id="not-a-real-doc-action")
    assert cores.evaluate_guards(snapshot) == [
        "No guard registered for documentation action: not-a-real-doc-action"
    ]
