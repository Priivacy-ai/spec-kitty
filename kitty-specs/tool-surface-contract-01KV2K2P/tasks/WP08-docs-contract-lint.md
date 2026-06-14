---
work_package_id: WP08
title: Docs Contract Lint
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
requirement_refs:
- FR-016
- FR-017
tracker_refs: []
planning_base_branch: feat/tool-surface-contract
merge_target_branch: feat/tool-surface-contract
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
- T040
- T041
- T042
agent: "claude:opus:reviewer:reviewer"
shell_pid: "58600"
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: curator-carla
authoritative_surface: src/specify_cli/tool_surface/
create_intent:
- src/specify_cli/tool_surface/docs.py
- tests/specify_cli/tool_surface/test_docs.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/docs.py
- tests/specify_cli/tool_surface/test_docs.py
- docs/**/*.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load curator-carla
```

## Objective

Add a `DocsLinter` that validates generated/native tool surface path references in documentation against the ToolSurfaceContract registry, and integrate it into the CI/lint pipeline so docs cannot silently drift from the contract.

**This WP depends on WP01-WP06** being merged so all surface kinds are registered and path patterns are available for validation.

**Child issue**: #1942
**Parent epic**: #1945

## Context

Documentation files (e.g., `docs/host-surface-parity.md`, user guides) reference paths like `.agents/skills/spec-kitty.plan/SKILL.md` or `.claude/agents/architect-alphonso.md`. These paths are derived from the ToolSurfaceContract registry. If a path pattern changes in the registry, the doc references become stale and mislead users.

The `DocsLinter` prevents this by maintaining the invariant: every documented generated/native tool surface path must match a registered path pattern.

## Branch Strategy

- Planning base branch: `feat/tool-surface-contract`
- Merge target: `feat/tool-surface-contract`
- Command: `spec-kitty agent action implement WP08 --agent claude`

## Subtask Details

### T038 -- Implement `docs.py` `DocsLinter`

**Purpose**: Scan doc files for generated/native path references and validate them against the registry.

**Interface**:
```python
class DocsLinter:
    """Validates doc path references against the ToolSurfaceContract registry."""

    def __init__(self, registry: ToolSurfaceRegistry) -> None: ...

    def lint_file(self, doc_path: Path) -> list[DocsLintFinding]:
        """Lint a single doc file. Returns findings for any drifted paths."""
        ...

    def lint_directory(self, docs_dir: Path, patterns: list[str] | None = None) -> list[DocsLintFinding]:
        """Lint all matching files in a directory."""
        ...

@dataclass(frozen=True)
class DocsLintFinding:
    doc_path: Path
    line_number: int
    referenced_path: str
    finding: str   # "UNREGISTERED_PATH" or "AMBIGUOUS_MATCH"
    detail: str
```

**Path extraction heuristic**: Look for backtick-quoted paths in Markdown that match patterns like:
- `.agents/skills/spec-kitty.*/SKILL.md`
- `.claude/agents/*.md`
- `.kittify/*.json`
- Any path starting with `.` followed by a known tool directory

The linter should not flag every path -- only those that look like generated/native tool surface paths. Add a comment annotation `<!-- tool-surface: ignore -->` to suppress a specific line.

**Files**: `src/specify_cli/tool_surface/docs.py` (new, ~100 lines)

**Validation**:
- [ ] `lint_file` returns `DocsLintFinding` for a doc that references a non-existent path pattern
- [ ] `lint_file` returns empty list for a doc with no tool surface paths
- [ ] `<!-- tool-surface: ignore -->` suppresses the finding on that line
- [ ] `mypy --strict` passes

---

### T039 -- Build registry path index for doc reference validation

**Purpose**: Build a lookup structure that maps concrete path examples to registered path patterns.

The registry holds `path_pattern` values like `.agents/skills/spec-kitty.{command}/SKILL.md`. To validate a doc reference like `.agents/skills/spec-kitty.plan/SKILL.md`, the linter needs to match it against the pattern.

```python
class RegistryPathIndex:
    """Indexes registry path patterns for fast validation."""

    def __init__(self, registry: ToolSurfaceRegistry) -> None: ...

    def is_registered_path(self, path: str) -> bool:
        """Return True if path matches any registered path pattern."""
        ...

    def suggest_correction(self, path: str) -> str | None:
        """Return the closest registered pattern if path is close but not matching."""
        ...
```

**Files**: part of `src/specify_cli/tool_surface/docs.py` or a helper in the same file

**Validation**:
- [ ] `.agents/skills/spec-kitty.plan/SKILL.md` matches the command-skill pattern
- [ ] `.agents/skills/nonexistent/SKILL.md` does NOT match (returns `UNREGISTERED_PATH`)
- [ ] Performance: index is built once and reused across lint calls

---

### T040 -- Add CI/lint integration for docs contract check

**Purpose**: Integrate the `DocsLinter` into the project's lint pipeline so it runs in CI.

**Approach**:
1. Add a `pytest` test that runs the linter against the `docs/` directory:
   ```python
   def test_docs_contract_lint():
       """No doc file should reference unregistered tool surface paths."""
       linter = DocsLinter(get_registry())
       findings = linter.lint_directory(Path("docs/"))
       assert len(findings) == 0, f"Docs drift found:\n{format_findings(findings)}"
   ```
2. Optionally add a `spec-kitty doctor tool-surfaces --kind docs --json` filter (if the doctor command architecture supports it).

**Files**: `tests/specify_cli/tool_surface/test_docs.py` (includes the CI-level assertion)

**Validation**:
- [ ] `pytest tests/specify_cli/tool_surface/test_docs.py::test_docs_contract_lint` passes
- [ ] Test fails if a new unregistered path is added to a doc file (verify this by temporarily adding one)

---

### T041 -- Fix existing doc paths that drift from registry

**Purpose**: After the linter is running, fix any existing doc files that reference paths not in the registry.

**Approach**:
1. Run the linter against all `docs/**/*.md` files
2. For each finding, either:
   - Update the doc to use the correct registered path
   - Add `<!-- tool-surface: ignore -->` with a comment explaining why the path is intentionally non-standard
3. This step may not find any drift (if existing docs are already accurate) -- that is fine

**Files**: Any `docs/**/*.md` files that need updating

**Validation**:
- [ ] `pytest tests/specify_cli/tool_surface/test_docs.py::test_docs_contract_lint` passes with zero findings after fixes

---

### T042 -- Write tests for docs linter

**Purpose**: Unit-test the `DocsLinter` and `RegistryPathIndex` in isolation.

**Tests**:
```python
def test_docs_linter_finds_unregistered_path():
    """Linter detects path not matching any registry pattern."""
    ...

def test_docs_linter_passes_registered_path():
    """Linter returns empty for doc with correct registered path."""
    ...

def test_docs_linter_ignore_annotation():
    """<!-- tool-surface: ignore --> suppresses findings."""
    ...

def test_registry_path_index_matches_pattern():
    """Pattern with {command} variable matches concrete path."""
    ...

def test_registry_path_index_no_match():
    """Non-matching path returns False."""
    ...
```

**Files**: `tests/specify_cli/tool_surface/test_docs.py` (new, ~80 lines total including T040 and T042 tests)

**Validation**:
- [ ] `pytest tests/specify_cli/tool_surface/test_docs.py` passes

## Definition of Done

- [ ] `DocsLinter` is implemented and tested
- [ ] `pytest tests/specify_cli/tool_surface/test_docs.py::test_docs_contract_lint` passes with zero findings
- [ ] Adding a fake unregistered path to a doc causes the lint test to fail
- [ ] `mypy --strict src/specify_cli/tool_surface/docs.py` passes
- [ ] No existing docs drift (or all drift is suppressed with `<!-- tool-surface: ignore -->` and a comment)

## Risks

- **Pattern matching ambiguity**: Template variables in path patterns (e.g., `{command}`) require simple pattern matching, not full glob or regex. Use a dedicated pattern-matching approach (e.g., replace `{...}` with `[^/]+` and compile as regex).
- **Doc coverage**: The linter only catches paths explicitly mentioned in docs. Docs that describe surface layouts verbally (without backtick paths) are not caught -- that is acceptable for this WP.

## Reviewer Guidance (Codex)

- Verify linter does not flag non-tool-surface paths (e.g., `src/specify_cli/` references)
- Verify `ignore` annotation works
- Verify CI test would catch a new drift introduced in a future PR

## Activity Log

- 2026-06-14T11:42:32Z – claude – shell_pid=46357 – Ready for review: DocsLinter+RegistryPathIndex (docs.py) validate generated/native tool surface path refs against the registry (FR-017); wired via service.build_docs_linter/lint_docs_directory into CI-collected pytest test_docs_contract_lint. Live-wiring proven: passes clean on real docs/, FAILS on injected drift, passes after revert. T041 drift in 3-2-harness-research-method.md suppressed with rationale. ruff exit 0 on all 3 changed files; mypy --strict clean; full tool_surface suite 192 passed. --force used only for the known behind-base preflight quirk (real lane base kitty/mission-tool-surface-contract-01KV2K2P); tree clean, commit 09d484887 present.
- 2026-06-14T11:43:02Z – claude:opus:reviewer:reviewer – shell_pid=51475 – Started review via action command
- 2026-06-14T11:47:17Z – user – shell_pid=51475 – Review passed (independent reviewer). --force used ONLY for the known behind-base preflight quirk (real lane base kitty/mission-tool-surface-contract-01KV2K2P; tree clean; WP08 commit 09d484887 present). Prior review-cycle-2 rejection was a workflow re-dispatch note (dependency-lane auto-merge conflict on service.py), NOT an unresolved code defect; the manual provider-union merge it describes is verified intact (6 providers, 10 kind tokens, 8 builtin definitions); WP08 only ADDED build_docs_linter/lint_docs_directory + DocsLinter import. DocsLinter+RegistryPathIndex validate path refs vs registry path_patterns (FR-016/FR-017). DRIFT-INJECTION VERIFIED on REAL docs/: injected .agents/skills/__reviewer_injected__/SKILL.md -> test_docs_contract_lint FAILED with UNREGISTERED_PATH; PASSED clean after revert. No false positives. Lane suppression is a genuine FP (advise dir ref). CI-collected by default pytest.ini. ruff clean, mypy --strict clean, 192 tests pass; no noqa/type-ignore, no feature aliases.
- 2026-06-14T12:04:03Z – user – shell_pid=51475 – Re-review to write approved artifact superseding false rejection note
- 2026-06-14T12:04:05Z – claude:opus:reviewer:reviewer – shell_pid=58600 – Started review via action command
- 2026-06-14T12:10:06Z – user – shell_pid=58600 – Restore to approved: 192 tool_surface tests green; supersedes false-rejection orchestration note (dependency-lane merge-conflict re-dispatch), already independently reviewed
