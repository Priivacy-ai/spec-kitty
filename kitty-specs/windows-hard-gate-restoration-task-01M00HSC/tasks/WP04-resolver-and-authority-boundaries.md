---
work_package_id: WP04
title: Resolver-first boundary и authority allowlist closure
dependencies:
- WP03
requirement_refs:
- FR-004
- FR-005
- FR-007
- FR-011
- NFR-004
planning_base_branch: codex/setup-plan-hard-gates
merge_target_branch: codex/setup-plan-hard-gates
branch_strategy: Planning artifacts for this mission were generated on codex/setup-plan-hard-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/setup-plan-hard-gates unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
phase: Фаза 4 — resolver-first boundary и authority evidence
history:
- at: '2026-08-16T03:33:31Z'
  actor: codex
  action: Follow-up создан после полного architecture gate WP03; четыре residual-класса отделены от WP03.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/coordination/status_transition.py
- tests/architectural/test_no_write_side_rederivation.py
- tests/architectural/test_resolution_authority_gates.py
- tests/architectural/resolution_gate_allowlist.yaml
role: implementer
tags:
- architecture
- resolver
- authority
tracker_refs: []
---

# Work Package Prompt: WP04 — Resolver-first boundary и authority allowlist closure

## ⚡ Do This First: Load Agent Profile

Сначала загрузи профиль `python-pedro` через `/ad-hoc-profile-load`, затем прочитай этот prompt, mission `spec.md`/`plan.md`/`tasks.md`, WP03 review-cycle-1 и charter. Работай только в выданном lane-worktree.

## Цель

Устранить два подтверждённых архитектурных класса после WP03: повторный вывод mission anchor через `parent.parent` и stale authority token. Нельзя добавлять blanket allowlist, расширять wildcard-исключения или подменять production resolver тестовым сканером.

## Контекст и границы

- WP03 уже исправил Windows path/hash/node-id seams, но полный architecture gate остался красным.
- `status_transition._identity_for_request()` должен получать anchor через существующий canonical resolver/placement seam. Сохранить fail-loud семантику для ambiguity/conflict и не менять SaaS/auth precedence.
- `RealCoordCommitRouter.feature_write_dir` — legitimate coord-owned write surface; обновлять только exact live token, с rationale и negative/mutation evidence.
- Тестовые файлы перечислены явно, хотя часть их исторически принадлежала approved WP01; это последовательный follow-up, а не параллельное владение. В handoff и move-task note укажи эту координацию.

## Подзадачи

- [ ] T021 В RED воспроизвести raw root-walk и stale-token failures через production/static oracle; добавить положительные контроли.
- [ ] T022 Перевести `status_transition` на canonical resolver-first путь, сохранив managed-legacy fallback только при доказанном `MissionNotFound` и не скрывая другие ошибки.
- [ ] T023 Синхронизировать authority allowlist с фактическим live call-site, зафиксировать rationale и проверить отсутствие stale/лишних записей.
- [ ] T024 Убить mutation/negative cases для root-walk и allowlist token, выполнить targeted Ruff/strict mypy/py_compile/diff-check и передать exact evidence.

## Стратегия реализации

1. Снять независимый RED на базовом SHA до production-правки; не использовать только строковую проверку, которая переживает удаление фикса.
2. Найти canonical helper в `surface_resolver`/mission resolution и передать уже разрешённый anchor через существующий operation context.
3. Проверить legacy fallback на linked-worktree и ordinary-checkout сценариях; не менять путь ошибок для unrelated checkout.
4. Исправить только live allowlist token и добавить test, который падает при возврате старой аннотации или при удалении записи.
5. Запустить targeted packet, mutation tests и статические gates. Полный architecture gate выполняет WP06 после обоих follow-up пакетов.

## Проверки

- RED: raw root-walk fail + stale-token fail + положительные controls.
- GREEN: resolver-first linked-worktree lifecycle и authority census.
- Mutations: вернуть `parent.parent`; удалить/испортить allowlist token; оба должны быть пойманы.
- `pytest` targeted, Ruff diff-scoped, `mypy --strict` для production-модуля, `py_compile`, `git diff --check`.

## Definition of Done

- Нет нового функционального raw root-walk в production path.
- Все authority entries имеют живой exact match; stale entries и broad exceptions отсутствуют.
- Тесты вызывают production path, а не только synthetic source parser.
- Lane clean, commit SHA и evidence записаны в history; WP можно передать в review.

## Риски и reviewer guidance

- Не удалять legacy fallback без linked-worktree regression test.
- Не считать изменение тестового token косметикой: оно должно быть привязано к live source и mutation oracle.
- Любой новый boundary/edge требует синхронизации codemap в том же commit или явного rationale, почему dependency graph не изменился.
