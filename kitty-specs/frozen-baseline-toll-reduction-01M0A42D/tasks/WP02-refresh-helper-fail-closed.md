---
work_package_id: WP02
title: Refresh helper + fail-closed match + non-fakeable regression
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- NFR-001
planning_base_branch: fix/frozen-baseline-toll-reduction
merge_target_branch: fix/frozen-baseline-toll-reduction
branch_strategy: Planning artifacts for this mission were generated on fix/frozen-baseline-toll-reduction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/frozen-baseline-toll-reduction unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
history:
- at: '2026-08-18T12:40:00+00:00'
  actor: claude
  note: WP created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/_refresh_dead_symbol_hashes.py
create_intent:
- tests/architectural/_refresh_dead_symbol_hashes.py
- tests/architectural/test_refresh_dead_symbol_hashes.py
execution_mode: code_change
owned_files:
- tests/architectural/_refresh_dead_symbol_hashes.py
- tests/architectural/test_refresh_dead_symbol_hashes.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). Apply its boundaries/directives/tactics. **ATDD red-first**; mypy `--strict` + zero new suppressions; complexity ≤ 15.

## Objective

Build `tests/architectural/_refresh_dead_symbol_hashes.py`: a helper that recomputes `body_hash` for allowlist entries whose symbol is **still dead** (so editing a dead symbol's body no longer forces a manual hash edit), and that is **structurally incapable of admitting a new dead symbol**. The safety property is proven by a regression that *runs the helper* — not by asserting outcomes an unsafe helper could also satisfy.

## Context (the hard part — read the contract before coding)

Authorities to reuse (single source of truth — do NOT re-implement hashing/deadness):
- **Still-dead set + new hash**: `test_no_dead_symbols._compute_offenders(decls, per_symbol, star_targets, allowlist=frozenset(), corpus, collision_index)` — with an **empty** allowlist it returns the full currently-dead `module::Name` set via the production aggregate path (def at `test_no_dead_symbols.py:~2025` post-rebase — **symbol-anchored, re-grep `def _compute_offenders`; do not trust the number**). New/edited key via `_resolve_final_key`. Tier via `key_tier`; collisions via `classify_collisions` (from `_symbol_key.py`).
- **`classify_collisions` returns ALL live `__all__` locations — it has NO deadness notion.** Deadness comes only from `_compute_offenders`. (Do not write "classify_collisions filtered to still-dead" — that is the mistake the post-plan squad caught.)
- Content-tier `SymbolKey` is **location-free** (`module_path=None`). Across a body edit the hash changes, so the **only** discriminator between "same symbol edited" and "different symbol, same `bare_name`" is the `module_path`, recovered from the WP01-normalized `# module::Name` provenance comment (source-parsed via `tokenize`, **as a fail-closed hint only, never for hashing**).

The full behavioral contract is `contracts/gate-behavior-contracts.md` §Contract A — implement to it verbatim.

## Subtasks

### T005 — Pure core `refresh(...)`
- `refresh(corpus, decls, per_symbol, allowlist_source) -> rewritten_source`. **Inject the corpus** (do not close over `_SRC_ROOT`) so the regression can construct a synthetic tree. Rewrites hashes **in place** in the allowlist source via `tokenize` (mypy-clean), **iterating existing entries only — never appending**.
- **Validation**: signature + "never append" invariant unit-covered.

### T006 — Wire the still-dead / hash authority
- Compute the still-dead set and the fresh key via `_compute_offenders(..., allowlist=frozenset())` + `_resolve_final_key`. No private hash recompute.
- **Validation**: a unit test shows the helper's dead-set equals the gate's for a known corpus.

### T007 — Fail-closed match
- Per existing entry `E`: recover identity-minus-hash (`bare_name` always; `module_path` from `E.module_path` for collision-tier, else from the normalized provenance comment for content-tier). Candidate set = still-dead live locations with matching `bare_name`, narrowed to `E`'s `module_path`. **Refresh iff exactly one still-dead candidate; else refuse** (0 → dangling, leave red; ≥2 → ambiguous; **unrecoverable `module_path` → refuse, NEVER bare-name-only corpus-wide match**). **Preserve the entry's tier** (a collision-tier entry keeps `module_path`).
- **Validation**: unit tests for each branch (exactly-one → refresh; 0 → refuse; ≥2 → refuse; unrecoverable → refuse).

### T008 — Entrypoint
- `python -m tests.architectural._refresh_dead_symbol_hashes` runs the refresh over the real tree and rewrites the allowlist source; on refusal it prints the ambiguous `bare_name` (never guesses). Confirm the `_`-prefixed module does not trip `test_no_dead_modules` (that gate is `src/`-scoped; `_symbol_key.py` is precedent).

### T009 — Non-fakeable NFR-001 / SC-006 regression (THE teeth — do not weaken)
In one run, over a constructed corpus:
- (a) **positive control**: a body-edited still-dead `X::Foo` **is** refreshed to its new `body_hash` (proves the admit branch actually ran).
- (b) a new still-dead `Y::Foo` (**same `bare_name`**, different module) is present, **not** admitted, and the gate REDs on `Y`.
- (c) **assert** `E`'s candidate set contained ≥2 `bare_name` matches narrowed to exactly `{X}` (proves the discrimination logic executed — guards against the F1 vacuity trap where the fixture is refused for an unrelated reason).
- (d) exercise **all four** Contract-A refuse branches by *running* the helper (incl. the 0-candidate dangling case).
- **Validation**: the regression fails against a deliberately-unsafe (bare-name-only) helper stub and passes against the real one. **The stub must fail for the RIGHT reason** (anti-mutation-trap): it differs from the real helper *only* in the `module_path`-narrowing step, so it **passes the positive control (a)** [still refreshes `X`] and fails **specifically on (b)/(c)** [admits `Y` / candidate-set not narrowed to `{X}`]. A stub that fails on (a) — returns `None`, raises, refreshes nothing — is a vacuous strawman and does NOT satisfy this.

### T010 — AC3 edge tests
- gained-a-caller, **body unchanged** → gate REDs with **`stale`**; helper does not refresh.
- gained-a-caller **+ body edit** → gate REDs with **`dangling`** (a body edit changes the content key so `_compute_stale` cannot match) — assert `dangling`, NOT `stale`.
- collision-tier refresh preserves `module_path` (tier preserved).

### T011 — Quality
- ruff + mypy `--strict` clean on both new files; zero new suppressions; every helper branch has a direct test; complexity ≤ 15.

## Branch Strategy

Base/merge target `fix/frozen-baseline-toll-reduction`. Worktree per computed lane (`lanes.json`); WP02 is `lane-b`, `depends_on_lanes: [lane-a]` (WP01). Implement via `spec-kitty agent action implement WP02 --agent claude`. **Approved-vs-merged caveat:** the dependency gate releases WP02 when WP01 is *approved*, not merged, and `lane-b` does not auto-rebase onto `lane-a`'s tip — so WP02's worktree can still hold an un-normalized allowlist. T005–T011/T009 run over a **synthetic injected corpus** and are unaffected, but before running the **real-tree entrypoint T008**, rebase `lane-b` onto WP01's landed normalization (or the real-tree refresh will merely *refuse* against un-normalized comments).

## Definition of Done

- Helper refreshes still-dead entries and **provably** cannot admit a new dead symbol: T009 green with the **positive control (a)** [X refreshed], the **collision non-admit (b)** [Y absent, gate reds on Y], and the **candidate-set ≥2→{X} assertion (c)** [proves the discrimination branch ran, not an unrelated refusal], plus all four refuse branches — and it **fails against a bare-name-only stub that passes (a) but fails (b)/(c)** (fail-for-the-right-reason).
- Fail-closed on 0/≥2/unrecoverable `module_path`; tier preserved; `stale` vs `dangling` correct per T010.
- ruff + mypy `--strict` clean; SC-002 ("exactly one invocation → gate green") holds for a refreshable entry.

## Risks & Reviewer Guidance

- **AC2 safety hinges on `module_path` recovery.** Reviewer: confirm there is **no** bare-name-only fallback path anywhere — the unrecoverable case MUST refuse. This is the silent-admit vector.
- Confirm T009 asserts the candidate-set narrowing (c), not just outcomes — outcomes alone are F1-vacuous.
- The helper imports from `test_no_dead_symbols.py` (WP01's file) but does not edit it — ownership stays disjoint.
