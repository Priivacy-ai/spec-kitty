# Mission Specification: Doctrine Governance Fidelity

**Mission Branch**: `mission/doctrine-governance-fidelity`
**Created**: 2026-06-27
**Status**: Draft
**Mission ID**: `01KW42KY6AXQ3B6DTCTFT0XMTV`
**Topology**: lanes (no coordination branch)
**Input**: Operator scope — issues #2156, #2166, #2153, #2082 (Charter & Doctrine governance correctness).

## Summary

Three doctrine surfaces compute or read a governance signal but silently fail to
**honour it at the consumer surface** — the defect class is "the data is present,
the consumer doesn't use it." This mission closes all three, each as an
independent lane:

- **Lane A — #2153**: `charter generate` reads the `documentation_policy` interview
  answer but emits a hardcoded directive line instead of interpolating it.
- **Lane B — #2156 + #2166**: `spec-kitty dispatch` (and agent-profile projection)
  never pass `org_dirs` when building the profile repository, so **org / extension
  doctrine-pack agents are invisible** to dispatch routing, to the governance
  context of a `--profile`-hinted org agent, and to the projected `.claude/agents/`
  surface — even when the operator has activated them.
- **Lane C — #2082**: the built-in-override governance predicate
  (`drg/override_policy.py`) has **no runtime consumer** — it is enforced only by an
  architectural test that deployed consumer repos never run — so an unsanctioned
  built-in override surfaces nowhere in a real project.

The lanes are file-disjoint and independently testable (true MVP slices). The
provisional 3-issue scope was found by the pre-planning adversarial squad to be
undersized ~2–3× (#2156 is three legs, not one site; #2082 requires promoting
test-local logic into production before wiring), and #2166 is not separable from
#2156 — it is the projection leg of the same `org_dirs` omission.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Documentation policy survives charter generation (Priority: P2)

An operator runs the comprehensive charter interview and writes a detailed
`documentation_policy` answer. They expect that policy text to appear in the
generated charter alongside the other interview answers (as `risk_boundaries`
already does).

**Why this priority**: P2 correctness/fidelity bug (#2153). Low blast radius
(single site, single sink) but it silently discards operator input — a governance
trust defect. Smallest, lowest-risk slice; lands first.

**Independent Test**: Seed `.kittify/charter/interview/answers.yaml` with a sentinel
`documentation_policy` value, run `spec-kitty charter generate --from-interview`,
and grep the generated `charter.md` Project Directives section for the sentinel.
Red against current code (sentinel absent), green after the fix.

**Acceptance Scenarios**:

1. **Given** an interview answers file whose `documentation_policy` is
   `"SENTINEL_DOCS: adopt Divio structure"`, **When** `charter generate
   --from-interview` runs, **Then** the generated `charter.md` Project Directives
   section contains the substring `SENTINEL_DOCS: adopt Divio structure`.
2. **Given** an interview answers file with **no** `documentation_policy` answer,
   **When** `charter generate --from-interview` runs, **Then** no documentation
   directive line is emitted (the empty-answer branch does not regress).
3. **Given** the same interview, **When** the charter is generated, **Then** the
   `documentation_policy` directive is rendered with the same interpolation shape
   as the adjacent `risk_boundaries` directive (label + verbatim answer).

---

### User Story 2 — Org-pack doctrine agents participate in dispatch end-to-end (Priority: P1)

An operator installs an org / extension doctrine pack that ships agent profiles
and activates one. They expect that profile to be **routable by `spec-kitty
dispatch`**, to carry **its governance context** when invoked via `--profile`, and
to be **projected into the host agent surface** (`.claude/agents/`) — exactly as
built-in profiles are.

**Why this priority**: P1 (#2156 + #2166). Operators who install doctrine
extension packs cannot use their agents in the single public governed dispatch
surface, nor see them in their IDE — a governance-configuration gap that defeats
the purpose of extension packs. Highest user-visible value.

**Activation contract**: An org-pack agent profile is dispatch/projection-visible
when the pack is **declared** in `.kittify/config.yaml` **AND** the profile passes
the three-state charter gate — `activated_agent_profiles` absent (`None` → all
admitted, backward-compat default), or the id is in the explicit list. An explicit
list that omits the id (or an empty set) makes it a structured miss, identically
across `charter context --include`, dispatch routing, governance context, and
projection.

**Independent Test**: In a scratch project, declare a real-format net-new org-pack
profile and measure visibility on the dispatch routing catalog, the `--profile`
governance context, and the projection manifest across both gate regimes (key
absent / explicit list including vs excluding the profile). The positive case is
RED today (dispatch sees N−1); the negative case must stay hidden.

**Acceptance Scenarios**:

1. **Given** an org-pack profile `orgzilla-org-analyst` with `activated_agent_profiles`
   absent (default) **or** an explicit list that includes it, **When**
   `ProfileRegistry(repo_root).list_all()` is read (the dispatch routing catalog),
   **Then** `orgzilla-org-analyst` is present (currently absent).
2. **Given** the same profile, **When** `spec-kitty dispatch "<request>" --profile
   orgzilla-org-analyst` runs, **Then** the invocation resolves the profile **and**
   its governance context is non-empty (not a routed-but-context-empty half-fix).
3. **Given** the same pack (activation-admitted), **When** agent profiles are
   projected, **Then** `orgzilla-org-analyst` is written to the host agent surface
   and recorded in the projection manifest with a non-builtin `source_layer` (#2166).
4. **Given** an explicit `activated_agent_profiles` list that **excludes**
   `orgzilla-org-analyst`, **When** dispatch routing and projection run, **Then**
   the profile is **absent** from both (charter de-activation is honoured — the
   gate is not bypassed by a raw `org_dirs` splice).
5. **Given** a project with **no** org packs declared, **When** dispatch /
   projection run, **Then** behaviour is byte-identical to today (no regression on
   the built-in-only path) and the existing `.kittify/profiles` project layer is
   still honoured unchanged.
6. **Given** a future contributor wires a routing/projection surface, **When** they
   splice raw `org_dirs`/`resolve_org_roots` that bypass the activation filter,
   **Then** an architectural gate fails (the bypass cannot silently recur).
7. **Given** an org pack laid out for runtime resolution (`<pack>/agent_profiles/`),
   **When** `spec-kitty charter activate agent-profile orgzilla-org-analyst` runs,
   **Then** it succeeds (no "Unknown agent-profile ID") — the activation CLI and
   runtime resolve the pack from the same layout (FR-013).

---

### User Story 3 — Unsanctioned built-in overrides surface in a real repo (Priority: P2)

An operator's org pack overrides a built-in DRG node. Whether the repo *sanctions*
that override is governed by `.kittify/doctrine/replaceable-builtins.yaml`. The
operator expects `spec-kitty doctor doctrine` to report an **unsanctioned**
override as a finding — not have the adjudication live only in a test the deployed
repo never runs.

**Why this priority**: P2 tech-debt closure (#2082). Wires a dormant governance
gate to a runtime consumer and retires its dead-symbol allowlist headroom. Depends
on no other lane; sized as its own slice because the adjudication logic must first
be promoted from test code into production.

**Independent Test**: In a scratch repo with an org pack that overrides a built-in
node **without** a sanctioning allowlist entry, run `spec-kitty doctor doctrine
--json` and assert the unsanctioned override appears as a finding and the report is
not `healthy`. With a sanctioning entry present, assert it is **not** flagged.

**Acceptance Scenarios**:

1. **Given** an org pack overriding a built-in DRG node with no allowlist entry,
   **When** `spec-kitty doctor doctrine --json` runs, **Then** the override is
   reported as an unsanctioned finding and `healthy` is false.
2. **Given** the same override **with** a matching `replaceable-builtins.yaml`
   entry, **When** `doctor doctrine` runs, **Then** it is not flagged
   (sanctioned overrides are silent).
3. **Given** a project-tier (not org-tier) override, **When** `doctor doctrine`
   runs, **Then** it is intentionally **not** governed (trusted operator tier) and
   the scope boundary is documented.
4. **Given** the override-policy symbols now have a runtime consumer, **When** the
   dead-symbol / dead-module gates run, **Then** the four `override_policy` symbols
   and the module are **removed** from their allowlists and the
   `category_7_grandfathered_orphans` baseline is lowered 7 → 6.

### Edge Cases

- **Two distinct project profile layers.** `.kittify/profiles` (legacy invocation
  layer, read by `ProfileRegistry`) and `.kittify/doctrine/agent_profiles`
  (doctrine layer, read by `DoctrineService`) are **different bounded contexts**.
  Lane B must **add** `org_dirs` while preserving each site's existing project
  layer — it must NOT blind-swap `ProfileRegistry` onto `DoctrineService`, which
  would change which project profiles dispatch sees.
- **Built-in-only sites are intentional.** Some `AgentProfileRepository`
  construction sites (e.g. `agent/tasks.py` language resolution, `charter/context`
  module cache) may be deliberately built-in-only. Lane B's consolidation +
  ratchet is scoped to the **org-pack-honouring** surfaces (dispatch routing,
  governance context, projection); built-in-only sites are confirmed-then-excluded,
  not swept.
- **Charter is the org-resolution gate (not a test-reliability footnote).** The
  activation gate lives in `charter/resolver.py` (`DoctrineService.agent_profiles`
  filters by `PackContext.activated_agent_profiles`), two layers above
  `resolve_org_roots`. Wiring **raw** `org_dirs` into the routing/projection
  repositories would surface declared-but-de-activated org profiles whenever a
  project maintains an explicit activation list — bypassing the charter as the
  entry point and creating a NEW split-brain opposite to the one this mission
  closes (gated `charter context --include` hides what ungated dispatch routes to).
  The org overlay MUST be the activation-filtered subset (C-008).
- **Gate is opt-in / off-by-default.** `activated_agent_profiles` absent → `None`
  → all org profiles admitted (so #2156 "install → visible" holds for the common
  case with no activation needed). The first `charter activate` materialises an
  explicit list (~16-entry default pack + target), turning the gate on project-wide
  thereafter — from then on, de-activated profiles must be hidden everywhere.
- **Activation-CLI vs runtime layout split-brain (FR-013).** Runtime resolves
  `<pack>/agent_profiles/`; the activation CLI (`charter/_layer_roots.py`) only
  registers an org root when `<pack>/doctrine/` exists, so `charter activate
  agent-profile <id>` fails "Unknown agent-profile ID" against a runtime-flat pack.
  Both resolvers must agree on pack layout.
- **Override shadow at the routing surface (noted, partial).** An org profile
  reusing a built-in id shadows it at merge time. Routing through the activation
  filter closes the activation half; override-**sanction** (`replaceable-builtins`)
  stays a `doctor doctrine` diagnostic (Lane C) and is intentionally NOT enforced
  at the dispatch surface in this mission — recorded so a later mission can close it.
- **Empty `documentation_policy`.** The fix must not emit a stray directive line
  when the answer is absent.
- **No org packs declared.** All Lane B/C surfaces must short-circuit to today's
  built-in-only behaviour with zero new output.
- **Gate-unmask cannot self-validate.** Lowering the `category_7` baseline only
  takes effect post-merge; Lane C must pair the unmask with a full `tests/
  architectural/` dry-run before the PR (it cannot catch offenders within its own
  merge).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Interpolate `documentation_policy` into the charter directive | As an operator, I want my documentation-policy answer rendered in the generated charter so that my governance intent is not silently dropped. | High | Open |
| FR-002 | Preserve the empty-answer branch | As an operator who omits a documentation policy, I want no spurious directive line emitted so that the charter stays clean. | Medium | Open |
| FR-003 | Charter-activation-aware org-profile resolver | As a maintainer, I want one helper that returns the **charter-activated** org-pack profiles (composing `resolve_org_roots` + `PackContext.activated_agent_profiles` via `build_activation_aware_doctrine_service`), provenance-tagged, so that every org-honouring consumer resolves org profiles through the charter gate identically. | High | Open |
| FR-004 | Dispatch routing sees charter-activated org profiles | As an operator, I want `ProfileRegistry`/router to include org-pack profiles **admitted by the charter activation gate** so that `dispatch` routes to activated org agents and never to de-activated ones. | High | Open |
| FR-005 | `--profile`-hinted org agent carries governance context | As an operator, I want a dispatched (activated) org profile to load its governance context so that the invocation is governed, not empty. | High | Open |
| FR-006 | Projection includes charter-activated org profiles (#2166) | As an operator, I want **charter-activated** org-pack agents projected to `.claude/agents/` and the projection manifest so that my host IDE sees exactly the activated set. | High | Open |
| FR-007 | Preserve existing project profile layers | As an operator, I want the `.kittify/profiles` and `.kittify/doctrine/agent_profiles` project layers unchanged so that the fix adds the org overlay without moving existing profiles. | High | Open |
| FR-008 | Anti-regression gate for activation-bypassing construction | As a maintainer, I want an architectural gate forbidding a routing/projection surface from splicing **raw** `org_dirs`/`resolve_org_roots` that bypass the activation filter, so that the charter gate cannot silently be bypassed and must be the entry point. | Medium | Open |
| FR-013 | Unify activation-CLI pack layout with runtime resolution | As an operator, I want `charter activate agent-profile <id>` to resolve org packs from the **same** layout runtime resolution uses, so that activating a runtime-resolvable org profile does not fail with "Unknown agent-profile ID". | High | Open |
| FR-009 | Promote override-adjudication into production | As a maintainer, I want `find_overridden_builtin_urns` / `find_unsanctioned_overrides` / `UnsanctionedOverride` moved from the test into `drg/override_policy.py` so that a runtime consumer can call them. | High | Open |
| FR-010 | `doctor doctrine` reports unsanctioned built-in overrides | As an operator, I want `doctor doctrine` to flag unsanctioned built-in overrides in a deployed repo so that governance is enforced at runtime, not only in CI tests. | High | Open |
| FR-011 | Retire override-policy dead-symbol allowlists + lower baseline | As a maintainer, I want the four override-policy symbols + module removed from the dead-symbol/-module allowlists and `category_7` baseline lowered 7 → 6 so that the ratchet is not gamed. | Medium | Open |
| FR-012 | Document the project-tier ungoverned boundary | As an operator, I want it documented that project-tier overrides remain intentionally ungoverned so that the trust model is explicit. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No built-in-only regression | A project with no org packs and no `documentation_policy` produces byte-identical output to pre-mission on all three surfaces (charter, dispatch/projection, doctor). | Reliability | High | Open |
| NFR-002 | Two-regime live-evidence proof for Lane B | The fix is proven by a live run on BOTH regimes: (positive) a charter-activated org profile IS visible through dispatch + projection, AND (negative) a declared-but-**de-activated** org profile (explicit `activated_agent_profiles` excluding it) is ABSENT from dispatch + projection. A single activated-only assertion is insufficient (it cannot witness a gate bypass). | Reliability | High | Open |
| NFR-003 | New-code quality gates | All new/boy-scout-touched code passes ruff + mypy with zero issues and complexity ≤ 15; every new branch/helper has a focused test in the same lane (Sonar new-code coverage). | Maintainability | High | Open |
| NFR-004 | Fail-closed governance reads | Promoted override-policy predicates remain pure and fail-closed (a malformed allowlist or DRG does not flip an unsanctioned override to "sanctioned"). | Security | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Lanes topology, no coord | Mission runs as `topology: lanes` with no coordination branch; lanes are file-disjoint and independently mergeable. | Technical | High | Open |
| C-002 | Distinct project layers preserved | C-002 governs the **project** overlay only: Lane B must NOT collapse `.kittify/profiles` and `.kittify/doctrine/agent_profiles` into one layer or reroute `ProfileRegistry`'s project layer through `DoctrineService`. The **org** overlay is composed separately (C-008). | Technical | High | Open |
| C-003 | Ratchet scoped to org-honouring surfaces | FR-008's gate covers dispatch/context/projection only; confirmed built-in-only sites are excluded with recorded rationale, not swept. | Technical | Medium | Open |
| C-008 | Charter is the org-resolution entry point | Org-pack agent profiles reach dispatch routing, governance context, and projection **only** through the charter activation filter (`PackContext.activated_agent_profiles`, three-state). No invocation/projection-layer consumer may splice raw `org_dirs`/`resolve_org_roots` that bypass the filter. Reuse `build_activation_aware_doctrine_service`; never re-implement the gate. | Technical | High | Open |
| C-004 | Gate-unmask paired with full-gate dry-run | FR-011's baseline lower is validated by a full `tests/architectural/` (incl. CI-only shards) dry-run before the PR. | Technical | High | Open |
| C-005 | Red-first through pre-existing entry points | Each lane's failing test drives the pre-existing public surface (`charter generate`, `ProfileRegistry`/`dispatch`, `doctor doctrine`), not the fix's new internal API. | Process | High | Open |
| C-006 | Canonical sources only | Use `resolve_org_roots` and the existing `_doctrine_collect`/doctor DRG load; do not hand-roll org-root resolution or new DRG plumbing. | Technical | High | Open |
| C-007 | Realistic test data | Org-pack fixtures use real-format pack ids, profile ids, and `.agent.yaml` shape; sentinel values are realistic policy prose, not `foo`/`bar`. | Process | Medium | Open |

### Key Entities

- **Org doctrine pack**: declared in `.kittify/config.yaml` (`doctrine.org.packs[].local_path`),
  resolved to roots by `resolve_org_roots`; agent profiles live under
  `<pack>/agent_profiles/*.agent.yaml`.
- **AgentProfileRepository layers**: `built_in` / `org_dirs` / `project_dir` — the
  org layer is the one omitted at the dispatch/projection construction sites.
- **ReplaceableBuiltinsPolicy**: the `.kittify/doctrine/replaceable-builtins.yaml`
  allowlist governing which built-in DRG nodes an org pack may override.

## Issue Matrix

| Issue | Title | Priority | Parent epic | Lane | Disposition |
|-------|-------|----------|-------------|------|-------------|
| #2156 | Enable non built-in Doctrine agents in dispatch mode | P1 | #1799 | B | in-mission |
| #2166 | Agent-profile projection ignores the org-pack layer | P1 | #1868 | B | in-mission (folded — projection leg of #2156) |
| #2153 | charter generate discards `documentation_policy` answer | P2 | #1799 | A | in-mission |
| #2082 | Wire built-in-override governance into doctor doctrine | P2 | #2080 | C | in-mission |
| #2049 | Shrink ratchet allowlists | P3 | — | C | reference-by-checklist (FR-011 delivers one burn-down item; no sweep) |
| #2059 | Decompose `doctor.py` god-module | P3 | — | C | reference-by-checklist (land override code by extraction; no full de-godding) |
| #1416 | Charter synthesis drops interview answers (key drift) | — | — | A | prior-art cross-link (CLOSED via PR #1419; touched only `synthesizer/`, never `compiler.py` — #2153 is distinct) |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A seeded `documentation_policy` sentinel appears verbatim in the
  generated `charter.md` Project Directives; the empty-answer case emits no line.
- **SC-002**: With an org-pack profile **admitted** by the charter gate (default
  or explicitly activated), the dispatch routing catalog, the `--profile`
  governance context, and the projection manifest all include it (specify-vs-dispatch
  divergence eliminated); with the profile explicitly **de-activated**, all three
  exclude it (the gate is honoured, not bypassed).
- **SC-007**: `spec-kitty charter activate agent-profile <id>` succeeds against an
  org pack laid out for runtime resolution (no "Unknown agent-profile ID") — the
  activation CLI and runtime resolver agree on pack layout.
- **SC-003**: A project with no org packs and no documentation policy produces
  identical output on all three surfaces vs pre-mission (no regression).
- **SC-004**: `spec-kitty doctor doctrine` flags an unsanctioned built-in override
  in a deployed repo and stays silent for a sanctioned one.
- **SC-005**: The four `override_policy` symbols + module are removed from the
  dead-symbol/-module allowlists, `category_7_grandfathered_orphans` baseline is
  6, and the full `tests/architectural/` suite (incl. CI-only shards) passes.
- **SC-006**: An architectural gate fails if a new org-honouring profile-repo
  construction site omits org awareness.
