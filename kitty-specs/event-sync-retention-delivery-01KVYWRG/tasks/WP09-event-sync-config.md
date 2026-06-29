---
work_package_id: WP09
title: EventSyncConfig policy & modes
dependencies:
- WP05
- WP06
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
- T053
- T054
- T055
phase: Phase 5 - Policy, migration, status, CLI
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "78262"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/delivery/config.py
create_intent:
- src/specify_cli/delivery/config.py
- tests/delivery/test_config.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/delivery/config.py
- tests/delivery/test_config.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – EventSyncConfig policy & modes

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`
If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

This WP implements plan concern **IC-06 — EventSyncConfig policy & modes**. `EventSyncConfig` is the
operator dial over **retention × delivery**. It is *policy*, not target selection: it decides whether
events are journaled and which receiver (if any) drains them, but it does **not** independently choose a
network target — that authority belongs to WP01's `ResolvedSyncTarget` / target authority (FR-016,
C-007, contract §1). When a mode names "Teamspace", it means "use the Teamspace receiver against the
already-resolved target", not "pick a server".

Complete when:

- `delivery/config.py` models `EventSyncConfig` as **two orthogonal axes** — retention (on/off) ×
  delivery (none / Teamspace / external-receiver) (**FR-006**, spec US2: "Modeled as two orthogonal
  axes ... with the named modes as presets").
- Four named presets sit on those axes: `TEAMSPACE`, `EXTERNAL_RECEIVER`, `LOCAL_RETENTION`,
  `OPT_OUT`/`TRASH` (**FR-006**; spec FR-006 mode list).
- A mode resolves to `(DeliveryReceiver from WP06, retention flag)`; `EXTERNAL_RECEIVER` and the stub
  reuse the **same** machinery as Teamspace (**FR-007**; the stub falls out of `EXTERNAL_RECEIVER`,
  spec US3).
- `OPT_OUT`/`TRASH` discards **only** local-only or explicitly-discardable families; a Teamspace-bound
  discard is **refused or audit-recorded through a durable source**, never silently dropped
  (**C-008**, contract §2 rule 4 + §3).
- Tests (US2 Independent Test) assert observable on-disk + network behavior for each mode:
  `LOCAL_RETENTION` journals but never posts; `OPT_OUT` neither journals nor posts for local-only
  families; a Teamspace-bound discard is refused/audited.

Satisfies/contributes to **SC-009** (events still captured under blocked delivery) at the policy layer
and the US2 acceptance scenarios 1–5.

## Context & Constraints

**Prerequisite WPs and what they hand you:**

- **WP05 — Delivery Ledger** (`src/specify_cli/delivery/ledger.py`). Resolution does not write the
  ledger, but the modes' observable behavior is *defined against* ledger state (e.g. `LOCAL_RETENTION`
  produces journal rows with no delivery ledger rows). Your tests assert that the chosen
  `(receiver, retention)` produces the right downstream journal/ledger footprint.
- **WP06 — DeliveryReceiver contract + receivers** (`src/specify_cli/delivery/receivers.py`). It gives
  you `TeamspaceReceiver`, `ExternalReceiver`, `StubReceiver`, and the `DeliveryReceiver` protocol. Mode
  resolution returns one of those receivers (or `None` for delivery=none). You consume the receiver
  types; you do not re-implement delivery. The stub is just `EXTERNAL_RECEIVER` pointed at a localhost
  endpoint — reuse the same resolution path (spec US3, SC-005).

**Links:**

- `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md` — FR-006, FR-007; US2 (the four modes +
  the two-axis framing) and its Independent Test; US2 acceptance scenarios 1–5; SC-009; Key Entity
  **EventSyncConfig**; edge case "Capture before drain gates".
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` — IC-06 (modes, opt-out safety);
  IC-00/FR-016 (target authority owns the network target, not this config).
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md` — §2
  (capture-before-drain; OPT_OUT/TRASH may discard only local-only/discardable; Teamspace-bound discard
  refused or audit-recorded through a registered durable source), §3 (journal/ledger), §4 (the receivers
  this config resolves to).

**Architectural constraints to honor:**

- **WP09 is policy, not target authority.** `EventSyncConfig` selects retention × delivery; it must NOT
  resolve or override the network server URL. The resolved target comes from WP01 (FR-016, C-007,
  contract §1). If a mode needs the resolved URL (Teamspace), it reads it from the resolved target,
  never from this config. (This is the explicit boundary called out in the WP brief.)
- **C-008 — no silent Teamspace-bound discard.** Opt-out / missing-auth / disabled-sync may block
  *drain eligibility*, but a Teamspace-bound fact may be discarded only if a durability registry/audit
  classification proves it is local-only or explicitly discarded. Otherwise: refuse the policy with an
  audit-visible reason, or write durable audit evidence (SQLite/git audit/replay source). Never silently
  drop. (Contract §2 rule 4.)
- **NFR-001** — tests assert observable on-disk + network state, not call order.
- **C-001 (separate domain)** — all logic lands in `delivery/config.py`; no leakage into `queue.py` or
  `src/specify_cli/events/`.
- **Terminology Canon** — "Mission" not "feature"; no `feature*` aliases in any mode name, field, or
  config key. Use `OPT_OUT`/`TRASH`, `LOCAL_RETENTION`, `TEAMSPACE`, `EXTERNAL_RECEIVER` verbatim.

**Out-of-map edits:** none. Both `delivery/config.py` and `tests/delivery/test_config.py` are in
`owned_files`. CLI wiring of mode selection is WP12 (T074) — do **not** edit `cli/commands/sync*` here.

## Branch Strategy
- **Strategy**: Planning artifacts were generated on mission/event-sync-retention-delivery; completed changes must merge back into mission/event-sync-retention-delivery.
- **Planning base branch**: mission/event-sync-retention-delivery
- **Merge target branch**: mission/event-sync-retention-delivery
> Populated by `spec-kitty agent mission tasks`. Do not change manually.

## 🔴 ATDD-First (binding — charter C-011)

**You cannot start implementation until a failing-first ATDD test exists.** Per the charter's *ATDD-First Discipline* (binding, C-011), this WP follows red→green→refactor:

1. **RED first** — before any implementation commit, write at least one acceptance test that pins the user-observable behaviour this WP delivers (see the Subtasks/Acceptance below) and commit it **as the lane's first, separate commit while it FAILS**.
2. **GREEN** — implement until that test (and the rest) pass.
3. **Refactor** with the tests green.

The reviewer verifies **red→green**: the ATDD test was RED on `mission/event-sync-retention-delivery` and GREEN on this WP's final commit. A WP without a failing-first ATDD commit is **rejected at review** even if the code works.

## ⌨️ Operator CLI surface (A7)

EventSyncConfig mode selection is pinned to `spec-kitty sync mode <TEAMSPACE|EXTERNAL_RECEIVER|LOCAL_RETENTION|OPT_OUT>` (`sync mode` with no argument prints the current mode). Define this surface's policy resolution in `delivery/config.py`. Honor the Terminology Canon — no `feature*` aliases in the flag/command/field.

## Subtasks & Detailed Guidance

### Subtask T051 – Model EventSyncConfig as two orthogonal axes
- **Purpose**: Encode the spec's framing precisely: retention (on/off) and delivery
  (none / Teamspace / external-receiver) are independent axes; the named modes are presets over them.
  This is the load-bearing design decision of FR-006 / US2.
- **Steps**:
  1. In `src/specify_cli/delivery/config.py`, define two enums:
     - `Retention` = `{ON, OFF}` (does the journal persist payloads?).
     - `Delivery` = `{NONE, TEAMSPACE, EXTERNAL_RECEIVER}` (which receiver, if any, drains?).
  2. Define `EventSyncConfig` (frozen dataclass) holding `retention: Retention`, `delivery: Delivery`,
     and any delivery-specific operator parameters that are NOT target authority (e.g. for
     `EXTERNAL_RECEIVER`: the operator endpoint URL + optional auth — these are *config* inputs to the
     `ExternalReceiver`, distinct from the WP01-resolved Teamspace target).
  3. Add a docstring stating the boundary: this config never resolves the Teamspace network target; the
     `TEAMSPACE` delivery reads the resolved URL from the WP01 target authority.
  4. Keep the axes genuinely independent in the type system — do not collapse them into a single enum,
     because LOCAL_RETENTION (retention ON × delivery NONE) must be distinct from OPT_OUT
     (retention OFF × delivery NONE).
- **Files**: `src/specify_cli/delivery/config.py`.
- **Parallel?**: `[P]` — the axis/type model can be authored first; presets and resolution build on it.
- **Validation**:
  - [ ] Two independent axes exist; retention and delivery are not conflated.
  - [ ] `EventSyncConfig` carries external-receiver config (URL/auth) but **no** Teamspace server URL.
  - [ ] Module docstring states the "policy not target authority" boundary (FR-016/C-007).
- **Edge cases**: an invalid axis combination should be representable only through validation, not
  silently — but note all four presets are valid; the only "invalid" intent is a free-form combination
  the presets do not name (handle via a constructor that accepts presets, see T052).

### Subtask T052 – Four presets over the axes
- **Purpose**: Provide the operator-facing named modes (FR-006) as presets on the two axes.
- **Steps**:
  1. Define a `Mode` enum: `TEAMSPACE`, `EXTERNAL_RECEIVER`, `LOCAL_RETENTION`, `OPT_OUT`. Treat `TRASH`
     as a documented alias of `OPT_OUT` (spec writes `OPT_OUT`/`TRASH`); normalize the alias to the
     canonical `OPT_OUT` at the input boundary so only one canonical value is stored.
  2. Map each preset to its `(Retention, Delivery)` point:
     - `TEAMSPACE` → retention ON × delivery TEAMSPACE (journal on → Teamspace receiver).
     - `EXTERNAL_RECEIVER` → retention ON × delivery EXTERNAL_RECEIVER (journal on → operator endpoint).
     - `LOCAL_RETENTION` → retention ON × delivery NONE (retain now, drain later — a target can be set
       later and `sync now` drains the retained events; US2 acceptance scenario 2).
     - `OPT_OUT`/`TRASH` → retention OFF × delivery NONE (do not journal local-only families, do not
       send; US2 acceptance scenario 4).
  3. Provide `EventSyncConfig.from_mode(mode, *, external_endpoint=..., external_auth=...) ->
     EventSyncConfig` so the CLI (WP12) constructs config from a mode token. Hoist the preset table to a
     module constant (Sonar S1192) rather than scattering literals.
- **Files**: `src/specify_cli/delivery/config.py`.
- **Parallel?**: No — depends on the T051 axes.
- **Validation**:
  - [ ] All four presets resolve to the exact `(retention, delivery)` points above.
  - [ ] `TRASH` normalizes to `OPT_OUT`; only the canonical value is stored.
  - [ ] `LOCAL_RETENTION` (retention ON) is distinguishable from `OPT_OUT` (retention OFF).
- **Edge cases**: `EXTERNAL_RECEIVER` mode with no endpoint configured → constructor raises/returns a
  validation error (you cannot deliver externally with no endpoint). `TEAMSPACE` mode does not require an
  endpoint here — it reads the resolved target at delivery time.

### Subtask T053 – Resolve mode → (DeliveryReceiver, retention flag)
- **Purpose**: Turn a config into the runtime pair the dispatcher (WP07) and journal use, reusing the
  WP06 receivers. EXTERNAL_RECEIVER and the stub share the same machinery (FR-007, SC-005).
- **Steps**:
  1. Add `resolve(self, *, resolved_target, receiver_factory=...) -> ResolvedPolicy` returning a small
     value object: `retain: bool` and `receiver: DeliveryReceiver | None`.
     - retention ON → `retain = True`; OFF → `retain = False`.
     - delivery NONE → `receiver = None`.
     - delivery TEAMSPACE → `TeamspaceReceiver` parameterized by the WP01-resolved target (read the URL
       from `resolved_target`, never from this config).
     - delivery EXTERNAL_RECEIVER → `ExternalReceiver` parameterized by the config's operator
       endpoint/auth. A localhost endpoint here *is* the stub case (no new path).
  2. Inject the receiver construction via a `receiver_factory` (or import the WP06 constructors directly)
     so tests can substitute a `StubReceiver` — but resolution logic is identical; the stub is just an
     external receiver at a localhost URL (contract §4 rule 2).
  3. Keep `resolve` under the complexity ceiling (≤15) — it is a small lookup/build; do not fold gate
     evaluation in here (gates are receiver-owned, WP06).
- **Files**: `src/specify_cli/delivery/config.py`.
- **Parallel?**: No — depends on T051/T052 and WP06 receiver types.
- **Validation**:
  - [ ] Each mode resolves to the correct `(retain, receiver)` pair.
  - [ ] TEAMSPACE reads the URL from the resolved target, not from this config.
  - [ ] EXTERNAL_RECEIVER and a localhost stub use the same resolution branch (no separate stub path).
- **Edge cases**: TEAMSPACE resolve with no resolved target available → surface a clear policy error
  (not a crash); this is the "delivery blocked, capture still happens" seam (SC-009) handled jointly with
  T054 and WP03's capture-first.

### Subtask T054 – OPT_OUT/TRASH discard safety (C-008)
- **Purpose**: Enforce the hard rule: OPT_OUT discards ONLY local-only or explicitly-discardable
  families; a Teamspace-bound discard must be REFUSED or audit-recorded through a durable source — never
  silently dropped (C-008, contract §2 rule 4).
- **Steps**:
  1. Add a classification-aware discard gate, e.g. `discard_decision(event_family, *, classification)
     -> DiscardDecision`, where `DiscardDecision` is one of: `discard_allowed` (local-only or explicitly
     discardable), `refused` (Teamspace-bound, no durable evidence — block the policy with an
     audit-visible reason), or `audit_recorded` (Teamspace-bound, but durable audit evidence is written
     to an approved source so the fact is not lost).
  2. Consume the family classification (local-only / Teamspace-bound / explicitly-discardable) from the
     durability registry/classification surface. If WP09's prerequisites do not yet expose a classifier,
     define the decision interface and default any unclassified family to **NOT discardable**
     (fail-closed): an unknown family is treated as potentially Teamspace-bound and is refused/audited,
     never silently dropped (C-008 fail-closed posture).
  3. Ensure OPT_OUT for a Teamspace-bound family produces an audit-visible reason (the same
     `drain_blocked_reason`/audit channel WP03 capture-first uses) rather than a no-op.
- **Files**: `src/specify_cli/delivery/config.py`.
- **Parallel?**: No — depends on the mode model (T051/T052).
- **Validation**:
  - [ ] OPT_OUT discards local-only / explicitly-discardable families only.
  - [ ] A Teamspace-bound discard is refused OR audit-recorded through a durable source — never silent.
  - [ ] Unknown/unclassified family defaults to non-discardable (fail-closed).
- **Edge cases**: a family that is *explicitly* marked discardable by an approved durability
  classification IS allowed to be dropped (the exception C-008 permits) — assert this path too, so the
  rule is not over-broad. A discard refusal must carry a human-readable, audit-visible reason string.

### Subtask T055 – Tests in tests/delivery/test_config.py (US2 Independent Test)
- **Purpose**: Prove each mode's observable on-disk + network behavior (US2 Independent Test, NFR-001).
- **Steps**:
  1. **TEAMSPACE**: resolve against a fake resolved target; assert `retain` is True and the receiver is a
     `TeamspaceReceiver` whose endpoint is the resolved target's URL (not anything from the config) —
     US2 acceptance scenario 1.
  2. **LOCAL_RETENTION**: assert `retain` is True and `receiver` is `None`; driving a produce+sync cycle
     **journals** events but **never posts** (no receiver invoked); then set a target/mode later and
     confirm the retained events become drainable — US2 acceptance scenario 2.
  3. **EXTERNAL_RECEIVER**: with a localhost stub endpoint, assert resolution yields an `ExternalReceiver`
     (the stub) and a delivery records ledger state with no Teamspace credentials present (ties to
     SC-005, US2 acceptance scenario 3, US3).
  4. **OPT_OUT (local-only family)**: assert `retain` is False and `receiver` is `None`; a produce cycle
     for a local-only family **neither journals nor posts** — US2 acceptance scenario 4.
  5. **OPT_OUT (Teamspace-bound family)**: assert the discard is **refused or audit-recorded** with an
     audit-visible reason and the fact is NOT silently dropped (durable evidence or refusal) — US2
     acceptance scenario 5, C-008, SC-009.
  6. Assert the alias: constructing from `TRASH` yields the canonical `OPT_OUT` mode.
  7. Assertions are observable on-disk (journal rows / ledger rows / audit reason) + network
     (receiver invoked or not), never call order (NFR-001).
- **Files**: `tests/delivery/test_config.py`.
- **Parallel?**: No — depends on T051–T054 and WP05/WP06.
- **Validation**:
  - [ ] One observable-behavior test per mode (TEAMSPACE, EXTERNAL_RECEIVER, LOCAL_RETENTION, OPT_OUT).
  - [ ] LOCAL_RETENTION journals but never posts; OPT_OUT (local-only) neither journals nor posts.
  - [ ] Teamspace-bound OPT_OUT is refused/audited (never silent) — C-008 asserted directly.
  - [ ] TRASH alias normalizes to OPT_OUT.
  - [ ] No real network; the external/stub path uses a localhost/in-process `StubReceiver`.
- **Edge cases**: ensure no ambient Teamspace credential leaks into the EXTERNAL_RECEIVER/stub case (mirror
  SC-005 hygiene). The Teamspace-bound discard test must fail if the implementation no-ops the discard.

## Test Strategy

- **Owned test file**: `tests/delivery/test_config.py`.
- **Run (parallel-safe — config resolution + in-process stub, no real ports):**
  ```bash
  PWHEADLESS=1 .venv/bin/pytest tests/delivery/test_config.py -q
  ```
- **Fixtures/stub notes:** use a fake `ResolvedSyncTarget` (from WP01's shape) for the TEAMSPACE case so
  the test asserts the URL comes from the target, not the config. For EXTERNAL_RECEIVER, point the
  config at a localhost `StubReceiver` (WP06) — this is the same machinery, not a special path. No daemon
  / real-port resources are needed, so `-n0` is not required.
- **Assertion style (NFR-001):** assert on the resolved `(retain, receiver)` pair, journal/ledger row
  presence, and the audit-reason string — never on internal call sequencing.

## Risks & Mitigations

- **Config silently choosing a network target** (FR-016/C-007 violation). *Mitigation*: TEAMSPACE reads
  the URL from the WP01 resolved target; the TEAMSPACE test asserts the endpoint equals the target's URL,
  not anything stored in `EventSyncConfig`.
- **OPT_OUT silently dropping Teamspace-bound facts** (C-008, the IC-06 headline risk). *Mitigation*:
  fail-closed `discard_decision` (unknown family → non-discardable); the Teamspace-bound discard test
  asserts a refusal/audit, and fails on a no-op.
- **LOCAL_RETENTION vs OPT_OUT conflated** (both delivery=NONE). *Mitigation*: keep retention a distinct
  axis; separate tests assert LOCAL_RETENTION journals while OPT_OUT does not.
- **Stub treated as a special mode** instead of EXTERNAL_RECEIVER at localhost. *Mitigation*: single
  resolution branch for EXTERNAL_RECEIVER; the stub is a localhost endpoint (contract §4 rule 2).
- **Complexity ceiling (15)** on `resolve`/`from_mode`. *Mitigation*: preset table is a module constant
  lookup; resolution is a small build step; classification gate is a separate helper.

## Review Guidance

For `/spec-kitty.review`, a reviewer must verify (tie to US2 Independent Test + contract §2/§4):

- `EventSyncConfig` models retention × delivery as two independent axes, and the four presets map to the
  exact axis points (FR-006).
- Mode resolution returns `(receiver, retention)` reusing WP06 receivers; TEAMSPACE reads the resolved
  URL from WP01 target authority, not from the config (FR-016/C-007 boundary).
- EXTERNAL_RECEIVER / stub share one resolution branch (FR-007, SC-005); the stub is a localhost external
  receiver, not a special mode.
- OPT_OUT/TRASH discards only local-only/discardable families; a Teamspace-bound discard is refused or
  audit-recorded through a durable source, never silent (C-008, contract §2 rule 4); unknown families
  fail closed.
- `tests/delivery/test_config.py` asserts observable on-disk + network behavior per mode (NFR-001):
  LOCAL_RETENTION journals-not-posts; OPT_OUT (local-only) neither-journals-nor-posts; Teamspace-bound
  discard refused/audited; TRASH→OPT_OUT alias.

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T09:25:41Z – claude:opus:python-pedro:implementer – shell_pid=74764 – Assigned agent via action command
- 2026-06-29T09:40:41Z – claude:opus:python-pedro:implementer – shell_pid=74764 – for_review (propagate; lane pristine at cd5d871bd)
- 2026-06-29T09:40:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=78262 – Started review via action command
- 2026-06-29T09:46:12Z – user – shell_pid=78262 – Review passed: 24/24 test_config.py green @100% cov, full delivery suite 125 passed, mypy+ruff clean. ATDD red verified (config.py absent at test-only commit 7909f469b, present at impl cd5d871bd). Two orthogonal axes Retention x Delivery, 4 presets; Mode.from_token case/-insensitive rejects unknown + feature_sync (canon). resolve(): TEAMSPACE reads URL from resolved_target not config (no Teamspace URL field), EXTERNAL_RECEIVER+stub share one branch, NONE->None, TEAMSPACE w/o target raises PolicyResolutionError (SC-009 seam), EXTERNAL w/o endpoint raises MissingExternalEndpointError. C-008: Teamspace-bound/UNKNOWN discard REFUSED (dropped=False, audit-visible reason) w/o durable sink, AUDIT_RECORDED to on-disk JSONL with sink; local-only/explicitly-discardable allowed; unknown fails closed. C-001 honored (imports only WP06 receivers). Owned files only.
