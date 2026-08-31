# Research: Charter Delivery Finish and Context Degod

**Phase 0 output.** Two profile-loaded research passes (architect-alphonso — WS3 decomposition map; paula-patterns — WS1 seam + blast radius), each grounded in `spec-kitty_TWO` HEAD and re-verified by the orchestrator. Builds on [notes/post-spec-squad-findings.md](notes/post-spec-squad-findings.md).

---

## Decision 1 — WS2/#3082: normalize the `when` clause into the closed contract set

- **Decision**: Normalize each authored `when` clause in the single choke-point `context_renderers/fetch_stanza.py:133` (`fetch_stanza_lines`) so the emitted line is grammatical **and** headed by one of the closed `_WHEN_DOING_RE` lead-ins. Assert per-stanza (not whole-prompt `.search()`).
- **Rationale**: `_WHEN_DOING_RE = when you (are about to|need to|encounter|introduce|rename|review)` (verified `test_wp_prompt_governance_contract.py:221`) is a **closed 6-verb set**. Authored clauses are frequently gerund phrases ("designing or reviewing …") or full sentences (`STATED_DEFAULT_WHEN`). A grammatical-but-non-matching rewrite (`When you are designing…`) silently breaks the contract. Mapping the clause to a verb-led form the set accepts (default anchor: the existing `DEFAULT_WHEN_CLAUSE = "are about to apply a code change"`) satisfies both.
- **Default chosen**: **Map/normalize, do not widen the regex.** Widening `_WHEN_DOING_RE` is a wire-contract change (kept in sync with `charter-context-resolver.md`) — reserved for a clause that genuinely cannot be mapped, decided explicitly at tasks.
- **Alternatives considered**: (a) widen the regex to accept gerunds — rejected as default: expands the contract surface for a prose nit; (b) strip the `When you` prefix when the clause is a full sentence — rejected: breaks the `_WHEN_DOING_RE` anchor.

## Decision 2 — WS1/#3064 seam: executor auto-route pre-check, NOT the shared gate or ProfileRegistry

- **Decision**: Add `src/specify_cli/invocation/empty_charter.py::resolve_generic_fallback(repo_root, request_text)` and call it at the **executor auto-route branch** `invocation/executor.py:255-259` (the `elif self._router is not None:` / no-profile-hint path): `result = resolve_generic_fallback(...) or self._router.route(request_text)`.
- **Rationale**: The "all built-ins" behaviour is the shared three-state gate in `charter/resolver.py` (via `doctrine_service_factory.py:38-86`), consumed by routing **and** `build_charter_context`. Mutating it (or gutting `ProfileRegistry._build_merged_profiles`) has a blast radius across `profiles list`, `--include`, the `agent workflow` schema resolve (`agent/workflow.py:1047`), and **breaks explicit `--profile <specialist>` under an empty charter**. The auto-route branch is the *only* place the "no hint" dispatch signal exists, so the override is surgical.
- **Consequence (de-risking)**: the shared gate, `ProfileRegistry`, and every gate/parity fixture stay **untouched** — no re-baseline. `test_no_activation_key_admits_all_builtins_in_routing` stays green as the "gate untouched" proof.
- **Alternatives considered**: (a) pre-check in `ProfileRegistry` — rejected: over-reaches, breaks explicit-profile dispatch + workflow resolve; (b) mutate the three-state gate — rejected: cross-subsystem blast radius, re-resolves governance context for every consumer.

## Decision 3 — WS1 predicate is COMPOSITE across ALL charter-activatable dimensions (post-plan correction)

- **Decision**: empty-charter ⇔ **all** of:
  `charter_activated_urns(repo_root) == ∅` (covers the 6 URN kinds: directives/tactics/toolguides/procedures/paradigms/styleguides)
  **AND** `PackContext.from_config(repo_root)` has `activated_agent_profiles is None` **AND** `activated_mission_step_contracts is None` **AND** `activated_glossary_packs is None`
  **AND** `PackContext.org_roots == ()` (no org/project packs).
- **Rationale**: `charter_activated_urns()` (`pack_context.py:496`) is restricted to 6 URN kinds via `_ACTIVATION_URN_KINDS` and **excludes** the other charter-activatable dimensions. `PackContext` carries three-state `activated_agent_profiles`, `activated_mission_step_contracts`, `activated_glossary_packs` (`pack_context.py:167-176`), and `glossary-pack` + `mission-step-contract` **are** charter-activatable (`CHARTER_KIND_TOKENS`, `artifact_kinds.py`). `anti_pattern` is NOT charter-activatable (excluded with template/asset) — omit it. A repo that activated only a glossary-pack (or step-contract, or an org pack) would otherwise satisfy the naive predicate and false-fallback to generic-agent with a wrong "unconfigured" warning on a demonstrably configured repo. Decision 3's meaning — "the operator activated nothing at all" — requires all dimensions.
- **Truth-table cases the WP test MUST cover**: nothing activated → fallback; URN-only / profile-only / glossary-pack-only / step-contract-only / org-pack-present → NO fallback.
- **Alternatives considered**: single-authority `charter_activated_urns()==∅` — rejected (misfires on 3 dimensions + org packs); re-enumerating raw `activated_*` keys — rejected (divergent "empty" definition).

## Decision 4 — WS1 governance context does NOT agree for free; the empty-charter path must scope the governance block (post-plan CORRECTION)

- **Decision**: US1 scope includes a **governance-context adjustment** on the empty-charter/generic-agent path — the dispatch governance block must NOT merge the project catalog-fallback directives. Add a **red-first** agreement test that asserts the `Directive IDs:` block is empty/generic-agent-scoped.
- **Rationale (retracts the earlier "agrees by construction")**: `_render_compact_governance` → `render_compact_view` (`compact.py:216-230`) MERGES `resolver_directives` from `_resolve_governance_summary(repo_root)` into the `Directive IDs:` block, **independent of the profile**. Under a wholly-empty charter, `resolve_project_governance` → `_resolve_directives_selection` (`resolver.py:233-260`) has empty `doctrine.selected_directives`, so it returns `fallback = sorted(doctrine_catalog.directives)` — **the full built-in directive canon** (`catalog_fallback`). So an unadjusted generic-agent dispatch would emit every built-in `DIR-###` in its governance block — a doctrine leak contradicting C-003/SC-001. This is the split-brain the first squad warned of, proven real.
- **Implementation options (bounded, no shared-gate mutation)**: (a) preferred — when `empty_charter_fallback` fired, the executor resolves governance in a mode that suppresses the resolver-directive merge (e.g. a `build_charter_context(..., suppress_project_resolver=True)` param or a dedicated minimal-governance render for the fallback), leaving `render_compact_view` untouched for all other callers; (b) alternative — a scoped render helper for the fallback path. Do NOT change `_resolve_directives_selection`'s catalog-fallback globally (broad blast radius across every compact-context consumer).
- **Test (new, red-first)**: dispatch under a wholly-empty charter; assert `payload.profile_id == "generic-agent"`, the governance `Directive IDs:` block is empty (or exactly generic-agent's own cited directives), no specialist marker, and `empty_charter_fallback is True`. The test is RED before the governance scoping lands.

## Decision 5 — WS1 warning surface

- **Decision**: Emit once in `cli/commands/dispatch.py::_render_rich_payload` (lines 59-91), gated on a new explicit `InvocationPayload.empty_charter_fallback: bool` flag (added to `__slots__`/annotations `executor.py:139-163`, serialized in `to_dict` for `--json`). Rich callers get a yellow panel; `--json` callers get the boolean.
- **Rationale**: The router (pure, ADR-3 no-I/O) and registry must not print. Keying on `payload.profile_id == "generic-agent"` alone would false-warn a deliberate `--profile generic-agent` on a configured charter; the dedicated flag prevents that.

## Decision 6 — WS1 default charter asset (FR-005)

- **Decision**: Ship `src/doctrine/assets/built-in/charter_scaffold_minimal.yml` + sidecar `charter_scaffold_minimal.yml.asset.yaml` (**`id: common-charter-scaffold-minimal`** — deliberately NOT "default-charter", to avoid colliding with `src/charter/packs/default.yaml`; `mime: application/yaml`, `path: built-in/charter_scaffold_minimal.yml`, `title: Minimal charter scaffold`); resolvable via `spec-kitty doctrine asset path common-charter-scaffold-minimal` (resolve/copy-only, no install). Content = a **minimal curated starter** charter, NOT a copy of `packs/default.yaml`. Add a one-line cross-reference comment in each of the two files pointing at the other so a later agent does not "consolidate" them.
- **Rationale**: `packs/default.yaml` activates **all** built-ins across 9 kinds — the semantic inverse of "empty"; naming a second asset "default charter" invites drift. A minimal curated starter matches the user intent ("forego authoring, get a sane baseline"). Declare `mime: application/yaml`; `mimetypes.guess_type('x.yml')` already returns `application/yaml` on this repo's Python 3.11, so the sidecar passes `_check_asset_mime` today — the `pack_validator` regression is a **guard**, not a 3.13-forward fix (earlier rationale corrected).
- **Activatability (post-plan)**: FR-005's done-line is not just resolvability — a test must **activate** the shipped scaffold in a temp repo and assert the resulting charter validates (non-empty, activatable) without touching any pre-existing user charter.
- **OPEN DECISION for operator visibility (non-blocking)**: minimal-curated-starter is the chosen default; if the operator prefers the asset to point at `packs/default.yaml` (activate-all), that is a one-line content swap.

## Decision 7 — WS3 decomposition: continue `context_renderers/`, consolidate, dissolve the cycle

- **Decision**: Decompose `context.py` (3243 LOC) into the seams mapped in [data-model.md](data-model.md), continuing the existing `context_renderers/` package; **consolidate** into `token_budget.py`, `section_bodies.py`, `reference_pointers.py`, `profile_sections.py`, `fetch_stanza.py`, `delivery_table.py` where a partial home exists; mint new siblings only for genuinely new seams. Residual ceiling **`context.py` ≤ 500 LOC (stretch 400)**.
- **Cycle dissolution (verified one-directional)**: `profile_sections.py:160-165` function-locally imports 4 symbols from `charter.context`. Pin them to LEAF homes — `_budget_estimate` + `_PROFILE_INLINE_BODY_LIMIT_CHARS` → `token_budget.py`; `_render_fetch_stanza` → fold into `fetch_stanza.py`; `_diagnose_catalog_miss` (+ `_available_catalog_ids`) → new leaf `catalog_diagnosis.py` (deps: `charter._catalog_miss` only). `profile_sections.py` then imports all four at top level; both `noqa: PLC0415` deleted. No back-edge into `context.py`.
- **FR-009 preserve surface (verified)**: **zero** production/`src` callers import private symbols from `charter.context` — the entire private surface (~40 symbols incl. the 4-test anchor `_reset_agent_profile_cache`) is **test-only**. Keep one explicit `# FR-009 preserved surface` re-export block in `context.py` (lowest-regression; ~55 LOC). Optionally migrate pure-seam tests to import from new homes later (follow-up, not a completion gate).
- **Extraction sequence (low-risk → high-risk)**: (1) `catalog_diagnosis` → (2) `token_budget` consolidate → (3) `fetch_stanza` consolidate → (4) `artifact_bodies` → (5) `charter_md_parsing` + `reference_pointers` consolidate → (6) `context_state` → (7) `template_include` → (8) `selection_block` → (9) `activation_block` → (10) `compact_governance` + `bootstrap_text` → (11) `context_json` → (12) `org_pack_discovery` + `action_doctrine_bundle` → (13) `profile_resolution` + `doctrine_service_builder` **LAST** (carries the US1-mutated activation-wrapper region + the profile caches).

## Decision 8 — Load-bearing sequencing (US1 ∩ US3)

- **Decision**: US2 (#3082) and US1 (#3064) land first; the US3 byte-parity baseline is (re)captured **only after** both merge; US3 extraction lands last, and the `doctrine_service_builder`/`profile_resolution` seams (the `_build_activation_aware_doctrine_service` region `context.py:~1550-1566` that US1 touches) are extracted last of all, against a frozen wrapper.
- **Rationale**: US1 changes `build_charter_context`'s output for an empty-charter input; capturing the US3 parity golden before US1 merges would freeze stale bytes and collide. Confirmed the *real* collision is US1∩US3 (not US2∩US3 — US2's fix is in the already-extracted `fetch_stanza.py`, which US3 doesn't structurally move beyond consolidating the thin wrapper).

## Decision 9 — Residual-LOC ceiling + WIRED completion test (post-plan tightening)

- **Decision**: Wire a dedicated completion test `tests/charter/test_context_decomposition_completion.py` (owned by the last US3 WP) asserting **both**: (1) `wc -l src/charter/context.py ≤ 600` (the HARD gate), and (2) each named seam module in a manifest **exists** AND is imported by ≥1 non-`context` caller (imported *from the seam*, not only re-exported through `context.py`). The **seam-existence manifest is the primary, un-fakeable completion signal**; the LOC gate is secondary.
- **Ceiling rationale (grounded)**: python-pedro measured the irreducible STAY weight — 3 orchestrators ≈ 372 LOC + module preamble/`CharterContextResult`/`BOOTSTRAP_ACTIONS` ≈ 35 + import block (grows with ~17 seam imports) ≈ 70 + FR-009 re-export shim ≈ 55 ⇒ realistic floor **≈ 500–540**. A `≤600` HARD gate clears that floor with margin (still proves ~80% reduction from 3243) and avoids a self-inflicted red; **`≤500` becomes the aspirational stretch**, and the earlier `400` stretch is **dropped as unrealistic**. If the implementer cannot reach `≤600`, that is a BLOCKER requiring explicit operator re-sign-off — NOT an implementer-side ceiling adjustment (closes the "re-negotiable prose" fakeability the squad flagged).
- **Rationale**: the gates already green on the monolith (`__all__`, zero `specify_cli` imports, byte-parity on a no-op) are regression guards, not completion signals; the LOC gate + seam-existence manifest is the non-fakeable completion signal.

---

## Decision 10 — Sequencing enforced by task dependency + baseline provenance (post-plan)

- **Decision**: Because all three workstreams land in ONE mission (no inter-workstream merge), the "US3 baseline captured after US1+US2" rule is enforced as an explicit `/tasks` **WP dependency edge** — the parity-baseline-capture WP depends on the US1 (empty-charter) and US2 (prose) WPs being **approved** — and the captured baseline **must include the empty-charter input** producing the generic-agent/no-doctrine-block output (proving it was generated post-US1). The `profile_resolution`/`doctrine_service_builder` seams (the US1-frozen `_build_activation_aware_doctrine_service` region) extract in the **last** US3 WP.

## Decision 11 — `empty_charter_fallback` payload default (post-plan, pedro)

- **Decision**: `InvocationPayload.__init__(**kwargs)` only sets provided keys and `to_dict` does `getattr(self, s, None)` — so always thread `empty_charter_fallback=<bool>` at the single construction site (`executor.py:~336-348`), and have `dispatch.py::_render_rich_payload` read via `getattr(payload, "empty_charter_fallback", False)`. Otherwise existing payload-constructing tests emit `null` in `--json` and the rich path `AttributeError`s.

## Decision 12 — cycle-dissolution placement guardrail (post-plan, pedro)

- **Decision**: `fetch_stanza.py` receives ONLY the pure stanza renderer (`_render_fetch_stanza` → fold into `fetch_stanza_lines`). `_budget_estimate` + `_PROFILE_INLINE_BODY_LIMIT_CHARS` go to `token_budget.py` (which already imports `fetch_stanza`). Do NOT co-locate the budget gate into `fetch_stanza.py` — that would form `fetch_stanza → token_budget → fetch_stanza`. `_build_doctrine_service` and `_maybe_build_doctrine_service` each need their own `import doctrine.service as _doctrine_service_module` in their new homes.

## Tracker-hygiene carry-forwards (from squad, actioned at tasks)

- **#2399 (P1)** — "Structurally enforce agent-profile loading across all invocation contexts" — is adjacent: this mission adds a new dispatch-invocation resolution branch (generic-agent fallback). Note #2399 so its future enforcement does not treat the empty-charter generic-agent route as a violation. (No foldable dup; #371/#1049 are model-scoring routing, #1278 is doctrine content.)

- Enumerate the issue-matrix rows for #3082/#3064/#2532 at tasks; verify survival of `finalize-tasks`.
- `#2532` declares `Epic: #2173` in its body; planner-priti notes it is labelled tech-debt/tidy-up and behaviour-preserving (arguably `#2519`). **Honour the issue author's `#2173`**; note the tension, do not force-relink.
- `#3082` carries no priority/type label — add one at tasks for dashboard/matrix consistency.
- Optional rename of `test_no_activation_key_admits_all_builtins_in_routing` is unnecessary under the chosen seam (it stays semantically correct — the gate does still admit all built-ins; only *auto-route dispatch* overrides).
