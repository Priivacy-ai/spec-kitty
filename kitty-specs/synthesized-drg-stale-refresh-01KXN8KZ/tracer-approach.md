# Mission Tracer — Approach

**Mission:** `synthesized-drg-stale-refresh-01KXN8KZ` · Fixes [#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681)

> Seeded at tasks-authoring time. Implementers append notes per WP as they
> work; assessed at mission close (WP04, T026).

## The defect (why we are here)

A synthesized-DRG project can become permanently stuck reporting
`synthesized_drg: stale`. `_compute_synthesized_drg`
(`src/specify_cli/charter_runtime/freshness/computer.py`) judges freshness by
comparing the synthesis manifest's `created_at` — deliberately frozen on
no-op runs by the #1912/#1913 clean-tree fix — against the synced bundle's
raw mtime, which advances on any ordinary git operation (clone, checkout,
rebase, machine migration) even without a content change. Once the frozen
timestamp falls behind, no prescribed remediation can catch it up, because the
only write that would refresh it is the exact no-op write #1912/#1913
correctly suppresses.

## The chosen approach: content-identity, not timestamps

Freshness is redefined to reflect whether the synthesized graph still matches
the **doctrine/bundle content** it was built from — not incidental filesystem
timestamps — while fully preserving the clean-tree guarantee #1912/#1913
introduced.

- A new **substantive (non-volatile)** `bundle_content_hash` field on
  `SynthesisManifest`, produced by ONE shared helper
  (`charter.bundle.compute_bundle_content_hash`, per-file `hash_content` over
  the four synced-bundle files), persisted by every manifest writer through
  ONE canonical finalizer (`manifest.finalize_manifest`), and compared at read
  time against a freshly recomputed hash.
- Equal → `fresh`; differ, or a pre-fix manifest lacking the field → `stale`,
  self-healing in exactly one remediation run (the new non-volatile line
  survives the no-op-stable text diff, so the first `synthesize`/`resynthesize`
  after the fix rewrites once, then holds stable).

## Why mtime-tolerance was ruled out (determined design outcome, spec AS-1/AS-2)

Filesystem mtimes are not a reliable freshness signal across git operations.
A genuine content edit and an innocuous git-operation mtime bump are
indistinguishable in timestamp-space (both set mtime to "now"); machine
migration produces unbounded jumps; clock skew must not by itself trip
`stale`. Only content identity satisfies AS-1 (fresh survives mtime
perturbation) and AS-2 (genuine change → stale) together. Rejected
alternatives: mtime-tolerance/threshold heuristics (cannot separate edit from
git-op bump) and refresh-`created_at`-on-stale (couples the reader to a write
side-effect, churns the tree on every `stale` re-check).

## Scope discipline (seed-only)

Fixes the one in-scope defect (#2681). Preserves the #1912/#1913
no-op-stable write (C-001). Out of scope and NOT folded: #1914 (umbrella),
#2157 (different terminal state — `MISSING`), #2373 (different code surface —
`build_charter_context`); #2009 is explicitly-not-related (a shipped BOM/CRLF
fix, different mechanism). Known deferred limitation (research.md Decision 2):
`charter activate`/`deactivate` mutate `config.yaml` but do not rewrite the
bundle files until a later `sync`/compile, so an activate/deactivate is
invisible to a hash over `references.yaml` until that recompile — pre-existing
(the old mtime code had the identical blind spot), orthogonal to this fix,
noted for a future issue.

## Implementation notes (appended during implementation)

- _(WP01 — append notes here)_
- _(WP02 — append notes here)_
- _(WP03 — append notes here)_
- **WP04 — mission-close assessment (2026-07-16):** the chosen approach held
  end to end. WP01 landed the schema field + `finalize_manifest` + the
  per-field `verify_manifest_hash` shim + the pure, unwired
  `compute_bundle_content_hash` helper (`759d24fa6`); WP02 wired the helper
  through all four manifest-persist sites via the single finalizer,
  including the `apply_post_condition` built-in-only-flip preserve
  (`d6bc124e7`); WP03 swapped `_compute_synthesized_drg`'s comparison from
  the mtime cascade to the content-identity comparison, removing the dead
  `manifest_exists`/`bundle_ts` names (`fc679f573`) — the terminal fix for
  #2681. WP04 closed the loop: corrected the external
  `charter-status-json.md` contract doc (FR-007, reviewer-attested — no
  automated pin exists for a `kitty-specs/` prose doc), added a permanent
  NFR-002 perf ratchet (`compute_freshness` observed ~3.7ms locally,
  ~500x under the 2.0s budget), and re-ran the full mission-affected-surface
  sweep (1693 tests) plus the C-001/NFR-001 no-op-stability guards green.
  No approach deviation was required at closeout.
- **Deferred/out-of-scope limitation carried to close (research.md Decision
  2):** `spec-kitty charter activate`/`deactivate` mutate
  `.kittify/config.yaml` (the `references.yaml` activation source) but do
  not themselves rewrite the four bundle files until a subsequent
  `charter sync`/compile — until that recompile, an activate/deactivate is
  invisible to `compute_bundle_content_hash`. This is a **pre-existing**
  blind spot (the old mtime code had the identical gap; `config.yaml` was
  never in `_BUNDLE_FILES` and its mtime was never compared either) and is
  explicitly out of scope for this mission — not folded in, not silently
  "fixed" by expanding the hashed file set beyond the synced-bundle
  contract (C-005/C-006 reuse the existing `charter_source` pattern; adding
  `config.yaml` would invent a fourth divergent input set). Left as a named,
  documented limitation for a future issue.
