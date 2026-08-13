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

- `repository_root: Path` — repository-root checkout для Git и topology операций.
- `mission_anchor_root: Path` — checkout, где находится PRIMARY Mission surface данного вызова.
- `mission_id: str`.
- `mission_slug: str`.
- `checkout_kind` — происхождение выбранного Mission anchor.

Инварианты:

- PRIMARY artifact dirs находятся внутри `mission_anchor_root/kitty-specs`;
- STATUS artifact dirs вычисляются существующим placement seam и могут отличаться от PRIMARY;
- все lifecycle-команды одного состояния возвращают одну identity;
- выбор контекста не пишет на диск.

## MissionSurfaceConflict

- стабильный error code;
- selector;
- безопасный список candidate roots и соответствующих `mission_id`/slug;
- отсутствие fallback и файловых изменений.

Конфликт существует только при несовпадающей immutable identity. Две поверхности с одной identity разрешаются детерминированно.
