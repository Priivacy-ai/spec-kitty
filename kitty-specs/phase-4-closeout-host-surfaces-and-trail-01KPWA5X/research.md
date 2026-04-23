# Research: Phase 4 Closeout — Host-Surface Breadth and Trail Follow-On

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Phase**: 0 (Outline & Research)
**Baseline**: `origin/main` @ `eb32cf0a8118856de9a59eec2635ddda0b956edf` (2026-04-23)

This document records the research conclusions behind the 10 design decisions (D1–D10) the plan phase committed to. Every `[NEEDS CLARIFICATION]` slot that the spec reserved is resolved here. Every resolution is grounded in a read of the live code at `main`, the operator trail contract already shipped in `docs/trail-model.md`, and the behaviour of the advise/ask/do / `profile-invocation complete` surface as of `3.2.0a5`.

## Resolution summary (fast index)

| ID | Decision | Ref |
|----|----------|-----|
| D1 | Correlation contract = append-only JSONL events (`artifact_link`, `commit_link`) on the existing invocation file. `--artifact` repeatable; `--commit` singular. Ref normalises to repo-relative under checkout, absolute fallback otherwise. | §D1 |
| D2 | `mode_of_work` derived from CLI entry command (deterministic), not from routed action. Recorded on the `started` event. Null-tolerant for pre-mission records. | §D2 |
| D3 | Tier 2 promotion is rejected at `complete_invocation` for mode ∈ `{advisory, query}` with typed `InvalidModeForEvidenceError`. Correlation links remain allowed in all modes. | §D3 |
| D4 | SaaS read-model policy = typed Python module `src/specify_cli/invocation/projection_policy.py` (`ModeOfWork`, `EventKind`, `ProjectionRule`, `POLICY_TABLE`, `resolve_projection()`). Not YAML-configurable. | §D4 |
| D5 | Tier 2 evidence SaaS projection stays **local-only in 3.2.x**. Decisively documented in `docs/trail-model.md`. | §D5 |
| D6 | Host-surface inventory lives mission-locally during execution at `artifacts/host-surface-inventory.md`; promoted on mission close to `docs/host-surface-parity.md`. | §D6 |
| D7 | Dashboard wording: `Feature` → `Mission Run` for user-visible strings only, in three files. Backend identifiers preserved per FR-004 / C-007. | §D7 |
| D8 | Four ADRs under `decisions/` — correlation (D1), mode derivation (D2), policy shape (D4), Tier 2 deferral (D5). | §D8 |
| D9 | Testing: per-FR unit + integration. `tests/specify_cli/invocation/test_invocation_e2e.py` extended, not replaced. SaaS-disabled contract test asserts NFR-007 / SC-008. | §D9 |
| D10 | Sequencing A → B strict; 5 Tranche A WPs + 7 Tranche B WPs. Tasks phase finalises. | §D10 |

---

## §D1 — Correlation contract (FR-007)

### Evaluated alternatives

| Option | Storage | Pros | Cons | Rejected? |
|--------|---------|------|------|-----------|
| **(A) Git commit trailer** `Invocation-Id: <ulid>` on every commit produced by an invocation | In `git log` | Tight coupling to git; visible via `git log --grep` | Requires a git hook for enforcement — unreliable across host LLMs and operators; read path scans whole history; cannot represent non-commit artifacts | Rejected |
| **(B) Append correlation events to the existing invocation JSONL** `{event: "artifact_link" \| "commit_link", ...}` | `.kittify/events/profile-invocations/<id>.jsonl` | Single-file read yields all correlations; append-only (C-004 compliant); no hook, no git mutation; handles both commits and artifacts | Requires a new `writer.append_correlation_link()` method and CLI flags on `complete` | **Chosen** |
| **(C) New sibling index file** `.kittify/events/correlation-links.jsonl` | New file | Central index | Second source of truth; reconstructing per-invocation still requires either grep or a load into memory; duplicates `invocation-index.jsonl` pattern | Rejected |
| **(D) Hybrid A + B** | Both | Flexible | Double write, double maintenance; no operator asked for redundant surfaces | Rejected |

### Decision

**Option B.** Append correlation events to the same invocation JSONL. Extend `spec-kitty profile-invocation complete` with:

- `--commit <sha>` — **singular**. Records the commit SHA most directly produced by the invocation. Hosts that produce multiple commits can record the head commit; a subsequent invocation records subsequent commits.
- `--artifact <path>` — **repeatable**. Records any number of artifact refs associated with the invocation (build output, generated doc, updated mission artifact, test report).

Flags are orthogonal to the existing `--evidence <path>` (Tier 2 promotion); they can be combined freely.

### Ref normalisation rule

For `--artifact` paths (and for `--evidence` paths, for consistency with the existing behaviour already in `executor.complete_invocation`):

- Resolve the input path: `resolved = Path(ref).resolve()`.
- If `resolved.is_relative_to(repo_root.resolve())`, persist `str(resolved.relative_to(repo_root))` — the **repo-relative path**.
- Otherwise, persist `str(resolved)` — the **absolute path**, recorded as-resolved so later reads are unambiguous even after the operator's `cwd` changes.

This mirrors the resolution already used in `src/specify_cli/invocation/executor.py:238-245` for evidence promotion, so behaviour is consistent across ref types.

For `--commit`: record the 40-char (or abbreviated, as supplied) SHA verbatim. No normalisation. Do not attempt to verify the SHA exists; the trail is observational, not a validator.

### Event shapes (full definitions in `data-model.md`)

```json
{"event": "artifact_link", "invocation_id": "01H...", "kind": "artifact", "ref": "kitty-specs/042-foo/tasks/WP03.md", "at": "2026-04-23T04:45:00+00:00"}
{"event": "commit_link",   "invocation_id": "01H...", "sha": "a1b2c3d4...", "at": "2026-04-23T04:45:00+00:00"}
```

Readers that encounter unknown event types may safely skip the line — the same invariant already holds for the `glossary_checked` event (see `src/specify_cli/invocation/writer.py:142-168`).

### Acceptance mapping

- SC-003 → single-file read yields all correlations.
- FR-007 → one deterministic chain, additive to JSONL.
- C-004 → append-only preserved.

---

## §D2 — Runtime mode-of-work derivation (FR-008)

### Evaluated alternatives

| Option | Derivation source | Pros | Cons | Rejected? |
|--------|-------------------|------|------|-----------|
| **(A) CLI entry command** — `advise`/`ask`/`do`/mission-step drivers/query commands map to modes | CLI layer | Deterministic; resilient to router changes; operator can predict mode from the command they typed | Requires passing entry-command name into the executor | **Chosen** |
| (B) Routed action (`action` field from router) | Router layer | Co-located with existing routing | Router action taxonomy is finer-grained and will drift; mapping back to modes duplicates CLI-level intent | Rejected |
| (C) Hybrid — entry-command primary, action as secondary signal | Both | Flexible | Two sources of truth → drift risk; no operator benefit | Rejected |

### Decision

**Option A.** Derive `mode_of_work` at the CLI entry layer from the invoked subcommand:

| Entry command | `ModeOfWork` |
|---------------|--------------|
| `spec-kitty advise` | `advisory` |
| `spec-kitty ask <profile>` | `task_execution` |
| `spec-kitty do` | `task_execution` |
| `spec-kitty profile-invocation complete` | `task_execution` (recorded as a tail event; it is not itself an invocation-opener, so no new `started` event carries its mode — but its handler **reads** mode from the `started` line on the target file) |
| mission-step drivers (invocations issued by `spec-kitty next --agent …` for `specify`, `plan`, `tasks`, `merge`, `accept`, `implement`, `review`) | `mission_step` |
| `spec-kitty profiles list` | `query` |
| `spec-kitty invocations list` | `query` |

The CLI entry layer passes the derived `ModeOfWork` into `ProfileInvocationExecutor.invoke()` as a new keyword argument with default `None` (for backwards compatibility with any internal caller that bypasses CLI). The executor records the value on the `started` event as an additive optional field `mode_of_work`.

### Null-tolerance

Pre-mission records have no `mode_of_work` field. Readers treat `mode_of_work=None` as "unknown, pre-enforcement." Enforcement paths (D3) treat `None` as "skip enforcement, allow by default" — we do not retroactively reject existing advisories.

### Acceptance mapping

- FR-008 → runtime-derived, on started event.
- NFR-001 → derivation is a dict lookup; no new I/O before `started` write.
- C-003 → additive optional field.

---

## §D3 — Mode enforcement at Tier 2 promotion (FR-009)

### Decision

Extend `ProfileInvocationExecutor.complete_invocation()` so that **before** it calls `promote_to_evidence()`:

1. Read the `started` event (first line of the invocation JSONL) — already read via `InvocationWriter.write_completed` internally for `profile_id`; extend that read to capture `mode_of_work`.
2. If `evidence_ref is not None` and `mode_of_work in {ModeOfWork.ADVISORY, ModeOfWork.QUERY}`, raise a new typed exception `InvalidModeForEvidenceError(invocation_id, mode)`.
3. If `mode_of_work is None` (pre-mission records), skip enforcement — existing behaviour preserved.
4. Otherwise (mode ∈ `{task_execution, mission_step}` or `None`), proceed to promote as today.

The error is raised **before** `write_completed` writes the `completed` event, so a rejected promotion leaves the invocation **still open** — the operator can retry with corrected flags or close without evidence.

### Alternative considered: reject post-write, clean up

Rejected. Creating a `completed` event and then deleting it would violate C-004 (append-only) and C-003 (additive). Pre-validation keeps both invariants.

### Alternative considered: silent downgrade (record the attempt but do not create evidence)

Rejected. SC-004 requires clear, typed rejection in 100 % of cases. Silent downgrade is a behavioural lie.

### Error shape

```python
class InvalidModeForEvidenceError(InvocationError):
    """--evidence supplied on an invocation whose mode disallows Tier 2 promotion."""
    def __init__(self, invocation_id: str, mode: ModeOfWork) -> None:
        self.invocation_id = invocation_id
        self.mode = mode
        super().__init__(
            f"Cannot promote evidence on invocation {invocation_id}: "
            f"mode is {mode.value}; Tier 2 evidence is only allowed on "
            f"task_execution or mission_step invocations."
        )
```

CLI layer translates to exit code `2` (`InvocationError` exit code) and prints a human-readable message via `rich`.

### Acceptance mapping

- FR-009 → typed rejection at promotion boundary.
- SC-004 → 100 % rejection for mode ∈ `{advisory, query}`.
- C-004 → no line is mutated or deleted.

---

## §D4 — SaaS read-model policy module (FR-010)

### Decision

New module: `src/specify_cli/invocation/projection_policy.py`. Typed, not an untyped dict.

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ModeOfWork(str, Enum):
    ADVISORY = "advisory"
    TASK_EXECUTION = "task_execution"
    MISSION_STEP = "mission_step"
    QUERY = "query"

class EventKind(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ARTIFACT_LINK = "artifact_link"
    COMMIT_LINK = "commit_link"
    # glossary_checked is omitted — it is never projected (see contract doc)

@dataclass(frozen=True)
class ProjectionRule:
    project: bool
    include_request_text: bool
    include_evidence_ref: bool

POLICY_TABLE: dict[tuple[ModeOfWork, EventKind], ProjectionRule] = { ... }

def resolve_projection(mode: ModeOfWork | None, event: EventKind) -> ProjectionRule:
    """Return the projection rule for (mode, event). None mode falls back to TASK_EXECUTION default."""
    ...
```

`ModeOfWork` is defined in a sibling module `src/specify_cli/invocation/modes.py` and re-exported from `projection_policy.py` to keep the policy module self-contained for callers.

### Policy table (initial entries)

| mode | event | project | include_request_text | include_evidence_ref |
|------|-------|---------|----------------------|----------------------|
| advisory | started | true | false | false |
| advisory | completed | true | false | false |
| advisory | artifact_link | false | false | false |
| advisory | commit_link | false | false | false |
| task_execution | started | true | true | false |
| task_execution | completed | true | true | true |
| task_execution | artifact_link | true | false | false |
| task_execution | commit_link | true | false | false |
| mission_step | started | true | true | false |
| mission_step | completed | true | true | true |
| mission_step | artifact_link | true | false | false |
| mission_step | commit_link | true | false | false |
| query | any | false | false | false |

This table is the **single source of truth** for small-action projection. It is consumed by `_propagate_one` *after* the existing `routing.effective_sync_enabled` short-circuit, so sync-disabled checkouts remain silent (C-002).

### Wiring

`_propagate_one(record, repo_root)` changes shape from today's behaviour (which unconditionally builds an envelope for `started`/`completed`):

```python
# existing pre-check (unchanged):
if routing is not None and not routing.effective_sync_enabled:
    return
client = _get_saas_client(repo_root)
if client is None:
    return

# NEW: consult policy
mode = ModeOfWork(record.mode_of_work) if record.mode_of_work else None
event = EventKind(record.event)
rule = resolve_projection(mode, event)
if not rule.project:
    return  # policy says no projection for this (mode, event)
```

For `task_execution` / `mission_step` the table preserves **exactly** today's behaviour. Advisory and query get minimal-timeline or no-projection respectively. Correlation events project for `task_execution` / `mission_step` only. This is the minimum surface that keeps FR-010 honest without changing dashboard timelines for existing missions.

### Why typed module, not YAML

- C-009 disallows new dependencies; no YAML-config surface exists today for runtime invocation behaviour, and introducing one invites operator drift and divergent projection behaviour across checkouts.
- Operator-facing predictability (SC-005) is satisfied by a single table in code + a mirror in `docs/trail-model.md`.
- `mypy --strict` (NFR-005) verifies exhaustive handling at compile time for enums.

### Acceptance mapping

- FR-010 → policy resolvable from code/config alone.
- SC-005 → single doc table predicts projection per (mode, event).
- NFR-005 → typed enums + dataclass pass `mypy --strict`.

---

## §D5 — Tier 2 SaaS projection resolution (FR-011)

### Decision

**Keep Tier 2 evidence local-only in 3.2.x.** Explicitly documented in `docs/trail-model.md` under a new subsection "Tier 2 SaaS Projection — Deferred" with the reasoning and revisit trigger below. No code change to the propagator path for evidence bodies.

### Reasoning

1. **Shipped contract already states this.** `docs/trail-model.md` at baseline says: "Tier 2 evidence artifacts — Local only in 3.2. Not uploaded to SaaS." The decisive close just requires promoting this from a note to a named, rationalised decision.
2. **Bounded projection would require privacy / redaction / size-limit design** that the brief explicitly rejects as out-of-scope for the closeout ("Optimize for decisive closeout stewardship, not another broad rewrite").
3. **Future projection is still possible without contract change.** If Phase 6 or 7 later introduces a bounded projection profile, it can read the existing Tier 2 artifact on disk and project it with its own policy; no invocation-record field needs to be reserved now.
4. **Operator expectations are not violated.** The 3.2.x release line already sets "local-only evidence" as the observed behaviour; confirming it in doctrine does not surprise anyone.

### Revisit trigger

Revisit when at least one of the following is true:
- A named future mission / epic accepts SaaS evidence projection as its scope (likely Phase 6+).
- Operators actively request that evidence artifacts be viewable in the SaaS dossier (no such request observed as of 2026-04-23).
- A regulatory / audit requirement forces centralised evidence retention.

### Acceptance mapping

- FR-011 → decisive, documented answer.
- SC-006 → single answer in shipped docs.
- C-002 → reinforces local-first invariant.

---

## §D6 — Host-surface inventory artifact location

### Decision

- **During mission execution**: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md`. Living matrix, updated by WP01 and each subsequent Tranche A WP.
- **At mission close**: WP05 promotes the final matrix to `docs/host-surface-parity.md` — a durable operator-facing doc referenced from `docs/trail-model.md` and from README's governance section.

### Schema (full schema in `contracts/host-surface-inventory.md`)

Per-row columns:

| Column | Values / Example |
|--------|------------------|
| `surface_key` | `claude`, `codex`, `vibe`, `copilot`, `auggie`, `q`, `cursor`, `gemini`, `opencode`, `windsurf`, `kilocode`, `roo`, `kiro`, `qwen`, `agent` |
| `directory` | `.claude/commands/`, `.agents/skills/spec-kitty.advise/`, … |
| `kind` | `slash_command` \| `agent_skill` |
| `has_advise_guidance` | yes / no |
| `has_governance_injection` | yes / no |
| `has_completion_guidance` | yes / no |
| `guidance_style` | `inline` \| `pointer` |
| `parity_status` | `at_parity` \| `partial` \| `missing` |
| `notes` | free text |

The canonical list of 15 host surfaces and their directories is derived from `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py::AGENT_DIRS` — single source of truth per CLAUDE.md guidance.

### Acceptance mapping

- FR-001 → authoritative matrix.
- NFR-003 → 100 % of 15 surfaces represented.
- FR-006 → per-row `guidance_style` + `notes` capture in-surface vs. pointer decision.

---

## §D7 — Dashboard wording scope

### Decision

Based on the grep pass against baseline (`eb32cf0a`):

**User-visible changes (in scope):**

`src/specify_cli/dashboard/templates/index.html`:
- Line 25: `<label>Feature:</label>` → `<label>Mission Run:</label>`
- Line 93: `<h2>Feature Overview</h2>` → `<h2>Mission Run Overview</h2>`
- Line 195: `<h3 style="…">Feature Analysis</h3>` → `<h3 style="…">Mission Run Analysis</h3>`
- Line 223: `Run <code>…</code> to create your first feature` → `Run <code>…</code> to create your first mission run`
- Line 235: `<p>Create your first feature using …</p>` → `<p>Create your first mission using …</p>`

`src/specify_cli/dashboard/static/dashboard/dashboard.js`:
- Line 354: `<h3>Feature: ${feature.name} …</h3>` → `<h3>Mission Run: ${feature.name} …</h3>`
- Line 1095: `return feature.display_name || feature.name || feature.id || 'Unknown feature';` → `'Unknown mission'`
- Line 1152: `` `Feature: ${getFeatureDisplayName(features[0])}` `` → `` `Mission Run: ${getFeatureDisplayName(features[0])}` ``
- Line 1397: `<div><strong>Feature:</strong> ${data.current_feature.name}</div>` → `<div><strong>Mission Run:</strong> ${data.current_feature.name}</div>`
- Line 1420: `<th …>Feature</th>` → `<th …>Mission Run</th>`

`src/specify_cli/dashboard/diagnostics.py`:
- Line 177: `"no feature context"` → `"no mission context"`

**Not in scope (backend identifiers preserved per FR-004 / C-007):**

- CSS classes `.feature-selector`, `.feature-selector label`, `.feature-selector select`, `.feature-selector select:hover`, `.feature-selector select:focus`
- HTML IDs `feature-selector-container`, `feature-select`, `single-feature-name`, `diagnostics-features`, `no-features-message`
- JS globals `currentFeature`, `allFeatures`, `featureSelectActive`, `featureSelectIdleTimer`, `lastFeature` cookie
- JS function names `switchFeature`, `getFeatureDisplayName`, `computeFeatureWorktreeStatus`, `updateFeatureList`, `setFeatureSelectActive`, `saveState(feature, page)`
- API route segments `/api/kanban/<feature>`, `/api/artifact/<feature>/<name>`, `/api/contracts/<feature>`, `/api/checklists/<feature>`, `/api/research/<feature>`
- JSON field names returned by the scanner (`feature_id`, `feature_number`, `feature.name`, `feature.display_name`, `current_feature.name`)
- Python helper `scanner.format_feature_display_name(...)` and its docstring

These backend identifiers are explicitly out of scope. Renaming them would cascade into API types, scanner, and cookie migration, which is exactly what C-007 forbids.

### Acceptance mapping

- FR-003 → every user-visible string above changes.
- FR-004 → backend identifiers unchanged.
- SC-002 → no user-visible `Feature` on the mission surfaces after WP02.

---

## §D8 — Decision-record structure

Four ADRs under `decisions/`, each drafted in the `adr-drafting-workflow` format (Context, Decision, Rationale, Alternatives Considered, Consequences, Revisit Trigger):

| ADR | Subject | Corresponds to |
|-----|---------|----------------|
| ADR-001 | Correlation contract uses append-only JSONL events on the invocation file | D1 / FR-007 |
| ADR-002 | `mode_of_work` is derived from the CLI entry command, not from the routed action | D2 / FR-008 |
| ADR-003 | SaaS read-model policy is a typed Python module, not operator-configurable YAML | D4 / FR-010 |
| ADR-004 | Tier 2 evidence SaaS projection is deferred — stays local-only in 3.2.x | D5 / FR-011 |

Each ADR explicitly references the rejected alternatives listed in this research document so that the decision context is preserved alongside the decision.

---

## §D9 — Testing approach

Applied to every Tranche B FR; Tranche A FRs get targeted tests for the wording fix and the parity matrix.

| FR | Test type | File | Assertion |
|----|-----------|------|-----------|
| FR-001 | Contract | `tests/specify_cli/docs/test_host_surface_inventory.py` (new) | The promoted `docs/host-surface-parity.md` lists all 15 surfaces from `AGENT_DIRS` with a non-empty `parity_status`. |
| FR-003 | Unit | `tests/specify_cli/dashboard/test_dashboard_wording.py` (new) | Read the three files; assert `"Feature:"` and `">Feature<"` do not occur in user-visible positions; assert `"Mission Run:"` and `">Mission Run<"` do occur at the expected positions. Also assert that `.feature-selector` CSS class and the `feature-select` HTML ID still exist (regression guard for FR-004). |
| FR-004 | Unit (regression) | Same file above | Assert presence of backend identifiers. |
| FR-007 | Integration | `tests/specify_cli/invocation/test_correlation.py` (new) | `profile-invocation complete --artifact path --artifact other --commit abc123` appends two `artifact_link` events and one `commit_link` event in order; `invocations list --json` reports them; ref-normalisation for in-checkout vs. out-of-checkout paths tested. |
| FR-008 | Unit | `tests/specify_cli/invocation/test_modes.py` (new) | `derive_mode(entry_command)` parameterised table — every entry command maps to its expected `ModeOfWork`. |
| FR-008 | Integration | `tests/specify_cli/invocation/test_invocation_e2e.py` (extended) | `mode_of_work` field appears on `started` event for advise/ask/do. |
| FR-009 | Integration | `tests/specify_cli/invocation/test_invocation_e2e.py` (extended) | `complete_invocation` with `--evidence` raises `InvalidModeForEvidenceError` when started mode is `advisory` or `query`; passes for `task_execution` / `mission_step`. |
| FR-010 | Unit | `tests/specify_cli/invocation/test_projection_policy.py` (new) | Every `(ModeOfWork, EventKind)` pair from the table has a `ProjectionRule`; `resolve_projection()` returns the exact `project`/`include_request_text`/`include_evidence_ref` for every pair. |
| FR-010 | Integration | Extend `tests/specify_cli/invocation/test_invocation_e2e.py` | With a mocked connected WebSocket client, `_propagate_one` skips events whose rule has `project=False`. |
| FR-011 | Doc-presence | `tests/specify_cli/docs/test_trail_model_doc.py` (new) | `docs/trail-model.md` contains the literal subsection headings "SaaS Read-Model Policy" and "Tier 2 SaaS Projection — Deferred". |
| FR-012 | Integration | Extend e2e | With sync disabled (`routing.effective_sync_enabled=False`), all new events are written locally and `propagation-errors.jsonl` stays empty. |
| FR-013 | Doc-presence | Same as FR-011 test | Migration subsection present in `docs/trail-model.md` and `CHANGELOG.md` unreleased entry. |
| FR-014 | Manual checklist | WP12 | Tracker hygiene verified by the release owner at merge; not code-tested. |
| NFR-001 | Performance | Extend e2e | Timed write of 100 `started` events; P95 ≤ 5 ms on a local filesystem. |
| NFR-002 | Performance | Extend e2e | 10,000 files scenario unchanged (existing test budget preserved after correlation fields added). |
| NFR-007 | Contract | Same as FR-012 | `propagation-errors.jsonl` empty after full e2e run with sync disabled. |

Mutation coverage encouraged for `invocation/` modules changed by Tranche B; not a release gate for this mission (the codebase already has mutation coverage for sibling modules per 3.2.0a4's mutation-aware pass).

---

## §D10 — Sequencing

Tranche A → Tranche B, strict. WP dependencies inside each tranche:

```
Tranche A:
  WP01 (inventory)
    ├─► WP02 (dashboard wording)          — can run in parallel with WP03 after WP01
    ├─► WP03 (rendering-contract sweep)   — can run in parallel with WP02
    └─► WP04 (skill-pack rollout)         — starts after WP01; partial overlap with WP02/03 possible
       └─► WP05 (inventory promotion + close #496)

Tranche B (begins only after WP05 approved):
  WP06 (mode derivation)
    └─► WP07 (correlation contract)       — WP07 depends on mode field existing on started event
       └─► WP08 (mode enforcement)        — WP08 depends on both WP06 (mode field) and WP07 wiring
  WP09 (projection policy)                — independent of WP07/WP08; depends on WP06 for mode enum
  WP10 (Tier 2 doc)                       — independent; can run in parallel with WP06–09
  WP11 (migration note + CHANGELOG)       — last; captures WP06–10
  WP12 (tracker hygiene)                  — at mission merge only
```

The smallest next chunk to build after `/spec-kitty.tasks` is **WP01**, whose single deliverable is the inventory matrix file at `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md`. **WP02** (dashboard wording) follows immediately and is the smallest code-touching chunk.

---

## Failure Modes and Premortem

Applying the premortem tactic: "assume this mission merged and failed at its goals — what went wrong?"

| Failure mode | Trigger | Detection | Prevention |
|--------------|---------|-----------|------------|
| Dashboard wording bleed — an operator sees `Feature` somewhere unexpected after merge | Hidden template/component renders `Feature` via a path not covered by WP01 grep | Post-merge dashboard walk-through in `quickstart.md` | WP02 grep test asserts no user-visible `Feature` in the three files + spot-check any other user-visible dashboard text surface found by WP01. |
| Correlation events appended to wrong invocation file | Path collision on malformed invocation_id input | Contract test on `append_correlation_link` | Reuse the existing `invocation_path()` helper; reject malformed ULIDs at CLI layer before calling writer. |
| Mode enforcement blocks legitimate mission-step evidence | A mission-step invocation's mode is misderived as advisory | Parameterised `derive_mode` test | D2 mapping is exhaustive and table-tested; mission-step drivers pass explicit mode via the executor kwarg. |
| SaaS policy regression — an existing `task_execution` event stops projecting | Misrowed `POLICY_TABLE` entry | Contract test checks each row against a baseline expectation | POLICY_TABLE has a golden-path test asserting `task_execution` rows preserve `project=True` for `started`/`completed`. |
| Local-first violation — a new code path blocks Tier 1 write on a SaaS failure | Someone calls `resolve_projection()` from the Tier 1 write path | E2e test with sync disabled + authenticated client absent | Plan forbids calling `resolve_projection` before `_ensure_dir`/`write_started`; enforced by code review + test. |
| Ref normalisation breaks on worktree paths | Worktrees live under `.worktrees/<slug>-lane-…`, which are nominally under `repo_root` | Integration test with worktree setup | D1 rule uses `is_relative_to(repo_root.resolve())`; worktrees resolve to the shared git root, so they are recorded relative to it — confirmed by test. |
| Tracker hygiene forgotten | Manual checklist drift | WP12 is a dedicated WP with explicit Definition of Done | Operator checklist in `quickstart.md`. |

---

## References

- `src/specify_cli/invocation/executor.py` — `ProfileInvocationExecutor.invoke`, `complete_invocation`
- `src/specify_cli/invocation/writer.py` — `InvocationWriter.write_started`, `write_completed`, `write_glossary_observation`
- `src/specify_cli/invocation/propagator.py` — `_propagate_one`, `InvocationSaaSPropagator`
- `docs/trail-model.md` — shipped trail contract
- `.agents/skills/spec-kitty.advise/SKILL.md` — governance injection guidance
- `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` — standalone invocations guidance
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py` — `AGENT_DIRS` (canonical host-surface list)
- `src/specify_cli/dashboard/{templates,static,diagnostics.py,api_types.py,scanner.py}` — dashboard surface
- CHANGELOG entry for 3.2.0a5 (2026-04-22)
- GitHub issues `#461`, `#466`, `#496`, `#534`, `#701`, `#759`
