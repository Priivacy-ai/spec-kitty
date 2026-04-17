# C-3 — Neutrality Lint Pytest Contract

**Kind**: Test harness contract
**Covers**: FR-010, FR-011, SC-003, SC-005, NFR-001

## Statement

A single pytest module at `tests/charter/test_neutrality_lint.py` MUST implement the neutrality-lint regression gate with the following behavior:

### Discovery

- The test is collected automatically under `pytest tests/` (default pytest configuration; no opt-in marker required).
- The test produces a single top-level test case (`test_generic_artifacts_are_neutral`) PLUS per-term parametrized assertions for diagnostic granularity.
- Total runtime on a baseline developer machine MUST NOT exceed 5.0 seconds wall-clock (NFR-001).

### Inputs

- `src/charter/neutrality/banned_terms.yaml` — v1 schema per C-4.
- `src/charter/neutrality/language_scoped_allowlist.yaml` — v1 schema per C-5.
- All files under the following scan roots (initial configuration; extensible via lint config):
  - `src/doctrine/` — **primary bias surface**; shipped doctrine artifacts (agent profiles, styleguides, toolguides) are where Python/pytest leakage has historically occurred. Scanning this root is load-bearing for FR-008.
  - `src/charter/` (excluding `src/charter/neutrality/` itself to avoid self-match)
  - `src/specify_cli/missions/*/command-templates/`
  - `src/specify_cli/missions/*/mission.yaml`
  - `.kittify/charter/` (if present in the working tree)

Scanning `src/doctrine/` is not optional: the Mission #653 motivation was Python-tool bias in shipped doctrine, so a lint that omits it would pass while the real surface remained contaminated.

### Behavior

- For each scanned file whose repo-relative path does NOT match any `LanguageScopedPath` entry (literal or glob), the scanner greps for each `BannedTerm` pattern.
- Any hit produces a `BannedTermHit(file, line, column, term_id, match)`.
- A stale allowlist entry (path that resolves to zero files) produces a `stale_allowlist_entries` entry.
- The test passes iff `NeutralityLintResult.passed` is True.

### Failure output contract

On failure, the test MUST produce a diagnostic of this shape (pytest's standard `assert` inspection is sufficient if the message is pre-formatted):

```
Neutrality lint failed.

HITS:
  src/charter/example.md:14:3 — term_id=PY-001 matched="pytest"
  src/specify_cli/missions/software-dev/command-templates/plan.md:42:7 — term_id=PY-003 matched="pip install"

STALE ALLOWLIST ENTRIES:
  src/charter/profiles/python/missing.md  (no file resolves this path)

Remediation for each HIT:
  (a) Remove the banned term from the file, OR
  (b) Add the file's path to src/charter/neutrality/language_scoped_allowlist.yaml
      if the file is INTENTIONALLY language-scoped.

Remediation for STALE entries:
  Delete the stale path from language_scoped_allowlist.yaml, or restore the expected file.
```

### Fault-injection test (SC-005)

A separate test case temporarily writes a synthetic generic-scoped file containing `pytest` into a tmp path, points the lint at the tmp scan root, and asserts the lint fails with a hit on that file. Restores on teardown.

## Machine-enforced assertion

```python
# tests/charter/test_neutrality_lint.py (skeleton)
def test_generic_artifacts_are_neutral():
    result = run_neutrality_lint()
    assert result.passed, _format_failure(result)

def test_fault_injection_catches_regression(tmp_path):
    (tmp_path / "generic.md").write_text("run pytest to verify\n")
    result = run_neutrality_lint(scan_roots=[tmp_path])
    assert not result.passed
    assert any(hit.term_id == "PY-001" for hit in result.hits)

def test_runtime_budget():
    import time
    start = time.perf_counter()
    run_neutrality_lint()
    assert (time.perf_counter() - start) < 5.0
```

## Non-contract

- The test does NOT examine file content for semantic meaning (no AST, no NLP). Only pattern matching.
- The test does NOT gate PR merge directly — CI enforces via the existing pytest job.

## Breakage response

Lint failures are expected and intentional when a contributor introduces a banned term. The remediation instructions in the failure output are the canonical response. Do not weaken the lint or add terms to the allowlist without explicit review.
