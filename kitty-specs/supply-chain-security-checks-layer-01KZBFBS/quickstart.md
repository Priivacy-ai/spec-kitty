# Quickstart: Supply Chain Security Checks Layer

## Goal

Validate that the new doctrine layer resolves correctly for software-dev planning, implementation, and review workflows, and that adversarial evidence expectations are explicit.

## Prerequisites

- Repository root checkout: `/Users/zohar/apps/spec-kitty`
- Active branch: `feat/supply-chain-security-checks-layer`
- Mission handle: `01KZBFBS3V1JMRXS5VQ2S5WWPY`

## 1) Verify mission context and branch contract

```bash
spec-kitty agent context resolve --action plan --mission 01KZBFBS3V1JMRXS5VQ2S5WWPY --json
spec-kitty agent mission setup-plan --mission 01KZBFBS3V1JMRXS5VQ2S5WWPY --json
```

Expected:
- `current_branch == target_branch == feat/supply-chain-security-checks-layer`
- `branch_matches_target == true`

## 2) Verify action-level governance resolution

```bash
spec-kitty charter context --action plan --json
spec-kitty charter context --action implement --json
spec-kitty charter context --action review --json
```

Expected:
- Security-layer artifacts are present for each software-dev action context.

## 3) Verify profile-level coverage

```bash
spec-kitty agent profile show reviewer-renata
spec-kitty agent profile show implementer-ivan
spec-kitty agent profile show node-norris
spec-kitty agent profile show frontend-freddy
```

Expected:
- Supply-chain checks and script/LTS posture guidance are visible in targeted profiles.

## 4) Verify decision integrity

```bash
spec-kitty agent decision verify --mission 01KZBFBS3V1JMRXS5VQ2S5WWPY
```

Expected:
- No `DEFERRED_WITHOUT_MARKER`, `MARKER_WITHOUT_DECISION`, or `STALE_MARKER` errors.

## 5) Run targeted tests

```bash
pytest tests/architectural/ -q
pytest tests/doctrine/ -q
pytest tests/charter/ -q
```

Expected:
- Relevant new and updated tests pass.

## Done Criteria

- Plan, research, data model, and contracts are substantive
- Decision verification passes
- Action and profile contexts include the security layer
- Advisory v1 compatibility is preserved (no new fail-closed security transition gate)
