---
work_package_id: WP02
title: Neutrality Lint Scaffolding
dependencies: []
requirement_refs:
- FR-008
- FR-009
- FR-013
- FR-014
- FR-012
- NFR-001
- NFR-006
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-ownership-consolidation-and-neutrality-hardening-01KPD880
base_commit: 443e4dc7b2f58b49bf9a4b7bfa6862272336c41d
created_at: '2026-04-17T09:25:21.194192+00:00'
subtasks:
- T004
- T005
- T006
- T007
- T008
- T009
phase: Phase 1 — Foundational
assignee: ''
agent: "claude:sonnet-4-6:implementer:implementer"
shell_pid: "6410"
history:
- timestamp: '2026-04-17T09:03:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/neutrality/
execution_mode: code_change
owned_files:
- src/charter/neutrality/**
tags: []
---

# Work Package Prompt: WP02 – Neutrality Lint Scaffolding

## Objective

Build the neutrality tripwire module from scratch as a new package `src/charter/neutrality/`. Deliver the scanner, both configuration YAMLs (banned terms and path allowlist) with seeded real data, and a public API that WP03's pytest regression gate can call.

This is the largest WP in the mission. Take time with it. A buggy scanner (false positives or false negatives) undermines every downstream regression test.

## Context

The scanner reads two config files and emits hits for any banned-term match found in a file that is NOT covered by the language-scoped allowlist. Three contracts specify the expected shapes and live in `contracts/`:

- `contracts/neutrality-lint-contract.md` — C-3: pytest test harness contract (WP03 will consume this).
- `contracts/banned-terms-schema.yaml` — C-4: JSON Schema for `banned_terms.yaml`.
- `contracts/language-scoped-allowlist-schema.yaml` — C-5: JSON Schema for `language_scoped_allowlist.yaml`.

The data model in `data-model.md` (Entity 1 through Entity 3) is the authoritative description of runtime types. This WP implements those types.

A baseline audit found the following doctrine files currently contain banned terms — they MUST seed the allowlist, or the lint fails on its first run:

- `src/doctrine/agent_profiles/shipped/python-implementer.agent.yaml`
- `src/doctrine/styleguides/shipped/python-conventions.styleguide.yaml`
- `src/doctrine/toolguides/shipped/python-review-checks.toolguide.yaml`
- `src/doctrine/toolguides/shipped/PYTHON_REVIEW_CHECKS.md`

Two further files in `src/doctrine/_reference/quickstart-agent-augmented-development/candidates/` also hit banned terms but are reference/import candidates, not shipped artifacts. Decide during T006 whether to allowlist them (safer) or exclude the `_reference/` subtree from the scan roots (cleaner). Recommendation: allowlist them explicitly — being explicit beats broad exclusions.

One additional file, `src/doctrine/skills/spec-kitty-setup-doctor/SKILL.md`, mentions `pytest` — spec-kitty itself is a Python tool so the setup-doctor skill is legitimately Python-scoped. Allowlist it.

## Branch Strategy

Planning base branch is `main`; merge target is `main`. Execution worktree path is resolved by the runtime from `lanes.json`.

## Implementation Sketch

### Subtask T004 — Create the package skeleton

**Files** (new):

- `src/charter/neutrality/__init__.py` (~20 lines) — public API. Re-export `run_neutrality_lint`, `BannedTermHit`, `NeutralityLintResult`.
- `src/charter/neutrality/lint.py` — placeholder for T007.
- `src/charter/neutrality/banned_terms.yaml` — placeholder for T005.
- `src/charter/neutrality/language_scoped_allowlist.yaml` — placeholder for T006.

Module-level docstring in `__init__.py` names the mission and links to the contracts in the mission folder for readers.

### Subtask T005 — Author `banned_terms.yaml`

Seed with exactly these four entries (per research.md R-003 — intentionally narrow to avoid false positives):

```yaml
schema_version: "1"
terms:
  - id: PY-001
    kind: literal
    pattern: "pytest"
    rationale: "Primary offender in pre-3.1.5 prompts; unambiguously Python test framework."
    added_in: "3.2.0"
  - id: PY-002
    kind: literal
    pattern: "junit"
    rationale: "Python ecosystem reporter (pytest-junit). Unambiguously Python test ecosystem."
    added_in: "3.2.0"
  - id: PY-003
    kind: regex
    pattern: "\\bpip install\\b"
    rationale: "Concrete Python install command."
    added_in: "3.2.0"
  - id: PY-004
    kind: regex
    pattern: "\\bpython -m\\b"
    rationale: "Python module execution command."
    added_in: "3.2.0"
```

Do NOT add entries for `pytest.ini`, `pyproject.toml`, `.py` suffix, or `conftest.py`. Those false-positive on multi-ecosystem enumerations in generic templates (see R-003 "Terms dropped after a grep pass").

Format the YAML with two-space indentation and a top-of-file comment block pointing readers to the contract and explaining how to add a new term:

```yaml
# Neutrality banned-terms list. Schema: contracts/banned-terms-schema.yaml
#
# To add a term:
#   1. Append an entry with a fresh id matching ^[A-Z]{2,4}-\d{3}$.
#   2. Set `kind` to "literal" or "regex".
#   3. Provide a rationale of at least 8 characters.
#   4. Run `pytest tests/charter/test_neutrality_lint.py` to verify.
```

### Subtask T006 — Author `language_scoped_allowlist.yaml`

Seed with exactly these entries (baseline audit — these files WILL hit banned terms on first scan):

```yaml
schema_version: "1"
paths:
  - path: "src/doctrine/agent_profiles/shipped/python-implementer.agent.yaml"
    scope: python
    owner: "charter team"
    reason: "Shipped Python implementer agent profile; pytest/pip references are intentional."
    added_in: "3.2.0"
  - path: "src/doctrine/styleguides/shipped/python-conventions.styleguide.yaml"
    scope: python
    owner: "charter team"
    reason: "Canonical Python conventions styleguide; Python vocabulary is the subject."
    added_in: "3.2.0"
  - path: "src/doctrine/toolguides/shipped/python-review-checks.toolguide.yaml"
    scope: python
    owner: "charter team"
    reason: "Python review-check toolguide; tool names (pytest, mypy) are the subject."
    added_in: "3.2.0"
  - path: "src/doctrine/toolguides/shipped/PYTHON_REVIEW_CHECKS.md"
    scope: python
    owner: "charter team"
    reason: "Human-readable companion to python-review-checks.toolguide.yaml."
    added_in: "3.2.0"
  - path: "src/doctrine/_reference/quickstart-agent-augmented-development/candidates/agent-python-pedro.import.yaml"
    scope: python
    owner: "charter team"
    reason: "Reference import candidate for the Python agent profile; quickstart material."
    added_in: "3.2.0"
  - path: "src/doctrine/_reference/quickstart-agent-augmented-development/candidates/toolguide-python-review-checks.import.yaml"
    scope: python
    owner: "charter team"
    reason: "Reference import candidate for the Python review-checks toolguide."
    added_in: "3.2.0"
  - path: "src/doctrine/skills/spec-kitty-setup-doctor/SKILL.md"
    scope: python
    owner: "charter team"
    reason: "Spec Kitty itself is a Python package; setup-doctor skill necessarily references Python tooling."
    added_in: "3.2.0"
```

Add a top-of-file comment block explaining the schema, mirroring the style of `banned_terms.yaml`.

**Before committing**: run the scanner (after T007) and confirm it returns `passed=True`. If additional files surface as banned-term hits, **audit each one** before adding to the allowlist — a new hit may indicate a real regression, not a legitimate language-scoped artifact.

### Subtask T007 — Implement `lint.py`

**File**: `src/charter/neutrality/lint.py` (~180 lines).

Public surface (importable from `charter.neutrality`):

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class BannedTermHit:
    file: Path             # repo-relative
    line: int              # 1-indexed
    column: int            # 1-indexed
    term_id: str
    match: str

@dataclass(frozen=True)
class NeutralityLintResult:
    hits: tuple[BannedTermHit, ...]
    stale_allowlist_entries: tuple[str, ...]
    scanned_file_count: int
    banned_term_count: int
    allowlisted_path_count: int

    @property
    def passed(self) -> bool:
        return not self.hits and not self.stale_allowlist_entries

def run_neutrality_lint(
    *,
    repo_root: Path | None = None,
    scan_roots: list[Path] | None = None,
    banned_terms_path: Path | None = None,
    allowlist_path: Path | None = None,
) -> NeutralityLintResult:
    ...
```

Scan roots (when caller doesn't override):

1. `src/doctrine/` — **primary bias surface**; this one is load-bearing per R-001 and must NOT be omitted.
2. `src/charter/` excluding `src/charter/neutrality/` itself (the scanner must not match its own config files).
3. `src/specify_cli/missions/*/command-templates/` (glob).
4. `src/specify_cli/missions/*/mission.yaml` (glob).
5. `.kittify/charter/` if present in the working tree.

Implementation notes:

- **File types**: scan `.md`, `.yaml`, `.yml`, `.txt`, `.j2`. Skip binary files, `.pyc`, `__pycache__`, and any path under `.worktrees/`.
- **Reading**: `path.read_text(encoding="utf-8", errors="replace")`. Do not raise on decoding issues.
- **Literal terms** (`kind: literal`): simple substring match per-line; record line and column.
- **Regex terms** (`kind: regex`): `re.compile(pattern, re.MULTILINE)` at load time, applied per-line. If any regex fails to compile, raise a clear `ValueError` naming the offending term id.
- **Allowlist match**: build one `pathlib.PurePath` match per entry. Globs (e.g. `src/charter/profiles/python/**/*.md`) use `pathlib.Path.match` semantics or `fnmatch` on the POSIX path. Literal paths match by string equality against repo-relative POSIX form.
- **Stale allowlist detection**: if an allowlist entry resolves to zero files, record the raw path string in `stale_allowlist_entries`. This is a hard failure signal — reviewers must delete stale entries, not ignore them.
- **Counts**: `scanned_file_count` = files traversed (allowlisted ones are counted but not scanned for hits); `banned_term_count` = total term definitions loaded; `allowlisted_path_count` = total allowlist entries loaded.

YAML loading uses `ruamel.yaml` (already a project dependency). Never use `yaml.load` without a safe loader.

Type-annotate everything. Use `from __future__ import annotations` so forward references are cheap.

### Subtask T008 — Verify on baseline

From the worktree root:

```bash
python -c "from charter.neutrality import run_neutrality_lint; r = run_neutrality_lint(); print('passed:', r.passed); print('hits:', len(r.hits)); print('stale:', r.stale_allowlist_entries)"
```

Expected output:

```
passed: True
hits: 0
stale: ()
```

If `passed` is `False`:

- **If hits are on known-Python files**: the allowlist is incomplete; add the specific path, document why, and re-run.
- **If hits are on a generic file**: congratulations, you found a real neutrality regression. Report it — do NOT bury it in the allowlist. Decide whether the offending content should be scrubbed (most cases) or the file genuinely needs to become language-scoped (rare).
- **If stale entries appear**: a path in the allowlist does not resolve; either fix the path or remove the stale entry.

### Subtask T009 — Confirm `mypy --strict` passes

```bash
mypy --strict src/charter/neutrality/
```

Must return zero errors. Add type annotations to any helper that slipped through.

## Files

- **New**: `src/charter/neutrality/__init__.py`
- **New**: `src/charter/neutrality/lint.py`
- **New**: `src/charter/neutrality/banned_terms.yaml`
- **New**: `src/charter/neutrality/language_scoped_allowlist.yaml`

## Definition of Done

- [ ] All four files exist and are importable / parseable.
- [ ] `from charter.neutrality import run_neutrality_lint, BannedTermHit, NeutralityLintResult` succeeds.
- [ ] `run_neutrality_lint()` on baseline returns `passed=True`.
- [ ] Seed populations in the two YAMLs match the spec in T005 and T006 exactly.
- [ ] `mypy --strict src/charter/neutrality/` passes.
- [ ] Coverage on `lint.py` is ≥ 90% once WP03's test module lands (verify during WP03 review).

## Risks

- **Running from a worktree**: when called from `.worktrees/...`, the default scan roots (`src/doctrine/`, `src/charter/`, …) are relative to the worktree root, which is a full checkout of the repo. This should work without special cases. If it doesn't, add a `repo_root` parameter defaulting to the directory containing the caller's `pyproject.toml`.
- **Glob semantics**: `pathlib.Path.glob("src/charter/profiles/python/**/*.md")` and `pathlib.Path.match` have subtle differences. Pick one and be consistent. When in doubt, use `fnmatch.fnmatchcase` on the POSIX-form repo-relative path.
- **Hidden surprise hits**: the baseline audit found 7 banned-term-containing doctrine files. If you see more during T008, do NOT assume they all belong in the allowlist — audit each one.
- **YAML loader choice**: use `ruamel.yaml` with `typ="safe"`, not `yaml.load`. Project dependencies assume the former.

## Reviewer Checklist

- [ ] `banned_terms.yaml` contains exactly PY-001 through PY-004; no wider enumeration.
- [ ] `language_scoped_allowlist.yaml` contains exactly the seven seed entries above; no others.
- [ ] Scan roots include `src/doctrine/` — **this is load-bearing**, not optional.
- [ ] Scanner excludes `src/charter/neutrality/` itself from scanning (prevents self-hits).
- [ ] Stale allowlist entries are reported in the result, not silently ignored.
- [ ] `run_neutrality_lint()` is a pure function — no hidden state, no side effects beyond filesystem reads.
- [ ] `mypy --strict` passes on the whole package.

## Activity Log

- 2026-04-17T09:25:22Z – claude:sonnet-4-6:implementer:implementer – shell_pid=6410 – Assigned agent via action command
- 2026-04-17T09:41:11Z – claude:sonnet-4-6:implementer:implementer – shell_pid=6410 – Ready for review: baseline passes (345 files scanned, 0 hits, 0 stale), mypy --strict clean (2 source files, 0 errors). 4 banned terms seeded, 8 allowlist entries.
