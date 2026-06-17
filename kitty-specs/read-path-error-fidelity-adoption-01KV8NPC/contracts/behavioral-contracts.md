# Behavioral Contracts — Read-Path / Error-Fidelity Adoption

These are the function-over-form contracts each IC must satisfy. They are observable behaviors, NOT
structure. Every contract has a topology-true test obligation (NFR-002): real 26-char ULID, real
coord-worktree, real git-submodule — no fabricated short ids, no single-repo stand-in. Verification of
adoption is by **deletion** of the bypass/shadow path with the contract suite staying green (NFR-003).

## C-IC01 — ExecutionContext invariant (FR-009)
- **MUST** raise `ActionContextError("CONTEXT_INVARIANT_VIOLATION", …)` if a context is built where
  `context.target_branch != branch_ref.target_branch`.
- **MUST** be immutable post-build (assigning `target_branch` on a built context raises).
- **MUST NOT** demand `branch_name == branch_ref.target_branch` (lane branch legitimately differs).
- **MUST NOT** introduce a new context type or retire the flat substrate.

## C-IC02 — `next` typed-error pass-through (FR-001/002)
- Given a read-path miss (coord_branch declared, no coord worktree), `spec-kitty next` (query + advance)
  **MUST** emit the resolver's real code (e.g. `STATUS_READ_PATH_NOT_FOUND` / `COORDINATION_BRANCH_DELETED`)
  and its checked paths, with a read-path remediation.
- **MUST NOT** emit `MISSION_NOT_FOUND` or a "run mission list" remediation for a read-path miss.
- The decision-answer path (`answer_decision_via_runtime`) **MUST** preserve the code identically.
- **Deletion proof:** removing the `MISSION_NOT_FOUND` collapse at the three catch-sites keeps the
  suite green (the typed envelope flows through).

## C-IC03 — `decision open` single authority (FR-003)
- Given a valid coord-aware handle, `decision open` **MUST** succeed (resolve through the single
  canonical resolver).
- **MUST NOT** reject it with "Mission path would escape kitty-specs/" nor surface an `ActionContextError`
  as a raw traceback.
- A raw operator token containing path traversal **MUST** still be rejected (`_SAFE_SLUG_RE`).
- **Deletion proof:** removing the escape-walk for resolved paths keeps coord + primary handles working.

## C-IC04 — planning-entry adoption (FR-004/005/006)
- **setup-plan**: with exactly one substantive mission present, **MUST** auto-select it (no `--mission`);
  with >1, **MUST** return the structured ambiguity/detection error (no silent fallback).
- **is_committed**: a spec committed on the primary target branch (coord branch lacking it) **MUST**
  report `spec_committed: true`; the diagnostic **MUST** list every ref/surface checked.
- **_commit_to_branch**: on success **MUST** report the real commit hash; a no-op against the wrong
  surface (artifact NOT present at the resolved placement) **MUST** surface a typed diagnostic, not a
  silent `commit_created: None`.
- **finalize-tasks**: **MUST NOT** fail-closed on a materialized-empty coord worktree before reading the
  primary surface (#11).

## C-IC05 — implement single resolution + #1993 (FR-008/011)
- `agent action implement WP##` after a successful claim **MUST** consume the claim's already-resolved
  context (single resolution path) and **MUST NOT** fail with "no workspace could be resolved" on a
  verified read-path.
- `resolve_lanes_dir(feature_dir)` **MUST** be the single derivation of the lanes dir; the 2-3 ad-hoc
  `feature_dir/lanes.json` joins **MUST** route through it.
- **Deletion proof:** removing the re-resolution call + the ad-hoc lanes joins keeps implement green.

## C-IC06 — root-resolver unification (FR-007)
- Invoked from inside a real git submodule (`.git` FILE), `resolve_canonical_root` **MUST** return the
  submodule root, identical to `locate_project_root`.
- `assert_initialized` from inside an initialized submodule **MUST NOT** raise
  `SPEC_KITTY_REPO_NOT_INITIALIZED`.
- **Equivalence:** parameterized over {primary, coord-worktree, submodule} the two resolvers agree (NFR-001).

## C-IC07 — charter status no-op (FR-010)
- `charter status` / `sync` status **MUST** be side-effect-free (no writes to the working tree; `git
  status` unchanged before/after).
- **MUST** emit one normalized hash that is JSON-serializable.

## C-FR012 — #1827 regression (test-only, D-3)
- A full `merge` record→commit→assert sequence INCLUDING a resume/re-run **MUST** pass (the assert reads
  the recorded baseline, not a re-derived HEAD). **No code fix** — this is a verified-already-fixed lock.
- The test **MUST** include a falsification guard proving the broken ordering would fail (so the green is
  trustworthy, per live-evidence discipline).
