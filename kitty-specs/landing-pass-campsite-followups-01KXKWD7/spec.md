# Mission Specification: Landing-Pass Campsite Follow-ups

**Mission**: landing-pass-campsite-followups-01KXKWD7
**Mission type**: software-dev
**Target branch**: feat/landing-pass-campsite-followups
**Created**: 2026-07-15

## Purpose

Clear the tech-debt residue left by the #2670 maintainer landing pass so the
shared `main` branch stops going red for process reasons and the affected
surfaces regain single-source integrity. Four pre-existing debt items surfaced
during that pass (verified against `upstream/main` @ `c6b70d22e`): a recurring
test-shard registration gap (#2671), a parallel-test isolation flake and its
duplicate/theme-twin (#2673 + #2638 + #2672), an unguarded set of sync
remediation commands (#2674), and a cluster of type-check errors (#2675). This
mission consolidates them into one quick-follow with two rigour tiers: a
mechanical debt burn-down plus one topology design decision.

## User Scenarios & Testing

Primary actors: a **Spec Kitty contributor** landing a change, and the **CI
system** gating that change.

### Scenario A — Adding an architectural test file (#2671)
A contributor lands a new `tests/architectural/*.py` guard.
- **Today**: the file receives no shard marker, so `main` goes red on *two*
  gates at once — the shard-marker completeness gate and the orphan-surface
  gate — until the contributor discovers and hand-edits the shard-assignment
  table and re-pushes. This has recurred across three registration incidents.
- **Desired**: the file is automatically covered by exactly one shard and both
  gates stay green with zero manual registration; a contributor who *wants* to
  tune placement can still add an explicit entry that wins.

### Scenario B — Running the architectural suite in parallel (#2673, #2638, #2672)
A contributor runs the architectural suite locally under
`-n auto --dist loadfile`.
- **Today**: a test that injects a synthetic path-join into the **real**
  `core/mission_creation.py` on disk is read mid-mutation by a sibling worker's
  scanner, producing an intermittent false failure; two scanners are affected
  (#2673, #2638). A separate test similarly mutates the real
  `synthesis-manifest.yaml` and depends on ambient color env (#2672).
- **Desired**: parallel runs are deterministic; no test mutates a shared real
  repository file that another test scans, and console determinism comes from
  the object, not the environment.

### Scenario C — Adding or renaming a sync remediation command (#2674)
A contributor adds or renames a command emitted in a sync-preflight remediation
hint.
- **Today**: only the dict-backed hints are validated to resolve; the inline
  remediation builder emits bare command literals (`sync migrate`,
  `orphan-daemons`, `auth login`) that no guard checks, so a typo or a stale
  command ships green. Two remediation sentences are also duplicated between the
  dict and the inline builder.
- **Desired**: every remediation command — dict-backed or inline — is validated
  to resolve, and each remediation sentence has a single canonical source.

### Scenario D — Running the type checker (#2675)
A contributor runs `mypy` over the CLI surfaces.
- **Today**: 17 pre-existing errors across 8 files (redundant casts, un-narrowed
  Optionals, `str` used where the `Lane` enum is required, `Any` leaks), 8 of
  them clustered in the core-CLI workflow executor.
- **Desired**: zero errors on the named files, fixed at their shared boundaries
  (not scattered casts) and without suppression.

### Rules / invariants that must always hold
- Every collected architectural test belongs to **at least one** shard (no test
  escapes all shards) — the union invariant is the correctness net.
- A test must never leave a shared, tracked repository file in a mutated state
  observable by a concurrently-running test.
- A remediation hint may only name a command that resolves under `--help`.
- Type errors are fixed in the code; suppression comments are not an accepted
  remedy.

## Domain Language

- **Shard / shard group**: a CI partition of a pole's test roots. The `arch`
  group partitions the four architectural pole roots into three balanced,
  disjoint shards; the assignment table is deliberately manual and
  duration-balanced.
- **Shard-marker completeness gate (GC-1)**: asserts every group-root test
  carries exactly one `<prefix>_<N>` marker.
- **Orphan-surface gate**: asserts no gate-selected surface is selected by zero
  shards.
- **Bite-battery**: a red-first test that injects an unsanctioned raw path-join
  and asserts the untrusted-path audit flags it.
- **Remediation registry**: the single canonical source of remediation sentences
  that both the JSON hint field and the human-readable bullet builder draw from.
- **CliConsole**: the deterministic console proxy whose determinism is a
  property of the object, not ambient environment variables.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | An unregistered `tests/architectural/*.py` file is automatically assigned to exactly one shard via a deterministic default fallback, so both the shard-marker completeness gate and the orphan-surface gate pass without any manual registration step. | Draft |
| FR-002 | An explicit shard-assignment entry for a file continues to take precedence over the default fallback, preserving hand-tuned placement for duration-balancing and family co-location. | Draft |
| FR-003 | The shard-union invariant (no collected architectural test escapes all shards) is retained and serves as the correctness net that would catch a fallback defect. | Draft |
| FR-004 | The default-fallback behaviour is opt-in per shard group; the `arch` group opts in while other groups are unaffected unless they also opt in. | Draft |
| FR-005 | The bite-battery source-mutation test no longer mutates a shared, tracked source file that a concurrent scanner reads; the injected witness is isolated so parallel runs are deterministic, while the test still proves the untrusted-path audit detects an unsanctioned raw path-join. | Draft |
| FR-006 | The second scanner victimised by the same injection (#2638) is immune to the race once the mutation is isolated (closed by the same fix, not a separate patch). | Draft |
| FR-007 | The color/synthesis-manifest hygiene flake (#2672) no longer mutates a real repository file and no longer depends on ambient color environment; deterministic console output is obtained through the CliConsole proxy rather than environment mutation. | Draft |
| FR-008 | Every sync-preflight remediation command — whether emitted from the dict-backed hints or the inline remediation builder — is validated to resolve under `--help`, so a stale or mistyped command fails the guard before merge. | Draft |
| FR-009 | Remediation sentences are single-sourced: no remediation prose literal is duplicated between the dict-backed hints and the inline builder; the command-name guard scans the full remediation set, not a subset. | Draft |
| FR-010 | The in-scope `mypy` errors are resolved to zero across the in-scope surfaces, with each shared-root cluster fixed once at its boundary (the lane-reader sentinel promotion, a typed work-package accessor, and a de-duplicated shared interview helper) and the genuinely independent Optional narrowings fixed at their own call sites. The three mechanical redundant-cast drops in `_read_path_resolver.py`, `status/emit.py`, and the `m_2_1_4` migration are in scope (drop the cast, remove any now-unused `cast` import); the three redundant-cast drops in `charter/mission_type_profiles.py` are **deferred** (owned by the in-flight mission-type work — see Scope Boundaries). | Draft |
| FR-011 | The load-bearing doctrine header of `tests/_arch_shard_map.py`, which currently instructs contributors to manually append to `_ARCH_SHARD_N_FILES`, is rewritten to document the new automatic-default + explicit-override model so it no longer misinstructs future contributors. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Adding a new architectural test file requires no shard-table edit for CI to stay green. | 0 manual registration steps | Draft |
| NFR-002 | The isolation fix is verifiable by a **structural invariant** (the real tracked source file is byte-unchanged after the mutating test completes, and the injected witness is confined to an isolated root), with a repeated-run smoke as secondary evidence. | Structural assertion passes; ≥ 5 consecutive green parallel runs as smoke | Draft |
| NFR-003 | Type checking is clean on the **in-scope** surfaces (all named files except the deferred `charter/mission_type_profiles.py` casts). | 0 mypy errors on in-scope surfaces (14 of the 17; the 3 deferred clear when the sibling mission lands) | Draft |
| NFR-004 | No new suppression is introduced to satisfy any requirement. | 0 new `# type: ignore` / `# noqa` / Sonar suppressions | Draft |
| NFR-005 | Each new branch or extracted helper is exercised by a focused test in the same change. | New-code coverage ≥ project quality gate | Draft |
| NFR-006 | The default-fallback shard assignment is deterministic per file path and assigned by a stable hash-modulo over the shard count (not "lightest shard"), so fallback files cannot systematically pile onto one shard. | Deterministic per path; hash-modulo distribution (mechanism-tested, not chance-balanced) | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Fix the code, never suppress — no blanket `# type: ignore`, `# noqa`, or Sonar-suppression comments (charter). | Draft |
| C-002 | The #2671 default fallback is **additive**: it must preserve the existing auditable, duration-balanced manual bin-packing as the override path, not replace it. The doctrine header that documents the manual model is rewritten in the same change (FR-011) so the two stay consistent. | Draft |
| C-003 | The bite-battery must continue to exercise the **real** detector code path (root-agnostic scan logic); isolating the mutation must not weaken what the test proves. | Draft |
| C-004 | #2638 is closed as fixed-by (duplicate root cause); #2672 is folded as the same real-file-mutation hygiene class — both resolved within this mission. | Draft |
| C-005 | Every fix reproduces its failure **red-first** through the pre-existing entry point (ATDD), then goes green; the reviewer verifies red→green. | Draft |
| C-006 | This mission proceeds **in parallel** with the in-flight resolver-seam mission (#2651/S0). The shared test file `test_single_mission_surface_resolver.py` (~1372 LOC, the resolver mission's primary and still-growing test surface) is a **sharp** contention point, not a trivial touchpoint: the #2673 fix relocates mid-file logic (~line 822) in the highest-churn zone. The #2673 WP must therefore either land in a **quiescent window** of the resolver mission or be **folded into that mission's lane** (single owner). The plan must not budget this as a free rebase. | Draft |
| C-007 | No release/version numbers are assigned in scope; the product owner superimposes versioning at release time. | Draft |
| C-008 | Design decision for #2671 is **Direction A** (per-group opt-in default fallback via a stable hash-bucket in the shard registry, explicit entries win, union invariant retained) — resolved by the operator, recorded as the mission's decision moment. | Draft |

## Success Criteria

- **SC-001**: A contributor adds a `tests/architectural/*.py` file with no
  shard-table edit and `main` stays green on both the completeness and
  orphan-surface gates.
- **SC-002**: The architectural suite runs green in parallel locally across at
  least five consecutive runs — the bite-battery flake no longer reproduces.
- **SC-003**: A mistyped or renamed sync remediation command is caught by the
  command-name guard before merge, and no remediation sentence exists in two
  places.
- **SC-004**: `mypy` reports zero errors on the eight named files, achieved with
  zero new suppressions.
- **SC-005**: Issues #2671, #2673, #2674, #2675 are resolved and #2638, #2672
  are closed.
- **SC-006**: A follow-up issue is filed for the remaining ~6 un-migrated
  `_SourceMutation` / `_SourceInsertion` sites (the real-file-mutation hazard
  class beyond the #2673/#2638 pair), so the carve-out is tracked rather than
  silently dropped.

## Assumptions

- All six items (#2671/#2673/#2674/#2675 + folded #2638/#2672) are pre-existing
  debt on `main`, verified at `c6b70d22e`; none were introduced by #2670.
- `CliConsole` (`src/specify_cli/cli/console.py`, verified present at
  `c6b70d22e`) is the canonical deterministic-console seam — its docstring
  states "determinism is a property of the object, not the environment" — and is
  the operator-directed vehicle for the #2672 fix rather than `NO_COLOR` env
  mutation.
- The `Lane` type is a `StrEnum`. The legacy read sentinel `"uninitialized"` is
  **semantically distinct** from the existing `Lane.GENESIS` (sentinel = WP absent
  from snapshot; GENESIS = seeded but unseeded-lane), so the operator-chosen full
  unification adds a **new `Lane.UNINITIALIZED` member** (value preserved) and
  threads it through the FSM state-map, display filters, and merge/worktree
  consumers with behavior tests — a heavier-than-mechanical change (confirmed
  during plan; see plan IC-05).
- Local `pytest-xdist` workers are separate processes, so a process-local
  monkeypatch of the scan root is invisible to sibling workers (the basis of the
  #2673 isolation fix).

## Scope Boundaries

**In scope**: #2671, #2673 (+ #2638 dup, + #2672 theme-twin), #2674, #2675.

**Out of scope** (tracked separately, do not fold):
- #2475 / #2476 — local arch-pole pre-PR parity CLI (a larger design effort
  under the CI-topology / test-friction epics).
- #2607 — GC-2b baseline abs-path-id portability (different surface).
- #2625, #2631, #1843 — different surfaces / strategic doctrine.
- Migrating the remaining ~6 `_SourceMutation` / `_SourceInsertion` sites beyond
  the #2673/#2638 pair — filed as a tracked follow-up issue (see SC-006); not
  fixed in this mission.
- The **three** redundant-cast drops in `charter/mission_type_profiles.py`
  (lines 577/581/876) sit on production code owned by the in-flight
  mission-type-single-source work. To avoid a cross-mission ownership collision
  on production code, they are **deferred** here (they clear when the sibling
  mission lands). The other three mechanical casts (`_read_path_resolver.py`,
  `status/emit.py`, the `m_2_1_4` migration) are **in scope** — see FR-010.

## Traceability

| Issue | Workstream | Disposition |
|-------|-----------|-------------|
| #2671 | Shard-registry default fallback (Direction A) | In scope — decision-moment WP |
| #2673 | Bite-battery mutation isolation | In scope |
| #2638 | Second scanner victim | Folded into #2673 (close as fixed-by) |
| #2672 | Color/synthesis-manifest hygiene | Folded (CliConsole seam) |
| #2674 | Sync remediation registry + guard | In scope |
| #2675 | Type-debt (6 roots) | In scope (3 `mission_type_profiles.py` casts deferred) |
| #1928 | Parent epic (ruff/mypy/Sonar debt) | Parent link for #2675 — not scoped |

Full verified research: `research-notes-csf-2670.md` (repository root of this
mission clone).

**Sequencing note (from post-spec sizing review):** WP for #2671 is a soft
enabler and is safe/beneficial to land first — it de-frictions the in-flight
#2651/S0 missions that keep hitting the same `_arch_shard_map.py` registration
gap. #2675's `workflow_executor.py` edits (three of its clusters land on that one
file) must be consolidated into a single work package/lane, decomposed **by file,
not by error category**, to avoid a parallel-lane ownership collision.
