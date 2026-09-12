# WP03 Review Feedback — Cycle 3

## Verdict

Rejected after the second native run exposed a real Windows durability false-negative in the review-cycle serialization/readback contract.

## Hosted evidence

- Run: https://github.com/Priivacy-ai/spec-kitty/actions/runs/32725512250
- Windows baseline failed in round 0 for both reviewers with `persistence_failed` / `destination_readback_mismatch`, after the commit router reported each review-cycle artifact committed at `main`.
- Both failures completed in roughly one to two seconds, so this is not the allowed 10-second busy refusal.
- `ReviewCycleArtifact.write()` currently uses text-mode `Path.write_text()` with `\n` content. On Windows, text I/O can materialize CRLF locally while Git's normal clean conversion stores LF in the committed blob. WP03 then compares raw worktree bytes with `git show` bytes and rejects the successfully committed artifact.

## Required correction

Make review-cycle serialization emit deterministic UTF-8 LF bytes on every operating system before the commit/readback comparison. Preserve the exact-byte verification—do not normalize or weaken the comparison after the fact, and do not treat `destination_readback_mismatch` as success. Add focused serializer/durability coverage for the canonical LF byte contract and preserve parsing/adoption behavior.

WP03 ownership is widened only to `src/specify_cli/review/artifacts.py` and the smallest focused review-artifact test module needed to prove deterministic bytes, in addition to its existing files.

## Required evidence

- Focused artifact serialization tests prove LF-only deterministic bytes.
- WP03 cycle/adoption and WP04 durability suites pass.
- The exact SC-004 baseline passes on Windows in a fresh hosted run.
- Ruff, strict mypy, and diff-check pass on touched files.

