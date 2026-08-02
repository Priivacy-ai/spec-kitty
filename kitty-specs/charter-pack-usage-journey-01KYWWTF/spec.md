# Mission Specification: Charter Pack Usage Journey

**Mission**: `charter-pack-usage-journey-01KYWWTF`
**Type**: software-dev (behavioural / usability)
**Status**: Draft
**Purpose (TL;DR)**: Make `charter pack apply` actually deliver usable governance — so applying a pack no
longer silently breaks dispatch or leaves `charter context`/`charter status` reporting the charter as missing.

> Research basis: a 2-lens research squad (architect-alphonso — architecture + reproduced all 8 journeys
> end-to-end; paula-patterns — related-issues + campsite) scoped this mission. Full synthesis in
> `notes/research-synthesis.md`. This is **Mission 2 of 2**; Mission 1
> (`doctrine-built-in-seam-consolidation`, #3119/#3106/#3116/#3120/#3090) has **LANDED on main**
> (`873832aa1` + `fd53023b6`) — this mission is rebased onto it and its M1-precondition constraints
> (C-001/C-002) are now satisfied facts. The spec was **revision-refreshed** against the post-M1
> tree (2-agent revision squad, 2026-08-01): design re-validated (all root causes reproduce live),
> file refs re-anchored past M1's `context.py` shim-removal shift.
>
> **Scope closes: #3104, #3105, #3118** (the core usage journey) **plus, folded in per operator
> direction: #3095** (advertised charter section selectors don't resolve — with its terminology-canon
> generated-prompt twin **#3094** and its code-review-checklist twin **#2552**, all the same root cause),
> **#3096** (the documented `spec-kitty analyze` command is missing from the CLI), and **#3102** (a
> path-filtered CI workflow for `src/doctrine/**` + `src/charter/**`). These adjacent charter/doctrine
> tooling & CI-hygiene items are grouped here rather than left as loose follow-ups. Spec + IC map
> post-plan-squad-refreshed (2026-08-02): FR-007 fix-locus corrected off the inert `DoctrineService`
> wrapper onto `resolve_project_governance` + three-state guard; `empty_charter.py` re-anchored to
> `src/specify_cli/invocation/`; FR-006 second present-signal site + `--json` contract flip recorded.

## User Scenarios & Testing *(mandatory)*

The user is an **operator** setting up governance on a project, and the **runtime dispatch** that routes
their requests. The failure: applying a charter pack today delivers *less* usable governance than doing
nothing — it disables the safe dispatch fallback and the governance surfaces still report "not found".

### User Story 1 - Applying a pack keeps dispatch safe (Priority: P1, #3104)

An operator on an unconfigured project runs `spec-kitty charter pack apply minimal` to get started. Today
that flips the "is the charter configured?" check to true (config.yaml now has activation keys) but
activates **no routable agent profile** — so the generic-agent dispatch safety net switches off and the
next unmatched `spec-kitty dispatch` hard-fails with `ROUTER_NO_MATCH`. Applying a pack must never leave
dispatch *worse* than an empty project: an unmatched request must still fall back to the warned generic
agent until the project actually has routable governance.

**Why this priority**: it is a P1 regression where the documented "get started" remedy actively breaks the
thing it is meant to help.

**Acceptance**:
1. **Given** an empty project, **when** an unmatched request is dispatched, **then** it falls back to the
   warned generic agent (baseline).
2. **Given** `charter pack apply minimal` **without** a compile, **when** the same unmatched request is
   dispatched, **then** it **still** falls back to the generic agent — **not** `ROUTER_NO_MATCH`.
3. **Given** a project whose pack has been compiled into the bundle, **when** an unmatched request is
   dispatched, **then** the router runs and `ROUTER_NO_MATCH` is the *honest* signal (the project opted in).
4. **Given** a project configured with an **org pack** (routable profiles, no compiled bundle), **when** an
   unmatched request is dispatched, **then** the net stays disengaged and the router reaches the org
   profiles (no regression — the fix must not fire the net for genuinely-routable projects).

### User Story 2 - Applying a pack (and compiling) delivers working governance (Priority: P1, #3105)

After applying a pack, the operator checks `charter context --action implement` and `charter status`.
Today both report the charter as **missing** — they gate on the display-only `charter.md`, which `apply`
never creates, instead of the authoritative compiled bundle `charter.yaml`. The governance read surfaces
must reflect the operator's activations once the bundle is compiled, and `apply` must tell the operator the
exact step to get there.

**Why this priority**: without this, `apply` is a dead end — the operator has no signalled path from
"activated" to "governance actually delivered".

**Acceptance**:
1. **Given** a pack applied and compiled, **when** `charter context --action implement` runs, **then** it
   renders the pack's activated directive/tactic set (not "Charter file not found", not the full catalog).
2. **Given** a compiled bundle is present, **when** the display-only `charter.md` is deleted, **then**
   `charter context` and `charter status` **still** work — proving the gate is on `charter.yaml`, not
   `charter.md`.
3. **Given** a pack applied and compiled, **when** `charter status` runs, **then** it reports the charter as
   available/synced.
4. **Given** an operator runs `apply` **without** `--compile`, **when** they read its output, **then** it
   names the exact next command (`spec-kitty charter generate`) — no vague "a compile may be needed".
5. **Given** `charter context --include section:<id>` (a prose selector), **when** it runs, **then** it
   still reads `charter.md` prose — this mission must **not** entangle the prose readers (#3094/#3095).

### User Story 3 - Governance has one directive authority (Priority: P2)

The resolver that several surfaces use (`resolve_project_governance`) silently falls back to **all** built-in
directives when the authored governance selection is empty — which it is after a pack-apply+compile. So a
project that activated 5 directives is reported by that path as having all 29. Governance must have **one**
directive authority (the activated set), not a divergent catalog-fallback second source.

**Why this priority**: it is a correctness divergence (5 vs 29) that undermines the whole point of activating
a curated pack, and it is the load-bearing "no legacy resolver paths" cleanup C-004 depends on.

**Acceptance**:
1. **Given** a pack activating 5 directives, applied + compiled, **when** `resolve_project_governance` runs,
   **then** its directives are the 5 activated (from the compiled catalog / activation authority), **not**
   the 29-directive built-in catalog-fallback.

### User Story 4 - Charter/doctrine tooling advertises only what it delivers (Priority: P2, folded: #3095/#3094, #3096, #3102)

Three adjacent tooling gaps make the charter/doctrine surface advertise commands or selectors that do not
resolve, and make its CI feedback slow and unfocused. An operator or agent should never be told to run a
governance selector or command that the installed CLI rejects, and a doctrine/charter-scoped change should
get fast, isolated CI feedback.

**Why this priority**: these are correctness-of-advertised-surface + contributor-feedback items in the same
charter/doctrine neighbourhood; grouping them here avoids leaving loose follow-ups after the bridge work
already opens these files/areas.

**Acceptance**:
1. **Given** a generated implement prompt or action-context that requires `charter context --include
   section:terminology-canon` / `section:code-review-checklist`, **when** that selector is run against a
   charter surface, **then** it **resolves** to the corresponding section — or the surface no longer
   advertises a selector it cannot resolve (no "No charter section found for selector" dead-end). Covers
   **#3095** and its generated-prompt twin **#3094**.
2. **Given** an operator or agent follows the documented `spec-kitty analyze` surface, **when** they invoke
   it, **then** the command exists (an alias to the supported `agent mission record-analysis` flow) — or the
   skill/command mapping and docs direct them *only* to the supported command, with no documented-but-absent
   surface. Covers **#3096**.
3. **Given** a PR that changes only `src/doctrine/**` / `src/charter/**` (or one that changes neither),
   **when** CI runs, **then** the doctrine/charter test surface (DRG freshness/sharding, charter-context
   resolution, the architectural/adversarial gates) runs in a dedicated **path-filtered** workflow — giving
   the doctrine/charter change fast isolated feedback and sparing unrelated PRs that cost/noise. Covers
   **#3102**.

### Edge Cases

- **"Empty" means the compiled bundle is ABSENT**, never "bundle present but activations empty". A
  `charter generate` on a bare project bootstraps a near-empty `charter.yaml`; the dispatch predicate must
  treat that as *not* empty (the operator opted into a compiled bundle → `ROUTER_NO_MATCH` is honest). A
  future "improvement" that inspects bundle *contents* would re-import the #3064 exhaustiveness trap — a
  test must pin the bootstrapped-empty-bundle-keeps-net-OFF behaviour.
- `apply --compile` inherits `charter generate`'s **git-worktree requirement**; default `apply` stays
  git-agnostic (pure additive merge). Both paths are journey-tested.
- A **fourth** config→bundle producer already exists (the `spec-kitty upgrade` finalize migration mints
  `charter.yaml` from bare config and strips `activated_*`). `apply --compile` must **converge** with it —
  same shape — so the config→bundle transform stays one authority.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Fix the dispatch-net predicate (`is_charter_empty`) so it keys on **compiled-bundle presence** (`.kittify/charter/charter.yaml`) plus the direct dispatch-routability sources (`org_roots`, `activated_agent_profiles`) — NOT the config activation aggregate — so `apply`-without-compile keeps the generic-agent net, while a compiled bundle or a routable org/profile config disengages it. | Draft |
| FR-002 | The predicate must be org-pack/profile safe: a project with an org pack or explicit agent-profile activation (routable without a compiled bundle) does **not** fire the net (no regression); a glossary-only/directive-only project with no bundle **does** fire it. | Draft |
| FR-003 | Wire `charter pack apply --compile` to chain the **existing** compile seam (`charter generate --no-from-interview` / `compile_charter`+`write_compiled_charter`) after the config merge — introducing no new compiler code; the flag inherits and documents `generate`'s git-worktree requirement. | Draft |
| FR-004 | Make default `apply` output **truthful**: name the exact next command (`spec-kitty charter generate`) required to deliver governance, replacing today's vague "a compile may still be needed". | Draft |
| FR-005 | Retarget the charter **presence** read gates from the display-only `charter.md` onto the authoritative `charter.yaml`: the `build_charter_context` bootstrap gate (`context.py`, the `canonical_root / CHARTER_MD` presence check ~`:206`/`:233`/`:236` post-M1, rendering `charter.md` prose only when present) and the status/context presence path via a **new sibling** bundle-path resolver (`_resolve_charter_bundle_path`) — the shared `_common._resolve_charter_path` (`:27`, raises on `charter.md` absent) is NOT retargeted in place (it serves prose consumers). **Nuance:** `_status_collectors._collect_charter_sync_status` calls `_resolve_charter_path` at `:62` *before* its own `charter.yaml`-aware logic (`:65-76`) runs, so that awareness is dead when `charter.md` is absent — routing the presence gate through the sibling resolver is what fixes it. | Draft |
| FR-006 | Soften the JSON project-charter "present" signal to report `charter.yaml` (authority) presence as primary; `charter.md` presence becomes a secondary display field. **Two sites** carry this signal and must stay consistent: `context_json._project_charter_json_block` (`context_json.py:87`, the producer) **and** the hardcoded fallback default in `cli/commands/charter/context.py:158` (`{"present": False, "path": ".kittify/charter/charter.md"}`). This flips a **`charter context --json` machine-output contract** — record it as a deliberate contract change (SC-002 requires `present` to key on `charter.yaml` so it survives `charter.md` deletion), enumerate `project_charter.present` consumers, and cross-reference #2787 (freeze-the-`--json`-contract appetite). Library-layer gate reuses the existing `charter.bundle.CHARTER_YAML` constant (`bundle.py:48`), never a fresh literal (the `src/charter/` layer must not import `specify_cli`). | Draft |
| FR-007 | Retire the legacy catalog-fallback so `resolve_project_governance` stops being a divergent second directive authority. **Fix-locus (unambiguous):** `resolver.py::_resolve_directives_selection` (`:233`, returns `sorted(doctrine_catalog.directives)` at `:258-260`) called by `resolve_project_governance` (`:289`, builds the unfiltered catalog at `:316`, constructs no `PackContext`). Thread `PackContext.from_config(repo_root).activated_directives` down and use it as the fallback source. **All 5 consumers** (`prompt_builder.py:437`, `runtime/doctor.py:133`, `context_json.py:141`, `compact.py:303`, `resolver.py:415`) call `resolve_project_governance` **directly** — they do NOT traverse the activation-aware `DoctrineService` wrapper (`resolver.py:57-139`); adding a `directives` property to that wrapper would leave the RED journey test failing, so the wrapper is explicitly **out of scope** here (the context-bundle path that already returns 5 goes through the wrapper; `resolve_project_governance` is the divergent 29-path). **Preserve `activated_directives`'s three-state** (`pack_context.py:144`): filter to the activated set **only when `activated_directives is not None`**; when `None` (no pack ever applied → unconfigured) keep the existing catalog default — a naive `sorted(activated or frozenset())` would regress a bare project 29→**0**. | Draft |
| FR-008 | Assert `apply --compile` and the upgrade finalize migration produce a **convergent** `charter.yaml` shape (or explicitly document the migration as the upgrade-time equivalent). **Narrowed post-M1:** the activation-key *vocabulary* is already one authority (M1/FR-010's `ACTIVATION_YAML_KEYS`, which the finalize migration already derives from) — so M2 need only assert the **transform shape** (config activation → `charter.yaml` catalog) matches `write_compiled_charter`, not re-unify the vocabulary. | Draft |
| FR-009 | Fold the journey-doc portion of #3107: document the `apply` → `generate` two-step and the empty-charter dispatch behaviour in the charter journey guides. | Draft |
| FR-010 | Make the advertised charter section selectors resolve (**#3095/#3094 + its code-review-checklist twin #2552**): `charter context --include section:terminology-canon` / `section:code-review-checklist` (required by generated `implement`/`review` prompts) resolve to their section — OR the surface stops advertising selectors it cannot resolve. **Engine:** `context_renderers/section_bodies.py::render_critical_section_include` (`:282`; slugifies `ACTION_CRITICAL_SECTIONS` incl. `TERMINOLOGY_CANON="Terminology Canon"` / `CODE_REVIEW_CHECKLIST="Code Review Checklist"`), returning `None` at `:308-311` when the heading is absent → `context.py:354` raises the dead-end. **Resolution (plan-phase decided, research.md Decision 1):** make `render_critical_section_include` return an **honest placeholder** instead of `None` so the selector always resolves *and* `context.py:354` is never reached — keeping `context.py` untouched by this FR (the fix lives entirely in `section_bodies.py`, optionally the `generate.py` companion seed). The dead-end is a **CONTENT** question (a freshly-compiled `charter.md` seed lacks those headings — the repo's own hand-authored `charter.md` masks it as a false-green). Stays on the `charter.md`/section *prose* path (C-003) — does NOT fold that reader into the presence-gate retarget, and does NOT edit `context.py`. | Draft |
| FR-011 | Reconcile the `spec-kitty analyze` command surface (**#3096**): either expose `spec-kitty analyze` as a thin alias to the supported `agent mission record-analysis` flow, or update the `spec-kitty.analyze` skill + command mapping + docs to direct users *exclusively* to the supported command — so the documented surface and the CLI agree (no documented-but-absent command). | Draft |
| FR-012 | Add a **path-filtered CI workflow** scoped to `src/doctrine/**` + `src/charter/**` (**#3102**) that runs the doctrine/charter test surface (DRG freshness/sharding, charter-context resolution, the architectural/adversarial gates) as an isolated, fast signal — so PRs touching that layer get focused feedback and unrelated PRs do not pay/gate on it. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The dispatch-net predicate is single-load on the hot path (folds #3118). | `is_charter_empty` on an unconfigured repo performs at most one `PackContext.from_config` + one `stat`, with **no** `charter_activated_urns` URN load (advisory, load-counting spy). | Draft |
| NFR-002 | Every journey is regression-guarded. | The 8 journeys in `notes/research-synthesis.md` §"Journey acceptance tests" are executable tests (dispatch-net ×3 incl. org-pack safety, context/status bundle-authority ×2 incl. charter.md-deletion, resolver single-authority, truthful output, perf), **plus** three squad-added guards: a **bare-project resolver regression** (no pack applied → `resolve_project_governance().directives` keeps the catalog default, NOT 0 — pins FR-007's three-state, M3), a **FR-006 JSON present-signal test** (`charter context --json` `project_charter.present` keys on `charter.yaml`, survives `charter.md` deletion), and a **`frozenset()` opt-out pin** (explicit zero-profile activation keeps the net disengaged — so a later reader can't "tidy" `is not None` into truthiness). | Draft |
| NFR-003 | No new lint/type regressions. | `ruff` + `mypy` zero new issues on all changed modules. | Draft |
| NFR-004 | Behaviour-change decisions are explicit, not slipped. | The spec/PR record: (a) the deliberate drop of **all** non-routing dimensions from the net predicate — directives/tactics/toolguides/procedures/paradigms/styleguides/**mission-step-contracts**/**glossary-packs** — so a project activating *only* any of these (no bundle, no routable profile/org) now fires the generic-agent net (the #3064 glossary reversal is one case of this broader, benign change); (b) the "empty = bundle absent" definition; (c) the `charter context --json` `project_charter.present` contract flip (FR-006). | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | **Mission 1 (`doctrine-built-in-seam-consolidation`) has LANDED on main** (`873832aa1` seam consolidation + full `packs/built-in` relocation; `873832aa1`'s companion `fd53023b6` = M1/FR-010 "derive activation-key vocabularies from the single authority, restore `activated_glossary_packs`"). This mission is rebased onto that main. M2/FR-007's resolver-fallback-from-activated-set trusts M1's unified activation vocabulary, now present — confirmed live: `PackContext.activated_directives` reads the config-activated set correctly. (Was a pending precondition; now satisfied.) | Active |
| C-002 | **Shared-file coordination (landed):** M1 already repointed the two `resolver.py` operator error strings (`:187`/`:250`) to `packs/built-in/…`. M2 edits the same file for FR-007 (`_resolve_directives_selection`, `:258-260`) — a **distinct** region — and must **not** revert M1's `:187`/`:250` strings. Verify against HEAD before layering the fallback retarget. | Active |
| C-003 | **Keep the presence-gate retarget (FR-005) and the section-selector fix (FR-010) as two distinct changes on two distinct paths.** The `charter.md` prose readers — `context.py:397` (`--include section:<id>`) and the prose body reads (`:333`) — legitimately need `charter.md`; the *presence* gates (FR-005) move to `charter.yaml`, but must **not** be collapsed onto the prose reader (no single shared path constant). FR-010 fixes selector *resolution* on the prose/section path itself — it does not retarget that reader to `charter.yaml`. | Active |
| C-004 | **`apply --compile` is opt-in.** Default `apply` stays a git-agnostic pure additive merge; auto-compiling would change apply's contract (git-worktree requirement, `charter.md` seed, `library/`, gitignore, git-stage, config→pointer migration). | Active |
| C-005 | Out of scope: #3106 (activation-vocab — M1/WP05), #3107's inert CLI-reference parity gate (docs-infra), #2831/#3092/#3045/#2992/#2213 and the other pre-existing/unrelated reds (classify vs merge-base, never green-wash). | Active |

### Key Entities

- **Activation write store** — `config.yaml` `activated_*` (or the pointed-at `charter.yaml` when a `charter:`
  pointer exists); written by `charter pack apply`.
- **Compiled bundle** — `.kittify/charter/charter.yaml` (`governance`/`directives`/`catalog`/`metadata`); the
  authoritative read cache; written by the compile seam.
- **Display companion** — `.kittify/charter/charter.md`; prose only, never a governance authority.
- **Dispatch net** — the generic-agent fallback gated by `is_charter_empty`; must key on routability, not
  config-activation presence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After `charter pack apply` (no compile), an unmatched dispatch **never** returns
  `ROUTER_NO_MATCH` — it falls back to the generic agent 100% of the time (the #3104 fix), while an org-pack
  or agent-profile project is unaffected (no net-fire regression).
- **SC-002**: After `apply` + compile, `charter context`/`charter status` report the pack's governance
  (not "not found"), and continue to work with `charter.md` deleted — proving the authority is `charter.yaml`.
- **SC-003**: `resolve_project_governance` returns the **activated** directive set, never the full built-in
  catalog-fallback (5, not 29, for the minimal pack).
- **SC-004**: `apply` output names the exact next command; `apply --compile` compiles the bundle in one step.
- **SC-005**: The deliberate #3064 glossary-dimension reversal and "empty = bundle absent" are recorded, and
  a test pins the bootstrapped-empty-bundle-keeps-net-OFF behaviour.
- **SC-006**: M2's diff does not touch M1/WP05's vocab surface, does not *collapse* the `charter.md` prose
  readers into the presence gate, and does not green-wash the pre-existing/unrelated reds (C-005).
- **SC-007** (folded): every charter selector the tooling advertises resolves (or is no longer advertised)
  — `section:terminology-canon`/`section:code-review-checklist` no longer dead-end (#3095/#3094 **and its
  code-review-checklist twin #2552**); the documented `spec-kitty analyze` surface and the CLI agree (#3096);
  and a dedicated path-filtered CI workflow runs the doctrine/charter test surface in isolation (#3102).

## Assumptions

- The config→bundle compile already exists (`compile_charter`/`write_compiled_charter`, exposed as
  `charter generate`); M2 wires and retargets, it does not build a compiler.
- `charter.yaml` is the authoritative governance read source and `charter.md` is display-only (corroborated
  in-tree: `freshness/computer.py`, `compact_governance.py`).
- Mission 1 has **landed on main** (`873832aa1` + `fd53023b6`); M2 is rebased onto it, so its unified
  activation vocabulary and built-in seam are present. `PackContext` (the org-pack-safe predicate's inputs)
  was untouched by M1, and the compile seam is unchanged — both confirmed by the revision squad's live
  repro on the post-M1 tree (2026-08-01).
