---
work_package_id: WP00
title: Composite-key re-key of the gating architectural ratchets (front-load)
dependencies: []
requirement_refs:
- NFR-004
tracker_refs:
- "2072"
- "2071"
planning_base_branch: feat/single-planning-surface-authority
merge_target_branch: feat/single-planning-surface-authority
branch_strategy: Planning artifacts for this mission were generated on feat/single-planning-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-planning-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "355862"
history:
- Created by /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_no_write_side_rederivation.py
- tests/architectural/test_single_mission_surface_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before touching any file, **load the `randy-reducer` profile** so this WP is
executed under the semantic-compression / behavior-preserving-reduction lens
(re-keying a ratchet without weakening it is exactly Randy's discipline):

- Preferred: invoke the `/ad-hoc-profile-load` skill (or `spk-doctrine-profile-load`)
  with `randy-reducer`.
- Fallback: read the profile YAML directly at
  `src/doctrine/agent_profiles/built-in/randy-reducer.agent.yaml` and adopt its
  identity, governance scope, boundaries, and initialization declaration.

Randy's binding rule for this WP: **the re-key is a behavior-preserving
transformation of the allowlist KEY representation only.** Detection logic,
assertion strength, baseline counts, and the *set* of flagged offenders must be
byte-for-byte equivalent before and after. If a change would alter what the
ratchet flags or how loudly it fails, it is out of scope — stop and escalate.

## Objective

Convert the two **gating** architectural ratchets in this mission's blast radius
off brittle `file:line` allowlist keys and onto the **existing** content-addressed
primitive `tests/architectural/_ratchet_keys.composite_key` — a
`(qualname, token_line)` key that survives benign line drift. Specifically:

1. Re-key `tests/architectural/test_no_write_side_rederivation.py`'s `_ALLOW_LIST`
   (currently a `frozenset[tuple[str, int]]` of `(rel_path, lineno)`) onto
   composite keys, and **delete its duplicated private `_code_tokens_by_line`
   helper** (lines 91–118) in favor of importing from the canonical
   `_ratchet_keys` module.
2. Re-key `tests/architectural/test_single_mission_surface_resolver.py`'s
   `_ALLOWLISTED_RAW_JOINS` (currently a `dict[str, str]` keyed by
   `"<rel_path>:<line>"` strings) onto composite keys, while preserving the
   `discover_rows()` live-walk semantics and the `DIAG`/`TBYD` rationale strings.

**Why front-load this and not a plain line re-key:** the seam WPs move the exact
lines these guards allowlist — WP02 (IC-02) edits `core/mission_creation.py:328`
and WP04 (IC-04) rewrites `missions/_read_path_resolver.py:885`. A plain
`file:line` ratchet would false-RED the architectural gate the moment those edits
land. Composite keys are content-addressed, so they survive the line drift and
this re-key is **front-loadable**: it lands BEFORE the seam WPs and stays green
through them. A plain *line* re-key is **not** front-loadable — it would just
re-pin to a line the seam then moves again.

This is **test-only** (`owned_files` are two test modules; `authoritative_surface:
tests/architectural/`). No `src/` change. No new test infrastructure —
`composite_key` already exists and is already consumed by
`test_no_worktree_name_guess.py` (use that as the reference pattern).

## Context

**Ground truth verified in this checkout (cite, do not re-derive):**

- `tests/architectural/_ratchet_keys.py` is the canonical home. Public surface:
  - `code_tokens_by_line(source: str) -> dict[int, str]` (line 62) — the
    tokenize-based half (strings/comments dropped; f-string interior normalized
    for 3.11/3.12 parity).
  - `enclosing_qualname(source: str, lineno: int) -> str` (line 157) — innermost
    `FunctionDef`/`AsyncFunctionDef`/`ClassDef` dotted qualname; `"<module>"` for
    module-level code.
  - `composite_key(source: str, lineno: int) -> tuple[str, str]` (line 204) —
    returns `(qualname, token_line)`.
  - `composite_key_from_file(path: Path, lineno: int) -> tuple[str, str]` (line 226).
  - The module docstring (lines 23–28) **explicitly names** the duplicated
    `_code_tokens_by_line` in `test_no_write_side_rederivation.py` and states "This
    module is the canonical shared extraction point." That dup is what this WP deletes.

- **Reference consumer pattern** — `tests/architectural/test_no_worktree_name_guess.py`:
  - imports `from tests.architectural._ratchet_keys import composite_key` (line 52).
  - keys its allowlist as `dict[tuple[str, str], str]` / `frozenset[tuple[str, str]]`
    (e.g. `_ALLOWED_SITES_FILES` at line 92, `_ALLOWED_SITES` at line 124).
  - builds the lookup key with `key = composite_key(source, lineno)` inside the
    scan loop (line 371) and checks `if key in _ALLOWED_SITES`.
  - carries a `test_allow_list_entries_are_real_and_benign` (line 388) staleness
    test that re-scans the mapped file and asserts the composite key is still live.
  - **Mirror this exact shape.** It is the canonical post-re-key form.

- **Owned file 1 — `test_no_write_side_rederivation.py`** (current state):
  - `_ALLOW_LIST: frozenset[tuple[str, int]]` (line 84) holds exactly one entry:
    `("src/specify_cli/coordination/status_transition.py", 336)` — the deferred
    S2 #1716 `coord_branch or _current_branch` HEAD-selector fallback arm.
  - The **duplicated** `_code_tokens_by_line(source)` lives at lines 91–118 (a
    byte-near copy of `_ratchet_keys.code_tokens_by_line` minus the f-string
    normalization). It is used by `_scan_source` (line 134) and by
    `test_allow_listed_line_is_the_deferred_head_selector` (line 261).
  - `_Finding.as_allow_key()` (line 62) returns `(rel_path, lineno)` — the current
    line-scoped key.
  - Gating tests in this file: `test_adopted_modules_have_no_write_side_rederivation`
    (line 153), the bite/parametrized self-test (line 192), the prose-ignore test
    (line 213), `test_allow_list_is_line_scoped_not_a_blanket_file_escape` (line 233),
    `test_allow_listed_line_is_the_deferred_head_selector` (line 251).
  - **Subtlety (do not break):** `test_allow_list_is_line_scoped_not_a_blanket_file_escape`
    currently asserts the key is a `(str, int)` pair. After re-key the key becomes
    `(qualname:str, token_line:str)` — that test's INTENT ("not a bare file path /
    blanket file escape") must be PRESERVED but its shape assertion updated to the
    composite form. Do NOT delete the intent; re-express it.

- **Owned file 2 — `test_single_mission_surface_resolver.py`** (current state):
  - `_ALLOWLISTED_RAW_JOINS: dict[str, str]` (line 181) keyed by `row.key()` =
    `"<rel_path>:<line>"` strings; values are `DIAG`/`TBYD` rationale strings. Five
    live entries, including the two seam-drifting ones this WP must protect:
    `"specify_cli/core/mission_creation.py:328"` (line 233) and
    `"specify_cli/missions/_read_path_resolver.py:885"` (line 219).
  - The guard loop (`test_zero_functional_raw_bypass_on_collapsed_tree`, line 317)
    does `key = row.key()` then `if key not in _ALLOWLISTED_RAW_JOINS`.
  - `test_allowlist_entries_are_not_stale` (line 358) builds
    `live_raw_bypass_keys = {row.key() ...}` and asserts every allowlist key is live.
  - `ResolutionRow` comes from the dynamically-loaded `surface_resolution_audit/audit.py`
    module (`row.key()` at line 338, `row.call_name`, `row.handle_source`). Each row
    exposes a rel-path + line; you must derive a composite key from `(file, line)`
    via `composite_key_from_file`. **Verify `ResolutionRow` exposes the absolute or
    rel path + lineno needed** (read `surface_resolution_audit/audit.py` to confirm
    the field names before writing the re-key — do not assume).

**Scope fence (carve-outs that stay CONTENT-unchanged):** leave the
`surface_resolver.py:472` / `:477` and `review/cycle.py:185` allowlist *content*
exactly as-is (untouched seam joins; their PERMANENT-vs-DEFERRED classification is
tracked separately under #2072). They get re-keyed to composite form like every
other entry, but their rationale text and disposition are not edited.

**Campsite (#1970):** touched LINES only. Do not reformat, do not re-order
unrelated entries, do not chase other ratchets in these files.

## Subtasks

### T001 — Re-key `_ALLOW_LIST` + delete the duplicated `_code_tokens_by_line` in `test_no_write_side_rederivation.py`

- Replace the `import ... tokenize` + private `_code_tokens_by_line` (lines 91–118)
  with `from tests.architectural._ratchet_keys import code_tokens_by_line, composite_key`
  (and `composite_key_from_file` if convenient). Update `_scan_source` (line 134)
  and `test_allow_listed_line_is_the_deferred_head_selector` (line 251/261) to call
  the imported `code_tokens_by_line`.
- Convert `_ALLOW_LIST` from `frozenset[tuple[str, int]]` to
  `frozenset[tuple[str, str]]` of composite keys. Compute the composite key for the
  single deferred entry (`coordination/status_transition.py` `coord_branch or
  _current_branch` fallback arm) via `composite_key_from_file(_REPO_ROOT / rel, lineno)`
  using the **current live line** — do not hardcode a guessed `(qualname, token_line)`;
  derive it programmatically (e.g. a module-level constant built once) OR, mirroring
  `test_no_worktree_name_guess.py`, keep a `(composite_key) -> rel_path` map and a
  staleness test rather than a raw literal. Prefer the map+staleness form so the
  entry self-documents and a future drift is caught loudly.
- Update `_Finding.as_allow_key()` (line 62) to return the composite key
  `composite_key(<source>, self.lineno)` (the `_scan_*` path already has the source
  in scope; thread it through rather than re-reading the file per finding).
- Update the gating guard (`test_adopted_modules_have_no_write_side_rederivation`,
  line 153) lookup to compare composite keys.

### T002 — Preserve the line-scoped INTENT + deferred-line tests under the new key shape

- `test_allow_list_is_line_scoped_not_a_blanket_file_escape` (line 233): re-express
  the assertion so it proves the key is a `(qualname, token_line)` composite — NOT a
  bare file path. The anti-blanket-escape intent (paula SF-2) stays: assert each
  entry is a 2-tuple of non-empty `str`s and that the second component (token_line)
  is non-empty (a real code line, not a whole-file wildcard). Rename the test only if
  the new name is clearer; keep its docstring's intent.
- `test_allow_listed_line_is_the_deferred_head_selector` (line 251): keep it green —
  it must still prove the single allowlisted site really holds
  `coord_branch or _current_branch`. Resolve the composite key back to its live line
  (or re-scan the file) and assert the token_line / source contains the selector.
  This is the anti-rot guard; do not weaken it.

### T003 — Re-key `_ALLOWLISTED_RAW_JOINS` in `test_single_mission_surface_resolver.py`

- First **read `surface_resolution_audit/audit.py`** and confirm the `ResolutionRow`
  fields that expose `(rel_path, lineno)` (the `row.key()` `"<rel>:<line>"` split is
  the minimum; prefer a structured field if present).
- Convert `_ALLOWLISTED_RAW_JOINS` from `dict[str, str]` (string-locator keyed) to
  `dict[tuple[str, str], str]` (composite-key keyed), preserving every `DIAG`/`TBYD`
  rationale string verbatim, including the seam-drift NOTE comments. Build each
  composite key from the row's `(file, line)` via `composite_key_from_file`.
- Update `test_zero_functional_raw_bypass_on_collapsed_tree` (line 317) and
  `test_allowlist_entries_are_not_stale` (line 358) to compute the composite key per
  discovered row (`composite_key_from_file(_REPO_ROOT / row_rel, row_line)`) and look
  it up in the composite-keyed map.
- Keep `test_all_allowlisted_entries_have_rationale` (line 503) working against the
  new key type (iterate `.items()`; the rationale value type is unchanged).
- Do **not** touch the `discover_rows()` live-walk, the mutation/self-tests
  (`_SourceMutation`, the bite proofs), the floor assertions, or the selection-callsite
  ratchet — those are out of scope and must stay byte-identical.

### T004 — Prove non-vacuity + zero dangling references + both guard files green

- **Anti-vacuity (planted violation):** for EACH re-keyed guard, temporarily plant a
  real offender that the re-keyed allowlist must NOT exempt, and confirm the guard goes
  RED, then revert. For `test_no_write_side_rederivation.py`, the planted offender must
  prove the COMPOSITE key `(qualname, token_line)` is what gates — NOT `token_line`
  alone. Plant a NEW `coord_branch or _current_branch` line whose **`token_line` is
  byte-identical to the single allowlisted entry's `token_line`** (the deferred S2
  HEAD-selector arm) but inside a **DIFFERENT function** (different `qualname` → the
  composite key differs in its first component even though the second is shared). If the
  re-key were keyed on `token_line` alone, this offender would be over-matched and
  silently exempted; under the composite key it must NOT be — confirm
  `test_adopted_modules_have_no_write_side_rederivation` FAILS on it. (Choosing a
  qualname-only-distinct offender is the load-bearing part of this proof: it
  demonstrates `qualname` is a real component of the key and is not over-matched away.)
  For `test_single_mission_surface_resolver.py`, reuse the existing in-file mutation
  helper shape (a real raw `KITTY_SPECS_DIR / slug` join in a non-allowlisted file)
  and confirm `test_zero_functional_raw_bypass_on_collapsed_tree` FAILS. Record both
  RED → revert → GREEN observations in the WP notes (live evidence, not static reading).
- **Zero dangling references:** confirm the deleted `_code_tokens_by_line` has ZERO
  remaining references — `rg '_code_tokens_by_line' tests/` must return nothing, and
  `rg 'import tokenize|import io' tests/architectural/test_no_write_side_rederivation.py`
  must be empty if those imports are now unused (remove dead imports — ruff F401 will
  catch them).
- **Both guard files green:**
  `PWHEADLESS=1 pytest tests/architectural/test_no_write_side_rederivation.py tests/architectural/test_single_mission_surface_resolver.py -q`
  passes. Then run the full `tests/architectural/` suite to confirm no collateral
  ratchet regressed: `PWHEADLESS=1 pytest tests/architectural/ -q`.
- `ruff check tests/architectural/test_no_write_side_rederivation.py tests/architectural/test_single_mission_surface_resolver.py`
  and `mypy` on the two files: zero issues, zero warnings. No new `# noqa` / `# type: ignore`.

## Branch Strategy

Planning artifacts for this mission were generated on
`feat/single-planning-surface-authority`. During `/spec-kitty.implement` this WP may
branch from a dependency-specific base, but completed changes must merge back into
`feat/single-planning-surface-authority` unless the human explicitly redirects the
landing branch. WP00 has **no dependencies** and lands FIRST so the seam WPs
(WP01–WP07) build on the drift-proof gate.

## Definition of Done

- [ ] `randy-reducer` profile loaded before edits (declared in WP notes).
- [ ] `test_no_write_side_rederivation.py`: `_ALLOW_LIST` is composite-keyed
      (`tuple[str, str]`); the duplicated `_code_tokens_by_line` is DELETED and the
      module imports `code_tokens_by_line` from `_ratchet_keys`; `rg
      '_code_tokens_by_line' tests/` returns nothing.
- [ ] `test_single_mission_surface_resolver.py`: `_ALLOWLISTED_RAW_JOINS` is
      composite-keyed (`dict[tuple[str, str], str]`) with every `DIAG`/`TBYD`
      rationale preserved verbatim; the `discover_rows()` live-walk, mutation proofs,
      floor and selection-callsite tests are untouched.
- [ ] The seam-drift sites — `mission_creation.py:328` and `_read_path_resolver.py:885`
      — are now keyed by `(qualname, token_line)`, NOT by line number (the whole point:
      WP02/WP04 may move them without RED-ing the gate).
- [ ] `surface_resolver.py:472/:477` and `review/cycle.py:185` allowlist CONTENT
      (rationale + disposition) is unchanged — only the KEY representation changed.
- [ ] Detection logic, assertion strength, and the set of flagged offenders are
      EQUIVALENT pre/post (behavior-preserving; baselines/counts unchanged).
- [ ] **Anti-vacuity proven LIVE:** a planted offender in a different qualname/file
      makes EACH re-keyed guard go RED; reverted to GREEN. Both RED→GREEN observations
      recorded as live evidence.
- [ ] The line-scoped-INTENT test and the deferred-HEAD-selector test are preserved
      (re-expressed, not deleted) and pass.
- [ ] `pytest tests/architectural/test_no_write_side_rederivation.py
      tests/architectural/test_single_mission_surface_resolver.py` green; full
      `tests/architectural/` green (no collateral regression).
- [ ] `ruff` + `mypy` clean on both owned files; no new suppressions.
- [ ] Campsite (#1970): touched lines only — no unrelated reformat/re-order.

## Risks

1. **Vacuous re-key (silent gate loss).** If the composite key is computed wrong
   (e.g. wrong lineno, stale source) the allowlist could exempt MORE than intended,
   neutering the gate. Mitigation: the T004 planted-violation proof + the
   staleness/`*_are_not_stale` tests must both pass; never hand-author a
   `(qualname, token_line)` literal — derive it from the live file.
2. **`ResolutionRow` field mismatch.** The surface-resolver guard derives keys from
   audit rows; if `ResolutionRow` exposes only `row.key()` you must split
   `"<rel>:<line>"` reliably (rsplit on the last `:`). Read `audit.py` first; do not
   assume a structured field exists.
3. **Accidentally weakening the line-scoped intent.** `test_allow_list_is_line_scoped_
   not_a_blanket_file_escape` exists to block a blanket file escape (paula SF-2).
   Re-express it for the composite shape — deleting it would re-open that hole.
4. **Front-load ordering breach.** If this WP does NOT land before WP02/WP04, those
   seam edits will RED the gate on a *line* basis. Confirm WP00 is sequenced first
   (it is: `dependencies: []`, all seam WPs depend transitively on it).
5. **Dead-import / f-string-parity drift.** Deleting the local helper but leaving
   `import io` / `import tokenize` trips ruff; switching to the canonical
   `code_tokens_by_line` changes f-string token normalization (3.11/3.12 parity) —
   benign for the single `coord_branch or _current_branch` selector (no f-string), but
   re-run the deferred-HEAD-selector test to confirm the token_line still matches.

## Reviewer Guidance

- **This is behavior-preserving by contract.** Diff the assertion bodies: the
  detection logic, baseline literals, and the flagged-offender SET must be unchanged.
  Any change to *what* the guard flags (not just the key shape) is a REJECT.
- **Verify the dup is truly gone:** `rg '_code_tokens_by_line' tests/` returns
  nothing, and `test_no_write_side_rederivation.py` imports `code_tokens_by_line`
  from `_ratchet_keys` (no resurrected private copy).
- **Verify the seam-drift protection is real:** the entries for
  `mission_creation.py:328` and `_read_path_resolver.py:885` must be
  `(qualname, token_line)` tuples, not line numbers. Spot-check by mentally inserting
  a blank line above each site — the key must not change.
- **Demand the live anti-vacuity evidence.** A re-key that passes only because nothing
  is currently flagged is vacuous. The WP notes must show each guard going RED on a
  planted offender (different qualname/file) and GREEN on revert. Static "looks fixed"
  is not acceptance (live-evidence rule).
- **Scope discipline:** reject any edit to `src/`, to `discover_rows()`/`audit.py`, to
  the mutation/floor/selection tests, or any re-formatting beyond touched lines (#1970).
  The `surface_resolver.py:472/:477` and `cycle.py:185` rationale text must be
  byte-identical.
- Use `reviewer-renata` for the review; confirm `ruff` + `mypy` clean with no new
  suppressions, and that the full `tests/architectural/` suite is green (the gate this
  WP protects runs there).

## Activity Log

- 2026-06-22T14:18:39Z – claude:opus:randy-reducer:implementer – shell_pid=330235 – Assigned agent via action command
- 2026-06-22T14:36:19Z – user – shell_pid=330235 – WP00 implement: re-key gating ratchets onto composite_key
- 2026-06-22T14:36:20Z – user – shell_pid=330235 – WP00 implement: re-key gating ratchets onto composite_key
- 2026-06-22T14:37:51Z – claude:opus:randy-reducer:implementer – shell_pid=330235 – Re-keyed both gating ratchets onto _ratchet_keys.composite_key (qualname, token_line); deleted duplicated _code_tokens_by_line (now imports code_tokens_by_line from _ratchet_keys). _ALLOWLISTED_RAW_JOINS now dict[tuple[str,str],str] derived live via composite_key_from_file (rationales verbatim, incl. surface_resolver.py:472/477 + cycle.py:185 untouched). Behavior-preserving: detection/baselines/flagged-offender SET unchanged. NON-VACUITY proven LIVE: file1 planted same-token_line/different-qualname coord_branch-or-_current_branch -> RED(rc=1)->revert GREEN(rc=0) (qualname load-bearing); file2 planted raw KITTY_SPECS_DIR/slug in aggregate.py -> RED(rc=1)->revert GREEN(rc=0). Both guard files 25 passed (exit 0). ruff diff-scoped exit 0; mypy clean. Full tests/architectural/ 428 passed, 1 PRE-EXISTING failure (test_pytest_marker_convention::test_support_helper_tree_is_exempt confirmed identical on clean lane base 887d5b6d5). Code on lane branch commit 37e4e0a7e.
- 2026-06-22T14:38:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=355862 – Started review via action command
- 2026-06-22T14:54:21Z – user – shell_pid=355862 – Review passed (reviewer-renata): all 7 DoD criteria; non-vacuity re-verified live; ruff/mypy clean; test-only scope
