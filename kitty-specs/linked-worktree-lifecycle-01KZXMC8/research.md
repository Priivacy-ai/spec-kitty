# Исследование: lifecycle Mission в caller-owned worktree

## Наблюдение

`resolve_mission_creation_root()` уже сохраняет scaffold в текущем linked worktree. После создания lifecycle-команды снова вызывают `locate_project_root()`/`get_main_repo_root()`, которые намеренно возвращают repository-root checkout. Поэтому Mission существует, но resolver индексирует другой `kitty-specs`.

## Рассмотренные варианты

### Глобально изменить `locate_project_root()`

Отклонено: это сломает CWD-инвариантность существующих managed coordination/lane сценариев и изменит поведение не-Mission команд.

### Копировать Mission в primary checkout

Отклонено: нарушает изоляцию task-owned worktree, создаёт split-brain и изменяет primary.

### Исправлять каждую команду отдельно

Отклонено: появятся независимые root-решения и неизбежный drift.

### Mission-scoped operation context

Выбрано: одна boundary сначала определяет допустимую Mission surface, затем передаёт два разных корня существующим identity и placement resolver. `repository_root` отвечает за Git/topology, `mission_anchor_root` — за PRIMARY Mission artifacts. Это сохраняет Git-root семантику и делает конфликт явным.

## Решения

- Использовать существующий `FsMissionResolver` отдельно для каждого допустимого candidate root; не создавать новую грамматику selector.
- Сравнивать immutable `mission_id`; slug/path являются сопровождающими данными.
- Managed topology имеет приоритет над caller-owned эвристикой.
- Явный root считается операторским намерением и не расширяет candidate set через `cwd`.
- Path equality нормализуется через `resolve()` и platform-aware comparison; Git принадлежность — через common Git directory, а не строковый префикс пути.
- Ошибка split-brain возникает до materialization/commit/write.
- Full `mission_id` дополнительно сверяется с совпадающим slug на остальных допустимых поверхностях: обычный identity lookup сам по себе не увидит копию с другим ID.
- Единый универсальный `feature_dir` не используется для managed topology: конкретный путь определяется по `MissionArtifactKind` существующим placement seam.

## Проверяемые риски

- Полный lifecycle должен тестироваться через production CLI.
- Branch-context без selector должен использовать caller checkout только после безопасной классификации текущей Mission context.
- Производительность измеряется на заранее созданном индексе из 100 Mission; дополнительное сканирование ограничено candidate roots.
- Repo-wide census и architectural guard должны выявить lifecycle-код, который повторно вызывает `locate_project_root()`/`get_main_repo_root()` после создания operation context.
