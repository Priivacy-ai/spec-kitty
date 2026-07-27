# Tooling-Friction Trace — single-authority-topology-cleanup-01KVRJ6P

**Purpose:** a running log of spec-kitty tooling friction encountered while running this
mission (a coordination-topology, dogfooding mission). Seeded at spec→tasks; **append
during the implement loop**; reviewed afterward to assess the state of the tooling.
Each entry: what blocked, where, witnessed evidence, disposition.

> Format per entry: `[date] [phase] SYMPTOM — anchor — disposition (fixed PR#/ticket#/workaround/open)`

---

## Seeded during spec → plan → tasks (2026-06-23)

1. **[tasks] check-prerequisites ↔ finalize-tasks planning-surface SPLIT (#2087).** The
   resolver returned `feature_dir` = the **coord worktree** for tasks authoring, but
   `finalize-tasks` reads inputs from the **primary checkout** → tasks authored where
   finalize can't see them → "all requirements unmapped". **Witnessed live** (finalize
   parsed `requirement_refs_parsed={}`). Disposition: **FIXED** — PR #2089 (`check_prerequisites`
   delegates to `_primary_anchored_feature_dir`). Root structural unification deferred → #2090.

2. **[tasks] Ownership validator dependency/lane-BLIND (#2088).** `validate_no_overlap`
   rejected same-lane sequential WPs sharing `owned_files` (the linearized lane-B chain),
   even though the lane allocator's own `write_scope_overlap` rule collapses them into one
   lane. **Witnessed:** "Ownership validation failed: Overlap WP05/WP03…". Disposition:
   **FIXED** — PR #2089 (dependency-aware overlap; sequential pairs exempt). Operator: "if
   the validator rejects same-lane sequential sharing, that is a bug."

3. **[next/implement-prep] mid8 → malformed coord branch (#2091).** `spec-kitty next` on a
   coord mission composed `kitty/mission-<slug>-` (empty mid8) → `git worktree add` exit 128
   → `DecisionGitLogUnavailable`. Root: `_primary_runtime_feature_dir` read identity via the
   topology-AWARE resolver (→ coord worktree, no meta.json) instead of the primary anchor.
   **Witnessed** via the golden-path e2e. Disposition: **FIXED** — PR #2089 (primary-anchored
   identity read). The mid8-persistence SSOT remains → #2090/#1716.

4. **[dispatch/profile-load] doctrine tactic "catalog entry not found".** `delete-the-assertion-not-the-test`
   declared `applies_to_languages: [any]`; the loader treats `any` as a literal language →
   filtered out under the python scope → `missing_artifact` warning during python-pedro load.
   `doctrine validate` PASSES (invisible). Disposition: **FIXED** (field removed, PR #2089);
   root wildcard-semantics gap → **#2092** (P1, 3.2.x).

5. **[git/worktree] coord-topology branch-switch friction.** Repeated `git stash`/checkout
   dance for the `meta.json` `pr_bound` field + untracked Mission-B files when moving the
   bugfix between feat/pr branches; a stray `op(python-pedro): generate` governance commit
   landed on feat from a dispatched Op. Disposition: **workaround** (stash/cherry-pick/rebase);
   no ticket (manageable, but a coord-topology authoring friction symptom).

6. **[finalize] new-file create_intent gate.** finalize's literal-path-zero-match check
   required `create_intent` for WP-created test files (legit). Disposition: **expected**
   (added create_intent); not a bug.

7. **[install] frozen pipx vs source doctrine.** The pipx `spec-kitty-cli` venv held a frozen
   3.2.2 `specify_cli` (not editable) → would not load source doctrine; needed an editable
   rebuild + the pyenv-shim-precedence to load the remediated artefacts. Disposition:
   **workaround** (`pipx install --force --editable .`); a dev-loop sharp edge.

## During implement loop — APPEND BELOW
<!-- e.g. move-task surface (run from primary vs lane), lane-base divergence, status desync,
     issue-matrix gate, finalize/merge friction, accept dirty-gate residue, the dogfooding of
     the very paths under fix. Cite witnessed evidence + disposition. -->

8. **[tasks/sizing-reslice] WP-ID scheme forces an append-renumber on mid-plan split.**
   The sizing-squad re-slice split 4 WPs into sub-WPs. The natural scheme — suffix IDs
   (`WP03a/b/c`, paula's notation) — is **rejected by the tooling**: WP IDs are validated
   `^WP\d{2}$` / `^WP\d+$` across ~10 sites (`status/wp_metadata.py:325`,
   `core/wps_manifest.py`, `frontmatter.py`, `task_metadata_validation.py`, the dependency
   parser `WP\d{2}`). **Witnessed** by grepping the validators before editing. Disposition:
   **workaround** — used an **append scheme** (new sub-WPs as WP14–WP18, the 13 originals
   keep their numbers; tasks.md lists WPs in lane/dependency order so the non-monotonic IDs
   read in execution order). Lower-risk than a full WP01–WP18 renumber (which would rewrite
   every dependency ref). `finalize-tasks --validate-only` confirmed 18 WPs / 0 ownership
   warnings / clean lane collapse. Friction symptom: the planning tooling has no
   first-class "split a WP" operation; a mid-plan re-slice is a manual file-surgery +
   dependency-repoint exercise. Candidate gap (no ticket yet — note for #2094 cadence ROI).

9. **[implement-bootstrap] `record-analysis` DIRTY_WORKTREE gate is topology-blind +
   residue-set INCOMPLETE — peak dogfooding (a sibling of the #2084/#2085 + FR-012 bugs
   this mission fixes).** `spec-kitty agent mission record-analysis` (the implement-gate
   precondition) refused with `DIRTY_WORKTREE` on the coord-topology primary checkout.
   **Witnessed:** the refusal's `dirty_paths` **excludes** `tasks.md`/`plan.md`/
   `status.*`/`issue-matrix.md`/`tasks/` (recognized as coordination residue) but
   **includes** `spec.md` + `data-model.md` + `research.md` + `checklists/` — all four
   tracked on the coord branch (verified `git cat-file -e kitty/mission-…:…/spec.md` →
   ON COORD) yet the residue authority does NOT recognize them, so they read as "dirty"
   on the primary. Same blind spot from the coord worktree too (it still checks the
   primary tree). **This is the exact bug class the mission targets:** the canonical
   `_COORD_RESIDUE_FILENAMES` / `is_coordination_artifact_residue_path` set is **missing
   `spec.md`, `data-model.md`, `research.md`, `checklists/`**. Disposition: **workaround**
   (tool's own remediation — `git stash -u` the coord-residue, run record-analysis, pop).
   **Scope implication:** FR-008/FR-012 WPs (WP12/WP13/WP17) must ensure the converged
   residue set INCLUDES these four artifact kinds; and a NEW finding — the
   `record-analysis` dirty-gate is a topology-blind consumer not in the mission's
   enumerated gate list (accept=FR-008, merge=FR-012). Candidate: extend FR-008's
   converge-list to `record-analysis`, or a sibling ticket of #2084/#2085. Surfaced to
   operator.
