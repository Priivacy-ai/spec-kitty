# Проверка Windows hard-gates

**Дата**: 2026-08-14

**Тип**: How-To
**Аудитория**: сопровождающий Spec Kitty

## 1. Подготовка

```powershell
Set-Location 'C:\Users\Ruslan\.codex-worktrees\spklw-planning-setup-plan-hard-gates'
uv sync --frozen --extra test --extra lint
git status --short --branch
```

## 2. Targeted portability и collection

Сначала подтвердить collection всех известных файлов:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q -p no:cacheprovider `
  tests\cli\commands\test_sync_doctor_consent_health_3030.py `
  tests\integration\test_intake_size_cap.py `
  tests\review\test_pre_review_gate_engine.py `
  tests\specify_cli\core\test_target_branch_primitive.py `
  tests\sync\test_consent_fault_vocabulary_3030.py `
  tests\sync\test_consent_write_refusal_3030.py `
  tests\sync\test_issue_598_hang_fixes.py
```

Затем запустить точные portability и dependent coverage/shard/session-reaper commands из WP01. До зелёного targeted packet полный architecture suite не запускать.

## 3. Полные локальные gates

```powershell
.\.venv\Scripts\python.exe -m pytest tests\contract -q
.\.venv\Scripts\python.exe -m pytest tests\architectural -q
```

Ожидается `0 failed`, `0 errors`. Skip/xfail фиксируются отдельно и не удаляются ради зелёного результата.

## 4. Code map и статические проверки

```powershell
.\.venv\Scripts\python.exe -m ruff check <changed-python-files>
.\.venv\Scripts\python.exe -m mypy --strict <changed-production-files>
.\.venv\Scripts\python.exe -m py_compile <changed-python-files>
git diff --check
```

Дополнительно проверить JSON/HTML parity и SHA-256 из `docs/codemap/codemap.lock`, а независимым oracle — что карта перечисляет callers/impact/tests для обеих изменённых boundaries.

## 5. Внешний E2E gate

Сначала проверить read-only доступ к `Priivacy-ai/spec-kitty-end-to-end-testing`. При отсутствии доступа локальная реализация может иметь `implementation_complete=true`, но handoff обязан оставить `e2e_ready=false` и `release_ready=false`; не клонировать подмену и не создавать exception. При доступе использовать documented commands самого E2E-репозитория против exact CLI commit.
