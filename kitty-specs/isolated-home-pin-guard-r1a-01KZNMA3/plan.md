# Implementation Plan: R1a — the guard half: freeze the `SPEC_KITTY_HOME` behaviour class

**Branch**: `feat/isolated-home-pin-guard` | **Date**: 2026-08-10 | **Spec**: [`spec.md`](spec.md) @ `96b2b0910`
**Input**: Mission specification from `kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/spec.md`

**Branch contract** (deterministic, from `setup-plan --json`): current branch `feat/isolated-home-pin-guard`;
planning/base branch `feat/isolated-home-pin-guard`; merge target `feat/isolated-home-pin-guard`;
`branch_matches_target: true`. Nothing in this Mission merges (C-013).

**Spec status**: CLOSED at `96b2b0910` after five passes, a three-lens post-spec gate (13 blockers) and an
independent population reproduction. This plan does not re-open requirements. Where planning found a spec
defect it is recorded in **§7 Spec findings** and referred to the operator — not silently repaired and not
worked around by weakening a criterion.

---

## Summary

R1a installs a census-backed AST guard that reds when the 40-member `SPEC_KITTY_HOME` behaviour class
changes, plus a canonical owner giving a legitimate 41st member a green path. It adopts nothing,
adjudicates nothing, deletes nothing, and edits no existing test module.

The technical approach is one shared, root-parameterised scanning module (`tests/architectural/_home_pin_scan.py`)
authored by WP-0, which every other package **imports and never re-implements**; a mandatory byte pre-filter
in front of `ast.parse`; a frozen 40-row census plus a key-set hash baseline held in a second file; and a
set-equality guard `discovered == census ∪ E` with `|E| = 2` fixed by type and by hash.

WP-0 is a **gate, not a package of convenience**: it measures the forward catch rate `R` over
`709a595 → 5d49d31ed` and publishes a machine-readable verdict. `r < 50%` halts the Mission pending
operator sign-off. No other package may begin until the verdict reads `proceed` or `proceed-degraded`.

## Technical Context

**Language/Version**: Python 3.12.13 (repo floor 3.11; the measurement venv is 3.12.13)
**Primary Dependencies**: stdlib `ast`, `pathlib`, `hashlib`, `tokenize`; `PyYAML` (census/baseline I/O);
`pytest >=9.0.3,<9.1` (`pyproject.toml:102`); `pytest-xdist` (`--dist loadfile`);
`specify_cli.contracts.anchoring.composite_key` re-exported via `tests/architectural/_ratchet_keys.py` (C-012)
**Storage**: two checked-in YAML artefacts — `tests/architectural/census/spec_kitty_home_pin_R1a.yaml`
(40 rows) and `tests/architectural/spec_kitty_home_pin_baseline.yaml` (census key-set hash + `E` hash +
tombstones). No database, no runtime state.
**Testing**: pytest, red-first per DIR-034. Guard behaviour is proved over **synthetic trees** via FR-009's
root parameter, never by mutating a real test module (C-001). Owner behaviour is proved **behaviourally**
(SC-011, SC-012), never inferred from source.
**Target Platform**: local dev + CI `arch-adversarial` pole, `blacksmith-4vcpu-ubuntu-2404`,
3-shard matrix, `-n auto --dist loadfile`, `if: always()`, no path filter (`ci-quality.yml:2024-2035`).
**Project Type**: single project; test-tree-only change. **No file under `src/` changes.**
**Performance Goals**: guard ≤ **6 s** warm ×3, gating (NFR-001); coverage proof ≤ **90 s** warm, separable
from NFR-001's budget but **not** separable from CI (NFR-002); key-indirection empty-set assertion negligible.
**Constraints**: C-001 (no test module edited), C-003 (AST never text search), C-004 (never narrow the
silhouette), C-006 (blast radius), C-007 (census entitles nothing), C-011 (published key sets, never counts),
C-012 (`composite_key`, repo idiom), C-013 (nothing merged, no issue created).
**Scale/Scope**: 2737 `.py` under `tests/`; 100 byte-hit files; 191 write sites; 40 members in 36 files.
All figures are **settled and not re-measured by this plan** (spec §0.8, independently reproduced).

**Environment (binding on every package).** The external pytest-9.0.3 venv is reused; a verified one is
`/home/jeroennouws/dev/sk-missions/3108/.venv` (`pytest 9.0.3`). **No `.venv` is created inside
`/home/jeroennouws/dev/sk-missions/3121`.** Never a bare `uv run` or `uv sync`.
`.pytest_cache/spec-kitty-test-venv/` is built by the suite's own fixture and is not ours to touch.

**Destructive gate instructions — read and refused.** Two gates in this repo emit instructions that would
destroy work, and every package must refuse them:

| Gate | Instruction it emits | Why refused | What to do instead |
|---|---|---|---|
| `scripts/docs/check_docs_freshness.py` (`DOCS-INDEX-DRIFT` `suggested_action`) | `PYTHONPATH=. uv run python scripts/docs/docs_index.py --write` | A bare `uv run` re-syncs the environment and destroys a hand-built venv; it has already cost mission `sync-sleep-count-3136` four rebuilds | Run the same script with the external venv's interpreter directly, or leave the finding and report it |
| `spec-kitty agent tasks` / `move-task` guidance (`src/specify_cli/cli/commands/agent/tasks_parsing_validation.py:808`) | `git restore --source <branch> --staged --worktree -- kitty-specs/` | Overwrites the worktree copy of `kitty-specs/`, destroying uncommitted spec/plan/tasks work | Commit first with explicit-path `git add`, then reconcile by hand; never run the restore |

Both were read at the cited locations during this planning pass. Neither was executed.

## Charter Check

*GATE: passed before Phase 0. Re-checked after Phase 1 — see §8.*

**Namespaces, because they collide**: `DIR-005/006/007/010/011/012/013` are **project** directives from
`.kittify/charter/charter.md` (which stops at DIR-013); `DIR-024/025/030/034/041` are **built-in** doctrine
directives from the agent profile. A reader resolving DIR-024 against the project charter finds nothing.

| Rule (namespace) | Bearing on R1a | Status |
|---|---|---|
| DIR-005 / DIR-034 — tests for new functionality, test-first | Every guard behaviour lands red-first over a synthetic tree | PASS |
| DIR-006 / NFR-004 — `mypy --strict`, `ruff check`, no new suppression | `_home_pin_scan.py` is fully annotated; `Member` and `Exempt` are frozen dataclasses; `E` is `tuple[Exempt, Exempt]` | PASS |
| DIR-007 — docstrings for public APIs | The shared module's public seam (§3) is docstringed, including the no-second-copy rule | PASS |
| DIR-012 — tracker ticket assigned to the HiC before implementation | #3121 is OPEN and already assigned to `MOES-Media` (verified via `gh issue view 3121`) | PASS — no action needed |
| DIR-013 / C-009 — pre-existing reds reported, not fixed or absorbed | Baseline-red classification applies; any red encountered is attributed against the merge-base before being called ours | PASS |
| DIR-024 / DIR-025 — locality, boy-scout only when safe and local | The one out-of-blast-radius edit (`tests/_arch_shard_map.py`) is mandatory, not opportunistic — see §7.2 | PASS with recorded rationale |
| Canonical sources, never improvise | Plan built from `spec-kitty next` / `agent context resolve` / `setup-plan`; census follows `tests/architectural/census/`; keys follow `_ratchet_keys.py`; guard follows the sole-door idiom | PASS |
| ATDD-first (C-011) — assert against published key sets, never counts | **RESOLVED — see §7.1.** The independent reproduction is recovered, checked in verbatim and named in C-011 | PASS |
| C-012 — the canonical key expresses every member distinctly | **RESOLVED by interpretation — see BLOCKER-1.** The 40 members yield only **19** distinct *bare* `composite_key`s (**21** surplus rows, **29** members invisibly removable); the path-qualified 3-tuple every authority C-012 names already uses yields **40** | PASS via C-012 as interpreted |
| DIR-041 (built-in) — tests fail when the contract breaks; no pass-for-the-wrong-reason | **This is the directive under which the gate's B3-B8 findings are defects rather than style.** Population-0 assertions now ship positive controls; SC-001's 19-element anchor, SC-002's ignorable `prefilter` parameter and SC-007's self-comparison are all closed | PASS after remediation |
| DIR-030 (built-in) — tests and typecheck gate before handoff | `ruff check` + `mypy --strict` on every touched file, and the guard's own budget gate blocks merge via `timing-nfr-serial` | PASS |
| Terminology Canon — Mission, not feature | Followed throughout | PASS |
| No merge, no issue creation (C-013) | No `gh pr merge`, `git merge`, un-drafting or `gh issue create` in any package | PASS |

## Project Structure

### Documentation (this mission)

```
kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/
├── spec.md              # CLOSED at 96b2b0910
├── plan.md              # This file
├── research.md           # Phase 0 — OD-001/OD-002/OD-003 discharge and the repo findings
├── research/
│   └── spec_kitty_home_pin_evidence/   # C-011's artefact: clf.py, step3.py, members.json, README.md
├── data-model.md         # Phase 1 — Member, Exempt, CensusRow, Baseline, Verdict
├── contracts/
│   └── home-pin-scan-seam.md   # The shared module's public surface (the anti-drift contract)
├── quickstart.md         # Regeneration + verification commands
└── tasks/                # NOT created by /spec-kitty.plan
```

### Source Code (repository root)

```
tests/
├── conftest.py                                    # WP-a: owner added STRICTLY AFTER line 298
├── _arch_shard_map.py                             # WP-b: shard rows for every new arch test file
└── architectural/
    ├── _home_pin_scan.py                          # WP-0: THE shared module (enumerator, resolver,
    │                                              #        scope-chain silhouette, discover(),
    │                                              #        census + baseline generators, __main__)
    ├── census/
    │   └── spec_kitty_home_pin_R1a.yaml           # WP-c: 40 rows, generated, header-documented
    ├── spec_kitty_home_pin_baseline.yaml          # WP-c: census key-set hash + E hash + tombstones
    ├── test_spec_kitty_home_pin_guard.py          # WP-b: the guard + the eight SC-006 transitions
    ├── test_spec_kitty_home_pin_prefilter.py      # WP-b: OD-002 form (a) + SC-002b
    ├── test_spec_kitty_home_pin_budget.py         # WP-b: SC-007 — `timing`-marked, timing-nfr-serial
    ├── test_spec_kitty_home_pin_census.py         # WP-c: real-tree discovered == census ∪ E
    ├── test_home_owner_behaviour.py               # WP-a: SC-011 (i)(ii), SC-012 limb 1
    ├── test_home_owner_never_wins.py              # WP-a: SC-012 limb 2 — the ONE exempt real-tree member
    └── _home_pin_gate.py                          # WP-0: the one-shot gate driver (git/subprocess live
    #                                                     HERE, never in _home_pin_scan.py — C2)
docs/adr/3.x/2026-08-1X-N-<halt-path>.md           # WP-0 or WP-d: the halt-path ADR (C-006)
```

**Structure Decision**: everything lands under `tests/architectural/` because OD-004 is settled by
measurement — that tree runs in the always-on `arch-adversarial` pole on 100% of pushes and PRs. Every new
module is a **top-level** `tests/architectural/*.py`, including the two probes: the shard assignment table
is documented as keyed *"by whole test-file (for `tests/architectural/*.py`) or whole directory (for the
other three pole roots)"*, so a `tests/architectural/probes/` subdirectory sits in the ambiguous gap between
those two keying rules. Flat placement removes the ambiguity at zero cost. **Synthetic trees are NOT checked in**: they are materialised into `tmp_path` at test time from source
strings and reached through FR-009's root parameter. A checked-in `_`-prefixed directory would be skipped by
**pytest collection** but still walked by the **classifier**, whose enumerator is bound to every `.py` under
the root and never narrowed — so its deliberate 41st members would land in `discovered` and
`discovered == census u E` could never green (B7).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Editing `tests/_arch_shard_map.py` — **OPTIONAL balance-control pinning** | The explicit tables are the *authoritative balance control*. Pinning R1a's files keeps the three shards balanced rather than hash-scattered. | **The first version of this row was WRONG and is withdrawn.** It claimed *"there is no alternative"* because a new file with no row reds the completeness guard. False: `tests/_arch_shard_map.py:419` sets `default_fallback=True` and `tests/_shard_registry.py:181` hash-buckets any unregistered under-root file, so a new file is auto-covered — the module's own docstring says *"no manual table edit is required just to keep main green."* The alternative is simply **not editing it**, which stays green. |
| WP-0 owns the shared module end to end, where §0.8 says WP-b "then extends" it | FR-004(2) already requires both artefacts to be emitted by that module, so WP-0 owning the generators removes WP-c's only reason to touch it — and removes a shared-file conflict from the parallel section | Leaving the generators to WP-b/WP-c means two packages editing one module concurrently, which is the drift `_sole_door_scan.py:13-27` records as a live incident. **Accepted by the operator as a deliberate strengthening.** |

---

## Implementation Concern Map

> Implementation concerns are not work packages. `/spec-kitty.tasks` translates them.

### IC-01 — The shared scanning module and its anti-drift seam

- **Purpose**: build one importable scanner — enumerator, byte pre-filter, binding resolver, scope-chain
  silhouette, `discover()`, and the census/baseline generators — so that no second copy of the predicate
  can exist anywhere in the tree.
- **Relevant requirements**: FR-001, FR-002, FR-004(2), FR-009, FR-010, C-003, C-004, C-012, §0.8.
- **Affected surfaces**: `tests/architectural/_home_pin_scan.py` (new, sole owner WP-0);
  `contracts/home-pin-scan-seam.md`.
- **Sequencing/depends-on**: none — this is the first thing built, before the gate can be measured.
- **Risks**: this repository has a **live drift incident on record** — `_sole_door_scan.py:13-27` documents
  Gates 4 and 5 each rolling an independent, drifting copy of the same primitives, Gate 4's having already
  lost Gate 1's docstring rationale. Prose ("WP-b imports it") did not prevent that and will not prevent
  this. The seam is therefore mechanised — see §3.


> **Key type settled by BLOCKER-1** (an interpretation of C-012, not an amendment): `Member` carries the `MemberKey` 3-tuple plus a non-authoritative `lineno`, and the key is formed at the **write site**, at the boundary, from the record.
### IC-02 — The forward-catch-rate gate and its verdict artefact

- **Purpose**: measure `R` (arrivals **within the effect class**) across `709a595 → 5d49d31ed` by running
  the shared `discover()` at both SHAs and differencing the site sets keyed by `composite_key`; apply the
  rename detector, the `|R| ≥ 10` visibility floor, ±1 stability over **consequence classes**, and the
  pre-committed widening schedule; publish a machine-readable `verdict:`.
- **Relevant requirements**: SC-000, §0.9, FR-008, C-003, C-012.
- **Affected surfaces**: the verdict artefact under `kitty-specs/<mission>/`; the halt-path ADR.
- **Sequencing/depends-on**: IC-01.
- **Risks**: `r < 50%` **halts the Mission**. The implementer may not proceed on their own authority. The
  window is non-tunable; the widening schedule is fixed in the spec before its own measurement, and every
  attempted window — including discarded ones — is published. `:1165` is the named boundary case and must
  not be resolved silently: the write test is on the **call**, receiver-agnostic, and `mp` is bound by a
  `with ... as` item rather than an `ast.Assign`. **The rationale once attached to that is FALSE**: measured,
  removing `withitem` binding entirely still finds all 40 members and still admits `:1165`. What admits it is
  **receiver-agnosticism on the call**; a receiver-*qualified* matcher is what would drop it and bias `r`
  toward *proceed*.


> **Key type settled by BLOCKER-1.** This concern differences site sets *keyed by the member key*; under the bare 2-tuple the rename detector would mis-pair arrivals against departures **across files**, which is the exact dependant §7 named. Also split per C-2: the driver is `_home_pin_gate.py`, importing `discover` — `subprocess`/`git` never enter the budgeted module.
### IC-03 — The canonical owner

- **Purpose**: one fixture in `tests/conftest.py`, non-autouse, function-scoped, **returning `None`**
  (which is the fixture's contract, and is load-bearing for SC-012's non-circularity — a fixture that returns
  its own path invites comparing the environment against the fixture's own report). **`tuple[str, str]` types
  `E`'s ENTRY, not the fixture** — asserting both of the fixture is unsatisfiable (FR-005). Establishes the
  home by `monkeypatch.setenv` only, added **strictly after
  line 298**, never overriding a definition that keeps its own pin.
- **Relevant requirements**: FR-005, FR-006, NFR-005, NFR-006, SC-005, SC-010, SC-012, C-005.
- **Affected surfaces**: `tests/conftest.py` — the **only** edit to an existing file in the Mission.
- **Sequencing/depends-on**: IC-02 (its first task asserts WP-0's `verdict:` before doing anything else).
- **Risks**: inserting above line 253 would shift `_isolated_worker_home`'s position in the module's
  definition order and change
  conftest fixture ordering **while its old line range shows no modification** — so the diff-shaped check
  alone is satisfiable with the risk untouched. SC-010's AST assertion on the **ordered list of definition
  names** — not a scalar definition index, which the tasks layer names as a failure mode — is the real
  check. The owner is **itself a class member** under FR-001; that is why `discovered == census ∪ E` is the
  only correct form, and excluding it by predicate would require the narrowing C-004 forbids.

### IC-04 — The guard, the exemption set, and the eight transitions

- **Purpose**: assert `discovered == census ∪ E` with `E` fixed-arity by type and pinned by a hash held
  outside the guard module; mechanise direction (limb (a)'s per-row `frozen_at_sha` equality is **struck** —
  `frozen_at_sha` is a header scalar under FR-003 and a per-row equality is no longer expressible; its load is
  **inherited by limb (b)'s shrink-only key-set hash**, and removing (b) is barred while (a) is struck; a
  shrink-only key-set hash plus an explicit tombstone list); prove all eight SC-006 transitions and SC-004
  and SC-013 over synthetic trees.
- **Relevant requirements**: FR-004, FR-009, FR-011, SC-004, SC-005, SC-006, SC-013, **C-002** (no counted
  definition-of-done — the eight transitions assert sets, never the number 40), C-007.
- **Affected surfaces**: `test_spec_kitty_home_pin_guard.py`, `test_spec_kitty_home_pin_budget.py`,
  synthetic trees **materialised into `tmp_path` at test time** (never checked in — B7), and optionally
  `tests/_arch_shard_map.py` for balance pinning.
- **Sequencing/depends-on**: IC-01, IC-02. **Not** dependent on IC-03 — see §4.
- **Risks**: the census-equality assertion over the **real** tree cannot green until the owner (IC-03) and
  the retained-pin probe both exist. Keeping that one assertion out of this concern (it belongs to IC-06)
  is what makes IC-03 and IC-04 parallelisable. The tempting shortcut when it reds is a subset-only
  ratchet, which SC-004's synthetic tree exists specifically to fail.


> **Key type settled by BLOCKER-1**, and this concern now owns the **eighth** SC-006 transition (a deliberate bare-key collision pair) plus the **verdict gate test** that blocks every package.
### IC-05 — The pre-filter's proof obligations

- **Purpose**: prove the byte pre-filter over-selects (OD-002), and prove its unstated premise — that the
  env key is a literal at the call site — by the empty-set assertion of SC-002b.
- **Relevant requirements**: FR-002, NFR-002, SC-002, SC-002b, C-003 forms (i) and (ii).
- **Affected surfaces**: `test_spec_kitty_home_pin_prefilter.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: no precedent for an executable pre-filter proof exists in this repository — the two shipping
  byte pre-filters (`_sole_door_scan.py:461-476`, `test_commit_target_kind_guard.py:186-188`) both argue
  soundness in a comment and prove nothing. R1a sets the precedent. **Neither OD-002 form closes the
  key-indirection hole**; SC-002b is separate, unconditional, and is the only check that can falsify the
  premise.

### IC-06 — The frozen census, its baseline, and the real-tree equality

- **Purpose**: emit the 40-row census and the baseline file from the shared module's generator; assert the
  real tree satisfies `discovered == census ∪ E`.
- **Relevant requirements**: FR-003, FR-004, SC-001, SC-003, **C-002** (40 and 36 are content published as
  key sets, never thresholds), C-007, C-011.
- **Affected surfaces**: `census/spec_kitty_home_pin_R1a.yaml`, `spec_kitty_home_pin_baseline.yaml`,
  `test_spec_kitty_home_pin_census.py`.
- **Sequencing/depends-on**: IC-03 **and** IC-04 (both `E` entries must exist for the equality to green).
- **Risks**: the natural implementation of "a checked-in hash" is `sha256(file.read_bytes())`, and that is
  **wrong**: FR-004 pins a hash of the **sorted key set**, not of the file. Hashing bytes would make an
  `owed_to` re-point or a header edit red the guard with no tombstone legitimately available — converting a
  documentation edit into a fake adjudication. See §5.


> **Key type settled by BLOCKER-1.** The census schema also changes under A1: `frozen_at_sha` and `owed_to` become **header scalars**, and rows gain `home_partition` (effect, rule imported per BLOCKER-2) beside `kind` (shape).
### IC-08 — CI landing requirements (the guard must actually RUN)

- **Purpose**: make the conditions under which the guard executes in CI explicit, because they are the
  difference between a gate and a decoration, and `/spec-kitty.tasks` reads this map — not the narrative.
- **Relevant requirements**: OD-004, NFR-001, NFR-003, SC-007.
- **Affected surfaces**: every new module's module-level `pytestmark`; optionally `tests/_arch_shard_map.py`.
- **Sequencing/depends-on**: none — but IC-04, IC-05 and IC-06 are **not done** until it holds.
- **The six limbs OD-004's "100% of pushes and PRs" actually rests on**:
  1. **A selected marker.** The pole selects `-m '<arch_shard_N> and not windows_ci and (git_repo or
     integration or architectural) and not timing'`, so each module must declare **at least one of
     `architectural`, `integration`, `git_repo`** — `architectural` is the correct one. No conftest hook
     applies it. Declare it **module-level**, not per-function.
  2. **A shard marker**, which `default_fallback=True` supplies automatically; an explicit row in
     `tests/_arch_shard_map.py` is **optional** load-balance pinning (see Complexity Tracking).
  3. **`E`'s seed must not trip the positional-anchor ratchet.**
     `tests/architectural/test_ratchet_positional_anchor_ban.py::test_no_int_line_sink_in_architectural_python_seeds`
     walks every `tests/architectural/**/*.py` and flags an int literal reaching the second positional
     argument of `composite_key_from_file(path, N)`, **including a module-level seed constant embedding a
     positional `path:NNN` anchor** (#2564 clause). The cheapest form of `E` trips it. Compliant form:
     `E`'s entries are content-addressed `MemberKey` 3-tuples, and any `lineno` used in a recomputation
     comes from `discover()` at runtime, never from a literal in the seed. **Found in §7.5 and never
     folded back into this concern map, which is what every code WP actually reads.**
  4. **Not a zero-gate orphan.** `test_gate_coverage.py::test_no_new_orphan_surfaces` is a hard ratchet with
     an **empty** committed baseline, so every new test file must be selected by at least one job.
  5. **Neither `pr:deferred` nor `pr:skip-ci`** is set on the PR.
  6. **A docs-only PR takes the narrowing branch** (`-m '<shard> and docs_scoped and not windows_ci'`,
     tolerating exit code 5) — benign here, since a docs-only PR cannot mutate `tests/`.
- **Plus placement**: every module lands **flat** at `tests/architectural/*.py`; the shard table is keyed by
  whole test-file for that glob or by whole directory for the other three pole roots, and a subdirectory
  falls between those rules.
- **And the budget gate**: SC-007's wall-clock test is `timing`-marked and therefore runs in
  `timing-nfr-serial` (`-m timing -n0`, always-on, merge-blocking), not in the pole.
- **Risks**: each limb is individually cheap and collectively invisible. Limb 1 is the one that silently
  turns the whole Mission into a no-op.

### IC-07 — The reduced record and the two corrections

- **Purpose**: update #3121 with the three separately labelled reach figures, the retraction of 26.06%, the
  census-is-not-a-manifest distinction and its reviewer test, §0.3's provenance correction, the statement
  that R1a adjudicates nothing, and — **unconditionally** — `r`, `|R|`, `|R_f|`, both window SHAs, every
  attempted window, and the machine-readable band verdict.
- **Relevant requirements**: FR-008, SC-009, C-013.
- **Affected surfaces**: issue #3121 (comment only — `gh issue comment`, never `gh issue create`); the
  Mission record.
- **Sequencing/depends-on**: IC-02 (for the gate outputs) and IC-06 (so the record reports what shipped).
- **Risks**: the publication obligation is unconditional, not degraded-band-only — the first revision made
  it invisible by enumerating four items that did not include `r`. D-1 and D-2 are **not** in R1a: both
  target files exist only on `spike/isolated-home-3121`, C-013 bars merging, so there is no in-scope path
  to either. They are carried to R1b.

---

## 1. OD-001 — which tracker reference `owed_to` names

**Decision: `#3121`, on all 40 rows.**

**Evidence.**

- `gh issue view 3121 --json number,title,state,labels,assignees` returns `state: OPEN`, assignee
  `MOES-Media` (Jeroen Nouws), labels `priority:P2` + `tech-debt`, title
  *"test(isolation): the 22 `_isolated_home` fixtures are a name collision, not a duplicated seam —
  converge only the provable class"*. The issue is live, assigned, and its subject **is** the adjudication
  R1b will perform — so it is a creditor, not a placeholder.
- R1a is barred from creating issues (C-013). The alternative in OD-001 — "a ticket the operator opens
  before WP-c lands" — makes WP-c's landing depend on an operator action outside the Mission's control, and
  a row whose `owed_to` names a not-yet-minted number resolves to nothing. OD-001 names that exact failure:
  *"a row whose `owed_to` resolves to nothing is a row with no creditor, which is indistinguishable from a
  permanent one."*
- `^#[0-9]+$` (FR-003) admits `#3121` and rejects the struck `SK-12-also-pins-home` shape.

**Consequence deliberately made cheap.** All 40 rows carrying one creditor is not a hedge — if the operator
later opens an R1b-specific issue, re-pointing `owed_to` is a **regeneration, not a hand-edit** (FR-004(2)),
and because the baseline hash is over the **sorted `composite_key` set** and not over the file (§5), a mass
re-point changes no hash and needs no tombstone. That property is what makes this decision reversible at
zero cost, and it is an argument *for* deciding now rather than deferring.

**What this decision cannot see**: whether #3121 is the right *scope* for 40 distinct adjudications.
SC-003 already says so — it can only check that `owed_to` is a well-formed reference and not prose.

## 2. OD-002 — how C-003 form (i) is discharged, and at what strength

**Decision: form (a), both-passes set identity, under NFR-002's 90 s budget. No hybrid.**

**Evidence, and why the hybrid was the tempting wrong answer.**

The case for the hybrid — (b) in the always-on pole, (a) marked — rests entirely on a premise that CI
measurement falsifies. The premise is that "separable and non-gating" (NFR-002) means (a) would not run on
a normal PR, leaving the pre-filter unproved in practice. Read directly at
`.github/workflows/ci-quality.yml`, the always-on `arch-adversarial` pole selects

```
-m '<arch_shard_N> and not windows_ci and (git_repo or integration or architectural) and not timing'
```

so a module under `tests/architectural/` carrying `pytestmark = pytest.mark.architectural` and **no**
`timing` marker runs on 100% of pushes and PRs. Form (a) measured **≈18.6 s** locally
(17.64 s unfiltered + 1.003 s pre-filtered, spec §0.6) against a 90 s budget. It needs no new marker, so
no `pytest.ini` edit (which would be a second out-of-blast-radius file, and is guarded by
`test_marker_registry_single_source.py`).

**"Separable" therefore means separable from NFR-001's budget, not separable from CI.** With that
established, (b) buys nothing: it is strictly weaker, it *assumes the member set it is meant to help
establish* — the circularity C-011 names — and shipping it alongside (a) creates a cheap green whose only
function, the day (a) gets slow on a runner, is to be the thing someone keeps while deleting the strong
one. That is NFR-002's own stated defeat: *narrowing or skipping (b) to fit (a) relocates the defeat into
the proof of the guard.*

**Implementation shape that makes (a) honest.** Both passes must come from **one** classifier called twice,
`discover(root, prefilter=True)` and `discover(root, prefilter=False)`, so the comparison cannot degenerate
into two implementations agreeing with each other. The pre-filter is a parameter of the shared module, not
a separate code path.

**Stated limitation, carried into the criterion.** Both passes run the same classifier, so if it cannot see
key-indirection members neither pass finds them and the symmetric difference is empty *by construction*.
With respect to that hole, 90 s buys nothing over 0.056 s. **SC-002b is the only check that can falsify the
premise**, it is unconditional, and it is not substitutable by either form.

**Budget note recorded, not exploited.** NFR-002 carries no explicit "may be raised with evidence" clause,
where NFR-001 does. If (a) exceeds 90 s on `blacksmith-4vcpu-ubuntu-2404` under `-n auto` contention, the
same rule applies by analogy — **raise the budget with runner evidence; never narrow the walk, never drop
to form (b)**. Recorded in §7.5 as a spec asymmetry rather than assumed.

## 3. The shared-module seam — how "imports, not re-implements" is made enforceable

The spec's instruction (§0.8) is *"WP-0 must ship them as one importable module that WP-b then extends,
never as a parallel implementation cross-checked for agreement,"* and cites `_sole_door_scan.py:13-27` as a
live drift incident rather than a hypothesis. Prose is what failed there. The seam is therefore three
things, in increasing order of teeth:

**(3a) The gate driver is a SEPARATE MODULE, and the predicate module stays pure.** `_home_pin_scan.py`
holds the predicate, the resolver, `discover()` and the generators — **no `subprocess`, no `git`** — because
collected tests import it under a 6-second budget on every PR. The **window measurement** (git-archive
extraction at two SHAs, the rename detector, ±1 stability, banding, the 5-attempt widening schedule,
verdict emission) lives in a separate one-shot driver, `tests/architectural/_home_pin_gate.py`, which
**imports `discover`**. The first pass shipped the gate as
`python -m tests.architectural._home_pin_scan --gate`, which puts `subprocess`/`git` on the import path of
that budgeted module, and none of that half appeared in the seam's nine symbols, the Project Structure
tree, C-006, or the anti-drift teeth. The gate is a **consumer**, exactly as (3d) already framed it. Its
surface is contracted and it is named in C-006. This preserves the no-second-copy-of-the-predicate
property completely — the driver owns no predicate.

**(3a-bis) One writer per phase.** `tests/architectural/_home_pin_scan.py` is authored **end to end by WP-0**,
including the census and baseline generators and the `__main__` regeneration entry point. WP-b may extend
it with guard-only helpers. **WP-c never edits it** — WP-c *invokes* the generator. This is a deliberate
strengthening of "WP-b then extends": FR-004(2) already requires both artefacts to be emitted by this
module, so putting the generators in WP-0 removes the only reason WP-c would have to touch it, and removes
a shared-file conflict from the parallel section of §4.

**(3b) A published contract, not a docstring.** The public surface is fixed **in one place only** —
`contracts/home-pin-scan-seam.md` — before either consumer exists. **The table that used to be duplicated
here is deleted.** It had already drifted from the contract inside a single planning pass: this document
published `render_census`/`render_baseline` as `(members, *, sha, exempt) -> str` while the contract gives
`render_census(members, *, sha, owed_to)` and `render_baseline(members, *, exempt)`, and **neither
generator took the parameter list published here.** The anti-drift document drifting from its own
contract is the argument for one copy, made against itself. *(A1 also changes `owed_to`'s role: it is now
a census header scalar, so the contract's generator signatures are the authority on how it is passed.)*

**(3c) A guard on the guard — the mechanism.** An arch test asserts, by AST, that **no module under
`tests/` other than `_home_pin_scan.py` contains a second implementation of the predicate**: concretely,
that `test_spec_kitty_home_pin_guard.py`, `test_spec_kitty_home_pin_prefilter.py` and
`test_spec_kitty_home_pin_census.py` contain **zero** `ast.parse` calls and **zero** `ast.NodeVisitor`
subclasses, and obtain everything through `from tests.architectural._home_pin_scan import ...`. This is
cheap, it is AST rather than text (C-003), and it converts the §0.8 instruction from an intention into a
red. It is the answer to "plan the seam": the seam is not the import, it is the test that makes the import
the only option.

**(3d) WP-0 is its own first consumer.** The gate (IC-02) obtains `R` by extracting each window SHA's
`tests/` with `git archive` into a temp directory and calling `discover(root=<extracted>/tests)` — so
FR-009's root parameter is **exercised by WP-0 before WP-b depends on it**, and the two-SHA measurement is
proof that the seam works, not a claim that it will.

## 4. Sequencing and parallelism

```
WP-0  (gate + shared module)                         ── gates everything
  │
  ├── WP-a  (owner in tests/conftest.py)          ─┐  parallel, disjoint files
  ├── WP-b  (guard, E, pre-filter proofs, probes) ─┘
  │
  └── WP-c  (census + baseline + real-tree equality)   needs BOTH WP-a and WP-b
        │
        └── WP-d  (record: #3121, ADR)                 last, reports what shipped
```

**Why WP-a ∥ WP-b is safe — corrected: files were disjoint, CONTRACTS were not.** The first pass assigned
`test_home_owner_behaviour.py` and `test_home_owner_never_wins.py` to **WP-b**, and both request the owner
that **WP-a** adds to `tests/conftest.py`. Disjoint files, coupled contracts — and that absent contract is
why the `return None` / `tuple[str, str]` conflict (B9) survived planning in the first place.

**Both owner probes move into WP-a**, whose remaining content is now: the owner, the two probes, and
**`contracts/canonical-home-owner.md` as its FIRST deliverable** — fixing name, scope, `autouse`, the yield
type (`None`, and the reason: it forces the probe to compute `str(tmp_path / "home")` itself instead of
comparing the environment against the fixture's own report), and precedence. WP-b's remaining content is
then entirely FR-009-rooted, so this costs nothing.

WP-b proves all **eight** SC-006 transitions, SC-004 and SC-013 over **synthetic trees materialised into
`tmp_path`** (FR-009), which is exactly what FR-009 was written for: *"without this, SC-004 has no
C-001-compatible demonstration path."* The real-tree `discovered == census ∪ E` stays in WP-c. WP-b is
therefore green on its own branch without WP-a.

**Why WP-c cannot start early on content but can on structure.** The 40 census rows depend only on the
frozen SHA and are generatable immediately after WP-0. The *assertion* needs both `E` entries. So WP-c's
artefacts are authorable in parallel; its test is not. Sequencing WP-c after both is the honest read.

**There is no shared-file conflict, and the design that solved one is deleted.** The first pass had
WP-b pre-write WP-c's shard row to avoid a concurrent edit to `tests/_arch_shard_map.py`. That conflict
does not exist: `default_fallback=True` auto-covers any unregistered file, so **no package needs to edit
the table at all**, and any editing that happens is optional balance pinning that can be done once, last,
by whoever lands last. Deleted rather than kept "just in case" — a mechanism defending against an
impossible failure is indistinguishable from one defending against a real one, and the next reader
cannot tell which they are looking at.

**Every new arch test module must declare a selected marker at module level** — the pole selects
`(git_repo or integration or architectural)`, `architectural` is the correct one, and **no conftest hook
applies any of them**. Without one the guard is collected and then deselected on every PR, which silently
falsifies OD-004's conclusion. Now carried as **IC-08**, because `/spec-kitty.tasks` reads the concern map
and not this paragraph. See §7.3.

**The verdict gate is a COLLECTED TEST, not "WP-a's first task".** SC-000 says *"WP-a...WP-**d** may not
begin"*, but the only mechanism the first pass gave was a task on WP-a — written when WP-a was next in
line, and then left standing when §4 made WP-a and WP-b **concurrent**. IC-04 listed no verdict task at
all, so a WP-b implementer could build the entire guard on a `halt` verdict. It now ships as a test that
**reds until the published artefact reads `proceed` or `proceed-degraded`**, which gates all four packages
at once and cannot be skipped by whichever one starts first. A published HALT is still a halt (SC-000).
*(The pass that bought parallelism relocated the gate one level over — the lineage's signature defect,
committed by the mechanism that was meant to catch it.)*

## 5. The direction mechanism — what the hash is over

FR-004 requires *"a checked-in hash of the sorted freeze-time key set"*. The natural implementation is
`sha256(census_path.read_bytes())` and it is wrong in a way that is expensive to discover late:

| Hash over | `owed_to` re-point | Header/comment edit | Row removal | Row addition |
|---|---|---|---|---|
| File bytes | **reds**, no tombstone honestly available | **reds** | reds → tombstone | reds |
| **Sorted `composite_key` set** (correct) | passes | passes | reds → tombstone | reds |

Hashing bytes turns a documentation edit into a fake adjudication — the only way to green it is to write a
tombstone for a member that was never adjudicated, which is precisely the entitlement C-007 forbids.
**Bind: the baseline hash is `sha256` over the sorted, newline-joined `MemberKey` TRIPLES — `(rel_path,
enclosing_qualname, normalized_token_line)`, never the bare 2-tuple BLOCKER-1 refused — computed by
the shared module's generator, and the guard recomputes it from the census and compares** (FR-004(3)).
`E`'s hash is over its own sorted entry set and lives in the same baseline file — a **different file from
the census**, so the pin is never editable in the same hunk as its subject.

`E` and the census get **different co-edit rules**, and the asymmetry is load-bearing: any delta to `E` or
its hash reds unconditionally (`E` never legitimately changes, in R1a or R1b), while a census delta reds
unless a tombstone accounts for it (a blanket both-touched rule would forbid R1b's entire job). Git-state
inspection is not used — it does not survive rebase or squash; content comparison does.

## 6. How the plan lives with the `:1165` fragility

`tests/sync/tracker/test_tracker_egress_refusal_3108.py:1165` is held in the class **only** by an unused
`monkeypatch` parameter on its enclosing test — the sole such case of the 40. `ruff`'s `ARG` is relaxed for
`tests/**` (confirmed at `pyproject.toml`, `[tool.ruff.lint.per-file-ignores] "tests/**" = ["ARG", "S",
"E402"]`), so no automation flags it and a human will eventually delete the token. Behaviour is unchanged;
membership is not. C-001 bars repairing it and C-004 bars widening the predicate to catch it (inferring the
silhouette from *usage* rather than declaration is a larger change than R1a should make).

**The plan does not repair it. It makes its red legible, and pre-writes the adjudication.** Three parts:

1. **Confirm the failure direction is safe.** When the token goes, the member leaves the class, `discovered`
   loses a key, and `discovered == census ∪ E` **reds on a stale census row** (US1 AS-3). It is not a blind
   spot — it is a spurious red on a behaviour-preserving edit. That is the correct polarity and needs no
   change.
2. **Make the red diagnosable, which is the actual work.** A stale row is ambiguous between *the member was
   deleted* and *the member fell out of the silhouette while its pin remains*. The classifier can
   distinguish these for free: for any stale row, re-run the **effect limb alone** (does a site in that file
   still write `SPEC_KITTY_HOME` to `tmp_path/"home"`?) and emit
   `site still present, silhouette no longer satisfied — this is NOT an adjudication` versus
   `site absent — deleted`. Without that, the cheapest green for a confused contributor is a tombstone,
   which records an adjudication that never happened.
3. **Record it where FR-003 puts rationale — the census file header, not a `reason` column.** The header
   names `:1165` as the single known-fragile row, states that its membership rests on an unused parameter,
   and gives the instruction: *if this row goes stale with the site still present, the repair is neither a
   tombstone nor a predicate change — it is an R1b adjudication.* This follows
   `census/verdict_seam_IC01.yaml`, whose header carries exactly this kind of load-bearing prose while the
   rows stay data. It survives the reviewer test — the note entitles the definition to **nothing** and
   changes no check's outcome.

The related receiver form that *would* produce a miss — `pytest.MonkeyPatch.context()` — already landed in
this same window in #3108 and satisfies the predicate only because the write test is receiver-agnostic and
applies to the call — and **that receiver-agnosticism, not `withitem` binding, is what admits `:1165`**:
measured, removing `withitem` binding entirely still finds all 40 members. A receiver-*qualified* matcher is
what would drop `:1165` from `R` and bias the gate toward *proceed*.

## 7. Spec findings

Statuses are current as of the second planning pass. Items marked **FIXED IN SPEC** were corrected under
explicit operator authorisation; **BLOCKER-1** is new, is not fixed, and is not mine to fix.

### BLOCKER-1 (RESOLVED by interpretation) — `composite_key` is not unique across the 40 members, and the guard was blind to 29 of them

**Measured, using the repository's own primitive against the C-011 evidence artefact** (AST throughout, no
text search):

| | |
|---|---|
| Member sites | **40** |
| Distinct bare `composite_key` values | **19** |
| Distinct `(path, composite_key)` values | **40** |
| Surplus rows lost to collapse (40 − 19) | **21** |
| **Members that can be removed INVISIBLY** (any member of a class of size >= 2) | **29** |
| Largest collision class | **11 members** sharing `('_isolated_home', 'monkeypatch . setenv ( , str ( tmp_path / ) )')` |
| Colliding keys | **8** (sizes 11, 5, 3, 2, 2, 2, 2, 2) |

`composite_key`'s `normalized_token_line` **strips string literals** — verified directly: the site at
`tests/cli/commands/test_sync_commands.py:55` normalises to `monkeypatch . setenv ( , str ( tmp_path / ) )`
with both `"SPEC_KITTY_HOME"` and `"home"` removed. Combined with `enclosing_qualname`, and with 22
identically-named `_isolated_home` fixtures in the tree (the subject of #3121's own title), collision is not
a corner case — it is the dominant case.

**What breaks, concretely:**

1. **FR-003 is unsatisfiable as written.** "40 rows, one per measured member" keyed by `composite_key`
   cannot exist; a set keyed that way has 19 elements.
2. **FR-004's ratchet inverts.** `discovered == census ∪ E` over 19-element key sets is **blind to the
   removal of any of the 29 members that sit in a collision class** — delete one of the 11 and the key
   set is unchanged, so **the guard greens on a removal**. That is exactly what the tombstone mechanism
   exists to catch. **Three distinct figures, published separately because they mean different things:
   19 distinct keys / 21 surplus rows / 29 invisibly-removable members.** The first pass of this plan
   published `21` as the invisibly-removable count, which is the surplus — its own operand table sums
   to 29 (11+5+3+2x5). That was this pass's instance of the §7.4 shape, inside the finding whose
   subject is derived figures that do not follow from their rules.
3. **US1's thesis fails for the most likely 41st member.** A new `_isolated_home` fixture of the same shape
   — the single most probable form of new member — leaves the key set unchanged, so **SC-006 transitions
   3, 4, 5 and 7 do not red.**
4. **SC-001's anchor is VOID, not merely pending — the worst consequence, and the first pass missed it.**
   The published key set has **19** elements, so a classifier that finds exactly **one** member per
   collision class discovers 19 members and produces the **same 19-element set** — SC-001 green. C-011
   cannot distinguish a 40-member classifier from a 19-member one, which is **strictly worse than the
   tune-until-40 failure C-011 was written to prevent.** The first pass recorded C-011 as PASS and
   C-012 as BLOCKER on the same Charter Check table; they were one finding.
5. **The 3-tuple is not injective either — at MEMBER level the collision population is 0.** Over all **191** sites the
   guard walks: **190** distinct 3-tuples, one collision class of two —
   `tests/paths/test_runtime_root_spec_kitty_home.py:91,93`, a definition carrying the **full**
   `(tmp_path, monkeypatch)` silhouette whose two `setenv` sites collapse because `"one"` and `"two"`
   are stripped. It is a non-member only because those values are not `tmp_path/"home"` — **one string
   literal away from being two members with one key**, in a file named
   `test_runtime_root_spec_kitty_home.py` — **neither site is a member, so the member-level collision
   population is 0**: hazard real, status not live. Closed by an **import-time exactly-one assertion at
   MEMBER level** over `discover()`'s output. **Not** by `assert_descriptor_unique_within_qualname` per
   member, which WP01 measured raising on **11 of the 40** because literal-stripping collapses
   `_isolated_home`'s three consecutive `setenv` calls into one token line where only one is a member —
   a guard prescribed for the wrong population, this Mission's most-repeated defect.

**The resolution is inside C-012 itself, which is why this is reported rather than decided.** C-012 has two
clauses that now disagree. It says *"Keys use `composite_key` — `(enclosing_qualname,
normalized_token_line)`"*, and it also says *"the guard follows the repo's **sole door** idiom
(`tests/architectural/_sole_door_scan.py`)"*. That idiom is **already path-qualified**:
`ConstructionSite(rel_path, qualname, token, lineno, …)` at `_sole_door_scan.py:524-529` carries `rel_path`
beside the key components. The sibling idiom that uses a bare key (`test_trio_seam_only.py:710`) operates
over `src/`, where qualnames are near-unique.

So `(rel_path, enclosing_qualname, normalized_token_line)` satisfies both halves of C-012, matches the
precedent C-012 names, and measures 40/40 distinct. It also preserves C-012's stated motive — expressing
two pin sites inside one definition — for every case except two *byte-identical* sites in one definition,
whose population the evidence artefact measures at **0** ("members with >1 site: 0"). C-012 chose its key
to solve a problem with population 0 and thereby adopted one that cannot separate 21 live members.

**Resolved by the operator as an INTERPRETATION of C-012, not an amendment to it** — all three authorities
C-012 names already use the path-qualified 3-tuple for row identity: `_sole_door_scan.py:87`
(*"`rel_path`/`qualname`/`token` form the authoritative composite key"*, `lineno` explicitly
non-authoritative), `_ratchet_keys.py`'s *"Key shape — reuse, not fork"* docstring
(`CompositeKey = tuple[str, str, str]`), and `tests/architectural/surface_resolution_audit/audit.py:90-91`. All three verified present on this
branch and quoted verbatim during the path sweep. C-012's
parenthetical is a gloss on the **primitive's return type**, not a row-identity rule. C-012 is not
reopened; its **justification sentence is corrected**, because *"an improvised `(file, qualified_name)`
cannot express two pin sites inside one definition"* is measurably false of the 3-tuple, which carries
the token line. A single `MemberKey` type alias now types all four dependent rows.

**And the line the key is formed at is BOUND: the write site, never the definition.** Measured, the two
readings produce 40-row censuses with **zero overlap** (19 write-site keys against 21 def-line keys),
and under the def-line reading C-012's whole motive collapses. **C-004 governs membership attribution,
not site identity**: `enclosing_qualname` returns the innermost *dotted* qualname, which is correct for
identity precisely because it contains the whole chain — at `:1165` it is
`test_bind_counter_wrapper_changes_no_outcome_committed_red._run_once`, the one member of the 40 whose
anchoring qualname differs from the evidence artefact's keyed-def `qual`. Left unstated this is a coin
flip, and `:1165` is the site it lands on.
Everything downstream — `data-model.md`'s `Member.composite_key`, the census schema, the baseline hash
input, the rename detector's difference key, and WP-0's gate measurement, which differences site sets
"keyed by `composite_key` (C-012)" and would therefore mis-pair arrivals against departures across files —
depends on the answer.

### BLOCKER-2 (RESOLVED) — `home_partition`'s rule was not undefined; it was on another branch, keyed on another variable

This pass's self-reported defect. The diagnosis was right about the symptom and **wrong about the cause**,
and the correction is the more useful finding.

**What I reported**: `home_partition` had no derivation rule in R1a — `B2` occurred exactly once in the
whole specification, in the row I wrote, and the resolver's limbs produced no partition.

**What was actually true**: the rule is defined *precisely*, at
`spike/isolated-home-3121:.../evidence/ablation/VERDICT.md:38-41` — **A** does not re-pin `HOME`, **B1**
re-pins it to `tmp_path/"home"`, **B2** to `tmp_path/"user-home"`. I could not cite it for two compounding
reasons: it is **not on this branch**, and it keys on a **second environment variable**. My observation that
"the resolver's specified limbs produce no partition" was correct — and the reason was not a missing rule
but a variable the scanner never enumerated.

**Operator ruling, implemented:**

1. **FR-001's walk now resolves two variables.** `SPEC_KITTY_HOME` decides membership; `HOME`, under the
   same three-form receiver-agnostic write test and the same A2-widened value resolution, decides
   `home_partition` over each member's own scope chain. New limb, so it ships a **positive control** (B6).
2. **The byte pre-filter stays sound, and the argument is now stated rather than assumed**: a member's scope
   chain lies entirely within one file, so every `HOME` write that can change its partition sits in the same
   file as that member's `SPEC_KITTY_HOME` write — a byte-hit file by construction. No widening needed, and
   widening is explicitly not permitted as a substitute for the argument.
3. **M4's evidence is imported verbatim** to `research/m4_ablation_evidence/` (`VERDICT.md`, `TABLES.md`,
   `RESIDUALS.md`), `sha256`-pinned, extracted with `git show` — **no merge, rebase or cherry-pick** — and
   cited by path from FR-003 and C-006.
4. **Cross-checked, and it is a second external anchor.** Measured over the current 40: **A = 27, B1 = 11,
   B2 = 2**. Against M4's independent per-member labels: **intersection 28** (measured, not assumed — it
   could have been smaller, since the 28 were identified under the superseded predicate), **28 agreements,
   0 disagreements**. The delta decomposes exactly: the 10 members from the limb drop are **all `test-body`
   and all `A`**; the 2 from #3108 are **both fixtures and both `B1`**.
5. **17/9/2 of 28 stays labelled as the superseded frame and is not R1a's figure.** That honesty flag was
   correct and survives.

**And the import falsified a published figure.** §0.3 said *"the `HOME` orphaned-binding trap rose from 7 to
9"*. M4 measures B1 = **9** over its 28, and both arrivals are B1 — so the trap went **9 to 11**, low by two
at both endpoints. It had been cited in prose for five passes against a definition living on another branch.
§0.3's companion claim, that both arrivals are B1, is **verified** by the same measurement.

**The residual, and it is the general lesson**: a citation that resolves only on a branch the Mission is not
on is C-011's failure mode wearing a file path — a reviewer cannot check it. See §7.7.

**The second self-report from the same decision is also closed.** Hoisting `frozen_at_sha` to a header
scalar let me strike FR-004(a) with the justification *"nothing for it to catch"* — true **only because**
limb (b)'s shrink-only key-set hash independently reds on an added row. FR-004 now **names the inheriting
mechanism at the strike site**, records that (a) was a **redundant** defence rather than a vacuous one, and
**bars removing (b) while (a) is struck**, so the same reasoning cannot be applied twice to leave nothing.

### 7.1 RESOLVED — C-011's evidence artefact, recovered and checked in

The first planning pass found that C-011's artefact had never been checked in, leaving SC-001's anchor
circular. **The operator recovered the post-spec gate's independent reproduction, and it is now checked in
— C-011 is satisfied, and the one-shot oracle the first pass proposed is dropped entirely.**

**Path, which is what C-011 literally requires and what no commit had satisfied**:
`kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/research/spec_kitty_home_pin_evidence/` — instrument
`clf.py`, producer `step3.py`, evidence `members.json` (40 entries), all **verbatim** and `sha256`-pinned
in that directory's `README.md`. The directory is now named in C-006.

**Why it is strictly better than the oracle.** It was authored by the post-spec gate's independent third
lens from the specification's predicate text alone, never compared against the spec author's classifier
before publication, and it reproduced every headline figure on the first run with no tuning. The oracle's
stated residual — *"one agent reading one spec twice reproduces its own misreadings"* — does not apply.

**Verified during this pass, not taken on trust:**

- Re-running `step3.py` on this tree rewrites `members.json` **byte-for-byte identically**.
- `git diff --stat 5d49d31ed HEAD -- tests/` is **empty**, so the tree it measured is byte-identical to the
  one on this branch and the figures are checkable today without a checkout.
- It reproduces 40 members / 36 files, the 30/10/0 kind split, 39 under innermost attribution with the
  symmetric difference exactly `:1165`, and 30 under the superseded decorator-limbed predicate.
- Its `clf.py` binds `ast.withitem` receivers, so the `pytest.MonkeyPatch.context()` form resolves — the
  §0.8 requirement — though measured, `withitem` binding is not what admits `:1165`; receiver-agnosticism on
  the call is, and the `withitem` *resolution* limb has real-tree population 0.

**Consumption, and why it is not circular.** `members.json` carries `(path, qual, line, sites)`, not keys.
The identification of *which* 40 sites are members is external — it comes from this artefact. The key
*encoding* is derived at test time by the repository's own `composite_key_from_file`, a pure function of
`(file, lineno)` supplied by the repo rather than by R1a's classifier. One source of truth is kept by
deriving rather than checking in a second normalised copy. **See BLOCKER-1: that derivation does not yield
40 distinct keys, and the key type has to be settled before SC-001 can be written.**

**Both first-pass deviations dissolve.** The oracle is gone, and with it the unauthorised scope and the
C-006 gap it created.

### 7.2 FIXED IN SPEC — C-006's blast radius omitted `tests/_arch_shard_map.py`, which the Mission cannot avoid editing

OD-004 settles the guard's home as `tests/architectural/` *"with a shard assignment in
`tests/_arch_shard_map.py`"* — but C-006's enumerated blast radius (*"Limited to: …"*) does not list that
file. `tests/architectural/test_arch_shard_marker_completeness.py` asserts a **total partition**: every test
collected under the arch pole roots carries exactly one `arch_shard_N` marker. A new arch test file with no
row reds that existing guard. **~~The edit is mandatory and unavoidable.~~ WITHDRAWN — see §4 and C-006.** `tests/_arch_shard_map.py:419` sets `default_fallback=True` and `tests/_shard_registry.py:181-186` hash-buckets any unregistered under-root file, so a new arch test file is **auto-covered by construction**; the module's own docstring calls the explicit tables *"authoritative balance control, not a keep-green obligation"*. The edit is **optional load-balance pinning**. The C-006 enumeration gap this finding identified was real; the premise offered for it was not.

It does **not** violate C-001 — `tests/_arch_shard_map.py` is a registry helper, not a test module; it
collects nothing. It is a C-006 enumeration gap. **This is the same defect shape the spec's own Note
Carried to R1b describes**: OD-004 changed where the guard lives, and C-006's derived list was left
standing.

### 7.3 FIXED IN SPEC — OD-004's "runs on 100% of PRs" depended on limbs it never named

The always-on pole selects `-m '<shard> and not windows_ci and (git_repo or integration or architectural)
and not timing'`, and **no conftest hook auto-applies any of the three**. A module declaring none of them is
collected and then **deselected on every PR**, and NFR-001's budget would protect something no contributor
ever feels. Same shape again: a conclusion derived from a rule (`tests/architectural/` runs always-on) that
holds only under conditions the deriving section never states.

**Two corrections to this finding, from the post-plan gate.** The requirement is the **disjunction**, not
the `architectural` marker alone — `test_resume_non_reemission_guard.py` is selected via `git_repo` while
carrying `architectural` on one function only. And the **"161 of 164" count is withdrawn**: by AST it is
162/165 recursive and 161/164 top-level, it turns on whether a per-function decorator counts alongside a
module-level `pytestmark`, and it was a text-search figure, which C-003 bars. The qualitative claim is what
carried the argument.

Second-order, and it resolves cleanly: `not timing` excludes SC-007's wall-clock budget assertion from the
pole — correctly, because a wall-clock assertion on a contended 4-vCPU runner under `-n auto` is a flake
generator. The repository already ships the right home: **`timing-nfr-serial`**
(`ci-quality.yml:2193-2211`) runs `-m timing -n0` over `tests/` on `blacksmith-4vcpu-ubuntu-2404`, with
`if: always()`, no filter gate and no `needs:` edge, and it **is wired into `quality-gate.needs`, so a red
timing gate blocks merge**. Marking the budget test `timing` therefore gets all four properties NFR-001
needs at once: gating, serial and uncontended, on the same runner class as the guard, and always-on. §9
uses it.

### 7.4 FIXED IN SPEC — FR-001 published the innermost-attribution figures the spec elsewhere withdraws

This is the instance the brief predicted, and it is in a normative Requirements row rather than in prose.

FR-001 reads: *"The decorator limb is dropped because it was a shape key **excluding 9 effect sites against
the silhouette's 1** (§0.1a)."* But §0.1a (line 49) states *"The decorator limb excluded **10** — every one
of the ten non-fixture effect sites satisfies the superset silhouette **at its keyed def**"*, and the struck
claim at line 57 makes the provenance explicit: *"(Measured at the innermost def the figure is 9 of 10 —
the reading C-004 refuses, and the one an earlier revision published.)"* §0.1b adds that under the
scope-chain evaluation FR-001 actually binds, the silhouette limb excludes *"none at all"*.

So both of FR-001's numbers are innermost-attribution figures: under the predicate FR-001 itself binds, the
pair is **10 against 0**, not 9 against 1. It checks out arithmetically — 40 members under the current
predicate minus 30 under the superseded decorator-limbed one is exactly the 10 test-body sites.

This was the **fifth** appearance of the `30/9/1` split. The Note Carried to R1b says it *"survived four
separate publications of a document that had already changed the rule producing it"* — FR-001 made five, in
the row that binds the classifier. *(The first pass cited that quotation as "line 524" when it sits at
`spec.md:532`, and called this the fourth appearance in a sentence that then said fifth — three ways to
count one thing, in the finding about counting. Corrected.)* It changes no requirement (the predicate text in FR-001 is correct and
matches §0.8), so it is a justification defect, not a behavioural one — but an implementer who trusts
FR-001's justification over §0.1a will build the wrong intuition about which limb was doing the excluding.

### 7.5 FIXED IN SPEC — a third existing hard ratchet every new R1a test file must satisfy

`tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces` is a **hard ratchet**: no test
file may newly fall into zero CI gates, and *"since the #2296 drain the committed baseline is EMPTY by
design."* Every new module R1a adds must therefore be positively selected by at least one CI job. Under
this plan all of them are — the guard/census/prefilter/probe modules via the `architectural` marker plus a
shard row, and the budget module via `timing` — but this is a third guard that a naive landing trips, and
`tests/_arch_shard_map.py` records a prior mission doing exactly that: a file landed *"without registering
it in this shard map … main went red on both `test_arch_shard_marker_completeness` and
`test_no_new_orphan_surfaces`."* Recorded so R1a does not become the next entry in that comment.

Verified while planning that the ratchet has **no reverse limb** — the four shard tests are universe-nonempty,
exactly-one-marker, shard-union-equals-universe, and expected-groups-registered; none asserts that a row
names an existing file. **That observation stands; the design it was offered in support of does NOT.** §4's
conflict pre-emption (WP-b adds WP-c's row ahead of time) is **deleted**, because `default_fallback=True`
means no package needs to edit the table at all and the conflict it defended against cannot occur. The
reverse-limb finding survives as a fact about the shard guards; it no longer justifies anything.

### 7.7 A defect CLASS, not an instance — evidence citations that resolve only on another branch

Swept every backticked file path across `spec.md`, `plan.md`, `research.md`, `data-model.md` and
`contracts/`: **79 cited paths, 19 not resolvable on this branch.** Triaged:

| Class | Count | Verdict |
|---|---|---|
| Forward references to R1a's own deliverables (`_home_pin_scan.py`, `_home_pin_gate.py`, the census, the baseline, `contracts/canonical-home-owner.md`) | 6 | **Not defects** — they are what the Mission builds. Distinguished here so a reviewer does not chase them. |
| Relative citations that resolve from their context (`census/verdict_seam_IC01.yaml`) | 2 | **Not defects** — sweep artefacts. |
| Abbreviated but real (`surface_resolution_audit/audit.py`) | 1 | **Fixed** — written in full as `tests/architectural/surface_resolution_audit/audit.py:90-91`, and all three C-012 authorities verified present and quoted verbatim. |
| Internal cross-references inside the imported M4 files (`arm1/raw-output.txt` and siblings) | 7 | **Recorded** — the import is deliberately partial (3 of ~20 ablation files); noted in that directory's README. |
| **Genuinely dangling and load-bearing** | 3 | **See below.** |

**The three that matter**, and they are all the same class the operator identified:

1. **`docs/adr/3.x/2026-08-07-1-a-mission-halting-instrument-is-worth-its-cost.md`** — cited in `spec.md`'s
   header as the **Record of the halt**. It does not exist here; it exists on `spike/isolated-home-3121`.
   And C-006 separately lists *"the halt-path ADR"* as something R1a **writes** — so as it stood, R1a was
   set up to author a **second, divergent record of one halt** while its own header cited the first. Now
   recorded at the citation: the owning WP must **import it verbatim**, not author a new one.
2. **`home_partition`'s rule** — BLOCKER-2, now imported.
3. **`scripts/mutants/ablate_home_pin_3121.py` and `evidence/ablation/VERDICT.md`** (FR-009's corrections,
   D-1/D-2) — these were **already correctly labelled** as spike-only and deferred to R1b, so they are the
   one case the specification had handled. `VERDICT.md` is now partially imported, which does not change
   D-1's deferral.

**Why this is a class and not three accidents.** The parent Mission's entire evidence tree —
`VERDICT.md`, `HALT.md`, `P.json`, `RESIDUALS.md`, `anchor.md`, the ablation arms — exists on
`spike/isolated-home-3121`, while on this branch `kitty-specs/isolated-home-pin-convergence-01KZCTWC/`
contains **only empty directories**. Every inherited claim R1a makes points into that void. Three instances
have now surfaced one at a time, over five spec passes and two plan passes, each found only when someone
tried to *use* the citation. **The check is mechanical and belongs in the working habit: after writing a
path, confirm it resolves on the branch you are on.**

### 7.6 FIXED IN SPEC — three smaller derived-figure slips

- **Budget (b) does not derive from its own derivation.** §0.6 says *"Slowest measured both-passes figure
  (30.5 s) × 3"* and then states **90 s**. 30.5 × 3 = 91.5. The budget is 1.5 s *tighter* than its stated
  derivation. Harmless in direction (tighter, not looser) but it is a published figure that does not follow
  from its published rule.
- **NFR-002 carries no raise-with-evidence clause** where NFR-001 explicitly does, while both budgets face
  the same unmeasured-runner risk. §2 applies NFR-001's rule to NFR-002 by analogy and says so rather than
  assuming it.
- **`status.events.jsonl`'s `MissionCreated` payload still reads "31-row census" / "30-member class".** This
  is an append-only event log and correctly immutable; `meta.json` was refreshed to 40. Noted only so a
  future reader does not treat it as a live contradiction.

## 8. Charter Check — post-design re-evaluation

All rows from the pre-Phase-0 table hold after design, with one change: the ATDD-first / C-011 row is
**confirmed** as a blocker-class finding rather than a risk, and §7.1 carries its only honest discharge plus
the operator action that would strictly improve on it. Complexity Tracking now records exactly **two** deviations, and the change since the first pass matters:
WP-0 owning the shared module end to end is **accepted** (FR-004(2) already requires both artefacts to come
from that module), while editing `tests/_arch_shard_map.py` has been **re-justified as optional balance
pinning** after its original "not optional" premise was measured false (C1). The oracle deviation is gone
entirely. Neither surviving row is a licence, and each is bounded where it is stated rather than by a
forward reference.

## 9. Verification strategy

| What | How | Where it runs |
|---|---|---|
| Guard behaviour (SC-004, SC-006 ×8, SC-013) | Synthetic trees via FR-009's root parameter, red-first | `arch-adversarial`, always-on |
| Real-tree class equality (SC-001, SC-003) | `discover(tests/) == census ∪ E`, keys never counts | `arch-adversarial`, always-on |
| Pre-filter coverage (SC-002, form (a)) | One classifier, two calls, symmetric difference empty **over both variables' outputs** — members and `home_partition` | `arch-adversarial`, always-on |
| Pre-filter premise (SC-002b) | Empty-set assertion over `src/` ∪ `tests/` | `arch-adversarial`, always-on |
| Owner statics (SC-005, SC-010) | AST over `tests/conftest.py`: non-autouse, function-scoped, **returns `None`** (the `tuple[str, str]` is asserted of `E`'s entry, not the fixture), added after 298, and the module's **ordered list of definition names with the newly-added owner removed** unchanged — one known addition then exact equality, never a scalar index, and never "unchanged" outright, which FR-005 makes unsatisfiable | `arch-adversarial`, always-on |
| Owner behaviour (SC-011, SC-012) | Probe modules — real fixtures, real `os.environ` reads | `arch-adversarial`, always-on |
| `E` fixed arity (SC-005) | `mypy --strict` proves a third entry is a **type error**; the "or reds the guard" disjunction is deliberately not used | `mypy` gate |
| Budget (a) (NFR-001, SC-007) | Warm ×3 timing, `timing`-marked, plus the enumerated-file **set** equality (count reported, not asserted) | `timing-nfr-serial` — always-on, `-n0`, blocks merge |
| Parallel correctness (NFR-003) | Identical verdicts under `-n0` and `-n auto --dist loadfile`, both demonstrated | Local, both modes |
| Static gates (NFR-004, SC-008) | `ruff check` (never `ruff format`), `mypy --strict`, no new suppression | `lint` |

**OD-003 discharge — measured, not argued.** The 3× factor in NFR-001 is a measured 1.86× two-machine
spread doubled for a runner nobody has measured. The discharge is: mark
`test_spec_kitty_home_pin_budget.py` `timing`, land WP-b on the mission's **draft** PR, and read the figure
straight out of the `timing-nfr-serial` job — `blacksmith-4vcpu-ubuntu-2404`, `-m timing -n0`, always-on,
merge-blocking. Serial execution is what makes that number a measurement rather than a sample of runner
contention, and it is the same runner class the guard itself will face in `arch-adversarial`. **The budget
may be raised with that evidence. The walk may never be narrowed** — no directory filter, no filename
filter, no `except SyntaxError: continue`.

Note the residual honestly: `timing-nfr-serial` measures the guard **uncontended**, while
`arch-adversarial` runs it under `-n auto` on 4 vCPUs alongside three other workers. The serial figure is
therefore a floor, not the worst case. That is the correct trade — a contended wall-clock assertion is a
flake, not a gate — but the budget must be raised against the *serial* figure with the contention headroom
stated, not silently assumed to cover both.

**Every long command is bounded with `timeout`, and a timeout is a datum — recorded, never silently
retried** (C-013).

## 10. Reviewer guidance

**If you deep-review exactly one package, review WP-c.**

The parallelism in §4 is bought by moving the real-tree `discovered == census ∪ E` assertion out of WP-b
and into WP-c. That is the right trade — it is what lets WP-a and WP-b run concurrently, and it is what
FR-009's root parameter exists to enable — but it has a cost that is invisible from the dependency graph:
WP-c now looks like a generated data file, and generated data files get skimmed. **The single assertion
that actually proves the class is frozen lives in the package least likely to get a hard look.** WP-b, by
contrast, is all mechanism and synthetic trees, and will attract scrutiny automatically because it is
where the code is.

Specific things to check in WP-c that nothing else will catch:

1. **The baseline hash is over the sorted key set, not the file bytes** (§5). Hashing bytes passes every
   test on day one and turns an `owed_to` re-point or a header edit into a fake adjudication on day thirty.
2. **The census row count is content, not a threshold** (C-002/C-011). If the diff contains a literal `40`
   in an assertion, that is the tune-until-40 path C-011 names.
3. **`discovered == census ∪ E` is set equality, not containment.** A subset-only ratchet passes WP-b's
   synthetic trees for every transition except SC-004's, which is exactly why SC-004 exists — confirm it
   is present and reds.
4. **Every tombstone corresponds to a real adjudication.** A tombstone written to green a red is the
   entitlement C-007 forbids, wearing the mechanism that was supposed to prevent it.

And review the two `E` entries against BLOCKER-1's outcome: if the key type changes, `E`'s hash input
changes with it.

## 11. Definition of Done — stated, because §9 is not one

**§9 is a routing table: it says where each check runs, not when the Mission is finished.** Saying so
plainly, because the alternative is that every fakeability question lands on the SC set by default and the
tasks phase inherits *"the plan covered it."* R1a is done when **all** of the following hold:

1. WP-0's verdict artefact exists, `band(published) == published.verdict` passes, and the verdict reads
   `proceed` or `proceed-degraded`. The gating test is collected and green.
2. `discover(Path("tests")) == census ∪ E` over `MemberKey` 3-tuples, with `|E| = 2` fixed by type and
   pinned by a hash held outside the guard module.
3. All **eight** SC-006 transitions, SC-004 and SC-013 red-first over materialised synthetic trees, and the
   counterpart guard proves no member lives under a test-owned fixture root.
4. Every population-0 assertion has a passing **positive control**.
5. SC-002 asserts empty symmetric difference **over both variables' outputs** (members and `home_partition`)
   **and** that the two passes parsed different file sets.
6. SC-001 compares against the C-011 artefact's 40 write-site keys, and `verify.py` exits 0.
7. `timing-nfr-serial` is green with the guard inside its budget on the real runner (OD-003 discharged with
   a recorded figure, not an assumption).
8. IC-08's six limbs hold for every new module — checked by observing the guard actually run in
   `arch-adversarial` on the draft PR, not by reading the workflow.
9. `ruff check` and `mypy --strict` clean, no suppression added; #3121 carries FR-008's items.

**Not done** if any of: the census holds 40 rows keyed on the bare 2-tuple; a synthetic tree is checked in
under `tests/`; a tombstone was written to green a red; or the budget was met by narrowing the walk.

## 12. What this plan deliberately does not decide

- **The verdict.** `|R|`, `|R_f|` and `r` are WP-0's to measure and were deliberately not measured here or
  in the spec. Fixing a trigger after seeing its measurement is the failure the instrument exists to
  prevent.
- **Whether any member deserves to be a member.** Entirely R1b's. The guard's semantic content is empty by
  design: it proves the class has not changed since SHA X, and nothing else.
- **`|P|`.** Not used, not inherited, not cited (C-008).
