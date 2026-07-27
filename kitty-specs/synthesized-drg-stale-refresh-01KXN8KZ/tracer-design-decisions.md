# Mission Tracer — Design Decisions

**Mission:** `synthesized-drg-stale-refresh-01KXN8KZ` · Fixes [#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681)

> Seeded at tasks-authoring time. Records the binding structural decisions so a
> later agent does not "un-decide" them. See `data-model.md` / `research.md`
> for the full contracts and the live-code fact table.

## D1 — Single canonical `finalize_manifest` authority across all FOUR persist sites (C-006)

The root cause of the two post-plan BLOCKERs was the "build a raw
`manifest_data_without_hash` dict, hash it, then separately construct a
`SynthesisManifest(...)`" duplication across persist sites. Decision: ONE
finalizer `manifest.finalize_manifest(manifest) -> SynthesisManifest` that
recomputes `manifest_hash` from the FULL instance. Every persist site builds/
modifies an instance and calls it before writing. The four sites:

1. `write_pipeline.promote` (synthesize) — instance + helper + finalize (WP02).
2. `resynthesize_pipeline._rewrite_manifest` (resynthesize) — needs `repo_root`
   threaded (WP02).
3. `project_drg.apply_post_condition` (built-in-only flip) — `model_copy` +
   finalize, PRESERVES `bundle_content_hash` unchanged (BLOCKER-1, WP02).
4. `_fresh_doctrine._fresh_seed_manifest_text` (fresh seed) — raw-`hashlib`
   path that desyncs on the bare field addition; rerouted through finalize
   (WP01, fact #15).

This is **structural** unification (one shared producer), not test-enforced
parity — it closes BLOCKER-1 (dropped field) and BLOCKER-2 (dict/instance
divergence) by construction.

## D2 — Schema `schema_version` bumps in TWO steps (fact #17)

`promote` and `_rewrite_manifest` hardcode `"schema_version": "2"` in their
hashed dict but construct the instance via the model default. Bumping the
default to `"3"` at the same time as adding the field (WP01) would write a
`"3"` instance hashed over `"2"` → `verify_manifest_hash` RAISES → accidental
RED indistinguishable from a real regression. So: **WP01 widens the `Literal`
to `["2","3"]` but KEEPS the default `"2"`; WP02 bumps the default to `"3"`
ATOMICALLY with converting those two writers** (dropping the hardcoded dict).
The fresh-seed manifest stays `schema_version: "2"` intentionally (the reader
short-circuits on `built_in_only`; `versioning.py`'s v2 repair guards on
`!= "2"`).

## D3 — Per-field `verify_manifest_hash` backward-compat shim (fact #16)

Adding the field makes `compute_manifest_hash` include `bundle_content_hash:
None`, so every existing on-disk v2 manifest (hashed without the field) would
fail `verify_manifest_hash`. Decision: generalize the legacy fallback to
recompute via **raw** `hashlib.sha256(canonical_yaml(subset))` over EXACTLY
the `_raw_field_names` subset (the keys the file actually carried). It MUST be
per-field gated, NOT a fixed pop-list (a pop-list silently weakens tamper
detection for every v3 file), and NOT via `compute_manifest_hash` (which
re-injects model defaults). Preserves tamper detection: a v3 file with a
present-but-tampered `bundle_content_hash` still RAISES.

## D4 — Fail-safe helper: per-file hashing, `None` on any absence/unreadability

`compute_bundle_content_hash` hashes EACH of the four bundle files
independently via `charter.hasher.hash_content` (per-file BOM/CRLF normalize),
then combines the digests. Per-file (not concat-then-hash-once) is required —
`canonical_yaml` only strips a LEADING BOM of the whole payload, so a BOM on
files 2-4 would survive → #2009-class false-`stale` (fact #14). Returns `None`
when the charter dir is missing OR any file is missing/unreadable — the read
guard catches **both `OSError` AND `UnicodeDecodeError`** (`/analyze` C1: a
non-UTF-8 file raises `UnicodeDecodeError`, a `ValueError` subclass NOT caught
by `OSError`). `None` → the reader reports `stale` (fail-safe, recoverable),
never a crash — `compute_freshness` is a pure observer (spec fail-posture MUST,
spec.md:47).

## D5 — Substantive (non-volatile) field → single-pass self-heal (C-001/AS-4)

`bundle_content_hash` is NOT added to `_VOLATILE_MANIFEST_FIELDS`. It is
deterministic under fixed content (steady-state runs recompute the same value
→ no-op-stable holds) yet substantive (a pre-fix manifest lacking it differs
at the textual no-op check → rewritten exactly once → next read `fresh`).
Adding it to the volatile set to "avoid churn" would silently break the
backfill and re-introduce the deadlock — explicitly forbidden.

## D6 — Two complementary manifest signals, neither subsumes the other (C-005)

`manifest.verify()` / per-artifact `content_hash` = OUTPUT-artifact integrity
("do the doctrine files on disk still match what the manifest committed?").
`bundle_content_hash` = INPUT currency ("was the manifest built from the
content current now?"). Both live on the manifest. `_compute_synthesized_drg`
stays the single canonical READ authority; the shared helper (via the
finalizer at every writer) is the single canonical WRITE authority.

## D7 — 4-WP structure with per-WP red→green (C-011, post-`/analyze` restructure)

The original 5-WP split had a pure red-tests WP (WP02) whose tests stayed red
until later WPs — a mission-level C-011 dilution. Restructured to FOUR WPs,
folding each test into the WP that makes it green: WP01 (schema/hash infra),
WP02 (writers, reader-independent), WP03 (reader) are each self-contained
red→green; WP04 (closeout) delivers no new runtime behavior (C-011 N/A — its
gate is the full regression + NFR guards).

## Notes (appended during implementation)

- _(append per-WP decisions/deviations here)_

## D8 — WP04 mission-close assessment (C-011 per-WP red→green held)

The D7 restructure's premise was verified in practice, not just planned:

- **WP01** (`759d24fa6`) — the schema/hash-infra layer's own tests (the
  widened-`Literal`/default-`"2"` parity pin, the `verify_manifest_hash`
  per-field shim red-first pin on a mutated present field, and the
  production fresh-seed reroute) were RED against WP01's own base and GREEN
  on WP01's final commit — self-contained, reader-independent.
- **WP02** (`d6bc124e7`) — the writer-field / BLOCKER-1 (`apply_post_condition`
  dropping the field) and BLOCKER-2 (dict/instance divergence) regressions
  were RED before the finalizer-routed writer conversion and GREEN after,
  still reader-independent (WP03 had not yet landed).
- **WP03** (`fc679f573`) — AS-1 (`test_synthesized_drg_fresh_after_mtime_only_
  bump`, a realistic past-dated `created_at` vs. a future-bumped bundle
  mtime) and AS-5 (the full #2681 reproduction, both `synthesize` and
  `resynthesize` remediation entry points) were RED on the pre-swap mtime
  comparison and GREEN once the content-identity comparison landed — the
  terminal, load-bearing pins per NFR-006 (explicitly not the pre-existing
  `2099-…` sentinel test).
- **WP04** delivered no new runtime code path (C-011 correctly N/A per the
  WP prompt) — its one new test
  (`TestNfr002FreshnessComputeUnder2Seconds::test_compute_freshness_
  under_2_seconds`) is a permanent performance ratchet, not a red→green
  behavior pin, and is documented as such in the test docstring.

## D9 — WP04 ownership-metadata resolution (F1 cross-referenced)

WP04's `owned_files` declares only
`tests/charter/synthesizer/test_performance_envelopes.py` (the NFR-002
guard) — it deliberately does NOT list the external contract doc
`kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/
charter-status-json.md` that T022 edits, because `finalize-tasks`'s
ownership gate hard-rejects any `owned_files` entry under `kitty-specs/`
(any mission's tree) and an empty `owned_files` is separately rejected by
`compute_lanes`. This is a deliberate metadata resolution, not a scope gap:
the contract-doc edit is real, reviewer-attested work (see tracer-tooling-
friction.md F1 for the full mechanism and the candidate upstream fix). A
later agent should not "fix" this by adding the `kitty-specs/` path to
`owned_files` — doing so hard-fails `finalize-tasks`.
