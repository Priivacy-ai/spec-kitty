# Переход выбранной рабочей копии в ревью

## Реализовано

- `move-task --owned-checkout` поддерживает переход `in_progress -> for_review`;
- `planning_commit_sha` один раз разрешается в конкретный commit и используется
  как база diff и проверки наличия реализации;
- база должна существовать, отличаться от `HEAD` и быть его предком;
- выбранная копия проходит штатные проверки как `lane_workspace`, без обхода
  через `repo_root`;
- TASKS_INDEX и STATUS_STATE для внутренней проверки подзадач читаются через
  `effective_root`;
- незакоммиченные deliverables автоматически фиксируются на целевой ветке
  выбранной копии до перехода;
- primary и соседние рабочие копии не читаются как fallback и не изменяются.

Lane-only проверка загрязнения `kitty-specs` не применяется к явному
`single_branch`: план, статус и реализация законно находятся на одной ветке.
Проверки здоровья Git, чистоты, актуальности, implementation commit, подзадач и
pre-review gate сохранены.

## Проверки

- `tests/integration/test_owned_checkout_move_task.py`: **31 passed**;
- связанные subtask/readiness seam-тесты: **74 passed**;
- consolidated compatibility guard: **351 passed**;
- `ruff` по изменённым модулям и тестам: успешно;
- `mypy --strict` по пяти изменённым source-модулям: семь известных базовых
  сообщений, новых сообщений нет;
- `git diff --check`: успешно;
- hashes `codemap.json` и `codemap.html` совпадают с `codemap.lock`.

T010 завершена. Поддержка входа в ревью, одобрения, мотивированного возврата,
review evidence и компенсации остаётся в T011-T013. Активная синхронизация,
`done`, force/skip и публикация не разрешены этим результатом.
