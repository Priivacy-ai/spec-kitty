# Issue matrix — agent-harness-install-audit-follow-through-01KT5YTQ

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1649 | Epic: Agent plugin and harness install verification follow-through | deferred-with-followup | Follow-up: #1644, #1646, #1647 addressed in this mission (WP01/WP03); epic closeable once child issues are closed |
| #1644 | Docs: remove stale Codex .codex prompt/skill install guidance | deferred-with-followup | Follow-up: #1644 delivered in WP01 (squash merge f928f12 to main 2026-06-03) |
| #1645 | Tests: refresh command renderer snapshots for current WP lifecycle wording | fixed | WP02 commit 6ce09d1bd: snapshots updated to canonical `approved or done` wording; squash merge f928f12 confirmed 100 passed |
| #1646 | Spike: verify Antigravity CLI plugin, skills, MCP, and hook install targets | deferred-with-followup | Follow-up: #1646 documented in WP03 as unverified (CLI not present on audit system); re-verify when Antigravity CLI is available |
| #1647 | Research: verify whether Kiro has a plugin/Powers package surface before adding plugin install support | deferred-with-followup | Follow-up: #1647 delivered in WP03 — Kiro classified prompt-only, excluded from #1635 scope (squash merge f928f12 2026-06-03) |
| #1635 | Feature: install Spec Kitty via Claude Code and Codex plugins | deferred-with-followup | Follow-up: #1635 deferred to 3.3.x per spec C-001/C-003; plugin-install implementation out of scope |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`.
