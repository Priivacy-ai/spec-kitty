---
work_package_id: WP18
title: Review-cycle merge driver for the two-sided tasks/ hazard
dependencies:
- WP04
requirement_refs:
- NFR-002
- NFR-003
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T16:10:00Z'
subtasks:
- T077
- T078
- T079
- T080
agent: claude
history:
- at: '2026-08-03T16:10:00Z'
  actor: operator
  action: WP authored mid-mission to discharge WP04's T017 ownership deadlock (operator adjudication)
agent_profile: architect-alphonso
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- src/specify_cli/upgrade/migrations/m_3_2_7_review_cycle_merge_driver.py
- tests/specify_cli/cli/commands/test_review_cycle_merge_driver.py
execution_mode: code_change
model: ''
owned_files:
- .gitattributes
- src/specify_cli/cli/commands/merge_driver.py
- src/specify_cli/cli/commands/__init__.py
- src/specify_cli/cli/commands/init.py
- src/specify_cli/lanes/merge.py
- src/specify_cli/upgrade/migrations/m_3_2_7_review_cycle_merge_driver.py
- tests/specify_cli/cli/commands/test_review_cycle_merge_driver.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP18 - Review-cycle merge driver for the two-sided `tasks/` hazard

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load architect-alphonso
```

## Why this work package exists

**This WP was authored mid-mission, by operator adjudication, to discharge an
ownership deadlock WP04 could not resolve.** It is not part of the original
17-WP slicing and its provenance matters, so it is recorded here rather than
implied.

WP04 (T017) was required to resolve the two-sided `tasks/` reconciliation-class
hazard that ADR 2026-08-03-1 names as a required deliverable. Its Reviewer
Guidance permitted exactly two discharges: a merge-driver diff, **or** a
re-justification *backed by a passing test demonstrating the clobber cannot
occur*. WP04 established that:

- Option (b) is **dishonest**. The create-window split makes the clobber
  genuinely reachable — the coord worktree materialises lazily at the commit
  boundary, so a coord mission's *first* review cycle lands PRIMARY and later
  ones COORD, with `next_cycle_number` globbing one surface. No honest test can
  demonstrate that a reachable clobber cannot occur.
- Option (a) requires files outside WP04's `owned_files`.

So neither permitted discharge was achievable within WP04's slicing boundary.
WP04 landed the ruling, an updated `_NON_DIVERGENT_COORD_RESIDUE_DIRS` comment,
and a fail-closed tripwire test, then escalated. The operator ruled: **land the
driver in a new work package that owns the registration surface.** That is this
WP. WP04's T017 is discharged by deferral to it.

## The hazard, precisely

`tasks` is registered in `_NON_DIVERGENT_COORD_RESIDUE_DIRS`
(`tests/architectural/test_merge_reconciliation_class_guard.py`) on the
justification that it is *"authored once and never independently edited on the
target side"*. ADR 2026-08-03-1's Consequences section states that the partition
flip **falsifies** that justification: WP task files live on the target side
while review cycles are authored on the mission branch, so `tasks/` becomes
genuinely two-sided.

The concrete failure: during the migration window a coord mission carrying
cycles 1–3 on PRIMARY writes cycle 1 to COORD (because `next_cycle_number`
globs a single surface), and `_phase_mission_to_target`'s
`git merge --squash -X theirs` overwrites the target's cycle 1. **That is the
#2804 clobber shape, in a directory the reconciliation guard has pre-classified
as safe** — which is why prose alone was refused as a discharge.

**Union-merge is NOT a valid driver here.** The existing
`spec-kitty-event-log` driver unions append-only JSONL lines, which is correct
for an event log. A review-cycle artifact is not append-only: two *distinct
verdicts* colliding under one filename must never be byte-interleaved into a
single Markdown document. That would fabricate a verdict no reviewer wrote —
precisely the failure FR-001 and US2 exist to prevent. The driver must refuse or
disambiguate, never blend.

## Context & Constraints

Read in full before starting:

- `docs/adr/3.x/2026-08-03-1-review-cycle-artifacts-are-coord-partition.md` —
  the Consequences section's `tasks/`-becomes-two-sided entry, and the
  create-window split entry.
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/tasks/WP04-review-cycle-kind-and-plumbing.md`
  — T017 in full, plus its Risks entry explaining why the existing guard test
  will **not** red on a skipped T017.
- `tests/architectural/census/verdict_seam_IC04.yaml` — WP04's census fragment,
  which records the T017 ruling and its blocking rationale.
- **`src/specify_cli/upgrade/migrations/m_3_2_6_decisions_event_log_merge_driver.py`
  — the direct precedent and your template.** It registered a merge driver for
  `decisions.events.jsonl` across exactly the surface this WP must touch. Follow
  its shape rather than improvising; per the charter's canonical-sources rule,
  deviating from an existing precedent needs a stated reason.
- `src/specify_cli/upgrade/migrations/m_3_1_1_event_log_merge_driver.py` — the
  earlier sibling, for the same reason.
- `src/specify_cli/cli/commands/merge_driver.py` — the five existing driver
  implementations. Read `merge_driver_event_log` and
  `merge_driver_issue_matrix` in full: the former is the union shape you must
  **not** copy, the latter is a row-aware shape closer to what is needed.
- `.gitattributes` — the five existing `merge=spec-kitty-*` rules and the
  `linguist-generated` entries.
- `src/specify_cli/lanes/merge.py` and `src/specify_cli/cli/commands/init.py` —
  the two registration call sites a fresh clone and a lane merge go through.

**Constraints (binding)**:
- **Never blend two verdicts.** The driver must not produce a document
  containing content from two distinct verdict records. Refuse (non-zero exit,
  leaving conflict markers or an explicit diagnostic) or disambiguate by
  renumbering — never interleave.
- **Registration must be complete, or the driver is inert.** A driver declared
  in `.gitattributes` but absent from `.git/config` silently falls back to
  git's default merge. All registration surfaces must be covered: the
  `.gitattributes` rule, the hidden `app.command(...)` wiring, the fresh-init
  path, the lane-merge path, and an upgrade migration for existing clones.
- **`src/specify_cli/cli/commands/__init__.py` is in `owned_files`, but check
  the version-bump rule before editing.** `CLAUDE.md` requires a `pyproject.toml`
  version bump plus a `CHANGELOG.md` entry for `__init__.py` changes. Neither
  file is in this WP's `owned_files`. If your change to that file triggers the
  rule, **stop and escalate** rather than editing an unowned file or skipping a
  binding requirement — the same deadlock class that created this WP.
- **Do not weaken the WP04 tripwire.** `test_review_cycle_tasks_hazard_is_ruled_and_tracked`
  is designed to red when a driver appears, forcing this WP to be visible. That
  test is in WP04's `owned_files`, not yours. When it reds because you landed
  the driver, **report it as a required cross-WP update** rather than editing
  it — it is the mechanism working as intended.

## Subtask T077 — Implement the review-cycle merge driver

- **Purpose**: A driver that resolves a `review-cycle-*.md` collision without
  fabricating a verdict.
- **Steps**:
  1. Add `merge_driver_review_cycle` to `src/specify_cli/cli/commands/merge_driver.py`,
     following the existing drivers' `%O %A %B` signature and exit-code
     contract.
  2. Decide and document the collision semantics. Both sides holding the *same*
     cycle number with *different* content is the load-bearing case. Options to
     weigh explicitly in the docstring: refuse fail-closed; or renumber the
     incoming record to the next free cycle number so neither verdict is lost.
     Per FR-006 ("verdict numbering never overwrites") and C-002(b) ("a failed
     durable write leaves no orphan"), losing a verdict is the worst outcome —
     but so is inventing one.
  3. Identical content on both sides is a trivial fast-path and must not be
     reported as a conflict.
- **Files**: `src/specify_cli/cli/commands/merge_driver.py`
- **Validation checklist**:
  - [ ] Two distinct verdicts under one filename never produce a blended document.
  - [ ] Identical-content collision resolves cleanly.
  - [ ] Exit-code contract matches the sibling drivers.

## Subtask T078 — Register it across every surface

- **Purpose**: An unregistered driver is inert and fails silently to git's
  default merge.
- **Steps**:
  1. Add the `.gitattributes` rule for `kitty-specs/**/tasks/*/review-cycle-*.md`.
     **Filename-anchored, not directory-anchored** — the same discipline
     WP04/T014 applied to the classifier, and for the same reason:
     `tasks/<wp>/baseline-tests.json` is deliberately PRIMARY and must not be
     swept in.
  2. Wire the hidden `app.command(name="merge-driver-review-cycle", hidden=True)`
     entry in `src/specify_cli/cli/commands/__init__.py` (see the binding
     constraint above about the version-bump rule).
  3. Cover the fresh-init registration path (`init.py`) and the lane-merge path
     (`lanes/merge.py`).
- **Files**: `.gitattributes`, `src/specify_cli/cli/commands/__init__.py`,
  `src/specify_cli/cli/commands/init.py`, `src/specify_cli/lanes/merge.py`
- **Validation checklist**:
  - [ ] `git config --get merge.spec-kitty-review-cycle.driver` resolves after a
        fresh init.
  - [ ] The `.gitattributes` rule does not match `baseline-tests.json` or
        `tasks/WP*.md`.

## Subtask T079 — Upgrade migration for existing clones

- **Purpose**: Existing projects must gain the driver without re-running init.
- **Steps**: Author
  `src/specify_cli/upgrade/migrations/m_3_2_7_review_cycle_merge_driver.py`,
  modelled on `m_3_2_6_decisions_event_log_merge_driver.py`. Use the
  config-aware helper `get_agent_dirs_for_project()` if the migration touches
  agent directories; respect deletions and never `mkdir` a missing dir.
- **Files**: `src/specify_cli/upgrade/migrations/m_3_2_7_review_cycle_merge_driver.py`
- **Validation checklist**:
  - [ ] Idempotent — running it twice is a no-op.
  - [ ] Does not clobber an operator's existing custom driver value.

## Subtask T080 — Prove the clobber is closed

- **Purpose**: T017's original discharge condition, now actually achievable.
- **Steps**: Build a test that reproduces the create-window clobber
  scenario — a coord mission with cycles on PRIMARY, a cycle-1 write to COORD,
  and a `-X theirs` squash — and assert that with the driver registered the
  target-side verdict is **not** destroyed. Red-first: confirm it fails without
  the driver before wiring it in.
- **Files**: `tests/specify_cli/cli/commands/test_review_cycle_merge_driver.py` (new; modelled on the sibling
  `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`).
- **Validation checklist**:
  - [ ] Red without the driver, green with it — demonstrated, not asserted.
  - [ ] The test exercises the real merge path, not a hand-rolled stand-in.

## Definition of Done

- A `review-cycle` merge driver exists that never blends two distinct verdicts
  (T077).
- It is registered across `.gitattributes`, the command table, the init path and
  the lane-merge path, and `git config` resolves it after a fresh init (T078).
- An idempotent upgrade migration registers it for existing clones (T079).
- The create-window clobber is demonstrated closed, red-first (T080).
- WP04's `test_review_cycle_tasks_hazard_is_ruled_and_tracked` tripwire is
  reported as needing update (it reds by design once the driver lands) —
  **reported, not edited**, since it is outside this WP's ownership.
- `ruff`, `ruff check --select C901` and `mypy --strict` clean on every touched
  file, zero new suppressions.
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15.

## Risks & Mitigations

- **Copying the union driver.** `merge_driver_event_log` is the wrong template;
  unioning two verdict documents fabricates a verdict. Mitigate by writing the
  collision semantics into the docstring *before* the implementation.
- **Partial registration.** A `.gitattributes` rule with no `.git/config` entry
  is silently inert. Mitigate with T078's `git config --get` check as an
  executable assertion, not a manual step.
- **Directory-anchoring the `.gitattributes` pattern**, sweeping in
  `baseline-tests.json`. Same failure WP04/T014 avoided; mitigate the same way.
- **Editing the WP04 tripwire to make CI green.** That would remove the
  mechanism that made this hazard visible. Report instead.

## Reviewer Guidance

- Demand the collision-semantics decision in writing, and confirm no code path
  can produce a document containing content from two distinct verdicts.
- Confirm the `.gitattributes` pattern is filename-anchored by asking for the
  `baseline-tests.json` negative case.
- Confirm registration is complete by asking for the `git config --get` output
  after a simulated fresh init — not just the presence of the `.gitattributes`
  line.
- Confirm T080's test was red before the driver landed. A green-only
  demonstration does not prove the clobber was ever closed.
- Confirm the WP04 tripwire was reported and not silently edited.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T16:10:00Z – operator – lane=planned – WP authored mid-mission to discharge WP04's T017 ownership deadlock.
- 2026-08-04T12:00:00Z – claude-opus-5 (reviewer, transcribed from the implementer's report) – lane=for_review – T077–T080 implemented.
  **T077 collision semantics: REFUSE FAIL-CLOSED, not renumber.** Identical
  content on both sides is a clean fast-path (exit 0, file untouched). A
  genuine collision embeds both documents verbatim behind standard conflict
  markers and exits 1. Renumbering was considered and rejected: `cycle_number`
  is exactly the field downstream readers (`ReviewCycleArtifact.latest`,
  `latest_review_artifact_verdict`) use to decide which verdict is
  authoritative, so silently reassigning it during an unattended squash would
  change "which verdict is latest" with no human present — the same
  fabrication risk FR-006/C-002(b) warn against, one layer down — and it would
  have to trust a merge-time directory listing, the mechanism class that
  caused this hazard. Refusing loses nothing; both verdicts survive
  byte-for-byte. This supersedes WP04-XWP-03's prediction that reconciliation
  would "likely need re-numbering one side, coordinating with WP09's numbering
  rework": no such coordination was needed.
  **Registered across all four surfaces** (`.gitattributes`, the hidden
  command entry, `init.py`'s fresh-init seed, `lanes/merge.py`'s registry)
  plus an idempotent upgrade migration, because an unregistered driver is
  inert and fails silently to git's default merge.
  **T080 proved non-vacuous**, which is the part worth crediting: the red was
  demonstrated through the real `_merge_branch_into` → `git merge --squash -X
  theirs` path, and the *green* test was then shown to fail (`DID NOT RAISE`)
  when the registry was monkeypatched — so the test can actually fail. A third
  hermetic variant drives real `git merge` with an absolute-interpreter driver
  command, depending on neither ambient `PATH` nor ambient `.git/config`.
  **Version-bump rule did not fire**, settled on precedent rather than
  argument: commit `b04da00e1` registered `merge_driver_issue_matrix` in the
  same nested `cli/commands/__init__.py` with no `pyproject.toml`/`CHANGELOG`
  change, and `src/specify_cli/__init__.py`'s `__version__` is resolved
  dynamically from package metadata rather than being a literal to bump.
  **Prompt errors found:** (1) the three pinned-exhaustive gates this WP was
  warned about (`test_inline_meta_read_gate`, `test_mission_resolver_walker_gate`,
  `untrusted_path_audit/inventory.md`) did NOT red — the migration touches no
  `meta.json`, walks no `kitty-specs/`, and joins no untrusted segments; all
  three verified green. Two *different*, unnamed gates did red
  (`test_no_dead_modules.py`, `test_ratchet_baselines.py`) plus the
  pytest-marker-convention and completion-manifest checks. (2) The prescribed
  filename `m_3_2_7_*` contradicts its own required `target_version`: with
  `pyproject.toml` still at 3.2.6, declaring 3.2.7 trips
  `test_discovered_migration_targets_do_not_exceed_package_version`, so
  `target_version = "3.2.6"` is used and documented in the module.
  **Disclosed cross-WP edits** (all to files no WP in this mission owns, or to
  a closed WP's files): `tests/architectural/test_no_dead_modules.py`
  (category-1 auto-discovered-migrations allowlist),
  `tests/architectural/_baselines.yaml` (ratchet 98→99 with justification
  appended to the existing chain), `src/specify_cli/_completion_manifest.json`
  (hand-trimmed to only the new command; an unrelated pre-existing help-text
  drift the regenerate picked up was reverted and traced to commits already on
  the branch, not silently absorbed), and — following that tripwire's own
  written instruction — `test_merge_reconciliation_class_guard.py`'s final
  assertion plus `census/verdict_seam_IC04.yaml`'s WP04-XWP-03 closure.
  **Two mypy --strict errors are pre-existing, verified not asserted:** the
  `no-any-return` at `merge_driver.py:635` is inside
  `merge_driver_acceptance_matrix`'s helper and reproduces on the mission
  branch; the `Class cannot subclass "MergeDriverSeedingMigration"` reproduces
  identically for the sibling `m_3_2_6_decisions_event_log_merge_driver.py:39`,
  so it is a property of that untyped base class, inherited by correctly
  following the sibling pattern rather than introduced here.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP18 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
