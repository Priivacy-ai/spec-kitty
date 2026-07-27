---
work_package_id: WP04
title: CHANGELOG canonical→root sync generator
dependencies:
- WP03
requirement_refs:
- C-002
- FR-007
tracker_refs: []
planning_base_branch: design/doc-quality-hardening-2245
merge_target_branch: design/doc-quality-hardening-2245
branch_strategy: Planning artifacts for this mission were generated on design/doc-quality-hardening-2245. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doc-quality-hardening-2245 unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Lane B2
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "181108"
history:
- at: '2026-06-30T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/docs/sync_changelog.py
create_intent:
- scripts/docs/sync_changelog.py
- tests/docs/test_sync_changelog.py
execution_mode: code_change
model: ''
owned_files:
- scripts/docs/sync_changelog.py
- CHANGELOG.md
- .github/workflows/docs-freshness.yml
- tests/docs/test_sync_changelog.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – CHANGELOG canonical→root sync generator

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

Make root `CHANGELOG.md` a generated artifact: `docs/changelog/CHANGELOG.md` is
the canonical source; root is the release-tooling copy consumed by
`scripts/release/extract_changelog.py`. A blocking sync check prevents drift.

**DoD**:
- `scripts/docs/sync_changelog.py` exists; pure stdlib; `ruff`+`mypy` clean.
- `--write` regenerates root from canonical (written `utf-8-sig`).
- `--check` exits 0 iff `root == generate_root(canonical)`, else exits 1.
- Root is a valid Keep-a-Changelog file parseable by `extract_changelog.py`.
- `tests/docs/test_sync_changelog.py` exists, marked `@pytest.mark.fast`, green.
- Divergence test (T013) is demonstrably red-first.
- `.github/workflows/docs-freshness.yml` has a `sync_changelog.py --check` step.

---

## Context & Constraints

**Spec**: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/spec.md` (FR-007, C-002, SC-003)
**Plan**: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/plan.md` (IC-02, D-5)
**Research**: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/research.md` (R-03)
**Contract**: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/contracts/changelog-sync-contract.md`
**Depends on**: WP03 (link fixes applied to canonical before sync)

**D-5 (utf-8-sig)**: `extract_changelog.py:76` reads root with
`read_text(encoding="utf-8-sig")`. The generator MUST write root with
`Path.write_text(..., encoding="utf-8-sig")`. Encoding mismatch corrupts release
notes extraction.

**C-002**: Root must remain Keep-a-Changelog-valid. `extract_changelog.py` matches
`## [VERSION] - DATE` headings. The generator must not prepend frontmatter or
any header that breaks `CHANGELOG_HEADING_RE`.

**Current divergence (SC-003)**: The two files diverge in two ways today: (a)
canonical has a YAML frontmatter block absent from root; (b) root contains a stale
`architecture/2.x/05_ownership_map.md` body line WP03 removes from canonical. Both
are resolved by regeneration after WP03 lands.

**WP02 boundary**: WP04 owns the `sync_changelog.py --check` step in
`docs-freshness.yml`. WP02's gate-widen edits `EXCLUDE_PREFIXES` in
`relative_link_fixer.py`, not this workflow step.

**C-003**: Pure stdlib only — no `ruamel.yaml`, `click`, `typer`. Frontmatter
strip is trivial string splitting.

**Marker discipline**: `test_sync_changelog.py` → `@pytest.mark.fast`; use
`tmp_path` for all tests except the live-sync invariant.

---

## Branch Strategy

- **Strategy**: coord
- **Planning base branch**: `design/doc-quality-hardening-2245`
- **Merge target branch**: `kitty/mission-doc-quality-hardening-2245-01KW9AKV`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T011 – Create `scripts/docs/sync_changelog.py`

- **Purpose**: Implement `generate_root` + `--check`/`--write` CLI.

- **Steps**:
  1. Create `scripts/docs/sync_changelog.py` (pure stdlib, `#!/usr/bin/env python3` shebang).
  2. Implement `generate_root(canonical_text: str) -> str`:
     - Strip the YAML frontmatter block (delimited by `---` at the start). Return
       the body beginning at `# Changelog` with no leading blank lines.
     - Pattern: split on `\n---\n` after the opening `---`, take the second part,
       strip leading newlines.
     - The function is pure (no I/O); type-annotated; has a one-line docstring.
     - **Preserve `<!-- tool-surface: ignore -->` markers verbatim.** Upstream
       `ccd278061` added 2 such markers to the body of BOTH files (sanctioned
       escape hatch for legacy skill paths in historical entries). Since
       `generate_root` copies the canonical body verbatim (minus frontmatter),
       the markers carry through automatically — but add a test asserting the
       generated root still contains both `tool-surface: ignore` markers so a
       future generator change can't silently strip them and re-break
       `test_docs_contract_lint`.
  3. Implement the CLI with `argparse` or bare `sys.argv`:
     - `--check`: read root (`CHANGELOG.md`) and canonical (`docs/changelog/CHANGELOG.md`)
       relative to the repo root; if `root != generate_root(canonical)` print a
       divergence message to stderr and exit 1; else exit 0.
     - `--write`: write `generate_root(canonical)` to root using
       `Path.write_text(..., encoding="utf-8-sig")`; print confirmation; exit 0.
     - Resolve repo root via `Path(__file__).parent.parent.parent` (follow the
       pattern of sibling scripts in `scripts/docs/`).
  4. `ruff check scripts/docs/sync_changelog.py` → 0. `mypy scripts/docs/sync_changelog.py` → 0.

- **Files**: `scripts/docs/sync_changelog.py` (CREATE)

---

### Subtask T012 – Regenerate root `CHANGELOG.md` from canonical

- **Purpose**: Apply the generator to produce a correct, C-002-valid root from
  the post-WP03 canonical.

- **Steps**:
  1. Confirm WP03's five link fixes are in place in `docs/changelog/CHANGELOG.md`.
  2. Run: `python scripts/docs/sync_changelog.py --write`
  3. Verify root starts with `# Changelog` (not `---`):
     `head -1 CHANGELOG.md` → `# Changelog`
  4. Smoke-test C-002: `python scripts/release/extract_changelog.py 3.2.3` → non-empty output (not the fallback message).
  5. Verify `utf-8-sig` BOM:
     ```bash
     python -c "d=open('CHANGELOG.md','rb').read(3); assert d==b'\xef\xbb\xbf',repr(d); print('BOM OK')"
     ```
  6. Confirm stale line gone: `grep "architecture/2.x/05_ownership_map" CHANGELOG.md && echo STALE || echo OK` → `OK`

- **Files**: `CHANGELOG.md` (MODIFY via `--write`)

---

### Subtask T013 – Red-first divergence test

- **Purpose**: Prove SC-003 — current files diverge; `--check` detects it; converge fixes it.

- **Steps**:
  1. Create `tests/docs/test_sync_changelog.py` with `pytestmark = pytest.mark.fast`.
  2. Required test functions (use `tmp_path` except `test_live_files_are_synced`):
     - `test_generate_root_strips_frontmatter`: assert output does not start with `---` and
       starts with `# Changelog`.
     - `test_check_fails_when_files_diverge(tmp_path)`: assert `generate_root(canonical) != root`
       when root body differs from the generated form.
     - `test_check_passes_after_write(tmp_path)`: write generated text to a tmp file with
       `encoding="utf-8-sig"`, read it back, assert equality.
     - `test_generated_root_parseable_by_extract_changelog`: import `extract_changelog_section`
       from `scripts/release/extract_changelog.py`; assert it extracts a named version from
       `generate_root(canonical_text)` correctly (C-002).
     - `test_live_files_are_synced` (permanent CI invariant, reads live files):
       read `docs/changelog/CHANGELOG.md` (`encoding="utf-8"`) and `CHANGELOG.md`
       (`encoding="utf-8-sig"`); assert `root == generate_root(canonical)` with a message
       directing the implementer to run `--write`.
  3. **Red-first proof**: `pytest tests/docs/test_sync_changelog.py::test_live_files_are_synced -q`
     must FAIL before T012. Run T012 (`--write`), then confirm it passes.

- **Files**: `tests/docs/test_sync_changelog.py` (CREATE)

---

### Subtask T014 – Wire `sync_changelog.py --check` into `docs-freshness.yml`

- **Purpose**: Block drift from shipping green in CI (FR-007).

- **Steps**:
  1. Open `.github/workflows/docs-freshness.yml`. Locate the `relative_link_fixer.py --check` step to understand the step format.
  2. Add a new step after the link-fixer step:
     ```yaml
     - name: Check CHANGELOG sync (canonical → root)
       run: python scripts/docs/sync_changelog.py --check
     ```
  3. Validate YAML: `python -c "import yaml; yaml.safe_load(open('.github/workflows/docs-freshness.yml'))"` → exit 0.

- **Files**: `.github/workflows/docs-freshness.yml` (MODIFY)
- **Notes**: Do not touch any other existing step. WP02 will separately widen the gate scope.

---

## Test Strategy

```bash
# Red-first proof (before T012):
pytest tests/docs/test_sync_changelog.py::test_live_files_are_synced -q   # must FAIL

# After T012 (--write):
pytest tests/docs/test_sync_changelog.py -q                                # all green
python scripts/release/extract_changelog.py 3.2.3                          # non-empty output (C-002)

# Clean checks (NFR-004):
ruff check scripts/docs/sync_changelog.py tests/docs/test_sync_changelog.py
mypy scripts/docs/sync_changelog.py tests/docs/test_sync_changelog.py
pytest tests/architectural/test_no_legacy_terminology.py -q
```

---

## Risks & Mitigations

- **Risk**: `utf-8-sig`/`utf-8` mismatch causes live-sync test to fail after `--write`.
  **Mitigation**: test reads root with `encoding="utf-8-sig"`; generator writes with the same.
- **Risk**: Frontmatter strip too greedy — root begins with blank lines.
  **Mitigation**: `test_generate_root_strips_frontmatter` pins this; verify with `head -1 CHANGELOG.md`.
- **Risk**: Sonar gap on `--check`/`--write` branches.
  **Mitigation**: diverge/write tests cover both; also cover the "no frontmatter" passthrough path.

---

## Review Guidance

1. `sync_changelog.py` imports are pure stdlib (`grep -E "^import|^from"` shows no third-party).
2. `generate_root` strips only frontmatter; body is verbatim.
3. `write_text(..., encoding="utf-8-sig")` present in the `--write` path.
4. Red-first: `git stash` → live-sync test FAILS; `git stash pop` → PASSES.
5. `python scripts/release/extract_changelog.py 3.2.3` → non-empty output (C-002).
6. `docs-freshness.yml` has the sync step; YAML parses cleanly.
7. `ruff` + `mypy` zero issues on new files.
8. All tests except `test_live_files_are_synced` use `tmp_path`.

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action>`

**Example**:
```
- 2026-01-12T10:00:00Z – system – Prompt created
- 2026-01-12T10:30:00Z – claude – Implementation complete, ready for review
```

**Why this matters**: The acceptance system reads the LAST entry as current state.
Append only — never prepend or insert in the middle.

**Initial entry**:

- 2026-06-30T00:00:00Z – system – Prompt created.

---

### Updating Status

Use `spec-kitty agent tasks move-task WP04 --to <status>` to change WP status.
- 2026-06-30T18:03:15Z – claude:sonnet:python-pedro:implementer – shell_pid=120093 – Assigned agent via action command
- 2026-06-30T18:15:45Z – claude:sonnet:python-pedro:implementer – shell_pid=120093 – handoff: sync_changelog.py (pure stdlib, utf-8-sig write) + 8 green fast tests incl. red-first live-sync invariant + CI step in docs-freshness.yml; extract_changelog 3.2.3 smoke non-empty; ruff exit 0; mypy exit 0
- 2026-06-30T18:16:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=181108 – Started review via action command
- 2026-06-30T18:19:42Z – user – shell_pid=181108 – Review passed: pure-stdlib sync_changelog.py (argparse/sys/pathlib/typing only; no ruamel/click/typer); generate_root strips frontmatter verbatim; --check exit 0/1, --write utf-8-sig (D-5). C-002: root regenerated, head=# Changelog+BOM, extract_changelog 3.2.3=185 lines (non-fallback). 3.2.4 content preserved (## [Unreleased] - 3.2.4 both files); 2 tool-surface:ignore markers in root+canonical. SC-003: 8 fast tests pass + CLI red-first proof (synced=0, diverged=1, restore=0). docs-freshness.yml --check step added (+2 lines, YAML valid, WP02 EXCLUDE_PREFIXES untouched). WP03's 5 link fixes carried into root. ruff/mypy clean. Nit (non-blocking): step uses bare 'python' vs sibling 'uv run python'; stdlib-only so works, but consistency fix suggested.
