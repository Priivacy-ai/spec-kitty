# Charter E2E #827 Follow-ups (Tranche A)

| Field | Value |
|---|---|
| Mission | charter-e2e-827-followups-01KQAJA0 |
| Mission ID | 01KQAJA02YZ2Q7SH5WND713HKA |
| Mission type | software-dev |
| Target branch | main |
| Suggested feature branch | `fix/charter-e2e-827-followups` |
| Closes (when this PR lands) | #844, #845, #846, #848 |
| Related, remains open | #827 (umbrella epic — only fully closed when broader acceptance is met) |
| Related, already closed | #847 (intentionally out of scope) |
| Superseded references | PR #855 (closed, superseded by PR #864 — historical reference for #844 only) |

## Purpose

### TLDR

Close out the #827 epic's immediate follow-up tranche by fixing four mission-blocking defects (#844, #845, #846, #848) so charter E2E and review gates stay reliable.

### Context

The #827 charter golden-path epic landed in Tranche 2 (PR #864), but four follow-up issues were intentionally deferred. Until they ship, charter E2E coverage permits null prompt paths, dossier snapshots can self-block status transitions, specify/plan can declare success without committing real mission content, and review gates can fail on environment drift. This mission closes those four gaps as a single stabilization PR before #822 backlog work begins.

## User Scenarios & Testing

### Primary actor

Spec Kitty maintainers and downstream agent operators who run the charter golden-path E2E, drive missions through the standard lifecycle (specify → plan → tasks → implement → review → merge), and depend on review gates being trustworthy.

### Primary scenario — review-gate hygiene (#848 first)

1. Maintainer pulls latest `main` and prepares to review or open a PR.
2. They run a single documented pre-review/pre-PR command that brings the installed environment into agreement with `uv.lock`.
3. They run review-gate checks. Drift between `uv.lock` and the installed `spec-kitty-events` (or any other shared package whose compatibility-range vs exact-pin contract is governed by `uv.lock`) is detected automatically and blocks the gate with an actionable message.
4. With drift resolved, the review gate passes for legitimate reasons only — no false failures, no false passes.

### Primary scenario — charter E2E mandates a real prompt file (#844)

1. An agent runs `spec-kitty next --json` for a mission whose runtime emits an issued composed step.
2. The JSON exposes a stable, public path to the prompt file under a documented field name (existing `prompt_file` if that is the contract, or another documented public field).
3. The path value is non-null, non-empty, and refers to a file that exists on disk.
4. If for any reason a runtime step is not actionable, the JSON returns `kind=blocked` with a reason — never `kind=step` with a missing or null prompt path.
5. `tests/e2e/test_charter_epic_golden_path.py` enforces all of the above and fails loudly if any issued `kind=step` has a null/empty/non-resolving prompt path.

### Primary scenario — dossier snapshots do not self-block transitions (#845)

1. An agent runs a mission command that updates `.kittify/dossiers/**/snapshot-latest.json` as a side effect (for example a status-aware command, mission action, or status-transition pre-flight).
2. The snapshot write either is tracked/staged/committed automatically as a mission artifact, or it lives in a location that is excluded from the worktree dirty-state check used by `agent tasks move-task` and related transitions — based on a single documented ownership policy.
3. Subsequent calls to `agent tasks move-task` and related lane transitions do not fail with a self-inflicted dirty-state error caused by the snapshot the same command just wrote.
4. Regression coverage exercises the exact pre-flight path that previously blocked, so the defect cannot silently return.

### Primary scenario — specify/plan commit boundary (#846)

1. An agent runs `/spec-kitty.specify` (or `/spec-kitty.plan`) and the command produces or updates `kitty-specs/<mission_slug>/spec.md` (or `plan.md`).
2. If the produced content is substantive (real spec/plan content, not just template scaffolding), the workflow auto-commits the populated file(s) to the target branch.
3. If the produced content is empty, template-only, or otherwise non-substantive, the workflow does not silently auto-commit a "success" state. Instead, it either blocks with a clear, actionable message or surfaces a documented prompt that requires the agent to commit substantive content explicitly.
4. Workflow state never reports a spec or plan phase as complete while substantive content is still untracked or uncommitted.
5. Regression coverage or workflow documentation makes the commit boundary explicit so future templates cannot drift back into the silent-commit-of-empty-content failure mode.

### Edge cases & exception paths

- `uv.lock` is fully in sync with installed packages → review gate passes with no friction.
- `uv.lock` and installed `spec-kitty-events` differ → review gate fails with the documented sync command in the error output.
- A mission's `next --json` legitimately has no actionable step → returned `kind` is `blocked` (or another non-`step` kind) with a reason; E2E still passes.
- `agent tasks move-task` is invoked when the worktree has unrelated dirty state → it still rejects, as today; this mission only removes the self-inflicted snapshot-induced dirty state.
- `/spec-kitty.specify` is invoked with no description on a mission that already has substantive content → existing content is not silently overwritten; commit boundary still holds.
- A document-only mission (no code) reaches the commit boundary → spec.md/plan.md are still substantive prose, so the boundary still passes.

### Rules / invariants that must always hold

- A `kind=step` runtime decision **must** carry a resolvable prompt file. Null, empty, or missing-on-disk values are illegal.
- A workflow command that auto-commits **must not** auto-commit empty or template-scaffold-only content as if it were a completed phase.
- A status/transition pre-flight **must not** fail because of an artifact that the same command path just wrote, unless that policy is explicit and documented.
- The review gate **must** detect `uv.lock` vs installed-package drift before running mission-review checks that are sensitive to it, and **must** name the offending package(s) and the documented sync command in its error output.
- All four fixes share `main` as the target branch and ship as a single PR.

## Domain Language (canonical terms)

| Term | Canonical meaning in this mission |
|---|---|
| Issued composed step | A `next --json` decision with `kind=step` for which the runtime has selected an actionable composed-step prompt. Must always have a resolvable prompt file. |
| Prompt file | The on-disk file path the agent reads as the prompt body for an issued composed step. Exposed via a stable public field in `next --json` output. |
| Dossier snapshot | The `.kittify/dossiers/**/snapshot-latest.json` artifact written by status-aware mission commands. |
| Self-inflicted dirty state | A worktree dirty-state condition caused by an artifact the same command path just wrote, which then blocks that command path's own follow-up step. |
| Substantive mission content | Spec or plan content that materially expresses requirements/design beyond the empty template scaffolding produced by `mission create`. |
| Pin drift | A divergence between the exact pins recorded in `uv.lock` and the versions actually installed in the environment running the review gate, specifically for shared packages whose contract is governed by `uv.lock`. |
| Review gate | The automated checks (CI and/or local pre-PR) that gate mission-review approval and PR-readiness. |

## Functional Requirements

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-001 | The review-gate path **must** include an automated check that fails when `uv.lock` and the installed `spec-kitty-events` package (and any other shared package whose pin contract is governed by `uv.lock`) disagree, before running mission-review checks that are sensitive to that drift. | P0 | Draft |
| FR-002 | A single documented pre-review/pre-PR command **must** exist that brings the installed environment into agreement with `uv.lock`. The command name and invocation **must** appear in the failure output of the FR-001 check. | P0 | Draft |
| FR-003 | Any existing issue-matrix or status row that currently labels environment/pin-drift hygiene as "verified-already-fixed" **must** be corrected to reflect the real status if the underlying risk still exists. | P1 | Draft |
| FR-004 | `spec-kitty next --json` **must** expose a stable, documented public field that gives the on-disk path to the prompt file for an issued composed step (`kind=step`). | P0 | Draft |
| FR-005 | The value emitted by FR-004 for an issued `kind=step` **must** be non-null, non-empty, and **must** resolve to an existing file on disk. | P0 | Draft |
| FR-006 | When a runtime decision is not an actionable step, `next --json` **must** return a non-`step` kind (for example `kind=blocked`) with a reason, instead of returning `kind=step` with a missing or null prompt path. | P0 | Draft |
| FR-007 | `tests/e2e/test_charter_epic_golden_path.py` **must** assert that for every issued `kind=step` decision the prompt path field is present, non-null, non-empty, and that `Path(prompt).is_file()` returns true. | P0 | Draft |
| FR-008 | Host-facing guidance and runtime documentation **must** be updated to remove any text that legitimizes a null/missing prompt path for `kind=step`; that contract is illegal. | P1 | Draft |
| FR-009 | Mission commands that update `.kittify/dossiers/**/snapshot-latest.json` **must** follow a single documented ownership policy: either (a) automatically track/stage/commit the snapshot as a mission artifact, or (b) write it to a location that is excluded from the worktree dirty-state check used by `agent tasks move-task` and related transitions. | P0 | Draft |
| FR-010 | After FR-009 is in effect, `agent tasks move-task` and related status transitions **must not** fail with a dirty-state error caused solely by a dossier snapshot that the same command path just wrote. | P0 | Draft |
| FR-011 | Regression coverage **must** exercise the exact pre-flight path that previously blocked on dossier-snapshot-induced dirty state, so the defect cannot silently return. | P0 | Draft |
| FR-012 | `/spec-kitty.specify` and `/spec-kitty.plan` workflows **must** auto-commit `spec.md` (and `plan.md` for plan) only when the file content is substantive — that is, materially beyond the template scaffolding produced by `mission create`. | P0 | Draft |
| FR-013 | When the produced content is empty or template-scaffold-only, the workflow **must** either block with a clear, actionable message or surface a documented prompt that requires the agent to commit substantive content explicitly. The workflow **must not** silently auto-commit a "success" state. | P0 | Draft |
| FR-014 | Workflow status reporting **must not** indicate that a spec or plan phase is complete while substantive content for that phase is still untracked or uncommitted on the target branch. | P0 | Draft |
| FR-015 | Regression coverage or explicit workflow documentation **must** define the commit boundary in FR-012 / FR-013 / FR-014 so future templates and commands cannot drift back into the silent-commit-of-empty-content failure mode. | P0 | Draft |
| FR-016 | The PR that lands this mission **must** explicitly state in its body: that it fixes #844, #845, #846, #848 (as applicable); that #847 is closed and intentionally out of scope; that #827 remains open unless the broader epic acceptance is fully met; and that PR #855 was superseded by PR #864 and was not merged. | P1 | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The new `uv.lock` vs installed-package drift check (FR-001) **must** complete in under 5 seconds on a developer laptop on a clean install. | < 5s wall time on a clean install | Draft |
| NFR-002 | The drift-check error output (FR-001 / FR-002) **must** name the offending package(s) and include the exact pre-PR sync command. | Output explicitly contains both pieces of information | Draft |
| NFR-003 | All affected verification commands **must** be green on the merging branch before PR closeout: `uv lock --check`; `PWHEADLESS=1 uv run pytest tests/e2e/test_charter_epic_golden_path.py -q`; `uv run pytest tests/contract/test_cross_repo_consumers.py -q`; `uv run pytest tests/next -q`; `uv run pytest tests/specify_cli/cli/commands/agent -q`; `uv run pytest tests/integration -k 'dossier or move_task or dirty or transition' -q`; `uv run pytest tests/integration -k 'specify or plan or auto_commit or mission' -q`. | 100% pass on the listed commands | Draft |
| NFR-004 | New code added by this mission **must** meet the project's standing quality bars: `mypy --strict` passes with no new type errors, and new logic carries unit/integration tests sufficient to keep the project's coverage gate satisfied. | `mypy --strict` clean; coverage gate satisfied | Draft |

## Constraints

| ID | Constraint | Rationale | Status |
|---|---|---|---|
| C-001 | All work in this mission **must** target `main` and ship as a single stabilization PR on a feature branch (suggested `fix/charter-e2e-827-followups`). The four fixes **must not** be split across separate PRs. | Closing the four #827 follow-ups as one tranche is the explicit operator intent and reduces interleave risk with #822 backlog work. | Active |
| C-002 | #847 is **out of scope**. Do not include it in this tranche unless a new repro appears within this mission's window. | The issue is already closed. | Active |
| C-003 | This mission **must not** start the #822 stabilization backlog (#771, #726/#728/#729, #303/#662/#595, #260/#253/#631/#630/#629/#644/#317). That work belongs on a separate `release/3.2.0a7-stabilization-backlog` branch after this PR lands or is explicitly deferred. | Keeps blast radius bounded and matches the operator's tranche ordering. | Active |
| C-004 | The #848 fix **must** stay scoped as environment/review-gate hygiene and drift detection. It **must not** evolve into a broader dependency-management redesign (no replacement of `uv.lock`, no new package-management abstractions, no changes to compat-range vs exact-pin policy in `pyproject.toml`). | The defect is a missing hygiene check, not a flawed dependency model. Scope creep here would block the tranche and conflict with the existing shared-package-boundary contract. | Active |
| C-005 | The #844 fix **must not** weaken the existing `kind=step` contract by making the prompt field optional. A blocked or non-actionable runtime state must use a non-`step` kind. | Preserves the invariant that issued composed steps always carry an executable prompt. | Active |
| C-006 | The #845 fix **must** pick exactly one ownership policy for dossier snapshots (track/stage/commit OR exclude from dirty-state) and document it. It **must not** introduce a runtime branch where both policies apply conditionally. | A single policy keeps the worktree dirty-state contract auditable and prevents a recurrence vector. | Active |
| C-007 | The #846 fix **must not** silently delete or rewrite existing substantive content. It must only change the auto-commit decision boundary and the surfaced workflow state. | Avoids data-loss regressions for missions already in flight. | Active |
| C-008 | PR #855 is closed/superseded by PR #864 and **must not** be merged wholesale. It may be consulted as historical reference for #844 only. | Operator-stated; #855 has already been replaced upstream. | Active |

## Success Criteria

1. The four follow-up issues #844, #845, #846, #848 are closed by the PR that lands this mission, with `Closes #844`, `Closes #845`, `Closes #846`, `Closes #848` (or equivalent GitHub-recognized syntax) in the PR body.
2. On a clean checkout of the merged `main`, all of the verification commands listed in NFR-003 pass on the first run, with no manual setup beyond the documented pre-review/pre-PR sync command.
3. The charter golden-path E2E test fails fast and clearly when any issued `kind=step` has a null/empty/non-resolving prompt path — verified by running the test against an intentionally broken fixture during review.
4. After running a mission command that writes `snapshot-latest.json`, the very next `agent tasks move-task` call on the same worktree succeeds (assuming no unrelated dirty state) — verified by the FR-011 regression test.
5. `/spec-kitty.specify` and `/spec-kitty.plan` against an empty/template-only state do not auto-commit a success; the agent receives a clear, actionable signal and the workflow state does not advance — verified by the FR-015 coverage.
6. The review-gate drift check (FR-001) detects an artificially induced `uv.lock` vs installed `spec-kitty-events` mismatch and surfaces both the offending package name and the documented sync command in its error output — verified during review with a synthetic mismatch.
7. The PR body includes the closeout statements required by FR-016 (issue references, #847 out-of-scope note, #827 remains-open note, PR #855 superseded note).
8. No issue from the #822 backlog is touched by this PR.

## Key Entities

| Entity | Where it lives | Why it matters here |
|---|---|---|
| `next --json` runtime decision | Emitted by `spec-kitty next` (likely surfaced through `src/specify_cli/cli/commands/next_cmd.py`, `src/specify_cli/next/decision.py`, `src/specify_cli/next/runtime_bridge.py`) | Carries the prompt-file contract for `kind=step` (#844). |
| Charter golden-path E2E | `tests/e2e/test_charter_epic_golden_path.py` | Authoritative regression coverage for #844. |
| Dossier snapshot | `.kittify/dossiers/**/snapshot-latest.json` (writer logic in `src/specify_cli/dossier*`) | Subject of #845's worktree dirty-state interaction. |
| Status-transition pre-flight | `src/specify_cli/cli/commands/agent/tasks.py` and the `src/specify_cli/status/*` package | The pre-flight path that #845 must stop self-blocking. |
| Specify/plan workflow templates | `src/specify_cli/missions/**/command-templates/*.md`, `src/doctrine/**`, `src/specify_cli/cli/commands/agent/mission.py`, `src/specify_cli/cli/commands/agent/tasks.py` | The auto-commit decision boundary for #846. |
| Shared-package pin contract | `pyproject.toml` (compat ranges) and `uv.lock` (exact pins); CI gate at `.github/workflows/ci-quality.yml` (`clean-install-verification`); architectural enforcement under `tests/architectural/` | The drift surface for #848. |
| Issue matrix / status rows | `kitty-specs/**/issue-matrix.md` | Where stale "verified-already-fixed" labels for #848 must be corrected. |
| Cross-repo consumers contract test | `tests/contract/test_cross_repo_consumers.py` | Boundary check that must remain green; used in the #848 verification path. |
| Runtime-next skill guidance | `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` | Host-facing text that must stop legitimizing null prompts (#844). |

## Assumptions

- The four follow-ups can be diagnosed and fixed without changes to the merge engine, lane state machine, or shared-package boundary contract — i.e., the existing 3.x runtime architecture is sound and only the four named gaps are in play.
- A single drift-detection check on `uv.lock` vs installed packages (centered on `spec-kitty-events`) is sufficient hygiene; this mission does not need to invent a new dependency-management mechanism.
- The `kind=step` / `kind=blocked` taxonomy already exists in the runtime decision shape; FR-006 enforces correct use rather than introducing a new kind.
- For #845, choosing a single ownership policy (track/stage/commit vs exclude) is acceptable for the foreseeable future and does not require a runtime config switch.
- For #846, "substantive content" can be defined operationally enough (e.g., presence of mandatory sections / non-template tokens / minimum content delta from the scaffold) for a regression test or workflow guard to enforce it.
- PR #855's content remains available for inspection if useful for #844, but no part of it is required to land.

## Out of Scope (explicit)

- #847 — closed; not included in this tranche.
- The #822 stabilization backlog: #771 (stale-lane auto-rebase), #726/#728/#729 (intake papercuts), #303/#662/#595 (CI/Sonar/release-readiness cleanup), #260/#253/#631/#630/#629/#644/#317 (compatibility, Windows, encoding, install cleanup). These belong on a separate later branch.
- Any redesign of dependency management beyond the drift-detection hygiene check needed by #848 (no replacement of `uv.lock`, no new package-management abstractions, no policy changes to compat ranges vs exact pins).
- Closing #827 itself — that umbrella epic remains open unless its broader acceptance is fully complete; this mission only closes its four immediate follow-ups.
- Merging PR #855 — superseded; reference only.
- Any changes to the merge engine, lane computation, worktree creation, or status state machine.

## PR closeout (informational, derived from constraints above)

The PR that lands this mission is expected to:

- Use a feature branch off `main` (suggested `fix/charter-e2e-827-followups`).
- Include `Closes #844`, `Closes #845`, `Closes #846`, `Closes #848` (as applicable) in the PR body.
- State explicitly in the PR body that #847 is already closed and out of scope, that #827 remains open unless full epic acceptance is met, and that PR #855 was superseded by PR #864 and was not merged.
- Pass all NFR-003 verification commands on the merging branch before opening for review.
