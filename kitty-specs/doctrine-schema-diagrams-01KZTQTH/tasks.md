# Work Packages: Doctrine Schema Diagrams and PlantUML Rendering (Scope B)

**Mission**: `doctrine-schema-diagrams-01KZTQTH`
**Planning base / merge target**: `feat/doctrine-schema-diagrams-impl`
**Source of truth**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

> Subtask rows below are **reference rows**, not checkboxes. Completion is
> event-sourced — record it with `spec-kitty agent tasks mark-status Txxx --status done`.
> The `[P]` column marks parallel-safety, not status.

## Critical sequencing (from plan IC map + post-plan squad)

- **WP01 is a BLOCKING egress spike.** Runnability of `docker run --network=none` render
  is currently **UNPROVEN**. WP01's green exit-criterion on **both** `ubuntu-latest` and
  `blacksmith-4vcpu-ubuntu-2404` gates every render/diagram WP. Escalate if blacksmith fails.
- **IC-04 (WP08 drift guard) is parallel to the render pipeline** — it parses `@startyaml`
  text + introspects models; it does NOT need the render step. It depends on the diagram
  WPs (WP05–WP07) only because it validates the *real authored* diagrams.
- **IC-03 render-acceptance serializes behind WP01** (the diagram must be provably renderable).
- **Hard single-WP ownership**: `doctrine-kinds.md` (WP05) and `doctrine-relationships.md`
  (WP06) are each owned by exactly one WP — both files are shared surfaces for IC-03 + IC-06.
- **WP09 (IC-05 READMEs) is LAST, decoupled, abandonable** — never on the critical path;
  its links resolve to in-mission targets so link-resolution never reds on an external merge.
- **WP05–WP07 hard-depend on WP01 by design (de-risk gate, not over-serialization)** — the diagram
  *markdown* is render-independent, but gating on the spike avoids wasted authoring if WP01 fails on
  blacksmith fonts/DNS (the whole capability would be abandoned). WP08's guard *engine* can be built
  in parallel; only the guard *run* waits on WP05–WP07.
- **Execution posture (topology = single_branch)** — the flatten routes lifecycle to the primary
  partition, so the whole-file `issue-matrix.json` / `acceptance-matrix.json` are NOT coord-isolated.
  **Integrate lanes serially** (update those matrices one lane at a time); content write-scopes are
  disjoint and `status.events.jsonl` is append-only, so single_branch is safe + lower-overhead as long
  as parallel worktree lanes do not write the matrices concurrently.
- **Spike workflow fate** — `plantuml-egress-spike.yml` (WP01) is kept as a standing runner-capability
  canary after WP03's corpus-isolation test subsumes its behavioral guarantee (a conscious keep, not an
  orphan); revisit at WP03 review whether to retire it.

## Pre-implement gates (do before claiming any WP)

- **DIR-012**: capture/assign a tracking issue to the HiC (this mission edits
  `.github/workflows/docs-*.yml` and pins an external `plantuml.jar`).
- **DIR-013**: pre-declare the baseline-red attribution posture for the `tests/docs/` touch.
- **`/spec-kitty.analyze`** must run (persists `analysis-report.md`) — the implement gate
  refuses (`analysis_report_required`) until it exists.

## Dependency graph

```
WP01 (spike, GATE) ──┬─→ WP02 (render step) ──┐
                     ├─→ WP05 (doctrine-kinds) ─┼─→ WP08 (drift guard)
                     ├─→ WP06 (relationships) ──┼─→ WP03 (security proofs)
                     └─→ WP07 (mission-type) ───┴─→ WP09 (module READMEs, LAST)
WP04 (ADR) ── independent (co-lands, no code dep)
```

- WP01: `[]`
- WP02: `[WP01]`
- WP04: `[]`
- WP05: `[WP01]`
- WP06: `[WP01]`
- WP07: `[WP01]`
- WP03: `[WP02, WP05, WP06, WP07]`
- WP08: `[WP05, WP06, WP07]`
- WP09: `[WP05, WP06, WP07]`

**MVP**: WP01 (proves the capability is even possible). **Critical path**:
WP01 → {WP05|WP06|WP07} → WP08.

## Subtask Index (reference table — `[P]` = parallel-safe, not status)

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Pin `plantuml.jar` (version + sha256); record in `scripts/docs/plantuml_pins.json` | WP01 | |
| T002 | Select + digest-pin a JRE image; document prefetch-before-isolation | WP01 | [P] |
| T003 | `scripts/docs/plantuml_invoke.py` — stdlib-only sha256-verify + `docker --network=none` java wrapper (SANDBOX) | WP01 | |
| T004 | Author a real `@startyaml` spike fixture diagram | WP01 | [P] |
| T005 | `.github/workflows/plantuml-egress-spike.yml` — matrix both runners, render under `--network=none` | WP01 | |
| T006 | Prove green on BOTH runners; capture run URLs; escalate on blacksmith failure | WP01 | |
| T007 | `scripts/docs/plantuml_render.py` — fence recovery, `html.unescape`, assert `language-plantuml`, inject SVG + derived alt/aria | WP02 | |
| T008 | Wire render step into `docs-build-pr.yml` after `glossary_linker`, before redirect-stub/`seo_verify`; drop host `setup-java` | WP02 | |
| T009 | Wire same into `docs-pages.yml` + extend enumerated `paths:` allowlist | WP02 | |
| T010 | Round-trip test (fence→`_site`→recovered→SVG through downstream chain; Mermaid untouched; malformed + sha256-mismatch fail-closed) | WP02 | |
| T011 | Alt-text distinct-caption test (two titled diagrams → distinct alt == caption, not in generic-fallback set) | WP02 | |
| T012 | SANDBOX behavioral negative test (`!includeurl` → local listener sees zero inbound) | WP03 | |
| T013 | No-egress corpus isolation test (render ALL authored `@startyaml` docs under `--network=none`) | WP03 | |
| T014 | URL-grep secondary lint over rendered corpus | WP03 | [P] |
| T015 | Write ADR `…-plantuml-schema-diagram-rendering.md` (cite toolguide; new genre vs C4; carve-out; tradeoff) | WP04 | [P] |
| T016 | Amend `docs/architecture/diagrams/README.md` R-04 (generated docsite-only schema lane) | WP04 | [P] |
| T017 | Author `@startyaml` cross-kind overview diagram (from `list(ArtifactKind)`=12) with derived title/alt | WP05 | |
| T035 | Author `@startyaml` **agent-profile** schema diagram (`AgentProfileSchema` + nested `AgentSpecialization`, alias-normalized) — FR-003 4th artefact | WP05 | |
| T018 | Fill `glossary-pack` kind description | WP05 | [P] |
| T019 | Fill `anti-pattern` kind description (distinct from `styleguides` `AntiPattern`) | WP05 | [P] |
| T020 | Sweep "## The eight doctrine artifact kinds" → 12-member reality; record `template` audit note | WP05 | |
| T021 | Author `@startyaml` DRG diagram bound to `DRGNode`+`DRGEdge`+`NodeKind`+`Relation` | WP06 | |
| T022 | Note the unguarded "15" prose literal (diagram-unguarded) | WP06 | [P] |
| T023 | Author `@startyaml` mission-type/step diagram (`MissionStep`/`MissionStepContract`) | WP07 | |
| T024 | Author `action-index` diagram WITH standalone explanatory prose (C-004) | WP07 | |
| T025 | Confirm `action-index` filed here, not the kinds catalog; note `mission-type` is a mission concept | WP07 | [P] |
| T026 | Author explicit `file:class` binding table (1:N) incl. dispositions for ALL `ArtifactKind` | WP08 | |
| T027 | Guard engine: Pydantic `FieldInfo.alias or name` + nested recursion; dataclass `fields()`; StrEnum `list()`; diagram-side `@startyaml` key parse | WP08 | |
| T028 | Completeness-over-all-`ArtifactKind` test (synthetic member FAILS until dispositioned) | WP08 | |
| T029 | Omit-a-field test (diagram missing a model field FAILS) + `AntiPattern`-vs-`anti_pattern` binding test | WP08 | |
| T030 | Nested depth-2 test (`AgentProfileSchema → AgentSpecialization`) asserts FAIL on nested field add | WP08 | |
| T031 | Inventory `src/doctrine/**` modules; map each → doctrine-kinds entry + schema diagram (+ opportunistic plan) | WP09 | |
| T032 | Extend/create pointer-only `README.md` per module (in-mission fallback links; don't clobber ~17 existing) | WP09 | |
| T033 | README structural lint (length cap / forbid field-table markers) — machine pointer-only | WP09 | |
| T034 | Run lint green; confirm all links resolve in-mission | WP09 | |

---

## WP01 — PlantUML egress-isolation spike (BLOCKING gate)

- **Goal**: Prove the render mechanism actually runs on the CI runners — render a **real**
  `@startyaml` diagram to SVG via a **digest-pinned JRE** container under
  `docker run --network=none`, using a **version+sha256-pinned** `plantuml.jar`, with **no**
  DNS/font-driven failure, on **both** `ubuntu-latest` **and** `blacksmith-4vcpu-ubuntu-2404`.
- **Priority**: P1 — this is the mission's de-risking spike; its green run gates render/diagram WPs.
- **Independent test**: the spike CI job is green on both runner labels; the produced SVG is a
  valid `<svg>` carrying the fixture's title/key tokens with **no** PlantUML error signature (a
  mere non-empty `<svg>` is insufficient — PlantUML renders font/DNS failures as a valid error SVG
  at exit 0); the render runs under `--network=none` (still succeeds with no network).
- **Subtasks**: T001, T002, T003, T004, T005, T006
- **Dependencies**: none. **Prompt**: [tasks/WP01-egress-isolation-spike.md](tasks/WP01-egress-isolation-spike.md)
- **Est. size**: ~320 lines.
- **Escalation**: if blacksmith fails on fonts/DNS, STOP and escalate — the whole capability
  depends on it (fallback options: bundle fonts into the image, or pin an image that ships them).

## WP02 — PlantUML render post-processor + workflow wiring

- **Goal**: Land `scripts/docs/plantuml_render.py` (host-native, **stdlib-only**) that recovers
  ` ```plantuml ` fences from `docs/_site`, renders them via WP01's invoker, and injects SVG +
  derived alt/aria; wire it into **both** docs workflows after `glossary_linker`.
- **Priority**: P1. **Independent test**: round-trip a fenced page → published HTML contains the SVG;
  Mermaid untouched; malformed fence + sha256 mismatch fail-closed; alt-text is distinct/derived.
- **Subtasks**: T007, T008, T009, T010, T011
- **Dependencies**: WP01. **Prompt**: [tasks/WP02-render-postprocessor.md](tasks/WP02-render-postprocessor.md)
- **Est. size**: ~380 lines.

## WP03 — Security proofs: SANDBOX + no-egress corpus isolation

- **Goal**: Prove no doctrine-content egress **behaviorally**: (a) an `!includeurl` diagram under
  SANDBOX leaves a local listener with **zero** inbound; (b) the **full authored corpus** renders
  under `docker run --network=none`. Plus a secondary URL-grep lint.
- **Priority**: P1. **Independent test**: the SANDBOX negative test is RED without SANDBOX and GREEN
  with it; the isolation test renders the real corpus offline.
- **Subtasks**: T012, T013, T014
- **Dependencies**: WP02, WP05, WP06, WP07. **Prompt**: [tasks/WP03-no-egress-proofs.md](tasks/WP03-no-egress-proofs.md)
- **Est. size**: ~300 lines.

## WP04 — ADR + R-04 amendment

- **Goal**: Govern the rendering decision + the schema-diagram genre. New ADR cites the
  `plantuml-diagramming` toolguide, positions schema diagrams as a genre distinct from C4 zoom,
  records the accessibility carve-out, and states the docsite-only tradeoff. Amend R-04.
- **Priority**: P1 (co-lands with the capability). **Independent test**: ADR exists with the
  required citations/carve-out; `diagrams/README.md` R-04 reflects the new lane; terminology guard green.
- **Subtasks**: T015, T016
- **Dependencies**: none. **Prompt**: [tasks/WP04-adr-r04-amendment.md](tasks/WP04-adr-r04-amendment.md)
- **Est. size**: ~230 lines.

## WP05 — `doctrine-kinds.md`: cross-kind overview diagram + fill thin kinds + heading sweep

- **Goal**: Author the `@startyaml` cross-kind overview (from `list(ArtifactKind)`=12) **and the
  agent-profile schema diagram (FR-003 4th artefact, `AgentProfileSchema`+nested `AgentSpecialization`)**,
  fill the genuinely-thin `glossary-pack` + `anti-pattern` kinds, and sweep the stale "eight" heading to
  the 12-member reality. **Sole owner** of `doctrine-kinds.md`.
- **Priority**: P1/P3 (mixed; overview + agent-profile P1, fills P3). **Independent test**: page has the
  overview + agent-profile diagrams; both thin kinds documented; no "eight" heading remains; `template`
  audit note present.
- **Subtasks**: T017, T035, T018, T019, T020
- **Dependencies**: WP01. **Prompt**: [tasks/WP05-doctrine-kinds-overview.md](tasks/WP05-doctrine-kinds-overview.md)
- **Est. size**: ~300 lines.

## WP06 — `doctrine-relationships.md`: DRG diagram + "15" prose note

- **Goal**: Author the `@startyaml` DRG diagram bound to `DRGNode`+`DRGEdge`+`NodeKind`(16)+
  `Relation`(15), members derived by `list(...)`; note the unguarded "15" prose literal. **Sole
  owner** of `doctrine-relationships.md`.
- **Priority**: P1. **Independent test**: page has the DRG diagram; the "15" prose note is present;
  the drift guard (WP08) binds and passes.
- **Subtasks**: T021, T022
- **Dependencies**: WP01. **Prompt**: [tasks/WP06-drg-diagram.md](tasks/WP06-drg-diagram.md)
- **Est. size**: ~230 lines.

## WP07 — `mission-type-resolution.md`: mission-type/step + action-index diagrams w/ prose

- **Goal**: Author the `@startyaml` mission-type/step diagram (`MissionStep`/`MissionStepContract`)
  and the `action-index` diagram **with standalone explanatory prose** (C-004 — not a picture alone);
  confirm `action-index` is filed here, not in the kinds catalog.
- **Priority**: P1. **Independent test**: both diagrams present; action-index has standalone prose;
  action-index absent from kinds catalog.
- **Subtasks**: T023, T024, T025
- **Dependencies**: WP01. **Prompt**: [tasks/WP07-mission-type-diagrams.md](tasks/WP07-mission-type-diagrams.md)
- **Est. size**: ~260 lines.

## WP08 — Drift guard + binding table

- **Goal**: Enforce zero diagram/code drift via an explicit `file:class` binding table (1:N) and a
  guard engine that introspects models (alias-normalized, transitively recursed, StrEnum via `list()`)
  and parses the `@startyaml` field set. Non-fakeable tests: completeness-over-all-kinds,
  omit-a-field, nested depth-2. ATDD red-first.
- **Priority**: P1. **Independent test**: guard passes on the authored corpus; a synthetic new
  `ArtifactKind` FAILS until dispositioned; omitting a diagram field FAILS; a nested-model field add FAILS.
- **Subtasks**: T026, T027, T028, T029, T030
- **Dependencies**: WP05, WP06, WP07. **Prompt**: [tasks/WP08-drift-guard.md](tasks/WP08-drift-guard.md)
- **Est. size**: ~420 lines.

## WP09 — Per-module pointer READMEs + lint (LAST, abandonable)

- **Goal**: Add pointer-only `README.md` to each doctrine source module linking the doctrine-kinds
  entry + the schema diagram (in-mission targets that always resolve) + opportunistically the owning
  plan; a structural lint enforces pointer-only. **Extend** ~17 existing READMEs, don't clobber.
- **Priority**: P2. **Independent test**: each covered module has a pointer-only README whose links
  resolve in-mission; the lint rejects duplicated schema/field content.
- **Subtasks**: T031, T032, T033, T034
- **Dependencies**: WP05, WP06, WP07. **Prompt**: [tasks/WP09-module-readmes.md](tasks/WP09-module-readmes.md)
- **Est. size**: ~280 lines.

---

## Coverage map (FR → WP)

| Requirement | WP(s) |
|-------------|-------|
| FR-001 render capability | WP01, WP02 |
| FR-002 ADR + R-04 | WP04 |
| FR-003 schema diagrams (agent-profile=WP05/T035, overview=WP05, DRG=WP06, mission-type=WP07) | WP05, WP06, WP07 |
| FR-004 drift guard | WP08 |
| FR-005 module READMEs | WP09 |
| FR-006 fill thin kinds | WP05 |
| NFR-001 fidelity | WP08 |
| NFR-002 no-egress | WP01, WP03 |
| NFR-003 reproducible build | WP01 |
| NFR-004 non-regression | WP02 |
| NFR-005 accessibility | WP02, WP04 |
| C-001 local rendering | WP01, WP03 |
| C-002 docsite-only | WP02 |
| C-003 introspection not hand-counts | WP06, WP08 |
| C-004 correct filing | WP05, WP07, WP08 |
| C-005 READMEs are pointers | WP09 |
| C-006 governed reconciliation | WP04 |

## Next command

`/spec-kitty.analyze --mission doctrine-schema-diagrams-01KZTQTH` (required implement gate),
then `/spec-kitty.implement` (or the `spec-kitty-implement-review` skill) starting with WP01.
