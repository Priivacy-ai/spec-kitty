# WP05 — Review cycle 1 (reviewer-renata)

**Verdict: REJECT (1 blocker).**

Everything measurable in the budget/attribution/SC-013 family was re-derived independently and
holds. The rejection is on **FR-005 / SC-012 at sites C and D**: their diagnosis is written into an
optional `diagnostics` sink that **no production caller ever supplies**, so nothing an operator sees
changes at those two sites.

---

## BLOCKER

**[BLOCKER] `src/specify_cli/cli/commands/implement_cores.py:620` (and `:461-465`, `:361-365`) —
sites C and D are diagnosable in tests only; the message is unreachable in production, so `SC-012`
is not met for 2 of the 5 read expressions.**

`SC-012` (`spec.md:453-458`) requires, verbatim:

> a corrupt fixture produces an **operator-visible** message that names **`meta.json`** **and** the
> path […] The generic dirty-worktree message must no longer be the only thing the operator sees at
> any of them.

Both new messages are appended to an **optional** `diagnostics: list[str] | None = None` sink. The
sole production caller of `_is_self_write_only_diff` does not pass one:

```
src/specify_cli/cli/commands/implement_cores.py:619:    def _self_write(repo_rel: str) -> bool:
src/specify_cli/cli/commands/implement_cores.py:620:        return _is_self_write_only_diff(repo_root, repo_rel, coord_branch_for_filter, git=git)
```

`_committed_meta_mapping`'s only production call site is inside `_is_self_write_only_diff` itself
(`:467-469`), so it inherits the same `None`. `implement.py:62,68` imports both symbols as a
**re-export shim only** (`# WP03 / T019: re-export shim`, `:55`) and never calls them.
`PlanningArtifactStagingPlan` (`:576-581`) carries no diagnostics field, so there is no downstream
surface either. Grep of the whole `src/specify_cli/cli/` + `src/specify_cli/git/` tree finds
`diagnostics=` supplied at exactly two places, both in `ref_advance.py` (`:315`, `:383`) — never in
`implement_cores.py`.

Contrast with the sites that were done correctly:

- **Site A/B** are wired end to end — `_dirty_entries` allocates the sink and folds it into the
  operator-visible refusal:
  ```
  src/specify_cli/git/ref_advance.py:382:            notes: list[str] = []
  src/specify_cli/git/ref_advance.py:383:            if _meta_change_is_vcs_lock_only(worktree, path, env, diagnostics=notes):
  src/specify_cli/git/ref_advance.py:389:                    dirty.append(f"{line} ({notes[0]})")
  ```
  and `test_corrupt_worktree_meta_blocks_advance_and_is_diagnosed` asserts through
  `advance_branch_ref`, the real entry point. This is the standard the WP set for itself.
- **Site E** raises `EventLogMergeError`, which `merge_driver_meta`'s handler echoes to stderr
  before `Exit(1)` (`merge_driver.py:261-263`). Operator-visible.

Sites C and D never reach that bar. The tests at
`tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py:84-174` pass only because the
**test** allocates the list the production code path never does.

A committed architectural artifact now asserts the opposite. Registry row
`tests/architectural/tool_artifact_enrolment/registry/_is_self_write_only_diff.md` (added by
`c660d28f3`) states:

> That branch now emits a message naming `meta.json` and the resolved `source` path before returning
> `False`

It does not emit; it appends to a sink nobody passes. That statement must not land as-is.

**Recommendation** (implementer's choice of shape; do not route — the budget is correctly spent):
thread the sink from the production caller, e.g. have `resolve_planning_artifact_staging` allocate a
`list[str]`, pass it into both `_self_write` invocations (`:624`, `:630`), carry it out on
`PlanningArtifactStagingPlan`, and have the git-executor caller in `implement.py` surface it — the
same "core collects, executor emits" split this module already uses for `structural`. Then add one
assertion that runs through the **production entry point** (as site A's test does), not through a
directly-constructed sink. Correct the registry-row prose in the same commit.

---

## MAJOR

**[MAJOR] `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP05-evidence.md:411-412` — the
`SC-012` table presents sites C and D as satisfying an operator-visibility criterion they do not
satisfy, and the limitation is not disclosed.**

The T031 section (`:326-327`) honestly says the diagnosis is "**collected** into an optional
`diagnostics` sink rather than printed", but it does not say that **no production caller collects
it**. The `SC-012` table then lists both rows beside sites A, B and E with no distinction. Re-issue
the table with the reachability of each row stated explicitly.

---

## MINOR

**[MINOR] `tests/architectural/tool_artifact_enrolment/registry/_is_self_write_only_diff.md` — cites
`implement_cores.py:426-431` for the `meta.json` branch; post-edit those lines are inside the
`_is_self_write_only_diff` docstring.** The branch is at `:455-466` on the committed tree
(`455: if name == _META_JSON_FILENAME:` … `466: return False`). The same pre-edit coordinate system
is used in the evidence's "lines actually edited" list for `implement_cores` (`:428-429`, `:338`),
while `ref_advance` correctly gives both pre and post (`:242`→`:249`). Pick one convention and say
which. Given risk #9 in the WP prompt, a registry row that points at a docstring is the one that
matters.

**[MINOR] `tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py:177-179` —
`test_default_git_port_is_untouched` asserts `DEFAULT_GIT_PORT is not None`, which is true on every
tree WP05 could produce.** It cannot go red for any defect in scope (DIR-041: no defect-masking or
always-green assertions). Either pin the port's actual identity/shape or delete the assertion.

**[MINOR] `kitty-specs/.../evidence/WP05-evidence.md:539-566` — the `SC-008` byte-identity proof uses
`git diff --stat feat/meta-fail-closed-3162 -- <path>` from a checkout of that same branch.** That is
a working-tree-vs-tip diff: it is empty whether or not WP05 changed the file, because WP05's changes
are *on* the tip. The `ls` guard correctly rules out the nonexistent-path false green but not this
one. The obligation-bearing command is per-commit:
`git show --name-only --format="" <sha> -- <path>` over WP05's five SHAs. I ran it; all three
obligations hold (`test_row_aware_merge_driver.py`, `test_meta_fail_closed_full_census_contract.py`
and `contracts/` are absent from every WP05 commit). Substance is fine; the quoted method does not
prove it.

**[MINOR] `kitty-specs/.../evidence/WP05-evidence.md:366-368` — the `merge_driver_meta` handler is
quoted at `:246-248`; on the committed tree it is `:261-263`.** WP05's own +15 lines moved it. The
quoted text is verbatim correct.

**[MINOR] `kitty-specs/.../evidence/WP05-evidence.md:197 — "`grep -rn '_VCS_LOCK_META_FIELDS' src/`
→ 6 lines" now returns 7.** WP05's own `Q8` comment (`ref_advance.py:232-238`) adds the seventh. The
decomposition that matters (2 declarations, 2 comparators) is unchanged and verified.

**[MINOR] `tests/specify_cli/git/test_ref_advance_meta_diagnosability.py:97` — local variable
`feature_dir` for a mission directory.** Terminology Canon / DIR-032. It mirrors the pre-existing
`load_meta_fail_closed(feature_dir: Path)` signature so it is drift-consistent rather than new drift,
but `mission_dir` is the canonical word in new test code.

---

## The three self-reported items — adjudicated ACCEPTABLE, all three

1. **`merge_driver.py:645` `mypy --strict` `no-any-return` — genuinely pre-existing. Do NOT fix here.**
   Verified against the merge base by running the checker on both trees, not by reading:
   - `8ad575ceb^`: `src/specify_cli/cli/commands/merge_driver.py:630: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]` — `Found 1 error in 1 file`
   - committed tip: same error, `:645` — `Found 1 error in 1 file`
   Both lines carry the identical expression
   `return AcceptanceMatrix.from_dict(merged_document).to_dict()`; 630 + 15 (WP05's net insertions
   above it) = 645. Outside WP05's surface, reported rather than silently patched — correct handling.
   The other two owned files are clean (`Success: no issues found in 2 source files`), as are
   `ruff check` and `ruff check --select C901` on all three (`All checks passed!`, exit 0).
   Informational only: no tracker row exists for this finding. Not a condition of this review.

2. **`Q8`'s "×3" premise measured as ×2 — the correction is right.** Independently re-derived:
   declarations are exactly two (`implement_cores.py:50`, `ref_advance.py:42`); comparators exactly
   two (`ref_advance:_is_vcs_lock_only_meta_change`, `implement_cores:_is_vcs_lock_only_meta_diff:241`).
   `acceptance/__init__.py:76` `ACCEPTANCE_PROVENANCE_FIELDS` is a 7-element tuple
   (`accepted_at, accepted_by, accepted_from_commit, acceptance_mode, accept_commit, vcs,
   vcs_locked_at`) serving the squash driver's field-shape contract — correctly excluded as a
   different concept, not a third copy. Non-equivalence also confirmed:
   `implement_cores.py:255` uses `base.get(key, _MISSING_META_VALUE) != working.get(key, _MISSING_META_VALUE)`
   against `ref_advance.py:253`'s `worktree_meta.get(key) != committed_meta.get(key)` — an explicit
   `None` and an absent key are distinguishable in one and not the other.

3. **`move-task --to for_review --force` did not paper over a real omission.** All eleven files WP05
   touched appear in its five commits; `git status --porcelain` over every WP05-owned path is empty;
   the last WP05 commit (`eb98551fe`, `2026-08-06T01:43:25Z`) precedes the force event
   (`2026-08-06T01:54:54Z`, `"force": true`, `in_progress -> for_review`). The guard fired on a
   sibling's file, as reported. Ask: put the sibling-collision reason in the move-task `reason`
   next time rather than only in the evidence file.

---

## Verified and passing — for the record

**Budget (re-counted, not accepted).** Same scanner
(`tests.architectural.test_inline_meta_read_gate.scan_routed_load_meta_calls`) applied to three
extracted trees:

```
pre   (e06dfdc6f^ = a41eb7de7): total=129  ref_advance=[]
post1 (e06dfdc6f):              total=130  ref_advance=[('.../src/specify_cli/git/ref_advance.py', 277)]
tip   (62db7aa82):              total=130  ref_advance=[('.../src/specify_cli/git/ref_advance.py', 299)]
exit=0
```

Both endpoints of the attribution measured with the same selection: `ref_advance.py` held **0**
routed sites at the parent and **exactly 1** after. `129 → 130` is WP05's and nothing else's.

**Band and "126 is RED", from source.** `ROUTED_LOAD_META_FLOOR_MARGIN = 4` (`:220`),
`ROUTED_LOAD_META_FLOOR = 126` (`:221`). `test_routed_load_meta_floor` (`:1084`) middle clause,
verbatim:

```python
    assert len(routed) > ROUTED_LOAD_META_FLOOR, (
        "ROUTED_LOAD_META_FLOOR must be a concrete census integer strictly below "
        "the live routed count, not '>= len(routed)' (anti-vacuous)."
    )
```

Strict `>`, so 126 fails clause 2 while passing clauses 1 and 3 — 126 is red, not merely
below-target. Band `[127, 130]`; 130 sits at the top. Floor unchanged at 126 (WP06's to re-derive).

**Site A really is routed, not re-messaged.** `ref_advance.py:299`
`worktree_meta = load_meta_fail_closed(meta_path.parent)`; `:300`
`except MissionMetaReadError as exc:` — **by name**. `MissionMetaReadError` is
`class MissionMetaReadError(RuntimeError):` (`core/paths.py:506`); MRO carries no `ValueError` and no
`OSError`, so no broad handler could catch it incidentally. `None` arm at `:312-313` still returns
`False`. Identity holds: `load_meta_fail_closed` reads `feature_dir / "meta.json"`
(`core/paths.py:672`) under the `Path(path).name == _META_FILENAME` gate (`:381`). No behaviour lost:
`_parse_meta_text` catches `(json.JSONDecodeError, OSError, UnicodeDecodeError)`
(`mission_metadata.py:349`), so the old `except OSError` coverage survives and `UnicodeDecodeError`
is newly covered — the delta is an improvement, as claimed.

**No ledger movement.** `grep -c 'load_meta(' src/specify_cli/git/ref_advance.py` → `0`;
`_TARGET = "load_meta"` (`test_meta_fail_closed_full_census_contract.py:58`) is an exact-name match,
so `load_meta_fail_closed` adds no row.

**`SC-012` messages are real.** Re-executed the corrupt fixtures in-process; the strings reproduce
the evidence table byte-for-byte:

```
SITE C: /tmp/…/kitty-specs/demo/meta.json: meta.json could not be decoded; not treated as a self-write-only diff
SITE D: HEAD:kitty-specs/demo/meta.json: meta.json could not be decoded at HEAD (committed blob is not a JSON object)
SITE E: /tmp/…/kitty-specs/demo/meta.json: meta.json could not be decoded (Expecting property name enclosed in double quotes: line 1 column 2 (char 1))
```

Not transcribed. (Reachability is the blocker, not authenticity.)

**`SC-013`.** Re-ran the same AST walk over the committed tree:
`INPUT: name set = 10 names; population = 1199 .py files` → `OUT: predicate definitions = 12`,
identical to WP01's P01–P12 in membership **and** `file:line`. 12 ≤ 12; no new local predicate.
Mutation-probe revert is clean: WP05's five commits touch exactly eleven files, none of them a
scratch or probe artifact; `git status` in the review worktree is empty; no second `_require_meta`
exists anywhere under `src/`.

**`SC-008`.** Per-commit, over all five WP05 SHAs: `test_row_aware_merge_driver.py`,
`test_meta_fail_closed_full_census_contract.py` and `contracts/` are absent from every one.
`ls` succeeds on all three real paths.

**Filings precede code.** `gh issue view`: #3228 `2026-08-06T01:11:16Z`, #3229 `01:11:41Z`,
#3230 `01:12:07Z`; first code commit `e06dfdc6f` `2026-08-06T01:21:25Z`. `Q8`'s number is cited at
`ref_advance.py:232-238`, immediately above the surviving comparator at `:239`. Not unified — `C-009`
respected.

**Suites run (lane-c worktree, `PYTHONPATH=<worktree>/src`, `-ra`, redirected; never
`tests/sync`, never `tests/cli`):**

| Selection | Result |
|---|---|
| `test_ref_advance_meta_diagnosability.py` + `test_meta_bypass_diagnosability.py` | `18 passed in 85.69s`, 18 selected, `exit=0`, `^ERROR tests/` = 0 |
| `test_issue_2795_claim_blocker.py` + `test_merge_driver_wrappers_2709.py` + `test_exemption_registry_ratchet.py` + `test_inline_meta_read_gate.py::test_routed_load_meta_floor` + `test_implement_cores.py` | `96 passed in 69.79s`, 96 selected, `exit=0`, `^ERROR tests/` = 0 |
| `test_meta_fail_closed_full_census_contract.py` | `27 passed in 65.09s`, 27 selected, `exit=0` |

`_parse_meta_object`'s `None` contract survives and `tests/regression/` is untouched by any WP05
commit.

**Anti-pattern checklist:** 1 FAIL (new `diagnostics` parameters at sites C/D have no production
caller) · 2 PASS · 3 PASS · 4 **FAIL** (FR-005 at sites C and D) · 5 PASS · 6 PASS · 7 PASS
(concurrency recorded in the evidence; put it in the move-task reason too) · 8 PASS.

---

**Downstream:** `WP06` and `WP08` depend on `WP05`. Nothing in this rejection touches the routed
count, the floor, or `ref_advance.py`'s routed site, so `WP06`'s inputs are unaffected — but it
should rebase after the fix lands, since `implement_cores.py` will move again.
