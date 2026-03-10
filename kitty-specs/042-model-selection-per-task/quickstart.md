# Quickstart: Model Selection per Task

**Feature**: 042-model-selection-per-task

## User Setup

1. Create `~/.spec-kitty/config.yaml` (or add to existing file):

```yaml
models:
  specify: claude-opus-4-6
  plan: claude-opus-4-6
  implement: claude-sonnet-4-6
  review: claude-sonnet-4-6
```

2. Run upgrade in any spec-kitty project:

```bash
spec-kitty upgrade
```

3. Verify injection:

```bash
head -5 .claude/commands/spec-kitty.specify.md
# Expected:
# ---
# description: ...
# model: claude-opus-4-6
# ---
```

## Notes

- Only commands listed in `models:` receive a `model:` field — others are unaffected
- Run `spec-kitty upgrade` again after changing the config to re-apply
- Model names are not validated — use names valid for your agent subscription
- Unknown command names in config produce a warning during upgrade

## Developer Setup

```bash
cd /path/to/spec-kitty
pip install -e ".[dev]"
pytest tests/specify_cli/test_model_injection_migration.py -v
```
