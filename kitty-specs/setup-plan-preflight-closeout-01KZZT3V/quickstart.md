# Быстрая проверка реализации

## RED

```powershell
.\.venv\Scripts\python.exe -m pytest tests\agent\test_agent_feature.py::TestGitPreflightEnforcement::test_setup_plan_exits_on_preflight_failure_json -q
```

Ожидаемый baseline на regression HEAD: тест получает `PLAN_CONTEXT_UNRESOLVED` вместо `GIT_PREFLIGHT_FAILED`.

Добавить production-path тесты, которые до исправления доказывают:

- Mission resolver вызывается раньше failed preflight;
- caller-owned checkout нельзя получить простым использованием `located_root`;
- порядок/количество вызовов чувствительны к mutation.

## GREEN

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\agent\test_agent_feature.py::TestGitPreflightEnforcement `
  tests\integration\test_caller_owned_worktree_lifecycle.py -q
```

## Статические gates

```powershell
.\.venv\Scripts\python.exe -m ruff check <changed-python-files>
.\.venv\Scripts\python.exe -m mypy --strict <changed-production-files>
.\.venv\Scripts\python.exe -m py_compile <changed-python-files>
git diff --check
```

Broad failures считать baseline только после branch/base differential и существующего либо нового GitHub issue согласно charter.
