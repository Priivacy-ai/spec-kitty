# Модель данных

## CheckoutCandidate

- `root: Path` — нормализованный checkout root.
- `kind` — `EXPLICIT`, `MANAGED`, `CALLER_OWNED` или `REPOSITORY_ROOT`.
- `git_common_dir: Path` — identity Git-репозитория.
- `mission` — разрешённый `ResolvedMission` либо `None`.

Инварианты:

- candidate не участвует в выборе, если его Git common directory не совпадает с project identity;
- managed candidate не переклассифицируется в caller-owned;
- explicit candidate не дополняется неявными кандидатами.

## MissionOperationContext

- `project_root: Path` — repository-root checkout для Git topology операций.
- `operation_root: Path` — checkout, где находится primary Mission surface данного вызова.
- `mission_id: str`.
- `mission_slug: str`.
- `feature_dir: Path`.
- `surface_kind` — происхождение выбранного checkout.

Инварианты:

- `feature_dir` находится внутри `operation_root/kitty-specs`;
- все lifecycle-команды одного состояния возвращают одну identity;
- выбор контекста не пишет на диск.

## MissionSurfaceConflict

- стабильный error code;
- selector;
- безопасный список candidate roots и соответствующих `mission_id`/slug;
- отсутствие fallback и файловых изменений.

Конфликт существует только при несовпадающей immutable identity. Две поверхности с одной identity разрешаются детерминированно.
