# Implementation Plan: Charter Pack Usage Journey

**Branch**: `feat/charter-pack-usage-journey` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/charter-pack-usage-journey-01KYWWTF/spec.md`
**Research basis**: [notes/research-synthesis.md](./notes/research-synthesis.md) (authoritative design input — 2-lens research squad + revision-squad refresh vs landed M1)

## Summary

`charter pack apply` writes the activation store (`config.yaml` `activated_*`) but nothing compiles it into
the read-authority bundle (`.kittify/charter/charter.yaml`), and several read/dispatch surfaces gate on the
wrong artifact. The result: applying a pack *disables* the safe generic-agent dispatch fallback (#3104),
leaves `charter context`/`charter status` reporting "not found" (#3105), and lets `resolve_project_governance`
report all 29 built-in directives instead of the 5 activated (US3). This mission **wires `apply` to the
existing compile seam** (opt-in `--compile`, truthful default output), **retargets the presence read-gates**
onto `charter.yaml`, **rewrites the dispatch predicate** to key on compiled-bundle-presence + direct
routability (org-pack safe), and **retires the resolver catalog-fallback** so governance has one directive
authority. Folded in per operator direction: make advertised charter section selectors resolve (#3095/#3094),
reconcile the `spec-kitty analyze` surface (#3096), and add a path-filtered CI workflow for
`src/doctrine/**` + `src/charter/**` (#3102). No new compiler is built — the config→bundle lowering
(`compile_charter`/`write_compiled_charter`, exposed as `charter generate`) already exists.

## Technical Context

**Language/Version**: Python 3.11+ (project standard; 3.12 idioms permitted)
**Primary Dependencies**: Typer (CLI), ruamel.yaml (config/bundle I/O), `spec_kitty_events`/`spec_kitty_tracker` (public imports only) — no new runtime deps
**Storage**: On-disk governance artifacts under `.kittify/charter/` (`charter.yaml` compiled bundle = read authority; `charter.md` display-only companion; `config.yaml` `activated_*` = write store)
**Testing**: `pytest` (targeted node-ids locally, `-n auto --dist loadfile` for parallel); the 8 journey acceptance tests (synthesis §"Journey acceptance tests") are the behavioral regression net; `ruff` + `mypy` zero-new-issue gate
**Target Platform**: Linux/macOS developer + CI (GitHub Actions)
**Project Type**: single (CLI + library — `src/charter/`, `src/specify_cli/`, `src/doctrine/`)
**Performance Goals**: `is_charter_empty` on an unconfigured repo ≤ 1 `PackContext.from_config` + 1 `stat`, no URN load (NFR-001, folds #3118)
**Constraints**: opt-in `--compile` (default `apply` stays git-agnostic, C-004); presence-gate retarget and section-selector fix stay two distinct paths (C-003); must not revert M1's landed `resolver.py:187/:250` operator strings (C-002); classify reds vs merge-base, never green-wash (C-005)
**Scale/Scope**: ~7 code modules + 1 CI workflow + journey docs; 12 FR / 4 NFR / 5 C; behavioral (no bulk edit, no occurrence_map)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Loaded via `spec-kitty charter context --action plan` (mode: compact). Relevant governing principles and how
this plan satisfies them:

- **Single canonical authority** — the mission's *entire thesis* is collapsing a divergent second authority:
  one compiled bundle (`charter.yaml`) as the read authority, one write store (`config.yaml`/pointer), one
  directive authority (activated set, retiring the catalog-fallback). ✅ Aligned, not in tension.
- **No legacy resolver paths** — FR-007 retires the catalog-fallback branch rather than adding a
  no-canonical-field fallback. ✅
- **ATDD-first / red-first** — journey test #6 (resolver returns 5 not 29) is RED on the current tree; it is
  authored first and drives FR-007. The 8 journeys are executable acceptance tests (NFR-002). ✅
- **Campsite cleaning** — the dead composite-predicate docstring + the now-dead `charter_activated_urns`
  import (NOT `PackContext`, which stays live) in `empty_charter.py`, and the 2 identical `path`/`apply`
  resolve-or-exit blocks in `pack.py` (`list_cmd`'s narrower variant left alone), are cleaned *while editing
  those files* — scoped, no creep. ✅
- **Canonical sources** — wires the existing `charter generate` compile seam; does not hand-roll a compiler
  or reconstruct paths the resolver should provide. ✅
- **Terminology adherence** — no `feature*` terms introduced; run `test_no_legacy_terminology.py` before
  pushing doctrine/prose (FR-009/FR-010/FR-011 touch prose + templates). ✅
- **Behaviour-change transparency** — the deliberate reversal of #3064's glossary-pack dimension is recorded
  (NFR-004, SC-005) with a pinning test, not slipped. ✅

No violations to justify — Complexity Tracking left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/charter-pack-usage-journey-01KYWWTF/
├── plan.md              # This file
├── spec.md              # Mission spec (12 FR / 4 NFR / 5 C)
├── research.md          # Phase 0 — the one open plan decision (FR-010 content-vs-advertise)
├── notes/
│   └── research-synthesis.md   # Authoritative design input (squad + revision refresh)
├── contracts/           # Phase 1 — behavioral contracts for the predicate + bridge + resolver
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   ├── context.py                # build_charter_context presence gate (IC-03) — retarget to charter.yaml; keep prose readers on charter.md; NOT edited by IC-06
│   ├── context_json.py           # _project_charter_json_block (IC-03 owns edits; IC-04 reads :141 only) — soft-retarget present-signal
│   ├── resolver.py               # _resolve_directives_selection / resolve_project_governance (IC-04) — retire catalog-fallback; DO NOT touch M1's :187/:250 strings; wrapper :57-139 is NOT the fix
│   ├── bundle.py                 # CHARTER_YAML constant :48 — REUSED by IC-03 library gates (layer rule: src/charter must not import specify_cli)
│   ├── pack_context.py           # PackContext.activated_directives :144 (three-state) — read by IC-01 + IC-04
│   ├── compiler.py               # compile_charter / write_compiled_charter — REUSED, not modified (bridge target)
│   └── context_renderers/
│       └── section_bodies.py     # render_critical_section_include :282 (IC-06) — the #3095/#3094/#2552 section-selector engine (None→placeholder)
├── specify_cli/
│   ├── invocation/
│   │   └── empty_charter.py      # is_charter_empty :48-67 (IC-01) — rewrite to bundle-presence + routability (NOT under src/charter/; OUTSIDE IC-08's path filter)
│   ├── cli/commands/charter/
│   │   ├── pack.py               # apply (IC-02) — add --compile bridge + truthful output; hoist 2 (path/apply) resolve-or-exit blocks
│   │   ├── context.py            # :158 fallback default (IC-03) — 2nd project_charter present-signal site, keep consistent with FR-006
│   │   ├── _common.py            # NEW sibling _resolve_charter_bundle_path (IC-03, CLI-layer) — do NOT retarget _resolve_charter_path in place
│   │   ├── _status_collectors.py # _collect_charter_sync_status :62 (IC-03) — route presence gate through the sibling resolver
│   │   └── generate.py           # _CHARTER_MD_COMPANION_SEED :189 (IC-06 secondary, #2808-contested) — optional seed enrichment
│   ├── cli/commands/             # analyze surface reconciliation (IC-07, #3096)
│   └── upgrade/migrations/m_unify_charter_activation_finalize.py  # fourth producer — convergence ASSERTED (IC-05, document-as-equivalent), not modified

tests/
├── charter/                      # journey acceptance tests (NFR-002) — predicate, bridge, resolver, presence-gate
└── ...                           # convergence test (IC-05), perf spy (NFR-001)

.github/workflows/                # path-filtered doctrine/charter CI (IC-08, #3102)
docs/                             # charter journey guides (IC-09, FR-009) + analyze-surface docs (IC-07)
.agents/skills/spec-kitty.analyze/ # OR the skill/mapping redirect (IC-07 alternative)
```

**Structure Decision**: Single-project layout. Governance code lives in `src/charter/` (library) and
`src/specify_cli/cli/commands/charter/` (CLI surface); the compile seam in `src/charter/activation/compiler.py` is
reused unchanged. All file:line anchors below are **symbol-anchored** — `context.py` has drifted twice
(M1's #3116 shim removal shifted it), so implementers resolve by symbol, using the synthesis re-anchor table
as a hint, and re-verify against HEAD before editing (C-002).

## Complexity Tracking

*No Charter Check violations — not applicable.*

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into
> executable WPs — one concern may become one WP or split; small concerns may merge.

### IC-01 — Dispatch-net predicate: bundle-presence + org-pack-safe routability

- **Purpose**: Rewrite `is_charter_empty` so applying a pack without compiling keeps the generic-agent
  safety net, while a compiled bundle or a routable org/profile config disengages it — fixing #3104 without
  regressing org-pack projects.
- **Relevant requirements**: FR-001, FR-002, NFR-001 (folds #3118), NFR-004, SC-001, SC-005.
- **Affected surfaces**: `src/specify_cli/invocation/empty_charter.py` (`is_charter_empty` `:48-67`,
  `_MATCH_REASON` `:42`) — **note the real path is `src/specify_cli/invocation/`, NOT `src/charter/`**
  (squad-corrected). Campsite: delete the dead ~20-line dimension-enumeration docstring + the now-dead
  `charter_activated_urns` import (`:33`) and its `:56` call — **keep `PackContext`** (`:33`), the rewritten
  predicate still calls `PackContext.from_config` / `.org_roots` / `.activated_agent_profiles`; update
  `_MATCH_REASON` to the bundle-presence rationale so the warning panel doesn't lie.
- **Sequencing/depends-on**: none (foundational; other concerns can proceed in parallel).
- **Risks**: A pure `charter.yaml`-presence predicate is NOT #3064-safe — MUST split governance-emptiness
  from dispatch-routability (`org_roots != ()`, `activated_agent_profiles is not None`). Pin the
  bootstrapped-empty-bundle-keeps-net-OFF behaviour (SC-005) so a future contents-inspecting "improvement"
  can't re-import the #3064 exhaustiveness trap. **Pin the `frozenset()` opt-out** (explicit zero-profile
  activation keeps the net disengaged — same as today's `:59`), so a later reader can't "tidy" `is not None`
  into truthiness (m6). Record the deliberate drop of **all** non-routing dimensions, not just glossary
  (NFR-004). **IC-08 coupling:** this file is outside IC-08's `src/charter/**`/`src/doctrine/**` filter —
  flag to IC-08 so the P1 predicate + dispatch-net journey tests get gated (see IC-08 risk).

### IC-02 — `apply --compile` bridge + truthful default output

- **Purpose**: Chain the existing compile seam after the config merge (opt-in `--compile`), and make default
  `apply` name the exact next command instead of hand-waving — giving the operator a signalled path from
  "activated" to "governance delivered".
- **Relevant requirements**: FR-003, FR-004, SC-004; journey tests 2 & 7.
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/pack.py` (`apply` `:200-205` output;
  `--compile` flag chaining `charter generate --no-from-interview` / `compile_charter`+`write_compiled_charter`).
  Campsite: hoist the **2 identical** `path_cmd`/`apply_cmd` resolve-or-exit try-blocks (`:112`/`:146`, both
  catch `(UnknownPackError, FileNotFoundError)`) — **NOT 4×**; `list_cmd` (`:78`) is a narrower variant
  (list-comprehension, catches `FileNotFoundError` only) — leave it or reconcile its except set explicitly,
  do not force it into the shared helper (m-4).
- **Sequencing/depends-on**: none (reuses `compiler.py`; introduces no compiler code).
- **Risks**: `--compile` inherits `charter generate`'s **git-worktree requirement** (`generate.py:313`) —
  document it; default `apply` MUST stay git-agnostic pure-merge (C-004). Do not auto-compile.

### IC-03 — Read-surface presence-gate retarget (charter.yaml authority)

- **Purpose**: Make `charter context` / `charter status` reflect the operator's activations once the bundle
  is compiled — retarget the *presence* gates from display-only `charter.md` onto authoritative
  `charter.yaml`, without entangling the prose readers.
- **Relevant requirements**: FR-005, FR-006, SC-002; journey tests 4 & 5 (incl. `charter.md`-deletion) + the
  FR-006 JSON present-signal test.
- **Affected surfaces**: `src/charter/activation/context.py` (`build_charter_context` `CHARTER_MD` presence gate `:206`/
  `:236` — render `charter.md` prose only when present, graceful-degrade; **reuse `charter.bundle.CHARTER_YAML`
  `bundle.py:48`**, never a fresh `"charter.yaml"` literal); `src/charter/activation/context_json.py:87`
  (`_project_charter_json_block` soft-retarget — **IC-03 owns this file's edits**); the **2nd present-signal
  site `src/specify_cli/cli/commands/charter/context.py:158`** (the `{"present": False, "path": "…charter.md"}`
  fallback default — keep consistent with the producer); `_common.py` (**NEW** CLI-layer sibling
  `_resolve_charter_bundle_path`, do NOT retarget the shared `_resolve_charter_path:27` — it serves prose
  consumers `status.py`/`resynthesize.py`); `_status_collectors.py:62` (route presence through the sibling —
  its `charter.yaml`-aware logic at `:65-76` is dead today because `:62` raises first).
- **Sequencing/depends-on**: none. **Sole owner of `context.py` and `context_json.py`** (IC-04 reads
  `context_json.py:141` but must not edit it; IC-06 does NOT touch `context.py`).
- **Risks**: **C-003** — must NOT collapse the presence gate and the prose readers (`context.py` section
  reader `:342-354`, prose body reads) onto one shared path constant (whack-a-field that breaks #3094/#3095).
  Two paths stay two paths. **Two-layer split is forced** (the `src/charter/` layer must not import
  `specify_cli`): library gates use the `bundle.CHARTER_YAML` constant, the CLI sibling resolver serves CLI
  consumers only. **FR-006 flips a `charter context --json` contract** (`project_charter.present`) — record it
  as deliberate (NFR-004), enumerate consumers, cross-ref #2787; add its own test (M-2, priti m3). **IC-03 is
  at the ~7-subtask / 4-file ceiling** — hold a split (presence-gate vs status-collector) ready if the WP
  prompt exceeds ~500 lines (priti m5).

### IC-04 — Single directive authority: retire the catalog-fallback

- **Purpose**: Stop `resolve_project_governance` from being a second, divergent directive authority — when
  the authored selection is empty (as after apply+compile), source directives from the config-activated set,
  never the full built-in catalog.
- **Relevant requirements**: FR-007, US3, SC-003; journey test 6 (RED today) + the bare-project regression.
- **Affected surfaces**: `src/charter/activation/resolver.py` — the fix-locus is **`_resolve_directives_selection`
  (`:233`, catalog-fallback `:258-260`) and `resolve_project_governance` (`:289`, builds unfiltered catalog at
  `:316`, constructs no `PackContext`)**. Thread `PackContext.from_config(repo_root).activated_directives` down
  and use it as the fallback *source*. **The `DoctrineService` wrapper (`:57-139`) is NOT the fix** — all 5
  consumers call `resolve_project_governance` directly and never traverse the wrapper (the wrapper is the
  context-bundle path that already returns 5); adding a `directives` property there would leave journey-6 RED
  (alphonso M2). Treat the wrapper gap as an out-of-scope observation, not this concern's edit.
- **Sequencing/depends-on**: none, but **shares `resolver.py` with M1's landed changes** — re-verify M1's
  `:187`/`:250` operator strings at HEAD and do NOT revert them (C-002). Trusts M1's unified activation
  vocabulary (C-001, landed). Reads `context_json.py:141` for consumer verification — **read-only** (IC-03
  owns that file's edits).
- **Risks**: **Three-state `activated_directives`** (`pack_context.py:144`: `None` = no pack → return all;
  `frozenset()` = explicit opt-out → empty; `{ids}` = filter) — filter to the activated set **only when
  `activated_directives is not None`**; when `None` keep the existing catalog default. A naive
  `sorted(activated or frozenset())` regresses a **bare project 29→0** (alphonso M3) — add a bare-project
  regression test (no pack → directives == catalog default, `directives_source` unchanged) as a sibling to
  journey 6. The 5 consumers (`prompt_builder.py:437`, `runtime/doctor.py:133`, `context_json.py:141`,
  `compact.py:303`, `resolver.py:415`) carry no `charter.md` pre-gate — only the fallback *source* changes;
  verify none depended on the 29-catalog behaviour.

### IC-05 — Fourth-producer convergence assertion

- **Purpose**: Keep the config→bundle transform one authority — assert `apply --compile` and the
  `spec-kitty upgrade` finalize migration produce a convergent `charter.yaml` shape (or document the
  migration as the upgrade-time equivalent).
- **Relevant requirements**: FR-008 (narrowed post-M1 — assert transform *shape* only; vocabulary is already
  one authority via M1's `ACTIVATION_YAML_KEYS`).
- **Affected surfaces**: test-only; references the finalize migration's full-document producer
  `_compose_charter_yaml_document`+`_write_new_charter_yaml` (`m_unify_charter_activation_finalize.py:240-281`)
  and `write_compiled_charter`. No production edit to the migration. (paula confirmed these two are the only
  full-document config→bundle producers — no 5th.)
- **Sequencing/depends-on**: IC-02 (asserts the bridge's output shape). **Undersized (~2 subtasks, test-only)
  — fold into IC-02's WP at /tasks** unless a standalone tiny WP is cleaner (priti m1).
- **Risks**: Narrow — do not re-unify the vocabulary (M1 owns it, C-005). The migration embeds raw `activated_*`
  keys (`:266-268`) + a store/pointer model while `write_compiled_charter` is a pure derived read-cache, so
  they will **not** be byte-convergent — assert on **catalog-shape derived from the same activation input**
  (the "document-as-equivalent" branch), not field-identity, or the test codifies a latent divergence (m-6).

### IC-06 — Advertised section selectors resolve (#3095/#3094 + #2552)

- **Purpose**: Make `charter context --include section:terminology-canon` / `section:code-review-checklist`
  (required by generated `implement`/`review` prompts) resolve instead of dead-ending — closing #3095, its
  terminology-canon twin #3094, **and its code-review-checklist twin #2552**.
- **Relevant requirements**: FR-010, SC-007 (partial); acceptance US4.1.
- **Affected surfaces**: **`src/charter/activation/context_renderers/section_bodies.py::render_critical_section_include`
  ONLY** (`:282`; returns `None` at `:308-311` when the heading is absent). Make it return an **honest
  placeholder** ("This charter has not yet authored a *Terminology Canon* section — add one to
  `.kittify/charter/charter.md`") instead of `None`, so the selector always resolves *and* the dead-end raise
  at `context.py:354` is never reached — **keeping `context.py` untouched** (IC-03's exclusive file; priti's
  MAJOR ownership fix). Optional secondary: enrich `generate.py:_CHARTER_MD_COMPANION_SEED` (`:189`) with stub
  section headings. **Stays on the `charter.md`/section prose path (C-003)** — does NOT retarget to
  `charter.yaml`.
- **Sequencing/depends-on**: **primary graceful-degrade is dependency-free** (pure prose-path change,
  independent of whether the compile ran); only the *optional secondary* seed enrichment soft-depends on the
  bridge existing (alphonso m4 — do not over-serialize the whole concern behind IC-02).
- **Risks**: The primary graceful-degrade is the #2808-safe fix (operators still author their own content).
  The **secondary seed-stub tensions with #2808** ("no example content scaffolded") — prefer shipping only the
  placeholder and defer/omit the seed-stub unless reconciled with #2808 (paula m-7). If touching
  `src/doctrine/` prompts at all, run `test_no_legacy_terminology.py`.

### IC-07 — `spec-kitty analyze` surface reconciliation (#3096)

- **Purpose**: Make the documented `spec-kitty analyze` surface and the CLI agree — no documented-but-absent
  command.
- **Relevant requirements**: FR-011, SC-007 (partial); acceptance US4.2.
- **Affected surfaces**: EITHER a thin `spec-kitty analyze` alias to the supported `agent mission
  record-analysis` flow (`src/specify_cli/cli/commands/`), OR the `spec-kitty.analyze` skill +
  command-skills manifest + docs redirected to the supported command.
- **Sequencing/depends-on**: none.
- **Risks**: If exposing an alias, it must route through the canonical `record-analysis` flow (no
  reimplementation — missing-CLI-command-is-a-gap → trace source). If redirecting, update all 19 agent
  surfaces consistently (skill + manifest + docs). **Scope-creep guard (paula m-8):** this is
  surface-*reconciliation* only — do NOT absorb the `analyze`-*expansion* issues (#849/#851/#853, which want
  `analyze` to do readiness-review / product-coherence / full-corpus). Decision 2 (research.md) redirects to
  the supported command; fall back to a thin alias only if a caller hard-codes `spec-kitty analyze`.

### IC-08 — Path-filtered doctrine/charter CI workflow (#3102)

- **Purpose**: Give PRs touching `src/doctrine/**` / `src/charter/**` fast isolated feedback (DRG
  freshness/sharding, charter-context resolution, the architectural/adversarial gates) and spare unrelated
  PRs that cost/noise.
- **Relevant requirements**: FR-012, SC-007 (partial); acceptance US4.3.
- **Affected surfaces**: `.github/workflows/` (new path-filtered workflow; `paths:` on `src/doctrine/**` +
  `src/charter/**` — **and `src/specify_cli/invocation/**`**, see risk).
- **Sequencing/depends-on**: none (its seam-work prerequisite is satisfied by M1 landing; does NOT require
  #3101 wheel-split).
- **Risks**: **Coverage gap (alphonso M1, MAJOR):** the #3104 P1 centerpiece `is_charter_empty` and its
  dispatch-net journey tests (1–3) live under `src/specify_cli/invocation/` — **outside** a bare
  `src/charter/**`+`src/doctrine/**` filter. Either **widen the `paths:` set to include
  `src/specify_cli/invocation/`** (empty_charter + router + executor + the net tests) so the P1 fix is gated,
  or explicitly accept those tests ride the main CI only and document that in the workflow. Do not let the
  filter falsely imply the predicate layer is covered. Path-filter un-skip semantics — a PR that changes none
  of the filtered paths must **skip-with-green** (required check satisfied when skipped), not skip-with-fail.
  Do not duplicate gates the main CI already runs in a way that double-charges.

### IC-09 — Journey documentation (#3107 partial fold)

- **Purpose**: Document the `apply` → `generate` two-step and the empty-charter dispatch behaviour in the
  charter journey guides, so the operator-facing story matches the new behaviour.
- **Relevant requirements**: FR-009.
- **Affected surfaces**: charter journey guides under `docs/`; freshen page-inventory + docs-index if pages
  are added.
- **Sequencing/depends-on**: IC-01, IC-02, IC-03 (documents their delivered behaviour).
- **Risks**: The inert CLI-reference parity gate of #3107 is **out of scope** (docs-infra, C-005) — document
  the journey only. Run `test_no_legacy_terminology.py` on prose changes.
