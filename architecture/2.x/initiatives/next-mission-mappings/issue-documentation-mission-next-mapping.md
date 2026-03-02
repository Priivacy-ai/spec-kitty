# Tracking Issue: `documentation` Mission `next` Mapping

Status: OPEN
Owner: spec-kitty team
Created: 2026-02-17

## Problem

`documentation` mission does not currently yield a usable `next` step path and can terminate early due to missing state-machine/template parity in the `next` decision path.

## Desired Behavior

For a feature using mission `documentation`, first `next` call returns:

1. `kind=step`
2. non-null `action`
3. non-null prompt context/output path

## Acceptance Criteria

1. `documentation` mission has explicit `next`-compatible state/action mapping.
2. Required command templates exist and resolve for mapped actions.
3. Existing strict `xfail` integration test is converted to a normal passing test.
4. This file status is changed to `CLOSED` in the same PR.
