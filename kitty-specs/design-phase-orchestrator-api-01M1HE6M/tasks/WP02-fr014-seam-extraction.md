---
work_package_id: WP02
title: FR-014 — extract next_invocation_lifecycle seam
dependencies:
- WP01
requirement_refs:
- FR-014
- NFR-001
- C-005
planning_base_branch: feat/design-phase-orchestrator-api-3837
merge_target_branch: feat/design-phase-orchestrator-api-3837
branch_strategy: Planning artifacts for this mission were generated on feat/design-phase-orchestrator-api-3837. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/design-phase-orchestrator-api-3837 unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
- T008
history: []
agent_profile: implementer-ivan
authoritative_surface: src/runtime/next/
create_intent:
- src/runtime/next/next_invocation_lifecycle.py
- tests/specify_cli/next/test_next_invocation_lifecycle_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/next_invocation_lifecycle.py
- src/specify_cli/cli/commands/next_cmd.py
- tests/specify_cli/next/test_next_invocation_lifecycle_seam.py
role: implementer
tags: []
tracker_refs: []
---

# WP02 — FR-014: extract the next-invocation lifecycle/event-log seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (unset — select at implementation time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ CHOKEPOINT — read before starting

This WP touches the **CLI ↔ runtime boundary**: `next_cmd.py`'s `--answer`
handling is live control-loop code every `spec-kitty next --answer`
invocation in this repository (and every downstream mission using this
CLI) runs through. It is the mission's obvious serialization point — not
just a dependency arrow in the WP graph, a real review chokepoint: any
regression here breaks `spec-kitty next` for every mission, not just this
one. It is also the ONLY WP whose new module (`src/runtime/next/next_invocation_lifecycle.py`)
falls under the **enforced 90%-of-changed-lines diff-coverage gate**
(`ci-quality.yml`'s `diff-coverage` job, `critical_paths` includes
`'src/runtime/next/*'`) — this WP's own tests are what that gate measures,
not a downstream WP's. Per plan.md § (l), this WP is explicitly called out
as one of the two WPs (with WP08) a reviewing squad should read FIRST AND
IN ISOLATION, before the additive verb WPs.

## Objective

Extract `_pair_previous_lifecycle_record`, `_emit_mission_next_invoked`,
and `_write_issuance_lifecycle_record` — currently private, inlined in
`next_cmd.py`'s `--answer` handling — into a new shared, public module
`src/runtime/next/next_invocation_lifecycle.py`, so both the host CLI
(`next_cmd.py`, this WP) and orchestrator-api's future `answer-decision`
verb (WP08, strictly after this WP) can call the SAME functions. This is a
**pure, behaviour-preserving move**, per operator ruling SPEC-FRESH2-001
(`reviews/spec.ruling.md`) and spec constraint C-005 — never a redesign,
never duplicated logic.

## Context

Per operator ruling SPEC-FRESH2-001: an `answer-decision` verb built only
from the two engine calls (`answer_decision_via_runtime` +
`decide_next`/`decide_next_via_runtime`) would look byte-identical to the
CLI's own response while silently failing to advance the mission's event
log or lifecycle-record store — a documented boundary violation replaced
by a worse, silent behavioural divergence. The operator ruled: reach the
three side effects through a seam extracted from `next_cmd.py`, never by
inlining or duplicating them into the orchestrator-api layer. This WP
builds that seam; WP08 (hard-gated on this WP) is the only consumer this
mission adds.

**Target module decision (plan.md § (a), do not re-derive)**: new file
`src/runtime/next/next_invocation_lifecycle.py`, top-level under
`src/runtime/next/` — a sibling of `runtime_bridge.py` and `decision.py`,
**NOT** under `_internal_runtime/` (reserved for internalized
former-`spec-kitty-runtime`-package DAG-engine re-exports, confirmed by
that subpackage's own module docstrings — grepping it for
`lifecycle_record`/`issuance` returns zero matches, i.e. no existing
natural home there). **NOT** `src/specify_cli/orchestrator_api/` — that
would be exactly the "inline into the orchestrator-api layer" the operator
ruling rejected. Precedent for this placement: `decision.py:33` already
imports `specify_cli.mission_metadata.mission_identity_fields`,
`decision.py:188` already imports
`specify_cli.mission_v1.events.read_events` (the READ counterpart of the
very `emit_event` call `emit_mission_next_invoked` needs), and
`runtime_bridge.py:319` already imports
`specify_cli.mission_metadata.resolve_mission_identity` — `runtime.next`
modules already freely import `specify_cli.*` domain modules; this
module's own placement follows that existing pattern.

**Extracted function signatures** (module-level, public — carried over
verbatim from the current private functions; same parameters, same
best-effort/fail-closed semantics — this is a pure move, not a redesign):

```python
# src/runtime/next/next_invocation_lifecycle.py
def pair_previous_lifecycle_record(
    agent: str, mission_slug: str, result: str, repo_root: object,
    *, effective_root: Path | None = None,
) -> None: ...

def emit_mission_next_invoked(
    agent: str, result: str, mission_slug: str, repo_root: object,
    decision: object, *, effective_root: Path | None = None,
) -> None: ...

def write_issuance_lifecycle_record(
    agent: str, mission_slug: str, repo_root: object, decision: object,
    *, effective_root: Path | None = None,
) -> None: ...
```

**Current call sites to replace** (`next_cmd.py:244-269`, inside the
`--answer` handling path, AFTER `_validate_result_and_answer`/
`_maybe_handle_answer` at `next_cmd.py:211-220` and BEFORE the function
returns):

```
next_cmd.py:244  _pair_previous_lifecycle_record(...)   # BEFORE decide_next
next_cmd.py:248-250  decision = decide_next(...)         # unchanged — the
                                                           # engine call itself,
                                                           # not part of the seam
next_cmd.py:251-258  _emit_mission_next_invoked(...)      # AFTER decide_next
next_cmd.py:263-269  _write_issuance_lifecycle_record(...)  # AFTER, only when
                                                              # decision.kind == "step"
                                                              # (check the existing
                                                              # conditional guard,
                                                              # preserve it exactly)
```

`next_cmd.py`'s three functions currently defined at `next_cmd.py:333`
(`_pair_previous_lifecycle_record`), `next_cmd.py:430`
(`_write_issuance_lifecycle_record`), `next_cmd.py:863`
(`_emit_mission_next_invoked`) become thin callers of the new module (or
are deleted entirely if nothing else in `next_cmd.py` calls the private
versions — verify with a repo-wide grep before deleting).

**SC-008 shared regression test helper (this WP's own deliverable,
extended unmodified in shape by WP08 — plan.md § (a))**:

```python
def assert_lifecycle_seam_effects(feature_dir, repo_root, mission_slug, run_action) -> None:
    """run_action: zero-arg callable performing the action under test.
    Agnostic to caller — a next_cmd --answer invocation here, an
    orchestrator-api answer-decision call in WP08's extension."""
```

- Reads `mission-events.jsonl` via `specify_cli.mission_v1.events.read_events`
  and asserts a `MissionNextInvoked` entry was appended after `run_action()`.
- Reads the issuance-lifecycle-record store via
  `specify_cli.invocation.lifecycle.read_lifecycle_records` and asserts
  BOTH (a) the previous `started` record was paired to a completion record,
  and (b) a NEW `started` record was written.
- Raises via a plain `assert` on the first missing/mismatched effect
  (this repo's pytest-native style — no bool return), so a failing case
  points directly at which of the three seam functions regressed.

## Subtask T004: RED — author the shared test module (fails via ImportError, not a vacuous assertion)

**Purpose**: Land a genuinely-RED, non-vacuous ATDD test BEFORE the seam
module exists.

**Steps**:
1. Create `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py`
   with a **module-level, top-of-file import** of the not-yet-existing
   module: `from runtime.next.next_invocation_lifecycle import (
   pair_previous_lifecycle_record, emit_mission_next_invoked,
   write_issuance_lifecycle_record )`. Because the module does not exist
   yet, this import raises `ModuleNotFoundError` at COLLECTION time — the
   whole test file fails to load. **This is the genuine RED**, not an
   assertion failure: it exercises real, not-yet-built behavior (per the
   ATDD-first discipline's own bar — "a WP whose ATDD test cannot fail
   first, e.g. it only asserts a symbol exists, is a decomposition
   defect"). A test that merely called the EXISTING `next_cmd --answer`
   path and checked side effects would NOT be RED pre-WP02 (the inline
   implementation already produces those side effects today) — that
   vacuous-test trap is explicitly why the import itself, not a behavioral
   assertion, is this WP's RED signal.
2. In the same file, define `assert_lifecycle_seam_effects(...)` per the
   contract above.
3. Add one test function exercising the CLI path: drive a fixture mission
   to a `decision_required` state (reuse this repo's existing fixture-mission
   helpers from `tests/specify_cli/next/conftest.py` or sibling
   `test_runtime_bridge_composition.py`/`test_next_output_preservation.py`
   test setup, whichever this repo's existing fixtures already provide —
   do not hand-roll a new fixture-mission builder if one already exists),
   invoke `spec-kitty next --answer <value> --decision-id <id> --agent
   <name> --result success` as `run_action`, and call
   `assert_lifecycle_seam_effects(...)` against it.
4. Mark the module `pytestmark = pytest.mark.integration` (add
   `pytest.mark.git_repo` too if the fixture-mission setup performs a real
   `git init` — check the fixture helper you reuse in step 3; match
   whichever the sibling precedent files
   (`test_runtime_bridge_composition.py`, `test_next_output_preservation.py`)
   use for the same shape of fixture). **This is non-negotiable**: this
   test does real file I/O (`mission-events.jsonl`, the
   issuance-lifecycle-record store) — it does not qualify as `fast` per
   `pytest.ini:25`'s definition ("no subprocess/git overhead"). An unmarked
   or `fast`-marked module lands in the right directory
   (`tests/specify_cli/next/`, matching the `test_runtime_bridge.py` /
   `test_runtime_bridge_dispatch.py` precedent for other
   `src/runtime/next/` top-level modules) but stays INVISIBLE to both
   coverage-emitting jobs — `fast-tests-next` runs `-m "fast and not
   windows_ci"`; `integration-tests-next` runs `-m '... and (git_repo or
   integration) ...'` — and the enforced `diff-coverage`
   `src/runtime/next/*` gate (90% floor on changed lines) would then see
   ZERO coverage for this WP's new module and fail the gate outright.
5. Commit this file alone as the RED commit. Confirm it fails collection
   (`pytest tests/specify_cli/next/test_next_invocation_lifecycle_seam.py -v`
   → `ModuleNotFoundError` / collection error) BEFORE writing any
   implementation.

**Files**: `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py` (new, ~120-180 lines).

**Validation**: `pytest tests/specify_cli/next/test_next_invocation_lifecycle_seam.py -v`
fails with a collection error on `planning_base_branch`
(`feat/design-phase-orchestrator-api-3837`, this mission's own base — the
mission topology is `single_branch`).

## Subtask T005: Create `next_invocation_lifecycle.py` (move, not duplicate)

**Purpose**: Land the seam module itself.

**Steps**:
1. Create `src/runtime/next/next_invocation_lifecycle.py`.
2. Move the THREE function bodies from `next_cmd.py` (post-T002's
   suppression fix/justification from WP01) verbatim into this new module
   as PUBLIC functions (`pair_previous_lifecycle_record`,
   `emit_mission_next_invoked`, `write_issuance_lifecycle_record` — no
   leading underscore; these are now a shared contract). Same parameters,
   same best-effort/fail-closed semantics, same imports
   (`specify_cli.invocation.lifecycle`, `specify_cli.mission_metadata`,
   `specify_cli.mission_v1.events`) — a pure relocation.
3. Add a module docstring naming this as the FR-014 shared seam, citing
   operator ruling SPEC-FRESH2-001 and this mission (`kitty-specs/design-phase-orchestrator-api-01M1HE6M`)
   for future readers.
4. Do NOT change any internal logic, error handling, or the best-effort
   `except Exception: return` patterns the original functions use — this
   WP's contract is explicitly behaviour-preserving (C-005).

**Files**: `src/runtime/next/next_invocation_lifecycle.py` (new, ~150-200 lines — three moved functions plus module docstring).

**Validation**: `mypy --strict src/runtime/next/next_invocation_lifecycle.py` passes.

## Subtask T006: `next_cmd.py` call sites become thin callers

**Purpose**: Complete the extraction — the host CLI now calls through the
seam instead of its own private copies.

**Steps**:
1. Replace the three private function bodies in `next_cmd.py` (formerly at
   `next_cmd.py:333`, `:430`, `:863`) — either delete them entirely and
   update the call sites at `next_cmd.py:244`, `:251-258`, `:263-269` to
   import and call `runtime.next.next_invocation_lifecycle`'s public
   functions directly, OR keep thin private wrappers that immediately
   delegate (choose whichever keeps the diff smallest and clearest — direct
   replacement at the call sites is the simpler, more direct option and is
   preferred unless another call site in `next_cmd.py` independently
   depends on the private names).
2. Before deleting, grep `next_cmd.py` (and the wider repo) for any OTHER
   caller of `_pair_previous_lifecycle_record` / `_emit_mission_next_invoked`
   / `_write_issuance_lifecycle_record` by name — if none exist outside the
   three call sites already cited, deletion is safe.
3. Add the import: `from runtime.next.next_invocation_lifecycle import
   pair_previous_lifecycle_record, emit_mission_next_invoked,
   write_issuance_lifecycle_record` at `next_cmd.py`'s existing import
   block (follow the precedent already in this file — `next_cmd.py:67`
   already does `from runtime.next.decision import decide_next as
   _decide_next` inside a function; match whichever import style
   — module-level vs. inline — this file already uses for `runtime.next`
   imports).
4. Preserve the EXACT conditional guard around
   `write_issuance_lifecycle_record` (`next_cmd.py:263-269` — only called
   "whenever the resulting decision's `kind == "step"`") — do not drop or
   loosen this condition.

**Files**: `src/specify_cli/cli/commands/next_cmd.py` (~30-60 line diff — net removal, since the three function bodies move out).

**Validation**: `mypy --strict src/specify_cli/cli/commands/next_cmd.py` passes; `ruff check src/specify_cli/cli/commands/next_cmd.py` passes.

## Subtask T007: GREEN — confirm the seam test passes, plus behaviour-preservation re-run

**Purpose**: Close the RED→GREEN loop and prove C-005 (zero observable
change to the host CLI's own behavior).

**Steps**:
1. Run `pytest tests/specify_cli/next/test_next_invocation_lifecycle_seam.py -v`
   — must now PASS (the import resolves, and `assert_lifecycle_seam_effects`
   observes all three side effects from the `next_cmd --answer` path).
2. Re-run the EXISTING `next_cmd.py` `--answer` test surface unmodified:
   `pytest tests/specify_cli/cli/commands/test_next_answer_effective_root.py
   tests/specify_cli/cli/commands/test_next_fail_closed.py
   tests/specify_cli/cli/commands/test_next_owned_commit_guard.py
   tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py -v`
   — must be GREEN, with ZERO changes to these test files themselves (they
   are re-run for behaviour-preservation confirmation, not edited).
3. Record any test in either run that is red for a reason OTHER than
   this WP's own change — cross-reference against WP01's baseline
   snapshot in `tracer-tooling-friction.md`; cite issue #3284 explicitly
   if it matches, otherwise stop and report per the charter's Pre-existing
   Failure Reporting Rule.

**Files**: none new — verification only.

**Validation**: All listed test files GREEN; zero diff in the four
existing `test_next_*.py` files.

## Subtask T008: Targeted architectural-boundary regression check

**Purpose**: Confirm the new `src/runtime/next/` module introduces no
retired-package import and no charter/doctrine-boundary violation.

**Steps**:
1. Run `pytest tests/architectural/test_shared_package_boundary.py
   tests/architectural/test_runtime_charter_doctrine_boundary.py -v`.
2. This is a REGRESSION check, not expected to need new assertions —
   `next_invocation_lifecycle.py` imports only `specify_cli.*` domain
   modules already proven safe by `decision.py`/`runtime_bridge.py`'s own
   existing imports (see Context above). If either test fails, that is a
   genuine finding to report, not something to silently work around.

**Files**: none new — verification only.

**Validation**: Both architectural tests GREEN.

## Write-Scope / Adjacent Open PRs

`src/runtime/next/next_invocation_lifecycle.py` (new) and
`src/specify_cli/cli/commands/next_cmd.py` are not touched by any of the
three adjacent open PRs named in this mission's tasks-authoring brief
(#3842 touches `agent_config.py`/`protection_policy.py`/
`_command_surface_doctor.py`/`charter/*`/`orchestrator.py`; #3826 touches
`orchestrator_api/commands.py`'s merge-mission area and `mission_create.py`;
#3836 touches `mission_setup_plan.py`) — no same-file rebase-risk note
applies to this WP's own files. WP08 (the only consumer of this WP's new
module) DOES carry a same-file overlap note for `orchestrator_api/commands.py`
against #3826 — see WP08's task file.

## Definition of Done

- [ ] `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py`
      committed RED first (collection failure via `ModuleNotFoundError`),
      confirmed on `planning_base_branch` before any implementation commit.
- [ ] `pytestmark = pytest.mark.integration` (+ `pytest.mark.git_repo` if
      the fixture setup does a real `git init`) set on the new test module.
- [ ] `src/runtime/next/next_invocation_lifecycle.py` created with the
      three public functions, signatures unchanged from the originals.
- [ ] `next_cmd.py`'s three call sites (`:244`, `:251-258`, `:263-269`)
      now call the seam module; the private function definitions are
      removed or reduced to thin delegating wrappers.
- [ ] `assert_lifecycle_seam_effects` lands in the shared test module,
      exactly matching the signature `plan.md` § (a) pins — WP08 imports
      this helper unmodified, so its shape must not change without
      coordinating with WP08's author.
- [ ] Seam test GREEN; existing 4 `test_next_*.py` files GREEN with zero
      diff; targeted architectural tests GREEN.
- [ ] `mypy --strict` and `ruff check` clean on both changed/new files.
- [ ] Commits: RED test commit, then implementation commit(s) — ATDD-first.

Run: `spec-kitty agent action implement WP02 --agent <name>`

## Risks

- **Silent behavioral drift during the move**: copy-paste errors during
  extraction (wrong parameter order, dropped `effective_root` kwarg,
  altered exception handling) would silently change `next_cmd.py`'s own
  behavior — this is exactly what T007's unmodified re-run of the existing
  4 test files is designed to catch. Treat any diff in their outcome as a
  blocking regression, not a "probably fine."
- **Diff-coverage gate miss**: if the new test module's marker is wrong
  (missing `integration`, or accidentally `fast`), the diff-coverage gate
  will silently see zero coverage for the new module and fail — this is
  the single most likely mechanical mistake in this WP; double-check the
  `pytestmark` line before committing.
- **WP08 hard dependency**: WP08 cannot even begin drafting its RED test
  until this WP's module exists on the branch — communicate completion
  promptly if WPs are being coordinated across separate agents/lanes.

## Reviewer Guidance

- This is one of the two WPs (with WP08) plan.md recommends reading FIRST
  AND IN ISOLATION — verify the RED commit genuinely fails via
  `ModuleNotFoundError`, not a passing-then-retrofitted test.
- Confirm the extraction is a byte-for-byte behavioral move: diff the
  moved function bodies against `next_cmd.py`'s pre-WP02 versions (via
  `git log -p` on the WP01 commit) — any logic change beyond the
  suppression fix from WP01 is out of scope for this WP.
- Confirm `assert_lifecycle_seam_effects`'s signature matches plan.md § (a)
  exactly — WP08 depends on this shape being stable.
- Confirm the `pytestmark` on the new test module and re-verify against
  live `ci-quality.yml` job definitions (`fast-tests-next`,
  `integration-tests-next`) rather than trusting this file's own citation.
