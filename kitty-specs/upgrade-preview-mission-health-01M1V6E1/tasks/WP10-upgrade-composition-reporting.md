---
work_package_id: WP10
title: Upgrade composition and compatible CLI reporting
dependencies:
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-010
- NFR-002
- C-001
- C-002
planning_base_branch: codex/upgrade-preview-mission-health
merge_target_branch: codex/upgrade-preview-mission-health
branch_strategy: Planning artifacts for this mission were generated on codex/upgrade-preview-mission-health. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/upgrade-preview-mission-health unless the human explicitly redirects the landing branch.
subtasks:
- T047
- T048
- T049
- T050
- T051
- T052
- T053
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- src/specify_cli/upgrade/assessment.py
- tests/upgrade/test_upgrade_assessment.py
- tests/upgrade/test_upgrade_cli_contract.py
execution_mode: code_change
owned_files:
- src/specify_cli/__init__.py
- src/specify_cli/cli/helpers.py
- src/specify_cli/cli/commands/upgrade.py
- src/specify_cli/upgrade/assessment.py
- src/specify_cli/upgrade/runner.py
- src/specify_cli/upgrade/finalize.py
- src/specify_cli/upgrade/metadata.py
- src/specify_cli/upgrade/outcome.py
- src/specify_cli/upgrade/compat.py
- src/specify_cli/upgrade/detector.py
- src/specify_cli/upgrade/registry.py
- src/specify_cli/upgrade/autocommit.py
- src/specify_cli/compat/**
- tests/specify_cli/compat/**
- tests/upgrade/test_upgrade_assessment.py
- tests/upgrade/test_upgrade_cli_contract.py
- tests/upgrade/test_finalizer.py
- tests/upgrade/test_upgrade_integration.py
- tests/upgrade/test_upgrade_idempotency.py
- tests/upgrade/test_teamspace_consent_scope.py
- docs/guides/how-to/installation/upgrade-project.md
- docs/guides/how-to/installation/upgrade-cli.md
- docs/guides/how-to/installation/tool-surface-upgrade-and-repair.md
- docs/api/upgrade-lifecycle.md
role: implementer
tags: []
tracker_refs: []
---

# WP10: Upgrade Composition and Compatible CLI Reporting

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

Legacy alias maps to canonical `spk-doctrine-profile-load`.
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent profile show python-pedro
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty charter context --action implement --json
```
Apply initialization, boundaries, directives/tactics and independent handoff.
Read AGENTS.md and .kittify/charter/charter.md before implementation.
Disclose #3908 if structured governance remains empty despite success; use
explicit charter/resolved profile sources, not invented successful activation.
Warm direct binaries only; no uv resync, production dependencies or model override.

---

## Objective

Integrate owner-produced upgrade assessment with pure process-entry intent,
consistent target validation and strict legacy/full-plan reporting.
Suppress preview startup writes and restore validated application preparation
in the same change, preserving finalizer/worktree/consent behavior.

## Context

Authority: approved spec.md, plan.md, research.md, data-model.md, wps.yaml and
contracts/* in this mission. Exact T047-T053 are in external task-authoring-brief.md.
Read upgrade-cli.md completely: its route precedence is normative, not examples
from which to infer a simpler replacement policy.
owner-operations.md fixes exact effects/clock/rechecks; acceptance.md fixes public
G/B/P evidence; corpus-recovery.md keeps history repair separately consented.

WP03 delivers pure intent/global APIs without altering public root startup.
WP04-WP08 deliver concrete owner assessment/apply; WP09 charter prepared bytes.
WP02/WP01 core/harness are transitively delivered through these dependencies.
Do not start integration against credit-interrupted, unreviewed handoffs.
No edits to upstream protocol, provider, installer, charter or harness files.
Route required corrections to their single owner.

WP10 exclusively owns root __init__.py, cli/helpers.py and cli/commands/upgrade.py.
Use WP03's parse-only intent API, not another raw-argv policy implementation.
No root-only suppression commit that breaks cold-home valid apply is acceptable.
Only this package coordinates startup gating with the replacement apply calls.
WP13 owns full aggregated acceptance, installed wheel and assessment AST gate.
WP11/WP12 own corpus recovery and archive-policy evidence, not this package.

Use existing VersionDetector, MigrationRegistry, validate_upgrade_target and
finalize_upgrade; no new migration list, generic transaction or replay endpoint.
Authoritative surface is the explicit production prefix, not an empty common
source/test prefix or a codebase-wide overlap exemption.
New literal files are exactly the three listed in create_intent.

After parent dispatch:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent action implement WP10 --agent codex --mission upgrade-preview-mission-health-01M1V6E1
```

### Subtask T047: Characterize Existing Routes and Commit Real Red

**Purpose:** Preserve compatibility while exposing actual root/JSON defects.

**Steps:**
1. Read root main_callback, _run_startup_project_gates and machine-mode logging.
2. Read upgrade.py hidden dispatch, guidance, too-new guard, planner and apply routes.
3. Trace runner validation and injected finalizer steps, including churn commits.
4. Read compat planner/cache/provider semantics and existing consumer schema.
5. Record real cold/stale public dry-run mutation and same-version omission
   witnesses using WP01's independent observer, not a mocked root.
6. Record downgrade legacy JSON payload versus human rejection at current
   3.2.7rc1 and target 3.2.6; process zero is not an ALLOW assertion.
7. Characterize default actual --json too-new output as legacy planner/process 5.
8. Characterize standalone hidden operations versus effective preview conflicts.
9. Commit relevant failing public-entrypoint regressions before functional fixes.
10. Tidy only touched owned seams in a distinct behavior-preserving change.

**Files:** Owned root/CLI/upgrade/compat modules and tests/upgrade tests.
The ownership glob is permission scope, not an instruction to rewrite all compat.

**Validation:** Red comes from existing executable behavior and intended assertion.
Unsupported new --plan-json is not evidence of the original bug.
Keep stdout/stderr, fixture/source provenance and full snapshot differences.
Do not hide known failures with xfail or weaken existing actual-output assertions.

### Subtask T048: Share Target Validation and Non-Persisting Compatibility

**Purpose:** Independent target/schema axes without preview cache/network writes.

**Steps:**
1. Extend upgrade/runner.py's validator for malformed input; reuse packaging PEP 440.
2. Preserve lower rejection, equal repair eligibility and valid higher targets.
   Do not invent an installed-version upper bound or promise future migrations.
3. Unknown current uses existing migration-from-0.0.0 behavior; malformed known
   metadata is diagnosed, never silently coerced to unknown.
4. Omitted target resolves to installed CLI version consistently.
5. Use the existing compatibility planner with a no-network/non-persisting view.
6. Suppress cache mkdir, locks, latest fetch, preferences and shown-at updates.
   CI/--no-nag/sync=0 alone do not enforce this boundary.
7. Keep schema blockers independent of target result; invalid target selects no
   migrations, even when compatibility reports migration needed.
8. Preserve distribution-aware hints and truthful project state.
9. For strict legacy latest_source, cached unsupported values such as simple_index
   become no latest/none, never falsely relabeled pypi.
10. Keep semantic result separate from process exit normalization.

**Files:** runner.py, owned compat modules and tests/specify_cli/compat/**.
Use existing cache/provider seams; no new persistent plan store.

**Validation:** Lower/equal/higher/prerelease/malformed/omitted/unknown cells.
Pair lower and higher with stale, corrupt and too-new schema blockers.
No network/cache writes under public preview with available cacheable data.
Errors are bounded and explicit, not tracebacks or false metadata corruption.

### Subtask T049: Compose Owner Phases and Charter Preparation

**Purpose:** One complete assessment inventory with honest migration opacity.

**Steps:**
1. Create upgrade/assessment.py consuming existing registry and owner assessments.
2. Compose global preparation, migrations/metadata, provisioning, manifest repair
   and surface effects in the approved phase order.
3. Reuse version detection/selection; migration count is not repair completeness.
4. Consume WP09 lower-layer prepared target/bytes/projected activation values.
5. Wrap charter results in PhysicalEffect upstairs; never import tool_surface
   values into charter or duplicate YAML/pointer/seed policy in upgrade.
6. Preserve missing-key versus explicit empty activation and comments/unowned
   sections; recheck both pointer/config and resolved target observations.
7. Supply concrete projected config/manifests/package selections to dependent
   owners; no virtual filesystem or simulated writes.
8. Deduplicate shared roots while retaining all logical owners.
9. Include all persistent manifests, pruning, provisioning, directories and
   global effects; report transient apply artifacts/commit policy separately.
10. Opaque migration effects leave real migration IDs with incomplete dependent
    phases. Do not claim complete no-change when assessment cannot finish.
11. Existing migration apply may proceed under existing policy, followed by
    fresh post-migration owner assessment before repair.
12. Same-version ordinary fixtures must be complete; no opacity escape there.

**Files:** New assessment.py and existing owned metadata/outcome/registry helpers.
Provider/charter fixes are upstream-owned, never silently patched here.

**Validation:** Nonempty same-version repair plan/apply effects agree.
Legacy and pointer-based charter missing-key fixtures prepare exact bytes.
Empty activation remains empty; dangling pointer refuses without fallback.
Corrupt manifest/config/source has typed diagnostics, not empty success.
Prepared clocks/backups remain owner values; composer never resamples or renames.

### Subtask T050: Freeze Human, Legacy and Full-Plan Routes

**Purpose:** Implement exact approved flag/schema precedence, not additive JSON drift.

**Steps:**
1. Add --plan-json as explicit preview-only output; accept redundant --json/--dry-run.
2. Keep --project --json planner-only even without --dry-run.
3. Keep default actual --json outcome shape EXCEPT too-new schema:
   full pinned legacy BLOCK_CLI_UPGRADE payload, semantic/process 5, no bootstrap.
4. New --plan-json retains full-plan envelope even on that early too-new refusal.
5. Preserve --cli guidance and default no-project guidance; full-plan missing
   project is blocked/code 1 with project_not_initialized, not shape fallback.
6. Resolve hidden --agent-choice/check/latest by effective intent. Reject with
   explicit preview, implicit --project --json or guidance before hidden writes.
7. Standalone hidden operations retain their own outputs/preference semantics,
   including outside projects; do not misclassify them as default guidance.
8. Conflicts exit 2; full request gets full blocked envelope, implicit
   preview/guidance --json gets pinned legacy flags/case-none/code-2 payload.
9. Preserve Click parse-error/help/version conventions without bootstrap.
10. Human renders full effects; legacy rendered_human gets a bounded summary and
    full-plan hint, never extra keys, fabricated migrations or an ID-only plan.

**Exact target-only legacy projection:**
- decision BLOCK_INCOMPATIBLE_FLAGS; case none; semantic exit_code 2.
- pending_migrations []; truthful compatible project.state remains compatible.
- rendered_human: Refusing to downgrade project metadata from 3.2.7rc1 to 3.2.6.
- Malformed target: Invalid upgrade target version: <target>, safely bounded.
- Retain every required legacy field; rendered_human max 1024.
- Stronger flags/corrupt/too-new/stale precedence follows upgrade-cli.md.
- Independent blocker and invalid-target reasons both remain visible.

**Exit distinctions:**
- Target-only legacy dry-run: semantic 2, process 0; human process 1.
- Non-dry --project --json invalid target: process 2.
- Actual-outcome standalone invalid target: existing error shape/process 1.
- Legacy too-new dry-run and default actual JSON: process 5.
- Full ready 0; invalid/flags 2; too-new 5; corrupt metadata 6;
  missing project/required owner failure/incompleteness 1, per contract.
- Nested full-plan compatibility is original assessment, not legacy projection;
  outer target/decision/diagnostics must carry the upgrade refusal.

**Files:** upgrade.py, assessment.py and owned compat/render helpers.
Validate whole stdout against unchanged pinned legacy schema and new full schema.
Resolve schema references locally, never via network. Full report is not an apply token.

### Subtask T051: Wire Root Suppression and Validated Apply Together

**Purpose:** Close process-entry mutation without breaking ordinary upgrades.

**Steps:**
1. Consume WP03 parse-only intent from real Click option definitions.
2. Wire root __init__.py and cli/helpers.py with upgrade.py in the same delivery.
3. Skip bootstrap/nag/preferences for effective preview/guidance and invalid flags.
4. Include --plan-json in early machine logging detection; stdout stays one JSON value.
5. Validate target/schema before executing global preparation for apply.
6. Restore legitimate cold-home global bootstrap through the delivered owner API;
   do not merely remove root ensures or leave duplicate hidden bootstrap paths.
7. Preserve help/version/completion/next and ordinary non-upgrade startup.
8. Keep actual finalizer order: provision -> surface repair -> generated churn
   commit -> independently consented mission-state repair.
9. Preserve dirty baseline/manual review, worktree success/failure and outcome
   derived exits; finalizer never imports CLI.
10. --no-worktrees excludes discovery/stamping/repair of worktrees, not globals.
11. --yes/--force never authorize preview writes, drift overwrite or mission repair.
12. Recheck owner batches immediately before apply; mismatch requires reassessment.
    Preserve truthful partial outcomes, no cross-owner rollback promise.

**Files:** __init__.py, cli/helpers.py, upgrade.py, finalize.py and owned helpers.
No edits to WP03 intent/runtime files; escalate interface gaps to their owner.

**Validation:** Cold-home valid apply performs necessary preparation successfully.
Cold/stale previews are healthy and write-free, not merely failing before writes.
Explicit mission-repair positive consent remains reachable; --yes-only is negative.
Same-version second apply changes no bytes, modes, links or mtimes.
No intermediate acceptance based on root suppression alone.

### Subtask T052: Execute Public Target/Flag/Worktree Regression Cells

**Purpose:** Green owned integration evidence before full WP13 aggregation.

**Steps:**
1. Implement focused public subprocess tests in test_upgrade_cli_contract.py.
2. From current 3.2.7rc1, cover 3.2.6, 3.2.7rc0, equal, 3.2.7rc2, 3.2.7, 3.2.8;
   human/legacy with and without --project, plus full-plan cells.
3. Add malformed empty/not-a-version/control-character inputs, omitted target,
   unknown current and malformed known metadata.
4. Pair lower/higher with stale/too-new/corrupt schema; assert both reasons.
5. Add --project --json plus each hidden choice/check/latest on cold home;
   explicit guidance conflicts and standalone hidden-operation positive controls.
6. Add default actual JSON too-new legacy/code-5 and full-plan too-new/code-5.
7. Exercise redundant/reordered flags, target=value, --cli conflicts and parser errors.
8. Test nonempty owner effects, charter pointer/legacy preparation and full stdout.
9. Test worktree included/excluded, dirty-baseline commit policy, manual-review
   outcomes and separate consent using the existing owned tests.
10. Use WP01 independent snapshot/transient controls; never fake root or installers.
11. Run owned tests, affected upgrade/compat subsystems, changed-module Ruff/mypy
    and calibrated repository fast tests. Record exact commands/counts/provenance.
12. Hand WP13 evidence and executable cells; do not edit its harness/gate files.

**Focused command after parent-approved isolation prerequisites:**
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/pytest tests/upgrade/test_upgrade_assessment.py tests/upgrade/test_upgrade_cli_contract.py tests/upgrade/test_finalizer.py tests/upgrade/test_upgrade_integration.py tests/upgrade/test_upgrade_idempotency.py tests/upgrade/test_teamspace_consent_scope.py -q
```

**Environment:** Disposable homes/XDG/runtime/temp/tool roots; child sync=0 last.
Existing conftest may override shell flag; approved policy is required, not
wholesale conftest disabling. Flag=1 alone is not proof of live SaaS activity.
No real home writes, live credentials, hosted endpoints or production network.
No xfailed product bugs, uv resync, production dependencies or make test-full.
Full CORE contract/architecture/E2E/issue-matrix gates remain parent-owned.

### Subtask T053: Update Shipped Upgrade Documentation

**Purpose:** Document delivered CLI behavior at its existing public sources.

**Steps:**
1. Update docs/guides/how-to/installation/upgrade-project.md for pure preview,
   same-version work, full-plan invocation and exact apply distinction.
2. Update upgrade-cli.md in that directory for guidance/hidden precedence.
3. Update tool-surface-upgrade-and-repair.md for owner effects, preserved drift,
   supporting manifests and global/worktree scope.
4. Update docs/api/upgrade-lifecycle.md with unchanged finalizer/consent ordering.
5. Explain legacy semantic versus process exits and actual too-new exception.
6. Include explicit --plan-json schema/flag examples without promising replay.
7. State incomplete assessment honestly; do not advertise no-change from no migrations.
8. Cite canonical contracts; do not edit mission spec/plan or consumer schemas.
9. Verify examples against delivered public subprocess output from T052.
10. Keep compatibility notes within owned docs; no release/version bump.

**Files:** Exactly the four manifest-owned documentation paths.
Prefer focused sections/tables over rewriting unrelated installation guidance.

**Validation:** Commands/flags/schema examples agree with full captured output.
No documentation claims executed corpus repair, approved final gates or implicit consent.
Record reference/link checks and any separately owned doc followup.

## Definition of Done

- T047-T053 each has attributable evidence and canonical completion records.
- Root suppression and valid cold-home apply preparation both pass together.
- Strict legacy schema remains unchanged; full plan is explicit preview-only.
- Target validity and schema compatibility remain independent in every route.
- All ordinary same-version effects, including charter/global support, are visible.
- Corrupt/incomplete assessments cannot become empty ALLOW or no-change.
- Rechecks, partial outcomes, worktrees, custom assets and separate consent survive.
- Owned/subsystem/lint/type results and tracked baseline dispositions recorded.
- Docs match real output; independent review approves actual implementation.
- No unrun full-gate/wheel/corpus result is claimed by this package.

After each subtask actually passes, record supported event-sourced status:
```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty agent tasks mark-status T047 --status done --mission upgrade-preview-mission-health-01M1V6E1
```
Repeat for T048-T053 only with evidence. No fake tasks.md/status or hand-edited
review outcomes. Authoring this file does not execute implementation or runtime.

## Risks

- Early guard prints wrong envelope: preserve old actual exception and full precedence.
- Root purity breaks apply: both behaviors must land and pass in this package.
- Optional hidden flags mutate effective preview: classify intent before dispatch.
- Composer duplicates owners: consume delivered preparation, never derive paths anew.
- Opaque migrations look empty: explicit incompleteness, reassess after actual migration.
- Clock drift: never rerender owner bytes or rename prepared backups upstairs.
- Broad scope: seven concrete subtasks; avoid unrelated compat/CLI cleanup.
- Interrupted dependency workers: logs/uncommitted edits are not approved handoffs.

## Reviewer Guidance

Start with real public cold-home and actual-apply positive witnesses.
Inspect root callback, hidden dispatch and too-new printer before serializers.
Require complete pinned JSON validation, exact semantic/process distinctions.
Check source-free registry/charter consumption and no upward import.
Inspect finalizer outcome/consent/worktree regression evidence.
Reject mocked-root tests, process-zero ALLOW inference and skip-waived defects.
Ensure no shared provider/harness edits or manufactured runtime state.
Keep WP10 green distinct from parent's full final-gate approval.

