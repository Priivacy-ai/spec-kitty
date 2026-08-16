---
work_package_id: WP06
title: Полная local acceptance и SHA-bound handoff
dependencies:
- WP07
requirement_refs:
- FR-009
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-005
- NFR-006
planning_base_branch: codex/setup-plan-hard-gates
merge_target_branch: codex/setup-plan-hard-gates
branch_strategy: Planning artifacts for this mission were generated on codex/setup-plan-hard-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/setup-plan-hard-gates unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
phase: Фаза 5 — final local acceptance и handoff
history:
- at: '2026-08-16T03:33:31Z'
  actor: codex
  action: Follow-up acceptance package добавлен; запускается только после approved WP04 и WP05.
agent_profile: reviewer-renata
authoritative_surface: acceptance-matrix.json
create_intent:
- acceptance-matrix.json
- contracts/hard-gate-result.md
- traces/approach.md
- traces/design-decisions.md
- traces/tooling-friction.md
execution_mode: planning_artifact
model: ''
owned_files:
- acceptance-matrix.json
- contracts/hard-gate-result.md
- traces/approach.md
- traces/design-decisions.md
- traces/tooling-friction.md
role: reviewer
tags:
- acceptance
- handoff
tracker_refs: []
---

# Work Package Prompt: WP06 — Полная local acceptance и SHA-bound handoff

## ⚡ Do This First: Load Agent Profile

Сначала загрузи профиль `python-pedro` через `/ad-hoc-profile-load`, затем прочитай этот prompt, mission artifacts и approved handoffs WP04/WP05. Работай в planning checkout только для документов; code lane не изменяй.

## Цель

На exact SHA после WP04 и WP05 выполнить полный contract/architecture gate и оформить честный результат. `local_ready=true` разрешён только при нуле failures/errors и завершённой collection. Внешний E2E и release остаются отдельными состояниями.

## Подзадачи

- [ ] T029 Запустить полный `tests/contract` и `tests/architectural` на неизменённом SHA; сохранить команды, версии, counts, skips/xfails/warnings и время.
- [ ] T030 Если gate красный, классифицировать каждый failure по merge-base и вернуть его в отдельный follow-up, не расширяя текущий пакет молча.
- [ ] T031 Обновить acceptance matrix и `contracts/hard-gate-result.md`: implementation/local/E2E/release статусы, exact SHA, worktree, branch и external blockers.
- [ ] T032 Дополнить tracers, проверить clean tree и подготовить финальный handoff для `accept`; не утверждать external E2E без доступа.

## Definition of Done

- Полные gates воспроизводимы на одном immutable SHA.
- Acceptance matrix не green-wash'ит `local_ready`, E2E и release.
- Документы по-русски, ссылки на evidence и exact commands присутствуют.
- Planning checkout и product lanes clean; следующий шаг однозначен.

## Финальный пакет evidence

- Immutable integration SHA: `bcc33914d45319aacbed6e049bf8cada500b091b`.
- Contract: `305 passed, 3 skipped, 0 failed, 0 errors` за `179.41s`.
- Architecture: `2120 passed, 5 skipped, 2 xfailed, 0 failed, 0 errors,
  14 warnings` за `4140.66s`; collection завершена без ошибок.
- Integration worktree: `C:\spkhg\.worktrees\windows-hard-gate-restoration-task-01M00HSC-integration`.
- WP07 marker-only follow-up `eae4dc006` закрывает 25-site residual без подъёма
  frozen ceiling; mutation снятия marker снова красная.
- Acceptance matrix и hard-gate contract обновлены: `local_ready=true`, но
  `e2e_access=blocked`, `e2e_ready=false`, `release_ready=false`.
- Ложные red-запуски из несвязанного cwd вынесены в отдельную заметку; в
  readiness учитывается только запуск из корня integration worktree.

## Activity Log

- 2026-08-16T15:54:27Z — codex — final local acceptance recorded on bcc33914d; full contract and architecture suites green; external E2E remains blocked.
