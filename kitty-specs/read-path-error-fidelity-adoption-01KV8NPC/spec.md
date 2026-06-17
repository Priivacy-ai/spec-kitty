# Read-Path / Error-Fidelity Adoption

**Mission**: `read-path-error-fidelity-adoption-01KV8NPC`
**Type**: software-dev
**Target branch**: `feat/read-path-error-fidelity` (stacked on `feat/naming-rider-3-2-1` / PR #2012)
**Advances**: epic #1619 (runtime/state SSOT), epic #1868 (identity/read-path seam)

---

## Purpose

Robert's 3.2.0 training run (#2007) surfaced a cluster of read-path failures across six
commands. The disease is uniform: the **single typed mission-context/read-path authority already
exists** — `resolve_action_context` → `ExecutionContext` / `IdentityFragment`
(`src/mission_runtime/resolution.py:682`, `context.py:184`) — and four of the six named commands
already route through it. The failing commands fail because they **bypass it** (a second resolver
authority) or **flatten its typed error** into a generic, misleading message. This mission is
**FINISH + ADOPT, not build**: route the bypassing commands onto the existing resolver, preserve
its typed `ActionContextError` (code + checked paths) end-to-end, and make the resolver behave
equivalently across the three input classes (primary checkout, coordination worktree, submodule).

## Background — the disease

A real operator session does not see "the resolver works". It sees `next` reporting
`MISSION_NOT_FOUND` with a "run mission list" remediation when the truth is a read-path miss on a
mission that exists; `decision open` rejecting a valid coordination-aware handle; `setup-plan`
demanding `--mission` when exactly one mission is present; `spec_committed=false` on a spec that is
committed; and a submodule checkout resolving the parent repo as the project root. Each of these is
a **fidelity loss** — the typed failure the resolver produced is reclassified or swallowed before it
reaches the operator, so the remediation points the wrong way. The structural root (debbie +
alphonso): the "single resolver" is **not behavior-equivalent across input classes** (two root
resolvers; coord-only `is_committed`; fail-closed pre-read gating the primary read), and the
`ExecutionContext` composite is still **mutable + internally split-brained**
(`branch_name ≠ branch_ref.target_branch`, `resolution.py:793-801`).

**Live-evidence discipline (binding):** every PINNED root cause below was witnessed in a real run.
A bug witnessed in a real session **is not fixed because the code looks fixed** — each fix is
TDD-first with a live-repro regression test, and no referenced issue is closed on static reading.

---

## User Scenarios

### US-1 — `next` tells the truth (P0, #15)
**As** an operator running `spec-kitty next` in a checkout where the status read-path cannot be
resolved, **I want** the error to name the real failure (read-path not found, with the checked
paths) **so that** I fix the actual problem instead of chasing a non-existent "missing mission".

### US-2 — `decision open` accepts valid coord handles (#8)
**As** an operator opening a decision from a coordination-aware checkout, **I want** the canonical
read-path resolver to be the single authority that decides whether my handle resolves **so that** a
valid coord handle is not rejected by a second, divergent escape-check.

### US-3 — `setup-plan` auto-selects the only mission (#4)
**As** an operator in a repo with exactly one mission, **I want** `setup-plan` to resolve that
mission without forcing `--mission` **so that** the command matches its prompt/docs and the
exact-one ergonomics of the rest of the CLI.

### US-4 — `spec_committed` reflects reality across surfaces (#7)
**As** an operator whose spec is committed on the primary target branch, **I want** the
committed-check to consult the primary target-branch leg (not only the coordination ref/worktree)
**so that** `spec_committed` is true when the spec is in fact committed — and **I want** auto-commit
failures to surface, not be silently swallowed.

### US-5 — submodule checkouts resolve the right root (launch-blocker, #6 / #2011)
**As** an operator running spec-kitty inside a git submodule, **I want** the canonical root resolver
to stop at the submodule root **so that** mission resolution does not walk up into the parent repo.

### US-6 — typed errors survive the whole call chain (#12, #14)
**As** any caller of the resolver, **I want** `ActionContextError.code` and its `checked_paths` to
pass through every bridge/caller without reclassification **so that** `STATUS_READ_PATH_NOT_FOUND`,
explicit-resolution failures, and ambiguity errors arrive with their real code and remediation.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | **Typed-error pass-through (cheapest high-leverage cut).** `ActionContextError` (its `code` + `checked_paths`) MUST propagate from `resolve_action_context` through every bridge and command caller without being reclassified or flattened. Specifically, the `next` path MUST NOT collapse an `ActionContextError` wrapping `STATUS_READ_PATH_NOT_FOUND` into `MissionNotFoundError`/`MISSION_NOT_FOUND` (`runtime_bridge.py:3128-3134` → `next_cmd.py:469-473`). Closes #12/#14/#15 **with no resolver change.** | Approved |
| FR-002 | **`next` typed diagnostics.** When the status read-path cannot be resolved, `next` MUST report the typed code and the checked paths, with a remediation that matches the real failure class (read-path, not "missing mission"). | Approved |
| FR-003 | **`decision open` single authority.** `decision open` MUST resolve mission handles through the canonical `resolve_mission_read_path` (`decision.py:425`) ONLY. The second escape-check authority (walk-up-to-`kitty-specs`, `decision.py:86-107`) MUST be removed so there is exactly one read-path decision authority. | Approved |
| FR-004 | **`setup-plan` exact-one auto-select.** When exactly one mission is resolvable, `setup-plan` MUST auto-select it instead of hard-requiring `--mission` (`agent/mission.py:1248-1250`). Ambiguity (>1) MUST still return the structured `MISSION_AMBIGUOUS_SELECTOR` error — no silent fallback. | Approved |
| FR-005 | **`is_committed` primary-target-branch leg.** The committed-check (`missions/_substantive.py`) MUST consult the primary target-branch leg, not only the coordination ref + coord-worktree HEAD, so `spec_committed` is true when the spec is committed on the primary target branch. | Approved |
| FR-006 | **`_commit_to_branch` no silent swallow.** `_commit_to_branch` (`agent/mission.py:1178-1195`) MUST NOT silently swallow commit failures (the observed `commit_created:None` + untracked artifact). A failed auto-commit MUST surface a typed error/diagnostic; success MUST report the real commit hash. | Approved |
| FR-007 | **Submodule root unification (launch-blocker).** `resolve_canonical_root` (`core/paths.py:284-288`) MUST stop at the submodule root when invoked inside a submodule (a `.git` FILE), not walk up into the parent repo. The two root authorities (`resolve_canonical_root` vs `locate_project_root`, the latter already patched by #1944/#1965) MUST agree on the submodule case. | Approved |
| FR-008 | **#1832 verified read-path entry.** `agent action implement` MUST consume the same resolved context the claim used to create the workspace (single resolution path), eliminating the "no workspace resolved" failure on a verified read-path. This is the safe lead entry for the adoption. | Approved |
| FR-009 | **ExecutionContext builder-hardening (#1619).** The `ExecutionContext` composite MUST be internally consistent at build time: `branch_name` MUST equal `branch_ref.target_branch` (fix the split-brain at `resolution.py:793-801`). The builder MUST reject (or normalize, with a single declared rule) an internally inconsistent composite rather than emitting one. | Approved |
| FR-010 | **Charter status side-effect-free + JSON-safe (#2, partial).** `charter status`/`sync` status MUST be side-effect-free and emit one normalized hash with JSON-safe serialization. | Approved |
| FR-011 | **Single-authority adoption across the named commands.** Every command in the #2007 set (`next`, `agent context resolve`, `setup-plan`, `finalize-tasks`, `decision open`, `agent action implement`+`review`) MUST route mission/read-path resolution through the canonical resolver — no per-command second authority. Adoption is verified by deletion of the bypassing shadow paths (function-over-form). | Approved |
| FR-012 | **#1827 re-test-first (merge baseline).** #1827 MUST be re-verified by **live repro first** (debbie could not reproduce on HEAD — it may be stale). Scope (fix vs verified-already-fixed-with-regression-test) is decided by that live result, recorded in the issue-matrix. | Approved |

## Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | **Behavioral equivalence across input classes.** The resolver MUST return the same resolution outcome (or the same typed error) for the same logical mission regardless of input class (primary checkout, coordination worktree, submodule). | Verified by parameterized tests over the three real topologies; zero divergence. |
| NFR-002 | **Realistic, topology-true fixtures.** Tests MUST use production-shaped data: full 26-char ULID `mission_id`, real coordination-worktree + submodule git topology — NO fabricated short ids/slugs and NO synthetic single-repo stand-ins for the submodule/coord cases. | 100% of new fixtures are topology-true; the submodule/coord bugs are surface-specific and a fabricated fixture masks them. |
| NFR-003 | **Function-over-form + verification-by-deletion.** Behavioral tests MUST be detached from code structure; the proof that adoption is complete is that the shadow-path implementations are deleted and the behavioral suite stays green. | No new form-coupled test except where it already exists (the naming ratchet, out of scope here). |
| NFR-004 | **Quality gates clean.** New/changed code MUST pass `ruff` + `mypy` with zero issues, complexity ≤ 15, no suppressions. | Enforced in CI; no `# noqa`/`# type: ignore` additions. |
| NFR-005 | **Bounded conflict surface.** Changes MUST stay within the named resolver/consumer/root files; no on-disk worktree/coord churn (idempotency-preserving). | Conflict surface limited to enumerated owned files. |

## Constraints

| ID | Constraint |
|----|-----------|
| C-001 | **No new authority.** This mission adopts the EXISTING `resolve_action_context`/`ExecutionContext` SSOT. Introducing a new resolver, a new root authority, or a parallel typed-error type is out of scope and prohibited. |
| C-002 | **TDD-first for behavioral fixes.** #1888-style and contract-sensitive fixes (#1832, #6, #7, #8) MUST land test-first with a live-repro regression test that fails before the fix. |
| C-003 | **Live-evidence-over-static-fixed.** No referenced issue may be closed on static reading. Each "fixed" claim is re-verified by live repro; #1827 specifically is re-test-first. |
| C-004 | **No patch-version prescription.** This spec/plan MUST NOT prescribe a patch version (3.2.1/3.2.2/...). Versioning is a PO/release call. |
| C-005 | **#1716 write-side scope decided in plan.** Whether a bounded slice of #1716 (write-side coord topology authority root — the deepest grain) is in-scope or stays a later focus is a **plan-time** decision (Phase 0 sizing), not a spec assumption. |
| C-006 | **Edit canonical sources only.** Behavioral fixes touch `src/` runtime; any doctrine/prose touches edit SOURCE templates in `src/doctrine/`, never generated agent copies. |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | `spec-kitty next` in a read-path-miss checkout reports the typed read-path code + checked paths, NOT `MISSION_NOT_FOUND` — proven by a live-repro test (#15). |
| SC-002 | `decision open` accepts a valid coord-aware handle through the single canonical authority; the second escape-check is gone — proven by a coord-topology test (#8). |
| SC-003 | `setup-plan` auto-selects the sole mission; >1 still errors structurally (#4). |
| SC-004 | `spec_committed` is true for a spec committed on the primary target branch; a forced commit failure surfaces (not swallowed) (#7). |
| SC-005 | A spec-kitty invocation inside a real submodule resolves the submodule root, not the parent repo — proven by a submodule-topology test (#6/#2011). |
| SC-006 | The shadow/bypass implementations are deleted and the full behavioral suite is green (verification-by-deletion); `ruff`/`mypy` clean, complexity ≤ 15 (NFR-003/004). |

---

## Key Entities

- **`ActionContextError`** — typed resolver error carrying `code` (e.g. `STATUS_READ_PATH_NOT_FOUND`,
  `MISSION_AMBIGUOUS_SELECTOR`) + `checked_paths`. The fidelity-carrying object that must survive the
  call chain (FR-001).
- **`ExecutionContext` / `IdentityFragment`** — the existing single typed read-path composite
  (`resolution.py:682`, `context.py:184`). Builder-hardened by FR-009.
- **`resolve_action_context`** — the canonical resolution entry the bypassing commands must adopt.
- **`resolve_canonical_root` vs `locate_project_root`** — the two root authorities that must agree on
  the submodule case (FR-007).
- **`is_committed` / `_commit_to_branch`** — the committed-check + auto-commit pair whose
  surface-blindness and silent-swallow are fixed by FR-005/FR-006.

---

## Tracker / Issue Matrix

**Numbering caution (load-bearing, from the priti sweep):** the `#4/#7/#8/#12/#14/#15/#2/#6` indices
are **#2007 epic-internal bug numbers, NOT GitHub issue numbers.** Their GitHub trackers are the
C-cluster children **#2010** (read-path unification → bugs 4/7/8/11/12/14/15) and **#2011** (submodule
root → bug 6), plus the per-bug trackers folded in below. Epic **#2007** + sub-issues **#2010** + **#2011**.
Member bugs and their mission mapping:

| Issue | Root cause (PINNED, witnessed on HEAD) | FR | Disposition |
|-------|----------------------------------------|----|-------------|
| #15 (P0) | `next` collapses `ActionContextError`(STATUS_READ_PATH_NOT_FOUND) → `MISSION_NOT_FOUND` | FR-001/002 | in-mission |
| #14 | STATUS_READ_PATH_NOT_FOUND reclassified/lost across callers | FR-001 | in-mission |
| #12 | explicit-resolution failure flattened into generic "pass --mission" | FR-001 | in-mission |
| #8 | `decision open` second escape-check authority rejects valid coord handle | FR-003 | in-mission |
| #4 | `setup-plan` hard-requires --mission, no exact-one auto-select | FR-004 | in-mission |
| #7 | coord-only `is_committed` + silent-swallow `_commit_to_branch` | FR-005/006 | in-mission |
| #6 / #2011 | submodule root misresolution in `resolve_canonical_root` (launch-blocker) | FR-007 | in-mission |
| #1832 | `agent action implement` "no workspace resolved" — verified read-path entry | FR-008 | in-mission |
| #1619 | ExecutionContext builder-hardening (mutable + split-brain) | FR-009 | in-mission |
| #2 (partial) | charter status/sync side-effects + JSON serialization | FR-010 | in-mission |
| #2010 | C3 read-path resolver unification (umbrella) | FR-011 | in-mission |
| #1827 | merge-baseline bug — debbie could NOT reproduce on HEAD | FR-012 | **re-test-first** (verdict set by live repro) |

### FOLD-IN (priti eager sweep, 2026-06-16 — all "claims-fixed, verify": CLOSED ≠ fixed)

| Issue | State | Relation | FR | Disposition |
|-------|-------|----------|----|-------------|
| #1884 | CLOSED | **GitHub tracker for bug #7** — `is_committed` still lacks a primary-target-branch leg → reproduces despite "fix" | FR-005/006 | in-mission (re-verify live) |
| #1889 | CLOSED | **GitHub tracker for bug #8** — `decision open` StatusReadPathNotFound when `coordination_branch` declared but no coord worktree | FR-003 | in-mission (re-verify live) |
| #1692 | CLOSED | `context resolve` rejects primary mission dir when coord worktree absent — the fail-closed-pre-read class (bug #11) | FR-001/011 | in-mission (re-verify live) |
| #1981 | CLOSED | `map-requirements` read spec.md from coord surface instead of primary — coord-vs-primary read-surface defect | FR-011 | in-mission — **verify the #1990 fix routes through the resolver SSOT, not a local patch** |
| #1911 | OPEN | query-mode error lost its actionable `next_step` in the #1910 reconciliation — typed-error remediation must survive | FR-001/002 | in-mission |
| #1914 | OPEN | governed/gate ops must be no-op-stable (read-path/status-read no-op slice; charter-status side-effect-free) | FR-010 | in-mission — **read-path/status-read no-op slice only**; broader umbrella stays on its own track |

### CROSS-REF (note only — out of scope; decided/owned elsewhere)

- **#2008** (C1 command-surface/docs drift, bugs 1/5/9) — delivered by the prior naming-rider Focus A; not read-path.
- **#2009** (C2 charter status/sync/preflight) — charter-freshness track; only the #1914 no-op slice is touched here.
- **#1890** (bug 13 worktree-repair UX) / **#1891** (bug 16 `--json`/`CommitResult` serialization) — command/JSON-contract drift, distinct surface.
- **#1716** / **#1878** — write-side coord topology + entry-side strangler umbrella; **#1716 in/out decision is plan-time (C-005)**, default later focus.
- **#1971** (3-way `locate_project_root` consolidation) — root-resolver sibling to FR-007/#2011, which pins a *different* resolver (`resolve_canonical_root`); #1971 alone is insufficient. Note as sibling, do not conflate.
- **#1993** (`resolve_lanes_dir` pure seam) — **co-dependency flag:** per #2007 it MUST NOT land alone; pair with #1832 or carry minimal adoption.
- **#1666** (context/state domain-boundary epic) — grandparent; this mission is one #1619/#1666 increment. Its ~30-child CLOSED corpus (#1615/#1672/#1823/#1991/#1718/#1982 …) is the **regression-verification reservoir** where bypasses regrow — spot-check, do not trust as done.

**Provenance flag (correct before any verify-and-close cites it):** the naming-SSOT
`00-OVERVIEW.md` states #1888 "landed as #1886", but **#1886 is a different issue** (post-merge
stale-assertion analyzer) and **#1888 (ownership existence-check) is still OPEN.** This mission does
not own #1888 (it was the prior naming-rider's verify-and-close), but the docs cross-reference is
wrong and should be fixed in `docs/engineering_notes/` separately.

**Claim-before-working:** the tickets this mission works on are claimed (assigned to operator) with a
tracker comment naming this mission, per ticket-based mission hygiene. Tracker mutations go through
planner-priti.

**Eager related-issues sweep (in-flight):** a planner-priti sweep
(`research/priti-related-issues-sweep.md`) enumerates net-new related issues beyond the #2007 set
(the operator's "be eager in looking for related issues"). Its FOLD-IN recommendations are merged
into this matrix **before tasks**; the plan's Phase 0 inventory reconciles them against the call-site
map.

---

## Assumptions

- The canonical resolver (`resolve_action_context`/`ExecutionContext`) is sound for the in-context
  case; the failures are at the **adoption boundary** (bypass) and the **error boundary**
  (reclassification), not in the resolver's core resolution logic.
- The #1944/#1965 fix patched `locate_project_root` only; a second root authority
  (`resolve_canonical_root`) still mis-walks on submodules (FR-007 confirmed reproducible on
  v3.2.0/HEAD by debbie).
- Real coord-worktree + submodule fixtures are available/constructible in tests (these bugs are
  topology-specific; fabricated fixtures will mask them — the exact trap the prior mission hit).

## Out of Scope

- Building any new resolver, root authority, or typed-error type (C-001).
- The full #1716 write-side coord topology authority root — only a bounded slice may be pulled in,
  and that decision is deferred to plan (C-005).
- The naming/identity AST ratchet and `branch_naming.py` mid8 routing — delivered by the prior
  naming-rider mission (#2012); this mission does not re-touch that seam.
- Patch-version assignment (C-004).
