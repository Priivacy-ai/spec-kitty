# Tasks: Naming/Identity Routing Rider (+ #2007 Focus A drift guard)

**Mission:** `naming-identity-routing-rider-01KV7SFD` · **Branch:** `feat/naming-rider-3-2-1`
**Spec:** [spec.md](./spec.md) · **Plan:** [plan.md](./plan.md) · **Scope review:**
[scope-review/SCOPE-REVIEW-SYNTHESIS.md](./scope-review/SCOPE-REVIEW-SYNTHESIS.md)

7 work packages over the 6 implementation concerns. **Ownership is disjoint** (no two WPs share
`owned_files`); only **WP01 edits `branch_naming.py`**. **Testing is function-over-form + verification-by-
deletion**; the ratchet (WP02) is the sole form-coupled test and is sequenced **last** so it locks the
already-clean state with a minimal allow-list (no per-WP allow-list editing → clean ownership).

## Dependency graph / lanes

> **Reordered after the post-tasks adversarial squad (binding — fixes F-1, the `worktree_allocator.py`
> build-breaker).** The demotion (`mid8`→`_mid8`) lands **LAST**: route WPs target the already-public
> `resolve_mid8` first, so de-exporting `mid8` never breaks a cross-lane importer. See
> `tasks-review/POST-TASKS-SYNTHESIS.md`.

```
{WP03 (contract-sensitive routes + worktree_allocator) ┐
 WP04 (direct + 5-missed routes)                        ┼─► WP01 (demote mid8→_mid8, de-export) ─► WP02 (ratchet)
 WP05 (#2000 compose-routing)                          ┘
WP06 (#1888 TDD-verify + #1971-tail test)   [independent]
WP07 (#2007 Focus A: drift repoints + CI guard)  [independent]
```

- **WP03/WP04/WP05** have no deps — they route every external `mid8` consumer to the already-public
  `resolve_mid8` (disjoint files, parallel). **WP01** depends on WP03+WP04+WP05 (demotes `mid8`→`_mid8`
  + de-exports only after all external importers are migrated — the F-1 fix). **WP02** depends on WP01
  (ratchet references the final `_mid8`; the consumer class is empty, the seam HOMES are carved out at
  file level). **WP06** and **WP07** are independent and parallel to everything.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Rename `mid8`→`_mid8` (private); update 3 internal seam callers | WP01 | | [D] |
| T002 | Make `resolve_mid8` the sole public mid8 door; drop `mid8` from `__all__` | WP01 | | [D] |
| T003 | Preserve `resolve_transaction_mid8`/`resolve_mission_branch` + one-shot warning + reset seam | WP01 | | [D] |
| T004 | Behavioral tests: resolver contracts, one-shot warning, byte-parity of composed names | WP01 | | [D] |
| T005 | Route `status/aggregate.py:250` via `resolve_mid8` (preserve `""`) | WP03 | [D] |
| T006 | Route `dashboard/scanner.py:438` via `resolve_mid8(...) or None` (preserve `None`) | WP03 | [D] |
| T007 | `doctor.py:3070/3162` — conscious decision on the `try/except` short-id tolerance | WP03 | [D] |
| T008 | Route `implement.py:386` (preserve `meta["mid8"]` preference + `None`) | WP03 | [D] |
| T009 | Characterization tests pin current `""`/`None`/short-id output BEFORE change (TDD) | WP03 | [D] |
| T010 | Delete the WP03 inline shadow derivations (verification-by-deletion) | WP03 | [D] |
| T011 | Route the direct guaranteed-full-id sites (sparse_checkout, apply ×2, mission_resolver, retrospective_terminus) via `resolve_mid8` | WP04 | [D] |
| T012 | Route the 5 scope-review additions (resolution.py:171 `str(x)[:8]`, agent/mission.py:772 `raw_mid[:8]`, mission_type.py:643 `..._id_meta[:8]`, agent/workflow.py:292 `mid[:8]`, retrospective/generator.py:112 `mid[:8]`) | WP04 | [D] |
| T013 | Verify FR-002: no `ExecutionContext`-held site re-derives mid8 | WP04 | [D] |
| T014 | Delete the WP04 shadows; verification-by-deletion run (suite green) | WP04 | [D] |
| T015 | Route `core/mission_creation.py:321` compose via `mission_dir_name` | WP05 | [D] |
| T016 | Route `core/worktree.py:367/370` compose via `worktree_dir_name` (removes 2 bare callers) | WP05 | [D] |
| T017 | Byte-parity tests for the composed dir/branch names | WP05 | [D] |
| T018 | Add the AST short-id slice detector (incl. `str(x)[:8]`/`mid[:8]`/`raw_mid[:8]`/`..._id_meta[:8]`) covering `src/` + `dashboard/scanner.py` | WP02 | | [D] |
| T019 | Add the failover-bypass rule (forbid bare `_mid8()`/`[:8]` on correctness paths) | WP02 | | [D] |
| T020 | Minimal/empty allow-list; must NOT trip `invocation_id[:8]`; honesty note names the deferred `parent.parent` repo-root class | WP02 | | [D] |
| T021 | Guard self-test: planted bad slice fails, clean passes | WP02 | | [D] |
| T022 | (#1888) TDD: failing repro — validation passes a phantom owned path | WP06 | [D] |
| T023 | (#1888) Add the existence check to `ownership/validation.py` (scoped to declared owned paths; don't reject future `create_intent` files) | WP06 | [D] |
| T024 | (#1971-tail) Regression test DISPROVING the `SPECIFY_REPO_ROOT`/worktree split-brain across the 3 `locate_project_root` entries; do not touch the deferred-import shims | WP06 | [D] |
| T025 | (#2007 #1/#9 docs) Repoint the 11 `doctrine list/show` refs in `spec-kitty-charter-doctrine/SKILL.md` + 1 in `spec-kitty-mission-system/SKILL.md` to real surfaces / `DoctrineService` | WP07 | [D] |
| T026 | (#2007 #4/#5) Fix the 3 behavioral refs in `software-dev/plan/prompt.md` (`context resolve --action`; `setup-plan` require `--mission`) | WP07 | [D] |
| T027 | (#2007 #13/#16) Repoint the `worktree repair` hint → `doctor workspaces --fix`; document the implement/review JSON contract | WP07 | [D] |
| T028 | (#2007 Focus A) Add the command-snippet CI guard (generalize the docs-CLI reference-parity test `test_docs_cli_reference_parity.py` + `_typer_walker.walk()`), path-level, empty-frozenset ratchet | WP07 | [D] |
| T029 | (#2007 Focus A) Guard self-test: planted nonexistent-command snippet fails, clean passes; placeholder/auto-negation false-positives handled | WP07 | [D] |

---

## WP01 — Seam SSOT entrypoint: demote `mid8` → `_mid8` (IC-05)

- **Goal:** make the failover-aware `resolve_mid8` the only public mid8 door; demote bare `mid8()` to
  internal `_mid8`. Foundation — everything routes to this shape.
- **Priority:** P0 (foundation). **Independent test:** `resolve_mid8` is the only public mid8 symbol;
  composed names byte-identical; one-shot warning preserved.
- **Subtasks:** T001, T002, T003, T004
- **Dependencies:** none. **Sole owner of `branch_naming.py`.**
- **Risks:** mission-id-only callers (`resolve_mid8("", mission_id=full)` must equal old `mid8(full)`);
  preserve `reset_legacy_failover_warning` test seam + one-shot `DeprecationWarning`.
- **Prompt:** ~250 lines.

## WP03 — Route the contract-sensitive sites (IC-02a)

- **Goal:** route the 4 byte-parity-landmine sites through `resolve_mid8` (NOT bare `_mid8`), preserving
  each site's exact `""`/`None`/short-id contract; delete the shadows.
- **Priority:** P1. **Independent test:** characterization tests green before & after; outputs byte-identical.
- **Subtasks:** T005, T006, T007, T008, T009, T010
- **Dependencies:** WP01. **Owns:** `status/aggregate.py`, `dashboard/scanner.py`, `cli/commands/doctor.py`,
  `cli/commands/implement.py` (+ their tests).
- **Risks:** `mid8()` raises vs `resolve_mid8` returns `""`; `doctor.py` `try/except` tolerance is a
  conscious decision (T007); `scanner.py` `None` registry contract.
- **Prompt:** ~320 lines.

## WP04 — Route the direct sites + scope-review additions (IC-02b)

- **Goal:** route the guaranteed-full-id direct sites + the 5 var-name-independent shapes the first grep
  missed; verify zero fragment-adopt; delete shadows; verification-by-deletion.
- **Priority:** P1. **Independent test:** suite green with shadows deleted; outputs unchanged.
- **Subtasks:** T011, T012, T013, T014
- **Dependencies:** WP01. **Owns:** `git/sparse_checkout.py`, `doctrine_synthesizer/apply.py`,
  `context/mission_resolver.py`, `runtime/next/_internal_runtime/retrospective_terminus.py`,
  `mission_runtime/resolution.py`, `cli/commands/agent/mission.py`, `cli/commands/agent/workflow.py`,
  `cli/commands/mission_type.py`, `retrospective/generator.py` (+ tests).
- **Risks:** the 5 additions hide behind `str()`/var-name; confirm each is mission-identity (not
  `invocation_id`); byte-parity.
- **Prompt:** ~300 lines.

## WP05 — #2000 compose-routing (IC-03)

- **Goal:** route the 2 hand-rolled composes through `mission_dir_name`/`worktree_dir_name` (removes 2
  bare callers); byte-parity.
- **Priority:** P1. **Independent test:** composed dir/branch names byte-identical; no bare caller remains.
- **Subtasks:** T015, T016, T017
- **Dependencies:** WP01. **Owns:** `core/mission_creation.py`, `core/worktree.py` (+ tests).
- **Risks:** byte-parity on the composed names (NFR-001).
- **Prompt:** ~200 lines.

## WP02 — Ratchet: AST short-id detector + failover-bypass rule (IC-01) — LANDS LAST

- **Goal:** lock the clean state. Add the AST detector + bypass rule with a minimal/empty allow-list.
- **Priority:** P1 (regression tripwire). **Independent test:** planted bad slice fails CI; clean passes;
  `invocation_id[:8]` not tripped.
- **Subtasks:** T018, T019, T020, T021
- **Dependencies:** WP03, WP04, WP05 (so the routed sites are gone and the allow-list is empty/minimal).
  **Sole owner of `tests/architectural/test_no_worktree_name_guess.py`.**
- **Risks:** AST can't distinguish `mission_id` from `invocation_id` → name allow-list; honesty note must
  name the deferred `parent.parent` repo-root class; the ratchet is a tripwire, not the proof.
- **Prompt:** ~280 lines.

## WP06 — #1888 existence-check fix + #1971-tail verify (IC-04)

- **Goal:** fix the phantom-path validation bug (real, TDD-first); add the #1971-tail split-brain-
  disproving regression test.
- **Priority:** P1 (real bug). **Independent test:** repro fails before, passes after; #1971-tail test
  proves the 3 entries converge under env-var/worktree conditions.
- **Subtasks:** T022, T023, T024
- **Dependencies:** none. **Owns:** `ownership/validation.py` + its tests + the `locate_project_root`
  regression test.
- **Risks:** don't reject legitimate future `create_intent` files; don't touch the intentional
  deferred-import shims.
- **Prompt:** ~230 lines.

## WP07 — #2007 Focus A: command-contract-drift guard (IC-06)

- **Goal:** repoint the 15 SOURCE drift refs + add the command-snippet CI guard; fix the worktree-repair
  hint and the implement/review JSON contract doc.
- **Priority:** P1 (stops agents probing nonexistent surfaces). **Independent test:** planted bad snippet
  fails the guard; clean passes; the 15 refs resolve to registered surfaces.
- **Subtasks:** T025, T026, T027, T028, T029
- **Dependencies:** none. **Owns:** `src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md`,
  `src/doctrine/skills/spec-kitty-mission-system/SKILL.md`,
  `src/doctrine/missions/mission-steps/software-dev/plan/prompt.md`,
  `tests/architectural/test_docs_cli_reference_parity.py`, `scripts/docs/_typer_walker.py`.
- **Risks:** edit SOURCE only (agent copies regenerate); placeholder/auto-negation false positives →
  path-level validation first.
- **Prompt:** ~280 lines.
