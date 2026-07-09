# Phase 0 — Research

Mission `mission-resolver-port-01KX1C05` · #2173 Phase-2 MissionResolver port.
Primary source: `docs/plans/engineering-notes/2173-infra-logic-separation/00-SYNTHESIS.md`. Grounding
established by the 3-lens pre-spec squad (architect-alphonso, paula-patterns, researcher-robbie) — full
findings in the `tracer-*.md` files. This file records the decisions the plan rests on.

## D-Q1 — Which `resolve_mission` is the canonical single walk?

- **Decision**: `src/specify_cli/context/mission_resolver.py::resolve_mission` (returns `ResolvedMission`;
  walks `kitty-specs/` via `_build_index`). This is the identity authority the port faces.
- **Rationale**: `src/specify_cli/runtime/resolver.py` has **no** `resolve_mission` — it resolves
  *template/config paths* (`resolve_command_template_path`, `resolve_content_template_path`,
  `resolve_mission_config_path`). The scout's "two `resolve_mission` functions" was imprecise; they are
  different concerns, not rivals. The `_read_path_resolver` canonicalizer already *delegates* to the
  context resolver (`_read_path_resolver.py:503`), confirming it is the single identity walk.
- **Alternatives considered**: unifying with the runtime path resolver — rejected: different return type
  and concern (path vs identity); merging would create the exact god-resolver the synthesis warns against.

## D-Q2 — Where does the port live? (REVISED post-squad — ledger blocker)

- **Decision**: **Protocol `MissionResolver` in `mission_runtime`** (a new small module
  `mission_runtime/mission_resolver_port.py`); **`FsMissionResolver` + `FakeMissionResolver` adapters in
  `src/specify_cli/context/mission_resolver.py`** beside the walk they wrap.
- **Why revised**: the original "everything in `specify_cli.context`" plan reds `test_layer_rules.py`
  (`TestMissionRuntimeBoundary`): `_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI` (`:76-95`) does **not** list
  `"context"`, and `mission_runtime` currently imports **zero** `specify_cli.context`. The planned shell
  import (even lazy/in-function — the gate does a full `ast.walk`) would create a **new ledger edge** —
  which is doubly wrong because #2173's charter is to *drain* that ledger. The scout conflated *direction*
  with *subpackage*: the established edges are `core`/`missions`/`coordination`, not `context`.
- **How the revision dodges it**: the shell references only the local Protocol (no `specify_cli.context`
  import). Adapters import the Protocol via the allowed downward `specify_cli → mission_runtime`
  (package-root) direction. The default `FsMissionResolver` is constructed at the CLI/`specify_cli` entry
  boundary and threaded down; `mission_runtime` shell functions accept a Protocol-typed `resolver` and
  pass it into the already-ledgered `specify_cli.missions` canonicalizer.
- **Acceptance criterion**: `test_layer_rules.py` green with **zero new ledger edge**. Fallback (add
  `"context"` to the ledger with rationale) requires an explicit operator note.

## D-08 — Full trunk, not a 7th parallel path (operator ruling post-squad)

- **Decision**: the port is the **single walk trunk**. The free `resolve_mission` gains an optional
  `resolver` param and is threaded end-to-end; **all 8 free-function callers** (`audit/engine.py:87`,
  `selector_resolution.py:218`, `retrospect.py:124`, `agent_retrospect.py:72`, `mission_type.py:1051`,
  `runtime/show_origin.py:231`, `acceptance/__init__.py:910`, `_read_path_resolver.py:503`) + the
  canonicalizer route through it or are explicitly documented.
- **Rationale**: the squad showed the dominant read path reaches the walk via the free `resolve_mission`
  inside the canonicalizer, bypassing an assembler-injected port. A scoped port would be a 7th path and
  leave the split-brain open — contradicting "unification, not parity." The AST gate bans raw `iterdir`
  but NOT free-fn calls, so the trunk needs the caller audit too.

## D-01 — Seam location (REVISED post-squad — inject at callers, thread down)

- **Decision**: thread `resolver: MissionResolver | None` from the shell **callers** of
  `_resolve_mission_slug` (`resolve_action_context` :1384, `mission_context_for`, `resolve_placement_only`
  ~:866) through the canonicalizer chain (`_read_path_resolver`) down to the free `resolve_mission`.
  **Never** on `build_execution_context` (pure door) and **never** on the frozen context.
- **Why revised**: the squad showed `_resolve_mission_slug` runs *before* `_assemble_core_fragments` and
  its output is an *input* to the assembler — so injecting *inside* the assembler is structurally
  incoherent. The seam belongs at the callers. Threading preserves the canonicalizer + topology-aware
  (coord/primary) read that `_resolve_mission_id`/`_resolve_mission_slug` carry today.
- **Rationale (unchanged)**: a frozen value object carrying a mutable I/O collaborator breaks immutability
  (ADR `2026-06-26-1`, "context is a proto-DI container" = category error).

## D-07 — Legacy-<slug> bootstrap sentinel is a carve-out, not a fallback (post-squad)

- **Decision**: `_resolve_mission_id` (`resolution.py:944`) deliberately degrades to a `legacy-<slug>`
  sentinel for pre-identity/bootstrap/scaffold missions. This path is an **explicit, documented pre-identity
  carve-out** that does NOT flow through the fail-closed `resolve()`; a regression test pins it.
- **Rationale**: the port's `resolve()` is fail-closed-loud (raises). Silently routing the bootstrap
  branch through it would break mission-create/scaffold. This is NOT the forbidden `is None` fallback
  (D-05) — it is a distinct operation (mint an id for a mission with none yet), not resolution of an
  existing mission.

## D-09 — NFR-001 scoped precisely (post-squad — overclaim fix)

- **Decision**: NFR-001 proves the **identity-resolution leg** of the builder is FS-free via
  `FakeMissionResolver` — NOT that the whole assembler is FS-free.
- **Rationale**: the squad noted `_assemble_core_fragments` has 4+ other FS/git legs
  (`get_main_repo_root`, `_resolve_coordination_branch`, `_resolve_status_surface_dir`, topology) and that
  `build_execution_context` is *already* FS-free. Those remaining legs are separate ports deferred to
  later #2173 phases; the spec/test wording says so.

## Census expansions (post-squad — the counts undershot)

- **Clock**: 12 byte-identical isoformat copies in `specify_cli` + **2 cross-package** copies
  (`glossary/events.py:215`, `runtime/next/_internal_runtime/retrospective_terminus.py:63`) that must be
  triaged (shared home or OUT-with-rationale — never a silent stop at 12). Preserve the 2 stamp + 2
  datetime helpers. ADJACENT S1192: the literal `"%Y-%m-%dT%H:%M:%SZ"` recurs 18× with 4 redundant
  constant defs — a separate stamp-consolidation cleanup; only the SAFE `mission_parsing.py:259`
  hardcoded literal folds here.
- **#2139**: ≥9 non-migration readers (not 4). Route all onto `read_target_branch_from_meta` or explicitly
  triage the dataclass-hydration `KeyError` reads (`context/models.py:83`, `lanes/models.py:200`) as OUT.
- **AST-gate allowlist**: ~16 live non-migration `kitty-specs/` walkers exist — seed the full census
  day-one or the gate reds on introduction. (This many walkers *validates* the bind-by-construction thesis.)

## D-02 — No cache in Phase-2 (from squad, binding)

- **Decision**: the resolver is request-scoped; any memoization is instance-lifetime only. Module/process
  `@lru_cache` is forbidden (C-005).
- **Rationale**: `merge/ordering.py` mutates the scanned surface under the global merge lock, and the
  dashboard daemon is long-lived — a persistent cache would serve stale indexes (a correctness bug). The
  Phase-2 value is the *seam* (Fake → FS-free builder test), not perf.

## D-03 — #2139 is a sibling reconcile, not a resolver method (from squad, binding)

- **Decision**: route the 4 stragglers onto the existing `read_target_branch_from_meta` authority
  (`core/paths.py:655`) and delete the divergent `"main"`/`""`/`KeyError` defaults; deliver as its own WP.
- **Rationale**: `target_branch` extraction is a *field read* on an already-resolved mission — a different
  granularity from handle→mission resolution. Making it a resolver method widens the port past its
  concern (violates "one adapter per port").

## D-04 — Clock is 3 helpers, not 1 (from squad, binding)

- **Decision**: collapse the 12 byte-identical isoformat copies into one `now_utc_iso() -> str`; keep a
  format-preserving stamp helper for the 2 `%Y-%m-%dT%H:%M:%SZ` callers and a `now_utc() -> datetime`
  helper for the 2 `decisions/*` callers.
- **Rationale**: the stamp callers serialize to a different, second-precision `...Z` format and the
  decisions callers return `datetime`; folding them would change on-disk timestamps (NFR-004).

## D-05 — Fail-closed, no legacy branch (from squad + ADR 2026-07-01-1, binding)

- **Decision**: cold-miss → structured not-found naming `spec-kitty migrate backfill-identity`; ambiguity
  → `MissionSelectorAmbiguous`/`AmbiguousHandleError`. No `if <canonical> is None: <fallback>` or
  `mission_id or slug` branch. Fake fixtures are canonical-shaped.
- **Rationale**: the motivating incident (PR #2277) proved the reflexive `is None` branch was wrong; the
  real root was stale non-canonical fixtures. Forbidden shape is an existing binding ADR.

## D-06 — Bind by construction (from squad)

- **Decision**: ship an ADR + a new AST call-site gate naming `FsMissionResolver` the sole sanctioned
  `kitty-specs/` walker (token-keyed allowlist), copying `test_protection_resolver_call_sites.py`.
- **Rationale**: without a structural gate the "one walk" invariant is reviewer-vigilance and walker #7
  reappears. Allowlist keyed on tokens/symbols, never line numbers (they drift on merge — F5).

## D-10 — DDD rename `ExecutionContext → MissionExecutionContext` (operator-directed, IC-00)

- **Decision**: rename the frozen composite `mission_runtime.context.ExecutionContext` →
  `MissionExecutionContext`; land as the FIRST WP so downstream resolver work uses the corrected name.
- **Rationale (it fits)**: `MissionExecutionContext` is already the ubiquitous term — the class docstring
  (`context.py:11`), a parity-test assertion (`test_execution_context_parity.py:1545`), and the **#1619
  epic title** all use it; the class name is the only laggard (DDD: code follows the ubiquitous language).
  Decisive extra reason: it **collides** with `core/context_validation.py:41 class ExecutionContext(StrEnum)`
  — an unrelated type. Renaming disambiguates.
- **Scope**: class def + `ActionContext` alias (`:349`) + ~12 import sites + usages (20 files) + ADR prose
  (`2026-06-22-1`, `2026-06-03-1`). **Hard exclusion**: the `ExecutionContext(StrEnum)` — a different type,
  untouched (its own rename is ADJACENT, out of scope unless the operator asks).
- **Discipline**: bulk-edit-shaped though the mission is not wholesale `change_mode: bulk_edit` — apply a
  scoped occurrence classification at `/tasks` and verify with the full arch suite + `test_mission_runtime_surface.py`
  / `test_execution_context_parity.py` after (the collision is the whack-a-symbol trap).

## Adopt-don't-duplicate (reuse, verified)

- `PlacementSeam` (`mission_runtime/resolution.py:1266`) — yield dirs through its grammar, never compose paths.
- `_canonicalize_primary_read_handle` (`_read_path_resolver.py:1243`) — handle-form canonicalization delegates here; the port does identity→dir only, and stays OUT of the blind primitive `primary_feature_dir_for_mission` (C-007).
- `resolve_mid8` / `mission_dir_name` (`lanes/branch_naming.py`) — the mid8 SSOT.
- DI idiom: `RuntimeEventEmitter` Protocol + `NullEmitter` (`runtime/next/_internal_runtime/events.py:67/95`); wiring `emitter or NullEmitter()` (`engine.py:191`).

## Arch-gate green-list (must not regress — NFR-002)

`test_no_raw_mission_spec_paths.py`, `test_protection_resolver_call_sites.py`,
`test_single_mission_surface_resolver.py`, `test_resolution_authority_gates.py`
(`CANONICALIZER_FLOOR`/`ROUTED_CANONICALIZER_FLOOR`/`COORD_AUTHORITY_WRITE_FLOOR`),
`test_coord_read_residuals_closeout.py` (duplicate canonicalizer pins + identity/lanes floors),
`test_inline_meta_read_gate.py`, `test_write_surface_placement_guard.py`, `test_mission_runtime_surface.py`.
Floors are **shrink-only**; verify from the primary checkout (markers vacuous under `.worktrees/` — F1);
grep floor constants repo-wide before assuming one gate file owns a pin (F2/F3).
