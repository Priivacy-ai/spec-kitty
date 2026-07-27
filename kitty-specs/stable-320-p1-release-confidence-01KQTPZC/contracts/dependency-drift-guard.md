# Contract: Dependency Drift Guard

## Purpose

Prevent review or release evidence from being trusted when the active installed environment uses a critical Spec Kitty package version that differs from `uv.lock`.

## Minimum Package Set

Required:

- `spec-kitty-events`

Optional if verification proves equivalent risk:

- `spec-kitty-tracker`

## Inputs

- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/uv.lock`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty/pyproject.toml`
- Active Python environment package metadata from the command environment used for evidence

## Pass Condition

For each checked package:

- package exists in `uv.lock`
- active installed version exists
- active installed version equals the `uv.lock` resolved version
- `pyproject.toml` constraint contains the lockfile version

## Failure Shape

Failure output must include:

- package name
- installed version
- lockfile version
- constraint, when available
- remediation command

Example:

```text
spec-kitty-events installed version drift:
  installed: 4.0.0
  uv.lock:   4.1.0
  constraint: spec-kitty-events>=4.0.0,<5.0.0
Remediation: uv sync --extra test --extra lint
```

## Closure Evidence If No Code Change Is Needed

If current gates already satisfy this contract, the mission must record:

- workflow names and job names that enforce it
- command output proving `spec-kitty-events` installed version matches `uv.lock`
- a closure note suitable for #848

## Non-Goals

- Do not loosen `pyproject.toml` constraints to hide drift.
- Do not vendor `spec-kitty-events`.
- Do not require SaaS or tracker network access for the local drift guard.
