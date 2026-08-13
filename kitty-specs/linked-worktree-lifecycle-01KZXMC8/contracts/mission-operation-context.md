# Внутренний контракт Mission operation context

## Вход

- исходный project root;
- `cwd`;
- Mission selector, если команда его принимает;
- признак explicit root;
- существующий Mission resolver/placement API.

## Выход

- единый `MissionOperationContext` с repository root, operation root и immutable Mission identity.

## Приоритет

`explicit root` → `managed topology` → `caller-owned Mission checkout` → `repository-root fallback`.

## Ошибки

- Mission отсутствует на всех допустимых поверхностях;
- selector неоднозначен внутри одной поверхности;
- candidate относится к другому Git common directory;
- candidate surfaces содержат конфликтующие immutable identity.

Все ошибки возникают до записи. CLI отображает стабильный code и безопасные пути; Python boundary использует типизированные исключения.

## Совместимость

- Не меняет публичную грамматику Mission selector.
- Не меняет artifact partition и coordination/lane placement.
- Не меняет `locate_project_root()`/`get_main_repo_root()` для прочих команд.
- Не требует миграции существующих Mission.
