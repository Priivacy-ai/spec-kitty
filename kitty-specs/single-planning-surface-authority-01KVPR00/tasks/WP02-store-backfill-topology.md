---
work_package_id: WP02
title: Store + backfill MissionTopology in meta.json (mint at create, migrate, doctor)
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
tracker_refs:
- "2069"
planning_base_branch: feat/single-planning-surface-authority
merge_target_branch: feat/single-planning-surface-authority
branch_strategy: Planning artifacts for this mission were generated on feat/single-planning-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-planning-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "436701"
history:
- Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/mission_creation.py
create_intent:
- src/specify_cli/migration/backfill_topology.py
- tests/specify_cli/migration/test_backfill_topology.py
- tests/migration/test_backfill_topology_cli.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/mission_creation.py
- src/specify_cli/migration/backfill_topology.py
- src/specify_cli/cli/commands/migrate_cmd.py
- src/specify_cli/cli/commands/doctor.py
role: implementer
tags: []
---

## Profile load (REQUIRED FIRST STEP)

Before writing any code, load your governed identity:

```bash
spec-kitty profile-context --profile python-pedro
```

Adopt **python-pedro** (implementer). You own a SEAM extension on the
mission-creation + migration surfaces. You are NOT a reviewer; `reviewer-renata`
reviews this WP. Read the profile's boundaries, then read this prompt in full
before touching code. Honour the campsite-clean directive (#1970) for **touched
lines only** — do NOT extract or de-god anything (C-008).

> **Path correction recorded at /spec-kitty.tasks authoring time.** The planning
> `plan.md` sketched the new migration file as `src/specify_cli/migrate/<backfill_topology>.py`.
> The verified location of the existing `backfill-identity` precedent is
> **`src/specify_cli/migration/backfill_identity.py`** (package `migration`, not
> `migrate`), registered in **`src/specify_cli/cli/commands/migrate_cmd.py`**.
> This WP's `owned_files` therefore use `src/specify_cli/migration/backfill_topology.py`
> + `migrate_cmd.py`. Verified by `grep -rn "def backfill" src/specify_cli` →
> `src/specify_cli/migration/backfill_identity.py`, and the `@app.command(name="backfill-identity")`
> registration at `migrate_cmd.py:175`.

---

## Objective

Make a mission's **`MissionTopology` a stored, authoritative value in `meta.json`**,
not a thing re-inferred from disk at resolve time:

1. **FR-002 — Mint at create.** At `mission create`
   (`src/specify_cli/core/mission_creation.py`), write a `topology` field (one of
   the four `MissionTopology` values WP01 added) into `meta.json`, plus a
   `flattened` provenance flag (history mark, default `false`, NOT a topology
   value). Read thereafter; never re-infer.
2. **FR-003 — Backfill legacy once.** Add `spec-kitty migrate backfill-topology`
   (mirroring the `backfill-identity` precedent) that computes each legacy
   mission's topology from current on-disk/meta signals and **PERSISTS** it to
   `meta.json`. Add a `spec-kitty doctor topology --json` audit subcommand that
   reports each mission's stored (or absent) topology.
3. **FR-003 dogfooding landmine (see Context).** THIS mission's own `meta.json`
   must be backfilled with its topology BEFORE any later WP reads the stored
   field — and the backfill helper must be the single compute-once-then-persist
   shim later resolvers fall through.

You are the **second link of the linearized seam chain** (WP01 enum/predicate →
**WP02 store/backfill** → WP03 resolver). You consume the `MissionTopology` enum
+ WP01's `classify_topology` classifier; you do NOT add the resolver
(`resolve_context_for_mission` is WP03) and you do NOT touch `context.py`,
`resolution.py`, or `runtime_bridge.py`.

---

## Context

### What exists today (verified ground truth — cite, don't re-derive)

- **Mint site:** `src/specify_cli/core/mission_creation.py` →
  `create_mission_core(...)`. The `meta` dict is assembled at
  **`mission_creation.py:374-420`** ("# 6. meta.json"). It already sets
  `mission_id`, `mission_number`, `slug`, `mission_slug`, `mission_type`,
  `target_branch`, `created_at`, then **`meta["coordination_branch"] = coordination_outcome.branch_name`**
  at **`:416`**, and persists via `write_meta(feature_dir, meta)` at
  **`:418-420`** (`from specify_cli.mission_metadata import ... write_meta`).
  Your `topology` write lands **after `:416` (coordination_branch is known) and
  before the `write_meta` call at `:420`** so the persisted dict already carries it.
- **`write_meta` / `load_meta`:** `src/specify_cli/mission_metadata.py:314`
  (`write_meta`) and `:252` (`load_meta`). Use these — do NOT hand-roll a JSON
  dump for the create-path write.
- **Backfill precedent (MIRROR THIS):**
  `src/specify_cli/migration/backfill_identity.py` —
  - `BackfillResult` dataclass (`:66-91`): `feature_dir, slug, action ("wrote"|"skip"|"error"), reason, …`
  - `backfill_mission(feature_dir, *, dry_run=False) -> BackfillResult` (`:99`) —
    idempotent single-mission write (reads `meta.json`, mutates, `write_text`
    with `json.dumps(..., indent=2, ensure_ascii=False, sort_keys=True) + "\n"`).
  - `backfill_repo(repo_root, *, dry_run=False, mission_slug=None) -> list[BackfillResult]`
    (`:211`) — walks `kitty-specs/`, scopes to one mission when `mission_slug` given.
  - Idempotence law: an existing field value is **never** overwritten.
- **CLI registration precedent (MIRROR THIS):**
  `src/specify_cli/cli/commands/migrate_cmd.py:175` —
  `@app.command(name="backfill-identity")` → `def backfill_identity(...)` with
  `--json`, `--dry-run`, `--mission SLUG` options; it imports
  `from specify_cli.migration.backfill_identity import backfill_repo`, runs it,
  partitions results into `wrote/skip/error`, prints a human summary or a
  `--json` payload, and `raise typer.Exit(1)` iff any `error`.
- **Doctor subcommand precedent (MIRROR THIS):**
  `src/specify_cli/cli/commands/doctor.py:1172` —
  `@app.command(name="identity")` → `def identity(...)` with `--json`,
  `--mission`, `--fail-on`. It calls an auditor, builds a JSON report
  (`json_output` branch at `:1246-1262` writes `json.dumps(report, indent=2)`
  to stdout and exits), else renders a human table via `_print_identity_human`.
  Your `topology` subcommand follows the same `--json` / human-table shape.
- **Topology signals (for the backfill derivation):** the derivation reads
  `meta["coordination_branch"]` (None ⇒ no coord) and lanes presence via
  `read_lanes_json(feature_dir)` (`from specify_cli.lanes import read_lanes_json`,
  defined in `specify_cli/lanes/persistence.py`). WP01 provides the single
  mission-shape classifier — **`classify_topology(coordination_branch, has_lanes)
  -> MissionTopology`** — on the `mission_runtime` seam. This is a GIVEN: import
  it (`from specify_cli.mission_runtime import classify_topology`) and call it.
  **Use WP01's `classify_topology` — do NOT re-implement the 2×2 coord×lanes grid
  here.** Hand-rolling a parallel derivation is a second-authority reject (C-003:
  one authority for computing topology from signals).

### FR-002 / FR-003 verbatim (binding)

> **FR-002** — *Store the topology in `meta.json`.* `topology` MUST be minted into
> `meta.json` at `mission create` (`src/specify_cli/core/mission_creation.py`) and
> READ thereafter — never re-inferred from disk/git at resolve time. The stored
> value is authoritative; a `flattened` provenance flag records history without
> changing the shape value.

> **FR-003** — *Backfill legacy missions once.* Add `spec-kitty migrate
> backfill-topology` (mirroring the `backfill-identity` precedent) that computes
> each legacy mission's topology from the current signals and PERSISTS it to
> `meta.json`, plus a `spec-kitty doctor topology --json` audit. **Sequencing
> landmine (dogfooding):** THIS mission's own `meta.json` MUST be backfilled with
> its `topology` BEFORE any caller reads the stored field. Until a mission is
> backfilled, the shell computes-and-persists the topology exactly once via the
> legacy derivation, then reads the stored value.

### ⚠️ DOGFOODING SEQUENCING LANDMINE (read twice — this is the WP's trap)

The implement loop runs **ON a coord-topology mission** (`single-planning-surface-authority-01KVPR00`
has a `coordination_branch` in its own `meta.json`) — i.e. THIS mission exercises
the exact bug class under fix. WP03's resolver and WP04's read path will, in later
WPs, **read the stored `topology`**. If THIS mission's `meta.json` lacks the field
when they run, they read `None` and the loop wedges.

Therefore WP02 must ship a **compute-once-then-persist shim** as the canonical
fallback, and the create-path and backfill both route through it:

- Provide a single function — e.g. `ensure_topology(feature_dir) -> MissionTopology`
  — that: reads `meta.json`; if `topology` is present, returns it (no write);
  if absent, derives it once via WP01's `classify_topology` from
  `coordination_branch` + lanes presence, **persists** it to `meta.json`, and
  returns it.
- `migrate backfill-topology` walks `kitty-specs/` calling the same idempotent
  per-mission helper (`backfill_mission_topology`) — never overwriting an
  existing value.
- As part of THIS WP's DoD, run `spec-kitty migrate backfill-topology` (or the
  in-process helper) against THIS repo so `kitty-specs/single-planning-surface-authority-01KVPR00/meta.json`
  gains its `topology` BEFORE WP03/WP04 land. Capture the before/after `meta.json`
  diff as live evidence.

The fallback must compute-and-persist **exactly once** (idempotent): a second
read returns the stored value with no write. Do not leave a perpetual re-inference
arm — that re-opens the parallel-inference class C-004 forbids.

### Scope guards

- **C-008 / #2059 carve:** `doctor.py` is a god-module, but its de-godding is a
  SEPARATE follow-up mission. **ONLY ADD the `doctor topology` subcommand here.**
  Do NOT extract the doctor coord-recovery cluster, do NOT split the module, do
  NOT touch unrelated subcommands.
- **#1970 campsite:** clean only the lines you touch. No opportunistic rewrites
  of `mission_creation.py` beyond the topology write.
- **Disjoint ownership:** you do NOT edit `context.py` (WP01 — enum/predicate),
  `resolution.py` / `runtime_bridge.py` (WP03 — resolver/derivation retirement),
  or `mission.py` (WP05 — write path). Import the `MissionTopology` enum and
  `classify_topology` from the WP01 `mission_runtime` seam — both are GIVENS WP01
  provides; do NOT duplicate them.

---

## Subtasks

### T010 — `meta.json` topology schema + the compute-once-then-persist shim
Add (in a single small module — co-locate with the backfill helper in
`src/specify_cli/migration/backfill_topology.py`, or a tiny helper consumed by
both create + backfill):
- `ensure_topology(feature_dir: Path) -> MissionTopology` — read `meta.json`; if
  `topology` present and valid, return it (no write); else derive once via WP01's
  `classify_topology` (`coordination_branch` from `meta`, lanes via `read_lanes_json`),
  **persist** the string value + a `flattened: false` default (preserve an
  existing `flattened` flag if already present), and return it.
- The persisted `topology` value MUST be the enum's stable string form (use
  `MissionTopology.<X>.value` — agree the serialization with WP01's enum; do NOT
  invent a second string vocabulary).
- `flattened` is a separate boolean provenance flag, NOT a topology value
  (spec Domain Language). Never store `"FLATTENED"` as a topology.
Unit tests (pure where possible; tiny tmp-dir for the read/write): present-field
no-write; absent-field derive-and-persist; second-read idempotent no-write. The
exhaustive 4-cell classification (all four `MissionTopology` values) is asserted
in WP01's `classify_topology` unit test and in T012's backfill test (where
synthetic `coordination_branch`/lanes inputs can reach all four cells); the T010
shim test only needs to prove it round-trips the classifier's result through the
read/derive/persist path, not re-test the full grid.

### T011 — Mint `topology` at `mission create` (FR-002)
In `src/specify_cli/core/mission_creation.py`, after `coordination_branch` is set
(`:416`) and before `write_meta(...)` (`:420`):
- Compute the topology by calling WP01's `classify_topology(coordination_branch,
  has_lanes)` with the just-known `coordination_branch` and `has_lanes=False` — a
  fresh mission at `mission create` has NO `lanes.json`, so create-time
  classification only ever yields **`COORD`** (coord branch present) or
  **`SINGLE_BRANCH`** (no coord). The `LANES` / `LANES_WITH_COORD` cells are
  unreachable at create and arise only post-finalize; never force a lanes-bearing
  value here.
- `meta["topology"] = <classified>.value` and `meta.setdefault("flattened", False)`.
- Use `meta[...] = ...` / `meta.setdefault(...)` consistent with the existing
  block style (`:386-395`); persist through the existing `write_meta` call — do
  NOT add a second write.
Test (drive `create_mission_core` end-to-end in a tmp repo over asserting on a
fabricated dict): a freshly created **coord** mission's `meta.json` has
`topology == "COORD"` and `flattened == false`; a no-coord create has
`topology == "SINGLE_BRANCH"` and `flattened == false`. These two cells are the
ONLY reachable create-time outcomes — do NOT assert `LANES`/`LANES_WITH_COORD` at
create (those are exercised in WP01's `classify_topology` test and T012's backfill
test, where synthetic inputs reach all four cells).

### T012 — `backfill_topology.py` (mirror `backfill_identity.py`) (FR-003)
New file `src/specify_cli/migration/backfill_topology.py`:
- `TopologyBackfillResult` dataclass (mirror `BackfillResult`: `feature_dir, slug,
  action ("wrote"|"skip"|"error"), topology: str|None, reason: str|None`).
- `backfill_mission_topology(feature_dir, *, dry_run=False) -> TopologyBackfillResult`
  — idempotent: present-and-valid `topology` ⇒ `skip`; absent ⇒ derive via the
  T010 shim/classifier and `wrote`; corrupt/unreadable `meta.json` ⇒ `error`
  (mirror `backfill_identity`'s `json.JSONDecodeError/OSError/ValueError` guard at
  `backfill_identity.py:138`). Write with the same canonical form
  (`json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"`).
- `backfill_topology_repo(repo_root, *, dry_run=False, mission_slug=None) -> list[...]`
  — walk `kitty-specs/`, scope-to-one when `mission_slug` given (mirror
  `backfill_repo` at `backfill_identity.py:211-263`).
Tests: idempotent (run twice → second run all `skip`, no file mtime/content
change); `--dry-run` writes nothing but reports the would-write; corrupt meta ⇒
`error` result, not an exception; per-mission scoping. **Full 4-cell coverage
lives here:** synthetic missions whose `coordination_branch`/`lanes.json` signals
span all four `coord × lanes` combinations backfill to each of the four
`MissionTopology` values (`SINGLE_BRANCH`, `LANES`, `COORD`, `LANES_WITH_COORD`) —
because, unlike the create path, backfill runs on populated missions and can reach
the lanes-bearing cells.

### T013 — Register `migrate backfill-topology` CLI (FR-003)
In `src/specify_cli/cli/commands/migrate_cmd.py`, add
`@app.command(name="backfill-topology")` mirroring `backfill_identity` (`:175`):
- Options `--json`, `--dry-run`, `--mission SLUG` (same metavar/help shape).
- `locate_project_root()` guard (mirror `:232-235`).
- Call `backfill_topology_repo(...)`, partition `wrote/skip/error`, print human
  summary or `--json` payload (`{"dry_run", "summary": {...}, "results": [...]}`),
  and `raise typer.Exit(1)` iff any `error`.
Test the command via `typer.testing.CliRunner` (or invoke the registered app):
exit 0 on clean repo, exit 1 on a corrupt-meta fixture, JSON shape stable, idempotent.

### T014 — `doctor topology --json` audit subcommand (FR-003)
In `src/specify_cli/cli/commands/doctor.py`, add `@app.command(name="topology")`
mirroring `identity` (`:1172`):
- Options `--json`, `--mission` (`--fail-on` OPTIONAL — only add if cheap; the FR
  asks for an audit, not a CI gate).
- Read each mission's stored `topology` (and `flattened`) WITHOUT re-inferring —
  report the **stored** value, and surface `topology: null` for missions not yet
  backfilled (so the audit drives the backfill).
- `--json` branch writes `json.dumps(report, indent=2)` to stdout (mirror
  `:1246-1262`); human branch prints a small table (mirror `_print_identity_human`
  shape, but keep it minimal — do NOT pull in the full identity machinery).
- **C-008: ADD ONLY this subcommand.** No de-godding, no module split, no edits
  to `identity` or the coord-recovery cluster.
Test: a repo with one backfilled + one un-backfilled mission reports the stored
value for the first and `null` for the second; `--json` shape stable; `--mission`
scoping works.

---

## Branch Strategy

Planning artifacts for this mission were generated on
`feat/single-planning-surface-authority`. During `/spec-kitty.implement` this WP
may branch from a dependency-specific base (WP01's tip, since you consume the
enum/classifier), but completed changes MUST merge back into
`feat/single-planning-surface-authority` unless the human explicitly redirects the
landing branch. Do NOT push to `origin/main`; do NOT open a PR from this WP.

---

## Definition of Done (NON-FAKEABLE)

A reviewer must be able to reproduce each item; "the code looks right" is NOT done
(live-evidence standing rule).

1. **FR-002 mint, witnessed.** A freshly created coord mission's `meta.json`
   contains `topology` set to the correct `MissionTopology` value AND
   `flattened: false`. Evidence: run `create_mission_core` (or `spec-kitty`
   create flow) in a tmp repo and `cat meta.json` showing the field — not a
   unit assertion on a fabricated dict alone.
2. **FR-003 backfill, persists + idempotent.** `spec-kitty migrate
   backfill-topology` on a repo with a legacy (no-`topology`) mission WRITES the
   computed value; a SECOND run reports all `skip` with byte-identical
   `meta.json` (capture `sha256sum meta.json` before/after the second run, equal).
3. **FR-003 audit.** `spec-kitty doctor topology --json` emits valid JSON listing
   each mission's STORED topology (and `null` for un-backfilled). Paste the JSON.
4. **Dogfooding landmine cleared.** THIS repo's
   `kitty-specs/single-planning-surface-authority-01KVPR00/meta.json` has a
   `topology` field after this WP (run the backfill against this repo). Show the
   `git diff` of that meta.json adding `topology`.
5. **Compute-once law.** The fallback shim derives-and-persists exactly once; a
   repeat read does not re-derive or re-write (test proves no second write).
6. **Disjoint + carve respected.** Diff touches ONLY the four `owned_files`. No
   edits to `context.py` / `resolution.py` / `runtime_bridge.py` / `mission.py`.
   `doctor.py` diff is the single new `topology` subcommand (+ minimal render
   helper) — no de-godding, no module split (C-008).
7. **Tests for every new branch (Sonar gate).** T010–T014 each ship focused tests
   executing the new helpers/branches directly (idempotence, dry-run, corrupt
   meta error arm, four-cell classification, CLI exit codes). New-code coverage
   ≥ project gate.
8. **NFR-004 clean.** `ruff check .` and `mypy` zero issues/zero warnings on
   new/changed code; cyclomatic complexity ≤15 (extract small helpers in the CLI
   callbacks rather than letting them grow); no new S1192 (hoist the repeated
   `"topology"` / action-string literals to module constants); NO suppressions
   added.
9. **Suite green.** `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile` passes
   (or only pre-existing unrelated reds, verified via cross-base diff). Run the
   terminology guard if any prose changed:
   `pytest tests/architectural/test_no_legacy_terminology.py`.

---

## Risks

- **R1 — Re-inference creep (C-004).** The compute-once shim must NOT degrade into
  a permanent "if no field, derive from disk every call" arm. If WP03/WP04 read a
  missing field, the correct fix is "ensure it was backfilled", not "always
  re-derive". Persist once; read thereafter.
- **R2 — Serialization mismatch with WP01.** The stored string MUST equal the
  enum's `.value` exactly, or WP03's resolver won't round-trip it. Agree the
  vocabulary with WP01 (import the enum; don't hardcode strings).
- **R3 — `flattened` mistaken for a topology.** `flattened` is a boolean
  provenance flag. Never store `"FLATTENED"` as `topology`; the four values are
  `SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD` only.
- **R4 — Overwriting on backfill.** Idempotence is sacred: an existing valid
  `topology` is never rewritten (mirror `backfill_identity`'s skip-on-present).
- **R5 — Scope bleed into doctor de-godding (C-008).** Resist refactoring
  `doctor.py` while adding the subcommand. Touched lines only.
- **R6 — Lanes signal at create time.** A brand-new mission has no `lanes.json`,
  so create-time classification yields `COORD`/`SINGLE_BRANCH`; `LANES_*` arises
  only after finalize. Backfill (which runs on a populated mission) is where
  lanes-bearing values appear. Don't force a `LANES` value at create.

---

## Reviewer Guidance (reviewer-renata)

- **Verify the live evidence, not the prose.** Demand the `cat meta.json` after a
  real create, the before/after `sha256sum` proving backfill idempotence, the
  `doctor topology --json` output, and the `git diff` of THIS repo's meta.json
  gaining `topology`. Reject a static-reading sign-off (C-002 spirit).
- **Confirm the precedent was mirrored, not improvised.** `backfill_topology.py`
  must structurally echo `backfill_identity.py` (same dataclass/action vocabulary,
  same canonical JSON write, same repo-walk + `--mission` scoping). A hand-rolled
  parallel migration framework is a reject (canonical-sources discipline).
- **Check the classifier source.** The 2×2 grid logic must come from WP01's seam,
  not be re-implemented in WP02. A second copy of the coord×lanes derivation is a
  reject (C-003 — one authority).
- **Confirm compute-once.** There must be a test proving the second read does not
  re-write. A perpetual re-inference arm is a structural reject (C-004).
- **Enforce the carve.** The `doctor.py` diff must be ONLY the `topology`
  subcommand + a minimal render helper. Any de-godding / module split / unrelated
  edit is a reject (C-008).
- **Boundaries.** Diff must stay inside the four `owned_files`. Any edit to
  `context.py` / `resolution.py` / `runtime_bridge.py` / `mission.py` is a
  cross-WP boundary violation.
- **Gates.** `ruff`/`mypy` zero; complexity ≤15; no new S1192; every new branch
  has a direct test. Incorrect doc/path references are blocking, not advisory.

## Activity Log

- 2026-06-22T15:20:49Z – claude:opus:python-pedro:implementer – shell_pid=419668 – Assigned agent via action command
- 2026-06-22T15:33:47Z – claude:opus:python-pedro:implementer – shell_pid=419668 – WP02 done: ensure_topology compute-once shim + backfill_topology.py (mirror backfill_identity) + migrate backfill-topology + doctor topology. Mint at create via WP01 classify_topology (COORD/SINGLE_BRANCH reachable). Tests: 16 unit + 6 CLI + 5 doctor + 2 create = all pass (56 incl precedents). ruff/mypy/C901 clean diff-scoped exit 0. DOGFOOD: backfilled THIS mission on PRIMARY -> topology=lanes flattened=false; idempotent (2nd run skip sha256 byte-identical); doctor topology --json confirms. Owned files byte-identical lane-base vs feat (conflict-free) so --force safe; lane NOT rebased per flat-mission guidance. NOTE: primary meta.json write is OUTSIDE the lane - NOT committed from lane, flagged for orchestrator.
- 2026-06-22T15:34:30Z – claude:opus:reviewer-renata:reviewer – shell_pid=436701 – Started review via action command
- 2026-06-22T15:39:51Z – user – shell_pid=436701 – FR-002 mint via WP01 classify_topology (COORD/SINGLE_BRANCH reachable cells only) + FR-003 backfill_topology.py mirrors backfill_identity (idempotent, canonical JSON, never-overwrite) + migrate backfill-topology CLI + doctor topology read-only audit. C-003/C-008 respected. Both live mutation-checks RED (overwrite-backfill, re-infer-doctor). ruff/mypy/C901 clean diff-scoped; 29 tests pass. Scope = only 4 owned files (WP02 commit 9fbe17c69); other diff = inherited WP01/WP00. --force for known-benign lane-base divergence (owned files identical at base).
