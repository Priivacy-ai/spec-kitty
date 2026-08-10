# Quickstart: Verifying CI Scoping Gate Reliability

No data model or API contracts apply (CI-config + arch-guard change).

## 1. Corpus data triggers + runs the blocking suite (#3008, SC-001)

- Path-filter test: a diff confined to `packs/built-in/**` selects the `corpus` group and the
  `fast-tests-corpus` job; a corpus regression makes the `quality-gate` decision failure.
- Manual: open a scratch PR touching only `packs/built-in/**` and confirm the quality workflow triggers
  (previously it did not run at all) and the corpus job appears + is required.

## 2. No false-trigger on lifecycle churn (#3008, SC-002)

- Path-filter test: a diff confined to `kitty-specs/<m>/status.events.jsonl` does NOT select the
  `corpus` group. (Also `notes.md`/`trace/**`.)

## 3. Docs dead-link gate is diff-scoped (#3147, SC-003)

- With an untouched file elsewhere carrying a broken link, a docs PR whose own changed files have no
  broken links PASSES the blocking gate; introduce a broken link in a changed file → it FAILS.
- The whole-tree scan (scheduled/full-run) still reports the untouched broken link.

## 4. Arch invariants stay green (SC-004)

```bash
PWHEADLESS=1 python -m pytest tests/architectural/test_ci_quality_path_filters.py tests/architectural/test_ci_collection_completeness.py -p no:cacheprovider -q
```
Both green with the new `corpus` group claimed (no suite left unclaimed; no skip/noqa).
