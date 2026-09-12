# Post-Plan Brownfield Review Squad — findings & dispositions

**Point-cut:** post-plan (brownfield lens). **Date:** 2026-08-23.
**Squad (profile-loaded, read-only):** architect-alphonso (seams/topology),
doctrine-daphne (DRG wiring/integrity), debugger-debbie (falsifiability/coverage),
reviewer-renata (anti-laziness/contracts). Verdict: **REQUEST CHANGES** to
plan/contracts — direction sound, two central IC-2 claims falsified, IC-4 approach
wrong, IC-3/IC-5 coverage gaps. Dispositions per
`contracts/adversarial-evidence-contract.md`: accepted / changed / deferred.

## Confirmed findings & dispositions

| # | Finding (evidence) | Lens | Severity | Disposition |
|---|--------------------|------|----------|-------------|
| F1 | IC-4 seam-fix would **double-fold** for 4 callers already passing `org_roots`+`org_fragments` (`gate_bindings.py:305`, `activate.py:300/398`, `deactivate.py:156`) and mis-tier org content as built-in precedence (`_drg_helpers.py:218`). Only `executor.py:362` + `action_doctrine_bundle.py:192` are deficient. | architect | HIGH | **accepted** → IC-4 inverted to option (b): thread `org_fragments=load_org_drg(repo_root, strict=False)` at the 2 callers only. Do not touch the `:245` DoctrineService seam. |
| F2 | "Only the extractor reads context-sources" is **false** — ≥8 consumers: `agent_profiles/__init__.py:13,31` (`__all__`), `scripts/generate_schemas.py:485-492`, `scripts/doctrine/inline_reference_inventory.py:166-193`, `tests/charter/test_emit_delivery_bind.py:577,677`, `tests/doctrine/agent_profiles/test_supply_chain_profile_bindings.py:158`, `tests/doctrine/test_profile_model.py`, `test_shipped_profiles.py`, `test_model_strictness_roundtrip.py`, `test_extractor.py:135`, `test_extractor_projection.py:535`. | daphne | HIGH | **accepted** → IC-2 consumer list enumerated in plan/WP; each updated in the same WP. |
| F3 | `additional` is **not** pure-drop: reviewer-renata's `context-sources.additional` carries `adversarial-evidence-disposition`, the only place that string exists, pinned by `test_supply_chain_profile_bindings.py:158`. Dropping it silently loses an operator supply-chain binding. | daphne | HIGH | **accepted** → migrate that intent to an explicit ref (directive/tactic) or a deliberate test update; no silent drop. New FR. |
| F4 | C-006 **delivery regression** for python-pedro/DIRECTIVE_034: `hand_authored_overlay.py:585` authors pedro `suggests→034` (with `when`); IC-2's `directive-references→requires` makes 034 a requires-diamond → `progressive_disclosure.py:186` suppresses the suggested link → pedro loses that delivered line. | daphne | HIGH | **accepted** → handle deliberately (exclude 034 from pedro's requires projection, or drop the overlay `suggests→034` with a ledger note); regenerate `agent_profile.graph.yaml` + reconcile `hand_authored_overlay.py`. |
| F5 | Golden **re-ledger required**: pedro directive requires-edge 9→10 + relation shift; `test_golden_count_ban.py` + composition ledger + Daphne's boundary. Plan omitted `packs/built-in/agent_profile.graph.yaml` regen AND `hand_authored_overlay.py`. Migration must **set-merge, not append** (`directive-references` ⊇ `context-sources.directives`). | daphne | HIGH/MED | **accepted** → add regenerate-graph + overlay-reconciliation + ledger row (or walk-gate) task to IC-2; migration set-merge + dup-guard. |
| F6 | IC-2/FR-005 DoD **green-by-construction** — all 25 shipped profiles already duplicate refs on `*-references`, so `del context-sources` passes. C-006 points at no falsifiable artifact. | renata | HIGH | **accepted** → add a **divergent user-profile fixture** (ids absent from `*-references`) + frozen pre-migration snapshot; pin C-006 to the golden `agent_profile.graph.yaml` diff. |
| F7 | IC-1 drift-guard `_DRG_NODE_KINDS == {k.value for k in NodeKind}` is a **tautology** post-derive; value==prefix is structurally safe (`DRGNode._validate_urn`); an SSOT twin already exists at `merge.py:504` (`_NODE_KIND_PREFIXES`). | debugger, architect, renata | MED | **accepted** → reuse/align with `merge.py:504`; pin the **membership-gate behaviour** (monkeypatch a NodeKind member → resolver recognizes it), not set-equality. |
| F8 | #3629 p2 close **regression-unprotected**: existing tests call `assert_governance_scope_edges_resolve` with synthetic edges, never `generate_graph`. | renata | MED | **accepted** → add one end-to-end `generate_graph`-level raise test for the built-in tier. |
| F9 | **No org-tier governance-profile scope path exists at all** — `extract_governance_profile_scope_edges` reads only built-in missions (`extractor.py:1368`). Org-tier `selected_*` typo is unread + unguarded (total no-op). | debugger | HIGH | **accepted (scope expanded, operator decision)** → **implement** org-tier governance-profile scope extraction + fail-loud guard + tests in this mission. IC-3 reclassified from verify to implement. |
| F10 | IC-5 built-in+internal = **1 org pack**; `merge_three_layers` already iterates all fragments (`merge.py:1251`); the "only-first-pack" bug was the caller seam, already fixed by #3525. One org pack exercises fragment-drop (class b) only, not the multi-org-pack fold (class a). | debugger | HIGH | **accepted (operator decision)** → **add a 2nd minimal org fixture**; assert pack #2's fragment node/edge reaches the merged graph (class a) alongside spec-kitty-internal (class b). |
| F11 | C-IC4 "does not double-fold" + C-IC5 "misconfig fails loud" under-specified (fakeable). IC-4 valid-fragment red test needed (existing degrade test uses a **malformed** fragment, `test_executor.py:915`). | renata, debugger | MED | **accepted** → C-IC4 asserts edge/node **multiset count == single-fold** + warning-iff (fragment-only→no warn; graphless→warn); C-IC5 enumerates misconfigs with expected exception type and warn-vs-raise; IC-4 red test uses a **valid** fragment. |
| F12 | executor pre-probe (`executor.py:347-360`) raises `DRGLoadError` for a fragment-only pack → excluded from `healthy_roots` (a *warned* drop) before the seam — a second drop point on that path. | debugger | LOW/MED | **accepted** → IC-4 must confirm org content is delivered via `org_fragments` regardless of the pre-probe; adjust the pre-probe warning if noisy. |
| F13 | `action_doctrine_bundle.py` has a **2nd org seam** at `:245` (DoctrineService, artifact content) distinct from the `:192` edge seam. | architect | LOW | **accepted (guard)** → IC-4 fix scoped to `:192` only; do not widen to `:245`. |
| F14 | IC-6 doc-nit is **coupled** to IC-2's re-ledger — the `extractor.py:557` "no golden-count update required" wording is exactly what IC-2 changes; validate IC-6 after IC-2's ledger settles. | architect, daphne | LOW | **accepted** → sequence IC-6 after IC-2; the doc-nit text must reflect IC-2's re-ledger. |
| F15 | `staleness.py:141-176` reads a DRG **node** attr `context_sources` (different surface, won't break) but shares the retired name — terminology collision. bulk-edit examples reference `context-sources.*` as stale field-paths. | daphne | LOW | **accepted** → no code change for staleness (note the collision); refresh bulk-edit example paths. |

## Non-fakeable assertions adopted (from renata)

- C-IC1: monkeypatch `NodeKind` with an extra member → `_DRG_NODE_KINDS` reflects it (behavioural derivation), not literal equality.
- C-IC2/FR-005: divergent user-profile fixture (ids not on `*-references`) proves the data-moving branch; frozen pre-migration snapshot proves "no reference lost".
- C-006: golden `packs/built-in/agent_profile.graph.yaml` regen diff must be empty except the deliberately-ledgered pedro/034 delta.
- C-IC3: end-to-end `generate_graph` raise test (built-in) + a real org-tier resolution test (org path now implemented).
- C-IC4: edge/node multiset count == single-fold; warning fires iff neither `*.graph.yaml` nor `drg/fragment.yaml` exists.
- C-IC5: per-misconfig parametrized cases with expected exception type; warn vs raise disambiguated.

## Convergence / divergence

No irreconcilable divergence. debugger + renata + architect converge on IC-1 (tautology → behaviour pin). daphne + renata converge on the shipped-profile duplication fact (⇒ green-by-construction + provable C-006). architect's IC-4 caller enumeration is decisive and uncontested. All four independently confirmed #3629 p2 built-in guard is genuinely present (scope-honesty holds).
