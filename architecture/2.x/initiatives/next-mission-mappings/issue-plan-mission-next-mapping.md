# Tracking Issue: `plan` Mission `next` Mapping

Status: OPEN
Owner: spec-kitty team
Created: 2026-02-17

## Problem

`spec-kitty next` can return `blocked` for `plan` mission at initial state `goals` because state-to-action mapping and template coverage are incomplete.

## Desired Behavior

For a feature using mission `plan`, first `next` call returns:

1. `kind=step`
2. non-null `action`
3. non-null prompt context/output path

## Acceptance Criteria

1. `plan` mission initial and subsequent states map deterministically to supported `next` actions.
2. Command template resolution succeeds for mapped actions without fallback ambiguity.
3. Existing strict `xfail` integration test is converted to a normal passing test.
4. This file status is changed to `CLOSED` in the same PR.
