---
work_package_id: WP06
title: root-resolver submodule unification
dependencies: []
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: feat/read-path-error-fidelity
merge_target_branch: feat/read-path-error-fidelity
branch_strategy: Planning artifacts for this mission were generated on feat/read-path-error-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-path-error-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2298074"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/paths.py
create_intent:
- tests/specify_cli/core/test_resolve_canonical_root_submodule.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/paths.py
- tests/specify_cli/core/test_resolve_canonical_root_submodule.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before doing anything else, load the implementer profile so identity, governance scope, and
boundaries are in force for this session:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order, so the fix is grounded in the canonical mission record (do NOT improvise
from memory):

- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md` — FR-007, SC-005, US-5, NFR-001/002.
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/plan.md` — IC-06 (root-resolver
  unification) and the sequencing note (IC-06 has **no dependency**, start anytime).
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/contracts/behavioral-contracts.md` — C-IC06.
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/research/live-repro.md` §"#6 / #2011" — the
  witnessed live failure on HEAD with the exact `file:line` and topology.

## Objective

Make `resolve_canonical_root` (`src/specify_cli/core/paths.py:284-288`) **stop at the submodule
root** when invoked inside a git submodule (a `.git` FILE that is a non-worktree pointer), instead
of walking UP into the parent repository. After this WP the two root authorities —
`resolve_canonical_root` and `locate_project_root` (the latter already patched by #1944/#1965) —
**agree** on the submodule case (FR-007, C-IC06, SC-005). This is a **launch-blocker** (#6 / #2011):
Robert's run had `assert_initialized` resolve the parent repo and raise
`SPEC_KITTY_REPO_NOT_INITIALIZED` from inside an initialized submodule.

**C-001 — adopt, don't build.** Do NOT introduce a new root authority or a new error type. Make the
existing `resolve_canonical_root` agree with the existing `locate_project_root` by mirroring the
boundary check that already lives there.

## Context

**The disease (witnessed on HEAD, `research/live-repro.md` §"#6 / #2011").** A real submodule
topology: parent repo `econcept-next` (its `.git` is a DIRECTORY, no `.kittify`); submodule
`elissar-api` added via `git submodule add`, so its `.git` is a FILE
(`gitdir: ../.git/modules/elissar-api`), carrying its own `.kittify/config.yaml` and a mission.
Live probe from inside the submodule:

```
resolve_canonical_root(<submodule>) -> .../econcept-next        # PARENT — WRONG
locate_project_root(<submodule>)    -> .../econcept-next/elissar-api  # correct
```

**Root cause (PINNED).** In `resolve_canonical_root` (`paths.py:284-288`), a submodule `.git` FILE
makes `_read_worktree_gitdir(git_path)` return `None` (non-worktree pointer), and the code then
executes `continue` ("keep walking so an enclosing repo is still resolved"). It ascends past the
submodule with **no `.kittify`/`kitty-specs` boundary check and no submodule-boundary stop**,
landing on the parent (whose `.git` is a directory, returned at `:280-282`). Meanwhile
`locate_project_root` (`paths.py:120-131`) correctly stops at the submodule because **after** its
git-marker checks it falls through to a `.kittify` marker check (`(candidate / KITTIFY_DIR).is_dir()
→ return candidate`). The live `assert_initialized` guard calls the BROKEN `resolve_canonical_root`,
which is why #1944/#1965 (which only patched `locate_project_root`) never covered bug #6.

**The fix shape.** Before the `continue` at `paths.py:287-288`, apply the **same boundary check
`locate_project_root` uses** so the two resolvers AGREE: if the current `candidate` carries the
canonical marker (`.kittify` dir present, mirroring `paths.py:122/130`; the spec also cites
`kitty-specs`), stop and return that candidate rather than walking up. Mirror `locate_project_root`
exactly — do not invent a new heuristic. Keep the existing real-worktree-pointer leg (`:289-290`)
and the regular-repo leg (`:280-282`) untouched; only the non-worktree-pointer (submodule) branch
changes.

**Scope discipline.** **#1971 is a SEPARATE 3-way `locate_project_root` consolidation — do NOT
conflate it with this WP.** #2011 pins THIS resolver (`resolve_canonical_root`); #1971 alone is
insufficient and is explicitly out of scope (plan.md IC-06 Risks, spec.md CROSS-REF). Touch only the
named `owned_files`.

**Engineering discipline (binding for every subtask):**
- **Function-over-form + verification-by-deletion.** Tests assert observable behavior (which root is
  returned, whether `assert_initialized` raises), not internal structure. The proof is that
  `resolve_canonical_root` and `locate_project_root` return the **same** root across the topology
  matrix.
- **TDD-first.** Write the failing submodule test (T029) before the fix (T030). It must FAIL on
  pre-fix `paths.py` (resolving the parent) and PASS after.
- **Topology-true fixtures — NO fabricated short ids.** Build a **REAL git submodule**: a parent
  repo with its own `.git` directory and NO `.kittify`, plus a real `git submodule add` child whose
  `.git` is a FILE (`gitdir:` pointer) carrying its own `.kittify/config.yaml` and a mission with a
  **full 26-char ULID `mission_id`**. The coord and primary legs of the equivalence test (T031) use
  a real coordination worktree and a real primary checkout. A synthetic single-repo stand-in **masks
  this bug** (NFR-002) — it is the exact trap the prior mission hit.
- **Quality gates.** New/changed code passes `ruff` + `mypy` with zero issues, cyclomatic complexity
  ≤ 15, NO suppressions (`# noqa`, `# type: ignore`, per-file ignores). Fix the code, not the gate
  (NFR-004).

## Subtasks

### T029 — TDD: `resolve_canonical_root` returns the submodule root (real submodule) [P]
1. Create `tests/specify_cli/core/test_resolve_canonical_root_submodule.py`.
2. Build a real submodule fixture (helper in-test): `git init` parent `econcept-next` (no
   `.kittify`); `git init` a child, commit it, then `git submodule add ./child elissar-api` so the
   submodule's `.git` is a FILE. Write `.kittify/config.yaml` into the submodule and a mission dir
   under `kitty-specs/<slug>-01KV.../` with `meta.json` carrying a full 26-char ULID `mission_id`.
3. Assert (this is the failing assertion before the fix):
   `resolve_canonical_root(submodule_path) == submodule_path`.
4. Also assert `assert_initialized()` invoked from inside the submodule does **NOT** raise
   `SpecKittyNotInitialized` / `SPEC_KITTY_REPO_NOT_INITIALIZED` (the operator-facing symptom,
   `live-repro.md` §"#6").
5. **Validation:** run the new test against unmodified `paths.py` and confirm it FAILS by resolving
   the parent (`econcept-next`) — capture the failure so the green after T030 is trustworthy
   (live-evidence discipline).

### T030 — Fix the submodule boundary in `paths.py` (mirror `locate_project_root`) [P]
1. In `resolve_canonical_root` (`src/specify_cli/core/paths.py:284-288`), before the `continue` in
   the non-worktree-pointer branch, add the boundary check `locate_project_root` already performs
   (`paths.py:122/130`): if `candidate` carries the canonical `.kittify` marker (mirror the existing
   `(candidate / KITTIFY_DIR).is_dir()` predicate; honour the spec's `kitty-specs` mention if
   `locate_project_root` consults it), return `candidate.resolve()`.
2. Keep the real-worktree-pointer leg (`:289-290`) and the regular-`.git`-directory leg (`:280-282`)
   unchanged; the regular-repo leg must still win for non-submodule checkouts.
3. Update the docstring bullet at `paths.py:262-263` ("keep walking…") so it documents the new
   boundary stop, keeping the resolver's contract honest.
4. Extract a tiny helper if the branch pushes the function toward complexity 15 — keep
   `resolve_canonical_root` ≤ 15.
5. **Validation:** T029 now PASSES; full `pytest tests/specify_cli/core/ -q` is green; `ruff check
   src/specify_cli/core/paths.py` and `mypy src/specify_cli/core/paths.py` are clean.

### T031 — Equivalence test over {primary, coord, submodule}: both resolvers agree [P]
1. In the same test module, add a parameterized test over the three real input classes — **primary**
   checkout, **coordination worktree** (real `git worktree add` of a coord branch), and the
   **submodule** fixture from T029.
2. For each topology assert `resolve_canonical_root(p) == locate_project_root(p)` (NFR-001 zero
   divergence) and that both equal the expected canonical root for that class.
3. **Validation:** the parameterized test is green for all three classes; running it against pre-fix
   `paths.py` shows ONLY the submodule case diverging (confirming the other classes were never
   broken and the fix is surgical).

## Branch Strategy

Planning artifacts were generated on `feat/read-path-error-fidelity`. During `/spec-kitty.implement`
this WP may branch from a dependency-specific base, but completed changes merge back into
`feat/read-path-error-fidelity` unless the human explicitly redirects the landing branch. WP06 has
**no dependencies** and is immediately startable in parallel with WP07/WP08.

## Definition of Done

- [ ] `tests/specify_cli/core/test_resolve_canonical_root_submodule.py` exists and was authored
      TDD-first against a REAL git submodule fixture (full 26-char ULID `mission_id`, `.git` FILE
      with `gitdir:` pointer); the TDD test **FAILED FIRST on HEAD** (resolving the parent) and the
      **captured red is pasted into the Activity Log** (not a prose claim), flipping to green after the
      fix. The T031 equivalence test's pre-fix divergence (only the submodule case diverging) is
      likewise captured.
- [ ] `resolve_canonical_root` returns the submodule root from inside a submodule, identical to
      `locate_project_root` (C-IC06; FR-007; SC-005).
- [ ] `assert_initialized` from inside an initialized submodule does NOT raise
      `SPEC_KITTY_REPO_NOT_INITIALIZED`.
- [ ] Parameterized equivalence test over {primary, coord-worktree, submodule} proves both resolvers
      agree (NFR-001).
- [ ] The fix mirrors `locate_project_root`'s existing boundary check — NO new root authority, NO new
      error type (C-001); #1971 NOT conflated.
- [ ] Only `src/specify_cli/core/paths.py` and the new test file changed; the regular-repo and
      worktree legs are untouched (NFR-005).
- [ ] `ruff` + `mypy` clean on changed files; `resolve_canonical_root` complexity ≤ 15; no
      suppressions added (NFR-004).
- [ ] `pytest tests/specify_cli/core/ -q` green.

## Risks / reviewer guidance

- **Topology-true is non-negotiable.** A fabricated single-repo "submodule" stand-in cannot exhibit
  the `.git`-FILE non-worktree-pointer path and will pass vacuously. Reviewer: confirm the fixture
  uses a genuine `git submodule add` (assert the child `.git` is a FILE, not a dir, and that
  `_read_worktree_gitdir` returns `None` for it).
- **Do not over-reach into `locate_project_root` or #1971.** The fix is a single boundary check on
  the non-worktree-pointer branch of `resolve_canonical_root`. The 3-way consolidation (#1971) is a
  separate, out-of-scope track; pulling it in is scope creep.
- **Regular-repo regression.** Verify a plain (non-submodule) repo still resolves at its own root and
  a real spec-kitty worktree still follows the pointer back to the main checkout — the equivalence
  test's primary/coord legs guard this.
- **Boundary marker parity.** The reviewer should confirm the new check uses the SAME predicate as
  `locate_project_root` (so "agree" is structural, not coincidental).

## Activity Log

- 2026-06-16 — WP prompt authored from plan.md IC-06, contracts C-IC06, and the live-repro #6/#2011
  evidence. Awaiting implementation.
- 2026-06-16T20:10:55Z – claude:opus:python-pedro:implementer – shell_pid=2261877 – Assigned agent via action command
- 2026-06-16T20:17:34Z – user – shell_pid=2261877 – WP06 implement loop: advancing to claimed
- 2026-06-16T20:17:36Z – user – shell_pid=2261877 – WP06 implement loop: advancing to in_progress
- 2026-06-16T20:19:36Z – claude:opus:python-pedro:implementer – shell_pid=2261877 – Ready: submodule root unified — resolve_canonical_root mirrors locate_project_root's .kittify boundary check; real git-submodule fixture (26-char ULID, .git FILE) RED-first then GREEN; {primary,coord,submodule} equivalence proven; core 165 passed; ruff+mypy+C901 clean.
- 2026-06-16T20:20:54Z – claude:opus:reviewer-renata:reviewer – shell_pid=2298074 – Started review via action command
- 2026-06-16T20:27:36Z – user – shell_pid=2298074 – Review passed (renata): real-submodule fixture + captured-red verified; surgical paths.py fix; 165 core tests green
