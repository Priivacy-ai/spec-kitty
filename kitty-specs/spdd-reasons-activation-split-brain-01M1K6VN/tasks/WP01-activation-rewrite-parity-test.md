---
work_package_id: WP01
title: activation.py rewrite + mandatory parity test
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-004
planning_base_branch: fix/spdd-reasons-activation-split-brain-3838
merge_target_branch: fix/spdd-reasons-activation-split-brain-3838
branch_strategy: Planning artifacts for this mission were generated on fix/spdd-reasons-activation-split-brain-3838. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spdd-reasons-activation-split-brain-3838 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history: []
agent_profile: implementer-ivan
authoritative_surface: src/charter/offering/spdd_reasons/
create_intent:
- tests/charter/test_spdd_reasons_activation_parity.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/offering/spdd_reasons/activation.py
- tests/charter/test_spdd_reasons_activation_parity.py
role: implementer
tags: []
tracker_refs: []
---

# WP01 — Rewrite `is_spdd_reasons_active` to read `activated_*`; mandatory parity test

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Replace `is_spdd_reasons_active`'s body (`src/charter/offering/spdd_reasons/activation.py`) with a raw,
`charter.activation`-import-free read of `activated_paradigms`/`activated_directives`/`activated_tactics`
via the INV-2 two-file pointer resolution `PackContext.from_config` implements — instead of the current,
stale `governance.charter.selected_*` read — and back it with the mandatory parity test that proves the
two implementations agree (Decision Record 1, FR-001/002/003/004/005). This WP delivers the mission's
**load-bearing artifact**: without the parity test, nothing stops the two readers drifting apart again.

## Context

This is THE defect the mission exists to fix (spec.md Summary): `is_spdd_reasons_active` currently reads
`charter.yaml`'s authored `governance.charter.selected_*`/`directives:` sections, which the compiler's own
docstring says are retired as an activation source. `PackContext.from_config` (`src/charter/activation/pack_context.py`)
is the real authority. `charter.offering.spdd_reasons.activation` cannot import `charter.activation.pack_context.PackContext`
directly — C-004 forbids `charter.offering -> charter.activation` in any form, enforced non-vacuously by
`tests/architectural/test_charter_offering_does_not_import_activation.py`. So this WP gives `activation.py`
its **own** raw `ruamel.yaml` read that replicates `PackContext.from_config`'s INV-2 resolution steps
(Decision Record 1, Option A) — a second, independent implementation of the *reading* half of INV-2, which
is exactly why the parity test (T002) is mandatory, not optional (C-003).

**Bug-preserving-test discipline (binding for this WP and the whole mission):** every test this WP adds
must fail against `main`'s current body before the rewrite, and pass after. T001/T002/T003 below state,
for each test, the exact reason it is RED on `main` today — not merely "should be red."

**This WP has no dependency on WP02/WP03** (different files, no shared code) but **WP04 depends on this
WP's implementation commit** — its bucket-3 fixture rewrites (8 test methods) are red against this WP's
OLD (pre-fix) body and must go green only after this WP's rewrite lands. Coordinate with whoever
implements WP04: do not consider this WP "done" for planning purposes until its implementation commit
(T005) has actually merged/landed on the shared branch, since WP04's own red-first commits are meaningless
until they can be run against this WP's new code.

**Cross-WP semantic chokepoint (read before writing the oracle in T002 or the conversion logic in T004):**
WP01, WP02, and WP03 are file-disjoint and may be implemented in parallel, but **all three encode the
same semantic contract** — "an absent `activated_<kind>` key means `None`, and `None` means all built-ins
available; an explicit `[]` means nothing." A reviewer must not review this WP's `None`-handling in
isolation from WP02's and WP03's — if any one of the three treats `None` as an empty set (the exact bug
class this mission exists to close, per the mission brief), the mission's own goal is violated even if
this WP's own tests pass. When this WP is reviewed, cross-check its oracle/conversion logic against WP02's
and WP03's for the identical semantic rule before approving.

**One-PR-shape note:** this mission ships as one PR across all 5 WPs (plan.md, "PR shape"). This WP's
diff is the largest single-file change (a full-body rewrite of a ~200-line module) but is self-contained
and narrowly scoped to one function/module — it does not by itself make the aggregate diff unreviewable
in one sitting.

**Baseline capture (plan.md section (g), mandatory prerequisite — do this BEFORE any other subtask):**
Before touching `activation.py`'s body, run the exact scoped baseline command from plan.md section (f)/(g)
in your own workspace and capture the **full list of failing node-ids** (not a bare count):

```
pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py \
  tests/architectural/test_no_dead_symbols.py -q
```

Classify every failing node-id against CLAUDE.md's three baseline-red categories (pre-existing P0 red,
e.g. issue #3284; CI-environment-only; stale-install false-red) before attributing any red to this
mission. Re-run the identical command after T005's implementation commit and diff the new failing set
against this captured baseline — any newly-red node-id not in the baseline is this WP's own regression to
fix before considering the WP done; any baseline-red node-id that stays red, unchanged, is out of scope
(C-005) — do not fix it, do not re-file it. (WP02 and WP03 independently repeat this same baseline capture
in their own workspaces per section (g) — do not assume one WP's capture covers another's parallel
workspace.)

### Marker discipline (verified live against `pytest.ini` and the workflow files for this WP — SK-144/#3241)

`tests/charter/test_spdd_reasons_activation_parity.py` (NEW) must carry
`pytestmark = [pytest.mark.fast, pytest.mark.doctrine]` — verified against this file's real sibling
convention: `tests/charter/test_activate_resolves_no_answers_edit.py` carries
`pytestmark = [pytest.mark.fast, pytest.mark.doctrine]` and `tests/charter/test_answers_inert_and_org_union.py`
carries `pytestmark = [pytest.mark.unit, pytest.mark.fast, pytest.mark.doctrine]` (both confirmed by
reading the live files, not assumed from plan.md). The `fast` marker is what actually gates collection:
`fast-tests-charter` (`ci-quality.yml`) runs `pytest tests/charter ... -m "fast and not windows_ci and not
timing" ... --cov=charter --cov-fail-under=55`, and `doctrine-charter-tests.yml`'s dedicated job runs
`pytest tests/doctrine/ tests/charter/ ... -m "fast and not windows_ci and not timing"` — **both select by
the `fast` marker plus path membership under `tests/charter/`, NOT by the `doctrine` marker**, which is
not read by either job's `-m` filter. Adding `pytest.mark.doctrine` is therefore a sibling-convention
courtesy, not functionally required for CI collection by either job — stated here so a reviewer does not
mistake it for load-bearing. Do not omit `fast`; that IS load-bearing (its absence would make this
mandatory parity test CI-invisible in both blocking jobs).

### `__all__` / C-007 disposition

`activation.py` currently declares **no** `__all__` at all (confirmed by reading the live file — this is a
pre-existing gap FR-003 explicitly requires this WP to close). Add, at minimum:
`__all__ = ["is_spdd_reasons_active", "clear_activation_cache"]`. Both already have real callers in `src/`
(`is_spdd_reasons_active`: `bootstrap_text.py:332`, `template_renderer.py`'s `apply_spdd_blocks_for_project`,
and the `__init__.py` re-export; `clear_activation_cache`: test-only reset hook, kept in `__all__` per
FR-001(e)'s explicit instruction even though its only callers are tests). If T004's implementation
introduces any NEW private helper function (e.g. a small "resolve the three-state value" helper factored
out of the INV-2 replication), it does **not** need to be added to `__all__` — keep it private
(leading-underscore name), with `is_spdd_reasons_active`/`_compute_active`-equivalent as its real `src/`
caller inside the same module. `tests/architectural/test_no_dead_symbols.py` walks `__all__`, not every
private symbol, so a private helper with a real in-module caller is already satisfied.

## Subtask T001: Baseline capture + red-first FR-004 absent-config regression test

**Purpose**: Establish the pre-mission baseline (section g) and commit the FR-004 absent-`.kittify/config.yaml`
pin as a red-first test, per C-011.

**Steps**:
1. Run the baseline command from the Context section above; save the full failing node-id list somewhere
   you can diff against later (a scratch file is fine — it is not a mission deliverable).
2. Write a test (in the new `tests/charter/test_spdd_reasons_activation_parity.py`, or a small dedicated
   test in the same file — your call, keep it in the parity test's file since FR-004 is part of the same
   module rewrite) asserting: given a `tmp_path` with **no** `.kittify/config.yaml` at all,
   `is_spdd_reasons_active(tmp_path)` returns `False`.
3. **Why this must be committed RED first, per C-011**: against the CURRENT (pre-fix) body, an absent
   `.kittify/charter/` directory already returns `False` (see `is_spdd_reasons_active`'s existing early
   return on `charter_dir.exists()`), so this specific assertion is trivially GREEN on `main` today — it is
   not itself a red-on-main regression test. What makes it belong in the ATDD-first sequence is that it
   pins the value the REWRITE (T004) must preserve byte-for-byte per FR-004's explicit carve-out from full
   `PackContext` parity — commit it before T004's rewrite so the rewrite's own correctness against this
   pinned case is verified by a pre-existing assertion, not asserted after the fact. State this explicitly
   in the test's docstring/comment: this is a **pin**, not a red-on-main regression, and say why.
4. **FR-004's own falsifiable Acceptance Criterion, through the real entry point (spec.md FR-004 row) —
   add this as a second test in the same file, distinct from step 2's assertion:** given a `tmp_path` with
   no `.kittify/config.yaml` on disk, call `apply_spdd_blocks_for_project(template_text, tmp_path)`
   directly (`src/charter/offering/spdd_reasons/template_renderer.py:179`, real signature
   `apply_spdd_blocks_for_project(template_text: str, repo_root: Path | None) -> str` — re-verify this
   line number against the live file before citing it) with a `template_text` that contains a real
   `spdd:reasons-block:start`/`spdd:reasons-block:end` marker pair (import `REASONS_BLOCK_START`/
   `REASONS_BLOCK_END` from the same module, or inline the literal marker comment strings — the function's
   own fast path skips the activation read entirely when no marker is present in `template_text`, so a
   marker-free fixture would not exercise this AC at all). Assert the returned text has the block's marker
   lines AND content stripped entirely (matches what `process_spdd_blocks(template_text, active=False)`
   produces) — this is the spec's own "equivalent direct call" allowance, distinct from step 2's
   `is_spdd_reasons_active(tmp_path) is False` pin, which exercises the activation helper in isolation
   rather than the real template-stripping entry point FR-004's AC names. Same pin/not-red-on-main
   rationale as step 3 applies here too (the old body already returns `False`/strips blocks for an absent
   `.kittify/charter/` directory) — state that in this test's docstring/comment as well. This test lives in
   the same file and inherits the file's module-level `pytestmark = [pytest.mark.fast, pytest.mark.doctrine]`
   — no separate marker declaration needed; it is collected by the same `fast-tests-charter` /
   `doctrine-charter-tests.yml` CI jobs named in the Marker discipline section above.

**Files**: `tests/charter/test_spdd_reasons_activation_parity.py` (new, ~45 lines for this subtask's slice)
**Validation**: `pytest tests/charter/test_spdd_reasons_activation_parity.py -k "absent_config or apply_spdd_blocks" -v`
— both pass against the old and new body (by design, per the notes above).

## Subtask T002: The parity test — the mandatory, load-bearing artifact (FR-002)

**Purpose**: Write the fixture-matrix parity test comparing the (not-yet-rewritten) `is_spdd_reasons_active`
against `PackContext.from_config()`'s real `activated_*` fields, committed RED first against the OLD body.

**Steps**:
1. Create `tests/charter/test_spdd_reasons_activation_parity.py` (if not already started in T001) with
   `pytestmark = [pytest.mark.fast, pytest.mark.doctrine]` per the marker discipline above.
2. Build the fixture matrix per plan.md section (b): three states (absent key / explicit `[]` / non-empty
   list containing a SPDD-relevant id) × three kinds (`activated_paradigms` with
   `structured-prompt-driven-development`; `activated_tactics` with `reasons-canvas-fill` and, separately,
   `reasons-canvas-review`; `activated_directives` with `DIRECTIVE_038` AND, in a separate parametrized
   case, its numeric-hint-slug form `038-structured-prompt-boundary`) × two pointer shapes (`config.yaml`
   with no `charter:` key, `activated_*` directly on `config.yaml`; `config.yaml` with a `charter:` string
   pointer to a separate `charter.yaml` carrying `activated_*` at its top level — this repo's own dogfood
   shape). Use `pytest.mark.parametrize` with ids naming the state/kind/pointer-shape combination so a
   failure names exactly which fixture combination disagreed (not an opaque smoke result — this is an
   explicit spec requirement, User Story 1 Scenario 4).
3. **The oracle MUST NOT use `x or set()`.** Write the disjunction as:
   `pack_context.activated_paradigms is None or PARADIGM_ID in pack_context.activated_paradigms`, and the
   equivalent `is None or <id> in <field>` form for tactics (either `TACTIC_FILL_ID` or `TACTIC_REVIEW_ID`
   present) and directives (any activated id matches `_is_directive_038`-equivalent logic — you may import
   `activation.py`'s own `_is_directive_038`/`DIRECTIVE_ID`/`DIRECTIVE_NUMERIC_HINT` constants for the
   matching logic ONLY, since that is matching logic being reused, not the activation-source read under
   test — importing the module's own constants/pure-matching-helper is fine; do not import
   `charter.activation.*` here). Every fixture asserts
   `is_spdd_reasons_active(tmp_path) == <hand-computed disjunction over PackContext.from_config(tmp_path)>`.
4. Add the same-process two-call mutation case (FR-002): call `is_spdd_reasons_active(tmp_path)` once with
   `activated_paradigms: []`, then rewrite `.kittify/config.yaml` on disk with
   `activated_paradigms: [structured-prompt-driven-development]`, call again in the same process (no
   interpreter restart), and assert the second call returns `True` (reflecting the mutation) — this is the
   direct regression test for T004's cache-key fix.
5. **Why every fixture in this test is RED on `main` today, concretely**: `is_spdd_reasons_active`'s
   current body never reads `.kittify/config.yaml` or any `activated_*` key at all — it reads
   `.kittify/charter/charter.yaml`'s `governance:`/`directives:` sections exclusively (see
   `_compute_active`/`_governance_selects_pack`/`_directives_select_pack` in the live file). Every fixture
   this test constructs writes ONLY `.kittify/config.yaml` (optionally with a `charter:` pointer) and
   deliberately leaves `governance.charter.selected_*` absent/empty — so on `main`, `_compute_active` sees
   an absent/empty `governance:`/`directives:` section regardless of what `activated_*` says, and
   `is_spdd_reasons_active` returns `False` unconditionally for every "selector present" fixture in the
   matrix. The oracle expects `True` for those fixtures. This is a real, structural RED — not a
   coincidence of one fixture's values — verify it by actually running this test against the pre-rewrite
   body before starting T004.

**Files**: `tests/charter/test_spdd_reasons_activation_parity.py` (~180-220 lines including T001's slice)
**Validation**: `pytest tests/charter/test_spdd_reasons_activation_parity.py -v` — every non-`absent_config`
case is RED before T004, GREEN after.

## Subtask T003: Confirm FR-004's carve-out reachability claim (read-only verification)

**Purpose**: FR-004 states, as a settled spec-time finding (not deferred to implementation), that
`command_renderer.py`'s `apply_spdd_blocks_for_project` IS reached before `.kittify/config.yaml` exists
during `spec-kitty init`, while `bootstrap_text.py:332` and `asset_generator.py`'s `render_command_template`
are NOT. Re-verify this against the live code before relying on it (citation-drift discipline) — do not
re-derive it from scratch, just confirm the call chain still holds.

**Steps**:
1. Read `src/specify_cli/init.py`'s `command_installer.install` call site (the `elif agent_key in
   ("codex", "vibe", "pi", "letta")` branch) and confirm it calls into `command_installer.py`'s
   `_render_command_skill` → `command_renderer.render(..., repo_root=repo_root)` →
   `command_renderer.py`'s `apply_spdd_blocks_for_project`, and that this executes before
   `_save_vcs_config`/`save_agent_config` write `.kittify/config.yaml`.
2. If the call chain has drifted (symbol renamed, order changed), note the drift in this WP's PR
   description — do not silently "fix" the spec's claim by editing spec.md; flag it for the reviewer.
   If it still holds as described, no code or doc change is needed for this subtask — it exists to catch
   drift before T004 relies on FR-004's carve-out being safe.

**Files**: none changed (verification-only)
**Validation**: Manual trace confirmed; note any drift in the PR description.

## Subtask T004: The full-body rewrite (FR-001, FR-003, FR-005)

**Purpose**: Replace `_compute_active`/`_governance_selects_pack`/`_directives_select_pack` with the raw,
INV-2-aware `activated_*` read, add `__all__` (folded into this same commit per Standing Order #2 /
plan.md section (h) — no separate campsite-clean commit), and turn T001/T002's red tests GREEN.

**Steps**:
1. Replace `is_spdd_reasons_active`'s supporting functions with a body that:
   a. Loads `.kittify/config.yaml` (absent → return `False`, the FR-004 pin, preserved from T001/T003's
      confirmed carve-out — keep a code comment here stating this is a deliberate, evidence-based
      divergence from full `PackContext` parity, not an oversight, per NFR-001).
   b. Checks for a `charter:` key whose value is a **string** (mirror
      `pack_context.resolve_charter_yaml_pointer`'s "only a string is a pointer" rule — a mapping
      `charter:` namespace, e.g. a legacy inline block, is NOT a pointer; do not stringify it into a
      path).
   c. Pointer present → resolve it relative to `repo_root` if not absolute, then load that file's
      top-level `activated_paradigms`/`activated_directives`/`activated_tactics`. Missing/malformed file
      at the pointer target → raise (mirror `_load_charter_activation_source`'s fail-loud
      `CharterPackConfigError`-equivalent — you do not need to import `CharterPackConfigError` itself
      from `charter.activation`; raise a plain `ValueError`/module-local exception carrying an equivalent
      message, since importing that exception class would itself violate C-004). Pointer absent → read
      those same three keys directly from `config.yaml` itself.
   d. Apply the three-state semantics verbatim, matching `_read_list_key`'s contract: key absent → `None`
      (treated by the disjunction as "selector satisfied," matching Decision Record 1's per-kind "all
      built-ins" semantics for this narrow-replication scope); key present as `[]` → explicit empty
      (`frozenset()`); key present non-empty → the set of ids. **Do not use `x or set()` anywhere in this
      path** — that idiom is the exact truthiness-collapse bug class this WP exists to avoid reintroducing
      (see the parity test's own oracle discipline in T002, and the cross-WP chokepoint note in Context).
   e. Malformed top-level YAML in `config.yaml` OR the pointed `charter.yaml` → propagate (raise), never a
      silent `False`/`True` (FR-005).
   f. Preserve `_is_directive_038` (the numeric-hint + case-insensitive matching logic) verbatim — this is
      matching logic, not a source-of-truth question, and is explicitly out of scope to change (spec Edge
      Cases).
   g. **Second carve-out, symmetric with (a)'s FR-004 carve-out — also needs a named code comment:** the
      rewritten body deliberately does NOT apply `compile_charter`'s `project_configured` gate
      (`src/charter/activation/compiler.py`'s `_resolve_config_activated_roots`, re-verify the exact line
      span against the live file before citing it — currently `compiler.py:101-179`, covering
      `_CONFIG_ACTIVATION_FIELDS` through the `project_configured` check). That gate means: once a project
      has set ANY of the seven `activated_<kind>` fields anywhere in its activation source,
      `compile_charter`'s real delivered authority stops treating an OTHER, still-absent `activated_<kind>`
      key as "all built-ins" — it resolves to `frozenset()` instead. This WP's replication tracks
      `PackContext.from_config`'s raw, unconditional per-kind semantics instead, per Decision Record 1's
      scope boundary (plan.md section (a) item 1, "Explicit carve-out, mirroring FR-004's precedent").
      Add a code comment on the rewritten `is_spdd_reasons_active` (or its module docstring) stating this
      divergence explicitly and citing Decision Record 1, so a future reader has a named starting point
      rather than an implicit, undocumented gap — the same treatment step (a) above gives the FR-004
      absent-config-file carve-out.
2. **Cache-key fix (FR-001(e))**: the current per-process cache is keyed on `.kittify/charter/charter.yaml`'s
   mtime alone — the old single-file assumption. Pick one of the two documented options and state which in
   a code comment: (i) compose the cache key from BOTH `.kittify/config.yaml`'s mtime and the resolved
   pointer target's mtime (`None` when no pointer), so a same-process edit to either file invalidates the
   cache; or (ii) retire per-process caching entirely, matching `PackContext.from_config`'s always-fresh
   semantics (state the `<50ms typical` budget rationale from `contracts/activation.md` if you pick this
   option — the rewrite reads at most two YAML files, the same count `PackContext.from_config` itself
   reads, so retiring the cache stays within budget). `clear_activation_cache` stays in `__all__` either
   way (T002's same-process mutation test exercises whichever option you pick).
3. Add `__all__ = ["is_spdd_reasons_active", "clear_activation_cache"]` at module level (FR-003), per the
   `__all__` disposition note in Context above.
4. Update the module docstring to describe the new source of truth (drop the stale reference to
   `governance:`/`directives:` sections as the read target).
5. Run T001/T002's tests — both must now be GREEN. Re-run the full scoped baseline command and diff
   against the captured baseline (Context section) — no newly-red node-id outside this mission's own
   intentionally-flipped tests.

**Files**: `src/charter/offering/spdd_reasons/activation.py` (full-body rewrite, ~150-200 lines net)
**Validation**: `pytest tests/charter/test_spdd_reasons_activation_parity.py tests/architectural/test_charter_offering_does_not_import_activation.py tests/architectural/test_no_dead_symbols.py -v`

## Subtask T005: Re-run the C-004/NFR-002/NFR-003 gates against the finished diff

**Purpose**: Confirm the rewrite introduces no `charter.activation` import and that the dead-symbol gate
stays green, as a distinct final verification step (not merely "tests passed").

**Steps**:
1. `pytest tests/architectural/test_charter_offering_does_not_import_activation.py -v` — must show zero
   violations against this WP's diff.
2. `pytest tests/architectural/test_no_dead_symbols.py -v` — must pass; confirm `__all__`'s two entries
   both resolve to real callers.
3. `ruff check src/charter/offering/spdd_reasons/activation.py tests/charter/test_spdd_reasons_activation_parity.py`
   and `ruff check ... --select TID251` on the same paths (advisory + enforced-TID251 respectively, per
   plan.md section f) — fix anything TID251 flags; ruff's general findings are advisory but should still be
   addressed per repo Code Style rules.
4. Commit the implementation as its own commit, separate from T001/T002's red-first test commit(s), per
   C-011.

**Files**: none new (verification only)
**Validation**: All four commands above pass/report zero violations.

## Definition of Done

- `tests/charter/test_spdd_reasons_activation_parity.py` exists, carries `pytest.mark.fast` +
  `pytest.mark.doctrine`, and was committed RED (against the pre-fix body) before the implementation
  commit, per `spec-kitty agent tasks mark-status T00x --status done` records for each subtask.
- `is_spdd_reasons_active`'s body no longer reads `governance.charter.selected_*`/`directives:`; it reads
  `activated_*` via the raw INV-2 replication described above.
- `__all__` declared on `activation.py`; `test_no_dead_symbols.py` passes.
- `test_charter_offering_does_not_import_activation.py` passes with zero violations.
- The FR-004 absent-config pin and FR-005 fail-loud behavior are both covered by tests and pass, including
  FR-004's own falsifiable Acceptance Criterion through the real `apply_spdd_blocks_for_project` entry
  point (T001 step 4) — not merely `is_spdd_reasons_active(tmp_path) is False` in isolation.
- The cache-key fix is implemented (either option) and T002's same-process mutation case passes.
- Baseline diff shows no newly-red node-id outside this mission's own intentionally-flipped tests.

## Risks

- **Truthiness-collapse regression**: any `x or set()`/`if activated_paradigms:` shortcut anywhere in the
  new body silently reintroduces the exact bug class this mission exists to close. Grep the finished diff
  for `or set()`, `or frozenset()`, and bare `if activated_` truthiness checks before considering T004
  done.
- **Cache-key omission**: forgetting the cache-key fix (or picking cache retirement without confirming the
  `<50ms` budget still holds) would leave T002's same-process mutation case failing silently if that
  specific assertion is accidentally skipped in a partial test run — always run the full parity file, not
  a `-k` filtered subset, before declaring T004 done.
- **C-004 violation**: any accidental `from charter.activation import ...` (even inside a docstring-adjacent
  comment meant as an example) risks a reviewer or future editor copy-pasting it into real code — keep the
  rewrite's imports to `ruamel.yaml`, stdlib, and `activation.py`'s own existing constants only.

## Reviewer Guidance

- Confirm the oracle in T002 uses `is None` disjunction, never `x or set()`.
- Confirm every fixture in T002 was actually run against the pre-fix body (ask for the RED-run output, not
  just a claim) before trusting the "RED on main" statement in this WP's PR description.
- Confirm `__all__`'s two entries both have real `src/` callers (not just test callers).
- Cross-check this WP's `None`-handling against WP02's and WP03's diffs for the identical semantic rule
  (the cross-WP chokepoint note in Context) — do not approve in isolation.
- Confirm no `charter.activation.*` import was added anywhere under `src/charter/offering/`.

Implementation command: `spec-kitty agent action implement WP01 --agent claude`
