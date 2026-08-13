# Внутренний контракт Mission operation context

## Вход

- исходный project root;
- `cwd`;
- Mission selector, если команда его принимает;
- признак explicit root;
- существующий Mission resolver/placement API.

## Выход

- единый `MissionOperationContext` с `repository_root`, `mission_anchor_root` и immutable Mission identity;
- kind-aware placement API, получающий оба корня и возвращающий конкретный artifact dir/commit target.

## Приоритет

`explicit root` → `managed topology` → `caller-owned Mission checkout` → `repository-root fallback`.

## Ошибки

- Mission отсутствует на всех допустимых поверхностях;
- selector неоднозначен внутри одной поверхности;
- candidate относится к другому Git common directory;
- candidate surfaces содержат конфликтующие immutable identity.

Все ошибки возникают до записи. CLI отображает стабильный code и безопасные пути; Python boundary использует типизированные исключения.

## Dual-root placement

- Git refs, worktree registry, coordination/lane topology вычисляются только от `repository_root`.
- PRIMARY metadata/planning artifacts вычисляются от `mission_anchor_root`.
- STATUS/coord artifacts продолжают следовать существующей stored topology.
- Ни один lifecycle consumer после получения context не выполняет повторный root lookup.

## Совместимость

- Не меняет публичную грамматику Mission selector.
- Не меняет artifact partition и coordination/lane placement.
- Не меняет `locate_project_root()`/`get_main_repo_root()` для прочих команд.
- Не требует миграции существующих Mission.
