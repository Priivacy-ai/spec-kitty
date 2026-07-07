# Design: Contract-Ownership Boundary — a modeled, owned artifact for shared contracts + their retirement

- Mission: `contract-ownership-boundary-01KWYRE5` (design-first phase)
- Tracking issue: #2441 (parent) · CT7/#2077 (sweep-mechanisation payload) · #2438 (dynamic review-time gate) · #2283 (boundary that surfaced the gap)
- Author role: architect-alphonso · mode: design · **read-only; no code produced**
- Governing directive: **DIR-041 Tests as Scaffold, Not Friction** — this whole boundary is the concrete instance of DIR-041's integrity rule *"Duplicate test knowledge (the same contract asserted in many drifting places) has one source of truth, not N hand-synced copies."*

---

## 1. The problem, grounded in this repo

A **shared contract** — a public function signature, a fallback/compat name (`falls_back`), or a retired literal a caller once depended on — **and its retirement** are not, today, a modeled, owned artifact with a declared consumer set. There is no single place that says: *"contract X exists; these N call-sites/tests are its declared consumers; when X retires, its removal is verified against that list."*

Instead, at least **four** independently-evolved mechanisms each catch a *slice* of the same failure mode. I traced each in this branch:

### Slice A — dynamic review-time gate (#2438, `pre_review_gate.py`, M5)
*Not yet merged into this branch* (confirmed: no `pre_review_gate.py` under `src/`), so modeled from the issue: at `for_review` it **re-runs the consuming test shards** and fails if a consumer *test* now fails against the retired surface.
- **Catches:** the case where a consuming *test still exists* and exercises the retired surface.
- **Blind to:** a production caller that **no test exercises** — a test run proves the *presence of a new failure*, never the *absence of a retired symbol*.
- **Re-derives:** *which* shards are "the consumers" — it has no declared consumer set to read.

### Slice B — write-side rederivation / write-target-drain ratchets (`tests/architectural/`)
The most sophisticated slice, and the template for how *not* to hand-roll the model N times:
- `test_no_write_side_rederivation.py` (287 L) — a token/AST content-addressed gate flagging hand-rolled re-derivation of `mission_id`/`mid8`/`primary_root` across an **enumerated** `_ADOPTED_MODULES` set (6 hard-coded module paths, lines 43–50), with a hand-seeded `_ALLOW_LIST_SEED` (lines 100–106) of deferred residuals.
- Siblings applying the identical shape to other surfaces: `test_write_surface_placement_guard.py` (611 L, the write-target-drain two-ref placement invariant), `test_gate_read_literal_ban.py` (1815 L, read/write literal-ban seam), `test_topology_inference_retired.py` ("death-spiral grep gate" — a *retired inference pattern* must have zero live decision sites).
- **Shared primitive already extracted:** `tests/architectural/_ratchet_keys.py` — `composite_key(source, lineno) → (enclosing_qualname, normalized_token_line)`. This is the **DIR-041-compliant content-anchoring** primitive: drift-proof against benign blank/comment insertion, keyed on content not `file.py:NNN`.
- **Catches:** a retired code *shape* reappearing in a specific enumerated consumer set.
- **The debt:** every mission re-implements this pattern by hand — a bespoke detector + a hand-enumerated `_ADOPTED_MODULES` list + a hand-seeded allow-list, per surface. The consumer set and the allow-list are **Python literals that rot**. This is exactly the "N hand-synced copies" DIR-041 forbids.

### Slice C — `stale_assertions` post-merge analyzer (`src/specify_cli/post_merge/stale_assertions.py`, 686 L)
AST-based, compares `base..head`, flags test assertions referencing changed identifiers/literals. **Deliberately advisory** — FR-003 forbids emitting `"definitely_stale"`; caps false positives at `FP_CEILING = 5.0/100 LOC`.
- **Catches:** *test-side* assertions likely invalidated by a merged source change.
- **Blind to:** production callers; and it is post-merge + advisory, so it never blocks.

### Slice D — the `test_no_legacy_*` grep/AST-absence family (4 hand-written files)
The residual sweep for **"factor c-static / c′"** — the production caller no test covers:
- `tests/architectural/test_no_legacy_terminology.py` (165 L) — `git grep` for forbidden terms, with a hand-maintained `_EXCLUDED_PATH_FRAGMENTS` list and a `docs/adr/` narrow-exemption sub-test.
- `tests/architectural/test_no_legacy_status_emit_callers.py` (63 L) — AST scan for `emit_status_transition*` call sites, with a hand-coded `_ALLOWED` set of 3 module paths.
- `tests/audit/test_no_legacy_agent_profiles_path.py` (63 L) — path-literal absence.
- `tests/audit/test_no_legacy_path_literals.py` (291 L) — `~/.kittify`/`~/.spec-kitty` literal absence, scoped to the CLI tree, with its own hand-scoped exemption prose.
- **Catches:** the residual — a retired term/symbol/path reappearing anywhere, including production paths no test touches.
- **The debt:** one hand-rolled test per retirement, each with its own scan roots + exclusion list + self-flag defense, **no shared model, no declared consumer set**. This is CT7/#2077's mechanisation target.

### What falls between all four
- A retired contract with a **production caller that NO test exercises** is structurally uncatchable by any test-*run* slice (A, C). Only an **assert-absence sweep** (B, D) catches it — and B/D are hand-rolled per retirement with no owner and no consumer list.
- **No slice knows a contract's declared consumer set.** A/B/D each *re-derive* "who the consumers are" (A: which shards; B: which modules; D: which scan roots) at author time, by hand, and let it rot.
- **No slice models retirement completeness.** None can answer "have all N declared consumers of X been migrated to `replaced_by`?" against a real list.

---

## 2. The existing near-precedent (do not invent from scratch)

There is **already** a modeled, owned artifact for *one kind* of shared contract — the compat/fallback name. It is the shape to generalize:

| Artifact | Path | Role |
|---|---|---|
| Schema authority | `kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/shim-registry-schema.yaml` | declarative schema |
| Registry manifest | `docs/migrations/shim-registry.yaml` (currently `shims: []`) | the owned records |
| Loader + validator | `src/specify_cli/compat/registry.py` (`ShimEntry`, `load_registry`, `validate_registry`) | typed load + schema enforcement |
| Retirement check | `spec-kitty doctor shim-registry` (`src/specify_cli/compat/doctor.py`, CLI `cli/commands/doctor.py:515`) | **overdue-shim detection** (removal release shipped but shim still on disk) |
| Registered-completeness gate | `tests/architectural/test_unregistered_shim_scanner.py` | every `__deprecated__ = True` module MUST be a registry entry |
| Rulebook | `docs/migrations/06_migration_and_shim_rules.md` | operator process |

A `ShimEntry` already carries: `legacy_path` (identity), `canonical_import` (replacement), `introduced_in_release` + `removal_target_release` + `tracker_issue` (retirement metadata), `grandfathered`.

**What it lacks — exactly the #2441 gap:**
1. It only models the **`fallback_name`** kind — not `signature`, not `retired_literal`.
2. It has **no declared consumer set** (the N call-sites/tests that depend on the contract).
3. Its retirement verification is *"is it registered / is the shim file drained?"* — **not** *"when it retires, verify removal against its declared consumers."*

**Design stance:** generalize this proven chain (schema → manifest → loader → doctor → scanner) into a **Contract Registry**, rather than invent a new mechanism. This is the canonical-source discipline the charter mandates.

---

## 3. The modeled artifact: the Shared-Contract Record

### 3.1 Record shape

A **Contract Record** is a declarative entry in a YAML manifest, backed by a schema authority and a typed loader (the shim-registry chain, generalized). Fields:

```yaml
- id: status.emit.emit_status_transition            # stable, human+machine handle
  kind: fallback_name                               # signature | fallback_name | retired_literal
  anchor:                                            # content-addressed identity (never file:line)
    symbol: specify_cli.status.emit.emit_status_transition   # for signature/fallback_name (dotted)
    # literal: "~/.kittify"                          # for retired_literal (fixed string / token)
  status: deprecated                                 # active | deprecated | retired
  owner: "#2441"                                     # tracker issue / mission that owns it
  replaced_by: coordination.status_transition.status_transition
  retirement:
    introduced_in: "3.0.0"
    removal_target: "3.4.0"
    tracker_issue: "#2077"
  consumers:                                         # THE DECLARED CONSUMER SET (the missing piece)
    call_sites:                                      # content-anchored, via _ratchet_keys.composite_key
      - qualname: "specify_cli.status.work_package_lifecycle.transition"
        token_line: "emit_status_transition ( ... )"
      - ...
    test_shards:                                     # the dynamic-arm consumers (Slice A reads these)
      - "tests/status/test_emit.py"
    scan_roots: ["src", "tests", "docs"]             # the static-arm sweep scope (Slice D reads these)
    exemptions:                                      # replaces each test's hand-rolled exclusion list
      - "docs/adr/"                                  # historical snapshots (byte-for-byte immutable)
  deferred_residuals:                                # replaces _ALLOW_LIST_SEED (Slice B), content-keyed
    - qualname: "specify_cli.coordination.status_transition._resolve_write_target"
      token_line: "return coord_branch or _current_branch ( repo_root )"
      rationale: "deferred #1716 write-surface-selection ladder"
  verification:                                      # the retirement-verification contract (§5)
    static: absence_sweep                            # c′ — anchor appears in ZERO live consumers
    dynamic: rerun_test_shards                       # c — no consuming test exercises the retired surface
    completeness: all_consumers_migrated             # every declared consumer moved to replaced_by
    enforcement: advisory                            # advisory | enforcing  (per-record, §6)
```

### 3.2 The three `kind`s map 1:1 to the issue's three examples
- `signature` — a public function signature (e.g. an `__all__` export). Verified by the AST-import machinery (`test_no_dead_symbols.py` already resolves `(module, name)` import sites — reuse as the consumer-discovery seam).
- `fallback_name` — a fallback/compat name like `falls_back` / `emit_status_transition`. This is the existing `ShimEntry` specialization, subsumed unchanged.
- `retired_literal` — a retired literal a caller depended on (a term, a path, a status value). This is the `test_no_legacy_*` family's target.

### 3.3 Anchoring: content, never `file:line` (DIR-041)
All positional identity uses the **already-extracted** `tests/architectural/_ratchet_keys.py::composite_key` → `(enclosing_qualname, normalized_token_line)`, and AST symbol resolution for `signature`/`fallback_name`. **No `file.py:NNN` keys** — DIR-041 validation criterion 33 forbids introducing them, and this registry must not become the very rot it replaces. `_ratchet_keys.py` is promoted from a `tests/architectural/` private helper to a shared anchoring library the registry loader depends on.

### 3.4 Where it lives — decision: **YAML manifest + typed loader** (not frontmatter, not a registry-module of Python literals)
- **Manifest** `docs/contracts/contract-registry.yaml` (docs-scoped, so it runs on the arch pole's docs-only trim exactly like `shim-registry.yaml` and `test_no_legacy_terminology.py` — see their `docs_scoped` markers) + schema authority `docs/contracts/contract-registry-schema.yaml`.
- **Loader** `src/specify_cli/contracts/registry.py` — generalized from `compat/registry.py` (`ContractRecord`, `load_registry`, `validate_registry`). `compat/registry.py`'s `ShimEntry` becomes the `kind=fallback_name` projection.
- **Rejected — frontmatter:** scatters the model across N source files; no single queryable owner set; can't be validated as one artifact.
- **Rejected — a Python registry-module of literals:** exactly the rot DIR-041 forbids ("hand-synced copies"). The manifest is declarative + schema-validated; the *only* Python is the loader + the detectors.

---

## 4. Unification — how one artifact subsumes the four slices (incrementally, not big-bang)

The registry becomes the **single source of the consumer set + retirement metadata**; each existing slice is re-cast as a *consumer/renderer* of it, keeping its surface-specific detector. Nothing is ripped out on day one.

| Slice | Today | After unification | Migration |
|---|---|---|---|
| **A** #2438 dynamic gate | re-derives which shards to re-run | reads `consumers.test_shards` from the record | wire when #2438 lands (WP5) |
| **B** write-side ratchets | `_ADOPTED_MODULES` + `_ALLOW_LIST_SEED` are Python literals per test | detector stays; reads `consumers.call_sites` + `deferred_residuals` from the record | externalize the literals, keep detectors (WP4) |
| **C** `stale_assertions` | advisory, no owner context | when a changed anchor matches a record, cross-references `consumers` + names the `owner` | registry-aware confidence boost (WP6, optional) |
| **D** `test_no_legacy_*` (×4) | one hand-rolled test per retirement | ONE content-anchored absence-sweep driver reads all `kind∈{retired_literal,fallback_name}, status=retired` records | fold each into a record; retire the 4 files behind the driver (WP3) = **CT7/#2077 payload** |

**Migration path = introduce-then-adopt, never big-bang.** WP1 introduces the model and seeds it with a *single* already-modeled contract. Each subsequent WP adopts one slice's consumer sets into records and, only once parity is proven, retires that slice's hand-rolled machinery behind the shared driver (the *delete-the-assertion-not-the-test* tactic: coverage preserved by the driver before the old file is removed). The bespoke **detectors** in Slice B are genuinely surface-specific and are **kept** — only the enumerated consumer set + allow-list they read is externalized.

---

## 5. The retirement-verification contract (the gap today)

When a record's `status` flips `deprecated → retired`, a single verification driver runs the record's `verification` obligations **against its declared `consumers`** — this is what no slice does today:

1. **Static arm (c′ — the residual):** a content-anchored **absence sweep** proves the record's `anchor` appears in **zero live consumers** across `consumers.scan_roots` minus `consumers.exemptions`. This is the residual a test-*run* can never prove (absence of a symbol), generalizing the `test_no_legacy_*` family into ONE driver. It is the CT7/#2077 payload.
2. **Dynamic arm (c):** re-run `consumers.test_shards` (the #2438 mechanism) and prove no consuming test still exercises the retired surface.
3. **Completeness arm (net-new):** every entry in `consumers.call_sites` must have been **migrated to `replaced_by`** — verified against the *declared list*, not re-derived. This is the "verify removal against a real list instead of re-deriving by hand" the issue asks for. Precedent exists half-built: `spec-kitty doctor shim-registry` already does overdue-removal detection; extend it to consumer-completeness.

The trigger is the **retirement event** (the `status` flip in the manifest), which is exactly the "triggered on shared-contract retirement" hook #2077 names. Whether that flip is a manual manifest edit or a CT7-emitted event is an open decision (§8).

---

## 6. Blast radius + risk (this is high-blast-radius)

- **Wrong consumer set = false confidence.** If a record omits a real consumer, retirement is "verified" while a caller silently breaks — *worse* than today, because the green check implies completeness. Mitigation: consumer sets seeded from a **discovered** import/call graph (reuse `test_no_dead_symbols.py`'s import-site resolver, or codegraph) then frozen + reviewed, never hand-typed blind.
- **Over-broad sweep = false friction.** An enforcing `retired_literal` absence sweep across all of `src/tests/docs` will red on any benign prose mention — the exact pain `test_no_legacy_terminology.py` manages with its `docs/adr/` narrow exemption + string-fragment self-flag defense. Generalizing that exemption model is non-trivial; **the sweep stays advisory** until the exemption model is proven per-record.
- **Losing surface-specific detectors.** Slice B's detectors encode real grammar knowledge (token-based, prose-immune). **Do not** collapse them into the registry; externalize only the consumer set + allow-list.
- **DIR-041 self-consistency.** The registry must not reintroduce `file:line` rot. Anchoring is `_ratchet_keys.composite_key` + AST symbols only; the schema validator must **reject** any positional `file:line` field.

**What stays advisory vs enforcing in v1:**
- **Enforcing (v1):** the schema validator (`doctor contracts` — malformed record fails) and the registered-completeness gate (generalized `test_unregistered_shim_scanner.py` — a `__deprecated__` module absent from the registry fails). These are structural and safe.
- **Advisory (v1):** the retirement absence-sweep + completeness arm — **report-only**, per-record `enforcement: advisory`. A record opts into `enforcing` only after its consumer set is proven stable. The one already-enforcing precedent (`doctor shim-registry` overdue check) stays enforcing.

**Conservative first increment:** introduce model + schema + loader + validator + `doctor contracts`; seed with **one** contract already fully caught today (e.g. the `status_emit` fallback-name, or one `test_no_legacy_*` retirement) **with its real declared consumer set**; wire `doctor contracts` to validate well-formedness; **delete nothing, enforce nothing new.** This proves the model end-to-end at near-zero blast radius.

---

## 7. Proposed WP breakdown (for the follow-up implementation mission)

**WP1 — Contract Record model (MVP, self-contained; WP1 is a safe standalone slice).**
Schema authority `docs/contracts/contract-registry-schema.yaml`; manifest `docs/contracts/contract-registry.yaml` seeded with **one** record (a `fallback_name` or `retired_literal` already caught today) **including its declared consumer set**; loader+validator `src/specify_cli/contracts/registry.py` (generalized from `compat/registry.py`); `spec-kitty doctor contracts` validating well-formedness; promote `_ratchet_keys.py` to a shared anchoring lib. **No enforcement change, nothing deleted.** Proves model + one adopted consumer set.

**WP2 — Retirement-verification driver, static arm (= CT7/#2077 payload).**
One content-anchored absence-sweep (`tests/architectural/test_retired_contracts_absent.py`) driven by `status=retired` records, using `composite_key` anchoring, with a mandatory anti-vacuity negative control (planted reappearance is flagged). **Advisory/report-only.** The WP1-seeded record proves it bites.

**WP3 — Adopt the `test_no_legacy_*` family (highest ad-hoc-debt payoff, lowest blast).**
Model the 4 hand-written sweeps' terms/symbols/paths as `retired_literal`/`fallback_name` records with declared consumers + exemptions; prove parity against the driver; then retire the 4 files behind the single driver (coverage preserved first). Directly discharges CT7/#2077's "mechanise into a single content-anchored, allowlist-free sweep."

**WP4 — Adopt the write-side ratchet consumer sets (higher blast).**
Externalize `_ADOPTED_MODULES` + `_ALLOW_LIST_SEED` from `test_no_write_side_rederivation.py` (and siblings `test_write_surface_placement_guard`, `test_topology_inference_retired`) into records' `consumers.call_sites` + `deferred_residuals`. **Detectors stay**; only the hand-maintained literals move.

**WP5 — Dynamic arm + completeness arm.**
Wire #2438 `pre_review_gate` (once landed) to read `consumers.test_shards` from records instead of re-deriving; add the completeness arm (every declared consumer migrated to `replaced_by`); extend `doctor contracts` from overdue-detection to consumer-completeness.

**WP6 (optional) — Enforcement flip + advisory enrichment + rulebook.**
Flip `advisory → enforcing` per proven-stable record; add `stale_assertions` registry-aware confidence/owner-attribution; author `docs/contracts/contract-ownership-rules.md` + `doctor contracts` remediation guidance.

---

## 8. Open decisions for the operator

1. **Manifest home & fold-vs-sibling.** New `docs/contracts/contract-registry.yaml`, OR extend `docs/migrations/shim-registry.yaml` in place. And: **fold** shim-registry INTO the contract registry (one artifact, one-time migration + `doctor shim-registry` re-point), OR keep shim-registry as the `fallback_name` specialization and add the contract registry alongside (less disruption, two artifacts). *Recommendation: new sibling registry that reuses the shim schema/loader chain; fold shim-registry in a later WP once the model is proven.*
2. **Enforce-vs-advisory for v1.** *Recommendation: advisory for the new absence-sweep + completeness arm; only the structural validator + registered-completeness gate enforce in v1.* Operator confirms whether WP1's seeded record enforces or reports.
3. **Which existing mechanism to adopt first.** *Recommendation: the `test_no_legacy_*` family (WP3) — it IS the #2077 payload, lowest blast, highest ad-hoc-debt payoff — before the write-side ratchets (WP4, higher blast).*
4. **Consumer-set provenance.** Hand-declared vs **discovered-then-frozen** (import/call-graph via `test_no_dead_symbols`'s resolver or codegraph). *Recommendation: discovered-then-frozen + reviewed, never hand-typed blind — a wrong list is worse than no list.*
5. **Retirement trigger wiring.** Manual manifest `status` edit vs a CT7-emitted retirement event. Must be coordinated with #2077's ownership boundary.
6. **CI pole / scan scope.** `docs/contracts/` docs-scoped (matches shim-registry + `test_no_legacy_terminology` `docs_scoped` markers) vs `.kittify/` governance. Affects which pole scans the manifest. *Recommendation: docs-scoped, mirroring the precedent.*
7. **`signature`-kind scope for v1.** Whether v1 models `signature` contracts at all, or defers to `fallback_name` + `retired_literal` (the two kinds with existing catch-mechanisms) and adds `signature` once the `test_no_dead_symbols` import-graph seam is wired as the consumer-discovery source.

---

## 9. Traceability

- Requirements → #2441 (parent ownership-model gap), CT7/#2077 (sweep mechanisation), #2438 (dynamic arm), #2283 (surfacing boundary), DIR-041 (governing directive).
- Real mechanisms grounded: `tests/architectural/{test_no_write_side_rederivation,_ratchet_keys,test_write_surface_placement_guard,test_gate_read_literal_ban,test_topology_inference_retired,test_no_legacy_terminology,test_no_legacy_status_emit_callers,test_unregistered_shim_scanner,test_no_dead_symbols}.py`; `tests/audit/{test_no_legacy_agent_profiles_path,test_no_legacy_path_literals}.py`; `src/specify_cli/post_merge/stale_assertions.py`; `src/specify_cli/compat/{registry,doctor}.py`; `docs/migrations/shim-registry.yaml`; `src/doctrine/directives/built-in/041-tests-as-scaffold-not-friction.directive.yaml`.
