# План реализации: платный opt-in ревьюер GLM 5.3

**Ветка**: `codex/glm53-paid-spec-reviewer` | **Дата**: 2026-08-29 | **Спецификация**: [spec.md](./spec.md)  
**Целевая аудитория**: разработчик Spec Kitty и reviewer, проверяющий денежный gate

## Резюме

Расширить существующий provider-neutral `spec-review` ровно одним платным профилем: `openrouter/z-ai/glm-5.3`. Бесплатная ветка остаётся прежней. Для платного профиля CLI требует канонический `--max-cost-usd`, связывает его с disclosure digest, а runner выдаёт permit только после проверки единственной точной записи OpenCode model metadata и консервативной верхней оценки стоимости. Неполная metadata, cap ниже оценки, другой платный маршрут или превышение prompt byte-bound завершаются до создания OpenCode session.

## Технический контекст

**Язык**: Python 3.11+  
**Основные зависимости**: Typer, стандартные `decimal`/`json`/`subprocess`, существующий OpenCode loopback adapter  
**Хранение**: append-only YAML `reviews/spec-review-*.yaml`; credentials не хранятся  
**Тестирование**: pytest unit + CLI + integration, ATDD red-first, без сети/model call  
**Платформы**: Windows, Linux, macOS  
**Ограничения**: один exact paid route; без fallback/retry; `0 < cap <= 5`; decimal round-up до 6 знаков; loopback transport остаётся неизменным  
**Масштаб**: один CLI leaf и bounded context `src/specify_cli/spec_review`

## Проверка charter

- **Единый источник**: pricing/cost authorization остаётся только в `runner.py`; CLI лишь валидирует и передаёт policy.
- **ATDD-first**: сначала отдельный failing commit с observable CLI/runner/storage expectations, затем implementation commit.
- **Архитектурная граница**: flow остаётся `CLI → service → runner → parser/storage`; credentials и provider response не выходят из transport boundary.
- **Терминология**: пользовательский объект — Mission; новый флаг не вводит legacy `feature`.
- **Кроссплатформенность**: только стандартная библиотека, без shell и без provider-specific executable.
- **Scope reconciliation**: меняются только файлы spec-review bounded context, его schema/tests и операторский guide; соседние модули не рефакторятся.
- **Результат проверки**: PASS, исключений charter нет.

## Архитектурные решения

1. **Предел входит в consent manifest.** `DisclosureManifest` хранит каноническую decimal-строку `max_cost_usd | null`; digest меняется вместе с ней.
2. **Один платный allowlist-route.** `PAID_GLM53_ROUTE = "openrouter/z-ai/glm-5.3"`; cap не разрешает произвольные платные модели.
3. **Цена проверяется до prompt.** Preflight manifest даёт безопасную верхнюю границу входных байт: `6 × total_payload_bytes + fixed JSON envelope`. Множитель покрывает максимальное JSON-экранирование UTF-8 входа. После построения prompt runner повторно проверяет фактическую длину против permit.
4. **Денежная оценка fail-closed.** Из exact model document принимаются только конечные неотрицательные decimal prices и положительный целочисленный `limit.output`. Неизвестные/дублированные поля либо route отказываются.
5. **Консервативная формула.** Максимум входных токенов не больше UTF-8 bytes. Input/cache leaves суммируются; output price умножается на advertised output limit. Итог делится на 1M и округляется вверх до `0.000001 USD`.
6. **Permit — runtime teeth.** Permit связывает issuer, route, byte-bound, cap и upper estimate. Несоответствие либо фактический prompt больше bound даёт отказ до session creation.
7. **Audit trail.** Host-owned artifact получает `max_cost_usd` и `estimated_max_cost_usd`; оба `null` для бесплатного режима. Contract schema обновляется совместно.
8. **Ограничение честности.** Это верхняя оценка по локальным advertised metadata, а не provider-side reservation. OpenCode HTTP message contract не предоставляет `maxTokens`; при metadata drift требуется новый preview/consent.

## Поток данных

```text
CLI validates route + canonical cap
  → disclosure binds route + cap + input byte-bound
  → user confirms digest
  → pricing probe reads exact cached OpenCode metadata
  → quote computes conservative upper estimate
  → permit only when estimate <= cap
  → spec is rechecked, prompt is built
  → runner checks prompt bytes <= permit bound
  → one loopback session call
  → host stores findings plus cap/estimate provenance
```

## Структура изменений

```text
src/specify_cli/
├── cli/commands/spec_review.py          # --max-cost-usd validation and rendering
└── spec_review/
    ├── models.py                        # consent + persisted cost provenance
    ├── preflight.py                     # cap-bound manifest
    ├── runner.py                        # exact quote, estimate and permit gate
    ├── service.py                       # ordering and provenance handoff
    └── storage.py                       # YAML fields

tests/
├── integration/test_spec_review_integration.py
└── specify_cli/spec_review/
    ├── test_cli_preview.py
    ├── test_models.py
    ├── test_preflight.py
    ├── test_runner.py
    ├── test_service.py
    └── test_storage.py

docs/guides/spec-review.md
kitty-specs/glm53-paid-spec-reviewer-01M16CYX/contracts/
```

## Карта implementation concerns

### IC-01 — Consent и денежная модель

- **Назначение**: канонизировать cap, связать его с digest и задать проверяемую формулу upper estimate.
- **Требования**: FR-002–FR-006, NFR-002–NFR-003.
- **Поверхности**: `models.py`, `preflight.py`, `runner.py`, contract schema.
- **Зависимости**: нет.
- **Риски**: float-округление, неполная cost-map, ложное обещание provider-side cap.

### IC-02 — Оркестрация и обратная совместимость

- **Назначение**: провести cost policy через CLI/service/storage, не изменив бесплатный flow.
- **Требования**: FR-001, FR-005–FR-008, NFR-001, NFR-004.
- **Поверхности**: CLI, service, storage, operator guide, focused tests.
- **Зависимости**: IC-01.
- **Риски**: prompt/session может стартовать до полного gate; cap может не попасть в audit artifact.

## Проверки

1. Failing-first:
   - `pytest tests/specify_cli/spec_review/test_cli_preview.py tests/specify_cli/spec_review/test_runner.py tests/specify_cli/spec_review/test_storage.py -q`
2. Focused green:
   - `pytest tests/specify_cli/spec_review tests/integration/test_spec_review_integration.py tests/mission_runtime/test_spec_review_artifact_placement.py -q`
3. Quality:
   - `ruff check src/specify_cli/spec_review src/specify_cli/cli/commands/spec_review.py tests/specify_cli/spec_review tests/integration/test_spec_review_integration.py`
   - `mypy --strict src/specify_cli/spec_review src/specify_cli/cli/commands/spec_review.py`
4. Compatibility:
   - существующие free-route tests без новых аргументов;
   - `python docs/codemap/codemap.lock`;
   - `git diff --check`.

## Rollout и gates

- Реализация и тесты полностью offline.
- Платный smoke, изменение OpenRouter account/Auto Router и DSH исключены.
- После реализации отдельное разрешение пользователя необходимо для любого фактического вызова GLM 5.3.

