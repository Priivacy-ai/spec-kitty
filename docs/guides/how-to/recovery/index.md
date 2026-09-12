---
title: Recovery & Troubleshooting
description: "Recover from implementation crashes and interrupted merges, and troubleshoot merge failures."
doc_status: active
updated: '2026-08-15'
type: explanation
related:
- docs/operations/recovery-index.md
---

# Recovery & Troubleshooting

Recover from implementation crashes and interrupted merges, and troubleshoot merge failures.

- [Recover from an Implementation Crash](recover-from-implementation-crash.md) — How to recover from an implementation crash with Spec Kitty 3.2: Learn how to restore a work package that is stuck in inprogress after an agent crash or.
- [Recover from an Interrupted Merge](recover-from-interrupted-merge.md) — How to recover from an interrupted merge with Spec Kitty 3.2: Learn how to resume or abort a spec-kitty merge that was interrupted before it completed.
- [How to Troubleshoot Merge Issues](troubleshoot-merge.md) — How to troubleshoot merge issues with Spec Kitty 3.2: Use this guide to recover from interrupted merges, resolve conflicts, and fix pre-flight failures.

## See also

- [Operations: Recovery guides](../../../operations/recovery-index.md) — the
  operational sibling home: coord/lane split-brain recovery (operator-grant,
  `doctor --fix`). This page covers agent-facing crash/merge how-tos; that page
  covers operator-driven coordination-branch and lane-worktree recovery.
  Cross-linked, not merged, because the two serve different audiences and
  different failure classes.
