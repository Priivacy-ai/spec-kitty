# Implementation Plan: Cascade drops asset-kind targets with no report

**Branch**: `fix/cascade-asset-silent-drop-3705` | **Date**: 2026-08-24 | **Spec**: `kitty-specs/cascade-asset-silent-drop-01M0RME0/spec.md`
**Input**: Mission specification from `kitty-specs/cascade-asset-silent-drop-01M0RME0/spec.md`

All line numbers below were re-verified live against this checkout (not copied from the
spec's own citations, though they turned out to match). Re-verify again before implementation
if any drift is suspected — code moves.

## Summary

`_referenced_artifacts` (`src/charter/cascade.py:266-295`) walks the DRG forward-reference
closure and, for every reached node, drops the node silently via a bare `continue`
(`cascade.py:291-292`) when its `ArtifactKind` is not in `CHARTER_ACTIVATABLE_KINDS`
(`template`/`asset`). Nothing downstream — `CascadeActivationResult`, `NoCascadeReport`,
`DeactivationPlan`, or their three CLI renderers — ever sees that the node existed. This
mission changes `_referenced_artifacts` to return a second partition (the kind-filtered nodes,
reusing the existing `ReferencedArtifact` shape) from the *same* pass, threads it through all
three result dataclasses via each dataclass's own existing three call sites (all three already
call `_referenced_artifacts` internally — this is the literal `_referenced_artifacts` shared
seam ADR 2026-08-20-1 calls the symmetry primitive), and renders it through one shared CLI
rendering helper reused by all three render call sites. No traversal, scope, or
`CHARTER_ACTIVATABLE_KINDS` logic changes — this is a collect-and-report change laid directly
on top of existing, unmodified graph logic.

## Technical Context

**Language/Version**: Python 3.11+ (repo standard; this mission touches only pre-existing
Python modules, no new dependency).
**Primary Dependencies**: none added. Touches `dataclasses` (stdlib), `rich.console.Console`
(already imported in `activate.py`/`deactivate.py`).
**Storage**: N/A — pure in-memory graph computation over an already-loaded `DRGGraph`; no
persistence.
**Testing**: pytest, scoped per the spec's Test-run scope note to
`tests/charter/test_cascade.py` plus the CLI command test files enumerated below. No full-repo
`pytest tests/` run required for this mission's own validation (reserved for post-merge/
cross-cutting cases per the charter's Testing Requirements).
**Target Platform**: CLI (`spec-kitty charter activate` / `spec-kitty charter deactivate`),
cross-platform per repo standard — no OS-specific code touched.
**Project Type**: Single project (existing CLI + kernel-adjacent library code, no new
subproject).
**Performance Goals**: No new I/O or algorithmic complexity class change — `_referenced_artifacts`
already does one BFS forward closure per call; this mission adds one more list append inside
the SAME existing loop, not a second pass. Console line count grows (NFR-002, deliberately),
not asymptotic cost.
**Constraints**: NFR-004 (additive-only console output — no existing line shape may change);
C-001 (`CHARTER_ACTIVATABLE_KINDS` itself never reopened); C-006 (kind-filtered nodes must
never flow through `CascadeScope.selects()` or the existing scope-bucketing loops).
**Scale/Scope**: 4-5 source files, ~9 FRs, one PR (see PR Shape below).

## Charter / Constitution Check

*GATE: re-checked after this plan's design below.*

- **ATDD-first (C-011)**: satisfied by construction — every WP below is scoped with an
  explicit red-first ATDD test named before any implementation commit (see Work Package
  Breakdown). PASS.
- **Single canonical authority**: FR-001 requires exactly one seam decide
  kind-filtered-vs-activatable (`_referenced_artifacts`'s `kind not in CHARTER_ACTIVATABLE_KINDS`
  test at `cascade.py:291`) and this plan keeps it that way — no sibling re-implementation.
  PASS (see "C-002 Symmetry" below for the concrete mechanism).
- **Architectural alignment / shared-package boundaries**: no touch to
  `spec-kitty-events`/`spec-kitty-tracker` external packages, no touch to the internal-runtime
  boundary (`src/runtime/next/`), no CLI-reaches-past-service-into-kernel-internals violation —
  `activate.py`/`deactivate.py` call only the public `charter.cascade` functions, same as today.
  PASS.
- **Locality of change / smallest-viable-diff vs. Boy Scout**: the touched file set is fixed
  by the spec's own blast radius (5 files + their existing test files); no campsite-clean
  commit is warranted (see "Campsite-Clean Scope" below) so there is no boy-scout-vs-locality
  tension to reconcile here. PASS.
- **Terminology canon**: no `--feature` flags, no "feature" in new user-facing strings — this
  mission adds CLI console lines and dataclass fields, not new options. PASS (verify at review
  by grepping the diff for `feature`).

No constitution violations requiring the Complexity Tracking table below; it is intentionally
left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/cascade-asset-silent-drop-01M0RME0/
├── spec.md                     # already authored, R1-R6 reviewed
├── plan.md                     # this file
├── tracer-approach.md          # seeded at spec phase
├── tracer-design-decisions.md  # seeded at spec phase
├── tracer-tooling-friction.md  # seeded at this plan phase
└── tasks.md                    # Phase 2 output (/spec-kitty.tasks — NOT this phase)
```

No `research.md`, `data-model.md`, `quickstart.md`, or `contracts/` are warranted: this is a
small, single-seam bugfix over already-designed graph logic (the data model already exists —
see Key Entities in spec.md — and there is no new external contract to document). Skipping
these phase-0/phase-1 artifacts is itself the smallest-viable-diff decision for a plan this
size, not an omission.

### Source code (repository root) — the actual, verified blast radius

```
src/
├── charter/
│   └── cascade.py                                    # _referenced_artifacts (266-295),
│                                                       # CascadeActivationResult (322-337),
│                                                       # NoCascadeReport (388-410),
│                                                       # DeactivationPlan (470-486),
│                                                       # cascade_activation_targets (340-379),
│                                                       # referenced_but_not_cascaded (413-444),
│                                                       # deactivation_plan (489-565)
├── doctrine/
│   └── artifact_kinds.py                              # CHARTER_ACTIVATABLE_KINDS docstring
│                                                       # only (317-333) — C-001: value NOT touched
└── specify_cli/cli/commands/charter/
    ├── activate.py                                    # _render_cascade_activation (274-338),
    │                                                   # _render_no_cascade_warning (383-417);
    │                                                   # new shared render helper + label
    │                                                   # constant land here (see C-002/FR-009)
    └── deactivate.py                                   # _render_cascade_deactivation (133-194);
                                                          # imports the shared helper from
                                                          # activate.py (existing precedent,
                                                          # deactivate.py:45-50)

tests/
├── charter/
│   └── test_cascade.py                                 # 863 lines; engine-level ATDD tests land
│                                                        # here (WP-A, WP-D); pinned test at line 648
│                                                        # (test_instantiates_is_followed_but_
│                                                        # template_dropped_at_candidacy) — C-004,
│                                                        # untouched
└── specify_cli/cli/commands/charter/
    ├── test_charter_activate_commands_cascade_output.py  # WP-B/WP-C CLI-level ATDD tests
    ├── test_charter_activate_commands_cascade_flags.py   # existing cascade-flag coverage —
    │                                                      # verify no assertion needs weakening
    │                                                      # (SC-006)
    └── test_charter_deactivate_commands.py                # WP-D CLI-level ATDD test (User Story 3)
```

**Structure Decision**: no new modules, no new packages. Every change lands inside the five
files already named by the spec's blast radius; the only structural decision this plan makes
is WHERE the new shared rendering helper (FR-009) lives — see "C-002 Symmetry" below.

---

## 1. Seam and blast radius

**Seam**: `charter` (kernel-adjacent library layer, `src/charter/`) for the data/collection
change, plus `specify_cli.cli.commands.charter` (CLI layer) for the three render sites. No
`doctrine` schema, no sync surface, no orchestrator-api surface.

- `src/charter/cascade.py` — data layer. `charter` imports only `doctrine` (per the module's
  own docstring, "Layering" section, verified still true: `from doctrine.artifact_kinds import
  CHARTER_ACTIVATABLE_KINDS, ArtifactKind` and `from doctrine.drg.models import DRGEdge,
  DRGGraph, Relation` are the only non-stdlib imports) — never `specify_cli`. This mission adds
  no new import; the boundary is unaffected.
- `src/specify_cli/cli/commands/charter/activate.py` and `deactivate.py` — CLI layer, the only
  two callers of `charter.cascade`'s public functions in `src/` (confirmed by grep: no other
  `src/` file imports from `charter.cascade`). No CLI command reaches past these two files into
  `charter.cascade` internals — `_referenced_artifacts` stays private (`_`-prefixed, not in
  `__all__`), called only from inside `cascade.py` by its three existing public functions.
- `src/doctrine/artifact_kinds.py` — docstring-only touch. `CHARTER_ACTIVATABLE_KINDS` itself
  (`artifact_kinds.py:330-333`, `frozenset(ArtifactKind) - {ArtifactKind.TEMPLATE,
  ArtifactKind.ASSET}`) is NOT modified (C-001) — only its docstring may gain a forward
  reference noting the new consumer, if a reviewer wants that; not required by any FR.
- Tests: `tests/charter/test_cascade.py` (engine-level), plus the CLI command test files listed
  in Project Structure above. No test file outside `tests/charter/` and
  `tests/specify_cli/cli/commands/charter/` needs a new assertion for this mission's own
  functional change (existing SC-006 protects everything else).

**No CLI command reaches past a service into kernel internals**: confirmed — neither
`activate.py` nor `deactivate.py` imports any private (`_`-prefixed) symbol from
`charter.cascade`; both import only the public functions/classes already re-exported via
`__all__` (`CascadeScope`, `cascade_activation_targets`, `referenced_but_not_cascaded`,
`deactivation_plan`). This mission's new fields are added to already-public dataclasses that
the CLI already imports the *functions* returning them; the CLI does not need to import the
dataclass names themselves (see "Contracts" below — this turns out to matter for the
dead-symbol gate).

## 2. C-002 symmetry as an architectural requirement

**The single shared seam, concretely.** `_referenced_artifacts(graph, source_urn)`
(`cascade.py:266-295`) changes its return type from `list[ReferencedArtifact]` to
`tuple[list[ReferencedArtifact], list[ReferencedArtifact]]` — `(activatable, kind_filtered)`.
The kind-filtered node is appended to the SECOND list at the exact line that today is a bare
`continue` (`cascade.py:291-292`):

```python
# today (cascade.py:288-293)
for urn in reachable:
    kind = _kind_of(urn)
    if kind is None:
        continue
    if kind not in CHARTER_ACTIVATABLE_KINDS:
        continue                                            # <-- silent drop, line 291-292
    refs.append(ReferencedArtifact(kind=kind, artifact_id=_bare_id(urn), urn=urn))
```

becomes (shape, not final code — WP-A owns the literal diff):

```python
for urn in reachable:
    kind = _kind_of(urn)
    if kind is None:
        continue
    ref = ReferencedArtifact(kind=kind, artifact_id=_bare_id(urn), urn=urn)
    if kind not in CHARTER_ACTIVATABLE_KINDS:
        kind_filtered.append(ref)
        continue
    activatable.append(ref)
```

`ReferencedArtifact` (`cascade.py:304-319`, existing) is reused verbatim for the kind-filtered
partition — it already carries exactly `kind`/`artifact_id`/`urn`, the shape the spec's Key
Entities section calls for. Reusing it rather than inventing a "sibling" dataclass also avoids
adding a second entry to the symbol-level dead-code allowlist (see "Contracts" below).

**How one seam feeds all three consumers, not three re-implementations.** All three public
functions already call `_referenced_artifacts` exactly once each, today:

- `cascade_activation_targets` (`cascade.py:340-379`) — `for ref in
  _referenced_artifacts(graph, source_urn):` at (effectively) line ~371.
- `referenced_but_not_cascaded` (`cascade.py:413-444`) — same pattern, ~line 439.
- `deactivation_plan` (`cascade.py:489-565`) — same pattern inside its candidate-collection
  loop, ~line 533.

Each of these three call sites unpacks BOTH partitions from the single updated call. The exact
binding differs per call site and per WP boundary — `cascade_activation_targets` binds
`activatable, kind_filtered = _referenced_artifacts(graph, source_urn)` unqualified, because it
populates the real field value immediately; `referenced_but_not_cascaded` and
`deactivation_plan` bind `activatable, _kind_filtered = _referenced_artifacts(graph, source_urn)`
(leading underscore) at WP-A's own commit boundary, since neither function reads the second
value yet and ruff's F841 would otherwise fire — see §12 WP-A for the full underscore-prefix
rule and WP-C/WP-D's later rename back to `kind_filtered`. All three continue iterating
`activatable` through its EXISTING scope-bucketing logic completely unchanged (this is what
keeps C-006 true — see below), and each eventually folds its partition directly into its own new
result field with NO scope filtering applied. This is the single collection seam: one function,
one membership test (`kind not in CHARTER_ACTIVATABLE_KINDS`, unchanged, still the only place
in the codebase that runs it), three callers each doing their own trivial threading — not three
independent re-derivations of the graph walk. A "sibling helper" is explicitly not needed or
introduced; FR-001's permitted exception (a sibling that calls the same shared test rather than
reimplementing it) does not need to be exercised.

**New fields, one per dataclass, each following its OWN existing field-shape convention** (C-002
requires the field be added consistently to all three — it does not require the three fields to
share an identical Python type, and forcing that would fight each dataclass's existing
rendering pattern):

- `CascadeActivationResult` (`cascade.py:322-337`) — new field `not_cascaded_kind_filtered:
  dict[str, list[str]] = field(default_factory=dict)`, alongside `activated`
  (`cascade.py:336`) and `skipped_by_scope` (`cascade.py:337`), same kind→sorted-bare-IDs shape
  those two already use.
- `NoCascadeReport` (`cascade.py:388-410`) — new field `not_cascaded_kind_filtered: dict[str,
  list[str]] = field(default_factory=dict)`, alongside `skipped` (`cascade.py:404`), same shape.
- `DeactivationPlan` (`cascade.py:470-486`) — new field `not_cascaded_kind_filtered: list[str]
  = field(default_factory=list)` (sorted URNs), alongside `deactivate` (`cascade.py:485`, a
  flat `list[str]` of URNs — NOT kind-bucketed) and `skipped_shared` (`cascade.py:486`, a
  `list[SharedSkip]`). `deactivate.py`'s existing render loop already partitions a URN into
  kind/config-id itself (`urn.partition(":")`, `deactivate.py:166`) — a flat URN list is the
  form that call site already knows how to render, so this is the minimal-friction shape, not
  an inconsistency with the other two.

Field name `not_cascaded_kind_filtered` is used consistently across all three (naming
consistency is part of "added consistently," even though the container type differs per
dataclass) — final naming is a WP-A implementation decision but should not drift across the
three dataclasses.

**FR-009's shared rendering helper — the decision.** All three render call sites need to print
"this kind/id was reached but is not charter-activatable" using IDENTICAL wording. The natural
home is `activate.py`: it is already the file `deactivate.py` imports shared CLI-layer helpers
from (`deactivate.py:45-50` already imports `RESYNTHESIZE_HELP`, `render_pack_config_error`,
`run_full_synthesize`, `validate_pack_config` from `activate.py` — this is existing, precedented
cross-command sharing, not a new pattern this mission invents). Plan decision: define one new
private function in `activate.py`, e.g. `_render_kind_filtered_line(kind_token: str, config_id:
str) -> None`, that prints exactly one line using a single module-level string constant (see
Gate Set below for why this constant matters for the Sonar repeated-literal rule), and have
`_render_cascade_activation`, `_render_no_cascade_warning` (both already in `activate.py`) and
`_render_cascade_deactivation` (in `deactivate.py`, importing the new helper alongside the
existing four names it already imports from `activate.py`) all call it. Exact wording is picked
once at WP-B (the first WP to implement a render call site) and never re-coined by WP-C/WP-D — a
candidate wording, to be finalized in WP-B's ATDD test:

```
[dim]Not cascaded[/dim]: {kind_token}/{config_id} (kind not charter-activatable)
```

This deliberately echoes the existing `[dim]Skipped (out of scope)[/dim]: ...` line's `[dim]`
styling (visually "not an error," per FR-003's "never phrased as a warning/error/failure") while
using different literal text ("Not cascaded" vs. "Skipped") so the two remain
grep-distinguishable per FR-008 — an operator (or a script) cannot mistake one for the other.

## 3. Contracts

**Nothing moves.** No doctrine schema change, no mission step contract change, no action index
change, no orchestrator-api surface change, no `spec_kitty_events`/`spec_kitty_tracker` package
change.

**`CascadeActivationResult` / `NoCascadeReport` / `DeactivationPlan` — additive-only, verified.**
Confirmed live: no code outside `src/charter/cascade.py` imports `CascadeActivationResult` or
`NoCascadeReport` by name anywhere in `src/` (`grep -rn "CascadeActivationResult\|
NoCascadeReport" --include=*.py .` outside `cascade.py` and `tests/` returns nothing) — both
CLI callers receive instances positionally from the functions that construct them
(`cascade_activation_targets`, `referenced_but_not_cascaded`) and never need to import the class
names themselves. `DeactivationPlan` IS imported by name in `tests/charter/test_cascade.py`
(isinstance assertions) and appears in `cascade.py`'s `__all__` (line 69) and in
`tests/architectural/test_no_dead_symbols.py`'s allowlist (see Gate Set below) — but `deactivate.py`
itself only imports the `deactivation_plan` FUNCTION (`deactivate.py:32`), not the
`DeactivationPlan` class. Adding a field to each is a pure ADD (no field removed, renamed, or
retyped — satisfies C-004/NFR-004/SC-004/SC-006's "additive only" requirement literally). No
downstream consumer breaks because there are no downstream consumers outside this repo's own
two CLI files and its own test files.

**`spec-kitty-events` / `spec-kitty-tracker` — confirmed uninvolved.** Verified live: neither
package (present in `.venv/lib/python3.11/site-packages/spec_kitty_events` and
`spec_kitty_tracker`) is imported anywhere in `src/charter/cascade.py`,
`src/specify_cli/cli/commands/charter/activate.py`, or `deactivate.py` — those three files'
import blocks contain no `spec_kitty_events`/`spec_kitty_tracker` reference at all, and neither
external package's own source imports `charter.cascade`. There is no event envelope, payload
schema, or tracker model that references these three dataclasses. The claim in the mission
brief that these packages "do not consume these specific dataclasses" is confirmed true, not
merely assumed.

## 4. Generated artifacts

**None touched.** Verified against the spec's own Non-Goals framing (no `doctrine pack
validate` change, no schema change): `CHARTER_ACTIVATABLE_KINDS` itself is unchanged (C-001),
so `scripts/generate_schemas.py`'s output (doctrine schema generation) has nothing to
regenerate — the schema-freshness check (`.github/workflows/ci-quality.yml`'s "Verify
generated doctrine schemas are up to date" step, `uv run python scripts/generate_schemas.py
--check`) should pass unchanged. Similarly `scripts/generate_contextive_glossaries.py` (the
Contextive glossary generator) is driven by domain-term declarations, not by console-string
literals or dataclass field names in `src/charter/`; this mission adds no new domain/glossary
term. If either check unexpectedly fails during implementation, that is new information to
report, not an assumption to override.

## 5. Gate set

Chosen from the hub gate table, verified against `.github/workflows/ci-quality.yml`,
`module-kernel.yml`, `module-doctrine-fast.yml`, and `doctrine-charter-tests.yml` live on this
checkout — every ENFORCED gate below is included with its concrete trigger condition
confirmed; every gate NOT included states why.

**Included, will fire:**

- **commitlint** (every commit after the 2026-02-25 cutoff, `ci-quality.yml` "Run commit
  message linting") — every commit this mission makes must be a valid conventional-commit type.
  Note: the mission-scaffold commit `826fc2056` (`tracer-tooling-friction.md` item 1) is
  ALREADY non-conforming ("Add meta for feature cascade-asset-silent-drop-01M0RME0" — no type
  prefix, and "feature" violates the Terminology Canon) and predates this plan phase; it must
  be folded/reconciled at PR-prep per that tracer file's own disposition note, not re-litigated
  here.
- **markdown lint** (`ci-quality.yml` "Run markdown style linting on changed files") — this
  mission edits `tracer-tooling-friction.md` (already committed) and this `plan.md`; both are
  changed `.md` files and will be linted. No known style violations introduced (plain prose,
  standard heading levels, no bare URLs).
- **doctrine schema freshness** (`scripts/generate_schemas.py --check`) — included per gate
  discipline even though "Generated artifacts" above concludes it should pass unchanged; it is
  cheap to verify and catches a false assumption if `artifact_kinds.py`'s docstring edit
  somehow interacts with schema generation (it should not — schemas are generated from the
  `ArtifactKind` enum values and `CHARTER_ACTIVATABLE_KINDS`'s frozenset MEMBERSHIP, not its
  docstring).
- **Contextive glossary freshness** (`scripts/generate_contextive_glossaries.py check`) — its
  CI trigger condition is a diff against `glossary/**`, `src/specify_cli/**`, `src/charter/**`,
  `.kittify/traceability/**` (`ci-quality.yml:861`); this mission's diff touches `src/charter/**`
  so the check WILL run (not skipped). Expected to pass with no glossary edits needed — no new
  domain term is introduced (see "Generated artifacts" above) — but it fires and must be
  watched, not assumed green.
- **TID251 banned-API lint** (`ruff check src tests --select TID251`, ENFORCED, no
  continue-on-error) — applies to all new/changed lines in `src/` and `tests/`; this mission's
  code uses no banned API (no raw `hashlib.sha256` reimplementation of the charter hasher, no
  direct `click.exceptions.*` catch) — nothing in the planned diff triggers it, but it runs
  unconditionally on every PR regardless of path, so it is included as a real gate, not skipped.
- **Bandit** (`bandit -r src/ --severity-level medium --confidence-level medium`, ENFORCED) —
  runs on all of `src/` unconditionally; the planned diff adds no subprocess calls, no
  deserialization, no credential handling — no new medium+ finding expected, but it runs.
- **pip-audit** (ENFORCED, runs unconditionally, no new dependency added by this mission —
  `uv.lock` is not touched, so no new CVE surface).
- **`patch()` target validation** (`scripts/check_patch_targets.py`, ENFORCED, runs
  unconditionally over all test files) — any new `unittest.mock.patch("...")` string this
  mission's new tests add (e.g. patching a render function to assert it was called with the
  right kind-filtered data) must resolve to a real importable target; the WP author must run
  this script locally before committing new patch-target strings.
- **Coverage-floored shard: `fast-tests-charter`** (`ci-quality.yml`, `--cov=charter
  --cov=specify_cli.charter_runtime --cov-fail-under=55`) — **verified concretely**: `src/charter/`
  falls under THIS shard's 55% floor, not the "kernel ≥90%" floor. `src/charter/cascade.py` is
  NOT under `src/kernel/` (`module-kernel.yml`'s 90% floor is scoped to `--cov=src/kernel` and
  `tests/kernel/` only — cascade.py is outside that tree entirely) and is NOT under
  `src/specify_cli/mission_loader/` (the OTHER named 90% floor, `mission-loader-coverage`
  job, `ci-quality.yml:1437-1462` — scoped to `tests/unit/mission_loader/` and
  `tests/integration/test_mission_run_command.py`, unrelated to charter). The applicable floor
  for this mission's actual touched module is `fast-tests-charter`'s 55%, confirmed live in
  `ci-quality.yml:2267-2299`. Every new branch this mission adds must be covered by a WP-owned
  test regardless (per the charter's "every new branch/helper needs tests" Sonar-shaping rule,
  which binds independent of the numeric CI floor).
- **`clean-install-verification`** (ENFORCED, `ci-quality.yml`) — runs unconditionally,
  structurally proves `spec-kitty next` runs after a clean install; this mission changes no
  packaging/entry-point surface, so it is expected to pass unaffected, but it is a real gate on
  every PR and is included.

**Included but confirmed a non-issue (verified, not skipped without reason):**

- **Typer 0.26 JSON error surface** (`uv run --with 'typer>=0.26' python -m pytest
  tests/agent/test_json_group_typer_surface.py -q`) — this is a FIXED test file exercising the
  Typer JSON-error-surface contract generically; it does not specifically target `charter
  activate`/`charter deactivate`. Checked concretely: neither `activate_cmd`
  (`activate.py:486-597`) nor `deactivate_cmd` (`deactivate.py:197-280`) declares a `--json`
  option — `grep -n "json" activate.py deactivate.py` finds only two unrelated
  `json_output=False` keyword arguments passed to the internal `_generate`/`_synthesize` calls
  inside `run_full_synthesize` (`activate.py:473,479`), which are not console-output modes of
  `activate`/`deactivate` themselves. These commands have no `--json` mode at all, so the new
  kind-filtered console lines have no JSON-output surface to interact with — this gate's
  scope simply does not overlap this mission's change. It still runs (unconditionally) and is
  expected to pass untouched.

**NOT included, with reason:**

- **ruff (full report) / mypy (full report)** — both are explicitly `[INFO]`
  `continue-on-error: true` steps in `ci-quality.yml` ("Run ruff report (advisory)" line ~871,
  "Run mypy report (advisory)" line ~902) — advisory only, do not gate the PR. `make lint`
  discipline (charter's own local-only rule) still applies as author hygiene, not a CI gate.
- **SonarCloud** — its job (`ci-quality.yml:3445` `sonarcloud:`) is gated
  `if: always() && (github.event_name == 'schedule' || github.event_name == 'workflow_dispatch')`
  (confirmed live at `ci-quality.yml:3502`) — it does NOT run on `pull_request` events at all.
  This PR will get no Sonar verdict; do not promise one. The repo's own Sonar-SHAPING rules from
  `CLAUDE.md` still apply as code-shaping constraints regardless (see below).
- **`uv.lock` freshness (`uv-lock-check`)** — runs unconditionally but this mission adds no
  dependency, so `pyproject.toml` is untouched and the lockfile stays in sync trivially; not a
  meaningful gate for this diff (included in spirit, but there is nothing to verify beyond "the
  diff touches no dependency declaration," which is true by construction).
- **`fast-tests-doctrine` / kernel-tests 90% floor / mission-loader-coverage 90% floor** — none
  of these three floors are scoped to `src/charter/` (see the concrete scoping proof above under
  the included `fast-tests-charter` bullet) — they run (unconditionally or on their own path
  triggers) but are not meaningfully affected by this mission's diff and carry no floor
  applicable to the touched files.
- **`doctrine-charter-tests.yml`** — this is a SEPARATE, dedicated fast-signal workflow (not a
  numbered gate in the hub table) that will ALSO fire because it path-triggers on
  `src/charter/**` and `src/specify_cli/cli/commands/charter/**`
  (`doctrine-charter-tests.yml:143-150`). It re-runs `tests/charter/` and
  `tests/specify_cli/cli/commands/charter/` with NO coverage-floor enforcement of its own (the
  file's own header explicitly disclaims that: "coverage-floor enforcement ... remain
  ci-quality.yml's responsibility") — it is a duplicate-but-faster correctness signal, not an
  additional numeric gate.

**Sonar code-shaping constraints (no CI run, still binding per `CLAUDE.md`):**

- **Complexity ceiling 15** (ruff `C901`/`mccabe`, `pyproject.toml:313-314`,
  `max-complexity = 15`). `_render_cascade_activation` (`activate.py:274-338`) already has two
  nested `for` loops plus a `try`/`except`; adding a third loop (or, per the shared-helper
  decision above, a single extra `for kind_value in sorted(result.not_cascaded_kind_filtered):`
  block calling the new one-line helper) should stay well under 15 — if the reviewer's
  post-hoc complexity check disagrees, extract a private `_render_kind_filtered_section(...)`
  helper rather than inlining a fourth loop into the existing function body.
- **Repeated literals → constants.** The new label wording (FR-009's shared string) is exactly
  a Sonar `S1192` candidate — it is used at minimum 3 times (once per render call site) if NOT
  centralized, or exactly once (inside the shared helper) if centralized as planned above. Plan
  decision: the literal lives as ONE module-level constant in `activate.py`
  (co-located with the existing `RESYNTHESIZE_HELP` constant, `activate.py:59-65`, following
  that file's existing convention for shared render-string constants), consumed only by the new
  `_render_kind_filtered_line` helper — never inlined at any of the three call sites.
- **Tests for every new branch/helper** — see Work Package Breakdown; each WP's ATDD test
  directly exercises its new branch(es), not just an end-to-end smoke assertion.
- **No `# noqa`/`# type: ignore` additions** planned or anticipated; the change is
  straightforward dataclass-field-plus-render-line work with no type-checker friction expected.

## 6. Baseline

Per the spec's own Test-run scope note (spec.md lines 294-300) and the charter's Testing
Requirements: scope validation to `tests/charter/test_cascade.py` plus
`tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py`,
`test_charter_activate_commands_cascade_flags.py`, `test_charter_activate_commands_core.py`,
and `test_charter_deactivate_commands.py` — NOT a full-repo sweep.

**Concrete baseline-capture procedure, to run before WP-A's first commit:**

```bash
.venv/bin/python -m pytest \
  tests/charter/test_cascade.py \
  tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py \
  tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_flags.py \
  tests/specify_cli/cli/commands/charter/test_charter_activate_commands_core.py \
  tests/specify_cli/cli/commands/charter/test_charter_deactivate_commands.py \
  -q --tb=short > /tmp/cascade-3705-baseline.txt 2>&1
```

Capture the pass/fail/error COUNT and the exact list of any failing/erroring test node IDs
from this run before any WP's implementation commit lands. After each WP's final commit, re-run
the identical command and diff the failing-node-ID set against the captured baseline:

- A node ID red in BOTH baseline and post-WP run → pre-existing, not this mission's — do not
  "fix" it, do not attribute it to this WP.
- A node ID green in baseline but red post-WP → introduced by this mission — must be fixed
  before the WP is done, per charter's red-first/never-retry-to-green discipline.
- Any node ID red in the baseline scoped run that is NOT already covered by the existing GitHub
  issue #3284 (~23 known-failing tests / 2 errors) triggers the charter's Pre-existing Failure
  Reporting Rule — but issue #3284 already exists and is the canonical umbrella for the
  known-red set, so the default expectation is that any scoped-run red found here is already
  inside #3284's coverage, not a new issue to file. Only file a NEW issue if a scoped-run
  failure is clearly outside #3284's described set (verify by reading #3284's body before
  filing anything new).

## 7. ATDD-first (charter §C-011) — per work package

Binding, stricter than generic red-first: for EVERY work package below, implementation may not
begin until a failing-first ATDD test exists, committed as a SEPARATE commit preceding any
implementation commit in that WP's lane. The reviewer verifies RED on the WP's
`planning_base_branch` (`fix/cascade-asset-silent-drop-3705`) and GREEN on the WP's final
commit. This is restated per-WP in the Work Package Breakdown below, not left abstract.

**Explicit exception, already settled by the spec — do not re-derive a WP for it**: FR-006 (the
ADR-citation-in-PR-body requirement) is a PR-open-time process gate, checked by the pre-merge
review squad / accept gate against the PR body text — it is NOT a work package, has no
user-observable runtime behavior to pin, and must NOT get a manufactured red-first ATDD test.
The tasks phase must not decompose FR-006 into a WP. A specific reviewer step at mission close
(not a WP) owns SC-005 (verifying the PR body cites ADR 2026-08-20-1).

## 8. Campsite-clean scope (standing order 2)

Read live, in full, all five touched-surface files
(`src/charter/cascade.py`, `src/doctrine/artifact_kinds.py`,
`src/specify_cli/cli/commands/charter/activate.py`, `deactivate.py`) before writing this plan.
No pre-existing, domain-matched debt was found in the specific functions this mission touches:

- `_referenced_artifacts`, `cascade_activation_targets`, `referenced_but_not_cascaded`,
  `deactivation_plan`, `CascadeActivationResult`, `NoCascadeReport`, `DeactivationPlan` are all
  well under the complexity ceiling, already carry full docstrings, already have `__all__`
  discipline correct, and show no lint/type suppressions.
- `_render_cascade_activation`, `_render_no_cascade_warning`, `_render_cascade_deactivation`
  each carry exactly one pre-existing lint suppression: a `# noqa: PLC0415` on a deferred
  `from charter._drg_helpers import load_validated_graph` local import
  (`activate.py:297`, `activate.py:395`, `deactivate.py:153`). This is the repo-wide
  lazy-import convention, not debt this mission introduced or touches — the mission's
  kind-filtered-node reporting change does not go anywhere near the graph-loading import
  path. Judged non-domain-matched debt. Otherwise no dead branches, no other suppressed
  warnings, no TODO markers.
- `CHARTER_ACTIVATABLE_KINDS`'s docstring in `artifact_kinds.py` is current and accurate as of
  this reading (no stale cross-reference found).

**Decision: no campsite-clean commit.** No domain-matched debt was found — the one
pre-existing `# noqa: PLC0415` per render function noted above is unrelated to this mission's
change and is judged non-domain-matched; inventing a tidy-first commit here would be
manufactured busywork against the charter's own "an invented campsite commit is worse than
none" guidance. This is stated explicitly per instruction, not silently skipped, and stands on
the corrected, accurate record above.

## 9. Reflexivity

This changes `charter activate`/`charter deactivate` console output. Per NFR-004 and the spec's
own Edge Cases section (spec.md line 214-221), the concrete guarantee this plan restates and
does not contradict:

- **No existing line shape is removed, renamed, reordered, or has its exact string changed.**
  `Cascade-activated: ...`, `Warning: ... was not activated (no --cascade)`, `Skipped (out of
  scope)`, `Cascade-deactivated: ...`, and `Skipped (shared artifact)` all keep their exact
  current text and code paths (SC-006 protects this; the WP author must NOT touch any existing
  `console.print(...)` call's f-string in `_render_cascade_activation`, `_render_no_cascade_warning`,
  or `_render_cascade_deactivation` except to add new, separate `console.print` calls alongside
  them).
- **A running mission or script parsing today's output is unaffected**: it continues to match
  the unchanged line shapes. A parser that assumed cascade output was already exhaustive of
  everything a source references was relying on the exact bug this mission fixes, and will now
  see MORE lines, never fewer or differently-shaped ones for the cases it already handled.
- **`FR-005a`'s guard change is additive to control flow, not a removal**: `has_skipped`
  (`cascade.py:407-410`) gains an additional OR-condition (checking the new
  `not_cascaded_kind_filtered` field too); it does not remove the existing `any(self.skipped.
  values())` check, so a source with only activatable-kind skipped refs (today's only case)
  still triggers the guard exactly as before.

## 10. PR shape

**One PR per mission** (the repo default). This mission is scoped tightly — 4-5 source files,
9 FRs, 3 constraints, verified live to require no new dependency, no schema change, no
contract change — well within one reviewable diff. No case for a per-WP PR split: the WPs below
are sequential and each depends on the shared field(s)/helper the prior WP introduced (see Work
Package Breakdown), so splitting into separate PRs would force either (a) landing an
intermediate PR that adds a dataclass field with no renderer yet (dead-ish but not truly dead —
still exercised by WP-A's own engine-level test) or (b) an awkward stacked-PR review chain for a
change this small. Decision: one PR, opened after all WPs land on the mission branch, per the
repo's `mission-wrap-up-sequence` procedure.

## 11. Scope discipline — this mission's main risk

Explicitly, none of the following are touched by this plan, per the spec's own Non-Goals
section, which OVERRIDES the workspace's general "no follow-up issues — fold in" standing order
for this specific mission (both the issue and the spec are explicit that these are
separately-tracked, maintainer-scoped concerns):

- **#2599** (executable asset-gate handlers) — not touched; this mission is the visibility half
  only, never the executable half.
- **#3037, #2536, #3418** — not investigated, not touched.
- **The fail-open `_mt_dispatch_one_gate` wrapper** — not touched.
- **SK-76** (URN-minting divergence, `doctrine/drg/merge.py` vs.
  `charter/kind_vocabulary.py::resolve_artifact_urn`) — distinct defect (C-005), not this
  mission's fix target; `merge.py` and `kind_vocabulary.py`'s URN-minting logic are not in this
  plan's blast radius and will not be edited by any WP below.
- **`doctrine pack validate` warning idea** — out of scope, not folded in even if it would "fall
  out naturally" during implementation of any WP.
- **`CHARTER_ACTIVATABLE_KINDS` reversal/narrowing** — C-001 is absolute; no WP below adds
  `TEMPLATE` or `ASSET` back to that frozenset, under any framing.

A tasks-phase author decomposing this plan into WPs must not widen into any of the above — doing
so is a scope violation, not helpfulness, per the spec's explicit framing.

## 12. Work package breakdown

This section sketches phasing/sequencing for the tasks phase to decompose directly; it does
NOT materialize WP IDs, does NOT write `tasks.md`, and does NOT invent task numbers — that is
the next phase's job.

**Sequencing rationale**: C-002/C-006 are MISSION-LEVEL (final-state) invariants, not
per-commit invariants — SC-003 (activate/deactivate agreement), SC-006 (no existing line
changes), and C-006's required test are all checked at mission close / by the accept gate, not
enforced to hold at every intermediate WP commit. This means the four consumers can be threaded
sequentially across WPs (collection → activation render → no-cascade render → deactivation
render) WITHOUT leaving any single WP's own final commit red or C-002-inconsistent internally —
each WP's own tests pass on its own final commit; the mission-wide symmetry claim is true only
once all WPs have landed, which is exactly when C-002/SC-003 are actually checked. This is
verified against the actual code structure, not assumed: `_referenced_artifacts`'s SIGNATURE
is shared across all three consumers — `cascade_activation_targets`,
`referenced_but_not_cascaded`, and `deactivation_plan` all call the same function body via the
identical `for ref in _referenced_artifacts(...): ...ref.kind...` pattern — so that signature
is migrated in full, at all three call sites, in WP-A; it is never left partially applied.
What IS threaded per-consumer across WP-A/C/D is only each dataclass's FIELD population (the
new `not_cascaded_kind_filtered` field's real value), which each of those three functions
already independently owns (see "C-002 Symmetry" above) and which is additive — a new
`field(default_factory=...)` — rather than a change to any existing shared call shape. This is
exactly what keeps every WP's own final commit green against §6's baseline-diff procedure: the
one genuinely shared thing (the function signature) never sits half-migrated, while the three
independent things (each dataclass's field value) land on their own WP's schedule. Nothing
below MUST land in one atomic WP beyond WP-A's three-call-site unpacking fix.

**Suggested WP shape** (4 WPs, sequential dependency, not parallelizable — WP-B/WP-C/WP-D each
need WP-A's new field(s) and WP-B's new shared helper):

- **WP-A — shared collection seam (FR-001, FR-002; the activation-side half of the C-006
  required test — WP-D completes the deactivation-side half, see WP-D below).**
  Change `_referenced_artifacts`'s return shape from `list[ReferencedArtifact]` to
  `tuple[list[ReferencedArtifact], list[ReferencedArtifact]]` — `(activatable,
  kind_filtered)`. `_referenced_artifacts` is ONE shared function body, called identically
  (`for ref in _referenced_artifacts(...): ...ref.kind...`) from all three consumers, so this
  WP adjusts ALL THREE call sites' unpacking in the same commit — but the two that do not
  populate a field yet must NOT bind the name `kind_filtered` unqualified, or ruff's pyflakes
  ruleset (`F841` unused-variable, selected repo-wide with no per-file exemption for
  `cascade.py`) flags it, contradicting §5's "No `# noqa`/`# type: ignore` additions planned"
  line. Concretely, in this WP's own commit:
  - `cascade_activation_targets` changes to `activatable, kind_filtered =
    _referenced_artifacts(...)` — unqualified, because this WP populates the real field value
    from it (see below).
  - `referenced_but_not_cascaded` changes to `activatable, _kind_filtered =
    _referenced_artifacts(...)` — leading underscore, because at WP-A's own final commit
    boundary this function does not yet read the second value.
  - `deactivation_plan` changes to `activatable, _kind_filtered = _referenced_artifacts(...)`
    — leading underscore, same reason.
  This is an explicit instruction to the WP-A implementer, not a stylistic option: the
  underscore prefix in the latter two call sites is required to keep the WP-A commit lint-clean.
  WP-C (for `referenced_but_not_cascaded`) and WP-D (for `deactivation_plan`) each rename
  `_kind_filtered` back to `kind_filtered` (dropping the underscore) in their OWN commit, at the
  exact point they start using it to populate their own dataclass field — this rename is an
  explicit, required step of WP-C's and WP-D's own diffs, not an afterthought left for the WP
  author to discover. All three call sites continue iterating `activatable` exactly as before —
  a mechanical, behavior-preserving change for the latter two, which do NOT populate their new
  dataclass field yet. This keeps every consumer compiling and all existing tests
  (`tests/charter/test_cascade.py:283-406, 603-845+`) green on this WP's own final commit.
  Only `CascadeActivationResult` gains the new field's REAL VALUE
  (`not_cascaded_kind_filtered`, populated from `kind_filtered`) in this WP, via
  `cascade_activation_targets`. ATDD test (RED-first, engine-level, in
  `tests/charter/test_cascade.py`): construct a fixture graph with one `suggests` edge to a
  `tactic` and one to `asset:...` from a common source; assert
  `cascade_activation_targets(graph, source, CascadeScope.all()).not_cascaded_kind_filtered ==
  {"asset": ["..."]}` — RED on `fix/cascade-asset-silent-drop-3705` today (field does not
  exist), GREEN after. Also lands the activation-side half of the C-006-required regression
  test: under `CascadeScope.all()`, assert the asset URN appears in `not_cascaded_kind_filtered`
  and NOT in `activated` or `skipped_by_scope` — the two scope-gated fields
  `CascadeActivationResult` already had. C-006's own text also names `deactivate`/candidates
  (`DeactivationPlan`'s field), which this WP's test does NOT cover — that half is WP-D's job
  (see WP-D below); the two WPs' tests together, not WP-A's alone, satisfy C-006 in full. Does
  NOT populate `NoCascadeReport` or `DeactivationPlan` with their new field's real value yet,
  and does NOT need to touch either function's already-updated unpacking/iteration logic again
  — that is WP-C/WP-D's job, which now only needs to rename `_kind_filtered` to `kind_filtered`
  and add `not_cascaded_kind_filtered=kind_filtered` to their own dataclass construction plus
  the CLI render call. Does NOT touch any CLI file — no user-visible console change from this WP
  alone (the field is threaded through all three engine functions, but nothing renders it yet).

- **WP-B — activation-report rendering (FR-003, FR-004, FR-008, FR-009's shared helper —
  first definition).** Add the shared `_render_kind_filtered_line` helper + label constant in
  `activate.py`; call it from `_render_cascade_activation` for each
  `not_cascaded_kind_filtered` entry; add the FR-004 zero-activatable-targets message
  (trigger: `not result.activated and bool(result.not_cascaded_kind_filtered)` — see "C-002
  Symmetry" above for why this exact condition satisfies Scenarios 2/3/4 and SC-002/SC-007
  without conflation). ATDD test (RED-first, CLI-level, in
  `test_charter_activate_commands_cascade_output.py`): run `charter activate ... --cascade all`
  against the User-Story-1 fixture; assert the console output contains BOTH the existing
  `Cascade-activated:` line for the tactic AND the new distinct line for the asset — RED today
  (asset produces nothing), GREEN after. A second test for the zero-activatable-targets case
  (Scenario 2) and a third asserting Scenario 4 does NOT print that message (SC-007) — all
  three in the same WP since they share the one code path.

- **WP-C — no-cascade warning path (FR-005, FR-005a).** Rename `_kind_filtered` to
  `kind_filtered` in `referenced_but_not_cascaded` (per WP-A's instruction above) and thread the
  field through `NoCascadeReport`; call the SAME shared helper from
  `_render_no_cascade_warning` (imported from `activate.py`, already in the same file, no new
  import needed); fix the `has_skipped` guard to also fire on kind-filtered-only sources. ATDD
  test (RED-first, CLI-level): run `charter activate ...` with NO `--cascade` against the same
  fixture; assert the existing no-cascade warning line still appears for the tactic AND the new
  line appears for the asset, using DIFFERENT wording than the recovery-hint line — RED today,
  GREEN after. A second test for the kind-filtered-only-source case (Scenario 2 of User Story
  2) exercising the `has_skipped` guard fix specifically.

- **WP-D — deactivation-side symmetry (FR-007; the deactivation-side half of the C-006 required
  test; NFR-003's cross-command test = SC-003).**
  Rename `_kind_filtered` to `kind_filtered` in `deactivation_plan` (per WP-A's instruction
  above) and thread the field through `DeactivationPlan`; call the shared helper (imported into
  `deactivate.py`) from `_render_cascade_deactivation`. Two DISTINCT ATDD tests land in this WP,
  covering two different requirements — do not conflate them:
  1. **CLI-level, in `test_charter_deactivate_commands.py`** (NFR-003/SC-003 cross-command
     verification): activate the User-Story-1 fixture with `--cascade all` (asset line
     appears), THEN deactivate the same source with `--cascade all` and assert the equivalent
     kind-filtered line appears in the deactivation output too — this single test IS the
     NFR-003/SC-003 cross-command verification the spec requires (exercises BOTH commands
     against the SAME fixture, not two differently-shaped ones; checks that activate and
     deactivate AGREE on the same node) — RED today (deactivation reports nothing for the
     asset), GREEN after.
  2. **Engine-level, in `tests/charter/test_cascade.py`** (the deactivation-side half of the
     C-006 required test, completing WP-A's activation-side half above): under
     `CascadeScope.all()`, assert the kind-filtered asset URN appears in
     `deactivation_plan(...).not_cascaded_kind_filtered` and NOT in `.deactivate` or inside any
     `SharedSkip` in `.skipped_shared` — RED today (the field does not exist / the URN would be
     absent from all three), GREEN after. This is a different assertion from test 1 above: test
     1 checks activate/deactivate console output AGREE on the same node; this test checks
     `DeactivationPlan`'s OWN dataclass fields never leak a kind-filtered node into the
     activatable-shaped fields (`.deactivate`, `.skipped_shared`). Both are needed and both land
     in this WP.

Each WP's reviewer verifies RED on `fix/cascade-asset-silent-drop-3705` → GREEN on that WP's
final commit, per §7 above. WP-A's and WP-D's engine-level tests land in
`tests/charter/test_cascade.py`; WP-B/WP-C/WP-D's CLI-level tests land in
`tests/specify_cli/cli/commands/charter/test_charter_activate_commands_cascade_output.py` /
`test_charter_deactivate_commands.py` — this mirrors the existing separation of engine tests
from CLI-rendering tests already present in the repo (verified: `test_cascade.py` never asserts
console strings; the CLI test files never construct `DRGGraph` fixtures directly). WP-D is the
only WP that lands tests in both files, per its two-test split above (C-006's engine-level
deactivation-side assertion plus NFR-003/SC-003's CLI-level cross-command assertion).

## Complexity Tracking

*Empty — no constitution violations to justify (see Charter/Constitution Check above).*
