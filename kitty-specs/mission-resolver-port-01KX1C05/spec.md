# Mission Specification: MissionResolver Port (2173 Phase 2)

**Mission slug**: `mission-resolver-port-01KX1C05`
**Mission ID**: `01KX1C051X4JT9VZE6NA3HEPXT`
**Mission type**: software-dev
**Status**: Draft (post-squad grounding)
**Roadmap**: 3.2.x · enabler spine — **#2173 Phase-2** (the `MissionResolver` port). The enabler that unblocks the `#1619` runtime-context root and de-risks the later `#2160` coord-authority degod.
**Tracker**: implements **#2173** (Phase-2) · folds **#2139** (target_branch reader reconcile) and **#2447** (doctrine phantom) · under **#1619** · enabler for **#2160** / **#1797**

> **Post-squad note.** A three-lens pre-spec research squad (architect-alphonso, paula-patterns,
> researcher-robbie) grounded the intent against the architectural direction, live code state, and
> the retrospectives of the in-lineage missions (`single-authority-resolution-gates-01KW1P0F` =
> Phase-1/#2164; `read-surface-ssot-closeout`; `coord-primary-partition-lock-01KWZ46V`). The squad
> **confirmed the port target is real** (the uncached per-call `_build_index` walk + TOCTOU is live in
> `context/mission_resolver.py`) but **corrected the scope in four material ways**, all encoded below:
> (1) the "6 walkers → 1" framing is overstated — the canonicalizer already *delegates* to
> `resolve_mission`, so the honest deliverable is putting a Protocol+Fake face on the *existing single*
> walk; (2) **#2139 is a reconcile-first sibling WP, not a resolver method**; (3) **Clock is 3 helpers,
> not 1**; (4) **no cache in Phase-2**. Primary source:
> `docs/plans/engineering-notes/2173-infra-logic-separation/00-SYNTHESIS.md`. Squad findings are
> preserved in the mission tracer files.

## Purpose (stakeholder-facing)

**TL;DR**: Introduce one injected `MissionResolver` seam so the mission execution-context builder can
be tested without a real filesystem — the concrete enabler that unblocks the `#1619` runtime-context
root and makes the later `#2160` degod safe.

Today every Spec Kitty command re-derives *"which mission am I in and where does it live"* by walking
the `kitty-specs/` directory on every call — uncached, and with no way for a test to substitute the
result. Because that walk is hard-wired into the code that assembles a mission's execution context,
that builder cannot be exercised in a unit test without a real on-disk mission tree, which is exactly
what makes the `#1619` unification hazardous to attempt. This mission puts a single, injectable
`MissionResolver` (a real filesystem adapter plus an in-memory fake) in front of that one walk, at the
imperative shell — never on the frozen context value — so downstream work can build and verify mission
context deterministically. It also folds two adjacent, already-half-consolidated infra reads (the
wall-clock timestamp helper family and the installed-version read) behind the same shipped
default-param dependency-injection idiom, and finishes two small strangler residuals (`#2139`,
`#2447`) that live in the same resolution surface.

## Context & Motivation

`#2173` ("Infrastructure-to-logic separation — inject ports for FS, Clock, GitOps, …") is an **enabler
epic** on the 3.2.x spine: it makes the `#1797` degod payoff real (a god-object only pays off once its
pure core is stub-testable through a port) and unblocks the `#1619` root (one `MissionExecutionContext`
minted per invocation cannot land while the builder re-walks the filesystem per call site).

**Phase-1 (`#2164`, CLOSED via `single-authority-resolution-gates-01KW1P0F`)** shipped the
*canonicalizer gate* — a single-authority seam plus AST call-site ratchets — but explicitly did **not**
build the port (ADR `2026-06-26-1`, "Negative"). Phase-2 is that port.

**Why a port and not "just cache the walk":** the walk's value defect is *testability*, not speed. The
`FakeMissionResolver` is what makes the builder FS-free-testable (the `#1619` unblock). Caching is a
correctness trap here — `merge/ordering.py` mutates the very surface it scans under the global merge
lock, and the dashboard daemon is long-lived — so Phase-2 ships the walk **uncached but injectable**.

**Adopt, don't greenfield.** The port-and-adapters idiom is already shipped in the tree
(`RuntimeEventEmitter` Protocol + `NullEmitter`, engine wiring via `emitter or NullEmitter()`); this
mission copies that idiom, it does not import a framework or build a god-resolver.

## Scope

### In scope

1. **`MissionResolver` seam** — a `Protocol`, an `FsMissionResolver` (real FS adapter owning the single
   `resolve_mission` / `_build_index` walk), and a `FakeMissionResolver` (in-memory `ResolvedMission`
   list), injected at the resolution **shell** (`_assemble_core_fragments`) via a `resolver=None`
   default parameter.
2. **Adopt the two missed resolve-by-identity consumers** the scout under-counted:
   `doctrine_synthesizer/apply.py:602/788` and `core/vcs/detection.py:169`.
3. **New ADR + new AST call-site arch-gate** binding the seam by construction.
4. **`#2139` sibling WP (reconcile, not a resolver method):** route the 4 straggler `target_branch`
   readers onto the existing `read_target_branch_from_meta` authority and delete the divergent
   `"main"` / `""` / `KeyError` absent-value defaults.
5. **Clock consolidation:** collapse the 12 byte-identical isoformat `_now_utc` copies into one
   canonical helper; **preserve** the 2 `%Y-%m-%dT%H:%M:%SZ` stamp callers and the 2 `-> datetime`
   callers as their own distinct helpers. Inject a Clock port *only* at determinism-tested sites.
6. **InstalledVersion routing:** route the un-routed migration reader through the already-existing
   `_CliStatusLike` Protocol (no new port).
7. **`#2447` doc tail:** repoint (or remove) the phantom `core/mission_detection.py::_detect_from_branch()`
   row in the shipped `git-operations-matrix.md`, and add a guard that every `src/…` path referenced in
   that matrix resolves on disk.

### Out of scope (explicitly, to stop epic-title scope-creep)

mid8 / canonicalizer work (Phase-1 `#2164`, and the legacy-drop `#2463`); decision-event identity
(`#2138`); read-surface `load_meta*` residuals (`#2465`, `#2477`–`#2480`); cross-worktree artifact sync
(`#2334`); GitOps (dropped by `#2173`); and the other four ports named in the stale `#2173` title
(GitOps / ProcessEnv / SaaSQueue / Renderer).

### Anti-fold (named so a future implementer cannot "helpfully" regress them)

- `status/identity_audit.py:202/269` — MUST NOT route through the resolver: `_build_index` **silently
  skips** `mission_id`-less missions, which are exactly the legacy missions the identity audit exists
  to find.
- `merge/ordering.py:184/291/294/581` — a `max(mission_number)` **aggregate over a caller-supplied,
  non-primary scan root** under the merge lock; different surface and concurrency regime.
- `core/paths.py:816/835` — best-effort, exception-swallowing error-message listings; the opposite of
  the resolver's fail-closed-loud contract.
- Migration-time walks (`m_0_13_0_*`, `m_2_0_11_*`) — must not depend on the runtime resolver.

## Domain Language

| Term | Meaning |
|------|---------|
| **MissionResolver** | The `Protocol` for handle→mission resolution over `kitty-specs/`. Owns *enumeration/identity resolution only* — not field extraction, not placement. |
| **FsMissionResolver** | The real adapter performing the single filesystem walk. |
| **FakeMissionResolver** | The in-memory stub (a list of `ResolvedMission`) enabling FS-free builder tests. |
| **The shell** | The imperative I/O boundary `_assemble_core_fragments` in `mission_runtime/resolution.py`, where the port is injected. |
| **The frozen context** | `MissionExecutionContext` — a `@dataclass(frozen=True)` pure value snapshot (renamed from `ExecutionContext` per FR-012, DDD ubiquitous language). **Never** carries an adapter. |
| **Cold-miss** | A handle that resolves to no mission → fail-closed-loud, pointing to `spec-kitty migrate backfill-identity`; never a silent slug fallback. |
| **Blind-primitive non-fold rule** | Prior-mission rule (ADR `2026-06-26-1`, "FR-011"): canonicalization must NOT be folded into `primary_feature_dir_for_mission`; the resolver sits at the shell *in front of* the primitive, never inside it. |

## User Scenarios & Testing

Actors here are the **CLI runtime**, the **agent/developer writing tests**, and **downstream missions**.

- **S1 — The unblock (primary):** a developer writes a unit test for the execution-context builder,
  constructs a valid `MissionExecutionContext` by injecting a `FakeMissionResolver` seeded with
  in-memory `ResolvedMission` fixtures, and asserts the built context **with zero filesystem access**.
- **S2 — Cold-miss:** a command resolves an unknown handle → `FsMissionResolver` raises a structured
  not-found error naming `spec-kitty migrate backfill-identity`; there is **no** silent slug fallback.
- **S3 — Ambiguity:** two missions share a handle prefix → `MissionSelectorAmbiguous`, never
  first-match-wins.
- **S4 — target_branch reconcile (`#2139`):** a `meta.json` missing `target_branch` → the single
  authority fails closed; each of the 4 former stragglers now behaves identically (no `"main"` / `""` /
  `KeyError` divergence).
- **S5 — Walker regression prevention:** a future PR adds a raw `kitty-specs/` `iterdir()` outside the
  resolver's sanctioned owners → the new AST call-site gate fails the build.
- **S6 — Timestamp stability:** the Clock consolidation lands and the 2 `%Y-%m-%dT%H:%M:%SZ` stamp
  callers produce **byte-identical** serialized output vs. pre-mission.

**Edge cases:** `mission_id`-less legacy missions remain visible to `identity_audit` (C-001);
`merge/ordering` number assignment is unaffected (C-002); a determinism test that monkeypatched a
`_now_utc` copy still controls time after consolidation.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Provide a single `MissionResolver` `Protocol` with an `FsMissionResolver` (real) and a `FakeMissionResolver` (in-memory) adapter; `FsMissionResolver` owns the one `kitty-specs/` enumeration/identity walk currently in `context/mission_resolver.py::_build_index`. | Draft |
| FR-002 | Make the port the **single walk trunk**: thread `resolver: MissionResolver \| None` from the shell **callers** of `_resolve_mission_slug` (`resolve_action_context`, `mission_context_for`, `resolve_placement_only`) through the canonicalizer chain to the one walk; the free `resolve_mission` gains an optional `resolver` param so no read path bypasses it. The Protocol is defined in `mission_runtime` (no new layer-ledger edge); adapters in `specify_cli.context`. `build_execution_context` stays FS-free and takes no resolver; no adapter on the frozen context. | Draft |
| FR-003 | Route the resolve-by-identity consumers through the resolver: the 2 adopted (`doctrine_synthesizer/apply.py:602/788`, `core/vcs/detection.py:169`) **and an audit of the 8 free-`resolve_mission` callers**, each routed or explicitly documented, so the port is the trunk not a parallel path. | Draft |
| FR-004 | The execution-context builder is unit-testable with `FakeMissionResolver` — a test constructs a valid `MissionExecutionContext` with **no filesystem access**. | Draft |
| FR-005 | Cold-miss and ambiguity are fail-closed-loud: ambiguity → `MissionSelectorAmbiguous`; cold-miss → structured not-found naming `spec-kitty migrate backfill-identity`. **No `is None` / `or slug` legacy fallback branch** (ADR `2026-07-01-1`). | Draft |
| FR-006 | Ship a new ADR recording: ports inject at the shell/builder via per-seam default-param wiring, one adapter per port, **no shared DI container**, **no port on the frozen context**; the resolver owns handle→mission resolution only (not `target_branch` field extraction, not the `merge/ordering` aggregate); the blind-primitive non-fold rule is restated. | Draft |
| FR-007 | Ship a new AST call-site arch-gate naming `FsMissionResolver` as the single sanctioned `kitty-specs/` walker (token-keyed allowlist **seeded with the full ~16-walker census** so it does not red on introduction; discriminating enumeration-of-all-missions from single-dir access), banning new raw `iterdir()`/`glob()` enumeration of the specs dir — the enumeration analogue of `test_protection_resolver_call_sites.py`. | Draft |
| FR-008 | (`#2139`) Route the 4 straggler `target_branch` readers (`context/resolver.py:82`, `retrospective/generator.py:1263`, `cli/commands/agent/mission_branch_context.py:63`, `missions/_resolve_planning_branch.py:80`) through `read_target_branch_from_meta`; delete the re-embedded `"main"` / `""` / `KeyError` defaults so all readers share one fail-closed behavior. Delivered as a **sibling WP**, not a resolver method. | Draft |
| FR-009 | (Clock) Collapse the 12 byte-identical isoformat `_now_utc` copies into one canonical `now_utc_iso() -> str`. Keep a **format-preserving** stamp helper for the 2 `%Y-%m-%dT%H:%M:%SZ` callers (`task_utils/support.py:101`, `cli/commands/agent/mission_parsing.py:257`) and a `now_utc() -> datetime` helper for the 2 `decisions/*` callers. Inject a Clock port only at determinism-tested sites. | Draft |
| FR-010 | (InstalledVersion) Route the un-routed migration version read (`upgrade/migrations/m_2_1_4_enforce_command_file_state.py:55`) through the existing `_CliStatusLike` Protocol; no new port introduced. | Draft |
| FR-011 | (`#2447`) Repoint or remove the phantom `core/mission_detection.py::_detect_from_branch()` row in the shipped `src/doctrine/skills/spec-kitty-git-workflow/references/git-operations-matrix.md`, and add a guard that every `src/…` path referenced in that matrix resolves on disk. | Draft |
| FR-012 | (DDD rename) Rename the frozen composite `mission_runtime.context.ExecutionContext` → `MissionExecutionContext` (code follows the ubiquitous language already used in its docstring, the #1619 epic, and the parity test), updating all ~12 import sites + usages + the `ActionContext` alias + ADR prose. The unrelated `core/context_validation.py::ExecutionContext(StrEnum)` is **explicitly excluded** (different type). | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Identity-leg FS-free-testability | ≥1 unit test drives the builder's **identity-resolution leg** via `FakeMissionResolver` with **no** `kitty-specs/` tree present (green with the specs dir absent). Scoped to the identity leg — the assembler's other FS legs (`get_main_repo_root`, `_resolve_coordination_branch`, `_resolve_status_surface_dir`, topology) are separate ports deferred to later #2173 phases. | Draft |
| NFR-002 | Architectural ratchet integrity | Full `tests/architectural/` suite green; named floor constants are **shrink-only** (never raised); every drained site verified against a full arch run **plus a repo-wide floor-constant grep**, from the **primary checkout** (never trusting a green marker run inside `.worktrees/`). | Draft |
| NFR-003 | Code quality | `ruff` and `mypy` report **zero** new issues/warnings; cyclomatic complexity ≤ 15 on every touched or extracted function; no new `# noqa` / `# type: ignore` / per-file ignores. | Draft |
| NFR-004 | Timestamp serialization stability | The 2 `%Y-%m-%dT%H:%M:%SZ` stamp callers produce **byte-identical** serialized output post-consolidation, proved by a characterization test. | Draft |
| NFR-005 | Structured failure, no silent fallback | Cold-miss/ambiguity emits a typed error with `backfill-identity` guidance; a test asserts the error type and the absence of any slug fallback. | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | `status/identity_audit.py:202/269` MUST NOT route through the resolver (the resolver silently skips `mission_id`-less missions the audit exists to find). | Draft |
| C-002 | `merge/ordering.py` (`:184/291/294/581`) MUST NOT route through the resolver — caller-supplied non-primary scan root + `mission_number` aggregation under the merge lock. | Draft |
| C-003 | If `core/paths.py:816/835` is touched at all, its best-effort swallow-and-degrade error-listing semantics are preserved (never converted to the resolver's fail-closed contract). | Draft |
| C-004 | Migration-time walks must not depend on the runtime resolver. | Draft |
| C-005 | **No process-level or module-level cache** of the walk (`@lru_cache` forbidden). The resolver is request-scoped; any memoization is instance-lifetime only. | Draft |
| C-006 | Ports live on the shell/builder, **never** on the frozen `MissionExecutionContext`; the Resolver / Clock / InstalledVersion seams share **no** DI container. | Draft |
| C-007 | The blind-primitive non-fold rule (ADR `2026-06-26-1`) is preserved: canonicalization is not folded into `primary_feature_dir_for_mission`; the resolver sits at the shell in front of it. | Draft |
| C-008 | Scope is `MissionResolver` + the named Clock/InstalledVersion/`#2139`/`#2447` seams only; the other four `#2173`-title ports stay out. | Draft |
| C-009 | Existing arch-gates stay green and their allowlists are token-keyed (never line-numbered): `test_no_raw_mission_spec_paths.py`, `test_protection_resolver_call_sites.py`, `test_single_mission_surface_resolver.py`, `test_resolution_authority_gates.py`, `test_write_surface_placement_guard.py`, `test_mission_runtime_surface.py`. | Draft |

## Success Criteria

1. The execution-context builder can be unit-tested with **zero filesystem access** via `FakeMissionResolver` (the `#1619` unblock is demonstrable).
2. **Zero** raw `kitty-specs/` `iterdir()`/`glob()` enumeration remains outside `FsMissionResolver`'s sanctioned owners, enforced by the new AST gate.
3. Every `target_branch` read resolves through one authority; **no** reader returns a silent `"main"` on missing metadata.
4. Exactly one canonical wall-clock ISO helper exists; on-disk timestamp formats are unchanged.
5. Full `tests/architectural/` suite is green and all touched floor constants moved shrink-only.
6. The shipped doctrine no longer references a phantom code path, and a guard prevents recurrence.

## Key Entities

- **`MissionResolver` / `FsMissionResolver` / `FakeMissionResolver`** — the new seam and its two adapters.
- **`ResolvedMission`** — the value the resolver returns (`context/mission_resolver.py:51`).
- **`MissionExecutionContext`** — the frozen composite the builder mints (`mission_runtime/context.py:11`).
- **The resolution shell** — `_assemble_core_fragments` / `build_execution_context` (`mission_runtime/resolution.py`).
- **`read_target_branch_from_meta`** — the existing single `target_branch` authority (`core/paths.py:655`).
- **`_CliStatusLike`** — the existing InstalledVersion Protocol (`readiness/upgrade_ux.py:52`).
- **`PlacementSeam`** — the `#1716` placement SSOT the resolver defers to, never duplicates.

## Assumptions

1. Phase-1 (`#2164`) shipped; its canonicalizer allowlist and floor constants are the baseline this mission builds on.
2. `context/mission_resolver.py::resolve_mission` is the canonical single walk to face with the port; the path-variant `runtime/resolver.py` is disambiguated to one authority during design.
3. The Clock and InstalledVersion consolidations ship as parallel WPs that share no DI container with the resolver.
4. The operator merges to local `main`; a PR to `origin/main` follows on explicit instruction (this mission does not push to `origin`).

## Dependencies

- **Under `#1619`** (runtime-context root) as its enabler; **de-risks `#2160`** and the `#1797` degod payoff.
- **Adopts** the `#1716` `PlacementSeam` SSOT and the Phase-1 `#2164` canonicalizer — reuses, never re-implements.
