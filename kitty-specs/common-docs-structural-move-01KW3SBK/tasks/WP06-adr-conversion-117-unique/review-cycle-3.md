---
affected_files: []
cycle_number: 3
mission_slug: common-docs-structural-move-01KW3SBK
reproduction_command:
reviewed_at: '2026-06-27T15:40:16Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP06
review_artifact_override_at: "2026-06-27T15:50:43Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP06"
review_artifact_override_reason: "Cycle-3 approved (reviewer-renata): resolves the sole cycle-2 blocker (terminology guard RED). docs/adr/ added to _EXCLUDED_PATH_FRAGMENTS mirroring kitty-specs/ historical-artifact precedent with NFR-001/C-002 rationale comment; narrow regression test test_docs_adr_exemption_is_narrow proves docs/adr/ exempt while docs/guides|architecture|top-level still scanned (verified it FAILS under a blanket docs/ exemption). Guard GREEN (3 passed, was RED). Fidelity intact: census 117 realpath-unique, content-invariance + census suite 4 passed, no dangling symlinks, ruff/mypy clean. Only out-of-map touch is the guard test (justified leeway, documented in commit + comment)."
---

# WP06 Review — Cycle 2 — REJECTED (reviewer-renata)

## Verdict: REJECT → planned

The conversion execution is **almost** clean — census, content-invariance, symlink
dereferencing, status distribution, and the flat-shim closure all pass rigorously.
**But one acceptance criterion fails: the terminology guard is RED**, and it is RED
*because of* WP06's move. This is a CI merge-blocker (it runs in CI's
`integration-tests-core-misc` job and the local doctrine sweep both). Reject.

---

## Per-criterion results

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Census == 117 realpath-unique (NFR-001) | **PASS** |
| 2 | Content-invariance non-vacuous (C-002) | **PASS** |
| 3 | 71 symlinks dereferenced, no dangling | **PASS** |
| 4 | Status distribution 93/13/11, bare `status` | **PASS** |
| 5 | Flat shim closed + adjacent gates green | **FAIL — terminology guard RED** |

### What passes (do not redo)

- **Census == 117.** `find docs/adr -name '*.md' ! -name 'README.md' | wc -l` → 117;
  realpath-unique → 117; per-era 12 (1.x) + 37 (2.x) + 68 (3.x) = 117. Base tree had
  exactly 117 real ADR blobs (`100644`) + 71 symlinks (`120000`) — input/output census
  reconciles. The 20 era-less `architecture/adrs/` real ADRs correctly land under 3.x
  (48 native + 20 = 68).
- **Content-invariance non-vacuous.** `tests/docs/test_adr_content_invariance.py` →
  4 passed. Reuses WP05's raw-byte `invariant()` (imported, not forked), recovers
  pre-images from the planning merge-base, and asserts `compared == 117` (false-green
  guard present) plus a `convert(pre)==committed` sanity check. Independently
  spot-checked 3 ADRs (1.x explicit-base-branch, era-less prompts-do-not-discover,
  and confirmed the 2.x shared-package-boundary was a *symlink* correctly
  dereferenced) — in every real ADR only the header→frontmatter block changed; the
  decision body is byte-identical.
- **71 symlinks dereferenced.** `find docs/adr -xtype l` → EMPTY; `find docs/adr -type l`
  → EMPTY. Base had 24 (2.x/adr) + 47 (architecture/adrs) = 71 symlinks, all dropped,
  none converted as distinct ADRs (no census inflation).
- **Distribution.** 93 Accepted / 13 Proposed / 11 Superseded = 117. Bare `status:`
  throughout; zero `doc_status:` leakage into ADRs.
- **Flat shim closed.** `architecture/adrs/`, `architecture/{1.x,2.x,3.x}/adr/` all
  removed. The 3 era READMEs are `R100` verbatim renames into `docs/adr/<era>/README.md`.
  Converter consumed not modified (WP05 dependency). ruff + mypy clean on the new test.
  WP01 `tests/docs/test_runtime_read_resolution.py` → 15 passed.

---

## The blocker (criterion 5): terminology guard RED

`PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q` → **1 failed**
(`test_forbidden_term_does_not_appear[ceremony]`).

**Root cause — WP06-introduced regression.** The guard's `_SCAN_ROOTS` is
`("src", "tests", "docs")` — it does **not** scan `architecture/`. The ADRs carrying
the forbidden legacy term "ceremony" lived under `architecture/3.x/adr/` (unscanned)
before WP06. Moving them into `docs/adr/<era>/` (scanned) newly exposes them. Four
occurrences now trip the guard — all **verbatim historical ADR body prose** (correctly
preserved per NFR-001, confirmed against the base tree):

```
docs/adr/1.x/2026-01-23-1-record-architecture-decisions.md:39      - Lightweight and low-ceremony ...
docs/adr/3.x/2026-04-09-2-cli-saas-auth-is-browser-mediated-oauth-not-password.md:28   ... second password ceremony ...
docs/adr/3.x/2026-04-17-1-charter-synthesizer-adapter-seam.md:103  ... No inheritance ceremony.
docs/adr/3.x/2026-04-20-1-mutation-testing-as-local-only-quality-gate.md:15            level of ceremony, and with what scope.
```

This is precisely the CI-only-gate trap CLAUDE.md warns about: it passes a naive local
run but fails the repo-wide terminology gate at CI (and on the post-merge architectural
sweep).

### Required remediation — do NOT reword the ADR bodies

Rewording "ceremony" out of the bodies would **violate NFR-001 / C-002** (no mutation of
historical immutable snapshots) — and would break your own invariance test. The canon is
explicit: *"Historical archived artifacts may retain legacy wording only as immutable
snapshots."* So the fix is to **exempt the historical ADR surface from the guard**, not
edit the ADRs:

1. Add `docs/adr/` (the era subtree) to `_EXCLUDED_PATH_FRAGMENTS` in
   `tests/architectural/test_no_legacy_terminology.py`, mirroring the existing
   `kitty-specs/` historical-artifact precedent. Add a one-line rationale comment tying
   it to the canon's immutable-snapshot rule and NFR-001.
2. **Pair it with a regression test** (DIR-030 / DIR-041): assert that `docs/adr/` is
   exempt *and* that the rest of `docs/` stays scanned — so the exclusion can't silently
   widen into a hole that lets new prose drift past the guard.
3. `tests/architectural/test_no_legacy_terminology.py` is outside WP06's declared owned
   set (`architecture/.../adr/**`, `docs/adr/**`, `tests/docs/test_adr_content_invariance.py`).
   Editing it is justified ownership leeway (the move is what breaks the guard), but flag
   it in the WP note / coordinate so the lane that owns architectural gates isn't
   surprised. If another WP in this mission already owns the terminology guard's
   docs-scope adjustment, route it there instead and add a dependency.
4. Re-run before re-review:
   `PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q` must be
   green, and the invariance/census suite must stay green (the ADR bodies must remain
   untouched).

---

## Summary

Conversion fidelity is excellent — nothing lost, nothing mutated, symlinks cleanly
dereferenced. The single failure is a real, WP06-caused CI regression: relocating
historical ADRs into the `docs/` terminology-guard scope without exempting them. Fix the
guard's exclusion (not the ADR text), add a focused regression test, and re-submit.
