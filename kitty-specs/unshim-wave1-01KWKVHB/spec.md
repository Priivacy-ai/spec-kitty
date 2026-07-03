# Mission Specification: Unshim Wave 1 — category_4 shim deletion + category_7 orphan triage

**Mission Branch**: `tidy/unshim-wave1`
**Created**: 2026-07-03
**Status**: Draft — **Revision 2** (post-spec squad folds applied 2026-07-03: renata APPROVE-WITH-FOLDS ×5, paula 3-WP single-lane shape + delete/drain atomicity, randy related-surfaces verdict "legitimately thin — fold only ~13 LOC doc hygiene"; scope verdict: NO-FOLD on #2290/#2291, thinness is structurally proven by the green bidirectional dead-module gate)
**Input**: Operator directive: first slice of the tidy-first unshim cluster (#2289–#2293, parent epic #1797) per the HiC "Tidy first" ruling — execute #2289 (delete the 8 category_4 backcompat re-export shims) and #2292 (adjudicate + execute the 6 category_7 grandfathered orphans). Pre-planning 4-lens adversarial squad (debugger-debbie, planner-priti, architect-alphonso, randy-reducer; 2026-07-03, verified on main @ cf2e91e17) census and verdicts are folded into this spec; squad-corrected facts override the issue bodies where they conflict.

## Squad-Verified Census (binding facts, override stale issue-body claims)

All 14 target modules verified present on main @ cf2e91e17 with **zero live `src/` callers** each. Degod wave-2 and gate-substrate merges touched none of them.

**Category 4 — the 8 backcompat re-export shims (#2289), 135 LOC exact.** The issue body has **4 wrong canonical-home cells**; the verified homes below are the authoritative re-anchor targets:

| Shim (delete) | LOC | VERIFIED canonical home | Test re-anchor sites |
|---|---|---|---|
| `specify_cli/acceptance_matrix.py` | 13 | `specify_cli.acceptance.matrix` | 2–3 files |
| `specify_cli/core/identity_aliases.py` | 5 | `specify_cli.identity.aliases` (issue said `core.identity` — wrong) | 0 imports + 1 symbol-allowlist row |
| `specify_cli/doc_generators.py` | 11 | `specify_cli.doc_analysis.doc_generators` (issue's `missions.documentation.*` does not exist) | 1–2 files |
| `specify_cli/doc_state.py` | 16 | `specify_cli.doc_analysis.doc_state` (same issue-body error) | 3–6 files |
| `specify_cli/gap_analysis.py` | 24 | `specify_cli.doc_analysis.gap_analysis` (same issue-body error) | 1–2 files |
| `specify_cli/state_contract.py` | 14 | `specify_cli.state.contract` | 0–1 |
| `specify_cli/tasks_support.py` | 30 | `specify_cli.task_utils` (`.support`) | **~35 sites / ~12 files, incl. 10 `patch("specify_cli.tasks_support...")` string targets** |
| `specify_cli/workspace_context.py` | 22 | `specify_cli.workspace.context` | 0 functional |

Total re-anchor effort: **~45–50 sites across ~19 test files** (the issue's "~15" is a ~3× undercount). `patch()` string targets must be rewritten to the canonical dotted path or the mock silently no-ops. Three shims (`identity_aliases`, `state_contract`, `workspace_context`) have zero importers anywhere → pure deletes.

**Category 7 — the 6 grandfathered orphans (#2292), 1453 LOC.** Squad adjudication (divergences resolved from sources — ADR text, #2124/#2131 merge state):

| Orphan | LOC | Verdict | Grounds |
|---|---|---|---|
| `specify_cli/retrospective/lifecycle.py` | 36 | **DELETE** | `LifecycleStub` Protocol has zero importers anywhere (docstring claim "gate.py needs it" is false); terminus runner shipped via live sibling `retrospective.lifecycle_events`. NOTE: #2292's "#2280 signals imminent wire" is a misread — #2280 is the uncommitted-retrospective-files bug, unrelated. |
| `specify_cli/sync/replay.py` | 357 | **DELETE** (+ its single-purpose test `test_replay_tenant_collision.py`) | Never wired since birth (2026-04-26); superseded by the landed event-sync rework (#2124 CLOSED / PR #2131 MERGED) which rebuilt the delivery/replay domain and still did not wire it. |
| `specify_cli/task_profile.py` | 155 | **DELETE** (+ `test_task_profile_suggestion.py`) | Superseded by the canonical profile-resolution surface (AgentProfileRepository + DRG lineage + model_task_routing + dispatch). Wiring it would reintroduce a second profile-routing authority (split-brain class). |
| `specify_cli/sync/tracker_client_glue.py` | 285 | **DELETE** (+ `test_tracker_bidirectional_retry.py`) | Zero callers post-#2131 merge: the event-sync mission touched the file and still left it orphaned → superseded. (Squad divergence resolved: the "active mission" defer premise was stale — #2124 CLOSED, #2131 MERGED.) |
| `specify_cli/policy/audit.py` | 88 | **KEEP → ADOPT-AS-FOLLOW-UP issue** | Real designed governance seam (append-only `policy-audit.jsonl` evidence log) with obvious intended emission points (commit_guard_hook, risk override, merge gate). Wiring is design work → file a follow-up issue; do NOT delete, do NOT wire in-mission. |
| `specify_cli/auth/transport.py` | 532 | **DOCUMENTED-DELETE, DEFERRED TO ROBERT — DO NOT TOUCH** | ADR `docs/adr/3.x/2026-05-18-2-delete-specify-cli-auth-transport.md` (Accepted) recommends DELETE but binds execution to Robert (HiC §5a.3, its C-005: the module and `test_auth_transport_singleton.py` MUST NOT be modified). #2292's "#614/#391 blocker" attribution is wrong — correct it on the issue. Living twin `auth.http.transport` is a different, live module. |

Executed deletions = **4 of 6** → meets #2292's "≥4 resolved" AC and its C-006 "≥2 per major" floor without sacrificing `policy.audit`.

**Gate/config blast radius (exhaustive; no other gate fires):**
- `tests/architectural/test_no_dead_modules.py`: drain `_CATEGORY_4_BACKCOMPAT_SHIMS` 8→0 (stale-allowlist guard hard-fails otherwise, by design) and remove the 4 deleted rows from `_CATEGORY_7_GRANDFATHERED_ORPHANS` (6→2: `auth.transport` + `policy.audit` stay).
- `tests/architectural/test_no_dead_symbols.py`: remove the symbol-allowlist row `specify_cli.core.identity_aliases::with_tracked_mission_slug_aliases` (:176) and the `sync.replay::*` ×8 + `tracker_client_glue::*` ×4 category_b rows (they become silent danglers otherwise). `_CATEGORY_B_T001_UNBLINDED` `auth.transport` rows stay.
- `tests/architectural/_baselines.yaml`: `category_4_backcompat_shims` 8→0; `category_7_grandfathered_orphans` 6→2; `category_b_grandfathered_legacy` 237→224. All shrink-only (sanctioned ratchet direction).
- `pyproject.toml`: remove the 3 dangling `[[tool.mypy.overrides]]` transitional-quarantine entries (`doc_state`, `gap_analysis`, `tasks_support`).
- **Zero** Design-P `resolution_gate_allowlist.yaml` keys and **zero** audit-inventory rows (untrusted_path / surface_resolution) point into any target — those gates do not engage.
- `src/specify_cli/next/` and the shared-package boundary are **#2291's territory** — explicitly out of scope, no collision (grep-verified).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Shim-free canonical imports (Priority: P1)

As a Spec Kitty contributor, when I search for a module I find exactly one home — the canonical one — with no backcompat re-export shims suggesting a second import path, so new code cannot anchor to retired seams.

**Why this priority**: The 8 shims are the adjudicated "removable-now" class; every day they exist is a day a new import can re-couple to them (reintroduction is the repo's most severe debt class).

**Independent Test**: `python -c "import specify_cli.tasks_support"` (and the other 7) raises `ModuleNotFoundError`; the full test suite passes with imports re-anchored to canonical homes; `_CATEGORY_4_BACKCOMPAT_SHIMS` is empty.

**Acceptance Scenarios**:

1. **Given** main with the 8 shims deleted, **When** `pytest tests/architectural/test_no_dead_modules.py` runs, **Then** it passes with `_CATEGORY_4_BACKCOMPAT_SHIMS == frozenset()` and no stale-allowlist entries.
2. **Given** the re-anchored test suite, **When** each of the 10 former `patch("specify_cli.tasks_support...")` mocks executes, **Then** it provably still intercepts: per rewritten patch site, EITHER (a) an `assert_called*`/call-count assertion exists (added if absent — most of the 10 are bare return-value redirects with no call assertion today), OR (b) a red-first proof is recorded (point the patch at a bogus target, confirm the test flips red, restore). NOTE the trap: the correct patch target is the **consumer's lookup namespace** — for a `from specify_cli.tasks_support import find_repo_root` consumer that is the consumer module's own namespace after re-anchoring, not necessarily `specify_cli.task_utils.support`.
3. **Given** the deletion, **When** `mypy` runs whole-tree, **Then** zero errors with the 3 dangling override entries removed.

---

### User Story 2 - Orphan adjudication executed, not re-litigated (Priority: P2)

As the operator, I want the 6 category_7 orphans resolved per the adjudicated verdicts (4 deletes, 1 follow-up, 1 ADR-deferred) with the tracker corrected where its claims drifted, so the census stays honest and nobody re-investigates dead modules.

**Why this priority**: 1453 LOC of orphaned code is discovery noise and split-brain bait (`task_profile` is a competing routing authority; `auth/transport.py` shadows the live `auth/http/transport.py` by name).

**Independent Test**: The 4 deleted modules and their 3 single-purpose test files are gone; `policy.audit` follow-up issue exists and is linked; #2292 carries the corrected auth.transport blocker attribution; category_7 baseline reads 2.

**Acceptance Scenarios**:

1. **Given** the 4 deletions, **When** `pytest tests/` runs, **Then** green with no orphan-test collection errors and no other test depends on the deleted tests' fixtures.
2. **Given** `auth/transport.py` untouched, **When** `git diff` on the mission is inspected, **Then** neither `src/specify_cli/auth/transport.py` nor `tests/.../test_auth_transport_singleton.py` appears in it (ADR C-005 binding).
3. **Given** mission merge, **When** #2292 is read, **Then** a comment corrects the blocker attribution (ADR 2026-05-18-2 / Robert, not #614/#391) and records the per-orphan verdict table.

---

### User Story 3 - Tracker and census coherence (Priority: P3)

As a future planner, the shim census (`_baselines.yaml`, allowlists, epic #1797) reflects reality after the wave, so Wave 2 (#2290, #2291, #2293) plans against accurate baselines.

**Why this priority**: Wave 2 planning starts immediately after; stale baselines would poison its census the way #2289's stale canonical-home cells almost poisoned this one.

**Independent Test**: `_baselines.yaml` values match the live gate counts; #1797 has a progress comment; the policy.audit follow-up is filed and cross-linked.

**Acceptance Scenarios**:

1. **Given** the merged wave, **When** `pytest tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py` runs, **Then** green with baselines 0 / 2 / 224 and no stale or dangling allowlist rows.

### Edge Cases

- A `patch()` string target rewritten to the wrong canonical path no-ops silently → acceptance scenario 1.2 requires the affected tests' own assertions to still exercise the mock.
- `tests/architectural/test_no_dead_modules.py`'s orphan detector may FLAG the canonical homes if a re-anchor is missed (imports keep a module "live"): run the full architectural suite after each deletion batch, not only at the end.
- The `doc_state` dynamic imports (`import specify_cli.doc_state as mod`) need module-object re-anchoring, not just symbol re-anchoring.
- Deleting `sync/replay.py` while `sync/queue.py:1352` keeps a `:func:` docstring cross-reference → scrub the docstring reference in the same change (doc hygiene, not a gate).
- ~12 string-literal path references to `workspace_context.py` survive in historical mission-fixture `owned_files` lists (string compares, no gate reads them) → **leave as-is**; they are immutable fixture data, and this disposition is recorded here so reviewers don't flag them as a miss.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Delete the 8 category_4 shim modules | As a contributor, I want the 8 pure re-export shims deleted so that only canonical import paths exist. | High | Open |
| FR-002 | Re-anchor all test imports to verified canonical homes | As a contributor, I want the ~45–50 test import/patch sites re-pointed to the squad-verified canonical paths (table above) so the suite is shim-free; every rewritten `patch()` site must carry an interception proof per AC 1.2 (assert_called* or red-first bogus-target flip). | High | Open |
| FR-003 | Drain category_4 gate + config residue | As a maintainer, I want `_CATEGORY_4_BACKCOMPAT_SHIMS` 8→0, the identity_aliases symbol-allowlist row removed (NOTE: that row is ALSO a `_CATEGORY_B_GRANDFATHERED_LEGACY` member — its removal is the −1 that combines with FR-005's −12 to reach category_b 237→224), `_baselines.yaml category_4` 0, and the 3 pyproject mypy-override entries removed in the same change so no gate carries ghost rows. | High | Open |
| FR-004 | Delete the 4 adjudicated category_7 orphans | As the operator, I want `retrospective/lifecycle.py`, `sync/replay.py`, `task_profile.py`, `sync/tracker_client_glue.py` deleted with their 3 single-purpose test files, the `sync/queue.py:1352` docstring xref scrubbed, and the 3 stale module paths in `docs/architecture/documentation-mission.md:899-901` re-pointed to their `doc_analysis.*` canonical homes (live doc, `doc_status: active`). | High | Open |
| FR-005 | Drain category_7 + category_b gate residue | As a maintainer, I want `_CATEGORY_7_GRANDFATHERED_ORPHANS` 6→2 and the 12 category_b rows for deleted modules removed (`sync.replay::*` ×8 + `tracker_client_glue::*` ×4); with FR-003's identity_aliases category_b row that totals −13 → `_baselines.yaml` category_7 2 / category_b 224. | High | Open |
| FR-006 | policy.audit adopt-as-follow-up | As the operator, I want a follow-up issue filed for wiring `policy.audit` into the governance emission seam (commit_guard_hook / risk override / merge gate), cross-linked from #2292, with the module and its test kept intact. | Medium | Open |
| FR-007 | auth.transport documented verdict + issue correction | As the operator, I want the mission to record the verdict "DELETE approved by ADR 2026-05-18-2, execution deferred to Robert" and a #2292 comment correcting the stale #614/#391 blocker attribution — with zero modifications to the module or its singleton test. | Medium | Open |
| FR-008 | Tracker + doc closeout | As the operator, I want #2289 and #2292 closed by the mission PR, a progress comment on epic #1797, the issue-matrix carrying terminal verdicts for every referenced issue, the executed rows in `docs/plans/degod-unshim-inventory.md` struck/marked-executed (~10 LOC), and the two untracked debt classes surfaced by the related-surfaces sweep filed as fresh issues (pre-3.0 auto-discovered-migration retirement, 87 modules compat-gated; `test_example_round_trip` legacy-contract allowlist backfill, 151 entries) — operator may veto either filing. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Full-suite green | `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile` passes on the merged mission branch; the full `tests/architectural/` sweep passes with zero staleness reds. | Reliability | High | Open |
| NFR-002 | Zero-callers invariant holds at merge | At merge time this exact check returns empty (guards against mid-mission reintroduction elsewhere on main): `grep -rnE "(from specify_cli(\.core)?(\.sync)?(\.retrospective)? )?import .*(tasks_support|acceptance_matrix|identity_aliases|doc_generators|doc_state|gap_analysis|state_contract|workspace_context|task_profile)\b|from specify_cli\.(tasks_support|acceptance_matrix|doc_generators|doc_state|gap_analysis|state_contract|workspace_context|task_profile|core\.identity_aliases|sync\.(replay|tracker_client_glue)|retrospective\.lifecycle) import" src/` — import-scoped so comments/prose don't false-positive. | Correctness | High | Open |
| NFR-003 | Static gates stay clean | Whole-tree `mypy` stays at 0 errors; `ruff check .` clean; no new suppressions anywhere in the diff. | Maintainability | High | Open |
| NFR-004 | Shrink-only ratchets | Every baseline/allowlist change in the diff is a removal or count decrease — zero additions to any exception set. | Governance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | auth.transport no-touch | Per ADR 2026-05-18-2 (HiC §5a.3): `src/specify_cli/auth/transport.py` and `tests/architectural/test_auth_transport_singleton.py` (and its unit twin) MUST NOT appear in the mission diff. | Governance | High | Open |
| C-002 | No behavior changes to live code | Deletion/triage only: no live production module changes beyond removing dead docstring xrefs; no new features, no wiring work in-mission (adopt verdicts become follow-up issues). | Technical | High | Open |
| C-003 | #2291 boundary | `src/specify_cli/next/`, `src/runtime/next/`, and `specify_cli.glossary` shims are out of scope (separate registered-removal track per HiC ruling). | Scope | High | Open |
| C-004 | Refactor-stable self-conformance | The mission's own gate edits follow the refactor-stable doctrine: allowlist drains + shrink-only ratchets, no new positive literal-presence scans, no re-pins. | Doctrine | Medium | Open |
| C-005 | Verified-canonical-homes authority | Re-anchor targets come from this spec's verified table (squad census), never from the #2289 issue body (4 wrong cells). | Process | Medium | Open |
| C-006 | Atomic delete + drain per WP | The stale-allowlist guard (`test_no_dead_modules.py:590`) hard-fails any tip where a deleted module's allowlist row survives (or vice versa). Every WP that deletes a module MUST remove its frozenset rows and decrement the matching `_baselines.yaml` keys in the SAME WP; a standalone gate-drain WP is forbidden (it would be red at tip). | Technical | High | Open |

### Key Entities

- **Category_4 shim**: a pure `from <canonical> import (...)` re-export module with zero src callers; deletion = file removal + test re-anchor + allowlist drain.
- **Category_7 orphan**: a grandfathered zero-caller module requiring an adjudicated verdict (delete / adopt-as-follow-up / deferred) before removal.
- **Stale-allowlist guard**: `test_no_dead_modules.py`'s assertion that every allowlist row matches a live orphan — the by-construction mechanism forcing gate drains to ship in the same PR as deletions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 12 modules deleted (8 shims + 4 orphans), ≈968 src LOC (135 shims + 833 orphans) + ≈539 test LOC removed; `git diff --stat` on the mission PR confirms the deletion-dominant shape (net-negative ≈−1,450 LOC after re-anchor insertions; the #2258 pre-mission prune on this branch adds a further −248). No hard LOC floor — the tables above are the accounting authority.
- **SC-002**: `_CATEGORY_4_BACKCOMPAT_SHIMS == frozenset()`, `_CATEGORY_7_GRANDFATHERED_ORPHANS` has exactly 2 entries, `_baselines.yaml` reads 0 / 2 / 224 — all verified by the architectural suite passing.
- **SC-003**: #2289 and #2292 closed by the PR; #1797 progress comment posted; policy.audit follow-up issue filed and cross-linked; #2292 blocker attribution corrected.
- **SC-004**: Zero regressions: full parallel suite + architectural sweep + whole-tree mypy + ruff all green on the merged branch, with no retry-to-green and no new suppressions.
