# Tracer — Design Decisions

Mission: `mission-resolver-port-01KX1C05` · #2173 Phase-2 MissionResolver port.
Seeded at planning from the 3-lens pre-spec squad (architect-alphonso, paula-patterns, researcher-robbie).
**Append a dated entry whenever a material decision is made or revised during implement; assess at close.**

## Decisions carried in from the pre-spec squad (2026-07-08)

- **D1 — Seam on the shell, never the frozen context.** The `resolver=None` default-param is injected at
  `_assemble_core_fragments` (the FS shell), **not** on `build_execution_context` (the pure projection
  door) and **never** on the frozen `MissionExecutionContext`. Rationale: a frozen value object carrying
  a mutable I/O collaborator breaks the immutability invariant — the synthesis records the "context is a
  proto-DI container" framing as a category error (ADR `2026-06-26-1`).
- **D2 — "6 walkers → 1" is overstated; honest deliverable is Protocol+Fake on the existing single walk.**
  The canonicalizer already *delegates* to `resolve_mission` (`_read_path_resolver.py:503`); it is not a
  rival walk. Phase-2 puts a port face on the one `_build_index` walk (+ adopts 2 missed identity
  consumers: `doctrine_synthesizer/apply.py:602/788`, `vcs/detection.py:169`). We do NOT oversell a
  six-way collapse.
- **D3 — #2139 is a reconcile-first SIBLING WP, not a resolver method.** `read_target_branch_from_meta`
  already exists as the authority; making `target_branch` a resolver method conflates mission-selection
  with field-extraction (widens the port past its concern). Work = route 4 stragglers + delete divergent
  `"main"`/`""`/`KeyError` defaults.
- **D4 — No cache in Phase-2.** Request-scoped resolver only; module/process-level `@lru_cache` is a
  correctness trap because `merge/ordering.py` mutates the scanned surface under the merge lock and the
  dashboard daemon is long-lived. The Phase-2 win is the seam (Fake → FS-free builder test), not perf.
- **D5 — Clock is 3 helpers, not 1.** Collapse the 12 byte-identical isoformat copies; preserve the 2
  `%Y-%m-%dT%H:%M:%SZ` stamp callers (`task_utils/support.py:101`, `mission_parsing.py:257`) and the 2
  `-> datetime` callers (`decisions/emit.py:64`, `decisions/service.py:86`) as distinct helpers. Folding
  them would change on-disk timestamp serialization (NFR-004).
- **D6 — Fail-closed-loud, no legacy branch.** Cold-miss → structured not-found → `backfill-identity`;
  ambiguity → `MissionSelectorAmbiguous`. Forbidden shape: `if <canonical> is None: <fallback>` /
  `mission_id or slug` (ADR `2026-07-01-1`; motivating incident PR #2277 — the real root was stale
  non-canonical fixtures, not a missing fallback). Fake fixtures must be canonical-shaped.
- **D7 — Scope to MissionResolver only.** The `#2173` epic title still lists 5 ports; the synthesis
  rejected 4 (GitOps=consolidation-not-absence; ProcessEnv/Clock=monkeypatch suffices; SaaSQueue=already
  seamed). Spec states this explicitly (C-008) so the title cannot pull scope back in.
- **D8 — Bind by construction.** Ship an ADR + a new AST call-site gate (`FsMissionResolver` = single
  sanctioned walker) together, copying the `test_protection_resolver_call_sites.py` precedent — otherwise
  the invariant is reviewer-vigilance, not structural, and walker #7 reappears.

## Open questions — RESOLVED at /plan (2026-07-08, by code analysis)
- **Q1 → context/mission_resolver.py::resolve_mission.** `runtime/resolver.py` has NO `resolve_mission`
  — it resolves template/config *paths* (`resolve_command_template_path`, …), a different concern; not a
  rival. The canonicalizer already delegates to the context resolver (`_read_path_resolver.py:503`),
  confirming it is the single identity walk. See research.md D-Q1.
- **Q2 → co-locate the port in `src/specify_cli/context/mission_resolver.py`** (not `mission_runtime`).
  The walk + `ResolvedMission` + errors already live there; `mission_runtime` submodules are
  external-import-forbidden (MR gate) but tests/CLI must import the Fake; and `mission_runtime → specify_cli`
  is already an established direction (`resolution.py:327/344/394…`). See research.md D-Q2.

## Post-plan squad revisions (2026-07-08, operator ruling: FULL TRUNK)
- **D-08 — full trunk, not a 7th path.** Route all 8 free-fn `resolve_mission` callers + the canonicalizer
  through the port; free `resolve_mission` gains optional `resolver` param. (Split-brain flag: the dominant
  read path reached the walk via the free fn, bypassing an assembler-injected port.)
- **D-Q2 REVISED — Protocol in `mission_runtime`, adapters in `specify_cli.context`.** Original co-location
  reds `test_layer_rules.py` (`_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI` omits `context`). Dodge the ledger
  (which #2173 exists to DRAIN) by keeping the shell referencing a local Protocol; adapters import it
  downward. Acceptance: zero new ledger edge.
- **D-01 REVISED — seam at the callers of `_resolve_mission_slug`, threaded through the canonicalizer** —
  not inside `_assemble_core_fragments` (which runs after, and consumes the slug as input).
- **D-07 — `legacy-<slug>` bootstrap sentinel is a documented carve-out**, not routed through fail-closed
  `resolve()` (else mission-create/scaffold breaks). Distinct from the forbidden `is None` fallback.
- **D-09 — NFR-001 scoped to the identity leg** (the assembler has 4+ other FS legs; `build_execution_context`
  is already FS-free). Remaining legs = later #2173 phases.
- **Census expansions**: Clock 12→14 (2 cross-package triaged); #2139 4→≥9 (route or triage KeyError reads);
  AST-gate allowlist seeds ~16 walkers day-one.

## D-10 — DDD rename ExecutionContext → MissionExecutionContext (operator, 2026-07-08, IC-00)
Code follows ubiquitous language: `MissionExecutionContext` is already the name in the class docstring
(context.py:11), the parity test (test_execution_context_parity.py:1545), and the #1619 epic title. Plus it
**collides** with `core/context_validation.py:41 class ExecutionContext(StrEnum)` — renaming the
`mission_runtime.context` composite disambiguates. Scope: class + ActionContext alias + ~12 importers (20
files) + ADR prose. HARD EXCLUSION: the StrEnum (different type). Land FIRST (IC-00). Bulk-edit-shaped →
scoped occurrence classification at /tasks; NOT wholesale change_mode:bulk_edit. Verify with full arch
suite + test_mission_runtime_surface + test_execution_context_parity (collision = whack-a-symbol trap).
See [[feedback_brownfield_logical_duplication_consolidation]] discipline; ADJACENT: the StrEnum's own name smell.

## Decisions made during implement
_(append here)_
