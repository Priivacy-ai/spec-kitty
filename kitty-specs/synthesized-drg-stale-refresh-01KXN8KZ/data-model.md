# Data Model: Synthesized DRG Stale-Refresh Fix

**Mission:** `synthesized-drg-stale-refresh-01KXN8KZ` · Fixes [#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681)

See `research.md` for the rationale (and the live-code fact table) behind every
decision recorded here. This revision folds the post-plan squad's blockers plus
a `verify_manifest_hash` backward-compat break found during re-verification.

## Entity: `SynthesisManifest` (schema change)

File: `src/charter/synthesizer/manifest.py`

| Field | Before | After (WP01) | After (WP02) | Volatility |
|-------|--------|--------------|--------------|------------|
| `schema_version` | `Literal["2"] = "2"` | `Literal["2","3"] = "2"` (widen literal, **keep default `"2"`**) | `Literal["2","3"] = "3"` (bump default) | n/a (discriminant) |
| `bundle_content_hash` | *(does not exist)* | `str \| None = None` (added WP01) | *(unchanged)* | **Substantive (non-volatile)** — must NOT be added to `write_pipeline._VOLATILE_MANIFEST_FIELDS` |

**Why the default bumps in two steps (round-2 MAJOR):** `promote`
(`write_pipeline.py:668`) and `_rewrite_manifest` (`resynthesize_pipeline.py:188`)
hardcode `"schema_version": "2"` in their hashed `manifest_data_without_hash`
dict but construct `SynthesisManifest(...)` with NO `schema_version` kwarg
(model default). Bumping the default to `"3"` at WP01 would write a `"3"`
instance whose hash was computed over `"2"` → `verify_manifest_hash` RAISES →
`test_promote_writes_manifest_with_valid_self_hash` +
`test_resynthesize_kind_slug_is_no_op_stable_when_content_unchanged` go RED at
the WP01 boundary. So WP01 keeps the default `"2"` (all four sites
self-consistent, field `None` everywhere → verify green); WP02 bumps the
default to `"3"` **atomically** with converting `promote`/`_rewrite_manifest`
to build `SynthesisManifest` instances routed through `finalize_manifest`
(removing the hardcoded `"2"` raw-dict literals). `apply_post_condition` passes
`schema_version=manifest.schema_version` explicitly, so it is unaffected. The
**fresh-seed** manifest stays `schema_version: "2"` intentionally (see below).

`bundle_content_hash` holds the `sha256:`-prefixed digest returned by
`charter.bundle.compute_bundle_content_hash` (Decision 5). Populated with a real
value only by the synthesize/resynthesize writers (WP02); left `None` on
built-in-only seeds and post-condition flips (the reader short-circuits on
`built_in_only` before the comparison).

**Backward compatibility:** `extra="forbid"` rejects *unknown* keys, not
*absent* optional keys — a pre-fix v2 file (no `bundle_content_hash`, `"2"`)
still `model_validate`s (widened literal accepts `"2"`; field defaults `None`).
BUT adding the field is NOT free on the integrity surface — see the mandatory
`verify_manifest_hash` shim below.

## Contract: `finalize_manifest` (single canonical manifest finalizer)

**New symbol:** `src/charter/synthesizer/manifest.py::finalize_manifest(manifest:
SynthesisManifest) -> SynthesisManifest`

```
Recompute manifest_hash from the FULL instance and return an updated copy:
    zeroed = manifest.model_copy(update={"manifest_hash": "0" * 64})
    return manifest.model_copy(
        update={"manifest_hash": compute_manifest_hash(zeroed)})
```

Every manifest-persisting site builds/modifies a `SynthesisManifest` INSTANCE
and calls `finalize_manifest` immediately before writing. This eliminates the
per-site raw `manifest_data_without_hash` dicts and explicit-kwarg
reconstructions that caused BLOCKER-1 (dropped field) and BLOCKER-2 (dict/instance
divergence). Behavior-preserving: identical content → identical `manifest_hash`
to today's `compute_manifest_hash` path.

### Complete set of manifest-persist consumers (FOUR — squad found three)

| Site | Role | `schema_version` | `bundle_content_hash` | Finalizer landed in |
|------|------|------------------|-----------------------|---------------------|
| `write_pipeline.promote` (inline builder, `manifest_override is None`) | Writer — synthesize | `"3"` from model default after WP02 bump (drop hardcoded `"2"` dict) | Computed via helper (real value) | WP02 |
| `resynthesize_pipeline._rewrite_manifest` | Writer — resynthesize (needs `repo_root` threaded, `:95-99,447`) | `"3"` from model default after WP02 bump (drop hardcoded `"2"` dict) | Computed via helper (real value) | WP02 |
| `project_drg.apply_post_condition` (`:321`) | Built-in-only flip (BLOCKER-1) | `=manifest.schema_version` explicit (preserved) | **Preserved unchanged** via `model_copy` (never recomputed here) | WP02 |
| `src/specify_cli/cli/commands/charter/_fresh_doctrine.py::_fresh_seed_manifest_text` (`:78-82`, raw `hashlib`) | Built-in-only fresh seed | **stays `"2"`** (explicit in `without_hash`; intentional — see note) | Stays `None` | **WP01** (raw-`hashlib` path desyncs on the bare field addition — fact #15) |

**Fresh-seed `schema_version` stays `"2"` intentionally:** the reader
short-circuits on `built_in_only` before any version/hash check, and
`versioning.py`'s v2 repair guards on `!= "2"`. Bumping it to `"3"` would only
perturb `test_bundle_validate_fresh_seed.py`'s golden with no benefit.
Documented so a later agent does not "fix" it. The WP01 reroute through
`finalize_manifest` changes only the self-hash computation (raw-`hashlib` →
model-normalized), not the version.

`src/doctrine/versioning.py::_compute_v2_synthesis_manifest_hash` is a v2-only
migration/repair path (guarded by `schema_version != "2": return`) — out of
scope; it correctly stays within v2 field semantics.

## Contract: `verify_manifest_hash` backward-compat shim (MANDATORY with the field)

File: `src/charter/synthesizer/manifest.py::verify_manifest_hash`

`compute_manifest_hash` normalizes through the model, so after the field is
added it includes `bundle_content_hash: None` in the recomputed digest. Every
existing on-disk **v2** manifest was hashed WITHOUT the field → `verify_
manifest_hash` would RAISE (empirically: stored `abc25ece…` vs recomputed
`c15b61e0…`). The current legacy fallback only fires when `built_in_only` is
absent, so it does NOT cover this.

**Required change (WP01) — precise recipe (round-2 MEDIUM):** generalize the
legacy fallback to recompute via **raw** `hashlib.sha256(canonical_yaml(subset))`
over EXACTLY the `_raw_field_names` subset:

```
subset = {k: v for k, v in manifest.model_dump(mode="python").items()
          if k in manifest._raw_field_names and k != "manifest_hash"}
if hashlib.sha256(canonical_yaml(subset)).hexdigest() == manifest.manifest_hash:
    return
```

- **Per-field gated by `_raw_field_names`**, NOT a fixed pop-list that always
  drops `bundle_content_hash`.
- **Raw `hashlib`, NOT `compute_manifest_hash`** — the latter re-normalizes and
  re-adds model defaults (re-injecting `bundle_content_hash: None`), collapsing
  the fallback into the primary check.
- Subsumes the existing `built_in_only`-absent special-case.
- **Preserves tamper detection:** a v3 file that carries a *present* but
  tampered `bundle_content_hash` has that key in `_raw_field_names` → the subset
  includes the tampered value → recompute mismatches → RAISE. Pinned by a WP01
  red-first test (mutated present field → verify raises), distinct from the
  "absent key → passes" case.

Without this, `validate_synthesis_state` (`charter status`/`doctor`/`bundle
validate`) and the migration tests (`test_charter_bundle_v2_migration.py`,
`test_versioning.py`) go red on all unmigrated projects.

## Contract: shared reader/writer helper

**New symbol:** `src/charter/bundle.py::compute_bundle_content_hash(repo_root:
Path) -> str | None` (+ `BUNDLE_CONTENT_HASH_FILES` constant). **Lands in WP01
as a PURE, UNWIRED helper** (no callers until WP02 writers / WP03 reader →
behavior-inert, red-first preserved). WP03's AS-1 "fresh" fixtures call the
REAL helper to seed a correct `bundle_content_hash`, so there is one canonical
recipe (C-005) and no risk of a hand-copied fixture diverging from the
WP02/WP03 helper.

```
Input:  repo_root — absolute project root.
Reads:  the four files in BUNDLE_CONTENT_HASH_FILES (same names as
        computer.py::_BUNDLE_FILES) under repo_root/.kittify/charter/.
Method: hash EACH file independently via charter.hasher.hash_content()
        (per-file BOM-strip + CRLF-normalize), then combine deterministically:
        hash_content("\n".join(digests_in_declared_order)).
        Per-file (NOT concat-then-hash-once): a BOM on files 2-4 would else
        survive → #2009-class false-stale for AS-1 machine migration (fact #14).
        No raw hashlib → TID251 clean.
Output: "sha256:<hex>", deterministic for fixed file CONTENT (mtime-agnostic,
        call-site-agnostic) — the basis for no-op-stable convergence (C-001).
        None when .kittify/charter/ is missing OR any of the four files is
        individually missing/unreadable (OSError, UnicodeDecodeError) —
        fail-safe: the reader maps None → stale, never a crash (spec
        fail-posture, spec.md:47).
```

Consumers: `promote` + `_rewrite_manifest` (eager import); `computer.py`
reader (LAZY import inside `_compute_synthesized_drg`, LD-3/NFR-003).

## Behavior change: read-side comparison

File: `src/specify_cli/charter_runtime/freshness/computer.py`,
`_compute_synthesized_drg` (currently `:337-443`).

**Preserved (no behavior change):**
- `built_in_only` branch incl. graph-residue diagnostic (`:356-382`).
- `not graph_exists` → legacy-fresh-seed + `missing` (`:384-397`).
- `synced_bundle.state != "fresh" or last_change is None → stale` precedence
  (`:402-409`) — upstream-bundle staleness still wins first.

**Replaced:** the block `:411-441` (the `bundle_ts` parse + `manifest_ts`
cascade + `manifest_ts + 1.0 < bundle_ts` comparison) becomes:

```
current_hash = compute_bundle_content_hash(repo_root)   # lazy import
stored_hash = manifest.bundle_content_hash if manifest is not None else None
if stored_hash is None or current_hash is None or stored_hash != current_hash:
    → stale (remediation="spec-kitty charter synthesize")
else:
    → fresh
```

**Dead-name removals (do NOT claim verbatim preservation, per squad):**
`manifest_exists` (`:352`) and `bundle_ts` (`:412`) become unreferenced once
the `manifest_ts`/`bundle_ts` cascade is gone — remove both. Both comparands are
now hashes, so no timestamp is parsed and the old `ValueError` early-return on a
malformed `synced_bundle.last_change` no longer has an input to guard; it is
removed with the cascade (the `synced_bundle`-precedence branch already handles
a non-fresh/absent `last_change`).

| Manifest state | Result | Requirement |
|---|---|---|
| Post-fix, content unchanged (mtime bumped) | `fresh` | AS-1, FR-001 |
| Post-fix, doctrine content edited | `stale` | AS-2, FR-002 |
| Pre-fix v2 (no `bundle_content_hash`) | `stale` → self-heals in one remediation | AS-4, pre-fix-manifest edge case |
| `manifest is None` (corrupt/unreadable) | `stale` (explicit fail-posture, recoverable) | spec fail-posture |
| Any file missing/unreadable → helper `None` | `stale` | spec fail-posture |
| Clock skew / non-monotonic mtimes | unaffected (no timestamps compared) | edge case |

`graph_mtime_iso` (the `last_change` display value) is unchanged.

## Migration / backfill behavior (pre-fix manifests)

No migration script. Self-heal is structural (Decision 3 / fact #11): a pre-fix
manifest is read as `stale` (field `None`) → the prescribed remediation
(`synthesize`/`resynthesize`) writes a fresh `"3"` manifest with the real
`bundle_content_hash` (the textual no-op diff finds it substantively different →
rewrites once) → next read is `fresh`. Exactly one remediation invocation
(AS-4), no manual edit (C-004), identical via both entry points (FR-003/AS-3).
Independently, the `verify_manifest_hash` shim keeps the pre-fix v2 manifest's
integrity check GREEN in the interval before that remediation runs.

## Contract-doc updates required (FR-007)

- `computer.py` module docstring (`:9-12`, "Detection rules") — corrected in
  WP03 so the file isn't self-contradictory mid-mission.
- `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/charter-status-json.md`
  ("Staleness computation", `:41-51`) — corrected in WP04. See `contracts/`.
