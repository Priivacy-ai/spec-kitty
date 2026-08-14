# Модель выполнения setup-plan preflight

Новых persisted-сущностей нет. Модель описывает значения одного CLI-вызова.

## Значения

### LocatedProjectRoot

- Канонический repository-root checkout, возвращённый `locate_project_root()`.
- Используется для same-repository проверки, SaaS boundary и coordination topology.

### ActiveGitCheckoutRoot

- Checkout, из которого фактически вызвана команда, если он принадлежит той же Git identity; иначе `LocatedProjectRoot`.
- Используется только Git preflight.
- Не является источником Mission identity или Mission artifact placement.

### MissionOperationContext

- Разрешается только после успешного Git preflight и только для caller-owned same-repository linked-worktree пути.
- Содержит `repository_root`, `mission_anchor_root` и immutable Mission identity.
- Остаётся единственным источником Mission anchor.

### OrdinaryCheckoutFeatureResolution

- После успешного Git preflight обычный checkout сохраняет действующий `_resolve_setup_plan_feature_dir`.
- Это исключает лишний рефакторинг всех setup-plan путей на `MissionOperationContext`.

## Переходы

```text
hosted-auth gate
  → locate project
  → SaaS boundary gate
  → resolve active Git checkout
  → Git preflight
      → failed: emit GIT_PREFLIGHT_FAILED, stop, zero Mission writes
      → passed caller-owned: resolve MissionOperationContext
      → passed ordinary: use existing feature-dir resolver
          → Mission error: emit Mission-context error
          → success: continue setup-plan lifecycle
```

## Инварианты

- `GitPreflightCallCount == 1`.
- Failed preflight означает `MissionResolverCallCount == 0` и `MissionWriteCount == 0`.
- `ActiveGitCheckoutRoot` может отличаться от `LocatedProjectRoot`, но не заменяет `mission_anchor_root`.
- Unrelated CWD не может стать `ActiveGitCheckoutRoot`.
