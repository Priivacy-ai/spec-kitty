# Issue matrix — unify-charter-activation-surfaces-01KX5SJ9

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2526 | Unify charter activation surfaces (Slice 0 / epic foundation) | fixed | This mission: config is the single activation authority; references/graph derive from it; parity guard fails closed. All 11 FR/NFR pass (acceptance-matrix.json). |
| #2524 | `test_no_new_charter_reference_danglers` broke — activated artefact dangles | fixed | WP03 `tests/charter/test_activate_resolves_no_answers_edit.py` — activate resolves with no answers edit; dangler baseline shrunk to empty. |
| #2380 | Shrink-only dangler baseline should reach empty | fixed | WP03 `PRE_EXISTING_DANGLING_BASELINE = frozenset()`; the 3 baseline danglers now resolve (config-sourced superset + direct roots). |
| #2519 | EPIC: charter authoring lifecycle | deferred-with-followup | This mission is Slice 0 (the de-conflicting foundation). Epic stays open; children #2520/#2521/#2522 remain. |
| #2522 | Child C — `charter author` scaffold command | deferred-with-followup | Explicit Out of Scope; unblocked by this slice (config is now the single write-side authority). Next epic child. |
| #2521 | Child B — harness-freshness preflight / deterministic intake | deferred-with-followup | Explicit Out of Scope; unblocked by this slice. Next epic child. |
| #2520 | Child A — emit CharterCreated/CharterUpdated events | deferred-with-followup | Explicit Out of Scope; unblocked by this slice. Next epic child. |
| #2468 | Make `mission-type` an activatable kind | deferred-with-followup | Explicit Out of Scope; `MissionTypeNotAnArtifactKind` is deliberate. Tracked under epic #2466. |
| #2466 | EPIC: mission-types-as-doctrine | deferred-with-followup | Out of Scope for this mission; referenced only to bound scope. Remains open. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

## Deferred follow-ups discovered during this mission (file at close)

- **Lynn-Cole interview alias dead code**: `apply_doctrine_intent_aliases` still mutates the interview, but activation no longer reads it — now dead-effect. Remove or re-wire.
- **`synthesis-manifest.yaml` test-isolation leak**: charter/CLI test runs regenerate `.kittify/charter/synthesis-manifest.yaml` into the repo tree (restored via `git restore` throughout this mission). Isolate to a tmp dir.
- **move-task sync-daemon hang** — FIXED (folded in): the status fan-out (`fire_saas_fanout` / `fire_lifecycle_saas_fanout`) caught per-handler exceptions but not hangs, so a stalled sync-daemon poll blocked canonical persistence. Each fan-out handler now runs under a wall-time bound (`SPEC_KITTY_SAAS_FANOUT_TIMEOUT`, default 10s; ≤0 = inline/legacy); on timeout the caller proceeds and logs a WARNING. Regression: `tests/status/test_saas_fanout_timeout.py`.
- **Default-pack loader duplication**: WP04 `_load_default_pack_ids` / WP07 `load_default_pack_ids` — consolidate into one shared charter-layer helper.
- **`resolver.py:372` `resolve_governance_for_profile`**: reads `interview.selected_directives`, now latent (no in-tree caller). Remove or repoint.
