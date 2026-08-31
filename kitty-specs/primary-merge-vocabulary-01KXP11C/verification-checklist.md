# Verification Checklist — Primary & Merge Vocabulary Disambiguation (Track 1 / #2653)

**WP06 — Enforcement disclosure + verification wrap.** Authored in lane `lane-f`,
which branches from the mission base and does **not** contain WP01–WP05's lane
commits (they converge only at `spec-kitty merge`). Therefore the aggregate
Success-Criteria verification (SC-001..SC-006 over the merged diff) **cannot** be
run from this lane and is **deferred to the post-merge accept gate**. This
checklist records (1) the enforcement-model disclosure confirmation, (2) the
alias-ban guard deferral + rationale, (3) the exact accept-gate checks to run, and
(4) the two known post-merge follow-ups.

---

## 1. Enforcement model — disclosed (FR-011) — CONFIRMED IN-LANE

Confirmed present in `spec.md` (read on this lane):

- **FR-011** (`spec.md:105`): states honestly that Track 1 ships **no automated
  primary/merge sense-guard** — the terminology guard
  (`tests/architectural/test_no_legacy_terminology.py`) is a hardcoded **2-literal
  grep** (`ceremony`, `status-writing`) and does not enforce sense-correctness.
  Sense-correctness is **review-enforced** against `occurrence_map.yaml`.
- **NFR-003** (`spec.md:113`): honest-scope caveat — a green
  `test_no_legacy_terminology.py` means ONLY "no `ceremony`/`status-writing`
  regression"; it does NOT verify primary/merge sense-correctness. The run must
  prove the guard actually executes over the new entries (guard-skip risk #2701).
- **SC-006** (`spec.md:144`): records the boundary — Sense-C code rename → Track 2
  (**#2730**) and `src/glossary/` package removal → **#2727** — in one place.

**Verdict:** enforcement disclosure is present and honest. No spec edit required
(WP06 confirms, does not author, this disclosure).

---

## 2. Alias-ban guard — DEFERRED to Track 2 (#2730)

**Decision:** Do **not** add `"primary target"` / `"primary ref"` (or the Sense-C
`"primary checkout"` / `"primary surface"`) bans to
`tests/architectural/test_no_legacy_terminology.py` in Track 1.

**Rationale (evidence-backed):**

1. **Sense-C aliases legitimately persist until the code rename.** `"primary
   checkout"` / `"primary surface"` describe the `primary_feature_dir_for_mission`
   cluster, whose rename is explicitly Track 2 (C-002, #2730). Banning them now
   would red on load-bearing code that this mission deliberately does not touch.
2. **Even the non-Sense-C aliases cannot be zero-residual-verified pre-merge.** A
   `git grep -nE 'primary (target|ref)' -- src tests docs` on the lane base
   returns **60** occurrences, including:
   - **C-004 do-not-touch** unrelated uses — e.g. the charter-synthesizer
     `primary target` (`src/charter/synthesizer/orchestrator.py`,
     `synthesize_pipeline.py`), which is explicitly out of scope.
   - The **Sense-D glossary entry itself** (`docs/context/orchestration.md:519,523`)
     which *intentionally names* the retired aliases in order to forbid them
     ("Avoid the bare aliases 'primary target' and 'primary ref'"). A literal ban
     would flag the very entry that documents the retirement.
   A repo-wide ban therefore **false-reds on legitimate residual** — exactly the
   friction-test anti-pattern (DIRECTIVE_041). The zero-residual precondition that
   T023 requires is not satisfiable in Track 1.

**Deferral target:** Track 2 (#2730) lands the Sense-C code rename; only after that
rename does the residual collapse to the classified-as-intentional set, at which
point a durable alias-ban guard can be added without false-reds.

---

## 3. Post-merge accept-gate checks (run on the MERGED mission branch)

Run all of the following from `feat/terminology-primary-merge-disambiguation`
after `spec-kitty merge` consolidates WP01–WP06. This is the aggregate SC
verification that T021/T022 defer to accept.

### SC-001 — one canonical term per sense; no ambiguous touched passages
- Read `docs/context/orchestration.md` + `execution.md`: confirm distinct entries
  for the 4 primary senses (PRIMARY partition / Primary Branch / repository root
  checkout / target ref) and 3 merge operations (lane consolidation / branch
  integration / publish to origin), each with a `Do NOT use when`.
- Proxy grep over touched files:
  `git grep -nE "primary (surface|checkout|target|ref)" -- <touched files>` —
  residual must equal the classified-as-intentional set in `occurrence_map.yaml`
  (Sense-C aliases persist to Track 2; they must NOT appear in *this mission's*
  edited prose).

### SC-002 — 0 exempt / serialized identifiers changed (exempt-token invariance)
```
git diff <base>..HEAD | grep -E '^\-' | grep -E 'merge_target_branch|is_primary_artifact_kind|Surface\.PRIMARY|primary_branch|current_is_primary|MergeState|"(merge|squash|rebase)"|resolve_merge_target_branch|primary_repo_root|primary_candidate|WorktreeTopology\.PRIMARY|PRIMARY_CHECKOUT'
```
Expect **no output**. Cross-check against `occurrence_map.yaml` exceptions[].

### SC-003 — single canonical resolver behavior
- `git grep -n "def resolve_primary_branch" src/` → one real definition
  (`core/git_ops.py`); `tasks_shared` is removed OR an explicit compat shim
  reflected in `tasks.py.__all__` + `test_tasks_compat_surface`.
- `grep -n "_resolve_primary_branch_for_recommendation" src/` → folded (delegates
  to canonical with `bias`) or explicitly scoped-out with a rationale comment.
- `uv run pytest -k "git_ops or tasks_compat_surface or mission_branch_context"` → green.

### SC-004 — one prose-glossary home
- `git grep -n "glossary/contexts" glossary/README.md` → no dead links.
- `ls glossary/` → legacy prose relocated under `docs/context/`.
- `uv run python -m scripts.docs.relative_link_fixer --check` → clean.

### SC-005 — occurrence_map per-category diff-compliance + all gates green (0 new suppressions)
- Confirm the merged diff complies with each `occurrence_map.yaml` per-category
  action (all 8 categories actioned — NFR-004).
- Gate battery:
```
uv run pytest tests/docs/ tests/architectural/test_no_legacy_terminology.py -q
uv run python scripts/docs/anti_sprawl_ratchet.py --strict
uv run python -m scripts.docs.relative_link_fixer --check   # relative-link gate
uv run ruff check .
uv run mypy --strict <touched modules>
```
- **Prove the terminology guard executed** over the new entries (guard-skip
  #2701) — inspect the parametrized run, do not trust a silent pass.
- **Exempt-surface pins still green:** `test_mission_runtime_surface`,
  `test_shared_package_boundary`, `test_tasks_compat_surface`.
- **Description-length gate** (≤180 chars) on any added/moved docs page.
- **`.github` symlinks** re-added with `git add -f` if any moved page carries one.

### SC-006 — boundary recorded
- Confirm `spec.md` C-002/C-003 + the mission issue matrix state Sense-C rename →
  Track 2 (#2730) and `src/glossary/` removal → #2727 in one place. (Confirmed
  in-lane, §1 above — re-confirm survives the merge.)

---

## 4. Known post-merge follow-ups (investigate at accept, do NOT block WP06)

1. **Glossary "Realized by" refs point at pre-rename helper names.**
   `docs/context/orchestration.md:532` and `:545` say `merge_lane_to_mission` /
   `merge_mission_to_target`, but the FR-008 rename (landed on a different lane)
   renamed these to `consolidate_lane_into_mission` /
   `integrate_mission_into_target` (see `src/specify_cli/lanes/merge.py:104,188`).
   This is expected cross-lane drift (the glossary edit and the code rename lived
   on separate lanes and converge only at merge). **Action at accept:** sync the
   two "Realized by" references to the new canonical helper names so the glossary
   matches the shipped symbols. Verify with:
   `git grep -n "Realized by the internal helper" docs/context/orchestration.md`.

2. **Pre-existing charter-compilation red `test_profile_charter_e2e`.** Observed
   red independent of this mission's diff. **Action at accept:** confirm it is
   pre-existing on the merge base (not introduced by Track 1) per the
   pre-existing-failure reporting rule, and surface to the operator rather than
   retry-to-green. Do not attribute it to this mission without a base-vs-HEAD
   bisect.

---

## Deferred subtasks (for the record)

| Subtask | State | Reason |
|---------|-------|--------|
| T021 (SC-002 grep + occurrence_map diff-compliance) | deferred to accept | requires merged diff; not present in isolated lane |
| T022 (full gate battery over aggregate) | deferred to accept | requires merged diff; not present in isolated lane |
| T023 (alias-ban guard) | **deferred to Track 2 (#2730)** | zero-residual precondition unsatisfiable in Track 1 (§2) |
| T024 (FR-011 disclosure confirmation) | **done in-lane** | confirmed §1 |
