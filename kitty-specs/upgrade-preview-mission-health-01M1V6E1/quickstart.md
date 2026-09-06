# Validation Runbook

Audience: implementing and reviewing engineers. Updated: 2026-09-06.
These steps are planned, not executed by the plan author. Run mutations only
in the assigned isolated implementation/test checkout with sandboxed homes.

## Preparation

Read spec.md, plan.md and contracts/*.md. Parent owns setup-plan/phase changes,
task generation, commits and review dispatch. Local consolidation target:
codex/upgrade-preview-mission-health; publication PR: main.
Do not run setup-plan merely to find paths; use the explicit root mission paths
supplied by parent. No coord edits or runtime/status/meta changes by plan author.

Use the already warm .venv binaries and SPEC_KITTY_ENABLE_SAAS_SYNC=0.
Do not resync, install a global CLI, or alter host HOME. Test subprocesses bind
their own HOME/XDG/runtime/temp/tool roots per contracts/acceptance.md.

## Red-First

Before each production change, commit a relevant failing public-entry-point
acceptance test through the parent's workflow. Core original witnesses:

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty upgrade --dry-run --verbose --no-worktrees
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty upgrade --dry-run --json --target 3.2.6 --no-worktrees
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty doctor mission-state --audit --fail-on teamspace-blocker --json
```

These bare examples require the isolated harness environment; do not run them
against host/global assets. Pin target-test metadata 3.2.7rc1 and known schema,
not whatever version happens to be installed. Capture snapshots BEFORE the
first CLI call. A new --plan-json unsupported-option failure is not bug evidence.

## Green and Contract Checks

After implementation, run the acceptance matrix using its new owned file:

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/pytest tests/upgrade/test_upgrade_preview_acceptance.py -q
```

The harness must execute real preview and apply commands on equivalent
independent fixtures, then compare actual physical effects and second-run
idempotence. New full-plan example:

```sh
env SPEC_KITTY_ENABLE_SAAS_SYNC=0 .venv/bin/spec-kitty upgrade --plan-json --no-worktrees
```

Validate complete stdout with json.loads, not last-line extraction.
Validate legacy payloads against the unchanged pinned schema/hash in
contracts/upgrade-cli.md; use installed jsonschema, no missing-library fallback
that ignores extra fields. Validate full plan against upgrade-plan.schema.json.
Register the pinned legacy schema locally under its existing canonical $id,
including references used by the full schema. Schema resolution must never
fetch the network. Check cross-field invariants (root references, unique IDs/
paths, action states, ownership and completeness) beyond JSON structural checks.

Run owner module tests and full affected subsystem directories, plus make
test-fast under the same isolated worker HOME policy. Use direct
.venv/bin/ruff and .venv/bin/mypy for changed modules. Run new assessment-boundary
and existing layer/import/dead-code gates; run the full architectural suite for
the shared test/gate change under repository policy. Record commands/counts;
no make test-full or unrelated whole-repo test sweep in this handoff.

## Wheel and Mutation Witness

Build the project's ordinary wheel using existing build tooling in an isolated
workspace; install that artifact into a disposable test environment without
changing production dependencies or host tools. Record wheel SHA, executable,
distribution/module path and version. Clear source/template overrides and
PYTHONPATH; run from disposable projects outside the source tree.
Replay the minimal installed matrix in contracts/acceptance.md.

Run independent oracle controls and disposable source mutations: restored
bootstrap call, omitted manifest effect, false downgrade ALLOW, missing ignored
file observation and overwritten custom sentinel must each fail. Include
transient-write interception separately from persistent snapshots.

Re-review cells from Paula: exercise P7 for legacy and pointer-based charter
provisioning, preserving comments/unrelated sections and explicit empty lists;
dangling pointers fail honestly. Exercise T1-assess/T2-apply exact bytes and
independent-time public backup path equality, occupied candidates, racing
collisions and second-apply no churn. Keep all old backup bytes and raw manifest
evidence; only the owner-contract's declared new timestamp fields may normalize
across separate runs, never within one assessment/apply invocation.
Include fresh managed-skills manifest `/created_at` only at
`.kittify/skills-manifest.json` absent in both baselines, per owner contract.
Keep raw bytes/hashes and unchanged mtimes; negative controls must reject
changed existing manifest creation time and changed mission-meta created_at.

## Corpus and Close-Out

Follow contracts/corpus-recovery.md in IC-08's workspace: exact 31-file restore,
R2-T1 byte-preserving move/reference mapping, two canonical snapshot replays,
event/verdict comparison and second materialization. Run the full gated audit
and record zero blockers with no lost history.

Measure source preview cold/warm p50/p95 against the charter <2s typical CLI
budget. Distinguish fixture/wheel setup from measured process execution and
record existing baseline cost. Report all failed/unsupported checks honestly.

Archive-gate prerequisite: retain parent's observed first red and await the
full diagnostic. Follow plan.md's IC-10 classification and positive preservation
checks, including destructive mutation controls and independent review. Do not
interpret #3911's parent-reported 1 failed/2 passed reproduction as permission to
weaken preservation. Do not
skip the M1 gate or add a whole-path exemption to make authorized lifecycle
appends/corpus repair pass. Full architectural rerun remains required.

Parent attaches per-issue red/green/effect/hash/review evidence, advances phases
and obtains independent post-plan/post-tasks/implementation reviews. Runtime
composition placeholder (#3909) and degraded governance (#3908) use explicit
canonical prompt/charter reads, never fabricated phase-success reports. Exact
CLI friction remains in the external ledger; no broad governance repair here.

## Parent Final Gate Handoff

Use contracts/acceptance.md's Parent-Owned Final Gate Table as the authoritative
execution checklist: full CORE tests/contract/, full tests/architectural/, full
current E2E scenarios/ with all five named floor cases, then terminal issue
matrix. Neither runtime review PASS nor fast/targeted tests substitutes for it.
Resolve effective sync-fixture policy first; shell sync=0 alone is insufficient,
and fixture flag=1 is not proof of live SaaS traffic. Parent-authorized package
installs remain disposable and recorded, not described as network-free runs.

Known baseline is 2 failed/3 passed/0 skipped. CORE #3912 planning ancestry and
E2E spec-kitty/EXPERIMENTAL-spec-kitty-end-to-end-testing#411 fake-events diary
collection failure remain tracked blockers, not environmental skips or intended
drift detection. Require actual inner envelope assertion plus unmutated green
control. Record retired SaaS scenario by deletion/ADR provenance, not PASS.
Parent's #3458 recurrence followup Op 01M1V8WKCPN7KZT629FP57NA2X reports 33 passed
and clean Ruff/mypy, independently APPROVED. Parent reports guard/golden
integration at c3657a86a; integrated tests and original next remain running.
No full gate is approved; these are parent results, not author reruns.

For bounded Renata re-review, inspect the effective hidden preview/guidance
precedence and default actual --json too-new legacy/code-5 exception in
contracts/upgrade-cli.md, plus their cold-home public cells in acceptance.md.
No implementation, new harness lane or baseline rerun belongs to this document
clarification point-cut; parent schedules execution and independent reviews.
