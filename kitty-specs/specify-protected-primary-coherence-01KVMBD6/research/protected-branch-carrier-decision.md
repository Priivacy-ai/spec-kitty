# Design decision: protected-branch configuration carrier (pillar C)

**Date:** 2026-06-21
**Status:** DECIDED (operator, post-squad)
**Scope:** FR-007 / FR-008 / FR-009 / FR-010 (boundary-resolved protection config)

## Method

A 5-agent design squad evaluated the operator's initial proposal ("a new
`EnvironmentContext` nested as a sub-object on an existing context"): expert trio
(architect-alphonso, patterns-paula, randy-reducer, profile-loaded) + a dialectic
pair (Proponent thesis / Skeptic antithesis). All opus, code-grounded, read-only.

## Decisive finding (convergent — 4 of 5, conceded by the 5th)

**No protection callsite holds a built `ExecutionContext` at the decision point —
least of all the deadlock site.** The standalone `spec-kitty safe-commit` process
(`cli/commands/safe_commit_cmd.py`) carries no mission identity; the only
`ExecutionContext` factory, `resolve_action_context` (`mission_runtime/resolution.py`),
**requires** action+mission+wp and **fails closed with no fallback**. Therefore an
`EnvironmentContext` nested on `ExecutionContext` **cannot reach the very callsite the
mission exists to fix** without fabricating a mission context that does not exist.
Nesting on `WorkspaceContext` is worse — it is JSON-persisted per-WP
(`workspace/context.py` `save_context`/`to_dict`), so owner config would leak into
stale snapshots, breaking US2/SC-002.

## De-risking discovery

The boundary-resolved **decision** pattern already exists for this exact decision:
`core/commit_guard.py` `evaluate(target, ProtectionState(is_protected), capability)`
is pure / IO-free — the caller computes `ProtectionState` at the boundary and hands
it in. The bug is only that the **input** (`git/commit_helpers.py` `protected_branches(repo_root)`)
is re-read at the callsites (and re-shells `git remote show origin` via
`_remote_default_branch`). So pillar C is **lift the input to one resolver; route the
callsites through it** — the decision machinery is done, not to be reinvented.

`coordination/policy.py` already calls itself "the single chokepoint for protected-branch
refusal" (module docstring) yet still re-reads `protected_branches(repo_root)` at :214 —
a live #1868 "authority in name only" instance the FR-010 guard must close.

## DECISION

**Carrier shape: a standalone, frozen value object** (NOT nested on any existing
context as the primary carrier) with **one** `resolve(repo_root)` boundary resolver per
command entrypoint, passed **explicitly**, feeding the existing
`commit_guard.evaluate(ProtectionState)` seam. Replace — never parallel — the scattered
`protected_branches(repo_root)` reads.

**Object scope: cohesive 3-field** (earns its keep, folds duplication):
- `protected_branches: frozenset[str]` — resolved set (`.kittify` config ∪ name-default
  `{main, master}`; absent key → default; remote-default augmentation preserved on the
  default path only — see US2 empty-config edge case).
- `operator_hatch_active: bool` — resolved `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`
  state (FR-006), so the hatch is boundary-resolved too.
- `is_protected(ref) -> bool` — the one decision method, folding the duplicated
  `not hatch and ref in protected` idiom (appears at `commit_helpers.py:1017`,
  `policy.py:215`, `commit_helpers.py:519`).

**Naming:** NOT `EnvironmentContext` (collides with `os.environ` and the existing
`context.py` "environment = worktree-vs-code-change" meaning — Paula). Prefer
`ProtectionPolicy` / `RepositoryProtectionConfig` (final name a plan/implementation
detail).

**Composition (operator's original instinct):** explicitly **deferred / not primary**.
Optionally the value object MAY also be attached as an `ExecutionContext` fragment later
for in-loop callers (implement/tasks/accept) — a system-coherence bet (Alphonso/Thesis),
not required for the P0 and rejected as the primary carrier (Randy/Antithesis: churn +
scope-inversion for a repo-scoped value on an action-scoped composite). Not in this
mission's critical path.

**Deferred (do NOT pull in):** consolidating the four scattered `.kittify/config.yaml`
loaders (`core/agent_config.py`, `merge/config.py`, `charter_runtime/preflight/config.py`,
`retrospective/config.py`) behind one repository-settings object — a separate strangler
(Paula). Design the resolver with headroom but migrate loaders later.

## Boundary seams (for plan)

- **Primary (the deadlock):** `cli/commands/safe_commit_cmd.py` — resolve the policy right
  after `repo_root = _current_worktree_root()` / `_resolve_commit_target(...)`, pass into
  `safe_commit(...)`; the internal `protected_branches(repo_root)` + `protected_branches(worktree_root)`
  reads (`commit_helpers.py:1017-1020`) are replaced by `policy.is_protected(...)`. This is
  also where pillar A's `CoordinationWorkspace.resolve()` materialize-then-retry hooks.
- **Secondary (in-loop, optional fragment):** `build_execution_context`
  (`mission_runtime/resolution.py`) — only if the optional EC-fragment attachment is taken.
- FR-007 reads as **"resolved once per command entrypoint via the single sanctioned
  resolver,"** not one global bootstrap (there are two real process classes).

## Callsites to route through the resolver (FR-009) — ~8 reads

`git/commit_helpers.py:1017,1019` (safe_commit, ×2), `:527` (assert_not_protected_branch),
`coordination/policy.py:214`, `cli/commands/implement.py:59`, `cli/commands/agent/tasks.py:882,916`,
`cli/commands/agent/mission.py:898`, `cli/commands/accept.py:366`, `acceptance/__init__.py:1202`.
The sole resolver + `protected_branches()` delegator form the FR-010 allowlist; any other
direct `protected_branches(repo_root)` / hardcoded `{main, master}` decision fails CI.

## Key file anchors

- Decision seam (reuse): `core/commit_guard.py` `evaluate` + `ProtectionState`.
- Input today (lift to resolver): `git/commit_helpers.py:420,485-531,1017-1031`.
- EC + fragment pattern (optional secondary): `mission_runtime/context.py:177-261`,
  `mission_runtime/resolution.py:90-127`.
- No-fallback EC factory (why nesting fails at deadlock): `mission_runtime/resolution.py:855`.
- Persisted per-WP context (why not WorkspaceContext): `workspace/context.py:147-324`.
- `.kittify/config.yaml` reader pattern to mirror: `core/agent_config.py:47-122`.
