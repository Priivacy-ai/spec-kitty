---
work_package_id: WP03
title: Windows-stable baseline closure и честная local acceptance
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-007
- FR-011
- FR-012
- NFR-002
- NFR-006
planning_base_branch: codex/setup-plan-hard-gates
merge_target_branch: codex/setup-plan-hard-gates
branch_strategy: Planning artifacts for this mission were generated on codex/setup-plan-hard-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/setup-plan-hard-gates unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
phase: Фаза 3 — Windows-stable baselines и local acceptance
history:
- at: '2026-08-15T00:00:00Z'
  actor: codex
  action: Пакет добавлен после независимой классификации residual architecture failures
agent_profile: reviewer-renata
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_doctrine_census.py
- tests/architectural/test_kernel_no_doctrine_import.py
- tests/architectural/test_glossary_pack_no_regression.py
- tests/architectural/test_golden_count_ban.py
- tests/architectural/_golden_count_baseline.json
- tests/architectural/test_mission_exit_baseline.py
- tests/review/test_pre_review_gate_engine.py
- tests/contract/test_machine_facing_canonical_fields.py
role: reviewer
tags:
- windows
- architecture
- baseline
- acceptance
task_type: implement
tracker_refs:
- '#3438'
---

# Work Package Prompt: WP03 — Windows-stable baseline closure и честная local acceptance

## Сначала загрузить профиль

Используй `/ad-hoc-profile-load` для `python-pedro`, затем полностью прочитай этот
prompt, mission `spec.md`/`plan.md`/`research.md`/`data-model.md`/`quickstart.md`,
`contracts/hard-gate-result.md`, approved WP01/WP02 handoff и charter. Работай только
в task-owned lane, возвращённой runtime.

## Почему пакет добавлен

После approved WP02 на текущем SHA были независимо проверены четыре остаточных
класса. Это не повод снижать gate: они требуют отдельного RED/GREEN:

1. `test_doctrine_census.py` и `test_kernel_no_doctrine_import.py` сравнивают
   Windows `Path`-строки с POSIX inventory keys; четыре реально owned WP05–WP07
   файла ошибочно объявляются orphan, а pre-existing kernel exemptions не
   применяются.
2. Проверка glossary seed pin сравнивает LF Git blob с CRLF checkout на Windows.
   Seed менять нельзя; канонизируется только содержимое для проверки, смешанные
   newline должны оставаться ошибкой.
3. `golden-count` baseline старше фактического merge-base (`integration=35`,
   `specify_cli=270` против ceilings 33/269), а новый contract helper содержит
   один обоснованный cardinality-only site.
4. Windows capability fallback меняет numeric id `True-9` на `True-15`, из-за чего
   committed mission-exit floor видит shrink, хотя параметр всё ещё собирается.

CLI width guard проверен официальным запуском с корневым `tests/conftest.py`:
`3 passed, 1 warning`. Его красный результат в диагностическом режиме
`--confcutdir=tests/architectural` не является production failure и не должен
порождать blanket source change.

## T014 — RED-first residual packet

До любой GREEN/production записи создать отдельный test-only RED commit. Он должен
падать на каждом из четырёх классов и иметь положительный контроль, доказывающий,
что assertion не vacuous:

- обратная замена `.as_posix()` на `str(Path)` возвращает separator failure;
- seed digest на искусственном CRLF/LF смешанном содержимом отвергается;
- удаление `golden-count` marker возвращает site в ratchet;
- удаление explicit `pytest.param(..., id="True-9")` обнаруживается node-id oracle.

В RED evidence отдельно указать, что width guard в официальном окружении зелёный.

## T015 — Path/hash seams

Минимальный GREEN:

- в doctrine census и kernel scanner относительный путь формируется через
  `.as_posix()`, а static expected keys остаются строковыми константами;
- `_seed_digest()` нормализует только CRLF→LF перед SHA-256, дополнительно
  отвергает оставшиеся bare `\r`/смешанные переводы строк;
- seed-файл `.kittify/glossaries/spec_kitty_core.yaml` не меняется;
- не добавлять `ORPHAN_REACHED_EXCEPTIONS`: текущие четыре файла уже принадлежат
  WP05–WP07, проблема только в представлении пути.

## T016 — Mission-exit node-id

Сохранить committed node-id
`tests/review/test_pre_review_gate_engine.py::test_posix_signal_targets_owned_process_group[True-9]`
явным `id="True-9"` у параметра. Capability skip должен оставаться честным: на
Windows тест собирается и помечается skip, но floor не shrink'ится; на POSIX
поведение и ожидаемый сигнал не меняются.

## T017 — Golden-count baseline

Проверить exact merge-base evidence и только затем:

- добавить `# golden-count: cardinality-is-contract` ровно к helper-проверке
  `len(helpers) == 1`, если независимый reviewer подтверждает, что это контракт
  структуры, а не список runtime-элементов;
- выполнить штатный `python -m tests.architectural.test_golden_count_ban
  --freeze-baseline`, а не редактировать JSON вручную;
- подтвердить, что baseline не уменьшается и не скрывает новый non-cardinality site.

## T018 — Mutations и targeted GREEN

Обязательные временные mutations: slash normalization, mixed newline, explicit
node-id и marker removal. Каждый mutation должен быть убит конкретным тестом,
после чего должен быть точечно восстановлен. Запустить:

- все восемь owned test modules;
- official width test без `--confcutdir`;
- Ruff, `py_compile`, `git diff --check` и exact owned-scope check.

## T019 — Full local gate

После GREEN зафиксировать candidate SHA и не менять файлы во время проверки:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\contract -q
.\.venv\Scripts\python.exe -m pytest tests\architectural -q
```

Требование: `0 failed`, `0 errors`, collection без ошибок. `--confcutdir`,
partial packet и прерванный timeout не заменяют эти два запуска. Если появляется
новый root-cause, остановить WP03 и вернуть результат на отдельный follow-up WP.

## T020 — Handoff и acceptance state

Обновить `contracts/hard-gate-result.md` и `acceptance-matrix.json` в planning
checkout: до зелёного exact architecture SHA `local_ready=false`; после него
`local_ready=true`. Зафиксировать worktree, branch, RED/GREEN SHAs, counts,
skip/xfail, mutation evidence, seed unchanged, baseline diff и clean-tree state.

## Definition of Done

- [ ] T014–T020 выполнены штатным lifecycle.
- [ ] RED commit предшествует GREEN.
- [ ] Четыре residual-класса классифицированы без blanket skip/allowlist.
- [ ] Seed не изменён; golden baseline сгенерирован штатным scanner'ом.
- [ ] Committed mission-exit node-id сохранён.
- [ ] Все mutations убиты и восстановлены.
- [ ] Full contract и architecture на exact final SHA: `0 failed`, `0 errors`.
- [ ] `local_ready` отражает фактический SHA; E2E blocker не green-wash'ится.
- [ ] Lane clean, handoff воспроизводим.

## Review guidance

Reviewer обязан независимо проверить merge-base hash seed, POSIX path keys, exact
node-id floor, scanner output до/после freeze и официальный full-suite command.
Review blocker, если baseline просто расширен без evidence, seed отредактирован,
floor сокращён, `--confcutdir` выдан за full gate или acceptance matrix заявляет
`local_ready=true` при любом architecture failure/error.


## Activity Log

- 2026-08-16T03:40:15Z – codex – shell_pid=1220 – Полный architecture gate на GREEN SHA 06026d6d0: 2107 passed, 5 skipped, 2 xfailed, 1 warning, 8 failed. WP03-локальные четыре класса зелёные; выявлены четыре новые группы: raw status_transition parent.parent anchor, Windows diagnostic path, stale authority token, CRLF-sensitive codemap lock. Зафиксировано в tasks/review-cycle-1-WP03.md; требуется follow-up WP04–WP05 и финальный WP06, local_ready=false.
