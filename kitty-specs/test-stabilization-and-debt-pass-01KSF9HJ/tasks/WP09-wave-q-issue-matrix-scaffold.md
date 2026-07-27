---
work_package_id: WP09
title: 'Wave Q: /spec-kitty.tasks scaffolds issue-matrix.md when spec references GH issues (FR-009)'
dependencies: []
requirement_refs:
- FR-009
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
base_commit: a0d62e57fa9af2936094634195baa621fd1af8c1
created_at: '2026-05-25T14:47:23.478839+00:00'
subtasks:
- T036
- T037
- T038
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1966774"
history:
- by: claude
  at: '2026-05-25T14:00:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tasks/
execution_mode: code_change
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- src/specify_cli/cli/commands/tasks_finalize.py
- src/specify_cli/tasks/issue_matrix.py
- tests/specify_cli/tasks/test_issue_matrix_scaffold.py
priority: P2
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further.

## Objective

When `/spec-kitty.tasks` (i.e. `spec-kitty agent mission setup-tasks` and friends) runs against a mission whose `spec.md` references GitHub issue numbers (e.g. `#1298`, `#1163`), automatically scaffold `kitty-specs/<slug>/issue-matrix.md` with one row per detected issue.

The schema matches the Gate-4 contract from `spec-kitty-mission-review`: columns `Issue`, `Title`, `Verdict`, `Evidence ref`. Closes #1163 and partially closes F-08 of mission 01KSAF14 (the duplication of acceptance-matrix.json and issue-matrix.md).

## Branch strategy

- Planning base branch: mission lane branch
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- [`spec.md`](../spec.md) FR-009.
- [#1163](https://github.com/Priivacy-ai/spec-kitty/issues/1163) — the inbound feature request.
- `docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md` F-08 (acceptance-matrix vs issue-matrix duplication).
- `~/.claude/skills/spec-kitty-mission-review/SKILL.md` Step 8.5 Gate 4 — the consumer schema.

## Subtask details

### T036 — DIR-012 assign #1163 to HiC

```bash
unset GITHUB_TOKEN
gh issue edit 1163 --add-assignee stijn-dejongh --repo Priivacy-ai/spec-kitty
```

### T037 — Detect GH issue references in spec.md

Create `src/specify_cli/tasks/issue_matrix.py` (NEW module):

```python
"""Scaffold ``issue-matrix.md`` from GitHub-issue references in a mission spec.

Closes #1163.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple


_GH_ISSUE_PATTERN = re.compile(
    r"(?:^|\s|\(|\[)#(\d{2,6})(?=\s|\)|\]|,|;|\.|$)",
    re.MULTILINE,
)


class IssueReference(NamedTuple):
    number: int
    first_line_context: str  # the line in spec.md where this issue first appears


def detect_issue_references(spec_md_path: Path) -> list[IssueReference]:
    """Return the unique list of GH issue refs in spec.md, ordered by first appearance.

    Skips refs that look like markdown anchor links (``#section-name``) and
    requires the number to be 2-6 digits to avoid matching markdown headings.
    """
    text = spec_md_path.read_text(encoding="utf-8")
    seen: dict[int, str] = {}
    for line in text.splitlines():
        for match in _GH_ISSUE_PATTERN.finditer(line):
            num = int(match.group(1))
            if num not in seen:
                seen[num] = line.strip()
    return [IssueReference(num, ctx) for num, ctx in seen.items()]
```

### T038 — Scaffold the issue-matrix.md skeleton

Add to `src/specify_cli/tasks/issue_matrix.py`:

```python
def scaffold_issue_matrix(
    feature_dir: Path,
    spec_md_path: Path,
) -> Path | None:
    """Author ``feature_dir/issue-matrix.md`` from detected refs.

    Returns the path to the generated file, or ``None`` if no GH issue refs
    appear in spec.md. Does NOT overwrite an existing issue-matrix.md.
    """
    out_path = feature_dir / "issue-matrix.md"
    if out_path.exists():
        return out_path  # respect existing operator-curated file
    refs = detect_issue_references(spec_md_path)
    if not refs:
        return None
    lines = [
        f"# Issue matrix — {feature_dir.name}",
        "",
        "Per FR-037 of spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.",
        "",
        "| Issue | Title | Verdict | Evidence ref |",
        "|-------|-------|---------|--------------|",
    ]
    for ref in refs:
        lines.append(f"| #{ref.number} | <fill at WP-implementation time> | unknown | <link or commit> |")
    lines.append("")
    lines.append("Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`.")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
```

Wire it into the `/spec-kitty.tasks` flow at `src/specify_cli/cli/commands/tasks_finalize.py` (or wherever `setup-tasks` / `finalize-tasks` is the natural call site):

```python
# In the tasks-finalize / tasks-outline command body, after the existing scaffold work:
from specify_cli.tasks.issue_matrix import scaffold_issue_matrix
issue_matrix_path = scaffold_issue_matrix(feature_dir, spec_file)
if issue_matrix_path is not None:
    typer.echo(f"[info] Scaffolded {issue_matrix_path.relative_to(repo_root)}")
```

Create `tests/specify_cli/tasks/test_issue_matrix_scaffold.py` covering:
- spec.md with multiple `#NNN` refs → matrix has all refs, no duplicates.
- spec.md with no refs → returns `None`, no file created.
- Existing `issue-matrix.md` → not overwritten.
- `#section-name` anchor-style refs are NOT matched.

## Definition of Done

- [ ] Issue #1163 assigned to HiC.
- [ ] `src/specify_cli/tasks/issue_matrix.py` exists with `detect_issue_references` + `scaffold_issue_matrix`.
- [ ] `tasks_finalize.py` (or equivalent) invokes the scaffold after the existing setup.
- [ ] `tests/specify_cli/tasks/test_issue_matrix_scaffold.py` covers the 4 scenarios above; all pass.
- [ ] `ruff check src/specify_cli/tasks/ tests/specify_cli/tasks/` clean.
- [ ] `mypy --strict src/specify_cli/tasks/issue_matrix.py` clean.

## Risks

- **Wrong call site**: `/spec-kitty.tasks` is a slash-command alias for multiple CLI subcommands (setup-tasks, finalize-tasks, tasks-outline, tasks-packages). Wire the scaffold call into the EARLIEST point in the flow that has both `feature_dir` and `spec_file` available — typically `setup-tasks` or `tasks-outline`.
- **Regex false positives**: markdown anchor-style refs `#section-name` and code-block `#NNN` references inside fenced code may produce false positives. The 2-6 digit requirement filters common false positives but won't catch all.

## Reviewer guidance

1. Verify the scaffold runs only ONCE per mission (idempotent: existing file not overwritten).
2. Verify the regex pattern doesn't match `#section-name` style anchor links.
3. Spot-check that the scaffolded matrix's `Verdict` column header matches the skill's Gate-4 enum.

## Activity Log

- 2026-05-25T14:47:24Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1920014 – Assigned agent via action command
- 2026-05-25T14:56:45Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1920014 – issue-matrix.md scaffold landed (closes #1163)
- 2026-05-25T14:57:21Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1966774 – Started review via action command
- 2026-05-25T14:59:39Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1966774 – Review passed: issue-matrix scaffold landed, #1163 closed, 4/4 + 10/10 regression tests
