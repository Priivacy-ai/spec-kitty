# Исследование: ручной внешний ревьюер спецификаций

## Проверенные факты

- `spec-kitty review` уже занят post-merge mission review и зарегистрирован как одиночная top-level команда.
- `ProfileInvocationExecutor` документирован как синхронная governance primitive и прямо не выполняет LLM call.
- Reviewer profile Renata уже охватывает спецификации и дизайн, поэтому рубрика может ссылаться на существующую reviewer doctrine, но transport остаётся отдельным.
- В исторических миссиях есть append-only `reviews/*.findings.yaml` со схемой `review-findings/v1`.
- `mission_runtime.artifacts` не классифицирует каталог `reviews/`; неизвестный nested path не получает canonical partition. Directory-level mapping захватил бы все legacy review artifacts, поэтому нужен filename-anchored pattern только для новых `spec-review-*.yaml`.
- `docs/codemap/` отсутствует в текущем repository snapshot.

## Рассмотренные варианты

### Расширить `spec-kitty review` subcommand-ами

Отклонено: текущий `review` — leaf command с совместимыми flags. Превращение в Typer group изменит UX и может сломать automation.

### Научить `ProfileInvocationExecutor` вызывать OpenCode

Отклонено: разрушает явную governance/transport границу и меняет семантику всех profile invocations.

### Писать файл напрямую в существующий `reviews/`

Отклонено: путь исторически используется, но не принадлежит canonical artifact classifier. В coordination topology это создаёт неявную placement политику.

### Добавить provider-neutral `spec-review` и `SPEC_REVIEW`

Выбрано: минимально меняет существующие команды, локализует внешний риск и оставляет модель заменяемой. Новый filename-anchored artifact kind не мигрирует существующий review trail автоматически.

## Privacy и trust boundary

Внешний provider получает untrusted/user-authored content. Результат модели также untrusted: отдельный `review-response/v1` валидируется по размеру, schema, line ranges и exact-input spans; только host строит trusted `spec-review-run/v1`. Raw stdout/stderr не покидают bounded in-memory adapter. OpenCode владеет auth и network transport; Spec Kitty передаёт prompt через stdin и не читает credential storage.

## Нерешённые внешние свойства

Доступность, цена, лимиты, владелец и data-retention Ox Alpha могут измениться. Реализация должна показывать model ID и не строить security claim на маркетинговой странице провайдера.
