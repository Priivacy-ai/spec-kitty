---
work_package_id: WP06
title: Документация, quality gates и opt-in smoke harness
dependencies:
- WP03
- WP04
- WP05
requirement_refs:
- C-003
- C-004
- FR-006
- FR-009
- FR-010
- FR-012
- FR-013
- FR-014
- NFR-001
- NFR-003
- NFR-005
- NFR-006
- NFR-008
planning_base_branch: codex/ox-alpha-spec-reviewer
merge_target_branch: codex/ox-alpha-spec-reviewer
branch_strategy: Planning artifacts for this mission were generated on codex/ox-alpha-spec-reviewer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/ox-alpha-spec-reviewer unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
phase: Phase 4 - Release readiness
history:
- at: '2026-08-22T17:51:11Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
agent: codex
authoritative_surface: docs/guides/spec-review.md
create_intent:
- docs/guides/spec-review.md
- tests/integration/test_spec_review_integration.py
- tests/integration/test_spec_review_live.py
execution_mode: code_change
model: ''
owned_files:
- docs/guides/spec-review.md
- docs/changelog/CHANGELOG.md
- tests/integration/test_spec_review_integration.py
- tests/integration/test_spec_review_live.py
role: curator
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Документация, quality gates и opt-in smoke harness

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `implementer`
- **Agent/tool**: `codex`

---

## ⚠️ IMPORTANT: Review Feedback

Проверь `review_ref`. Provider claims, privacy wording и live-smoke gates должны быть закрыты до review.

## Review Feedback

План запрещает выдавать route suffix `-free` за подтверждение цены/ZDR/владельца и отделяет live evidence от deterministic CI.

## Objectives & Success Criteria

- Документировать prerequisite/preview/consent/result/failure flow.
- Не обещать free, ZDR, availability или provider ownership.
- Добавить deterministic end-to-end test на fake runner и optional live marker на synthetic spec.
- Обычный CI не зависит от OpenCode/network/model quota.
- Пройти Ruff, mypy, targeted/full relevant tests и ≥90% coverage новых ветвей.
- Проверить code map drift и согласовать mission artifacts с фактом.

## Context & Constraints

Прочитай:

- `quickstart.md`, `spec.md` и exit-code table.
- оба schema contracts и `data-model.md`.
- фактические CLI help/output после WP05.
- repository docs/changelog conventions.

Фактический live call не разрешён этим WP автоматически: его запуск требует отдельного подтверждения пользователя и только synthetic spec. Harness/test можно реализовать без запуска.

## Branch Strategy

- **Planning base**: `codex/ox-alpha-spec-reviewer`
- **Merge target**: `codex/ox-alpha-spec-reviewer`
- Начинай после WP05; final verification выполняется на интегрированной task branch.

## Subtasks & Detailed Guidance

### T028 — Operator guide и changelog

- Preconditions: install/login принадлежит OpenCode user.
- Preview command с disclosure manifest и unverified provider-properties warning.
- Interactive/noninteractive consent examples.
- Noninteractive пример использует точный `--confirm-digest <sha256>` из preview; mismatch даёт exit 2 без вызова runner.
- Таблица status/exit/remediation.
- Artifact path/schema и manual treatment of findings.
- Privacy limits: heuristic scanner не гарантирует обезличивание.
- No auto-fix, no mandatory workflow gate, no fallback model.
- Документировать fail-closed pricing gate: paid/unknown/stale snapshot блокирует запуск до prompt и передачи spec.
- No automatic retry; 429/rate limit отображается как provider error и требует нового ручного запуска с новым consent.
- Changelog entry concise, user-facing, без benchmark marketing claims.

### T029 — Integration и optional live harness

- Deterministic integration test создаёт temp mission и fake OpenCode runner.
- Проходит preview → confirmed `completed` → persisted host artifact → новый отдельно подтверждённый run.
- Проверяет hashes, summary, line ranges, exit 0, non-mutation.
- Проверяет, что paid/unknown/stale pricing возвращает `SPEC_REVIEW_MODEL_NOT_FREE` до prompt composition и вызова runner.
- Failure cases representative: 429 без retry, timeout/invalid output/write failure.
- `test_spec_review_live.py` помечен explicit marker/env opt-in, принимает только встроенный synthetic spec.
- Live test не читает repo mission specs и не запускается в обычном CI.
- Harness перед call показывает route/manifest и требует отдельный confirm gate.

### T030 — Targeted quality gates

- Запусти все new unit/contract/integration tests без live marker.
- Ruff на изменённых modules/tests.
- mypy strict по repo convention.
- Измерь branch coverage новых modules; минимум 90%.
- Если команда coverage в repo отличается, используй project authority, не импровизированный denominator.
- Зафиксируй command + результат в WP activity/review evidence, не в новый log file.

### T031 — Full regression и codemap drift

- Запусти relevant existing suites: CLI command registration, mission_runtime artifacts/resolution, invocation executor, review command.
- Затем full suite в разрешённом repo environment, если runtime/время позволяют.
- Любой pre-existing failure по charter требует отдельного issue before acceptance; не маскируй.
- Повтори codemap verification from WP01 против final HEAD.
- Если boundaries изменились, обнови все три codemap files в том же integration commit; это требует sequential coordination с WP01 ownership, не parallel edit.

### T032 — Mission/evidence reconciliation

- Сверь FR/NFR/C с tests и implementation paths.
- Обнови выполненные task checkboxes/status только штатными commands.
- Убедись, что live smoke не заявлен passed, если call не выполнялся.
- Подготовь concise review packet: changed surfaces, commands, results, residual gates.
- Не push/PR/merge/deploy без соответствующего authorization/lifecycle.

## Test Strategy

- Integration test использует fake runner, temp dirs и canonical resolver.
- Live test excluded by default via marker and environment gate.
- Sentinel проверяется во всех captured streams/artifacts.
- CLI docs examples проверяются хотя бы help/smoke contract tests.
- Coverage report относится только к new branches и не сохраняет source/prompt data.

## Risks & Mitigations

- **Маркетинговое обещание** → exact warning test/document wording.
- **Live dependency в CI** → marker off by default and synthetic-only fixture.
- **Fake-only confidence** → live smoke remains explicit optional evidence.
- **Codemap drift** → final lock verification.
- **Test baseline ambiguity** → charter issue rule.

## Review Guidance

Reviewer проверяет:

- docs совпадают с фактическим help/exit codes;
- route label не выдан за provider/price/ZDR fact;
- live test cannot consume arbitrary mission path;
- ordinary test run makes no network call;
- quality commands и results воспроизводимы;
- mission artifacts отражают только фактически выполненное.

## Definition of Done

- [ ] Guide соответствует фактическому CLI help.
- [ ] Guide содержит preview/consent/exit/artifact flow.
- [ ] Guide документирует `--confirm-digest`, запрет retry и 429/provider-error поведение.
- [ ] Warning явно отделяет route label от provider/price/ZDR facts.
- [ ] Scanner limitations описаны честно.
- [ ] Changelog не содержит benchmark claims.
- [ ] Deterministic integration test не использует network.
- [ ] Live harness принимает только built-in synthetic fixture.
- [ ] Live marker выключен по умолчанию.
- [ ] Targeted tests зелёные.
- [ ] Ruff и mypy зелёные.
- [ ] Coverage новых ветвей ≥90%.
- [ ] Relevant regression suite зелёная.
- [ ] Full suite result классифицирован честно.
- [ ] Codemap lock соответствует final HEAD/content policy.
- [ ] Mission/tasks отражают только выполненное.
- [ ] External smoke не заявлен без фактического call.

## Forbidden Changes

- Не запускать live model без отдельного подтверждения.
- Не отправлять real mission spec в smoke.
- Не добавлять CI dependency on OpenCode/model quota.
- Не заявлять free/ZDR/owner/availability как гарантии.
- Не скрывать pre-existing test failures.
- Не push/PR/merge/deploy из этого WP автоматически.
- Не менять code files, owned другими WPs, кроме согласованного sequential codemap refresh.

## Verification Evidence

Handoff содержит docs/help parity, exact test/lint/type/coverage commands и exits, live marker default-off proof, codemap verification и список remaining external gates. Длинные логи не сохранять.

## Rejection Conditions

Reviewer отклоняет WP, если docs обещают provider properties, live marker активен по умолчанию, fixture принимает arbitrary mission path, обычные tests требуют OpenCode/network, coverage ниже gate, codemap stale или evidence выдаёт невыполненный live smoke за подтверждённый.

Внешняя недоступность модели не маскирует детерминированные regression failures.

## Activity Log

- 2026-08-22T17:51:11Z – system – Prompt created.
- 2026-08-24 – codex – T030: offline targeted gate `pytest -p no:base_url tests/specify_cli/spec_review tests/mission_runtime/test_spec_review_artifact_placement.py tests/integration/test_spec_review_integration.py tests/integration/test_spec_review_live.py -m 'not live_adapter' --cov=specify_cli.spec_review --cov=specify_cli.cli.commands.spec_review --cov-branch --cov-report=term-missing -q` → `130 passed, 1 deselected`, branch coverage новых модулей `96%`; diff-relevant Ruff → `All checks passed`; `mypy --strict --platform linux` по 11 source files → `Success`. Live model не запускался.

### Updating Status

`spec-kitty agent tasks move-task WP06 --to <status>`.
- 2026-08-24T19:09:14Z – codex – shell_pid=18780 – Интегрированы approved dependency lanes WP03→WP04→WP05 в lane-f; planning/status authority сохранена из WP06 lane. Проверено на фактическом HEAD без сети/OpenCode/model call: 83 spec-review tests passed с -p no:base_url, Ruff passed, mypy --strict --platform linux passed.
