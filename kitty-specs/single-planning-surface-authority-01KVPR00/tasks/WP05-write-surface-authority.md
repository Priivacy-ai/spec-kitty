---
work_package_id: WP05
title: Single write-surface authority across planning commits + status emission
dependencies:
- WP03
requirement_refs:
- FR-007
- FR-009
tracker_refs:
- "2063"
- "2069"
planning_base_branch: feat/single-planning-surface-authority
merge_target_branch: feat/single-planning-surface-authority
branch_strategy: Planning artifacts for this mission were generated on feat/single-planning-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-planning-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "556727"
history:
- Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission.py
create_intent:
- tests/architectural/test_wp05_write_target_drain.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/safe_commit_cmd.py
- src/specify_cli/cli/commands/spec_commit_cmd.py
- src/specify_cli/status/emit.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/coordination/status_transition.py
role: implementer
tags: []
---

## Profile load (BLOCKING — do first)

You are **python-pedro**, the implementer profile. Before writing any code, LOAD the
profile doctrine (`agent_profile: python-pedro`) — adopt its identity, governance scope,
boundaries, and effort discipline. Do NOT proceed as a generic persona. python-pedro is the
implementer ONLY (never the reviewer; reviews are reviewer-renata's job).

Operating rules you inherit from this profile + mission charter:
- **New/changed code passes `ruff` and `mypy` with ZERO issues and ZERO warnings.** No blanket
  `# noqa`, no `# type: ignore`, no per-file ignore additions to make a check pass (NFR-004).
- **Cyclomatic complexity ≤15** on every function you touch; extract helpers rather than nest.
- **No new S1192** — hoist any non-trivial literal that would appear ≥3 times in a module.
- **Every new branch/helper gets a focused test in THIS WP** (Sonar new-code coverage gate).
- **Live evidence over static-fixed (NFR-001/C-002).** A bug is NOT fixed because the code
  *looks* fixed. You MUST witness the behaviour on a real repro. This WP carries a
  live-evidence-gated drain decision (T029) — do not close it on a static read.

## Objective

Establish a **single write-surface authority** for every planning-phase artifact commit and
every status-event emission (FR-007 + FR-009). Today two write paths re-derive their
destination from the *current `HEAD` branch* independently of the topology seam, which is the
root of the #2063 write-surface desync:

1. **Generic `safe-commit`** (`safe_commit_cmd._resolve_commit_target`, `safe_commit_cmd.py:181`
   / `:193`) resolves its `CommitTarget` from `get_current_branch(repo_root)` when `--to-branch`
   is omitted — a CWD/HEAD-dependent inference, NOT the seam.
2. **Status emission** flows through `coordination/status_transition._resolve_write_target`
   whose **fallback arm at `status_transition.py:336`** is `coord_branch or _current_branch(repo_root)`
   — a `git HEAD` selector reached in the pre-meta create window.

This WP makes mission-aware planning commits and status emission resolve their write
destination through the WP03 seam (`resolve_context_for_mission` placement projection),
SEPARATES `safe-commit`'s two responsibilities (NFR-002), and routes the two
`.kind is COORDINATION` decision sites in `mission.py` through WP01's
`routes_through_coordination` predicate (FR-005, the two sites that live in this WP's owned
file). It ALSO routes the status **READ-contract** topology classification in
`status_transition._read_contract_from_transaction_target` (`:544-584`) through the STORED
topology — retiring the `:558 coordination_branch is None` SURFACE re-inference while preserving
the C-006 transient on-disk arms (`status_transition.py` is already owned). The
`status_transition.py:336` drain is **live-evidence-gated** (T029).

You OWN `cli/commands/agent/mission.py` ENTIRELY — the write path AND the finalize read region
that WP06 linearizes AFTER. WP06 owns `tasks.py`, NOT `mission.py`. Do NOT touch `resolution.py`
(WP03), `tasks.py` (WP06), or `_substantive.py` (WP07).

## Context

### Ground truth (verified by reading the files)

**`safe_commit_cmd.py` — the #2063 root, two responsibilities (NFR-002 SEPARATION):**
- `_resolve_commit_target(*, explicit_to_branch, repo_root)` (`:159`) is documented as "the ONLY
  destination resolution in this file". With `--to-branch X` → `CommitTarget(ref=X, kind=PRIMARY)`.
  When omitted → `inferred = get_current_branch(repo_root)` (`:181`) →
  `CommitTarget(ref=inferred, kind=CommitTargetKind.PRIMARY)` (`:193`) with a stderr v3.3
  deprecation. **This HEAD-inference arm is the #2063 root for mission-aware commits.**
- This command commits **generic operator files** (`_current_worktree_root()` deliberately keeps
  the current worktree, NOT `find_repo_root`'s main-checkout redirect). That GENERIC path is
  legitimate and MUST stay functional + tested (NFR-002).
- **Two responsibilities to separate:** (a) a mission-aware planning commit MUST resolve via the
  seam; (b) a generic non-mission operator-file commit keeps its existing `--to-branch`/HEAD
  behaviour. Do NOT overload one resolver — discriminate and route.
- **CT4 (#2075) preserve-signature guard:** the public typer command `safe_commit_command`
  signature (its `files`, `--message`, `--to-branch`, `--json` params) MUST NOT change. Re-point
  only the *planning* assertion if seam adoption changes the internal call shape. The
  `safe_commit_cmd.py:189-212` `--to-branch` "required in v3.3" deprecation is NOT-YET-DUE
  (current 3.2.x) — LEAVE it.

**`spec_commit_cmd.py` — ALREADY seam-routed (verify, light touch):**
- `spec_commit_command` derives the mission slug (`_derive_mission_slug`, `:48`), resolves
  `ProtectionPolicy.resolve(repo_root)` at the boundary (`:153`), and routes through
  `commit_for_mission(...)` (`:155`). It does NOT infer from `HEAD`. This is the canonical
  mission-aware write seam already in place. Your job here is to CONFIRM it stays seam-routed and
  add a regression test that a coord-topology spec commit lands on the seam-resolved surface
  (#2063 witnessed). Do NOT re-plumb a working path.

**`mission.py` — the write paths (mostly already on `commit_for_mission`) + the 2 decision sites:**
- `_commit_artifact_to_branch` (`:1040`+) ALREADY delegates to `commit_for_mission` with
  `resolve_placement_only` as the destination authority, NOT `git HEAD` (`:1055-1058`). `setup_plan`
  (`:1905`) and the finalize commits route through `commit_for_mission` (`:1862`, `:2296`, `:2343`,
  `:3761`). The write authority here is LARGELY adopted — your work is to (i) confirm no residual
  `get_current_branch`-as-destination decision survives on the planning write path, and (ii) route
  the two decision sites below.
- **The 2 FR-005 `.kind is COORDINATION` decision sites in `mission.py`:**
  - `_planning_commit_worktree` `:776` — `if placement.kind is not CommitTargetKind.COORDINATION:`
    decides whether the commit runs in the coord worktree vs the main checkout.
  - `_enforce_analysis_report_write_preflight` `:858` — `if placement_ref is not None and
    placement_ref.kind is CommitTargetKind.COORDINATION:` decides whether to drop coord-artifact
    residue from the dirty set.
  Both MUST adopt WP01's `routes_through_coordination(target)` predicate instead of reading
  `.kind is COORDINATION` directly. The `CommitTargetKind` TYPE survives vestigial (eradication is
  Mission B / C-007) — you stop *reading* `.kind` to decide, you do NOT delete the type.

**`status/emit.py` — `emit_status_transition` and its `feature_dir` param (FR-009):**
- `emit_status_transition(...)` (`:399`) is the single status entry point; its first positional
  param is `feature_dir` (`:400`). It already `canonicalize_feature_dir(feature_dir)` (`:515`) —
  the redirect-to-main behaviour — but the **caller** supplies the path. FR-009 requires every
  call site to pass a `feature_dir` that the SEAM resolved, not an ad-hoc per-caller path, so
  dep-gate / kanban / review-claim reads and `move-task` writes converge on one surface.
- The actual write-target HEAD selector for the transactional emit lives in
  `coordination/status_transition._resolve_write_target` (`:296`), whose `:336` fallback
  `return coord_branch or _current_branch(repo_root)` is reached only when
  `resolve_placement_only(repo_root, mission_slug)` raises (pre-meta create window / ad-hoc
  fixture). `status_transition.py` is NOT in your owned_files — you do NOT edit it; you DRAIN
  its ALLOWLIST entry in the architectural guard test (see T029), and only if the live repro
  proves the arm dead.

**`tests/architectural/test_no_write_side_rederivation.py` — the gating guard (YOU own it):**
- `_ADOPTED_MODULES` (`:43`) binds the write-side modules; `_ALLOW_LIST` (`:84`) seeds exactly ONE
  deferred entry: `("src/specify_cli/coordination/status_transition.py", 336)` — the `:336` HEAD
  selector. `test_allow_listed_line_is_the_deferred_head_selector` (`:251`) pins that the
  allow-listed line still holds `coord_branch or _current_branch`.
- **Linearized-chain note (FLAG IN RISKS):** WP00 RE-KEYS this guard's allow-list onto
  `_ratchet_keys.composite_key` (content-addressed `(qualname, token_line)`) FIRST, and deletes the
  private `_code_tokens_by_line` copy. The WP05 drain PROOF (T029) lives in your OWNED test
  `tests/architectural/test_wp05_write_target_drain.py` (declared in `create_intent`) — that is the
  DEFAULT home for the negative-probe / reachability assertion, NOT an edit to WP00's guard file.
  The ONLY edit you make to WP00's `test_no_write_side_rederivation.py` is the single
  allow-list-entry removal + `test_allow_listed_line_is_the_deferred_head_selector` flip, and ONLY on
  a Proven-DEAD verdict — a documented one-line **out-of-map edit**, gated on the negative-probe.
  **You MUST rebase on WP00's re-key before touching this file.** WP00 and WP05 both list this file:
  deliberate linearized chain, not an accident.

### Why this is non-fakeable

The #2063 scenario in `spec.md` (Primary scenario, lines 92-96): an operator runs
`/spec-kitty.specify` then `/spec-kitty.tasks` on a **coord-topology** mission; `spec.md` is
committed through the seam-resolved placement and lands on the surface the NEXT command reads.
A static "it routes through `commit_for_mission`" claim is NOT proof — you must witness the commit
landing on the seam-resolved surface for a coord-topology mission, and the generic `safe-commit`
path must stay green (NFR-002).

## Subtasks (T025..T030)

### T025 — Separate `safe-commit`'s two responsibilities (FR-007, NFR-002)
In `safe_commit_cmd.py`, split `_resolve_commit_target` so the **mission-aware** path resolves
its destination via the WP03 seam (`resolve_context_for_mission` placement projection /
`resolve_placement_only`) when the commit targets a resolvable mission's planning artifacts, while
the **generic operator-file** path keeps its existing `--to-branch` / HEAD behaviour. Discriminate
explicitly (e.g. a resolvable `kitty-specs/<slug>/` path argument or `--mission`-style signal
routes to the seam; everything else stays generic). Do NOT widen the public `safe_commit_command`
signature (CT4 / #2075). Keep the v3.3 `--to-branch` deprecation arm intact for the generic path.
**Acceptance:** the generic path still resolves a `CommitTarget` from `--to-branch`/HEAD and lands
the commit (NFR-002 preserved); the mission-aware path resolves from the seam, never from
`get_current_branch` as the destination decision.

### T026 — Confirm + regression-pin `spec_commit_cmd.py` seam routing + READ-BACK leg (FR-007, #2063, SC-004)
`spec_commit_command` already routes through `commit_for_mission` with a boundary-resolved
`ProtectionPolicy` and never infers from `HEAD`. Add a regression test proving a **coord-topology**
mission spec commit lands on the **seam-resolved surface** (the #2063 witnessed scenario): commit
`spec.md` for a coord-topology mission and assert the resulting `placement_ref` is the coordination
branch (not the primary HEAD). Do NOT re-plumb the working path — only confirm + pin.
**READ-BACK leg (SC-004, paula — the half SC-004 actually demands):** the write-lands assertion
above proves only the WRITE leg. The #2063 round-trip SC-004 requires that the artifact is ALSO
**read back from that same seam-resolved surface by the next command's read path**. EXTEND this
test to assert the committed `spec.md` is READABLE from the next-command read surface — i.e. resolve
the read/placement surface the way `/spec-kitty.tasks` would (the seam read leg) and assert the
committed `spec.md` content is recoverable from THAT surface, not merely that `placement_ref` is the
coordination branch. A test that proves only the write leg (placement_ref == coord branch) is
INSUFFICIENT — SC-004 is satisfied only when the read leg recovers the written content from the same
surface.

### T027 — Route the 2 `.kind is COORDINATION` decision sites through `routes_through_coordination` (FR-005)
In `mission.py`, replace the two direct `.kind is COORDINATION` reads with WP01's
`routes_through_coordination(target)` predicate:
- `_planning_commit_worktree` `:776` (`if placement.kind is not CommitTargetKind.COORDINATION:`)
  → `if not routes_through_coordination(placement):`
- `_enforce_analysis_report_write_preflight` `:858`
  (`if placement_ref is not None and placement_ref.kind is CommitTargetKind.COORDINATION:`)
  → `if placement_ref is not None and routes_through_coordination(placement_ref):`
Import the predicate from the `mission_runtime` seam (WP01). Leave `CommitTargetKind` imported +
constructed (vestigial; Mission B eradicates the type). **Acceptance:** `grep` shows zero
`.kind is COORDINATION` *decision* reads remaining in `mission.py`; both sites read the predicate;
behaviour is byte-equivalent for already-correct topologies (NFR-003).

### T028 — Status emission resolves `feature_dir` from the seam + status READ-contract routes through stored topology (FR-009)
Ensure every `emit_status_transition(...)` call site reachable from the planning / move-task write
paths supplies a **seam-resolved** `feature_dir` (the canonical primary feature dir the
read/placement path resolves to), not an ad-hoc per-caller path. Where a call site hands a CWD- or
worktree-local path, route it through the seam so dep-gate / kanban / review-claim reads and
`move-task` writes converge on ONE surface (the #2062 status-read leg). `status/emit.py` itself
`canonicalize_feature_dir`s — do NOT remove that backstop; the fix is at the *caller* so the
seam-resolved path is supplied in the first place.

**Status READ-contract: route topology classification through the STORED topology (squad finding —
`status_transition.py` is already in this WP's owned_files).** `coordination/status_transition.`
`_read_contract_from_transaction_target` (`status_transition.py:544-584`) classifies the status
read-contract THREE ways today: `:558 if identity.coordination_branch is None`, `:572
worktree_root.exists()` (disk-stat), and `:555 _is_under_worktree`. The `:558 coordination_branch
is None` arm is a **fresh re-inference of the coord-vs-primary SURFACE** — exactly the forbidden
re-derivation FR-009/SC-001 retires. Route the **SHAPE** decision (coord vs primary) through the
STORED topology (the WP03 seam / stored placement) instead of re-inferring it from
`coordination_branch is None`.
**CRITICAL preservation (C-006 — do NOT break #1718 / #1848):** the stored topology decides the
coord-vs-primary SHAPE only; the **transient on-disk arms stay probe-discriminated**. The
`:572` worktree-exists / branch-deleted / coord-empty arms continue to PROBE the on-disk state —
the stored topology answers "is this a coord-shaped mission?", the probe still answers "is the
coord worktree materialized right now?". Re-routing the SHAPE through stored topology MUST NOT
collapse those transient arms: the create-window (#1718) and coord-deleted (#1848) contracts are
preserved because the probe — not the stored topology — handles the materialized-yet/deleted-now
states. Do NOT make the stored topology answer the transient question.

**Non-vacuous-pass discipline (renata — `emit.py` canonicalizes, which MASKS a wrong caller path).**
A single happy-path "the event landed on the right surface" test is INSUFFICIENT, because the
`canonicalize_feature_dir` backstop inside `emit.py` will rescue a wrong caller path and the test
passes anyway. You MUST deliver BOTH of:
- **(a) Exhaustive call-site audit.** ENUMERATE every `emit_status_transition` call site reachable
  from the planning / move-task write paths and record, in the review notes (and DoD), a per-site
  verdict for each: **seam-resolved** (already passes a seam-resolved `feature_dir`), **converted**
  (changed in this WP to pass the seam-resolved path), or **N/A** (not on the planning/move-task
  write path — justify why). No call site on the write path may be left unclassified.
- **(b) A test that goes RED if the `emit.py` canonicalize backstop were removed.** Prove the
  CALLER supplies the seam-resolved `feature_dir` — not that `emit.py` rescued it. Achieve this by
  asserting at the caller boundary (the value handed INTO `emit_status_transition` is already the
  seam-resolved surface, e.g. spy/capture the argument before `emit.py` canonicalizes), or by
  exercising the caller with the canonicalize backstop neutralized so a wrong caller path would
  produce the wrong surface and fail. The test must FAIL if a caller regresses to an ad-hoc path,
  regardless of the backstop.

**Acceptance:** the exhaustive per-site verdict table is recorded; the caller-supplies-the-seam test
goes RED under a (hypothetically) removed canonicalize backstop; the `canonicalize_feature_dir`
backstop in `emit.py` remains present and untouched. **READ-contract:** a `grep`/assertion proves
`status_transition.py:558`'s `coordination_branch is None` **SURFACE** decision is RETIRED — the
coord-vs-primary SHAPE in `_read_contract_from_transaction_target` is read from the stored topology,
and the only surviving reads of `coordination_branch` in that function are the C-006 **transient**
arms (worktree-exists / branch-deleted / coord-empty probe discrimination), aligning with SC-001's
zero-inference-sites gate and WP03's grep. A test witnesses that a coord-shaped mission classifies
coord-vs-primary from the stored topology while the transient on-disk arms (#1718 create-window /
#1848 coord-deleted) still discriminate via the probe.

### T029 — `status_transition.py:336` drain decision (LIVE-EVIDENCE-GATED, NEGATIVE-PROBE, FR-009)
`:336` (`return coord_branch or _current_branch(repo_root)`) is the `_resolve_write_target`
**fallback arm** reached only when `resolve_placement_only` cannot resolve the mission — the
pre-meta create window. The DEFAULT verdict is **LEAVE + re-key** (the line is presumed live unless
a negative-probe PROVES it dead). Determine empirically whether FR-002/FR-003 (stored topology minted
at `mission create`) make the `_current_branch` arm **unreachable for real missions**:

1. **Instrument** the fallback (temporary log/counter on the `:336` arm).
2. **NEGATIVE-PROBE — try to REACH `:336` via its genuine reaching condition (REQUIRED to claim
   DEAD).** A happy-path "ran `mission create` → first-write once and didn't hit it" run is
   **INSUFFICIENT** — `resolve_placement_only` succeeds for a clean coord mission, and FR-002/FR-003
   mint topology AT CREATE, structurally biasing every happy-path run toward "never hit". That run
   proves NOTHING about deadness. Instead, construct the arm's REAL reaching condition: emit a status
   transition for a mission whose `meta.json` has **no resolvable placement yet** — the genuine
   pre-meta create window / an ad-hoc fixture mission with placement deliberately unresolvable so
   `resolve_placement_only` RAISES. With the instrumentation in place, observe whether the `:336`
   arm is reached **even under this adversarial reaching attempt**.
3. **Decide:**
   - **Proven DEAD** — ONLY if the negative-probe (step 2) demonstrates the arm is NOT reached even
     when its genuine reaching condition is forced (`resolve_placement_only` raises and the code path
     still never returns via `:336`). → DRAIN: remove the `:336` allow-list entry from `_ALLOW_LIST`
     in `test_no_write_side_rederivation.py` and FLIP/retire
     `test_allow_listed_line_is_the_deferred_head_selector` (it asserts the entry exists) — this
     allow-list removal is a single documented one-line **out-of-map edit** to WP00's owned guard
     file, gated on the negative-probe (see Risk #1). The drain PROOF itself lives in your OWNED
     `tests/architectural/test_wp05_write_target_drain.py` (declared in `create_intent`), which
     encodes the negative-probe as a permanent regression: it forces the reaching condition and
     asserts the `:336` arm is not taken. If `:336` itself is dead, the `status_transition.py`
     deletion is a follow-on note (you don't own that file — coordinate).
   - **Still reachable (DEFAULT)** — the negative-probe reaches `:336`, OR you cannot construct a
     reaching attempt that proves unreachability → LEAVE the line; WP00 has already re-keyed the
     allow-list. Record in `tests/architectural/test_wp05_write_target_drain.py` (owned) the
     witnessed reachability and the live evidence (which probe hit the arm), and note it in
     `research/observations.md` and the DoD.

**The drain-assertion test is WP05-PRIVATE BY DEFAULT.** It lives in your owned
`tests/architectural/test_wp05_write_target_drain.py` (in `create_intent`), NOT as an edit to WP00's
guard file. The ONLY edit you make to WP00's `test_no_write_side_rederivation.py` is the single
allow-list-entry removal + pin-test flip, and ONLY on a Proven-DEAD verdict — a documented one-line
out-of-map edit (see Risk #1), not a co-owned rewrite.

**Do NOT drain speculatively (regression risk) and do NOT re-pin a dead line (immortalized
exemption).** This decision is gated on witnessed live evidence from the NEGATIVE-PROBE
(NFR-001 / C-002) — NOT a static read, and NOT a single happy-path create→first-write that never
trips the arm.

### T030 — Tests + static-analysis gate
Add focused tests for every branch/helper you introduced (T025 discriminator, T027 predicate
sites, T028 seam-resolved feature_dir + canonicalize-removal-RED test + status READ-contract
stored-topology SHAPE classification with probe-discriminated transient arms, T026 write+read-back,
T029 negative-probe in the owned `tests/architectural/test_wp05_write_target_drain.py`). Run:
- `PWHEADLESS=1 pytest tests/architectural/test_wp05_write_target_drain.py` (your OWNED drain proof —
  encodes the T029 negative-probe / reachability verdict).
- `PWHEADLESS=1 pytest tests/architectural/test_no_write_side_rederivation.py` (the guard you own —
  must be green after the WP00 re-key + your drain/leave decision).
- `pytest tests/architectural/test_no_legacy_terminology.py` (CI-only gate; run before push since
  you touch prose/docstrings in `mission.py`/`safe_commit_cmd.py`).
- `ruff check .` and `mypy` on every touched file — ZERO issues, ZERO warnings (NFR-004).
- The differential equivalence gate `tests/missions/test_surface_resolution_equivalence.py` MUST be
  green at this WP boundary (NFR-001) — it is owned by WP04 but must not regress here.

## Branch Strategy

Planning artifacts for this mission were generated on `feat/single-planning-surface-authority`.
During `/spec-kitty.implement` this WP may branch from a dependency-specific base (WP03's tip, since
`dependencies: [WP03]`), but completed changes MUST merge back into
`feat/single-planning-surface-authority` unless the human explicitly redirects the landing branch.
**You depend on WP03 (the pure `resolve_context_for_mission` seam) and transitively on WP00's
re-key of `test_no_write_side_rederivation.py` and WP01's `routes_through_coordination` predicate.**
Rebase on WP00 + WP01 + WP03 tips before editing the shared guard test and the predicate sites.

## Definition of Done (non-fakeable)

- [ ] **FR-007 / NFR-002:** `safe-commit`'s two responsibilities are SEPARATED — the generic
  operator-file path still resolves from `--to-branch`/HEAD and lands a commit (proven by a GREEN
  generic-path test), and the mission-aware path resolves its destination via the WP03 seam, never
  from `get_current_branch` as a destination decision. The public `safe_commit_command` signature is
  unchanged (CT4).
- [ ] **FR-007 / #2063 WITNESSED (write + READ-BACK / SC-004):** a test proves a planning commit
  (`spec.md`) for a **coord-topology** mission lands on the **seam-resolved surface** (coordination
  branch, the value `resolve_placement_only` computes) — NOT the primary HEAD — AND that the
  committed `spec.md` is **read back** from that same seam-resolved surface via the next-command read
  leg (the round-trip SC-004 demands, not just the write leg). (The #2063 write-surface scenario from
  `spec.md:92-96`.)
- [ ] **FR-005:** both `.kind is COORDINATION` decision sites in `mission.py` (`:776`, `:858`) read
  `routes_through_coordination(target)`; `grep` finds zero `.kind is COORDINATION` *decision* reads
  remaining in `mission.py`; `CommitTargetKind` left vestigial (not deleted).
- [ ] **FR-009 (exhaustive audit + non-vacuous test):** every `emit_status_transition` call site on
  the planning/move-task write path carries a per-site verdict (seam-resolved / converted / N/A) in
  the review notes; a test proves the CALLER supplies the seam-resolved `feature_dir` and goes RED if
  the `emit.py` canonicalize backstop were removed (the backstop is retained and untouched). A single
  happy-path test is INSUFFICIENT.
- [ ] **FR-009 (status READ-contract through stored topology):** `_read_contract_from_transaction_`
  `target` (`status_transition.py:544-584`) classifies the coord-vs-primary SHAPE from the STORED
  topology; `grep`/assertion shows `status_transition.py:558`'s `coordination_branch is None`
  **SURFACE** decision is RETIRED (only the C-006 transient arms — `:572` worktree-exists /
  branch-deleted / coord-empty — still read `coordination_branch`), aligning with SC-001's
  zero-inference-sites gate and WP03's grep. The create-window (#1718) and coord-deleted (#1848)
  contracts are preserved (transient arms stay probe-discriminated); a test witnesses both the
  stored-topology SHAPE classification and the probe-discriminated transient arms.
- [ ] **FR-009 / T029 (NEGATIVE-PROBE):** the `status_transition.py:336` drain decision is made on
  **witnessed live evidence from the negative-probe** — an explicit attempt to REACH `:336` via its
  genuine reaching condition (`resolve_placement_only` forced to raise), NOT a happy-path
  create→first-write that never trips the arm. The proof lives in the OWNED
  `tests/architectural/test_wp05_write_target_drain.py` (in `create_intent`): either DRAINED
  (negative-probe proved unreachable → one-line allow-list removal + pin-test flip in WP00's file as
  a documented out-of-map edit) or LEFT-with-recorded-reachability (DEFAULT) — NOT a speculative
  drain, NOT a re-pin of a dead line.
- [ ] `test_no_write_side_rederivation.py` is GREEN after the WP00 re-key + your decision.
- [ ] **NFR-004:** `ruff` + `mypy` ZERO issues/warnings on every touched file; complexity ≤15; no
  new S1192; no suppressions added to pass.
- [ ] **NFR-001:** the differential equivalence gate + terminology guard are green at the WP boundary.
- [ ] Every new branch/helper has a focused test in THIS WP.

## Risks

1. **Linearized-chain dependency on WP00 + WP01 + WP03 (TOP).** You read
   `routes_through_coordination` (WP01 adds it) over the seam (WP03 adds it), and the T029 drain
   PROOF lives in your OWNED `tests/architectural/test_wp05_write_target_drain.py` (in
   `create_intent`) — NOT in WP00's guard file. The ONLY out-of-map edit to WP00's
   `test_no_write_side_rederivation.py` is the single allow-list-entry removal + pin-test flip, and
   ONLY on a Proven-DEAD verdict from the negative-probe — a documented one-line edit, not a co-owned
   rewrite. **Rebase on all three tips before that one-line edit.** If `finalize-tasks
   --validate-only` rejects even that single line as a shared-file overlap, leave WP00's file
   untouched and keep the entire drain decision in your owned test (record the LEAVE/DRAIN verdict
   there) — DO NOT force the shared edit through; note it in the PR.
2. **Speculative drain regression (T029) — the load-bearing-workaround trap.** Draining `:336`
   without the NEGATIVE-PROBE proving the arm dead re-opens the create-window write bug. The fakeable
   path: an implementer runs ONE happy-path create→first-write, never trips `:336` (because
   `resolve_placement_only` succeeds for a clean coord mission, and FR-002/FR-003 mint topology at
   create — structurally biasing toward "never hit"), concludes "DEAD", and drains. That run proves
   NOTHING. The DEAD verdict REQUIRES the negative-probe: force the genuine reaching condition (emit a
   transition for a mission whose `meta.json` has no resolvable placement so `resolve_placement_only`
   RAISES) and prove the arm is still not reached. DEFAULT to LEAVE + re-key unless the negative-probe
   proves unreachability. C-006: the create-window (#1718) and coord-deleted (#1848) transient states
   are orthogonal to the enum and stay probe-discriminated — a re-route that assumes the stored
   topology answers "is the coord worktree materialized?" regresses #1718. Witness the arm's
   reachability; do NOT close on a static read.
3. **`safe-commit` overload regression (NFR-002).** The mission-aware path must NOT break the
   generic operator-file commit. Keep them discriminated and the generic path independently tested.
4. **Scope creep into Mission B / block C (C-007 / C-008).** Do NOT extract `mission.py` helpers to
   `commit_router.py` (#2056 de-godding is CARVED — opportunistic cleanup of TOUCHED lines only). Do
   NOT delete the `CommitTargetKind` type or migrate the 14 `resolve_placement_only` sites to the
   richer API (Mission B). You touch the 2 decision sites + the planning commit / status-emit write
   paths only.
5. **CT4 signature drift (#2075).** Re-pointing the planning assertion is fine; changing
   `safe_commit_command`'s public params is not.

## Reviewer Guidance (for reviewer-renata)

- **Verify the #2063 witness is LIVE, not static, AND covers the READ-BACK leg.** The coord-topology
  spec-commit test must assert the commit landed on the **coordination branch** placement_ref, not
  merely that `commit_for_mission` was called — reject a test that only mocks the router. It must
  ALSO assert the committed `spec.md` is **read back** from the same seam-resolved surface via the
  next-command read leg (SC-004 round-trip). A test that proves only the write leg (placement_ref ==
  coord branch) without the read-back is INSUFFICIENT — REJECT.
- **Verify NFR-002 separation is real.** There must be a GREEN test exercising the generic
  `safe-commit` operator-file path with `--to-branch`/HEAD inference still working. A diff that
  routes ALL `safe-commit` through the seam (breaking generic) is a NFR-002 regression — REJECT.
- **Verify the FR-009 audit is exhaustive and the test is non-vacuous.** The review notes MUST carry
  a per-call-site verdict (seam-resolved / converted / N/A) for every `emit_status_transition` call
  site on the planning/move-task write path — no unclassified site. The seam test must go RED if the
  `emit.py` canonicalize backstop were removed (it proves the CALLER supplies the seam-resolved
  `feature_dir`, not that `emit.py` rescued it). A single happy-path test that passes only because
  `emit.py` canonicalized is a vacuous pass — REJECT.
- **Verify the status READ-contract routes through the stored topology, not a re-inference.**
  `grep -n "coordination_branch is None" src/specify_cli/coordination/status_transition.py` must NOT
  return the `:558` SURFACE-decision arm — the coord-vs-primary SHAPE in
  `_read_contract_from_transaction_target` must come from the stored topology. The only surviving
  `coordination_branch` reads in that function must be the C-006 transient arms (worktree-exists /
  branch-deleted / coord-empty probe discrimination). REJECT a diff that re-routes the SHAPE but also
  collapses the transient arms (that regresses #1718 create-window / #1848 coord-deleted). A test must
  witness BOTH: stored-topology SHAPE classification AND the probe-discriminated transient arms.
- **Verify the T029 drain decision cites the NEGATIVE-PROBE, not a happy-path run.** The DEAD verdict
  is valid ONLY if backed by an explicit attempt to REACH `:336` via its genuine reaching condition
  (a mission whose `meta.json` has no resolvable placement so `resolve_placement_only` raises), with
  instrumentation proving the arm is not reached even then. "Ran create→first-write once, didn't hit
  it" is INSUFFICIENT — REJECT a drain backed only by a happy-path run. The proof must live in the
  OWNED `tests/architectural/test_wp05_write_target_drain.py` (in `create_intent`); WP00's guard file
  may carry ONLY the one-line allow-list removal + pin flip, and only on a Proven-DEAD verdict. A
  drain with no negative-probe, or a re-pin of a confirmed-dead line, is blocking. If LEFT, the
  allow-list re-key (WP00) must be the reason, not silent masking.
- **Verify FR-005 routing.** `grep -n "kind is COORDINATION" src/specify_cli/cli/commands/agent/mission.py`
  returns zero *decision* reads; both sites use `routes_through_coordination`.
- **Verify scope discipline.** No `mission.py` helper extracted to `commit_router.py`; no
  `CommitTargetKind` type deletion; no `resolution.py` / `tasks.py` / `_substantive.py` edits.
- **Static analysis:** `ruff` + `mypy` clean on all five owned files; complexity ≤15; no new
  suppressions. Incorrect doc paths in this prompt are blocking, not warnings.

## Activity Log

- 2026-06-22T16:21:13Z – claude:opus:python-pedro:implementer – shell_pid=482541 – Assigned agent via action command
- 2026-06-22T16:59:35Z – claude:opus:python-pedro:implementer – shell_pid=482541 – WP05 done (forced past flat-mission lane-behind preflight; owned files verified disjoint+conflict-free vs feat/, NO rebase per prompt). T025: safe-commit two responsibilities SEPARATED — generic operator-file path keeps --to-branch/HEAD (NFR-002); mission-aware kitty-specs path resolves via WP03 seam, never get_current_branch; signature unchanged (CT4). T026/#2063/SC-004: real coord-topology spec commit lands on seam-resolved coord branch AND read back via candidate_feature_dir_for_mission. T027/FR-005: both mission.py .kind is COORDINATION sites route through routes_through_coordination (AST gate=0). T028/FR-009: caller-supplies-seam proven via emit.py-backstop-NEUTRALIZED test; READ-contract coordination_branch-is-None SURFACE decision RETIRED, SHAPE from stored topology (classify_topology, pure); C-006 #1718/#1848 transient arms preserved. T029 :336 NEGATIVE-PROBE: REACHABLE (resolve_placement_only raises + coord_branch=None -> _current_branch) => verdict LEFT, WP00 re-key kept, NO drain. ruff+mypy clean (0 NEW errors); complexity<=15. Pre-existing failure (not WP05): test_mission_runtime_surface::test_public_surface_matches_contract red on lane base (WP01/WP03 widened __all__ w/o updating _PUBLIC_SURFACE).
- 2026-06-22T17:00:57Z – claude:opus:reviewer-renata:reviewer – shell_pid=556727 – Started review via action command
- 2026-06-22T17:09:09Z – user – shell_pid=556727 – APPROVED cycle 1: FR-007/NFR-002 two-responsibility split verified (generic --to-branch/HEAD + mission-aware seam, both GREEN, CT4 signature intact); #2063/SC-004 read-back witnessed live (real seam, no router mock, coord-worktree read-back + negative primary check); FR-009 non-vacuity proven via emit.py-backstop-NEUTRALIZED test (caller supplies seam path, not emit.py rescue); SC-001 coordination_branch-is-None SURFACE decision retired (AST-pinned), C-006 #1718/#1848 transient probe arms preserved; T029 :336 NEGATIVE-PROBE re-run REACHABLE -> LEFT is genuine (WP00 allow-list untouched, reachability pinned in owned drain test); FR-005 both .kind sites route through routes_through_coordination (AST gate=0, CommitTargetKind type survives); ruff clean, zero NEW mypy errors (all no-any-return pre-existing on untouched lines), complexity<=15, equivalence+terminology gates GREEN. 32/32 WP05 tests pass.
