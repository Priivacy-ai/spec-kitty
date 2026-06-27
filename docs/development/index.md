---
title: "Development notes"
description: "Internal contributor notes for Spec Kitty: testing policy, review gates, contract pinning, local overrides, and the 3.2 documentation information architecture."
---

# Development notes

Internal engineering and contributor process notes. These pages document how Spec Kitty
is built, tested, and reviewed; they target maintainers rather than end users.

## Key pages

- [Testing flakiness policy](testing-flakiness.md) — detection, tiers, and the never-retry-to-green rule.
- [Review gates](review-gates.md) — the gates a change passes before merge.
- [Contract pinning](contract-pinning.md) — pinning observable contracts in tests.
- [Local overrides](local-overrides.md) — dev editable/path overrides that must never be committed.
- [3.2 information architecture](3-2-information-architecture.md) — the documentation refresh IA.

Many additional `3-2-*` working notes in this directory track the 3.2 documentation
refresh (publication checklist, navigation plan, version taxonomy, and audit logs).

## See also

- [Documentation home](../index.md)
- [Contributing guide](../../CONTRIBUTING.md)
