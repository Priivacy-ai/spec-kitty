---
work_package_id: WP01
title: Windows portability и collection closure
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-006
- FR-007
planning_base_branch: codex/setup-plan-hard-gates
merge_target_branch: codex/setup-plan-hard-gates
branch_strategy: Planning artifacts for this mission were generated on codex/setup-plan-hard-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/setup-plan-hard-gates unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Фаза 1 — Windows portability
agent: codex-review
shell_pid: 26716
shell_pid_created_at: '1786739803.8896844'
history:
- at: '2026-08-14T16:35:00Z'
  actor: codex
  action: Prompt подготовлен после post-plan Sol-аудита
agent_profile: python-pedro
authoritative_surface: tests/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/contract/test_machine_facing_canonical_fields.py
- tests/cli/commands/test_sync_doctor_consent_health_3030.py
- tests/integration/test_intake_size_cap.py
- tests/review/test_pre_review_gate_engine.py
- tests/specify_cli/core/test_target_branch_primitive.py
- tests/sync/test_consent_fault_vocabulary_3030.py
- tests/sync/test_consent_write_refusal_3030.py
- tests/sync/test_issue_598_hang_fixes.py
- tests/architectural/test_shared_module_object_patches.py
- tests/architectural/test_tracker_egress_guards_3108.py
- tests/architectural/test_runtime_charter_doctrine_boundary.py
- tests/architectural/test_ci_quality_path_filters.py
- tests/architectural/test_cli_console_render_width.py
- tests/architectural/test_doctrine_census.py
- tests/architectural/test_glossary_pack_no_regression.py
- tests/architectural/test_golden_count_ban.py
- tests/architectural/test_kernel_no_doctrine_import.py
- tests/architectural/test_marker_job_completeness.py
- tests/architectural/test_mission_exit_baseline.py
- tests/architectural/test_no_write_side_rederivation.py
- tests/architectural/test_pytest_marker_correctness.py
- tests/architectural/test_real_home_isolation_guard.py
- tests/architectural/test_resolution_authority_gates.py
- tests/architectural/test_session_reaper.py
- tests/architectural/_gate_coverage.py
role: implementer
tags:
- windows
- testing
- architecture-gates
task_type: implement
tracker_refs:
- '#3438'
---

# Work Package Prompt: WP01 — Windows portability и collection closure

## Сначала загрузить профиль

Используй `/ad-hoc-profile-load` для `python-pedro`, затем полностью прочитай этот prompt, `spec.md`, `plan.md`, `research.md`, `quickstart.md`, `contracts/hard-gate-result.md` и charter. Работай только в lane worktree, возвращённом runtime.

## Цель и критерии успеха

Устранить только platform/test-harness причины ложных hard-gate failures:

- contract test не открывает literal `/dev/null`;
- import/collection не вызывает отсутствующий `os.geteuid` на Windows;
- actual repo-relative paths формируются в canonical POSIX-виде;
- static expected inventories не проходят через тот же normalizer и остаются независимым oracle;
- семь перечисленных файлов собираются с `0 errors`;
- dependent coverage/shard/session-reaper gates видят полный набор;
- Linux/macOS permission branch сохраняется и имеет отдельный test oracle;
- production topology, architecture inventories WP02 и code map не меняются.

## Обязательные источники

- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/spec.md`;
- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/plan.md`;
- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/research.md`;
- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/quickstart.md`;
- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/contracts/hard-gate-result.md`;
- `.kittify/charter/charter.md`.

## Ограничения

- Не изменять `src/`, `docs/codemap/`, `surface_resolution_audit/`, `untrusted_path_audit/` и `test_topology_resolution_boundary.py`.
- Не добавлять blanket Windows skip. Допустим только узкий skip конкретного Unix permission oracle при отсутствии capability, с отдельным тестом POSIX-ветки.
- Не уменьшать count floors, expected sets или coverage groups.
- Не нормализовать expected inventory тем же production/helper path, что actual census.
- Не лечить collection errors retries или исключением файлов из universe.
- Любой out-of-map файл требует material replan до записи.
- До начала implementation создать GitHub issue по charter; если внешняя запись недоступна, остановить пакет как blocked, а не обходить правило.

## T001 — GitHub issue о pre-existing failures

Создай один issue в canonical repository и укажи:

- baseline branch/commit;
- contract result `293 passed, 3 skipped, 1 failed` и literal `/dev/null`;
- architecture result `2036 passed, 5 skipped, 2 xfailed, 28 failed, 34 errors`;
- targeted collection `AttributeError: module 'os' has no attribute 'geteuid'`;
- почему failures предшествуют этой lane;
- ссылку на эту mission без служебного transcript.

Добавь issue reference в Activity Log/runtime metadata штатной командой. Не включай credentials или локальные private paths, кроме необходимого repo-relative evidence.

## T002 — RED-first commit

До любых GREEN fixes создай отдельный test-only commit. Он обязан воспроизводить как минимум:

1. Contract null sink: существующая production test entry падает на Windows при literal `/dev/null` и ожидает platform sink.
2. EUID collection: import/collect-safe test доказывает отсутствие прямого вызова отсутствующего capability.
3. Path representation: фактический `Path` с Windows separators сравнивается со статическим POSIX expected value.
4. Seven-file collection: bounded command фиксирует каждый файл, а не только aggregate count.
5. POSIX branch: injected capability/monkeypatch доказывает, что Unix permission oracle не удалён.

RED должен быть вызван нужным defect class, а не broken fixture. Зафиксируй exact failing assertions и commit SHA.

## T003 — Tidy-first

После RED и до functional commit осмотри только owned files:

- локальное дублирование path-key helpers;
- import-time side effects;
- stale comments, мешающие понять capability boundary;
- Ruff/mypy/py_compile diagnostics в изменяемых файлах.

Если нужен cleanup — отдельный behavior-preserving commit и фокусные тесты. Если нет — записать `none found` с проверенными файлами/командами, без пустого commit.

## T004 — Platform-safe oracles

Минимальная реализация:

- использовать `os.devnull` и закрываемый context manager;
- проверять наличие/семантику EUID capability до декоратора/collection-time вызова;
- permission test пропускать только когда capability реально отсутствует;
- actual repo-relative key формировать через `Path.relative_to(...).as_posix()` либо один эквивалентный owning helper;
- expected constants оставить литеральными POSIX-строками;
- сообщения failure должны печатать canonical repo-relative пути и отличать actual от expected.

Не создавать общий production utility ради test-only проблемы без material replan.

## T005 — Collection и dependent gates

Обязательный collect-only command:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q -p no:cacheprovider `
  tests\cli\commands\test_sync_doctor_consent_health_3030.py `
  tests\integration\test_intake_size_cap.py `
  tests\review\test_pre_review_gate_engine.py `
  tests\specify_cli\core\test_target_branch_primitive.py `
  tests\sync\test_consent_fault_vocabulary_3030.py `
  tests\sync\test_consent_write_refusal_3030.py `
  tests\sync\test_issue_598_hang_fixes.py
```

После `0 errors` запусти owning coverage/shard/session-reaper tests из owned files. Если проявился новый primary collection defect в неowned файле — остановись и запроси material replan; не расширяй scope молча.

## T006 — Mutation и targeted GREEN

Обязательные мутации:

1. Вернуть `/dev/null` — contract test падает.
2. Вернуть import-time `os.geteuid()` — collect-only падает на Windows.
3. Удалить `.as_posix()`/canonicalization actual path — separator test падает.
4. Пропустить normalizer через expected inventory — независимый static-oracle test падает.
5. Исключить один из семи файлов из collection list/universe — completeness assertion падает.
6. Удалить POSIX capability branch — POSIX-oracle test падает.

Каждую мутацию выполнить временно, назвать убивший её test, восстановить через точечный patch и повторить GREEN. Не использовать reset/checkout для восстановления.

Финальный targeted packet:

- contract regression;
- seven-file `--collect-only`;
- все изменённые test modules;
- dependent coverage/shard/session-reaper tests;
- Ruff для изменённых Python files;
- `py_compile` для изменённых files;
- cumulative `git diff --check`;
- exact owned-file diff и clean lane после commit.

## Test strategy

- Oracle независим от implementation: expected paths — статические POSIX literals.
- Mocks допустимы только для platform capability boundary; реальные pytest collection и file discovery обязательны.
- Не принимать aggregate `pytest passed` без per-defect evidence.
- После GREEN reviewer обязан повторить минимум contract, seven-file collection, separator set и одну mutation sensitivity check.

## Definition of Done

- [ ] T001–T006 done через runtime.
- [ ] Pre-existing failure issue существует и привязан.
- [ ] Отдельный RED commit предшествует любому functional commit.
- [ ] `/dev/null` и unsafe `os.geteuid` отсутствуют в owning paths.
- [ ] Семь файлов дают `0 collection errors`.
- [ ] Separator-sensitive gates сравнивают actual POSIX path со static expected inventory.
- [ ] Dependent coverage/shard/session-reaper targeted packet зелёный.
- [ ] Шесть обязательных mutations убиты.
- [ ] Production topology, WP02 inventories и code map не изменены.
- [ ] Ruff, py_compile, diff-check и exact scope зелёные.
- [ ] Lane clean, handoff содержит commits, counts и residual uncertainty.

## Review guidance

Reviewer отклоняет пакет, если:

- Windows pass достигнут blanket skip или уменьшением expected set;
- expected inventory нормализуется тем же helper, что actual;
- seven-file collection заменена тестом одного файла;
- POSIX permission behavior удалено без oracle;
- product boundary или WP02-owned files изменены;
- RED commit нельзя воспроизвести на planning base;
- mutation evidence является grep-only или synthetic helper-only.

## Activity Log

- 2026-08-14T16:35:00Z — codex — Prompt подготовлен; реализация не начата.
