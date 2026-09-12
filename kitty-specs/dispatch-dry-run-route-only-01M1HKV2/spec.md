# Mission Specification: `dispatch --dry-run` — side-effect-free routing query mode

**Mission Branch**: `feat/dispatch-dry-run-route-only-3840`
**Created**: 2026-09-02
**Status**: Draft
**Input**: GitHub Issue [#3840](https://github.com/Priivacy-ai/spec-kitty/issues/3840) — "dispatch --json: no side-effect-free routing query — every call opens a governance Op"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Route-as-you-type UI probes the router without littering governance history (Priority: P1)

An external consumer (e.g. an intent-composer UI) wants to show "this would route to
`implementer-ivan` / `fix`, confidence: canonical_verb" as the operator types, updating on
every keystroke or debounce tick. Today the only way to get that signal is a real
`spec-kitty dispatch --json` call, which opens a governance Op (writes `kitty-ops/<id>.jsonl`,
appends to `kitty-ops/ops-index.jsonl`, and persists glossary-event candidates) that the UI
then has to close as `abandoned` — or the UI must not probe at all.

**Why this priority**: This is the issue's core ask. Without it, the mission delivers nothing
the issue requested.

**Independent Test**: Run `spec-kitty dispatch "<request>" --dry-run --json` twice in a row
against a clean checkout. Assert: (a) both calls return `"status": "dry_run"` JSON with a
routing signal (`profile_id`, `action`, `router_confidence`), and (b) no file under `kitty-ops/`
is created or modified by either call (see FR-002 / AC-002 for the exact assertion shape).

**Acceptance Scenarios**:

1. **Given** a clean checkout with no `kitty-ops/` directory, **When** the operator runs
   `spec-kitty dispatch "fix the failing test" --dry-run --json`, **Then** the command exits 0,
   prints a JSON payload with `"status": "dry_run"`, and no `kitty-ops/` directory is created.
2. **Given** an existing `kitty-ops/` directory with N files and M lines in
   `kitty-ops/ops-index.jsonl`, **When** the operator runs `spec-kitty dispatch "<request>"
   --dry-run --json` any number of times, **Then** the directory still contains exactly N files
   and `ops-index.jsonl` still has exactly M lines afterward.
3. **Given** a request whose tokens are unrecognized by the glossary index, **When** the
   operator runs `spec-kitty dispatch "<request>" --dry-run --json`, **Then** no new
   `TermCandidateObserved` glossary event is persisted (FR-003), even though the JSON payload's
   `glossary_observations` field still reports the in-memory scan result.

---

### User Story 2 - Consumer reads `alternatives` to judge routing confidence before trusting the winner (Priority: P2)

The issue's own "Related" section names the router's confident-misroute behavior (SK-08,
covered by User Story 3) and states: "A confidence/ambiguity field in the dry-run output would
let consumers apply their own threshold." A UI or automation consumer wants to see not just the
winning profile, but what else was in contention, so it can decide for itself whether a
`domain_keyword`-confidence single-candidate win is trustworthy enough to act on.

**Why this priority**: Directly requested by the issue; depends on User Story 1's dry-run
plumbing existing first, but is independently valuable on the real (Op-opening) `dispatch` path
too (FR-005).

**Independent Test**: Construct a request that matches two profiles (one via canonical verb,
one via domain keyword). Call `dispatch --dry-run --json` and assert the JSON payload's
`alternatives` array is non-empty and contains the losing candidate's `profile_id`, `action`,
`confidence`, and `match_reason`.

**Acceptance Scenarios**:

1. **Given** a request that matches exactly one profile with no competing candidates, **When**
   dry-run or real dispatch routes it, **Then** `alternatives` is present and is `[]` (an
   explicit empty list — never `null`/omitted, per the charter's silent-success prohibition).
2. **Given** a request routed via an explicit `--profile` hint, **When** dry-run or real dispatch
   runs, **Then** `router_confidence` is `"exact"` and `alternatives` is `[]` (the router never
   computes candidates on the explicit-hint path — see FR-005).
3. **Given** a request that would raise `ROUTER_AMBIGUOUS` under real dispatch, **When** the
   operator runs the same request under `--dry-run`, **Then** the command does NOT raise; it
   returns `"status": "dry_run"` with `profile_id: null`, `action: null`,
   `router_confidence: "ambiguous"`, and `alternatives` populated with every tied candidate
   (FR-009) — this is the exact UI-probing use case the issue names.

---

### User Story 3 - Router stops confidently misrouting on a single generic domain keyword (SK-08) (Priority: P3)

Per `SPEC-KITTY-LEDGER.md:2727` (SK-08, verified first-hand), `ActionRouter.route()` lets a
single generic `domain_keyword` match outrank the request's own `canonical_verb` match and
opens the real Op anyway with no warning — while a tied canonical-verb match correctly fails
closed (`ROUTER_AMBIGUOUS`). This hands the agent the wrong profile's governance directives
under a misleading "confident" label. This work package lands AFTER User Stories 1 and 2
(WP1/WP2) as its own commit, distinct from WP1/WP2's commits (WP3) — but not guaranteed to be a
conflict-free independent `git revert` target, since WP2 and WP3 both edit the single-candidate
return and the `routing_priority` tiebreaker block inside `route()` (see C-002) — because it
changes selection behavior on every real (Op-opening) dispatch call, not just the new dry-run
path.

**Why this priority**: Lower priority only in sequencing, not in importance — it is additive
work (dry-run, alternatives) that must not stall on this riskier behavioral fix, per operator
decision. See "Clarifications / Decision Records" below.

**Independent Test**: Reproduce one of the ledger's verified misroute cases (a request whose
tokens match a canonical verb for one profile AND a domain keyword for a higher-`routing_priority`
profile). Before the fix: the domain-keyword profile wins with `confidence: domain_keyword`, Op
opened. After the fix: the canonical-verb profile wins (or, if no canonical verb matched at all
and only one lone domain-keyword candidate exists, the router raises `ROUTER_AMBIGUOUS` instead
of auto-selecting it — and if no canonical verb matched at all and two or more domain-keyword
candidates exist, the router likewise raises `ROUTER_AMBIGUOUS` regardless of their
`routing_priority` spread, per FR-007's generalization, AC-4/SC-006 — instead of auto-selecting
the higher-priority candidate as it does today).

**Acceptance Scenarios**:

1. **Given** a request whose tokens match a canonical verb for profile A and a domain keyword
   for profile B, where B has a higher `routing_priority` than A, **When** `dispatch` (with or
   without `--dry-run`) routes the request, **Then** the winner is profile A with
   `confidence: "canonical_verb"`, and profile B appears in `alternatives` with
   `confidence: "domain_keyword"` — `routing_priority` no longer lets a domain-keyword candidate
   outrank a canonical-verb candidate.
2. **Given** a request whose tokens match no canonical verb for any profile, but match exactly
   one profile's domain keyword (the "lone/weak" case), **When** `dispatch` routes the request
   without `--profile`, **Then** the router raises `RouterAmbiguityError` (`ROUTER_AMBIGUOUS`,
   exit 1, no Op opened) instead of auto-selecting that profile — mirroring today's tied
   canonical-verb behavior, closing the asymmetry.
3. **Given** the same lone-domain-keyword request as above, **When** the operator supplies an
   explicit `--profile <id>`, **Then** routing succeeds exactly as before (explicit hints bypass
   the router entirely and are unaffected by this change).
4. **Given** a request whose tokens match no canonical verb for any profile, but match TWO OR
   MORE profiles' domain keywords (zero verb-tier candidates, multiple keyword-tier candidates —
   e.g. profile B at `routing_priority` 80 and profile C at `routing_priority` 10, both
   keyword-only), **When** `dispatch` routes the request without `--profile`, **Then** the router
   raises `RouterAmbiguityError` (`ROUTER_AMBIGUOUS`) regardless of the `routing_priority` spread
   between B and C — the pre-existing priority-based auto-select no longer applies once there are
   zero verb-tier candidates (FR-007).
5. **Given** `tk-watch`'s existing `TK_WATCH_PROFILE` / `--profile` pin workaround for SK-08,
   **When** this fix lands, **Then** the pin continues to work unmodified (it uses the
   explicit-hint path, untouched by this change) and becomes unnecessary as an SK-08 workaround
   specifically — but this mission does not modify `tk-watch`'s code (out of scope; see
   Clarifications).

---

### Edge Cases

- **`--dry-run` combined with `--profile`**: the explicit profile hint bypasses the router
  entirely (Level 1 in `ActionRouter.route()`). `router_confidence` is `"exact"`,
  `alternatives` is `[]`. This is identical behavior to real dispatch with `--profile`, minus
  the writes. (FR-008)
- **`--dry-run` on a request that would raise `ROUTER_AMBIGUOUS`**: does NOT raise. Returns a
  `"status": "dry_run"` payload with `profile_id: null`, `action: null`,
  `router_confidence: "ambiguous"`, `alternatives` populated with the tied candidates. This is
  the deliberate UI-probing affordance the issue asks for. (FR-009)
- **`--dry-run` on a request that would raise `ROUTER_NO_MATCH`** (zero candidates — nothing
  matched at all): DOES still raise, with the same structured error JSON as real dispatch
  (`error_code: "ROUTER_NO_MATCH"`, exit 1). There is no routing signal at all to report in this
  case; returning a `"status": "dry_run"` envelope with nothing meaningful in it would itself be
  the silent-success anti-pattern the charter forbids. (FR-009)
- **`--dry-run` with an unknown `--profile`** (`ProfileNotFoundError`): DOES still raise, same
  structured error JSON and exit 1 as real dispatch — there is no profile to describe. (FR-009)
- **`--dry-run` under an empty-charter fallback** (no charter activations found): behaves like
  real dispatch's empty-charter fallback path — `resolve_generic_fallback()` still runs (it is
  already read-only), `empty_charter_fallback: true` is still surfaced in the payload, and the
  generic-agent profile is still the reported routing signal. The one-shot rich-console warning
  (`_render_empty_charter_warning`) is a console-rendering concern outside the JSON payload
  contract and is unaffected either way. (FR-010)
- **`--dry-run` combined with a request the glossary chokepoint flags as a high-severity term
  conflict**: `glossary_observations.high_severity` is still populated in the dry-run payload
  (the scan itself is read-only and safe to run) — only the persisted `TermCandidateObserved`
  event write is suppressed. (FR-003)

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | `--dry-run` flag on `dispatch` | As an external UI/automation consumer, I want a `--dry-run` flag on `spec-kitty dispatch` so that I can query the routing signal without opening governance history. | High | Open |
| FR-002 | Dry-run suppresses every write on the invoke path | As an operator, I want `--dry-run` to write absolutely nothing so that repeated probing never litters `kitty-ops/` or the glossary trail. | High | Open |
| FR-003 | Dry-run passes a falsy `invocation_id` into the glossary chokepoint scan | As an operator, I want the chokepoint's `TermCandidateObserved` write gate (already present, keyed on truthy `invocation_id`) to actually engage under dry-run, so the non-obvious existing write path is closed, not merely the visible Op write. | High | Open |
| FR-004 | Dry-run JSON payload shape | As a consumer, I want a `"status": "dry_run"` payload reusing the existing `InvocationPayload` field set (minus `invocation_id` and `close_contract`) so the shape is familiar and the "nothing was opened" property is unambiguous. | High | Open |
| FR-005 | `alternatives` field on `RouterDecision`, threaded to both dry-run and real dispatch payloads | As a consumer, I want the router's already-computed candidate list exposed (minus the winner) on every successful route — dry-run or real — so I can judge routing confidence myself. | High | Open |
| FR-006 | SK-08 rerank: canonical-verb candidates outrank domain-keyword-only candidates | As an agent relying on `dispatch` for governance context, I want a canonical-verb match to always beat a domain-keyword match regardless of `routing_priority`, so the profile whose directives I load actually matches the request's own verb. "Regardless of `routing_priority`" applies only cross-tier (a canonical-verb candidate beats a domain-keyword candidate no matter their `routing_priority` values). `routing_priority` continues to break ties WITHIN the canonical-verb tier ONLY — between two canonical-verb candidates — unchanged from today's behavior; it is only removed as a way for a domain-keyword candidate to outrank a canonical-verb one. `routing_priority` does **not** survive as a tiebreaker between two-or-more domain-keyword-tier candidates considered in isolation (i.e. when zero verb-tier candidates are present): that scenario is governed exclusively by FR-007 — see FR-007, AC-4 (User Story 3), and SC-006 — which requires `ROUTER_AMBIGUOUS` regardless of the `routing_priority` spread among those keyword-tier candidates. `tests/specify_cli/invocation/test_router.py::test_router_priority_tiebreaker_selects_higher_priority` (a canonical-verb-vs-canonical-verb priority tiebreak) must keep passing unmodified. | High | Open |
| FR-007 | SK-08 rerank: a lone/weak domain-keyword-only match is ambiguous, not confident | As an agent, I want a single unopposed domain-keyword hit to fail closed (`ROUTER_AMBIGUOUS`) like a tied canonical-verb match does today, instead of silently opening an Op under the wrong profile. This generalizes beyond the single-candidate case: whenever zero verb-tier candidates exist, the router MUST raise `ROUTER_AMBIGUOUS` regardless of how many domain-keyword-tier candidates there are or how their `routing_priority` values compare — a priority spread among keyword-tier-only candidates is exactly the kind of unconfident, canonical-verb-unbacked resolution this requirement exists to close, so the existing priority-based auto-select no longer applies once there are zero verb-tier candidates. See FR-006, which scopes the surviving intra-tier `routing_priority` tiebreak to canonical-verb-vs-canonical-verb candidates only — FR-006's tiebreak does NOT extend to the keyword-tier-only candidates this requirement governs. Also see AC-4 (User Story 3) and SC-006 for the concrete 2+-keyword-tier-candidates test obligation. | High | Open |
| FR-008 | `--dry-run --profile` interaction | As a consumer combining an explicit profile hint with `--dry-run`, I want `router_confidence: "exact"` and `alternatives: []`, matching real dispatch's explicit-hint behavior minus the writes. | Medium | Open |
| FR-009 | Dry-run error-path behavior (`ROUTER_AMBIGUOUS` vs `ROUTER_NO_MATCH` / `ProfileNotFoundError`) | As a consumer, I want `--dry-run` to turn `ROUTER_AMBIGUOUS` into a reportable `"status": "dry_run"` payload (candidates as `alternatives`, no winner) since that is exactly the ambiguity-probing signal the issue asks for, while `ROUTER_NO_MATCH` and `ProfileNotFoundError` continue to raise/exit 1 as today, since there is no partial signal worth reporting in those cases. The candidate dicts `route()` raises inside `RouterAmbiguityError` for `ROUTER_AMBIGUOUS` must also carry a `confidence`/`_confidence` key — sourced the same way the winning-candidate dicts already are elsewhere in `route()` — so `alternatives` can be built from `err.candidates` on this branch without omitting the `confidence` field the Key Entities contract requires on every entry. **This obligation is not scoped to the one `ROUTER_AMBIGUOUS` raise site that exists in `route()` today (the post-tiebreaker "still ambiguous" raise): it applies to EVERY `RouterAmbiguityError` raised anywhere in `route()` for `ROUTER_AMBIGUOUS`, including any new or restructured raise sites WP3 (FR-006/FR-007) introduces for the lone-candidate case (AC-2) and the 2+-keyword-tier-candidates case (AC-4).** This is a shared-contract point between WP1 and WP3: WP1 lands first and can only fix the raise site that exists at WP1 time (the post-tiebreaker raise); WP3, landing after WP1, inherits the same confidence-key obligation for whatever new `ROUTER_AMBIGUOUS` raise(s) its restructuring of `route()` introduces — a WP3 implementation must not reintroduce the pre-FR-009 candidate-dict shape (`profile_id`/`action`/`match_reason` only) on its own raise sites. | High | Open |
| FR-010 | Dry-run under empty-charter fallback | As a consumer probing an unconfigured project, I want dry-run to surface `empty_charter_fallback: true` and the generic-agent routing signal, exactly mirroring real dispatch's read-only fallback path. | Medium | Open |
| FR-011 | `cli-do-output.md` contract doc updated with the `dry_run` status branch | As a future contributor reading the JSON-output contract, I want the `--dry-run` shape and the new `alternatives` field documented alongside the existing `"status": "open"` branch. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Dry-run adds no meaningful latency over real dispatch | `--dry-run`'s wall-clock cost is dominated by the same governance-context computation real dispatch already performs (`build_charter_context(..., mark_loaded=False)`, already read-only) — omitting the Op/glossary-trail writes and SaaS propagation submit can only make dry-run *faster* than real dispatch, never slower. No new caching layer is introduced or required by this mission. | Performance | Medium | Open |
| NFR-002 | Dry-run has no lock/flock semantics to release | The invoke path acquires no lock/flock anywhere (writes are plain atomic appends) — dry-run therefore has no lock-release edge case to specify. Stated explicitly so this is read as "considered and absent," not "unconsidered." | Reliability | Low | Open |
| NFR-003 | No production-deploy / Human-in-Charge approval step | Every step on the dry-run and real dispatch paths is local filesystem read/computation (or, for the real path, local filesystem writes and a best-effort background SaaS submit) — no deploy, no irreversible external action requiring HITL approval. | Governance | Low | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | ATDD-first per work package (charter C-011, binding) | Each of WP1 (dry-run + payload shape), WP2 (`alternatives`), and WP3 (SK-08 rerank) requires its own failing-first test pinning user-observable behavior (e.g. "no new file under `kitty-ops/` after a `--dry-run` call," "no new line appended to any `kitty-ops/*.jsonl`," "canonical-verb candidate wins regardless of `routing_priority`"), committed as its own commit BEFORE the implementation commit for that WP. | Process | High | Open |
| C-002 | WP3 lands as its own commit, distinct from WP1/WP2 | The SK-08 rerank (FR-006/FR-007) must land as its own commit/diff boundary, distinct from the additive dry-run and `alternatives` work, per operator decision. This is NOT guaranteed to be a conflict-free `git revert <wp3-sha>` target independent of WP2: WP2 (FR-005, `alternatives`) and WP3 (FR-006/FR-007, the rerank) both edit the same statements inside `route()` — the `if len(candidates) == 1:` single-candidate return and the `routing_priority` tiebreaker block — so reverting WP3 alone may require reverting or hand-resolving WP2's `alternatives` edits to those same lines. The achievable property is "own commit, auditable and cherry-pickable in isolation," not "independently, cleanly revertible regardless of WP2." **WP1/WP3 shared-contract note**: WP3's restructuring of `route()` also creates new/restructured `RouterAmbiguityError` raise sites (the lone-candidate case, AC-2, and the 2+-keyword-tier-candidates case, AC-4) that did not exist when WP1 fixed the confidence-key gap on the one raise site current code has — see FR-009's amendment for the resulting obligation on WP3's own raise sites. | Technical | High | Open |
| C-003 | No `contract_version`/semver envelope discipline in this mission | `dispatch`'s JSON payload has never carried a `contract_version` field; this mission does not introduce one. That unification effort belongs to orchestrator-api's separate, larger contract-versioning work and is explicitly out of scope here. | Technical | Medium | Open |
| C-004 | `tk-watch`'s `--profile` pin is out of scope to modify | `tk-watch`'s existing `TK_WATCH_PROFILE`/`--profile` pin workaround (`~/.hermes/skills/tk-watch/references/remediation-brief.md`) is a related but out-of-scope caller. This mission does not touch `tk-watch`'s code; FR-006/FR-007 make the pin unnecessary as an SK-08 workaround specifically, but the pin remains functionally correct and is left in place. | Business | Medium | Open |
| C-005 | Bulk-edit / occurrence-classification gate does not apply | This mission does not rename or migrate any existing identifier, path, or key across the codebase — it adds a flag, a field, and a selection-rule fix. No bulk-edit occurrence classification is triggered. | Technical | Low | Open |
| C-006 | C-007 (`__all__`/frozen-public-surface discipline) does not bind this mission's touched files | C-007 is binding on `src/charter/` and `src/kernel/`. This mission's changes are confined to `specify_cli.invocation` / `glossary` / the CLI command layer — outside those seams — so reviewers should not expect `__all__` updates here. | Technical | Low | Open |
| C-007 | External contract packages remain non-vendored | `spec-kitty-events` and `spec-kitty-tracker` are true external PyPI dependencies. Any blast-radius note touching the glossary-events machinery (`emit_term_candidate_observed`) must not imply these packages are vendored/editable in this repo. | Technical | Medium | Open |
| C-008 | Pre-existing red tests are tracked separately | `main` carries known-red tests, already tracked as issue #3284. This mission's test-baselining notes cite #3284 and do not imply a new issue is needed for pre-existing failures unrelated to this work. | Process | Low | Open |

### Key Entities

- **`RouterDecision`** (`src/specify_cli/invocation/router.py`): gains a new `alternatives:
  list[dict[str, str]]` field. Each entry carries `profile_id`, `action`, `confidence`, and
  `match_reason` for a candidate that was considered but did not win. Always present, always a
  list (possibly empty) — never `None`.
- **Dry-run response envelope**: the JSON object returned by `dispatch --dry-run --json`. Reuses
  `InvocationPayload`'s field set minus `invocation_id` and `close_contract`, plus a terminal
  `"status": "dry_run"` value and the new `alternatives` field. On the `ROUTER_AMBIGUOUS`
  dry-run branch, `profile_id`/`action` are `null` and `router_confidence` is `"ambiguous"`.
- **Candidate** (informal, internal to `router.py`): the existing `dict` shape (`profile_id`,
  `action`, `match_reason`, `_confidence`) already built by `route()`'s verb-match and
  keyword-match passes. This mission threads a public-facing view of this list out through
  `alternatives` instead of discarding all but the winner.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A consumer can call `spec-kitty dispatch "<request>" --dry-run --json` any number
  of times against the same checkout without ever creating or modifying a file under `kitty-ops/`
  — verified by an automated test that snapshots the directory tree and `ops-index.jsonl` line
  count before and after N dry-run calls and asserts byte-identical state.
- **SC-002**: A consumer can call dry-run on a request whose tokens are unrecognized by the
  glossary index without a new `TermCandidateObserved` event being persisted — verified the same
  way as SC-001, by directory-level snapshot rather than a named-file line count: the glossary
  event log path is keyed on `invocation_id`
  (`.kittify/events/glossary/profile-invocation-<invocation_id>.events.jsonl`, per
  `chokepoint.py`'s `_build_event_context` and `events.py`'s `get_event_log_path`), and
  `executor.py` mints a fresh ULID on every `invoke()` call — dry-run included — so a regressed
  write would land in a brand-new, uniquely-named file, never increment an existing file's line
  count. The test MUST assert that the set of files under `.kittify/events/glossary/` (by name,
  or by total file count when the directory is empty at test start) is unchanged before and after
  N dry-run calls — i.e. "no new file is created under `.kittify/events/glossary/`" — not that
  any single named file's line count is unchanged. This explicitly includes the case where
  `.kittify/events/glossary/` does not exist at all, either before or after the N calls — the
  common case in a clean checkout, since `events.py`'s `get_event_log_path` only calls
  `mkdir(parents=True, exist_ok=True)` on an attempted write, and a correctly-suppressed dry-run
  never calls it. The test must treat "directory absent" and "directory present but empty" as
  equivalent unchanged states, not require a `FileNotFoundError` to be handled separately from an
  empty `listdir()` result.
- **SC-003**: On a request matching two or more candidate profiles, both dry-run and real
  dispatch return a non-empty `alternatives` list containing every non-winning candidate's
  `profile_id`, `action`, `confidence`, and `match_reason`.
- **SC-004**: On the SK-08 reproduction case (canonical-verb match for profile A, domain-keyword
  match for a higher-`routing_priority` profile B), `dispatch` (real or dry-run) selects profile
  A, not profile B — verified by a regression test built from one of the ledger's documented
  probe requests.
- **SC-005**: On a lone/weak domain-keyword-only match with no competing canonical-verb match,
  real `dispatch` (without `--profile`) exits 1 with `error_code: "ROUTER_AMBIGUOUS"` and opens
  no Op — verified by an automated test asserting no new `kitty-ops/` file appears after the
  call.
- **SC-006**: On a request with zero verb-tier candidates and two or more domain-keyword-tier
  candidates at different `routing_priority` values, real `dispatch` (without `--profile`) exits
  1 with `error_code: "ROUTER_AMBIGUOUS"` and opens no Op, regardless of the `routing_priority`
  spread between the candidates — verified by an automated test asserting no new `kitty-ops/`
  file appears after the call (mirrors SC-005 for FR-007's generalized zero-verb-tier,
  2+-keyword-tier-candidates case, AC-4).

## Clarifications / Decision Records

These decisions were made by the operator before mission scaffolding and are recorded here as
settled — not open questions for the review squad or a future reader to re-litigate.

1. **SK-08 rerank is in scope, landing as WP3, after WP1/WP2.** Rationale: the additive,
   lower-risk dry-run + `alternatives` work must not stall on the riskier behavioral fix to
   `ActionRouter.route()`'s selection logic — a fix that changes every real (Op-opening)
   dispatch call, not just the new dry-run path. WP3 lands as its own commit, distinct from
   WP1/WP2's commits — but is not guaranteed to be a conflict-free independent `git revert`
   target, since it shares touch points inside `route()` with WP2's `alternatives` work (C-002).
2. **`alternatives` ships in v1, on both the dry-run and the real dispatch success path** —
   not deferred, and not restricted to dry-run only. The router already computes the full
   candidate list internally (`candidates`/`sorted_candidates`/`top_candidates` in
   `router.py`'s `route()`) before discarding all but the winner; exposing it is threading an
   already-computed list out through a new field, additive on both paths. Decision, stated
   explicitly per the brief's request: restricting `alternatives` to dry-run-only would add
   branching complexity in `InvocationPayload`/`RouterDecision` for no benefit — the field is
   equally useful for a consumer inspecting a real dispatch's confidence after the fact.
3. **Naming: `--dry-run` flag on the existing `dispatch` command, not a `route-only` flag or a
   `dispatch route` subcommand.** Matches the repo's established convention
   (`agent_retrospect.py`'s `--dry-run`/`--apply` pattern, `_cutover_doctor.py`'s
   `dry_run=True` "writes nothing" convention). Output shape reuses `InvocationPayload`'s
   existing JSON shape with a new terminal `"status": "dry_run"` value (mirroring the existing
   `"status": "open"` pattern), dropping `close_contract` (nothing to close). No
   `contract_version`/semver envelope discipline is introduced (C-003) — that is
   orchestrator-api's separate, larger unification effort.
4. **`tk-watch`'s `TK_WATCH_PROFILE`/`--profile` pin workaround is a related but out-of-scope
   caller** (C-004). It continues to function unmodified after this mission (it uses the
   explicit-hint router path, which SK-08's fix does not touch), and becomes unnecessary as an
   SK-08-specific workaround once FR-006/FR-007 land — but this mission does not edit
   `tk-watch`'s code.
5. **In-mission auto-routed (no `--profile`) `dispatch` calls are exposed to a
   routing-consistency risk when WP3 lands mid-mission, and this is accepted.** `route()` is a
   pure, stateless function re-evaluated on every call; a spec-kitty mission whose WP subagents
   dispatch across the span of time during which WP3 merges to main could see two auto-routed
   calls for similar request text resolve to different profiles before and after the rerank
   lands. This is accepted as inherent to any bug fix to `router.py`'s selection logic — not
   novel to this mission — and is not mitigated further here (e.g. no mid-mission routing-version
   pin is introduced); a caller wanting a stable profile across a mission's lifetime should pass
   an explicit `--profile` hint, which this fix does not affect.

## Blast Radius / Files Touched *(informative — for the plan phase)*

Implementation files:

- `src/specify_cli/cli/commands/dispatch.py` — new `--dry-run` flag, dry-run-branch JSON
  rendering, error-path routing for FR-009.
- `src/specify_cli/invocation/executor.py` — new dry-run code path on `ProfileInvocationExecutor`
  (or a sibling method) that skips `write_started`/`write_glossary_observation`/
  `propagator.submit`, and passes a falsy `invocation_id` into `GlossaryChokepoint.run()`.
- `src/glossary/chokepoint.py` — no behavior change required (the `if not invocation_id: return
  None` gate in `_build_event_context` already exists); verify/pin this behavior with a test.
- `src/specify_cli/invocation/router.py` — `RouterDecision.alternatives` field; SK-08 selection
  rerank inside `route()`.
- `src/specify_cli/invocation/errors.py` — `RouterAmbiguityError`'s candidate dicts (currently
  `profile_id`/`action`/`match_reason` only, built in `route()`'s `ROUTER_AMBIGUOUS` raise) must
  also carry a confidence key (see FR-009 amendment above), so the dry-run ROUTER_AMBIGUOUS
  branch can populate `alternatives` from `err.candidates` without a schema mismatch against the
  Key Entities `alternatives` contract.
- `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md` — existing
  JSON-output contract doc for `dispatch`; add the `status: "dry_run"` branch and the
  `alternatives` field on the existing `"status": "open"` example.

Test files:

- `tests/specify_cli/invocation/test_router.py` — SK-08 rerank cases, `alternatives` field
  assertions. `test_router_priority_tiebreaker_selects_higher_priority` (the existing
  canonical-verb-vs-canonical-verb intra-tier priority tiebreak) must continue to pass
  unmodified — see FR-006.
- `tests/specify_cli/invocation/cli/test_dispatch.py` — `--dry-run` CLI-level tests, including
  the "no new file under `kitty-ops/`" and "no new glossary event" assertions.
- `tests/invocation/test_dispatch_recommendation.py` — verify the advisory model-routing
  recommendation still populates under `--dry-run` (it is already read-only).

No kernel/doctrine seam is touched — see Constraint C-006.
