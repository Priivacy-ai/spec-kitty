# Implementation Plan: 3.1.1 Post-555 Release Hardening

**Mission**: `079-post-555-release-hardening`
**Mission type**: software-dev
**Spec**: [kitty-specs/079-post-555-release-hardening/spec.md](spec.md)
**Date**: 2026-04-09
**Branch contract**: planning_base = `main` · merge_target = `main` · current = `main` · `branch_matches_target = true`
**Baseline**: PR #555, merge commit `f3d017f663fa0a19aad686e58876d23b47cc60e7`, merged 2026-04-09 06:05:40 UTC
**Working repo**: `/private/tmp/311/spec-kitty` (every concrete reference in this plan uses this path)

---

## 1. Summary

This plan implements the seven core forward-correctness tracks defined in the spec:

1. **Track 1 — `init` coherence**: rewrite `spec-kitty init` so it does not initialize git (no escape hatch — the `--no-git` flag is removed and there is no opt-in `--git` flag), does not create the "Initial commit from Specify template" commit, does not seed `.agents/skills/`, and prints next-steps that name the `spec-kitty next` loop and the `spec-kitty agent action implement/review` per-decision verbs (per D-4) rather than top-level `spec-kitty implement`.
2. **Track 2 — Planning-artifact producer correctness**: stop filtering `ExecutionMode.PLANNING_ARTIFACT` WPs out of `compute_lanes()`; assign them to a canonical `lane-planning` lane that resolves to the main repo checkout; collapse the post-#555 special-case branches in `context/resolver.py`, `workspace_context.py`, and `worktree.py` to a uniform lane-contract path.
3. **Track 3 — Mission identity Phase 1**: mint a ULID `mission_id` in `meta.json` at creation time; switch newly added/stabilized machine-facing flows to identify by `mission_id`; do **not** backfill historical missions.
4. **Track 4 — Tasks/finalize hotfix**: bound `_split_wp_sections()` so the final WP section stops at trailing prose / non-WP markdown rather than slurping to EOF; add explicit precedence for `dependencies:` declarations.
5. **Track 5 — Auth refresh race fix**: extend the existing `filelock.FileLock` from per-I/O scope to a full-transaction scope around `refresh_tokens()`; on 401, re-read on-disk credentials under the same lock before treating the failure as terminal.
6. **Track 6 — Top-level `implement` de-emphasis**: rewrite the user-facing teach-out across `init.py:641-650`, `README.md:8-9`, the slash-command templates under `src/specify_cli/missions/software-dev/command-templates/`, and `spec-kitty implement --help`; leave the command runnable for compatibility (no behavioral change to its execution path).
7. **Track 7 — Repo dogfood / version coherence**: align `pyproject.toml` and `.kittify/metadata.yaml`; extend `scripts/release/validate_release.py` to assert metadata-yaml ↔ pyproject sync and the FR-606 CHANGELOG-entry-presence check; surface the existing `build_release_prep_payload` as the structured draft artifact.

The plan preserves the spec's locked rollout sequence (§12 of `spec.md`): #555 baseline → init → tasks/finalize → planning-artifact → identity → auth → implement de-emphasis → version coherence. Track H / #401 is intentionally deferred (D-5).

---

## 2. Technical Context

| Field | Value |
|-------|-------|
| Language / Runtime | Python 3.11+ (existing repo requirement) |
| Primary dependencies | `typer`, `rich`, `ruamel.yaml`, `filelock`, `httpx`, `python-ulid` (>=3.0, **already present** in `pyproject.toml:72`), `pytest`, `mypy` |
| Storage | Filesystem only — `kitty-specs/<mission>/`, `.kittify/`, `~/.spec-kitty/credentials` (TOML), `.worktrees/`, `lanes.json`, `status.events.jsonl` |
| Testing | `pytest` (`PWHEADLESS=1 pytest tests/`), `mypy --strict` |
| Target platform | macOS / Linux developer machines, CI |
| Project type | Single Python package |
| Performance goals | Per spec NFR-001..NFR-007 (see spec §8) — measurable thresholds |
| Constraints | mypy strict clean; ≥ 90% line coverage on new code; no fallback / compat shims; no historical archaeology |
| Scale / scope | 7 tracks, ~50 functional requirements, ~7 NFRs, ~12 constraints; preview WP envelope ≈ 12-16 WPs (final shape determined by `/spec-kitty.tasks`) |

**No `[NEEDS CLARIFICATION]` markers remain.** All decisions D-1..D-5 are locked in the spec; all engineering unknowns were resolved through Phase 0 code-surface research (see [research.md](research.md)).

---

## 3. Charter Check

Charter file present at `/private/tmp/311/spec-kitty/.kittify/charter/charter.md`. Plan-action doctrine loaded from `spec-kitty charter context --action plan --json`.

| Charter directive / tactic | Plan compliance |
|----------------------------|-----------------|
| `DIRECTIVE_010` Specification Fidelity Requirement | ✅ Every change in this plan traces to an FR/NFR/C in `spec.md`. The track sections in §6 carry explicit FR ID columns. Deviations are flagged in §10. |
| `DIRECTIVE_003` Decision Documentation Requirement | ✅ Material technical choices (e.g., Track 2 unification model, Track 4 bound mechanism, Track 5 lock scope shape) are captured in [research.md](research.md) and in the per-track design notes in §6. ADR references are listed where existing ADRs constrain the choice (e.g., Track 3 references `architecture/adrs/2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md`). |
| `requirements-validation-workflow` tactic | ✅ The Phase 1 verification matrix in §8 ties every FR to at least one acceptance test under `tests/`. |
| `adr-drafting-workflow` tactic | ✅ The plan does **not** introduce new ADRs. Track 3 implements the existing ULID identity ADR (`b85116ed`). Track 2 references the established lane-contract model — no new architectural decision is required. If the implementation reveals a need for a new ADR (e.g., Track 7 release-validation workflow), the implementation phase will draft one before merge. |
| Charter policy: typer + rich + ruamel.yaml + pytest + mypy strict | ✅ Plan uses only these dependencies. No new third-party libraries are introduced; `python-ulid` is already in `pyproject.toml`. |
| Charter policy: pytest, ≥90% coverage on new code, mypy strict clean, integration tests for CLI commands | ✅ Per-track plans in §6 include explicit test additions and target coverage. The new tests live under `tests/init/`, `tests/core/`, `tests/lanes/`, `tests/sync/`, `tests/release/`, and `tests/agent/`. |

**Result**: Charter Check **PASSES** at Phase 0 entry. Re-evaluated post-Phase 1 design (§9) — still passes.

---

## 4. Project Structure

This mission edits and adds files inside the existing `src/specify_cli/` Python package. No new top-level package, no new sibling project, no architectural restructuring.

### Documentation for this mission

```
/private/tmp/311/spec-kitty/kitty-specs/079-post-555-release-hardening/
├── plan.md                  # this file
├── spec.md                  # mission specification (updated by /spec-kitty.specify)
├── meta.json                # mission identity (no mission_id yet — Track 3 will add it)
├── research.md              # Phase 0 consolidated findings
├── data-model.md            # Phase 1 conceptual entities
├── quickstart.md            # Phase 1 operator validation walkthrough
├── contracts/
│   ├── cli-contracts.md     # CLI behavior contracts per track
│   ├── file-format-contracts.md   # meta.json, lanes.json, .kittify/metadata.yaml shapes
│   └── test-contracts.md    # regression test scenario contracts
├── checklists/
│   └── requirements.md      # spec quality checklist (passes)
└── tasks/                   # populated by /spec-kitty.tasks (NOT this command)
```

### Source code surfaces touched (by track)

```
src/specify_cli/
├── cli/commands/
│   ├── init.py                       # Track 1: rewrite next-steps + remove git side-effects + remove `--no-git` flag + remove .agents/skills seeding (NO `--git` opt-in escape hatch)
│   ├── next_cmd.py                   # Track 6: READ-ONLY reference — `spec-kitty next` is the canonical loop entry point users will be directed at; NOT modified by this mission
│   ├── implement.py                  # Track 2: collapse planning-artifact special-case at lane lookup; Track 6: docstring rewritten to mark command as internal infrastructure (NOT execution behavior change — FR-505)
│   └── agent/
│       ├── mission.py                # Track 2: producer (compute_lanes/write_lanes_json call site) — no semantic change, just consume new model; Track 3: write mission_id
│       ├── tasks.py                  # Track 4: tighten disagree-loud + use new bounded parser
│       ├── workflow.py               # Track 6: READ-ONLY reference — `spec-kitty agent action implement/review` are the canonical per-decision verbs users (via agents) will invoke; NOT modified by this mission
│       └── release.py                # Track 7: surface validation summary; reference structured draft payload
├── core/
│   ├── git_ops.py                    # Track 1: remove init_git_repo() commit-from-init call path
│   ├── worktree.py                   # Track 2: route lane-planning through repo_root via lane lookup (not WP-type branch); Track 3: stop using get_next_feature_number() for new identity
│   ├── mission_creation.py           # Track 3: mint ULID mission_id; persist to meta.json
│   ├── dependency_parser.py          # Track 4: bound _split_wp_sections() against trailing prose; precedence guarantee
│   └── paths.py                      # (read-only — get_main_repo_root() is the helper Track 2 needs)
├── lanes/
│   ├── compute.py                    # Track 2: stop filtering PLANNING_ARTIFACT; assign to canonical lane-planning
│   ├── models.py                     # Track 2: ExecutionLane unchanged; LanesManifest may simplify planning_artifact_wps to derived view
│   ├── persistence.py                # Track 2: write_lanes_json — no shape change unless models.py changes
│   └── branch_naming.py              # Track 2: lane_branch_name() must handle lane-planning specially (no new branch — resolves to current planning branch)
├── context/
│   └── resolver.py                   # Track 2: remove if execution_mode == "planning_artifact" branch at lines 174-182 — go through lane_for_wp() uniformly
├── workspace_context.py              # Track 2: ResolvedWorkspace for lane-planning resolves to main repo root via lane lookup, not WP-type branch
├── sync/
│   ├── auth.py                       # Track 5: extend FileLock scope across full refresh transaction; re-read-on-401 path
│   ├── emitter.py                    # Track 3: include mission_id in emit_mission_created payload
│   └── events.py                     # Track 3: emit_mission_created signature accepts mission_id
├── status/
│   └── locking.py                    # (reference for Track 5 lock pattern; no edit)
├── release/
│   ├── version.py                    # (read-only — propose_version helper exists)
│   ├── changelog.py                  # Track 7: ensure build_changelog_block surfaces a structured draft (FR-605)
│   └── payload.py                    # Track 7: build_release_prep_payload is the structured draft entry (FR-605)
├── mission_metadata.py               # Track 3: MissionIdentity dataclass adds mission_id field
└── missions/software-dev/command-templates/
    ├── specify.md                    # Track 6: remove top-level implement teach-out
    ├── plan.md                       # Track 6: ditto
    ├── tasks.md                      # Track 6: ditto
    ├── tasks-packages.md             # Track 6: ditto
    └── implement.md                  # Track 6: re-frame as the slash-command surface that calls into the runtime; don't teach top-level CLI

scripts/release/
└── validate_release.py               # Track 7: add .kittify/metadata.yaml ↔ pyproject.toml sync check; expose CHANGELOG-presence check (FR-606)

pyproject.toml                        # Track 7: version stays 3.1.1aN until release cut; release-cut WP bumps to 3.1.1
.kittify/metadata.yaml                # Track 7: bump from 3.1.1a2 to match pyproject (and to 3.1.1 at the cut)
README.md                             # Track 6: remove top-level implement from canonical workflow line; reference slash-command path

tests/
├── init/test_init_minimal_integration.py     # Track 1: extend with no-git / no-commit / no-skills assertions
├── init/test_init_next_steps.py              # Track 1: NEW — assert next-steps output does not name `spec-kitty implement`
├── core/test_dependency_parser.py            # Track 4: extend with trailing-prose regression test (FR-304)
├── core/test_mission_creation.py             # Track 3: NEW or extend — assert mission_id present and ULID-shaped
├── lanes/test_compute_planning_artifact.py   # Track 2: NEW — planning-artifact WPs land in canonical lane
├── context/test_resolver_planning_artifact.py # Track 2: NEW — resolver returns coherent context for planning-artifact WP via lane lookup
├── sync/test_auth_concurrent_refresh.py      # Track 5: NEW — concurrent refresh + rotation + 401 race
├── release/test_validate_release.py          # Track 7: NEW or extend — metadata.yaml sync + CHANGELOG entry presence
├── release/test_release_payload.py           # Track 7: NEW or extend — structured draft (FR-605) shape
└── agent/cli/commands/test_implement_help.py # Track 6: NEW — assert help text marks compatibility surface
```

**Structure decision**: Single-project layout, edits only. The mission introduces no new top-level directories. The closest thing to a "new module" is Track 7's potential extraction of a `release/coherence.py` helper if `validate_release.py` cannot cleanly host the new check; that decision is deferred to implementation and tracked as Risk R-7.1 in §10.

---

## 5. Phase 0: Outline & Research

Phase 0 is captured in [research.md](research.md). Five parallel code-surface investigations covered all seven tracks:

| Track(s) | Research focus | Key finding |
|----------|----------------|-------------|
| 1 + 6 | `init` and top-level `implement` user-facing surfaces | `init.py:547-560` calls `init_git_repo`; `git_ops.py:115` carries the literal commit message; `init.py:641-650` lists `/spec-kitty.implement` in next-steps; existing init tests do **not** lock current commit-message behavior (safe to change). |
| 2 + 4 | Lane producer/consumer + dependency parser | `compute.py:254-276` filters `ExecutionMode.PLANNING_ARTIFACT`; `LanesManifest` carries parallel `planning_artifact_wps`; `context/resolver.py:174-182` is the post-#555 special-case branch. The dependency parser does NOT do prose inference — the false positive is from explicit-format patterns matching trailing prose because `_split_wp_sections()` slurps to EOF (`dependency_parser.py:56`). |
| 3 | Mission identity ADR + creation site | ADR adopted at `architecture/adrs/2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md`; format is ULID; field is `mission_id`; library `python-ulid>=3.0` already in `pyproject.toml:72`; `mission_creation.py:289-309` writes 7 fields, none of them `mission_id`; mission 079 itself (this mission) has no `mission_id` — confirmed via `meta.json` read. |
| 5 | Credential refresh and lock scope | `sync/auth.py` uses `filelock.FileLock` with 10s timeout; current scope is per-I/O; `refresh_tokens():324-394` splits into 3 locked segments with the network call at `:345` unprotected; `:349-351` clears credentials on 401 without re-reading; `tracker/saas_client.py:226-249` already shows the correct refresh+retry-within-session pattern. |
| 7 | Release-hygiene infrastructure | `pyproject.toml:3` = `3.1.1a3`; `.kittify/metadata.yaml:6` = `3.1.1a2` (**confirmed mismatch**); `src/specify_cli/release/{version,changelog,payload}.py` and `cli/commands/agent/release.py` already exist; `scripts/release/validate_release.py` already validates pyproject + CHANGELOG, but does **not** check `.kittify/metadata.yaml` sync. |

**Output**: [research.md](research.md) consolidates the findings, the rejected alternatives (where any), and the locked technical decisions per track.

---

## 6. Per-Track Design

This section is the engineering design layer — what changes, where, why. Final task breakdown is the job of `/spec-kitty.tasks`; this section is the WP-shape preview the planner uses to keep the design coherent.

### Track 1 — `init` coherence (FR-001..FR-008, NFR-001)

**Change shape**:
1. **Remove the auto-git-init call from `init.py` entirely. No escape hatch.** The current call site is at `init.py:547-560`, gated by `--no-git`. The new model has no opt-in `--git` flag and no path through which `init` ever calls `git init`, `git add`, or `git commit`. Per D-1 / FR-001 / FR-002 / FR-007, `init` is file-creation-only — there is no flag, no environment variable, no config option that re-enables git side effects. If a user wants a git repo after init, they run `git init` themselves. The `--no-git` flag is removed from the `init` command (it has no meaning under the new model and keeping it as a no-op would be a backward-compat shim that the project's CLAUDE.md explicitly forbids). Users passing `--no-git` after this lands will get a "no such option" error from typer; this is the intended CLI surface change.
2. **Remove `init_git_repo()` from `git_ops.py:104-128` from the `init` call path entirely**. The function may remain in `git_ops.py` if it has other callers (e.g., test fixtures); a follow-up cleanup may delete it once those callers are migrated. The literal string `"Initial commit from Specify template"` is deleted from the codebase (FR-002). The plan adds an explicit grep in the test suite asserting this string is absent from `src/`.
3. **Remove `.agents/skills/` seeding** from `init.py:515-540`. Skills install is replaced by the per-agent install path that copies into the agent's own directory (e.g., `.codex/prompts/`), not into a shared `.agents/` root. (FR-003)
4. **Rewrite the next-steps output** at `init.py:641-650`. Replace the slash-command list with a short, accurate teach-out that names `spec-kitty next --agent <name> --mission <slug>` as the canonical loop entry and `spec-kitty agent action implement` / `spec-kitty agent action review` as the per-decision verbs the agent invokes. The text MUST NOT name top-level `spec-kitty implement` as a canonical user-facing command. (FR-004)
5. **Lock the deterministic file-set contract**: after `init`, the file set MUST equal the documented set; any new test that runs `init` MUST list the expected files explicitly. (FR-005)
6. **Idempotency / fail-fast on re-run**: extend `init.py` to detect a previously-initialized directory (e.g., presence of `.kittify/config.yaml` with same agent set) and either no-op or fail with a clear message. (FR-006)
7. **Refuse to touch git state inside an existing repo**: when invoked inside a git repo, `init` MUST NOT call `git init`, MUST NOT create any commits, MUST NOT stage anything. Just files. (FR-007)
8. **Update `init --help` text** to describe the new model accurately. (FR-008)

**Tests**:
- Extend `tests/init/test_init_minimal_integration.py` with assertions: no `.git/`, no `.agents/skills/`, no commit (FR-001..FR-003).
- Add `tests/init/test_init_next_steps.py` (NEW) — capture stdout, assert it names `spec-kitty next` and `spec-kitty agent action implement/review`, assert top-level `spec-kitty implement` is **not** named as a canonical user-facing command (FR-004, FR-501).
- Add `tests/init/test_init_in_existing_repo.py` (NEW) — set up a temp repo with an existing `.git/`, run `init`, assert no git state changed (FR-007).
- Add `tests/init/test_init_idempotent.py` (NEW) — re-run `init` in an already-initialized directory, assert idempotent or fail-fast with clear message (FR-006).

**Risks**:
- R-1.1: Existing tests in `tests/init/` may rely on the auto-git-init side effect for setup (e.g., to assert files are tracked). Need to update their fixtures, not just delete the call.
- R-1.2: The `.agents/skills/` removal may surface in skill-discovery downstream code that assumes the directory exists. Phase 0 research shows skills are projected per-agent via `install_skills_for_agent()`, so this should be safe — but the removal must be verified end-to-end.

### Track 2 — Planning-artifact producer correctness (FR-101..FR-106)

**Change shape**:
1. **Stop filtering at `compute.py:254-276`**. The branch that splits `code_wp_ids` from `planning_artifact_wps` is removed. Every WP — code or planning-artifact — flows into the lane assignment algorithm.
2. **Introduce a canonical `lane-planning` lane**. When `compute_lanes()` encounters a WP whose `manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT`, it assigns it to a single per-mission `lane-planning` lane (lane_id = `"lane-planning"`). The lane's `write_scope` is the union of planning-artifact owned-files globs; `predicted_surfaces` is the union; `depends_on_lanes` is empty by default; `parallel_group` is its own group (planning artifacts run in the planning workspace, parallel to code lanes).
3. **`lane-planning` resolves to the main repo checkout**, not a worktree. This is enforced in two places:
   - `branch_naming.py`: `lane_branch_name(mission_slug, "lane-planning")` returns the planning branch (the current target branch from `meta.json`), **not** a `kitty/mission-<slug>-lane-planning` branch.
   - `worktree.py`: the lane-resolution path that maps lane-planning to a workspace returns `repo_root` directly (no `git worktree add` call). The existing `create_planning_workspace()` helper (`worktree.py:135`) is the right hook.
4. **Collapse the consumer special-case branch in `context/resolver.py:174-182`**. Today:
   ```python
   if execution_mode == "planning_artifact":
       authoritative_ref = None
   else:
       lane = require_lanes_json(feature_dir).lane_for_wp(wp_code)
       authoritative_ref = lane_branch_name(mission_slug, lane.lane_id)
   ```
   New shape:
   ```python
   lane = require_lanes_json(feature_dir).lane_for_wp(wp_code)
   if lane is None:
       raise MissingIdentityError(...)
   authoritative_ref = lane_branch_name(mission_slug, lane.lane_id)
   ```
   The lane lookup uniformly returns the planning lane for planning-artifact WPs; `lane_branch_name` uniformly returns the planning branch for `lane-planning`. No type-branching at the consumer.
5. **`workspace_context.py` and `worktree.py`**: the same collapse — lane lookup is uniform; lane-to-workspace resolution branches on `lane_id == "lane-planning"`, which is a lane-model fact, not a WP-type fact.
6. **`LanesManifest.planning_artifact_wps`**: keep this field as a **derived view** (computed from the lane assignments) for backwards compatibility with the manifest schema, but mark it deprecated in the model docstring. Removing it entirely is OUT OF SCOPE for this mission (would touch historical lanes.json files in fresh clones — that's archaeology adjacent). Plan: keep as derived, update docstring to point at the new model.
7. **`implement.py:_ensure_planning_artifacts_committed_git()` (lines 179-200)**: keep the planning-artifact-aware git semantics (commit to the planning branch in the main repo checkout), but route through the new uniform lane lookup. The function's name and behavior stay; only its lane-resolution input changes.

**Tests**:
- `tests/lanes/test_compute_planning_artifact.py` (NEW): build a mission with at least one planning-artifact WP and at least one code WP; call `compute_lanes()`; assert the planning-artifact WP receives lane_id `"lane-planning"`; assert the code WP receives a `lane-a`/`lane-b` style id; assert `LanesManifest.planning_artifact_wps` is consistent with the lane assignment.
- `tests/lanes/test_branch_naming_planning.py` (NEW): assert `lane_branch_name(mission_slug, "lane-planning")` returns the mission's planning branch, not `kitty/mission-<slug>-lane-planning`.
- `tests/context/test_resolver_planning_artifact.py` (NEW): exercise `resolve_authoritative_ref` for a planning-artifact WP; assert no `MissingIdentityError`; assert the returned ref is the planning branch.
- `tests/agent/cli/commands/test_implement_planning_artifact.py` (NEW): exercise `spec-kitty implement WP##` for a planning-artifact WP via the slash-command runtime; assert it lands in the main repo checkout, not a worktree.

**Risks**:
- R-2.1: Removing `LanesManifest.planning_artifact_wps` is tempting for clean architecture but breaks historical `lanes.json` consumers and contradicts NG-1 (no archaeology). Plan: keep as derived view, never write it from the producer side as the source of truth.
- R-2.2: `branch_naming.py` may be used by tools other than the resolver (e.g., the merge command). Need to verify `lane-planning` doesn't trigger a worktree-create elsewhere. Phase 0 shows `worktree_allocator.py` is the only worktree-create path; it must check for `lane_id == "lane-planning"` and return `repo_root` instead of allocating.

### Track 3 — Mission identity Phase 1 (FR-201..FR-206)

**Change shape**:
1. **Mint `mission_id` at creation**. Edit `core/mission_creation.py:create_mission_core()` (around lines 289-309) to add:
   ```python
   from ulid import ULID
   meta.setdefault("mission_id", str(ULID()))
   ```
   The `mission_id` is a string-encoded ULID (the canonical lexicographic-sortable form). It is persisted at creation time and is immutable for the life of the mission.
2. **Stop using `get_next_feature_number()` for canonical identity allocation**. The function at `worktree.py:163-207` continues to exist as a **display-helper** for the numeric prefix (numeric prefix remains as a display-friendly index per FR-203), but the canonical identity is `mission_id`. This means: scanning `kitty-specs/` and `.worktrees/` is acceptable to compute the display prefix, but it MUST NOT be used to derive any machine-facing identifier.
3. **Add `mission_id` to `MissionIdentity` dataclass** at `mission_metadata.py:79-84`. Add as a required field (with a fallback `None` for legacy missions that don't have it — this is the **only** legacy-tolerance hook in the mission, and it exists solely so that historical missions can still be loaded for human-display purposes per NG-1).
4. **Add `mission_id` to `emit_mission_created()` payload** at `sync/events.py:235-245` and `sync/emitter.py:425-449`. Existing call sites that emit this event get updated to pass `mission_id`. The schema change is additive (new field, not replacing existing fields).
5. **Concurrency**: mission creation does not currently take a lock. Per FR-205, two concurrent creates from two checkouts MUST NOT collide on `mission_id`. ULID is by construction collision-resistant (128-bit, random tail), so this is satisfied without a lock. However, we still extend `core/mission_creation.py` to take the existing `feature_status_lock_path` lock during the `meta.json` write, to make the create-write transaction atomic and to prevent partial writes if two processes race.
6. **Backfill is OUT OF SCOPE** (NG-2). Existing missions without `mission_id` keep working as legacy-display via the `MissionIdentity` fallback. **Mission 079 itself currently has no `mission_id`** — Track 3's first WP MUST add it to its own `meta.json` so 079 dogfoods the new identity model.

**Tests**:
- `tests/core/test_mission_creation_identity.py` (NEW): call `create_mission_core` for a fresh mission; read `meta.json`; assert `mission_id` exists, is non-empty, and parses as a valid ULID.
- `tests/core/test_mission_creation_concurrent.py` (NEW): spawn two threads that call `create_mission_core` concurrently from two repos; assert their `mission_id` values do not collide and both `meta.json` writes complete cleanly.
- `tests/sync/test_emit_mission_created_includes_mission_id.py` (NEW): emit a mission-created event; assert the payload contains `mission_id`.
- Extend existing tests in `tests/core/` and `tests/agent/cli/commands/` that call `create_mission_core` to consume the new field.

**Risks**:
- R-3.1: Adding a new required-ish field to `MissionIdentity` may break callers that destructure the dataclass. Mitigation: add as a `mission_id: str | None = None` field (legacy-safe) so existing destructure patterns keep working; new flows treat `None` as a hard error.
- R-3.2: Concurrent `meta.json` write under `filelock.FileLock` may slow down test fixtures that create many missions in a tight loop. Mitigation: the lock is per-mission-slug (per the existing `feature_status_lock_path` pattern), so two different missions don't contend.

### Track 4 — Tasks/finalize hotfix (FR-301..FR-305)

**Change shape**:
1. **Bound `_split_wp_sections()` at `dependency_parser.py:39-59`**. The change replaces the EOF fallback with a stop pattern. Two implementation options were considered (see [research.md](research.md) for the rejected alternatives):
   - **Chosen**: scan forward from the WP header until either (a) the next WP header, (b) a top-level `## ` heading whose text is not a WP id (e.g., `## Notes`, `## Appendix`, `## Glossary`), or (c) EOF. This bounds the section against trailing prose without requiring a structural marker in `tasks.md`.
   - The bound regex is conservative — it only stops at headings that are clearly outside the WP namespace.
2. **Make explicit precedence explicit** (FR-302/FR-303). The parser currently does NOT do prose inference, but the conflict-detection / preserve logic in `agent/tasks.py:1923-1970` could in principle overwrite frontmatter with parsed values. Add a unit-level invariant: when a WP has an explicit `dependencies:` declaration in frontmatter, the parsed-from-prose value is used as a **diff input** for "disagree-loud" (T004), not as a replacement. The disagree-loud logic is preserved as-is.
3. **Add the FR-304 regression test** in `tests/core/test_dependency_parser.py`. Author a `tasks.md` with: a final WP that declares `dependencies: []` explicitly, followed by trailing prose containing `Depends on WP01`; assert the parser returns `WPN: []`, not `WPN: [WP01]`.
4. **Full manifest redesign is OUT OF SCOPE** (NG-3, FR-305). The plan does NOT introduce a new manifest, does NOT change the `tasks.md` authoring contract, and does NOT introduce a manifest-vs-prose precedence model beyond what already exists.

**Tests**:
- Extend `tests/core/test_dependency_parser.py` with the trailing-prose regression test (FR-304).
- Add a sibling test that exercises a `## Notes` heading immediately after the final WP — assert the parser stops at the heading.

**Risks**:
- R-4.1: The bound heuristic may stop too aggressively if a real WP section uses sub-headings like `### Implementation notes`. Mitigation: the bound only fires on `##` (top-level), not `###`, which keeps WP sub-structure intact. Verify with an existing tasks.md fixture.
- R-4.2: `disagree-loud` may begin firing on the new bounded inputs differently. Mitigation: re-run the existing 21 parser tests under the new bound; expected behavior is identical for them (none of them have trailing prose past the final WP).

### Track 5 — Auth refresh race fix (FR-401..FR-405)

**Change shape**:
1. **Extend the `FileLock` scope**. Today, `auth.py:_acquire_lock()` is called per-I/O inside `load()`/`save()`/`clear()`. The new pattern: `refresh_tokens()` (`auth.py:324-394`) acquires the lock at entry and holds it for the **full transaction** — read current credentials, perform the network call, parse the response, persist new credentials (or handle failure). The lock release is in a `finally` block.
2. **Re-read on 401**. Inside the locked transaction, on a 401 response:
   - Re-read on-disk credentials (under the same lock).
   - If the re-read shows the refresh token has changed since the request started (i.e., another process rotated it while our network call was in flight), treat the 401 as **stale** and exit cleanly without clearing.
   - If the re-read shows the refresh token is unchanged, the 401 is authoritative and proceeds to clear credentials (still under the lock).
3. **Clearing under lock**. `clear_credentials()` is called only from inside the locked `refresh_tokens()` transaction; the standalone `clear()` (`auth.py:94-101`) keeps its own per-I/O lock for direct invocations (e.g., logout).
4. **Reentrancy**. `filelock.FileLock` is reentrant per-thread by default. The internal `load()` / `save()` calls inside the locked refresh transaction reacquire the lock (no-op since it's already held by the same thread). Verify this assumption with a test.
5. **Background sync compatibility**. The background sync service (`sync/background.py:315-335`) uses a `threading.Lock` to serialize its own ticks; this is orthogonal to the cross-process file lock. The plan does **not** change the threading lock. The cross-process file lock now correctly serializes refresh transactions across CLI processes and the background daemon.
6. **Tests**.

**Tests**:
- `tests/sync/test_auth_concurrent_refresh.py` (NEW): spawn two threads (or two subprocess calls) that race a refresh; mock the network so one wins (rotates the token) and the other gets a 401; assert the loser observes the rotated token on its re-read and exits cleanly without clearing.
- Add a test that exercises the locked-transaction path with a non-401 success: assert the lock is held for the full duration (use a sleep-and-poll on the lock file from a second thread).
- Add a test that exercises the locked-transaction path with a non-stale 401: assert credentials are cleared cleanly.

**Risks**:
- R-5.1: Holding the file lock across a network call introduces a worst-case latency floor of "request RTT". For non-contended refresh, this is the same as today (no change). For contended refresh, the second caller waits up to the 10s lock timeout. Mitigation: the lock timeout already exists at 10s; this is acceptable per NFR-002 (≤+50ms median, no worst-case constraint).
- R-5.2: A network hang under the held lock could deadlock other CLI invocations. Mitigation: the existing httpx client uses default timeouts; verify that timeout < lock timeout (10s) so the network call always returns before the lock is forced.

### Track 6 — Top-level `implement` de-emphasis (FR-501..FR-506)

**The canonical post-#555 path concretely**: Phase 0 research (see [research.md](research.md) §6 update) confirmed that the actual canonical user workflow is the **`spec-kitty next` loop**, not a renamed `/spec-kitty.implement` slash command. Specifically:

- **Loop entry**: `spec-kitty next --agent <name> --mission <slug>` (top-level command at `src/specify_cli/cli/commands/next_cmd.py:24`). Agents call this repeatedly. Each call returns a JSON decision with an `action` and a `prompt_file`.
- **Per-decision actions**: For an `implement` action, the agent invokes `spec-kitty agent action implement <WP> --agent <name>` (`src/specify_cli/cli/commands/agent/workflow.py:379`). For a `review` action, `spec-kitty agent action review <WP> --agent <name>` (`workflow.py:1156`). These are agent-facing instruction surfaces that display the WP prompt and manage lane state transitions.
- **Slash command templates already teach this**: `src/specify_cli/missions/software-dev/command-templates/implement.md:159` already says `**Next step**: \`spec-kitty next --agent <name>\` will advance to review.` The slash-command templates are the right model — the gap is in `init` next-steps, README, command help, and the docs.

**Important caveat**: `spec-kitty agent action implement` does internally delegate workspace creation to top-level `spec-kitty implement`. After Track 6 lands, top-level `spec-kitty implement` is **strictly an internal implementation detail of `agent action implement`** — it is removed from the user-facing surface. The fact that the wrapper happens to call the legacy command is not a user-facing concern; Track 6's contract is about what users are taught, not about which Python function calls which.

**Change shape**:
1. **Update `init.py:641-650`**. Replace the slash-command list with a short teach-out that tells users (and the agent driving the user) to invoke the `spec-kitty next` loop. Concrete example replacement text: a "Next steps" panel that names `spec-kitty next --agent <agent> --mission <slug>` as the canonical loop entry, names `spec-kitty agent action implement` and `spec-kitty agent action review` as the per-decision verbs, and DOES NOT name top-level `spec-kitty implement` at all.
2. **Update `README.md:8-9`**. The current canonical-workflow line (`\`spec\` -> \`plan\` -> \`tasks\` -> \`implement\` -> \`review\` -> \`merge\``) is rewritten to show the actual post-#555 flow: `\`spec-kitty.specify\` -> \`spec-kitty.plan\` -> \`spec-kitty.tasks\` -> \`spec-kitty next\` (loop) -> \`spec-kitty merge\``. The mermaid diagram (lines 64-80 per research) is updated to remove the `⚡ Implement | Agent workflows` cell that names `implement`, replacing with `spec-kitty next` as the loop step.
3. **Update `spec-kitty implement --help`**. The docstring at `cli/commands/implement.py:389` is rewritten to mark the command as **internal infrastructure** (not user-facing). Example new docstring: `"""Internal — allocate or reuse the lane worktree for a work package. This is an implementation detail of \`spec-kitty agent action implement\`. Users should invoke \`spec-kitty next\` to drive a mission; agents should invoke \`spec-kitty agent action implement\`. This command remains as a compatibility surface for direct callers and is not part of the canonical 3.1.1 user journey."""`. The command continues to run unchanged for direct invokers (FR-505).
4. **Update slash-command templates** under `src/specify_cli/missions/software-dev/command-templates/`:
   - `implement.md`: research shows this template already teaches `spec-kitty next --agent <name>` at line 159. Audit the rest of the file for any remaining top-level `spec-kitty implement WP##` invocations and replace them with `spec-kitty agent action implement <WP> --agent <name>` (the agent-facing wrapper that takes care of workspace creation). The slash command itself (`/spec-kitty.implement`) is preserved as a slash-command surface, but its body teaches the agent to invoke `spec-kitty agent action implement`, not top-level `spec-kitty implement`.
   - `tasks.md`, `tasks-packages.md`, `tasks-outline.md`, `specify.md`: research already shows these teach `spec-kitty next` as the next step. Audit any remaining `spec-kitty implement WP##` examples in command bodies and replace them with `spec-kitty agent action implement` or remove if no longer needed.
5. **Update getting-started docs** under `docs/`. Per Phase 0 research, ~12 doc files name top-level `spec-kitty implement` in their first ~5 paragraphs. This mission updates only the **canonical-path** mentions (where `implement` is presented as the recommended user path); references in troubleshooting / recovery / how-to-deeply contexts are left alone if they describe the command as an internal detail. The replacement names `spec-kitty next` as the loop and `spec-kitty agent action implement/review` as the per-WP actions.
6. **Do NOT change `cli/commands/implement.py` execution behavior** (FR-505). The command continues to allocate worktrees and do its work. Only the help string and canonical-path narrative change. `spec-kitty agent action implement` continues to call into it internally — that delegation is an implementation detail, not a user-facing contract.

**Why this satisfies D-4**: D-4 requires that top-level `spec-kitty implement` is no longer the canonical path advertised to new users. After Track 6:
- `init` output names `spec-kitty next` as the loop entry; users never see `spec-kitty implement` recommended.
- `README.md` names `spec-kitty next` as the canonical workflow step.
- `spec-kitty implement --help` marks the command as internal infrastructure.
- Slash-command templates teach `spec-kitty next` as the loop and `spec-kitty agent action implement` as the per-decision verb.
- Top-level `spec-kitty implement` continues to RUN for compatibility (FR-505) but is removed from the user-facing teach-out at every surface that previously named it as canonical.
- `#538`, `#540`, `#542` (top-level `implement` stabilization issues) remain open for a later release; this mission does not partially fix them (FR-506).

**Tests**:
- `tests/agent/cli/commands/test_implement_help.py` (NEW): invoke `spec-kitty implement --help`; assert the output names "compatibility surface" and references the slash-command path.
- Extend `tests/init/test_init_next_steps.py` (Track 1) with assertion: top-level `spec-kitty implement` is not named in init's next-steps.
- A README content test: assert `README.md` does not contain the literal text `\`implement\`` in the canonical workflow line. (Or a more semantic check.)

**Risks**:
- R-6.1: The slash-command guidance update (`missions/software-dev/command-templates/`) needs to be re-deployed to existing projects via migration. The mission CLAUDE.md note explicitly says edit SOURCE templates, not generated copies. Confirm the migration mechanism still picks them up.
- R-6.2: Touching `README.md` may cause merge conflicts with concurrent doc work. Mitigation: keep the README change minimal — just the canonical-workflow line.

### Track 7 — Repo dogfood / version coherence (FR-601..FR-606, NFR-005)

**Change shape**:
1. **Bump `.kittify/metadata.yaml` version**. Update `:6` from `3.1.1a2` to `3.1.1a3` (matching pyproject) and then to `3.1.1` at the release-cut WP. The bump is an explicit WP, not an automatic side effect of any other change.
2. **Add the `.kittify/metadata.yaml` ↔ `pyproject.toml` sync check**. Extend `scripts/release/validate_release.py` (currently 389 lines) with a new function `validate_metadata_yaml_version_sync(repo_root)` that:
   - Reads `pyproject.toml` `[project].version`
   - Reads `.kittify/metadata.yaml` `spec_kitty.version`
   - Asserts they are equal; reports the mismatch with both file paths and line numbers if they disagree.
   - The function is called from `validate_release.py:main()` in branch mode.
3. **Surface the FR-606 CHANGELOG-entry-presence check**. The existing `changelog_has_entry(changelog, version)` function in `validate_release.py:179-194` already does this; just ensure it is called for the target version (`pyproject.toml` version) on every branch-mode validate, not only on tag-mode.
4. **Surface the FR-605 structured draft artifact**. The existing `build_release_prep_payload()` in `src/specify_cli/release/payload.py` already produces a structured draft. This mission adds:
   - A CLI affordance to invoke it explicitly: `spec-kitty agent release prep --channel stable --json` (already exists per Phase 0 research) — verify it works against the working repo and surfaces a non-empty proposed CHANGELOG block whose header references the target version.
   - A test that asserts the payload structure is valid (FR-605).
5. **Wire the CI gate**. `.github/workflows/release-readiness.yml` already calls `validate_release.py`. The new metadata-yaml sync check is automatically picked up. No new workflow file is needed.
6. **Release-cut WP does the version bumps but NOT the tag**. Per the user's CLAUDE.md, `git tag v3.1.1` and PyPI publish are human actions. Track 7's WPs stop at: bumped versions in both files + green CI + structured draft generated + dogfood proof.

**Tests**:
- `tests/release/test_validate_metadata_yaml_sync.py` (NEW): create a temp repo with pyproject + metadata.yaml; call the validator; assert it passes for matched versions and fails for mismatched versions.
- `tests/release/test_validate_changelog_entry.py` (NEW or extend): assert the CHANGELOG-presence check fires on branch mode and accepts/rejects entries correctly.
- `tests/release/test_release_payload_draft.py` (NEW): call `build_release_prep_payload(channel="stable")` against the working repo; assert the returned payload has a `proposed_changelog_block` field that is non-empty and starts with `## [3.1.1`.

**Risks**:
- R-7.1: If the new metadata-yaml sync function does not fit cleanly into `scripts/release/validate_release.py`, extract it to `src/specify_cli/release/coherence.py` and import from the script. This is a low-risk refactor.
- R-7.2: The CHANGELOG-entry-presence check may misfire if the human release engineer hasn't yet added the `3.1.1` entry. Mitigation: this is the **intended behavior** — the check fails the cut until the entry exists. The error message must be clear and actionable.

---

## 7. Phase 1: Design & Contracts

### 7.1 Data model

See [data-model.md](data-model.md). Conceptual entities:
- **Mission** (with new `mission_id` field)
- **Work Package** (no schema change, but execution-mode handling unifies via lane)
- **Lane** (with new canonical `lane-planning` lane id)
- **Mission Identity** (`MissionIdentity` dataclass adds `mission_id` field)
- **Credential** (no schema change, but lock-scope contract changes)
- **Init Model** (canonical post-init file set)
- **Release Cut** (validation gates)

### 7.2 Contracts

The contracts directory describes the boundary contracts the implementation must satisfy. There are no REST/GraphQL contracts in this mission — the surface is CLI commands, file formats, and test scenarios. See:

- [contracts/cli-contracts.md](contracts/cli-contracts.md) — per-track CLI behavior contracts
- [contracts/file-format-contracts.md](contracts/file-format-contracts.md) — `meta.json`, `lanes.json`, `.kittify/metadata.yaml`, `~/.spec-kitty/credentials` schema expectations
- [contracts/test-contracts.md](contracts/test-contracts.md) — regression test scenarios that must pass

### 7.3 Quickstart

See [quickstart.md](quickstart.md) — operator validation walkthrough. The walkthrough exercises every track end-to-end against `/private/tmp/311/spec-kitty` and is the dogfood acceptance gate (S-7 / V-7 from `spec.md`).

### 7.4 Agent context update

Agent context for the active runtime is updated automatically by the spec-kitty harness when this plan commits. No manual script invocation is required.

---

## 8. Phase 1: Verification Matrix (FR → Test)

| FR | Test file (planned) | Acceptance scenario |
|----|---------------------|---------------------|
| FR-001..FR-003 | `tests/init/test_init_minimal_integration.py` (extend) | S-1: no .git/, no commit, no .agents/skills/ |
| FR-004, FR-501 | `tests/init/test_init_next_steps.py` (NEW) | S-1, S-6: next-steps text content |
| FR-005 | `tests/init/test_init_minimal_integration.py` (extend) | S-1: deterministic file set |
| FR-006 | `tests/init/test_init_idempotent.py` (NEW) | S-1 edge case: re-run idempotency |
| FR-007 | `tests/init/test_init_in_existing_repo.py` (NEW) | S-1 edge case: existing repo |
| FR-008 | `tests/init/test_init_help.py` (NEW or extend) | S-1: help text |
| FR-101..FR-103 | `tests/lanes/test_compute_planning_artifact.py` (NEW) | S-4: lane assignment |
| FR-104..FR-105 | `tests/context/test_resolver_planning_artifact.py` (NEW) | S-4: consumer uniformity |
| FR-106 | All Track-2 test files | S-4: regression coverage |
| FR-201..FR-204 | `tests/core/test_mission_creation_identity.py` (NEW) | S-3: mission_id at creation |
| FR-205 | `tests/core/test_mission_creation_concurrent.py` (NEW) | S-3 edge case: concurrent create |
| FR-206 | (no test — out of scope assertion via PR review) | NG-2 |
| FR-301 | `tests/core/test_dependency_parser.py` (extend) | S-2: section bound |
| FR-302..FR-303 | `tests/core/test_dependency_parser.py` (extend) | S-2: explicit precedence |
| FR-304 | `tests/core/test_dependency_parser.py` (extend) | S-2: trailing-prose regression |
| FR-305 | (no test — out of scope assertion via PR review) | NG-3 |
| FR-401..FR-403 | `tests/sync/test_auth_concurrent_refresh.py` (NEW) | S-5: lock contract |
| FR-404 | `tests/sync/test_auth_concurrent_refresh.py` (NEW) | S-5: race regression |
| FR-405 | (release gate, not a test) | RG-5 |
| FR-501 | `tests/init/test_init_next_steps.py` (NEW) | S-6: init output content |
| FR-502 | `tests/docs/test_readme_canonical_path.py` (NEW or content check) | S-6: README content |
| FR-503 | `tests/agent/cli/commands/test_implement_help.py` (NEW) | S-6: --help text |
| FR-504 | `tests/missions/test_command_templates_canonical_path.py` (NEW or content check) | S-6: slash-command guidance |
| FR-505 | `tests/agent/cli/commands/test_implement_runs.py` (extend existing) | S-6: command still runs |
| FR-506 | (no test — out of scope assertion via PR review) | NG-7 |
| FR-601 | `tests/release/test_validate_metadata_yaml_sync.py` (NEW) | S-7: version coherence |
| FR-602 | `tests/release/test_validate_metadata_yaml_sync.py` (NEW) | S-7: cut fails on mismatch |
| FR-603..FR-604 | `tests/release/test_dogfood_command_set.py` (NEW) | S-7: command set runs cleanly |
| FR-605 | `tests/release/test_release_payload_draft.py` (NEW) | S-7: structured draft shape |
| FR-606 | `tests/release/test_validate_changelog_entry.py` (NEW or extend) | S-7: CHANGELOG entry presence |

---

## 9. Re-evaluated Charter Check (post-Phase-1 design)

| Charter directive | Post-design status |
|-------------------|--------------------|
| `DIRECTIVE_010` Specification Fidelity | ✅ Verification matrix in §8 maps every spec FR to a test. No deviation. |
| `DIRECTIVE_003` Decision Documentation | ✅ Per-track design notes in §6 capture material decisions. Rejected alternatives are in [research.md](research.md). |
| `requirements-validation-workflow` | ✅ Tests planned at the level of each FR, including the explicit out-of-scope FRs (FR-206, FR-305, FR-506) which are tracked as PR-review assertions, not test code. |
| `adr-drafting-workflow` | ✅ No new ADRs planned. Track 3 implements the existing ULID identity ADR (`b85116ed`); Track 2 follows the established lane-contract model. If implementation reveals a need for a new ADR (Track 7 release-validation workflow), the implementation phase will draft one before merge. |
| Charter tooling (typer, rich, ruamel.yaml, pytest, mypy) | ✅ No new dependencies introduced. |
| ≥90% coverage on new code | ✅ Per-track test plans support this; verified at `/spec-kitty.review`. |

**Result**: Charter Check **PASSES** post-Phase-1 design.

---

## 10. Open Risks and Mitigations

| Risk | Track | Mitigation |
|------|-------|------------|
| R-1.1 | 1 | Existing init tests may rely on auto-git side effect; update fixtures, not just delete the call. |
| R-1.2 | 1 | `.agents/skills/` removal must not regress per-agent skill discovery. Verified end-to-end via test extension. |
| R-2.1 | 2 | Don't remove `LanesManifest.planning_artifact_wps`; keep as derived view to honor NG-1. |
| R-2.2 | 2 | Verify `branch_naming.py` "lane-planning" path doesn't trigger worktree creation in `worktree_allocator.py`. |
| R-3.1 | 3 | `MissionIdentity.mission_id: str | None = None` keeps existing destructure callers working. |
| R-3.2 | 3 | Per-mission lock contention is bounded; tests creating many missions don't share a lock. |
| R-4.1 | 4 | The `## ` bound stops only at top-level headings; sub-headings (`### `) inside a WP section are preserved. |
| R-4.2 | 4 | Re-run all 21 existing parser tests after the bound change; no behavior change expected for them. |
| R-5.1 | 5 | Lock-held network call latency is bounded by httpx default timeout < 10s file-lock timeout. |
| R-5.2 | 5 | Verify httpx client timeout < lock timeout to prevent deadlock. |
| R-6.1 | 6 | Slash-command template edits are at SOURCE files only (per CLAUDE.md); migration deploys to agent copies. |
| R-6.2 | 6 | README change is minimal (one line + diagram cell) to reduce conflict risk. |
| R-7.1 | 7 | If `validate_release.py` can't host the new check cleanly, extract `release/coherence.py`. |
| R-7.2 | 7 | CHANGELOG-presence failure is the intended behavior; error message must be actionable. |
| R-X.1 | All | Mission 079 itself currently has no `mission_id`. Track 3's first WP must add it to 079's own `meta.json` so the mission dogfoods the new identity model. |

---

## 11. WP Envelope Preview (NOT actual tasks)

The actual WP breakdown is generated by `/spec-kitty.tasks`. This preview is for sequencing sanity, not for implementation.

| Order | Track | WP-shape (preview) | Depends on |
|-------|-------|---------------------|------------|
| 1 | — | Mint `mission_id` for mission 079 itself (dogfood the new identity model up-front) | none |
| 2 | 1 | Remove `init_git_repo()` call path from `init.py`; remove commit string | none |
| 3 | 1 | Remove `.agents/skills/` seeding from `init.py` | WP-1 of Track 1 |
| 4 | 1 | Rewrite `init` next-steps output text | WP-1 of Track 1 |
| 5 | 1 | Add init regression tests (no-git, no-commit, no-skills, idempotent, in-existing-repo, next-steps) | WP-2..WP-4 of Track 1 |
| 6 | 4 | Bound `_split_wp_sections()` and add FR-304 regression test | none |
| 7 | 2 | Stop filter at `compute.py:254-276`; assign planning-artifact WPs to canonical `lane-planning` | none |
| 8 | 2 | Update `branch_naming.py` to handle `lane-planning` (resolve to planning branch) | WP of step 7 |
| 9 | 2 | Collapse `context/resolver.py:174-182` special-case branch | WP of step 8 |
| 10 | 2 | Update `worktree.py` / `workspace_context.py` to route `lane-planning` → main repo via lane lookup | WP of step 8 |
| 11 | 2 | Add Track 2 regression tests | WP of steps 7-10 |
| 12 | 3 | Mint ULID `mission_id` in `mission_creation.py`; persist to `meta.json` | none (independent of Track 2) |
| 13 | 3 | Add `mission_id` field to `MissionIdentity` dataclass; update `emit_mission_created` | WP of step 12 |
| 14 | 3 | Add Track 3 regression tests (mission_id present, ULID-shaped, concurrent non-collision) | WP of steps 12-13 |
| 15 | 5 | Extend `FileLock` scope across `refresh_tokens()` transaction; re-read on 401 | none (independent) |
| 16 | 5 | Add Track 5 concurrent-refresh regression test | WP of step 15 |
| 17 | 6 | Update `init.py:641-650` next-steps (overlap with Track 1 WP 4 — combine if possible) | (overlap) |
| 18 | 6 | Update `cli/commands/implement.py` `--help` docstring; mark compatibility surface | none |
| 19 | 6 | Update `README.md` canonical workflow line + mermaid; update slash-command source templates | none |
| 20 | 6 | Add Track 6 content/help tests | WP of steps 18-19 |
| 21 | 7 | Bump `.kittify/metadata.yaml` version to match `pyproject.toml` | none |
| 22 | 7 | Extend `scripts/release/validate_release.py` with metadata-yaml ↔ pyproject sync check | WP of step 21 |
| 23 | 7 | Add Track 7 regression tests (sync check, CHANGELOG presence, structured draft shape) | WP of step 22 |
| 24 | 7 | Dogfood acceptance check: run V-7 walkthrough end-to-end against `/private/tmp/311/spec-kitty` | all of the above |

Sequencing notes:
- Track 1 and Track 6 share the `init.py:641-650` next-steps edit. Plan to merge those two WPs into one to avoid double-edit churn.
- Track 2 and Track 3 are independent — they can run in parallel lanes.
- Track 4 is a tiny narrow-slice fix, ideal to land early.
- Track 5 is independent of all others — it can run in its own lane.
- Track 7's dogfood acceptance check (step 24) is the final WP and gates the release.

---

## 12. Branch Contract (Restated)

- **Current branch** at plan time: `main`
- **Planning/base branch**: `main`
- **Final merge target**: `main`
- `branch_matches_target`: **true**

This is the second statement of the branch contract per the plan-action protocol. No re-resolution needed.

---

## 13. Next Step

This command is **complete** after generating Phase 0 + Phase 1 artifacts. The next command is `/spec-kitty.tasks` to generate the actual task breakdown, executed by the user (not by this command).

**Generated artifacts**:
- `/private/tmp/311/spec-kitty/kitty-specs/079-post-555-release-hardening/plan.md` (this file)
- `/private/tmp/311/spec-kitty/kitty-specs/079-post-555-release-hardening/research.md`
- `/private/tmp/311/spec-kitty/kitty-specs/079-post-555-release-hardening/data-model.md`
- `/private/tmp/311/spec-kitty/kitty-specs/079-post-555-release-hardening/contracts/cli-contracts.md`
- `/private/tmp/311/spec-kitty/kitty-specs/079-post-555-release-hardening/contracts/file-format-contracts.md`
- `/private/tmp/311/spec-kitty/kitty-specs/079-post-555-release-hardening/contracts/test-contracts.md`
- `/private/tmp/311/spec-kitty/kitty-specs/079-post-555-release-hardening/quickstart.md`
