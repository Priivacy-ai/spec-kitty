# Mission Specification: Contract-ownership boundary — MVP (model + static-arm driver + `test_no_legacy_*` adoption)

**Status**: Draft
**Issues**: Closes #2441. Refs #2077 (CT7 sweep payload), #2438 (dynamic arm, later), DIR-041 (governing directive).
**Provenance**: architect-alphonso design (`kitty-specs/contract-ownership-boundary-01KWYRE5/design.md`). This mission is the **conservative first increment** — model + validator + one seeded contract + the static-arm absence-sweep driver + adopting the `test_no_legacy_*` family. The higher-blast WPs (write-side ratchet adoption, dynamic/completeness arms wiring #2438, enforcement flip) are **tracked follow-ups under #2441**.

## User Scenarios & Testing *(mandatory)*

**Primary actor**: a maintainer retiring a shared contract (a public signature, a fallback/compat name, or a retired literal a caller depended on) who today has **no single owned artifact** that says "contract X exists, these are its declared consumers, and its removal is verified against that list." Four mechanisms each catch a slice (#2438's dynamic gate; the write-side rederivation ratchets; `stale_assertions`; the `test_no_legacy_*` family) — each **re-derives** the consumer set by hand and lets it rot.

**Grounding** (design, confirmed against the repo):
- **Near-precedent to generalize (do NOT reinvent)**: the shim chain — schema `kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/shim-registry-schema.yaml`, manifest `docs/migrations/shim-registry.yaml`, loader/validator `src/specify_cli/compat/registry.py` (`ShimEntry`), retirement check `spec-kitty doctor shim-registry`, completeness gate `tests/architectural/test_unregistered_shim_scanner.py`. It models only the `fallback_name` kind, has **no declared consumer set**, and its retirement check is "is it registered / drained" — not "verified against declared consumers." That gap is #2441.
- **Content-anchoring primitive already exists**: `tests/architectural/_ratchet_keys.py::composite_key(source, lineno) → (qualname, normalized_token_line)` — DIR-041-compliant, keyed on content not `file:line`.
- **The `test_no_legacy_*` family (adoption target) is HETEROGENEOUS** (post-spec squad, verified) — only part is a genuine retired-literal absence sweep foldable into the static driver: `tests/architectural/test_no_legacy_terminology.py` (a clean literal fold) + the **CLI-tree literal-grep half** of `tests/audit/test_no_legacy_path_literals.py`. The rest do **NOT** fold into a content-anchored `status=retired` sweep without dropping coverage: `path_literals` also has **behavioral** tests (mock `SPEC_KITTY_HOME`, invoke `_emit_migrate_nudge`, assert stderr); `tests/architectural/test_no_legacy_status_emit_callers.py` is an **AST import-alias/call-site gate** for a LIVE `status=deprecated` compat wrapper with 3 allow-listed live callers (needs the deferred `signature`-kind machinery; a `retired`-only driver never fires on it); `tests/audit/test_no_legacy_agent_profiles_path.py` asserts **directory non-existence**. Only the literal-sweep parts are in adoption scope.

### User Story 1 — A shared contract is a modeled, owned artifact (Priority: P1)
As a maintainer, I want a Contract Record (id, kind, content-anchored anchor, status, owner, replaced_by, retirement metadata, and — the missing piece — a **declared consumer set**) in a schema-validated manifest, so a contract's existence + consumers + retirement obligations live in one owned place.
**Independent test**: a seeded record loads + validates via `spec-kitty doctor contracts`; a malformed record (or one with a forbidden `file:line` anchor) fails validation (red-first).

### User Story 2 — Retirement is verified against the declared consumers (static arm) (Priority: P1)
As a maintainer, when a contract retires, I want a **content-anchored absence sweep** to prove its anchor appears in **zero live consumers** (the residual a test-*run* can never prove) — driven by the record's declared `scan_roots` minus `exemptions`.
**Independent test**: the sweep is **advisory**; a planted reappearance of a retired anchor is flagged (anti-vacuity negative control); a clean tree reports clean.

### User Story 3 — Prove the model can subsume the literal sweeps — without downgrading enforcement (Priority: P1)
As a maintainer, I want the genuine **retired-literal absence sweeps** (`test_no_legacy_terminology.py` + the CLI-tree literal-grep portion of `test_no_legacy_path_literals.py`) modeled as records + a demonstration that the advisory driver's detection **subsumes (is a superset of)** what they catch (DIR-041 feasibility proof) — it preserves all the gate's coverage (NFR-001) AND additionally over-flags comment-line / non-`.py` mentions the CLI-path gate carves out (an advisory-safe over-flag, since the driver never blocks) — but the existing **merge-blocking** gates **STAY in place** (removing them behind an advisory driver would silently downgrade enforcement to report-only). The gate's comment-skip + `.py`-scoping must be modeled in the driver before the deferred enforcing-flip to avoid false friction. The actual retirement awaits the enforcing-driver follow-up. The AST-directional / behavioral / directory-existence checks are **carved out** entirely.
**Independent test**: the driver flags a **superset** of the terms/paths the enforcing sweeps flag (set-equality over the curated divergence-free envelope; a comment-line control proves `driver ⊋ gate`), with the enforcing gates still blocking; the carved-out checks unchanged.

### Edge Cases
- **Wrong consumer set = false confidence** (design §6): an omitted consumer makes retirement "verified" while a caller silently breaks — worse than today. Mitigation: consumer sets are **discovered** (import/call-graph, reusing `test_no_dead_symbols`'s resolver) then **frozen + reviewed**, never hand-typed blind. The sweep stays **advisory** in this mission.
- **Over-broad sweep = false friction**: a `retired_literal` sweep reds on benign prose. The per-record `exemptions` model generalizes `test_no_legacy_terminology.py`'s `docs/adr/` narrow exemption + self-flag defense; until proven, advisory.
- **Delete-the-assertion-not-the-test (US3)**: a `test_no_legacy_*` file is removed ONLY after the driver+record demonstrably preserves its coverage — never delete first.
- **DIR-041 self-consistency**: the registry must not reintroduce `file:line` rot — anchoring is `composite_key` + AST symbols only; the schema validator **rejects** any positional `file:line` field.
- **`signature` kind deferred**: v1 models `fallback_name` + `retired_literal` (the kinds with existing catch-mechanisms). `signature` waits until the `test_no_dead_symbols` import-graph seam is wired (follow-up).

## Requirements *(mandatory)*

### Functional Requirements
| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Contract Record schema + manifest | US1 — a schema authority `docs/contracts/contract-registry-schema.yaml` + manifest `docs/contracts/contract-registry.yaml` (docs-scoped, sibling to `shim-registry.yaml`). Record: `id`, `kind`∈`{fallback_name, retired_literal}`, content-anchored `anchor` (dotted symbol OR fixed literal — never `file:line`), `status`∈`{active, deprecated, retired}`, `owner`, `replaced_by`, `retirement`{...}, `consumers`{`scan_roots`, `exemptions`, `test_shards`?, `call_sites`?}, `verification`{`enforcement: advisory`}. | High | Open |
| FR-002 | Typed loader + `doctor contracts` validator | US1 — `src/specify_cli/contracts/registry.py` (`ContractRecord`, `load_registry`, `validate_registry`), generalized from `compat/registry.py`; `spec-kitty doctor contracts` **enforces** well-formedness (schema, resolvable anchors, no `file:line`). Structural validation is the only enforcing gate in v1. | High | Open |
| FR-003 | Promote `_ratchet_keys` to a shared anchoring lib | US1 — promote `tests/architectural/_ratchet_keys.py::composite_key` to a shared library the registry loader + the sweep driver depend on (no behavior change to existing ratchet callers). | Medium | Open |
| FR-004 | Seed the adopted-sweep contracts with their declared consumer sets | US1 — seed the manifest with the `retired_literal` records for BOTH adopted literal sweeps (the terminology terms + the CLI-tree path-literal), each **including its discovered-then-frozen consumer set** (scan_roots + exemptions). WP01 **solely owns the manifest**, and WP03's parity depends on both records existing — so both are seeded in WP01. | High | Open |
| FR-005 | Static-arm absence-sweep driver (advisory) | US2 — one content-anchored sweep `tests/architectural/test_retired_contracts_absent.py` driven by `status=retired` records, using `composite_key`/literal anchoring over `scan_roots` minus `exemptions`, with a **mandatory anti-vacuity negative control** (a planted reappearance is flagged). **Advisory/report-only.** | High | Open |
| FR-006 | Model + prove-parity for the literal sweeps — WITHOUT retiring the enforcing gates | US3 — model the literal-sweep subset (`test_no_legacy_terminology.py` + the CLI-tree literal-grep half of `test_no_legacy_path_literals.py`) as `retired_literal` records + **prove the advisory driver's detection is a SUPERSET of what those (currently merge-BLOCKING) gates catch** — it preserves all the gate's coverage (NFR-001) AND additionally over-flags comment-line / non-`.py` mentions the CLI-path gate carves out (an advisory-safe over-flag; `driver ⊋ gate`). Set-equality is proven only over the curated divergence-free envelope; a comment-line control pins the strict-superset relationship. But **do NOT remove/neuter those enforcing assertions in this MVP** — retiring a blocking gate behind an advisory driver would silently downgrade it to report-only. The gate's comment-skip + `.py`-scoping must be modeled in the driver before the deferred enforcing-flip to avoid false friction. The delete-the-assertion retirement awaits the enforcing-driver follow-up. **Carve out** the behavioral/AST/directory checks entirely. | High | Open |

### Non-Functional Requirements
| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | No coverage regression | Nothing is removed in this MVP — the advisory driver is **additive**. Every invariant the family catches today stays caught AND (for the enforcing gates) stays **blocking** (NFR-004). The advisory driver's detection is a **superset** of each enforcing sweep's — it preserves all their coverage AND additionally over-flags comment-line / non-`.py` mentions the CLI-path gate carves out; this superset relationship is *proven, not substituted*. | Reliability | High | Open |
| NFR-002 | Advisory — no false confidence | The absence sweep is advisory (report-only) in v1; a wrong/incomplete consumer set must not produce a green "verified" that hides a break. Only the structural validator enforces. | Integrity | High | Open |
| NFR-003 | DIR-041 self-consistency | The registry introduces **no `file:line` anchoring**; the schema validator rejects any positional `file:line` field. The registry must not become the rot it replaces. | Integrity | High | Open |
| NFR-004 | No enforcing→advisory downgrade | An invariant that is merge-**blocking** today (`test_no_legacy_terminology.py` `pytest.fail`; the `path_literals` `assert`) must remain blocking after this mission. The advisory driver is **additive** — a new report-only layer that replaces no enforcing gate in v1. | Integrity | High | Open |

### Constraints
| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Generalize, don't reinvent | Build on the shim-registry chain (schema→manifest→loader→doctor); a **new sibling registry** under `docs/contracts/`, reusing the schema/loader shape. Fold shim-registry in a later follow-up (not this mission). | Technical | High | Open |
| C-002 | Scope: MVP = model + advisory driver + parity proof (ADDITIVE) | Deliver FR-001..006 as an **additive** layer — model + validator + advisory driver + a parity demonstration; **remove/retire nothing**. **Exclude** (tracked #2441 follow-ups): the enforcing-driver mode + the actual delete-the-assertion retirement of the folded gates; the `signature`-kind machinery + `status_emit_callers`; write-side ratchet adoption; the dynamic/completeness arms / #2438; `stale_assertions` enrichment. | Product | High | Open |
| C-003 | Consumer sets discovered-then-frozen | Consumer sets seeded from a discovered import/call graph (reuse `test_no_dead_symbols`'s resolver) then frozen + reviewed — never hand-typed blind (a wrong list is worse than no list). | Technical | High | Open |
| C-004 | Quality gates | `ruff` + `mypy --strict` clean; red-first proof for the validator + the sweep + each parity assertion; no suppression/ratchet; terminology guard clean. | Technical | High | Open |

### Key Entities
- **`docs/contracts/contract-registry{,-schema}.yaml`** — the owned manifest + schema (FR-001).
- **`src/specify_cli/contracts/registry.py`** — the typed loader/validator (FR-002).
- **`tests/architectural/test_retired_contracts_absent.py`** — the static-arm sweep driver (FR-005).
- **The 4 `test_no_legacy_*` files** — adoption target, retired behind the driver (FR-006).
- **`_ratchet_keys.composite_key`** — the shared content-anchoring primitive (FR-003).

## Success Criteria *(mandatory)*
- **SC-001**: `spec-kitty doctor contracts` validates the seeded record + fails a malformed one AND a `file:line`-anchored one (red-first) — NFR-003.
- **SC-002**: The static-arm sweep flags a planted reappearance of a retired anchor (anti-vacuity) and reports clean otherwise; it is advisory (never blocks) — NFR-002.
- **SC-003**: For the literal sweeps (`terminology` + the path-literal grep half), a parity test shows the advisory driver's detection is a **superset** of what the (still-in-place, still-enforcing) sweeps catch — it preserves all the gate's coverage (NFR-001) AND additionally over-flags comment-line / non-`.py` mentions the CLI-path gate carves out (an advisory-safe over-flag, since the driver never blocks; `driver ⊋ gate`, pinned by a comment-line control). Set-equality is proven only over the curated divergence-free envelope (non-comment lines in in-scope `.py` files), not globally. **No gate is removed** in this MVP (NFR-004); the gate's comment-skip + `.py`-scoping must be modeled in the driver before the deferred enforcing-flip to avoid false friction. The carved-out behavioral/AST/directory checks are untouched.
- **SC-004**: No `file:line` anchor anywhere in the registry; `ruff`+`mypy` clean; no suppression; the higher-blast arms are documented as tracked follow-ups (C-002).

## Out of Scope (tracked follow-ups under #2441)
- **The actual retirement (delete-the-assertion) of the terminology/path gates + the enforcing-driver mode that makes it safe** — deferred so no merge-blocking gate is downgraded to advisory (NFR-004). This MVP proves parity but removes nothing.
- Write-side ratchet consumer-set adoption (`test_no_write_side_rederivation` et al.).
- The dynamic arm (wiring #2438's `pre_review_gate` to read `test_shards`) + the completeness arm (`doctor contracts` consumer-migration check).
- The enforcement flip (advisory→enforcing) + `stale_assertions` registry-aware enrichment + the operator rulebook.
- The `signature` kind + folding shim-registry into the contract registry.

## Assumptions
- The `test_no_dead_symbols` import resolver (or codegraph) is usable to discover consumer sets (C-003).
- `docs/contracts/` docs-scoping matches the arch pole's docs-trim (like `shim-registry.yaml`).
