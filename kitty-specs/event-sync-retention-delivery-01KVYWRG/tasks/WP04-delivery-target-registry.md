---
work_package_id: WP04
title: Delivery Target Registry & identity
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-012
tracker_refs: []
planning_base_branch: mission/event-sync-retention-delivery
merge_target_branch: mission/event-sync-retention-delivery
branch_strategy: Planning artifacts for this mission were generated on mission/event-sync-retention-delivery. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/event-sync-retention-delivery unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 3 - Delivery domain
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "42340"
history:
- at: '2026-06-29T06:21:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/delivery/targets.py
create_intent:
- src/specify_cli/delivery/__init__.py
- src/specify_cli/delivery/interfaces.py
- src/specify_cli/delivery/targets.py
- tests/delivery/test_targets.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/delivery/__init__.py
- src/specify_cli/delivery/interfaces.py
- src/specify_cli/delivery/targets.py
- tests/delivery/test_targets.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Delivery Target Registry & identity

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`
If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` and `authoritative_surface`.

---

## Objectives & Success Criteria

This WP delivers plan concern **IC-03 (Delivery Target Registry & identity)** plus the delivery-side scaffolding of **IC-01 (core domain boundaries)**. It stands up the brand-new `delivery/` core domain and the identity surface every other delivery WP keys off.

When this WP is complete:

- The `src/specify_cli/delivery/` package exists with a clean public surface (`__init__.py`) and an `interfaces.py` that declares the `typing.Protocol` seams for the *other* delivery WPs (target registry, ledger, receiver, dispatcher) — so WP05/WP06/WP07 implement against a contract, not against each other's concretions. This is the IC-01 anti-spaghetti seam (**C-001**): nothing in `delivery/` may leak back into `src/specify_cli/sync/queue.py` or into `src/specify_cli/events/`.
- `delivery/targets.py` registers a **Delivery Target** whose identity is **canonical URL + `url_hash` + user/team scope**, enforced by `UNIQUE(url_hash, team_slug, user_email)` (**C-002**, **FR-002**). Identity inputs are derived from WP01's `ResolvedSyncTarget` — never reconstructed independently.
- The endpoint URL is canonicalized deterministically so the same logical endpoint always hashes to the same `url_hash`.
- Deployment metadata (`server_instance_id`, `deployment_id`, `environment_name`, `git_sha`) is **recorded as provenance** on the target row, never used as an identity key.
- A **change** in deployment metadata under a stable URL raises an *advisory* reset signal that offers a re-drain (**FR-012**), without forking identity on `deployment_id` churn (Upsun re-stamps `deployment_id` on every push).

**Acceptance criteria satisfied**: FR-002 (per-target identity is the prerequisite for the per-target ledger), FR-012 (target-reset detection — advisory), C-002 (identity = URL + scope), C-001 (separate domain). Contributes to SC-004 (every delivery records endpoint URL + scope). Tests assert observable on-disk/registry state, not internal call order (**NFR-001**).

## Context & Constraints

**Prerequisite WP (`dependencies: ["WP01"]`)** — WP01 builds `src/specify_cli/sync/target_authority.py` and the `ResolvedSyncTarget` model with the eight contract fields (see contract §1): `configured_server_url`, `env_server_url`, `override_mode`, `resolved_server_url`, `user_id`, `team_slug`, `derived_queue_scope`, `queue_db_path`, `active_queue_scope_status`. **WP04 consumes `ResolvedSyncTarget` to derive target identity inputs** — specifically `resolved_server_url` (→ canonical URL → `url_hash`), `team_slug`, and `user_id`/email. Do NOT re-resolve config/env here; that is WP01's job and a second resolver would re-introduce the split-brain (**C-007**, **SC-008**) this mission exists to kill.

**Reference docs** (read for detail, do not summarize back):
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/spec.md` — FR-002, FR-012, C-001, C-002, C-003, C-004, the "Target reset under a stable URL" edge case, Key Entities → *Delivery Target*.
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/plan.md` — IC-01, IC-03, IC-09 (the SaaS `/health` follow-on that is OUT OF SCOPE here).
- `kitty-specs/event-sync-retention-delivery-01KVYWRG/contracts/event-sync-delivery-contract.md` — §1 (Target Authority fields you consume), §3 (Journal & Ledger — your target rows back the ledger's target identity).

**Architectural constraints to honor**:
- **C-001 (separate domain)**: all delivery logic lives under `src/specify_cli/delivery/`. No import edge from `delivery/` back into `sync/queue.py` or `src/specify_cli/events/`. The only inbound dependency is on WP01's `ResolvedSyncTarget` (a value object) from `sync/target_authority.py`.
- **C-002 (identity = URL + scope)**: identity key is `(url_hash, team_slug, user_email)`. Deployment metadata is provenance, never identity. This is the load-bearing rule of the whole WP.
- **C-003 (single active target, ledger shaped for many)**: WP04 registers targets; it does NOT pick "the" active target or fan out. The registry simply allows multiple target rows to coexist (target A and target B), which is exactly what re-drain (FR-005, owned by WP07) needs.
- **C-004 / IC-09 (SaaS `/health` is OUT OF SCOPE)**: consuming `/api/v1/sync/health/` deployment metadata from a live SaaS is a sequenced cross-repo follow-on. **Here, only model the recording of deployment metadata and the advisory reset detection on metadata change.** Do NOT add an HTTP call to fetch health metadata. Deployment metadata arrives as caller-supplied input to the registry API in this WP.

**Out-of-map note**: no out-of-map edits expected. All four `owned_files` are new. Do not touch `tasks.md`, `spec.md`, `plan.md`, `meta.json`, or any WP03/WP05 file.

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

## 🔒 Identifier Safety (binding — charter)

This WP generates storage-facing identifiers (`url_hash`, `target_id`, canonical URL) from user/branch/URL/team input. Per the charter's *Identifier Safety Rules* they MUST be **ASCII-only and deterministic**: sanitize with an explicit ASCII allowlist (`[A-Za-z0-9_]`) or opt regexes into `re.ASCII` — never rely on default Unicode `\w`/`\W`. **Required regression coverage**: at least one accented-Latin input plus an assertion that the produced identifier `.isascii()` is `True`.

**Scope boundary (FR-012 — A5)**: reset-detection here is **advisory scaffolding only**. Full reset-detection consumes SaaS `/api/v1/sync/health/` deployment metadata, deferred to the IC-09 follow-on (C-004) and **out of scope** for this mission. Record the metadata + advisory change-detection; do not gate delivery on it.

## Subtasks & Detailed Guidance

### Subtask T020 [P] – Stand up the `delivery/` package + `interfaces.py` protocols
- **Purpose**: Create the clean domain seam (IC-01 / **C-001**). This is the foundation the rest of Phase 3/4 builds on: WP05 (ledger), WP06 (receiver), WP07 (dispatcher) implement protocols declared here so they never import each other's concrete classes. Getting the seam right now avoids the later churn the plan's IC-01 risk note warns about.
- **Steps**:
  1. Create `src/specify_cli/delivery/__init__.py`. Export only the intended public surface (the target registry types from `targets.py`, plus the protocol names from `interfaces.py`). Keep it a thin re-export module — no logic.
  2. Create `src/specify_cli/delivery/interfaces.py`. Declare `typing.Protocol` stubs (structural typing, `@runtime_checkable` only where a runtime `isinstance` is genuinely needed) for the four delivery seams:
     - `DeliveryTargetRegistry` — `register(...) -> DeliveryTarget`, `get(url_hash, team_slug, user_email) -> DeliveryTarget | None`, `detect_reset(...) -> ResetSignal | None`. (Implemented in this WP, in `targets.py`.)
     - `DeliveryLedger` — selection + record + `delivered_anywhere(event_id) -> bool` (WP05 implements; declare the method signatures only).
     - `DeliveryReceiver` — endpoint/auth/result-map/retry/gates (WP06 implements; mirror contract §4 column semantics).
     - `Dispatcher` — select → post → record (WP07 implements).
  3. Each protocol carries a docstring naming its owning WP and the contract section it satisfies, so downstream WPs do not guess. Do not put implementation in `interfaces.py`; only `...`-bodied protocol methods plus the small value-object dataclasses they exchange that are owned here (e.g. the target identity tuple, `ResetSignal`). Value objects owned by other WPs (ledger row, receiver result enum) are referenced by name with a `# implemented in WPxx` comment, not redefined.
- **Files**: `src/specify_cli/delivery/__init__.py`, `src/specify_cli/delivery/interfaces.py`.
- **Parallel?**: Yes `[P]` — first subtask; no in-WP dependency. Parallel-safe against WP02/WP03 which own different packages.
- **Validation**:
  - [ ] `import specify_cli.delivery` succeeds and exposes the target-registry surface.
  - [ ] `interfaces.py` declares the four Protocols; `mypy` accepts them with zero errors.
  - [ ] `grep` confirms `delivery/` has **no** import of `specify_cli.sync.queue` or `specify_cli.events` (C-001).
- **Edge cases**: avoid circular imports — `interfaces.py` must not import `targets.py` (the protocol is the abstraction; the concretion depends on it, not the reverse). Keep `__init__.py` free of side effects so importing the package never touches the filesystem/DB.

### Subtask T021 – Target identity: canonical URL + `url_hash` + `UNIQUE(url_hash, team_slug, user_email)`
- **Purpose**: Establish the C-002 identity model (**FR-002**). A Delivery Target is uniquely one endpoint identity = canonical URL + scope. This is what lets the ledger key per-event/per-target state and what lets target A and target B coexist for re-drain.
- **Steps**:
  1. In `src/specify_cli/delivery/targets.py`, define a SQLite-backed `delivery_targets` table (or the registry's chosen store) with columns: `target_id` (surrogate PK, e.g. a deterministic id or autoincrement), `canonical_url`, `url_hash`, `team_slug`, `user_email`, the deployment-metadata provenance columns (see T023), and timestamps (`first_seen_at`, `last_seen_at`).
  2. Add `UNIQUE(url_hash, team_slug, user_email)` as the identity constraint (**C-002**). Registering the same canonical URL + same scope must return the existing row (upsert semantics), not create a duplicate.
  3. Derive identity inputs **from WP01's `ResolvedSyncTarget`**: `resolved_server_url` → canonical URL (T022) → `url_hash`; `team_slug` and `user_id`/email come from the resolved target's scope fields. Provide a constructor like `register_from_resolved(resolved: ResolvedSyncTarget, *, deployment_metadata=None)` plus a lower-level `register(canonical_url, team_slug, user_email, ...)` for tests.
  4. `user_email` / `team_slug` may legitimately be `None`/empty when identity is unknown (pre-auth). The UNIQUE constraint must treat a consistent normalized empty value (e.g. `""`) deterministically so the same anonymous endpoint does not fork — pick one normalization and document it.
- **Files**: `src/specify_cli/delivery/targets.py`.
- **Parallel?**: No — depends on T020 (package) and T022 (canonicalization feeds `url_hash`).
- **Validation**:
  - [ ] Two distinct URLs (same scope) → two target rows (SC-001 precursor).
  - [ ] Same canonical URL + same scope registered twice → one row (idempotent register).
  - [ ] `url_hash` is a one-way digest of the canonical URL (record the hash algorithm choice in a module docstring).
- **Edge cases**: scope normalization for unknown identity must be consistent; a `None` `team_slug` and an empty-string `team_slug` must not produce two identities for the same endpoint.

### Subtask T022 – Canonicalize the endpoint URL deterministically
- **Purpose**: The same logical endpoint must hash identically regardless of incidental URL spelling, so `url_hash` is stable and identity does not fork on cosmetic differences. This is the precondition for T021's UNIQUE constraint to actually deduplicate.
- **Steps**:
  1. Implement a pure `canonicalize_url(raw_url: str) -> str` in `targets.py`. Apply deterministic, lossless-for-identity normalization: lowercase scheme + host, strip a trailing slash on the path, drop a default port (`:443` for https, `:80` for http), and normalize an empty path to a single canonical form. Do NOT mangle query/fragment unless the spec's identity model excludes them — for an events batch endpoint identity, keep the decision narrow and documented.
  2. Compute `url_hash = <hash>(canonical_url)` with a single named helper so T021 and tests share it.
  3. Keep `canonicalize_url` and the hash helper **pure** (no I/O), so they are trivially unit-testable per NFR-001's observable-state preference and stay under the complexity ceiling (≤15).
- **Files**: `src/specify_cli/delivery/targets.py`.
- **Parallel?**: No — feeds T021.
- **Validation**:
  - [ ] `https://x.example/` and `https://X.EXAMPLE` and `https://x.example:443` all canonicalize equal → same `url_hash`.
  - [ ] Two genuinely different endpoints canonicalize distinct → different `url_hash`.
  - [ ] `canonicalize_url` performs no network or filesystem I/O.
- **Edge cases**: malformed/empty URL input — raise a clear domain error rather than silently producing a hash of garbage. Document whether the path is identity-significant for the events endpoint.

### Subtask T023 – Record (NOT key on) deployment metadata as provenance
- **Purpose**: Capture server-advertised deployment identity for provenance and reset-detection, while keeping it strictly OUT of the identity key (**C-002**). This is what later answers "the URL is the same but the server is a different deployment".
- **Steps**:
  1. Add provenance columns on the target row: `server_instance_id`, `deployment_id`, `environment_name`, `git_sha` (all nullable — they may be absent in the URL-only MVP, **C-004**).
  2. On `register`/upsert, accept an optional `deployment_metadata` mapping and store the latest values on the existing identity row — updating provenance does NOT create a new target (identity is still `(url_hash, team_slug, user_email)`).
  3. Preserve the *previous* deployment metadata (or enough of it) so T024 can detect a change. A simple approach: keep `last_deployment_id` and `last_seen_deployment_metadata` columns, or a small provenance-history sidecar — choose the minimal shape that lets T024 compare old vs new without forking identity.
- **Files**: `src/specify_cli/delivery/targets.py`.
- **Parallel?**: No — extends the T021 row.
- **Validation**:
  - [ ] Registering the same identity with new deployment metadata updates provenance on the existing row; the target count stays 1.
  - [ ] All four provenance fields are nullable and round-trip through the store.
- **Edge cases**: deployment metadata entirely absent (URL-only MVP) must be a valid, non-error state. Partial metadata (e.g. only `deployment_id`) must be storable.

### Subtask T024 – Advisory reset-detection on deployment-metadata change
- **Purpose**: Implement **FR-012** — when deployment identity *changes* under a stable URL (a preview env was wiped but kept its URL), flag a possible environment reset and *offer* a re-drain. This is exactly the "Target reset under a stable URL" edge case: URL+scope identity alone would report "fully delivered" while the new server has nothing.
- **Steps**:
  1. Add `detect_reset(resolved_or_identity, new_deployment_metadata) -> ResetSignal | None` to `targets.py` (and to the `DeliveryTargetRegistry` protocol in `interfaces.py`).
  2. Compare the **stored** deployment metadata for the matched identity against the incoming metadata. A meaningful change in a stable field (primarily `server_instance_id`; secondarily `environment_name`/`git_sha`) → return a `ResetSignal` describing what changed and recommending a re-drain.
  3. **Do NOT fork identity on `deployment_id` churn.** Upsun re-stamps `deployment_id` on every push, so `deployment_id` alone changing is normal redeploy noise, NOT a reset — make the reset signal driven by the stable-identity field(s), and treat `deployment_id`-only drift as non-resetting (record it, do not flag). Document this distinction inline.
  4. The signal is **advisory** (FR-012 is Low priority): it is data the CLI/status can surface and an operator can act on. WP04 does NOT automatically re-drain, does NOT mutate ledger state, and does NOT call the SaaS `/health` endpoint (that fetch is IC-09, out of scope, C-004). It only models recording + detection on caller-supplied metadata.
- **Files**: `src/specify_cli/delivery/targets.py`, `src/specify_cli/delivery/interfaces.py` (signature only).
- **Parallel?**: No — depends on T023's stored provenance.
- **Validation**:
  - [ ] Same URL + changed `server_instance_id` → `detect_reset` returns a `ResetSignal`; identity row count unchanged (no fork).
  - [ ] Same URL + only `deployment_id` changed → returns `None` (redeploy noise, not a reset).
  - [ ] First-ever registration (no prior metadata) → returns `None` (nothing to compare).
- **Edge cases**: incoming metadata absent while stored metadata exists — decide deterministically (treat missing-new as "no signal", document it). Multiple fields change at once — produce one signal listing them.

### Subtask T025 – Tests in `tests/delivery/test_targets.py`
- **Purpose**: Lock the identity and reset-detection behavior as observable on-disk/registry state (**NFR-001**), proving the C-002 identity model and FR-012 advisory detection.
- **Steps**:
  1. Create `tests/delivery/test_targets.py` (and `tests/delivery/__init__.py` if the suite needs a package marker — that marker is acceptable scaffolding within the delivery test tree).
  2. Use a temp/in-memory SQLite registry fixture so each test is isolated and parallel-safe under `--dist loadfile`.
  3. Write these scenarios (mapping to the WP01 `ResolvedSyncTarget` inputs where relevant):
     - **two URLs → two targets**: register endpoint A and endpoint B (same scope) → registry holds two distinct rows with distinct `url_hash`.
     - **same URL + new `deployment_id` does NOT fork identity but flags a reset**: register URL with `server_instance_id=s1`; re-register same URL with a changed stable field → still one row, `detect_reset` returns a `ResetSignal`; separately, a `deployment_id`-only change → still one row, `detect_reset` returns `None`.
     - **identity uniqueness enforced**: registering the same `(url_hash, team_slug, user_email)` twice yields one row (UNIQUE/upsert), and differing scope (different `team_slug` or `user_email`) yields a separate row.
     - **canonicalization equivalence**: trailing-slash / case / default-port variants of one URL register as one target.
  4. Assertions read the registry/DB state and `detect_reset` return values — never internal call sequencing.
- **Files**: `tests/delivery/test_targets.py` (+ optional `tests/delivery/__init__.py`).
- **Parallel?**: Tests are file-scoped; safe under `--dist loadfile`.
- **Validation**:
  - [ ] All four scenario groups present and green.
  - [ ] No test depends on a real network or a real Teamspace.
- **Edge cases**: cover the anonymous-scope (no user/team) registration path so the empty-scope normalization from T021 is exercised.

## Test Strategy

- **Mandatory test file**: `tests/delivery/test_targets.py` (owned). Scenarios: two-URLs→two-targets; identity-uniqueness/upsert; canonicalization equivalence; reset-detection (stable-field change flags, `deployment_id`-only churn does not).
- **Run**:
  ```bash
  PWHEADLESS=1 .venv/bin/pytest tests/delivery/test_targets.py -q
  ```
  No real-port/daemon resources are used here, so the default parallel runner is fine; the file is collectable under `-n auto --dist loadfile`.
- **Fixtures/stubs**: an in-memory or temp-dir SQLite registry; a small `ResolvedSyncTarget` factory (mirroring WP01's eight fields) so identity-derivation tests do not depend on WP01's resolver internals. No HTTP, no SaaS, no `/health` call.
- **Quality gates**: `.venv/bin/ruff check src/specify_cli/delivery tests/delivery` and `.venv/bin/mypy src/specify_cli/delivery` must pass with zero issues. Keep `canonicalize_url`, `register`, and `detect_reset` each ≤15 complexity (extract helpers if a branch tree grows).

## Risks & Mitigations

- **deployment_id churn forking identity** (plan IC-03 risk): mitigated by T021's identity key excluding all deployment fields and T024 treating `deployment_id`-only change as non-resetting. A regression here would re-create target rows on every Upsun push — covered by the explicit `deployment_id`-only test.
- **Reset-detection over-reaching into MVP** (C-004): mitigated by keeping FR-012 advisory — no auto-re-drain, no SaaS `/health` fetch. Detection runs only on caller-supplied metadata.
- **Domain leakage** (C-001): mitigated by the `grep` validation that `delivery/` imports neither `sync.queue` nor `events`. The only inbound dependency is WP01's `ResolvedSyncTarget` value object.
- **Wrong seam shape forcing WP05/WP06/WP07 churn** (IC-01 risk): mitigated by writing the four Protocols in `interfaces.py` first and giving each a contract-section docstring, so downstream WPs bind to the abstraction.

## Review Guidance

A reviewer running `/spec-kitty.review` must verify:
- Identity is `(url_hash, team_slug, user_email)` with a real `UNIQUE` constraint; deployment metadata is stored but never part of the key (**C-002** — the load-bearing check).
- `canonicalize_url` is pure and makes cosmetic URL variants hash equal (contract §1 / FR-002 precursor).
- `detect_reset` flags a stable-field change and is silent on `deployment_id`-only churn (**FR-012**); it does no I/O and no `/health` call (**C-004**).
- `delivery/` does not import `sync.queue` or `events` (**C-001**); `interfaces.py` declares the four downstream Protocols.
- `tests/delivery/test_targets.py` covers the contract's required behaviors as observable registry state (**NFR-001**), including two-URLs→two-targets and the no-fork-on-`deployment_id` case.

## Activity Log
> Entries chronological, appended at END. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`
- 2026-06-29T06:21:37Z – system – Prompt created.
- 2026-06-29T07:49:22Z – claude:opus:python-pedro:implementer – shell_pid=31738 – Assigned agent via action command
- 2026-06-29T08:15:59Z – claude:opus:python-pedro:implementer – shell_pid=31738 – Ready: target registry (url+scope identity, metadata provenance, advisory reset); ATDD + identifier-safety + gates green
- 2026-06-29T08:17:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=42340 – Started review via action command
- 2026-06-29T08:24:21Z – user – shell_pid=42340 – Review passed: C-002 identity=(url_hash,team_slug,user_email) with real UNIQUE constraint, deployment metadata recorded as provenance only; canonicalize_url pure+deterministic; detect_reset advisory/read-only, dep_id-only churn non-resetting, no /health (C-004); C-001 boundary clean; ATDD red->green valid; mypy --strict + ruff clean, C901<=15, 100% coverage, identifier-safety ASCII test present.
