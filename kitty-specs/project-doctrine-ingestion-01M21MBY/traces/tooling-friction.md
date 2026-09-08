# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->

2026-09-09 — Maintenance base retains an override mission workflow, so runtime next replayed research/specify/plan after canonical scaffold completion. Owned single-branch task transitions require --auto-commit. Pytest cleans shared temporary prompts; persist evidence before concurrent test runs.

2026-09-09 — The four-subsystem pre-review scope exceeded its fixed 300-second budget with no new failures reported. Selected all changed test modules plus relevant architecture and generated-artifact gates (21 modules), independently reviewed as sufficient alongside broad owning-suite and CI results. The documented WP frontmatter scope key is rejected by WPMetadata; the supported config alias supplies the same scope for this invocation and is restored afterward. No guard was disabled.
