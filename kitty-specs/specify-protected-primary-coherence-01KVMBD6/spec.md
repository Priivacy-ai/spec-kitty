# Specification: Specify on Protected Primary + Branch-Protection Config

**Mission ID:** 01KVMBD6HTBP3A9Y5T4EQ80RA9 (`mid8` 01KVMBD6)
**Mission type:** software-dev
**Epic:** #1619 (Unify mission execution context across coord/main/lane topology) — P0 launch-blocker
**Status:** Draft

---

## Overview / Context

On a repository whose primary branch is named `main` or `master`, the **sanctioned**
`/spec-kitty.specify` flow currently **deadlocks** at the spec commit boundary. This was
reported by kentonium3 on epic #1619 (2026-06-19, stable 3.2.1) and reproduced **verbatim
and live on the current tree** (beyond 3.2.1 — not fixed by #2046/#2051/01KVGCE8) by a
debugger investigation.

The deadlock, using only sanctioned commands, on a `main`-named primary with
`--pr-bound --branch-strategy already-confirmed` (the operator deliberately staying on the
primary):

1. `mission create …` mints the coordination **branch** `kitty/mission-<slug>` but **no
   coordination worktree**; `spec.md`/`meta.json`/`status.events.jsonl` are written
   **untracked** on the primary.
2. The operator authors a substantive `spec.md`.
3. `spec-kitty safe-commit … <feature_dir>` is **refused**: "refusing to commit to protected
   branch 'main'. Use the coordination worktree at `.worktrees/<slug>-<mid8>-coord/` …" — but
   **nothing on the specify path materializes that worktree**, and `--to-branch` only asserts
   the HEAD already matches.

Two independent facts make this worse than first reported:

- **Protection is decided by branch *name* only** — a hardcoded `{main, master}` set — with no
  owner control. So the deadlock hits **every** repo whose primary is named `main`/`master` on
  the documented flow, not only GitHub-protected ones.
- **The runbook contradicts the guard.** The `software-dev` specify runbook instructs
  "specify works in the root checkout, no worktrees, commit to the target branch" via
  `safe-commit` — exactly the commit the guard structurally forbids on a protected primary.

The on-demand coordination-worktree materializer **already exists and works** (it was invoked
directly during the investigation and created the worktree cleanly). The bug is **path
coverage**: nothing on the specify path calls it before the spec commit, and the lifecycle
function that *does* materialize on demand for `plan`/`tasks` is never wired into the
top-level spec-time `safe-commit`.

This mission closes the deadlock from **both** directions and removes the underlying
brittleness:

- **(A) Deadlock fix** — materialize the coordination worktree on demand at the spec commit
  boundary (reusing the canonical materializer) so the protected-primary path actually works,
  and align the runbook so its instructions match the guard.
- **(B) Owner-configurable protection** — repository owners declare which branches are
  protected in `.kittify` configuration (default unchanged: `{main, master}`). An owner who
  marks the primary *unprotected* gets the documented "commit straight to the target branch"
  behavior with no worktree needed.
- **(C) Boundary-resolved configuration context** — the protected-branch set is resolved
  **once at the outermost system boundary** into a configuration-context object and propagated
  **inward**; core logic stops re-reading git/filesystem to make the protection decision.

This is a **distinct seam** from #2040's read/write surface-authority desync (that mission is
about two *materialized* surfaces disagreeing on state; here the coordination surface is never
materialized at all on the specify path, and the protection decision is hardcoded). They are
adjacent under epic #1619 but the fix lives in a different place.

---

## User Scenarios & Testing

### US1 — Operator completes specify on a protected primary (P0, MVP)

**Primary actor:** an operator running `/spec-kitty.specify` on a repository whose primary is
named `main`, staying on the primary (`--pr-bound --branch-strategy already-confirmed`).

**Happy path:** create the mission → author a substantive `spec.md` → run the sanctioned spec
commit. The coordination worktree is materialized on demand at the commit boundary and the
spec lands on the coordination branch. The operator is never deadlocked and never told to run
a command that does not work.

**Acceptance scenario (the kentonium3 repro):** on a `main`-primary repo, the four-step
sequence above completes through the spec commit using **sanctioned commands only** — **no**
manual git, **no** `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` hatch, **no** off-runbook
`git checkout -b feat/<slug>` detour. After the commit, `spec.md` is committed on
`kitty/mission-<slug>` (the coordination branch) and the working primary is clean.

### US2 — Owner configures which branches are protected

**Primary actor:** a repository owner editing `.kittify` configuration.

**Happy path:** the owner declares the protected-branch set in `.kittify` config. With the
primary marked **protected** (or config absent → default `{main, master}`), the spec commit
materializes/uses the coordination worktree (US1). With the primary marked **unprotected**,
the sanctioned spec commit lands **directly on the target branch** — matching the documented
"specify commits to the target branch, no worktrees" runbook — with no coordination worktree
required and no code change.

**Edge case:** config present but empty / lists a non-existent branch → resolved at the
boundary to a well-defined set (empty config = nothing protected; unknown names are simply not
matched); no crash, no silent fallback to the hardcoded default when config is explicitly set.

### US3 — Maintainer reasons about the protection decision from one place

**Primary actor:** a maintainer/agent extending a mutating command.

**Happy path:** every command that must refuse a commit to a protected branch reads the
protected-branch set from a single boundary-resolved **configuration context** handed to it,
not by re-reading the filesystem/git. Adding a new mutating command means consuming the
context, not re-implementing the protection lookup. A guard prevents a new direct
`protected_branches(repo_root)` / hardcoded-set decision from reappearing outside the resolver.

### Edge cases & exceptions

- **Create-window (#1718):** during the `create → first write` window the coordination
  surface is declared but may be unmaterialized; reads that must see the primary still resolve
  to the primary. Materialization is triggered at the **commit** boundary, not at read time.
- **Already-materialized coordination worktree:** the spec commit reuses it idempotently (no
  duplicate worktree, no error).
- **Non-protected feature branch (e.g. our own `fix/…` branch):** the spec commit lands
  directly on the current branch exactly as today — this mission changes nothing for
  feature-branch primaries.
- **Commit genuinely cannot proceed:** the error is **actionable** (it materializes-then-
  retries, or emits the exact sanctioned command) rather than pointing at a path that does not
  exist.

---

## Domain Language

| Term | Canonical meaning | Avoid |
|------|-------------------|-------|
| Protected branch | A branch the safe-commit guard refuses direct commits to; the **set is owner-configurable**, default `{main, master}` | "locked branch" |
| Coordination worktree | The on-demand `.worktrees/<slug>-<mid8>-coord/` checkout of the coordination branch where planning artifacts are committed under coord topology | "coord checkout" (ambiguous) |
| Configuration context | A boundary-resolved, immutable object carrying resolved repository/environment settings (incl. the protected-branch set), propagated inward to consumers | "config blob", "settings dict" |
| Boundary resolution | Resolving filesystem/git/config state **once** at the outermost system entry point, then threading the result inward | "lazy lookup", "re-resolve" |
| Spec commit boundary | The point in the specify flow where `spec.md` is committed (the deadlock site) | — |

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The specify-phase spec commit on a **protected** primary materializes the coordination worktree on demand and lands the spec on the coordination branch, completing with only sanctioned commands (no manual git, no env hatch, no off-runbook branch detour). | Draft |
| FR-002 | The materialization reuses the **canonical** on-demand materializer (`CoordinationWorkspace.resolve()` / the existing `_planning_commit_worktree` path that `plan`/`tasks` already use); **no parallel materialization path is introduced**. | Draft |
| FR-003 | When the spec commit cannot proceed on a protected primary, the surfaced error is **actionable** — it either performs the materialization-then-retry or emits the exact sanctioned command — instead of pointing at a coordination worktree that nothing materializes. | Draft |
| FR-004 | Repository owners can declare the set of protected branches in `.kittify` configuration. When the key is **absent**, the default protected set remains exactly `{main, master}` (no behavior change for existing repos). | Draft |
| FR-005 | When an owner marks the current primary as **not protected**, the sanctioned specify spec commit lands **directly on the target branch** (the documented runbook behavior) with no coordination worktree required and no code change. | Draft |
| FR-006 | The existing operator escape `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` is **preserved** (its role unchanged); this mission does not remove the solo-operator hatch. | Draft |
| FR-007 | The protected-branch set is resolved **once at the outermost system boundary** into a configuration-context object and propagated **inward**; core protection-decision logic performs **no** direct git/filesystem read for the protection set after boundary resolution. | Draft |
| FR-008 | The protected-branch set is carried by a **standalone, frozen value object** with a single `resolve(repo_root)` boundary resolver (decided post-squad — see `research/protected-branch-carrier-decision.md`). It is **not** nested as a sub-object on `ExecutionContext`/`WorkspaceContext` (the deadlock callsite holds no such parent; the only `ExecutionContext` factory fails closed without a mission). The object is cohesive (carries `protected_branches`, the resolved `operator_hatch_active` hatch state, and an `is_protected(ref)` method) and feeds the **existing** pure `commit_guard.evaluate(ProtectionState)` decision seam rather than introducing new decision machinery. Optional later attachment as an `ExecutionContext` fragment for in-loop callers is out of this mission's critical path. Final name is an implementation detail (avoid `EnvironmentContext` — collides with `os.environ`). | Draft |
| FR-009 | All current protected-branch decision callsites (the safe-commit guard plus the `protected_branches(repo_root)` / `assert_not_protected_branch(repo_root)` consumers in `coordination/policy.py`, `cli/commands/implement.py`, `cli/commands/agent/tasks.py`, `cli/commands/agent/mission.py`, `cli/commands/accept.py`, `acceptance/__init__.py`) read the protection set from the propagated context rather than a direct filesystem call. | Draft |
| FR-010 | A regression guard (architectural test) ensures **new** protected-branch decisions route through the context: a direct hardcoded-set or `protected_branches(repo_root)` decision introduced outside the single resolver/delegator set fails CI (binds #1868 "authority exists in name only"). | Draft |
| FR-011 | The `software-dev` specify runbook (`src/doctrine/missions/mission-steps/software-dev/specify/prompt.md`) is aligned so its instructions match the guard — a reviewer following it on a protected primary is never instructed to run a commit the guard refuses. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | No regression of the #1718 create-window contract. | The existing create-window invariant / equivalence tests remain green (0 new failures); a declared-but-unmaterialized coordination surface during the create→first-write window still resolves to the primary where the contract requires. | Draft |
| NFR-002 | On-demand materialization at the spec commit boundary adds no network round-trips and is bounded. | 0 network calls; materialization completes in < 2 s on a warm local repo (single coordination worktree). | Draft |
| NFR-003 | The protection decision is boundary-resolved, not re-read per call. | After boundary resolution, the protection-decision code path issues **0** filesystem/git reads for the protected-branch set (the context carries the resolved value). | Draft |
| NFR-004 | Default-config repositories behave identically to today. | For a repo with **no** `.kittify` protection key, protection behavior is byte-identical to current (`{main, master}` protected); the full regression suite is green. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Reuse the canonical `CoordinationWorkspace.resolve()` materializer; introducing a second materialization path is prohibited (canonical-sources discipline). | Draft |
| C-002 | Do not weaken the protected-branch guard: it must still refuse a direct commit to a **configured-protected** branch absent the sanctioned worktree path (or the preserved hatch). | Draft |
| C-003 | The configuration context follows the established immutable, boundary-built pattern (frozen, factory-constructed once); **no** post-build mutation. | Draft |
| C-004 | The `.kittify` configuration change is additive and backward compatible; existing configs without the protection key keep working unchanged. | Draft |
| C-005 | This mission is the **create-time materialization + protection-config** seam; it does **not** take on #2040's read/write surface-authority desync (a distinct seam under epic #1619). | Draft |
| C-006 | Mission is stacked on `pr-2051`; planning base and merge target are `fix/specify-protected-primary-coherence`. No version prescription (PO assigns at release). | Draft |

---

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | An operator on a primary named `main`/`master` completes `/spec-kitty.specify` end-to-end (spec committed) using only sanctioned commands — zero manual git, zero env hatch, zero off-runbook branch detour. (The kentonium3 repro passes.) |
| SC-002 | A repository owner can change which branches are protected via configuration and observe the specify commit honor it — protected primary → worktree path; unprotected primary → direct commit — with no code change. |
| SC-003 | Every protected-branch decision in the system resolves from the boundary-propagated configuration context; the protection-decision path performs no direct filesystem/git read for the protected set, enforced by a regression guard. |
| SC-004 | Repositories with no protection configuration see no behavior change: the default-protected set stays `{main, master}` and the existing regression suite is green. |
| SC-005 | The specify runbook and the protected-branch guard agree: a reviewer following the runbook on a protected primary is never instructed to run a command the guard refuses. |

---

## Key Entities

- **Protected-branch configuration** — a `.kittify` configuration key declaring the protected
  branch set; default `{main, master}` when absent.
- **Configuration context** — the boundary-resolved, immutable carrier that holds the resolved
  protected-branch set (and is the home for future repository/environment settings),
  propagated inward to consumers.
- **Coordination worktree** — the on-demand `.worktrees/<slug>-<mid8>-coord/` checkout where
  the spec commit lands under coord topology when the primary is protected.
- **Protected-branch guard** — the safe-commit decision point that refuses direct commits to a
  protected branch; now reads the configured set from the context.

---

## Assumptions

- The env hatch `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` remains a solo-operator escape and
  is not removed by this mission (FR-006).
- The carrier is **decided** (post-squad, 2026-06-21): a standalone, frozen, boundary-resolved
  value object feeding the existing `commit_guard.evaluate(ProtectionState)` seam — **not**
  nested on `ExecutionContext`/`WorkspaceContext` (the deadlock callsite holds no such parent).
  See `research/protected-branch-carrier-decision.md` for the full rationale and the ~8 callsites
  to route through the single resolver.
- "Protected" is determined by configuration + the existing name default, **not** by querying
  the GitHub branch-protection API (no network dependency); the owner declares intent in config.

## Out of Scope

- #2040's read/write mission-surface-authority desync (distinct seam; tracked separately).
- Real GitHub branch-protection API detection (explicitly replaced by owner-declared config).
- Changes to the `plan`/`tasks` materialization path, which already work (this mission only
  adds the missing **specify** call site and the shared context).

## Issues Addressed (issue-matrix seed)

| Issue | Relationship | Planned verdict |
|-------|-------------|-----------------|
| #1619 | Epic, P0 driver — the kentonium3 specify-deadlock repro is the headline acceptance scenario | in-mission |
| #1828 | Hatch-asymmetry between `assert_not_protected_branch` and `safe_commit` — folded into `ProtectionPolicy.is_protected()` (IC-01); de-facto fixed by PR #1850, pin a regression and close | in-mission (verify-and-close) |
| #1716 | Related — coordination topology coherence (this fixes the create→specify materialization facet) | references |
| #1868 | Related — canonical seams / "authority in name only"; bound by the FR-010 protection-decision guard | references |
| #1878 | Related — coordination placement/identity strangler umbrella; this discharges its specify-phase protected-primary evidence | references |
| #1829 | Divergent decision (delete the local guard wholesale) — **superseded** by this mission's configure-and-route approach (ADR 2026-06-21-1); **CLOSED not-planned 2026-06-21** with explanatory comment | references (closed-superseded) |
| #2040 | Out-of-scope boundary marker — read/write surface-authority desync is a distinct seam (C-005); shares only the IC-05 guard scaffolding | references (out-of-scope) |

## Dependencies

- Stacked on `pr-2051` (coord-topology orchestration + read-side resolver work already present).
- Canonical materializer `CoordinationWorkspace.resolve()` (exists, verified working).
- Existing `protected_branches()` / `assert_not_protected_branch()` seam and its ~7 callsites.
