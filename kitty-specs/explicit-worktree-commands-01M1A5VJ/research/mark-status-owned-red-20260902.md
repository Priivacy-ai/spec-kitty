# RED owned-режима `mark-status`

Карта вызовов обновлена на базе `ca91f626e`: Typer wrapper вызывает
`tasks_mark_status`, который повторно выбирает primary через
`get_main_repo_root`; status writer и ambient hooks находятся в прямой цепочке.

Новый real-Git тест создаёт primary, selected и sibling worktrees, финализирует
mission только в selected и вызывает настоящий `tasks.app`:

```text
uv run pytest tests/integration/test_owned_checkout_mark_status.py::test_mark_status_updates_only_selected_checkout -vv
```

Результат: `1 failed`. Команда завершилась кодом 2 на точном контрактном
разрыве `No such option: --owned-checkout`. Это не ошибка fixture, mission
resolver или status writer. Реализация ещё не изменена.

Push, install, publication и реальные lifecycle-записи не выполнялись.
