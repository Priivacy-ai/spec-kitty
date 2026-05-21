# Quickstart: Verifying the Runtime Safety Follow-ups

Run commands from the repository root:

`/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260521-124440-zhQksA/spec-kitty`

## WP01 Retrospective Schema

```bash
uv run pytest tests/cli/test_agent_retrospect_synthesize.py tests/cli/commands/test_retrospect.py
uv run mypy --strict src/specify_cli/retrospective src/specify_cli/cli/commands/agent_retrospect.py
```

Manual smoke:

```bash
uv run spec-kitty retrospect create --mission <slug>
uv run spec-kitty agent retrospect synthesize --mission <slug>
uv run spec-kitty agent retrospect synthesize --mission <slug> --apply
```

## WP02 Decision Closure

```bash
uv run pytest tests/cli tests/agent -k "decision or accept or clarification"
uv run mypy --strict src/specify_cli/decisions src/specify_cli/acceptance
```

Manual smoke:

```bash
uv run spec-kitty agent decision open --mission <slug> --flow specify --slot-key specify.example --input-key example --question "Q?"
uv run spec-kitty agent decision defer <decision_id> --mission <slug> --rationale "defer to plan default"
uv run spec-kitty agent decision resolve <decision_id> --mission <slug> --final-answer "Accept plan default"
uv run spec-kitty agent decision verify --mission <slug>
```

## WP03 Owned Files Validation

```bash
uv run pytest tests/tasks tests/agent -k "finalize or owned_files"
uv run pytest tests/architectural
```

## WP04 Bulk-edit Planning Pre-flight

```bash
uv run pytest tests/agent tests/cli -k "bulk_edit or occurrence_map or acknowledge_not_bulk_edit or implement"
uv run mypy --strict src/specify_cli/bulk_edit src/specify_cli/cli/commands/implement.py src/specify_cli/cli/commands/agent/workflow.py
```

## WP05 Lane Collapse

```bash
uv run pytest tests/tasks tests/runtime -k "lane or lanes or finalize"
uv run mypy --strict src/specify_cli/lanes
```

## WP06 Docs

```bash
uv run pytest tests/docs tests/architectural -k "docs or toc or link"
```

If a command explicitly tests hosted auth, tracker, sync, or SaaS behavior on
this machine, prefix it with:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 <command>
```
