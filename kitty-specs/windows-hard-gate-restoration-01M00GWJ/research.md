# Исследование: Windows hard-gates

**Дата**: 2026-08-14

**Тип**: Explanation
**Аудитория**: сопровождающий Spec Kitty

## Подтверждённые факты

1. Полный contract gate ранее дал `293 passed, 3 skipped, 1 failed`; единственный failure открывает literal `/dev/null` в `tests/contract/test_machine_facing_canonical_fields.py:332`.
2. Полный architecture gate ранее дал `2036 passed, 5 skipped, 2 xfailed, 28 failed, 34 errors`.
3. Репрезентативный запуск семи architecture tests воспроизвёл `7 failed`:
   - четыре separator-sensitive comparisons формируют `\` вместо canonical `/`;
   - два audits не содержат `_compose_mission_anchor_feature_dir` из `_read_path_resolver.py`;
   - topology gate обнаруживает raw coord-path predicate в `mission_creation.py`.
4. Targeted `--collect-only` для `test_sync_doctor_consent_health_3030.py` падает при импорте: на Windows отсутствует `os.geteuid`.
5. Current code map корректен по собственным hashes, но не отображает большую часть затрагиваемых hard-gate boundaries; одной проверки lock недостаточно.
6. Canonical cross-repo E2E repository не виден текущему GitHub principal. Это access blocker, а не test verdict.
7. `bd 1.1.2` дважды выбрал `C:\Users\Ruslan\.beads` даже при task-local `BEADS_DIR`; база содержит чужие задачи, поэтому запись остановлена.

## Решения

### D-001 — Нормализовать представление, не смысл

Repo-relative path переводится в POSIX-строку на boundary формирования census/inventory key. Имена, регистр, line number, qualname и count floor не упрощаются.

### D-002 — Сначала platform defects, затем architecture verdict

Пока separator и collection искажают oracle, нельзя автоматически считать каждый architecture failure реальным bypass. После их исправления каждый оставшийся сигнал проверяется независимо.

### D-003 — Inventory update не является production fix

Если call-site действительно нарушает canonical authority, сначала исправляется production routing. Inventory синхронизируется только после этого и получает negative/mutation evidence.

### D-004 — Один дорогой финальный architecture run

Разработка использует targeted tests. Полный suite запускается после зелёной collection и targeted packet, потому что его исходное время около 55 минут.

### D-005 — E2E availability и E2E result — разные состояния

`unavailable`/`unauthorized` не сворачивается в pass или fail продукта. Публикация остаётся blocked до canonical access либо принятого владельцем изменения policy вне этой mission.

## Отклонённые альтернативы

- Blanket `skipif(sys.platform == "win32")` для всех проблемных tests: скрывает переносимые oracles.
- Замена exact sets на subset/count-only assertions: нарушает shrink-only и non-vacuity.
- Добавление `mission_creation.py` в allowlist без проверки topology authority: может законсервировать boundary bypass.
- Повтор полного architecture suite после каждой строки: дорого и не локализует root cause.
- Запись Bead в найденную глобальную DB: смешивает несвязанные проекты и нарушает isolation.
- Локальная копия/заглушка E2E repo: не доказывает canonical cross-repo compatibility.

## Неопределённости до реализации

- Raw predicate в `mission_creation.py` может оказаться узким create-time invariant; implementer обязан доказать необходимость либо заменить его canonical call, а reviewer — проверить отрицательный oracle.
- После устранения `os.geteuid` могут проявиться дополнительные первичные collection defects в шести остальных файлах.
- Доступ к E2E repo может быть восстановлен независимо от кода; этот факт проверяется только в финальном пакете.
