# Mission Review Report: 083-agent-skills-codex-vibe

**Reviewer**: Claude Opus 4.6 (mission-review skill)
**Date**: 2026-04-14T11:07:13Z
**Mission**: `083-agent-skills-codex-vibe` — Agent Skills Support for Codex and Vibe
**Baseline commit**: `1ca0310c` (plan-phase commit, pre-implementation)
**HEAD at review**: `11650e9b`
**WPs reviewed**: WP01..WP07
**Source artifacts read**: spec.md, plan.md, tasks.md, research.md, data-model.md, quickstart.md, contracts/skill-renderer.contract.md, contracts/skills-manifest.schema.json, status.events.jsonl

---

## FR Coverage Matrix

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|-------|---------------------|----------|--------------|---------------|---------|
| FR-001 | `--ai vibe` accepted by init and agent config | WP04, WP05 | `test_init_vibe.py`, `test_agent_config_vibe.py` | ADEQUATE | — |
| FR-002 | `config.yaml` round-trips `vibe` | WP04 | `test_init_vibe.py:test_init_vibe_config_yaml`, `test_agent_config_vibe.py` | ADEQUATE | — |
| FR-003 | `init --ai vibe --non-interactive` exits 0 and leaves project driveable | WP05 | `test_init_vibe.py` | **FALSE_POSITIVE** | [RISK-1] init exits 0 but SKILL.md files are **not** installed |
| FR-004 | Render every canonical `/spec-kitty.*` command as Agent Skills package | WP02, WP03 | `test_command_renderer.py`, `test_command_installer.py` | PARTIAL | [DRIFT-1] spec names 16 commands, implementation renders 11 |
| FR-005 | Single `SKILL.md` body satisfies both Codex and Vibe | WP02 | `test_command_renderer.py` (snapshot tests) | ADEQUATE | — |
| FR-006 | Installer writes additively; tolerates third-party subdirs | WP03 | `test_command_installer.py::TestThreeTenantCoexistence` | **PARTIAL** | [RISK-4] test uses a `src/specify_cli/missions/` symlink into tmpdir that does not exist in production user projects |
| FR-007 | Installer tracks ownership (manifest with hashes) | WP01, WP03 | `test_manifest_store.py`, `test_command_installer.py` | ADEQUATE | — |
| FR-008 | `agent config remove` removes only no-longer-needed entries | WP04 | `test_agent_config_vibe.py::test_remove_vibe_leaves_codex_entries` | PARTIAL | [RISK-4] same synthetic-fixture concern |
| FR-009 | `verify-setup --check-tools` detects `vibe` binary | WP05 | `test_verify_vibe.py` | ADEQUATE | — |
| FR-010 | `.vibe/` protected in `.gitignore` | WP05 | `test_init_vibe.py::test_init_vibe_gitignore` | ADEQUATE | — |
| FR-011 | Codex removed from `AGENT_COMMAND_CONFIG`; served via skills | WP04 | `test_config_registry.py` | ADEQUATE (registry) / **FALSE_POSITIVE** (end-to-end) | [RISK-1, RISK-2] registry change correct; no live path actually serves Codex from skills for new installs |
| FR-012 | Migration deletes owned `.codex/prompts/` files; preserves non-Spec-Kitty files | WP06 | `test_m_3_2_0_codex_to_skills.py` | PARTIAL | [DRIFT-2] edge case (user-edited files must be surfaced) is not honored — Option A silently deletes all owned files |
| FR-013 | `AI_CHOICES`, `AGENT_DIRS`, `AGENT_DIR_TO_KEY`, `AGENT_SKILL_CONFIG`, `get_agent_dirs_for_project()` include `vibe` as shared-root | WP04 | `test_config_registry.py` | PARTIAL | [DRIFT-3] literal reading requires `vibe` in `AGENT_DIRS` and `AGENT_DIR_TO_KEY`; implementation omits it by design (arguably correct but textually non-compliant) |
| FR-014 | README and CLAUDE.md list Vibe + Codex Agent Skills shape | WP07 | Manual inspection | ADEQUATE | — |
| FR-015 | Mission delivers an architecture decision record | WP07 | — | **MISSING** | [DRIFT-4] no ADR under `architecture/adrs/`; content exists only in `kitty-specs/083-.../` |
| FR-016 | Automated tests cover 8 listed scenarios | WP01-WP07 | Multiple | PARTIAL | [RISK-1] the `init --ai vibe` test does not assert SKILL.md installation, which was on the list |

**Legend**: ADEQUATE = test constrains the required behavior. PARTIAL = test exists but uses synthetic fixture that does not match production model, or is textually narrower than the FR. MISSING = no artifact found. FALSE_POSITIVE = test passes even though the implementation is not wired into the live runtime path.

---

## Drift Findings

### DRIFT-1: FR-004 canonical command set is 11, spec says 16

**Type**: PUNTED-FR (partial scope drift)
**Severity**: MEDIUM
**Spec reference**: FR-004
**Evidence**:
- `kitty-specs/083-agent-skills-codex-vibe/spec.md` line 66: "`specify`, `plan`, `tasks`, `tasks-outline`, `tasks-packages`, `tasks-finalize`, `implement`, `review`, `accept`, `merge`, `analyze`, `research`, `checklist`, `status`, `dashboard`, `charter`" (16 commands).
- `src/specify_cli/skills/command_installer.py:47-59`: `CANONICAL_COMMANDS` tuple has 11 entries (`tasks-finalize`, `accept`, `merge`, `status`, `dashboard` missing).
- `ls src/specify_cli/missions/software-dev/command-templates/` confirms only 11 template files exist; the 5 missing commands never had templates.

**Analysis**: The 5 missing commands (`tasks-finalize`, `accept`, `merge`, `status`, `dashboard`) are real spec-kitty slash commands that exist as registered CLI subcommands (visible in the user's skill listing) but have no Markdown template file in the repo. For Codex and Vibe users, invoking `/spec-kitty.tasks-finalize` or `/spec-kitty.accept` inside the coding agent will not work after this mission — those commands have no skill package. This is a pre-existing gap (the template files were never present on pre-mission `main` either), so it is not a regression introduced by this mission. However, FR-004 was accepted during specify-phase review and the mission did not flag the impossibility of delivering it until the implementer phase. Either the FR text needed to be tightened during plan phase, or 5 template files needed to be authored as part of this mission.

---

### DRIFT-2: FR-012 edge case — user-edited files silently discarded

**Type**: LOCKED-DECISION VIOLATION (spec §Edge Cases clause)
**Severity**: HIGH
**Spec reference**: FR-012, spec.md lines 67 (Edge Cases)
**Evidence**:
- `spec.md` line 67: "A project previously used Codex via `.codex/prompts/` and ran into content drift (a user edited one of the prompt files by hand). Upgrade must not silently discard those edits without either migrating them into the new skill or surfacing them to the user; at minimum the old files must be preserved in git history so a user who edited them can recover."
- `src/specify_cli/upgrade/migrations/_legacy_codex_hashes.py`: ships `LEGACY_CODEX_FILENAMES: frozenset[str]` with no hash comparison.
- `src/specify_cli/upgrade/migrations/m_3_2_0_codex_to_skills.py:111-116`: `_classify()` labels every `.codex/prompts/spec-kitty.<command>.md` file as `owned_unedited` if the filename is in the set; no content check.
- `m_3_2_0_codex_to_skills.py:255-258`: `p.path.unlink()` runs on every `owned` file with only a summary "Migrated N Codex prompts" log; no per-file notice and no "you may have edited these" warning.
- `data-model.md` §LegacyCodexPrompt explicitly described a `status: "owned_edited"` state with a user-facing preservation notice; this state is declared in code (line 83) but explicitly unused (comment line 76-77: "`owned_edited` is unused in the Option-A implementation").

**Analysis**: The spec's Edge Cases clause requires the migration to either preserve user edits or surface them to the user. The Option A simplification taken by WP06 (filename-only matching) eliminates the surfacing branch and relies solely on "git history preserves the files" as mitigation. In practice, a user who hand-edited `.codex/prompts/spec-kitty.specify.md` to customize their workflow will run `spec-kitty upgrade`, receive a cheerful "Migrated 11 Codex prompts" message, and not realize their edits were deleted from the working tree until they notice the custom behavior has vanished. Recovery via git log is possible for users who know to look; the spec explicitly called this out and required active surfacing. The docstring at `_legacy_codex_hashes.py:18-22` telling users to "stash or rename these files before running `spec-kitty upgrade`" is not equivalent to surfacing them at upgrade time — it assumes users read migration-internal documentation before running an upgrade, which they do not.

---

### DRIFT-3: FR-013 literal text requires `vibe` in `AGENT_DIRS` but implementation omits

**Type**: PUNTED-FR (textual non-compliance; intent preserved)
**Severity**: LOW
**Spec reference**: FR-013
**Evidence**:
- FR-013 text: "The AI choices list, agent directories registry, and migration helpers (`AI_CHOICES`, `AGENT_DIRS`, `AGENT_DIR_TO_KEY`, `AGENT_SKILL_CONFIG`, and `get_agent_dirs_for_project()`) MUST be updated to include `vibe` as a shared-root agent..."
- `src/specify_cli/agent_utils/directories.py` `AGENT_DIRS` has no `vibe` entry; docstring explicitly says "codex and vibe use AGENT_SKILL_CONFIG".
- `AGENT_DIR_TO_KEY` has no `.vibe`-keyed entry either.

**Analysis**: The implementation decision is arguably correct — `AGENT_DIRS` is for command-layer directories (the 12 agents that have `.<agent>/commands/` or similar), and `vibe` has no such directory. But the FR literally requires updating `AGENT_DIRS` to include vibe. This is either a spec-text error that should have been caught in spec-phase review, or it is a real gap — the existing callers of `get_agent_dirs_for_project()` (notably migrations `m_0_10_1_populate_slash_commands.py` and others that iterate `AGENT_DIRS`) will not see `vibe`, which means any future migration that edits "all installed agents' directories" will silently skip vibe. Low severity because no current user flow is broken; this is a landmine for future maintenance.

---

### DRIFT-4: FR-015 ADR not delivered to `architecture/adrs/`

**Type**: PUNTED-FR
**Severity**: HIGH
**Spec reference**: FR-015
**Evidence**:
- FR-015 text: "The mission MUST deliver an architecture decision record describing the Agent Skills renderer contract, the shared-root coexistence policy, and the Codex migration path."
- `git diff 1ca0310c..HEAD --stat -- architecture/` returns **empty**.
- `architecture/adrs/` exists in the repo as the canonical ADR location (confirmed via `ls architecture/`).
- The content described (renderer contract, coexistence policy, migration path) exists in `kitty-specs/083-agent-skills-codex-vibe/plan.md`, `research.md`, and `contracts/skill-renderer.contract.md`, but these are per-mission docs that will not be indexed in the repo's ADR navigation.

**Analysis**: "Architecture decision record" is a defined repo convention with a specific filesystem location. The FR named it explicitly. WP07 owned the documentation surface but did not create `architecture/adrs/YYYY-MM-DD-N-agent-skills-renderer.md`. Reviewers during WP07 did not flag this (the WP07 task prompt also did not explicitly require it, and it was not in the per-WP DoD). This is a straightforward gap: a 1-2 page ADR should be authored referencing the existing plan/research content so that the architectural decision is discoverable from the repo's ADR index for future maintainers.

---

## Risk Findings

### RISK-1: No live code path installs vibe's command-skill packages (CRITICAL, RELEASE-BLOCKING)

**Type**: DEAD-CODE / CROSS-WP-INTEGRATION
**Severity**: CRITICAL
**Location**: `src/specify_cli/runtime/agent_commands.py:105-121`, `src/specify_cli/cli/commands/init.py:540-555`, `src/specify_cli/cli/commands/agent/config.py:95-140`
**Trigger condition**: User runs `spec-kitty init --ai vibe` or `spec-kitty agent config add vibe` on any real project.

**Analysis**: The implementation of `command_installer.install()` is functional and well-tested in isolation, but has no live caller that produces the user-facing behavior the spec promises.

1. `runtime/agent_commands.py:119-121` — the codex/vibe branch:
   ```python
   if agent_key in ("codex", "vibe"):
       from specify_cli.skills import command_installer
       return command_installer.install(Path.home(), agent_key)
   ```
   This branch sits inside `_sync_agent_commands()`, whose only caller is the auto-sync loop at `runtime/agent_commands.py:241`: `for agent_key in AGENT_COMMAND_CONFIG:`. After WP04 removed `codex` and excluded `vibe` from `AGENT_COMMAND_CONFIG`, this loop no longer iterates codex or vibe. The codex/vibe branch at line 119 is therefore **unreachable via the auto-sync path**. It is also arguably wrong even if reached: it passes `Path.home()` as `repo_root`, which would install into the user's home directory, violating NG-1 ("No global install").

2. `cli/commands/init.py:540-555` — the init flow:
   ```python
   agent_skill_class = (AGENT_SKILL_CONFIG.get(agent_key) or {}).get("class", "")
   if agent_skill_class in (SKILL_CLASS_SHARED, SKILL_CLASS_WRAPPER):
       tracker.complete(f"{agent_key}-skills", "skipped (global runtime)")
   else:
       # install_skills_for_agent(...) runs only for non-SHARED classes
   ```
   `vibe` (and `codex`) are in `SKILL_CLASS_SHARED`, so init **skips** skill installation with the message "skipped (global runtime)". Neither `install_skills_for_agent` (the legacy canonical-skill installer) nor `command_installer.install` (the new command-skill installer) is called for vibe.

3. `cli/commands/agent/config.py:134-140` — the `agent config add` flow:
   ```python
   if agent_key in _SKILL_ONLY_AGENTS:
       # Skill-only agents (codex, vibe) are registered in config only;
       # their skill files are installed at runtime via the skills installer.
       added.append(agent_key)
       config.available.append(agent_key)
       ...
       continue
   ```
   Updates `config.yaml` only. The comment claims "installed at runtime via the skills installer" — but no runtime path actually calls `command_installer.install()` for vibe.

**Net effect**: `spec-kitty init --ai vibe` and `spec-kitty agent config add vibe` complete successfully and print "Next steps for Mistral Vibe", but `.agents/skills/spec-kitty.<command>/SKILL.md` is never created and `.kittify/skills-manifest.json` is never written. When the user launches Vibe and types `/spec-kitty.specify`, Vibe will find no skill to invoke.

This is the exact "module with passing tests but no callers from live entry points" anti-pattern the skill guide warns about. The WP05 test `test_init_vibe.py` does **not** assert that SKILL.md files exist after init — I asked for that assertion in my dispatch prompt but the implementer omitted it, and the reviewer did not catch the omission.

**Remediation (outside this review's scope)**: wire `command_installer.install(project_path, agent_key)` into both `init.py` (after config write, for each codex/vibe agent) and `agent config add` (on the skill-only branch, before the `continue`). Fix `_sync_agent_commands` either to not call with `Path.home()` or to remove the codex/vibe branch entirely since it is now unreachable.

---

### RISK-2: `_resolve_template()` assumes `repo_root` contains the spec-kitty source tree (CRITICAL, RELEASE-BLOCKING)

**Type**: BOUNDARY-CONDITION
**Severity**: CRITICAL
**Location**: `src/specify_cli/skills/command_installer.py:45-49, 141-149`
**Trigger condition**: Any call to `command_installer.install(project_path, ...)` where `project_path` is a real user project (i.e., anything other than a spec-kitty-cli dev checkout).

**Analysis**: The template-path resolution builds an absolute filesystem path by joining `repo_root` with the repo-relative path `src/specify_cli/missions/software-dev/command-templates`:

```python
_COMMAND_TEMPLATES_REL = Path(
    "src/specify_cli/missions/software-dev/command-templates"
)

def _resolve_template(repo_root: Path, command: str) -> Path:
    return repo_root / _COMMAND_TEMPLATES_REL / f"{command}.md"
```

A real user project never contains `src/specify_cli/missions/...` inside its own tree. The installed `specify_cli` Python package contains those templates, and they must be located via `importlib.resources` (or equivalent), not via a path relative to the user's project.

Empirical confirmation: I ran `command_installer.install('/tmp/wp07-smoke', 'vibe')` against a tmpdir simulating a real project. The call raised:

```
SkillRenderError: template_not_found: {'path': '/tmp/wp07-smoke/src/specify_cli/missions/software-dev/command-templates/analyze.md'}
```

The test suites hide this bug because every installer test fixture symlinks the real `src/specify_cli/missions` directory into the tmpdir:

- `tests/specify_cli/skills/test_command_installer.py:79-86`:
  ```python
  missions_src = _TEMPLATE_REPO_ROOT / "src" / "specify_cli" / "missions"
  missions_dst = tmp_path / "src" / "specify_cli"
  missions_dst.mkdir(parents=True, exist_ok=True)
  missions_link = missions_dst / "missions"
  if not missions_link.exists():
      missions_link.symlink_to(missions_src)
  ```

- `tests/specify_cli/upgrade/test_m_3_2_0_codex_to_skills.py:49-54` does the same.

This is the exact "synthetic fixture that does not match the production model" pattern the skill guide warns about.

**Net effect**: Even if RISK-1 is fixed and `command_installer.install()` is wired into init/add, it will fail with `SkillRenderError("template_not_found")` on every real user project. The Codex upgrade migration (`m_3_2_0_codex_to_skills.py`) will also fail for the same reason on any user project that is not a spec-kitty-cli dev checkout.

**Remediation (outside this review's scope)**: change `_resolve_template` to use `importlib.resources.files("specify_cli.missions.software-dev.command-templates")` to locate the packaged templates, not the user's filesystem.

---

### RISK-3: `_sync_agent_commands` would write to `~/.agents/skills/` if ever reached (HIGH)

**Type**: BOUNDARY-CONDITION / NON-GOAL INVASION
**Severity**: HIGH (conditional — depends on RISK-1 remediation)
**Location**: `src/specify_cli/runtime/agent_commands.py:119-121`
**Trigger condition**: Any future code path that calls `_sync_agent_commands("codex", ...)` or `_sync_agent_commands("vibe", ...)` directly.

**Analysis**: The current branch:
```python
if agent_key in ("codex", "vibe"):
    from specify_cli.skills import command_installer
    return command_installer.install(Path.home(), agent_key)
```

passes `Path.home()` as the `repo_root` argument. `command_installer.install()` writes skill packages to `<repo_root>/.agents/skills/spec-kitty.<command>/` — which in this case resolves to `~/.agents/skills/`. This directly violates Non-Goal §1 of the spec ("Global (`~/`) skill installation for Vibe or Codex. This release targets project-local `.agents/skills/` only.").

Currently dead code (see RISK-1), but a future refactor that makes this function reachable for codex/vibe would silently globally-install skill packages into the user's home directory, bypassing both the spec's locked Non-Goal and the Codex migration's own project-local semantics.

**Remediation**: delete the codex/vibe branch from `_sync_agent_commands` entirely (codex/vibe are no longer auto-sync targets) or refactor to pass the correct project path.

---

### RISK-4: Test fixtures symlink production source tree; production execution unverified (HIGH)

**Type**: FALSE-POSITIVE TEST COVERAGE
**Severity**: HIGH
**Location**: Multiple test files (see list below)
**Trigger condition**: Tests pass in CI but do not exercise the production code path.

**Analysis**: Every test that exercises `command_installer.install()` or the codex migration symlinks the repo's real `src/specify_cli/missions/` directory into the test tmpdir so that `_resolve_template` can find the templates. Three test files are implicated:

- `tests/specify_cli/skills/test_command_installer.py:79-86` (fixture `repo`)
- `tests/specify_cli/skills/test_command_renderer.py` (also resolves templates relative to the repo source)
- `tests/specify_cli/upgrade/test_m_3_2_0_codex_to_skills.py:44-55` (fixture copier)

Because the fixtures match the implementation's incorrect assumption (templates are at `<repo_root>/src/specify_cli/missions/...`), the tests never exercise the production path where templates must be located inside the installed package. The regression test `test_twelve_agent_parity.py` uses a different code path (`render_command_template()` from `asset_generator`) and is not affected — but it covers the legacy command-file renderer, not the new `command_installer`.

**Remediation**: add at least one integration test that invokes `command_installer.install(project_path, "vibe")` against a tmpdir **without** symlinking the missions directory — simulating a real user project — and asserts that the install succeeds. If the current implementation makes that impossible (it does), the test will fail, surfacing RISK-2.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|-------------|
| `cli/commands/init.py:541-544` | `agent_skill_class in (SKILL_CLASS_SHARED, SKILL_CLASS_WRAPPER)` | `tracker.complete(..., "skipped (global runtime)")` — no SKILL.md install | FR-003: `init --ai vibe` claims success, user has no working skills |
| `cli/commands/agent/config.py:134-140` | `agent_key in _SKILL_ONLY_AGENTS` | `console.print("✓ Registered ... (skill-only agent)")` — no SKILL.md install | FR-001/FR-008 add/remove round-trip runs against a manifest that never gets created |
| `runtime/agent_commands.py:243-249` | `except Exception: logger.warning(..., exc_info=True)` | Warning in logs; no user-visible error | Any codex/vibe install failure inside the auto-sync loop would be swallowed (currently dead code) |
| `upgrade/migrations/m_3_2_0_codex_to_skills.py:255-260` | `except OSError as exc: warnings.append(...)` | Warning in migration result; user sees "Could not remove X" | User-edited files that fail deletion go into warnings but the upgrade proceeds; see DRIFT-2 |

The first two rows are the RISK-1 root cause made concrete: init and agent-config report success without performing the operation the spec requires.

---

## Security Notes

No security findings. The new code paths do not touch subprocess, network, credentials, or file locking. `agent_key` is validated against the `SUPPORTED_AGENTS = ("codex", "vibe")` allowlist before any filesystem path is constructed. `command` in `.agents/skills/spec-kitty.{command}/SKILL.md` comes from a hardcoded `CANONICAL_COMMANDS` tuple, not user input. Atomic writes use `Path.with_suffix()` + `os.replace`, which is standard-safe. No shell interpolation anywhere in new code.

---

## Final Verdict

### **FAIL**

### Verdict rationale

The mission cannot ship as-is. Two CRITICAL, release-blocking findings make the headline deliverable — Mistral Vibe support — non-functional on every real user project:

1. **RISK-1**: No live code path installs vibe's command-skill packages. `spec-kitty init --ai vibe` completes successfully but never calls `command_installer.install()`. The `.agents/skills/spec-kitty.<command>/SKILL.md` files are never written. When a user launches Vibe and types `/spec-kitty.specify`, nothing happens.

2. **RISK-2**: Even if RISK-1 were fixed, `_resolve_template()` looks for templates at `<project_path>/src/specify_cli/missions/...` — a path that exists in the spec-kitty-cli dev checkout but not in any real user project. The installer will fail with `SkillRenderError("template_not_found")` the first time it runs against a non-symlinked project. Tests mask this by symlinking the source tree into every fixture.

Both findings are consequences of an incorrect assumption about where templates live at runtime, compounded by a test suite whose fixtures match the implementation's assumption rather than the production model. The Opus per-WP reviewers did not catch RISK-1 (the test suite for `init --ai vibe` does not assert on SKILL.md creation, only on exit code and config.yaml). RISK-2 is latent across WP03, WP06, and WP07 and would only have been caught by a test fixture that simulated a real user project.

Announcing Mistral Vibe support with the next release, as the mission charter required, is **not safe** until these two findings are remediated and the new tests exercise a production-shaped fixture (no symlink, templates located via `importlib.resources`).

Secondary drift findings (FR-004 scope, FR-012 edge case, FR-013 literal compliance, FR-015 ADR) are all non-blocking but should be addressed before the release announcement to preserve the spec's credibility.

### Release-blocking findings that must be fixed

- **RISK-1** (CRITICAL): wire `command_installer.install(project_path, agent_key)` into the init/add flow for codex and vibe. Add an integration test that asserts SKILL.md files exist under `.agents/skills/` after `init --ai vibe`.
- **RISK-2** (CRITICAL): replace the filesystem-relative `_resolve_template` with `importlib.resources`-based template loading. Add an integration test against a tmpdir without the symlink fixture.

### Open items (non-blocking)

- **DRIFT-1**: either tighten FR-004 to 11 canonical commands or add the 5 missing template files in a follow-up mission.
- **DRIFT-2**: add a migration step that hashes existing `.codex/prompts/spec-kitty.*.md` against a known-good reference before deletion, and surfaces any mismatched files to the user with a preservation notice. The `LegacyCodexPrompt.status = "owned_edited"` state is already declared; wire it up.
- **DRIFT-3**: either update FR-013 to reflect the registry distinction (`AGENT_DIRS` is command-layer only) or extend `AGENT_DIRS` semantics to cover shared-root agents and iterate callers.
- **DRIFT-4**: author `architecture/adrs/2026-04-14-1-agent-skills-renderer.md` pulling the locked decisions and contract from `plan.md` + `contracts/skill-renderer.contract.md`.
- **RISK-3**: delete the unreachable codex/vibe branch in `_sync_agent_commands` once RISK-1 is remediated, so the landmine does not resurface in a future refactor.
- **RISK-4**: after fixing RISK-2, remove the `missions` symlinks from test fixtures — they will no longer be needed, and their presence is itself a quality-signal hazard.

### Review cycle signal

Only WP04 had a rejection cycle (cycle 1: ruff-only feedback, cycle 2: approved). No arbiter overrides. The clean cycle history is consistent with the fact that per-WP reviews did catch surface-quality issues but could not catch cross-WP integration gaps by construction — which is exactly the failure mode this mission-review skill exists to surface.
