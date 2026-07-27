# Contract: Redirect-Stub Generation (FR-006, NFR-002)

Implements Mission A's **D4** redirect mechanism: DocFX on GitHub Pages has no native redirect, so
every moved/deleted URL is preserved by a generated **`<meta http-equiv="refresh">` stub page emitted
at the old path** into the `_site` output, produced by a **post-build step in `scripts/docs/`**
(new `redirect_stub_generator.py`) reading a **checked-in redirect map**.

---

## Inputs

| Input | Shape | Source |
|-------|-------|--------|
| Redirect map | `{ old_path: new_path }` (checked-in) | Appended per move by IC-05 as references are rewritten |
| Baseline-URL inventory | set of pre-move published URLs | **Captured + committed by IC-02b before any move** — the NFR-002 denominator |
| DocFX `_site` | built site output | `docfx build docs/docfx.json` |

## Pre-move baseline capture (IC-02b) — makes coverage falsifiable

The baseline-URL set is captured by a dedicated **pre-move step (IC-02b)**, *not* inside IC-05 (which
runs after the move). Steps:

1. **Install DocFX** (.NET — CI-only today; install it in this step).
2. **Build the pre-move tree** (`docfx docfx.json` over `docs/` + `architecture/` *before* IC-03).
3. **Snapshot** the emitted `_site` URL set into a checked-in **baseline-URL manifest**.
4. **Commit** the manifest **before IC-03**.

If the baseline is reconstructed from the *post-move* tree, `check_coverage` measures against the
wrong denominator and reports a false 100% — the guarantee becomes unfalsifiable.

## CI wiring (IC-05) — inject stubs between build and upload

Wire `redirect_stub_generator.py` into **`.github/workflows/docs-pages.yml`**: add a step that runs
**after** the `Build documentation` step (`docfx docfx.json`) and **before** the
`Upload artifact` (`actions/upload-pages-artifact@v3`) step, so the emitted stubs land inside `_site`
before publish. The coverage check (against IC-02b's committed baseline) runs in the same job and
**fails the build** on any uncovered baseline URL.

## Behavior

### `generate(redirect_map, site_dir) -> emitted_stubs`

- For each `old_path → new_path`, emit a stub file at `old_path` inside `_site` whose content is a
  `<meta http-equiv="refresh" content="0; url=<new_path>">` page (client-side redirect — the only
  primitive available on static GitHub Pages).
- The stub MUST resolve to a live `new_path` (no stub may point at a 404).

### `check_coverage(baseline, redirect_map, site_dir) -> uncovered[]`

- A baseline URL is **covered** iff it resolves **directly** (the page still exists at that path) OR a
  redirect **stub** exists at that path pointing to a live target.
- **Contract:** `uncovered == []` — **100%** of baseline URLs covered (NFR-002). A non-empty
  `uncovered` set is a **CI failure**; each entry is a dead public URL.

## Invariant

> **URL-continuity:** `coverage(baseline) == 100%`. The denominator is the **captured baseline set**
> — capturing it *before* the move is what makes the guarantee falsifiable.

## Out of scope

- Server-side redirects / DocFX native aliases (unavailable on static GitHub Pages — D4 rejected).
- #1652 SEO optimization (sequenced after this mission); this contract only preserves existing
  canonical/301 continuity (NFR-003).
