# Mission Specification: SPEC_KITTY_HOME Pin Census — Owner Adoption (C-011 / #3121)

**Mission Branch**: `kitty/fix-home-pin-census-owner-adoption-3121`
**Created**: 2026-08-16
**Status**: Draft
**Input**: Fix issue #3121 — the `arch-adversarial (arch_shard_3)` gate is red on
`upstream/main` and every PR because `tests/architectural/test_spec_kitty_home_pin_census.py`
detects a legitimate new `SPEC_KITTY_HOME` isolation pin the frozen census cannot represent.

## Context & Root Cause *(mandatory)*

The `SPEC_KITTY_HOME` pin census (built by mission `isolated-home-pin-guard-r1a-01KZNMA3`,
C-011, tracked by #3121) is a **hard, shrink-only ratchet** enforcing three joint invariants:
`census == anchor` (t023), `discover(tests) − E == anchor` (t023), and
`discover(tests) == census ∪ E` (t024). `discover()` walks the whole `tests/` tree for
`SPEC_KITTY_HOME` writes resolving to `<tmp_path>/home` with a `{tmp_path, monkeypatch}`
silhouette; `E` is a fixed two-entry exempt set (the canonical owner + a retained-pin probe);
the anchor is frozen from an immutable third-party evidence file
(`.../research/spec_kitty_home_pin_evidence/members.json`, 40 members, resolved at
`fe5d492ed…`). By explicit design (the R1a mission's shrink-only requirement and
constraint) the census is **monotonically non-increasing — "additions are not expressible."**

A single legitimate isolation pin landed after the freeze, in commit `1b6386b20` (#3497):

- File: `tests/cli/commands/test_sync_status_drain_blockers.py:99`
- Test: `test_queue_get_drain_blocked_counts_persists_through_drain_round_trip`
- Line: `monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))`

`discover()` correctly classes it as the "41st member," so `discover − E` (41) ≠ anchor (40)
and the gate reds (t023 ×2, t026 ×3). The pin is **necessary**: the machine
layout-generation record (`<runtime_root>/projects/.layout-generation.json`, driven by
`begin_cutover` / `publish_project_only`) is scoped to `SPEC_KITTY_HOME` as a whole, not to
the test's project UUID; per-worker HOME isolation (WP04) does not protect it, so without a
per-test home the test flakes on order (`"layout is already project-only"`). **Deleting the
pin is not an option.**

**Design-sanctioned resolution (from the R1a spec's own User Story 2, "a legitimate 41st
member has a green path"):** the census exists precisely to force new home-pinning code onto
the canonical owner. The offending test must **request the exempt `canonical_home` fixture**
(`tests/conftest.py:372`, which sets the *identical* `SPEC_KITTY_HOME=<tmp_path>/home`,
mkdirs it, function-scoped) and **drop its own `setenv`**. The test then owns no write site,
`discover()` returns to 40, and all three invariants re-green with **zero edits to any frozen
or forbidden artefact** (`members.json`, anchor, `E`, census, baseline).

Rejected alternatives (all four research lenses concur):
- **Re-freeze the anchor** — inert unless `members.json` is edited, which is "the one
  artefact this Mission did not write and must never edit to green a test." Disqualified.
- **A new "uncounted" fixture** — the scanner detects `setenv` inside a fixture; a new
  isolation fixture is itself a new member. Teaching the scanner to skip fixtures narrows the
  walk (C-003) and dulls the gate. Disqualified.
- **Re-scope the layout record** — a disproportionate production change touching
  `sync/layout_generation.py` and the whole cutover suite. Out of scope; not needed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The census gate goes green without dulling the ratchet (Priority: P1)

As a maintainer, I want the `arch-adversarial (arch_shard_3)` census gate green on `main` and
every PR, achieved by adopting the canonical `SPEC_KITTY_HOME` owner in the one drifting test —
so the gate stops blocking unrelated work while retaining full falsifiability.

**Why this priority**: This is the entire mission. The red blocks CI on every branch;
correctness of the fix (not dulling the gate) is the binding constraint.

**Independent Test**: Run `pytest tests/architectural/test_spec_kitty_home_pin_census.py`
(expect all green) and `pytest tests/cli/commands/test_sync_status_drain_blockers.py`
(expect all green), with `git status` showing only the one test file changed.

**Acceptance Scenarios**:

1. **Given** the offending test refactored to request `canonical_home` and drop its own
   `setenv`, **When** the census suite runs, **Then** all census tests pass and no frozen
   artefact (`members.json`, anchor, `E`, census `R1a.yaml`, baseline) is modified.
2. **Given** the fix applied, **When** `test_sync_status_drain_blockers.py` runs, **Then** it
   passes — the isolation the test needs is preserved by the canonical owner (fresh per-test
   `<tmp_path>/home`, fresh LEGACY layout record).
3. **Given** the fix applied, **When** a spurious new `SPEC_KITTY_HOME` pin is injected into a
   throwaway test, **Then** the census gate goes **RED** — proving the ratchet still bites.
4. **Given** the fix applied, **When** the injected pin is removed, **Then** the census gate
   returns green.

### Edge Cases

- **Owner semantics differ from the manual pin?** `canonical_home` additionally `mkdir`s the
  home; an empty home directory contains no `.layout-generation.json`, so the record is still
  absent → still resolves LEGACY. Behaviour preserved (validated).
- **Consumer keeps its own pin after requesting the owner?** The owner never overrides a
  test that manages its own home, so a residual `setenv` still counts as a member and reds.
  The fix must therefore *delete* the `setenv`, not merely add the fixture.
- **Unused params after edit?** `tmp_path`/`monkeypatch` become unused once the `setenv` is
  removed; drop them (or `del`) to satisfy ruff — matching the repo idiom
  (`del canonical_home  # the ONE SPEC_KITTY_HOME owner (R1a #3121) pins the home`).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Adopt canonical owner | As a maintainer, I want the drifting test to request `canonical_home` and drop its own `SPEC_KITTY_HOME` `setenv`, so `discover()` no longer classes it as a census member. | High | Open |
| FR-002 | Preserve test behaviour | As a maintainer, I want `test_queue_get_drain_blocked_counts_persists_through_drain_round_trip` to keep passing (fresh per-test home, LEGACY layout record), so the fix is a pure isolation refactor with no behaviour change. | High | Open |
| FR-003 | Green the census gate | As a maintainer, I want `tests/architectural/test_spec_kitty_home_pin_census.py` fully green with no frozen-artefact edits, so `arch-adversarial (arch_shard_3)` passes on `main` and every PR. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Ratchet still bites | After the fix, injecting one spurious `SPEC_KITTY_HOME`→`<tmp_path>/home` pin into any test makes the census gate red; removing it makes it green. Zero tolerance for a dulled gate. | Reliability | High | Open |
| NFR-002 | Smallest viable diff | The change is confined to a single test file; no production code, no census machinery, no frozen artefacts touched. | Maintainability | High | Open |
| NFR-003 | Static-analysis clean | The edited file passes `ruff` and `mypy` with zero new issues. | Quality | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No frozen-artefact edits | `members.json`, the anchor yaml, `E` (`_home_pin_exempt.py`), census `R1a.yaml`, and the baseline must NOT be hand-edited to green a test. | Technical | High | Open |
| C-002 | No equality relaxation | The census tests (t022–t026) must not be weakened; `census == anchor` and `discover − E == anchor` stay set-equalities, never containment. | Technical | High | Open |
| C-003 | `E` stays arity-2 | No third exempt entry; `_home_pin_exempt.py` remains `tuple[Exempt, Exempt]` and `mypy --strict` clean. | Technical | High | Open |
| C-004 | No scanner narrowing / value evasion | `enumerate_py_files` stays un-narrowed and `resolve_value` unweakened; the fix must not make a pin invisible by dodging value resolution. | Technical | High | Open |
| C-005 | No product/behaviour change | `sync/layout_generation.py` and its record scoping are unchanged (the re-scope option is explicitly not chosen). | Technical | High | Open |

### Key Entities

- **`canonical_home`** (`tests/conftest.py:372`): the one exempt `SPEC_KITTY_HOME` owner;
  sets `SPEC_KITTY_HOME=<tmp_path>/home`, mkdirs it, function-scoped, returns `None`.
- **Census / anchor / `members.json`**: the frozen 40-member evidence chain; immutable here.
- **Offending test**: `tests/cli/commands/test_sync_status_drain_blockers.py::test_queue_get_drain_blocked_counts_persists_through_drain_round_trip`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `PWHEADLESS=1 pytest tests/architectural/test_spec_kitty_home_pin_census.py -q`
  reports 0 failures (was 6).
- **SC-002**: `PWHEADLESS=1 pytest tests/cli/commands/test_sync_status_drain_blockers.py -q`
  reports 0 failures.
- **SC-003**: `git diff --stat` shows exactly one changed file
  (`tests/cli/commands/test_sync_status_drain_blockers.py`); no census/anchor/`members.json`/
  `E`/baseline diff.
- **SC-004**: Ratchet-bite proof — with one spurious pin injected the census suite fails; with
  it removed the census suite passes.
- **SC-005**: `ruff` and `mypy` on the edited file report zero issues.
- **SC-006**: `arch-adversarial (arch_shard_3)` is green on CI for the PR.
