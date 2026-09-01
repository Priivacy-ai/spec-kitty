# Implementation Plan: Accept Path-Convention Honesty & Deduplication

**Mission Branch**: `fix/accept-path-remediation-honesty-3730` | **Date**: 2026-08-25 | **Spec**: `kitty-specs/accept-path-remediation-honesty-01M0TWZP/spec.md`
**Input**: `kitty-specs/accept-path-remediation-honesty-01M0TWZP/spec.md` (gated PASSED, 3 review rounds), `tracer-approach.md`, `tracer-design-decisions.md`, `tracer-tooling-friction.md`, `reviews/spec.confirmed.yaml`

This plan operationalizes the spec's already-pinned design (notably the Key Entities
section's exact FR-002 interface-change contract). It does not re-derive or re-litigate
any settled decision recorded there or in `reviews/spec.confirmed.yaml`.

## Summary

`spec-kitty accept`'s path-convention check has three operator-facing honesty defects
on one seam: (1) it reports the bare declared token instead of the resolved path it
actually tested; (2) `contracts/`'s dual declaration in `software-dev/mission.yaml`
(`artifacts.optional` + `paths.deliverables`) makes the same missing fact print once as
a non-blocking warning and once as a blocking violation, plus a cosmetic duplicate
print of the warning; (3) the strict-mode failure text asserts an unconditional
"required" claim that `--lenient` immediately disproves, without ever mentioning
`--lenient`. This mission fixes all three as a four-WP sequence (resolved-path
correctness → dedup → honest wording → red-first tests including a named repro
fixture), landing entirely on the CLI/validators/acceptance layer and introducing no
NEW kernel or doctrine coupling (one of the four touched files, `acceptance/__init__.py`,
already imports two kernel utilities for pre-existing, unrelated functionality — see
"Which seam the change lands on" below for the precise claim).

## Technical Context

**Language/Version**: Python 3.11+ (charter-mandated; this checkout runs 3.12 in CI).
**Primary Dependencies**: none new — `typer`, `rich` (existing, for the CLI/console
surfaces this mission edits), stdlib `pathlib`/`dataclasses`.
**Storage**: N/A — no persisted state; the change is to in-memory validation results
and their rendering.
**Testing**: `pytest`, targeted directories only per charter's testing-requirements
clause (not the full ~17,000-test suite): `tests/specify_cli/acceptance/`,
`tests/specify_cli/cli/commands/test_accept_warnings_render.py`,
`tests/agent/test_validators_unit.py`, `tests/characterization/test_trio_json_envelope.py`,
plus the new FR-007 fixture file WP4 adds.
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows), unaffected — no
platform-specific code paths are touched.
**Project Type**: Single project (existing `src/specify_cli/` package); no new
top-level structure.
**Performance Goals**: N/A — this is a string-formatting/reporting fix on an
already-fast validation path (well under the charter's <2s CLI budget already).
**Constraints**: C-001 (no change to which paths are enforced / pass-fail boundary),
C-002 (no change to what conventions are enforced), C-003 (canonical mission.yaml
tree only), C-004 (campsite-clean is a plan-phase decision, resolved below).
**Scale/Scope**: Four files touched (`validators/paths.py`, `acceptance/__init__.py`,
`acceptance/summary_core.py`, `cli/commands/accept.py`) plus tests. No new modules.

## Constitution Check

*Gate: charter alignment, checked before Phase 0 research and re-checked after design.*

- **Single canonical authority** (charter Governing Principles): WP2 reconciles two
  already-computed result lists in code rather than adding a second config-reading
  path or a second source of truth for "is this path required" — satisfies
  reconcile-don't-duplicate.
- **Architectural alignment**: change lands entirely within the existing
  CLI → acceptance → validators layering; no new seam, no NEW kernel/doctrine coupling
  (one touched file already has pre-existing, unrelated kernel imports — see below).
  See "Which seam the change lands on" below.
- **ATDD-first / red-first** (charter Standing Order 4): WP4 is sequenced explicitly
  to require, per WP, a test that fails on revert — not merely new green coverage. See
  "Red-first / revert discipline per WP" below.
- **Mission tracer files** (charter Standing Order 3): this plan phase surfaced one
  concrete decision beyond what's recorded (the exact WP1 relative-path formatting
  approach for `full_path`, and the exact WP2 parameter name/signature) — appended to
  `tracer-design-decisions.md` and `tracer-approach.md` as directed (see end of this
  document; do not re-read those files for content already reproduced here).
- **Campsite cleaning** (charter Standing Order 2 / C-004): resolved explicitly below
  — **not warranted** for this mission, with the evidence that makes that a legitimate
  answer rather than a skip.
- No violations requiring the Complexity Tracking table below; it is intentionally
  left as N/A (single project, no added abstraction layers, no new dependencies).

## Which seam the change lands on

**CLI / validators / acceptance layer only.** Concretely:
- `src/specify_cli/validators/paths.py` — `validate_mission_paths`, `format_errors`,
  `format_warnings`, `suggest_directory_creation` (pure validation + string
  formatting, no I/O beyond `Path.exists()` checks already present).
- `src/specify_cli/acceptance/summary_core.py` — `evaluate_path_conventions` (pure
  transform per this module's own docstring convention, with WP2's documented,
  deliberate in-place-mutation exception).
- `src/specify_cli/acceptance/__init__.py` — `_missing_artifacts`,
  `collect_feature_summary`, `AcceptanceSummary`.
- `src/specify_cli/cli/commands/accept.py` — `_print_acceptance_summary` (dedup
  removal), the `accept()` command's `--lenient` `typer.Option` help string.

**No NEW kernel/doctrine coupling.** Precisely: this mission introduces no NEW
kernel/doctrine import or read anywhere in its diff. It is **not** true that none of the
four files import from `src/kernel/` — `src/specify_cli/acceptance/__init__.py` already
imports `kernel.clock.now_utc_stamp` (`:10`) and `kernel.paths.to_posix` (`:14`), both
live call sites (used for acceptance-timestamp generation and status-artifact basename
normalization respectively, at `:1367` and `:205`) for pre-existing functionality
untouched by this mission's WPs. None of the other three files (`validators/paths.py`,
`acceptance/summary_core.py`, `cli/commands/accept.py`) import from `src/kernel/`,
`src/doctrine/`, or `src/mission_loader/`, and no WP below adds a new such import.
`mission.yaml` is read via the existing `Mission`/`MissionConfig` objects already passed
into these functions today — this mission adds no new read of mission config, only
reconciles two reads that already exist (per SPEC-ARCH-001's correction: only
`evaluate_path_conventions` reads `mission.config`; `_missing_artifacts` reads a
hardcoded literal list and gains no new `mission` parameter).

## Canonical sources

`accept` loads mission config from `src/specify_cli/missions/<type>/mission.yaml` at
runtime, via `_mission_path_by_name` → `_packaged_missions_dir()`
(`src/specify_cli/mission.py:78,70`). `packs/built-in/missions/` is a separate tree
serving the doctrine resolver — confirmed on this checkout to carry an identical
`contracts/` dual declaration (`artifacts.optional` line 145, `paths.deliverables`
line 154), but it is **not** what `accept` reads and is **not** touched by any WP
below. All WPs read/reference `src/specify_cli/missions/software-dev/mission.yaml`
only, and no WP edits either `mission.yaml` tree (C-003; the fix is code-side
reconciliation, per the tracer's settled design decision).

## Baseline honesty (this plan's own commitment, stated verbatim, not paraphrased)

`tests/specify_cli/acceptance/`, `tests/specify_cli/cli/commands/test_accept_warnings_render.py`,
`tests/agent/test_validators_unit.py`, `tests/characterization/test_trio_json_envelope.py`
→ **180 passed, 0 failed** on this checkout at mission start. This blast-radius surface
is GREEN — any red discovered later belongs to this mission, not to `main`'s
separately-tracked known-red set (#3284). Must-keep-passing pins, verbatim, never
modified:
- `tests/specify_cli/acceptance/test_acceptance_cores.py::TestEvaluatePathConventions::test_strict_metadata_true_blocks_with_violation`
- `tests/specify_cli/acceptance/test_acceptance_cores.py::TestEvaluatePathConventions::test_strict_metadata_false_downgrades_to_warning`
- `tests/specify_cli/cli/commands/test_accept_warnings_render.py::test_lenient_path_convention_warning_is_rendered_in_console`

Every WP below is designed so these three tests require **zero** edits: both pinned
`evaluate_path_conventions` tests call it positionally with exactly today's 4
arguments + `strict_metadata=`, so WP2's new parameter must default such that omitting
it is a no-op (empty/`None` optional-missing list to reconcile against). The lenient
render test only asserts on `summary.warnings` content already built by
`build_warnings`, which WP3 does not touch (`format_warnings()` is explicitly
unchanged — see WP3 below).

## Non-goals held hard

- **NOT #3016** — whether the hardcoded `src/`/`tests/`/`contracts/` conventions are
  the right conventions for non-standard layouts (Django `apps/`, Go `internal/`,
  docs-only repos). This mission fixes what the check *says*, never what it
  *enforces* or which paths a mission type declares. WP2's reconciliation direction
  (`path_violations` wins) is specifically the one that keeps this non-goal intact —
  the other direction would silently relieve #3016 as a side effect, which C-001
  forbids.
- **NOT #2330** — `format_warnings()` (the `--lenient`-mode print) is unchanged by
  this mission. WP3 touches only `format_errors()` (strict-mode) and the CLI
  `--help` text; both currently draw from the same `PathValidationResult.suggestions`
  list, so WP3's implementation must not alter the shared list itself, only the
  trailing prose `format_errors()` appends after rendering it.
- Not in scope: new mission types, per-project path-convention overrides, automatic
  layout detection, renaming/reworking `--lenient` itself.

## Blast radius

`src/specify_cli/validators/paths.py`, `src/specify_cli/acceptance/__init__.py`,
`src/specify_cli/acceptance/summary_core.py`, `src/specify_cli/cli/commands/accept.py`,
plus tests under `tests/specify_cli/acceptance/`, `tests/specify_cli/cli/commands/`,
`tests/agent/`, `tests/characterization/`, and one new FR-007 fixture file (WP4). **If
any WP's implementation needs to expand this set, that must be flagged loudly in the
WP's own notes — it changes the collision analysis below.** Zero collisions expected
across the 15 currently-open PRs; #3729 is thematically adjacent (also touches
`accept`) but does not share a file with this mission's blast radius.

## Campsite-clean scope (C-004 resolved here, not deferred again)

**Not warranted.** Evidence checked on this checkout before making this call:
- `acceptance/summary_core.py`'s own module docstring states it was extracted in a
  prior mission (WP04/T021) specifically "to bring `collect_feature_summary` and
  `_build_recommended_fix_order` under the S3776 <=15 complexity gate" — the
  complexity-debt class this mission would otherwise campsite-clean was already paid
  down there.
- Every function this mission's WPs touch is small: `validate_mission_paths` (~80
  lines, single loop, no nested conditionals beyond the existing artifact/build-path
  branch), `evaluate_path_conventions` (~38-39 lines including its docstring —
  `summary_core.py:110-148`), `_missing_artifacts` (~10 lines), `format_errors`/
  `format_warnings` (~15 lines each), `_print_acceptance_summary` (~29-31 lines —
  `accept.py:453-483`). None are near the 15-ceiling *complexity* by inspection or by
  the extraction history above — `evaluate_path_conventions` and
  `_print_acceptance_summary` are longer in raw line count than the earlier estimate
  in this section, but neither has nested branching or cyclomatic complexity anywhere
  near the charter's 15-ceiling (each is a short sequence of guard clauses / linear
  prints, not deep nesting), so the "not warranted" conclusion below still holds at
  the corrected sizes.
- Duplicated-literal check (>=3x threshold) on the four touched files: `"Optional
  artifacts missing"` occurs exactly twice (`summary_core.py:160`,
  `accept.py:478`) — WP2/WP3 removes one of those two occurrences as the functional
  fix itself, so there is no separable "clean first, then fix" step; the dedup *is*
  the cleanup. The literal `"contracts"` occurs exactly once
  (`acceptance/__init__.py:591`). Neither clears the >=3x bar that would license an
  opening tidy-first commit.
- `accept()` (`cli/commands/accept.py:633`) is long (~280 lines) but this mission's
  touch there is two single-line edits (the `--lenient` help string, and threading a
  mode-parameter into an existing call) — refactoring the whole command function is
  not domain-matched debt for a reporting-honesty fix and would violate Locality of
  Change (`DIRECTIVE_024`) by dragging in a much larger, unrelated file for a
  two-line change.

Conclusion: no opening campsite-clean commit. This is stated as the plan's explicit
answer to C-004, not a silent skip.

## Coverage floors

The four touched files (`validators/paths.py`, `acceptance/__init__.py`,
`acceptance/summary_core.py`, `cli/commands/accept.py`) are **not** under
`src/kernel/`, `src/doctrine/`, or `src/specify_cli/mission_loader/`, so:
- The kernel-tests 90% floor (`kernel-tests` job, gated on the `kernel` path-filter
  group in `.github/workflows/ci-quality.yml`) **does not bind** — this diff matches
  no file under `src/kernel/**`.
- The mission-loader 90% floor (`--cov-fail-under=90` on
  `src/specify_cli/mission_loader`, gated on `next || core_misc || platform`)
  **does not bind** — this diff matches none of those filter groups either.
- **Correction to the readiness framing on `diff-coverage`, verified against the
  actual workflow rather than assumed**: the `diff-coverage` job's *enforced*
  (`--fail-under=90`, blocking) step only checks a hardcoded `critical_paths` allow-
  list — `src/kernel/*`, `src/doctrine/*`, `src/charter/*`, `src/specify_cli/status/*`,
  `src/specify_cli/lanes/branch_naming.py`, `src/specify_cli/dashboard/handlers/*`,
  `src/specify_cli/dashboard/scanner.py`, `src/specify_cli/merge/*`,
  `src/runtime/next/*`, `src/mission_runtime/*` (`.github/workflows/ci-quality.yml:3349-3372`,
  the `critical_paths=( ... )` array itself — re-verify at implementation time since CI
  workflow line numbers drift with every edit to the file).
  None of `validators/**`, `acceptance/**`, or `cli/**` is in that list. The *only*
  other diff-coverage step ("full-diff, advisory") runs `diff-cover ... || true` —
  genuinely non-blocking, its failure cannot fail the job
  (`.github/workflows/ci-quality.yml:3400-3410`). **So `diff-coverage --fail-under=90`
  does NOT enforce on this mission's changed lines**, contrary to the readiness
  framing's assumption. This does not relax the mission's actual obligation: NFR-001
  (every FR needs a red-first test) and the charter's "every new branch/helper needs
  tests in the same PR" bind independently of diff-coverage's numeric floor, and are
  enforced the honest way here — by the pinned/new tests in WP4 actually running (and
  needing to pass) in `fast-tests-cli`/`integration-tests-cli` and
  `fast-tests-core-misc`/`integration-tests-core-misc` (see Gate set below), not by a
  coverage percentage gate. Every touched line still gets direct test coverage in
  this PR; the enforcement mechanism is "the new/pinned tests exist and are green,"
  not "the diff-coverage tool measured it."

## Gate set

Derived by reading `.github/workflows/ci-quality.yml` on this checkout (not
recalled from memory), specifically the `changes` job's `dorny/paths-filter` block
and each downstream job's `if:` condition.

**Path-filter groups this diff falls into:**
- `src/specify_cli/validators/**` → `governance` filter group
  (`.github/workflows/ci-quality.yml:510`).
- `src/specify_cli/acceptance/**` → its own `acceptance` filter group
  (`.github/workflows/ci-quality.yml:461-462`).
- `src/specify_cli/cli/**` and `tests/specify_cli/cli/**` → `cli` filter group
  (`.github/workflows/ci-quality.yml:318-321`).
- `tests/agent/**` → its own `agent` filter group (`.github/workflows/ci-quality.yml:437-439`).
- `tests/characterization/**` → routed into the `core_misc` filter group (explicit
  comment in the workflow naming this exact directory,
  `.github/workflows/ci-quality.yml` near the `core_misc` block).

**Job names that therefore run** (verified against each job's `if:` expression, not
assumed from the group name):
- `fast-tests-cli` and `integration-tests-cli` — gated on `cli == 'true'`
  (`ci-quality.yml:1553`, `:2876`).
- `fast-tests-core-misc` and `integration-tests-core-misc` (matrix-sharded) — gated on
  a disjunction that includes `acceptance`, `governance`, and `core_misc`
  (`ci-quality.yml:1667`, `:1922`); both fire for this diff via `acceptance` and
  `governance` alone even before considering `cli`.
- `fast-tests-agent` and `integration-tests-agent` — gated on `agent == 'true'`
  (`ci-quality.yml:2328`, `:2365`).
- `arch-adversarial` (3-shard matrix, `arch_shard_1/2/3`) — always-on regardless of
  path-filter group: it carries no dorny filter-group `if:` gate at all
  (`ci-quality.yml:2082-2086`), running on every push/PR via
  `-m '<shard> and not windows_ci and (git_repo or integration or architectural) and
  not timing'` (`ci-quality.yml:2196`). This is the job that actually runs
  `tests/architectural/test_no_legacy_terminology.py` for NFR-003 below — see WP3 —
  not `core_misc`.
- `kernel-tests` and the mission-loader coverage job do **not** run for this diff
  (gated on `kernel` and `next || core_misc || platform` respectively — this diff
  matches neither); confirmed above under Coverage floors.

**Always-on gates (unconditional `lint` job, not path-filtered):**
- **commitlint** — lints every commit message in the PR's commit range; binds
  regardless of file type. Every WP commit in this mission must use
  `type(scope): subject` form (the scaffold's own auto-commit `e2ecee4ee` already
  violates this — noted in `tracer-tooling-friction.md`, a PR-prep concern for
  sk-implement/sk-review, not this plan's WPs).
- **markdownlint** — runs only on changed `*.md`/`*.mdx` files, but
  `.markdownlint-cli2.jsonc`'s `ignores` list explicitly includes `kitty-specs/**`
  (confirmed by reading the config file directly). This `plan.md` and any
  tracer-file appends in `kitty-specs/accept-path-remediation-honesty-01M0TWZP/`
  are therefore **exempt** — markdownlint does not bind on this mission's own
  planning artifacts. (No other `.md` file is touched by any WP.)
- **TID251 banned-API lint** (`ruff check src tests --select TID251`,
  `ci-quality.yml:894`) — relevant: WP4's fixture must not use a banned API; standard
  compliance, no special risk identified.
- **Bandit + pip-audit** (`ci-quality.yml:914-938`) — relevant only in that new code
  must not trip a security scanner; this mission adds no subprocess/eval/network
  code, low risk.
- **`patch()` target-string validation** (`ci-quality.yml:940`) — relevant for WP4:
  any `unittest.mock.patch("module.path.symbol")` string in the new fixture/tests
  must reference a real, currently-importable symbol (this gate has bitten prior
  missions on stale patch targets after a refactor — WP4's fixture patches nothing
  hand-built per FR-007's own constraint, so risk is low, but any patch target used
  incidentally in new unit tests must be verified importable).
- **Typer JSON error surface** (`uv run --with 'typer>=0.26' python -m pytest
  tests/agent/test_json_group_typer_surface.py -q`, `ci-quality.yml:896-900`) —
  relevant since FR-002's Edge Cases explicitly require `--json` output to stay
  internally consistent post-fix; this existing suite is the gate that would catch a
  Typer-version-specific JSON-surface regression, separate from this mission's own
  `--json` consistency test (WP4).
- **`uv.lock` freshness** (`uv lock --check`, `ci-quality.yml:3906-3924`) — binds
  unconditionally but this mission adds no dependency and touches neither
  `pyproject.toml` nor `uv.lock`, so it is expected to stay green with zero action.
- **mypy --strict** and **ruff** (general lint, part of the same unconditional `lint`
  job) — bind on every changed line in the four touched files.

**diff-coverage** — see Coverage floors above: the enforced critical-path step does
not bind on this diff's files; the full-diff step is advisory only (`|| true`).

**SonarCloud does NOT run on `pull_request`.** Verified directly in
`.github/workflows/ci-quality.yml:3449-3455` and the job's own `if:` condition at
line 3506: `if: always() && (github.event_name == 'schedule' ||
github.event_name == 'workflow_dispatch')`. PRs skip Sonar entirely (the job's own
comment: "PRs skip Sonar entirely to keep review latency low"). This plan does not
promise a Sonar verdict for this PR.

## Proposed WP shape

Verified against the artifacts and against the live code read during this planning
pass. **Confirms the readiness-verified default shape below with two additions**: (a)
WP1's exact resolved-string formatting approach is specified concretely (not left
implicit), and (b) WP2's parameter name/signature is pinned concretely, both fed back
into the tracer files per Standing Order 3.

### WP1 — resolved-path correctness

**File**: `src/specify_cli/validators/paths.py`, `validate_mission_paths` (loop at
`:194-208`).

**Root cause** (confirmed by reading the function): at line 207,
`result.missing_paths.append(relative_path)` appends `relative_path` — the
`_prefix_required_path`-adjusted but still-*declared* token (e.g. `"contracts/"`)
— even though the preceding lines (194-202) already computed `full_path`, the
actual filesystem location tested via `full_path.exists()`. For an artifact-tagged
token, `full_path = feature_dir / candidate`; for everything else,
`full_path = project_root / candidate`. `full_path` is discarded after the
`.exists()` check instead of being reported. The very next line, `:208`
(`result.warnings.append(f"{mission.name} expects {key} path: {relative_path} (not
found)")`), builds the primary operator-visible sentence from the **same** bare
`relative_path` token — it has the identical defect and must be fixed together with
line 207, not as an afterthought: `format_errors()`/`format_warnings()` (`:61-78`,
`:44-58`) render `self.warnings` and `self.suggestions` as their content lines;
`self.missing_paths` is never rendered directly anywhere in the codebase (its only
other reader is `suggest_directory_creation`, which builds `self.suggestions`). Fixing
only line 207 would leave the actual first-read sentence — "`{mission.name} expects
{key} path: {relative_path} (not found)`" — printing the wrong (bare-token) location
forever.

**Fix direction**: compute the resolved, reportable string **once**, before either
`append` call, and reuse that single local value for **both**:
- `result.missing_paths.append(resolved)` (replacing line 207's
  `result.missing_paths.append(relative_path)`), and
- `result.warnings.append(f"{mission.name} expects {key} path: {resolved} (not
  found)")` (replacing line 208's `{relative_path}` interpolation with the same
  `resolved` value) —

while preserving:
- the trailing-slash convention `suggest_directory_creation` depends on (`path_str.
  endswith("/")` decides `mkdir -p` vs. `touch` — the resolved string must carry the
  same trailing slash the declared token had, since `full_path` as a bare `Path`
  loses it).
- a safe fallback when `full_path` is not under `project_root` (e.g. a
  cross-worktree topology): prefer `full_path.relative_to(project_root)` when it
  succeeds, fall back to `str(full_path)` on `ValueError` rather than raising —
  `format_errors()`/`format_warnings()` must never crash on a resolvable-but-
  reported path.
- the `candidate.is_absolute()` case and the no-`paths:`-declared no-op case
  unaffected, per spec Edge Cases.

This changes what value lands in both `result.missing_paths` **and**
`result.warnings`. `suggest_directory_creation` consumes `missing_paths` (for the
`mkdir -p`/`touch` suggestions), while `format_errors()`/`format_warnings()` consume
`warnings` and `suggestions` — **not** `missing_paths` directly — so both call sites
must be corrected together for the reporting fix to reach the operator-visible text;
correcting only `missing_paths` would leave the primary rendered sentence wrong.

**New field feeding WP2's dedup (this WP's own addition — additive on top of
`spec.md`'s Key Entities contract, which pins `missing_paths`/`warnings`/
`suggestions` but does not forbid a further field)**: WP2's token-normalization step
(see WP2 below) needs to identify, per `missing_paths` entry, whether it originated
from an artifact-tagged declaration and, when it did, recover its real
`feature_dir`-relative token; nothing available to `evaluate_path_conventions` today
can derive that from `missing_paths` alone — `missing_paths` entries are, post-WP1,
`project_root`-relative resolved strings for every branch, and `_normalize_path_token`
only slash-strips, it does not compute a relative path or recover which branch
produced a given entry. Rather than have WP2 re-derive this, WP1 computes it
directly, in the same loop iteration where `candidate`/artifact-tagging is already
known (`:194-208`), since it is trivial there. Add a new dataclass field,
**`missing_paths_feature_relative: list[str] = field(default_factory=list)`**
(alongside `PathValidationResult`'s existing list fields, `:34-37`), parallel-
populated alongside `result.missing_paths.append(resolved)` for **every** entry,
across all three of `validate_mission_paths`'s mutually-exclusive branches
(`:196-202`).

**The field's values are NOT uniformly `feature_dir`-relative** — only the
artifact-tagged branch's entries are. The other two branches populate a
`project_root`-relative (or, for the absolute case, unchanged-absolute) placeholder.
WP2's consumption of this field (below) is designed to structurally exclude those
placeholder entries from its comparison set via a membership check, not by assuming
they are harmless because they happen not to collide with a real artifact token
today:
- For an artifact-tagged entry (the `elif _normalize_path_token(declared[key]) in
  artifact_tokens:` branch, `:198-200`), append `_normalize_path_token(relative_path)`
  — the pre-resolution declared token itself, e.g. `"contracts"`. This IS
  `feature_dir`-relative by construction: `full_path = feature_dir / candidate` is
  built directly from it, so no further relative-path computation is needed. This is
  the only branch whose entries carry real `feature_dir`-relative semantics.
- For a build/repo-root entry (the `else:` branch, `:201-202`), append
  `_normalize_path_token(resolved)` instead — a `project_root`-relative placeholder
  (`resolved` in this branch is `full_path.relative_to(project_root)`, or
  `str(full_path)` on `ValueError`), **not** a `feature_dir`-relative value. WP2's
  comparison-set construction (below) structurally excludes this entry via an
  `artifact_tokens` membership check — the same recipe `validate_mission_paths`
  computes internally (`:187-192`) — rather than relying on this placeholder simply
  not colliding with a real artifact token by chance.
- For an absolute declared path (the `if candidate.is_absolute():` branch,
  `:196-197`), append `_normalize_path_token(resolved)` too — folded into the same
  placeholder bucket as the build/repo-root case above. Per this WP's Fix direction
  above, `resolved` for an absolute `full_path` is unaffected by this mission: the
  `relative_to(project_root)` computation raises `ValueError` for a path outside
  `project_root`, so `resolved` falls back to `str(full_path)` — the absolute path
  string itself, unchanged — matching spec.md's Edge Case pin that absolute-path
  resolution/reporting stays unaffected by this mission. This entry, too, is
  structurally excluded from WP2's comparison set by the same `artifact_tokens`
  membership check, not by any special-casing in WP1's population logic itself.

`evaluate_path_conventions` already holds the full `path_result` object returned by
`validate_mission_paths` (`summary_core.py:137-143`), not just `missing_paths` in
isolation, so this new field is available to it at no extra plumbing cost.

**Covers**: FR-001, SC-001, User Story 1 (both Acceptance Scenarios).

**Revert test** (must fail if WP1 is reverted): two cases in the same test file, one
per Acceptance Scenario — Case A covers Scenario 1 (artifact-tagged resolution),
Case B is the build/repo-root companion covering Scenario 2 (repo-root reporting
stays unchanged); Case B is what the Test Strategy table's US1/Scenario-2 row cites
as "WP1 revert test's build-path companion assertion."

*Case A — artifact-tagged path (Scenario 1)*: for a mission-artifact-tagged path
convention (`contracts/`) missing under a real `feature_dir` distinct from
`project_root`:
1. `PathValidationResult.missing_paths` and `.suggestions` both contain the resolved
   `feature_dir`-relative string (e.g. `kitty-specs/<slug>/contracts/`) and do **not**
   contain the bare token `contracts/` alone, **and**
2. `PathValidationResult.warnings` (or the full rendered `format_errors()`/
   `format_warnings()` output) also contains the resolved string and does **not**
   contain the bare token — this second assertion is the one that actually falsifies
   FR-001's defect, since `warnings`/`suggestions`, not `missing_paths`, are what
   `format_errors()`/`format_warnings()` render.

*Case B — build/repo-root path (Scenario 2, companion assertion)*: for a missing,
non-artifact-tagged, `src/`-style declared path (the `else:` branch, `:201-202`)
under the same fixture's `project_root`:
3. `PathValidationResult.missing_paths` and `.warnings` contain a `project_root`-
   relative resolved string — the same namespace this branch already reported in
   before WP1 (`resolved` there is `full_path.relative_to(project_root)`, or
   `str(full_path)` on `ValueError`) — confirming WP1's fix to the artifact-tagged
   branch's namespace does not change the build/repo-root branch's, **and**
4. the reported string is unchanged in value from what today's (pre-WP1) code
   reports for this same fixture (pre-WP1, the bare declared token for a build path
   is itself already `project_root`-relative-shaped text, since build paths are
   declared relative to the repo root; post-WP1 `resolved` reduces to the same
   string) — a genuine "stays the same" assertion, not merely "doesn't crash,"
   directly catching a regression where WP1's refactor accidentally re-namespaces the
   build/repo-root branch too.

`missing_paths_feature_relative` itself has no independent operator-visible behavior,
so this revert test does not need to assert on it directly — its correctness is
exercised by WP2's revert test below, the first consumer whose own dedup assertions
depend on its values being right.

Lives in `tests/specify_cli/acceptance/` (or `tests/agent/test_validators_unit.py`,
matching where `validate_mission_paths` is already unit-tested) — new test, red
against current `main`/pre-WP1 code (asserts on the corrected value, which the
current code cannot produce), green once WP1 lands.

### WP2 — stop double-reporting

**Files**: `src/specify_cli/acceptance/summary_core.py` (`evaluate_path_conventions`,
`:110-148`) + `src/specify_cli/acceptance/__init__.py` (call site `:1049-1056`) +
`src/specify_cli/cli/commands/accept.py` (`_print_acceptance_summary`, remove the
duplicate print at `:476-481`).

**Root cause** (confirmed): `software-dev/mission.yaml` declares `contracts/` at
both `artifacts.optional[]` (`:145`) and `paths.deliverables` (`:154`). Per
SPEC-ARCH-001's confirmed correction, `_missing_artifacts()`
(`acceptance/__init__.py:585-595`) does **not** read `mission.config.artifacts` — it
checks a hardcoded, mission-type-agnostic literal list that happens to include the
bare string `"contracts"`. Only `evaluate_path_conventions` → `validate_mission_paths`
genuinely reads `mission.config.paths`/`mission.config.artifacts`. So this is a
post-hoc reconciliation between two already-computed lists, not a
"read-both-YAML-lists-once" join.

**Interface change (pinned by spec.md's Key Entities section — implemented exactly
as specified, not re-derived)**:
- `evaluate_path_conventions` gains a new, defaulted keyword parameter —
  **`optional_missing_to_dedup: list[str] | None = None`** — named to signal the
  side effect per the spec's explicit naming instruction (not `optional_missing` or
  any name reading as inert pass-through).
- Both pinned tests (`test_strict_metadata_true_blocks_with_violation`,
  `test_strict_metadata_false_downgrades_to_warning`) call the function positionally
  with exactly today's 4 args + `strict_metadata=`, omitting the new parameter — the
  default `None` must make the function behave exactly as today (no dedup attempted,
  matching NFR-002's "pinned tests stay green, unmodified" requirement).
- Docstring gains a line next to the existing "Mission path conventions block
  acceptance by default..." / "returns (path_violations, warning)" documentation,
  stating explicitly: *"When `optional_missing_to_dedup` is provided, entries in that
  list whose normalized token also appears in the resolved `missing_paths` are
  removed from the list IN PLACE before this function's own 2-tuple return runs —
  this is a documented side effect, not a pass-through parameter."*
- **Token normalization**: `optional_missing`'s entries are bare, `feature_dir`-
  relative strings (e.g. `"contracts"`, from `_missing_artifacts`'s
  `str(p.relative_to(feature_dir))` at `acceptance/__init__.py:594`); `missing_paths`
  entries are, post-WP1, resolved strings relative to `project_root` (e.g.
  `"kitty-specs/<slug>/contracts/"`) — a form `_normalize_path_token`'s plain
  slash-strip cannot turn into a `feature_dir`-relative one by itself (it has no
  `feature_dir` prefix to strip and performs no relative-path computation). Rather
  than comparing basenames/last-path-components (which cannot distinguish two future
  dual-declared tokens sharing a final segment, e.g. a hypothetical `docs/contracts`
  optional artifact vs. an unrelated `api/contracts` declared path — spec.md's own
  Key Entities wording suggests exactly this comparable-token form), normalize
  **both sides relative to `feature_dir`, slash-stripped**, consuming WP1's new
  `PathValidationResult.missing_paths_feature_relative` field (see WP1 above) rather
  than re-deriving a relative path from `missing_paths` here — but WP1's field is
  mixed-namespace (real `feature_dir`-relative tokens only for artifact-tagged
  entries; `project_root`-relative or unchanged-absolute placeholders for the other
  two branches — see WP1 above), so WP2 must not blindly consume the whole list as if
  every entry were `feature_dir`-relative. **Structurally exclude the placeholder
  entries first**: `evaluate_path_conventions` recomputes the same `artifact_tokens`
  set `validate_mission_paths` computes internally (`paths.py:187-192` —
  `{_normalize_path_token(name) for name in (*required, *optional)}` over
  `getattr(mission.config, "artifacts", None)`'s `.required`/`.optional`, each
  defaulted via `getattr(artifacts, "...", ()) or ()` — the identical defensive
  recipe, for the identical partial-mock-safety reason), then builds its comparison
  set only from `path_result.missing_paths_feature_relative` entries whose own
  `_normalize_path_token(token)` is a member of that recomputed `artifact_tokens` set:
  `{_normalize_path_token(t) for t in path_result.missing_paths_feature_relative if
  _normalize_path_token(t) in artifact_tokens}`. This is a structural exclusion
  (membership-tested against the mission's real declared artifact set), not reliance
  on the build/repo-root and absolute-path placeholders happening not to collide with
  a real artifact token — a future mission type's build-path convention could
  otherwise share a normalized token with a future `artifacts.optional` entry and
  silently corrupt the dedup, and this membership filter forecloses that regardless
  of what literal value WP1's placeholder branches assign. Then drop from
  `optional_missing_to_dedup` any entry whose own `_normalize_path_token(entry)` is in
  that filtered set. This closes the basename-collision risk at no added cost beyond
  one extra `artifact_tokens` recomputation, since WP1's new field is populated in the
  same loop that already knows artifact-tagging per path. Example: `"contracts"`
  (bare, `optional_missing_to_dedup`) matches
  `path_result.missing_paths_feature_relative`'s corresponding entry, also
  `"contracts"` (populated by WP1 from the declared token `"contracts/"`, and a member
  of the recomputed `artifact_tokens` set because `"contracts"` is declared under
  `artifacts.optional`) — both normalize to `"contracts"`, correctly identifying the
  same fact as `missing_paths`'s parallel (but `project_root`-relative) entry
  `"kitty-specs/<slug>/contracts/"`, without ever needing to parse that resolved
  string. This is correct for a future multi-segment token too (e.g.
  `docs/contracts`), where a basename-only match would have collided.
- **Propagation mechanism (pinned, not left to WP2's judgment)**: because the return
  arity cannot change, and `collect_feature_summary` binds `missing_optional` once
  and reuses that list object for both `build_warnings(...)` and the
  `AcceptanceSummary(optional_missing=missing_optional, ...)` construction, the call
  site in `acceptance/__init__.py:1049-1058` passes
  `optional_missing_to_dedup=missing_optional` into `evaluate_path_conventions`
  **before** the `build_warnings(...)` call that currently follows it, so the mutated
  list is what `build_warnings` and the later `AcceptanceSummary(...)` construction
  both see. **The mutation fires ONLY inside the `if strict_metadata:` branch** of
  `evaluate_path_conventions` (`summary_core.py:146-147`, the condition at `:146` and
  its body at `:147`) — never unconditionally before that branch. This matches
  spec.md's own Acceptance Scenario 1 for FR-002, which is
  scoped explicitly to "default (strict) mode": in lenient mode, `validate_mission_paths`
  is still called non-strict and `path_violations` is always `[]` (the function's
  `strict_metadata=False` branch returns `format_warnings()`'s text instead), so the
  double-*severity* contradiction FR-002 fixes cannot occur there — only a cosmetic
  double-mention would be theoretically possible, and this mission does not touch it.
  Concretely: `optional_missing_to_dedup` is threaded into the call unconditionally
  (the parameter is always passed the same list reference), but the *mutation logic
  inside* `evaluate_path_conventions` only executes the dedup when it is also about to
  return the `strict_metadata=True` branch's `path_violations`; the `strict_metadata=False`
  branch returns before ever consulting `optional_missing_to_dedup`.
- `path_violations` keeps rendering the **full, unfiltered** `missing_paths` inside
  `format_errors()` exactly as today — only `optional_missing` loses the redundant
  entry. This is what keeps `path_violations` (not `optional_missing`) as the side
  that wins, and keeps `AcceptanceSummary.ok` unchanged for today's fixture (C-001).

**Dedup print removal**: `cli/commands/accept.py:476-481`'s
`if summary.optional_missing: console.print("\n[yellow]Optional artifacts missing:...")`
block is deleted outright — `_print_acceptance_warnings` (called immediately above
it) already renders the identical "Optional artifacts missing: ..." line from
`summary.warnings` whenever `missing_optional` is non-empty (via `build_warnings`).
This is the FR-003 fix and is independent of the FR-002 interface change (it removes
a redundant *print*, not a redundant *fact* — it applies even for a token declared
only under `artifacts.optional`, the common non-`contracts/` case, per spec's Edge
Cases).

**Scope boundary held**: does NOT extend to `research`'s `data/` (declared under both
`artifacts.optional` and `paths.data`) — `_missing_artifacts` never checks `data/`,
so no double-report defect exists there today; WP2 touches no `research`-specific
code path.

**Covers**: FR-002, FR-003, SC-002, SC-006, User Story 2 (all four Acceptance
Scenarios).

**Revert test** (must fail if WP2 is reverted): a test on a `software-dev`-shaped
fixture (or the real `collect_feature_summary` entry point per FR-007) with
`contracts/` missing, strict mode, asserting: (a) `"contracts"` appears in exactly
one of `AcceptanceSummary.optional_missing` / the rendered `path_violations` text,
never both, and (b) `AcceptanceSummary.ok is False` (the C-001 pass/fail-boundary
guard — Scenario 2 of User Story 2 made concrete). A second, narrower test asserts
`_print_acceptance_summary`'s console output contains the literal substring
`"Optional artifacts missing"` at most once (FR-003 / Scenario 3 of User Story 2,
directly targeting the removed print block). A third, lenient-mode test on the same
dual-declared fixture (`strict_metadata=False`) asserts `AcceptanceSummary.optional_missing`
is left **untouched** by the dedup (still contains `"contracts"`) — pinning that the
mutation fires only inside the strict-mode branch, per the Propagation mechanism note
above, and giving spec.md's Acceptance Scenario 1 strict-mode scoping an explicit
lenient-mode counterpart-check rather than leaving it implicit.

### WP3 — honest remediation text + flag discoverability

**Depends on WP1 + WP2 landing first** (the wording must describe the post-dedup,
resolved-path world).

**Files**: `src/specify_cli/validators/paths.py` (`format_errors`, `:61-78`,
+ `suggest_directory_creation`'s output ordering as consumed by `format_errors`),
`src/specify_cli/cli/commands/accept.py` (`--lenient`'s `typer.Option` help string,
`:643`).

**Design (combining three of #3730's four candidate directions, per the tracer's
settled decision — not re-derived here)**:
- `format_errors()` gets **no new parameter**. `grep -rn '\.format_errors(' src/`
  confirms exactly two call sites in the whole codebase — `PathValidationError.__init__`
  (`paths.py:24`, reached only via `validate_mission_paths(..., strict=True)`) and
  `evaluate_path_conventions`'s `if strict_metadata:` branch (`summary_core.py:147`,
  the function's *other* branch calls `format_warnings()` instead, never
  `format_errors()`) — both already reachable only when the caller is in the
  strict/blocking branch. Since `format_errors()` is by construction only ever invoked
  in the strict/blocking context (that is the entire reason the strict/lenient split
  exists as two separate methods), a mode-signal boolean parameter would be a
  compile-time-constant argument at every call site — an untested, unreachable `False`
  branch the charter's Sonar Expectations forbid. Instead, the new `--lenient`-pointer
  wording is added **unconditionally** to `format_errors()`'s existing trailing prose
  — no new parameter, no branch, no risk of dead/untested code.
- Replace the unconditional line `"These directories are required by the active
  mission. Create them before continuing."` with new fixed wording — unconditional in
  the sense of "always this text" (no branch on mode, since `format_errors()` is
  itself only ever reached from strict mode, per above) but honest in content: it (a)
  does not claim an unconditional requirement, and (b) names `--lenient` as a remedy
  **before** the `mkdir -p` suggestion listed above it, with `mkdir -p` explicitly
  marked secondary/optional — concretely following spec's own AC4 wording pattern:
  state the `--lenient` pointer first, then "... or, if you want to adopt the
  convention: `mkdir -p ...`" for each suggestion already present in
  `self.suggestions`.
- `suggest_directory_creation`'s list content and `format_warnings()`'s consumption
  of it are **untouched** — WP3 only changes the trailing prose
  `format_errors()` appends after the shared `suggestions` list, never the list
  itself, per the Edge Cases guard against #2330 (SPEC-GOV-003's confirmed
  remediation).
- `accept.py:643`'s `--lenient` `typer.Option(..., help="Skip strict metadata
  validation")` is widened to also name path-convention enforcement explicitly (FR-006
  / SC-003's `--help` requirement).

**Covers**: FR-004, FR-005, FR-006, FR-008 (regression guard only — `--lenient`'s
existing downgrade-to-warning behavior is exercised by the pinned lenient test and
must keep passing unmodified), NFR-003 (Terminology canon compliance — the new
`format_errors()` trailing prose and the widened `--lenient` help string use
"Mission"/"mission" only, never "feature"/"feature*"; independently enforced by
`tests/architectural/test_no_legacy_terminology.py` — this test carries only
`architectural`/`git_repo`/`docs_scoped` pytest markers, so it is invoked by path only
inside `fast-tests-docs` (`ci-quality.yml:1886`, gated on the `docs` filter, which this
diff does not touch) and is otherwise picked up solely by `arch-adversarial`
(`ci-quality.yml:2082-2115`), the always-on, unconditional job (sharded by
`arch_shard_1/2/3` markers, no dorny filter-group `if:` gate) that an in-repo comment
(`ci-quality.yml:1928-1930`) confirms is where the `architectural`-marked shard was
extracted to, specifically so it would NOT be re-added to `core_misc`'s
`integration-tests-core-misc` job. So this NFR is enforced by `arch-adversarial`, not
by `core_misc`/the `governance`/`acceptance` filter membership above), SC-003, User
Story 3 (all five Acceptance Scenarios).

**Revert test** (must fail if WP3 is reverted): a test on `format_errors()`'s output
for a missing declared path in strict mode asserting (a) the string `"--lenient"`
appears in the output, (b) it appears **before** any `mkdir -p` occurrence
(string-order assertion per AC4), (c) the output does not contain an unconditional
"are required by the active mission" claim, and (d) a separate test on `--help`
output (`spec-kitty accept --help`, e.g. via `CliRunner`) asserting the `--lenient`
help string mentions "path" (path-convention wording). A companion test re-runs the
existing pinned `test_lenient_path_convention_warning_is_rendered_in_console`
scenario unmodified to confirm `format_warnings()`'s output is byte-for-byte
unaffected by WP3 (the explicit #2330 guard).

### WP4 — red-first tests, including the FR-007 repro fixture

**Named deliverable (not folded anonymously into "add tests")**: a new test file
implementing FR-007/SC-004/User Story 4's fixture — e.g.
`tests/specify_cli/acceptance/test_accept_contracts_path_repro.py` (matching the
Independent Test paragraph's own suggested filename shape). Binding per #3085's
2026-08-02 triage comment ("add a focused repro/acceptance fixture ... before
implementation"), reiterated in FR-007's own text and NFR-001.

**Concrete construction**: build a real, on-disk `software-dev` mission layout under
`tmp_path` (a real `kitty-specs/<slug>/` directory tree with `spec.md`/`plan.md`/
`tasks.md` present and `contracts/` absent — mirroring `software-dev/mission.yaml`'s
actual declared conventions) and invoke `validate_mission_paths` and
`collect_feature_summary` (or the `accept` CLI command via `CliRunner`) **directly**
— never a hand-built `PathValidationResult`/`AcceptanceSummary` stand-in, per FR-007's
explicit constraint. The fixture's docstring names: this mission
(`accept-path-remediation-honesty-01M0TWZP`), both source issues (#3730, #3085), and
the two specific functions under test (`validate_mission_paths`,
`collect_feature_summary`) — satisfying the triage comment's "owner/dependency links"
requirement without requiring a reviewer to read the implementation diff first.

**Assertions** (both defects in one fixture, per Story 4's Acceptance Scenarios):
1. The reported missing-path/suggestion string equals the resolved
   `kitty-specs/<slug>/contracts/` path, not the bare `contracts/` token (fails
   pre-WP1, passes post-WP1).
2. `"contracts"` (normalized) appears in exactly one of
   `AcceptanceSummary.optional_missing` / the rendered `path_violations` — never both
   (fails pre-WP2, passes post-WP2).
3. A `--json`-mode assertion (CLI invocation with `--json`) confirming
   `optional_missing` and `path_violations` in the JSON payload reflect the same
   single-severity resolution as the console/summary-object path — no format-specific
   drift (FR-002 Edge Case / Scenario 4 of User Story 2). (The JSON key is
   `optional_missing`, confirmed at `AcceptanceSummary.to_dict()`,
   `acceptance/__init__.py:430` — not `missing_optional`, the wording spec.md's own
   Acceptance Scenario 4 uses; that spec.md-inherited terminology slip is out of scope
   for this plan-phase fix (spec.md is gated PASSED) and is flagged here for a future
   spec correction pass.)

**Reversibility check** (part of WP4's own validation, not a separate step): confirm
by inspection/local `git stash` of WP1+WP2's diff that this fixture's first two
assertions flip from pass to fail — this is what makes it a genuine repro, not
incidental new coverage. Record the confirmation in the WP4 implementation notes
handed to review (not required to re-verify at plan time; WP1/WP2 do not exist yet
on this branch).

**Covers**: FR-007, NFR-001 (the "every FR needs a red-first test" umbrella —
satisfied per-WP by the four revert tests named above plus this fixture), User
Story 4 (all three Acceptance Scenarios).

**This WP itself has no single "revert test" of its own in the WP1/2/3 sense** — it
*is* the verification layer; its own correctness is validated by the reversibility
check above rather than by a further meta-test.

## Red-first / revert discipline — summary table

| WP | Revert test (fails if WP is reverted) | Location |
|----|----------------------------------------|----------|
| WP1 | Case A asserts `missing_paths`/`suggestions`/`warnings` contain the resolved `feature_dir`-relative path, not the bare token, for a real artifact-tagged mission fixture; Case B (build-path companion) asserts the build/repo-root branch's reported string stays `project_root`-relative and unchanged. | `tests/specify_cli/acceptance/` or `tests/agent/test_validators_unit.py` |
| WP2 | Asserts `"contracts"` surfaces through exactly one of `optional_missing`/`path_violations` AND `AcceptanceSummary.ok is False` for the dual-declared fixture; plus a console-render test asserting `"Optional artifacts missing"` prints at most once; plus a lenient-mode test on the same fixture asserting `optional_missing` is left untouched by the dedup. | `tests/specify_cli/acceptance/`, `tests/specify_cli/cli/commands/` |
| WP3 | Asserts `format_errors()` output contains `"--lenient"` before any `mkdir -p`, no unconditional "required" claim, `--help` mentions path conventions; plus an unmodified re-run of the pinned lenient-render test as the #2330 non-regression guard. | `tests/agent/test_validators_unit.py`, `tests/specify_cli/cli/commands/` |
| WP4 | The FR-007 fixture itself (`test_accept_contracts_path_repro.py`), verified red-on-pre-fix/green-on-post-fix by the reversibility check described above. | `tests/specify_cli/acceptance/test_accept_contracts_path_repro.py` (new) |

## Test strategy per Acceptance Scenario

| User Story | Scenario | WP | Test |
|---|---|---|---|
| US1 | 1 (artifact-tagged path reports resolved location) | WP1 | WP1 revert test |
| US1 | 2 (build/repo-root path reporting unchanged) | WP1 | WP1 revert test's build-path companion assertion (existing repo-root case re-asserted, not newly introduced) |
| US2 | 1 (dedup resolves to exactly one severity) | WP2 | WP2 revert test (a) |
| US2 | 2 (pass/fail boundary unchanged, `ok is False`) | WP2 | WP2 revert test (a), C-001 guard |
| US2 | 3 (no duplicate console print) | WP2 | WP2 revert test (b), console-render assertion |
| US2 | 4 (`--json` internal consistency) | WP2 + WP4 | WP4 fixture assertion 3 |
| US3 | 1 (no unconditional "required" claim) | WP3 | WP3 revert test |
| US3 | 2 (`--lenient` named as alternative) | WP3 | WP3 revert test |
| US3 | 3 (`--help` mentions path conventions) | WP3 | WP3 revert test (`--help` assertion) |
| US3 | 4 (`--lenient` before `mkdir -p`, `mkdir -p` marked secondary) | WP3 | WP3 revert test (string-order assertion) |
| US3 | 5 (pinned tests still pass unmodified) | WP3 | Re-run of the three SC-005 pinned tests, unmodified |
| US4 | 1 (fixture fails on pre-fix code) | WP4 | Reversibility check |
| US4 | 2 (fixture passes on post-fix code) | WP4 | Fixture itself, green post-WP1-WP2 |
| US4 | 3 (fixture legible without reading the diff) | WP4 | Fixture docstring naming mission/issues/functions |

## PR shape

**ONE PR for this mission** — this repo's default; `accept`/`merge` machinery assumes
one mission branch (`fix/accept-path-remediation-honesty-3730`) maps to one PR. No
evidence surfaced during planning that warrants a split: all four WPs share the same
seam, the same four files, and a strict dependency order (WP1 → WP2 → WP3, with WP4
threaded alongside each as its red-first test and closed out with the FR-007 fixture)
— splitting would only fragment a single reviewable change into artificially
sequenced PRs with no independent value at any intermediate point.

## Parallel Work Analysis

Single-agent-friendly sequencing; no genuine parallelism opportunity given the
dependency chain, so this is stated for completeness rather than as a multi-agent
plan.

### Dependency Graph

```
WP1 (resolved-path correctness)
  -> WP2 (dedup, depends on WP1's resolved-string shape for the token-normalization rule)
       -> WP3 (honest wording, depends on WP1+WP2's post-fix world)
WP4 (red-first tests) threaded alongside WP1/WP2/WP3 each, as each WP's own revert
  test; the FR-007 fixture itself lands last (needs WP1+WP2 both landed to assert
  the post-fix state) but is written red-first against pre-WP1/WP2 code first.
```

### Work Distribution

- **Sequential work**: WP1 → WP2 → WP3 must land in that order (each depends on the
  prior's output shape, as pinned in spec.md's Key Entities section).
- **Parallel streams**: none genuinely independent — this mission is small enough
  (four files, ~4 focused edits) that single-agent sequential implementation is the
  right shape; no ownership-map split is warranted.
- **Agent assignments**: N/A for this mission's size.

### Coordination Points

- **Sync schedule**: N/A (sequential single-track work).
- **Integration tests**: the WP4 FR-007 fixture is the integration point — it is the
  one test that must observe WP1 and WP2's combined effect through real entry points,
  so it is written early (red, against pre-fix code) and re-verified green only after
  both WP1 and WP2 land.

## Project Structure

### Documentation (this mission)

```
kitty-specs/accept-path-remediation-honesty-01M0TWZP/
├── plan.md                      # This file
├── spec.md                      # Complete, gated PASSED
├── tracer-approach.md           # Appended (see below)
├── tracer-design-decisions.md   # Appended (see below)
├── tracer-tooling-friction.md   # Unchanged — no new tooling friction hit during planning
├── reviews/spec.confirmed.yaml  # Read, not modified
└── tasks/                       # Populated by /spec-kitty.tasks (next phase, not this one)
```

No `research.md`, `data-model.md`, `quickstart.md`, or `contracts/` outputs are
produced by this plan — this mission has no new data model or API contract; the
"Key Entities" already fully specified in `spec.md` are existing code structures
(`PathValidationResult`, `AcceptanceSummary`) being modified, not new entities
requiring a `data-model.md`.

### Source Code (repository root)

```
src/specify_cli/
├── validators/
│   └── paths.py            # WP1 (validate_mission_paths), WP3 (format_errors)
├── acceptance/
│   ├── __init__.py         # WP2 (_missing_artifacts call site, AcceptanceSummary)
│   └── summary_core.py     # WP2 (evaluate_path_conventions)
└── cli/commands/
    └── accept.py           # WP2 (duplicate print removal), WP3 (--lenient help)

tests/
├── specify_cli/
│   ├── acceptance/
│   │   ├── test_acceptance_cores.py                  # SC-005 pinned tests live here (unmodified)
│   │   └── test_accept_contracts_path_repro.py        # WP4 new FR-007 fixture
│   └── cli/commands/
│       └── test_accept_warnings_render.py             # SC-005 pinned test lives here (unmodified)
├── agent/
│   └── test_validators_unit.py                        # WP1/WP3 unit tests likely land here
└── characterization/
    └── test_trio_json_envelope.py                     # Baseline surface, re-run not edited
```

**Structure Decision**: Single project, existing layout. No new directories. All
edits are in-place modifications to the four files named in Blast radius, plus one
new test file (WP4's fixture) and additions to the existing test files listed above.

## Complexity Tracking

N/A — no Constitution Check violations. Single project, no new dependencies, no new
abstraction layers. WP2's interface change (an additive, defaulted parameter with a
documented in-place-mutation side effect) is a deliberate, spec-pinned departure from
`summary_core.py`'s pure-transform convention, not an architectural violation — it is
called out explicitly in WP2's docstring per the spec's own instruction so a reviewer
cannot mistake it for an unintended accident.

## Maintainer requirement cross-check

#3085's 2026-08-02 triage comment ("add a focused repro/acceptance fixture ...
before implementation") is satisfied by WP4's named, concrete fixture file
(`tests/specify_cli/acceptance/test_accept_contracts_path_repro.py`) — not implicitly
covered by "add tests" language anywhere else in this plan. This is stated here a
second time (beyond WP4's own section) because the maintainer requirement is binding
and must not be discoverable only by reading WP4's prose closely.
