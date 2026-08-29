---
affected_files: []
cycle_number: 2
mission_slug: charter-preflight-remediation-01KYG9WK
reproduction_command:
reviewed_at: '2026-07-27T12:05:42Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP04
---

# WP04 Review — Cycle 1 — REJECTED

Reviewer: Reviewer Renata (independent, adversarial)
Commit reviewed: `b4d26d5bf41ea1c3ffe5fcafa291f574b3bb21e7`

## Verdict: FAIL

The convergence work that *was* done is genuinely good and should not be redone. The reason
for rejection is a specific, live gap in the resolver census: a real operator-reachable
charter-presence resolver was missed — a fifth miss in this mission's enumeration history
(2 → 8 → 9 → 10 → 9 → **this**) — and it currently reproduces the exact User Story 2 symptom
this mission exists to fix.

## What passed (do not redo)

1. **Direction of fix** — `computer.py` has zero diff, confirmed via
   `git show --stat b4d26d5bf -- src/specify_cli/charter_runtime/freshness/computer.py` (empty
   output). No inversion.
2. **T022 census is genuinely criterion-derived, not list-shaped** — I falsified it twice:
   added a throwaway `charter.md`-gating function to `src/charter/language_scope.py`, ran
   `test_no_unrouted_charter_presence_checks_outside_the_seam`, got a clean RED **without
   updating any list**, reverted, `git status` clean. Repeated with a differently-named local
   variable in `src/specify_cli/cli/commands/charter_bundle.py` (`charter.yaml`, not
   `charter.md`) — also RED, also reverted clean. The AST-based, qualname-keyed scan does what
   it claims **within its declared scan roots**.
3. **Site 6 (`sync.py`) exclusion is correctly reasoned.** Read both call sites myself:
   `ensure_charter_bundle_fresh`'s own `charter_path.exists()` gates whether *it* has anything to
   refresh (an internal mutation-entry gate, never surfaced as a presence verdict on its own —
   every caller I traced treats a `None` return as "nothing to resolve *from*", not as the
   presence answer itself), and `_load_charter_yaml_section` degrades to "use an empty config"
   per its own docstring. Both are legitimately not resolvers under R-007. Agree with the 9.
4. **Seam is non-mutating** — confirmed by the full-suite `test_seam_is_non_mutating` run (part
   of the 1684 passed).
5. **Site 9 verified on F2.** Reproduced the F2 legacy-bundle fixture (charter.md present,
   charter.yaml absent, full 4-file legacy bundle) independently and ran
   `spec-kitty charter context --action implement --json`:
   `project_charter.present` → `false`, and `compute_freshness(...).charter_source.state` →
   `"missing"` on the same fixture. They agree.
6. **Site 10's raise is gone (NFR-004).** Ran `charter context --include section:...` against a
   charter-less repo: clean `Error: No charter found for section selector.` on stdout with
   exit code 1 — no traceback. `except ValueError` at the CLI boundary catches it.
7. **`_compact_section_block` is untouched** — confirmed the function body is byte-identical;
   the two hits in the diff are docstring/comment references only.
8. **C-002/C-003** — one canonical seam (`charter_yaml_present`), all call sites route through
   it or through `_resolve_charter_path` transitively; no charter artifact moved or renamed
   (`git diff --diff-filter=R` and `--summary` both empty for renames).
9. **The F4 crash exclusion in T023 is legitimate.** Reproduced the
   `doctrine.spdd_reasons.activation._compute_active` `ParserError` crash on an unparseable
   `charter.yaml` independently on **both** the tip and a worktree checked out at
   `b4d26d5bf~1` (pre-WP04) — identical traceback, identical reachability (both key off
   `charter.md`'s presence to reach the same downstream `is_spdd_reasons_active` call). Genuinely
   pre-existing, correctly out of this WP's locality of change. The exclusion in
   `test_all_surfaces_agree_on_presence` is narrowly scoped to the one `build_charter_context`
   mode-agreement assertion for F4 only — the other four assertions in that test (seam,
   `_resolve_charter_path`, JSON block, `--include`) still run unconditionally on F4 and pass.
10. **No weakened test assertions.** I read every one of the ~24 modified test files in this
    diff, not a sample. All are either (a) additive fixture-repair (adding a companion
    `charter.yaml` so a test whose intent predates R-001 still exercises the same downstream
    behavior it always did), or (b) a deliberate, well-reasoned re-pointing where the old
    assertion encoded the pre-fix bug itself (e.g. `test_missing_charter_file` now unlinks
    `charter.yaml` instead of `charter.md`, with a new sibling test
    `test_missing_companion_charter_md_degrades_to_compact` pinning the corrected behavior; and
    `test_charter_status_cli.py`'s `available` flip from `False` to `True` is correct because
    the `_seed_complete_bundle` fixture only ever wrote `charter.yaml`, never `charter.md` — under
    the old, wrong, charter.md-keyed code this was a false negative). None of the ~24 removes
    or loosens an assertion without a documented, verifiable reason.
11. **Regression suite**: `tests/charter/` → 1684 passed, 3 failed. I reproduced the 3 failures
    independently (not on trust) and confirmed each shells out to `/usr/bin/python`, which lacks
    `typer`/`doctrine` — a stale-environment issue (category 3 in the repo's own
    baseline-red gotcha doc), unrelated to this diff. Ruff clean on all changed files. Mypy
    `--strict` on the 7 changed `src/` files: 9 errors, and I independently diffed them against
    a worktree at the merge base (`b4d26d5bf~1`) — same 9 errors, same files, only line-number
    shifts. Zero new mypy errors.

## Why this fails: a live, unenumerated, unrouted resolver

`src/specify_cli/dashboard/charter_path.py::resolve_project_charter_path` is a project-level
charter-presence resolver that:

- **Already asks the presence question today.** Its own docstring: "The return value is the
  absolute path to `<canonical_root>/.kittify/charter/charter.md` when present, `None`
  otherwise... we surface that as `None` here to preserve the dashboard's 'no charter' UI
  signal." This is not "teaching a new surface the capability" (the spec's own Out-of-Scope
  carve-out) — it already has the capability and already exercises it.
- **Is genuinely operator-reachable**: it feeds `dashboard/handlers/api.py::handle_charter`
  (HTTP 404 "Charter not found" vs 200+content) and `dashboard/scanner.py::get_feature_artifacts`
  (the `"charter": {"exists": ...}` field shown per-feature in the dashboard/kanban UI).
- **Disagrees with the gate on the F2 legacy-bundle fixture — reproduced live**:

  ```
  gate_present: False
  dashboard resolve_project_charter_path: /tmp/.../.kittify/charter/charter.md
  dashboard says present: True
  ```

  This is the mission's exact User Story 2 symptom (gate blocks, diagnostic reports healthy),
  on a surface this WP left completely untouched.
- **Was never in R-003's census** (research.md enumerates 10 operator-reachable sites; this is
  not among them) and **falls entirely outside T022's `_SCAN_ROOTS`**
  (`src/charter`, `src/specify_cli/cli/commands/charter`, `charter_bundle.py` — the dashboard
  package is not scanned). The census's own claim — "a NEW hand-rolled presence check added
  anywhere else in the surface fails this test WITHOUT anyone updating a list" — is not true for
  this surface: I confirmed a probe planted inside the declared scan roots goes red, but this
  site sits outside those roots entirely and the test suite is silent about it.
- **Under R-007's own criterion this unambiguously is a resolver, not a content-degrade**: a
  missing file changes the *presence answer* (404 "not found" / `exists: False`), which is
  exactly the "is a resolver" column, not the "optional display content that degrades" column.
- **The bug is already tested and locked in**: `tests/test_dashboard/test_scanner.py::
  test_project_charter_propagates_to_all_features` (lines ~523–532) writes *only*
  `charter.md` (no `charter.yaml`) and asserts `feature["artifacts"]["charter"]["exists"]` is
  `True` for every feature — pinning the pre-fix bug as expected behavior.
- Confirmed via `grep -rn dashboard kitty-specs/charter-preflight-remediation-01KYG9WK/` (spec,
  research, plan, tasks) — zero hits. This was not a deliberate, reasoned exclusion recorded
  anywhere (unlike site 6/sync.py, which *was* reasoned about explicitly). It is a genuine miss.

## Required remediation

1. Route `resolve_project_charter_path`'s presence question through
   `charter.bundle.charter_yaml_present`, following the same pattern already established in
   `cli/commands/charter/_common.py::_resolve_charter_path` (separate "is charter.yaml present"
   from "path to charter.md for content-loading").
2. Fix `test_project_charter_propagates_to_all_features` (and audit
   `tests/test_dashboard/test_api_handler.py` / `test_scanner.py` generally) — it currently
   pins the bug; it must pin the corrected behavior instead, plus add the F2-shape regression
   case (charter.md present, charter.yaml absent → `exists: False` / 404), mirroring
   `test_all_surfaces_agree_on_presence`'s F2 case.
3. Either widen T022's `_SCAN_ROOTS` to include `src/specify_cli/dashboard/` so this class of
   regression is caught mechanically going forward, or — if there's an architectural reason the
   dashboard package must stay out of the AST scan — add the site to the census as an 11th
   pinned resolver explicitly routed through the seam, with the reasoning recorded in
   research.md the same way site 6 was recorded. Do not leave it silently absent from both the
   scan and the enumeration.
4. Update the pinned counts (`R-003` in research.md, `test_seam_exemption_table_is_exactly_pinned`,
   `test_direct_seam_adoption_count_is_pinned`) to reflect whatever the resolved count becomes,
   with the reasoning in the commit message and in research.md, consistent with how this WP
   already documents the 10→9 site-6 change.

## Not required

- Do not touch `computer.py`.
- Do not re-derive the already-correct sites 1–10 work; it is sound and independently verified
  above.
- Do not weaken any of the ~24 already-correct test edits.
