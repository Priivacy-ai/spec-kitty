# Canonical Path-Trust & Guard-Capability Seams

**Mission ID:** `01KVBBT6FEQ01NHNSQD7X8JTPE` · **mid8:** `01KVBBT6`
**Epic:** #1868 (canonical seams — bind authority to type/owner) · **Closes:** #2022 · **Folds:** #2017 facet B8
**Type:** software-dev · **Merge target:** main (PR-bound)

## Purpose

Bind path-trust decisions to single canonical seams so callers inherit them, and close a CI gap that lets
architectural regressions through. Today the same two decisions — *"is this mission slug a safe path
segment?"* and *"is this resolved path under a trusted root?"* — are re-implemented divergently across
several callers while the canonical path-assembly primitive validates **nothing**; and the architectural CI
gate can be silently skipped on guarded-surface edits. This is the #1868 *"name proposes, authority
disposes"* anti-pattern. After this mission, the validation lives in the authority (so the next would-be
bypass is a test failure, not a silent regression), the containment logic lives in one parameterized
utility, and the architectural gate cannot be masked.

## Background — the disease (grounded in the pre-spec investigation)

A 4-agent profile-loaded investigation squad (randy-reducer census / debugger-debbie feasibility+CI
forensics / paula-patterns coherence+grain / planner-priti tracker; basis in `research/`) established:

- **Slug validation is scattered and divergent.** Three validators encode the same intent with different
  regexes and exception types: `merge.py::_validate_mission_slug_path_segment` (`^[A-Za-z0-9_-]+$`, no dots,
  raises `ValueError`), `coordination/transaction.py::_validate_safe_segment` (`^[A-Za-z0-9][A-Za-z0-9._-]*$`,
  allows dots, raises `BookkeepingError`), `status/aggregate.py::_validate_mission_slug`. Meanwhile the
  canonical path-assembly primitives `primary_feature_dir_for_mission` (`_read_path_resolver.py:397`) and
  `candidate_feature_dir_for_mission` (`:370`) compose `repo / KITTY_SPECS_DIR / mission_slug` with **zero**
  validation. Of ~75–143 call sites only **2** are guarded → a third caller (the #2019 sibling-seam) inherits
  nothing.
- **Containment logic is triplicated.** `merge.py` carries three `is_relative_to`-against-trusted-roots
  helpers (`_assert_status_path_within_target_surface`, `_assert_status_surface_path_is_trusted`,
  `_assert_bookkeeping_snapshot_path_is_trusted`) plus the generic `ensure_within_directory` (core.utils).
  Three are the same algorithm with different root sets.
- **The architectural CI gate is maskable.** A hardcoded short-circuit at `ci-quality.yml:1357-1371` runs
  *only* `test_execution_context_parity.py` for `execution_context`-only changes and `exit`s, skipping the
  rest of `tests/architectural/**`. Because `src/specify_cli/status/**` is in the `execution_context` filter
  but **not** `core_misc` (which carries `tests/architectural/**`), a status-surface edit runs
  `fast-tests-status` but **not** the rederivation ratchet — the live failure this session (the
  `_repo_root_for_lifecycle_log` fallback passed fast-tests, failed late in the architectural shard). The
  asymmetry: the ratchet runs when you edit the **guard**, not when you edit the **guarded surface**.
- **Some ratchet allow-lists are line-number-keyed** (`test_no_worktree_name_guess.py` pins `doctor.py:3074`/
  `:3166` + count baselines): a +1 line drift flips them silently. (One line-pin — `test_no_write_side_
  rederivation._ALLOW_LIST` at `status_transition.py:295` — is a deliberate, #1716-blocked deferral and is
  explicitly out of scope here.)

## User Scenarios

### US-1 — a malformed slug is refused at the authority, everywhere
A caller (operator handle, automation, or internal seam) passes `../escape`, `a/b`, or a non-ASCII slug to
*any* path-assembly site. The canonical primitive refuses it with a clear `ValueError` **regardless of which
caller** — including the #2019 sibling seams (`primary_feature_dir_for_mission` calls at `merge.py:803`/`:828`/
`:2382`, and the `kitty-specs/{slug}` interpolations at `:597`/`:599`/`:1853`/`:2746`) that PR #2019's point-fix
did not cover. (Line numbers verified against HEAD by the post-tasks squad; the earlier `:2332`/`:811`/`:2696`
citations were drift artifacts.)

### US-2 — a legitimate real-format slug still works
Full-ULID slugs, `<slug>-<mid8>` worktree dir names, numeric-prefixed (`034-feature`), and bare-mid8 handles
all validate unchanged. No existing on-disk mission breaks (the regex-reconciliation safety net).

### US-3 — one containment utility, three callers
The three `_assert_*_trusted` helpers delegate to one `ensure_within_any(path, roots, files)` kernel utility;
the rollback file-allowlist arm and the worktrees-XOR-kitty-specs conditional helper are preserved exactly
(no behavior change).

### US-4 — the architectural gate cannot be skipped
An edit to a guarded write-side surface (`status/**`, `coordination/**`, `core/worktree.py`) triggers the
**full** `tests/architectural/**` suite — the `_repo_root_for_lifecycle_log`-class regression would now fail
in-PR on the same trigger, not late in a separate shard.

### US-5 — a line drift no longer flips a ratchet
Inserting a blank/comment line above a pinned site in `doctor.py` (or renaming around it) does not flip the
re-keyed ratchets RED; only a genuine new offender does.

### US-6 — verification at the primitive, not the caller
The slug-validation tests prove rejection fires inside `primary_feature_dir_for_mission` /
`resolve_mission_read_path` directly (not only via a merge.py caller), so the guarantee holds for every
present and future consumer.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | **One Shared-Kernel slug validator (Goal A core).** Create a single mission-slug path-segment validator in `core/paths.py` (Shared-Kernel; no circular-import risk — paula). It MUST reject empty, `.`, `..`, `/`, `\`, and non-segment/traversal inputs, and raise `ValueError` (matches the existing contract + tests). Call it inside `primary_feature_dir_for_mission` (`_read_path_resolver.py:397`) AND once in `resolve_mission_read_path` so BOTH read primitives inherit validation. | Draft |
| FR-002 | **Migrate the divergent validators to delegate.** `merge.py::_validate_mission_slug_path_segment`, `coordination/transaction.py::_validate_safe_segment`, and `status/aggregate.py::_validate_mission_slug` MUST delegate to (or be deleted in favor of) the canonical validator — migrate, do not wrap (no parallel mechanism, C-001). | Draft |
| FR-003 | **Close the #2019 sibling-seam gap structurally.** Because validation now lives in the primitive, the unguarded sibling composers PR #2019 left open (`primary_feature_dir_for_mission` calls at `merge.py:828`/`:2382`, and the `f"kitty-specs/{mission_slug}/…"` interpolations at `:597`/`:599`/`:1853`/`:2746`) inherit the guard. A test MUST prove a malformed slug is rejected by **calling the named sibling functions directly** (`_assert_status_path_within_target_surface` / the `:2382` target-dir path), NOT only at `_target_bookkeeping_status_paths`. | Draft |
| FR-004 | **Reconcile the regex deliberately (the real decision).** The unified grammar MUST preserve the `.`/`..`/`/`/`\` traversal guard. `KEBAB_CASE_PATTERN` (`core/mission_creation.py:65`) is a subset of both existing regexes. A test MUST assert the **union of currently-valid real-format slugs** (full 26-char ULID, `<slug>-<mid8>` dir names, numeric-prefix, bare mid8) still validates after reconciliation — no regression on real on-disk missions. | Draft |
| FR-005 | **One parameterized containment utility (Goal B core).** Add `ensure_within_any(path, roots, files)` beside `ensure_within_directory` in `core/utils.py` (kernel util, NOT merge.py-local), standardizing on `resolve(strict=False)`. It MUST express root-set containment plus an optional exact-file allowlist arm. | Draft |
| FR-006 | **Collapse the merge containment helpers to delegate.** The two pure-root-set helpers (`_assert_status_path_within_target_surface`, `_assert_bookkeeping_snapshot_path_is_trusted` — the latter carrying its `.kittify/merge-state.json` exact-file arm) MUST delegate to `ensure_within_any`. The conditional-XOR helper `_assert_status_surface_path_is_trusted` (worktrees XOR kitty-specs by `is_under_worktrees_segment`) MUST be preserved as a *conditional caller* of the kernel util — its XOR selection MUST NOT be widened to a union (that is a behavior change). | Draft |
| FR-007 | **Un-mask the architectural CI gate (Goal C — #2017 B8).** The `integration-tests-core-misc (architectural)` shard MUST run the **full** `tests/architectural/**` suite whenever any guarded write-side surface OR an architectural guard's scan-root/allow-list changes — not only when `tests/architectural/**` itself changes. Concretely: add `src/specify_cli/status/**`, `src/specify_cli/coordination/**`, and `src/specify_cli/core/worktree.py` to the `core_misc` filter (`ci-quality.yml:174-195`), or exempt the `architectural` shard from the `:1357-1371` short-circuit. | Draft |
| FR-008 | **Re-key the non-#1716 line-number ratchet pins (Goal C — #2017 B8).** Re-key the line-number-keyed allow-lists in `test_no_worktree_name_guess.py` (`doctor.py:3074`/`:3166`, `invocation/executor.py`, and the count baselines) to an AST/qualname + normalized-token-line composite anchor (machinery already exists in the sibling `test_no_write_side_rederivation.py`). A +1 line drift or surrounding rename MUST NOT flip the ratchet; only a genuine new offender does. **`test_no_write_side_rederivation._ALLOW_LIST` (`status_transition.py:295`) is explicitly OUT of scope (C-007).** | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | **Behavior-preserving.** No trusted-root *set* changes; no caller re-routing; no write-topology/rollback-semantics changes; `ensure_within_directory` stays in `core.utils`. | Full suite green pre/post; no observable behavior delta for valid inputs. |
| NFR-002 | **Validation proven at the primitive, not the caller.** Rejection is tested by invoking the primitive directly, so the guarantee is independent of any caller. | A test exercises `primary_feature_dir_for_mission` / `resolve_mission_read_path` directly with malformed input. |
| NFR-003 | **Topology-true fixtures.** Production-shaped data only: full 26-char ULID `mission_id`, real coord-worktree topology where the seam touches it — no fabricated short ids/slugs. | 100% topology-true; real-format slugs in the union test. |
| NFR-004 | **The new guards are themselves drift-proof + CI-unmaskable (the meta-invariant).** The re-keyed ratchet (FR-008) must survive line drift; the CI fix (FR-007) must itself be covered so a future filter regression is caught. | A meta-test asserts the architectural shard's trigger covers the guarded surfaces; the re-keyed ratchet has a drift test. |
| NFR-005 | **Quality gates.** `ruff` + `mypy` clean, complexity ≤ 15, no suppressions. | CI-enforced; no `# noqa`/`# type: ignore` additions. |
| NFR-006 | **No regression on real missions.** The union of currently-valid real-format mission slugs still validates after the regex reconciliation. | Parameterized test over real-format slugs (ULID, `<slug>-<mid8>`, numeric-prefix, bare mid8); zero false rejects. |

## Constraints

| ID | Constraint |
|----|-----------|
| C-001 | **Bind to canonical seams; no parallel mechanism.** One validator in `core/paths.py`; one containment util in `core/utils.py`. Existing divergent validators migrate (delegate or delete), they do not coexist as wrappers. No new public resolver. |
| C-002 | **Behavior-preserving for A/B.** Goals A and B change *where* the decision lives, not *what* it decides. Goal C changes *how* guards are keyed/scheduled, not *what* they assert. |
| C-003 | **Final A+B+C grain decided in plan.** Goal C (guard-capability) is folded per operator decision (2026-06-17). If plan finds C is a staple-on (paula's coherence caveat — C is CI/test-infra, not the #1868 runtime-authority spine), the fallback is to split C to a child of #1931 / #1914. Resolve in plan, like Mission A's C-005. |
| C-004 | **No patch-version prescription.** Versioning is a PO/release call. |
| C-005 | **Edit canonical sources only.** `src/` runtime; CI edits touch `.github/workflows/ci-quality.yml`; test edits touch `tests/architectural/`. No generated agent copies. |
| C-006 | **Live-evidence + TDD-first.** Behavioral changes land test-first; the FR-007 CI fix is validated against the live `_repo_root_for_lifecycle_log`-class scenario, not static reading. |
| C-007 | **BINDING NON-GOALS.** (1) Do NOT re-route the ~143 callers of the path primitives, nor unify the two primitives — that is read-path-adoption (`01KV8NPC`) / naming-rider (`01KV7SFD`) work. (2) Do NOT touch `test_no_write_side_rederivation._ALLOW_LIST` (`status_transition.py:295`) — a deliberate, #1716-blocked line-pin. (3) Do NOT change trusted-root sets, write topology, or rollback semantics. |
| C-008 | **Fix, don't litigate (#1970 / DIRECTIVE_025).** Adjacent breakage an implementer hits in a touched file is fixed in the same change, not deferred-with-blame. |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A single slug validator exists in `core/paths.py`; both read primitives call it; the three divergent validators delegate to it (or are deleted); the full suite is green (FR-001/FR-002). |
| SC-002 | A malformed slug is **rejected at a #2019 sibling seam** (`merge.py:828`/`:2382`), proven by a test that calls the named sibling functions directly — not only at `_target_bookkeeping_status_paths` (FR-003). |
| SC-003 | The union of currently-valid real-format slugs (ULID, `<slug>-<mid8>`, numeric-prefix, bare mid8) still validates; zero false rejects (FR-004/NFR-006). |
| SC-004 | One `ensure_within_any(path, roots, files)` utility exists in `core/utils.py`; the two root-set helpers + the file-arm helper delegate to it; the XOR-conditional helper is preserved as a conditional caller; behavior byte-identical (FR-005/FR-006). |
| SC-005 | An edit to a guarded write-side surface triggers the **full** `tests/architectural/**` suite; the `_repo_root_for_lifecycle_log`-class regression would fail in-PR on that trigger; a meta-test pins the trigger coverage (FR-007/NFR-004). |
| SC-006 | The non-#1716 line-number ratchet pins are re-keyed to AST/qualname composites; a +1 line drift no longer flips them; `status_transition.py:295` is untouched (FR-008/C-007). |
| SC-007 | `ruff`/`mypy` clean, complexity ≤ 15, no suppressions (NFR-005). |

## Key Entities

- **`core/paths.py` slug validator** — the new canonical authority (FR-001); the single place the
  segment-safety decision lives.
- **`primary_feature_dir_for_mission` / `candidate_feature_dir_for_mission` / `resolve_mission_read_path`**
  (`_read_path_resolver.py`) — the path-assembly primitives that now inherit validation.
- **The 3 divergent validators** — `merge.py`, `coordination/transaction.py`, `status/aggregate.py` — migrate
  to delegate (FR-002).
- **`ensure_within_any` / `ensure_within_directory`** (`core/utils.py`) — the unified containment seam (FR-005).
- **The 3 merge containment helpers** — two delegate; the XOR-conditional one is preserved as a caller (FR-006).
- **`ci-quality.yml` path filters + the `:1357-1371` short-circuit** — the maskable architectural gate (FR-007).
- **`test_no_worktree_name_guess.py` line-pins** — re-keyed (FR-008). **`test_no_write_side_rederivation._ALLOW_LIST:295`** — out of scope (C-007).

## Tracker / Issue Matrix

| Issue | Title | Relation | Disposition |
|-------|-------|----------|-------------|
| #2022 | Consolidate merge.py path-trust into two canonical seams | the primary deliverable (Goals A+B) | in-mission |
| #2017 (B8) | Workflow guards lacking depth / blocking — facet **B8** (line-pinned ratchets + changed-paths CI masking architectural gate) | Goal C folds **B8 only**; A1–A4/B5–B7 stay in the umbrella | in-mission (facet) |
| #1868 | Epic: canonical seams exist in name only — bind authority to type/owner | the epic this is a concrete increment of; wire #2022 as a NATIVE sub-issue (currently prose-only) | in-mission (increment) |
| #2019 | Guard merge bookkeeping mission slug paths | the point-fix whose sibling-seam gap this closes structurally (FR-003) | verified-superseded |
| #1931 | EPIC: Test quality & suite hygiene | home for the scoped B8 fix child to be filed (FR-007/FR-008) | followup-child |
| #1716 | coordination topology authority | blocks the `status_transition.py:295` rederivation pin (out of scope, C-007) | deferred-cross-ref |
| #1914 | no-op-stable gates umbrella | C-staple-on fallback home if plan splits Goal C (C-003) | cross-ref |

**Meta-epic guardrails (priti):** #1796 is **CLOSED** — do not parent under it. #1479 is a **META-TRACKER** — never a
canonical functional parent. The B8 fix child goes under **#1931**, not under #2017 or #1796. Tickets are
claimed (claim-before-working) via planner-priti with a comment naming this mission on #2022 / #2017 / #1868;
the fresh B8 occurrence is already logged on #2017 (comment-4733691676).

## Assumptions

- The pre-spec investigation's census is accurate; a Phase-0 re-verification against the current branch HEAD
  confirms the exact line numbers before any edit (they may drift post-merge).
- Moving validation into the primitive is non-breaking for all current call sites (debbie: SAFE-TO-MOVE);
  the only inputs that newly raise are malformed ones that today silently build a bad path.
- The `ci-quality.yml` filter widening is sufficient to close the mask; a meta-test pins it so a future
  filter edit cannot silently re-open it.

## Out of Scope

- Re-routing the ~143 callers of the path primitives or unifying the two primitives (read-path-adoption
  `01KV8NPC` / naming-rider `01KV7SFD` work).
- Touching `test_no_write_side_rederivation._ALLOW_LIST` (`status_transition.py:295`) — #1716-blocked.
- The other #2017 facets (A1–A4, B5–B7) — they remain in the #2017 umbrella with their own fold/open
  dispositions (A1→#1734, A2/A4→#1914, A3→#1979, B5→#1795, B6→#1862, B7→#582).
- Any change to trusted-root *sets*, write topology, or rollback semantics.
