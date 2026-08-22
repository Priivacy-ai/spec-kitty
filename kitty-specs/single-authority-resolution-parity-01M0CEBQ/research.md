# Phase 0 Research — Single-Authority Resolution Parity

All decisions below are grounded in direct inspection of `main` @ post-#3534. The spec's FR/NFR/C tables are the normative contract; this file records the *how* and the alternatives weighed. The mission's architectural decisions were pre-locked by the operator (C-001…C-006) and are **not** re-litigated here — the research validates them against the code and resolves the residual engineering choices.

---

## D-1 — Where the shared recursion authority lives

**Decision**: A new small module `src/doctrine/discovery_recursion.py` in the **doctrine layer**, exposing the org/project overlay recursion policy. Both the loader (`doctrine.base`, `doctrine.agent_profiles.repository`) and the resolver (`charter.kind_vocabulary`) import it.

**Rationale**: C-006 forbids `charter` importing `specify_cli`, and `doctrine` is the lowest layer (charter and specify_cli import *down* into it). A doctrine-layer authority is the only home both consumers can legally share. Precedent: `doctrine.artifact_kinds.PROJECT_KIND_DIRS` is already imported *down* by both charter (`kind_vocabulary`, `pack_manager`) and specify_cli.

**Shape**: Because recursion is **unconditional** (C-001 — not a per-kind flag), the authority is expressed so the gate can still detect per-kind divergence falsifiably. Chosen form: a policy function `overlay_scan_is_recursive(kind: ArtifactKind) -> bool` returning `True` for every kind, plus the derived set `RECURSIVE_OVERLAY_KINDS: frozenset[ArtifactKind]` (= all members). The gate asserts the loader-recursive set == resolver-recursive set == this authority for 100% of kinds. A single uniform-`True` policy keeps C-001 ("not a per-kind flag") while giving the gate a per-kind surface to prove parity against.

**Alternatives considered**:
- *A bare module-level `bool` constant.* Rejected: gives the gate no per-kind surface, so US2 AC-2 ("reintroduce a divergence for one kind → gate names the kind") cannot be expressed as a behavioral parity check.
- *Put the authority in `charter`.* Rejected: the loader (`doctrine`) cannot import *up* into `charter`; violates the layer ratchet.
- *Per-kind recursion flags.* Rejected by C-001 (explicitly "not a per-kind flag").

---

## D-2 — Loader recursion unification

**Decision**: `doctrine.base.BaseDoctrineRepository._project_scan` (used for **both** org and project overlays via `_apply_overlay_layer`) becomes recursive; the two redundant `rglob` overrides (`StyleguideRepository`, `AssetRepository`) are deleted; `agent_profiles/repository.py::_load` flips its org (`recursive=False`) and project (`recursive=False`) scans to `True` (built-in was already `True`, its own third divergence site).

**Rationale**: `_load_built_in_items` already uses `rglob`; the org/project path used a non-recursive `glob` default — the exact 71% tactic-undercount cause. Unifying on the shared authority (D-1) makes the loader recursive for every kind. Deleting the two overrides removes the last hand-restated recursion decisions on the loader side (NFR-002 holds: `rglob` over a flat/no-subdir dir yields the identical file set as `glob`, so styleguide/asset output is unchanged).

**Alternatives**: keep the overrides and only fix `base` — rejected: leaves two more restated copies that the whole mission exists to remove, and they'd escape the gate.

---

## D-3 — Resolver recursion unification

**Decision**: `charter.kind_vocabulary._org_scan_dirs` (flat entry currently `(flat, False)`) and `_layer_scan_dirs` (currently `(candidate, False)`) derive their `recursive` flag from the D-1 authority (→ `True`). `_built_in_scan_dir` is already `True`.

**Rationale**: This is the documented `#3426` residual (a nested org `styleguide` loads at runtime but the activation resolver drops it because it emits `recursive=False` for the flat org dir). The resolver now agrees with the loader by construction.

**Cross-check — `charter.pack_manager.list_available_detailed`**: already uses `scan_dir.rglob(glob)` (recursive). This is precisely the *list-vs-activate* asymmetry behind #3426 (the availability catalog saw nested artifacts; the activation resolver did not). No change needed there — the fix brings the **activation** resolver up to the already-recursive availability path. The parity gate notes it as an already-agreeing path.

---

## D-4 — Single derived kind-vocabulary authority

**Decision**: Add a derived **charter-activatable plural↔singular** authority in the doctrine layer, keyed by the set `ArtifactKind − {template, asset}` = **10 kinds including `anti_pattern`** (C-003/FR-005). Collapse onto it:
- `charter.activations._SINGULAR_TO_PLURAL_KIND`, `_PLURAL_TO_SINGULAR_KIND`, `_ALLOWED_KINDS`
- `charter._activation_render._singular_kind`'s inline inverse map, `_KIND_TO_PROPERTY`

**Rationale**: `_SINGULAR_TO_PLURAL_KIND` already carries the correct 10 kinds; the two `_activation_render.py` copies drifted two kinds behind (missing `glossary_pack`, `anti_pattern`), so `_singular_kind` fails open (`glossary_packs` renders as the plural token instead of `glossary_pack`) and `_KIND_TO_PROPERTY` blinds `_infer_kind` for `glossary_packs`. Deriving all four from one authority makes the drift structurally impossible. The 10-kind set is a **distinct** exclusion (`{template, asset}`) from `_NON_AUGMENTATION_ELIGIBLE_KINDS` (`{template, asset, anti_pattern}`); FR-005/C-003 explicitly keep `anti_pattern`.

**Safety of adding `anti_pattern`/`glossary_pack` to `_KIND_TO_PROPERTY`**: `_infer_kind` reads `getattr(service, prop, None)` and `continue`s on `None`. `service.glossary_packs` exists (real repo) → drift fixed. `service.anti_patterns` does not exist → `getattr` returns `None` → inert, never matches. Confirmed by reading `_infer_kind` and `doctrine/service.py`.

**`_KIND_TO_NODE_KIND` (project_drg, string-keyed, 3 entries)**: intentionally partial (only directive/tactic/styleguide are synthesizable targets; read via `.get`). M1 does **not** convert it to enum-keyed — that is **M6** (`#3038`), and doing it here would risk a golden-count ripple (C-004). M1's job is to make the gate **cover** it: validate its keys are legit kind tokens and exempt it from *totality* explicitly. If we accidentally converted it to enum-keyed and it moved a golden count, we'd STOP (C-004).

**Alternatives**:
- *Derive from `CHARTER_KIND_TOKENS` (9 kinds).* Rejected by C-003/FR-005 — drops `anti_pattern`, a behavior change.
- *Reuse `AUGMENTATION_ELIGIBLE_KINDS` (also `− {template, asset, ...}` + mission_type).* It excludes via `_NON_AUGMENTATION_ELIGIBLE_KINDS` (drops anti_pattern) and adds mission_type — wrong set for the charter-activatable vocabulary. A dedicated derived authority is clearest.

---

## D-5 — `--include` selector widening (FR-006)

**Decision**: In `charter.context_renderers.template_include._render_doctrine_artifact_include`, add `glossary_pack` to the `renderers` dict (→ `service.glossary_packs`, inline body render). Make `anti_pattern` a **recognized** selector kind that resolves to the standard "No anti_pattern found for selector" not-found path rather than the caller's "Unsupported --include selector kind" error.

**Rationale**: `_resolve_include_kind` already accepts all 12 kinds via `ArtifactKind.from_operator_token`; the failure is downstream — the hardcoded 6-kind `renderers` dict returns `None` for `glossary_pack`/`anti_pattern`, and the caller turns `None` into "Unsupported selector kind". SC-003 requires the stanza to **resolve** (kind recognized) rather than error on an *unknown selector*. `glossary_pack` has real artifacts → renders. `anti_pattern` ships no standalone artifact file (per `artifact_kinds.py`: anti-pattern nodes live inside graph fragments), so "recognized kind, no matching artifact" is the honest resolution — distinct from "unknown kind".

**Alternatives**: leave `anti_pattern` unhandled — rejected: it stays an "unknown selector kind" for a legitimate charter-activatable kind, exactly the #2981 inconsistency. Fully rendering `anti_pattern` — impossible/out of scope (no artifact file convention, and node emission is C-004 out-of-scope).

---

## D-6 — Falsifiable parity/totality gate

**Decision**: Extend `tests/doctrine/drg/test_kind_mapping_totality.py` (the existing AST gate) with two capabilities and one negative test:
1. **String-keyed kind-map coverage.** The current gate's AST scan only recognizes `ArtifactKind.MEMBER` / `NodeKind.MEMBER` dict keys, so every string-keyed copy (`_SINGULAR_TO_PLURAL_KIND`, `_KIND_TO_PROPERTY`, `_KIND_TO_NODE_KIND`, …) is invisible. Add discovery of module-level dicts whose **string keys** are drawn from the kind vocabulary, and validate each key is a legit `ArtifactKind` value (fail-loud on a typo/drifted key). Intentionally-partial string maps (`_KIND_TO_NODE_KIND`) are added to an explicit exempt-from-totality allow-list (key-validity still enforced) — mirroring the existing `_EXEMPT_GET_PARTIALS` mechanism.
2. **Loader↔resolver recursion parity.** A behavioral check: for every `ArtifactKind` with a non-empty glob, author a nested overlay fixture (`<dir>/<sub>/x.<kind>.yaml`) and assert the **loader** (`DoctrineService`/`BaseDoctrineRepository`) and the **resolver** (`charter.kind_vocabulary` resolution) both discover it. Reintroducing `recursive=False` in either seam makes the sets diverge → the gate fails and names the kind.
3. **C-002 negative test.** In the same nested fixture directory, drop a `.provenance/foo.yaml` and a `bar.md`; assert neither is captured by loader or resolver (kind-specific globs).

**Falsifiability proof (NFR-003, both directions on one commit)**: a test that monkeypatches/parametrizes one seam to `recursive=False` and asserts the gate reddens, then restores and asserts it greens — proving the gate is not vacuous.

**Rationale**: FR-007 demands the gate fail loudly on recursion divergence **or** kind-map inconsistency **including string-keyed maps**. The behavioral parity check binds the two authorities by observable output, not just by shared-constant inspection (a shared constant alone could be bypassed).

**Alternatives**: a purely structural gate (assert both seams import the authority) — weaker: it can't catch a bypass that re-hardcodes `False`. The behavioral check is strictly stronger and directly encodes US2's independent test.

---

## Adversarial evidence (plan/research)

No security-impacting dependency decision is made (no deps added/changed), so the supply-chain adversarial pass is **N/A** and recorded as such (not silently dropped) per `contracts/adversarial-evidence-contract.md` conventions. The substantive adversarial risk for this mission is **scope creep into a golden-count ripple** (C-004); the mitigation is the mandatory golden-count STOP gate (see plan Coordination Points) and is carried as a contested-finding disposition:

| Finding | Disposition | Note |
|---------|-------------|------|
| Making discovery recursive could change DRG golden counts / cascade reach | **accepted (guarded)** | Recursion only *adds nested overlay discovery*; it does not add DRG nodes or edges. Mandatory golden-count test gate in implement/review; if any count moves → STOP (belongs to M2/M5). |
| Converting `_KIND_TO_NODE_KIND` to enum-keyed now (tempting for gate coverage) | **deferred_with_rationale** | That is M6 (#3038) and risks a golden ripple; M1 covers it via string-keyed gate + totality exemption instead. |
| Adding `anti_pattern` to render/property maps could crash inference/render | **changed → verified safe** | `_infer_kind` uses `getattr(..., None)`; `anti_pattern` has no service repo → inert. Confirmed by code read. |

No contested finding is silently dropped.
