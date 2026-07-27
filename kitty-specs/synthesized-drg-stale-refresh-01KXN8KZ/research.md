# Research: Synthesized DRG Stale-Refresh Fix

**Mission:** `synthesized-drg-stale-refresh-01KXN8KZ` · Fixes [#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681)

This document records the live-code facts verified against the current
`fix/2681-synthesized-drg-stale` branch and the design decisions they ground.
The overall approach (content-identity freshness, single writer, single
reader, non-volatile field) was decided before planning began (C-005/C-006).
The **post-plan adversarial squad** found three blockers plus majors; this
revision folds them all, re-verified against live code. Two of the squad's
concerns plus one additional finding of my own (a `verify_manifest_hash`
backward-compat break) materially change the writer-side design — recorded
below as Decisions 3, 5, and 6.

## Verified live-code facts

| # | Fact | Citation |
|---|------|----------|
| 1 | `_BUNDLE_FILES = ("governance.yaml", "directives.yaml", "references.yaml", "metadata.yaml")` — `references.yaml` IS included. | `src/specify_cli/charter_runtime/freshness/computer.py:125` |
| 2 | Defective comparison: `if manifest_ts is not None and manifest_ts + 1.0 < bundle_ts: → stale`, `manifest_ts` prefers `manifest.created_at` (frozen by #1912/#1913 on no-op runs), `bundle_ts` is `synced_bundle.last_change` (raw mtime, advances on git ops). | `computer.py:411-441` (comparison at `:436`) |
| 3 | `synced_bundle.state != "fresh"` precedence branch (preserve) returns `stale` before the comparison. | `computer.py:402-409` |
| 4 | `built_in_only` (+graph-residue) and `missing`/legacy-fresh-seed branches sit above the comparison — untouched by this fix. | `computer.py:356-397` |
| 5 | `SynthesisManifest.schema_version: Literal["2"] = "2"`, `model_config = ConfigDict(frozen=True, extra="forbid")`. `mission_id: str | None = None` already exists — an optional field precedent. | `manifest.py:76-102` |
| 6 | `computer.py`'s manifest loader (`_load_synthesis_manifest_via_chokepoint`) catches ALL load exceptions → `manifest = None`. `load_yaml()` itself does NOT call `verify_manifest_hash` — it only `model_validate`s. So the READER tolerates a pre-fix v2 manifest (optional field defaults `None`, widened literal accepts `"2"`) without crashing. | `computer.py:179-204`, `manifest.py:150-175` |
| 7 | **`resynthesize_pipeline.run()` loads the on-disk manifest UNGUARDED**: `existing_manifest = load_manifest(manifest_path)` (no try/except). A strict `Literal["3"]` cutover would crash `resynthesize` on any pre-fix `"2"` manifest → confirms the widen-not-break decision. | `resynthesize_pipeline.py:379` |
| 8 | **Complete set of manifest-persist sites (squad found THREE; I confirm THREE `SynthesisManifest(` constructors + ONE raw-dict persist = FOUR total):** `write_pipeline.promote` (`:679`), `resynthesize_pipeline._rewrite_manifest` (`:199`), `project_drg.apply_post_condition` (`:321`), and `src/specify_cli/cli/commands/charter/_fresh_doctrine.py::_fresh_seed_manifest_text` (`:78-82`, uses raw `hashlib`, not the `SynthesisManifest(` constructor). `src/doctrine/versioning.py`'s `_compute_v2_synthesis_manifest_hash` is a v2-only migration/repair path guarded by `schema_version != "2": return` — out of scope. | grep of `SynthesisManifest(` + `manifest_hash` writes across `src/` |
| 9 | **BLOCKER-1 (verified).** `project_drg.apply_post_condition` (invoked UNCONDITIONALLY after every `synthesize()` from `orchestrator.py:194-197`) computes `manifest_hash = compute_manifest_hash(manifest.model_copy(update={"built_in_only": ..., "manifest_hash": "0"*64}))` — the `model_copy` PRESERVES `bundle_content_hash` — then reconstructs `SynthesisManifest(...)` via an **explicit kwarg list that OMITS `bundle_content_hash`** → the persisted instance reverts the field to `None` while the hash was computed over the real value → self-hash mismatch. Exercised by `tests/integration/test_charter_synthesize_built_in_only.py:118` (`verify_manifest_hash` after post-condition). | `project_drg.py:313-332`, `orchestrator.py:194-197` |
| 10 | `_VOLATILE_MANIFEST_FIELDS = frozenset({"created_at", "run_id", "synthesizer_version", "manifest_hash"})` — the new field must NOT be added here. | `write_pipeline.py:236-238` |
| 11 | Manifest no-op-stable skip (`promote()` step 4) diffs the **raw serialized text** of the fresh manifest vs. the on-disk file via `_substantively_equal()` → `kernel.atomic.substantively_equal()`, stripping only volatile-field lines. A new non-volatile `bundle_content_hash:` line (or changed `schema_version:`) is NOT stripped → substantive diff → self-heals in exactly one write (AS-4). | `write_pipeline.py:692-711`, `kernel/atomic.py:84-` |
| 12 | `manifest.verify()` / per-artifact `content_hash` = OUTPUT-artifact integrity; the new `bundle_content_hash` = INPUT currency. Complementary, both on the manifest, neither subsumes the other. | `manifest.py:255-303`, `:197-222` |
| 13 | `charter.hasher.hash_content(text) -> "sha256:<hex>"` normalizes leading BOM + CRLF/CR→LF + `.strip()` per its C2-e docstring (the #2009-class BOM/CRLF drift shim). `_charter_hash_of()` mirrors it. | `charter/hasher.py:15-42`, `computer.py:207-219` |
| 14 | **MAJOR (hashing correctness, verified).** `canonical_yaml()` includes None-valued keys (no None-dropping) and only strips a **leading** BOM of the whole payload. So concatenating raw file texts and hashing once would let a BOM on files 2-4 survive → a #2009-class false-`stale` under AS-1 machine migration. Per-file `hash_content()` (each file BOM/CRLF-normalized) avoids this AND avoids a raw `hashlib` call (TID251 gate). | `synthesize_pipeline.py:153-182` + empirical `canonical_yaml` probe |
| 15 | **Fourth-site break (verified empirically).** `src/specify_cli/cli/commands/charter/_fresh_doctrine.py::_fresh_seed_manifest_text` computes `manifest_hash = hashlib.sha256(canonical_yaml(without_hash))` over a raw dict that lacks `bundle_content_hash`, then WRITES `canonical_yaml(manifest.model_dump())` which (after the field is added) INCLUDES `bundle_content_hash:` → stored hash ≠ recomputable hash. Unlike the three constructor sites (which route through `compute_manifest_hash`, model-normalizing the `None` default), this raw-`hashlib` path desyncs on the **bare field addition**. | `_fresh_doctrine.py:67-82`; `canonical_yaml(without_key) != canonical_yaml(with_None_key)` probe |
| 16 | **NEW — backward-compat break in `verify_manifest_hash` (verified empirically, beyond the squad's list).** `compute_manifest_hash` normalizes via the model → after adding the field it includes `bundle_content_hash: None`. For an existing on-disk **v2** manifest (hashed WITHOUT the field), `verify_manifest_hash` recomputes a DIFFERENT digest (probe: stored `abc25ece…` vs recomputed `c15b61e0…`) → RAISES. The existing legacy fallback (`manifest.py:210-217`) only fires when `built_in_only` is ABSENT from the file; it does NOT cover `bundle_content_hash` absence → every post-Phase-7 v2 manifest (which HAS `built_in_only`) fails verify. This surfaces via `_check_manifest_integrity` → `validate_synthesis_state` (`charter status`/`doctor`/`bundle validate`) and migration tests (`test_charter_bundle_v2_migration.py`, `test_versioning.py`). MUST be fixed alongside the field addition. | `manifest.py:178-222`; `compute_manifest_hash`/`canonical_yaml` probe |
| 17 | **Field-addition is safe at WP01; a schema-DEFAULT bump is NOT (round-2 MAJOR, verified).** Two independent axes must be separated: (a) *adding* `bundle_content_hash: str \| None = None` — the three constructor sites use `compute_manifest_hash` (model-normalized), so with the value `None` everywhere the hash and instance agree → SAFE at WP01; they desync only once a **real** value flows (WP02), which is why BLOCKER-1/2 need the finalizer. (b) *bumping the model `schema_version` default* to `"3"` — `promote` (`write_pipeline.py:668`) and `_rewrite_manifest` (`resynthesize_pipeline.py:188`) HARDCODE `"schema_version": "2"` in their hashed `manifest_data_without_hash` dict but construct `SynthesisManifest(...)` with NO `schema_version` kwarg (relying on the model default). If WP01 bumped the default to `"3"`, the written instance would be `"3"` while its hash was computed over `"2"` → `verify_manifest_hash` RAISES → `test_promote_writes_manifest_with_valid_self_hash` (`test_write_pipeline.py:349`) + `test_resynthesize_kind_slug_is_no_op_stable_when_content_unchanged` (`test_orchestrator_resynthesize.py:240`) go RED at the WP01 boundary — an accidental-divergence RED indistinguishable from the intended #2681 RED. So WP01 WIDENS the literal to `Literal["2","3"]` but KEEPS the default `= "2"`; the default bump to `"3"` moves to WP02, done atomically with the finalizer conversion that removes the hardcoded `"2"` dict literals. `apply_post_condition` already passes `schema_version=manifest.schema_version` explicitly (`project_drg.py:322`), so it is unaffected by the default. | `write_pipeline.py:666-688`, `resynthesize_pipeline.py:186-208`, `project_drg.py:322` |
| 18 | `resynthesize_pipeline._rewrite_manifest(existing, new_results, run_id)` has NO `repo_root` param; `run()` has `_repo_root` in scope at the call site → thread it through to compute the bundle hash. | `resynthesize_pipeline.py:95-99, 447` |
| 19 | Reader dead-name removals after the swap: `manifest_exists` (`computer.py:352`, only used by the removed `manifest_ts` cascade) and `bundle_ts` (`computer.py:412`, only used by the removed comparison) become unreferenced. | `computer.py:352, 411-441` |
| 20 | The pipeline/freshness fixtures do NOT seed `.kittify/charter/{governance,directives,references,metadata}.yaml`: `repo_with_prior_synthesis` only runs `synthesize()` (which writes doctrine + manifest, not the sync-produced bundle files). The new comparison reads those four files, so fixtures must seed them for the hash to be meaningful. | `test_orchestrator_resynthesize.py:124-131`; bundle-file provenance in `bundle.py:10-23` |
| 21 | Flaky/symptomatic test to tighten: `test_charter_status_freshness.py:167` asserts `synthesized_drg.state in {"fresh","stale"}` — a live symptom of THIS bug (the assertion admits `stale` because the mtime rule is nondeterministic). Post-fix → `== "fresh"`. | `tests/integration/test_charter_status_freshness.py:167` |
| 22 | `AS-2` (genuine content change → `stale`) currently has NO dedicated test on the synthesized-DRG comparison path (`test_synthesized_drg_fresh_when_graph_followed_bundle` only covers the future-dated `2099-…` fresh sentinel, which never reaches the defective branch). | `tests/specify_cli/charter_freshness/test_computer.py:264-271` |
| 23 | FR-007 canonical contract doc: `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/charter-status-json.md:41-51` (still states the defective mtime rule); plus `computer.py:9-12` module docstring (same defective rule). | both files |

**Live code contradicts one premise of the squad's WP split** (fact #15 +
#16): adding the field is NOT "behavior-inert on the model only." It
immediately desyncs the fresh-seed raw-`hashlib` writer (#15) and breaks
`verify_manifest_hash` for existing v2 manifests (#16). The schema-addition
WP must therefore also carry the two backward-compat shims. This is the only
material deviation from the squad's prescribed WP boundaries; everything else
folds as directed. See Decision 6 and the plan's WP outline.

## Decisions

### Decision 1 — Content-hash freshness (not mtime-tolerance, not refresh-created-at)

Unchanged from the prior revision. Per spec Assumption 1 (a determined
outcome): mtimes are reset/advanced non-deterministically by git ops and a
real edit is indistinguishable from an mtime bump in timestamp-space. Only
content identity satisfies AS-1 and AS-2 together. Rejected: mtime-tolerance
(cannot distinguish edit from git-op bump; machine migration → unbounded
jumps; clock skew) and refresh-`created_at`-on-stale (couples reader to a
write side-effect, churns the tree on every `stale` re-check).

### Decision 2 — Hash the synced-bundle set (not `charter_hash`, not the raw doctrine tree)

Hash the four `_BUNDLE_FILES` (fact #1). `references.yaml` is the compiled
activated-doctrine selection synthesis consumes, so the set is a faithful
input proxy. `charter_hash` covers only `charter.md` (misses bundle-derivative
drift). Hashing `.kittify/doctrine/` (the OUTPUT) would make the check
self-referential and duplicate `manifest.verify()` (fact #12).

**Scoped limitation (named accurately, out of scope):** the **primary** drift
trigger this signal cannot see is `spec-kitty charter activate` /
`spec-kitty charter deactivate`, which mutate `.kittify/config.yaml` (the
activation source `references.yaml` is compiled from) but do NOT themselves
rewrite the four bundle files until a subsequent `charter sync`/compile. Until
that recompile lands, an activate/deactivate is invisible to a hash taken over
`references.yaml`. This is **pre-existing** — the old mtime code has the
identical blind spot (config.yaml is not in `_BUNDLE_FILES`, and its mtime was
never part of the comparison), it is orthogonal to the `stale` deadlock this
mission fixes, and the same class covers the pre-existing divergence between
`charter.bundle.CANONICAL_MANIFEST` (which excludes `references.yaml` per
C-012) and `computer.py::_BUNDLE_FILES` (which includes it). Noted for a
future issue; not folded into this mission's scope (C-002).

### Decision 3 — Store on `SynthesisManifest` as an OPTIONAL field; WIDEN (not break) `schema_version`

Add `bundle_content_hash: str | None = None` (mirrors the existing
`mission_id: str | None = None`, fact #5). Widen `schema_version` from
`Literal["2"]` to `Literal["2","3"]`. **The default is bumped in two steps
(fact #17):** WP01 widens the literal but KEEPS the default `= "2"` (so the
two writers that hardcode `"2"` in their hashed dict yet rely on the model
default in the constructor stay self-consistent → `verify_manifest_hash`
green); WP02 bumps the default to `"3"` **atomically** with the finalizer
conversion that removes those hardcoded `"2"` dict literals. New writes then
produce `"3"`; existing `"2"` files still validate throughout.

The **fresh-seed** manifest (`_fresh_doctrine`) intentionally STAYS
`schema_version: "2"` (it explicitly sets `"2"` in its `without_hash` dict, not
the model default): the reader short-circuits on `built_in_only` before any
version/hash check, and `versioning.py`'s v2 repair guards on `!= "2"`, so a
gratuitous bump to `"3"` would only perturb `test_bundle_validate_fresh_seed.py`'s
golden. Documented so a later agent does not "fix" it.

**Why not a strict `Literal["3"]` cutover:** `resynthesize_pipeline.run()`
loads the pre-existing manifest UNGUARDED (fact #7); a strict literal would
crash `resynthesize` — the very remediation FR-003/AS-3 requires — on any
pre-fix manifest. Widening is additive: old manifests parse
(`bundle_content_hash=None` → reader reports `stale` → backfill), new
manifests carry both markers.

**Self-heal (AS-4, single-pass):** a pre-fix manifest differs substantively
from the fresh candidate at the textual no-op check (fact #11 — the new/changed
non-volatile line is never stripped) → rewritten exactly once on the first
`synthesize`/`resynthesize` after the fix → next read is `fresh`. No second
bounce.

### Decision 4 — Reconciliation with `manifest.verify()` / `content_hash`

Unchanged. `verify()`/per-artifact `content_hash` = OUTPUT-artifact integrity;
`bundle_content_hash` = INPUT currency (fact #12). Complementary, both on the
manifest. `_compute_synthesized_drg` stays the single canonical READ authority
(C-005); the shared helper (Decision 5), called from every writer via the
finalizer (Decision 6), is the single canonical WRITE authority (C-006). No
third algorithm.

### Decision 5 — Shared helper: per-file hashing, fail-safe to `None`

`src/charter/bundle.py::compute_bundle_content_hash(repo_root: Path) -> str |
None` (+ `BUNDLE_CONTENT_HASH_FILES` naming the same four files):

- Hash **each** file INDEPENDENTLY via `charter.hasher.hash_content()` (per-file
  BOM-strip + CRLF-normalize, fact #13), then combine the four `sha256:`
  digests deterministically: `hash_content("\n".join(digests_in_declared_
  order))`. Per-file hashing is required (fact #14): concatenating raw texts
  and hashing once would let a BOM on files 2-4 survive → a #2009-class
  false-`stale` for AS-1 machine migration. This also keeps the helper off raw
  `hashlib` (TID251 clean).
- Return `None` when `.kittify/charter/` is missing OR **any** of the four
  files is individually missing/unreadable (`OSError`, `UnicodeDecodeError`).
  `_compute_synced_bundle`
  can report `fresh` with only 1-of-4 files present (`references.yaml` is
  produced by a separate compile stage), so the helper MUST tolerate
  partial/absent/unreadable inputs WITHOUT raising — `compute_freshness()` is a
  pure observer and a raise would crash `charter status`/preflight (spec
  fail-posture MUST, spec.md:47). `None` → the reader reports `stale`
  (fail-safe, recoverable via a prescribed remediation), never a crash.

**The helper lands in WP01 as a PURE, UNWIRED function** (round-2 MEDIUM): no
callers until WP02 (writers) / WP03 (reader), so it is behavior-inert and does
not break red-first. Landing it in WP01 lets WP03's AS-1 "fresh" fixtures call
the **real** helper to seed a correct `bundle_content_hash` instead of
hand-replicating the per-file-hash-then-combine recipe — a single canonical
recipe (C-005), avoiding a silent divergence if a hand-copied fixture differed
from the WP02/WP03 helper.

**Consumers (wired later):** writers (`promote`, `_rewrite_manifest`) import it
eagerly (already inside `charter.*`, WP02); the reader (`computer.py`) imports
it LAZILY inside `_compute_synthesized_drg` (LD-3/NFR-003 discipline, matching
the module's existing lazy `charter.bundle` / `charter.synthesizer.manifest`
imports, WP03). The eager-vs-lazy import discipline is a WP02/WP03 wiring
concern, not a WP01 one. `apply_post_condition` and
`src/specify_cli/cli/commands/charter/_fresh_doctrine.py` do NOT call the
helper — they only flip `built_in_only` / emit a built-in-only seed (reader
short-circuits on `built_in_only` before the hash comparison), so they preserve
whatever `bundle_content_hash` is present (or `None`) and rely on the finalizer
for self-hash consistency.

`computer.py::_BUNDLE_FILES` is left untouched and will hold the same four
names as `BUNDLE_CONTENT_HASH_FILES` by construction (minor intentional
duplication, to avoid pulling `charter.bundle` into computer.py's eager import
path for the unrelated `_compute_synced_bundle` code path). Consolidation
deferred.

### Decision 6 — ONE canonical manifest finalizer (closes BLOCKER-1 + BLOCKER-2 structurally)

The root cause of BLOCKER-1/2 is the "build a raw `manifest_data_without_hash`
dict, hash it, then separately construct/`SynthesisManifest(...)`" duplication
across the persist sites. Introduce a single helper in `manifest.py`:

```
finalize_manifest(manifest: SynthesisManifest) -> SynthesisManifest
    # recompute manifest_hash from the FULL instance and return a copy:
    return manifest.model_copy(
        update={"manifest_hash": compute_manifest_hash(
            manifest.model_copy(update={"manifest_hash": "0" * 64}))})
```

Every persist site builds/modifies a `SynthesisManifest` **instance** and calls
`finalize_manifest` before writing — eliminating the hand-synced dict literals.
This guarantees every field (incl. `bundle_content_hash`) is always in BOTH the
hashed payload and the persisted instance, structurally satisfying C-006
(write-side unification is structural, not test-enforced) and closing:

- **BLOCKER-1** — `apply_post_condition` builds its post-condition instance via
  `manifest.model_copy(update={"built_in_only": ...})` (which PRESERVES
  `bundle_content_hash`) then `finalize_manifest` — the explicit-kwarg
  reconstruction that dropped the field is deleted.
- **BLOCKER-2** — the raw `manifest_data_without_hash` dicts in `promote` and
  `_rewrite_manifest` are removed; the hash always derives from the full
  instance, so no field can be silently omitted.

**Behavior-preserving check:** for content identical to today, `finalize_
manifest` produces the same `manifest_hash` the current `compute_manifest_hash`
path produces (both hash the model_dump minus `manifest_hash`); the only
change to on-disk bytes is the additive `bundle_content_hash` /
`schema_version: '3'` lines — a one-time self-heal rewrite (Decision 3).

**Backward-compat shim (from fact #16 — MUST accompany the field addition;
round-2 MEDIUM tightened the recipe):** generalize `verify_manifest_hash`'s
legacy fallback to recompute via **raw** `hashlib.sha256(canonical_yaml(subset))`
over EXACTLY the `manifest._raw_field_names` subset — the keys the on-disk file
actually carried, `manifest_hash` excluded:

```
subset = {k: v for k, v in manifest.model_dump(mode="python").items()
          if k in manifest._raw_field_names and k != "manifest_hash"}
if hashlib.sha256(canonical_yaml(subset)).hexdigest() == manifest.manifest_hash:
    return   # legit pre-fix file (lacked the key) verifies
```

This is **per-field gated by `_raw_field_names`, NOT a fixed pop-list** that
always drops `bundle_content_hash`, and **NOT via `compute_manifest_hash`**
(which re-normalizes and re-adds model defaults — that would re-inject
`bundle_content_hash: None` and collapse the fallback into the primary check).
It subsumes the existing `built_in_only`-absent special-case. Crucially it
preserves tamper detection: a **v3** file that DOES carry a
`bundle_content_hash` key but with a tampered value has that key in
`_raw_field_names` → the subset includes the tampered value → recompute
mismatches → RAISE. A WP01 red-first test pins exactly that (mutated *present*
field → verify raises), distinct from the "absent key → verify passes" case.
Without this shim, adding the field makes `verify_manifest_hash` raise on all
unmigrated v2 projects (fact #16).

**Fourth-site fix (from fact #15):**
`src/specify_cli/cli/commands/charter/_fresh_doctrine.py::_fresh_seed_manifest_text`
is routed through `finalize_manifest` (replacing its raw
`hashlib.sha256(canonical_yaml(without_hash))`) so its written file's
`manifest_hash` matches `model_dump`. Its `bundle_content_hash` stays `None`
and its `schema_version` stays `"2"` (built-in-only seed; reader short-circuits
before the comparison). Because the existing `test_synthesize_on_fresh_project_
via_public_cli` (`test_charter_synthesize_fresh.py:162`) only asserts
`"built_in_only: true" in text` and `test_bundle_validate_fresh_seed.py` uses a
hand-rolled fixture (pinning the SHIM, not the reroute), a broken reroute would
ship silently today — so WP01 adds a **production-path** pin that `load_yaml` +
`verify_manifest_hash` the REAL `_fresh_seed_manifest_text` output.

**Sequencing consequence:** because fact #15/#16 mean the field addition is not
inert, the finalizer + both shims + the PURE helper land in the **schema WP
(WP01)**; the `schema_version` default bump and the three constructor sites'
finalizer wiring + real `bundle_content_hash` values (SAFE-until-real-value per
fact #17) land in WP02. See the plan's WP outline.

## Open items carried into tasks

- FR-007: correct BOTH `charter-status-json.md` (WP04) and `computer.py`'s
  module docstring (WP03, so the file isn't self-contradictory mid-mission).
- Fixture seeding of the four bundle files (fact #20) — WP02.
- Consolidating `computer.py::_BUNDLE_FILES` with
  `BUNDLE_CONTENT_HASH_FILES` — deferred (Decision 5).
- `charter activate/deactivate` config-drift blind spot — deferred future
  issue (Decision 2 scoped limitation).
