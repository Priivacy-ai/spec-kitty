# Quickstart проверки

## Сквозной сценарий

1. Создать чистый временный Git-репозиторий Spec Kitty и caller-owned linked worktree вне managed `.worktrees`.
2. Из linked worktree создать Mission.
3. Выполнить по `mission_id`: status, context resolve, setup-plan/spec-commit, tasks finalize, action implement/review, next и accept в предусмотренных тестом состояниях.
4. На каждом шаге проверить одинаковые `mission_id`, slug и путь внутри caller-owned worktree.
5. Сравнить branch, HEAD и `git status --porcelain` repository-root checkout с исходным снимком.

## Отрицательные сценарии

- Создать несовместимые копии одной selector-формы в caller и repository-root checkout: ожидать структурированную conflict-ошибку и нулевую запись.
- Передать explicit root: ожидать разрешение только относительно него.
- Выполнить managed lane/coord regressions: ожидать прежние пути и прежний запрет вложенного Mission create.
- Создать два caller-owned worktree с разными Mission: каждый selector видит только собственную Mission.

## Gates

```powershell
pytest -q <targeted lifecycle tests>
ruff check <changed Python files>
mypy --strict <changed production modules>
git diff --check
```

Дополнительно: 100 повторов детерминированности и benchmark с 100 Mission, p95 overhead не более 50 мс.
