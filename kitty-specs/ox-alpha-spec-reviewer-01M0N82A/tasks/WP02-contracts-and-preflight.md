---
work_package_id: WP02
title: Disclosure, response contracts и privacy preflight
dependencies:
- WP01
requirement_refs:
- C-005
- FR-001
- FR-002
- FR-003
- FR-004
- FR-007
- FR-011
- NFR-001
- NFR-002
- NFR-004
- NFR-006
- NFR-007
planning_base_branch: codex/ox-alpha-spec-reviewer
merge_target_branch: codex/ox-alpha-spec-reviewer
branch_strategy: Planning artifacts for this mission were generated on codex/ox-alpha-spec-reviewer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/ox-alpha-spec-reviewer unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Privacy foundation
history:
- at: '2026-08-22T17:51:11Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
agent: codex
authoritative_surface: src/specify_cli/spec_review/
create_intent:
- src/specify_cli/spec_review/models.py
- src/specify_cli/spec_review/preflight.py
- src/specify_cli/spec_review/prompt.py
- src/specify_cli/spec_review/parser.py
- tests/specify_cli/spec_review/test_models.py
- tests/specify_cli/spec_review/test_preflight.py
- tests/specify_cli/spec_review/test_prompt.py
- tests/specify_cli/spec_review/test_parser.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/spec_review/models.py
- src/specify_cli/spec_review/preflight.py
- src/specify_cli/spec_review/prompt.py
- src/specify_cli/spec_review/parser.py
- tests/specify_cli/spec_review/test_models.py
- tests/specify_cli/spec_review/test_preflight.py
- tests/specify_cli/spec_review/test_prompt.py
- tests/specify_cli/spec_review/test_parser.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Disclosure, response contracts и privacy preflight

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If unavailable, run `spec-kitty agent profile list --json` and select the Python implementer profile; do not invent a profile ID silently.

---

## ⚠️ IMPORTANT: Review Feedback

Перед работой прочитай `review_ref`; privacy findings являются implementation TODO, не рекомендациями.

## Review Feedback

План уже включает findings: manifest-wide consent, no raw streams, split response/run schemas, structured line evidence и exact-span filter.

## Objectives & Success Criteria

- Создать чистый domain layer без subprocess, storage и CLI imports.
- Consent связан с digest полного disclosure manifest, включая версионированный prompt template.
- Canonical input — только resolved `feature_dir/spec.md`, максимум 256 KiB.
- `review-response/v1` недоверенный; `spec-review-run/v1` host-owned.
- Evidence line range реально существует в spec snapshot.
- Scanner fail-closed по заявленным категориям, но UX не обещает полную анонимизацию.
- Unit/contract tests выполняют 0 сетевых вызовов.

## Context & Constraints

Прочитай:

- `spec.md`: FR-001–FR-004, FR-007, FR-011; NFR-001/002/004/006/007.
- `data-model.md` и оба YAML schema в `contracts/`.
- `plan.md`: IC-01/IC-02.
- Charter: ATDD-first, type annotations, no secrets leakage.

Нельзя читать OpenCode auth, env tokens или user-global config. Scanner не выводит matched value. Все public APIs имеют docstrings и strict typing.

## Branch Strategy

- **Planning base**: `codex/ox-alpha-spec-reviewer`
- **Merge target**: `codex/ox-alpha-spec-reviewer`
- Lane worktree определяется runtime; не писать в primary checkout.

## Subtasks & Detailed Guidance

### T005 — Red acceptance/contract tests

- Создай synthetic mission/spec fixtures только в pytest temp dirs.
- Зафиксируй manifest fields: transport, route, spec/rubric/schema/prompt-template digests и sizes, total, manifest digest.
- Для каждого поля изменяй значение между disclosure и send gate: дальнейший callback/runner spy получает 0 calls.
- Покрой отсутствие consent, интерактивную отмену как domain outcome, noninteractive refusal и несовпадающий `--confirm-digest`.
- Добавь tests для path escape, symlink spec, missing file, >256 KiB и file mutation.
- Все тесты сначала должны падать по ожидаемой причине.

### T006 — Typed models и schema validators

- Реализуй immutable/frozen types для `DisclosureManifest`, `ReviewResponse`, `SpecReviewFinding`, `SpecReviewRun`, закрытого status enum {`completed`, `refused`, `provider_error`, `timeout`, `invalid_output`, `write_failed`} и diagnostic enums.
- Model response не принимает host provenance fields.
- Host run вычисляет summary локально; сумма severity counts равна total/findings length.
- Для failure run findings пусты и diagnostic обязателен; для `completed` diagnostic `None`, а `findings: []` валиден.
- Host run копирует transport/requested route из согласованного manifest и фиксирует `actual_model: unverified`, если runner не получил проверяемые metadata провайдера.
- Finding IDs уникальны в response.
- Сверь implementation validators с YAML contracts; не дублируй divergent field lists.

### T007 — Canonical preflight и immutable buffer

- Принимай resolved repo/mission context, а не произвольный filesystem path.
- Разрешай только exact canonical `feature_dir/spec.md` после `resolve(strict=True)` и containment/reparse checks.
- До disclosure считай bytes, SHA-256 и line index.
- После consent перепроверь manifest components; затем один раз прочитай spec в immutable bytes/string buffer.
- Runner в следующем WP должен получать именно этот buffer, не перечитывать path.
- Диагностика содержит category/path metadata, но не file content.

### T008 — Versioned heuristic scanner

- Версия scanner входит в rubric/manifest metadata.
- Минимальные категории: common API/token assignments, PEM/private-key markers, credential-bearing URLs, high-confidence email/phone/person identifiers, corporate/internal markers, unusually long entropy-like strings.
- Нормализуй BOM/Unicode line endings только для анализа, не меняя payload bytes.
- Возвращай category + safe line/column, никогда matched value.
- Документируй false positives/negatives в code docstring и result warning.
- Override отсутствует.

### T009 — Prompt builder и output privacy filter

- Builder принимает immutable spec buffer, versioned rubric, response schema и versioned prompt template.
- Не добавляет repo path, plan/tasks, transcript, env, git diff или credentials.
- Manifest digests охватывают exact serialized rubric/schema/prompt template, которые пойдут в stdin.
- Parser принимает stdout только как один JSON-документ `review-response/v1`; любые дополнительные байты дают `invalid_output`.
- Privacy filter проверяет model-authored title/claim/remediation на точные normalized input spans от 32 символов.
- Evidence содержит только line numbers; цитаты/фрагменты входа schema не разрешает.
- Нарушение превращается в `invalid_output`, без сохранения offending text.

### T010 — Boundary и teeth tests

- line_start/end: positive, ordered, within snapshot line count.
- duplicate IDs, unknown fields, >100 findings, >2 MiB payload.
- пустой `findings: []` как валидный `completed` и пустой/смешанный stdout как `invalid_output`.
- wrong summary counts и failure status with findings.
- short generic text допустим; exact 32-char sentinel запрещён.
- scanner tests: real and decoy tokens, PEM, URL credentials, Unicode/BOM, long lines, false-positive examples.
- reversion-sensitive tests должны падать при удалении manifest drift check или line-range validation.

## Test Strategy

- Target: `pytest tests/specify_cli/spec_review/test_models.py tests/specify_cli/spec_review/test_preflight.py tests/specify_cli/spec_review/test_prompt.py tests/specify_cli/spec_review/test_parser.py`.
- Ruff и mypy на новых modules.
- Coverage новых ветвей ≥90% на финальном gate; в этом WP показать targeted coverage.
- Никаких monkeypatch реального network или OpenCode — runner ещё не существует.

## Risks & Mitigations

- **Scanner как ложная гарантия** → explicit heuristic warning и no override.
- **TOCTOU** → manifest-wide digest + exact immutable buffer.
- **Schema drift** → round-trip/contract tests на YAML examples.
- **Echo в findings** → evidence without excerpts + exact-span filter.
- **Overcoupling** → no CLI/subprocess/storage imports.

## Review Guidance

Reviewer обязан проверить:

- каждый manifest component защищён teeth test;
- output model не может задавать provenance;
- sentinel никогда не попадает в exception messages;
- scanner diagnostics не содержат matched values;
- line evidence проверяется относительно digest-confirmed snapshot;
- no network/process calls существуют в owned modules.

## Definition of Done

- [ ] Все public types frozen/typed и имеют docstrings.
- [ ] Manifest digest детерминирован при одинаковых bytes/route/transport/template.
- [ ] Изменение каждого manifest field аннулирует consent.
- [ ] Canonical spec path нельзя заменить symlink/reparse path.
- [ ] Spec buffer после consent не перечитывается.
- [ ] Scanner version участвует в manifest/rubric metadata.
- [ ] Scanner result не содержит matched value.
- [ ] Response rejects host provenance fields.
- [ ] Run status принимает только закрытый enum, requested route приходит из manifest, а непроверенная фактическая модель записывается как `unverified`.
- [ ] Parser принимает только единственный JSON-документ и допускает валидный `findings: []`.
- [ ] Evidence ranges существуют и ordered.
- [ ] IDs unique; limits enforce 100 findings/2 MiB.
- [ ] Summary host-computed и internally consistent.
- [ ] Failure outcome не содержит model-authored fields.
- [ ] Sentinel/span privacy tests зелёные.
- [ ] Targeted Ruff/mypy/pytest зелёные.

## Forbidden Changes

- Не добавлять runner, subprocess или CLI imports.
- Не сохранять consent между invocations.
- Не заявлять scanner как complete anonymizer.
- Не возвращать matched secret/PII в diagnostics.
- Не разрешать arbitrary input file option.
- Не ослаблять YAML contracts ради удобства parser.
- Не писать artifact files в этом WP.

## Verification Evidence

Handoff содержит test matrix с количеством cases для manifest drift, path/size, scanner categories, schema failures и sentinel checks; укажи команды/exit codes и coverage новых ветвей без raw fixtures.

## Activity Log

- 2026-08-22T17:51:11Z – system – Prompt created.

### Updating Status

`spec-kitty agent tasks move-task WP02 --to <status>`.
