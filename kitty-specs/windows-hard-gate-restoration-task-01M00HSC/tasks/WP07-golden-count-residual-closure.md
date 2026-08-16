---
work_package_id: WP07
title: Закрытие cardinality residual после полного architecture gate
dependencies:
- WP04
- WP05
requirement_refs:
- FR-011
- NFR-004
- NFR-006
planning_base_branch: codex/setup-plan-hard-gates
merge_target_branch: codex/setup-plan-hard-gates
branch_strategy: Planning artifacts for this mission were generated on codex/setup-plan-hard-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/setup-plan-hard-gates unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
phase: Фаза 5a — follow-up residual closure
history:
- at: '2026-08-16T05:44:20Z'
  actor: codex
  action: Новый residual полного architecture gate вынесен в отдельный follow-up до повторного WP06.
agent_profile: reviewer-renata
authoritative_surface: tests/architectural/test_resolution_authority_gates.py
execution_mode: code_change
owned_files:
- tests/architectural/test_resolution_authority_gates.py
role: reviewer
agent: codex
model: ''
tags:
- architecture
- golden-count
- follow-up
tracker_refs: []
---

# Work Package Prompt: WP07 — Закрытие cardinality residual после полного architecture gate

## ⚡ Do This First: Load Agent Profile

Сначала загрузи профиль `python-pedro` через `/ad-hoc-profile-load`, затем
прочитай этот prompt, `spec.md`, `plan.md`, `tasks.md`, handoff WP04/WP05 и
результат полного architecture gate на SHA `6cc416c42`. Работай только в
выделенном WP07 code worktree; planning checkout и чужие worktrees не меняй.

## Цель

Закрыть единственный новый failure полного `tests/architectural` на exact SHA:
`tests/architectural/test_golden_count_ban.py::test_convert_sites_do_not_exceed_frozen_baseline`
видит 25 неэкранированных `convert`-sites при frozen ceiling 24.

Новый site появился в WP04-тесте
`test_wp04_coord_router_entry_matches_exact_live_token`: assertion
`len(target) == 1` проверяет не случайный размер коллекции, а обязательную
уникальность ровно одной authority-записи. Это легитимный cardinality contract,
который должен быть отмечен только на собственной физической строке.

## Границы и ownership

Единственный owned файл:

- `tests/architectural/test_resolution_authority_gates.py`

Последовательный follow-up разрешён после approved WP04: WP04 уже завершил
основную authority-поверхность, WP07 добавляет только один документированный
marker на его assertion. Не редактируй `test_golden_count_ban.py`, frozen
baseline, allowlist, production code, codemap или planning artifacts.

## Подзадача T033 — воспроизвести и классифицировать residual

1. Проверь immutable baseline `6cc416c42` и clean status code lane.
2. Запусти recurrence guard в полном окружении или bounded exact test с
   корневым `tests/conftest.py`:

   ```powershell
   $py = 'C:\codex-scratch\spklw-planning\.venv\Scripts\python.exe'
   & $py -m pytest tests/architectural/test_golden_count_ban.py::test_convert_sites_do_not_exceed_frozen_baseline -q
   ```

3. Независимо вызови `scan_repo()` и зафиксируй список из 25 sites. Сравни с
   merge-base/WP03: единственная новая строка —
   `test_resolution_authority_gates.py:1903`, `len(target) == 1`.
4. До GREEN сохрани RED evidence в activity/handoff; не поднимай ceiling и не
   меняй baseline.

## Подзадача T034 — узкий marker без изменения семантики

На физическую строку assertion добавь только:

```python
assert len(target) == 1, (  # golden-count: cardinality-is-contract
```

Если форматирование/line break требует иного расположения, marker должен
оставаться на той же физической строке, которую `is_escaped()` читает как
assertion. Не меняй выражение `target`, текст ошибки, `target[0] in live` или
authority allowlist. Не добавляй marker к соседним `len`-проверкам.

## Подзадача T035 — mutation-sensitive GREEN

После marker:

- targeted recurrence guard проходит и скан показывает 24 non-escaped sites;
- точечный WP04 тест проходит и сохраняет exact live-token assertion;
- Ruff для изменённого файла, `py_compile` и `git diff --check` проходят;
- временное удаление marker снова делает recurrence guard красным (ожидаемый
  mutation), после чего marker восстанавливается и рабочее дерево чистое;
- baseline JSON остаётся byte-for-byte прежним.

Mutation запускай только во временной копии/обратимым patch, не оставляй
изменение в рабочем дереве и не трогай чужие процессы.

## Подзадача T036 — handoff для повторного WP06

В activity WP07 укажи RED/GREEN, точный diff, mutation result, SHA и clean
status. После commit передай WP06 exact новый SHA для полного contract и
architecture rerun. Не объявляй `local_ready`, E2E или release readiness из
этого targeted пакета.

## Definition of Done

- Один marker добавлен только к legitimate cardinality assertion WP04.
- `tests/architectural` recurrence guard зелёный; frozen ceiling не растёт.
- Mutation marker removal даёт ожидаемый failure и после восстановления не
  оставляет diff.
- Owned diff минимален, Ruff/py_compile/diff-check зелёные, lane clean.
- WP06 получает SHA-bound handoff и повторяет оба полных gate.

## Риски и reviewer guidance

Главный риск — green-wash через увеличение baseline или слишком широкий marker.
Reviewer должен проверить exact line, unchanged baseline, independent scan
count 24 и mutation RED. Любой дополнительный изменённый файл требует
остановки и отдельного согласования.

## Branch Strategy

Planning branch: `codex/setup-plan-hard-gates`.
Merge target: `codex/setup-plan-hard-gates`.
Реализация выполняется в task-owned worktree, вычисленном через `lanes.json`;
planning checkout остаётся только для Spec Kitty metadata и не используется
для code edits.

## Activity Log

- 2026-08-16T05:59:49Z – codex – shell_pid=20156 – Review: commit eae4dc006 меняет только одну строку в approved WP04 test_resolution_authority_gates.py; RED 25-site failure воспроизведён, marker GREEN даёт 24, его снятие снова RED; baseline unchanged, targeted 2/2, Ruff, py_compile и diff-check зелёные; shared-file follow-up согласован последовательно.
