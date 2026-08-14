# Исследование: порядок setup-plan preflight

## Решение 1 — сохранить preflight текущего checkout до Mission resolution

- **Решение**: после существующих hosted-auth и SaaS boundary gates, но до Mission resolver получить checkout текущей команды через same-repository Git identity helper; затем вызвать существующий `_enforce_git_preflight` один раз.
- **Почему**: `locate_project_root()` специально возвращает repository-root checkout даже из linked worktree, а текущий код проверяет `mission_anchor_root`. Значит простая перестановка на `located_root` незаметно изменит проверяемый checkout.
- **Альтернативы**:
  - preflight на `located_root` до resolver — отклонено из-за caller-owned worktree;
  - два preflight до и после resolver — отклонено из-за лишнего Git subprocess и расхождения диагностики;
  - Mission resolution до preflight — отклонено, потому что воспроизводит regression;
  - новый отдельный Mission-root resolver — запрещён single-authority контрактом.

## Решение 2 — не использовать Mission identity для checkout selection

- **Решение**: helper `resolve_same_repository_worktree_root(project_root, *, cwd=None) -> Path | None` подтверждает, что CWD — linked checkout того же Git common dir, и возвращает его root; `setup-plan` использует `located_root`, если helper вернул `None`.
- **Почему**: Git preflight требует Git checkout, но не Mission selector. Это позволяет fail-closed раньше Mission errors.
- **Альтернативы**:
  - `git rev-parse --show-toplevel` — отклонено как дополнительный subprocess до самого preflight;
  - raw `.git` parsing в `setup-plan` — отклонено как вторая authority и дублирование `core.paths`.

Обычный checkout не переводится на `MissionOperationContext`: он сохраняет существующий `_resolve_setup_plan_feature_dir`. Новый helper отвечает только за preflight checkout.

## Решение 3 — тестировать порядок, а не только итоговый код ошибки

- **Решение**: existing JSON regression дополняется spy-оракулом порядка/количества, helper-level no-subprocess guard и реальным caller-owned integration, который проверяет аргумент preflight и неизменность primary snapshot.
- **Почему**: один mock итогового payload не ловит второй preflight, preflight main checkout или Mission writes до отказа.
- **Альтернативы**: только broad suite — отклонено из-за длительности и известных Windows baseline failures.
