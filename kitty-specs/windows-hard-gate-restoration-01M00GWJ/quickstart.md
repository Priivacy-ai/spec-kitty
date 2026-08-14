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

Запустить команды, перечисленные в соответствующих work-package prompts. До зелёного targeted packet полный architecture suite не запускать.

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

Дополнительно проверить JSON/HTML parity и SHA-256 из `docs/codemap/codemap.lock`.

## 5. Внешний E2E gate

Сначала проверить read-only доступ к `Priivacy-ai/spec-kitty-end-to-end-testing`. При отсутствии доступа завершить handoff состоянием `blocked`; не клонировать подмену и не создавать exception. При доступе использовать documented commands самого E2E-репозитория против exact CLI commit.
