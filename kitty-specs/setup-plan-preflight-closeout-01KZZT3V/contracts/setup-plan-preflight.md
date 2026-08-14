# Контракт setup-plan preflight

## Failed Git preflight

Для `setup-plan --json`:

- exit code: `1`;
- `error_code`: `GIT_PREFLIGHT_FAILED`;
- `remediation`: непустой список существующих remediation steps;
- Mission resolver и planning writes не выполняются.

Для человекочитаемого режима:

- exit code: `1`;
- вывод содержит причину Git preflight и существующую remediation;
- порядок отказа совпадает с JSON-режимом.

## Successful Git preflight

- Git preflight вызывается один раз для активного checkout.
- Для caller-owned пути затем разрешается canonical `MissionOperationContext`; обычный checkout сохраняет действующий feature-dir resolver.
- В caller-owned linked worktree `feature_dir` и `plan_file` указывают на caller-owned Mission surface.
- Primary checkout не получает Mission-артефакты или изменения.
- Hosted-auth и SaaS boundary gates сохраняют прежний приоритет относительно Git preflight.

## Ошибки после preflight

Если Git preflight успешен, но Mission selector отсутствует, неверен или неоднозначен, возвращается существующая Mission-context ошибка без изменения её кода и remediation.
