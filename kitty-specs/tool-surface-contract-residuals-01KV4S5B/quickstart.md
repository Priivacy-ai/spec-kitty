# Quickstart / Validation Scenarios — ToolSurfaceContract Residual Closeout

Manual + automated checks that each residual is closed. All run from the repo root.

## IC-01 — #1940 profile-projection diagnostics + provenance

```bash
# Each condition emits its specific code (set up fixtures per test):
spec-kitty doctor tool-surfaces --kind agent-profile --json | jq '.findings[].code'
#  → includes profile-source-invalid / profile-name-invalid /
#    profile-overlay-conflict / profile-sentinel-skipped under their conditions
pytest tests/specify_cli/tool_surface/profiles/ -q          # per-finding-code tests green
# Manifest carries 8 fields incl. provenance:
jq '.entries[0] | keys' .kittify/agent-profiles-manifest.json
#  → [...,"source_path","source_hash","projection_version"]
```
- A `.kittify/agent-profiles-manifest.json` written by the pre-fix code (6 fields) loads without error.

## IC-02 — #1941 registry-backed agent sets

```bash
python -c "from specify_cli.cli.commands.agent import config; from specify_cli.skills import command_installer; assert set(config.SKILL_ONLY_AGENTS)==set(command_installer.SUPPORTED_AGENTS), 'not registry-backed'"
pytest tests/specify_cli/cli/commands/test_agent_config.py tests/specify_cli/cli/commands/test_agent_config_compat.py -q   # frozen interface green
# new scenario:
pytest -k "claude and session_presence" tests/specify_cli/cli/commands/ -q
```

## IC-03 — #1942 docs-lint CI enforcement (the proof: it must FAIL on drift)

```bash
pytest tests/specify_cli/tool_surface/test_docs.py -q        # passes clean
# adversarial: inject an unregistered surface path into a doc, then:
pytest tests/specify_cli/tool_surface/test_docs.py -q        # FAILS (docs.FINDING_UNREGISTERED_PATH == "UNREGISTERED_PATH")
# CI: confirm the integration-tests-core-misc shard collects it
grep -A3 "tool_surface" .github/workflows/ci-quality.yml      # path-filter entry present
grep -n "pytest.mark.integration" tests/specify_cli/tool_surface/test_docs.py
```

## IC-04 — #1944 guide + #1965 deterministic test

```bash
ls docs/**/setup*tool*surface* docs/**/*upgrade* 2>/dev/null  # user-facing guide present
pytest tests/specify_cli/tool_surface/test_docs.py -q         # guide is lint-clean
# determinism: passes even with an ambient ~/.claude present, from any cwd:
SPECIFY_REPO_ROOT=$(mktemp -d) pytest -k test_doctor_skills_json_error_schema_stable -q
python -c "import os,tempfile; os.environ['SPECIFY_REPO_ROOT']=tempfile.mkdtemp(); from specify_cli.core.paths import locate_project_root; print(locate_project_root())"
#  → prints the temp dir (override honored), NOT the ambient checkout
```

## Cross-cutting gates (all ICs)

```bash
ruff check <changed files> && mypy --strict <changed files>          # NFR-002
pytest tests/architectural/test_no_legacy_terminology.py -q          # NFR-003 (no feature* aliases)
pytest tests/specify_cli/tool_surface/ -q                            # full provider suite green
# backward-compat (NFR-001):
pytest -k "doctor_skills or agent_config_compat" -q
```
