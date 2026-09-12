# WP04 Review Cycle 1

**Verdict: changes requested**

## Blocking Finding

**[BLOCKER] `tests/architectural/test_status_command_guidance.py:28` and
`:104` - the required architectural gate is red on the reviewed commit and
does not faithfully resolve the scoped invocations through the executable
Typer tree.**

Reproduction:

```text
PWHEADLESS=1 pytest tests/architectural/test_status_command_guidance.py -q
F.

#2983 scoped guidance names an unregistered command:
  - docs/api/environment-variables.md:27: spec-kitty verify-setup
  - docs/api/environment-variables.md:261: spec-kitty verify-setup
  - docs/api/upgrade-lifecycle.md:129: spec-kitty prints a single banner before normal output
```

The first two failures are real commands whose Click-facing name is
`verify-setup`; the raw `scripts.docs._typer_walker.walk()` path derives
`verify_setup` from the callback before Click/Typer name normalization. The
third is ordinary prose, not a command invocation, but `_COMMAND_RE` scans any
unquoted `spec-kitty` token followed by lowercase words.

Repair the gate so it:

1. extracts only concrete invocations from the scoped Markdown/YAML content
   (for example, bash-fence command lines and inline code spans), excluding
   narrative prose;
2. resolves command paths against the compiled Click/Typer command tree, whose
   names match the actual CLI parser, rather than callback-name-derived raw
   registration metadata or a hand-maintained allowlist;
3. retains an explicit source/command denominator and mutation proof that a
   planted nonexistent command makes the same validation path fail; and
4. reruns every WP04 gate before returning the WP to review.

## Review Matrix

- Intent-correct replacements: **PASS**
- No new top-level `status` command: **PASS**
- Canonical doctrine source only: **PASS**
- Archived mission/changelog history untouched: **PASS**
- C-005 ownership disjointness: **PASS**
- Tracker claim/comment evidence: **PASS**
- YAML validation: **PASS**
- Ruff: **PASS**
- Markdownlint: **PASS**
- CLI reference parity: **PASS** (`4 passed, 2 skipped`)
- Terminology guard: **PASS** (`4 passed`)
- WP04 architectural gate: **FAIL** (`1 failed, 1 passed`)

## Anti-Pattern Checklist

- Dead code: **N/A** (no production module/API added)
- Synthetic-fixture test: **FAIL** (the shipped corpus gate is red and therefore
  does not provide accepted FR-012 evidence)
- Silent empty return: **N/A**
- FR coverage: **FAIL** (FR-012's required regression gate fails)
- Frozen surface: **PASS**
- Locked decision: **PASS**
- Shared-file ownership: **PASS**
- Production fragility: **N/A**
