---
work_package_id: WP01
title: Independent preview oracle and baseline witnesses
dependencies: []
owned_files:
  - tests/upgrade/preview_support/**
  - tests/upgrade/test_preview_oracle.py
create_intent:
  - tests/upgrade/test_preview_oracle.py
authoritative_surface: tests/upgrade/
execution_mode: code_change
task_type: testing
agent_profile: python-pedro
role: implementer
agent: codex
requirement_refs: [FR-001, FR-003, FR-011, NFR-001, NFR-003, C-003]
tracker_refs: ['#3900', '#3901', '#3902', '#3903']
subtasks: [T001, T002, T003, T004, T005]
---

# WP01: Independent Preview Oracle

## Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, the compatibility alias for
`spk-doctrine-profile-load`, before parsing the rest of this prompt.

- Profile: `python-pedro`
- Role: `implementer`
- Agent/tool: `codex`

Run the resolver-backed profile and action context commands with SaaS sync off.
Apply initialization, directives, tactics and reviewer handoff boundaries.
If #3908 still yields empty structured governance, disclose that failure and
read binding charter/profile sources explicitly; do not invent activation.

## Objective

Deliver a trustworthy, reusable acceptance harness and preserved pre-fix
witnesses for the four issues. Harness approval does not mean the product
defects are fixed: final executable product acceptance belongs to WP13.

## Context

Read spec.md, plan.md, data-model.md and contracts/acceptance.md completely.
Read contracts/owner-operations.md for net-delta semantics without importing
its future production implementation into the independent oracle.
Read contracts/upgrade-cli.md for payload/process distinctions.
Read contracts/corpus-recovery.md for original audit/provenance evidence.

This package is independent and may begin alongside WP02 and WP11.
No source, shared conftest, runtime state or corpus edits belong here.
Use actual installed source entrypoint, not a replacement Typer app.
Keep the final full matrix separate from harness self-tests.

```sh
spec-kitty agent action implement WP01 --agent codex --mission upgrade-preview-mission-health-01M1V6E1
```

### Subtask T001: Establish Real Entry and Baseline Provenance

**Purpose:** Make every later observation attributable to the actual executable.

**Steps:**
1. Inspect existing tests/upgrade fixtures and source entrypoint resolution.
2. Identify overrides that conftest injects into subprocess environments.
3. Resolve the intended executable absolutely before changing child HOME.
4. Record source commit, distribution version, module path and interpreter.
5. Inspect the small support functions that will be reused; avoid a parallel
   fixture framework if existing pure preparation is suitable.
6. Keep measured execution separate from fixture construction.
7. Record original public commands and expected current failure signatures.

**Files:** tests/upgrade/preview_support/provenance.py (planned new support).
Keep source changes out of this package.

**Validation:**
- Deliberately point at a different editable checkout and prove mismatch fails.
- Empty stdout or startup failure cannot satisfy a purity assertion.
- Log executable identity alongside each retained command result.
- No global assets are touched by baseline preparation.

**Evidence:** Commands, resolved source location and baseline hash in external
WP evidence; portable references go to the mission review handoff.

### Subtask T002: Isolate Homes and Realistic Project Preparation

**Purpose:** Measure cold/stale/warm state without prewarming the measured home.

**Steps:**
1. Build disposable Git repositories with real supported metadata/config.
2. Use canonical setup before measurement to establish genuine owned manifests.
3. For cold cases, prepare project assets under a separate setup home.
4. Attach an untouched measured home only after fixture setup is complete.
5. Rebind HOME, USERPROFILE, XDG_CONFIG_HOME, XDG_CACHE_HOME, XDG_DATA_HOME,
   XDG_STATE_HOME, APPDATA, LOCALAPPDATA, SPEC_KITTY_HOME and temporary roots.
6. Clear inherited template/source/config overrides that can escape the fixture.
7. Set child SPEC_KITTY_ENABLE_SAAS_SYNC=0 last, after fixture customization.
8. Disable bytecode writes for source runs and optional Git observation locks.
9. Use closed stdin, bounded timeouts and complete captured stdout/stderr.
10. Keep all symlink destinations and user sentinels inside the sandbox.

**Files:** tests/upgrade/preview_support/fixtures.py and process.py, as needed.
Prefer a small explicit API rather than generic fixture plugins.

**Validation:**
- Cold home is absent before the measured command and was never initialized.
- A child reports only sandboxed configurable roots.
- Sibling fixture changes do not leak into another measured case.
- Non-CI and TTY cases remain possible; CI suppression is not the purity fix.
- Parse the entire machine stdout as one JSON value, not its last line.

### Subtask T003: Independent Filesystem Delta Oracle

**Purpose:** Detect persistent effects that logical surface counts miss.

**Steps:**
1. Walk each audited root with lstat semantics, without following symlinks.
2. Record relative path, node kind, regular-file SHA-256, literal link target,
   permission bits and mtime_ns; represent empty directories and absent roots.
3. Include ignored/untracked files, dangling links, manifests and cache paths.
4. Exclude access times only; document Git internal observations separately.
5. Normalize cross-copy roots, never user identities or substantive content.
6. Derive net create/update/delete/replace/retarget/chmod independently.
7. Treat final creation mode as part of create, not a second chmod effect.
8. Preserve raw snapshot evidence before any permitted field normalization.

**Files:** tests/upgrade/preview_support/snapshot.py;
tests/upgrade/test_preview_oracle.py.

**Validation:**
- Ignored-file byte edit is detected.
- Empty directory creation and deletion are detected.
- Dangling symlink deletion and retarget are detected separately.
- Permission-only change is detected on a capable platform.
- Same-byte rewrite with changed mtime is detected within one fixture.
- Each deliberately omitted observation makes its negative control fail.
- Production effect-building helpers are not imported by the oracle.

**Evidence:** Retain representative raw before/after snapshots and mutation
control results; a count-only assertion is insufficient.

### Subtask T004: Observe Transient Write Attempts

**Purpose:** Snapshot equality cannot prove absence of write-then-delete.

**Steps:**
1. Introduce a test-only wrapper that installs a recording/denying audit hook
   before importing and calling the real CLI main function.
2. Cover write-capable open, create, mkdir, unlink, rename, chmod, utime and
   link operations where the platform exposes them.
3. Keep ordinary unwrapped public subprocess snapshots as the primary witness.
4. Do not monkeypatch providers, installers or readiness functions to no-op.
5. Distinguish permitted setup writes from measured assessment operations.
6. Document unsupported syscall coverage rather than claiming total tracing.
7. Confine observer files outside measured roots or account for their writes.

**Files:** tests/upgrade/preview_support/write_observer.py;
observer controls in tests/upgrade/test_preview_oracle.py.

**Validation:**
- A deliberate write-then-delete attempt is caught despite equal snapshots.
- A read-only real invocation is not rejected merely for reading files.
- Hook installation occurs before CLI imports, with an explicit assertion.
- Observer failure/unsupported capability cannot become a silent pass.
- No live hosted network or credentials are needed by the observer.

**Evidence:** Exact covered events, rejected operation and platform limitations.
Do not represent this observer as a general OS network/filesystem firewall.

### Subtask T005: Preserve Original Public Red Witnesses

**Purpose:** Demonstrate the original bugs through pre-existing entrypoints.

**Steps:**
1. Run G0/G1 human and legacy JSON preview on unchanged source behavior.
2. Run a same-version P6 preview and equivalent real apply under isolated roots.
3. Demonstrate lower-target legacy JSON wrongly permits the downgrade.
4. Record the original full corpus audit and four blocker identities.
5. Use the source baseline or a disposable baseline checkout if other packages
   have already fixed the behavior; never revert their shared working changes.
6. Record failure reason, command, exit, output, source identity and snapshot.
7. Run the harness self-tests green after proving the negative controls.
8. Hand the reusable API and original red evidence to owner WPs and WP13.

**Files:** Existing support modules and oracle tests only. Raw logs stay external.
Do not add a fake product implementation or xfail the final acceptance suite.

**Validation:**
- Red is the reported defect, not missing --plan-json or an import failure.
- P6 has real nonempty supporting writes, not a vacuous zero-equals-zero check.
- A normalized process exit 0 is not interpreted as downgrade approval.
- Product red evidence stays explicit even while harness tests pass.
- All support tests and affected existing fixture tests execute successfully.

## Definition of Done

- T001-T005 have canonical mark-status done records and linked evidence.
- Harness self-tests pass, including all negative controls above.
- Original four issues have attributable witnessed failures, not new-API errors.
- No product-fix or final-gate approval is claimed by this package.
- Run direct warm-venv pytest on the owned tests and relevant fixture consumers.
- Run changed-file Ruff and mypy; record actual outcomes, not intended commands.
- No shared conftest, production source or user assets changed.
- Commit exact owned changes and provide their hashes for independent review.

## Risks

- Fixture bootstrap can hide cold-home mutation: separate setup and measurement.
- Ignored paths or symlinks can hide side effects: lstat plus omission controls.
- Test fixtures may reset SaaS flags: bind child environment after their inputs.
- A weak wrapper can mask defects: retain unwrapped public subprocess evidence.
- Baseline evolution can erase red: retain the immutable source revision.

## Reviewer Guidance

Reviewer must be distinct from implementer and load its own profile.
Try to falsify the oracle with omitted ignored paths, dangling links and chmod.
Verify real executable provenance and cold-home preconditions independently.
Inspect whether any mocked boundary suppresses the operation under test.
Reject empty output, startup failure, missing imports or skip as bug evidence.
Approve only this infrastructure contract; product acceptance remains pending.
