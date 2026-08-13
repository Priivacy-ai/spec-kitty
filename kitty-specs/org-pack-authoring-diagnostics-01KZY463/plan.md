# Implementation Plan: Org-Pack Authoring Diagnostics

**Branch**: `feat/org-pack-authoring-diagnostics-3387` | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/org-pack-authoring-diagnostics-01KZY463/spec.md`,
narrowed for FR-001 by the binding operator ruling
[`reviews/spec.ruling.md`](./reviews/spec.ruling.md) (2026-08-13). This plan treats the ruling,
not the spec's original FR-001 prose, as FR-001's acceptance bar.

## Summary

Four independently-scoped org-pack authoring diagnostics land in `pack_validate`'s existing
`ValidationResult` surface, closing silent-success gaps where the pack loads, `pack validate`
reports clean, and part of the pack is inert or destructive at runtime:

- **FR-001** (documentation-only, per the binding ruling): correct
  `docs/guides/how-to/governance/create-an-org-doctrine-pack.md` at `:65`/`:140` from
  `*.contract.yaml` to `*.step-contract.yaml`, and cite ADR `2026-08-13-1` so the reader learns
  the whole step-contract surface is slated for retirement. No code.
- **FR-002**: `pack validate` additionally runs `AgentProfileRepository`'s real load/merge path
  against the pack's `agent_profiles/` directory and surfaces any `skipped_profiles()` entries as
  `ValidationIssue(category="profile_skipped")`, deduplicated against files that already produced
  a `schema_invalid` error.
- **FR-003**: `pack_validator._scan_files` recurses (`rglob`) for `"assets"` as well as
  `"styleguides"`, matching `AssetRepository._project_scan`'s existing `rglob` behavior.
- **FR-004**: `validate_pack` gains a keyword-only `check_drg_root: bool = True` parameter and a
  new check: a pack with `drg/*.graph.yaml` fragments and no pack-root `*.graph.yaml` gets a
  `category="drg_root_graph_missing"` error, because the runtime
  (`src/charter/_drg_helpers.py:load_validated_graph`) reads the pack root, not `drg/`. The
  assembler's internal round-trip check and `doctrine org validate`'s onboarding-scaffold check
  both pass `check_drg_root=False`, since their own architecture guarantees the drg/-fragments-
  only shape regardless of authoring correctness.

The entire change lands inside the CLI layer (`src/specify_cli/doctrine/`); it reads from, but
never modifies, the doctrine-model layer (`src/doctrine/agent_profiles/repository.py`,
`src/doctrine/assets/repository.py`). No new modules, no new CLI command or flag, no schema
change, no runtime DRG-carrier change.

## Technical Context

**Language/Version**: Python (`requires-python = ">=3.11"` in `pyproject.toml`; local dev
toolchain pinned to `3.11.15` via `.python-version`; `ruff`'s `target-version = "py311"`).
Managed with `uv` (`uv sync`, `uv run …`) — no bare `pip`/`venv` workflow.
**Primary Dependencies**: `typer>=0.24.1` (CLI framework — `pack_validate`/`org_validate` are
Typer commands, unchanged signatures), `pydantic>=2.0` (`ValidationError`, the artifact schema
models this touches read but does not modify), `ruamel.yaml>=0.18.0` (YAML parsing, already used
by `pack_validator.py`'s `_yaml_parser()`), `rich>=14.3.3` (console rendering via
`render_validation_result`, untouched). Dev/test-only: `pytest>=9.0.3,<9.1`,
`pytest-xdist>=3.8.0`, `ruff>=0.4.0`, `mypy>=1.10.0` (strict mode, `pyproject.toml`
`[tool.mypy] strict = true`), `bandit>=1.7.0`, `pip-audit>=2.7.0`.
**Storage**: N/A — no persistence layer touched; all inputs are pack directories on the local
filesystem, all outputs are in-memory `ValidationIssue`/`ValidationResult` dataclasses (or their
JSON/Rich rendering).
**Testing**: pytest, targeted-package mode per the charter's binding Testing Requirements section
and the spec's C-004 — not a full `pytest tests/` run. The four targeted files are
`tests/specify_cli/doctrine/test_pack_validator.py`,
`tests/doctrine/test_agent_profile_model_field.py`,
`tests/specify_cli/doctrine/test_pack_assembler.py`, `tests/cli/test_doctrine_org_commands.py`
(C-004). FR-001 contributes no test surface (documentation-only, ruling-confirmed).
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows 10+, per the charter's Deployment
and Constraints section) — this mission touches pure Python + one Markdown file, no
platform-specific code paths.
**Project Type**: Single project — Python CLI package (`spec-kitty-cli`), no frontend/mobile
surface in scope.
**Performance Goals**: No new perf-sensitive path. `pack validate` must still complete in
`<2s` for typical projects (charter's Performance and Scale section) — FR-002's added
`AgentProfileRepository` construction is bounded by the same `agent_profiles/` directory
`pack validate` already schema-scans, so no new I/O class is introduced, only one additional
pass over files already being read.
**Constraints**: C-001 (FR-001 is documentation-only, touches no code), C-002 (no
`src/charter/_drg_helpers.py` change), C-003 (no fifth surface — exactly the four FRs), C-004
(targeted test packages, not the full suite).
**Scale/Scope**: Three source files touched for code (`pack_validator.py`, `pack_assembler.py`,
`doctrine.py`), one doc file for FR-001, four existing test files extended — no new files, no
new package.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after this design; no violations found —
Complexity Tracking table is empty by design (see below).*

- **Governing Principles — Architectural alignment**: this change stays inside the CLI layer
  (`src/specify_cli/doctrine/`) and respects the `kernel <- doctrine <- charter <- specify_cli`
  layering — it reads `src/doctrine/agent_profiles/repository.py` and
  `src/doctrine/assets/repository.py` (both already CLI-importable, downward reads) but writes
  to neither. PASS.
- **Governing Principles — Single canonical authority**: FR-002 reuses
  `AgentProfileRepository.skipped_profiles()` directly rather than hand-rolling a second
  skip-detection heuristic (AC-4). FR-003 reuses `AssetRepository`'s own documented `rglob`
  rationale rather than inventing a new recursion rule. PASS.
- **Standing Order #2 (campsite cleaning)**: see "Campsite-Clean Scope" below — scoped to
  domain-matched debt in the three touched files, explicitly excluding `snapshot.py`'s
  `_ARTIFACT_BUCKETS` (ruling-excluded, different domain). PASS, scope recorded.
- **Standing Order #3 (mission tracer files)**: seeded this phase — see "Tracer Files" below.
  PASS.
- **Standing Order #4 (test remediation, red-first)**: see "The Baseline" below — this mission
  classifies pre-existing red before attributing any new red to itself. PASS, procedure recorded.
- **Sonar Expectations — complexity ceiling 15**: `validate_pack()` is already long
  (`pack_validator.py`'s own module docstring and `_scan_artifact_directory`'s docstring both
  record a prior extraction to stay under ruff's C901 limit). FR-002 and FR-004 each add a new,
  small, named helper function (`_check_profile_skipped_diagnostics`,
  `_check_drg_root_graph_missing`) called once from `validate_pack()`, rather than inlining new
  branches into the orchestration function itself — see "The Seam" below. PASS by construction;
  no Complexity Tracking entry needed.
- **Testing Requirements — targeted test packages**: C-004 and this plan's "The Gate Set" section
  bind validation to the four named files, not `pytest tests/`. PASS.

## The Seam

This mission's entire code diff lands in the CLI layer:

- `src/specify_cli/doctrine/pack_validator.py` — FR-002, FR-003, FR-004's new checks; the
  `check_drg_root` parameter.
- `src/specify_cli/doctrine/pack_assembler.py` — one call-site edit (`validate_pack(output_dir,
  check_drg_root=False)` at the existing `:335` call).
- `src/specify_cli/cli/commands/doctrine.py` — one call-site edit (`validate_pack(pack_path,
  check_drg_root=False)` at `org_validate`'s existing `:966` call).

It is **not** a kernel change and **not** a `src/doctrine/` (doctrine-model layer) change. FR-002
and FR-004 **read from** `src/doctrine/agent_profiles/repository.py`
(`AgentProfileRepository.skipped_profiles()`, `AgentProfileRepository.__init__`'s `org_dirs`
parameter) and, for FR-003, the *rationale* documented in
`src/doctrine/assets/repository.py:18-22`/`:130-132` (`AssetRepository._project_scan`) — but
neither doctrine-layer file is modified. No new modules are introduced anywhere: all new logic
extends the three files named above.

Because `pack_validator.py`'s own docstring already records that `validate_pack()` was extracted
once to stay under ruff's C901 / Sonar S3776 complexity-15 ceiling (see `_scan_artifact_directory`
and the DRG/asset passes already factored into `_validate_drg` / `_validate_asset_manifests`),
FR-002's and FR-004's new checks follow the **same extract-a-helper discipline**: each is a small,
named, single-purpose function (`_check_profile_skipped_diagnostics`,
`_check_drg_root_graph_missing`) called exactly once from `validate_pack()`, mirroring the
existing `_validate_drg` / `_validate_asset_manifests` seam rather than growing
`validate_pack()`'s own body. FR-003 is not a new branch at all — it is a one-clause widening of
`_scan_files`'s existing `directory.name == "styleguides"` condition to
`directory.name in {"styleguides", "assets"}`.

## What Is Generated, And By Which Command

`scripts/generate_schemas.py --check` regenerates the Pydantic-model-derived YAML schemas under
`src/doctrine/schemas/` from the Pydantic models in `src/doctrine/*/models.py` (verified: the
script's own docstring states "The Pydantic models in `src/doctrine/*/models.py` are the single
source of truth" and the registry maps model classes under that tree to schema files). This
mission's changes do **not** touch that surface: `ValidationIssue` and `ValidationResult`
(`src/specify_cli/doctrine/pack_validator.py:94-149`) are **plain `@dataclass`es in the CLI
layer** (`src/specify_cli/doctrine/`), not Pydantic models under `src/doctrine/`, and neither is
in `scripts/generate_schemas.py`'s registry. Adding a new string value to `ValidationIssue`'s
free-form `category: str | None` field (`profile_skipped`, `drg_root_graph_missing`) is not a
schema-shape change in the generated sense — it's a new value inside an already-untyped `str`
field, the same mechanism every existing category (`schema_invalid`, `duplicate_id`,
`asset_path_escape`, …) already uses. The doctrine-schema-freshness CI gate
(`uv run python scripts/generate_schemas.py --check`, `.github/workflows/ci-quality.yml:655`)
therefore applies as a standing CI gate but is expected to be a **no-op** for this diff — no
`src/doctrine/*/models.py` file changes, so no schema regeneration is triggered.

## Contract Movement — Explicitly Preserved, None Versioned

`ValidationResult.to_dict()`'s top-level shape (`src/specify_cli/doctrine/pack_validator.py:144-149`)
stays exactly `{ok, errors, advisories}` for all four FRs — **no new top-level JSON key** is
introduced anywhere in this mission (the spec is explicit that a standalone `skipped_profiles`
array is rejected). New information rides the existing `ValidationIssue.category` field with two
new string values: `profile_skipped` (FR-002) and `drg_root_graph_missing` (FR-004, name chosen
per spec's suggestion in User Story 4 AC-1 and confirmed here as the plan's category name).

FR-by-FR contract-preservation statement:

- **FR-001**: touches no contract at all — documentation only, no JSON payload, no schema.
- **FR-002**: no new top-level JSON key. No doctrine schema touched (`SkippedProfile` in
  `src/doctrine/agent_profiles/diagnostics.py` is read via `skipped_profiles()`, not modified,
  not re-serialized as its own JSON shape — it is translated into an existing `ValidationIssue`).
  No mission step contract, no action index, no orchestrator-api surface, no vendored
  `spec-kitty-events` package touched.
- **FR-003**: pure widening of an internal file-scan glob; `ValidationIssue`'s shape is
  unaffected — a nested asset manifest surfaces through the *existing*
  `schema_invalid`/`asset_mime_invalid`/`asset_path_escape` categories, no new category value.
- **FR-004**: one new category value (`drg_root_graph_missing`) inside the existing `errors`
  array; `validate_pack()`'s Python signature gains a keyword-only parameter
  (`check_drg_root: bool = True`) — an additive, backward-compatible signature change (every
  existing positional/keyword caller with zero `check_drg_root` usage keeps working unchanged).
  No CLI flag is added: `pack validate`'s Typer signature
  (`src/specify_cli/cli/commands/doctrine.py:349-359`) is untouched: the CLI-facing behavior is
  "always validate as a full-pack author," so it always gets the function's default `True` with
  no new `--` option surfaced to authors.

## Migration Chain

Not touched by this mission at all. No new persisted state, no schema version bump, no
`src/specify_cli/upgrade/migrations/` file is added or edited. There is nothing atomic,
idempotent, dry-run-capable, or self-recovering to plan for here — `pack validate` is a
stateless, read-only command over a pack directory; FR-002/003/004 add new read-only checks to
that same stateless pass. `validate_pack()` writes nothing to disk in any FR (the
`pack_assembler.py` caller's own rollback-on-failure logic at `:335-350` is pre-existing and
unmodified — this mission changes what `validate_pack()` decides, not what
`assemble_pack()` does with the verdict).

## The Gate Set

For each gate: whether it applies to this mission's diff, and why.

- **`make lint` (ruff)** — Applies. Local discipline; run before every commit. New code
  (`_check_profile_skipped_diagnostics`, `_check_drg_root_graph_missing`, the widened
  `_scan_files` condition, the `check_drg_root` parameter) must pass ruff's full selected rule
  set (`E`, `F`, `W`, `C90`, `C4`, `ARG`, `B`, `SIM`, `UP`, `ASYNC`, `S`, `TID251`) with zero
  suppressions per the charter's Code Style section.
- **Targeted pytest shards (spec's C-004)** — Applies; this is the mission's actual validation
  surface: `tests/specify_cli/doctrine/test_pack_validator.py` (FR-002/003/004's core new
  behavior), `tests/doctrine/test_agent_profile_model_field.py` (model-layer fixtures backing
  FR-002's synthetic skip scenario — no new runtime code there, per C-004's own annotation),
  `tests/specify_cli/doctrine/test_pack_assembler.py` (FR-004 AC-6, the assembler carve-out),
  `tests/cli/test_doctrine_org_commands.py` (FR-004 AC-7, the `org_validate` carve-out).
- **Kernel coverage ≥90% (`kernel-tests` CI job, `.github/workflows/ci-quality.yml:1077`, `--cov=src/kernel`)**
  — Does NOT apply. Nothing in `tests/kernel/` or `src/kernel/` is touched by any FR.
- **Mission-loader coverage ≥90% (`mission-loader-coverage` CI job, `:1522`, covers
  `src/specify_cli/mission_loader/**`, `events/**`, `paths/**`, `saas_client/**`, `identity/**`,
  `task_utils/**`)** — Does NOT apply. None of those paths are touched by any FR.
- **`fast-tests-doctrine` (`--cov=doctrine --cov=charter`, `:1138`)** — Applies as a standing CI
  job (it always runs), but expected to show **zero new-code delta** attributable to this
  mission: this mission reads `src/doctrine/agent_profiles/repository.py` and
  `src/doctrine/assets/repository.py` but adds/edits no line inside `src/doctrine/` or
  `src/charter/`, so it contributes no new coverage obligation to that job even though the job
  itself is unconditional.
- **Commitlint** — Applies to every commit (conventional commits, imperative subject, ≤72 chars
  on the summary line) — enforced by `.github/workflows/ci-quality.yml`'s `commitlint` step.
- **Markdown lint (`markdownlint-cli2`)** — Applies: FR-001 edits
  `docs/guides/how-to/governance/create-an-org-doctrine-pack.md`, a Markdown file, and the
  `markdownlint` CI step runs `markdownlint-cli2` against changed Markdown.
- **Architecture/docs consistency (`docs-freshness` workflow)** — Mostly does NOT apply (no new
  CLI command, no new slash command, no new doc cross-reference beyond the one guide edit), with
  **one concrete sub-check that DOES fire and must be satisfied, not exempted**: the
  **Relative body-link gate** (`scripts/docs/relative_link_fixer.py --check`,
  `.github/workflows/docs-freshness.yml`) checks that every relative Markdown link
  (`[text](path)`) in a changed doc resolves. The ADR FR-001 must cite —
  `docs/adr/3.x/2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md`
  — **does not exist on this branch**: it ships only inside unmerged PR #3378 (verified: `find
  docs/adr/3.x -iname "*retire-legacy-step-contract*"` returns nothing on this checkout).
  **Decision**: FR-001 cites the ADR by ID and title in **plain prose** (e.g. "see ADR
  `2026-08-13-1`, *Built-in mission subtree stays nested; retire legacy step contracts*
  (Accepted)"), not as a Markdown relative link, so the link-resolution gate has nothing to
  resolve and cannot red on a target that will legitimately land later via a different PR. The
  **Structural docs lint** and **description-length gate** also apply mechanically to the
  touched file but require no content change beyond bumping the existing `updated:` frontmatter
  field (currently `'2026-07-21'`) to `2026-08-13` per the charter's `docs-freshness-sla`
  styleguide ("pages without a freshness date are treated as stale").
- **Doctrine schema freshness (`scripts/generate_schemas.py --check`)** — Applies as a standing
  CI gate, expected **no-op** — see "What Is Generated" above.
- **Contextive glossary** — Checked directly: `grep -rn "schema_invalid\|duplicate_id\|asset_path_escape\|drg_dangling_edge"` across `src/specify_cli/.contextive/*.yml`, `src/glossary/.contextive.yml`, and `docs/context/*.md` returns **zero hits** — none of the *existing* `ValidationIssue.category` string values are glossary-tracked terms. This mission's two new category values (`profile_skipped`, `drg_root_graph_missing`) follow the same established precedent: **no glossary entry is needed**, consistent with how every prior category value was introduced, not a new exemption invented for this mission.
- **TID251 banned-API lint** — Applies, standard Python lint gate
  (`.github/workflows/ci-quality.yml:883-894`, `ruff check src tests --select TID251`); no known
  banned import is introduced by this diff (only stdlib `pathlib`, existing `doctrine.*` package
  imports already used elsewhere in `pack_validator.py`).
- **Typer JSON error surface gate** — Checked directly, does **NOT** apply. The gate found
  (`tests/agent/test_json_group_typer_surface.py`) is scoped specifically to
  `specify_cli.orchestrator_api.commands`'s `_JSONErrorGroup` shim — it asserts that invoking the
  `orchestrator-api` Typer group with **no subcommand** still emits a structured JSON error
  envelope (`{ok/success: false, error: ...}`), guarding against a typer-version-drift regression
  in that group's exception-capture shim. It does not validate the *content* shape of any
  individual command's successful `--json` payload. This mission adds no CLI flag or command
  signature change (`pack_validate`'s Typer signature at `doctrine.py:349-359` is untouched), and
  `pack validate --json`'s payload gaining two new `category` string values inside its existing
  `errors`/`advisories` arrays is not in this gate's scope at all — it is covered instead by the
  targeted pytest shard (`test_pack_validator.py`), not by the Typer error-envelope gate.
- **`patch()` target validation (`scripts/check_patch_targets.py`, CI step
  `.github/workflows/ci-quality.yml:941`)** — Applies: this script statically extracts every
  `patch("a.b.c.attr")` string in `tests/` and asserts the module portion imports and the
  attribute exists on it. Checked directly: `pack_validator.py`'s existing pattern is **lazy,
  function-local imports** (e.g. `_artifact_schema_registry()` imports `AgentProfile` etc. inside
  the function body, not at module scope) — there is **no existing precedent** for patching a
  `pack_validator.py`-reexported doctrine symbol (`grep` across `tests/` for
  `patch(".*AgentProfileRepository` / `patch(".*pack_validator` returns nothing). FR-002's new
  helper will do the same lazy, function-local `from doctrine.agent_profiles.repository import
  AgentProfileRepository` inside `_check_profile_skipped_diagnostics` — since that import is
  **not** a module-level binding of `pack_validator.py`, any new test that needs to substitute
  the repository must patch the **source location**,
  `"doctrine.agent_profiles.repository.AgentProfileRepository"` (or construct a real
  fixture pack directory and let the real repository run, which is what this plan recommends —
  see FR-002's WP notes), **not** a nonexistent
  `"specify_cli.doctrine.pack_validator.AgentProfileRepository"` alias, which
  `check_patch_targets.py` would correctly reject as unresolvable.
- **Bandit** — Applies, standard security scan (`lint` job); no new subprocess/eval/network
  surface is introduced.
- **pip-audit** — Applies as a standing CI gate; this mission adds no new dependency (no
  `pyproject.toml` edit), so expected no-op.
- **`uv.lock` freshness (`uv-lock-check` CI job, `:4025`)** — Applies as a standing gate;
  expected no-op, no dependency changes anywhere in this mission.
- **SonarCloud Quality Gate** — Applies; new-code coverage is the dominant factor given the
  mccabe/complexity-15 ceiling and the charter's "every new branch/helper needs tests" rule.
  `_check_profile_skipped_diagnostics` and `_check_drg_root_graph_missing` are each pure,
  testable extractions (deterministic inputs — a pack directory — deterministic outputs — a
  list of `ValidationIssue`), and each acceptance criterion in FR-002/FR-003/FR-004 maps to a
  narrow test exercising that exact helper's branch, per the Sonar Expectations charter section.

## The Baseline

`main` carries approximately 23 known-red tests and 2 errors (issue #3284) and a shared pytest
test-venv lock that can time out (issue #3283) — these are **known baseline facts, not findings
this mission produces**. Per the charter's red-main-release-discipline standing order and the
CLAUDE.md "Test-run baseline-red gotcha," this mission tells pre-existing red from introduced
red **before the first functional change lands**, using this concrete procedure:

1. Before any FR-002/003/004 code edit, run the four C-004-targeted files against the current
   pre-change HEAD (this branch's tip, which carries only the reviewed spec + this plan, no
   functional diff yet):
   `uv run pytest tests/specify_cli/doctrine/test_pack_validator.py
   tests/doctrine/test_agent_profile_model_field.py
   tests/specify_cli/doctrine/test_pack_assembler.py
   tests/cli/test_doctrine_org_commands.py -q`
2. Record the pass/fail/error set from step 1 as the mission's **local baseline** (distinct from
   and narrower than the repo-wide ~23/2 figure above — the baseline that matters here is scoped
   to exactly the four targeted files, since that is the only surface this mission's acceptance
   criteria touch).
3. After each FR's implementation, re-run the same four files. **Only a test that was green in
   step 1 and red after the change is attributable to this mission.** A test red in both runs is
   pre-existing and is not "fixed" as part of this mission's scope (per C-003, no fifth surface)
   unless it is directly one of the acceptance-criteria regression tests this mission is adding
   (in which case it is red-by-design until the corresponding FR lands, not a baseline red).
4. This procedure is run once per FR (or once for the FR-002+003+004 combined lane, if
   implemented as a single lane per "Chokepoint" below) — not once globally — so a reviewer can
   trace exactly which FR's change flipped which test.

This is not "the suite is red" reported as a finding; it is the documented pre-check that makes
later red attributable.

## Campsite-Clean Scope

Per Charter Standing Order #2, campsite-cleaning is scoped to **domain-matched debt** in the
three files this mission's functional change touches — a distinct, behaviour-preserving first
commit per file, before the functional edit in that file:

- **`pack_validator.py`**: candidate domain-matched cleanup is any small, already-present
  Sonar/complexity finding directly in `validate_pack()`, `_scan_files()`, or the DRG-validation
  region this mission is about to extend — e.g., if `validate_pack()` is found to sit close to
  the complexity-15 ceiling once instrumented, a preparatory extraction (in the same style as the
  existing `_validate_drg`/`_validate_asset_manifests` split) is in-scope campsite work,
  independent of and preceding FR-002/004's own new helpers.
- **`pack_assembler.py`** and **`doctrine.py`**: touched only for FR-004's Reflexivity carve-outs
  — a single-call-site keyword-argument addition each
  (`validate_pack(output_dir, check_drg_root=False)` and
  `validate_pack(pack_path, check_drg_root=False)`). This is too narrow a touch surface to expect
  meaningful pre-existing debt at exactly that line; no campsite work is anticipated here beyond
  the one-line edit itself, and none should be manufactured to satisfy the standing order —
  Locality of Change (`DIRECTIVE_024`) is the brake on inventing scope.

**Explicitly excluded, named so a reviewer does not file it as a missed opportunity**:
`snapshot.py`'s dead `_ARTIFACT_BUCKETS` table is **not** campsite-clean scope for this mission.
The binding operator ruling (`reviews/spec.ruling.md`) states this explicitly: it is genuinely
dead code, the finding stands, but it belongs to ADR `2026-08-13-1`'s retirement work (a
different domain — the legacy step-contract surface, not org-pack-authoring-diagnostics), not to
any file this mission's functional change actually touches. `snapshot.py` is not edited by this
mission at all.

## Tracer Files

`tracer-tooling-friction.md` already exists (seeded during the spec phase, recording the
`spec-commit` protected-branch refusal — SK-12/SK-13 corroboration). This plan phase seeds the
two remaining tracer files:

- `tracer-approach.md` — high-level approach: CLI-layer-only additive diagnostics, no runtime
  carrier changes, plus the citation-drift lesson from the spec phase (verify, don't trust,
  reported line numbers — the `snapshot.py` `_ARTIFACT_BUCKETS` vs `_count_artifacts`
  correction).
- `tracer-design-decisions.md` — the FR-001 re-scope ruling (documentation-only, ADR-cited, no
  code) and the `check_drg_root` keyword-only-parameter decision (default `True` for
  author-facing validation, `False` at the two call sites whose own architecture guarantees the
  drg/-fragments-only shape), plus the `profile_skipped` uniform-error-severity decision (see
  below) as a third item worth recording, since none of these three are self-evident from the
  spec text alone at implementation time.

Both are written as part of this plan phase (see files alongside `plan.md`).

## Topology

`meta.json` already reads `"topology": "lanes"` — irreversible, already set, not revisited here.
Work packages below are structured to fit a lanes topology (independent git worktrees per lane,
merged before the mission PR).

## Chokepoint

`pack_validator.py` is touched by **FR-002, FR-003, and FR-004 together** — all three land in the
same file, so they cannot be split into fully-parallel lanes without a same-file collision. This
plan resolves the chokepoint by treating FR-002+FR-003+FR-004 as **one lane** (Lane B below),
sequenced internally in the low-risk-to-high-risk order FR-003 (one-clause `_scan_files` widening)
→ FR-002 (new helper + one call site) → FR-004 (new helper + call site + signature change +
the two carve-outs in the other two files), rather than three separate lanes that would need a
merge-conflict-prone rebase against each other. FR-001 (documentation-only, zero code overlap
with anything in `pack_validator.py`) is a fully independent Lane A that can run in true parallel
with Lane B.

**Sibling-mission write-scope check (explicit, not silently assumed)**: sibling mission
`org-pack-drg-root-graph-guard-01KZY0QT` (issue #3384) is concurrently in spec phase on
`src/charter/_drg_helpers.py:87`. That file is **not** touched by this mission in any FR — C-002
explicitly forbids it, and this plan's FR-004 design (a `pack_validator.py`-only additive check)
was chosen specifically to avoid that surface. Checked directly: no overlap exists between this
mission's touched-file set (`pack_validator.py`, `pack_assembler.py`, `doctrine.py`, the one
guide `.md`) and `_drg_helpers.py`. No write-scope collision.

## Project Structure

### Documentation (this mission)

```
kitty-specs/org-pack-authoring-diagnostics-01KZY463/
├── spec.md                          # Complete, R1-R6 adversarially reviewed
├── plan.md                          # This file
├── reviews/
│   ├── spec.ruling.md               # Binding operator ruling narrowing FR-001
│   └── ...                          # R1-R6 review trail (not touched by this plan)
├── tracer-tooling-friction.md       # Seeded at spec phase (spec-commit refusal, SK-12/SK-13)
├── tracer-approach.md               # Seeded this phase
├── tracer-design-decisions.md       # Seeded this phase
├── research/                        # Unused — no Phase 0 unknowns beyond spec.md's own
│                                     #   "Verified Code Surfaces" table, which already
│                                     #   supplies every file:line citation this plan needs
├── tasks/                           # Phase 2 output (/spec-kitty.tasks — not this phase)
└── tasks.md                         # Phase 2 output (not this phase)
```

No `data-model.md`, `quickstart.md`, or `contracts/` directory content is produced: this mission
introduces no new persisted data model (FR-002/004 add string values to an already-untyped
`category: str | None` field on an existing dataclass; FR-003 changes no data shape at all) and
no new external contract (no CLI flag, no schema, no API). The spec's own "Verified Code
Surfaces" table already supplies every file:line citation a Phase 0 research pass would otherwise
produce, so no separate `research.md` is generated — duplicating it here would drift from the
spec rather than add information.

### Source Code (repository root)

```
src/
├── specify_cli/
│   ├── doctrine/
│   │   ├── pack_validator.py        # FR-002, FR-003, FR-004 — the chokepoint (see above)
│   │   │                            #   - _scan_files(): widen recursion to "assets" (FR-003)
│   │   │                            #   - new: _check_profile_skipped_diagnostics() (FR-002)
│   │   │                            #   - new: _check_drg_root_graph_missing() (FR-004)
│   │   │                            #   - validate_pack(): gains check_drg_root kwarg, calls
│   │   │                            #     both new helpers (FR-002, FR-004)
│   │   └── pack_assembler.py        # FR-004 — one call-site edit at assemble_pack()'s
│   │                                #   internal validate_pack(output_dir, ...) call (:335)
│   └── cli/
│       └── commands/
│           └── doctrine.py          # FR-004 — one call-site edit at org_validate's
│                                     #   validate_pack(pack_path, ...) call (:966);
│                                     #   pack_validate (:349-372) is READ, not edited —
│                                     #   its Typer signature and default check_drg_root=True
│                                     #   behavior are unchanged
├── doctrine/
│   ├── agent_profiles/
│   │   └── repository.py            # READ ONLY — AgentProfileRepository, skipped_profiles(),
│   │                                 #   _record_skip(); FR-002's seam, never modified
│   └── assets/
│       └── repository.py            # READ ONLY — AssetRepository._project_scan's rglob
│                                     #   rationale; FR-003's behavioral target, never modified
└── charter/
    └── _drg_helpers.py              # NOT TOUCHED (C-002) — named here only to make the
                                      # boundary explicit; sibling mission #3384's surface

docs/
└── guides/how-to/governance/
    └── create-an-org-doctrine-pack.md   # FR-001 — :65 (layout tree), :140 (namespace table),
                                          #   ADR citation (plain prose, not a relative link —
                                          #   see "The Gate Set"), updated: bump to 2026-08-13

tests/
├── specify_cli/doctrine/
│   ├── test_pack_validator.py       # FR-002 (profile-skip fixtures), FR-003 (nested-asset
│   │                                 #   fixtures), FR-004 (drg-root-graph fixtures) — new
│   │                                 #   test functions per FR's acceptance criteria
│   └── test_pack_assembler.py       # FR-004 AC-6 — assert check_drg_root=False is the actual
│                                     #   parameter value at assemble_pack()'s internal call
├── doctrine/
│   └── test_agent_profile_model_field.py   # FR-002 — model-layer fixture backing the
│                                             #   synthetic post-merge-skip scenario (no new
│                                             #   runtime code here, fixture data only)
└── cli/
    └── test_doctrine_org_commands.py       # FR-004 AC-7 — assert check_drg_root=False is the
                                              #   actual parameter value at org_validate's call
```

**Structure Decision**: Single project (Python CLI package), no frontend/mobile/web split. All
functional code changes are confined to `src/specify_cli/doctrine/` and one call site each in
`src/specify_cli/doctrine/pack_assembler.py` and `src/specify_cli/cli/commands/doctrine.py` — the
CLI layer only, per "The Seam" above. The doctrine-model layer (`src/doctrine/`) and the charter
layer (`src/charter/`) are read for context but carry zero diff lines.

## Complexity Tracking

*No Charter Check violations were found — table intentionally empty.* Both new helpers
(`_check_profile_skipped_diagnostics`, `_check_drg_root_graph_missing`) are extracted from the
start (never inlined into `validate_pack()` and then split later), following the discipline
`pack_validator.py` already established for `_validate_drg`/`_validate_asset_manifests`. If
implementation reveals `validate_pack()` itself approaching the complexity-15 ceiling once the
two new helper calls are wired in, the remediation is a further mechanical extraction (e.g.
splitting the registry-scan loop from the post-scan check dispatch), not a suppression — this
would be recorded here retroactively only if it required a genuine, non-mechanical design
trade-off, which is not anticipated.

## Implementation Concern Map

### IC-01 — FR-001: Guide correction (documentation-only)

- **Purpose**: Stop the published guide from instructing authors to create
  `*.contract.yaml` step-contract files the loader (`step_contracts.py`) and validator
  (`pack_validator.py`'s own registry) have never matched; point the reader at the ADR that
  retires the whole surface.
- **Relevant requirements**: FR-001, C-001, SC-001.
- **Affected surfaces**: `docs/guides/how-to/governance/create-an-org-doctrine-pack.md` (`:65`
  layout tree, `:140` namespace table, `updated:` frontmatter bump). No code.
- **Sequencing/depends-on**: none — fully independent of IC-02..IC-04 (Lane A).
- **Risks**: The ADR file this mission cites does not exist on `main` yet (ships via unmerged PR
  #3378) — mitigated by citing it as plain prose, not a Markdown relative link (see "The Gate
  Set," Relative body-link gate). If PR #3378 merges before this mission's PR, no rework is
  needed (prose citation stays valid either way).

### IC-02 — FR-003: Asset directory recursion widening

- **Purpose**: Make `pack_validator.py`'s asset scan recurse exactly like
  `AssetRepository._project_scan` does at runtime, so a nested
  `assets/<pack>/x.asset.yaml` manifest is no longer invisible to `pack validate`.
- **Relevant requirements**: FR-003, SC-003.
- **Affected surfaces**: `pack_validator.py`'s `_scan_files()` (`:202-206`) — widen the
  recursion condition from `directory.name == "styleguides"` to
  `directory.name in {"styleguides", "assets"}`.
- **Sequencing/depends-on**: Lane B, sequenced first within the lane (smallest, lowest-risk
  change — a single-clause widening with no new function).
- **Risks**: Minimal — the existing `if not type_dir.is_dir(): continue` guard in
  `validate_pack()`'s registry loop already handles an absent `assets/` directory (AC-4);
  this change does not touch that guard.

### IC-03 — FR-002: Profile-skip diagnostics wired into `pack validate`

- **Purpose**: Surface `AgentProfileRepository`'s post-merge `skipped_profiles()` diagnostics
  directly in `pack validate`'s own output, closing the residual gap where an author must
  separately know to run `spec-kitty doctor doctrine --json`.
- **Relevant requirements**: FR-002, SC-002.
- **Affected surfaces**: `pack_validator.py` — new `_check_profile_skipped_diagnostics(pack_dir,
  already_flagged_files)` helper (constructs `AgentProfileRepository(org_dirs=[pack_dir /
  "agent_profiles"])`, treating the pack as the sole org source per the spec's requirement text;
  calls `.skipped_profiles()`; emits one `ValidationIssue(category="profile_skipped",
  severity="error", ...)` per skip not already covered by a `schema_invalid` error for the same
  file); one new call site inside `validate_pack()`, positioned immediately after the main
  registry scan loop.
- **Sequencing/depends-on**: Lane B, sequenced second within the lane (after FR-003, before
  FR-004 — a new helper plus one call site, no signature change).
- **Risks**:
  - *Dedup correctness*: the dedup set is built from `{issue.file for issue in errors if
    issue.artifact_type == "agent_profiles"}` immediately after the registry loop. This assumes
    path-string equality between the generic scan's `str(yaml_file)` (from
    `type_dir.glob(glob)`, rooted at `pack_dir / "agent_profiles"`) and the repository's own
    scan path (from `AgentProfileRepository`'s `org_dir.glob(...)`, rooted at the same
    directory) — both are unresolved `Path` objects built from the identical directory instance,
    so string equality should hold, but AC-2's regression test is the actual proof, not this
    assumption.
  - *Absent-directory safety*: verified directly (`repository.py:392-393`,
    `_load_layer`: `if not directory.exists(): return loaded`) — constructing
    `AgentProfileRepository(org_dirs=[pack_dir / "agent_profiles"])` is **already safe** when
    the directory doesn't exist; no `if type_dir.is_dir()` guard is needed before construction
    (unlike FR-003's asset case). AC-5's regression test asserts this path actually executes
    (not merely that nothing crashes) — the helper must not wrap construction in a
    swallow-everything `try/except` that would make that assertion vacuous.
  - *Severity choice*: `SkippedProfile` (`src/doctrine/agent_profiles/diagnostics.py`) carries no
    severity field of its own — this is a plan-phase design decision (severity always
    `"error"`, matching `schema_invalid`'s severity for the equivalent "profile unusable"
    outcome), recorded in `tracer-design-decisions.md` since it is not explicit in the spec text.

### IC-04 — FR-004: DRG-root-graph mismatch diagnostic + reflexivity carve-outs

- **Purpose**: Warn at authoring time when a pack's DRG content lives only under `drg/` with no
  pack-root `*.graph.yaml`, since the runtime (`_drg_helpers.py:load_validated_graph`) reads only
  the pack root — today this shape passes `pack validate` cleanly and, per sibling mission #3384,
  zeroes the action grain at runtime. Simultaneously prevent the new check from breaking the two
  known-good call sites whose own architecture guarantees this exact shape.
- **Relevant requirements**: FR-004 (all seven ACs), SC-004, C-002.
- **Affected surfaces**:
  - `pack_validator.py` — new `_check_drg_root_graph_missing(pack_dir, drg_dir) ->
    list[ValidationIssue]` helper (returns one `error`-severity, `category=
    "drg_root_graph_missing"` issue when `drg_dir.glob("*.graph.yaml")` is non-empty and
    `pack_dir.glob("*.graph.yaml")` is empty, else `[]`); `validate_pack()` gains `*,
    check_drg_root: bool = True` and calls the new helper only `if check_drg_root`, positioned
    immediately after the existing `_validate_drg` call.
  - `pack_assembler.py` — `assemble_pack()`'s internal `validate_pack(output_dir)` call (`:335`)
    becomes `validate_pack(output_dir, check_drg_root=False)`.
  - `doctrine.py` — `org_validate`'s `validate_pack(pack_path)` call (`:966`) becomes
    `validate_pack(pack_path, check_drg_root=False)`. `pack_validate`'s call (`:370`) is
    unchanged — it gets the default `True`.
- **Sequencing/depends-on**: Lane B, sequenced third/last within the lane (touches the most
  surfaces: new helper, signature change, two carve-out call sites in the other two files).
  Cannot start meaningfully before FR-002 lands in the same lane only in the sense that both
  edit `validate_pack()`'s body — sequencing them in one lane avoids a same-file merge
  collision; there is no logical/data dependency between FR-002 and FR-004 beyond that.
- **Risks**:
  - *Near-miss glob*: AC-5 requires a file like `notes.graph.yaml.bak` not to be mistaken for a
    satisfying pack-root graph — `Path.glob("*.graph.yaml")` does not match a `.bak`-suffixed
    name, so this is correct by construction, not a new pattern to get subtly wrong (spec's own
    framing, confirmed against the exact glob used).
  - *Regression on the two known call sites*: without the carve-out, `assemble_pack()`'s
    round-trip check would newly fail `test_force_dedup_prunes_duplicate_edges_via_canonical_serializer`
    (`tests/specify_cli/doctrine/test_pack_assembler.py:169`) and `org_validate`'s onboarding
    check would newly fail `test_doctrine_org_validate_accepts_valid_pack`
    (`tests/cli/test_doctrine_org_commands.py:108`) — both are pre-identified in the spec's
    Reflexivity finding and must be re-run as part of this IC's own validation, not assumed
    fixed by the carve-out alone.
