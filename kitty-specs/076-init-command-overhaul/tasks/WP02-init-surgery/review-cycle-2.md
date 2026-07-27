---
affected_files: []
cycle_number: 2
mission_slug: 076-init-command-overhaul
reproduction_command:
reviewed_at: '2026-04-08T06:03:53Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

## Review Cycle 1 Feedback

**Reviewer:** codex:gpt-4o:python-reviewer:reviewer
**Date:** 2026-04-08

---

### Issue 1: `github_client` import and `download_and_extract_template` alias not removed (BLOCKING)

**File:** `src/specify_cli/cli/commands/init.py`, lines 43–56

**Current code:**
```python
from specify_cli.template.github_client import (
    download_and_extract_template as download_and_extract_template_github,
)
...
# Backward-compatible symbol used by tests and older integrations.
download_and_extract_template = download_and_extract_template_github
```

**Problem:**
Per subtask T014, the `download_and_extract_template` import from `github_client` must be removed. WP03 will delete `github_client.py` entirely; leaving this import in place will cause an `ImportError` once WP03 lands. The comment "Backward-compatible symbol used by tests and older integrations" is incorrect — the only test that monkeypatches `init_module.download_and_extract_template` is `tests/agent/test_init_command.py`, which tests the old remote-template download mode that has been removed by this WP. That test should be deleted or updated to not rely on the remote mode.

**How to fix:**
1. Delete lines 43–45 (the import block) and line 56 (the alias assignment).
2. Check `tests/agent/test_init_command.py` — if it tests the old remote-template flow (SPECIFY_TEMPLATE_REPO, `--script`, `--skip-tls` flags), delete or update that test to match the new simplified interface. The test at line 114 monkeypatches `download_and_extract_template` and invokes the old `--script`/`--skip-tls` flags which no longer exist.

**Verification:**
```bash
grep -n "download_and_extract_template\|github_client" src/specify_cli/cli/commands/init.py
# Must return 0 results
```

---

### All Other Criteria: PASS

- Flag count: `--help` shows only `--ai`, `--non-interactive`, `--no-git` (plus `--help`) — PASS
- Non-interactive test: `spec-kitty init --non-interactive --ai claude /tmp/test-$$` exits 0 — PASS
- Doctrine dead code (`_run_doctrine_stack_init`, `_run_inline_interview`, `_apply_doctrine_defaults`) — all removed, PASS
- Dashboard dead code (`ensure_dashboard_running`, `_maybe_generate_structure_templates`) — all removed, PASS
- `AgentSelectionConfig`, `preferred_implementer`, `preferred_reviewer` — all removed, PASS
- `ensure_runtime()` error handling: uses `_console.print("[red]Error:[/red] ...")` and `raise typer.Exit(1)` — PASS
- File size: 740 lines (within 600–800 target) — PASS
- mypy: 0 errors in `init.py` — PASS
- `_prepare_project_minimal()` does not create `.kittify/charter/` — PASS
- Global skill installation: implemented via `SkillRegistry.from_package()` loop — PASS
- Positive flow intact: banner, path resolution, agent selection, ensure_runtime, skills, scaffolding, git init, config save — PASS
- Scope discipline: only `init.py` and `init_help.py` changed (the latter is appropriate as init's companion help text) — PASS
