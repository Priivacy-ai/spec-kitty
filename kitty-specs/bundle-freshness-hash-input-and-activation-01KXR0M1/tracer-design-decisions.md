# Tracer — Design Decisions

Mission: `bundle-freshness-hash-input-and-activation-01KXR0M1` (bundles #2758 + #2759).
Base: stacked on `fix/2681-synthesized-drg-stale` (PR #2732), which introduced the
`bundle_content_hash` content-identity freshness mechanism.

## DD-1 — Bundle #2758 + #2759 as one mission; defer #2760 (operator-confirmed)

Both #2758 and #2759 are the same `bundle_content_hash` content-identity seam (wrong hash
input-set + activation-invisibility); fixing one in isolation worsens the other. #2760 is a
disjoint DRG-overlay surface soft-coupled to the in-flight epic #2721 — deferred until #2721's
built-in-DRG shards settle. Two missions, not three; not one-of-three-separate.

## DD-2 — Fix direction pivoted A → C (post-spec adversarial squad)

**Rejected — Direction A** (recompile `references.yaml` on activate): two code-verified blockers.
(1) `write_compiled_charter` rewrites the human-authored, tracked `charter.md` together with
`references.yaml` — activate would silently clobber a human doc. (2) `_write_references_yaml`
bakes an unconditional `generated_at` timestamp (compiler.py:1239) → every recompile, even a
no-op activate, moves the hash.

**Rejected — Direction B** (freshness-marker invalidation): breaks `commit_plan`'s documented
single-write invariant (activation_engine.py:366-372) and composes two independent staleness
detectors (violates single-recipe).

**Adopted — Option C**: hash a **canonical extract of the project's activation state** (read via
the canonical `PackContext` reader) and **remove the derived, sometimes-absent `references.yaml`**
from the identity. Closes both blind spots, touches `bundle.py`/`computer.py`/the synthesize write
path only, and — critically — **never touches `activate`/`deactivate`**, which dissolves the
entire #2721 coordination hazard that originally routed #2759 to the epic.

## DD-3 — Key-set is `YAML_KEY_MAP.values()` (9 keys), not the naive 6

Squad caught an initial grounded-fact error: the activation state spans 8 `activated_*` keys +
the `mission_type_activations` outlier. `mission_type_activations` is **excluded** from the
identity by default (its absent-default is a version-dependent `mission_types/` disk scan →
upgrade churn; NFR-002/OQ-2).

## DD-4 — Scope: signal-correctness, NOT `references.yaml` content-correctness

Removing `references.yaml` from the identity leaves its runtime content-correctness vs `config.yaml`
undetected — but #2732 never detected it either, and pulling `references.yaml` into the manifest is
an ADR-deferred rework (`06_unified_charter_bundle.md:52-56`). A `fresh` synthesized_drg explicitly
does NOT imply `references.yaml`/runtime-context currency. Surfacing that is a separate follow-up
for the operator, not smuggled in via a recompile.

## DD-6 — Activation identity re-based on the synthesizer's graph inputs (plan-gate correction)

The plan-gate architecture lens proved the "8 `activated_*` keys via `_load_default_pack` effective-set"
model was a **third disagreeing authority** that fingerprints a different object than `graph.yaml`:
the synthesizer feeds the graph ONLY `selected_directives` (`[] if activated_directives is None else
resolved`, the #2577 rule) + `selected_paradigms` (`_synthesis.py:57-112`). The 8-key model produced
guaranteed false-stale for the 6 non-graph kinds (activate an agent-profile → hash moves → synthesize →
byte-identical graph → re-bake fresh = no-op-synthesis churn) and false-fresh on the `[]`→default
materialization.

**Corrected design:** hash the digest of the synthesizer's resolved graph inputs (directives+paradigms),
via a shared charter-side helper extracted from `_synthesis.py` and called by BOTH the synthesizer and
`compute_bundle_content_hash` — attest the graph *by construction*, single authority, no drift. This
**dissolves OQ-6 and OQ-7** (absent-key handling is correct by mirroring the synthesizer; no
`_load_default_pack` version-coupling; the resolver is reused, not re-invented). Semantic consequence,
made explicit in the spec: activating a NON-graph kind (tactic, agent-profile, …) correctly leaves
`synthesized_drg = fresh` — the graph does not derive from it; reporting stale there would be a
false-stale. Their effect on `references.yaml`/runtime context remains the separate scoped-out concern.

## DD-7 — Final convergence: activation identity = resolved DIRECTIVES only (plan-gate round 2)

Plan-gate round 2 refined DD-6 twice more:
- **Architecture lens (MAJOR):** `selected_paradigms` is *set* on the synthesizer's interview snapshot but
  **inert** — nothing in `synthesizer/` consumes it, so a paradigm-only change leaves `graph.yaml`
  byte-identical. Including paradigms reinstated the false-stale/version-coupling defect class (paradigms
  also lack the #2577 absent→`[]` guard). **Resolution: digest = resolved DIRECTIVES only** — the sole
  activation input that varies `graph.yaml`. #2759 is fixed precisely for directive activation; paradigm/
  tactic/etc. correctly stay `fresh`.
- **Root-cause lens (MAJOR):** the re-base onto `resolve_config_activated_roots` introduced an uncaught
  `UnknownArtifactIdError` (a `ValueError`) crash path — a drifted config stem (in ANY kind) would crash the
  `charter status` freshness read (a never-raise/NFR-003 violation absent pre-mission). **Resolution:**
  `compute_bundle_content_hash` catches resolver exceptions → `None` → recoverable stale; red-first
  drifted-stem test.
- Mediums folded: scope the "attest by construction" prose to *directive* variation (the graph also derives
  from interview *answers* — a pre-existing out-of-scope gap); the `bundle→compiler` import is
  **function-local** (NFR-001 hot-path); the per-`charter status` `load_doctrine_catalog()` cost is bounded
  by the < 2s envelope (NFR-002).

Net: five squad rounds drove the identity from "8 config keys" → "directives+paradigms" → **"resolved
directives only, fail-safe"** — the irreducible, correct, minimal fingerprint of what `graph.yaml`'s
activation-derived content actually is.

## DD-8 — WP02 short-circuit of WP01's helper (cross-WP refinement, implement-phase)

WP02's #2759 change routed `compute_bundle_content_hash` through
`resolve_synthesis_graph_directives` → `resolve_config_activated_roots` → uncached
`load_doctrine_catalog()` (~1-2s, 354-file glob) on every `compute_freshness`. This broke two
pre-existing perf ratchets (`test_compute_freshness_under_2_seconds`,
`test_warm_path_under_300ms`) — both seed a repo with **absent** `activated_directives`, where the
helper returns `[]` regardless yet still paid the catalog load. **Fix (implement-phase, WP02):**
reorder the WP01 helper in `src/charter/compiler.py` to short-circuit `[]` on absent-directives
**before** resolving — so the freshness read never loads the catalog for a project with no
activated directives. Red-first pin: `test_absent_directives_skips_catalog_load` (spies that
`resolve_config_activated_roots` is not called).

**Cross-WP note (governance truthfulness):** this touched `compiler.py` + `test_synthesis_graph_directives.py`
(WP01's declared surface) during WP02 — a sequential single_branch refinement of WP01's helper
driven by WP02's new caller, not a scope leak. **It supersedes WP03 T007's original "add an
NFR-002 caching fallback" guidance** (obsolete: the absent-directives case is now fast via the
short-circuit; caching `load_doctrine_catalog` was rejected — test-isolation + one-shot-CLI-cold
concerns). Residual: a **config-PRESENT** freshness read still pays one ~1s cold catalog load — the
inherent cost of the vetted attest-the-graph (resolve-via-helper) design, **within the charter's
<2s CLI NFR**. Flagged for the PR body; a faster raw-config-stem hash (decoupled from the
synthesizer's resolution) is a possible fast-follow if upstream deems ~1s too slow.

## DD-5 — Carried into Plan as mandatory OQs (with candidate resolutions)

- OQ-4 fail-posture: reconcile `compute_bundle_content_hash` never-raise vs `PackContext`
  fail-closed for malformed config (map malformed→recoverable-stale, never permanent).
- OQ-6 the sharp one: absent-key three-state normalization creates a genuine **SC-003 (no-op
  stability) ↔ NFR-002 (no upgrade-churn)** conflict for the artifact-kind keys. Candidate: hash
  the *effective* activated set (resolve None→default once), treating a deliberate `default.yaml`
  change as a correct one-time migration stale (FR-007), not churn. Both reviewers judged this
  plan-resolvable and non-blocking.
