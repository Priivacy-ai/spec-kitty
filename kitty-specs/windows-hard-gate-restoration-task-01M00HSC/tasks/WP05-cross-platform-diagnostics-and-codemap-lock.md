---
work_package_id: WP05
title: Cross-platform diagnostics и deterministic code-map lock
dependencies:
- WP03
requirement_refs:
- FR-003
- FR-007
- FR-008
- FR-011
- NFR-002
- NFR-003
planning_base_branch: codex/setup-plan-hard-gates
merge_target_branch: codex/setup-plan-hard-gates
branch_strategy: Planning artifacts for this mission were generated on codex/setup-plan-hard-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/setup-plan-hard-gates unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
phase: Фаза 4 — cross-platform diagnostics и code-map integrity
history:
- at: '2026-08-16T03:33:31Z'
  actor: codex
  action: Follow-up создан после полного architecture gate WP03; diagnostic path и lock hash вынесены отдельно от resolver boundary.
agent_profile: reviewer-renata
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_topology_resolution_boundary.py
- docs/codemap/codemap.lock
role: reviewer
tags:
- windows
- diagnostics
- codemap
tracker_refs: []
---

# Work Package Prompt: WP05 — Cross-platform diagnostics и deterministic code-map lock

## ⚡ Do This First: Load Agent Profile

Сначала загрузи профиль `python-pedro` через `/ad-hoc-profile-load`, затем прочитай этот prompt, mission artifacts и WP03 review-cycle-1. Работай только в выданном lane-worktree.

## Цель

Закрыть два независимых Windows residual-класса без ослабления архитектурных проверок: POSIX-стабильные диагностические ключи и детерминированная проверка SHA-256 для code-map lock при CRLF checkout.

Диагностический helper находится в approved WP04-owned тестовом файле;
WP05 может внести туда только последовательное минимальное исправление с
coordination note, но не заявляет этот файл как параллельную ownership.

## Подзадачи

- [ ] T025 Зафиксировать RED, в котором Windows-разделитель ломает diagnostic path, и положительный контроль для POSIX key.
- [ ] T026 Нормализовать только представление repo-relative path в `_checkout_grammar_offenders`; не менять actual filesystem semantics и не расширять allowlist.
- [ ] T027 Сделать codemap lock oracle каноничным по LF-нормализованным bytes, проверить JSON/HTML parity и обновить только фактические fingerprints.
- [ ] T028 Убить mutations raw-byte hash/обратного slash и выполнить targeted Ruff/py_compile/diff-check плюс независимый lock/parity oracle.

## Контекст

- Full architecture gate выявил 2 diagnostic failures из-за `Path.relative_to()` без `.as_posix()` и 1 lock failure из-за сравнения raw Windows bytes с LF-based lock.
- `docs/codemap/codemap.json` и `.html` не менять семантически без доказанного boundary diff; WP05 владеет только lock, а JSON/HTML являются read-only inputs этого пакета.
- Историческое ownership approved WP01/WP02 пересекается с тестовым follow-up последовательно; coordination note обязателен.

## Проверки

- RED до GREEN с двумя положительными controls.
- Mutation: удалить `.as_posix()`; вернуть raw-byte hash; каждый дефект должен быть пойман.
- Проверить exact SHA-256 на committed LF bytes, JSON↔HTML parity и отсутствие незаявленного code-map drift.
- Запустить targeted tests, Ruff diff-scoped, `py_compile`, `git diff --check`.

## Definition of Done

- Диагностические сообщения имеют одинаковые POSIX repo-relative keys на Windows/POSIX.
- Lock совпадает с каноническими LF-нормализованными представлениями и не маскирует semantic drift.
- Нет изменений frozen seed или wildcard allowlist.
- Lane clean, evidence и SHA-bound handoff подготовлены для WP06.

## Activity Log

- 2026-08-16T04:26:54Z – codex – shell_pid=7652 – WP05 GREEN: RED cb3c2f02f воспроизвёл два Windows diagnostic path failure и raw-byte lock mismatch; GREEN 6cc416c42 добавил только .as_posix() для repo-relative diagnostic key, CRLF→LF normalization в lock oracle и фактические codemap fingerprints. Shared WP04 test file изменён последовательно с coordination note. Проверки: WP05-owned architecture files 39/39; mutation .as_posix() и raw-byte hash убиты; JSON↔HTML parity; Ruff, py_compile, diff-check; lock independent LF oracle; JSON/HTML semantic diff отсутствует.
