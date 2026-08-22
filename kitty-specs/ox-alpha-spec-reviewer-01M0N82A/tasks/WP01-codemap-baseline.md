---
work_package_id: WP01
title: Code map и архитектурный baseline
dependencies: []
requirement_refs:
- C-002
- NFR-005
- NFR-008
planning_base_branch: codex/ox-alpha-spec-reviewer
merge_target_branch: codex/ox-alpha-spec-reviewer
branch_strategy: Planning artifacts for this mission were generated on codex/ox-alpha-spec-reviewer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/ox-alpha-spec-reviewer unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 0 - Architecture baseline
history:
- at: '2026-08-22T17:51:11Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
agent: codex
authoritative_surface: docs/codemap/
create_intent:
- docs/codemap/codemap.json
- docs/codemap/codemap.html
- docs/codemap/codemap.lock
execution_mode: code_change
model: ''
owned_files:
- docs/codemap/codemap.json
- docs/codemap/codemap.html
- docs/codemap/codemap.lock
role: architect
tags: []
task_type: plan
tracker_refs: []
---

# Work Package Prompt: WP01 – Code map и архитектурный baseline

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `architect-alphonso`
- **Role**: `architect`
- **Agent/tool**: `codex`

If the profile loader is unavailable, run `spec-kitty agent profile show architect-alphonso` and apply the returned doctrine.

---

## ⚠️ IMPORTANT: Review Feedback

Перед реализацией проверь `review_ref` в status event log. Все findings должны быть закрыты или явно переданы reviewer.

## Review Feedback

На момент генерации feedback отсутствует.

## Objectives & Success Criteria

- Создать `docs/codemap/codemap.json`, `codemap.html`, `codemap.lock` до первой product-code правки.
- Ответить для каждого будущего модуля: кто вызывает, что он затрагивает, какие тесты покрывают.
- Зафиксировать load-bearing границы: `review` остаётся leaf command; `ProfileInvocationExecutor` не вызывает LLM; placement принадлежит `mission_runtime`.
- Обеспечить воспроизводимость: lock содержит HEAD, список source inputs, их digests, timestamp и verification command.
- Не менять product behavior, зависимости или CLI.

## Context & Constraints

Обязательные источники:

- `.kittify/charter/charter.md`
- `kitty-specs/ox-alpha-spec-reviewer-01M0N82A/spec.md`
- `kitty-specs/ox-alpha-spec-reviewer-01M0N82A/plan.md`
- `src/specify_cli/cli/commands/__init__.py`
- `src/specify_cli/cli/commands/review/__init__.py`
- `src/specify_cli/invocation/executor.py`
- `src/mission_runtime/artifacts.py`
- `src/mission_runtime/resolution.py`

В repo нет готового `docs/codemap/`. Не добавляй generator code за пределами owned files. Если формат нельзя сделать воспроизводимым без нового script, остановись и предложи material replan.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `codex/ox-alpha-spec-reviewer`; completed changes merge into the same task branch.
- **Planning base branch**: `codex/ox-alpha-spec-reviewer`
- **Merge target branch**: `codex/ox-alpha-spec-reviewer`
- Runtime later allocates worktrees by `lanes.json`; primary checkout не использовать для записи.

## Subtasks & Detailed Guidance

### T001 — Инвентаризировать вызовы и границы

- Найди root command registration для `review`, `dispatch`, `safe-commit`, `spec-commit`.
- Проследи `review_mission` до mission resolution и report writer.
- Проследи `ProfileInvocationExecutor.invoke()` и зафиксируй explicit no-LLM contract.
- Проследи `MissionArtifactKind` → classifier → placement seam → filesystem surface.
- Найди существующие `kitty-specs/*/reviews/*` patterns и отдели historical convention от runtime authority.
- Запиши edges с точными symbol/path, не с предположениями.

### T002 — Определить формат и source authority

- `codemap.json`: machine-readable nodes, edges, test coverage, source digests.
- `codemap.html`: статическое представление того же graph без внешних assets.
- `codemap.lock`: schema version, git HEAD, generator identity, source list/digests, JSON/HTML digests.
- Выбери deterministic ordering и normalized POSIX paths.
- Не включай credentials, env, user-global paths или contents вне repo.

### T003 — Сгенерировать три артефакта

- Создай каталог только внутри `docs/codemap/`.
- Включи узлы для будущих `spec_review` modules как planned, явно помеченные `planned`, а не `present`.
- Для present nodes укажи inbound callers, outbound effects и тестовые файлы/пробелы.
- HTML должен визуально отличать present от planned и показывать legend.
- JSON и HTML должны описывать один graph; lock связывает их digest.

### T004 — Проверить baseline

- Повтори source scan и сравни с map.
- Проверь, что не пропущены fast-path/doctor registration и topology resolver.
- Проверь exact HEAD и чистоту owned-files diff.
- Запусти `git diff --check`.
- Документируй verification command в lock; повторный запуск не должен менять файлы при неизменном HEAD.

## Test Strategy

- JSON должен parse стандартным Python `json`.
- HTML содержит все node IDs из JSON и открывается без network assets.
- SHA-256 в lock совпадает с файлами.
- Path normalization тестируется хотя бы на Windows separator input.
- Manual architecture check подтверждает три обязательных вопроса для каждого planned module.

## Risks & Mitigations

- **Косметическая карта** → edges и coverage обязательны, lock связывает source.
- **Ложный present node** → planned nodes имеют отдельный status.
- **Drift в том же commit** → WP06 повторно проверяет map после реализации.
- **Расширение scope** → owned surface только `docs/codemap/**`.

## Review Guidance

Reviewer проверяет:

- существующие boundaries представлены точно;
- planned graph соответствует `plan.md`;
- каждый planned module имеет callers/effects/tests;
- JSON/HTML/lock согласованы;
- product files не изменены.

## Definition of Done

- [ ] Все три файла существуют в `docs/codemap/`.
- [ ] `codemap.json` parseable и использует versioned top-level schema.
- [ ] Все paths repo-relative, normalized и не содержат home/worktree prefix.
- [ ] Каждый present node имеет source path и хотя бы caller/effect/coverage classification.
- [ ] Каждый planned node помечен как planned и ссылается на mission requirement/concern.
- [ ] `review_mission`, root registration, invocation executor и placement resolver отображены.
- [ ] Отсутствующее test coverage отмечено gap, а не выдуманным edge.
- [ ] HTML не содержит CDN/remote script/style dependencies.
- [ ] Lock содержит exact HEAD и digest source inputs.
- [ ] Lock digests JSON/HTML совпадают.
- [ ] Повторная verification команда завершается без diff.
- [ ] `git diff --check` проходит.
- [ ] Diff ограничен owned files.

## Forbidden Changes

- Не добавлять Python/PowerShell generator за пределами `docs/codemap/`.
- Не менять `pyproject.toml`, lockfiles, CI или dependencies.
- Не создавать product modules заранее.
- Не помечать speculative edge как существующий.
- Не читать user-global config, credentials или auth metadata.
- Не переписывать unrelated docs/codemap другого проекта.
- Не коммитить абсолютный путь worktree.

## Verification Evidence

В Activity Log/review handoff укажи:

1. HEAD SHA, на котором построена карта.
2. Количество present/planned nodes и edges.
3. Список source files, покрытых digest.
4. Команду JSON parse.
5. Команду digest verification.
6. Результат HTML offline inspection.
7. Ответы на три обязательных архитектурных вопроса для `spec_review`.
8. Подтверждение отсутствия product diff.

Review evidence не должен содержать полные file contents или noisy logs; достаточно command, exit code и counts.

## Rejection Conditions

Reviewer отклоняет WP, если карта не воспроизводима, planned/present смешаны, отсутствует хотя бы один из трёх обязательных ответов, lock не проверяет digests, HTML зависит от сети или product diff выходит за owned files. Косметически красивый graph без caller/effect/test edges считается незавершённым.

При rejection исправляй authority/data, а не только отображение.

## Activity Log

- 2026-08-22T17:51:11Z – system – Prompt created.

### Updating Status

Status меняется только через `spec-kitty agent tasks move-task WP01 --to <status>`.
