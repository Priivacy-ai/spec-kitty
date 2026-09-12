# Mission Specification: Accept Path-Convention Honesty & Deduplication

**Mission Branch**: `fix/accept-path-remediation-honesty-3730`
**Created**: 2026-08-24
**Status**: Draft
**Input**: GitHub issues #3730 ("accept: path-convention failure prescribes a fake-green
mkdir and hides the real --lenient escape hatch") and #3085 ("accept: contracts/
reported simultaneously as optional (Warnings) and required (blocking
path_violations), with wrong path in remediation")

## Summary

`spec-kitty accept`'s path-convention check — `validate_mission_paths`
(`src/specify_cli/validators/paths.py`) and its two callers, `evaluate_path_conventions`
(`src/specify_cli/acceptance/summary_core.py`) and `_missing_artifacts` /
`collect_feature_summary` (`src/specify_cli/acceptance/__init__.py`) — has three
defects, all in its **operator-facing output**, not in what it enforces:

1. **Wrong path reported.** The check resolves and tests the correct directory
   (`feature_dir/contracts/` for a mission-artifact-tagged path) but then reports and
   builds its `mkdir -p` remedy from the bare declared token (`contracts/`), which
   names a different, untested location (repo root).
2. **The same fact reported twice, contradictorily.** `contracts/` is declared both an
   optional artifact and a required path convention in `software-dev/mission.yaml`, so
   its absence is simultaneously a non-blocking warning ("Optional artifacts missing")
   and a blocking `path_violations` entry — in the same `accept` run. A separate,
   purely cosmetic duplicate print then repeats the "Optional artifacts missing" line
   a second time.
3. **The remediation text is fake-green.** The strict-mode failure message asserts the
   missing directories "are required by the active mission" and offers `mkdir -p` as
   essentially the only remedy — even though `accept --lenient` demonstrably accepts
   the mission without creating them. The message never mentions `--lenient`, and
   `--lenient --help` text never mentions path conventions, so an operator with a
   legitimately different repo layout has no discoverable path off the failure short
   of reading source.

Both issues land on the same seam and share root-cause code, so this mission fixes
all three together: resolved-path correctness is the substrate the dedup and honesty
fixes both depend on.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator gets an accurate, actionable path violation (Priority: P1)

An operator runs `spec-kitty accept --mission <slug>` on a mission whose
`kitty-specs/<slug>/contracts/` directory does not exist. `accept` reports that
directory as missing and suggests a remedy. The reported path and the suggested
`mkdir -p` command must name the exact directory the check actually tested
(`kitty-specs/<slug>/contracts/`), not a different, untested location.

**Why this priority**: This is the foundation defect (#3085a). A remediation
suggestion that names the wrong directory cannot be trusted, and the dedup and
honesty fixes (Stories 2 and 3) both need the resolved path already available where
they emit their own messages — fixing this first avoids two more agents editing the
same lines with stale context.

**Independent Test**: Create a `software-dev` mission with no `contracts/` directory
under its mission directory. Run `spec-kitty accept --mission <slug>` (or invoke
`validate_mission_paths` directly in a unit test) and assert the reported missing
path and the suggested `mkdir -p` target both equal the resolved
`kitty-specs/<slug>/contracts/`, not the bare `contracts/` token.

**Acceptance Scenarios**:

1. **Given** a mission-artifact-tagged path convention (e.g. `contracts/`, declared in
   `mission.config.artifacts`) whose resolved location is
   `kitty-specs/<slug>/contracts/` and which does not exist, **When**
   `validate_mission_paths` evaluates it, **Then** the reported missing-path string and
   the `mkdir -p` suggestion both reference `kitty-specs/<slug>/contracts/`, not the
   bare declared token `contracts/`.
2. **Given** a build/repo-root path convention (e.g. `src/`, not artifact-tagged) whose
   resolved location is `project_root/src/` and which does not exist, **When**
   `validate_mission_paths` evaluates it, **Then** the reported missing-path string and
   `mkdir -p` suggestion reference `project_root/src/` (repo-root-relative reporting for
   non-artifact paths is unchanged — this story only fixes the artifact-tagged
   resolution mismatch).

---

### User Story 2 - Operator sees each missing fact reported once, consistently (Priority: P1)

An operator runs `spec-kitty accept --mission <slug>` on a `software-dev` mission
missing `contracts/`. Today the same missing directory appears both as a non-blocking
"Optional artifacts missing" warning and as a blocking `path_violations` entry — one
fact, two contradictory severities, in the same run. After this fix, that fact is
reported exactly once, with one severity that determines whether `accept` blocks.

**Why this priority**: The contradiction actively misleads: an operator reading
"optional" has no reason to expect `accept` to then exit 1 for the identical thing.
This is #3085b, and it depends on Story 1's resolved-path substrate so the reconciled
message reports the correct location.

**Independent Test**: Run `spec-kitty accept --mission <slug>` on a `software-dev`
mission with no `kitty-specs/<slug>/contracts/` directory. Assert the console output
mentions `contracts` exactly once across the "Warnings" and "Outstanding items"
sections combined, and that the "Optional artifacts missing" line itself is printed
at most once (not once from `_print_acceptance_warnings` and again from
`_print_acceptance_summary`'s own reprint of `summary.optional_missing`).

**Acceptance Scenarios**:

1. **Given** a path token (e.g. `contracts/`) declared in BOTH
   `mission.config.artifacts.optional` and `mission.config.paths` for the same
   resolved location, **When** that location is missing and `accept` runs in default
   (strict) mode, **Then** the missing fact is surfaced through exactly one of
   `missing_optional` (non-blocking) or `path_violations` (blocking) — never both —
   resolved by keeping the more restrictive/blocking severity: `path_violations`
   wins and the corresponding `missing_optional` entry is dropped as the
   now-redundant one. `AcceptanceSummary.ok` and the printed severity agree with
   each other.
2. **Given** the same dual-declared-token case as Scenario 1 (`contracts/` missing
   on a `software-dev` mission, strict mode — the exact fixture used by this
   mission's own tests, see SC-005/FR-007), **When** `accept` runs, **Then**
   `AcceptanceSummary.ok` is `False`, exactly as on pre-fix code — the reconciliation
   direction in Scenario 1 must not flip `accept`'s pass/fail boundary for this
   fixture. This is the concrete, checkable form of C-001's "no change to the
   pass/fail boundary" and is neutral with respect to #3016 (resolving toward
   `missing_optional` instead would silently stop blocking `accept` on a missing
   `contracts/`, which this scenario forbids).
3. **Given** `summary.warnings` already includes an "Optional artifacts missing: ..."
   entry (because `missing_optional` is non-empty), **When** `_print_acceptance_summary`
   renders the console output, **Then** it does not print a second, separate "Optional
   artifacts missing: ..." line from `summary.optional_missing`.
4. **Given** the reconciliation in Scenario 1, **When** the same run is inspected with
   `--json`, **Then** `missing_optional` and `path_violations` in the JSON payload
   reflect the same single-severity resolution as the console output (no format-specific
   drift).

---

### User Story 3 - Operator is told the truth about "required" and finds `--lenient` (Priority: P1)

An operator on a repo with a legitimately different layout (e.g. no `contracts/`
directory by design) runs `spec-kitty accept --mission <slug>` and gets a strict-mode
failure. Today the failure text asserts the directories "are required by the active
mission... Create them before continuing" — an unconditional claim that
`accept --lenient` immediately disproves — and its only suggested remedy is
`mkdir -p`, which creates empty, permanently-unused directories whose sole effect is
to silence the check. `--lenient --help` gives no hint that the flag touches path
conventions. After this fix, the failure text is accurate about what "required" means
in this run's mode, and both the failure text and `--help` lead the operator to
`--lenient` as a legitimate alternative.

**Why this priority**: This is the mission's namesake defect (#3730) — the honesty
gap the charter's anti-fake-green language names directly. It depends on Stories 1
and 2 landing first so the wording it produces describes the post-dedup,
resolved-path world, not the pre-fix one.

**Independent Test**: Run `spec-kitty accept --mission <slug> --help` and assert the
`--lenient` help text mentions path conventions. Run `spec-kitty accept --mission
<slug>` in strict mode against a mission with a missing declared path and assert the
failure text does not present the requirement as unconditional and does reference
`--lenient` (or an equivalent operator-facing pointer) as an alternative remedy.

**Acceptance Scenarios**:

1. **Given** a mission with a missing declared path and default (strict) mode,
   **When** `accept` fails on the path-convention check, **Then** the printed failure
   text does not assert the paths are unconditionally "required" while `--lenient`
   would accept the mission without them — the wording is conditional on the mode
   actually in effect for this run.
2. **Given** the same failure, **When** the operator reads the failure text alone with
   no source reading, **Then** it names `--lenient` (or points at it unambiguously) as
   a way to resolve a legitimate layout mismatch, not only `mkdir -p`.
3. **Given** `spec-kitty accept --help`, **When** the operator reads the `--lenient`
   flag's help string, **Then** it indicates the flag affects path-convention
   enforcement (not only "strict metadata validation" in general).
4. **Given** the same failure, **When** the `mkdir -p` suggestion is still offered
   (permitted as a secondary remedy for operators who do want to adopt the
   convention), **Then** the `--lenient` pointer (Scenario 2) appears before the
   `mkdir -p` suggestion in the printed failure text, and the `mkdir -p` line is
   explicitly marked as a secondary/optional remedy (e.g. via wording such as "...
   or, if you want to adopt the convention: `mkdir -p ...`") — it is not presented as
   the only or primary path off the failure. This is checkable by plain
   string-order and string-content assertions on the printed text, with no external
   dependency on the tracer file.
5. **Given** the pinned tests listed in Success Criteria, **When** this story's
   change lands, **Then** all three continue to pass unmodified (verifies `--lenient`'s
   existing downgrade-to-warning behavior for missing paths is unchanged as a side
   effect of the wording fix).

---

### User Story 4 - A reviewer can prove both defects existed and are fixed (Priority: P2)

A reviewer of this mission's PR wants a single, runnable fixture that reproduces both
the wrong-path-reported defect (Story 1) and the double-reporting contradiction
(Story 2) against a real (or realistically faked) mission/repo layout — not only
inferred from unit-level assertions on internal functions.

**Why this priority**: Binding maintainer requirement from #3085's 2026-08-02 triage
comment ("add a focused repro/acceptance fixture ... before implementation"). Rated
P2 relative to Stories 1-3 only because it is a verification artifact riding on their
behavior, not a user-visible behavior change of its own — but it is not optional.

**Independent Test**: The fixture runs standalone (e.g.
`pytest tests/.../test_accept_contracts_path_repro.py` or equivalent), fails against
the pre-fix code (`git stash` / revert of Stories 1-2's changes reproduces both the
wrong path and the contradiction), and passes once Stories 1-2 land.

**Acceptance Scenarios**:

1. **Given** a fixture mission (or scenario) with `contracts/` declared as both an
   optional artifact and a required path convention, with the directory absent,
   **When** the fixture is run against the current `main` baseline, **Then** it
   demonstrably fails by observing the bare-token path in the reported message
   instead of the resolved path, AND observing `contracts` present in both
   `missing_optional` and `path_violations` simultaneously.
2. **Given** the same fixture, **When** run after Stories 1-2's fixes land, **Then**
   it passes: the reported path is resolved, and the fact is reported through exactly
   one severity.
3. **Given** the fixture, **When** a reviewer reads it without reading the
   implementation diff, **Then** it is legible as a repro of the exact defects
   described in #3085 (owner/dependency context — this mission, both issues, and the
   specific functions under test — is discoverable from the fixture's docstring/
   comments, satisfying the triage comment's "owner/dependency links" requirement).

### Edge Cases

- A declared path is absolute (`candidate.is_absolute()` true in
  `validate_mission_paths`): resolution and reporting are unaffected by this mission
  (no `feature_dir`/`project_root` prefixing applies today; Story 1 must not change
  this case's behavior).
- A mission type declares no `paths:` at all (e.g. a hypothetical minimal mission
  type): `validate_mission_paths` returns immediately with `required_paths` empty —
  a no-op, unaffected by any of these three fixes.
- A declared path token is under `artifacts.optional`/`artifacts.required` but is
  **not** also under `paths.deliverables`/`paths.workspace`/etc. (i.e. only
  single-declared, the non-`contracts/` common case): Story 2's reconciliation must
  leave this path's reporting exactly as today — the dedup only changes behavior for
  a token declared under *both* lists for the same resolved location.
- `--json` output: Stories 2 and 3 change human-console and/or shared summary text;
  the JSON payload's `missing_optional`/`path_violations`/`warnings` fields must stay
  internally consistent with each other post-fix (no format where JSON still shows
  the old contradiction while console does not, or vice versa).
- `format_warnings()`'s lenient-mode output (the text printed under `--lenient`) is
  unchanged by this mission — only `format_errors()`'s strict-mode message and
  `--help` text change (Story 3 / FR-004-FR-006 target `format_errors()` and the CLI
  help text only). `format_warnings()` and `format_errors()` both currently render
  from the same `PathValidationResult.suggestions` list built once by
  `suggest_directory_creation`; an implementation of FR-005's pointer-to-`--lenient`
  wording must not alter that shared list or `format_warnings()`'s own output. This
  is the explicit, checkable guard against #2330 (out of scope): #2330's complaint is
  specifically about the `--lenient` warning print, which this mission does not touch.
- Research-mission `path_prefix` mode (`_path_prefix_for_mission`): artifact-token
  resolution against `feature_dir` is explicitly bypassed when `path_prefix` is set
  (per `validate_mission_paths`'s existing `not path_prefix` guard) — Story 1's fix
  must preserve this; it only corrects what gets *reported*, not which of
  `feature_dir`/`project_root`/`path_prefix` is chosen to resolve against.
- A mission where `strict_metadata` is true (default) but the missing path is a
  **build/repo path** (e.g. `src/`), not an artifact-tagged one: Story 3's wording
  fix must still apply — the honesty gap is about the message's unconditional
  "required" framing, not specific to artifact-tagged paths.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Report the resolved path, not the bare declared token | As an operator, I want the missing-path message and `mkdir -p` suggestion to name the directory the check actually tested, so that following the suggested remedy creates the right directory. | High | Open |
| FR-002 | Reconcile dual-declared path facts to a single severity | As an operator, I want a path token declared as both an optional artifact and a required path convention to be reported once, resolved toward the more restrictive severity — `path_violations` (blocking) wins over `missing_optional` (non-blocking), so the now-redundant `missing_optional` entry for that token is dropped — so that "optional" and "blocking" never contradict each other in the same run and `accept`'s pass/fail boundary for today's fixtures is unchanged. | High | Open |
| FR-003 | Remove the cosmetic duplicate "Optional artifacts missing" print | As an operator, I want each distinct fact printed once in the console summary, so that the output isn't padded with an identical line repeated verbatim. | Medium | Open |
| FR-004 | Make the strict-mode failure text's "required" claim accurate for the run's mode | As an operator, I want the failure message to not assert an unconditional requirement that `--lenient` immediately disproves, so that I can trust what the tool tells me. | High | Open |
| FR-005 | Name `--lenient` (or an equivalent pointer) in the strict-mode failure output | As an operator with a legitimately different repo layout, I want the failure text itself to lead me to the flag that resolves my situation honestly, so that I don't need to read source to discover it. | High | Open |
| FR-006 | Widen `--lenient`'s `--help` text to mention path conventions | As an operator, I want `spec-kitty accept --help` to indicate `--lenient` affects path-convention enforcement, so that `--help` is a second, independent path to the same discovery. | Medium | Open |
| FR-007 | Provide a runnable repro/acceptance fixture for the wrong-path and double-reporting defects | As a reviewer, I want a focused, standalone fixture that fails on pre-fix code and passes on post-fix code for both #3085 defects, so that the maintainer's binding triage requirement (2026-08-02: "add a focused repro/acceptance fixture ... before implementation") is met, not merely implied by unit tests. The fixture must invoke `validate_mission_paths` and `collect_feature_summary` (or the `accept` CLI command) directly against a real/realistic mission layout — not a hand-built `PathValidationResult`/`AcceptanceSummary` stand-in — so reverting Stories 1-2's code changes necessarily flips the fixture's own pass/fail result. | High | Open |
| FR-008 | Preserve `--lenient`'s existing downgrade-to-warning behavior for missing paths | As an operator relying on today's `--lenient` semantics, I want missing paths still downgraded to a warning (never silently skipped, never still-blocking) under `--lenient` after this mission's wording and dedup changes, so that this mission does not regress the #1892 behavior. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Red-first coverage per behaviour change | Every FR above (001-007) has at least one test that demonstrably fails against the pre-fix code and passes post-fix (reproduced through the pre-existing entry point, per charter Standing Order 4 / ATDD) — not merely a new test written green from the start. | Testing | High | Open |
| NFR-002 | Pinned regression tests stay green, unmodified | The three pinned tests (see Success Criteria) continue to pass without any change to their assertions or fixtures. | Testing | High | Open |
| NFR-003 | Terminology canon compliance | All new/changed operator-facing strings, code comments, and this mission's own artifacts use "Mission" (never "feature"/"feature*" aliases), per `AGENTS.md`'s Terminology Canon. | Consistency | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No change to which paths are enforced | This mission changes only what the path-convention check *reports*; it must not add, remove, or alter which paths a mission type declares, nor change the pass/fail boundary. FR-002's dedup resolves a dual-declared token toward the more restrictive severity (`path_violations`, blocking, wins over `missing_optional`, non-blocking) precisely because that is the only resolution direction that leaves the pass/fail boundary unchanged; resolving toward `missing_optional` instead would silently stop blocking `accept` on a missing `contracts/`, which is #3016's relief landing as an unintended side effect. #3016 remains explicitly out of scope. | Scope | High | Open |
| C-002 | No change to what the check enforces for non-standard layouts | Whether `src/`/`tests/`/`contracts/` are the right conventions for Django `apps/`-style, Go `internal/`-style, or docs-only repos is not addressed by this mission (#3016, #2330 out of scope). | Scope | High | Open |
| C-003 | Canonical mission-type source for `accept` | `accept` loads mission config from `src/specify_cli/missions/<type>/mission.yaml` at runtime, via `_mission_path_by_name` → `_packaged_missions_dir()` (`src/specify_cli/mission.py`). `packs/built-in/missions/` is a separate tree serving the doctrine resolver, not what `accept` reads. Any fix or fixture referencing mission-type config must target the former; do not conflate the two trees. | Technical | High | Open |
| C-004 | Campsite-clean tidy-first is a plan-phase concern | Any Sonar findings, over-long functions, or refactor-worthy debt on the touched surfaces (`validators/paths.py`, `acceptance/__init__.py`, `acceptance/summary_core.py`, `cli/commands/accept.py`) is a distinct, behavior-preserving pass to be scoped and sequenced during planning (charter Standing Order 2), not committed to here. | Process | Low | Open |

### Key Entities

- **`PathValidationResult`** (`validators/paths.py`): carries `missing_paths`,
  `warnings`, `suggestions` for a mission's declared path conventions. FR-001 changes
  what value gets stored in `missing_paths`/`warnings` (resolved vs. bare token);
  FR-004/FR-005 change what `format_errors()` asserts.
- **`AcceptanceSummary`** (`acceptance/__init__.py`): carries `optional_missing` and
  `path_violations` as separate fields; `.ok` gates on `not self.path_violations` (and
  other fields, unrelated to this mission) but not on `optional_missing`.
  `optional_missing` is computed by `_missing_artifacts(feature_dir)` from a
  hardcoded, mission-type-agnostic literal list (`QUICKSTART_FILE`, `DATA_MODEL_FILE`,
  `RESEARCH_FILE`, and the bare string `"contracts"`) — it takes no `mission`
  parameter and does **not** read `mission.config.artifacts.optional`; the literal
  list happens to include `"contracts"` today, which is what makes `contracts/`
  dual-reported for `software-dev` missions specifically. `path_violations` (via
  `evaluate_path_conventions` → `validate_mission_paths`) is the side that genuinely
  reads `mission.config.paths` and `mission.config.artifacts` — but `path_violations`
  itself is not a list of individually comparable resolved-path strings today:
  `evaluate_path_conventions` collapses `PathValidationResult.missing_paths` (the
  structured, per-path list — post-FR-001, each entry holds the resolved path, e.g.
  `kitty-specs/<slug>/contracts/`) into a single, fully-rendered `format_errors()`
  paragraph before returning it as `path_violations`'s one-or-zero-element list; the
  individual resolved-path tokens never leave `evaluate_path_conventions`'s local
  scope in the current code. This is pinned by SC-005's
  `test_strict_metadata_true_blocks_with_violation`, which asserts
  `path_violations == ["missing src/"]` (the literal rendered string, not a list of
  paths) via a plain 2-tuple destructure — `violations, warning =
  evaluate_path_conventions(...)` — of the function's existing return value. FR-002's
  reconciliation is therefore an **interface change**, not a post-hoc comparison
  between two lists that don't yet coexist in comparable form: `evaluate_path_conventions`
  must gain a way to receive `optional_missing`'s tokens so it can drop, from that
  caller-owned list, whichever entries also appear (after normalization) in the
  resolved `missing_paths` — before `format_errors()` renders `path_violations`, which
  continues to render the FULL, unfiltered `missing_paths` exactly as it does today.
  That "path_violations renders unfiltered" detail is not optional: dropping an entry
  from `missing_paths` itself (rather than from `optional_missing`) would let
  `path_violations` go empty for a mission whose only declared path is the
  dual-declared one, silently flipping `AcceptanceSummary.ok` — precisely the
  `missing_optional`-wins outcome C-001 forbids as "#3016's relief landing as an
  unintended side effect." Because SC-005/NFR-002 pin `evaluate_path_conventions`'s
  return to that exact 2-tuple shape (both pinned tests destructure it literally and
  assert on the destructured values' exact types/contents), the interface change WP2
  makes must be additive on the **input** side (e.g. a new, defaulted parameter the
  two pinned tests' existing calls simply omit) — not a change to what the function
  returns; widening the return arity (e.g. a third return value) would break both
  pinned tests' `x, y = evaluate_path_conventions(...)` unpacking and is therefore not
  a viable path here. Finally, the comparison itself needs an explicit
  token-normalization rule: `optional_missing`'s entries are bare,
  feature_dir-relative strings (e.g. `"contracts"`, from
  `str(p.relative_to(feature_dir))`), while the resolved `missing_paths` entries are
  more qualified (e.g. `kitty-specs/<slug>/contracts/` once FR-001 lands) — the two
  won't be string-equal even once both are in scope together, so WP2 must define how
  they're reduced to a common, comparable token (e.g. both relative to `feature_dir`,
  slash-stripped) once FR-001 fixes the resolved string's concrete shape. The
  propagation mechanism itself is pinned too, not left to WP2's judgment: because the
  return arity above cannot change, and `collect_feature_summary` binds
  `missing_optional` from `_missing_artifacts(...)` exactly once — reusing that same
  list object for both the `build_warnings(missing_optional=missing_optional, ...)`
  call and the later `AcceptanceSummary(optional_missing=missing_optional, ...)`
  construction that follow it — the only channel through which the filtered result can
  reach either downstream use is `evaluate_path_conventions` mutating the
  `optional_missing` list it is passed **in place** (e.g. slice assignment or repeated
  `.remove()` for the matching, normalized entries) before its existing 2-tuple return
  runs; the caller's `missing_optional` binding is never reassigned, so both
  `build_warnings` and the `AcceptanceSummary` construction see the deduped list for
  free without any further plumbing. This is a deliberate, documented departure from
  this module's otherwise-pure-transform convention — every sibling function here
  (`build_warnings`, `build_work_package_state`, etc.) is documented "Pure:" and
  communicates results only via return values, per this file's own module docstring
  ("Every function here is a deterministic transform over already-resolved inputs").
  A reviewer must not be able to mistake the new parameter for an inert, no-op input:
  WP2 must name it to signal the side effect (e.g. `optional_missing_to_dedup`, not a
  name that reads as a plain pass-through) and document the in-place-mutation contract
  directly in `evaluate_path_conventions`'s docstring, next to its existing "returns
  (path_violations, warning)" line.
- **`mission.yaml` `artifacts.optional` / `paths.deliverables`** (declarative
  config, e.g. `src/specify_cli/missions/software-dev/mission.yaml`): the source of
  the dual declaration for `contracts/` that produces the config-driven half
  (`path_violations`) of the fact FR-002 must reconcile; `optional_missing`'s
  hardcoded list (see the `AcceptanceSummary` entry above) is what happens to also
  flag `contracts/` today, not a second read of this YAML. Per the mission's design
  decision, the reconciliation is code-side (an interface change threading
  `evaluate_path_conventions`'s structured `missing_paths` to the point where
  `optional_missing` can be filtered against it — see the `AcceptanceSummary` entry
  above), not a change to which tokens are declared where in the YAML. The `research`
  mission type declares an analogous-looking dual token
  (`data/` under both `artifacts.optional` and `paths.data`,
  `src/specify_cli/missions/research/mission.yaml`), but `_missing_artifacts()`'s
  hardcoded list never checks `data/`, so no double-report defect exists there today.
  This mission's fix does not extend to `research`'s `data/` or any other mission
  type's potential future dual declarations — only `contracts/`'s demonstrated
  `software-dev` defect is in scope, to head off unintended scope creep in WP2.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a mission-artifact-tagged path convention that is missing, the
  reported path string and `mkdir -p` suggestion both equal the resolved path that was
  actually tested (`feature_dir`-relative), not the bare declared token — verified by
  a test asserting on `PathValidationResult.missing_paths`/`.suggestions` content.
- **SC-002**: For `contracts/` (or any token declared under both
  `artifacts.optional` and `paths.*` for the same resolved location), an `accept` run
  with that location missing produces exactly one severity for that fact — either in
  `missing_optional` or in `path_violations`, never both — and the console output
  mentions it once, not twice.
- **SC-003**: The strict-mode path-convention failure text does not assert an
  unconditional "required" claim that `--lenient` disproves, and names `--lenient` (or
  an unambiguous equivalent pointer) as an alternative remedy; `accept --help`'s
  `--lenient` description mentions path conventions.
- **SC-004**: A runnable fixture — invoking `validate_mission_paths` and
  `collect_feature_summary` (or the `accept` CLI command) directly against a
  real/realistic mission layout, per FR-007 — reproduces both the
  wrong-path-reported and the double-reporting-contradiction defects, fails on
  pre-fix code, and passes on post-fix code.
- **SC-005**: The following three pre-existing tests continue to pass, unmodified, as
  a gate on this mission's changes:
  - `tests/specify_cli/acceptance/test_acceptance_cores.py::TestEvaluatePathConventions::test_strict_metadata_true_blocks_with_violation`
  - `tests/specify_cli/acceptance/test_acceptance_cores.py::TestEvaluatePathConventions::test_strict_metadata_false_downgrades_to_warning`
  - `tests/specify_cli/cli/commands/test_accept_warnings_render.py::test_lenient_path_convention_warning_is_rendered_in_console`

  (Verified present and passing on this checkout before mission start, alongside the
  documented baseline: `tests/specify_cli/acceptance/`,
  `tests/specify_cli/cli/commands/test_accept_warnings_render.py`,
  `tests/agent/test_validators_unit.py`, and
  `tests/characterization/test_trio_json_envelope.py` — 180 passed, 0 failed. Any red
  discovered during this mission belongs to this mission; `main` carries a separate,
  unrelated known-red set tracked under issue #3284, not present on this surface.)
- **SC-006**: No requirement above changes which paths a mission type declares or
  which paths block `accept` for a reason other than FR-002's dedup (i.e. #3016's and
  #2330's territory is untouched).

## Non-Goals

- **#3016** — whether the hardcoded `src/`/`tests/`/`contracts/` path conventions
  declared in `mission.yaml` files are the right conventions for non-standard repo
  layouts (Django `apps/`, Go `internal/`, docs-only repos, etc.). This mission fixes
  what the check *says*, not what it *enforces* or which paths a mission type
  declares.
- **#2330** — out of scope; not touched by any requirement above. See the Edge
  Cases entry pinning `format_warnings()`'s lenient-mode output as unchanged — the
  concrete guard against Story 3's strict-mode wording change bleeding into the
  shared `suggestions` list that #2330's complaint is actually about.
- Adding a new mission type, per-project path-convention overrides, or automatic
  layout detection.
- Renaming or reworking the `--lenient` flag itself (only its `--help` text and its
  discoverability from the failure output are in scope).

## Verification Notes (deviations from the mission brief, confirmed against live code)

- All three defects, their file/function locations, and the described mechanism were
  independently confirmed by reading `src/specify_cli/validators/paths.py`,
  `src/specify_cli/acceptance/__init__.py`, `src/specify_cli/acceptance/summary_core.py`,
  and `src/specify_cli/cli/commands/accept.py` on this checkout, and against `gh issue
  view 3085`/`3730` (titles, bodies, and #3085's 2026-08-02 triage comment).
- `suggest_directory_creation`'s definition starts at line 81 (not 79 as the brief's
  approximate range said) and runs to line 105 — a two-line drift, noted for
  precision; the function's described behavior is otherwise accurate.
- `packs/built-in/missions/software-dev/mission.yaml` was found to carry the identical
  `contracts/` dual declaration (`artifacts.optional` line 145, `paths.deliverables`
  line 154) as `src/specify_cli/missions/software-dev/mission.yaml`. Per C-003, only
  the latter is canonical for what `accept` loads at runtime; the doctrine-resolver
  tree's copy is not authoritative for this mission's fix and is out of scope to
  change (noted here so a reviewer does not assume it was missed).
- The three pinned tests were run directly on this checkout (`uv run pytest` on the
  three node IDs) and confirmed passing (3 passed) before writing this spec, not only
  taken on faith from the brief.
