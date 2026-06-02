# Issue matrix — slash-command-install-pipeline-repair-01KT3H00

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1608 | Broken template resolver: `_get_command_templates_dir()` returns None | fixed | commit b0d0a90ee — `_get_command_templates_dir()` now uses `doctrine.__file__`; renderer updated to per-step layout; lock write made atomic |
| #1609 | Doctor blind spot: `doctor skills` invisible to slash-command agents | fixed | commit d3854f976 — added `_load_slash_command_state()`, `_repair_slash_command_state()`, Slash Commands section in `doctor skills` output and `--fix` path |
| #1610 | Dev bootstrap gap: no path to ensure working dev environment | fixed | commit e9feb9e30 (Makefile `dev-setup` Layer B) + b0d0a90ee (Layer C: CLI startup auto-repair now functional) |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`.
