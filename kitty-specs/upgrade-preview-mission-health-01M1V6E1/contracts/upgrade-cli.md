# Upgrade CLI and JSON Contract

Audience: agentic-framework-core-team. Updated: 2026-09-06.
Normative for FR-001-006, NFR-001/002 and existing consent/worktree compatibility.

## Verified Legacy Authority

Do not edit or loosen the pinned consumer schema:

`kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json`

SHA-256: `62ff29b6121919a60ca0cc9e55eaccc7204db202a6d7c1c0f0ccdf0892d6357a`.
It fixes schema_version=1, additionalProperties=false at root and nested objects,
case/decision enums and rendered_human maxLength=1024. Its decision enum includes
BLOCK_INCOMPATIBLE_FLAGS; `compat/planner.py:_EXIT_CODE_MAP` maps it to 2.
Current documented use is incompatible --cli/--project. This mission explicitly
extends that existing decision's invocation-validation use to invalid --target,
without adding an enum/case/key or falsifying schema compatibility.

The existing compatibility Plan is a schema/invocation verdict, not the
upgrade write plan. Existing default actual --json returns an upgrade outcome;
--project --json currently returns planner JSON without applying even absent
--dry-run. Preserve this distinction, not just the common dry-run example.

## Flag Matrix

All preview/guidance rows are non-mutating from process entry, no matter TTY,
CI, current markers, SaaS toggle or confirmation flags.

| Flags / context | Behavior and representation |
| --- | --- |
| --dry-run [--project] | Human complete assessment; no application |
| --dry-run --json [--project] | Pinned legacy planner; bounded summary of repairs and full-plan hint in rendered_human, no extra keys |
| --project --json (no --dry-run) | Existing planner-only route, still no application; semantic process code |
| --plan-json [--project] [--dry-run] [--json] | New explicit full-plan schema, always preview; redundant --json/--dry-run accepted |
| default human / --project human, no preview | Existing apply; target/schema validation before global bootstrap; normal confirmation |
| default --json, no --project/preview | Existing actual-upgrade outcome JSON EXCEPT too-new schema: pinned legacy compatibility planner, process 5, no bootstrap |
| --cli [--json] [--dry-run] | Existing project-agnostic CLI guidance; --json uses its legacy shape; target/worktree flags retain existing ignored guidance semantics |
| no project, default (including --dry-run/legacy --json) | Existing CLI-guidance fallback |
| no project, --project legacy | Existing project-required error path; no bootstrap |
| no project, --plan-json | Full-plan blocked: project_not_initialized, no effects; no fallback to a different JSON shape |
| --cli --project | Flag conflict; exit 2, no mutation |
| --plan-json --cli | Flag conflict; full-plan blocked, exit 2, no mutation |
| --yes / --force on preview | Accepted but never executes, prompts or authorizes drift/mission repair |
| --no-worktrees | Select project/global only, no worktree discovery/stamping/application; keep existing scope |
| --verbose / -v after upgrade | Human detail only; no additional stdout for machine rows |
| --no-nag | Existing suppression; preview suppresses network/persistence even without it |

Hidden --agent-choice/--agent-check/--agent-latest precedence is determined by
resolved effective intent, not only the presence of preview switches. Resolve
a standalone hidden operation as its own intent (hidden options and their
ordinary presentation options, including --json); preserve its existing behavior,
including legitimate preference writes, even outside a project. Do not relabel
that standalone operation as implicit guidance merely because no project exists.

When hidden options accompany a preview/guidance route, reject before hidden
dispatch: explicit --dry-run/--plan-json, implicit planner-only --project --json,
explicit --cli guidance, or default no-project guidance selected by the ordinary
non-hidden route. This includes --agent-latest alone in such combinations, not
just --agent-choice. No preference/cache/bootstrap writes or prompts occur.
Rejection is process 2: --plan-json selects a full-plan blocked envelope; --json
on the implicit preview or guidance route selects the full pinned legacy payload
with BLOCK_INCOMPATIBLE_FLAGS/case none/semantic 2; human prints the conflict.
Do not run project assessment for this recognized intent conflict. Standalone
hidden check/choice controls keep their existing schemas/exits rather than being
converted to legacy planner output. Root help/version and completion preserve
their existing non-JSON conventions. Parser errors for unrecognized options or
missing values remain Click usage errors; no bootstrap on those paths.
Recognized semantic errors in machine requests emit one contract-shaped JSON
value, not console markup. If --plan-json is present it selects full schema,
including incompatible --cli/--project; otherwise --json selects the applicable
legacy planner or existing actual-outcome shape.
The existing too-new-schema early guard is the explicit exception: default
non-dry upgrade --json emits the full pinned legacy compatibility payload
(BLOCK_CLI_UPGRADE/project_too_new_for_cli/semantic 5) and process 5 before any
bootstrap. Preserve this even when an invalid target independently exists;
standalone invalid-target actual-outcome errors remain distinct. New --plan-json
always keeps its full-plan envelope, including too-new refusal/process 5; adapt
the guard's assessment, never let its old printer bypass the selected envelope.

## Target Policy and Independent Blockers

Use one extended `upgrade/runner.py` validation authority, not lexicographic
comparison and not a second renderer comparator.

| Current / target | target.valid / relation | Policy |
| --- | --- | --- |
| Known valid / lower PEP 440 | false / lower | Refuse downgrade |
| Known valid / equal | true / equal | May still need repair/migration; not no-work |
| Known valid / higher | true / higher | Valid target, only migrations shipped by this executable are selectable |
| Unknown current / valid target | true / unknown | Preserve existing legacy selection from 0.0.0; compatibility independently assessed |
| Any / malformed target | false / invalid | Explicit validation; no traceback or ALLOW |
| Malformed known current metadata | false / unknown | Corrupt metadata diagnostic; do not coerce to unknown/0.0.0 silently |
| Omitted target | Compare with installed CLI version | Same semantics in all project modes |

No new upper-version restriction is invented. A compatible target cannot
override too-new/corrupt schema. A stale schema's BLOCK_PROJECT_MIGRATION is
compatibility advice for an unsafe ordinary command; it does not prohibit
upgrade itself from performing the needed migrations.

For a standalone invalid target, the exact legacy fields are:

```json
{
  "schema_version": 1,
  "case": "none",
  "decision": "BLOCK_INCOMPATIBLE_FLAGS",
  "exit_code": 2,
  "pending_migrations": [],
  "rendered_human": "Refusing to downgrade project metadata from 3.2.7rc1 to 3.2.6"
}
```

This is a field projection, NOT a complete payload fixture: retain every
required cli/project/safety/install_method/upgrade_hint field from the actual
compatibility plan. Keep project.state=compatible for compatible metadata.
Malformed target message: `Invalid upgrade target version: <target>`.
Sanitize control characters and bound displayed untrusted values so the whole
rendered_human remains <=1024; normal version pairs above stay exact.

Decision precedence for legacy project planning:

1. Recognized mutually exclusive flags -> BLOCK_INCOMPATIBLE_FLAGS, case none,
   semantic/process 2. Do not perform project assessment to repair a flag error.
2. Corrupt metadata -> BLOCK_PROJECT_CORRUPT, project_metadata_corrupt, semantic 6.
3. Too-new schema -> BLOCK_CLI_UPGRADE, project_too_new_for_cli, semantic 5.
4. Stale/legacy schema -> BLOCK_PROJECT_MIGRATION, project_migration_needed,
   semantic 4, even if a target is independently invalid.
5. Otherwise invalid target -> BLOCK_INCOMPATIBLE_FLAGS, case none, semantic 2.
6. Otherwise preserve normal compatibility decision/case (ALLOW/ALLOW_WITH_NAG
   as applicable). Preview suppresses fresh nag/network side effects.

For rows 2-4 plus invalid target, rendered_human contains BOTH the existing
compatibility reason and the explicit invalid-target reason (compatibility
first, newline separator). This prevents independent blockers being concealed.
Do not compute migration selection for invalid target: pending_migrations=[].
Full-plan always exposes target and compatibility separately; no priority
translation may erase either reason.
Its nested compatibility is the original compatibility assessment, before the
legacy-only invalid-target/incomplete-assessment projection. Outer target,
decision and diagnostics express upgrade eligibility. Thus target-only refusal
may retain nested compatibility ALLOW while outer decision is blocked/code 2;
this is not the legacy top-level payload, which must carry the refusal above.

## Exit Codes and Assessment Failure

Payload exit_code above is SEMANTIC and never zeroed just because --dry-run is
present. Existing legacy project dry-run process normalizes to 0, except the
existing non-bypassable too-new-schema guard still exits 5 and flag errors 2.
Thus target-only JSON dry-run: payload 2, process 0; target-only human dry-run:
process 1, same explicit rejection. Non-dry --project --json uses semantic
code (2 for invalid target). Human/actual-upgrade invalid-target remains exit 1
and existing actual-outcome error fields; do not swap that route's schema.
Corrupt compatibility JSON dry-run retains normalized process 0 with payload 6;
human corrupt assessment fails nonzero. Tests must not infer ALLOW from exit 0.

Full-plan process: 0 when decision=ready, 2 invalid target/flags, 5 too-new,
6 corrupt project metadata, 1 incomplete owner assessment or required ownership/
source conflict. Stronger compatibility/flag failure wins process precedence.
Missing project in full-plan is blocked/code 1 with project_not_initialized
diagnostic, not corrupt metadata or an invocation flag error.
Full-plan includes process_exit_code explicitly, not nested legacy normalization.
Migration-only opacity means decision=incomplete, complete=false and code 1,
not permission to run its dependent effects.

Required config/manifest/source failures must not serialize empty ALLOW.
Full-plan uses blocked (hard failure) or incomplete (opaque migration phase)
with complete=false, typed diagnostics and known independent effects only.
Legacy has no assessment-completeness field: in those cases project preview
uses BLOCK_INCOMPATIBLE_FLAGS/case none/code 2 as a documented invocation
assessment refusal unless a stronger compatibility blocker already applies;
rendered_human states the incomplete owner/reason and full-plan command.
It does not mark project metadata corrupt for an unrelated manifest error.
Human prints the same refusal and exits 1. Unknown/custom preserved paths
alone are dispositions, not unreadable-state errors.

## Full-Plan Representation

`--plan-json` emits exactly upgrade-plan.schema.json. schema_version is the
report schema's own version, not a product release version. No persisted apply
endpoint or plan-file execution. Relative paths use roots[] for global/project/
worktree identity; phases and unique effect IDs are deterministic for identical
state after root normalization, excluding clock values/new timestamp hashes
from ID construction. Backup paths follow the state-derived collision rule in
owner-operations.md. after hashes describe exact invocation-prepared bytes;
new timestamp fields may differ across independent invocations only under that
contract's narrow comparison rule, including root `/created_at` solely for a
new `.kittify/skills-manifest.json` absent in both baselines. No global created_at
normalization, wire hash relaxation or per-invocation normalization is allowed.
Raw bytes/hashes and unchanged mtimes remain evidence. Include all persistent owner effects and
separately describe execution artifacts/commit policy.

complete=true iff all selected generated/supporting effects can be assessed;
decision=ready iff target and upgrade compatibility permit known automatic
work. Ready is not a promise of successful I/O or approval of consent-required
drift; dispositions describe such work and apply keeps its unresolved-drift exit.
blocked is an established refusal; incomplete is a cannot-finish-assessment
result. Both prohibit claiming no changes. Invalid target may be complete=true
because its refusal is fully known; do not assess or promise bootstrap effects
for a refused invocation.

Legacy machine preview includes a bounded summary/hint in rendered_human, not
complete repair paths or invented migration entries. Human preview lists full
effects from the same assessment; neither renderer performs ownership checks
or file discovery. Summary must say 'no migrations' separately from 'no changes'.

Preview does not fetch latest version, write cache or show-time/preferences.
For strict legacy preview cli.latest_source, use none/no latest when a cached
source is outside the pinned enum (e.g. simple_index); do not relabel it pypi.
Use existing distribution-aware install detection/hints and validate the whole
legacy payload; do not loosen the schema to accommodate unrelated output drift.

## Compatibility Protections

Keep migration selector/history, global custom paths, configured-agent scope,
worktree stamp/failure behavior, version pins and authored empty activations.
--no-worktrees does not mean no global assets: current root initialization and
project surfaces have global dependencies, which full plan must disclose.
Keep finalizer's single churn commit excluding independent mission repair;
preserve dirty-baseline/manual-review/autocommit policy and existing actual
outcome fields. No remote API/event format change.
