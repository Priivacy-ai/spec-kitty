---
affected_files: []
cycle_number: 1
mission_slug: charter-synthesize-reconciliation-01KZJQN6
reproduction_command:
reviewed_at: '2026-08-10T06:27:21Z'
reviewer_agent: claude
wp_id: WP06
---

# WP06 Review — REJECT

Reviewer: claude (reviewer-renata) · Commit reviewed: `14ab64bea` · Lane: `-lane-f`

## Verdict: REJECT (one MAJOR interplay regression + masking test gap)

The narrow contract (gate on `synthesized_drg`, run targeted `generate`, never
write `charter.md`) is implemented cleanly and FR-011/NFR-006 are demonstrated
in the unit test. But the **end-to-end boundary-heal interplay is broken for
non-`built_in_only` projects** — the exact audience references-parity exists
for — and the WP's own tests mask it. Details below.

---

## MAJOR-1 — WP06's `generate` leaves `synthesized_drg` STALE, turning a previously-passing heal into `passed=False`

**Where:** `preflight/runner.py` `_attempt_auto_refresh` call order vs
`preflight/references_refresh.py:refresh_references_if_needed` +
`cli/commands/charter/generate.py`.

**Mechanism (traced + reproduced):**
1. `_attempt_auto_refresh` runs, in order: `sync` → `synthesize` (step 2) →
   `bundle validate` → **WP06 `refresh_references_if_needed` (runs `generate`)** →
   `compute_freshness` (post-refresh recompute) → `passed = all(PASS)`.
2. `synthesize` (step 2) re-stamps the synthesis manifest's
   `bundle_content_hash` to the hash of `charter.yaml` **as it is before
   generate**.
3. `synthesized_drg` freshness = `manifest.bundle_content_hash ==
   compute_bundle_content_hash(repo)`, and `compute_bundle_content_hash`
   hashes the **whole `charter.yaml`** (`BUNDLE_CONTENT_HASH_FILES =
   ('charter.yaml',)`), **including the derived `catalog`**
   (`freshness/computer.py:451-494`, `charter.bundle.compute_bundle_content_hash`).
4. WP06's `generate` (step 4) rewrites `charter.yaml`'s `catalog` and **does
   NOT re-stamp the synthesis manifest** (verified: `generate.py` and
   `charter.activation.compiler.write_compiled_charter` contain no manifest/
   `bundle_content_hash`/synthesize write).
5. Therefore the post-refresh recompute (step 5) sees
   `stored_hash != current_hash` → `synthesized_drg = "stale"` →
   `post_passed = False` → the heal reports **blocked**.

**Proven concretely** (non-`built_in_only` repo, real manifest stamped fresh):
```
BEFORE generate: synthesized_drg = fresh | manifest_hash==charter_hash: True
AFTER  generate: synthesized_drg = stale | stored==current: False
```

**Regression:** Pre-WP06 the hook was a no-op; for a stale-`synthesized_drg`
non-`built_in_only` project the heal's `synthesize` step re-stamped the manifest
and the recompute reported **fresh → passed=True** (the documented self-heal
path, `freshness/computer.py` docstring: "self-heals to fresh on the next
`spec-kitty charter synthesize`"). WP06 appends a `generate` that mutates
`charter.yaml` **after** that stamp with no re-stamp, so the same heal now
reports **passed=False**. Scope of impact:
- `built_in_only` projects (most fresh projects): `synthesized_drg` is a PASS
  state → never in the stale cause set → WP06's `generate` never fires → no
  impact.
- **Non-`built_in_only` projects (org/project doctrine — the references-parity
  audience): every heal that includes `synthesized_drg` now runs `generate`,
  breaks the heal's own verdict, and (MAJOR-2) never converges.**

## MAJOR-2 — Non-convergence via the pre-existing (correctly-flagged) generate defect

`generate` is **not idempotent**: three consecutive plain `spec-kitty charter
generate --no-from-interview` runs against one repo produced three different
`charter.yaml` content hashes (`H2 != H3 != H4`), and a `generate` run against
an already-generated repo degrades 4 language-scoped styleguide/toolguide
`title`/`summary` strings to `"Definition unavailable in bundled doctrine"`
(`id`/`kind`/`source_path` stable). This is genuinely **pre-existing** in
`charter.activation.compiler` (reproduced with plain `generate`, zero WP06 code) — the
implementer flagged it and its commit message correctly recommends a tracker
issue, and the unit test's activated-id-SET comparison correctly works around
it without masking (that part is good).

The problem is the **interaction with MAJOR-1**: because WP06 now fires
`generate` automatically inside the boundary heal, this pre-existing defect is
promoted from an operator-invoked event to an **automatic one that runs on
every heal**. Combined with MAJOR-1 (no re-stamp), a non-`built_in_only`
project's heal will (a) never report passed, and (b) progressively degrade its
compiled doctrine catalog on each preflight. WP06 materially widens the blast
radius of the pre-existing defect into an automatic path.

## MAJOR-3 — Tests mask MAJOR-1 (coverage gap)

Neither test exercises the real end-to-end heal outcome with a real `generate`:
- `test_boundary_heal.py::test_references_parity_hook_is_installed_and_invoked_after_a_successful_heal`
  seeds a real non-`built_in_only` repo with a genuinely stale `synthesized_drg`
  (authoring-only `charter.yaml` edit) and calls the real hook — **but
  `_make_heal_subprocess_fake` stubs the `spec-kitty charter generate`
  subprocess to a no-op `CompletedProcess(returncode=0)`** (it only runs
  `synthesize` for real). So `charter.yaml` is never mutated and
  `result.passed is True` holds only because generate did nothing. If the fake
  ran `generate` for real (as `test_references_parity_refresh.py` does for its
  own scope), this test would go RED — it is asserting the very outcome the
  production defect breaks.
- `test_references_parity_refresh.py` runs `generate` for real (in-process) and
  proves catalog recompile + `charter.md` byte-equality, but calls
  `refresh_references_if_needed` **directly**, never through
  `_attempt_auto_refresh`, and against a repo with no stored synthesis-manifest
  hash to invalidate — so the post-refresh freshness recompute (the failure
  surface) is entirely outside coverage.

A regression guard is needed that drives `run_charter_preflight(auto_refresh=True)`
on a stale non-`built_in_only` repo with a **real** generate and asserts the
resulting `passed`/`synthesized_drg` state.

---

## Required to approve (pick a coherent fix, not a test tweak)

1. Make the heal manifest-coherent: after WP06's `generate` mutates
   `charter.yaml`, re-stamp the synthesis manifest `bundle_content_hash` (or
   re-run `synthesize` after generate, or have generate re-stamp) so the
   post-refresh recompute reflects reality. Whatever the seam, the boundary heal
   must end `passed=True` when it genuinely healed.
2. Add end-to-end coverage through `_attempt_auto_refresh`/`run_charter_preflight`
   with a **real** `generate` on a non-`built_in_only` stale repo; do not stub
   generate to a no-op in the success assertion.
3. File the pre-existing `charter.activation.compiler` generate-degradation defect as a
   tracker issue (as the commit message already recommends) and confirm the
   heal path does not silently degrade the catalog on repeat heals.

## Secondary / non-blocking observations

- **Over-trigger (the primary adjudication):** gating on `synthesized_drg` is
  broader than "references genuinely need recompilation" — `synthesized_drg`
  trips on any `charter.yaml` content change (governance/directives/activation),
  so `generate` fires on governance-only heals too. This is defensible as the
  best available post-#2759 proxy (the stand-alone parity check is retired) and
  is genuinely gated (not unconditional), so it is acceptable **in isolation** —
  but it is the reason MAJOR-1/MAJOR-2 fire on ordinary authoring edits, not
  just true activation drift.
- **Stale inline comment:** `runner.py` `_attempt_auto_refresh` still carries
  `# T019: references-parity extension point (stub in this WP — WP06 implements
  the real generate call)`. The stub is gone; update the comment (the function
  docstring was updated, this call-site comment was not). Campsite.
- **Scope note (not a defect):** `runner.py` was edited despite the WP prompt's
  "Do not modify `runner.py`" — but repointing the WP04 stub delegate is
  unavoidable and was pre-authorised by the dispatcher; fine. `generate.py`
  (an owned file) was correctly left untouched — no references-only mode was
  needed because `write_compiled_charter` already never writes `charter.md`;
  sound decision. No unexpected core edits.

## Gate results (all green — the defect is behavioral, not a gate failure)
- `pytest tests/specify_cli/charter_runtime/ -q` → **38 passed** (they pass
  because MAJOR-3 masks MAJOR-1).
- `ruff check src/specify_cli/charter_runtime` → clean.
- `mypy src/specify_cli/charter_runtime` → 3 errors, **all pre-existing in
  `computer.py`** (`no-any-return` at lines 187/203/210); `computer.py` is not
  in WP06's diff. references_refresh.py / runner.py: clean.
- `pytest tests/architectural/test_no_legacy_terminology.py` → **10 passed**.
