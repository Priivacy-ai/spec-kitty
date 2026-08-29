---
work_package_id: WP04
title: DRG-root-graph mismatch diagnostic + reflexivity carve-outs (FR-004)
dependencies:
- WP03
requirement_refs:
- FR-004
- C-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
history: []
authoritative_surface: src/specify_cli/doctrine/pack_validator.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/pack_validator.py
- src/specify_cli/doctrine/pack_assembler.py
- src/specify_cli/cli/commands/doctrine.py
- tests/specify_cli/doctrine/test_pack_validator.py
- tests/specify_cli/doctrine/test_pack_assembler.py
- tests/cli/test_doctrine_org_commands.py
- docs/changelog/CHANGELOG.md
tags: []
---

## Objective

Add an additive `pack validate` check that warns when a pack's DRG content lives only under
`drg/*.graph.yaml` fragments with no pack-root `*.graph.yaml` — the shape the runtime
(`src/charter/activation/_drg_helpers.py:load_validated_graph`) never reads, which sibling mission #3384
documents as **zeroing the action grain** at adoption. Gate this new check behind a
keyword-only `check_drg_root: bool = True` parameter on `validate_pack()`, and set that
parameter correctly at `validate_pack()`'s two other call sites per operator ruling #2.

## Context

**This is the highest-surface-area WP in the mission** — a new helper, a signature change on
`validate_pack()`, and one call-site edit each in two *other* files, plus a changelog entry.
Read this Context section fully before starting; the carve-out treatment for the two other
call sites is governed by a **binding operator ruling** (`reviews/plan.ruling.md`) that
inverted part of the original spec design mid-flight — do not implement the pre-ruling
version described anywhere else in this repo's history.

**Why the check exists**: `pack_validator.py`'s existing `_validate_drg`
(`:480-609`) only inspects fragments *inside* `drg/` (`drg_dir.glob("*.graph.yaml")`, `:506`)
— it never looks at the pack root. A pack authored exactly per the guide's `drg/` layout
passes `pack validate` cleanly today, and, per sibling mission #3384, silently loses its DRG
content at runtime. **Explicitly out of scope (C-002)**: no change to
`src/charter/activation/_drg_helpers.py`, `load_graph_or_dir`, or `load_validated_graph` — that surface
belongs to sibling mission `org-pack-drg-root-graph-guard-01KZY0QT` (#3384), in spec phase
concurrently. This WP's entire fix lives in `pack_validator.py` and two call-site edits.

**The two carve-outs — read `reviews/plan.ruling.md` (operator ruling #2) before touching
either call site.** `validate_pack()` has two other callers besides the CLI's `pack_validate`
command. **They are reasoned about separately, for different reasons — they do not stand or
fall together:**

1. **`pack_assembler.py:assemble_pack()`**'s internal call
   (`src/specify_cli/doctrine/pack_assembler.py:335`, currently `validate_pack(output_dir)`)
   becomes `validate_pack(output_dir, check_drg_root=False)`. This carve-out is
   **unconditional and stays** — its justification is structural, not an assumption about any
   caller: `_copy_drg_fragments` (`pack_assembler.py:475-539`) writes DRG content **only** to
   `output_dir/drg/*.graph.yaml`; no assembler write path can ever produce a pack-root
   `*.graph.yaml`. It is load-bearing:
   `tests/specify_cli/doctrine/test_pack_assembler.py:184-188`'s fragment names match
   `*.graph.yaml`, so without this carve-out,
   `test_force_dedup_prunes_duplicate_edges_via_canonical_serializer` (`:169`) — which asserts
   `result.ok is True` against exactly this drg/-fragments-only, no-pack-root-graph shape —
   would newly fail.
2. **`doctrine.py:org_validate`**'s call (`src/specify_cli/cli/commands/doctrine.py:966`,
   currently `validate_pack(pack_path)`) becomes `validate_pack(pack_path,
   check_drg_root=True)`, **written explicitly**, with **no carve-out**. This inverts what an
   earlier draft of this mission's design did. Per operator ruling #2: the check is already
   content-conditional (it only fires when `drg/*.graph.yaml` fragments exist AND the pack
   root has none) and `org_init`'s scaffold (`:899-940`) writes `drg/fragment.yaml` — a
   filename that never matches the `*.graph.yaml` glob — so a carve-out here has never
   protected against anything for the shape its own justification cited. Worse, an
   unconditional carve-out would suppress the diagnostic precisely when a pack that started as
   an `org init` stub later accumulates real `drg/*.graph.yaml` content with no pack-root
   graph — the exact destructive shape this check exists to catch. **The call site passes
   `check_drg_root=True` explicitly** (not relying on `validate_pack`'s own default) so that a
   future refactor changing that default cannot silently change `org_validate`'s behaviour
   without a visible diff at this call site; add a short inline comment recording this
   rationale. `pack_validate`'s own call (`doctrine.py:370`) is **not edited** — it already
   gets the implicit default `True`.

**The "merge-order constraint" some earlier planning material discusses is DISSOLVED** —
per operator ruling #2, do not implement any conditional/premise-dependent version of the
`org_validate` carve-out, and do not treat PR #2719 (see Risks below) as a blocker. There is
no operator decision pending on this WP's design; the design above is final.

**Chokepoint note for reviewers**: this WP is Lane B's third and final WP, landing after WP02
and WP03 in `pack_validator.py` (and, for WP03, `test_pack_validator.py`) — intentional
same-file/same-lane sequencing per `plan.md`'s "Chokepoint" section, not an ownership-map
violation.

### Subtask T014: ATDD red-first — AC-1's DRG-root-graph-missing regression test

**Purpose**: Commit the failing-first test proving `pack validate` today has no signal for the
drg/-only, no-pack-root-graph shape.

**Steps**:
1. In `tests/specify_cli/doctrine/test_pack_validator.py`, add a new test (a new class, e.g.
   `TestDrgRootGraphMissing`, matching the file's existing per-concern class organization)
   that:
   - Writes `drg/010-security.graph.yaml` under `tmp_path` with a minimal, schema-valid DRG
     fragment (mirror the existing `_validate_drg`-exercising fixtures elsewhere in this file
     for the YAML shape — `nodes: []` / `edges: []` is sufficient if no edge-resolution is
     needed for this specific test; keep the fragment minimal since this test is about the
     root-vs-fragment mismatch, not fragment content correctness).
   - Writes **no** `*.graph.yaml` file at the pack root (`tmp_path` itself).
   - Calls `validate_pack(tmp_path)` (the default `check_drg_root=True` — this test does not
     need to pass the keyword explicitly, since the CLI-facing default is what AC-1 targets).
   - Asserts `result.ok is False`, and that `result.errors` contains a `ValidationIssue` with
     `category == "drg_root_graph_missing"` naming the runtime carrier the check is about
     (a message referencing `src/charter/activation/_drg_helpers.py` / `load_validated_graph` / the
     pack-root `*.graph.yaml` requirement — the exact wording is your call, but the message
     must be actionable, not just a bare category name).
   - **Also exercises the CLI for AC-4's exit-code-1 half** (a direct `validate_pack()` call
     alone only proves `result.ok is False`, not that `pack_validate` maps that to exit code
     `1`): using `typer.testing.CliRunner` against the same fixture pack this test already
     built, `runner.invoke(app, ["pack", "validate", str(tmp_path)])` (mirror
     `tests/specify_cli/doctrine/test_config.py`'s `TestDoctrinePackCommands` invocation
     pattern, or `tests/cli/test_doctrine_org_commands.py`'s `runner.invoke(app, [...])`
     pattern for the app/fixture wiring already used in this repo) and assert
     `result.exit_code == 1`. This can be the same test function as the direct-call assertion
     above, or a small sibling test in the same class — either is fine as long as both the
     `ok is False` half and the CLI `exit_code == 1` half are actually exercised against AC-1's
     fixture pack, not just one of the two.
2. **Primary RED check (C-011)**: run this new test id in isolation against
   `planning_base_branch` (`main`, per `meta.json`'s `target_branch`), as a **separate
   ref/worktree checkout** — see this WP's Reviewer Guidance for the exact procedure (WP04 is
   Lane B's third WP, same non-first-WP situation WP03 was in). Confirm RED:
   `validate_pack()` at `planning_base_branch` has no `check_drg_root` parameter and no
   DRG-root-graph check exists yet, so the assertion fails.
3. Do not implement yet — commit this test addition as its own commit.

**Files**: `tests/specify_cli/doctrine/test_pack_validator.py` (new test class, ~20-30 lines
including the CliRunner exit-code assertion).

**Validation**: the new test id(s) fail against `planning_base_branch`, confirmed via the
separate-ref procedure — both the `result.ok is False` assertion and the CLI
`result.exit_code == 1` assertion fail (the category doesn't exist yet, and `pack_validate`
therefore has nothing to map to a non-zero exit).

### Subtask T015: ATDD red-first — AC-2, AC-3, AC-5 (no-diagnostic and near-miss cases)

**Purpose**: Commit the remaining negative-case tests for this check, red-first alongside
T014, covering the "when NOT to fire" half of the acceptance criteria.

**Steps**:
1. **AC-2**: add a test with a pack-root `*.graph.yaml` present (with or without `drg/`
   fragments) and assert no `drg_root_graph_missing` diagnostic appears.
2. **AC-3**: add a test with **neither** a pack-root graph **nor** a `drg/` directory at all,
   and assert no `drg_root_graph_missing` diagnostic appears — this check is about a
   *mismatch*, not about requiring DRG content to exist.
3. **AC-5**: add a test with a pack-root file named e.g. `notes.graph.yaml.bak` (a near-miss
   that does not match `*.graph.yaml`) plus `drg/` fragments present, and assert the AC-1
   diagnostic **still fires** — the near-miss file must not be mistaken for a satisfying
   pack-root graph. This is correct by construction (`Path.glob("*.graph.yaml")` does not
   match a `.bak`-suffixed name), so this test is a regression guard against a future,
   accidental widening of the glob, not a case expected to require special-case code.
4. Run all three (plus T014's) in isolation against `planning_base_branch` via the same
   separate-ref procedure — AC-2 and AC-3 should already pass trivially against
   `planning_base_branch` (no diagnostic exists at all today, so "no diagnostic fires" is
   vacuously true pre-implementation) — that is expected and fine; T014's and AC-5's positive
   cases are the ones that must show RED.

**Files**: `tests/specify_cli/doctrine/test_pack_validator.py` (three new tests, ~15-20 lines
each).

**Validation**: AC-1 (T014) and AC-5 fail against `planning_base_branch`; AC-2 and AC-3 pass
trivially both before and after (they assert absence of a diagnostic that doesn't exist yet
either way) — this is not a contradiction of C-011, since C-011 requires *a* failing-first
test pinning the WP's behaviour, which T014 already provides; AC-2/AC-3 are regression guards
alongside it.

### Subtask T016: ATDD red-first — AC-6's assembler parameter-value assertion

**Purpose**: Prove `assemble_pack()`'s internal call actually passes `check_drg_root=False` —
not merely that the existing test still happens to pass.

**Steps**:
1. In `tests/specify_cli/doctrine/test_pack_assembler.py`, add a new test that asserts
   `check_drg_root=False` is the literal parameter value used at `assemble_pack()`'s internal
   `validate_pack(...)` call. The most direct approach: patch
   `"specify_cli.doctrine.pack_assembler.validate_pack"` (verify this is the correct import
   binding location in `pack_assembler.py` — check whether `validate_pack` is imported at
   module scope there, per `scripts/check_patch_targets.py`'s static-analysis requirement that
   patch targets must resolve) with a `MagicMock` wrapping the real function (or simply
   inspecting the call args via `unittest.mock.patch` + `assert_called_with(...,
   check_drg_root=False)`), then run `assemble_pack(...)` with a minimal input pack and assert
   the mock was called with `check_drg_root=False`.
2. Also confirm the existing `test_force_dedup_prunes_duplicate_edges_via_canonical_serializer`
   (`:169`) — the only currently-passing test that actually exercises `validate_pack` on the
   drg/-fragments-only shape (`test_drg_conflict` at `:151` returns via an earlier
   conflict-detection guard and never reaches `validate_pack` — do not cite it as evidence
   either way) — is **not modified**, only re-run to confirm it still passes once T018's
   implementation lands.
3. Run the new parameter-value assertion test against `planning_base_branch` (separate-ref
   checkout) and confirm RED: `check_drg_root` does not exist as a keyword argument at
   `planning_base_branch`'s `validate_pack()` signature, so a call asserting it was passed
   fails (either the mock's `assert_called_with` fails, or — if you inspect the *real*
   function's signature — a `TypeError` on the nonexistent keyword makes the setup itself
   fail, which also counts as RED for this purpose: the assertion this test needs to make is
   simply not satisfiable pre-implementation).

**Files**: `tests/specify_cli/doctrine/test_pack_assembler.py` (one new test, ~20-25 lines).

**Validation**: the new test fails against `planning_base_branch`; `test_force_dedup_...`
(`:169`) is untouched in the diff.

### Subtask T017: ATDD red-first — AC-7(a) and AC-7(b)

**Purpose**: Commit both halves of AC-7: (a) a parameter-value assertion that `org_validate`'s
call passes `check_drg_root=True` explicitly (mirroring T016's assembler assertion, opposite
value), and (b) a brand-new positive-fire fixture proving `doctrine org validate` now catches
the destructive shape the dropped carve-out used to suppress.

**Steps**:
1. **AC-7(a)** — in `tests/cli/test_doctrine_org_commands.py`, add a test asserting
   `check_drg_root=True` is the literal parameter value at `org_validate`'s internal
   `validate_pack(...)` call — same *assertion shape* as T016 (patch + `assert_called_with(...,
   check_drg_root=True)`), but **not** the same patch target: `validate_pack` is **not** bound
   at module scope in `doctrine.py`. `org_validate`'s body does a lazy, function-local import
   (`from specify_cli.doctrine.pack_validator import (render_validation_result, validate_pack)`
   inside the command function, at `src/specify_cli/cli/commands/doctrine.py:961-964` (the call
   site itself is separately at `:966`), re-run on every invocation) — the same lazy-import
   shape WP03's T010 step 3 calls out for
   `AgentProfileRepository` in `pack_validator.py`, not the module-scope import
   `pack_assembler.py` has at line 37 (which is what makes T016's
   `"specify_cli.doctrine.pack_assembler.validate_pack"` patch target work there). Per
   `scripts/check_patch_targets.py`'s constraint that a patch target's module portion must
   actually expose the attribute being patched, the correct target here is the **source
   location**, `"specify_cli.doctrine.pack_validator.validate_pack"` — doctrine.py's lazy import
   picks up the patched function on each call. Do not patch a
   `specify_cli.cli.commands.doctrine.validate_pack` alias; it does not exist and `mock.patch`
   will reject it with an `AttributeError`.
2. Confirm the existing `test_doctrine_org_validate_accepts_valid_pack`
   (`tests/cli/test_doctrine_org_commands.py:108-119`) is **not modified** — per AC-7(a)'s own
   text, it "continues to exit `0` unmodified, because `drg/fragment.yaml` never matches the
   `*.graph.yaml` glob this check keys off, not because of any carve-out." Do not touch this
   test's body; only confirm (by running it) that it still passes once T018 lands.
3. **AC-7(b)** — add a **new** test fixture (there is no precedent for this shape in the suite
   today — build it from scratch): scaffold a pack via the CLI's `org init` command (mirror
   `test_doctrine_org_validate_accepts_valid_pack`'s own pattern:
   `runner.invoke(app, ["org", "init", str(pack_dir)])`), then **add a real
   `drg/*.graph.yaml` fragment** to that scaffolded pack — either replacing or supplementing
   the scaffold's own `drg/fragment.yaml` (which never matches the glob) with a file actually
   named e.g. `drg/010-security.graph.yaml` containing a minimal valid fragment (mirror T014's
   fragment shape) — with **no** pack-root `*.graph.yaml` added. Then invoke `doctrine org
   validate` against that pack (`runner.invoke(app, ["org", "validate", str(pack_dir)])`) and
   assert:
   - The output/JSON reports the `drg_root_graph_missing` diagnostic (match on category if the
     CLI's rendered output includes it, or invoke `validate_pack` directly if this test is
     easier to write at that layer — but the acceptance criterion is specifically about
     `doctrine org validate`'s CLI behaviour, so prefer exercising the CLI command via
     `runner.invoke` to keep the test's assertion at the right layer).
   - `result.exit_code != 0` (non-zero — `org_validate`'s existing pattern maps a non-`ok`
     `ValidationResult` to a non-zero exit; verify the exact exit-code convention against
     `org_validate`'s current implementation before asserting a specific value).
4. Run T017(a) and T017(b) against `planning_base_branch` (separate-ref checkout) and confirm
   RED for both: (a) fails because `check_drg_root` does not exist as a parameter to assert
   against; (b) fails because no `drg_root_graph_missing` diagnostic exists yet, so `doctrine
   org validate` exits `0` for this fixture at `planning_base_branch` — this is the load-bearing
   proof that the *shape* AC-7(b) exercises was genuinely unguarded before this WP, not merely
   an assertion added defensively.

**Files**: `tests/cli/test_doctrine_org_commands.py` (two new tests: one parameter-value
assertion ~15-20 lines, one full positive-fire fixture test ~25-35 lines).

**Validation**: both new tests fail against `planning_base_branch`; the existing
`test_doctrine_org_validate_accepts_valid_pack` is untouched and still passes both before and
after T018.

### Subtask T018: Implementation — the helper, the signature change, and both call sites

**Purpose**: Turn T014-T017's red tests green with the design already fixed by `plan.md` IC-04
and operator ruling #2.

**Steps**:
1. In `src/specify_cli/doctrine/pack_validator.py`, add a new helper (near `_validate_drg`,
   following the file's existing extract-a-helper discipline):
   ```python
   def _check_drg_root_graph_missing(
       pack_dir: Path,
       drg_dir: Path,
   ) -> list[ValidationIssue]:
       """Warn when DRG content lives only under drg/ with no pack-root graph.

       The runtime (src/charter/activation/_drg_helpers.py:load_validated_graph) reads a
       pack-root *.graph.yaml, never drg/ fragments — see spec.md
       Clarification 3 / sibling mission #3384. Fires only when drg/ contains
       at least one *.graph.yaml fragment AND the pack root has none; a pack
       with neither, or with a pack-root graph present, produces no issue.
       """
       if not drg_dir.is_dir():
           return []
       if not sorted(drg_dir.glob("*.graph.yaml")):
           return []
       if sorted(pack_dir.glob("*.graph.yaml")):
           return []
       return [
           ValidationIssue(
               severity="error",
               artifact_type="drg",
               artifact_id=None,
               file=str(pack_dir),
               message=(
                   "DRG content exists only under drg/*.graph.yaml with no "
                   "pack-root *.graph.yaml. The runtime "
                   "(src/charter/activation/_drg_helpers.py:load_validated_graph) reads "
                   "the pack root directly, not drg/ fragments — this pack's "
                   "DRG content will not be read as authored."
               ),
               category="drg_root_graph_missing",
           )
       ]
   ```
   (Verify the exact glob/guard logic against `_validate_drg`'s own `drg_dir.glob("*.graph.yaml")`
   call at `:506` — reuse the identical glob string, per AC-5's requirement that this check
   use "the same exact glob the runtime and the existing `_validate_drg` fragment scan already
   use.")
2. Change `validate_pack()`'s signature (`:340`) to add a keyword-only parameter:
   ```python
   def validate_pack(pack_dir: Path, *, check_drg_root: bool = True) -> ValidationResult:
   ```
3. Call the new helper conditionally, immediately after the existing `_validate_drg` call —
   locate it structurally (the `if drg_dir.is_dir(): drg_errors, drg_advisories =
   _validate_drg(...)` block), not by absolute line number: this block sits at `:387-392` on
   `main`'s tip as of this WP file's writing, but that citation is a `main`-tip reference taken
   before WP02's and WP03's own call-site additions land earlier in `validate_pack()`'s body —
   by the time WP04 implements, the block will have shifted down and the absolute line numbers
   above will be stale:
   ```python
   if check_drg_root:
       errors.extend(_check_drg_root_graph_missing(pack_dir, drg_dir))
   ```
4. In `src/specify_cli/doctrine/pack_assembler.py`, at `:335`, change:
   ```python
   validation = validate_pack(output_dir)
   ```
   to:
   ```python
   # The assembler never writes a pack-root *.graph.yaml (_copy_drg_fragments
   # only writes output_dir/drg/*.graph.yaml) — this carve-out is structural,
   # unconditional, and does not depend on any caller's output shape.
   validation = validate_pack(output_dir, check_drg_root=False)
   ```
5. In `src/specify_cli/cli/commands/doctrine.py`, at `:966`, change:
   ```python
   result = validate_pack(pack_path)
   ```
   to:
   ```python
   # Written explicitly (not relying on validate_pack's own default) so a
   # future default change cannot silently alter org_validate's behaviour
   # without a visible diff here. No carve-out: org_init's scaffold never
   # produces the drg-root-graph-missing shape, so this call was never
   # protected by a carve-out in the first place (operator ruling #2,
   # reviews/plan.ruling.md).
   result = validate_pack(pack_path, check_drg_root=True)
   ```
   Do **not** edit `pack_validate`'s call (`doctrine.py:370`) — it already gets the implicit
   default `True`.
6. Re-run T014-T017's test ids — all should now pass (GREEN).
7. Update `ValidationIssue`'s class docstring (`src/specify_cli/doctrine/pack_validator.py:95-114`,
   the "Valid values" bullet list) to add a `` * ``drg_root_graph_missing`` — ...`` bullet
   documenting the new category, matching the existing bullets' format (backtick-quoted category
   name, em dash, one-line description) — e.g. placed alongside the other DRG-related categories
   such as `drg_dangling_edge`. This docstring is the authoritative enumeration of valid
   `category` values; leaving it unupdated would make it silently disagree with the helper added
   in step 1.
8. **Re-measure `validate_pack()`'s complexity now that both new helper calls (FR-002's
   `_check_profile_skipped_diagnostics` from WP03 and this WP's own
   `_check_drg_root_graph_missing`) are wired in**, per `plan.md`'s "Complexity Tracking"
   section. `ruff check --select C901 --statistics` only ever reports a number when a function
   *violates* the configured ceiling (`pyproject.toml`'s `max-complexity = 15`) — for a
   compliant function it produces no output at all (verified: `ruff check
   src/specify_cli/doctrine/pack_validator.py --select C901 --statistics` against
   `validate_pack()`'s pre-mission complexity of 9 emits nothing), so it cannot supply a number
   "regardless of outcome." To get the actual number unconditionally, override the ceiling on
   the command line only — do **not** edit `pyproject.toml` — so ruff's per-violation message,
   which embeds the real complexity, always fires:
   ```bash
   ruff check src/specify_cli/doctrine/pack_validator.py --select C901 \
       --config "lint.mccabe.max-complexity=1"
   ```
   Read `validate_pack()`'s actual complexity `N` from its message, e.g. "`validate_pack` is too
   complex (N > 1)" — the `> 1` is this command's temporary override, not the project's real
   ceiling (still 15, unchanged in `pyproject.toml`). Record `N` in your implementation notes
   regardless of outcome — not just a comfortable/uncomfortable label — so a reviewer can
   independently check the same number without re-deriving judgment. Use a concrete numeric
   trigger for whether `plan.md` also needs an edit: if `N` is **>= 12** (80% of the
   complexity-15 ceiling), also record it in `plan.md`'s "Complexity Tracking" section as an
   early-warning note that the function is approaching the ceiling (a mechanical numeric
   trigger, additional to — not a substitute for — that section's own stated commitment to
   record a *design trade-off* only when one is genuinely non-mechanical); if `N` is **< 12**,
   the implementation-notes entry alone is sufficient and no `plan.md` edit is needed.
9. Commit as its own commit, separate from the T014-T017 test commits.

**Files**: `src/specify_cli/doctrine/pack_validator.py` (~25-line new helper, ~4-line signature
+ call-site change, and the `ValidationIssue` docstring's "Valid values" list updated with
`drg_root_graph_missing`), `src/specify_cli/doctrine/pack_assembler.py` (1-line call change +
3-line comment), `src/specify_cli/cli/commands/doctrine.py` (1-line call change + 4-line
comment); `plan.md`'s "Complexity Tracking" section only if step 8's re-measurement reads >= 12
(80% of the complexity-15 ceiling).

**Validation**: all of T014-T017's test ids pass. `test_force_dedup_prunes_duplicate_edges_via_canonical_serializer`
and `test_doctrine_org_validate_accepts_valid_pack` both still pass, unmodified. Step 8's
complexity re-measurement was performed and its actual numeric reading is noted in the
implementation notes either way, plus a `plan.md` "Complexity Tracking" entry if that reading
is >= 12 (80% of the ceiling).

### Subtask T019: CHANGELOG entry

**Purpose**: Document the breaking-change consequence of FR-002/003/004 together, per the
spec's Reflexivity-section obligation and the charter's binding "Breaking changes documented
in CHANGELOG.md" checklist item.

**Steps**:
1. Open `docs/changelog/CHANGELOG.md` — the **canonical file**. Do **not** edit the root
   `CHANGELOG.md` symlink; the docs-freshness `sync_changelog.py --check` gate fails only if
   the root file stops being a symlink to this canonical path, which happens if an
   implementer accidentally replaces it via a write-then-rename pattern instead of editing
   this file directly.
2. Under the current `## [Unreleased] - 3.2.6rc2` section, which today has only `### ✨ Added`
   and `### 🐛 Fixed` subsections, **create a new** `### 💥 Breaking Changes` heading (this
   exact heading text recurs elsewhere in the file at, e.g., lines `1761`, `2145`, `2206`,
   `2450` — match that established taxonomy, do not invent new heading text).
3. Add an entry documenting that `pack validate` (and `doctrine org validate`) now fails (exit
   code `1`) for three previously-passing pack shapes:
   - A merge-time-skipped agent profile (FR-002) — a profile that individually passes schema
     validation but fails to field-merge onto a same-ID built-in profile now surfaces as a
     `profile_skipped` error.
   - A nested `assets/<pack>/x.asset.yaml` manifest with a schema violation (FR-003) — nested
     asset manifests are now scanned recursively, matching what `AssetRepository` loads at
     runtime.
   - DRG content living only under `drg/*.graph.yaml` with no pack-root `*.graph.yaml`
     (FR-004) — the runtime reads only the pack root; this shape now produces a
     `drg_root_graph_missing` error.
   Follow the existing entries' style in this changelog section (mission name + issue number
   citation, a short "before/now" framing) — match the tone and format of the `### ✨ Added`
   entries already present in this same `## [Unreleased]` section rather than inventing new
   formatting conventions.
4. Confirm the frontmatter's `updated:` and `doc_status:` fields already satisfy the
   Structural docs lint gate (verified in `plan.md`'s "The Gate Set": this file already carries
   `doc_status: active` and an `updated:` field) — no frontmatter change is required here,
   only the CHANGELOG sync check, which passes as long as the root symlink is untouched.

**Files**: `docs/changelog/CHANGELOG.md` (new `### 💥 Breaking Changes` heading + one entry
under `## [Unreleased] - 3.2.6rc2`, ~10-20 lines).

**Validation**: `docs/changelog/CHANGELOG.md`'s root symlink (`CHANGELOG.md` at repo root) is
untouched — confirm with `git status` that only the canonical path shows as modified, and
`readlink CHANGELOG.md` still resolves to `docs/changelog/CHANGELOG.md`.

## Definition of Done

- [ ] T014-T017's red tests committed first (as one or more test commits, each preceding
      T018), each verified RED against `planning_base_branch` via the separate-ref procedure.
- [ ] T018's implementation committed after all red tests, turning them GREEN: the new
      `_check_drg_root_graph_missing` helper, `validate_pack()`'s `check_drg_root: bool = True`
      keyword-only parameter, the assembler's unconditional `check_drg_root=False`, and
      `org_validate`'s explicit `check_drg_root=True` (no carve-out).
- [ ] `ValidationIssue`'s class docstring "Valid values" list (`pack_validator.py:95-114`) has a
      new `drg_root_graph_missing` bullet, added by T018 step 7, matching the existing bullets'
      format.
- [ ] AC-1 through AC-7 all covered: AC-1 (fires), AC-2 (pack-root graph present → no fire),
      AC-3 (neither graph nor drg/ → no fire), AC-4 (error severity **and** exit code 1, both
      independently falsifiable via T014's test — `result.ok is False` via the direct
      `validate_pack()` call, and `result.exit_code == 1` via T014's added CliRunner assertion
      against `pack_validate`, not merely inferred from the unchanged ok→exit-code mapping),
      AC-5 (near-miss `.bak` file doesn't satisfy the check), AC-6
      (assembler's `check_drg_root=False` proven by parameter-value assertion, not just a
      passing pre-existing test), AC-7(a) (org_validate's explicit `True`, proven the same way)
      and AC-7(b) (the new positive-fire fixture, built from scratch, actually exercising
      `doctrine org validate`'s CLI path).
- [ ] `test_force_dedup_prunes_duplicate_edges_via_canonical_serializer` and
      `test_doctrine_org_validate_accepts_valid_pack` are both present in the diff **only** as
      confirmed-still-passing, never modified in body.
- [ ] `docs/changelog/CHANGELOG.md` (canonical path) carries the new `### 💥 Breaking Changes`
      entry; the root symlink is untouched.
- [ ] `uv run pytest tests/specify_cli/doctrine/test_pack_validator.py tests/specify_cli/doctrine/test_pack_assembler.py tests/cli/test_doctrine_org_commands.py -q`
      is fully green.
- [ ] No file outside `owned_files` is touched; `src/charter/activation/_drg_helpers.py` is not touched
      anywhere in this WP's diff (C-002).
- [ ] `ruff check src/specify_cli/doctrine/pack_validator.py src/specify_cli/doctrine/pack_assembler.py src/specify_cli/cli/commands/doctrine.py`
      and `mypy --strict` on the same three files (or the project's standard invocation) pass
      with zero new suppressions.
- [ ] T018 step 8's `validate_pack()` complexity re-measurement was performed, with the actual
      numeric ruff-reported complexity reading (via the forced-ceiling-override invocation, not
      plain `--statistics`) recorded in implementation notes, and additionally in `plan.md`'s
      "Complexity Tracking" section if that reading is >= 12 (80% of the ceiling).

## Risks

- **Regression on the assembler's known call site** (per `plan.md` IC-04 Risks): without the
  carve-out, `assemble_pack()`'s round-trip check would newly fail
  `test_force_dedup_prunes_duplicate_edges_via_canonical_serializer` — pre-identified in the
  spec's Reflexivity finding. T016/T018 must actually re-run this specific test, not assume
  the carve-out fixes it by construction.
- **New positive-fire fixture required (AC-7b)**: this fixture has no precedent in the suite
  today. Build it carefully — verify `doctrine org validate`'s actual exit-code convention for
  a failing `ValidationResult` before asserting a specific non-zero value (do not assume `1`
  without checking `org_validate`'s implementation).
- **Open-PR collision — `doctrine.py`** (per `plan.md`'s "Chokepoint" section, "Open-PR
  write-scope check": first verification (2026-08-14) found 18 open PRs, a later same-day
  re-check during a prior fix round found 19 — the extra PR, #3395, confirmed to touch no file
  this mission owns. A third live re-check performed for this fix round (`gh pr list --state
  open --json number`, 2026-08-14) again returned 19, so the count has not drifted further since
  the second check. PR counts drift continuously; the enumerated overlaps below, not the raw
  count, are the load-bearing claims, per plan.md's own framing): two currently-open PRs touch
  `doctrine.py`:
  - **PR #3166** ("feat(doctrine): ETag skip + Artifactory version for HTTPS fetch") edits
    `fetch()` (a different function, roughly `doctrine.py:94-160`). This WP's only edit to
    `doctrine.py` is `org_validate`'s call site (`:966`) — no line-range overlap. Benign
    same-file co-edit; at worst a mechanical rebase.
  - **PR #2719** ("feat: doctrine org init from local/git template") touches `org_init`, and
    per the investigation behind operator ruling #2, **never calls
    `validate_pack`/`check_drg_root` anywhere in its diff**. This is no longer a premise risk
    at all: FR-004's `org_validate` call site no longer depends on `org_init`'s output shape
    (the carve-out that depended on that shape is dropped, not conditioned). #2719 landing
    before or after this mission's PR has no effect on this WP's correctness. There is no
    operator merge-order decision pending here — do not reintroduce one.
  **PR #2719 also touches a second WP04-owned file** —
  `tests/cli/test_doctrine_org_commands.py` (+206/-0, confirmed via `gh pr list --state open
  --json number,title,files`) — which is a *distinct* co-edit risk from the `doctrine.py`
  overlap above: T017 adds its own new test functions to this same file (AC-7(a)'s
  parameter-value assertion and AC-7(b)'s positive-fire fixture). Landing order with #2719 may
  require a rebase inside `test_doctrine_org_commands.py` itself, not just `doctrine.py` — check
  for this specifically when this WP's branch is rebased, since a test-file conflict is more
  likely to need manual resolution than a same-function-absent `doctrine.py` co-edit.
  Separately, `docs/changelog/CHANGELOG.md` (also WP04-owned, per T019) is concurrently touched
  by eight other currently-open PRs — #3383, #3379, #3378, #3332, #3293, #2890, #2492, #2239 —
  all purely additive (0 deletions each), so low conflict risk, but previously undisclosed here.
  The core claim still holds under this re-check: **no open PR touches `pack_validator.py` or
  `pack_assembler.py`** — the chokepoint file itself has zero open-PR overlap.
  No other WP's `owned_files` in this mission overlaps any currently-open PR beyond what's
  enumerated above (verified fact from `plan.md`'s Chokepoint section — cited here, not
  re-derived; the raw open-PR count is not the load-bearing claim, per the framing note above).

## Reviewer Guidance

- **This WP is Lane B's third WP** (after WP02, WP03). Per `plan.md`'s "Per-FR ATDD
  Sequencing" section, verifying T014-T017's tests RED against `planning_base_branch` requires
  the same **separate ref/worktree checkout** procedure WP03 used: check out
  `planning_base_branch` (`main`) as a distinct ref, apply **only this WP's new test id(s)**
  on top of it (not the whole targeted test files — by now they carry WP02's and WP03's own
  new test functions too, which would independently show red against `planning_base_branch`
  and muddy the signal), and run each new test id there. The intra-lane "immediately before
  this WP's implementation commit" check is a secondary, attribution-only aid, never a
  substitute for the `planning_base_branch` check — apply this to **all** of AC-1's, AC-6's,
  and AC-7(a)/(b)'s new test ids, across all three targeted test files this WP touches.
- **Concrete mechanics for the separate ref/worktree check** — since this WP touches three
  different test files (each carrying its own new test id(s)), repeat the same procedure per
  file/test-id pair:
  ```bash
  # Idempotent cleanup first: this procedure repeats once per test id (T014/T015's several
  # ids, T016's id, T017(a)/(b)'s ids) in the same review session, so a prior iteration whose
  # `git apply` or `pytest` step failed before reaching the closing `git worktree remove`
  # below would otherwise leave the worktree registered and make the next `git worktree add`
  # fail outright ("already exists"). Clear it unconditionally before (re-)adding, every time:
  git worktree remove --force /tmp/pbb-check 2>/dev/null || true
  git worktree add /tmp/pbb-check main   # planning_base_branch is "main" per meta.json
  # For each target file (test_pack_validator.py, test_pack_assembler.py,
  # test_doctrine_org_commands.py), isolate only THIS WP's new test function(s) — not the
  # whole file, which by now also carries WP02's/WP03's own new tests:
  git show <this-WP's-test-commit-sha> -- <test file> | git -C /tmp/pbb-check apply
  # If the hunk doesn't apply cleanly, manually copy just the new test function's body into
  # /tmp/pbb-check's copy of the file instead.
  cd /tmp/pbb-check && uv run pytest <test file> -k <new_test_id> -q   # confirm RED
  cd - && git worktree remove /tmp/pbb-check
  ```
  Repeat for each of T014/T015's ids in `test_pack_validator.py`, T016's id in
  `test_pack_assembler.py`, and T017(a)/(b)'s ids in `test_doctrine_org_commands.py` — run
  the cleanup-then-add sequence at the top of each repetition, not just the first.
- Confirm the two carve-outs are treated **separately**, each for its own stated reason — a
  diff that treats them as one shared "assembler and org_validate both get carved out"
  guarantee is wrong per operator ruling #2, and is itself a finding.
- Confirm `org_validate`'s call passes `check_drg_root=True` **explicitly** (not relying on
  the function's own default) and carries the inline comment explaining why.
- Confirm AC-6 and AC-7(a) are proven by an actual parameter-value assertion (mock/patch-based
  or equivalent), not merely by an existing test continuing to pass — "the existing test still
  passes" is necessary but insufficient evidence for either AC.
- Confirm AC-7(b)'s fixture is genuinely new (check `git diff` shows a new test function in
  `tests/cli/test_doctrine_org_commands.py`, not a repurposed existing one) and that it
  exercises `doctrine org validate` end-to-end (via `runner.invoke`), not just `validate_pack`
  directly, since AC-7(b) is specifically about the CLI command's behaviour.
- Confirm `src/charter/activation/_drg_helpers.py` does not appear anywhere in this WP's diff (C-002).
- Confirm the CHANGELOG edit lands on `docs/changelog/CHANGELOG.md` (canonical path) and that
  `git status`/`readlink` show the root symlink untouched.
- Run only the three targeted test files named in this WP's `owned_files` for this WP's own
  gate (C-004) — never the full suite.

---

`spec-kitty agent action implement WP04 --agent <name>`
