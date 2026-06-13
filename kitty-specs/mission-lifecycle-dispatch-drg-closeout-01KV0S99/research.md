# Phase 0 Research — Mission lifecycle, dispatch & DRG closeout (01KV0S99)

Consolidated from three parallel read-only investigations (post-mission lifecycle,
dispatch collapse, DRG curation), with planning decisions and corrections applied.

---

## Workstream A — #1802 post-mission lifecycle surface (FSM + events)

**Operator decision (DM `01KV0V47…`):** extend the canonical status FSM + add
lifecycle events — NOT a parallel model.

### Findings

- **WP-level FSM** is the 10-state `Lane` enum (`src/specify_cli/status/models.py:23`);
  terminal lanes `done`/`canceled`. **Mission-level lifecycle is *derived*, not a
  canonical FSM:** `derive_mission_lifecycle()` (`status/lifecycle.py:164`) classifies
  a mission as active/recently_completed/archived/stale/abandoned/recoverable from WP
  states + age. "Merged" is **metadata-only** in `meta.json`
  (`merged_at`/`merged_by`/`merged_commit`/`merged_into`/`merged_strategy`,
  `mission_metadata.py:49`) — set by the merge gate, not by any event.
- **Lifecycle events already exist** as a distinct stream from WP status events:
  `status/lifecycle_events.py` defines an event enum (MissionCreated, SpecifyStarted,
  SpecifyCompleted, PlanStarted, …) with a `_build_envelope()` shape
  (`event_id` ULID, `event_type`, `aggregate_id`, `aggregate_type`, `schema_version`,
  `timestamp`, `payload`). Both lifecycle and WP-status events coexist in
  `status.events.jsonl`; **the reducer skips lifecycle events** (filters on the
  presence of WP fields like `to_lane`/`wp_id`), so adding event types does not perturb
  WP snapshots.
- **Force / terminal-exit machinery** exists at the WP level: `wp_state.py:_check_force`
  requires non-empty `actor` + `reason`; terminal force-exit from `done`/`canceled` is
  already a sanctioned, audited operation. Re-open reuses the *same audit discipline*
  (actor + reason + recorded event) at the **mission** level.
- **Identity:** `mission_id` (ULID, `meta.json`) is the immutable lookup key; follow-ups
  and re-opens attribute to `mission_id`, never to slug/number.

### Decisions

1. **D-A1 — Two new lifecycle event types** appended to the existing lifecycle stream:
   `MissionReopened` and `FollowUpRecorded` (payloads in `data-model.md`). They are
   **lifecycle** events (skipped by the WP reducer), surfaced through the mission
   lifecycle/history view, not the WP board.
2. **D-A2 — Re-open is event-as-authority, not a WP cascade.** `mission reopen <id>`
   appends `MissionReopened` (requires `--reason`, records actor) and clears `merged_*`.
   **Crucial correction (review-verified BLOCKING):** clearing `merged_*` alone is a no-op
   for the derived lifecycle — `derive_mission_lifecycle` / `_classify_state`
   (`status/lifecycle.py`) classify *purely* from WP-lane counts + age and never read
   `merged_*` or events. So actionability MUST come from the **event**: `derive_mission_lifecycle`
   is taught to honor a `MissionReopened` that postdates the last merge/completion marker,
   yielding a new `reopened` surface_state (treated as actionable) until a subsequent merge
   re-stamps `merged_*`. This keeps the event the single authority (consistent with the chosen
   FSM+events model and NFR-004), does **not** force-transition WPs (no cascading lane edits),
   keeps the reducer deterministic (lifecycle events stay reducer-skipped; only the derivation
   layer reads them), and is reversible. The `lifecycle.py` classification change is an
   explicit IC-01 deliverable (the original plan listed `lifecycle.py` as render-only — that
   was the gap).
3. **D-A3 — Follow-up is decoupled from re-open.** `mission follow-up <id>
   --commit <sha> | --pr <n>` appends `FollowUpRecorded` attributed to `mission_id`;
   allowed in **any** mission state (a post-merge doc/backport commit is a legitimate
   passive follow-up). Idempotent via dedup key `(mission_id, commit_sha|pr_number)`.
4. **D-A4 — Fail-closed re-open (NFR-004).** Re-open resolves the mission through declared
   authorities (`mission_id` + git registry). If the mission's branch/worktree is
   unrecoverable, fail closed with a structured error + remediation hint — never a silent
   partial state (spec edge case).
5. **D-A5 — Command home.** Add an instance-scoped `spec-kitty mission` command group
   (distinct from the existing `mission-type` group) hosting `reopen` and `follow-up`.
   Surface post-mission events in the mission lifecycle/history view (`status/views.py`
   + `lifecycle.py` result carries `post_mission_events`).

### Constraints / risks carried to the plan

- **C-SAAS (scope boundary, review-refined):** the SaaS event contract lives in the
  **external** `spec_kitty_events` package (shared-package-boundary ADR). Two registration
  facts: (1) `append_lifecycle_event` **hard-drops** any `event_type` not in the LOCAL
  `LIFECYCLE_EVENT_TYPES` frozenset — so both new types MUST be added there + to `__all__`
  (we control this). (2) `_validate_lifecycle_payload` strict-validates against the external
  package on the SaaS fan-out path and **skips** types in the external `LOCAL_ONLY_EVENT_TYPES`
  / not in its model map; an *unknown* type passes today, but a *future* `spec_kitty_events`
  release that learns `MissionReopened` with `additionalProperties:false` would make
  `strict=True` **raise** — a latent hard-fail, not a graceful degrade. Therefore: keep the
  two types **local-only** this mission (do not route them through the SaaS strict path);
  SaaS propagation of post-mission events is a **follow-up** requiring an external contract
  bump, not in scope. The local event log remains authoritative.
- **R-A1 (merge-gate re-entry):** a re-opened mission can re-enter merge. Mitigation:
  re-open clears `merged_*` and records the reason; the merge gate re-runs against the
  current snapshot (idempotent). Do **not** add speculative merge-policy knobs this
  mission (out of scope).
- **R-A2 (reducer determinism):** preserved because lifecycle events are reducer-skipped
  and the log is append-only (never rewritten). `FollowUpRecorded` is **idempotent** on its
  dedup key; `MissionReopened` is **append-each** (re-open twice → two recorded events, each
  a distinct fact). The derivation layer reads the latest `MissionReopened` vs the last merge
  marker; `post_mission_events` are sorted by `(timestamp, event_id)` so `lifecycle.json`
  stays byte-stable.

### Deferred sub-decisions (resolve in design/impl, not blocking)

- Does `mission_number` change on re-merge after re-open? **Default: reuse** the original
  number (historical stability); no new field this mission.
- `mission info --timeline`/`--history` rendering surface — additive view, low risk.

---

## Workstream B — #1810 unify do/ask/advise → `spec-kitty dispatch`

### Findings

- The governed-invocation **mechanism is already ~95% centralized** in
  `src/specify_cli/invocation/executor.py` (`ProfileInvocationExecutor.invoke()` →
  `complete_invocation()`): profile resolution (hint → registry, else router, else
  fail-closed), governance-context load (`mark_loaded=False`), glossary chokepoint scan,
  started-event write, best-effort SaaS propagate, structured payload return.
- `do` (`cli/commands/do_cmd.py`), `advise` + `ask` (`cli/commands/advise.py`) are **thin
  CLI wrappers** differing only in argument shape and mode. ~120 lines of duplicated
  helpers (`_get_repo_root`, `_build_executor`, `_detect_actor`, `_render_rich_payload`)
  across the two files; `advise.py` already centralizes via `_run_invoke()`, `do_cmd.py`
  does not reuse it.
- **Mode is a deterministic chokepoint** (`invocation/modes.py`): `_ENTRY_COMMAND_MODE`
  maps `do`/`ask` → `task_execution`, `advise` → `advisory` (ADR-002: mode derives from
  the CLI entry command, not the router action). The Op record (schema v2,
  `invocation/record.py`: `OpStartedEvent`/`OpCompletedEvent`, frozen Pydantic) carries
  `mode_of_work` as a required field.
- Registration is flat top-level commands in `cli/commands/__init__.py`
  (`app.command(name="do"|"ask"|"advise")`).

### Decisions

1. **D-B1 — Exposure, not extraction.** FR-004's "single mechanism" already exists
   (`ProfileInvocationExecutor`). The work is **CLI surface unification**: extract the
   duplicated helpers into one shared `_dispatch_impl(request, profile_hint, mode,
   json_output)`, and route all four verbs through it.
2. **D-B2 — `dispatch` is the canonical command;** `do`/`ask`/`advise` become thin
   aliases over `_dispatch_impl` (kept first-class per FR-005, NOT deprecated). Add a
   `dispatch` entry to `_ENTRY_COMMAND_MODE` (default `task_execution`). `dispatch`
   accepts `--profile`; alias verbs preserve their exact current argument shapes
   (`ask` keeps mandatory positional profile; `advise` keeps advisory mode).
3. **D-B3 — Parity is the binding contract (NFR-001, C-002).** Aliases and `dispatch`
   produce byte/contract-identical Op records (same `invocation_id` generation,
   `profile_id`/`action`/`request_text`/`actor`/`governance_context_hash`/`mode_of_work`,
   same JSONL path/shape) and identical JSON envelopes + exit codes. Land aliases in the
   **same change** as `dispatch` — never a window where the trio is broken (`spec-kitty do
   --profile …`, which this very workflow depends on, must keep working throughout).
4. **D-B4 — Propagation via SOURCE/manifest only (FR-006, C-004) — RESOLVED.** The
   verify-first question is answered: there is **exactly one** generated command-skill that
   documents the trio — `src/doctrine/skills/spec-kitty.advise/SKILL.md` (no separate `do`/`ask`
   skills, no per-agent hand-maintained command copies). FR-006 = add `dispatch` to that SOURCE
   SKILL.md, refresh `.kittify/command-skills-manifest.json` via the skills install path, and
   update the skill-routing prose that names the trio. This is **not** a "19-way" edit and never
   touches generated agent copies (C-004). Soften any "19-agent surfaces" wording to "the
   canonical skill + manifest (propagated to configured agents)."

### Work-slice shape

Refactor + add (B-1), parity tests (B-2, can run alongside), propagation (B-3, gated on
the verify-first finding). No router/executor/record changes.

---

## Workstream C — #1863 DRG curation (fix references + document residual)

### Findings

- Graph: `src/doctrine/graph.yaml`. Generator: `src/doctrine/drg/migration/extractor.py`
  (`generate_graph`); CLI: **`spec-kitty doctrine regenerate-graph [--check] [--json]`**.
  **Already deterministic / no-op-stable** (sorted nodes by URN, edges by
  `(source,target,relation)`, `generated_at="STATIC"`; `test_regenerate_twice_is_byte_identical`
  passes) — NFR-003 is *already satisfied* and only needs a regression-pin, not a fix.
- **26 orphan nodes** (no inbound/outbound edge). The `java-conventions.styleguide.yaml`
  `references:` entry points at `java-implementer.agent.yaml`, which **does not exist**;
  `_resolve_path_ref()` mints a phantom `agent_profile:java-implementer` node anyway.
- Freshness/regen tests live in
  `tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py`.

### Decisions (with the no-bulk-delete correction)

1. **D-C1 — Stale-ref repair, not deletion, is the FR-008 core.** Repaint
   `java-conventions.styleguide.yaml` → `java-jenny.agent.yaml` (the real Java specialist
   profile, which exists and already `specializes_from implementer-ivan`). Sweep for
   **other references of the same class** (path/id/casing/retired-id that point at a
   non-existent artifact) and repair-or-prune-the-reference (not the target artifact).
2. **D-C2 — CORRECTION to the research's "prune 18 Category A orphans."** An orphan that
   is a **valid, deliberately-authored doctrine artifact** (Fowler refactoring tactics,
   mutation-testing toolguides, the REASONS/skill-authoring styleguides, ZOMBIES TDD,
   etc.) is **not** a defect — it is unreferenced, not stale. Deleting valid doctrine to
   turn a graph metric green is content destruction and violates **C-003** ("documented,
   never silently accepted") and the never-delete-to-fix rule. For each genuinely-orphaned
   *artifact* (as opposed to a stale *reference*): **prefer wiring a real inbound edge**
   when a natural referent exists (e.g., link a refactoring tactic from the refactoring
   procedure/coding directive), **else document it as an accepted residual** with a
   per-orphan rationale. Pruning is reserved for artifacts that are genuinely retired
   (superseded, dead) — and each prune is individually justified, never bulk.
3. **D-C3 — Documented residual + regression pin (FR-009, C-003).** After repairs +
   edge-wiring, regenerate deterministically; the remaining orphan set is the
   **documented** residual (per-orphan rationale in-mission), and a curation follow-up
   ticket is filed if non-empty before #1863 closes. Pin the reduced orphan count with a
   regression test so it cannot silently grow.

### Work-slice shape

C-1 stale-reference repair (java-implementer + same-class sweep), C-2 orphan triage
(wire-or-document, individually-justified prunes only), C-3 deterministic regen +
orphan-count regression pin + residual doc.

---

## Cross-cutting

- **Independence:** A, B, C touch disjoint surfaces (`status/` + `cli/commands/mission*`
  vs `invocation/` + `cli/commands/{do,ask,advise,dispatch}` vs `src/doctrine/`). They are
  **parallel lanes** with no inter-dependency; tasks-phase should keep `owned_files`
  non-overlapping per workstream.
- **Closure ledger:** issue-matrix rows for #1802/#1804/#1810/#1863 stay `in-mission`
  until each reaches a terminal verdict at merge (per the in-mission verdict practice).
  #1804 closes when #1810 lands (FR-007); #1802 closes when FR-001/002 land or the residual
  is split to a child (FR-003).
- **Out of scope (C-005):** no-op-stability PR #1913 / umbrella #1914, #1916, #1907, API
  epic #1010. graph.yaml determinism is the *only* no-op-stability touchpoint here, and it
  is already satisfied — we pin, we don't re-architect.
