# План реализации: платный opt-in ревьюер GLM 5.3

**Ветка**: `codex/glm53-paid-spec-reviewer` | **Дата**: 2026-08-29 | **Спецификация**: [spec.md](./spec.md)  
**Целевая аудитория**: разработчик Spec Kitty и reviewer, проверяющий денежный gate

## Резюме

Расширить существующий provider-neutral `spec-review` ровно одним платным профилем: `openrouter/z-ai/glm-5.3`. Бесплатная ветка остаётся побайтно совместимой. Для платного профиля CLI требует канонический `--max-estimated-cost-usd`; paid preview получает metadata-only котировку и включает её целиком в disclosure digest. Runner выдаёт permit только после повторной проверки неизменности котировки и консервативной advertised-оценки полного контекста плюс полного выхода. Это локальный authorization threshold, а не ограничение фактического billing.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer, стандартные `decimal`/`json`/`subprocess`, существующий OpenCode loopback adapter  
**Хранение**: append-only YAML `reviews/spec-review-*.yaml`; credentials не хранятся  
**Тестирование**: pytest unit + CLI + integration, ATDD red-first, без сети/model call  
**Платформы**: Windows, Linux, macOS  
**Ограничения**: один exact paid route; без fallback/retry; `0 < threshold <= 5`; decimal round-up до 6 знаков; loopback transport остаётся неизменным
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

1. **Paid quote входит в consent manifest.** Платная секция содержит exact route, `max_estimated_cost_usd`, нормализованную price-map, `limit.context`, `limit.output`, `advertised_max_estimate_usd` и SHA-256 её канонического JSON. Изменение любого значения меняет digest.
2. **Free canonical form не меняется.** Бесплатный manifest и artifact вообще не содержат paid-секцию или новые `null`-поля. Старый digest и YAML закрепляются golden-тестами.
3. **Один платный allowlist-route.** `PAID_GLM53_ROUTE = "openrouter/z-ai/glm-5.3"`; threshold не разрешает произвольные платные модели.
4. **Две metadata-only проверки.** Paid preview получает котировку без prompt/session/model call. Execution повторяет probe до построения prompt и требует точного совпадения канонических metadata с digest; drift означает отказ и новый preview. Бесплатный preview сохраняет прежнее отсутствие probe.
5. **Денежная оценка fail-closed.** Из единственного exact model document принимаются только известные конечные неотрицательные decimal prices и положительные целочисленные `limit.context` и `limit.output`. Неизвестные/дублированные поля либо route отказываются.
6. **Консервативная advertised-формула.** Все input/cache price leaves применяются к полному `limit.context`, output price — к полному `limit.output`; итог округляется вверх до `0.000001 USD`. Это покрывает неизвестный до запуска system/agent framing OpenCode в рамках объявленных лимитов.
7. **Byte-bound — только integrity guard.** Preflight сохраняет верхнюю границу байт пользовательского пакета, а runner проверяет фактический prompt против permit. Эта величина не используется как billable-token estimate.
8. **Permit — runtime teeth.** Permit связывает issuer, route, quote fingerprint, byte-bound, threshold и estimate. Несоответствие даёт отказ до session creation.
9. **Audit trail без регрессии free path.** Paid artifact получает `max_estimated_cost_usd`, каноническую quote, fingerprint и `advertised_max_estimate_usd`; бесплатная сериализация остаётся прежней. Contract schema получает только optional paid-секцию.
10. **Ограничение честности.** UI и guide называют это локальным порогом advertised-оценки. OpenCode contract не предоставляет `maxTokens`, provider-side reservation отсутствует, поэтому фактический billing не ограничен и может отличаться.

## Поток данных

```text
CLI validates route + canonical threshold
  → paid preview probes exact OpenCode model metadata
  → quote validates prices + context/output limits
  → estimate uses full context + full output ceilings
  → disclosure binds route + threshold + quote + fingerprint + estimate
  → user confirms digest
  → execution re-probes and requires exact quote match
  → permit only when estimate <= threshold
  → spec is rechecked, prompt is built
  → runner checks prompt bytes only as an integrity bound
  → one loopback session call
  → host stores findings plus threshold/quote/estimate provenance
```

## Структура изменений

```text
src/specify_cli/
├── cli/commands/spec_review.py          # --max-estimated-cost-usd + warning
└── spec_review/
    ├── models.py                        # consent + persisted cost provenance
    ├── preflight.py                     # paid quote-bound manifest
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

- **Назначение**: канонизировать threshold и quote, связать их с digest и задать проверяемую advertised-формулу.
- **Требования**: FR-002–FR-006, FR-009, NFR-002–NFR-003.
- **Поверхности**: `models.py`, `preflight.py`, `runner.py`, contract schema.
- **Зависимости**: нет.
- **Риски**: float-округление, неполная cost-map, drift между preview и запуском, ложное обещание provider-side cap.

### IC-02 — Оркестрация и обратная совместимость

- **Назначение**: провести cost policy через CLI/service/storage, не изменив бесплатный flow.
- **Требования**: FR-001, FR-005–FR-009, NFR-001, NFR-004.
- **Поверхности**: CLI, service, storage, operator guide, focused tests.
- **Зависимости**: IC-01.
- **Риски**: prompt/session может стартовать до полного gate; paid provenance может изменить free digest/serialization.

## Проверки

1. Failing-first:
   - `pytest tests/specify_cli/spec_review/test_cli_preview.py tests/specify_cli/spec_review/test_runner.py tests/specify_cli/spec_review/test_storage.py -q`
2. Focused green:
   - `pytest tests/specify_cli/spec_review tests/integration/test_spec_review_integration.py tests/mission_runtime/test_spec_review_artifact_placement.py -q`
3. Quality:
   - `ruff check src/specify_cli/spec_review src/specify_cli/cli/commands/spec_review.py tests/specify_cli/spec_review tests/integration/test_spec_review_integration.py`
   - `mypy --strict src/specify_cli/spec_review src/specify_cli/cli/commands/spec_review.py`
4. Compatibility:
   - golden fixtures прежних free manifest digest и YAML artifact без новых аргументов/полей;
   - zero `create_session`/server spawn для каждого paid refusal и metadata drift;
   - `python docs/codemap/codemap.lock`;
   - `git diff --check`.

## Rollout и gates

- Реализация и тесты полностью offline.
- Платный smoke, изменение OpenRouter account/Auto Router и DSH исключены.
- После реализации отдельное разрешение пользователя необходимо для любого фактического вызова GLM 5.3; локальный threshold не является разрешением на расход.
