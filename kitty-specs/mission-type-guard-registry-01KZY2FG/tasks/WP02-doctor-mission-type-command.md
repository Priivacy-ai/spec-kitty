---
work_package_id: WP02
title: spec-kitty doctor mission-type command
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - doctor mission-type diagnostic command
history:
- at: '2026-08-13T22:40:00Z'
  actor: system
  action: Prompt generated during hand-authored /spec-kitty.tasks dispatch (no LLM tasks-phase command available in this run; canonical task-prompt-template.md structure followed directly).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- src/specify_cli/cli/commands/_mission_type_audit.py
- tests/specify_cli/cli/commands/test_doctor_mission_type.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/_mission_type_audit.py
- tests/specify_cli/cli/commands/test_doctor_mission_type.py
- tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – spec-kitty doctor mission-type command

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer) before parsing the
rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: (fill in at claim time)

---

## Objectives & Success Criteria

Ship `spec-kitty doctor mission-type --json [--fail-on <states>]`, modeled directly on
`spec-kitty doctor identity`, so operators can audit mission-type resolution health across
`kitty-specs/` proactively — the same unregistered/unresolvable-type class WP01 fixes at
runtime, made discoverable before it silently degrades a live run (FR-007, FR-008, FR-009,
NFR-004).

**Done when**: T008's RED test is GREEN, the FR-008 6-state taxonomy classifies every fixture
mission correctly with none omitted (SC-005), `--fail-on` matches `doctor identity`'s exit-code
contract byte-for-byte in shape (SC-006), the golden CLI-surface contract test passes with
`mission-type` as a real, registered 20th subcommand, `mypy --strict` / `ruff check` are clean,
and the command completes in under 2 seconds for a typical `kitty-specs/` tree (NFR-004).

## Context & Constraints

- **Binding source documents**: `.kittify/charter/charter.md`,
  `kitty-specs/mission-type-guard-registry-01KZY2FG/spec.md` (User Story 4, FR-007–FR-009,
  NFR-004, the FR-008 taxonomy definition and its blank/null/non-string boundary sentence),
  `kitty-specs/mission-type-guard-registry-01KZY2FG/plan.md` §Seam & Module Placement (the CLI
  seam bullets — this is the authoritative design, follow it exactly, especially the FR-008
  classifier decision procedure) and §Contracts (the golden-contract-test update requirement).
- **No functional dependency on WP01** — this WP's files (`doctor.py`,
  `_mission_type_audit.py`, and the two test files) never overlap with WP01's. You may start
  immediately without waiting for WP01 to land.
- **Canonical precedent — read both files in full before writing code, not just their
  docstrings** (plan.md's own verification already did this and corrected an earlier
  mischaracterization — PLAN-ARCH-001 — do not repeat it):
  - `src/specify_cli/status/identity_audit.py` (361 lines) — the domain-layer shape:
    `IdentityState` dataclass, `classify_mission`, `audit_repo`, `summarize`. This is the shape
    `MissionTypeState` / `classify_mission_type` / `audit_mission_types` /
    `summarize_mission_types` mirror.
  - `src/specify_cli/cli/commands/_identity_audit.py` (346 lines) — the CLI-glue/report-builder
    shape: `run_identity_audit`, `_build_identity_json`, `_compute_fail_on`. This is the shape
    `run_mission_type_audit` mirrors.
  - `src/specify_cli/cli/commands/doctor.py:396-444` — the `identity` `@app.command` shell
    itself (flags, `locate_project_root()` try/except, delegation pattern).
  - This mission's own `_mission_type_audit.py` **combines both precedent modules' roles into
    one new file** (plan.md's explicit, reasoned choice — mission-type resolution logic already
    lives entirely in `charter`/`doctrine`, so a second domain-layer home is unneeded) — do not
    split it into two files, and do not treat either single precedent file's line count as a
    target; the combined scale is the two files' roles folded together, at their combined LOC
    order of magnitude, not a 1:1 mirror of either one alone.
- **`doctor.py` is a thin-shell-only file** (its own binding docstring: "New subcommand logic
  belongs in a sibling, not here; this file stays a thin shim of command shells"). Do not put
  any classification/audit logic directly in `doctor.py`.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on
  `kitty/mission-mission-type-guard-registry-01KZY2FG`. Completed changes must merge back into
  it.
- **Planning base branch**: `kitty/mission-mission-type-guard-registry-01KZY2FG`
- **Merge target branch**: `kitty/mission-mission-type-guard-registry-01KZY2FG`

> Prepare the workspace with `spec-kitty implement WP02` — it resolves the lane worktree from
> `lanes.json`; do not reconstruct the path by hand.

## ATDD Commit Sequence (charter C-011, binding — do not reorder)

1. **Commit 1 (RED)** — T008, committed before any implementation commit. The command does not
   exist yet, so this is trivially, unambiguously RED (the CLI has no `mission-type` subcommand
   at all).
2. **Commit 2 (implementation)** — T009 + T010 land together (the sibling module and the thin
   shell that delegates to it are one coherent addition). T008 flips to GREEN.
3. **Commit 3 (golden-contract, folded per plan.md, not its own ATDD pin)** — T011. This is a
   direct, mechanical consequence of the new command existing (no new *behavior*, only a
   frozen-contract update reflecting behavior Commit 2 already introduced) — fold it into Commit
   2 if your workflow prefers a single implementation commit; do not treat it as optional either
   way (it is load-bearing — see tasks.md's Chokepoints section).
4. T012's verification may be folded into Commit 2/3 or stand alone, as long as the evidence
   lands in the Activity Log.

## Subtasks & Detailed Guidance

### T008 — RED: FR-008/SC-005/SC-006 ATDD pin + NFR-004 timing regression test

- **Purpose**: Pin the command's classification and exit-code behavior as a failing-first test
  before the command exists, AND give NFR-004 (the <2s performance budget) an automated
  regression test, not only a one-off manual measurement (TASKS-VERIFY-004 fix). The precedent
  this WP is modeled on, `doctor identity`, backs its own analogous budget (NFR-002) with exactly
  this shape of test — `tests/doctor/test_identity_audit.py::test_nfr_002_timing_200_missions`
  (read it before writing this step's test; it is the template) — and this WP's own Context &
  Constraints section already instructs reading the precedent modules "in full," which extends to
  their test suites, not only their production code.
- **Steps**:
  1. Create `tests/specify_cli/cli/commands/test_doctor_mission_type.py`. Build a fixture
     `kitty-specs/` tree (via `tmp_path` + a minimal `.kittify/` scaffold, following
     `test_doctor_identity`-style fixtures in this repo's existing doctor tests for the harness
     pattern) containing **one mission per FR-008 taxonomy state**:
     - `resolved` — `meta.json` has `mission_type` set to an activated, loadable type
       (`software-dev` is always safe to use here).
     - `activated-unresolvable` — `mission_type` is activated in the project charter but has no
       loadable profile/definition on disk (mirror the exact branch
       `_resolve_action_slot` hits at `charter/mission_type_profiles.py:799`'s
       `raise UnknownMissionTypeError(...)` — you are constructing the read-only classification
       twin of that raise, not calling it).
     - `unknown` — `mission_type` string present but not registered/activated anywhere.
     - `typeless` — no `mission_type` key at all.
     - `legacy-key-only` — only the retired `mission` key is present, no `mission_type` key.
     - `error` — `meta.json` unreadable or malformed for that mission directory (mirrors
       `doctor identity`'s `orphan`-on-unreadable-metadata posture).
  2. **FR-008 boundary case (binding, do not skip)**: add a mission whose `mission_type` key is
     present but blank (`""`) — or `null`, or a non-string value — AND whose legacy `mission`
     key holds a real string value. Assert this classifies as `typeless`, **not**
     `legacy-key-only`, per FR-008's closing sentence and plan.md's own called-out design
     decision (a present-but-blank/null/non-string `mission_type` key wins over checking the
     legacy key at all — the key's own presence-with-a-value is what routes into that branch,
     full stop, no fallback to the legacy key). This is the counter-intuitive case a
     plausible-but-wrong implementation would get backwards — plan.md's Seam & Module Placement
     section names this exact risk explicitly.
  3. Assert `spec-kitty doctor mission-type --json` (invoked via the Typer `CliRunner` pattern
     this repo's other `doctor` tests already use) classifies every fixture mission into the
     correct, single state — none omitted (SC-005).
  4. Assert `spec-kitty doctor mission-type --fail-on unknown` exits non-zero when an `unknown`
     mission exists in the fixture tree, and exits zero with no `--fail-on` flag regardless of
     findings (SC-006, matching `doctor identity`'s `--fail-on` contract).
  5. Confirm this whole file is RED against the WP's base commit — there is no `mission-type`
     Typer command registered yet, so every assertion fails at the CLI-invocation boundary.
  6. **NFR-004 automated timing regression test** (TASKS-VERIFY-004 fix): add
     `test_nfr_004_timing_200_missions`, mirroring
     `test_nfr_002_timing_200_missions`'s shape exactly — build a synthetic 200-mission
     `kitty-specs/` fixture tree (a sibling helper to that test's own `_build_200_mission_repo`,
     adapted for this command's fixture shape; reuse the pattern, not the literal function),
     invoke the mission-type audit (either `audit_mission_types(repo_root)` directly once T009
     exists, or the full CLI command — match whichever this WP's own `run_mission_type_audit`
     shape makes most direct to time), and assert `elapsed < 2.0` (NFR-004's stated budget, vs.
     the precedent's 3.0s for its own NFR-002). This is trivially RED today for the same reason
     as the rest of the file (no command/module exists yet) — no separate RED-verification step
     needed beyond step 5's file-level confirmation.
- **Files**: `tests/specify_cli/cli/commands/test_doctor_mission_type.py` (new).
- **Validation**: file fails to collect/run meaningfully against the base commit (no such
  command); passes once T009/T010 land, including `test_nfr_004_timing_200_missions`.

### T009 — `_mission_type_audit.py` (new sibling module)

- **Purpose**: The domain-layer classifier + CLI-glue/report-builder combined module (FR-008's
  exact decision procedure; FR-007/FR-009's report/exit-code shape).
- **Steps**: Implement, following plan.md's Seam & Module Placement section's FR-008 decision
  procedure **exactly** (do not improvise an alternate reading — a plausible-but-wrong
  alternative, "fall through to the legacy key whenever `mission_type` is blank," would silently
  misclassify the boundary case T008 pins):
  1. `MissionTypeState` dataclass — `path`, `slug`, `mission_type_raw: str | None`,
     `resolved_key: str | None`, `state` (the FR-008 6-value `Literal`), `error: str | None`.
     `to_dict()` mirrors `IdentityState.to_dict()`.
  2. `classify_mission_type(feature_dir, *, registered: list[str], repo: MissionTypeRepository)
     -> MissionTypeState`:
     - Read `meta.json` via `specify_cli.core.paths.load_meta_fail_closed`. On `OSError` /
       `MissionMetaReadError` → state `error`.
     - If `"mission_type" in raw` (key-presence check, not truthiness):
       `raw_val = raw["mission_type"]`; `key = canonical_mission_type_key(raw_val) if
       isinstance(raw_val, str) else None`.
       - `key is None` → state `typeless` (this is the T008 boundary case — no fallback to the
         legacy `mission` key here, regardless of what it contains).
       - Else: `is_registered = key in registered`.
         - not registered → `unknown`.
         - registered, `repo.get(key) is not None` → `resolved`.
         - registered, `repo.get(key) is None` → `activated-unresolvable`.
     - Else (no `"mission_type"` key at all): `raw_legacy = raw.get("mission")`; `legacy_key =
       canonical_mission_type_key(raw_legacy) if isinstance(raw_legacy, str) else None`.
       - `legacy_key is not None` → `legacy-key-only`.
       - `legacy_key is None` → `typeless`.
     - Do **not** call `_canonical_meta_mission_type` (`specify_cli/mission.py:542-556`)
       directly — it collapses "which key produced this value" into one string, which destroys
       the information `legacy-key-only` needs. Use the shared `canonical_mission_type_key`
       primitive (`charter/mission_type_key.py:24`) directly instead, as above.
  3. `audit_mission_types(repo_root) -> list[MissionTypeState]` — walks `kitty-specs/` like
     `identity_audit.audit_repo`; computes `registered = existing_mission_types(repo_root)` and
     `repo = MissionTypeRepository.default()` **once** before the loop (NFR-004 — avoid N
     redundant `.kittify/config.yaml` reads across the tree).
  4. `summarize_mission_types(states) -> dict[str, object]` — per-state counts, zero-filled
     across all six states.
  5. `run_mission_type_audit(repo_root, json_output, mission, fail_on) -> None` — the command
     entry point, mirroring `run_identity_audit`'s shape (fail-on parsing, JSON builder,
     human-readable print, `typer.Exit(1 if triggered else 0)`).
- **Files**: `src/specify_cli/cli/commands/_mission_type_audit.py` (new).
- **Validation**: unit-level correctness for all 6 states plus the boundary case, exercised via
  T008's fixture tree once wired to the CLI shell (T010).

### T010 — `doctor.py`: `mission-type` thin `@app.command` shell

- **Purpose**: Register the CLI surface (FR-007), mirroring `identity`'s shell exactly.
- **Steps**: Add `@app.command(name="mission-type")` with `--json` (flag), `--mission` (scoping
  option), `--fail-on` (comma-separated states option) — same shape as `identity`'s own options
  (`doctor.py:396-444`). Resolve `repo_root` via the same `locate_project_root()` try/except
  pattern. Delegate immediately: `from ._mission_type_audit import (  # noqa: E402\n
  run_mission_type_audit,\n)` (mirrors the existing import pattern at lines 97-98), then call
  `run_mission_type_audit(repo_root, json_output, mission, fail_on)`. Write real `--help` docs
  (the golden test in T011 captures whatever text you actually ship — it does not prescribe the
  text in advance, but it must be accurate and follow the terminology canon: `--mission`, never
  `--feature`).
- **Files**: `src/specify_cli/cli/commands/doctor.py`.
- **Validation**: `spec-kitty doctor mission-type --help` runs and shows the new command; T008's
  CLI-invocation assertions stop failing at the "no such command" boundary.
- **Parallel?**: Yes, alongside T011 once T009 exists (T011 needs T010's real `--help` text to
  capture an accurate golden snapshot, so sequence T010 before T011 in practice even though they
  touch disjoint parts of the same file/different files).

### T011 — Golden CLI-surface contract update (chokepoint — see tasks.md)

- **Purpose**: Keep `test_doctor_cli_surface_golden.py` truthful once `mission-type` is a real
  registered subcommand — this is load-bearing production-contract enforcement, not optional
  docs upkeep (plan.md's Contracts section).
- **Steps**: In `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py`:
  1. Add `"mission-type"` to `FROZEN_SUBCOMMANDS` (currently a 19-member frozenset at line ~56);
     update the module's own count-comment/docstring from "19" to "20" and name what added it
     (mirror the existing pattern documenting prior additions, e.g. "review-cycle-reconcile...
     WP08").
  2. Add `EXPECTED_OPTIONS["mission-type"] = {"--json": "flag", "--mission": "value",
     "--fail-on": "value"}` (identical shape to `identity`'s own entry at line ~93).
  3. Add `EXPECTED_HELP["mission-type"] = [...]` — capture the **actual**, whitespace-normalized
     `--help` output your T010 command emits (run `spec-kitty doctor mission-type --help` and
     transcribe it; do not write aspirational text the command doesn't actually produce).
- **Files**: `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py`.
- **Validation**: `pytest tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py -q`
  passes, including `test_registered_command_names_match_frozen_subcommands` and the
  parametrized per-subcommand option/help assertions for `"mission-type"`.

### T012 — Verify: GREEN, NFR-004 perf budget, targeted suite

- **Purpose**: Close out the WP with reviewer-ready evidence.
- **Steps**:
  1. Run `.venv/bin/python -m pytest tests/specify_cli/cli/commands/test_doctor_mission_type.py
     tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py -q` — confirm all pass,
     including T008's tests now GREEN, in particular `test_nfr_004_timing_200_missions`
     (TASKS-VERIFY-004 fix — this is the real, CI-enforced NFR-004 regression gate, not the
     manual spot-check below).
  2. As a belt-and-suspenders manual spot-check (not the primary evidence — step 1's automated
     test is): time `spec-kitty doctor mission-type --json` against a fixture tree of realistic
     size and confirm it completes in under 2 seconds (NFR-004) — record the actual measured time
     in the Activity Log, not an assumption.
  3. Run `mypy --strict` and `ruff check` on both new/changed production files; both clean.
  4. Run `pytest tests/architectural/test_no_legacy_terminology.py` locally before push (this
     command's new `--help` text is new user-facing prose; this gate runs only in CI's
     `integration-tests-core-misc` job, not the fast-tests shards, per CLAUDE.md's own
     instruction — do not assume local fast-test green covers it).
- **Files**: none (verification only).
- **Validation**: all four checks pass; results recorded in the Activity Log with actual
  command output.

## Test Strategy

- **Targeted surface only**: `tests/specify_cli/cli/commands/test_doctor_mission_type.py` (new,
  this WP's own primary test), `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py`
  (frozen-contract, this WP's mechanical update). Do **not** run the full `pytest tests/` suite.
- **Revert discipline**: T008's tests fail if the command, the classifier, the `--fail-on`
  exit-code behavior, or the NFR-004 timing budget is reverted or regressed — this is a stated
  acceptance requirement, not an aspiration.

## Risks & Mitigations

- **FR-008 boundary-case misreading**: the plausible-but-wrong alternative (fall through to the
  legacy `mission` key whenever `mission_type` is blank) silently misclassifies the boundary
  case. Mitigation: T008's fixture explicitly covers this; T009 implements the decision
  procedure exactly as plan.md specifies, with no alternate reading.
- **NFR-004 performance risk**: computing `existing_mission_types` / `MissionTypeRepository`
  per-mission instead of once per audit run would scale badly across a large `kitty-specs/`
  tree. Mitigation: T009's `audit_mission_types` computes both once before the loop, matching
  `identity_audit.audit_repo`'s own established pattern, AND T008's `test_nfr_004_timing_200_missions`
  is an automated regression gate for this, not only a design intention (TASKS-VERIFY-004 fix —
  a future change that reintroduces per-mission repository reads now fails CI, not just a manual
  spot-check).
- **Golden-contract miss**: forgetting T011 fails CI deterministically the moment `mission-type`
  is registered. Mitigation: land T011 in the same commit as T010 (see ATDD Commit Sequence).

## Review Guidance

- Confirm RED→GREEN on this WP's own base→final commit for T008's assertions (C-011) — use the
  concrete recipe below rather than accepting prose reasoning alone (TASKS-VERIFY-005 fix; see
  WP01's own Review Guidance for why prose-only RED claims are not trustworthy on their own).
- **Concrete RED-on-base re-verification recipe** (TASKS-VERIFY-005 fix): T008 is a single,
  trivially-RED commit (the whole file fails because no `mission-type` command exists yet), so
  file-level re-verification is sufficient here — no per-assertion node-ids needed, unlike WP01:
  ```
  git worktree add /tmp/review-wp02 kitty/mission-mission-type-guard-registry-01KZY2FG
  cd /tmp/review-wp02
  git checkout <WP02-commit-1-sha> -- tests/specify_cli/cli/commands/test_doctor_mission_type.py
  .venv/bin/python -m pytest tests/specify_cli/cli/commands/test_doctor_mission_type.py -q
  # EXPECT: collection/run failure for every test in the file — no `mission-type` command is
  # registered at this commit's production code (still the WP's base commit).
  git checkout <WP02-final-commit-sha> -- .
  .venv/bin/python -m pytest tests/specify_cli/cli/commands/test_doctor_mission_type.py \
      tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py -q
  # EXPECT: all pass, including test_nfr_004_timing_200_missions (TASKS-VERIFY-004's automated
  # regression gate) and the FR-008 boundary-case assertion below.
  ```
  (Substitute the WP's actual Commit-1 and final-commit SHAs.)
- Confirm the FR-008 boundary case (blank `mission_type` + real legacy `mission` value → still
  `typeless`) is actually exercised and actually passes — this is the single easiest place for
  an implementer to silently pick the more-intuitive-but-wrong reading.
- Confirm `test_nfr_004_timing_200_missions` exists, actually invokes the mission-type audit
  against a synthetic ~200-mission fixture, and actually asserts `elapsed < 2.0` — not only that
  T012's manual spot-check note is present (TASKS-VERIFY-004 fix).
- Confirm `doctor.py` stayed a thin shell — no classification logic leaked into it.
- Confirm the golden contract test's `EXPECTED_HELP["mission-type"]` matches the command's real
  `--help` output byte-for-byte (whitespace-normalized), not aspirational text.
- Confirm no file outside `owned_files` was touched.

## Activity Log

> **CRITICAL**: entries MUST be in chronological order (oldest first, newest last). Append at
> the end.

- 2026-08-13T22:40:00Z – system – Prompt created.
