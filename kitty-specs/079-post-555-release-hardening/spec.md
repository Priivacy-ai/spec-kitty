# Specification: 3.1.1 Post-555 Release Hardening

**Mission ID**: 079-post-555-release-hardening
**Mission Type**: software-dev
**Status**: Draft (output of `/spec-kitty.specify`)
**Owner**: @robertdouglass
**Branch contract**: planning_base = `main` · merge_target = `main`
**Baseline**: PR #555, merge commit `f3d017f663fa0a19aad686e58876d23b47cc60e7`, merged 2026-04-09 06:05:40 UTC
**GitHub meta-issue**: #566
**Working repo**: `/tmp/311/spec-kitty` — every example and validation step in this spec assumes that path

---

## 1. Problem Statement

PR #555 unblocked the most acute crash-class bugs in the post-#555 product surface (planning/code dependency mixing in review-context resolution, ephemeral query-mode `run_id` leak, and tracked-mission terminology drift), and added regression coverage for those fixes. Those changes are now `main` and are the new baseline for `3.1.1`.

`3.1.1` cannot ship on top of #555 alone. The product still has structural incoherences in **forward** flows — fresh `init`, new mission creation, task finalization, lane computation, credential refresh, the canonical implementation entrypoint advertised to new users, and release-cut version alignment — that surface immediately to any user who picks up `3.1.1` from a clean state. These are not historical archaeology problems. They are present in fresh runs of the current code on `main` today, and they make `3.1.1` incoherent as a release.

This mission specifies the **single, decisive** body of work needed to close those forward-correctness gaps and make `3.1.1` releasable. It is intentionally narrow: it does not redesign the planning manifest, does not sweep historical mission identity collisions, does not repair `kitty-specs/**` archaeology, and does not stabilize SaaS / dashboard parity (a CLI-only stabilization release was the explicit operator decision for `3.1.1`).

The mission is also intentionally **forward-correctness only**. Existing repositories with broken historical mission artifacts are tolerated. The goal is that fresh projects, new missions, active mission/runtime flows, the current CLI, the current auth/sync surface, and the release-cut dogfooding of the working repo (`/tmp/311/spec-kitty`) at `3.1.1` are all coherent. Nothing more.

---

## 2. Goals

| ID | Goal |
|----|------|
| G-1 | A new user can run `spec-kitty init <name> --ai <agent> [--non-interactive]` against a fresh empty directory and end up with a coherent project that does not carry git/state side-effects from the older bootstrapper, and whose printed next-step guidance names the `spec-kitty next` loop and the `spec-kitty agent action implement/review` per-decision verbs (per D-4). |
| G-2 | A user running `spec-kitty agent mission finalize-tasks` (and the slash-command equivalents) on freshly authored task content does not silently lose intended parallelism due to producer-side dependency inference bleeding past the final WP section. |
| G-3 | A user creating a new mission gets a canonical, collision-free identity (`mission_id`) at creation time, and no machine-facing flow added or stabilized in `3.1.1` relies on numeric prefix uniqueness for correctness. |
| G-4 | Lane computation handles planning-artifact work packages **identically** to other work packages from a producer/consumer-contract perspective; the product has exactly one canonical model for where planning-artifact WPs live. |
| G-5 | A user with background sync enabled cannot be silently logged out by a concurrent credential refresh race triggered by rotated refresh tokens. |
| G-6 | New users running `init` and reading the printed help / `init` output / README / help text are directed to the `spec-kitty next` loop (loop entry) and the `spec-kitty agent action implement` / `spec-kitty agent action review` per-decision verbs as the canonical user workflow. Top-level `spec-kitty implement` is not taught or advertised as a canonical user-facing entrypoint and is treated as internal infrastructure (an implementation detail of `spec-kitty agent action implement`). The command remains runnable as a compatibility surface for direct invokers but is no longer part of the new-user product surface for `3.1.1`. |
| G-7 | At the `3.1.1` release commit, `pyproject.toml` and `.kittify/metadata.yaml` report the same project version, and a fresh clone of the release tag can run every advertised core command without version-mismatch failure. |

---

## 3. Non-Goals (Out of Scope)

The following are intentionally OUT OF SCOPE for this mission and for `3.1.1`. They MAY be picked up in a later release but are not blockers for `3.1.1`. Any in-scope work that drifts into these areas is a scope violation and MUST be rejected at review.

| ID | Non-Goal |
|----|----------|
| NG-1 | Historical `kitty-specs/**` archaeology, repair, or backfill of pre-#555 mission artifacts. Existing repositories with broken historical missions are tolerated. |
| NG-2 | Repository-wide sweep of `#557` (mission identity collisions in historical missions). Phase 1 only — prevent NEW collisions; do not fix old ones. |
| NG-3 | Full redesign / manifest inversion for `#525`. Only the narrow producer-side hotfix is in scope. |
| NG-4 | Merge interruption / idempotency recovery work from `#416` unless explicitly re-scoped later. |
| NG-5 | Re-doing or extending #555 work itself. **#551, #552, and #526 are already covered by merged #555 and MUST NOT be re-spec'd here.** |
| NG-6 | SaaS / dashboard parity contract work for `#401`. `3.1.1` is a CLI-only stabilization release; #401 is intentionally deferred (D-5). |
| NG-7 | Full stabilization of top-level `spec-kitty implement` (#538, #540, #542). The command becomes a compatibility-only surface for `3.1.1`; full stabilization is not in scope. |
| NG-8 | Broad architecture cleanup that is not strictly required by the seven core tracks listed below. |

---

## 4. Locked Product Decisions

The following decisions are **locked** by this mission. Plan and implementation phases must respect them; they are not subject to "future clarification".

### D-1. Init model

A fresh `spec-kitty init <name> --ai <agent>` invocation creates project files only. It MUST NOT initialize a git repository. It MUST NOT create an initial commit on behalf of the user. It MUST NOT create `.agents/skills/` content. **There is no opt-in flag, environment variable, or config option that re-enables git side effects.** The `--no-git` flag (which existed in pre-3.1.1 versions to opt out of git initialization) is removed because it has no meaning under the new model; users passing `--no-git` after this mission lands will get a "no such option" CLI error from typer. Its printed next-step guidance MUST direct users at the `spec-kitty next` loop and the per-decision agent verbs (per D-4). The set of files it creates MUST be deterministic, enumerable from documentation, and consistent with the model the printed output describes (no surprise untracked artifacts under any model `init` advertises).

### D-2. Planning-artifact canonical model

Planning-artifact work packages are **first-class lane-owned entities**. Lane computation does NOT filter them out. Their canonical lane is the **planning lane**, which resolves to the main repo checkout (NOT a `.worktrees/<feature>-lane-X` worktree). Every downstream consumer (status events, query, review-context, implement dispatch) treats them uniformly with code WPs at the lane-contract boundary. Consumers MUST NOT branch on a "planning vs. code" type distinction at the lane boundary.

### D-3. New mission identity (Phase 1 only)

New missions mint a canonical `mission_id` at creation time, per the ADR adopted in commit `b85116ed`. Numeric prefix and slug remain as display-friendly indices but are NOT the canonical identity for any new machine-facing flow added or stabilized in `3.1.1`. Identity allocation does NOT depend on the local numeric-prefix space. Historical missions are **not backfilled** in this release (see NG-2).

### D-4. Top-level `spec-kitty implement`: de-emphasized, not stabilized

For `3.1.1`, top-level `spec-kitty implement` is **de-emphasized**. The command remains as a compatibility surface (it does NOT become a hard error and MUST continue to run for direct invokers) but is no longer the canonical path advertised to new users. After this mission lands, top-level `spec-kitty implement` is treated as **internal infrastructure** — an implementation detail of the agent-facing wrapper — not as a user-facing surface. Stabilization of #538/#540/#542 is NOT a release blocker for `3.1.1`; those issues remain open for a later release.

**The canonical post-#555 user workflow is concretely**:

1. **Loop entry** — `spec-kitty next --agent <name> --mission <slug>`. This is a top-level command (`src/specify_cli/cli/commands/next_cmd.py`) that agents call repeatedly. Each call returns a JSON decision with an `action` and a prompt file.
2. **Per-decision actions** — for an `implement` decision, the agent invokes `spec-kitty agent action implement <WP> --agent <name>`; for a `review` decision, `spec-kitty agent action review <WP> --agent <name>`. Both are registered in `src/specify_cli/cli/commands/agent/workflow.py` under typer name `action`.
3. **Internal delegation** — `spec-kitty agent action implement` may internally delegate workspace creation to top-level `spec-kitty implement`. That delegation is an implementation detail and is NOT part of the user-facing canonical contract; users and `init`/README/help text MUST NOT teach top-level `spec-kitty implement` as a step.

`init` output, project `README`, `spec-kitty implement --help` text, slash-command guidance shipped by `init`, and the getting-started portions of the `docs/` tree MUST direct users at the `spec-kitty next` loop and the `spec-kitty agent action implement/review` per-decision verbs. They MUST NOT name top-level `spec-kitty implement` as a canonical step.

### D-5. SaaS sync contract (#401): intentionally deferred

`3.1.1` is a CLI-only stabilization release. Track H / #401 is intentionally deferred. This mission MUST NOT introduce new SaaS-contract surface area. If `3.1.1` scope is later expanded to promise SaaS / dashboard parity, this decision MUST be revisited via a follow-up mission, not a quiet scope addition to 079.

---

## 5. Stakeholders & Affected Roles

| Role | Stake |
|------|-------|
| Repo maintainer (@robertdouglass) | Owns the release decision; must be able to cut `3.1.1` from this mission's outputs without manual archaeology. |
| New `spec-kitty` user | Runs `init`, expects coherent fresh project and accurate next-step guidance naming the `spec-kitty next` loop and the `spec-kitty agent action implement/review` per-decision verbs. |
| Spec author / mission operator | Runs specify/plan/finalize-tasks against fresh content; depends on planning-artifact handling, identity correctness, and parallelism preservation. |
| Background sync user | Has refresh tokens in motion; cannot tolerate spurious logouts under concurrent refresh. |
| Direct `spec-kitty implement` invoker | Existing scripts that depend on the command continue to work (compatibility surface) but the command is no longer the canonical product surface. |
| Release engineer cutting `3.1.1` | Needs version coherence between `pyproject.toml` and `.kittify/metadata.yaml` at the release commit and a clean dogfood run against `/tmp/311/spec-kitty`. |

---

## 6. User Scenarios & Acceptance Tests

### S-1: Fresh `init` in an isolated directory (Track 1)

**As** a new spec-kitty user
**I want to** run `spec-kitty init demo --ai codex --non-interactive` in a fresh empty directory
**So that** I get a coherent project with no surprise side effects.

**Then**:
- The directory contains the agent-specific files for the configured agent(s).
- No `.git/` directory was created by `init`.
- No commit titled `Initial commit from Specify template` (or any commit at all) exists.
- No `.agents/skills/` directory exists.
- The next-step guidance printed to the terminal names the `spec-kitty next` loop and the `spec-kitty agent action implement/review` per-decision verbs, and does NOT name top-level `spec-kitty implement` as a canonical user-facing entrypoint.
- Re-running `spec-kitty init demo --ai codex --non-interactive` in the same directory either is idempotent or fails fast with a clear message — never silently merging state.
- Running `spec-kitty init` inside an existing git repository does NOT touch git state.

### S-2: Fresh task finalization preserves intended parallelism (Track 4)

**As** a mission operator who has just authored `tasks.md` with explicit `dependencies:` declarations on each WP
**I want to** run `spec-kitty agent mission finalize-tasks --mission <slug>`
**So that** finalization respects my declared dependencies and does not collapse parallelism by inferring extra dependencies from prose past the final WP section.

**Then**:
- Every WP whose `dependencies:` field was explicit in source is preserved verbatim in the finalized manifest.
- The producer does not bleed prose from beyond the final WP section into the final WP's body.
- A regression test exists for the trailing-prose / parallel-eligible-final-WP false-positive case and asserts the finalized manifest preserves the parallel-eligibility.

### S-3: New mission creation mints a canonical identity (Track 3)

**As** a spec author running `/spec-kitty.specify` or `spec-kitty agent mission create`
**I want to** receive a `mission_id` in `meta.json` at creation time
**So that** new machine-facing flows can identify my mission without relying on numeric prefix uniqueness.

**Then**:
- `meta.json` contains a non-empty `mission_id` field whose value is a canonical (ADR-defined) identifier minted at creation.
- New machine-facing flows added or stabilized in `3.1.1` accept and prefer `mission_id` over numeric prefix.
- Two missions created concurrently in two checkouts of the same repository cannot collide on `mission_id`.
- Identity allocation does not depend on a local `max(prefix) + 1` scan.

### S-4: Planning-artifact WP flows end-to-end (Track 2)

**As** a mission operator whose plan generates planning-artifact work packages
**I want to** run finalize-tasks → implement dispatch → status query → review-context resolution
**So that** planning-artifact WPs flow through every consumer without special-case escape hatches at the lane boundary.

**Then**:
- Lane computation does not filter planning-artifact WPs out of its result.
- Each planning-artifact WP receives the canonical "planning lane" assignment.
- The "planning lane" resolves to the main repo checkout, not a `.worktrees/...` directory.
- Status events, query, review-context, and implement dispatch all treat planning-artifact WPs uniformly with code WPs at the lane-contract boundary.

### S-5: Concurrent credential refresh does not log the user out (Track 5)

**As** a user with background sync enabled and a refresh token in flight
**I want** two concurrent refresh attempts NOT to clear my credentials
**So that** I remain logged in across normal background-sync activity.

**Then**:
- Credential refresh holds an exclusive lock for the FULL refresh transaction (read → network call → persist), not only for file I/O operations in isolation.
- A 401 from a refresh attempt does NOT clear credentials before re-reading credentials from disk under the same lock; if the on-disk credentials have changed since the refresh started, the refresh is treated as stale and not as terminal.
- A regression test exercises two concurrent refresh attempts where one rotates the refresh token and the other races; the user remains logged in.

### S-6: New user reads `init` output and lands on the canonical implementation path (Track 6)

**As** a new user who just ran `spec-kitty init demo --ai codex`
**I want** the printed next-step guidance and the project's README / help to direct me at the `spec-kitty next` loop and `spec-kitty agent action implement/review` per-decision verbs
**So that** I do not learn to depend on top-level `spec-kitty implement` as a user-facing entrypoint.

**Then**:
- Init output, project README, slash-command guidance, and `spec-kitty implement --help` text all name `spec-kitty next` as the canonical loop entry and `spec-kitty agent action implement` / `spec-kitty agent action review` as the per-decision verbs.
- `spec-kitty implement --help` text additionally marks the command as **internal infrastructure** (implementation detail of `spec-kitty agent action implement`), not as a user-facing canonical path.
- `spec-kitty implement` itself still runs for direct invokers (no hard error). Internal delegation from `spec-kitty agent action implement` to `spec-kitty implement` is preserved as an implementation detail.

### S-7: Repo dogfoods cleanly at the release commit (Track 7)

**As** the release engineer cutting `3.1.1`
**I want** `pyproject.toml` and `.kittify/metadata.yaml` to agree on version
**So that** a fresh clone of the release tag can run every advertised core command without version-mismatch failure.

**Then**:
- At the release commit, `pyproject.toml` version == `.kittify/metadata.yaml` project version == `3.1.1`.
- A fresh clone of the release tag, with a clean install, can run `spec-kitty --version`, `spec-kitty init`, `spec-kitty agent mission create`, `spec-kitty agent mission finalize-tasks`, and `spec-kitty agent tasks status` without any error rooted in version skew.
- A pre-release validation step asserts version coherence and fails the release cut if it is not satisfied.
- The same set of commands runs cleanly against `/tmp/311/spec-kitty` at the release commit.

### Edge cases the spec must cover

- `spec-kitty init` invoked twice in the same directory (D-1; FR-006).
- `spec-kitty init` invoked inside an existing git repository (D-1; FR-007).
- Concurrent `spec-kitty agent mission create` from two checkouts (D-3; FR-205).
- A `tasks.md` file whose final WP is parallel-eligible by explicit declaration AND has trailing prose after the final WP section (D-2 hotfix; FR-304).
- A planning-artifact WP whose execution dispatch lands in the planning lane and not in a code worktree (D-2; FR-103).
- Two concurrent credential refresh attempts where one rotates the refresh token (D-5; FR-404).
- A scratch checkout where `pyproject.toml` and `.kittify/metadata.yaml` deliberately disagree on version — pre-release validation MUST fail the cut (FR-602).
- A direct invocation of `spec-kitty implement` after de-emphasis — MUST still run (FR-505).

---

## 7. Functional Requirements

Requirements are grouped by track. All status values are **Proposed** at the end of `/specify`. Plan/review phases may upgrade to Approved.

### Track 1 — `init` coherence and new-user entrypoint quality

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `spec-kitty init <name> --ai <agent> [--non-interactive]` MUST NOT initialize a git repository in the target directory. There MUST be no flag, environment variable, or config option that re-enables git initialization from `init`. | Proposed |
| FR-002 | `spec-kitty init` MUST NOT create any commit (including any commit titled `Initial commit from Specify template` or equivalent) on behalf of the user, ever, under any flag combination. The literal string `Initial commit from Specify template` MUST be removed from the production source tree. | Proposed |
| FR-003 | `spec-kitty init` MUST NOT create a `.agents/skills/` directory or its contents in the target project. If skill content is part of the new init model, it MUST be placed under the agent-specific directory the user explicitly opted into. | Proposed |
| FR-004 | `spec-kitty init` MUST print next-step guidance that names the `spec-kitty next` loop as the canonical entry point and `spec-kitty agent action implement` / `spec-kitty agent action review` as the per-decision verbs. The text MUST NOT name top-level `spec-kitty implement` as a canonical user-facing command. | Proposed |
| FR-005 | After `spec-kitty init` completes against a previously empty directory, the set of files created MUST be deterministic, enumerable from documentation, and consistent with the model the printed output describes (no ambiguous untracked files relative to any model `init` advertises). | Proposed |
| FR-006 | `spec-kitty init` re-run in a directory it already initialized MUST be either idempotent (same result, no error) or fail fast with a clear message that names the conflict; it MUST NOT silently merge or overwrite state. | Proposed |
| FR-007 | If `spec-kitty init` is invoked inside an existing git repository, it MUST NOT touch git state (no `git init`, no commits, no staging, no branch creation) and MUST limit its effect to file creation. This MUST hold under every flag combination — there is no escape hatch. | Proposed |
| FR-008 | `spec-kitty init --help` MUST describe the new model accurately: no git initialization, no commit, and next-step guidance that names the `spec-kitty next` loop and the `spec-kitty agent action implement/review` per-decision verbs. The `--no-git` flag from pre-3.1.1 versions MUST be absent from the help text (the flag is removed). | Proposed |

### Track 2 — Planning-artifact producer correctness

| ID | Requirement | Status |
|----|-------------|--------|
| FR-101 | Lane computation MUST NOT filter planning-artifact work packages out of its result. | Proposed |
| FR-102 | Each planning-artifact work package generated by `finalize-tasks` MUST receive the canonical **planning lane** assignment in the persisted lane metadata. | Proposed |
| FR-103 | The planning lane MUST resolve to the main repo checkout (the planning workspace) rather than to a `.worktrees/<feature>-lane-X` directory. | Proposed |
| FR-104 | The `finalize-tasks` producer MUST emit lane metadata for planning-artifact WPs that is consistent with the producer/consumer contract used by code WPs at the lane-contract boundary. | Proposed |
| FR-105 | All downstream consumers added or modified in `3.1.1` (status events, query, review-context resolution, implement dispatch) MUST treat planning-artifact WPs uniformly with code WPs at the lane-contract boundary; consumers MUST NOT branch on a "planning vs. code" type distinction at that boundary. | Proposed |
| FR-106 | Regression coverage MUST exist for: (a) lane computation including planning-artifact WPs; (b) implement dispatch resolving the planning lane to the main repo checkout for a planning-artifact WP; (c) review-context resolution returning a coherent context for a planning-artifact WP via the canonical model. | Proposed |

### Track 3 — Forward-only mission identity hardening (Phase 1 only)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-201 | `spec-kitty agent mission create` (and the slash-command equivalents) MUST mint a canonical `mission_id` per the adopted ADR (commit `b85116ed`) at creation time and persist it in `meta.json`. | Proposed |
| FR-202 | New machine-facing flows added or stabilized in `3.1.1` MUST identify a mission by its `mission_id`, not by numeric prefix uniqueness. | Proposed |
| FR-203 | Numeric prefix and slug MAY continue to be displayed and accepted on the human-facing CLI surface, but MUST NOT be the canonical identity for any new machine-facing flow added or stabilized in `3.1.1`. | Proposed |
| FR-204 | The mission-creation flow MUST NOT allocate identity by scanning local numeric prefixes and using `max(prefix) + 1`; identity allocation MUST be independent of the local numeric-prefix space. | Proposed |
| FR-205 | Two `spec-kitty agent mission create` invocations issued concurrently from two checkouts of the same repository MUST NOT produce colliding `mission_id` values. | Proposed |
| FR-206 | Backfill, repair, or rewrite of historical missions' identity is explicitly OUT OF SCOPE and MUST NOT be performed by this mission (see NG-2). | Proposed |

### Track 4 — Tasks/finalize pipeline hotfix (narrow slice only)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-301 | The dependency parser MUST bound the final WP section so that prose appearing after the final WP section is NOT included in the final WP's body. | Proposed |
| FR-302 | The dependency parser MUST respect explicit `dependencies:` declarations and MUST NOT overwrite them with values inferred from prose. | Proposed |
| FR-303 | When a WP carries an explicit `dependencies:` declaration, prose-based dependency inference MUST be additive-only OR disabled for that WP. The chosen behavior MUST be documented in the plan and consistent across all WPs. | Proposed |
| FR-304 | A regression test MUST exist that authors a `tasks.md` file with: (a) a final WP that is parallel-eligible by explicit declaration, and (b) trailing prose after the final WP section that, under the old behavior, would have introduced a false-positive dependency, and asserts the finalized manifest preserves the parallel-eligibility. | Proposed |
| FR-305 | Full manifest redesign / inversion is explicitly OUT OF SCOPE for this mission (see NG-3); only the producer-side hotfix is delivered. | Proposed |

### Track 5 — Concurrent credential refresh race fix

| ID | Requirement | Status |
|----|-------------|--------|
| FR-401 | Credential refresh MUST hold an exclusive lock for the FULL refresh transaction (read → network call → persist), not only for file I/O operations in isolation. | Proposed |
| FR-402 | On a refresh attempt that returns 401, the refresh MUST re-read on-disk credentials under the same lock before treating the 401 as terminal. If the on-disk credentials have changed since the refresh started, the refresh MUST be treated as stale (no terminal action) rather than as authoritative grounds for clearing. | Proposed |
| FR-403 | Credential clearing MUST only occur when (a) the lock is held, (b) the on-disk credentials match the credentials the failed refresh started from, and (c) the failure was non-stale by criteria (a)+(b). | Proposed |
| FR-404 | A regression test MUST exercise two concurrent refresh attempts where one successfully rotates the refresh token and the other races; the user MUST remain logged in after both attempts complete. | Proposed |
| FR-405 | This race fix is **release-gating** for `3.1.1` because background sync remains enabled in `3.1.1`. `3.1.1` MUST NOT ship without it. | Proposed |

### Track 6 — Top-level `implement` de-emphasis

**Scope clarification**: "The canonical post-#555 user workflow" is named concretely in D-4 and means the `spec-kitty next` loop plus the `spec-kitty agent action implement` / `spec-kitty agent action review` per-decision verbs. The requirements below name those commands explicitly so reviewers can verify against actual CLI surface, not against vague terminology. Top-level `spec-kitty implement` becomes **internal infrastructure** — an implementation detail of `spec-kitty agent action implement`, not a user-facing surface.

| ID | Requirement | Status |
|----|-------------|--------|
| FR-501 | The text printed by `spec-kitty init` MUST NOT name top-level `spec-kitty implement` as the canonical implementation entrypoint. The "Next steps" panel MUST direct users at the `spec-kitty next` loop and at `spec-kitty agent action implement` / `spec-kitty agent action review`. | Proposed |
| FR-502 | The project `README` and any `init`-shipped getting-started documentation MUST present the canonical user workflow as the `spec-kitty next` loop (loop entry) followed by `spec-kitty agent action implement` / `spec-kitty agent action review` (per-decision verbs). They MUST NOT name top-level `spec-kitty implement` as a canonical step. | Proposed |
| FR-503 | `spec-kitty implement --help` text MUST mark the command as **internal infrastructure** (an implementation detail of `spec-kitty agent action implement`) rather than as a user-facing canonical path. The help text MUST direct callers to `spec-kitty next` for the loop and `spec-kitty agent action implement` for the per-WP verb. | Proposed |
| FR-504 | The slash-command guidance shipped by `init` (the source templates under `src/specify_cli/missions/software-dev/command-templates/`) MUST teach `spec-kitty next` as the canonical loop and `spec-kitty agent action implement` / `spec-kitty agent action review` as the per-decision verbs. The templates MUST NOT teach top-level `spec-kitty implement WP##` as a canonical command users (or agents driving users) should invoke directly. The slash-command file `/spec-kitty.implement` itself MAY remain as a slash-command surface, but its body MUST resolve to the agent-facing `spec-kitty agent action implement` invocation under the hood, not to the top-level `spec-kitty implement` invocation. | Proposed |
| FR-505 | The `spec-kitty implement` command itself MUST still run for users who invoke it directly; this mission MUST NOT turn the command into a hard error or remove its entry point. Internal delegation from `spec-kitty agent action implement` to `spec-kitty implement` is preserved as an implementation detail. | Proposed |
| FR-506 | Stabilization of #538, #540, and #542 is explicitly OUT OF SCOPE for this mission (see NG-7); those issues remain open for a later release and MUST NOT be partially fixed in 079 in a way that changes the canonical user-facing path. | Proposed |

### Track 7 — Repo dogfooding / version coherence at release cut

**Scope boundary**: Track 7 owns **release-hygiene correctness**, not narrative release authoring. It MUST ensure version coherence across machine-relevant artifacts and add a pre-release validation step that fails if the repo cannot dogfood itself cleanly. Final `CHANGELOG.md` prose curation and GitHub release-note authoring remain part of the human release process. This mission MAY produce structured draft inputs (e.g., a proposed `CHANGELOG.md` block) and validation signals (e.g., "a `3.1.1` entry exists before the cut") for that human process, but MUST NOT author the final narrative.

| ID | Requirement | Status |
|----|-------------|--------|
| FR-601 | At the `3.1.1` release commit, the version reported by `pyproject.toml` MUST equal the version reported by `.kittify/metadata.yaml` (project version), and both MUST equal `3.1.1`. | Proposed |
| FR-602 | A pre-release validation step MUST assert version coherence between `pyproject.toml` and `.kittify/metadata.yaml`, and MUST fail the release cut if they disagree. | Proposed |
| FR-603 | A fresh clone of the `3.1.1` release tag with a clean install MUST be able to run `spec-kitty --version`, `spec-kitty init <name> --ai <agent> --non-interactive`, `spec-kitty agent mission create <slug> --json`, `spec-kitty agent mission finalize-tasks --mission <slug>`, and `spec-kitty agent tasks status --mission <slug>` without any error whose root cause is version skew. | Proposed |
| FR-604 | `/tmp/311/spec-kitty` MUST be able to run the same set of commands at the release commit; this is the dogfood acceptance check. | Proposed |
| FR-605 | The mission MUST provide a structured release-prep draftable artifact (e.g., a proposed `CHANGELOG.md` block for `3.1.1`) that the human release engineer can use as input to the final narrative. The mission MUST NOT author the final `CHANGELOG.md` prose or the GitHub release notes themselves. | Proposed |
| FR-606 | The pre-release validation step (from FR-602) MUST also assert that a `CHANGELOG.md` entry for `3.1.1` exists before the release cut, and MUST fail the cut if the entry is missing. The validation checks for presence and basic structural shape, not for narrative quality or wording. | Proposed |

---

## 8. Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | `spec-kitty init <name> --ai <agent> --non-interactive` against an empty directory MUST complete quickly and without ERROR-level log lines on a typical developer machine. | Wall time < 30 s; 0 ERROR log lines | Proposed |
| NFR-002 | The credential refresh race fix MUST NOT add measurable median latency to a non-contended refresh transaction. | ≤ +50 ms median over baseline | Proposed |
| NFR-003 | The dependency-parser hotfix MUST NOT regress finalization wall-time on a representative 30-WP `tasks.md`. | ≤ 10% wall-time regression vs. pre-fix baseline | Proposed |
| NFR-004 | New regression tests added by this mission MUST execute quickly enough in aggregate to be added to a fast pre-commit gate. | < 60 s aggregate under `PWHEADLESS=1 pytest tests/ -q` | Proposed |
| NFR-005 | The pre-release version-coherence validation step MUST execute quickly enough to be unconditionally run at every release cut. | < 5 s wall time | Proposed |
| NFR-006 | All new code added by this mission MUST satisfy the active repository charter: `mypy --strict` clean and ≥ 90% test coverage on new lines. | mypy strict clean; ≥ 90% line cov on new code | Proposed |
| NFR-007 | The full test suite MUST pass under `PWHEADLESS=1 pytest tests/` at the release commit, with no new flaky tests introduced by this mission. | 0 failures; 0 new flakes | Proposed |

---

## 9. Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Historical `kitty-specs/**` mission artifacts in existing repos MUST be tolerated as-is. This mission MUST NOT modify them. | Proposed |
| C-002 | Mission identity (`mission_id`) backfill across historical missions is OUT OF SCOPE; only NEW missions mint `mission_id` (Phase 1 only). | Proposed |
| C-003 | The full manifest redesign for #525 is OUT OF SCOPE; only the producer-side hotfix is delivered. | Proposed |
| C-004 | The full stabilization of #538/#540/#542 is OUT OF SCOPE; top-level `implement` is de-emphasized only. | Proposed |
| C-005 | #401 is OUT OF SCOPE; `3.1.1` is a CLI-only stabilization release. | Proposed |
| C-006 | #555 is the new baseline. This mission MUST NOT re-spec, re-implement, or extend the fixes already shipped in #555 (#551, #552, #526). | Proposed |
| C-007 | Backward compatibility for the existing `spec-kitty implement` command MUST be preserved; the command MUST continue to run for direct invokers. | Proposed |
| C-008 | This mission MUST NOT introduce new SaaS-contract surface area. | Proposed |
| C-009 | This mission MUST land via the standard `3.1.1` release flow into `main`; it MUST NOT be split across multiple unrelated release tags. | Proposed |
| C-010 | All new code MUST follow the active repository charter conventions (typer for CLI, rich for console output, ruamel.yaml for YAML, pytest for tests, mypy --strict for type checking). | Proposed |
| C-011 | All examples and validation steps in this spec assume the working repo is `/tmp/311/spec-kitty`. Plan and tests MUST use that path for any concrete dogfood verification. | Proposed |
| C-012 | Final `CHANGELOG.md` prose curation and GitHub release-note authoring remain part of the human release process and are OUT OF SCOPE for this mission. The mission MAY produce structured draft inputs and presence/structure validation signals for that process, but MUST NOT author the final narrative. | Proposed |

---

## 10. Acceptance Criteria

### Per-track acceptance

| Track | Accepted when |
|-------|---------------|
| Track 1 — `init` coherence | FR-001..FR-008 each pass an explicit test, and S-1 succeeds in `/tmp/311/spec-kitty` against a freshly created subdirectory under `/tmp/`. |
| Track 2 — planning-artifact producer | FR-101..FR-106 each pass an explicit test, and S-4 succeeds end-to-end against a fresh feature whose plan generates at least one planning-artifact WP. |
| Track 3 — mission identity Phase 1 | FR-201..FR-206 each pass an explicit test, and S-3 succeeds for a fresh mission created in `/tmp/311/spec-kitty`. Two concurrent creates in two checkouts MUST NOT collide. |
| Track 4 — tasks/finalize hotfix | FR-301..FR-305 each pass an explicit test, and S-2 succeeds via the regression test described in FR-304. |
| Track 5 — auth refresh race | FR-401..FR-405 each pass an explicit test, and the concurrent-refresh regression test in FR-404 passes deterministically. |
| Track 6 — `implement` de-emphasis | FR-501..FR-506 each pass an explicit content/text or behavior test; README, `init` output, slash-command source templates, and `spec-kitty implement --help` all name `spec-kitty next` and `spec-kitty agent action implement/review` exclusively as the canonical user-facing path; top-level `spec-kitty implement` is not named in any user-facing canonical-path teach-out; `spec-kitty implement` still runs for compatibility. |
| Track 7 — repo dogfood / version coherence | FR-601..FR-604 each pass an explicit test, and S-7 succeeds against the release commit checkout in `/tmp/311/spec-kitty`. |

### Mission-level acceptance

The mission as a whole is accepted when ALL of the following hold:
- All seven tracks above are individually accepted.
- All locked product decisions D-1..D-5 are reflected in the shipped behavior.
- All non-goals NG-1..NG-8 are honored — no in-scope work spilled into them.
- All non-functional thresholds NFR-001..NFR-007 are met.
- The full test suite passes under `PWHEADLESS=1 pytest tests/` with `mypy --strict` clean.

---

## 11. Release Gates (Definition of "Releasable as 3.1.1")

`3.1.1` MUST NOT ship until ALL of the following are true at the proposed release commit. These gates are the operator-facing summary of what makes `3.1.1` releasable.

| ID | Gate |
|----|------|
| RG-1 | **Init is coherent.** S-1 succeeds against a fresh `/tmp/` directory using a freshly built CLI from the proposed release commit. |
| RG-2 | **Tasks finalize hotfix is in place.** S-2 succeeds and the FR-304 regression test passes deterministically. |
| RG-3 | **Planning-artifact producer is canonical.** S-4 succeeds end-to-end and FR-101..FR-106 each have explicit test coverage. |
| RG-4 | **New mission identity is safe.** S-3 succeeds and a concurrent-create test demonstrates non-collision. |
| RG-5 | **Auth refresh race is fixed.** S-5 succeeds and the FR-404 regression test passes deterministically. (Release-gating per FR-405 because background sync remains enabled.) |
| RG-6 | **Top-level `implement` is de-emphasized.** S-6 succeeds: init output, README, `--help` text, and slash-command guidance no longer name top-level `spec-kitty implement` as the canonical path. The command still runs. |
| RG-7 | **Repo dogfoods cleanly.** S-7 succeeds at the release commit. `pyproject.toml` and `.kittify/metadata.yaml` agree on `3.1.1`. The pre-release validation step from FR-602 passes. |
| RG-8 | **No deferred work has leaked into the release.** A scope audit confirms NG-1..NG-8 each held: no historical archaeology, no #557 sweep, no #525 redesign, no #401, no #538/#540/#542 stabilization. |

If any of RG-1..RG-8 is not met, `3.1.1` MUST NOT be tagged.

---

## 12. Rollout / Implementation Order

Plan and tasks phases MUST preserve this sequence. Each step takes the previous step's output as its baseline and is gated by it.

1. **Baseline = #555.** Treat merge commit `f3d017f6` as the starting point. Do NOT redo or extend any of #555's fixes. (#551, #552, #526 are already closed by #555.)
2. **Track 1: `init` coherence.** Land the new init model first because every other track's verification eventually relies on a coherent fresh `init` to set up its test environment.
3. **Track 4: tasks/finalize hotfix.** Land the parser bound + explicit-dependencies-respect change before exercising any track that depends on finalize output.
4. **Track 2: planning-artifact producer correctness.** Land the canonical "first-class lane-owned, planning-lane = main checkout" model and update lane computation, then update downstream consumers added/modified in `3.1.1`.
5. **Track 3: new-mission identity hardening (Phase 1).** Mint `mission_id` at creation; switch new machine-facing flows to identify by `mission_id`.
6. **Track 5: auth refresh race fix.** Lock the full refresh transaction; re-read under lock on 401 before clearing.
7. **Track 6: top-level `implement` de-emphasis.** Update init output, README, slash-command guidance, and `--help` text. Leave the command runnable.
8. **Track 7: repo dogfooding / version coherence.** Align `pyproject.toml` and `.kittify/metadata.yaml`; add the pre-release version-coherence validation step; confirm `/tmp/311/spec-kitty` runs the dogfood command set cleanly at the release commit.
9. **(Conditional) Track H / #401.** Intentionally deferred. NOT included in `3.1.1`. Only revisited if release scope is explicitly expanded via a follow-up mission (per D-5).

This sequence is also the recommended work-package ordering for the plan/tasks phase.

---

## 13. Cross-References (Issue Mapping)

| Issue | Track | Status in this mission |
|-------|-------|------------------------|
| **#566** (Meta: 3.1.1 post-#555 hardening mission) | All tracks | Primary parent of this mission. |
| **#550** | Track 2 (planning-artifact producer correctness) | In scope. |
| **#557** | Track 3 (mission identity, Phase 1 only) | In scope, **Phase 1 only**. Historical sweep deferred per NG-2. |
| **#525** | Track 4 (tasks/finalize hotfix, narrow slice only) | In scope, **narrow slice only**. Full redesign deferred per NG-3. |
| **#554** | Track 5 (auth refresh race) | In scope. **Release-gating** per FR-405 because background sync remains enabled. |
| **#538** | Track 6 (top-level `implement` de-emphasis) | **Deferred for stabilization.** Mission de-emphasizes the canonical path; #538 stays open for a later release. |
| **#540** | Track 6 (top-level `implement` de-emphasis) | **Deferred for stabilization.** Same as #538. |
| **#542** | Track 6 (top-level `implement` de-emphasis) | **Deferred for stabilization.** Same as #538. |
| **#401** | Track H (SaaS sync contract) | **Intentionally deferred.** `3.1.1` is CLI-only; per D-5. |
| **#416** | (merge interruption / idempotency) | Out of scope per NG-4. |
| **#551** | (already merged in #555) | **Closed by #555.** MUST NOT be re-spec'd here. |
| **#552** | (already merged in #555) | **Closed by #555.** MUST NOT be re-spec'd here. |
| **#526** | (already merged in #555) | **Closed by #555.** MUST NOT be re-spec'd here. |

---

## 14. Verification Strategy

This is concrete, not generic. Every check below MUST be runnable against `/tmp/311/spec-kitty` at the proposed release commit.

### V-1. Fresh `init` in an isolated temp directory
1. Create a fresh empty directory under `/tmp/`, e.g. `/tmp/spec-kitty-init-verify-<ts>/`.
2. Build/install the CLI from the `/tmp/311/spec-kitty` working tree at the release commit.
3. Run `spec-kitty init demo --ai codex --non-interactive` inside the temp directory.
4. Assert: no `.git/` directory was created; no commit titled `Initial commit from Specify template` exists; no `.agents/skills/` directory exists; printed next-step guidance names `spec-kitty next` and `spec-kitty agent action implement/review` and does NOT name top-level `spec-kitty implement` as a canonical user-facing entrypoint; the file set created is enumerable and matches documentation. Additionally assert that passing `--no-git` to `spec-kitty init` results in a typer "no such option" error (the flag is removed in 3.1.1).
5. Re-run `spec-kitty init demo --ai codex --non-interactive` and assert idempotent OR fail-fast.
6. Repeat the run inside an existing git repo and assert no git state was touched.

### V-2. Fresh mission creation / identity correctness
1. From `/tmp/311/spec-kitty`, run `spec-kitty agent mission create test-identity-1 --json` and `spec-kitty agent mission create test-identity-2 --json`.
2. Read the resulting `meta.json` files for both missions and assert each contains a non-empty `mission_id`.
3. Run two concurrent `spec-kitty agent mission create` invocations from two checkouts of the same repository (e.g. `/tmp/311/spec-kitty` and a sibling clone) and assert their `mission_id` values do not collide.
4. Verify that no allocation in either creation flow scanned a local numeric prefix space.

### V-3. Tasks finalization preserves intended parallelism
1. Author a `tasks.md` file under a fresh test feature in `/tmp/311/spec-kitty` whose final WP is parallel-eligible by explicit `dependencies:` declaration AND has trailing prose after the final WP section.
2. Run `spec-kitty agent mission finalize-tasks --mission <slug>` against that feature.
3. Read the finalized manifest and assert the final WP retains its declared dependencies verbatim and is still parallel-eligible.
4. Confirm the FR-304 regression test exists in `tests/` and passes deterministically under `PWHEADLESS=1 pytest tests/`.

### V-4. Planning-artifact WP generation and downstream execution correctness
1. Construct a fresh feature in `/tmp/311/spec-kitty` whose plan generates at least one planning-artifact WP.
2. Run finalize-tasks and inspect persisted lane metadata; assert the planning-artifact WP has the canonical planning-lane assignment.
3. Run lane computation for that feature and assert the planning-artifact WP is included in the result (not filtered).
4. Resolve the planning lane and assert it points to the main repo checkout, not a `.worktrees/...` directory.
5. Exercise status events, query, review-context resolution, and implement dispatch against that planning-artifact WP and assert each consumer treats it uniformly with code WPs at the lane-contract boundary.

### V-5. Concurrent refresh behavior
1. Add an integration test that simulates two concurrent refresh attempts under the lock contract: one rotates the refresh token, the other races.
2. Assert: after both attempts complete, the user remains logged in; on-disk credentials reflect the rotated refresh token; no refresh attempt cleared credentials based on a stale 401.

### V-6. Top-level `implement` compatibility surface and de-emphasis
1. Run `spec-kitty implement --help` and assert the help text marks the command as **internal infrastructure** (an implementation detail of `spec-kitty agent action implement`) and directs callers to `spec-kitty next` for the loop and `spec-kitty agent action implement` for the per-WP verb.
2. Invoke `spec-kitty implement WP01` against a feature in `/tmp/311/spec-kitty` and assert the command still runs (compatibility surface preserved); full stabilization is NOT asserted (stays out of scope per FR-506).
3. Read README and `init` output and assert no canonical-path text names top-level `spec-kitty implement`.
4. Read the slash-command guidance shipped by `init` and assert it teaches `spec-kitty next` as the canonical loop and `spec-kitty agent action implement/review` as the per-decision verbs (no top-level `spec-kitty implement WP##` invocations as canonical user-facing examples).

### V-7. Repo self-dogfooding at the release-cut version
1. From `/tmp/311/spec-kitty` at the proposed release commit, assert `pyproject.toml` version == `.kittify/metadata.yaml` project version == `3.1.1`.
2. In a fresh shell with a clean install of the release tag, run: `spec-kitty --version`, `spec-kitty init demo --ai codex --non-interactive` (in a temp dir), `spec-kitty agent mission create dogfood --json` (in `/tmp/311/spec-kitty`), `spec-kitty agent mission finalize-tasks --mission dogfood`, `spec-kitty agent tasks status --mission dogfood`. Assert each command exits 0 with no version-skew error.
3. Run the pre-release validation step from FR-602 and assert it succeeds.
4. Introduce a deliberate version mismatch in a scratch checkout and assert the validation step fails the release cut.
5. Run the structured release-prep draft generator from FR-605 against the working tree and assert it produces a non-empty proposed `CHANGELOG.md` block whose header references `3.1.1`.
6. In a scratch checkout where `CHANGELOG.md` does NOT contain a `3.1.1` entry, run the FR-606 validation and assert it fails the release cut. Add the entry, re-run, and assert it succeeds.

### V-8. Scope audit (release gate RG-8)
1. Diff this mission's shipped changes against NG-1..NG-8.
2. Assert no historical `kitty-specs/**` artifacts were modified (other than mission 079 itself).
3. Assert no #557 sweep across historical missions occurred.
4. Assert no manifest redesign for #525 occurred.
5. Assert no #401 / SaaS contract surface area was added.
6. Assert no #538/#540/#542 stabilization occurred.

---

## 15. Assumptions

| ID | Assumption | Why it's safe |
|----|------------|---------------|
| A-1 | The ULID-based mission identity ADR adopted in commit `b85116ed` is the canonical scheme this mission targets for `mission_id`. | The ADR landed before this mission and there is no competing identity proposal in flight for `3.1.1`. |
| A-2 | The `spec-kitty next` loop (top-level command at `src/specify_cli/cli/commands/next_cmd.py`) and the `spec-kitty agent action implement` / `spec-kitty agent action review` per-decision verbs (`src/specify_cli/cli/commands/agent/workflow.py`) are the canonical user-facing implementation surface that `init`/help/README will direct users to. Top-level `spec-kitty implement` is internal infrastructure that `spec-kitty agent action implement` delegates to under the hood. Verified by Phase 0 code-surface research. | Operator decision (Q2): D-4. |
| A-3 | Background sync remains enabled in `3.1.1`. | No decision was made to disable it; per the brief, #554 is treated as release-gating in this case. |
| A-4 | `3.1.1` lands as a single coordinated release. | Per C-009. |
| A-5 | `pyproject.toml` and `.kittify/metadata.yaml` are the canonical version surfaces; no third version surface needs to be aligned. | Per the brief's framing of the version-coherence problem. If a third surface emerges during plan, it joins the coherence requirement under FR-601. |
| A-6 | The label "planning lane" is acceptable as the canonical lane name for planning-artifact WPs. The plan phase MAY rename it as long as the canonical-model contract (D-2) is preserved. | Naming detail; the contract is what is locked. |
| A-7 | The "explicit `dependencies:` overrides prose inference" rule (FR-302/FR-303) is acceptable as the narrow-slice fix for #525. | Explicitly aligned with the brief's narrow-slice instructions. |

---

## 16. Key Entities (Conceptual)

| Entity | Description |
|--------|-------------|
| **Mission** | A unit of planned work with a canonical `mission_id` (Phase 1 hardening), a numeric prefix and slug for human display, and a `meta.json` written at creation. |
| **Work Package (WP)** | A finalize-tasks-derived unit of work with a canonical lane assignment and (for code WPs) a worktree resolution. |
| **Code WP** | A WP whose lane resolves to a `.worktrees/<feature>-lane-X` directory and which carries an executable change. |
| **Planning-artifact WP** | A WP that produces planning artifacts and whose canonical lane is the planning lane (main repo checkout). NOT filtered out of lane computation under D-2. |
| **Lane** | The canonical grouping that maps WPs to a workspace. Includes the **planning lane** (main repo checkout) and code lanes (`.worktrees/...`). |
| **Mission Identity (`mission_id`)** | Canonical identifier minted at mission-creation time per the adopted ADR; replaces numeric-prefix uniqueness for new machine-facing flows. |
| **Credential** | Token material persisted to disk and refreshed via a locked refresh transaction; NOT cleared on stale 401 under D-2's lock contract (see FR-401..FR-403). |
| **Init Model** | The set of files, side-effects, and printed guidance produced by `spec-kitty init` under D-1. |
| **Release Cut** | The act of producing a `3.1.1` tag; constrained by the eight release gates RG-1..RG-8. |

---

## 17. Open Questions

None at the end of `/specify`. Both forcing-function product decisions were locked by the operator before this spec was written:

- **Q1 (SaaS scope)** → CLI-only stabilization. Track H / #401 is intentionally deferred. See D-5.
- **Q2 (top-level `implement` direction)** → De-emphasize. Compatibility surface remains; full stabilization of #538/#540/#542 is not in scope. See D-4.

If new ambiguities surface during plan/review, they MUST be resolved before any in-scope work is moved to "Approved", per the spec quality checklist.

---

## 18. Dogfood Working-Repo Note

All examples and validation steps in this spec assume the working repo is **`/tmp/311/spec-kitty`**. Any verification action that says "the repo" means that path. The release cut for `3.1.1` is also expected to be performed against that working tree, and S-7 / V-7 are the dogfood-acceptance proof.
