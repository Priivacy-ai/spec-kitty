# Quickstart — CLI Interview Decision Moments

Operator / implementer walkthrough. Assumes a checkout at `spec-kitty/` root.

## 1. Refresh the editable install after the events bump

```bash
pip install -e ".[dev]"
```

Verify:
```bash
python -c "import spec_kitty_events; print(spec_kitty_events.__version__)"
# expect: 4.0.0
```

## 2. Run the CLI locally

```bash
spec-kitty agent decision --help
spec-kitty agent decision open --help
```

## 3. Happy path — specify interview

```bash
# Simulated session
MISSION=my-feature-01ABCDEF
spec-kitty agent decision open \
  --mission $MISSION \
  --flow specify \
  --slot-key specify.intent-summary.q1 \
  --input-key auth_strategy \
  --question "Which auth strategy should we use?" \
  --options '["session","oauth2","oidc","Other"]'
# → {"decision_id": "01J...", "idempotent": false, ...}

# User answers "oauth2":
spec-kitty agent decision resolve 01J... --final-answer oauth2

# Verify clean state:
spec-kitty agent decision verify --mission $MISSION
# → {"status": "clean", ...}
```

## 4. Deferred path + sentinel

```bash
spec-kitty agent decision defer 01J... --rationale "revisit in plan"
# LLM then writes into spec.md:
# [NEEDS CLARIFICATION: auth strategy deferred from specify] <!-- decision_id: 01J... -->

spec-kitty agent decision verify --mission $MISSION
# → {"status": "clean", "findings": []}

# If the marker is removed from spec.md, verify fails:
spec-kitty agent decision verify --mission $MISSION
# → non-zero exit; findings include DEFERRED_WITHOUT_MARKER
```

## 5. Idempotent retry

```bash
# First call:
spec-kitty agent decision open \
  --mission $MISSION --flow specify \
  --slot-key specify.intent-summary.q1 --input-key auth_strategy \
  --question "Which auth strategy should we use?"
# → 01J... (new)

# Immediate retry with identical key:
spec-kitty agent decision open ... (same args)
# → 01J... (same decision_id, idempotent=true)
```

## 6. Local-first verification

```bash
unset SPEC_KITTY_ENABLE_SAAS_SYNC
# Run any decision operation — no SaaS calls, no hosted auth access:
spec-kitty agent decision open ...
```

## 7. Testing

```bash
pytest tests/specify_cli/decisions/ tests/specify_cli/cli/commands/test_decision.py -q
ruff check src/specify_cli/decisions/ src/specify_cli/cli/commands/decision.py
mypy src/specify_cli/decisions/
```

## 8. Charter integration smoke

```bash
spec-kitty charter interview --mission $MISSION
# Walk through questions; verify decisions/ directory fills up; answers.yaml unchanged in format.
```

## 9. Release checklist

- [ ] `pyproject.toml` `spec-kitty-events==4.0.0`
- [ ] `src/specify_cli/spec_kitty_events/` refreshed from 4.0.0 source
- [ ] `src/specify_cli/decisions/` module present and tested
- [ ] `src/specify_cli/cli/commands/decision.py` registered in `cli/main.py`
- [ ] `specify.md` and `plan.md` templates updated with ask-time/terminal instructions
- [ ] Charter interview wired to the API
- [ ] `pytest tests/ -q` green
- [ ] `ruff check .` + `ruff format --check .` clean
- [ ] `mypy` clean on changed modules
