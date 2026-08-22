# Пакеты работ: ручной ревьюер спецификаций Ox Alpha

**Входы**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  
**Стратегия**: сначала code map и контракты, затем placement/runner, после них orchestration CLI и итоговая проверка.  
**Тесты**: обязательны по спецификации и charter; обычные тесты не выполняют сетевых вызовов.

## WP01 — Code map и архитектурный baseline (P0)

**Цель**: до первой product-code правки создать актуальную карту вызывающих путей, затрагиваемых модулей и тестового покрытия.  
**Независимая проверка**: три файла `docs/codemap/` согласованы по digest и отвечают на вопросы «кто вызывает / что затрагивает / какие тесты покрывают».  
**Prompt**: `tasks/WP01-codemap-baseline.md`  
**Requirement refs**: NFR-005, NFR-008, C-002.

### Included Subtasks

- [ ] T001 Инвентаризировать CLI, invocation, artifact placement и существующие review paths (WP01)
- [ ] T002 Определить воспроизводимый формат и source inputs code map (WP01)
- [ ] T003 Сгенерировать `codemap.json`, `codemap.html`, `codemap.lock` (WP01)
- [ ] T004 Проверить карту на актуальном HEAD и зафиксировать архитектурный baseline (WP01)

### Implementation Notes

Не менять product behavior. Карта должна явно показать, что `review` — существующая leaf command, а `ProfileInvocationExecutor` не вызывает LLM.

### Parallel Opportunities

Нет: это обязательный pre-code gate.

### Dependencies

Нет.

### Risks & Mitigations

Риск косметической карты без authority → lock содержит входные digests и verification command.

---

## WP02 — Disclosure, response contracts и privacy preflight (P0, MVP foundation)

**Цель**: реализовать host-owned disclosure manifest, два раздельных schema contract и fail-closed локальный preflight.  
**Независимая проверка**: fake runner не вызывается при отсутствии consent, manifest drift, path escape, size violation или sensitive marker; валидный response преобразуется в host run с проверенными line ranges и summary.  
**Prompt**: `tasks/WP02-contracts-and-preflight.md`  
**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-007, FR-011, NFR-001, NFR-002, NFR-004, NFR-006, NFR-007, C-005.

### Included Subtasks

- [ ] T005 Написать red acceptance/contract tests для consent manifest и минимального пакета (WP02)
- [ ] T006 Реализовать typed domain models и отдельные `review-response/v1` / `spec-review-run/v1` validators (WP02)
- [ ] T007 Реализовать canonical path, size и immutable-buffer preflight с повторной digest проверкой (WP02)
- [ ] T008 Реализовать версионированный heuristic sensitive-data scanner с безопасной диагностикой (WP02)
- [ ] T009 Реализовать bounded rubric/prompt builder и exact-input-span privacy filter (WP02)
- [ ] T010 Покрыть line evidence, unique IDs, summary counts и boundary cases (WP02)

### Implementation Notes

Consent связан с digest всего manifest, а не только `spec.md`. Scanner не обещает полное обезличивание. Model-authored payload не может задавать provenance.

### Parallel Opportunities

После T005 модели/parser (T006/T010) и scanner/prompt (T008/T009) могут разрабатываться последовательно внутри одного lane без файлового overlap с другими WP.

### Dependencies

Зависит от WP01.

### Risks & Mitigations

Ложная privacy-гарантия → exact UX warning, fail-closed categories и adversarial sentinel tests.

---

## WP03 — Canonical PRIMARY placement и atomic storage (P0)

**Цель**: формализовать только новые `reviews/spec-review-*.yaml` как PRIMARY planning evidence и безопасно сохранять host-built run artifacts.  
**Независимая проверка**: topology matrix разрешает реальный path/commit target через canonical seams; legacy files не переклассифицируются; concurrent/symlink tests не допускают overwrite или escape.  
**Prompt**: `tasks/WP03-placement-and-storage.md`  
**Requirement refs**: FR-008, FR-009, FR-012, NFR-001, NFR-005, NFR-008, C-004.

### Included Subtasks

- [ ] T011 Зафиксировать ADR о PRIMARY ownership, lifecycle и legacy compatibility (WP03)
- [ ] T012 Добавить filename-anchored `SPEC_REVIEW` artifact classification и partition tests (WP03)
- [ ] T013 Реализовать storage только через `resolve_artifact_surface` и placement seam (WP03)
- [ ] T014 Реализовать atomic exclusive-create, ASCII run ID и cleanup собственного temp file (WP03)
- [ ] T015 Добавить topology, concurrency, occupied-ID и symlink/reparse tests (WP03)

### Implementation Notes

Artifact kind и writer routing находятся в одном WP: нельзя независимо слить только половину boundary.

### Parallel Opportunities

После WP02 может идти параллельно с WP04; owned files не пересекаются.

### Dependencies

Зависит от WP01 и WP02.

### Risks & Mitigations

Directory classifier захватит historical trail → только filename glob до fallback. Direct `feature_dir/reviews` запрещён architecture tests.

---

## WP04 — Безопасный OpenCode transport (P0)

**Цель**: реализовать заменяемый subprocess runner с stdin-only input, bounded private streams и cleanup всего process tree.  
**Независимая проверка**: fake process contract доказывает точный argv, `shell=False`, отсутствие raw stream leakage и корректные diagnostic codes на Windows/Linux/macOS paths.  
**Prompt**: `tasks/WP04-opencode-runner.md`  
**Requirement refs**: FR-005, FR-006, FR-010, NFR-001, NFR-003, NFR-004, NFR-005, NFR-006, C-001, C-003.

### Included Subtasks

- [ ] T016 Проверить локальный help-контракт OpenCode без model/network call и зафиксировать argv decision (WP04)
- [ ] T017 Написать red runner tests для stdin, shell isolation, exit taxonomy и bounded streams (WP04)
- [ ] T018 Реализовать typed runner protocol и OpenCode adapter без credential access (WP04)
- [ ] T019 Реализовать framing/stream limits без raw stdout/stderr propagation (WP04)
- [ ] T020 Реализовать cross-platform process-tree timeout cleanup и grandchild tests (WP04)
- [ ] T021 Покрыть auth/provider/invalid UTF-8/oversized/exception diagnostics (WP04)

### Implementation Notes

Результат provider остаётся untrusted. CLI/auth storage не читается; никаких fallback models.

### Parallel Opportunities

После WP02 выполняется параллельно WP03.

### Dependencies

Зависит от WP01 и WP02.

### Risks & Mitigations

OpenCode output contract может отличаться от предположения → T016 проверяет установленный help и требует material replan при несовместимости.

---

## WP05 — Advisory service и CLI integration (P1, MVP)

**Цель**: собрать preflight, consent, runner, parser и storage в отдельную `spec-kitty spec-review`, сохранив существующий `spec-kitty review`.  
**Независимая проверка**: root help показывает обе команды; preview/complete/cancel возвращают 0, failure outcomes — 2–7; mission state и `spec.md` неизменны.  
**Prompt**: `tasks/WP05-service-and-cli.md`  
**Requirement refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, NFR-001, NFR-007, C-002, C-004.

### Included Subtasks

- [ ] T022 Написать red service/CLI acceptance tests для preview, consent, success и failures (WP05)
- [ ] T023 Реализовать advisory orchestration service и disclosure manifest UX (WP05)
- [ ] T024 Реализовать тонкую top-level `spec-review` command и stable exit mapping (WP05)
- [ ] T025 Зарегистрировать команду без eager import external-review stack (WP05)
- [ ] T026 Добавить compatibility tests существующей leaf `review` и fast paths (WP05)
- [ ] T027 Проверить non-mutation mission/spec и human summary artifact path/counts (WP05)

### Implementation Notes

Advisory означает «не меняет lifecycle», а не «всегда exit 0». Preview имеет отдельный явный флаг.

### Parallel Opportunities

Нет после старта: WP объединяет load-bearing service и CLI compatibility.

### Dependencies

Зависит от WP02, WP03 и WP04.

### Risks & Mitigations

Регистрация сломает `review` → exact help/flag/exit regression tests и lazy import check.

---

## WP06 — Документация, quality gates и opt-in smoke harness (P2)

**Цель**: завершить публичную документацию, regression/coverage gates и отделённый synthetic live smoke.  
**Независимая проверка**: docs не обещают free/ZDR/provider ownership; Ruff, mypy, tests и coverage проходят; live smoke отсутствует в обычном CI и требует отдельного consent.  
**Prompt**: `tasks/WP06-docs-and-validation.md`  
**Requirement refs**: FR-006, FR-009, FR-010, FR-012, NFR-001, NFR-003, NFR-005, NFR-006, NFR-008, C-003, C-004.

### Included Subtasks

- [ ] T028 Написать operator guide и compatibility/changelog note без provider promises (WP06)
- [ ] T029 Добавить opt-in synthetic live-smoke harness/marker без CI dependency (WP06)
- [ ] T030 Запустить targeted tests, Ruff, mypy и измерить coverage новых ветвей (WP06)
- [ ] T031 Выполнить full relevant regression suite и проверить code map drift (WP06)
- [ ] T032 Сверить фактический результат со spec/plan/tasks и подготовить review evidence (WP06)

### Implementation Notes

Фактический model call допускается только после отдельного пользовательского подтверждения и только с synthetic spec.

### Parallel Opportunities

Документационный draft может начаться после WP05 API shape; smoke и итоговые gates — только после всех implementation WP.

### Dependencies

Зависит от WP03, WP04 и WP05.

### Risks & Mitigations

Green fake tests не доказывают provider → live evidence маркируется отдельно и не является merge prerequisite при внешней недоступности.

---

## Dependency & Execution Summary

- **Последовательность**: WP01 → WP02 → (WP03 ∥ WP04) → WP05 → WP06.
- **MVP**: WP01–WP05; WP06 обязателен до PR, но не расширяет product behavior.
- **Параллельность**: только WP03 и WP04 после общего contract foundation.
- **Review rule**: artifact kind и storage routing ревьюятся как единая load-bearing граница.

## Requirements Coverage Summary

| Requirement | Covered by |
|-------------|------------|
| FR-001–FR-004 | WP02, WP05 |
| FR-005–FR-006 | WP04, WP05, WP06 |
| FR-007 | WP02, WP05 |
| FR-008 | WP03, WP05 |
| FR-009 | WP03, WP05, WP06 |
| FR-010 | WP04, WP05, WP06 |
| FR-011 | WP02, WP05 |
| FR-012 | WP03, WP05, WP06 |
| NFR-001–NFR-008 | WP01–WP06 по профильным границам |
| C-001–C-005 | WP01–WP06 по профильным границам |

## Subtask Index (Reference)

| ID | Кратко | WP | Parallel |
|----|--------|----|----------|
| T001–T004 | Code map baseline | WP01 | Нет |
| T005–T010 | Contracts и preflight | WP02 | Частично |
| T011–T015 | Placement и storage | WP03 | С WP04 |
| T016–T021 | OpenCode runner | WP04 | С WP03 |
| T022–T027 | Service и CLI | WP05 | Нет |
| T028–T032 | Docs и validation | WP06 | Частично |
