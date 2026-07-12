"""Pure cores for ``runtime.next.runtime_bridge`` (#2531 WP06).

**Zero-dependency leaf.** This module is the bottom of the decomposition's
import DAG (research.md §Seams / §Import DAG): it may import stdlib,
``Lane``/decision types, and nothing else — in particular NEVER
``runtime_bridge_io`` / ``runtime_bridge_engine`` / ``runtime_bridge_composition``
/ ``runtime_bridge_identity``, and never a top-level edge back to the thin
residual ``runtime_bridge`` (C-007). Every function here is pure: no
filesystem, no git, no ``meta.json`` reads. Two pure clusters live here:

1. **The tasks.md parse family** (T021) — moved VERBATIM from
   ``runtime_bridge.py:343-473`` (pre-decomposition line numbers;
   ``:382-512`` on the WP05 tip this WP branches from):
   ``_extract_wp_heading``, ``_parse_wp_sections_from_tasks_md``,
   ``_parse_requirement_refs_from_tasks_md``,
   ``_collect_requirement_refs_for_section``, ``_iter_requirement_refs``,
   ``_requirement_inline_refs_suffix``, ``_is_requirement_heading``. Zero
   non-stdlib imports travel with them — the flagship pure leaf.
2. **The guard inversion** (T022/T023, FR-009) —
   ``evaluate_guards(snapshot) -> list[str]`` folds ALL THREE guard
   offenders (``_check_cli_guards``, ``_check_composed_action_guard``,
   ``_check_requirement_mapping_ready`` — all three still *reachable* at
   ``runtime_bridge.<name>``, but their branch-heavy decisions now live
   here) over the ``ArtifactPresenceSnapshot`` fact-port WP05's
   ``gather_artifact_presence`` (``runtime_bridge_io.py``) produces. The
   port gathers; this module decides. ``RequirementMappingFacts`` +
   ``_evaluate_requirement_mapping`` is the same fact-port/pure-core split
   applied to ``_check_requirement_mapping_ready``'s own decision tail
   (T023 — CC~22 -> two residual gather-only branches + this pure helper).

**Structural typing, not an import, for the snapshot shape.** ``evaluate_guards``
takes ``_ArtifactPresenceSnapshotLike`` — a :class:`typing.Protocol` defined
here, satisfied structurally by ``runtime_bridge_io.ArtifactPresenceSnapshot``
without this module importing that class (which would violate the "cores
imports nothing but stdlib" invariant above). mypy checks the shape match
across modules with no runtime coupling either direction.

**SC-007 — the load-bearing invariant.** ``guard_failures`` must be
content-and-order-identical to the pre-extraction inline guards, for every
branch x every mission family (software-dev / research / documentation),
including BOTH fail-closed defaults (research's and documentation's unknown
-action branches) and the 4-way ``tasks`` ``legacy_step_id`` union. Do not
"clean up" a failure string or reorder an ``.extend()`` call — see
``tests/runtime/test_bridge_cores.py`` for the pinned fixtures.

**Serial co-ownership note.** This module is *also* edited by WP07 (the
Decision-builder core, FR-011/``DecisionEnvelope``/``step_or_blocked``) — the
top-of-file structure above (parse family, then guard inversion) is left
clean so WP07 appends a third cluster below without churning this one.

3. **The Decision-builder** (T025/T026, FR-011) — ``DecisionEnvelope`` +
   ``step_or_blocked(envelope, guard_failures, *, prompt_exists) -> Decision``
   collapse the 29 open-coded ``Decision(...)`` constructions (and the 4x
   ``_state_to_action -> _build_prompt_or_error -> step-or-blocked`` triad)
   that used to be scattered across ``runtime_bridge.py``'s three public
   entries (``decide_next_via_runtime``, ``query_current_state``,
   ``answer_decision_via_runtime``'s ``_map_runtime_decision`` cluster).
   The blocked/query/terminal/decision_required branch is pure; the step
   branch is **port-injected** via ``prompt_exists`` because
   ``Decision.__post_init__`` (``decision.py:129``) stats disk
   (``Path(prompt).is_file()``) for ``kind="step"`` — production passes
   ``Path.is_file``, unit tests pass an in-memory stub (data-model.md
   §DecisionEnvelope). Neither ``DecisionEnvelope`` nor ``step_or_blocked``
   ever stamps ``timestamp``/``run_id``/``decision_id`` themselves — those
   are threaded through by the residual caller (NFR-003).

De-godding effort: https://github.com/Priivacy-ai/spec-kitty/issues/2531
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from runtime.next.decision import Decision, DecisionKind, InvalidStepDecision

# ---------------------------------------------------------------------------
# Local literal duplicates of runtime_bridge's module constants — avoids a
# circular top-level import back into runtime_bridge for five small string
# literals (``runtime_bridge`` imports THIS module at its own top level).
# Mirrors the "small local constant, no cross-module coupling" convention
# already used by the WP03/WP04/WP05 seams for their own leaf constants (see
# e.g. ``runtime_bridge_io.py``'s ``KITTIFY_DIR`` / ``MISSION_RUNTIME_YAML``).
# ---------------------------------------------------------------------------
SPEC_ARTIFACT = "spec.md"
PLAN_ARTIFACT = "plan.md"
TASKS_ARTIFACT = "tasks.md"
MISSING_ARTIFACT_MESSAGE = "Required artifact missing: {name}"
MISSING_TASK_FILES_MESSAGE = "Required: at least one tasks/WP*.md file"

_REQUIREMENT_REF_PATTERN = re.compile(r"\b(?:FR|NFR|C)-\d+\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# T021 — tasks.md parse family (moved VERBATIM from runtime_bridge.py)
# ---------------------------------------------------------------------------


def _extract_wp_heading(line: str) -> tuple[str, int] | None:
    """Return ``(wp_id, matched_prefix_len)`` for a tasks.md WP heading line."""
    heading_level = 0
    while heading_level < len(line) and line[heading_level] == "#":
        heading_level += 1
    if heading_level < 2 or heading_level > 4:
        return None
    if heading_level >= len(line) or not line[heading_level].isspace():
        return None

    cursor = heading_level
    while cursor < len(line) and line[cursor].isspace():
        cursor += 1

    work_package_prefix = "Work Package"
    if line.startswith(work_package_prefix, cursor):
        prefix_end = cursor + len(work_package_prefix)
        if prefix_end >= len(line) or not line[prefix_end].isspace():
            return None
        cursor = prefix_end
        while cursor < len(line) and line[cursor].isspace():
            cursor += 1

    if not line.startswith("WP", cursor):
        return None
    digit_start = cursor + 2
    digit_end = digit_start + 2
    if digit_end > len(line) or not line[digit_start:digit_end].isdigit():
        return None

    wp_id = line[cursor:digit_end]
    if digit_end == len(line):
        return wp_id, digit_end

    trailing = line[digit_end]
    if trailing == ":" or not (trailing.isalnum() or trailing == "_"):
        return wp_id, digit_end
    return None


def _parse_wp_sections_from_tasks_md(tasks_content: str) -> dict[str, str]:
    """Extract WP sections from tasks.md keyed by WP ID."""
    sections: dict[str, str] = {}
    matches: list[tuple[str, int, int]] = []
    content_len = len(tasks_content)
    search_at = 0

    while True:
        wp_pos = tasks_content.find("WP", search_at)
        if wp_pos == -1:
            break

        line_start = tasks_content.rfind("\n", 0, wp_pos) + 1
        newline = tasks_content.find("\n", wp_pos)
        line_end = content_len if newline == -1 else newline + 1
        search_at = line_end

        if not tasks_content.startswith("##", line_start):
            continue

        line = tasks_content[line_start:line_end]
        heading = _extract_wp_heading(line)
        if heading is not None:
            wp_id, matched_prefix_len = heading
            matches.append((wp_id, line_start + matched_prefix_len, line_start))

    for idx, (wp_id, start, _line_start) in enumerate(matches):
        end = matches[idx + 1][2] if idx + 1 < len(matches) else len(tasks_content)
        sections[wp_id] = tasks_content[start:end]

    return sections


def _parse_requirement_refs_from_tasks_md(tasks_content: str) -> dict[str, list[str]]:
    """Parse requirement references per WP from tasks.md content."""
    return {
        wp_id: _collect_requirement_refs_for_section(section_content)
        for wp_id, section_content in _parse_wp_sections_from_tasks_md(tasks_content).items()
    }


def _collect_requirement_refs_for_section(section_content: str) -> list[str]:
    """Collect deduplicated requirement refs from one WP section."""
    refs: list[str] = []
    in_requirement_ref_list = False
    for line in section_content.splitlines():
        stripped_line = line.strip()
        if in_requirement_ref_list:
            if not stripped_line:
                continue
            if stripped_line.startswith(("-", "*")):
                refs.extend(_iter_requirement_refs(stripped_line))
                continue
            in_requirement_ref_list = False

        suffix = _requirement_inline_refs_suffix(line)
        if suffix is not None:
            refs.extend(_iter_requirement_refs(suffix))
            continue
        if _is_requirement_heading(stripped_line):
            in_requirement_ref_list = True
    return list(dict.fromkeys(refs))


def _iter_requirement_refs(text: str) -> list[str]:
    """Return normalized requirement refs found in ``text``."""
    return [ref_id.upper() for ref_id in _REQUIREMENT_REF_PATTERN.findall(text)]


def _requirement_inline_refs_suffix(line: str) -> str | None:
    """Return inline requirement-ref suffix when ``line`` is a label/value row."""
    lower_line = line.lower()
    if "requirement" not in lower_line:
        return None
    prefix, separator, suffix = line.partition(":")
    if separator and "requirement" in prefix.lower():
        return suffix
    return None


def _is_requirement_heading(stripped_line: str) -> bool:
    """Return whether a markdown heading denotes a requirement refs section."""
    if not stripped_line.startswith("#"):
        return False

    body = stripped_line.lstrip("#").strip()
    if not body:
        return False

    normalized_body = body.replace("*", "").strip().lower()
    return normalized_body in {"requirement", "requirements", "requirement refs", "requirements refs"}


# ---------------------------------------------------------------------------
# T023 — requirement-mapping fact-port/pure-core split
# (``_check_requirement_mapping_ready``'s decision tail, CC~22 -> here)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RequirementMappingFacts:
    """Facts ``_check_requirement_mapping_ready``'s residual gathers (spec.md
    requirement IDs, WP requirement refs, the WP id list) so the missing
    /unknown/unmapped decision below can be pure (T023)."""

    spec_requirement_ids: frozenset[str]
    functional_requirement_ids: frozenset[str]
    wp_ids: tuple[str, ...]
    wp_requirement_refs: Mapping[str, tuple[str, ...]]
    feature_dir_name: str


def _evaluate_requirement_mapping(facts: RequirementMappingFacts) -> list[str]:
    """Pure decision tail of ``_check_requirement_mapping_ready`` (T023).

    Verbatim port of the original function's logic from its
    ``wp_ids = sorted(...)`` line onward — only the source of ``wp_ids`` /
    ``wp_requirement_refs`` / the two requirement-id sets changed (now facts,
    gathered by the residual instead of read here).
    """
    missing_requirement_refs_wps: list[str] = []
    unknown_requirement_refs: dict[str, list[str]] = {}
    mapped_requirement_ids: set[str] = set()

    for wp_id in facts.wp_ids:
        refs = facts.wp_requirement_refs.get(wp_id, ())
        if not refs:
            missing_requirement_refs_wps.append(wp_id)
            continue

        unknown_refs = sorted(ref for ref in refs if ref not in facts.spec_requirement_ids)
        if unknown_refs:
            unknown_requirement_refs[wp_id] = unknown_refs
        else:
            mapped_requirement_ids.update(refs)

    unmapped_functional_requirements = sorted(facts.functional_requirement_ids - mapped_requirement_ids)
    if not (missing_requirement_refs_wps or unknown_requirement_refs or unmapped_functional_requirements):
        return []

    details: list[str] = []
    if missing_requirement_refs_wps:
        details.append(f"missing refs for WPs: {', '.join(missing_requirement_refs_wps)}")
    if unknown_requirement_refs:
        unknown_parts = [
            f"{wp_id}: {', '.join(refs)}"
            for wp_id, refs in sorted(unknown_requirement_refs.items())
        ]
        details.append(f"unknown refs: {'; '.join(unknown_parts)}")
    if unmapped_functional_requirements:
        details.append(f"unmapped FRs: {', '.join(unmapped_functional_requirements)}")

    return [
        "Requirement mapping incomplete before finalize-tasks: "
        + "; ".join(details)
        + ". Run `spec-kitty agent tasks map-requirements --batch ... --mission "
        + f"{facts.feature_dir_name}"
        + " --json` or update WP requirement_refs before finalizing."
    ]


# ---------------------------------------------------------------------------
# T022 — ArtifactPresenceSnapshot consumer: pure evaluate_guards(snapshot)
# ---------------------------------------------------------------------------


class _ArtifactPresenceSnapshotLike(Protocol):
    """Structural shape ``evaluate_guards`` needs from the FR-009 fact-port
    snapshot (data-model.md §ArtifactPresenceSnapshot / ``runtime_bridge_io.
    ArtifactPresenceSnapshot``), without importing that class — cores.py
    stays a stdlib-only pure leaf (research.md §Import DAG: no
    ``runtime_bridge_io`` import here). Satisfied structurally; mypy checks
    the match across modules with no runtime coupling either direction.

    ``wp_advance_ready`` is populated by the residual guard delegates in
    ``runtime_bridge.py`` (not by ``gather_artifact_presence`` itself) —
    see their docstrings for why: it threads the pre-existing, unmoved
    ``_should_advance_wp_step`` I/O read through so its own WP02 compat
    reach stays intact, without adding a new gather concern to the WP05
    port or its already-green test suite.

    Declared via read-only ``@property`` getters (not plain attribute
    annotations) so this Protocol is satisfied by ``ArtifactPresenceSnapshot``
    -- a ``@dataclass(frozen=True)`` -- whose fields are read-only; a plain
    annotation declares a *settable* Protocol member and mypy correctly
    rejects a frozen dataclass instance against it.
    """

    @property
    def present_artifacts(self) -> frozenset[str]: ...

    @property
    def status_facts(self) -> Mapping[str, Any]: ...

    @property
    def mission_family(self) -> str: ...

    @property
    def step_id(self) -> str: ...

    @property
    def legacy_step_id(self) -> str | None: ...

    @property
    def wp_advance_ready(self) -> bool | None: ...


_CLI_TASKS_STEP_IDS = frozenset({"tasks_outline", "tasks_packages", "tasks_finalize"})


def evaluate_guards(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    """Pure decision folding ``_check_cli_guards`` + ``_check_composed_action_guard``
    (+ ``_check_requirement_mapping_ready``'s tail, via the precomputed
    ``status_facts["requirement_mapping_failures"]`` fact) over one
    ``ArtifactPresenceSnapshot``-shaped input (FR-009, SC-007).

    Dispatch mirrors the two original functions' mission-family branching
    exactly: research / documentation get their own fail-closed-by-default
    action tables; anything else (including the literal ``"software-dev"``
    family AND any unrecognized family value — the original composed guard
    fell through to the software-dev chain for both) gets the software-dev
    dispatch, which further branches on whether ``step_id`` carries the
    CLI-guard native vocabulary (``tasks_outline``/``tasks_packages``/
    ``tasks_finalize``) or the composed-action vocabulary (``tasks``, with
    ``legacy_step_id`` disambiguating the same three sub-cases plus the
    terminal/union case) — the two vocabularies produce genuinely different
    messages for the tasks family (see ``_evaluate_cli_tasks_guard`` vs.
    ``_evaluate_composed_tasks_guard`` — do not unify them further).
    """
    if snapshot.mission_family == "research":
        return _evaluate_research_guards(snapshot)
    if snapshot.mission_family == "documentation":
        return _evaluate_documentation_guards(snapshot)
    return _evaluate_software_dev_guards(snapshot)


def _check_artifact_present(snapshot: _ArtifactPresenceSnapshotLike, tag: str) -> list[str]:
    """Shared single-artifact-presence check (``MISSING_ARTIFACT_MESSAGE`` shape).

    ``present_artifacts`` is gathered via ``Path.is_file()`` uniformly
    (``runtime_bridge_io.gather_artifact_presence``); the software-dev
    branches' original reads used ``.exists()`` for spec.md/plan.md/tasks.md.
    The two predicates are equivalent for this fixed, well-known artifact-tag
    set in practice (none of these three names is ever expected to collide
    with a same-named directory — see ``gather_artifact_presence``'s own
    docstring for the identical rationale), so using the single ``is_file()``
    -based fact uniformly here reproduces both predicates' real-world
    behavior without carrying two parallel presence sets.
    """
    if tag in snapshot.present_artifacts:
        return []
    return [MISSING_ARTIFACT_MESSAGE.format(name=tag)]


# ---------------------------------------------------------------------------
# research / documentation mission families (composed-action guard only —
# the CLI-guard vocabulary never carries these families)
# ---------------------------------------------------------------------------


def _evaluate_gathering_guard(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    failures = _check_artifact_present(snapshot, "source-register.csv")
    if snapshot.status_facts["source_documented_count"] < 3:
        failures.append("Insufficient sources documented (need >=3)")
    return failures


def _evaluate_output_guard(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    failures = _check_artifact_present(snapshot, "report.md")
    if not snapshot.status_facts["publication_approved"]:
        failures.append("Publication approval gate not passed")
    return failures


def _evaluate_research_guards(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    """Research composition guard chain, incl. the fail-closed default for
    unknown research actions (v1 P1 silent-pass fix — SC-007 highest-risk
    fixture; do not weaken)."""
    action = snapshot.step_id
    if action == "scoping":
        return _check_artifact_present(snapshot, SPEC_ARTIFACT)
    if action == "methodology":
        return _check_artifact_present(snapshot, PLAN_ARTIFACT)
    if action == "gathering":
        return _evaluate_gathering_guard(snapshot)
    if action == "synthesis":
        return _check_artifact_present(snapshot, "findings.md")
    if action == "output":
        return _evaluate_output_guard(snapshot)
    return [f"No guard registered for research action: {action}"]


def _evaluate_generate_docs_guard(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    if snapshot.status_facts["has_generated_docs"]:
        return []
    return ["Required artifact missing: docs/**/*.md (no Markdown files found under docs/)"]


def _evaluate_documentation_guards(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    """Documentation composition guard chain, incl. the fail-closed default
    for unknown documentation actions (SC-007 highest-risk fixture)."""
    action = snapshot.step_id
    if action == "discover":
        return _check_artifact_present(snapshot, SPEC_ARTIFACT)
    if action == "audit":
        return _check_artifact_present(snapshot, "gap-analysis.md")
    if action == "design":
        return _check_artifact_present(snapshot, PLAN_ARTIFACT)
    if action == "generate":
        return _evaluate_generate_docs_guard(snapshot)
    if action == "validate":
        return _check_artifact_present(snapshot, "audit-report.md")
    if action == "publish":
        return _check_artifact_present(snapshot, "release.md")
    if action == "accept":
        return []  # terminal status commit step; publish gate is sufficient
    return [f"No guard registered for documentation action: {action}"]


# ---------------------------------------------------------------------------
# software-dev family — shared by BOTH the CLI-guard vocabulary
# (specify/plan/tasks_outline/tasks_packages/tasks_finalize/implement/review)
# and the composed-action vocabulary (specify/plan/tasks[+legacy_step_id]/
# implement/review). specify/plan/implement/review are identical between the
# two vocabularies; only "tasks" diverges (see the two tasks-guard helpers).
# ---------------------------------------------------------------------------


def _tasks_dir_ready(snapshot: _ArtifactPresenceSnapshotLike) -> bool:
    return bool(snapshot.status_facts["tasks_dir_is_dir"]) and "tasks_wp_files" in snapshot.present_artifacts


def _first_missing_dependency_failure(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    """Break-on-first-missing dependency check, message keyed by the WP
    file's FULL stem (e.g. ``WP03-foo``), matching the pre-extraction
    ``wp_file.stem`` — NOT the short ``WP03``-style id ``wp_lane_raw`` /
    ``wp_dependencies_present`` are keyed by (data-model.md §wp_dependency_records)."""
    for stem, has_deps in snapshot.status_facts["wp_dependency_records"]:
        if not has_deps:
            return [f"WP {stem} missing 'dependencies' in frontmatter (run 'spec-kitty agent mission finalize-tasks')"]
    return []


def _evaluate_tasks_packages_guard(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    """CLI-native ``tasks_packages`` — no tasks.md existence check (unlike
    the composed vocabulary's equivalent branch)."""
    if not _tasks_dir_ready(snapshot):
        return [MISSING_TASK_FILES_MESSAGE]
    return list(snapshot.status_facts["requirement_mapping_failures"])


def _evaluate_tasks_finalize_guard(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    """CLI-native ``tasks_finalize`` — distinct dir-missing message from the
    composed vocabulary, no requirement-mapping check, unconditional
    occurrence-gate check."""
    failures: list[str] = []
    if not snapshot.status_facts["tasks_dir_is_dir"]:
        failures.append("Required: tasks/ directory with finalized WP files")
    elif "tasks_wp_files" not in snapshot.present_artifacts:
        failures.append(MISSING_TASK_FILES_MESSAGE)
    else:
        failures.extend(_first_missing_dependency_failure(snapshot))
    failures.extend(snapshot.status_facts["occurrence_gate_failures"])
    return failures


def _evaluate_cli_tasks_guard(step_id: str, snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    if step_id == "tasks_outline":
        return _check_artifact_present(snapshot, TASKS_ARTIFACT)
    if step_id == "tasks_packages":
        return _evaluate_tasks_packages_guard(snapshot)
    return _evaluate_tasks_finalize_guard(snapshot)


def _evaluate_composed_tasks_packages_guard(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    failures = _check_artifact_present(snapshot, TASKS_ARTIFACT)
    if not _tasks_dir_ready(snapshot):
        failures.append("Required: at least one tasks/WP*.md file")
    else:
        failures.extend(snapshot.status_facts["requirement_mapping_failures"])
    return failures


def _evaluate_composed_tasks_terminal_guard(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    """Composed ``tasks`` for ``legacy_step_id in {"tasks_finalize", None}`` —
    the union of all three legacy substep checks (no weakening)."""
    failures = _check_artifact_present(snapshot, TASKS_ARTIFACT)
    if not _tasks_dir_ready(snapshot):
        failures.append("Required: at least one tasks/WP*.md file")
    else:
        failures.extend(snapshot.status_facts["requirement_mapping_failures"])
        failures.extend(_first_missing_dependency_failure(snapshot))
    failures.extend(snapshot.status_facts["occurrence_gate_failures"])
    return failures


def _evaluate_composed_tasks_guard(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    legacy_step_id = snapshot.legacy_step_id
    if legacy_step_id == "tasks_outline":
        return _check_artifact_present(snapshot, TASKS_ARTIFACT)
    if legacy_step_id == "tasks_packages":
        return _evaluate_composed_tasks_packages_guard(snapshot)
    return _evaluate_composed_tasks_terminal_guard(snapshot)


def _evaluate_wp_iteration_guard(step_id: str, snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    if snapshot.wp_advance_ready:
        return []
    if step_id == "implement":
        return ["Not all work packages have required status (for_review, approved, or done)"]
    return ["Not all work packages are approved or done"]


def _evaluate_software_dev_guards(snapshot: _ArtifactPresenceSnapshotLike) -> list[str]:
    step_id = snapshot.step_id
    if step_id == "specify":
        return _check_artifact_present(snapshot, SPEC_ARTIFACT)
    if step_id == "plan":
        return _check_artifact_present(snapshot, PLAN_ARTIFACT)
    if step_id in _CLI_TASKS_STEP_IDS:
        return _evaluate_cli_tasks_guard(step_id, snapshot)
    if step_id == "tasks":
        return _evaluate_composed_tasks_guard(snapshot)
    if step_id in ("implement", "review"):
        return _evaluate_wp_iteration_guard(step_id, snapshot)
    return []


# ---------------------------------------------------------------------------
# T025/T026 — DecisionEnvelope + step_or_blocked (FR-011)
#
# Collapses the 29 open-coded ``Decision(...)`` constructions in
# ``runtime_bridge.py`` (19 blocked / 4 step / 4 query / 1 terminal / 1
# decision_required — data-model.md §DecisionEnvelope) plus the 4x
# ``_state_to_action -> _build_prompt_or_error -> step-or-blocked`` triad
# into one normalized-input value object + one materializer.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionEnvelope:
    """Normalized inputs :func:`step_or_blocked` builds a :class:`Decision`
    from (data-model.md §DecisionEnvelope).

    Every field here mirrors a :class:`~runtime.next.decision.Decision`
    constructor argument of the same name, MINUS ``guard_failures`` (threaded
    as :func:`step_or_blocked`'s own second positional parameter — several
    call sites default it independently of the rest of the envelope) and
    MINUS ``is_query`` (derived from ``kind == DecisionKind.query``; every one
    of the 29 original sites set ``is_query`` 1:1 with that condition, never
    independently). ``timestamp``/``run_id``/``decision_id`` are ordinary
    pass-through fields here — the caller/residual computes and threads their
    values (a single ``now = datetime.now(UTC).isoformat()`` per
    ``decide_next_via_runtime`` call, ``run_ref.run_id``, the runtime's own
    ULIDs, …); neither this dataclass nor :func:`step_or_blocked` ever mints
    a fresh one (NFR-003 — the builder must stay deterministic and testable
    without monkeypatching a clock or an ID generator).

    For ``kind == DecisionKind.step`` envelopes, ``reason`` carries the
    pre-computed fallback reason to use if ``prompt_file`` is ``None``
    (mirrors each of the 4 original triads' own ``prompt_error or
    "<site-default>"`` computation — the literal default differs by call
    site, e.g. ``"no_prompt_template"`` vs ``"prompt_file_not_resolvable"``,
    so the residual computes it, not this shared core). It is unused for the
    "prompt_file resolved but no longer exists on disk" branch, which always
    used the literal ``"prompt_file_not_resolvable"`` across all 4 original
    triads (verified against the pre-extraction source) — :func:`step_or_
    blocked` hard-codes that literal for that branch rather than depending on
    ``reason`` (see its docstring).
    """

    kind: str
    agent: str | None
    mission_slug: str
    mission: str
    mission_state: str
    timestamp: str
    action: str | None = None
    wp_id: str | None = None
    workspace_path: str | None = None
    prompt_file: str | None = None
    reason: str | None = None
    progress: dict[str, Any] | None = None
    origin: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None
    step_id: str | None = None
    decision_id: str | None = None
    input_key: str | None = None
    question: str | None = None
    options: list[str] | None = None
    preview_step: str | None = None


def _non_step_decision(envelope: DecisionEnvelope, guard_failures: list[str]) -> Decision:
    """Pure materializer for every ``kind`` other than ``step``.

    Covers the 19 ``blocked`` + 4 ``query`` + 1 ``terminal`` + 1
    ``decision_required`` sites (25 of the 29) uniformly: a straight
    field-for-field pass-through, no I/O, no branching on ``prompt_file``.
    """
    return Decision(
        kind=envelope.kind,
        agent=envelope.agent,
        mission_slug=envelope.mission_slug,
        mission=envelope.mission,
        mission_state=envelope.mission_state,
        timestamp=envelope.timestamp,
        action=envelope.action,
        wp_id=envelope.wp_id,
        workspace_path=envelope.workspace_path,
        prompt_file=envelope.prompt_file,
        reason=envelope.reason,
        guard_failures=guard_failures,
        progress=envelope.progress,
        origin=envelope.origin,
        run_id=envelope.run_id,
        step_id=envelope.step_id,
        decision_id=envelope.decision_id,
        input_key=envelope.input_key,
        question=envelope.question,
        options=envelope.options,
        is_query=envelope.kind == DecisionKind.query,
        preview_step=envelope.preview_step,
    )


def _step_decision(envelope: DecisionEnvelope, guard_failures: list[str]) -> Decision:
    """Materialize the ``kind="step"`` branch of a :class:`Decision`.

    Only called once ``step_or_blocked`` has already confirmed
    ``envelope.prompt_file`` resolves via the injected ``prompt_exists``
    predicate. ``Decision.__post_init__`` (``decision.py:129``) re-checks the
    same fact on disk (``Path(prompt).is_file()``); this defense-in-depth is
    intentional (it mirrors the pre-extraction try/except
    :class:`InvalidStepDecision` race guard verbatim — see
    :func:`step_or_blocked`), not redundant dead code to be removed.
    """
    return Decision(
        kind=DecisionKind.step,
        agent=envelope.agent,
        mission_slug=envelope.mission_slug,
        mission=envelope.mission,
        mission_state=envelope.mission_state,
        timestamp=envelope.timestamp,
        action=envelope.action,
        wp_id=envelope.wp_id,
        workspace_path=envelope.workspace_path,
        prompt_file=envelope.prompt_file,
        guard_failures=guard_failures,
        progress=envelope.progress,
        origin=envelope.origin,
        run_id=envelope.run_id,
        step_id=envelope.step_id,
    )


def _blocked_from_step_envelope(
    envelope: DecisionEnvelope, guard_failures: list[str], *, reason: str | None
) -> Decision:
    """Materialize the ``kind="blocked"`` fallback of a ``kind="step"`` envelope."""
    return Decision(
        kind=DecisionKind.blocked,
        agent=envelope.agent,
        mission_slug=envelope.mission_slug,
        mission=envelope.mission,
        mission_state=envelope.mission_state,
        timestamp=envelope.timestamp,
        reason=reason,
        action=envelope.action,
        wp_id=envelope.wp_id,
        workspace_path=envelope.workspace_path,
        guard_failures=guard_failures,
        progress=envelope.progress,
        origin=envelope.origin,
        run_id=envelope.run_id,
        step_id=envelope.step_id,
    )


def step_or_blocked(
    envelope: DecisionEnvelope,
    guard_failures: list[str] | None,
    *,
    prompt_exists: Callable[[str], bool],
) -> Decision:
    """Materialize a :class:`Decision` from a :class:`DecisionEnvelope` (FR-011).

    The ``blocked``/``query``/``terminal``/``decision_required`` branch is
    PURE (:func:`_non_step_decision` — no I/O, no branching). The ``step``
    branch is PORT-INJECTED: it calls ``prompt_exists`` (production passes
    ``Path.is_file``; unit tests pass an in-memory stub) instead of relying
    solely on ``Decision.__post_init__``'s own disk stat, so the decision of
    "does this WP/step have a usable prompt" is testable without touching a
    filesystem. This collapses the 4x pre-extraction triad exactly:

    1. ``prompt_file is None`` -> blocked, using ``envelope.reason`` (the
       residual's pre-computed ``prompt_error or "<site-default>"`` — see
       ``DecisionEnvelope.reason``'s docstring for why the literal default
       does not need to be reproduced here).
    2. ``prompt_file`` resolves via ``prompt_exists`` -> ``kind="step"``.
    3. ``prompt_file`` was truthy but ``Decision.__post_init__`` still raises
       :class:`InvalidStepDecision` (the file vanished between the
       ``prompt_exists`` check and construction — the original race guard) ->
       blocked, with the literal ``"prompt_file_not_resolvable"`` reason.
       Verified against all 4 pre-extraction triads: whenever the ORIGINAL
       code reached its own ``except InvalidStepDecision`` clause,
       ``prompt_file`` was already non-``None`` (so its own ``_build_prompt_
       or_error``-sourced error was always ``None`` there), meaning every one
       of the 4 sites' ``prompt_error or "prompt_file_not_resolvable"``
       always evaluated to the literal — never the ``prompt_error`` value.

    ``guard_failures`` normalizes ``None`` to ``[]`` here (several original
    call sites passed ``guard_failures or []``; others passed nothing at all,
    relying on ``Decision``'s own default-factory ``[]`` — both collapse to
    the same empty list here).
    """
    resolved_guard_failures = list(guard_failures) if guard_failures else []

    if envelope.kind != DecisionKind.step:
        return _non_step_decision(envelope, resolved_guard_failures)

    if envelope.prompt_file is not None and prompt_exists(envelope.prompt_file):
        try:
            return _step_decision(envelope, resolved_guard_failures)
        except InvalidStepDecision:
            pass  # file vanished between the prompt_exists check and
            # construction — fall through to the blocked branch below,
            # exactly like the pre-extraction try/except race guard.

    blocked_reason = envelope.reason if envelope.prompt_file is None else "prompt_file_not_resolvable"
    return _blocked_from_step_envelope(envelope, resolved_guard_failures, reason=blocked_reason)
