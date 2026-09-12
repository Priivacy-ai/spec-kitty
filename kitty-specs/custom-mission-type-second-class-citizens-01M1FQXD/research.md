# Research: Custom mission types are second-class citizens

**Mission**: `custom-mission-type-second-class-citizens-01M1FQXD`
**Phase**: plan
**Author**: planner-priti (profile-loaded)
**Purpose**: settle the research-phase checkpoint spec.md Decision 2 (C-005) requires
before FR-004/#3831 can be scoped — is the legacy `Mission`/`mission.yaml` schema
compatible with the modern org-tier `MissionType`/governance-profile system without a
schema bridge? This is the "real org-pack fixture" evidence Decision 2 calls for; a prior
investigation built one and called `resolve_mission_type_context` against it. Every claim
below was independently re-verified against this checkout's live source
(`d1474edb4`, `main`-based) before being written here.

---

## R1 — The two schemas under comparison

### R1.1 Legacy `Mission`/`mission.yaml` (`src/specify_cli/mission.py`)

`MissionConfig` (`mission.py:161-186`) is a `pydantic.BaseModel` with `extra="forbid"`
(a typo in any field is a hard validation error, not a silent no-op). Verified fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | `str` | yes | |
| `description` | `str` | yes | |
| `version` | `str` | yes | `pattern=r"^\d+\.\d+\.\d+$"` — strict semver |
| `domain` | `Literal["software", "research", "writing", "seo", "other"]` | yes | **closed 5-value enum** |
| `workflow` | `WorkflowConfig` | yes | `phases: list[PhaseConfig]`, `min_length=1` |
| `artifacts` | `ArtifactsConfig` | yes | `required: list[str]`, `optional: list[str]` |
| `paths` | `dict[str, str]` | no (default `{}`) | keys validated against `VALID_PATH_KEYS` |
| `validation` | `ValidationConfig` | no (default) | `checks: list[str]`, `custom_validators: bool` |
| `mcp_tools` | `MCPToolsConfig \| None` | no | |
| `agent_context` | `str \| None` | no | |
| `task_metadata` | `TaskMetadataConfig \| None` | no | |
| `commands` | `dict[str, CommandConfig] \| None` | no | |
| `task_types` | `dict[str, TaskTypeConfig] \| None` | no | |

`PhaseConfig` (`mission.py:85-91`, `extra="forbid"`): `name: str`, `description: str` —
**both required**, every phase carries a human description. `ArtifactsConfig`
(`mission.py:94-100`, `extra="forbid"`): `required: list[str]`, `optional: list[str]` —
**two named buckets**, no per-step scoping.

Resolution today: `_mission_path_by_name` (`mission.py:78-83`) checks exactly two tiers —
`kittify_dir / "missions" / <name>` (project) then `_packaged_missions_dir() / <name>`
(built-in). No third (org) tier exists on this path. `get_mission_for_feature`
(`mission.py:756-803`) reads `mission_type` from `meta.json`, calls `get_mission_by_name`,
and on `MissionNotFoundError` falls back to `"software-dev"` behind a bare
`warnings.warn(...)` (`mission.py:802`, confirmed near the function's end, no other
signal).

### R1.2 Modern org-tier `MissionTypeProfile` / governance system (`src/charter`)

`MissionTypeProfile` (`src/charter/activation/mission_type_profiles.py:117-157+`,
`extra="forbid"`) is architecturally separate: `mission_type: str`, `id: str` (bound to
`mission_type` by an invariant, not free-standing identity), `template_set: str | None`,
and seven `selected_<kind>: list[str]` doctrine-activation lists (directives, tactics,
paradigms, styleguides, toolguides, procedures, agent profiles) plus
`selected_mission_step_contracts`. **No `workflow`/`domain`/`version`/`paths`/
`validation`/`task_metadata`/`commands`/`task_types` field exists on this model or its
resolution context.**

`action_sequence` — the org-tier analogue closest to `workflow.phases` — resolves as a
**bare `list[str]`** of step IDs (verified: `mission_type_profiles.py:409`,
`resolve_action_sequence_layer`/`_resolve_with_extends_fallback`). It carries no
per-step `description`, unlike `PhaseConfig.description` which is a required field.

The artifact-requirement analogue is `expected-artifacts.yaml`
(`mission_type_profiles.py` ~L101-102, ~L1099-1128,
`resolve_org_expected_artifacts` in `src/charter/activation/org_expected_artifacts.py`):
a mapping keyed on `schema_version` / `mission_type` / **`required_by_step`** — artifacts
required *per workflow step*, not `ArtifactsConfig`'s flat `required`/`optional` pair.
There is no `optional` concept at all on this side; collapsing `required_by_step` into
`ArtifactsConfig.required` (list) would either lose the per-step scoping or require
inventing a policy for which step's requirement set becomes "the" required list — a
genuinely lossy collapse, not a renaming.

A **third** schema exists in the same neighbourhood:
`packs/built-in/missions/<type>/mission-runtime.yaml`
(`mission.steps[{id, name, description, order, depends_on, agent-profile}]`) — closer in
shape to `workflow.phases` (it does carry per-step names/descriptions) — but it is
resolved by yet another independent reader,
`src/runtime/next/runtime_bridge_io.py::_runtime_template_key`, which neither
`MissionTypeProfile` nor `_mission_path_by_name` consult. A bridge would therefore need
to reconcile **three** independent resolvers/schemas (legacy `Mission`, org-tier
`MissionTypeProfile` + `expected-artifacts.yaml`, and `mission-runtime.yaml`'s own
reader), not two.

### R1.3 Live resolution confirms the org tier genuinely works — for its own consumers

`resolve_mission_type_context` was called end-to-end against a real, three-tier org-pack
fixture (project `.kittify/doctrine/mission_types/<type>/`, an activated org pack's
`mission_types/<type>/`, then built-in) and **successfully resolved** a custom mission
type's `action_sequence` and doctrine selections. This confirms the org-tier system is not
theoretical — it is a working resolver — but its output shape (a `MissionTypeProfile` /
`action_sequence` list / `expected-artifacts.yaml` map) does not carry what
`Mission`/`MissionConfig` needs to construct a valid instance: no `domain` classification
exists anywhere in the org tier (an adapter would have to invent a mapping policy from
whole cloth, e.g. deciding which of the 5 closed enum values a `qa`-type mission type maps
to, with no source data to derive it from), no `version` semver exists (an adapter would
fabricate a placeholder like `"1.0.0"`), and `workflow.phases[].description` has no source
(the bare `action_sequence` strings carry no description text to backfill it from).

### R1.4 Why fabricated placeholder values are a correctness problem, not a typing formality

`Mission.get_workflow_phases()` / `.get_required_artifacts()` / `.get_template()` are real
methods with real downstream consumers — confirmed call sites include
`src/specify_cli/dossier/manifest.py`, `src/specify_cli/core/worktree.py`,
`src/specify_cli/mission_v1/compat.py`, and `src/specify_cli/runtime/resolver.py`. A
fabricated `version="1.0.0"` or an empty-description `PhaseConfig` returned by these
methods would misrepresent the org-tier mission type's actual behaviour to every one of
those consumers — not merely satisfy `pydantic`'s validator. This is the concrete reason a
"just adapt the shapes" bridge is real design/schema work, not a small patch.

---

## R2 — Verdict: SPLIT

The legacy `MissionConfig` pydantic schema and the modern org-tier `MissionTypeProfile`
schema are **not compatible without new schema/migration work**. Evidence summary (full
detail in R1 above):

| `MissionConfig` field | Org-tier analogue | Compatible without new work? |
|---|---|---|
| `workflow.phases` (named, described, min 1) | `action_sequence: list[str]` (bare step IDs, no description) | **No** — description text has no source |
| `artifacts.required` / `.optional` | `expected-artifacts.yaml` `required_by_step` (per-step map, no "optional" concept) | **No** — lossy collapse, no optional analogue |
| `domain` (closed 5-value enum) | *(none)* | **No** — no source to derive from |
| `version` (semver) | *(none)* | **No** — would be fabricated |
| `paths` / `validation` / `task_metadata` / `commands` / `task_types` | *(none)* | **No** — no representation anywhere in org tier |
| *(third schema)* `mission-runtime.yaml` steps (own resolver, `_runtime_template_key`) | — | Adds a **third** resolver needing reconciliation, not a shortcut |

## R3 — Consequence for this mission's scope

- **FR-004** (org-tier lookup in `_mission_path_by_name`/`get_mission_for_feature`) is
  **DESCOPED** from this mission, per spec.md's own conditional text (FR-004: "IF the
  plan-phase investigation ... finds the legacy `Mission` schema and the org-tier
  `MissionType` schema compatible ... If incompatible, this FR is descoped") and C-005/
  C-006. It becomes a **tracked follow-up issue**, described here for a human/later
  mission to file (this plan does not file it):
  - **Title**: "Bridge the legacy `Mission`/`mission.yaml` schema to the org-tier
    `MissionTypeProfile` system for `_mission_path_by_name`/`get_mission_for_feature`"
  - **Scope** (one paragraph): resolve the three-schema reconciliation problem identified
    in R1.2 — legacy `MissionConfig` (`workflow.phases` with descriptions, flat
    `required`/`optional` artifacts, closed `domain` enum, semver `version`), org-tier
    `MissionTypeProfile` + `expected-artifacts.yaml` (bare `action_sequence`, per-step
    `required_by_step`, no `domain`/`version`), and `mission-runtime.yaml`'s independent
    step schema (has per-step descriptions but its own resolver,
    `runtime_bridge_io.py::_runtime_template_key`) — into one coherent org-tier
    consultation path for the legacy `Mission` loader, without fabricating placeholder
    values for fields real downstream consumers
    (`dossier/manifest.py`, `core/worktree.py`, `mission_v1/compat.py`,
    `src/specify_cli/runtime/resolver.py`) actually read. **Per spec.md C-002**, this
    bridge MUST reuse `resolve_existing_org_roots`/the existing org-roots precedence
    convention already used by `resolve_org_expected_artifacts`
    (`src/charter/activation/org_expected_artifacts.py`) and its callers
    (`mission_type_profiles.py::_resolve_expected_artifacts_slot`,
    `dossier/manifest.py::ManifestRegistry.load_manifest`,
    `src/specify_cli/runtime/resolver.py`) — not invent a third org-tier-walking
    mechanism. This constraint travels with the tracked
    issue itself (stated here, not only in this mission's own closed spec.md) so the future
    mission that picks it up does not have to re-derive it.
  - **Note**: this follow-up is **different scope** from #2660 (see spec.md's
    "Relationship to #2660" section, carried forward unchanged from spec phase — do not
    fold this follow-up into #2660 either).
- **FR-005** (loud, CLI-visible fallback signal replacing the filtered
  `warnings.warn` at `mission.py:802`) is **explicitly NOT descoped** by the SPLIT — per
  spec.md, "This FR applies regardless of the FR-004 split outcome." This mission still
  fixes the silent fallback in `get_mission_for_feature` (verified: the sole
  `warnings.warn` call inside that function's `except MissionNotFoundError` branch,
  `mission.py:802`) to be CLI-visible, independent of whether the org tier is ever
  consulted. See `plan.md` §Deferred Question 5 / §Blast Radius for the fix-site detail
  and non-regression scope.
- **PR closure shape** (per spec.md SC-006 / Decision 2 / the charter's Issue Closure
  Linkage Rule): `Closes #3830`, `Closes #3832`, `Refs #3831` (never `Closes #3831` for a
  partial fix) — plus a PR-body/tracker reference to the follow-up issue description above
  once it is actually filed (filing itself is out of this plan's scope; recording what to
  file is the research-checkpoint's job per Decision 2).

---

## R4 — Supporting evidence for the FR-006/FR-008 plan-phase design decisions

Referenced by `plan.md`'s five deferred-question decisions; kept here so `plan.md` states
the decision and rationale without repeating the underlying tables.

### R4.1 Verified template field shapes (four mission types)

| Type | Template | Fields (template order) | Shape per field |
|---|---|---|---|
| `software-dev` | `packs/built-in/missions/software-dev/templates/plan-template.md` | `Language/Version` (primary, L26), `Primary Dependencies`, `Storage`, `Testing`, `Target Platform`, `Project Type`, `Performance Goals`, `Constraints`, `Scale/Scope` — all under `## Technical Context` (L14) | bulleted `**Label**: value` lines, one container heading |
| `documentation` | `packs/built-in/missions/documentation/templates/documentation-plan-template.md` | `Documentation Framework` (primary, L14), `Languages Detected` (L15), `Output Format` (L22), `Hosting Platform` (L23), `Build Commands` (L24) — all under `## Technical Context` (L12) | bulleted `**Label**: value` lines, one container heading, same shape as software-dev **for `Documentation Framework`/`Languages Detected`/`Output Format`/`Hosting Platform` (inline value)** — but `Build Commands` (L24) writes its value as a bulleted sub-list on L26-28, *below* the label, not inline after the colon (verified directly against the template this session); see `plan.md` Decision 3(a) for the value-capture extension this requires. `Generator Tools` (L16, sub-list on L18-20) has the identical bulleted-sub-list shape but is not in this declared field list — verified, left out unchanged (see `plan.md` Decision 3(a)) |
| `research` | `packs/built-in/missions/research/templates/research-plan-template.md` | `Research Question` (primary, under `## Research Context`, L9-11) plus `Data Sources` (peer, `### Data Sources` nested under `## Methodology`, L56) | primary field: bulleted `**Label**: value` list under its own `##` heading; peer field: **nested `###` heading** with bulleted sub-lists in its body — TWO DIFFERENT container headings, not one shared section |
| `plan` | `packs/built-in/missions/plan/templates/plan-plan-skeleton.md` | `Problem Decomposition` (primary, `## Problem Decomposition`, L17), `Scope — MoSCoW` (`## Scope — MoSCoW`, L32), `Sequencing & Prioritisation` (`## Sequencing & Prioritisation`, L41), `Decisions` (`## Decisions` → nested `### Decision D-1`, L53/63) | FOUR separate top-level `##` sections, each its own field, each a **different shape**: markdown table (Problem Decomposition, Sequencing & Prioritisation), bulleted `- **Field**: value` list (Scope — MoSCoW), nested `###` heading (Decisions) |

Re-verified directly (not trusted from the mission brief): all four files read in full this
session; row contents match the brief's claims exactly, including line numbers.

**Note on `research`'s two-field count versus spec.md's three-name list**: spec.md's
Decision 3/NFR-004 name "Research Context, Methodology, Data Sources" as `research`'s three
scaffolded fields, but `## Methodology` (L22) has no bold-field/table content of its own
directly under it — only nested `###` subheadings (`Research Design` L24, `Data Sources`
L56, `Analysis Framework` L73). It is a grouping container, not itself a checkable field.
This table's two-field row is therefore the accurate statement of what has checkable
content, not a silent narrowing — see `plan.md` Decision 1 for the full reconciliation
against spec.md's field-name list.

### R4.2 Verified bracket-placeholder vocabulary (research / plan templates)

`research-plan-template.md`: `[RESEARCH QUESTION]`, `[Primary question]`, `[Academic field
or industry domain]`, `[When research will be conducted]`, `[Databases, tools, budget,
time]`, `[Context point 1]` / `[Context point 2]`, `[Database 1: e.g., IEEE Xplore,
PubMed, arXiv]` / `[Database 2]`, `[Gray literature, industry reports, etc.]`, `[List
search terms]`, `[What qualifies for review]`, `[What will be filtered out]`, `[How
findings will be categorized]`, `[Thematic analysis | Meta-analysis | Narrative
synthesis]`, `[How source quality will be evaluated]`.

`plan-plan-skeleton.md`: `[PLAN TITLE]`, `[Sub-problem statement]`, `[Cluster name]`,
`[SP-# or none]`, `[Without this, the plan fails its purpose]` (and the other three
MoSCoW bullet placeholders), `[High/Low]`, `[Why it goes first]` / `[Why it goes next]`,
`[Decision title]`, `[Problem, drivers, constraints forcing this decision now]`, `[Chosen
option, stated plainly]`, `[Why this option wins]`, `[Alternative A]` / `[Alternative B]`,
`[reason]`, `[Accepted trade-offs, positive and negative]`, `[Failure scenario]`,
`[High/Med/Low]`, `[Mitigation or accepted risk]`, `[Downstream action 1]` / `[Downstream
action 2]`, `[Anything still unresolved after decomposition and decision-making]`.

None of these literals exist in the current `_PLACEHOLDER_PATTERNS` list
(`src/specify_cli/missions/_substantive.py:31-49`), confirmed by inspection — that list's
17 entries are all software-dev/spec-shaped (`[NEEDS CLARIFICATION...]`, `[e.g., ...]`,
`[FEATURE]`, `[###-feature...]`, `[Short title]`, etc.).

### R4.3 Verified existing detector code this mission's fix reuses

- `_has_substantive_technical_context` (`_substantive.py:158-195`) — confirmed two
  independent hardcoded literals: the container-heading regex
  `r"##\s+Technical Context\s*\n..."` (L160-161) and the primary-field regex
  `r"\*\*Language/Version\*\*[ \t]*:..."` (L171-172); the peer-field scan
  (L185-189, `r"^[ \t]*(?:[-*][ \t]+)?\*\*(?P<label>[^*\n]+)\*\*..."`) already tolerates an
  optional leading `-`/`*` bullet marker per its own FR-013/#1896 comment.
- `_has_substantive_fr_row` (`_substantive.py:71-97`) — table-row half (L80-90,
  `_FR_TABLE_ROW` regex + descriptive-column check) already knows how to find
  non-placeholder content in a table row's first columns, generalized today only to rows
  literally prefixed `FR-###`.
- `is_substantive(file_path, kind)` (`_substantive.py:261-281`) dispatches purely on
  `kind` (`"spec"` / `"plan"`); it takes **no mission-type or template parameter today** —
  confirmed by reading the full function signature and body. Any mission-type-aware
  generalization requires extending this signature, not merely changing the private
  helper it calls.

### R4.4 Verified `mission_setup_plan.py` call-site shape

Exactly two `kind="plan"` call sites, both confirmed by grep against
`is_substantive(` in the file: `_commit_plan_if_substantive` (L794,
`if is_substantive(plan_file, "plan"):`) and `setup_plan` (L1230,
`plan_is_substantive = is_substantive(plan_file, "plan")`). A third call,
`spec_is_substantive = is_substantive(spec_file, "spec")` (L553), is `kind="spec"` and out
of FR-006's scope (it is FR-008's territory, see below).

`_resolve_plan_template` (L586-649) returns a `ResolutionResult`
(`src/charter/offering/resolver.py:62-65`: `path: Path`, `tier: ResolutionTier`,
`mission: str | None`) — the actually-resolved plan template for the mission's type.
`_commit_plan_if_substantive` **already receives** `plan_template: ResolutionResult` as an
explicit keyword parameter (confirmed in its signature, L769-778); `setup_plan` computes
`plan_template` once (L1215) and passes it into `_commit_plan_if_substantive` (L1238) *and*
uses it for `_scaffold_plan_template` — the same resolved value is already threaded through
both `kind="plan"` call sites today, just not yet into `is_substantive` itself.

### R4.5 Verified `kind="spec"` non-extension rationale (FR-008)

`mission_check_prerequisites.py:364`'s guard
(`mission_type != "software-dev" or is_substantive(spec_file, "spec")`) is the sole
`kind="spec"` call site relevant to FR-008. `is_substantive(..., "spec")` routes to
`_has_substantive_fr_row`, which looks for `FR-###` rows. Grepped directly:
`packs/built-in/missions/research/templates/research-spec-template.md` and
`packs/built-in/missions/plan/templates/plan-spec-skeleton.md` contain **zero** `FR-`
occurrences (confirmed: `grep -n "FR-" <both files>` returns no matches, exit code 1).
There is no FR-vocabulary in either type's spec template to derive a template-derived
check from — the FR-006 mechanism (which depends on a template declaring named fields to
check) has nothing to generalize onto for these two types' spec check today. See
`plan.md` §Deferred Question 5 for how this is recorded at the call site.

---

## R5 — Supporting evidence for the Gate Set (plan.md)

Independently verified against `.github/workflows/ci-quality.yml` (not assumed from the
mission brief) so `plan.md`'s gate-set statement is grounded rather than guessed:

- **`mission-loader-coverage` job** (ci-quality.yml, "mission_loader coverage gate
  (NFR-003, mission #505 / WP07)") runs `--cov=src/specify_cli/mission_loader` against
  `tests/unit/mission_loader/` + `tests/integration/test_mission_run_command.py`, with
  `--cov-fail-under=90`. **Correction to a name-based assumption**: despite the name,
  `src/specify_cli/mission_loader/` (`command.py`, `contract_synthesis.py`, `errors.py`,
  `registry.py`, `retrospective.py`, `validator.py`) is a **different package** from
  `src/specify_cli/mission.py` (the FR-005 fix site, containing `_mission_path_by_name`/
  `get_mission_for_feature`) — confirmed by directory listing; `mission.py` is not inside
  `mission_loader/` and none of `mission_loader/`'s modules define either function. **This
  named CI gate does not cover FR-005's file** despite the superficial name match — flagged
  explicitly in `plan.md` rather than assumed to apply.
- **`fast-tests-missions` job** runs `tests/missions/ tests/specify_cli/missions/` with
  `--cov=specify_cli.mission --cov=specify_cli.mission_metadata
  --cov=charter.offering.missions` (no per-package `--cov-fail-under` on this job) — this
  DOES cover `mission.py` (singular `specify_cli.mission`), so FR-005's file has real test
  coverage tracked, just not gated at a numeric floor by this job. It does **not** cover
  `specify_cli.missions` (plural — `_substantive.py`'s package) in its `--cov=` flags,
  despite running that package's tests (`tests/specify_cli/missions/`, which includes
  `test_substantive_gate_formats.py`).
- **`diff-coverage` job** enforces `--fail-under=90` on changed lines restricted to a
  `critical_paths` allowlist (ci-quality.yml L3370-3399, `critical_paths=(` … `)`).
  Verbatim entries, re-read directly from the array this session (not paraphrased):
  `src/kernel/*`, `src/charter/offering/*`, `src/charter/*`, `src/specify_cli/status/*`,
  `src/specify_cli/lanes/branch_naming.py`, `src/specify_cli/dashboard/handlers/*`,
  `src/specify_cli/dashboard/scanner.py`, `src/specify_cli/merge/*`, `src/runtime/next/*`,
  `src/mission_runtime/*`, `src/specify_cli/review/verdict_commit_queue.py`,
  `src/specify_cli/review/artifacts.py`, `src/specify_cli/review/cycle.py`,
  `src/specify_cli/cli/commands/agent/tasks_move_task.py`,
  `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`. (Correction from an
  earlier paraphrase in this document: the dashboard entries are the two specific paths
  above, not a blanket `dashboard/*`; `src/charter/offering/*` is its own separate entry
  alongside `src/charter/*`; the two `tasks_*` entries are not under `review/`.)
  **`src/runtime/next/*` matches FR-001-003's fix site**
  (`src/runtime/next/runtime_bridge_composition.py`) — the enforced 90% diff-coverage gate
  applies to that file. **None of** `src/specify_cli/mission_step_contracts/executor.py`
  (FR-001-003's other file), `src/specify_cli/mission.py` (FR-005), `src/specify_cli/
  missions/_substantive.py`, `mission_setup_plan.py`, or `mission_check_prerequisites.py`
  (FR-006/FR-008) match any critical-path entry — those changed lines are covered only by
  the job's advisory, non-blocking full-diff pass, not the enforced 90% gate.
- **"architecture/docs consistency"** job (ci-quality.yml ~L798, `[ENFORCED] Run
  architecture/docs consistency tests on changed markdown`) fires only when the PR changes
  markdown under `docs/architecture/` — this mission's fix sites are Python, and its
  `kitty-specs/` artifacts are not under `docs/`, so this gate is inert unless a WP
  deliberately adds/edits an ADR under `docs/architecture/`.
- No project-wide `--cov-fail-under` exists in `pyproject.toml`'s `[tool.coverage.*]`
  tables (confirmed: only `[tool.coverage.run]`/`[tool.coverage.paths]`, no threshold
  key) — the only numeric coverage floors are the named per-package/critical-path jobs
  enumerated above.

See `plan.md` §Gate Set for how these findings translate into this mission's included/
excluded gate list.
