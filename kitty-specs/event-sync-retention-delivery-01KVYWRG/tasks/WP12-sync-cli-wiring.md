---
work_package_id: WP12
title: Sync CLI wiring
dependencies:
- WP07
- WP09
- WP10
- WP11
requirement_refs:
- FR-005
- FR-009
- FR-010
- FR-019
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T071
- T072
- T073
- T074
- T075
- T076
- T077
phase: Phase 5 - Policy, migration, status, CLI
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "88547"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/sync.py
create_intent:
- tests/cli/commands/test_sync_commands.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/sync.py
- tests/cli/commands/test_sync_commands.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP12 – Sync CLI wiring

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`
If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

This WP is the **CLI surface half of plan concern IC-08** and the join point of the whole mission. It is the
**single owner of `src/specify_cli/cli/commands/sync.py`** and must stay **THIN — wiring only**. Every piece
of logic already lives in a domain module: dispatch in WP07, target authority in WP01/WP02, config in WP09,
migration in WP10, and status-report/retention in WP11. This WP connects the `sync` subcommands to those
modules; it must not re-implement any of their behavior.

You complete this WP when:

- `sync now` drives the WP07 dispatcher and `sync server <url>` sets the WP01 target authority (**FR-005** —
  changing the server re-delivers the same retained events to the new target).
- `sync status` and `sync status --check --json` emit the WP11 `status_report` sections additively
  (**FR-009**, **FR-019**).
- `sync gc` / `sync archive` invoke the WP11 `retention` operations as explicit destructive-only operations
  (**FR-010**).
- The `EventSyncConfig` mode selection surface (e.g. `sync config` / mode flags) routes to WP09 (**FR-006**
  semantics surfaced via the CLI).
- All existing `sync` flags and output stay backward-compatible; existing stats/status consumers keep working
  with clarified semantics (**NFR-006**).
- No `feature*` aliases appear in any new flag, command, field, or path; "Mission" not "feature"
  (Terminology Canon).
- `tests/cli/commands/test_sync_commands.py` asserts observable CLI output + on-disk/ledger state for
  now/server/status/gc/archive/config — not internal call order (**NFR-001**).

**Acceptance criteria satisfied**: FR-005, FR-009, FR-010, FR-019, NFR-001, NFR-006, plus the CLI surface of
US1 (replay to a fresh target), US2 (choose where events go), US4 (inspect + explicit cleanup).

## Context & Constraints

**Prerequisite WPs and what they hand you (consume, never re-implement):**

- **WP07 (`delivery/dispatcher.py`)** — the select→post→record dispatch path. `sync now` calls it; the CLI
  does not decide which events to send or how to map outcomes. Re-drain to a new target (FR-005) is
  dispatcher behavior; the CLI just triggers a run against the resolved active target.
- **WP01/WP02 (target authority, `sync/target_authority.py`)** — the `ResolvedSyncTarget`. `sync server <url>`
  writes the configured target; everything else reads the resolved target. The CLI must not derive queue
  scope or pick URLs itself (contract §1; SC-008).
- **WP09 (`delivery/config.py`, `EventSyncConfig`)** — the retention × delivery mode dial (TEAMSPACE /
  EXTERNAL_RECEIVER / LOCAL_RETENTION / OPT_OUT). The mode-selection CLI surface reads/writes config via
  WP09; the CLI does not encode mode semantics.
- **WP10 (`sync/migrate_journal.py`)** — migration is its own surface; this WP does not own migration
  commands, but coordinate so `sync` subcommands and migration share the resolved target.
- **WP11 (`delivery/status_report.py`, `delivery/retention.py`)** — `sync status [--check --json]` emits the
  status report; `sync gc` / `sync archive` call retention. The CLI passes already-resolved handles in and
  prints/serializes the result out.

**Links:**

- Spec: `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md`
- Plan: `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` (IC-08, CLI surface)
- Contract: `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md`
  §1 (target authority), §3 (journal/ledger), §6 (status/compatibility)

**Architectural constraints to honor:**

- **Single-owner / thin-CLI**: this WP is the only writer of `cli/commands/sync.py`. WP02 explicitly does NOT
  edit `queue.py` scope consumption here, and the CLI must not absorb domain logic. If you find yourself
  writing a loop over events, a result-mapping, or a count computation in `sync.py`, that logic belongs in a
  domain module — call it instead.
- **NFR-006 (additive compatibility)**: existing `sync` flags/output and body-upload status remain
  backward-compatible. Body-upload tables stay owned by `sync/queue.py` (C-006); the CLI surfaces their
  counts via WP11's `body_upload_compatibility` section, never conflated with journal/ledger counts.
- **NFR-001 (observable-state tests)**: CLI tests assert printed output + on-disk/ledger state, not which
  internal function was called in what order.
- **Terminology Canon (T076)**: no `feature*` aliases in any flag/command/field/path; "Mission" not
  "feature".

No out-of-map edits: both `owned_files` are owned solely by this WP.

## Branch Strategy
- **Strategy**: Planning artifacts were generated on mission/event-sync-retention-delivery; completed changes must merge back into mission/event-sync-retention-delivery.
- **Planning base branch**: mission/event-sync-retention-delivery
- **Merge target branch**: mission/event-sync-retention-delivery
> Populated by `spec-kitty agent mission tasks`. Do not change manually.

## 🔴 ATDD-First (binding — charter C-011)

**You cannot start implementation until a failing-first ATDD test exists.** Per the charter's *ATDD-First Discipline* (binding, C-011), this WP follows red→green→refactor:

1. **RED first** — before any implementation commit, write at least one acceptance test that pins the user-observable behaviour this WP delivers (see the Subtasks/Acceptance below) and commit it **as the lane's first, separate commit while it FAILS**.
2. **GREEN** — implement until that test (and the rest) pass.
3. **Refactor** with the tests green.

The reviewer verifies **red→green**: the ATDD test was RED on `mission/event-sync-retention-delivery` and GREEN on this WP's final commit. A WP without a failing-first ATDD commit is **rejected at review** even if the code works.

## ⌨️ Operator CLI surface (A7)

EventSyncConfig mode selection is pinned to `spec-kitty sync mode <TEAMSPACE|EXTERNAL_RECEIVER|LOCAL_RETENTION|OPT_OUT>` (`sync mode` with no argument prints the current mode). Wire this exact command in `cli/commands/sync.py`. Honor the Terminology Canon — no `feature*` aliases in the flag/command/field.

## Subtasks & Detailed Guidance

### Subtask T071 – Wire `sync now` → dispatcher; `sync server <url>` → target authority
- **Purpose**: Connect the two foundational subcommands. `sync now` runs the WP07 dispatcher against the
  resolved active target; `sync server <url>` sets the WP01 target authority so a later `sync now`
  re-delivers retained events to the new target (**FR-005**, US1).
- **Steps**:
  1. In `src/specify_cli/cli/commands/sync.py` resolve the `ResolvedSyncTarget` via WP01/WP02 once at the
     command entry, then hand it to the dispatcher. Do not let `sync.py` compute queue scope or pick URLs.
  2. `sync now`: call the WP07 dispatcher's run entry point with the resolved target + journal + ledger
     handles. Print an observable summary (delivered / duplicate / pending / rejected / terminal-failed
     counts) sourced from the dispatcher's return value — do not recompute counts in the CLI.
  3. `sync server <url>`: persist the configured server URL through the target-authority surface (WP01),
     preserving the existing flag/behavior contract. After this, `sync now` against the new URL re-drains the
     same retained events (FR-005 is dispatcher + ledger behavior; the CLI just re-triggers).
  4. Keep the command bodies short; extract any non-trivial argument plumbing into a small private helper if
     it threatens the complexity ceiling (≤ 15).
- **Files**: `src/specify_cli/cli/commands/sync.py` (authoritative surface).
- **Parallel?**: Yes — `[P]`. Lead subtask establishing the command scaffolding others extend.
- **Validation**:
  - [ ] `sync now` invokes the dispatcher and prints a summary from its result.
  - [ ] `sync server <url>` updates the configured target via target authority.
  - [ ] CLI does not derive queue scope or choose URLs itself.
- **Edge cases**: `sync now` with no events (empty summary, exit 0); `sync server` with an unchanged URL
  (idempotent); switching URL then `sync now` re-delivers retained events (US1 / FR-005 path).

### Subtask T072 – Wire `sync status` and `sync status --check --json` → WP11 status_report
- **Purpose**: Emit the additive status sections (**FR-009**, **FR-019**) without computing them in the CLI.
- **Steps**:
  1. `sync status`: build the report via WP11 `status_report.build_status_report(...)` and render the
     human-readable view. Preserve the existing human-readable identity-boundary block and the existing
     top-level fields (per `sync-status-output.md`).
  2. `sync status --check --json`: suppress the human block and emit the single JSON object — the existing
     top-level fields PLUS the seven additive sections from WP11 (`target_authority`, `event_journal`,
     `delivery_targets`, `delivery_ledger`, `migration_conflicts`, `terminal_failures`,
     `body_upload_compatibility`). The CLI serializes; it does not assemble.
  3. Preserve the existing `--check` exit-code contract (0 / 2) from `mvp-cli-sync-boundary-completion`; the
     additive sections do not change exit-code semantics (NFR-006).
- **Files**: `src/specify_cli/cli/commands/sync.py`.
- **Parallel?**: No — builds on T071 scaffolding.
- **Validation**:
  - [ ] `--check --json` output contains old top-level fields AND all seven new sections.
  - [ ] Human-readable `sync status` still prints the existing fields.
  - [ ] Exit codes unchanged; CLI does no count assembly.
- **Edge cases**: env/config target disagreement surfaced via `target_authority` and made non-silent before
  any network call (contract §1, SC-008); empty journal (sections present, zeros).

### Subtask T073 – Wire `sync gc` / `sync archive` → WP11 retention
- **Purpose**: Expose the explicit destructive-only operations (**FR-010**), preserving ledger history.
- **Steps**:
  1. `sync gc` and `sync archive` call the WP11 `retention` operations (`gc_payloads` / `archive_payloads`)
     with the resolved journal + ledger handles. Print the structured result (counts archived/purged/skipped)
     from retention — do not compute it in the CLI.
  2. These run only on explicit invocation. The CLI must never call retention from `sync now` or any
     automatic path (US4 scenario 3 — no source events deleted on a normal sync).
  3. Surface the WP11 GC *suggestion* (large AND fully-delivered) in `sync status` output where appropriate,
     but the *operation* fires only on the explicit `sync gc` / `sync archive` command.
- **Files**: `src/specify_cli/cli/commands/sync.py`.
- **Parallel?**: No.
- **Validation**:
  - [ ] `sync gc` / `sync archive` call WP11 retention and print its result.
  - [ ] No automatic path calls retention.
  - [ ] Delivery-ledger history is preserved after either command (asserted via WP11 surface).
- **Edge cases**: GC/archive with nothing eligible (no-op, clear message); confirm a `sync now` immediately
  before/after leaves source events intact.

### Subtask T074 – Wire EventSyncConfig mode selection → WP09
- **Purpose**: Let operators select the retention × delivery mode (TEAMSPACE / EXTERNAL_RECEIVER /
  LOCAL_RETENTION / OPT_OUT) via the CLI, routing to WP09 (**FR-006** surface; US2).
- **Steps**:
  1. Add the mode-selection surface (e.g. `sync config` to read/show current mode, plus mode flags as the
     design dictates) that reads/writes `EventSyncConfig` through WP09's `delivery/config.py`. The CLI does
     not encode preset semantics — WP09 owns mode → (receiver, retention) resolution.
  2. Surface the active mode in `sync status` output (read-only) so operators can see how event sync behaves
     (US2 observability).
  3. Reject/route invalid mode tokens through WP09's validation rather than the CLI second-guessing.
- **Files**: `src/specify_cli/cli/commands/sync.py`.
- **Parallel?**: No.
- **Validation**:
  - [ ] Mode selection reads/writes via WP09 only.
  - [ ] Active mode is visible in status.
  - [ ] Invalid mode handled via WP09 validation.
- **Edge cases**: switching to `LOCAL_RETENTION` then `sync now` attempts no delivery; `OPT_OUT` of a
  Teamspace-bound family is refused/audited by WP09 (CLI surfaces the refusal, does not silently drop —
  C-008); switching to `EXTERNAL_RECEIVER` without a configured endpoint surfaces WP09's error.

### Subtask T075 – Preserve backward-compatible behavior of existing flags/output (NFR-006)
- **Purpose**: Existing `sync` flags and output keep working; existing stats/status consumers keep working
  with clarified semantics (**NFR-006**).
- **Steps**:
  1. Inventory the current `sync` subcommands/flags before editing (read `cli/commands/sync.py` and the
     `mvp-cli-sync-boundary-completion` status contract). Preserve their names, output fields, and exit codes.
  2. Additive only: new subcommands/flags add behavior; they do not rename or remove existing ones. The
     existing body-upload counts and identity-boundary output remain (C-006).
  3. Where semantics are clarified (e.g. delete-on-success becomes ledger-on-success behind `sync now`), the
     *output surface* a legacy consumer reads stays stable; only the underlying behavior changed in WP07.
- **Files**: `src/specify_cli/cli/commands/sync.py`.
- **Parallel?**: No.
- **Validation**:
  - [ ] Every pre-existing `sync` flag/subcommand still resolves and behaves compatibly.
  - [ ] Existing output fields/exit codes preserved.
- **Edge cases**: a script parsing the old `sync status` output still finds its fields; old `--check`
  consumers still get the documented exit codes.

### Subtask T076 – Terminology Canon (no `feature*` aliases)
- **Purpose**: Enforce the Terminology Canon on every new CLI surface (**project guideline**).
- **Steps**:
  1. Review every new flag, subcommand name, JSON key, help string, and message added in T071–T075 for
     `feature` / `feature*` wording; replace with "Mission" or the event/journal/target/delivery vocabulary.
  2. Do not introduce `feature*` aliases for any new param/route/field/flag/env var/command.
  3. Before handoff, run the terminology guard (this WP touches user-facing CLI prose):
     `PWHEADLESS=1 .venv/bin/pytest tests/architectural/test_no_legacy_terminology.py -q`.
- **Files**: `src/specify_cli/cli/commands/sync.py` (plus the test file's strings).
- **Parallel?**: No — a final sweep over the surfaces the other subtasks add.
- **Validation**:
  - [ ] No `feature*` token in any new flag/command/field/help text.
  - [ ] `tests/architectural/test_no_legacy_terminology.py` passes.
- **Edge cases**: help text and error messages count as user-facing prose — sweep them too.

### Subtask T077 – Tests (observable CLI output, not call order — NFR-001)
- **Purpose**: Prove the wiring via observable CLI behavior and resulting on-disk/ledger state in
  `tests/cli/commands/test_sync_commands.py`.
- **Steps**:
  1. Use the CLI test harness (Typer `CliRunner` / the project's existing CLI test pattern) to invoke each
     subcommand and assert on **printed output** and **on-disk/ledger state**, never on internal call order
     or mock invocation sequence (NFR-001).
  2. **`sync now`**: produce events, run it, assert the printed summary and that ledger rows were written and
     journal rows were NOT deleted.
  3. **`sync server <url>` + replay (FR-005, US1)**: set target A, `sync now`, assert delivered to A and
     still retained; set target B, `sync now`, assert same events delivered to B.
  4. **`sync status` / `--check --json`**: assert old top-level fields AND the seven additive sections appear;
     assert distinct retained / current / previous / terminal-failed / body-upload counts.
  5. **`sync gc` / `sync archive`**: assert explicit-only behavior — a `sync now` does not delete; the
     explicit command archives/purges and ledger history survives.
  6. **`sync config` / mode**: assert each mode's observable on-disk + network behavior via the CLI
     (LOCAL_RETENTION journals-no-post; OPT_OUT refuses/audits Teamspace-bound).
  7. **Backward-compat (NFR-006)**: assert a pre-existing flag still works and old output fields persist.
- **Files**: `tests/cli/commands/test_sync_commands.py` (in `owned_files`).
- **Parallel?**: No.
- **Validation**:
  - [ ] All subcommands covered by observable-output assertions.
  - [ ] No test asserts internal call order / mock call sequence.
  - [ ] Replay (A→B), explicit-GC, and mode behaviors asserted on state, not internals.
- **Edge cases**: invoking commands with no events / no configured target; JSON parse of `--check --json`
  output succeeds and contains all sections.

## Test Strategy

- Mandatory file: `tests/cli/commands/test_sync_commands.py`.
- Command: `PWHEADLESS=1 .venv/bin/pytest tests/cli/commands/test_sync_commands.py -q`.
- These are CLI-harness tests over in-process domain objects + a stub receiver (WP06) — they do NOT need real
  ports/daemon, so they run fine under `-n auto --dist loadfile`. If any test ends up exercising a real
  daemon/port path, isolate it into a serial `-n0` case (per the parallel-test rules) — but the wiring tests
  here should stay in-process.
- Use the stub receiver (no Teamspace credentials) so the suite passes in fork CI (SC-005) and asserts
  delivery via the stub's recorded state.
- Before handoff also run: `PWHEADLESS=1 .venv/bin/pytest tests/architectural/test_no_legacy_terminology.py -q`
  (T076 guard), and `.venv/bin/ruff check src/specify_cli/cli/commands/sync.py` + `.venv/bin/mypy` with zero
  issues.

## Risks & Mitigations

- **Logic creep into the CLI (single-owner / thin risk, plan IC-08)**: the join point tempts you to compute
  counts, map outcomes, or derive scope here. *Mitigation*: all logic stays in WP07/WP09/WP10/WP11; the CLI
  resolves handles and prints results. Reviewer checks for any loop/mapping/count math in `sync.py`.
- **Breaking existing consumers (NFR-006)**: renaming a flag or dropping an output field. *Mitigation*:
  inventory-first (T075), additive-only, backward-compat test.
- **Body-upload/journal conflation (C-006)**: surfacing body-upload counts as journal counts. *Mitigation*:
  emit WP11's `body_upload_compatibility` section verbatim; never relabel.
- **Terminology regression (CI-only gate)**: forbidden-term checks run in CI's integration job. *Mitigation*:
  run the terminology guard locally before push (T076).
- **Dependency join ordering**: WP12 depends on WP07/WP09/WP10/WP11; build against their public surfaces and
  do not start before they land (it is the documented join point).

## Review Guidance

A reviewer for `/spec-kitty.review` must verify:

- `sync.py` is wiring only — no event-selection loops, outcome mapping, count computation, or scope
  derivation lives in the CLI (single-owner / thin-CLI invariant).
- `sync now` → WP07 dispatcher; `sync server` → WP01 target authority; replay to a new target works (FR-005).
- `sync status` / `--check --json` emit old top-level fields PLUS the seven WP11 sections; exit codes
  unchanged (FR-009, FR-019, NFR-006).
- `sync gc` / `sync archive` are explicit-only and preserve ledger history; no automatic path deletes source
  events (FR-010, US4 scenario 3).
- Mode selection routes through WP09; OPT_OUT of Teamspace-bound is refused/audited, not silently dropped.
- No `feature*` aliases in any new surface; terminology guard passes (T076).
- Tests assert observable CLI output + on-disk/ledger state, not internal call order (NFR-001), and run
  against the stub receiver with no Teamspace credentials (SC-005).

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T10:17:43Z – claude:opus:python-pedro:implementer – shell_pid=84575 – Assigned agent via action command
- 2026-06-29T10:50:13Z – claude:opus:python-pedro:implementer – shell_pid=84575 – for_review (propagate; lane pristine at d166808eb)
- 2026-06-29T10:50:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=88547 – Started review via action command
- 2026-06-29T10:57:20Z – user – shell_pid=88547 – Review passed: live CLI callers confirmed end-to-end (sync app mounted at cli/commands/__init__.py:231). dispatch()<-sync now; build_status_report()<-sync status[/--check --json]; gc_payloads/archive_payloads<-sync gc/archive; EventSyncConfig/Mode.from_token/.resolve<-sync mode. FR-005 replay PASS; FR-009/019 additive 7 sections + legacy fields PASS; FR-010 explicit-only retention PASS; A7 sync mode <TOKEN> persisted under [event_sync], invalid token rejected via WP09 PASS. Backward-compat: 51 cli -k sync + 26 WP12 tests green. Thin CLI, NFR-001 observable-state tests. ATDD red->green (996886f02 precedes d166808eb). Terminology clean; guard passes. mypy+ruff clean. --force used: kitty-specs lane guard (dependency-lane merge artifacts).
- 2026-06-29T10:58:08Z – user – shell_pid=88547 – Approved by reviewer-renata (on record): live CLI callers confirmed, backward-compat green. Propagating.
