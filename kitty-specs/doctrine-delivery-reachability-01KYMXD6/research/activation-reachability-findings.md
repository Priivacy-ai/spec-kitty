---
title: "Charter Activation Reachability — what is actually broken, measured"
description: "Adversarial re-measurement of the 'charter activations are inert' claim: refuted as stated, with four narrower defects that survive and eleven corrections to the prior assessment."
doc_status: active
updated: '2026-07-28'
related:
- docs/plans/doctrine/charter-activation-reachability-assessment.md
- kitty-specs/doctrine-delivery-reachability-01KYMXD6/spec.md
---
# Charter Activation Reachability — Findings

**Origin.** Pre-spec discovery for this mission, 2026-07-28. The operator asked for the claim
*"charter activations are inert"* to be investigated rather than inherited. It was assigned to an
agent briefed to **refute** it, not to confirm it.

All measurements taken on `upstream/main` @ `ed470756e` (the PR #3007 merge commit) and on the
pre-merge branch, this repository.

> ## ⚠ Figures in this document are superseded
>
> The post-spec squad re-derived every count and **D5 was refuted**. Read
> [`squad-findings-and-corrections.md`](./squad-findings-and-corrections.md) before using any number
> here. Summary of what changed:
>
> - **185 activated → 184.** `toolguide:rtk-search-tooling` was deleted by PR #3007 with its
>   activation entry; toolguides are 11, not 12. 185 was never true on the stated commit.
> - **91 unreachable → 88.** And three other lenses measured 78 and 59 under different traversals —
>   the count was never the right unit. The spec now asserts a named set.
> - **78 surfaced → 69 delivered.** The 8 paradigms arrive only as dead `_LIBRARY/` links; the
>   `procedures: 2` in §1 were prose substring false positives, contradicting §2's own table.
> - **214 references → 213.**
> - **D5 (§2) is REFUTED.** `prompt_builder` supplies the grain correctly via `build_with_scope`;
>   first load renders 31.5 KB with 80 activated ids. The cause is bootstrap exhaustion, not missing
>   grain. The callers that genuinely omit it are `agent/workflow.py:738` and
>   `agent/workflow_executor.py:459`.
> - **Correction #4's remedy names the wrong field.** The pointer is `charter:`, already shipping and
>   honoured. `charter_file:` exists nowhere in the codebase.
> - **§4's line anchors drifted** (four of five). Function names are correct; prefer symbol anchors.
> - **A sixth defect was missed:** the bundle resolves 5 styleguides and 3 toolguides and the renderer
>   emits zero — a drop one layer below `resolver.py`.

---

## 1. The headline claim is REFUTED as stated

[`charter-activation-reachability-assessment.md`](../../../docs/plans/doctrine/charter-activation-reachability-assessment.md)
states that **185 activated artefacts surface at zero** action boundaries, and that *"activation
influences what is compiled and what can be fetched, but not what is offered at the moment an agent
starts an action."*

That is false. Activation is **causally live** at the action boundary.

Decisive evidence — in a scratch clone of `.kittify`, narrowing `charter.yaml` to a single
activated tactic:

```
BEFORE  action bundle: directive_ids=18  tactic_ids=65  styleguide_ids=7  toolguide_ids=3
AFTER   action bundle: directive_ids=0   tactic_ids=1   styleguide_ids=0  toolguide_ids=0
        'avoid-gold-plating' (deactivated) still in action prompt? False
```

Deactivating an artefact removes it from the action prompt. And on a first-load `implement`
render with the mission type supplied, **78 of the 185 surface**, not zero:

```
build_charter_context(action='implement', depth=2, mission_type='software-dev')
  mode=bootstrap  len=31115
  surfaced of 185: 78  {tactics: 52, directives: 16, paradigms: 8, procedures: 2}
```

### Why the original measurement read zero

`spec-kitty charter context` exposes **no `--depth` flag**. Depth is inferred from first-load
state (`src/charter/context.py:623-628`):

```python
if depth is not None:        effective_depth = depth
elif first_load:             effective_depth = _MIN_EFFECTIVE_DEPTH   # 2 -> bootstrap
else:                        effective_depth = 1                      # -> compact
```

`.kittify/charter/context-state.json` recorded `implement` as loaded on 2026-07-22, so every CLI
run since returns compact. The prior assessment's own transcript carries the disconfirming
evidence it did not read: `"first_load": false`.

**The bootstrap render is consumed once per project and is unrepeatable from the CLI.**

---

## 2. The four defects that are real

### D1 — The compact rail structurally cannot carry four of six kinds

`src/charter/resolver.py:329-332` hardcodes `tactics=[], styleguides=[], toolguides=[],
procedures=[]` in the returned `GovernanceResolution`. This is not a missing argument at a call
site — the rail cannot carry those kinds regardless of what any caller passes.

Compounding it, `context.py:214` and `:245` call `_render_compact_governance(...)` without
`directive_ids` / `tactic_ids`, so `render_compact_view` (`compact.py:98`) defaults them to `()`
and `_append_section` (`compact.py:191`) emits `(none)`. The `Paradigms:` line (`compact.py:186`)
reads `charter.yaml governance.doctrine.selected_paradigms`, which is empty.

**Compact is the steady state.** After first load, this is what every agent gets.

### D2 — 91 of 185 can never reach any action prompt

Activation is an **intersection filter** over the DRG action-reachable set, not an entry vector.
Union across all 4 actions x 4 mission types:

| kind | activated | action-reachable | unreachable |
|---|---|---|---|
| tactics | 110 | 62 | **48** |
| directives | 25 | 16 | **9** |
| styleguides | 12 | 5 | **7** |
| toolguides | 12 | 3 | **9** |
| procedures | 18 | **0** | **18** |
| paradigms | 8 | 8 | 0 |
| **total** | **185** | **94** | **91** |

**All 18 procedures are structurally unreachable at every action**: `_ActionDoctrineBundle` has
no `procedure_ids` field at all.

### D3 — The bootstrap reference block is capped at 10, and the cap is order-rigged

`src/charter/context.py:1103`: `for reference in filtered_references[:10]`.

`_filter_references_for_action` (`context.py:1419`) is a **no-op for every doctrine kind**
(verified: 214 -> 214 for all four actions). `_build_references_from_service`
(`src/charter/compiler.py:877-980`) emits in fixed kind order: user_profile(1) -> paradigms(8) ->
directives(25) -> tactics(119) -> styleguides -> toolguides -> procedures -> agent_profiles.

Slots 1-10 are therefore **always** USER + 8 paradigms + `DIRECTIVE_001`. Tactics start at index
34 and can never be reached. **No test pins this cap** — it is unguarded in both directions.

### D4 — Every reference pointer is broken

The bootstrap block emits `(_LIBRARY/paradigm-atomic-design.md)` for every reference.
`.kittify/charter/_LIBRARY/` **does not exist**.

### D5 — `spec-kitty next` inherits the worst combination

`src/runtime/next/prompt_builder.py:404-410` calls `build_charter_context(repo_root, action,
mark_loaded=True, profile=...)` with **no `feature_dir` and no `mission_type`** on the
non-monorepo branch — typeless grain, therefore zero doctrine — *and* `mark_loaded=True`, which
burns the one bootstrap render on an empty payload. The `feature_dir` branch (`build_with_scope`)
forwards the grain correctly.

This is the path agents actually take. It is the most consequential single defect in the set.

---

## 3. Corrections to the prior assessment

| # | Prior claim | Correction |
|---|---|---|
| 1 | "185 activated; zero appear" | 78 appear on a first-load `implement` render with `--mission-type`; 94 can appear across all actions. Restate as *"91 of 185 can never reach an action prompt, and the other 94 only on the once-per-project first load."* |
| 2 | "Activation influences compile and fetch, not what is offered at an action" | Wrong. Deactivation demonstrably removes artefacts from the action prompt (65 -> 1). Activation is an **intersection filter over DRG action-reachability**, not an entry vector. |
| 3 | "This is not the typeless-grain defect of #883" | Wrong, and the inversion matters. The results matched only because compact never consults mission type. In bootstrap, `mission_type=None` yields `{directives:0, tactics:0, styleguides:0, toolguides:0}` vs `{16, 51, 5, 2}` with `software-dev`. This **is** #883, and #883 is more load-bearing than the assessment allows. |
| 4 | "V1 (`config.activated_*`) is the right survivor" | **Backwards.** `PackContext.from_config` (`src/charter/pack_context.py:203-212`) reads `config.yaml` only when the `charter:` pointer is absent. It is present here, so **`charter.yaml` is the live authority and `config.yaml`'s `activated_*` is an unread mirror.** Proven by mutation: editing `config.yaml` down to 2 tactics changed nothing; editing `charter.yaml` changed everything. |
| 5 | "V2 holds 110 tactics" | `interview/answers.yaml` holds **28** tactics (also 25 directives, 5 styleguides, 3 toolguides, 4 procedures, 0 paradigms). |
| 6 | "V3 holds `selected_*: []` for every kind" | Accurate, but nested. `charter.yaml` carries *both* top-level `activated_*` (185, live) *and* `governance.doctrine.selected_*` (all 8 empty). |
| 7 | "Three vocabularies" | An undercount — there are **six stores**, two of them dead files. `.kittify/charter/governance.yaml` and `.kittify/charter/directives.yaml` are **never read** (`load_governance_config`, `src/charter/sync.py:233-252`, reads `charter.yaml`'s sections per IC-04). They sit on disk looking authoritative. `references.yaml` (214 entries) is the sixth. |
| 8 | "`--include` works for all 185" | **157/185 by the documented selector form.** All 25 directives fail as `directive:025-boy-scout-rule` (the id form stored in the activation list) and require `directive:DIRECTIVE_025` — an id-vocabulary mismatch between the activation store and the fetch selector. Three more fail correctly via language scoping. Effective 182/185, with a 25-artefact usability trap. |
| 9 | Blast radius unstated | **Not repo-specific.** `src/charter/packs/default.yaml` ships **155 activated artefacts** to every project via `m_3_2_0rc35_default_charter_pack`. A fresh `init` hits the same shape. |
| 10 | — | Profile-cited artefacts are **not** activation. `python-pedro` renders `test-scaffolding-as-design-smell`, which is not in `activated_tactics`. Profile citations bypass the activation gate; do not count them as activation working. |

---

## 4. Fix sizing (independent estimate)

**R1 is landable without R2, and is smaller than the prior assessment implies** — the rendering
machinery already exists and works. Proven: writing 14 activated ids into `charter.yaml
governance.doctrine.selected_*` in a scratch clone made all 14 render with full inline bodies,
provenance, and budget substitution (text 5.8k -> 16.2k, `_render_selection_block`,
`context.py:1040`). **Nothing new needs building; a list needs feeding.**

Modules that change — **5 files, ~150-250 lines**:

| File | Change |
|---|---|
| `src/charter/resolver.py:329-332` | Remove the hardcoded `[]` for four kinds. **Blocking edit** — without it the compact rail cannot carry them regardless of callers. |
| `src/charter/context.py` | `_load_doctrine_selection` (:819) unions in `resolve_config_activated_roots`; `_render_selection_block` (:1040) moves out of bootstrap-only; compact callers (:214, :245) pass ids. |
| `src/charter/compact.py:177-191` | `_render_text` accepts paradigm/procedure/styleguide/toolguide lists, not just two. |
| `src/charter/context.py:1103` + `:1419` | Replace the order-rigged `[:10]` with a per-kind quota. |
| `src/runtime/next/prompt_builder.py:404-410` | Pass the mission-type grain; stop burning the bootstrap render. |

**The grain filter is already built and already correct.** The action-doctrine walk yields 55-65
tactics / 16-18 directives, not 110. R1 should reuse `_load_action_doctrine_bundle` rather than
invent a new filter. This removes the main sizing risk the prior assessment flagged.

**Tests:** `tests/charter/test_compact.py`, `tests/charter/test_context.py`,
`tests/contract/test_charter_compact_includes_section_anchors.py`,
`tests/charter/test_config_sourced_derivation.py`, `tests/cli/commands/test_charter_rendering.py`
— **79 passed** at baseline. Expect ~a dozen byte-stability fixtures to move (`(none)` ->
populated). The `[:10]` cap has no coverage and needs new tests in both directions.

---

## 5. Operator rulings taken during discovery (2026-07-28)

**On the 91 unreachable artefacts.** Add the `procedure_ids` field, and **author edges for the
obvious artefacts** so they become reachable. The non-obvious remainder is deferred to an
**after-mission operator interview** rather than guessed at in-mission.

**On the activation store.** `charter.yaml` / `charter.yml` is the authority. `.kittify/config`
holds the repository's Spec Kitty config and metadata and **points at the charter file via a
`charter_file:` field**. This settles correction #4 in favour of the live store and against the
prior R2 recommendation. Classified as an ordinary schema change with a consumer migration, **not**
a bulk edit.

---

## 6. Not verified

- A live `spec-kitty init` on a fresh project — `src/charter/packs/default.yaml` and the migration
  were read, but the init path was not executed end-to-end.
- The `.claude/commands/` runtime prompt path end-to-end. Static scan only: `.claude/commands` has
  0 files in this checkout; `.agents/skills` (87 files) contains 17 activated ids as literal prose
  and `src/doctrine/missions/mission-steps` (77 files) contains 6 — these are hand-authored
  mentions, not activation-driven injection.
- `_render_activation_block` (`context.py:2621`) — `charter.yaml governance.activations` is `[]`
  here, so it is a no-op that could not be exercised.
