---
work_package_id: WP07
title: FR-006 + FR-007 close-with-evidence regressions
dependencies: []
requirement_refs:
- FR-006
- FR-007
- NFR-007
- NFR-008
planning_base_branch: release/3.2.0a5-tranche-1
merge_target_branch: release/3.2.0a5-tranche-1
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a5-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a5-tranche-1 unless the human explicitly redirects the landing branch.
created_at: '2026-04-27T18:00:45+00:00'
subtasks:
- T033
- T034
- T035
agent: "reviewer-renata"
shell_pid: "84538"
history:
- at: '2026-04-27T18:00:45Z'
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: tests/specify_cli/cli/
execution_mode: code_change
mission_id: 01KQ7YXHA5AMZHJT3HQ8XPTZ6B
mission_slug: release-3-2-0a5-tranche-1-01KQ7YXH
owned_files:
- tests/specify_cli/cli/test_no_visible_feature_alias.py
- tests/specify_cli/cli/test_decision_command_shape_consistency.py
- tests/e2e/test_feature_alias_smoke.py
role: implementer
tags:
- regression-only
- close-with-evidence
---

# WP07 — FR-006 + FR-007 close-with-evidence regressions

## ⚡ Do This First: Load Agent Profile

Before reading further or making any edits, invoke the `/ad-hoc-profile-load` skill with these arguments:

- **Profile**: `implementer-ivan`
- **Role**: `implementer`

This loads your identity, governance scope, and self-review checklist. Even though this WP is test-only, the profile carries the bug-fixing-checklist tactic that ensures the tests you add actually exercise the invariants they claim to enforce.

## Objective

Lock down two "already correct on `main`" invariants by adding regression tests that prevent future drift, then close GitHub issues #790 and #774 with explicit "fixed; here's the regression" evidence per `start-here.md` "Done Criteria":

1. **FR-006 (#790)**: Every `--feature` declaration carries `hidden=True` (verified during planning) AND every existing call site that passes `--feature` continues to behave identically to `--mission`.
2. **FR-007 (#774)**: The decision command shape is consistently `spec-kitty agent decision { open | resolve | defer | cancel | verify }` across `--help`, docs, and skill snapshots — no `spec-kitty decision …` or `spec-kitty agent decisions …` survives.

## Context

From [research.md R5](../research.md#r5--feature-alias-hiding-fr-006--790) and [R6](../research.md#r6--spec-kitty-agent-decision-command-shape-fr-007--774):

- Verified during planning that all 28 `--feature` declarations across 17 command files already carry `hidden=True`.
- Verified during planning that the only documentation reference to the decision command (`docs/reference/missions.md:268`) already matches the canonical shape.

This WP adds NO production-code changes. It adds three test files and updates the GitHub issues.

See contracts:
- [feature_alias_hidden.contract.md](../contracts/feature_alias_hidden.contract.md)
- [decision_command_help.contract.md](../contracts/decision_command_help.contract.md)

## Branch Strategy

- **Planning base branch**: `release/3.2.0a5-tranche-1`
- **Final merge target**: `release/3.2.0a5-tranche-1`
- This WP has no dependencies; its lane is rebased directly onto `release/3.2.0a5-tranche-1`.
- Execution worktrees are allocated per computed lane from `lanes.json` (created by `finalize-tasks`).

## Subtasks

### T033 — Add `tests/specify_cli/cli/test_no_visible_feature_alias.py`

**Purpose**: Lock the `hidden=True` invariant via typer introspection AND `--help` output scanning.

**Files**:
- `tests/specify_cli/cli/test_no_visible_feature_alias.py` (new)

**Steps**:

1. Create the new test file:

   ```python
   from __future__ import annotations

   import re

   import click
   import pytest
   from click.testing import CliRunner

   from specify_cli.cli import cli  # adjust import to actual entrypoint


   FEATURE_TOKEN_RE = re.compile(r"--feature\b")


   def _walk_commands(group: click.Group, prefix: tuple[str, ...] = ()):
       for name, cmd in group.commands.items():
           path = prefix + (name,)
           if isinstance(cmd, click.Group):
               yield from _walk_commands(cmd, path)
           else:
               yield path, cmd


   def test_every_feature_parameter_is_hidden() -> None:
       offenders: list[str] = []
       for path, cmd in _walk_commands(cli):
           for param in cmd.params:
               if param.name == "feature" and not getattr(param, "hidden", False):
                   offenders.append(" ".join(path))
       assert not offenders, (
           "Found visible --feature parameter on:\n  " + "\n  ".join(offenders)
       )


   def test_help_output_never_mentions_feature_alias() -> None:
       runner = CliRunner()
       offenders: list[tuple[str, str]] = []
       for path, _cmd in _walk_commands(cli):
           result = runner.invoke(cli, list(path) + ["--help"], catch_exceptions=False)
           if FEATURE_TOKEN_RE.search(result.output):
               offenders.append((" ".join(path), result.output))
       assert not offenders, (
           "Found '--feature' token in --help output of:\n  "
           + "\n  ".join(name for name, _ in offenders)
       )
   ```

2. Adjust the `from specify_cli.cli import cli` import to the actual top-level Click/Typer object — check sibling tests in `tests/specify_cli/cli/`.

**Validation**:
- [ ] `pytest tests/specify_cli/cli/test_no_visible_feature_alias.py -q` exits 0 against current `main` (FR-006 is already satisfied).
- [ ] Same test FAILS if you temporarily flip one `hidden=True` to `hidden=False` (verify locally).

### T034 — Add `tests/e2e/test_feature_alias_smoke.py`

**Purpose**: Confirm the alias still WORKS — `--feature` continues to route to `--mission` semantics.

**Files**:
- `tests/e2e/test_feature_alias_smoke.py` (new)

**Steps**:

1. Pick one historically-accepting subcommand. The cleanest target is `spec-kitty agent mission status` (read-only).
2. Create the new test file:

   ```python
   from __future__ import annotations

   import json
   import subprocess
   from pathlib import Path

   import pytest


   def _init_project(tmp_path: Path) -> Path:
       subprocess.run(
           ["spec-kitty", "init", "demo", "--no-confirm"],
           cwd=tmp_path, check=True, capture_output=True, text=True,
       )
       project = tmp_path / "demo"

       # Create one mission so status has something to report.
       subprocess.run(
           [
               "spec-kitty", "agent", "mission", "create",
               "smoke",
               "--friendly-name", "Smoke",
               "--purpose-tldr", "Smoke",
               "--purpose-context", "Smoke test for FR-006 alias compatibility.",
               "--json",
           ],
           cwd=project, check=True, capture_output=True, text=True,
       )

       return project


   def test_feature_alias_routes_to_mission(tmp_path: Path) -> None:
       project = _init_project(tmp_path)

       # Resolve the actual mission slug created above.
       list_result = subprocess.run(
           ["spec-kitty", "agent", "mission", "list", "--json"],
           cwd=project, check=True, capture_output=True, text=True,
       )
       missions = json.loads(list_result.stdout)
       slug = missions[0]["mission_slug"]

       # Invoke with --mission
       mission_result = subprocess.run(
           ["spec-kitty", "agent", "tasks", "status", "--mission", slug, "--json"],
           cwd=project, check=False, capture_output=True, text=True,
       )

       # Invoke with --feature
       feature_result = subprocess.run(
           ["spec-kitty", "agent", "tasks", "status", "--feature", slug, "--json"],
           cwd=project, check=False, capture_output=True, text=True,
       )

       # Both calls succeed
       assert mission_result.returncode == 0, (mission_result.stdout, mission_result.stderr)
       assert feature_result.returncode == 0, (feature_result.stdout, feature_result.stderr)

       # Behavior is equivalent (modulo timestamps)
       mission_payload = json.loads(mission_result.stdout)
       feature_payload = json.loads(feature_result.stdout)
       # Drop volatile fields (e.g. timing) before comparison
       for payload in (mission_payload, feature_payload):
           payload.pop("now_utc_iso", None)
           payload.pop("NOW_UTC_ISO", None)
       assert mission_payload == feature_payload
   ```

3. If `agent mission list` doesn't exist or has a different shape, switch to whichever read-only command is closest to the test's needs. The point is: same command, two flags, same JSON.

**Validation**:
- [ ] `pytest tests/e2e/test_feature_alias_smoke.py -q` exits 0.

**Edge Cases / Risks**:
- The `tasks status` payload may include timestamps that differ between the two calls. Strip them before comparison.

### T035 — Add `tests/specify_cli/cli/test_decision_command_shape_consistency.py`

**Purpose**: Lock the canonical decision-command shape across docs, help, and snapshots.

**Files**:
- `tests/specify_cli/cli/test_decision_command_shape_consistency.py` (new)

**Steps**:

1. Create the new test file:

   ```python
   from __future__ import annotations

   import re
   from pathlib import Path

   import click
   import pytest
   from click.testing import CliRunner

   from specify_cli.cli import cli  # adjust import to actual entrypoint


   REPO_ROOT = Path(__file__).resolve().parents[3]
   EXPECTED_SUBCOMMANDS = {"open", "resolve", "defer", "cancel", "verify"}

   # Any non-canonical shape — these MUST NOT appear anywhere.
   NON_CANONICAL_RE = re.compile(
       r"spec-kitty\s+(?:agent\s+)?(?:decisions\b|decision-)"
       r"|"
       r"spec-kitty\s+decision\b(?!\s+(?:open|resolve|defer|cancel|verify))",
   )

   SCAN_ROOTS = [
       "docs",
       ".agents/skills",
       "tests/specify_cli/skills/__snapshots__",
       "src/specify_cli/missions",
   ]


   def test_agent_decision_subgroup_has_canonical_subcommands() -> None:
       agent_grp = cli.commands.get("agent")
       assert isinstance(agent_grp, click.Group), "spec-kitty agent group missing"
       decision_grp = agent_grp.commands.get("decision")
       assert isinstance(decision_grp, click.Group), "spec-kitty agent decision group missing"
       assert set(decision_grp.commands.keys()) == EXPECTED_SUBCOMMANDS


   def test_help_output_lists_canonical_subcommands() -> None:
       runner = CliRunner()
       result = runner.invoke(cli, ["agent", "decision", "--help"], catch_exceptions=False)
       for sub in EXPECTED_SUBCOMMANDS:
           assert sub in result.output, (
               f"Subcommand {sub!r} missing from `agent decision --help`:\n{result.output}"
           )


   def test_no_non_canonical_decision_command_shape_in_repo_text() -> None:
       offenders: list[tuple[str, str]] = []
       for rel in SCAN_ROOTS:
           root = REPO_ROOT / rel
           if not root.exists():
               continue
           for path in root.rglob("*"):
               if not path.is_file():
                   continue
               try:
                   text = path.read_text(encoding="utf-8", errors="ignore")
               except OSError:
                   continue
               for match in NON_CANONICAL_RE.finditer(text):
                   offenders.append((str(path.relative_to(REPO_ROOT)), match.group(0)))
       assert not offenders, (
           "Found non-canonical decision command shape:\n  "
           + "\n  ".join(f"{p}: {m!r}" for p, m in offenders)
       )
   ```

2. Run; expect green against current `main`.

**Validation**:
- [ ] `pytest tests/specify_cli/cli/test_decision_command_shape_consistency.py -q` exits 0.

**Edge Cases / Risks**:
- The non-canonical regex must NOT false-positive on legitimate text like "decision documentation requirement" — the regex is anchored to the `spec-kitty …` prefix to avoid that. Sanity-check by running it across the existing repo and verifying zero false matches.

## Test Strategy

Three independent test files, each enforcing one slice of NFR-007 (FR-006) or NFR-008 (FR-007). All three pass against current `main`; their value is preventing future drift.

## Definition of Done

- [ ] T033–T035 complete.
- [ ] `pytest tests/specify_cli/cli/test_no_visible_feature_alias.py tests/e2e/test_feature_alias_smoke.py tests/specify_cli/cli/test_decision_command_shape_consistency.py -q` exits 0.
- [ ] PR description includes:
  - "Already-fixed-on-main" rationale citing research.md R5 and R6.
  - One-line CHANGELOG entries for **WP02** to consolidate. Suggested:
    - `Add regression tests confirming \`--feature\` aliases stay hidden from \`--help\` while remaining accepted (#790).`
    - `Add regression test confirming \`spec-kitty agent decision\` command shape stays consistent across docs / help / skill snapshots (#774).`
  - Note that #790 and #774 are now closeable as "fixed; regression added at <test paths>".

## Risks

- **R1**: The non-canonical decision-command regex may false-positive on legitimate prose. Sanity check with `grep -rEn 'spec-kitty\s+(agent\s+)?(decisions\b|decision-)' .` before committing — expect zero matches today.
- **R2**: A future Click/Typer upgrade may change the `param.name` attribute for hidden params. The test asserts on `getattr(param, "hidden", False)` defensively to survive that.

## Reviewer Guidance

- Verify all three tests pass against the current tree without any production code change.
- Verify the regex in T035 is anchored on the `spec-kitty …` prefix so it doesn't snag on prose.
- Verify the `--feature` alias smoke (T034) actually exercises the alias on a command that currently accepts both flags (audit `agent tasks status` to confirm).

## Implementation command

```bash
spec-kitty agent action implement WP07 --agent claude
```

## Activity Log

- 2026-04-27T20:40:48Z – claude:sonnet:implementer-ivan:implementer – shell_pid=82876 – Started implementation via action command
- 2026-04-27T20:52:31Z – claude:sonnet:implementer-ivan:implementer – shell_pid=82876 – Ready for review: 3 new test files; --feature stays hidden, agent decision shape consistent
- 2026-04-27T20:53:40Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=84538 – Started review via action command
- 2026-04-27T20:55:44Z – reviewer-renata – shell_pid=84538 – Review passed: 3 new test files (T033/T034/T035) all green, ruff clean, regex zero false-positives across docs/skills/snapshots/templates. Deviation rulings: (1) param.opts inspection is correct - the contract polices the --feature CLI flag, not Python param names; (2) filtering hidden=True from decision subgroup equality check is correct - widen is correctly registered hidden, contract polices visible surface; (3) in-process CliRunner exercises both --mission and --feature on agent tasks status with JSON equivalence; (4) status/WP03 working-tree dirt is unrelated artifact, WP07 commit a46ce144 touches only the 3 new test files; (5) move-task --force standard for gitignored dossier file.
