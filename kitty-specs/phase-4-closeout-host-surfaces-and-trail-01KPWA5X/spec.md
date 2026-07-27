# Phase 4 Closeout: Host-Surface Breadth and Trail Follow-On

**Mission ID**: `01KPWA5X6617T5TVX4C7S6TMYB`
**Mission slug**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Mission type**: `software-dev`
**Target branch**: `main`
**Baseline commit**: `eb32cf0a8118856de9a59eec2635ddda0b956edf` on `origin/main` (2026-04-23)
**Latest release line in CHANGELOG**: `3.2.0a5` (2026-04-22); `main` has advanced beyond that release cut
**Umbrella roadmap epic**: #461
**Phase 4 tracker**: #466
**Direct parent issues**: #496 (host-surface breadth follow-on), #701 (trail follow-on)
**Explicitly deferred**: #534 (`spec-kitty explain`)

---

## Summary

Phase 4 core runtime is already landed on `main`: `ProfileInvocationExecutor`, `spec-kitty advise | ask | do`, `profile-invocation complete`, `profiles list --json`, `invocations list --json`, the deterministic ADR-3 router, the local-first JSONL invocation trail, and additive started/completed SaaS propagation. The Phase 4 closeout slice landed in `3.2.0a5`: `docs/trail-model.md` (the operator trail contract), sync-boundary suppression in `src/specify_cli/invocation/propagator.py::_propagate_one`, Tier 2 evidence promotion in `ProfileInvocationExecutor.complete_invocation`, Codex and gstack host guidance, and invocation e2e coverage. Phase 5 glossary foundation landed via #759 and is explicitly out of scope here.

This mission executes the remaining Phase 4 follow-on as **one combined closeout mission with two ordered tranches**:

- **Tranche A — #496 host-surface breadth tail.** Propagate the advise/ask/do governance-injection contract to the remaining host surfaces on top of the landed priority slice (Claude Code via `spec-kitty-runtime-next`, Codex CLI via `spec-kitty.advise` `SKILL.md`). Fix shipped host/operator misalignments tied to the Phase 4 runtime model — most visibly the local dashboard that still labels the mission selector and current-mission surface as `Feature` instead of `Mission Run` / mission terminology. Stays focused on real host/operator surfaces, wording, and rendering-contract consistency; does not redesign the invocation model.
- **Tranche B — #701 trail follow-on.** Strengthen four narrow gaps that the shipped `docs/trail-model.md` does not fully solve: (1) stronger request → invocation → artifact/diff correlation, (2) runtime-level mode-of-work detection/enforcement beyond the docs-level taxonomy, (3) an explicit SaaS read-model policy for small/advisory actions, (4) a clear near-term Tier 2 evidence SaaS projection policy (keep local-only vs. define a bounded projection). Does not re-specify the started/completed baseline, Tier 1/2/3 taxonomy, sync-aware suppression, or the intake/explain positions already documented.

**Execution order is A → B**, because Tranche A is mostly mechanical alignment on an already-shipped contract and unblocks clean host-side reads that make Tranche B's correlation work observable. The smallest next implementation chunk to build first is the Tranche A host-surface inventory plus the dashboard `Feature` → `Mission Run` wording fix (see Recommended Execution Order).

---

## User Scenarios & Testing

Spec Kitty's users for this mission are **host LLMs / harnesses** (e.g., Claude Code, Codex CLI, gstack, Vibe, other supported agents) and **human operators** running the Spec Kitty CLI and the local dashboard. There is no human-only end-user UX flow in this mission.

### Primary scenarios

1. **Host LLM on any supported surface invokes the governance layer correctly.**
   - A host that has never used Spec Kitty reads its agent skill pack, discovers the advise/ask/do command family, calls the right command for a given situation (pure routing advisory, profile-known task, profile-unknown task), injects `governance_context_text` as binding context, executes the work, and closes the record with `spec-kitty profile-invocation complete`.
   - The host behaves identically in wording and call shape across every supported host surface — no host-specific drift in "what to call" or "when".

2. **Operator browses the local dashboard after Phase 4 runtime work.**
   - The operator opens the dashboard, sees the current mission labelled as a **Mission Run** (not `Feature`), sees artifacts grouped under mission terminology, and can switch between missions without encountering the legacy `Feature` wording on the selector, breadcrumbs, or mission header.
   - Wording and rendering stay consistent with `docs/trail-model.md`, the invocation trail, and the advise/ask/do surface.

3. **Operator or reviewer reconstructs a request end-to-end.**
   - Starting from a `spec-kitty invocations list` entry, the operator can trace request → invocation → any Tier 2 evidence artifact and (where relevant) any diff/commit produced by the invocation, with a single deterministic correlation chain documented and enforced.

4. **Runtime recognises the mode of work and refuses inappropriate trail tiers.**
   - When a caller attempts a Tier 2 promotion on a pure-advisory invocation (`mode=advisory`), the runtime rejects the promotion with a clear error rather than silently accepting it. Mode detection is no longer documentation-only.

5. **SaaS projection of small/advisory actions is explicit and predictable.**
   - An operator with SaaS sync enabled sees advisory-only invocations as minimal timeline entries (no body upload) per an explicit policy, and can predict from the policy alone — without reading code — whether a given action will project a body, evidence, or nothing.

6. **Tier 2 evidence SaaS projection policy is decisive.**
   - Either Tier 2 evidence stays local-only in 3.2.x (status quo, documented explicitly) or projects to SaaS under a bounded, named projection profile; the policy does not remain ambiguous.

### Edge cases

- A host invokes Spec Kitty on a surface whose skill pack has **not** yet been updated: Spec Kitty still records the Tier 1 trail correctly; the failure mode is only that the host does not know to call advise/ask/do, not that Spec Kitty misbehaves.
- The dashboard is opened against a checkout where `kitty-specs/` contains missions created before this mission lands: mission terminology renders consistently regardless of which mission-slug or `mission_number` shape a given mission uses.
- A caller supplies `--evidence` on an invocation whose resolved `mode` is `advisory` or `query`: Tranche B rejects the promotion with a typed error; no evidence artifact is created and the invocation trail is otherwise unaffected (Tier 1 unconditional).
- Sync is disabled for a checkout (already covered by landed `_propagate_one` gate): SaaS projection policy for small actions remains a no-op; nothing in this mission re-enables it behind the operator's back.
- Correlation metadata is unavailable for a historical invocation (pre-this-mission records): read paths degrade gracefully — correlation fields read as `null`, no retroactive rewrite of existing JSONL lines.

---

## Functional Requirements

### Tranche A — #496 host-surface breadth tail

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Maintain an authoritative inventory of supported host surfaces that must teach the advise/ask/do governance-injection contract. The inventory must cover both the 13 slash-command host surfaces (`.claude/`, `.github/`, `.gemini/`, `.cursor/`, `.qwen/`, `.opencode/`, `.windsurf/`, `.kilocode/`, `.augment/`, `.roo/`, `.amazonq/`, `.kiro/`, `.agent/`) and the 2 Agent Skills host surfaces (Codex CLI, Vibe via `.agents/skills/`). The inventory must record, per surface, whether advise/ask/do guidance is present, whether governance-injection instructions are present, and whether the `profile-invocation complete` close-out step is present. | Draft |
| FR-002 | Bring every surface in the inventory to parity with the landed priority-slice guidance. Parity is defined by the content shape shipped in `.agents/skills/spec-kitty.advise/SKILL.md` ("Governance context injection" section) and `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` ("Standalone Invocations (Outside Missions)" section): when to use each of advise/ask/do, how to read and inject `governance_context_text`, how to handle `governance_context_available=false`, and how to close the record. | Draft |
| FR-003 | Replace legacy `Feature` wording on the local dashboard's mission selector, current-mission surface, mission header, and breadcrumbs with `Mission Run` / mission terminology, matching the Phase 4 runtime model. The wording change must cover `src/specify_cli/dashboard/static/dashboard/dashboard.js` and any HTML template / CSS class / CLI echo path that the dashboard renders into a user-visible label for the selected mission. The functional requirement is that no user-visible dashboard string in the mission-selection and current-mission surfaces reads `Feature` where the Phase 4 runtime model calls that concept a Mission Run. | Draft |
| FR-004 | Preserve dashboard backend compatibility. Where filesystem paths, cookie names, HTTP route segments, JSON field names, or persisted state keys contain the token `feature` (for example `kanban/<feature>`, `lastFeature` cookie, `artifacts/<feature_slug>`), those identifiers remain stable in this mission. Only user-visible strings and operator-facing help text change. | Draft |
| FR-005 | Rendering-contract consistency: audit the remaining host/operator surfaces tied to the Phase 4 runtime model (CLI help text for `advise`, `ask`, `do`, `profile-invocation complete`, `profiles list`, `invocations list`; README governance-layer section; `docs/trail-model.md` link targets; any surface that quotes the trail contract) for wording that contradicts the landed trail model or the mission-run / invocation vocabulary, and bring them into alignment. | Draft |
| FR-006 | Guidance-gap coverage: for every real host/operator surface identified in FR-001's inventory that lacks advise/ask/do guidance, ship either (a) the aligned guidance in-surface or (b) an explicit in-surface pointer to the canonical skill pack, with a rationale recorded alongside the inventory for why the surface points out vs. hosts the guidance inline. | Draft |

### Tranche B — #701 trail follow-on

| ID | Requirement | Status |
|----|-------------|--------|
| FR-007 | Define and implement a single deterministic **correlation contract** that binds `request → invocation_id → artifact/diff` for any invocation that produces a checkable output. The contract must make it possible, starting from one `invocation_id`, to read a stable reference to every Tier 2 evidence artifact and every associated diff/commit (e.g., via commit-trailer, artifact-manifest link, or equivalent stable reference) without scanning the whole repo. The chosen mechanism must be additive to existing append-only JSONL records — no mutation of existing lines. | Draft |
| FR-008 | Derive the **mode of work** (`advisory`, `task_execution`, `mission_step`, `query`) for every invocation at runtime rather than as documentation only. Mode is derived deterministically from the routed action and the caller's entry command (`advise`, `ask`, `do`, `profile-invocation complete`, mission-step drivers). The derived mode is recorded in the started event for the invocation. | Draft |
| FR-009 | Enforce mode-of-work constraints at the tier-promotion boundary. `profile-invocation complete --evidence <path>` must reject promotion when the invocation's mode is `advisory` or `query`, returning a typed, operator-readable error without creating the evidence artifact and without mutating existing trail lines. `task_execution` and `mission_step` continue to allow Tier 2 promotion as today. | Draft |
| FR-010 | Define and implement an explicit **SaaS read-model policy for small/advisory actions**. The policy must answer, per (mode, event) pair, whether the event projects to the SaaS timeline, whether `request_text` body is included, and whether `evidence_ref` is included. Policy must be resolvable from the code/config alone without reading a specific event's body, and must be documented where operators look (`docs/trail-model.md` or a sibling operator doc). | Draft |
| FR-011 | Resolve the **Tier 2 evidence SaaS projection policy** decisively. Either (a) keep Tier 2 evidence local-only in 3.2.x and document the reasoning explicitly in `docs/trail-model.md`, or (b) define a bounded projection profile (size limit, redaction rule, timing) and implement it. Ambiguity must not remain in the shipped docs or in the propagator behaviour. | Draft |
| FR-012 | Preserve the local-first invocation trail invariant. Every requirement in Tranche B must keep the Tier 1 JSONL write path unconditional: it writes correctly whether SaaS is reachable, sync is disabled, the user is authenticated, or any new correlation/policy surface has failed. No Tranche B change may cause a clean invocation to fail locally because a SaaS policy evaluation or correlation write errored. | Draft |

### Cross-cutting

| ID | Requirement | Status |
|----|-------------|--------|
| FR-013 | Operator migration guidance. Ship a short migration note in `CHANGELOG.md` and in `docs/trail-model.md` explaining what operators need to know about the new correlation contract, the runtime mode enforcement, and the resolved Tier 2 SaaS policy. The note must answer: what existed before, what changed, what operators must do (if anything), and what remains explicitly deferred (notably `#534` / `spec-kitty explain`). | Draft |
| FR-014 | Tracker hygiene. When this mission merges, close or retitle the child issues appropriately: #496 closed on delivery of Tranche A; #701 closed on delivery of Tranche B; #466 (Phase 4 tracker) updated to reflect that Phase 4 follow-on has shipped; #534 updated to reference Phase 5 glossary foundation as its unblocker. Tracker hygiene is part of the mission's Definition of Done, not a post-merge afterthought. | Draft |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Tier 1 write latency must not regress. The runtime must continue to write the `started` JSONL line before the executor returns, within the existing ~5 ms local write budget. | P95 `started`-event write ≤ 5 ms on a local filesystem; no new blocking I/O before `started` write. | Draft |
| NFR-002 | `spec-kitty invocations list --json` must remain O(limit) via the invocation index and meet the existing performance budget after correlation fields are added. | P95 ≤ 200 ms at 10,000 JSONL files, unchanged from the current budget. | Draft |
| NFR-003 | Host-surface guidance parity coverage. | 100 % of the 15 supported host surfaces (13 slash-command + 2 Agent Skills) must be represented in the FR-001 inventory and either updated to parity or explicitly documented as deferred with rationale before Tranche A merges. | Draft |
| NFR-004 | Test coverage for new code paths. | ≥ 90 % line coverage on new modules / new functions introduced by Tranche B (correlation writer, mode-derivation function, mode-guard at promotion, SaaS policy resolver). | Draft |
| NFR-005 | Type-check cleanliness. | `mypy --strict` passes on every new or modified module with no suppression comments added to previously-clean modules. | Draft |
| NFR-006 | Documentation freshness. | Every operator-facing doc that quotes the trail contract, mode taxonomy, or advise/ask/do surface (`docs/trail-model.md`, any skill pack README, `CHANGELOG.md`) is updated in the same mission as the code change that affects it — no doc lag at merge time. | Draft |
| NFR-007 | Propagation-error quiet invariant. | The SaaS propagation error log `.kittify/events/propagation-errors.jsonl` must not grow during clean invocations with sync disabled or the user unauthenticated, for any new event surface introduced by Tranche B. | Draft |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | **Architecture — host LLM ownership is immutable.** The host LLM / harness owns all reading and generation. Spec Kitty owns routing, governance context assembly, validation, trail writing, provenance, staging/promotion, and additive propagation. No code in this mission may introduce a second executor model, hidden LLM calls, or an LLM invocation inside the Spec Kitty process. | Locked |
| C-002 | **Local-first trail invariant.** The trail must remain local-first. No Tranche B change may introduce a SaaS dependency for the Tier 1 started/completed write path, for correlation writes, or for mode derivation. Sync-boundary suppression in `_propagate_one` must remain intact. | Locked |
| C-003 | **Additive propagation only.** All new SaaS events, fields, and policy surfaces must be additive. No deletion, replay-based overwrite, or idempotency-key gating is introduced; existing events and fields keep their shape. | Locked |
| C-004 | **Append-only invocation records.** No existing JSONL line is ever mutated. Any correlation metadata added after the fact is appended as a new event on the same invocation file or referenced out-of-band; `write_started` keeps its exclusive-create semantics and `write_completed` keeps its append semantics. | Locked |
| C-005 | **`#534` / `spec-kitty explain` remains deferred.** No requirement, acceptance criterion, or code path in this mission may implement or partially implement `spec-kitty explain`. The command stays Phase 5 work and continues to require DRG glossary addressability per #499. | Locked |
| C-006 | **No Phase 5 glossary foundation rework.** Mission 094 / #759 glossary foundation already shipped on `main`. This mission must not re-open glossary chokepoint behaviour, glossary schemas, or DRG residence. Glossary-related code changes are limited to any wording fixes required by FR-005 that happen to reference glossary terms. | Locked |
| C-007 | **No broad `Feature` rename.** A codebase-wide rename from `Feature` to `Mission Run` is explicitly out of scope. The wording change is scoped to the real host/operator surfaces tied to the Phase 4 runtime model — most centrally the local dashboard selector/current-mission surface. Filesystem paths, JSON field names, cookie keys, HTTP route segments, and internal variable names keep their current shape (see FR-004). | Locked |
| C-008 | **No new top-level CLI commands.** Tranche B extends the existing advise/ask/do/complete surface and the existing trail contract; it may add flags, fields, and config keys but must not introduce a new top-level `spec-kitty <verb>` command in this mission. | Locked |
| C-009 | **Tooling conformance.** Code changes use the project's existing toolchain: `typer` (CLI), `rich` (console output), `ruamel.yaml` (YAML), `pytest` (tests), `mypy --strict` (types). No new top-level dependencies are introduced for this mission. | Locked |
| C-010 | **Charter governance.** Work in this mission is subject to DIRECTIVE_003 (decision documentation) and DIRECTIVE_010 (specification fidelity). Material design decisions in Tranche B (correlation mechanism, mode-derivation source of truth, SaaS read-model policy shape, Tier 2 projection resolution) must each be captured in a short decision record co-located with the mission. | Locked |

---

## Success Criteria

Success is measured at the end of Tranche B and is technology-agnostic.

- **SC-001**: A fresh operator on any of the 15 supported host surfaces can, by reading only that surface's in-repo skill pack, correctly call advise/ask/do, inject governance context, and close the record within 5 minutes of first contact. Parity across surfaces is complete.
- **SC-002**: An operator browsing the local dashboard never sees the word `Feature` on the mission selector, current-mission header, or breadcrumbs; all references to the active mission use mission / Mission Run vocabulary consistent with the Phase 4 runtime model.
- **SC-003**: Starting from any `invocation_id` produced after this mission lands, an operator can enumerate every Tier 2 evidence artifact and every associated diff/commit produced by that invocation in a single deterministic lookup, without scanning `.kittify/events/` or the whole repository.
- **SC-004**: Attempting to promote a pure-advisory or query invocation to Tier 2 evidence is rejected at the promotion boundary with a clear, typed error in 100 % of cases; no advisory/query invocation ever produces a Tier 2 evidence artifact after this mission lands.
- **SC-005**: An operator can read the SaaS read-model policy for small/advisory actions in a single operator doc and predict, without reading code, the exact projection behaviour for each (mode, event) pair.
- **SC-006**: The Tier 2 evidence SaaS projection question has a single documented answer in `docs/trail-model.md` (either "local-only in 3.2.x" with reasoning, or a named projection profile with its bounds). No ambiguity remains in shipped docs.
- **SC-007**: `#496` and `#701` are closed; `#466` is updated to reflect Phase 4 follow-on delivery; `#534` is updated with the Phase 5 glossary-foundation linkage. No Phase 4 follow-on work remains open in the tracker after merge.
- **SC-008**: The local-first invariant holds end-to-end: running this mission's full test suite with SaaS sync disabled and no auth token produces zero entries in `propagation-errors.jsonl` and 100 % green Tier 1 writes.

---

## Key Entities

- **Host surface inventory**: the authoritative matrix of the 15 supported host surfaces × guidance parity dimensions (advise/ask/do presence, governance-injection presence, close-out presence). Source-of-truth lives in a single operator-facing table updated in the same commit as each surface change.
- **Invocation record (existing)**: `.kittify/events/profile-invocations/<invocation_id>.jsonl`; extended by this mission with a derived `mode_of_work` field on the `started` event and with correlation linkage to evidence artifacts and diffs/commits. No existing line is ever mutated.
- **Tier 2 evidence artifact (existing)**: `.kittify/evidence/<invocation_id>/evidence.md` + `record.json`; becomes the target of the new correlation contract and the subject of the resolved SaaS projection policy.
- **Mode of work (existing docs taxonomy, becomes runtime-enforced)**: one of `advisory`, `task_execution`, `mission_step`, `query`; derived deterministically at invocation time and recorded in the started event.
- **SaaS read-model policy (new)**: a single named policy resolvable from code/config that maps `(mode, event) → projection behaviour`; consumed by the propagator and documented in the operator trail doc.
- **Dashboard mission-run surface**: the set of user-visible strings in `src/specify_cli/dashboard/static/dashboard/dashboard.js` and its associated templates/CSS that name the active mission; the target of the FR-003 / FR-004 wording change.

---

## Assumptions

- Supported host surface set is the 13 slash-command agents (`.claude`, `.github`, `.gemini`, `.cursor`, `.qwen`, `.opencode`, `.windsurf`, `.kilocode`, `.augment`, `.roo`, `.amazonq`, `.kiro`, `.agent`) plus the 2 Agent Skills agents (Codex CLI and Vibe via `.agents/skills/`), per the project CLAUDE.md. If the user config on a given project excludes an agent, Tranche A work on that surface is non-destructive (respects `get_agent_dirs_for_project()` semantics).
- The correlation contract can be implemented additively on top of the existing invocation file plus the existing `kitty-specs/` and git-history surfaces; it does not need a new database or a new append-only log alongside JSONL.
- Tier 2 SaaS projection resolution (FR-011) is equally acceptable in either direction (keep local-only OR define a bounded projection). Plan / tasks phase will recommend a direction based on operator value and implementation cost; this spec only requires a decisive, documented answer.
- The existing `_propagate_one` sync-gate and the existing authenticated-client lookup pattern in `propagator.py` are the right attachment points for the new SaaS read-model policy surface; no restructuring of `sync/emitter.py` is required.
- Dashboard wording changes are localised enough to not require a dashboard-wide component refactor. If the plan phase discovers that they are not (for example, if `Feature` is also baked into a shared component used beyond the mission surface), plan will revise scope explicitly rather than broaden FR-003 silently.

---

## Dependencies

- **Upstream (landed, not re-opened)**: `ProfileInvocationExecutor` (`src/specify_cli/invocation/executor.py`), `InvocationWriter` (`src/specify_cli/invocation/writer.py`), `InvocationSaaSPropagator` (`src/specify_cli/invocation/propagator.py`), `ActionRouter`, `docs/trail-model.md`, the glossary foundation from #759.
- **Upstream (host surface references)**: `.agents/skills/spec-kitty.advise/SKILL.md`, `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`, `docs/how-to/setup-codex-spec-kitty-launcher.md` (Codex host guidance), plus the 13 slash-command agent directories as reference copies per CLAUDE.md template-flow rules.
- **Downstream (out of scope here, but this mission's output must not block them)**: Phase 5 glossary addressability work including `#499` and the `spec-kitty explain` unblocking path, Phase 6 mission rewrite / retrospective contract work, Phase 7 versioning/provenance hardening.
- **External**: none. No new third-party dependency is introduced; no SaaS contract change is required (the existing additive event envelope is sufficient; the new read-model policy is a consumer-side concern).

---

## Recommended Execution Order and Smallest Next Chunk

**Execution order (A → B, strict):**

1. **Tranche A — #496 host-surface breadth tail** (smaller, mostly alignment work with high leverage for downstream observability).
   - A.1 Build the FR-001 host-surface inventory matrix; capture which of the 15 surfaces already has parity, which has partial coverage, and which has nothing.
   - A.2 Fix the dashboard `Feature` → `Mission Run` user-visible wording (FR-003 / FR-004). This is the **smallest next implementation chunk** to build first. It is tightly bounded (one JS file plus associated templates/CSS), has no runtime contract risk, no SaaS risk, and produces an immediately visible, reviewable result that anchors the rest of Tranche A's wording work.
   - A.3 Rendering-contract consistency pass across CLI help text, README governance section, and doc cross-links (FR-005).
   - A.4 Fill the guidance gaps identified in A.1 using in-surface text or explicit pointers (FR-002, FR-006).
   - A.5 Close / retitle `#496` on merge.

2. **Tranche B — #701 trail follow-on** (begins only after Tranche A is merged).
   - B.1 Correlation contract — design record + implementation + tests (FR-007).
   - B.2 Runtime mode derivation and recording on the `started` event (FR-008).
   - B.3 Tier-promotion enforcement against derived mode (FR-009).
   - B.4 SaaS read-model policy for small/advisory actions — policy doc + resolver + propagator wiring (FR-010).
   - B.5 Tier 2 SaaS projection policy resolution — decision record + doc update, and (if option B is chosen) projection profile + tests (FR-011).
   - B.6 Cross-cutting: migration guidance (FR-013), tracker hygiene (FR-014), CHANGELOG updates.
   - B.7 Close `#701` on merge; update `#466` closeout state; update `#534` with Phase 5 linkage.

**Rationale for A → B:** Tranche A is mostly mechanical alignment with no new runtime contracts. Landing it first cleans the host surfaces and the dashboard so that Tranche B's correlation work produces observable, unambiguous results rather than landing into an inconsistent wording surface. Tranche B is also where the design decisions (correlation mechanism, mode derivation source of truth, SaaS read-model policy shape, Tier 2 projection direction) live; running it after Tranche A gives reviewers a clean surface to evaluate Tranche B's design records against.

**Why one mission, not two:** Tranches A and B share the same governance model, the same reviewer context, the same test scaffold (`tests/specify_cli/invocation/`), and the same operator-facing doc (`docs/trail-model.md`). Splitting into two sibling missions would introduce coordination cost (mission-level handoff, duplicated branch/worktree lifecycle, separate charter-context loads) without changing what actually ships. A single combined mission with Tranches A and B as ordered work-package groups is the decisive closeout shape.

---

## Tracker Hygiene Recommendations (for the Plan phase)

Plan should carry these through as explicit tracker updates, scheduled to fire at merge time:

- **#496** — Retitle to reflect the delivered scope (for example: "[Phase 4] Host-surface breadth rollout — complete"), close on merge of Tranche A.
- **#701** — Close on merge of Tranche B. Reference the two design records produced for the correlation contract and the SaaS read-model policy.
- **#466** — Update to state that Phase 4 follow-on has shipped in `3.2.x` under this mission; keep open only until #534 / Phase 5 work is formally tracked elsewhere.
- **#534** — Update with an explicit cross-link to the Phase 5 glossary-foundation work (#499 and the shipped mission 094 / #759) as the unblocker; keep deferred.
- **#461** — Leave open as the umbrella roadmap; no retitle needed.

---

## Explicit Non-Goals (this mission)

- Reopening charter synthesis plumbing.
- Reopening Phase 4 core runtime construction (`ProfileInvocationExecutor`, router, `InvocationWriter`, `InvocationSaaSPropagator`).
- Reopening Phase 5 glossary foundation (shipped via #759).
- Pulling in Phase 6 mission rewrite / retrospective contract work.
- Pulling in Phase 7 versioning / provenance hardening.
- Putting `spec-kitty explain` back into the current release gate (`#534` stays deferred).
- Introducing a second executor model, hidden LLM calls in Spec Kitty, or any non-local-first trail dependency.
- Running a broad codebase-wide `Feature` → `Mission Run` rename beyond the real host/operator surfaces tied to the Phase 4 runtime model. Filesystem paths, JSON field names, cookie keys, HTTP route segments, and internal variable names stay as they are (see FR-004 and C-007).
- Introducing a new top-level CLI command surface (see C-008).
- Mutating existing invocation JSONL lines in any way (see C-004).
