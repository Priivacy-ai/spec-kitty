# Research — Built-In Doctrine Seam Consolidation (Phase 0)

Consolidated from the 4-facet research squad + architecture design pass. The full briefs are in
`notes/research-synthesis.md`; the PR #3117 CI-failure ownership split is in
`notes/pr3117-ci-failures.txt`; the source issues are in `notes/source-issues.txt`. This file records
the design decisions that resolve every open question for the plan.

## Decision 1 — One built-in-location authority (`built_in_dir(kind)`)

- **Decision**: add `built_in_dir(kind: ArtifactKind) -> Path` to `src/doctrine/pack_paths.py`,
  returning `resolve_pack_root("built-in") / kind.plural`; route the 9 repository
  `_default_built_in_dir()` and the inline charter join sites through it.
- **Rationale**: built-in location is currently re-derived at ~25 sites via 5 mechanisms; the plural
  is hand-written at ~14. Deriving from `ArtifactKind.plural` (the existing SSOT) collapses them to
  one and kills the hardcoded-plural drift class. `pack_paths` importing `artifact_kinds` is safe
  (leaf, no back-import).
- **Alternatives considered**: leave per-repo joins (status quo — the whack-a-field surface the
  closed PR proved unbounded); a helper in each repo base class (still N copies of the plural).

## Decision 2 — Drop the fail-open `built_in_root` param

- **Decision**: remove `DoctrineService.built_in_root` and the nested `_built_in_dir`; repos
  self-resolve via Decision 1. Synthetic test tiers use the `SPEC_KITTY_PACKS_ROOT` env override.
- **Rationale**: `_built_in_dir` returns `root / kind / "built-in"` (pre-move shape) and fails OPEN —
  a real root silently loads zero artefacts. Redefining it as a "flat override that raises" keeps a
  second resolution path alive (the exact anti-pattern). Dropping it makes the wrong shape
  unconstructable. **Sizing**: only 20 files pass `built_in_root`; ~14 are coupled churn (6 already
  `None`, ~5 real-repo-stale = the FR-008 readers, ~9 nested-tmp → flat). The "~60-file" figure
  conflated the *different*, already-flat repository `built_in_dir=` param, which is NOT changed.
- **Alternatives considered**: keep a flat override (rejected — preserves a foot-gun API + a second
  authority).

## Decision 3 — `mission_step_contracts` = documented carve-out

- **Decision**: `built_in_dir(MISSION_STEP_CONTRACT)` RAISES a named error; step-contracts stay
  resolved via `importlib.resources` on `doctrine.missions.built_in_step_contracts`.
- **Rationale**: they were never relocated (they live under `missions/`, a kernel-layer `__file__`
  tree); relocating them IS #3091 (missions Phase-1b), deferred. Naming + gating the exception
  (raise) honours unification-not-parity — no silent second mechanism. The claim becomes "one seam
  across all file-based built-in kinds; step-contract is a documented package-resource exception."
- **Alternatives considered**: relocate step-contracts now (rejected — couples this narrow mission to
  a large deferred effort, violating narrow-COMPLETE).

## Decision 4 — CI-enforced single-authority ratchet

- **Decision**: add a `tests/architectural/` gate: (a) negative — no `src/` module outside
  `pack_paths.py` joins `resolve_pack_root("built-in")` or uses a `"built-in"` string path-part
  (AST-based, names the site); (b) positive — every shipped kind except the carve-out resolves inside
  `packs/built-in/<plural>/` and the dir exists, with a `#3091` carve-out marker; (c) anti-vacuity —
  the shipped `agent_profiles` set is non-empty.
- **Rationale**: convention is what let the relocation surface unbounded readers; the gate makes a
  sixth resolver fail CI instead of a future relocation. Mirrors `test_shared_package_boundary.py`.
- **Alternatives considered**: rely on review (rejected — the whole mission exists because convention
  failed).

## Decision 5 — Activation-vocabulary unification + live drift fix

- **Decision**: derive `charter_yaml_io._ACTIVATION_KEYS` and the finalize migration's
  `ACTIVATION_KEYS` from `pack_manager.YAML_KEY_MAP` (via a cheap exported plain-tuple constant); add
  a set-equality guard test. **Fix the live drift**: `m_unify_charter_activation_finalize.ACTIVATION_KEYS`
  is missing `activated_glossary_packs` (10 vs 11) → silently drops glossary activation on migration.
- **Rationale**: same root cause (vocabulary re-derived at the point of use); the drift is a real
  data-loss path. The migration's no-heavy-import constraint is honoured by exporting a plain tuple,
  not the pydantic-heavy import.
- **Cross-mission note (C-004)**: this must land before Mission 2's charter-resolver retarget, which
  trusts the activation store this migration writes.

## Decision 6 — Context.py shim retirement (severable) + provenance sweep (severable)

- **Decision (FR-011)**: re-point ~62 `from charter.context import _x` test imports to leaf modules;
  delete `context.py:25-145`. 0 production sites.
- **Decision (FR-012)**: sweep ~18 `packs/built-in/**` `related:`/`source_files:` old-path strings —
  **after** confirming they are descriptive, not runtime-resolved (grep for a "load related" reader;
  the research indicates descriptive). If runtime-resolved, escalate to FR-008.
- **Rationale**: lowest-risk, fully independent; both are the same "one source" theme. Severable so
  they can be their own WPs and never block the load-bearing seam work.

## Confirmed non-findings (de-risk the plan)

- The org-pack collision "regression" is **stale test setup** (`built_in_root=src/doctrine`), not a
  product bug — the collision pipeline is intact; the fix is the `built_in_root=None` path (IC-02).
- The product relocation is **essentially complete**; every shipped repo already self-resolves. The
  residue is test fixtures + operator strings + provenance + the two vestigial dead-in-prod paths.
- Only **7 of 41** PR #3117 CI failures are mission-owned; the other 34 are pre-existing/unrelated and
  are out of scope (C-002, SC-006) — including the accept-snapshot forgotten-regen.
