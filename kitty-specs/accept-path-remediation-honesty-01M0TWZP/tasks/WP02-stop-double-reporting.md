---
work_package_id: WP02
title: Stop double-reporting
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- NFR-002
planning_base_branch: fix/accept-path-remediation-honesty-3730
merge_target_branch: fix/accept-path-remediation-honesty-3730
branch_strategy: Planning artifacts for this mission were generated on fix/accept-path-remediation-honesty-3730. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/accept-path-remediation-honesty-3730 unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
phase: Phase 1 - Implementation
history:
- timestamp: '2026-08-25T00:00:00Z'
  agent: system
  action: Prompt generated via tasks phase authoring
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/acceptance/summary_core.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/cli/commands/accept.py
- tests/specify_cli/acceptance/**
- tests/specify_cli/cli/commands/**
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Reconcile `contracts/`'s dual declaration in `software-dev/mission.yaml`
(`artifacts.optional` + `paths.deliverables`) so the same missing fact is reported through
exactly one severity — `path_violations` (blocking) wins over `missing_optional`
(non-blocking) — and remove the cosmetic duplicate "Optional artifacts missing" console
print. Depends on WP01's resolved-path substrate for the token-normalization rule.

## Context

`_missing_artifacts()` (`src/specify_cli/acceptance/__init__.py:585-595`) does **not** read
`mission.config.artifacts` — it checks a hardcoded, mission-type-agnostic literal list
(`QUICKSTART_FILE`, `DATA_MODEL_FILE`, `RESEARCH_FILE`, and the bare string `"contracts"`).
Only `evaluate_path_conventions` (`summary_core.py`) → `validate_mission_paths` genuinely
reads `mission.config.paths`/`mission.config.artifacts`. So this is a post-hoc reconciliation
between two already-computed lists, not a "read both YAML lists once" join.

`software-dev/mission.yaml` declares `contracts/` at both `artifacts.optional[]` and
`paths.deliverables` — this is what makes `contracts/` show up in both `missing_optional`
(via `_missing_artifacts`) and `path_violations` (via `evaluate_path_conventions` →
`validate_mission_paths`) simultaneously, in strict mode.

**Interface change (pinned by spec.md's Key Entities section — implement exactly as
specified)**: `evaluate_path_conventions` (`summary_core.py:110-148`) gains a new, defaulted
keyword parameter — **`optional_missing_to_dedup: list[str] | None = None`** — named to
signal the side effect (not `optional_missing` or any name reading as inert pass-through).
Both pinned tests (`test_strict_metadata_true_blocks_with_violation`,
`test_strict_metadata_false_downgrades_to_warning`) call the function positionally with
exactly today's 4 args + `strict_metadata=`, omitting the new parameter — the default `None`
must make the function behave exactly as today (no dedup attempted; NFR-002).

Docstring gains a line, next to the existing "Mission path conventions block acceptance by
default..." / "returns (path_violations, warning)" documentation, stating explicitly:
*"When `optional_missing_to_dedup` is provided, entries in that list whose normalized token
also appears in the resolved `missing_paths` are removed from the list IN PLACE before this
function's own 2-tuple return runs — this is a documented side effect, not a pass-through
parameter."*

**Token normalization**: `optional_missing`'s entries are bare, `feature_dir`-relative
strings (e.g. `"contracts"`, from `_missing_artifacts`'s
`str(p.relative_to(feature_dir))` at `acceptance/__init__.py:594`); `missing_paths` entries
are, post-WP1, resolved strings relative to `project_root` (e.g.
`"kitty-specs/<slug>/contracts/"`) — a form `_normalize_path_token`'s plain slash-strip
cannot turn into a `feature_dir`-relative one by itself. Rather than comparing
basenames/last-path-components (which cannot distinguish two future dual-declared tokens
sharing a final segment, e.g. a hypothetical `docs/contracts` optional artifact vs. an
unrelated `api/contracts` declared path), normalize **both sides relative to `feature_dir`,
slash-stripped**, consuming WP1's new `PathValidationResult.missing_paths_feature_relative`
field — but WP1's field is mixed-namespace (real `feature_dir`-relative tokens only for the
artifact-tagged branch; placeholders for the other two branches). **Structurally exclude the
placeholder entries first**: `evaluate_path_conventions` imports and calls WP01's exported
`artifact_tokens_for_mission(mission)` helper (`validators/paths.py`, added by WP01's T016) to
get the same `artifact_tokens` set `validate_mission_paths` uses internally — do not
reimplement that `getattr(mission.config, "artifacts", None)`/`.required`/`.optional`
defensive recipe here; this module gets it as a single shared, importable function, not a
second hand-copy — then builds its comparison set only from
`path_result.missing_paths_feature_relative` entries whose own `_normalize_path_token(token)`
is a member of that `artifact_tokens` set:

```python
{_normalize_path_token(t) for t in path_result.missing_paths_feature_relative
 if _normalize_path_token(t) in artifact_tokens}
```

Then drop from `optional_missing_to_dedup` any entry whose own `_normalize_path_token(entry)`
is in that filtered set. This is a structural exclusion (membership-tested against the
mission's real declared artifact set), not reliance on the placeholder values happening not
to collide with a real artifact token.

**Propagation mechanism (pinned, not left to implementer judgment)**: because the return
arity cannot change (both pinned tests destructure `evaluate_path_conventions`'s return as a
literal 2-tuple), and `collect_feature_summary` binds `missing_optional` once
(`__init__.py:1049`) and reuses that list object for both the `build_warnings(...)` call
(`:1058-1059`) and the later `AcceptanceSummary(optional_missing=missing_optional, ...)`
construction (`:1115`), the call site passes `optional_missing_to_dedup=missing_optional`
into `evaluate_path_conventions` (`:1056`) **before** the `build_warnings(...)` call that
currently follows it — the mutated list is what `build_warnings` and the later
`AcceptanceSummary(...)` construction both see, with no further plumbing.

**The mutation fires ONLY inside the `if strict_metadata:` branch** of
`evaluate_path_conventions` (`summary_core.py:146-147`) — never unconditionally before that
branch. In lenient mode, `path_violations` is always `[]` (the function's
`strict_metadata=False` branch returns `format_warnings()`'s text instead), so the
double-*severity* contradiction FR-002 fixes cannot occur there. Concretely:
`optional_missing_to_dedup` is threaded into the call unconditionally (the parameter is
always passed the same list reference), but the mutation logic inside
`evaluate_path_conventions` only executes the dedup when it is also about to return the
`strict_metadata=True` branch's `path_violations`.

`path_violations` keeps rendering the **full, unfiltered** `missing_paths` inside
`format_errors()` exactly as today — only `optional_missing` loses the redundant entry. This
is what keeps `path_violations` (not `optional_missing`) as the side that wins, and keeps
`AcceptanceSummary.ok` unchanged for today's fixture (C-001). Dropping an entry from
`missing_paths` itself instead would let `path_violations` go empty for a mission whose only
declared path is the dual-declared one, silently flipping `AcceptanceSummary.ok` — the
`missing_optional`-wins outcome C-001 forbids.

**Dedup print removal (FR-003, independent of the interface change)**:
`cli/commands/accept.py:476-481`'s
`if summary.optional_missing: console.print("\n[yellow]Optional artifacts missing:...")`
block is deleted outright — `_print_acceptance_warnings` (called immediately above it, at
`:474`) already renders the identical "Optional artifacts missing: ..." line from
`summary.warnings` whenever `missing_optional` is non-empty (via `build_warnings`). This
applies even for a token declared only under `artifacts.optional` (the common
non-`contracts/` case, per spec's Edge Cases) — it removes a redundant *print*, not a
redundant *fact*.

**Scope boundary**: does NOT extend to `research`'s `data/` (declared under both
`artifacts.optional` and `paths.data`) — `_missing_artifacts` never checks `data/`, so no
double-report defect exists there today. This WP touches no `research`-specific code path.

## ⚡ Subtask T005: Add `optional_missing_to_dedup` parameter to `evaluate_path_conventions`

**Purpose**: Establish the additive interface change the pinned tests must not need to
change, per spec.md's Key Entities contract.

**Steps**:
1. In `src/specify_cli/acceptance/summary_core.py`, add
   `optional_missing_to_dedup: list[str] | None = None` as a new keyword-only parameter to
   `evaluate_path_conventions`'s signature (after `strict_metadata`, since both existing
   pinned tests call positionally through `strict_metadata=` and must continue to omit this
   new parameter entirely).
2. Add the docstring line specified in Context above, verbatim in substance, next to the
   existing "returns (path_violations, warning)" documentation.
3. Do not change the function's return type or arity — it must remain
   `tuple[list[str], str | None]`.

**Files**: `src/specify_cli/acceptance/summary_core.py`.

**Validation**: `test_strict_metadata_true_blocks_with_violation` and
`test_strict_metadata_false_downgrades_to_warning` still pass unmodified with zero changes to
their call sites (they simply don't pass the new parameter).

---

## ⚡ Subtask T006: Implement the dedup logic inside the `strict_metadata` branch

**Purpose**: The actual reconciliation — drop redundant `optional_missing` entries whose
normalized token also appears in the resolved `missing_paths`, only when strict.

**Steps**:
1. Inside `evaluate_path_conventions`, only within the `if strict_metadata:` branch (the one
   that currently does `return [path_result.format_errors() or _PATH_CONVENTIONS_NOT_SATISFIED], None`),
   and only when `optional_missing_to_dedup` is not `None`:
   - Import `artifact_tokens_for_mission` from `specify_cli.validators.paths` (added by WP01's
     T016) and call `artifact_tokens_for_mission(mission)` to get the `artifact_tokens` set —
     do **not** reimplement the `getattr(mission.config, "artifacts", None)`/`.required`/
     `.optional` defensive recipe inline here; `validate_mission_paths` and
     `evaluate_path_conventions` must consume the same single exported helper, not two
     independently-maintained copies of the same rule.
   - Build the filtered comparison set from `path_result.missing_paths_feature_relative`:
     `{_normalize_path_token(t) for t in path_result.missing_paths_feature_relative
     if _normalize_path_token(t) in artifact_tokens}`.
   - Mutate `optional_missing_to_dedup` **in place** (e.g. slice assignment
     `optional_missing_to_dedup[:] = [e for e in optional_missing_to_dedup
     if _normalize_path_token(e) not in filtered_set]`, or repeated `.remove()`) — do not
     reassign the parameter to a new list object; the caller's binding must see the mutation.
2. Ensure the lenient-mode (`strict_metadata=False`) branch never touches
   `optional_missing_to_dedup` at all — it returns before reaching this logic.
3. `path_violations`'s construction (`path_result.format_errors() or ...`) is untouched by
   this subtask — it still renders the full, unfiltered `missing_paths`.

**Files**: `src/specify_cli/acceptance/summary_core.py`.

**Validation**: A focused unit test on `evaluate_path_conventions` directly, passing a
`missing_optional`-shaped list containing `"contracts"` and a `mission`/`path_result` fixture
where `contracts` is both artifact-declared and in `missing_paths`; assert the list is
mutated to remove `"contracts"` after the call, in strict mode only.

---

## ⚡ Subtask T007: Wire the call site in `acceptance/__init__.py`

**Purpose**: Thread the dedup into the real `collect_feature_summary` flow so `build_warnings`
and `AcceptanceSummary` both see the deduped list.

**Steps**:
1. In `src/specify_cli/acceptance/__init__.py`, locate the call
   `path_violations, path_convention_warning = evaluate_path_conventions(mission, repo_root,
   feature_dir, planning_read_dir, strict_metadata=strict_metadata)` (around `:1056`), which
   currently runs **after** `missing_required, missing_optional = _missing_artifacts(planning_read_dir)`
   (`:1049`) and **before** the `build_warnings(missing_optional=missing_optional, ...)` call
   (`:1058-1059`).
2. Add `optional_missing_to_dedup=missing_optional` to the `evaluate_path_conventions(...)`
   call. Do not reorder the surrounding calls — `evaluate_path_conventions` must still run
   before `build_warnings`, since the mutation needs to land before `build_warnings` reads
   `missing_optional`.
3. Do not reassign `missing_optional` anywhere between `_missing_artifacts` and the
   `AcceptanceSummary(optional_missing=missing_optional, ...)` construction (`:1115`) — the
   same list object must flow through unchanged in identity so the in-place mutation is
   visible at both use sites.

**Files**: `src/specify_cli/acceptance/__init__.py`.

**Validation**: An integration-level test on `collect_feature_summary` (or via the `accept`
CLI) on a `software-dev`-shaped fixture missing `contracts/` in strict mode, asserting
`AcceptanceSummary.optional_missing` no longer contains `"contracts"` while
`AcceptanceSummary.path_violations` does (via its rendered text).

---

## ⚡ Subtask T008: Delete the duplicate print block in `accept.py`

**Purpose**: FR-003 — remove the cosmetic duplicate "Optional artifacts missing" print.

**Steps**:
1. In `src/specify_cli/cli/commands/accept.py`'s `_print_acceptance_summary` function
   (starts `:453`), delete the block:
   ```python
   if summary.optional_missing:
       console.print(
           "\n[yellow]Optional artifacts missing:[/yellow] "
           + ", ".join(summary.optional_missing)
       )
       console.print()
   ```
   (currently at `:476-481`, immediately after the `_print_acceptance_warnings(summary)` call
   at `:474`).
2. Confirm `_print_acceptance_warnings` (defined at `:438`) already renders the identical
   "Optional artifacts missing: ..." line from `summary.warnings` (built by `build_warnings`
   whenever `missing_optional` is non-empty) — no functional replacement needed, this is a
   pure deletion.
3. Do not touch `_print_acceptance_warnings` itself or any other code in
   `_print_acceptance_summary`.

**Files**: `src/specify_cli/cli/commands/accept.py`.

**Validation**: A console-render test asserting the literal substring
`"Optional artifacts missing"` appears **at most once** in `_print_acceptance_summary`'s
output for a fixture where `missing_optional` is non-empty.

---

## ⚡ Subtask T009: Write the four WP2 revert tests

**Purpose**: Red-first proof for FR-002/FR-003 (User Story 2, all four Acceptance Scenarios),
plus a dedicated guard for the `artifact_tokens` membership-filter's collision-avoidance
behavior.

**>>> DEVIATION FROM plan.md (TASKS-FRESH-002) <<<**
plan.md's "Red-first / revert discipline — summary table" (plan.md line 753), WP2 row,
"Revert test" column, reads **verbatim**:

> Asserts `"contracts"` surfaces through exactly one of `optional_missing`/`path_violations`
> AND `AcceptanceSummary.ok is False` for the dual-declared fixture; plus a console-render
> test asserting `"Optional artifacts missing"` prints at most once; plus a lenient-mode test
> on the same fixture asserting `optional_missing` is left untouched by the dedup.

That names exactly **three** revert tests for WP2 (dedup+`.ok` = Test (a) below,
console-render = Test (b), lenient-mode = Test (c)) — it names nothing corresponding to
Test (d). **Test (d) below — the `artifact_tokens` membership-filter collision guard,
including its (d-i)/(d-ii)/(d-iii) split — is a tasks-phase addition beyond plan.md's WP2 row
as quoted above.** Reason: it was added in response to TASKS-VERIFY-004 (the membership filter
needed its own presence/absence regression guard, which the original three tests do not
provide), then corrected per TASKS-FRESH-003 (the first attempt at this guard used a
same-branch-pair fixture that could not actually falsify the filter; it was replaced with the
(d-i)/(d-ii) split, which can), and then extended per TASKS-FRESH3-001 (that same fix
inadvertently dropped the only coverage for a *different* risk — full-token-vs-basename
collision — that the replaced fixture used to provide; (d-iii) restores it without regressing
(d-i)/(d-ii)'s filter-presence guard). Per this mission's CRITICAL CONSTRAINT, plan.md is not
edited to add a fourth test to the WP2 row — this note is the flag so a reviewer diffing
plan.md's literal WP2-row text (quoted above) against this WP file's Test (d) sees the addition
and its rationale without opening plan.md, and reads this as a deliberate, tracked correction
rather than silent drift from the settled plan.md contract.

**Steps**:
1. **Test (a) — dedup + pass/fail boundary**: using the real `collect_feature_summary` entry
   point (or the `accept` CLI invoked via `CliRunner`) — **not** a hand-built/mocked
   `software-dev`-shaped `SimpleNamespace` fixture in the style of the existing
   `TestEvaluatePathConventions` suite — with `contracts/` missing, strict mode, assert:
   - `"contracts"` (normalized) appears in exactly one of `AcceptanceSummary.optional_missing`
     / the rendered `path_violations` text — never both.
   - `AcceptanceSummary.ok is False` — the C-001 pass/fail-boundary guard (Scenario 2 of User
     Story 2 made concrete): the reconciliation direction must not flip `accept`'s pass/fail
     boundary for this fixture.
   The real entry point is required here (not merely preferred) because it is the only way
   this test also exercises WP01's actual `missing_paths_feature_relative` population code for
   the artifact-tagged branch, rather than only WP02's consumption/filtering logic — a mocked
   `SimpleNamespace` fixture would need the field hand-set to make the dedup fire, silently
   testing nothing about WP01's population correctness (TASKS-VERIFY-002). If a mocked fixture
   is used here instead for a compelling reason, note it explicitly in this WP's
   implementation notes and confirm WP01's T003/T004 already cover the population gap this
   would otherwise leave open (they do, as of WP01's own fix for the same finding).
   The `--json`-consistency assertion (Scenario 4) is **not** this test's responsibility — per
   plan.md's Test Strategy table, that check is WP04's T014 Assertion 3 alone; this test only
   needs the object-level (`AcceptanceSummary`) dedup + `.ok` assertions above.
2. **Test (b) — console-render dedup**: assert `_print_acceptance_summary`'s console output
   contains the literal substring `"Optional artifacts missing"` **at most once**, directly
   targeting the removed print block (FR-003 / Scenario 3 of User Story 2).
3. **Test (c) — lenient-mode untouched**: on the same dual-declared fixture with
   `strict_metadata=False`, assert `AcceptanceSummary.optional_missing` (or the raw
   `evaluate_path_conventions` return, whichever is more direct) is left **untouched** by the
   dedup — still contains `"contracts"` — pinning that the mutation fires only inside the
   strict-mode branch.
4. **Test (d) — collision guard for the `artifact_tokens` membership filter**: `path_result` is
   not an injectable argument of `evaluate_path_conventions`. Today's live signature
   (`summary_core.py:110-117`, before this WP's T005) is `evaluate_path_conventions(mission,
   repo_root, feature_dir, planning_read_dir, *, strict_metadata)`; after T005 it gains the new
   `optional_missing_to_dedup: list[str] | None = None` keyword parameter — but in neither form
   does it accept `path_result`. `path_result` is a local variable, computed internally via
   `validate_mission_paths`, never passed in. Build it by
   **monkeypatching `specify_cli.acceptance.summary_core.validate_mission_paths`**, matching
   the sibling `TestEvaluatePathConventions` class's existing convention
   (`tests/specify_cli/acceptance/test_acceptance_cores.py`), returning a `SimpleNamespace`
   with a pre-set `missing_paths_feature_relative`. This test's purpose is to isolate the
   membership-filter logic itself, not exercise WP01's population code, so a minimal `mission`
   is fine — but `mission.config.artifacts.optional`/`.required` must be real lists (since
   `artifact_tokens_for_mission` reads them for real, unmocked) and `mission.config.paths` only
   needs to be non-empty to pass `evaluate_path_conventions`'s own no-op guard.

   **(TASKS-FRESH2-001) The mocked `SimpleNamespace` must ALSO set two more attributes**, or
   the dedup mutation code this test is trying to exercise is never reached at all.
   `evaluate_path_conventions`'s live body (`summary_core.py:137-147`, confirmed against the
   current checkout) runs, in order: `path_result = validate_mission_paths(...)` → `if not
   path_result.missing_paths: return [], None` → (only if that guard passes) `if
   strict_metadata: return [path_result.format_errors() or _PATH_CONVENTIONS_NOT_SATISFIED],
   None` — and only past **both** of those does T006's dedup mutation code run. A
   `SimpleNamespace` built with only `missing_paths_feature_relative` set has no `missing_paths`
   attribute, so `if not path_result.missing_paths:` raises `AttributeError` before the dedup
   code is reached — the test cannot run as previously specified. Set, on the same
   `SimpleNamespace`, in addition to `missing_paths_feature_relative`:
   - `missing_paths=["placeholder"]` — a non-empty placeholder list; its content is irrelevant
     to Test (d), only its truthiness matters for the first guard (`if not
     path_result.missing_paths`).
   - `format_errors=lambda: "placeholder"` — a callable returning any string, needed because
     `strict_metadata=True` (used by (d-i), (d-ii), and (d-iii) below) reaches `path_result.
     format_errors()` before the dedup mutation runs.
   This matches the sibling `TestEvaluatePathConventions` class's own convention: e.g.
   `test_strict_metadata_true_blocks_with_violation`
   (`tests/specify_cli/acceptance/test_acceptance_cores.py:235-243`) sets
   `missing_paths=["src/"], format_errors=lambda: "missing src/"` on its own monkeypatched
   `SimpleNamespace` — this test's mock must set the equivalent pair, not `missing_paths_
   feature_relative` alone. **(d-i), (d-ii), and (d-iii) below all share this one
   mock-construction preamble, so this requirement applies to all three sub-cases identically**
   — do not add `missing_paths`/`format_errors` to only some of them.

   Per TASKS-FRESH-003: because `validate_mission_paths`'s own branch-selection uses the SAME
   `artifact_tokens` membership check to route a declared token to the artifact-tagged branch
   vs. the build/repo-root branch, a build/repo-root placeholder can never itself collide with
   `artifact_tokens` — so a same-branch-pair fixture (an artifact-tagged token vs. a
   differently-named build/repo-root token, the prior round's `docs/contracts` vs.
   `api/contracts` construction) cannot falsify the membership filter's presence regardless of
   the two token strings chosen — it exercises full-token-vs-basename comparison instead (a
   real but different guard). The genuine collision case requires the **absolute-path branch**
   specifically, since `if candidate.is_absolute():` is checked *before* the `artifact_tokens`
   `elif` (`validators/paths.py:196-198`), so an absolute declared path's normalized form CAN
   land inside `artifact_tokens` even though the token itself never took the artifact-tagged
   branch. Construct **three** sub-cases under this one Test (d):

   - **(d-i) genuine-collision outcome check** (documents correct behavior; NOT a
     filter-presence regression guard — see the note below): `mission.config.artifacts.optional
     = ["contracts"]`; monkeypatched `path_result.missing_paths_feature_relative = ["contracts",
     "contracts"]` — one entry standing in for the real artifact-tagged branch's own
     `"contracts"` (from a `paths.deliverables: "contracts/"` declaration) and one for an
     absolute-path branch placeholder (`_normalize_path_token("/contracts")` == `"contracts"`
     too, from an unrelated `/contracts` declared elsewhere in `mission.config.paths`) — both
     entries collapse to the identical string. Call `evaluate_path_conventions(mission, ...,
     strict_metadata=True, optional_missing_to_dedup=["contracts"])` and assert
     `optional_missing_to_dedup == []` (the dedup correctly fires for the genuine collision).
     Record explicitly in the test's own comments/docstring that this case does **not**
     distinguish "membership filter present" from "membership filter absent": an
     implementation that skipped the filter entirely (matching directly against the raw
     `missing_paths_feature_relative` list) would produce the identical `[]` outcome here,
     because both entries normalize to the same string. This sub-case documents that the
     filter's outcome stays correct when a genuine collision co-occurs with a same-string
     absolute-branch placeholder; it is not itself a regression guard.
   - **(d-ii) actual filter-presence regression guard**: a second `mission`/`path_result` pair
     where `mission.config.artifacts.optional = ["contracts"]` (so `artifact_tokens =
     {"contracts"}`; see the (TASKS-FRESH2-001) note immediately below for why this sub-case
     now deliberately makes `artifact_tokens` non-empty, unlike a prior draft) and
     `path_result.missing_paths_feature_relative = ["contracts", "build-secrets"]`: `"contracts"`
     stands in for a genuine artifact-tagged collision (a member of `artifact_tokens`, so it
     SHOULD be removed), and `"build-secrets"` stands in for an absolute-branch placeholder from
     an unrelated `/build-secrets` declaration — a token that is *not* a member of
     `artifact_tokens`, so it should NOT be removed. Call `evaluate_path_conventions` with
     `optional_missing_to_dedup=["contracts", "build-secrets"]` and assert
     `optional_missing_to_dedup == ["build-secrets"]` — i.e. `"contracts"` is removed **and**
     `"build-secrets"` survives, in the same call.

     **(TASKS-FRESH2-001) Why this two-entry, one-call construction — not a single
     `["build-secrets"]` list asserted "stays unchanged" — is the actual regression guard,
     not merely a coincidental value match:** a single-entry "unchanged" assertion cannot tell
     apart three implementations that all produce the SAME final list:
     (1) the correct implementation (filter present, membership check excludes
     `"build-secrets"`);
     (2) a mock that never reaches the dedup code at all (e.g. the first guard,
     `if not path_result.missing_paths:`, short-circuits because `missing_paths` was left
     unset/falsy) — the list is untouched not because the filter excluded it, but because the
     mutation code never ran;
     (3) an implementation with the membership filter silently no-op'd in some other way.
     The **two-entry** construction above breaks that ambiguity: it requires the dedup code to
     mutate the list (removing `"contracts"`) for the assertion to pass at all, which rules out
     early-return no-op (case 2) — an early return leaves the list as
     `["contracts", "build-secrets"]` in full, failing the `== ["build-secrets"]` assertion. It
     also rules out a filter-omitted implementation (matching directly against the raw
     `missing_paths_feature_relative` list without the `artifact_tokens` membership check): that
     would remove BOTH entries (both appear in `missing_paths_feature_relative`), producing
     `[]`, which also fails the assertion. **Only** a correct, filter-present implementation
     that actually reached the dedup code produces exactly `["build-secrets"]`. This is the
     genuine regression guard TASKS-VERIFY-004 originally asked for, and it is now falsifiable
     against "the function never got there" as well as against "the filter was removed" — unlike
     (d-i), where filter-present and filter-absent are indistinguishable (see (d-i)'s own note
     above).

   - **(d-iii) full-token-vs-basename collision guard (TASKS-FRESH3-001)**: uses two distinct
     multi-segment tokens that share a final path segment but differ earlier —
     `mission.config.artifacts.optional = ["docs/contracts"]` (so `artifact_tokens =
     {"docs/contracts"}`) and `path_result.missing_paths_feature_relative = ["docs/contracts",
     "api/contracts"]`. Call `evaluate_path_conventions` with
     `optional_missing_to_dedup=["docs/contracts", "api/contracts"]` and assert
     `optional_missing_to_dedup == ["api/contracts"]` — i.e. only the true full-token match
     (`"docs/contracts"`) is removed; the basename-sharing but full-token-distinct entry
     (`"api/contracts"`) survives. This falsifies a hypothetical implementation that normalized
     on `Path(t).name` (or any other basename reduction) instead of the pinned
     `_normalize_path_token` (`validators/paths.py:128-130`, which only strips leading/trailing
     slashes and never reduces to a final path component): such an implementation would collapse
     both `artifact_tokens` and both list entries to `"contracts"`, incorrectly removing BOTH
     entries and producing `[]` instead of `["api/contracts"]`. Neither (d-i) nor (d-ii) can
     catch this bug class — both use only single-segment tokens (`"contracts"`,
     `"build-secrets"`), so `Path(t).name` and the full normalized token are identical on their
     inputs. (d-iii) shares the same `missing_paths`/`format_errors` mock-construction preamble
     required above.

   Together, (d-i) and (d-ii) replace the prior round's single mismatched-string fixture
   (`docs/contracts` vs. `api/contracts`) **as a filter-presence guard** — per TASKS-FRESH-003,
   that fixture could not actually falsify the membership filter's presence under either
   implementation. (d-iii) above reintroduces the same `docs/contracts`/`api/contracts` token
   pair, but for a different assertion than that prior fixture made: it is a full-token-vs-
   basename regression guard (TASKS-FRESH3-001), not a filter-presence guard — filter-presence
   remains (d-ii)'s exclusive job.
5. Run all four tests (Test (d) counting as one test comprising its three constructed
   sub-cases, (d-i), (d-ii), and (d-iii)) against the current (pre-T005-T008) code first to
   confirm genuinely red — pre-T005/T006, `optional_missing_to_dedup` is never mutated at all,
   so (a), (d-i), (d-ii), and (d-iii) are all red because the expected mutation never happens
   (not specifically because the membership filter is missing, and not specifically because of
   basename-vs-full-token normalization) — then implement T005-T008 and re-run to confirm
   green. (d-ii) additionally distinguishes a *filter-omitted* future regression from a working
   implementation, which (d-i) alone cannot (TASKS-FRESH-003). (d-iii) additionally distinguishes
   a *basename-normalization* future regression from a working implementation, which neither
   (d-i) nor (d-ii) can (TASKS-FRESH3-001).

**Files**: `tests/specify_cli/acceptance/`, `tests/specify_cli/cli/commands/`.

**Validation**: `pytest <chosen files> -v` — red before T005-T008, green after; explicit
confirmation each of the four tests individually flips.

## Definition of Done

- T005-T009 all recorded via `spec-kitty agent tasks mark-status <Txxx> --status done`
  (event-sourced status).
- The four revert tests in T009 (a-d) are red against pre-T005/T008 code and green after —
  genuinely red-first (NFR-001). Test (d) comprises its three constructed sub-cases, (d-i),
  (d-ii), and (d-iii) — see T009 step 4 (TASKS-FRESH-003, TASKS-FRESH3-001).
- The three SC-005 pinned tests
  (`test_strict_metadata_true_blocks_with_violation`,
  `test_strict_metadata_false_downgrades_to_warning`,
  `test_lenient_path_convention_warning_is_rendered_in_console`) remain green, **unmodified**
  (NFR-002).
- `AcceptanceSummary.ok` is unchanged (`False`) for the SC-005/FR-007 dual-declared fixture —
  the reconciliation direction did not flip the pass/fail boundary (C-001).
- `--json` internal consistency for the dedup (spec.md Edge Cases / Scenario 4) is WP04's
  sole responsibility (T014 Assertion 3, per plan.md's Test Strategy table) — this WP's own
  Definition of Done does not gate on it.
- Full baseline re-run: `pytest tests/specify_cli/acceptance/ tests/specify_cli/cli/commands/test_accept_warnings_render.py tests/agent/test_validators_unit.py tests/characterization/test_trio_json_envelope.py -q`
  completes with 0 failed (per plan.md's "Baseline honesty" section), in addition to the 3
  named pinned tests above.
- `ruff`/`mypy` clean on touched files.

## Risks

- **Mutation-in-place is a departure from this module's pure-transform convention**: every
  sibling function in `summary_core.py` (`build_warnings`, `build_work_package_state`, etc.)
  is documented "Pure:" and communicates results only via return values. The docstring
  addition in T005 exists specifically so a reviewer does not mistake
  `optional_missing_to_dedup` for an inert, no-op pass-through parameter — do not weaken or
  omit that docstring line.
- **Two distinct collision risks, each now guarded by a dedicated test case (TASKS-FRESH-003,
  TASKS-FRESH3-001)**:
  (1) comparing only last-path-segments (rather than the full normalized-relative-to-
  `feature_dir` token) would incorrectly match a hypothetical future `docs/contracts` optional
  artifact against an unrelated `api/contracts` declared path — full-token (not basename)
  comparison forecloses this; do not simplify to a basename comparison for expedience. T009's
  Test (d), case (d-iii), directly exercises this (TASKS-FRESH3-001): round 3's replacement of
  the old same-purpose fixture with (d-i)/(d-ii)'s single-segment tokens left this risk
  asserted-as-guarded but untested — (d-iii) recovers that coverage using two distinct
  multi-segment tokens sharing a final path segment, alongside (not instead of) (d-i)/(d-ii)'s
  filter-presence guard. (2) a
  placeholder entry's normalized token spuriously matching an unrelated `artifact_tokens`
  member/`optional_missing` entry that isn't really an artifact-tagged duplicate — the
  `artifact_tokens` membership filter forecloses this for the case that's actually
  distinguishable (a placeholder token NOT in `artifact_tokens`); T009's Test (d), case
  (d-ii), directly exercises this rather than leaving it correct-by-inspection. Case (d-i)
  demonstrates outcome correctness for a genuine collision but is not itself a filter-presence
  regression guard (see T009 step 4 for why).
- **owned_files overlaps (full accounting, re-derived from `wps.yaml` live)**: this WP's
  `owned_files` overlap with three other WPs. All are deliberate — WP01, WP02, WP03, and WP04
  form a strict linear dependency chain (WP01→WP02→WP03→WP04) and are never worked
  concurrently, so the no-overlap convention (which exists to prevent parallel write
  collisions) does not apply to any of them:
  - **WP03** on `src/specify_cli/cli/commands/accept.py` (both WPs edit this file) and on the
    `tests/specify_cli/cli/commands/**` glob (both WPs' test coverage lives here — WP02's T009
    and WP03's T012).
  - **WP01** on the `tests/specify_cli/acceptance/**` glob (WP01's T003/T004 and WP02's T009
    revert tests may land in the same directory).
  - **WP04** on the same `tests/specify_cli/acceptance/**` glob — WP04's single owned file
    (`tests/specify_cli/acceptance/test_accept_contracts_path_repro.py`) falls inside it.

## Reviewer Guidance

- Confirm the mutation fires **only** inside the `if strict_metadata:` branch — a lenient-mode
  leak would silently change `--lenient`'s existing behavior, which FR-008 forbids.
- Confirm `path_violations` still renders the full, unfiltered `missing_paths` — this is the
  C-001 guard; dropping an entry from `missing_paths` itself (rather than `optional_missing`)
  would be the wrong direction and could silently flip `AcceptanceSummary.ok`.
- Confirm the two pinned `evaluate_path_conventions` tests were not edited at all — not even a
  parameter added to their call sites (NFR-002: "zero edits").
- Confirm `evaluate_path_conventions` calls WP01's exported `artifact_tokens_for_mission`
  helper (`validators/paths.py`, T016) rather than reimplementing the defensive
  `getattr(..., ()) or ()` recipe inline — a second hand-copy of that recipe here is exactly
  the drift risk WP01's T016 extraction exists to close.
- Confirm the duplicate-print deletion (T008) is a clean removal with no replacement text —
  `_print_acceptance_warnings` already covers the message.

---

Run `spec-kitty agent action implement WP02 --agent claude` to begin implementation.
