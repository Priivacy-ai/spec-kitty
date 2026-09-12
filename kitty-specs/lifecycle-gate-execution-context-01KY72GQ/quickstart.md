# Quickstart — Lifecycle Gate Execution Context and Tool-Artifact Ownership

Operational guide for anyone implementing or reviewing a work package on this mission.

---

## Environment

```bash
cd /home/stijn/Documents/_code/SDD/fork/coord-trust-2841   # dedicated clone
git rev-parse --abbrev-ref HEAD                             # remediation/coord-lifecycle-gates
```

- **Always `uv run --extra test …`.** A bare `python` or `pytest` in a clone imports the
  PRIMARY checkout's `src/`, silently testing the wrong tree.
- Base is `upstream/main` `6d9ed490d` (contains PR #2832, #2835, #2818, and sibling #2888). C-001 discharged; sibling published.
  Re-fetch and rebase before starting any `merge/`-package work package regardless — upstream moves.
- The mission runs **coordination topology**. Never hand-commit into the coordination
  worktree — if a defect appears to force it, that is mission evidence: record it rather than
  working around it (C-009).

---

## Running tests

```bash
# Focused, while iterating
PWHEADLESS=1 uv run --extra test pytest tests/acceptance/ -q

# Full parallel run — ALWAYS --dist loadfile, never bare --dist load
PWHEADLESS=1 uv run --extra test pytest tests/ -n auto --dist loadfile -p no:cacheprovider

# Daemon / real-port tests must run serially
PWHEADLESS=1 uv run --extra test pytest tests/sync/test_orphan_sweep.py -n0 -q

# Terminology guard — run before pushing any doctrine or prose change
uv run --extra test pytest tests/architectural/test_no_legacy_terminology.py
```

**There are no known baseline reds** (verified 2026-07-23 on base `6d9ed490d`:
`test_no_dead_symbols.py` 24 passed, `golden_count_ban` 9 passed). An earlier revision of this
file claimed both were red per #2825; that was stale and is deleted rather than corrected,
because a stale known-reds list licences green-washing a real regression.

**If an architectural test goes red, treat it as yours** until you have re-run it on the current
`upstream/main` and shown otherwise.

---

## Verifying the three live defects

```bash
# #1834 — the pending-invariant leg (the landed guard only covers recorded results)
sed -n '294,300p' src/specify_cli/acceptance/gates_core.py    # bare repo_root is passed
uv run --extra test pytest tests/regression/test_issue_1834.py -q   # green — covers the LANDED half only

# #2885 — preview resolves one dir for two partitions
grep -n "feature_dir_for_preview" src/specify_cli/merge/forecast.py

# #2795 — the lock write targets PRIMARY, not coord (issue text is refuted)
sed -n '1166p;1760p' src/specify_cli/cli/commands/implement.py
```

---

## Order of work (binding)

*Corrected 2026-07-23 — this list had drifted behind the plan's Sequencing Constraints and two
operator decisions (R-014 registry mode, R-017 ratchet-first). The plan is authoritative; this
mirrors it.*

1. **IC-01 first** — reproduce the claim-time consolidation blocker. Under coord topology this
   mission cannot consolidate itself until it is understood (C-002).
2. **IC-11 + IC-02** — the surface→filesystem translation seam (IC-11's own entry calls it the
   true schema root, ahead of IC-02) then the gate execution context + total resolvers.
3. **IC-03** — provenance, defer semantics, `pass_pending_consolidation`, single authoritative
   copy, and the FR-014 migration. **IC-09 is folded into IC-03** — it is not a separate step.
4. **IC-04 / IC-05** — post-consolidation verification (zero `merge/` footprint) and the
   two-partition preview, both off IC-03/IC-02.
5. **IC-12 before IC-06** — campsite-split `transaction.py` before the owner opens it.
6. **IC-06 → IC-08 → IC-07** — owner, then the **ratchet lands EARLY (second), before any
   retirement** (R-017: the primary stall countermeasure), then the retirements. The ratchet is an
   **enumerated-registry row-deletion**, NOT a golden count (R-014) — each retirement WP deletes
   its own registry row.
7. **IC-07 `merge/`-package retirement group (c) is scheduled late**; the `tasks_move_task.py`
   retirement (group f) is **unblocked** — sibling `scopesource-gate-followup` published (#2888).
8. **IC-10** (enforcement + disclosure + docs) and **IC-13** (archiving) land last; IC-13 is the
   first thing cut if scope must shrink (it is orthogonal to both seams).

---

## Recording this mission's own negative invariants

This mission fixes the defect that makes command-verified invariants unusable pre-consolidation, so it
must not fall into that trap itself.

- **Prefer scoped `grep_absence`.** Absence within a source directory that already exists on
  the primary surface is judgeable pre-consolidation and is the one shape #1834 never broke
  (provenance contract C9). Use it for "no second compensator", "no new exemption list", "no
  new `flattened` dependence".
- **For `custom_command` invariants**, judge them during per-WP review **from the lane
  surface** where the change exists, and record the result non-`pending` with the lane sha.
  The already-landed preserve guard (`b918e66df`) then protects them at acceptance.
- **Do not record a `deferred_to_consolidation` invariant before IC-03 lands** — the machinery that
  honours deferral does not exist until then.
- **Mission-wide absence claims** (e.g. "the exemption count reached zero") are the one shape no
  lane can prove and the primary tree contradicts until consolidation. Defer those; do not try to
  record them from a lane surface.

---

## Guardrails

- If a work package's answer is *"add an allowlist so gate G stops complaining"*, **stop** —
  that is the ninth exemption and the mission has failed its own thesis.
- Do not add new dependence on the `flattened` flag. Make resolvers total instead.
- Do not build a second rollback path. One compensator (owner contract C4).
- Do not name any new type or branch after coordination topology — #1834 reproduces on flat
  missions too (C-004).
- `review/pre_review_gate.py` is **out of scope**. See `research/sibling-mission-coordination.md`.

---

## Registration checklist for new surfaces

| If you add… | Register it in… |
|---|---|
| A symbol exported off the task-command surface | `test_tasks_compat_surface.py` — `SYMBOL_TO_MODULE`, the `tasks.py` re-export, and the golden count (**live value is 156 on this base** — the sibling's 157→156 move landed in #2888; a new symbol writes 157) |
| A new filesystem sink | `tests/architectural/untrusted_path_audit/inventory.md` — paste the tool-derived row |
| A new architectural test file | the shard map / shard registry |
| A new test file that shells out | `pytestmark` + `git_repo` markers |
| Anything changing test selection | the gate-coverage orphan and selection baselines — update deliberately |

---

## Delivery

Draft PR from the fork branch to `Priivacy-ai/spec-kitty`. The operator merges. Never
`git push origin main` (C-008).
