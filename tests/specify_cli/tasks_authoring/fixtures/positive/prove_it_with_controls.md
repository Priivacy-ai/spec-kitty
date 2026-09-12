---
work_package_id: WPA2
title: Prove the guard with production controls
---

## Objective

Prove the new guard actually blocks the bad path in the live pipeline.

## Acceptance Criteria

- Prove it with controls on a branch the forge will run, capturing the
  guard's verdict from the real pipeline.
- Demonstrate the merge-blocked-when-absent behavior against the protected
  branch.
