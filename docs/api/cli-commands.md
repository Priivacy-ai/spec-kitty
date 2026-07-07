---
title: CLI Command Reference
description: Complete Spec Kitty 3.2 CLI command reference with subcommands, options, mission workflow commands, and generated help output.
doc_status: active
updated: '2026-06-26'
related:
- docs/api/bulk-edit-gate.md
- docs/api/finalize-tasks-internals.md
---
# CLI Command Reference

This reference lists the user-facing `spec-kitty` CLI commands and their flags exactly as surfaced by `--help`. For agent-only commands, see `docs/api/agent-subcommands.md`.

Terminology note:
- `Mission Type` = reusable workflow blueprint
- `Mission` = tracked item under `kitty-specs/<mission-slug>/`
- `Mission Run` = runtime/session instance
- As of 3.1.0, `--mission` is the canonical flag name for specifying the mission slug. `--feature` was a hidden deprecated alias; as of 3.2.x it has been **removed everywhere** — from the internal/agent command cluster (#1060-A) and from the user-facing top-level commands (#1060). `--mission` is now the sole selector; passing `--feature` exits with `No such option`.
- `mission-state`/`accept-mission`/`merge-mission` are the canonical orchestrator-api command names

## Getting Started

- [Claude Code Integration](../guides/claude-code-integration.md)
- [Claude Code Workflow](../guides/claude-code-workflow.md)

## Practical Usage

- [Install Spec Kitty](../guides/install-spec-kitty.md)
- [Use the Dashboard](../guides/use-dashboard.md)
- [Upgrade to 0.11.0](../guides/install-and-upgrade.md)

## Command Internals

For non-obvious runtime behaviour an operator may encounter:

- [`finalize-tasks` internals](finalize-tasks-internals.md) — explicit empty `owned_files` semantics and lane-depth cycle safety.

## Schema references

- [Bulk-edit gate (`occurrence_map.yaml`)](bulk-edit-gate.md)

<!-- BEGIN GENERATED -->
# CLI Command Reference

## spec-kitty accept

```
 Usage: spec-kitty accept [OPTIONS]

 Validate mission readiness before merging to main.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission                                        TEXT  Mission slug to       │
│                                                        accept                │
│ --mode                                           TEXT  Acceptance mode:      │
│                                                        auto, pr, local, or   │
│                                                        checklist             │
│                                                        [default: auto]       │
│ --actor                                          TEXT  Name to record as the │
│                                                        acceptance actor      │
│ --test                                           TEXT  Validation command    │
│                                                        executed (repeatable) │
│ --json                                                 Emit JSON instead of  │
│                                                        formatted text        │
│ --lenient                                              Skip strict metadata  │
│                                                        validation            │
│ --no-commit                                            Report acceptance     │
│                                                        readiness without     │
│                                                        writing metadata or   │
│                                                        status changes        │
│ --diagnose                                             Diagnose acceptance   │
│                                                        blockers without      │
│                                                        writing metadata or   │
│                                                        matrix artifacts      │
│ --allow-fail                                           Return checklist even │
│                                                        when issues remain    │
│ --normalize-encoding    --no-normalize-encod…          Repair                │
│                                                        acceptance-artifact   │
│                                                        encoding              │
│                                                        (Windows-1252/Latin-1 │
│                                                        -> UTF-8) before      │
│                                                        validating.           │
│                                                        [default:             │
│                                                        no-normalize-encodin… │
│ --help                                                 Show this message and │
│                                                        exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty auth

_Authentication commands_

```
 Usage: spec-kitty auth [OPTIONS] COMMAND [ARGS]...

 Authentication commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ login   Log in to spec-kitty SaaS via browser OAuth (or device flow with     │
│         --headless).                                                         │
│ logout  Log out and revoke the current session.                              │
│ status  Show current authentication status.                                  │
│ whoami  Print the authenticated user's email and exit 0, or exit 1 if not    │
│         authenticated.                                                       │
│ doctor  Diagnose CLI auth and sync-daemon state. Default invocation is       │
│         read-only.                                                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty auth doctor

```
 Usage: spec-kitty auth doctor [OPTIONS]

 Diagnose CLI auth and sync-daemon state. Default invocation is read-only.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                          Emit findings as JSON.                       │
│ --reset                         Sweep orphan sync daemons.                   │
│ --force                         With --reset, also clean operator_required   │
│                                 daemons. No-op without --reset.              │
│ --unstick-lock                  Force-release a stuck refresh lock.          │
│ --stuck-threshold        FLOAT  Age (seconds) above which the refresh lock   │
│                                 is considered stuck.                         │
│                                 [default: 60.0]                              │
│ --server                        Check live server session status (makes      │
│                                 outbound call).                              │
│ --help                          Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty auth login

```
 Usage: spec-kitty auth login [OPTIONS]

 Log in to spec-kitty SaaS via browser OAuth (or device flow with --headless).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --headless            Use device authorization flow (for SSH or no-browser   │
│                       environments).                                         │
│ --force     -f        Re-authenticate even if already logged in.             │
│ --help                Show this message and exit.                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty auth logout

```
 Usage: spec-kitty auth logout [OPTIONS]

 Log out and revoke the current session.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force          Skip server revocation; only delete local credentials.      │
│ --help           Show this message and exit.                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty auth status

```
 Usage: spec-kitty auth status [OPTIONS]

 Show current authentication status.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty auth whoami

```
 Usage: spec-kitty auth whoami [OPTIONS]

 Print the authenticated user's email and exit 0, or exit 1 if not
 authenticated.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter

_Charter management commands_

```
 Usage: spec-kitty charter [OPTIONS] COMMAND [ARGS]...

 Charter management commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ activate      Activate a doctrine artifact by kind and ID (FR-004), with     │
│               optional cascade.                                              │
│ deactivate    Deactivate a doctrine artifact by kind and ID (FR-005), with   │
│               optional cascade.                                              │
│ interview     Capture charter interview answers for later generation.        │
│ generate      Generate charter bundle from interview answers + doctrine      │
│               references.                                                    │
│ context       Render charter context for a specific workflow action.         │
│ sync          Sync charter.md to structured YAML config files.               │
│ status        Display charter sync status plus synthesis/operator state.     │
│ synthesize    Validate and promote agent-generated project-local doctrine    │
│               artifacts.                                                     │
│ resynthesize  Regenerate a bounded set of project-local doctrine artifacts   │
│               (partial resynthesis).                                         │
│ lint          Detect decay in charter artifacts via graph-native checks.     │
│ preflight     Verify charter-derived state before a governed session begins. │
│ bundle        Charter bundle validation commands.                            │
│ mission-type  Mission type commands (activated types only).                  │
│ list          List activated doctrine artifacts by kind.                     │
│ pack          Charter pack management commands.                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter activate

```
 Usage: spec-kitty charter activate [OPTIONS] [KIND] [ARTIFACT_ID]

 Activate a doctrine artifact by kind and ID (FR-004), with optional cascade.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   kind             [KIND]         Activation kind (e.g. directive,           │
│                                   agent-profile).                            │
│   artifact_id      [ARTIFACT_ID]  Artifact ID to activate.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --cascade        TEXT  Cascade activation scope: 'all' for every referenced  │
│                        kind, or a comma-separated kind list (e.g.            │
│                        'agent-profile,tactic'). Omit to skip cascade         │
│                        (referenced artifacts are reported as a warning).     │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter bundle

_Charter bundle validation commands._

```
 Usage: spec-kitty charter bundle [OPTIONS] COMMAND [ARGS]...

 Charter bundle validation commands.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ validate  Validate the charter bundle against CharterBundleManifest v1.0.0.  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter bundle validate

```
 Usage: spec-kitty charter bundle validate [OPTIONS]

 Validate the charter bundle against CharterBundleManifest v1.0.0.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Emit structured JSON to stdout instead of a human-readable   │
│                 report.                                                      │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter context

```
 Usage: spec-kitty charter context [OPTIONS]

 Render charter context for a specific workflow action.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --action                             TEXT  Workflow action                   │
│                                            (specify|plan|implement|review)   │
│ --include                            TEXT  Fetch selector, e.g.              │
│                                            agent-profile:<id>,               │
│                                            template:<mission>/<name>,        │
│                                            directive:<id>, section:<slug>.   │
│ --mark-loaded    --no-mark-loaded          Persist first-load state          │
│                                            [default: mark-loaded]            │
│ --json                                     Output JSON. `directives` is      │
│                                            action-scoped; `all_directives`   │
│                                            and `project_charter` describe    │
│                                            the project-local charter, while  │
│                                            `org_charter` describes imported  │
│                                            org packs.                        │
│ --help                                     Show this message and exit.       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter deactivate

```
 Usage: spec-kitty charter deactivate [OPTIONS] [KIND] [ARTIFACT_ID]

 Deactivate a doctrine artifact by kind and ID (FR-005), with optional cascade.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   kind             [KIND]         Activation kind (e.g. directive,           │
│                                   agent-profile).                            │
│   artifact_id      [ARTIFACT_ID]  Artifact ID to deactivate.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --cascade        TEXT  Cascade deactivation scope: 'all' for every           │
│                        exclusively-referenced kind, or a comma-separated     │
│                        kind list. Shared artifacts are never removed. Omit   │
│                        to deactivate only the named artifact.                │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter generate

```
 Usage: spec-kitty charter generate [OPTIONS]

 Generate charter bundle from interview answers + doctrine references.

 Behavior contract (issue #841 / WP06 T029-T030):

 - On success in a git working tree, the produced
 ``.kittify/charter/charter.md``
   is auto-staged via ``git add`` so a subsequent ``charter bundle validate``
   finds it tracked without any operator ``git add`` between the two
   commands. Staging (not committing) matches the parity contract — the
   ``bundle validate`` tracked-files check keys on ``git ls-files``.
 - When the cwd is not inside a git working tree, ``generate`` exits
   non-zero before any side effect with an actionable error message that
   names the remediation (``git init``).
 - When ``.kittify/charter/charter.md`` is a symlink, ``generate`` exits
   non-zero before interview/default loading, compilation, sync,
   gitignore updates, or staging. Update the symlink target directly or
   replace it with a regular runtime charter.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission-type                               TEXT  Mission type for          │
│                                                    template-set defaults     │
│ --template-set                               TEXT  Override doctrine         │
│                                                    template set (must exist  │
│                                                    in packaged doctrine      │
│                                                    missions)                 │
│ --from-interview      --no-from-interview          Load interview answers if │
│                                                    present                   │
│                                                    [default: from-interview] │
│ --profile                                    TEXT  Default profile when no   │
│                                                    interview is available    │
│                                                    [default: minimal]        │
│ --force           -f                               Overwrite existing        │
│                                                    charter bundle            │
│ --json                                             Output JSON               │
│ --help                                             Show this message and     │
│                                                    exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter interview

```
 Usage: spec-kitty charter interview [OPTIONS]

 Capture charter interview answers for later generation.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission-type               TEXT  Mission type for charter defaults         │
│                                    (default: software-dev)                   │
│ --profile                    TEXT  Interview profile: minimal or             │
│                                    comprehensive                             │
│                                    [default: minimal]                        │
│ --defaults                         Use deterministic defaults without        │
│                                    prompts                                   │
│ --selected-paradigms         TEXT  Comma-separated paradigm IDs override     │
│ --selected-directives        TEXT  Comma-separated directive IDs override    │
│ --available-tools            TEXT  Comma-separated tool IDs override         │
│ --json                             Output JSON                               │
│ --mission-slug               TEXT  Mission slug for Decision Moment paper    │
│                                    trail (optional)                          │
│ --help                             Show this message and exit.               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter lint

```
 Usage: spec-kitty charter lint [OPTIONS]

 Detect decay in charter artifacts via graph-native checks.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission               TEXT  Scope lint to a specific mission slug          │
│ --orphans                     Run only orphan checks                         │
│ --contradictions              Run only contradiction checks                  │
│ --stale                       Run only staleness checks                      │
│ --json                        Output findings as JSON                        │
│ --severity              TEXT  Minimum severity (low/medium/high/critical)    │
│                               [default: low]                                 │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter list

_List activated doctrine artifacts by kind._

```
 Usage: spec-kitty charter list [OPTIONS] COMMAND [ARGS]...

 List activated doctrine artifacts by kind.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --show-available          Also show available-but-not-activated artifacts.   │
│ --all                     Show every available artifact per kind across the  │
│                           built-in, org, and project layers (annotated by    │
│                           source layer), including the template kind.        │
│                           Supersedes --show-available.                       │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter mission-type

_Mission type commands (activated types only)._

```
 Usage: spec-kitty charter mission-type [OPTIONS] COMMAND [ARGS]...

 Mission type commands (activated types only).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list  List activated mission types for the current project (FR-016).         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter mission-type list

```
 Usage: spec-kitty charter mission-type list [OPTIONS]

 List activated mission types for the current project (FR-016).

 Returns only mission types that are explicitly activated in this
 project's charter.  To see all doctrine-layer types regardless of
 activation state, use ``spec-kitty doctrine mission-type list``.

 Output columns (table): ID, SOURCE, DISPLAY NAME, ACTION SEQUENCE.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output as JSON.                                              │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter pack

_Charter pack management commands._

```
 Usage: spec-kitty charter pack [OPTIONS] COMMAND [ARGS]...

 Charter pack management commands.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ consistency-check  Run consistency check against activated doctrine          │
│                    artifacts (FR-011).                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter pack consistency-check

```
 Usage: spec-kitty charter pack consistency-check [OPTIONS]

 Run consistency check against activated doctrine artifacts (FR-011).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output as JSON.                                              │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter preflight

```
 Usage: spec-kitty charter preflight [OPTIONS]

 Verify charter-derived state before a governed session begins.

 Pipeline:

 1. Resolve the repo root (same logic as the rest of the ``charter``
    subcommand group).
 2. Invoke :func:`run_charter_preflight`.
 3. Render JSON or a Rich summary, then exit per the contract.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                  Emit the result as JSON (binding shape, see          │
│                         contracts/charter-preflight-json.md).                │
│ --auto-refresh          When checks fail and the worktree has no uncommitted │
│                         generated artifacts, run the safe refresh sequence   │
│                         (charter sync -> synthesize -> bundle validate).     │
│ --strict                Exit non-zero on any non-fresh state (default: exit  │
│                         zero unless a hard error occurs).                    │
│ --help                  Show this message and exit.                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter resynthesize

```
 Usage: spec-kitty charter resynthesize [OPTIONS]

 Regenerate a bounded set of project-local doctrine artifacts (partial
 resynthesis).

 Uses a structured selector to identify the target set:

 - ``directive:PROJECT_001`` — regenerate a specific project directive.
 - ``tactic:how-we-apply-directive-003`` — regenerate one tactic.
 - ``directive:DIRECTIVE_003`` — regenerate every artifact whose provenance
   references the built-in DIRECTIVE_003 URN.
 - ``testing-philosophy`` — regenerate all artifacts from that interview
 section.

 Unrelated artifacts are never touched (FR-017).

 Examples
 --------
 Resynthesize a single tactic::

     spec-kitty charter resynthesize --topic tactic:how-we-apply-directive-003

 Resynthesize all artifacts referencing a built-in directive::

     spec-kitty charter resynthesize --topic directive:DIRECTIVE_003

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --topic                     TEXT  Structured topic selector: <kind>:<slug>   │
│                                   (project-local), <drg-urn>                 │
│                                   (built-in+project graph), or               │
│                                   <interview-section-label>.                 │
│ --list-topics                     List valid structured topic selectors and  │
│                                   exit.                                      │
│ --adapter                   TEXT  Adapter to use. 'generated' (default)      │
│                                   validates agent-authored YAML under        │
│                                   .kittify/charter/generated/. 'fixture' is  │
│                                   offline/testing only.                      │
│                                   [default: generated]                       │
│ --skip-code-evidence              Skip code-reading evidence collection.     │
│ --skip-corpus                     Skip best-practice corpus loading.         │
│ --json                            Output JSON                                │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter status

```
 Usage: spec-kitty charter status [OPTIONS]

 Display charter sync status plus synthesis/operator state.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                Output JSON                                            │
│ --provenance          Include per-artifact provenance details.               │
│ --help                Show this message and exit.                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter sync

```
 Usage: spec-kitty charter sync [OPTIONS]

 Sync charter.md to structured YAML config files.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force  -f        Force sync even if not stale                              │
│ --json             Output JSON                                               │
│ --help             Show this message and exit.                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty charter synthesize

```
 Usage: spec-kitty charter synthesize [OPTIONS]

 Validate and promote agent-generated project-local doctrine artifacts.

 Reads the charter interview answers, resolves synthesis targets from the
 DRG + doctrine, and writes all artifacts to ``.kittify/doctrine/``.

 Doctrine generation is performed by the LLM harness (Claude Code, Codex,
 Cursor, etc.) via the spec-kitty-charter-doctrine skill. This command
 validates and promotes the artifacts the agent has written.

 Fresh-project behavior (issue #839 / WP06 T031-T033)
 ----------------------------------------------------
 On a fresh project where ``.kittify/charter/generated/`` is missing or
 empty (i.e. the LLM harness has not yet written agent artifacts), this
 command short-circuits the adapter pipeline and materializes the
 **minimal artifact set** the runtime requires:

 1. ``.kittify/doctrine/`` — directory marker. ``DoctrineService``'s
    project-root resolver (``src/charter/_doctrine_paths.py``) is a
    presence-only check; an empty directory is a valid project layer.
 2. ``.kittify/doctrine/PROVENANCE.md`` — human-readable record of the
    fresh-project seed path, citing #839.

 The runtime falls back to the built-in doctrine (``src/doctrine/``) for
 all artifact lookups until the harness writes per-target YAML and the
 operator re-runs ``synthesize`` (which then takes the normal adapter
 path). The fresh-project path is **idempotent**: re-running produces
 bytewise-identical output (T033). Charter prerequisites are still
 enforced — ``charter.md`` must exist (else ``TaskCliError`` is raised
 via ``_build_synthesis_request``).

 Examples
 --------
 Validate + promote generated artifacts written by the harness::

     spec-kitty charter synthesize

 Validate + promote with fixture adapter (offline/testing)::

     spec-kitty charter synthesize --adapter fixture

 Dry-run (stage + validate, no promote)::

     spec-kitty charter synthesize --dry-run

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --adapter                   TEXT  Adapter to use. 'generated' (default)      │
│                                   validates agent-authored YAML under        │
│                                   .kittify/charter/generated/. 'fixture' is  │
│                                   offline/testing only.                      │
│                                   [default: generated]                       │
│ --dry-run                         Stage and validate artifacts but do not    │
│                                   promote to live tree.                      │
│ --json                            Output JSON                                │
│ --skip-code-evidence              Skip code-reading evidence collection.     │
│ --skip-corpus                     Skip best-practice corpus loading.         │
│ --dry-run-evidence                Print evidence summary and exit without    │
│                                   running synthesis.                         │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty config

```
 Usage: spec-kitty config [OPTIONS]

 Display project configuration and asset resolution information.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --show-origin                Show where each resolved asset comes from (tier │
│                              label + path)                                   │
│ --mission      -m      TEXT  Mission to resolve assets for                   │
│                              [default: software-dev]                         │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty context

_Query workspace context information_

```
 Usage: spec-kitty context [OPTIONS] COMMAND [ARGS]...

 Query workspace context information

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ info             Show context information for current or specified           │
│                  workspace.                                                  │
│ list             List all workspace contexts.                                │
│ cleanup          Clean up orphaned workspace contexts.                       │
│ mission-resolve  Resolve and persist a MissionContext token.                 │
│ mission-show     Show all fields of a persisted MissionContext token.        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty context cleanup

```
 Usage: spec-kitty context cleanup [OPTIONS]

 Clean up orphaned workspace contexts.

 Removes context files for workspaces that no longer exist.

 Examples:
     # Preview cleanup
     spec-kitty context cleanup --dry-run

     # Clean up orphaned contexts
     spec-kitty context cleanup

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dry-run          Show what would be cleaned up without deleting            │
│ --help             Show this message and exit.                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty context info

```
 Usage: spec-kitty context info [OPTIONS]

 Show context information for current or specified workspace.

 Examples:
 # Auto-detect from current directory (if inside worktree)
 spec-kitty context info

 # Explicit workspace
 spec-kitty context info --workspace 010-feature-lane-a

 # JSON output
 spec-kitty context info --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --workspace  -w      TEXT  Workspace name (auto-detected if inside worktree) │
│ --json                     Output in JSON format                             │
│ --help                     Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty context list

```
 Usage: spec-kitty context list [OPTIONS]

 List all workspace contexts.

 Examples:
 # List all contexts
 spec-kitty context list

 # List only orphaned contexts (worktree deleted)
 spec-kitty context list --orphaned

 # JSON output
 spec-kitty context list --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json              Output in JSON format                                    │
│ --orphaned          Show only orphaned contexts                              │
│ --help              Show this message and exit.                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty context mission-resolve

```
 Usage: spec-kitty context mission-resolve [OPTIONS]

 Resolve and persist a MissionContext token.

 Creates a new bound context for the given work package and feature,
 writes it to .kittify/runtime/contexts/, and prints the token.

 The token can be passed to other commands via --context <token>.

 Examples:
     # Resolve and print token for piping
     TOKEN=$(spec-kitty context mission-resolve --wp WP01 --mission
 057-my-feature)

     # Resolve and print full JSON
     spec-kitty context mission-resolve --wp WP01 --mission 057-my-feature
 --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --wp             TEXT  Work package code (e.g., WP01) [required]          │
│    --mission        TEXT  Mission slug (e.g., 057-mission-name)              │
│    --agent          TEXT  Agent name (default: 'unknown')                    │
│    --json                 Output full JSON context (default: token only)     │
│    --help                 Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty context mission-show

```
 Usage: spec-kitty context mission-show [OPTIONS]

 Show all fields of a persisted MissionContext token.

 Loads the context file and pretty-prints its bound fields.

 Examples:
     spec-kitty context mission-show --context ctx-01HVXYZ...
     spec-kitty context mission-show --context ctx-01HVXYZ... --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --context        TEXT  Context token (e.g., ctx-01HV...) [required]       │
│    --json                 Output raw JSON                                    │
│    --help                 Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty dashboard

```
 Usage: spec-kitty dashboard [OPTIONS]

 Open or stop the Spec Kitty dashboard.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --port        INTEGER  Preferred port for the dashboard (falls back to the   │
│                        first available port).                                │
│ --kill                 Stop the running dashboard for this project and clear │
│                        its metadata.                                         │
│ --open                 Open dashboard URL in your default browser (disabled  │
│                        by default).                                          │
│ --json                 Print the mission registry as JSON (keyed by          │
│                        mission_id) and exit. Does not start the dashboard    │
│                        server.                                               │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty dispatch

_Dispatch a request to a governed Op (canonical surface)._

```
 Usage: spec-kitty dispatch [OPTIONS] REQUEST

 Dispatch a request to a governed Op (canonical surface).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    request      TEXT  Natural language request. The router picks the best  │
│                         profile.                                             │
│                         [required]                                           │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --profile        TEXT  Optional profile ID. Bypasses the router — use when   │
│                        the request is ambiguous.                             │
│ --json                 Output JSON payload                                   │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor

_Project health diagnostics_

```
 Usage: spec-kitty doctor [OPTIONS] COMMAND [ARGS]...

 Project health diagnostics

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ command-files       Check all agent command files for correctness.           │
│ skills              Check command-skill manifest drift for Codex, Vibe, Pi,  │
│                     and Letta.                                               │
│ tool-surfaces       Audit (and optionally repair) every configured tool      │
│                     surface.                                                 │
│ state-roots         Show state roots, surface classification, and safety     │
│                     warnings.                                                │
│ workspaces          Report .worktrees/ husk directories (entries lacking a   │
│                     .git entry).                                             │
│ identity            Report mission-identity health across kitty-specs/.      │
│ topology            Report each mission's STORED topology across             │
│                     kitty-specs/.                                            │
│ sparse-checkout     Detect and optionally remediate legacy sparse-checkout   │
│                     state.                                                   │
│ shim-registry       Check for overdue compatibility shims in the shim        │
│                     registry.                                                │
│ contracts           Validate the Contract Registry for well-formedness.      │
│ invocation-pairing  List orphan profile-invocation lifecycle records.        │
│ ops                 List orphan Op records; --close-stale sweeps stale ones  │
│                     closed as abandoned.                                     │
│ orphan-daemons      List orphan daemon owner records and emit retirement     │
│                     hints.                                                   │
│ restart-daemon      Stop the registered sync daemon and respawn it at the    │
│                     foreground.                                              │
│ mission-state       Audit, repair, or TeamSpace-validate mission-state       │
│                     shapes.                                                  │
│ doctrine            Check org doctrine snapshot status and list installed    │
│                     pack artifacts.                                          │
│ coordination        Run the WP04 #1348 coordination + sparse-checkout health │
│                     checks.                                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor command-files

```
 Usage: spec-kitty doctor command-files [OPTIONS]

 Check all agent command files for correctness.

 Verifies that every configured agent has the correct command files:
 - Full rendered prompts for prompt-driven commands (specify, plan, tasks, ...)
 - Thin shims for CLI-driven commands (implement, review, merge, ...)
 - Current version markers on all files

 Examples:
     spec-kitty doctor command-files
     spec-kitty doctor command-files --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor contracts

```
 Usage: spec-kitty doctor contracts [OPTIONS]

 Validate the Contract Registry for well-formedness.

 Reads docs/contracts/contract-registry.yaml and validates every record
 against the schema: required fields present, kind/status/enforcement in
 range, semver + tracker refs well-formed, anchors resolve, and — the DIR-041
 self-consistency gate (NFR-003) — NO positional file:line anchoring anywhere.
 Structural validation is the only enforcing gate in v1; the retirement
 absence-sweep is advisory.

 Exit codes:
   0  Registry is well-formed (or empty).
   2  Configuration error (registry file missing) or a schema violation.

 Examples:
     spec-kitty doctor contracts
     spec-kitty doctor contracts --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor coordination

```
 Usage: spec-kitty doctor coordination [OPTIONS]

 Run the WP04 #1348 coordination + sparse-checkout health checks.

 Iterates over every mission under ``kitty-specs/`` whose ``meta.json``
 declares a ``coordination_branch`` field, runs the coord-worktree
 and lane-sparse-checkout health checks, and prints findings.

 Also runs the minimum git-version (RR-01) check.

 Exits with code 1 if any ``error`` finding is emitted; ``warning``
 findings exit 0 but are still printed.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor doctrine

```
 Usage: spec-kitty doctor doctrine [OPTIONS]

 Check org doctrine snapshot status and list installed pack artifacts.

 Exit code reflects health (WP01, operator directive: loud over hidden): the
 command exits **1 when the report is unhealthy** and 0 only when healthy
 (``report.healthy`` drives the code on every output path). A clear RC=1 with
 a surfaced error is preferred over an RC=0 that hides a defect.  It
 enumerates each configured org pack (from ``.kittify/config.yaml``), prints
 its on-disk version (``git describe`` for git-managed packs, otherwise the
 ``pack-manifest.yaml`` ``pack_version``), per-artifact YAML counts, and
 ``org-charter.yaml`` policy status when present.

 Override governance (FR-010 / FR-012): when org packs are configured, any
 ``org:``-provenance override of a built-in DRG node that is NOT sanctioned
 by ``.kittify/doctrine/replaceable-builtins.yaml`` is reported as an
 ``unsanctioned_overrides`` finding and flips the report unhealthy (RC=1).
 Project-tier (``.kittify/doctrine/``) overrides of built-ins are
 intentionally **ungoverned** — project doctrine is the trusted operator tier
 and is not gated by the consumer-facing allowlist; only org-tier overrides
 are adjudicated.

 Examples:
     spec-kitty doctor doctrine
     spec-kitty doctor doctrine --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor identity

```
 Usage: spec-kitty doctor identity [OPTIONS]

 Report mission-identity health across kitty-specs/.

 Classifies every mission into one of four states (FR-045):

 \b
 - assigned: mission_id present AND mission_number non-null (fully migrated)
 - pending:  mission_id present AND mission_number null (pre-merge)
 - legacy:   mission_id missing AND mission_number present (needs backfill)
 - orphan:   both fields missing or meta.json unreadable (needs triage)

 Also reports duplicate numeric prefixes (FR-011) and ambiguous selectors
 that would resolve to multiple missions (FR-012).

 Examples:
     spec-kitty doctor identity
     spec-kitty doctor identity --json
     spec-kitty doctor identity --mission 083-foo
     spec-kitty doctor identity --fail-on legacy,orphan

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                 Emit structured JSON output (suitable for CI)         │
│ --mission        TEXT  Scope report to a single mission slug                 │
│ --fail-on        TEXT  Exit non-zero if any mission is in the given          │
│                        state(s). Comma-separated list of: assigned, pending, │
│                        legacy, orphan.                                       │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor invocation-pairing

```
 Usage: spec-kitty doctor invocation-pairing [OPTIONS]

 List orphan profile-invocation lifecycle records.

 WP05 (#843) wiring: scans
 ``.kittify/events/profile-invocation-lifecycle.jsonl`` for ``started``
 records with no paired ``completed`` or ``failed`` partner. Mid-cycle
 agent crashes show up here. The check observes; it does not remediate.

 Exit codes:
   0  No orphans observed.
   1  At least one orphan found.

 Examples:
     spec-kitty doctor invocation-pairing
     spec-kitty doctor invocation-pairing --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor mission-state

```
 Usage: spec-kitty doctor mission-state [OPTIONS]

 Audit, repair, or TeamSpace-validate mission-state shapes.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --audit                          Run mission-state audit (required to        │
│                                  proceed)                                    │
│ --fix                            Repair mission-state artifacts in place and │
│                                  write a migration manifest                  │
│ --teamspace-dry-run              Synthesize canonical TeamSpace envelopes    │
│                                  from local state and validate them          │
│ --json                           Emit JSON report to stdout                  │
│ --mission                  TEXT  Scope to a single mission handle            │
│ --fail-on                  TEXT  Exit 1 if findings meet a gate              │
│                                  (error|warning|info|teamspace-blocker)      │
│ --fixture-dir              PATH  Override scan root (for testing)            │
│ --include-fixtures               Audit the bundled mission-state survey      │
│                                  fixtures                                    │
│ --manifest-path            PATH  Path for --fix migration manifest           │
│ --allow-dirty                    Allow --fix when relevant git paths are     │
│                                  already dirty                               │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor ops

```
 Usage: spec-kitty doctor ops [OPTIONS]

 List orphan Op records; --close-stale sweeps stale ones closed as abandoned.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                      Machine-readable JSON output                     │
│ --close-stale               Close open Ops older than --threshold as         │
│                             abandoned (closed_by=doctor_sweep)               │
│ --threshold          FLOAT  Staleness threshold in hours (default 24; 0      │
│                             closes all). Requires --close-stale.             │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor orphan-daemons

```
 Usage: spec-kitty doctor orphan-daemons [OPTIONS]

 List orphan daemon owner records and emit retirement hints.

 Implements FR-010 of the identity-boundary mission: an orphan
 daemon owner record is one whose recorded PID is dead OR whose
 recorded executable path no longer exists on disk. Each orphan
 is printed with a copy-pasteable retirement command that removes
 the on-disk ``owner.json`` so the next ``sync status --check``
 returns clean.

 Exit codes:
   0  No orphan records.
   1  At least one orphan record found.

 Examples:
     spec-kitty doctor orphan-daemons
     spec-kitty doctor orphan-daemons --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor restart-daemon

```
 Usage: spec-kitty doctor restart-daemon [OPTIONS]

 Stop the registered sync daemon and respawn it at the foreground.

 Composes the existing daemon stop + launch primitives so the operator
 has a one-shot remedy when the foreground process and the registered
 daemon disagree on any of the six canonical D-3 fields (version,
 executable, source, server URL, team/user, or queue DB path).

 Exit codes:
   0  Daemon restarted (or stale owner record cleaned and respawned).
   1  No registered daemon — run ``spec-kitty sync now`` to launch one.
   2  Daemon stop succeeded but respawn failed; system is stopped.
   3  Daemon stop failed (unresponsive); owner record left intact.

 Examples:
     spec-kitty doctor restart-daemon
     spec-kitty doctor restart-daemon --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Emit a single JSON object instead of human-readable text.    │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor shim-registry

```
 Usage: spec-kitty doctor shim-registry [OPTIONS]

 Check for overdue compatibility shims in the shim registry.

 Reads docs/migrations/shim-registry.yaml and compares each entry's
 removal_target_release against the current project version. Fails with
 exit code 1 if any shim is overdue (removal release has shipped but
 shim file still exists on disk).

 Exit codes:
   0  All entries are pending, removed, or grandfathered.
   1  At least one entry is overdue — shim must be deleted or window extended.
   2  Configuration error (registry file or pyproject.toml missing/invalid).

 Examples:
     spec-kitty doctor shim-registry
     spec-kitty doctor shim-registry --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor skills

```
 Usage: spec-kitty doctor skills [OPTIONS]

 Check command-skill manifest drift for Codex, Vibe, Pi, and Letta.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --fix           Repair missing command-skill files                           │
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor sparse-checkout

```
 Usage: spec-kitty doctor sparse-checkout [OPTIONS]

 Detect and optionally remediate legacy sparse-checkout state.

 Without ``--fix``: scans the repo and prints a warning finding
 describing any active sparse-checkout state (primary + lane
 worktrees). Exits 0 when clean, 1 when state is present.

 With ``--fix``: in an interactive TTY, prints a step-by-step plan,
 prompts once for consent, and calls WP03's ``remediate()``. In
 non-interactive / CI environments, prints a remediation pointer and
 exits non-zero without mutating state (FR-023).

 Examples:
     spec-kitty doctor sparse-checkout
     spec-kitty doctor sparse-checkout --fix

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --fix           Apply remediation (disable sparse-checkout on primary +      │
│                 worktrees).                                                  │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor state-roots

```
 Usage: spec-kitty doctor state-roots [OPTIONS]

 Show state roots, surface classification, and safety warnings.

 Displays the three state roots with resolved paths, all registered
 state surfaces grouped by root with authority and Git classification,
 and warnings for any runtime surfaces not covered by .gitignore.

 Examples:
     spec-kitty doctor state-roots
     spec-kitty doctor state-roots --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor tool-surfaces

```
 Usage: spec-kitty doctor tool-surfaces [OPTIONS]

 Audit (and optionally repair) every configured tool surface.

 Examples:
 spec-kitty doctor tool-surfaces --json
 spec-kitty doctor tool-surfaces --kind command-skill --json
 spec-kitty doctor tool-surfaces --tool codex --fix

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --kind        TEXT  Filter to surface kind(s), e.g. command-skill            │
│ --tool        TEXT  Filter to a single configured tool key                   │
│ --fix               Repair missing or stale surfaces                         │
│ --json              Machine-readable JSON output                             │
│ --help              Show this message and exit.                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor topology

```
 Usage: spec-kitty doctor topology [OPTIONS]

 Report each mission's STORED topology across kitty-specs/.

 Reads the authoritative ``topology`` value persisted in ``meta.json`` WITHOUT
 re-inferring from disk/git. Missions not yet backfilled surface
 ``topology: null`` — run ``spec-kitty migrate backfill-topology`` to persist
 the computed value.

 Examples:
     spec-kitty doctor topology
     spec-kitty doctor topology --json
     spec-kitty doctor topology --mission 083-foo

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                 Emit structured JSON output (suitable for CI)         │
│ --mission        TEXT  Scope report to a single mission slug                 │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctor workspaces

```
 Usage: spec-kitty doctor workspaces [OPTIONS]

 Report .worktrees/ husk directories (entries lacking a .git entry).

 A husk is not a usable git worktree: git commands run inside it fall
 through to the primary repository (#1833). Workspace resolution refuses
 husks with a structured error; this check is the recovery path.

 Examples:
     spec-kitty doctor workspaces
     spec-kitty doctor workspaces --fix
     spec-kitty doctor workspaces --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --fix           Remove husks that are NOT registered in `git worktree list`  │
│                 (registered worktrees are never removed)                     │
│ --json          Machine-readable JSON output                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine

_Manage org-layer doctrine packs_

```
 Usage: spec-kitty doctrine [OPTIONS] COMMAND [ARGS]...

 Manage org-layer doctrine packs

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ fetch             Fetch org doctrine pack(s) from their configured remote    │
│                   sources.                                                   │
│ regenerate-graph  Regenerate the shipped DRG ``graph.yaml``                  │
│                   deterministically (FR-009).                                │
│ new               Scaffold a stub doctrine artifact YAML (FR-016).           │
│ validate          Validate project-layer doctrine artifacts against their    │
│                   schemas (FR-017).                                          │
│ pack              Validate or assemble doctrine packs.                       │
│ org               Manage org-layer doctrine pack authoring (init, validate). │
│ mission-type      Mission type commands.                                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine fetch

```
 Usage: spec-kitty doctrine fetch [OPTIONS]

 Fetch org doctrine pack(s) from their configured remote sources.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --pack           TEXT  Fetch only the named pack (default: fetch all         │
│                        configured packs).                                    │
│ --dry-run              Show what would be fetched without contacting any     │
│                        remote.                                               │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine mission-type

_Mission type commands._

```
 Usage: spec-kitty doctrine mission-type [OPTIONS] COMMAND [ARGS]...

 Mission type commands.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list  List all mission types in the doctrine layer (FR-013).                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine mission-type list

```
 Usage: spec-kitty doctrine mission-type list [OPTIONS]

 List all mission types in the doctrine layer (FR-013).

 Enumerates built-in, org, and project mission types regardless of
 activation state.  The DRG resolution chain applies: built-in →
 org → project.  An org type with the same id shadows the built-in
 type; a project type shadows the org type.

 Use ``spec-kitty charter mission-type list`` to see only types that
 are currently activated for this project.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output as JSON.                                              │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine new

```
 Usage: spec-kitty doctrine new [OPTIONS] KIND ID

 Scaffold a stub doctrine artifact YAML (FR-016).

 The scaffolder pre-fills the canonical schema's required fields with
 ``TODO …`` placeholders so the file passes ``doctrine validate`` on
 first emit.  Refuses to overwrite an existing file.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    kind             TEXT  Artifact kind (singular): one of agent_profile,  │
│                             directive, mission_step_contract, paradigm,      │
│                             procedure, styleguide, tactic, toolguide.        │
│                             [required]                                       │
│ *    artifact_id      ID    Artifact identifier (kebab-case for most kinds;  │
│                             SCREAMING_SNAKE for directives).                 │
│                             [required]                                       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --pack        PATH  Scaffold inside a doctrine pack directory instead of the │
│                     project layer. When omitted, the stub lands under        │
│                     .kittify/doctrine/.                                      │
│ --help              Show this message and exit.                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine org

_Manage org-layer doctrine pack authoring (init, validate)._

```
 Usage: spec-kitty doctrine org [OPTIONS] COMMAND [ARGS]...

 Manage org-layer doctrine pack authoring (init, validate).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ init      Scaffold a minimal org doctrine pack skeleton (FR-006).            │
│ validate  Validate an org doctrine pack using schema and DRG checks          │
│           (FR-006).                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine org init

```
 Usage: spec-kitty doctrine org init [OPTIONS] PACK_PATH

 Scaffold a minimal org doctrine pack skeleton (FR-006).

 Creates three files under *pack-path*::

     org-charter.yaml   — governance policy stub
     drg/fragment.yaml  — DRG extension stub (with pydantic_model: frontmatter)
     README.md          — authoring quickstart

 Refuses to overwrite an existing directory unless ``--force`` is passed.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    pack_path      PATH  Path to the directory to initialise as an org      │
│                           doctrine pack.                                     │
│                           [required]                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force          Overwrite an existing pack directory.                       │
│ --help           Show this message and exit.                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine org validate

```
 Usage: spec-kitty doctrine org validate [OPTIONS] PACK_PATH

 Validate an org doctrine pack using schema and DRG checks (FR-006).

 Calls the WP06 :func:`specify_cli.doctrine.pack_validator.validate_pack`
 loader.  Prints per-file findings with file paths.  Exits non-zero when
 at least one error is found.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    pack_path      PATH  Path to the org doctrine pack directory to         │
│                           validate.                                          │
│                           [required]                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine pack

_Validate or assemble doctrine packs._

```
 Usage: spec-kitty doctrine pack [OPTIONS] COMMAND [ARGS]...

 Validate or assemble doctrine packs.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ validate  Validate a doctrine pack against schema and DRG constraints.       │
│ assemble  Assemble multiple doctrine packs into a single distributable.      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine pack assemble

```
 Usage: spec-kitty doctrine pack assemble [OPTIONS] OUTPUT_PATH INPUT_PACKS...

 Assemble multiple doctrine packs into a single distributable.

 Exits 0 on success and 1 when conflicts block the merge or when the
 assembled output fails validation.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    output_path      PATH            Output directory for the assembled     │
│                                       distributable pack.                    │
│                                       [required]                             │
│ *    input_packs      INPUT_PACKS...  One or more input pack directories to  │
│                                       assemble.                              │
│                                       [required]                             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --conflicts-out        PATH  Write the conflict report to this path (JSON).  │
│ --force                      Resolve artifact-id conflicts by last-pack-wins │
│                              and drop duplicate DRG edges silently.          │
│ --json                       Emit machine-readable JSON instead of rich      │
│                              text.                                           │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine pack validate

```
 Usage: spec-kitty doctrine pack validate [OPTIONS] PACK_PATH

 Validate a doctrine pack against schema and DRG constraints.

 Exits 0 when the pack passes validation (advisories do not affect the
 exit code) and 1 when at least one error is reported.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    pack_path      PATH  Path to the doctrine pack directory to validate.   │
│                           [required]                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Emit machine-readable JSON instead of rich text.             │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine regenerate-graph

```
 Usage: spec-kitty doctrine regenerate-graph [OPTIONS]

 Regenerate the shipped DRG ``graph.yaml`` deterministically (FR-009).

 Composes the DRG extractor + calibrator into ``src/doctrine/graph.yaml``.
 Running twice on unchanged inputs yields byte-identical output. With
 ``--check`` the command never writes: it regenerates into a temp file and
 compares against the committed graph, exiting non-zero when stale — the
 operator-facing twin of the ``test_shipped_graph_yaml_is_fresh`` gate.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --check          Do not write; regenerate into a temp file and compare       │
│                  against the committed graph.yaml. Exit 1 when stale         │
│                  (operator-runnable freshness gate). Exit 0 when fresh.      │
│ --json           Emit machine-readable JSON instead of rich text.            │
│ --help           Show this message and exit.                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty doctrine validate

```
 Usage: spec-kitty doctrine validate [OPTIONS] PATH

 Validate project-layer doctrine artifacts against their schemas (FR-017).

 When *path* is a single file, validates that file.  When *path* is a
 directory, walks the tree for ``*.yaml`` files whose filename suffix
 matches a canonical artifact kind and validates each one.

 Exit code: ``0`` if every artifact validates; ``1`` if any artifact
 fails.  A per-file error report is printed for failures.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    path      PATH  Artifact YAML file or a directory containing            │
│                      project-layer doctrine artifacts (recurses into         │
│                      per-kind subdirectories).                               │
│                      [required]                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty glossary

_Glossary management commands_

```
 Usage: spec-kitty glossary [OPTIONS] COMMAND [ARGS]...

 Glossary management commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list       List all terms in glossary.                                       │
│ conflicts  Display conflict history from event log.                          │
│ resolve    Resolve a conflict asynchronously.                                │
│ show       Render the entity page for a glossary term.                       │
│ validate   Validate glossary seed file(s) against the schema.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty glossary conflicts

```
 Usage: spec-kitty glossary conflicts [OPTIONS]

 Display conflict history from event log.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission           TEXT  Filter conflicts by mission ID                     │
│ --unresolved              Show only unresolved conflicts                     │
│ --strictness        TEXT  Filter by effective strictness level (off, medium, │
│                           max)                                               │
│ --json                    Output as JSON (machine-parseable)                 │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty glossary list

```
 Usage: spec-kitty glossary list [OPTIONS]

 List all terms in glossary.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --scope         TEXT  Filter by scope (mission_local, team_domain,           │
│                       audience_domain, spec_kitty_core)                      │
│ --status        TEXT  Filter by status (active, deprecated, draft)           │
│ --json                Output as JSON (machine-parseable)                     │
│ --help                Show this message and exit.                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty glossary resolve

```
 Usage: spec-kitty glossary resolve [OPTIONS] CONFLICT_ID

 Resolve a conflict asynchronously.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    conflict_id      TEXT  Conflict ID to resolve [required]                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission ID for event log (auto-detected if omitted)   │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty glossary show

```
 Usage: spec-kitty glossary show [OPTIONS] TERM

 Render the entity page for a glossary term.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    term      TEXT  Term surface name or glossary URN (e.g.                 │
│                      'deployment-target' or 'glossary:deployment-target')    │
│                      [required]                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty glossary validate

```
 Usage: spec-kitty glossary validate [OPTIONS] PATH

 Validate glossary seed file(s) against the schema.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    path      PATH  Path to a glossary seed file (.yaml) or directory of    │
│                      seed files                                              │
│                      [required]                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output validation results as JSON                            │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty implement

```
 Usage: spec-kitty implement [OPTIONS] WP_ID

 Internal — allocate or reuse the lane worktree for a work package.

 This command is internal infrastructure, used by ``spec-kitty agent action
 implement``
 for workspace creation. It is not the canonical user-facing implementation
 path for
 spec-kitty 3.1.1.

 Canonical user workflow::

   spec-kitty next --agent <name> --mission <slug>   (loop entry)
   spec-kitty agent action implement <WP> --agent <name>  (per-WP verb)

 This command remains available as a compatibility surface for direct callers.
 See FR-503 and D-4 in the 3.1.1 spec.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    wp_id      TEXT  Work package ID (for example, WP01) [required]         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission                                      TEXT  Mission slug (for       │
│                                                      example,                │
│                                                      001-my-feature)         │
│ --auto-commit              --no-auto-commit          Auto-commit status and  │
│                                                      planning changes        │
│                                                      (default: from project  │
│                                                      config)                 │
│ --json                                               Output in JSON format   │
│ --recover                                            Recover from crashed    │
│                                                      implementation session  │
│ --base                                         TEXT  Explicit base ref for   │
│                                                      the lane workspace      │
│                                                      (default: auto-detect). │
│                                                      Use this when upstream  │
│                                                      dependency branches     │
│                                                      have been               │
│                                                      merged-and-deleted and  │
│                                                      you want to start from  │
│                                                      the current target      │
│                                                      branch tip, e.g. --base │
│                                                      main.                   │
│ --acknowledge-not-bulk…                              Suppress the bulk-edit  │
│                                                      inference warning when  │
│                                                      spec language resembles │
│                                                      a bulk edit but the     │
│                                                      mission is not one.     │
│ --help                                               Show this message and   │
│                                                      exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty init

```
 Usage: spec-kitty init [OPTIONS] [PROJECT_NAME]

 Initialize a new Spec Kitty project.

 Creates project files only. Does not initialize a git repository.
 Does not create any commits.

 If PROJECT_NAME is omitted, init runs in the current directory.
 Re-running init in an already-initialized directory exits cleanly
 (idempotent).

 Note: The --no-git flag from previous versions has been removed.
       init never touches git state regardless of flags.

 Interactive Mode (default):
 - Prompts you to select AI assistants

 Non-Interactive Mode:
 - Enabled with --non-interactive/--yes, SPEC_KITTY_NON_INTERACTIVE=1, or
 non-TTY
 - Skips all prompts; --ai is required
 - Perfect for CI/CD and automation

 What Gets Created:
 - .kittify/ - Project scaffold (memory, config)
 - Agent command and skill surfaces (.claude/commands/, .agents/skills/, etc.)
 - .gitignore and .claudeignore

 Specifying AI Assistants (--ai flag):
 Use comma-separated agent keys (no spaces). Valid keys include:
 codex, claude, gemini, cursor, qwen, opencode, windsurf, kilocode,
 auggie, copilot, q, kiro, antigravity, vibe, pi, letta.

 Template Discovery (Development Mode):
 Set SPEC_KITTY_TEMPLATE_ROOT to override bundled templates for local
 development.

 Examples:
   spec-kitty init --ai codex                    # Current directory (default)
   spec-kitty init my-project                    # Interactive mode
   spec-kitty init my-project --ai codex         # With Codex
   spec-kitty init my-project --ai codex,claude  # Multiple agents
   spec-kitty init --ai claude --non-interactive # Non-interactive

 Canonical Next Steps (after init):
   spec-kitty next --agent <agent> --mission <slug>         # Enter mission
 loop
   spec-kitty agent action implement <WP> --agent <name>   # Implement a work
 package
   spec-kitty agent action review    <WP> --agent <name>   # Review a work
 package

 Missions:
 - Missions are selected per-feature during /spec-kitty.specify

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   project_name      [PROJECT_NAME]  Name for your new project directory      │
│                                     (omit to initialize current directory)   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --non-interactive,--yes          Run without interactive prompts (suitable   │
│                                  for CI/CD)                                  │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Selection ──────────────────────────────────────────────────────────────────╮
│ --ai        TEXT  Comma-separated AI assistants (claude,codex,gemini,...)    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty intake

```
 Usage: spec-kitty intake [OPTIONS] [PATH]

 Ingest a plan document as a mission brief for /spec-kitty.specify.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   path      [PATH]  Path to plan document, or '-' to read from stdin. Omit   │
│                     when using --show or --auto.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force          Overwrite existing brief.                                   │
│ --show           Print current brief and provenance; no writes.              │
│ --auto           Scan known harness plan locations and ingest automatically. │
│ --help           Show this message and exit.                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty invocations

_Query local invocation records._

```
 Usage: spec-kitty invocations [OPTIONS] COMMAND [ARGS]...

 Query local invocation records.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list  List recent invocation records from the local audit log.               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty invocations list

```
 Usage: spec-kitty invocations list [OPTIONS]

 List recent invocation records from the local audit log.

 # FR-008 / T031: This command does not open an InvocationRecord at baseline.
 # If a future version of `invocations list` opens an invocation, it should
 use:
 #   derive_mode("invocations.list")  -> ModeOfWork.QUERY
 # The mapping is reserved in _ENTRY_COMMAND_MODE (modes.py) for enforcement
 # consistency (QUERY mode disallows Tier 2 evidence promotion per FR-009).
 # TODO(future): wire derive_mode("invocations.list") when InvocationRecord is
 opened here.

 Records are returned newest-first, sorted by ``started_at`` from file
 content.  Use ``--profile`` to narrow to one agent profile.  Use
 ``--json`` for machine-readable output.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --profile  -p      TEXT     Filter by profile ID (reads file content, not    │
│                             filename)                                        │
│ --limit    -n      INTEGER  Maximum number of records to return (default:    │
│                             20)                                              │
│                             [default: 20]                                    │
│ --json                      Emit a JSON array instead of a table             │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty issue-search

_Search tracker issues via the hosted read path_

```
 Usage: spec-kitty issue-search [OPTIONS]

 Search tracker issues via the hosted read path

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --provider        TEXT  Tracker provider slug [required]                  │
│ *  --query           TEXT  Issue identifier or search text [required]        │
│    --json                  Render tickets as a JSON array                    │
│    --help                  Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty lint

```
 Usage: spec-kitty lint [OPTIONS] [FILE_PATH]

 Run ruff and mypy on a file and report errors.

 This command is designed to be used as a post-edit hook for AI agents,
 providing immediate feedback on linting and type-checking violations.
 When invoked without a path (the wired hook form), the target file is read
 from the harness JSON payload on stdin.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   file_path      [FILE_PATH]  File to lint/type-check; omit to read the path │
│                               from a hook stdin payload                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output in JSON format for AI agents                          │
│ --fix           Attempt to automatically fix lint errors                     │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty materialize

```
 Usage: spec-kitty materialize [OPTIONS]

 Regenerate all derived views from the canonical event log.

 For each feature (or a single feature when --mission is given),
 writes the following files to ``.kittify/derived/<slug>/``:

 - ``status.json`` — full StatusSnapshot
 - ``board-summary.json`` — lane counts and WP lists
 - ``progress.json`` — lane-weighted progress percentage
 - ``lifecycle.json`` — canonical active/recent/stale/abandoned mission state

 Examples::

     spec-kitty materialize
     spec-kitty materialize --mission 034-my-feature
     spec-kitty materialize --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug to materialise (all if omitted)          │
│ --json                 Output a machine-readable JSON summary                │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty merge

```
 Usage: spec-kitty merge [OPTIONS]

 Merge a lane-based feature into its target branch.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --strategy                                [merge|squash|r  Merge strategy    │
│                                           ebase]           for               │
│                                                            mission→target    │
│                                                            step: merge |     │
│                                                            squash | rebase.  │
│                                                            Default: squash.  │
│ --delete-branch        --keep-branch                       Delete lane       │
│                                                            branches after    │
│                                                            merge             │
│                                                            [default:         │
│                                                            delete-branch]    │
│ --remove-worktree      --keep-worktree                     Remove lane       │
│                                                            worktrees after   │
│                                                            merge             │
│                                                            [default:         │
│                                                            remove-worktree]  │
│ --push                                                     Push to origin    │
│                                                            after merge       │
│ --target                                  TEXT             Target branch to  │
│                                                            merge into        │
│                                                            (auto-detected)   │
│ --dry-run                                                  Show what would   │
│                                                            be done without   │
│                                                            executing         │
│ --json                                                     Output            │
│                                                            deterministic     │
│                                                            JSON (dry-run     │
│                                                            mode)             │
│ --mission                                 TEXT             Mission slug when │
│                                                            merging from main │
│                                                            branch            │
│ --resume                                                   Resume an         │
│                                                            interrupted merge │
│                                                            from the last     │
│                                                            incomplete WP     │
│ --abort                                                    Abort an          │
│                                                            in-progress       │
│                                                            merge, cleaning   │
│                                                            up state and      │
│                                                            worktrees         │
│ --context                                 TEXT             Unused            │
│                                                            compatibility     │
│                                                            flag              │
│ --keep-workspace                                           Unused            │
│                                                            compatibility     │
│                                                            flag              │
│ --allow-sparse-c…                                          Proceed even if   │
│                                                            legacy            │
│                                                            sparse-checkout   │
│                                                            state is          │
│                                                            detected. Use of  │
│                                                            this override is  │
│                                                            logged. Does not  │
│                                                            bypass the        │
│                                                            commit-time       │
│                                                            data-loss         │
│                                                            backstop.         │
│ --yes              -y                                      Proceed after     │
│                                                            merge warnings    │
│                                                            without prompts   │
│ --help                                                     Show this message │
│                                                            and exit.         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty migrate

_Migration commands: update .kittify/ layout and backfill identity fields in legacy missions._

```
 Usage: spec-kitty migrate [OPTIONS] COMMAND [ARGS]...

 Migration commands: update .kittify/ layout and backfill identity fields in
 legacy missions.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dry-run            Show what would change without modifying the filesystem │
│ --verbose  -v        Show file-by-file detail                                │
│ --force              Skip confirmation prompt                                │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ backfill-identity    Write a ULID mission_id into any meta.json that lacks   │
│                      one.                                                    │
│ backfill-topology    Persist each legacy mission's MissionTopology into its  │
│                      meta.json.                                              │
│ charter-encoding     Scan charter content for non-UTF-8 encodings;           │
│                      normalize-or-fail-loud.                                 │
│ normalize-lifecycle  Normalize legacy ``kitty-specs`` missions for the MVP   │
│                      lifecycle model.                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty migrate backfill-identity

```
 Usage: spec-kitty migrate backfill-identity [OPTIONS]

 Write a ULID mission_id into any meta.json that lacks one.

 This command is **idempotent** — running it twice produces identical
 state.  Existing ``mission_id`` values are never overwritten.  The
 command also coerces legacy string-typed ``mission_number`` values
 (e.g. ``"042"`` → ``42``) while walking each mission.

 After writing, the dossier parity hash is recomputed for every mission
 that was modified.  Individual dossier failures are logged as warnings
 and do not abort the run.

 **When to run:**

 - After upgrading from a spec-kitty version that predates ``mission_id``
 - After pulling a clone that has legacy missions (no ``mission_id``)
 - As part of CI checks on legacy repositories

 Exit codes:

 - ``0`` — all results are ``wrote`` or ``skip``
 - ``1`` — one or more ``error`` results (corrupt JSON, sentinel strings, …)

 Examples:

     spec-kitty migrate backfill-identity --dry-run --json

     spec-kitty migrate backfill-identity --mission 083-foo-bar

     spec-kitty migrate backfill-identity

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                 Emit per-mission result list as structured JSON       │
│ --dry-run              Report what would change without writing any files.   │
│                        The JSON shape is identical to a live run.            │
│ --mission        SLUG  Scope to a single mission slug (e.g. 083-foo-bar).    │
│                        Omit to process all.                                  │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty migrate backfill-topology

```
 Usage: spec-kitty migrate backfill-topology [OPTIONS]

 Persist each legacy mission's MissionTopology into its meta.json.

 Computes every mission's topology (the coordination × lanes grid cell) from
 its current on-disk signals via the single WP01 classifier and writes it to
 ``meta.json`` as the authoritative ``topology`` value. This command is
 **idempotent** — a mission that already has a valid ``topology`` is skipped
 and its value is never overwritten.

 Exit codes:

 - ``0`` — all results are ``wrote`` or ``skip``
 - ``1`` — one or more ``error`` results (corrupt / unreadable meta.json)

 Examples:

     spec-kitty migrate backfill-topology --dry-run --json

     spec-kitty migrate backfill-topology --mission 083-foo-bar

     spec-kitty migrate backfill-topology

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                 Emit per-mission result list as structured JSON       │
│ --dry-run              Report what would change without writing any files.   │
│                        The JSON shape is identical to a live run.            │
│ --mission        SLUG  Scope to a single mission slug (e.g. 083-foo-bar).    │
│                        Omit to process all.                                  │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty migrate charter-encoding

```
 Usage: spec-kitty migrate charter-encoding [OPTIONS]

 Scan charter content for non-UTF-8 encodings; normalize-or-fail-loud.

 Walks every existing mission's charter content
 (``kitty-specs/*/charter/*.{yaml,md,txt}``) and the global charter store
 (``.kittify/charter/*.{yaml,md,txt}``), detects the encoding of each file
 via the WP06 chokepoint, and either:

 \b
 * **skips** the file (already pure UTF-8; idempotency pre-check passes)
 * **normalizes** the file to UTF-8 in-place with a provenance record
 * **surfaces** the file as ambiguous (exits non-zero; manual repair required)

 This migration is **idempotent** (NFR-006): running it twice on an
 already-normalized corpus is a near-instant no-op — no new provenance
 records are written for already-UTF-8 files.

 Implements FR-026, FR-027, NFR-006.

 Exit codes:

 - ``0`` — corpus is fully UTF-8 compliant (all files already-UTF-8 or
   successfully normalized)
 - ``1`` — one or more files are ambiguous (manual repair required)

 Examples:

     spec-kitty migrate charter-encoding --dry-run

     spec-kitty migrate charter-encoding --yes --json

     spec-kitty migrate charter-encoding

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dry-run                    Show what would change without writing any      │
│                              files.  Returns exit 0 unless ambiguous files   │
│                              are found.                                      │
│ --yes           -y           Apply normalizations without prompting.  Exits  │
│                              non-zero if any file is ambiguous (CI-safe).    │
│                              Do NOT pass --yes to silently bypass ambiguous  │
│                              files — manual repair is required for those.    │
│ --json                       Emit a JSON-stable summary report on stdout.    │
│ --project-root          DIR  Root of the Spec Kitty project (default:        │
│                              current working directory).                     │
│                              [default: .]                                    │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty migrate normalize-lifecycle

```
 Usage: spec-kitty migrate normalize-lifecycle [OPTIONS]

 Normalize legacy ``kitty-specs`` missions for the MVP lifecycle model.

 This command repairs enough historical mission state to make the canonical
 lifecycle model reliable across old repositories. It backfills identity
 where needed, rebuilds missing event logs from legacy state, and regenerates
 status/progress/lifecycle projections used by the CLI and Teamspace.

 Exit codes:

 - ``0`` — all targeted missions normalized or skipped cleanly
 - ``1`` — one or more missions hit an unrecoverable error

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                 Emit a structured per-mission normalization report    │
│ --dry-run              Preview lifecycle normalization without modifying the │
│                        filesystem                                            │
│ --mission        SLUG  Scope to a single mission slug (e.g. 083-foo-bar).    │
│                        Omit to process all.                                  │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission

_Inspect mission types for this project._

```
 Usage: spec-kitty mission [OPTIONS] COMMAND [ARGS]...

 Inspect mission types for this project.

 Use 'list' to see activated types (charter-filtered) and 'show <id>' for a
 full resolved definition.

 Mission types are selected per mission run during /spec-kitty.specify.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list       List activated mission types for the current                      │
│            project (FR-016).                                                 │
│ current    Show currently active mission for a mission                       │
│            (auto-detects mission from cwd).                                  │
│ info       Show details for a specific mission without                       │
│            switching.                                                        │
│ create     Fetch a tracker ticket and prepare it as a mission                │
│            brief.                                                            │
│ run        Start (or attach to) a runtime for a                              │
│            project-authored custom mission definition.                       │
│ close      Close a mission. Wraps FR-016 lifecycle teardown.                 │
│ reopen     Re-open a merged/closed mission, returning it to                  │
│            an actionable state (FR-002).                                     │
│ follow-up  Record a follow-up commit or PR against a mission                 │
│            (FR-001).                                                         │
│ switch     [REMOVED] Switch active mission - this command was  (deprecated)  │
│            removed in v0.8.0.                                                │
│ show       Show the fully resolved MissionType definition for                │
│            this project (FR-017).                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission close

```
 Usage: spec-kitty mission close [OPTIONS]

 Close a mission. Wraps FR-016 lifecycle teardown.

 Without ``--discard``: run the merge-completion teardown — persist the
 mission retrospective to its durable home and tear down the coordination
 worktree. Idempotent after a successful ``spec-kitty merge`` (which already
 ran the same teardown); useful when the teardown was skipped (e.g. the legacy
 plain-git/GitHub merge path) or interrupted. NOTE: on a mission that was
 merged without a retrospective, this generates one
 (``kitty-specs/<slug>/retrospective.yaml``) plus a ``RetrospectiveCaptured``
 event and commits both — it is not a pure no-op in that case.

 With ``--discard``: abandon the mission mid-flight. Deletes the
 coordination branch and every lane branch named in
 ``lanes.json``, then tears down the coordination worktree and the
 operator-visible lane worktrees. Requires confirmation unless
 ``--force`` is also passed. The coordination + lane branches are
 deleted with ``git branch -D`` (force-delete) because mid-flight
 abandonment by definition leaves uncommitted or unmerged work.

 Implements FR-016 from
 ``kitty-specs/mission-coordination-branch-atomic-event-log-01KSPTVW``.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission  -f      TEXT  Mission slug (auto-detected from cwd if omitted)    │
│ --discard                Discard the mission mid-flight: delete the          │
│                          coordination branch + all lane branches and tear    │
│                          down all worktrees. Without --discard, requires     │
│                          that the mission has already been merged (no-op     │
│                          cleanup otherwise).                                 │
│ --force                  Skip the confirmation prompt when --discard is set. │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission create

```
 Usage: spec-kitty mission create [OPTIONS]

 Fetch a tracker ticket and prepare it as a mission brief.

 Writes the ticket content to .kittify/ticket-context.md so the LLM can
 read it and run /spec-kitty.specify. Records a pending origin so the
 mission-to-ticket link is established automatically when specify completes.

 Example:
     spec-kitty mission create --from-ticket linear:PRI-42

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --from-ticket        TEXT  Tracker ticket reference in provider:KEY       │
│                               format (e.g. linear:PRI-42)                    │
│                               [required]                                     │
│    --help                     Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission current

```
 Usage: spec-kitty mission current [OPTIONS]

 Show currently active mission for a mission (auto-detects mission from cwd).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission  -f      TEXT  Mission slug                                        │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission follow-up

```
 Usage: spec-kitty mission follow-up [OPTIONS] HANDLE

 Record a follow-up commit or PR against a mission (FR-001).

 Exactly one of ``--commit <40-hex>`` / ``--pr <int>`` must be supplied.
 Appends a ``FollowUpRecorded`` lifecycle event attributed to ``mission_id``.
 Fail-closed (#1926): only valid once the mission has reached completion
 (merged, or all WPs terminal) — a follow-up against a not-yet-completed
 mission exits non-zero with a structured error and writes no event.
 Idempotent on its dedup key ``(mission_id, commit_sha | pr_number)`` —
 re-recording the same reference is a successful no-op.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    handle      TEXT  Mission handle: mission_id (ULID), mid8, or slug.     │
│                        [required]                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --commit        TEXT     40-hex commit SHA of the follow-up.                 │
│ --pr            INTEGER  Pull-request number of the follow-up.               │
│ --json                   Emit a JSON envelope instead of a rich panel.       │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission info

```
 Usage: spec-kitty mission info [OPTIONS] MISSION_NAME

 Show details for a specific mission without switching.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission_name      TEXT  Mission name to display details for [required]  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission list

```
 Usage: spec-kitty mission list [OPTIONS]

 List activated mission types for the current project (FR-016).

 Alias for ``spec-kitty charter mission-type list``.

 Returns only mission types that are explicitly activated in this
 project's charter (activation-filtered).  For all doctrine-layer
 types regardless of activation, use ``spec-kitty doctrine mission-type list``.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output as JSON.                                              │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission reopen

```
 Usage: spec-kitty mission reopen [OPTIONS] HANDLE

 Re-open a merged/closed mission, returning it to an actionable state (FR-002).

 Appends a ``MissionReopened`` lifecycle event (the authority for
 actionability — ``derive_mission_lifecycle`` reports the ``reopened``
 surface_state) and clears the ``merged_*`` markers from ``meta.json``. Does
 NOT mutate WP lanes — the operator repositions WPs explicitly afterwards.

 Fail-closed (NFR-004): the mission is unrecoverable when ``meta.json`` is
 absent/corrupt OR the mission branch resolves in neither the local repo nor
 any configured remote. A missing worktree directory alone is recoverable. On
 unrecoverable input the command exits non-zero with a remediation hint and
 writes no event / no metadata change.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    handle      TEXT  Mission handle: mission_id (ULID), mid8, or slug.     │
│                        [required]                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --reason        TEXT  Why the mission is being re-opened (required,       │
│                          audited).                                           │
│                          [required]                                          │
│    --json                Emit a JSON envelope instead of a rich panel.       │
│    --help                Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission run

```
 Usage: spec-kitty mission run [OPTIONS] MISSION_KEY

 Start (or attach to) a runtime for a project-authored custom mission
 definition.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission_key      TEXT  The reusable custom mission key. [required]      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission                 TEXT  Tracked mission slug. [required]          │
│    --json       --no-json          Emit JSON envelope to stdout instead of a │
│                                    rich panel.                               │
│                                    [default: no-json]                        │
│    --help                          Show this message and exit.               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission show

```
 Usage: spec-kitty mission show [OPTIONS] MISSION_TYPE_ID

 Show the fully resolved MissionType definition for this project (FR-017).

 Displays all fields of the activated mission type:
 id, display_name, action_sequence, governance_refs, template_set,
 source_layer, extends.

 Exits with code 1 and lists registered IDs when ``mission_type_id``
 is not an activated type.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission_type_id      TEXT  Mission type ID (e.g. software-dev).         │
│                                 [required]                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output as JSON.                                              │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission switch

> **Deprecated**: this command is deprecated

```
 Usage: spec-kitty mission switch [OPTIONS] MISSION_NAME

 (deprecated)
 [REMOVED] Switch active mission - this command was removed in v0.8.0.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission_name      TEXT  Mission name (no longer supported) [required]   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force          (ignored)                                                   │
│ --help           Show this message and exit.                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type

_Inspect mission types for this project._

```
 Usage: spec-kitty mission-type [OPTIONS] COMMAND [ARGS]...

 Inspect mission types for this project.

 Use 'list' to see activated types (charter-filtered) and 'show <id>' for a
 full resolved definition.

 Mission types are selected per mission run during /spec-kitty.specify.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list       List activated mission types for the current                      │
│            project (FR-016).                                                 │
│ current    Show currently active mission for a mission                       │
│            (auto-detects mission from cwd).                                  │
│ info       Show details for a specific mission without                       │
│            switching.                                                        │
│ create     Fetch a tracker ticket and prepare it as a mission                │
│            brief.                                                            │
│ run        Start (or attach to) a runtime for a                              │
│            project-authored custom mission definition.                       │
│ close      Close a mission. Wraps FR-016 lifecycle teardown.                 │
│ reopen     Re-open a merged/closed mission, returning it to                  │
│            an actionable state (FR-002).                                     │
│ follow-up  Record a follow-up commit or PR against a mission                 │
│            (FR-001).                                                         │
│ switch     [REMOVED] Switch active mission - this command was  (deprecated)  │
│            removed in v0.8.0.                                                │
│ show       Show the fully resolved MissionType definition for                │
│            this project (FR-017).                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type close

```
 Usage: spec-kitty mission-type close [OPTIONS]

 Close a mission. Wraps FR-016 lifecycle teardown.

 Without ``--discard``: run the merge-completion teardown — persist the
 mission retrospective to its durable home and tear down the coordination
 worktree. Idempotent after a successful ``spec-kitty merge`` (which already
 ran the same teardown); useful when the teardown was skipped (e.g. the legacy
 plain-git/GitHub merge path) or interrupted. NOTE: on a mission that was
 merged without a retrospective, this generates one
 (``kitty-specs/<slug>/retrospective.yaml``) plus a ``RetrospectiveCaptured``
 event and commits both — it is not a pure no-op in that case.

 With ``--discard``: abandon the mission mid-flight. Deletes the
 coordination branch and every lane branch named in
 ``lanes.json``, then tears down the coordination worktree and the
 operator-visible lane worktrees. Requires confirmation unless
 ``--force`` is also passed. The coordination + lane branches are
 deleted with ``git branch -D`` (force-delete) because mid-flight
 abandonment by definition leaves uncommitted or unmerged work.

 Implements FR-016 from
 ``kitty-specs/mission-coordination-branch-atomic-event-log-01KSPTVW``.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission  -f      TEXT  Mission slug (auto-detected from cwd if omitted)    │
│ --discard                Discard the mission mid-flight: delete the          │
│                          coordination branch + all lane branches and tear    │
│                          down all worktrees. Without --discard, requires     │
│                          that the mission has already been merged (no-op     │
│                          cleanup otherwise).                                 │
│ --force                  Skip the confirmation prompt when --discard is set. │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type create

```
 Usage: spec-kitty mission-type create [OPTIONS]

 Fetch a tracker ticket and prepare it as a mission brief.

 Writes the ticket content to .kittify/ticket-context.md so the LLM can
 read it and run /spec-kitty.specify. Records a pending origin so the
 mission-to-ticket link is established automatically when specify completes.

 Example:
     spec-kitty mission create --from-ticket linear:PRI-42

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --from-ticket        TEXT  Tracker ticket reference in provider:KEY       │
│                               format (e.g. linear:PRI-42)                    │
│                               [required]                                     │
│    --help                     Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type current

```
 Usage: spec-kitty mission-type current [OPTIONS]

 Show currently active mission for a mission (auto-detects mission from cwd).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission  -f      TEXT  Mission slug                                        │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type follow-up

```
 Usage: spec-kitty mission-type follow-up [OPTIONS] HANDLE

 Record a follow-up commit or PR against a mission (FR-001).

 Exactly one of ``--commit <40-hex>`` / ``--pr <int>`` must be supplied.
 Appends a ``FollowUpRecorded`` lifecycle event attributed to ``mission_id``.
 Fail-closed (#1926): only valid once the mission has reached completion
 (merged, or all WPs terminal) — a follow-up against a not-yet-completed
 mission exits non-zero with a structured error and writes no event.
 Idempotent on its dedup key ``(mission_id, commit_sha | pr_number)`` —
 re-recording the same reference is a successful no-op.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    handle      TEXT  Mission handle: mission_id (ULID), mid8, or slug.     │
│                        [required]                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --commit        TEXT     40-hex commit SHA of the follow-up.                 │
│ --pr            INTEGER  Pull-request number of the follow-up.               │
│ --json                   Emit a JSON envelope instead of a rich panel.       │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type info

```
 Usage: spec-kitty mission-type info [OPTIONS] MISSION_NAME

 Show details for a specific mission without switching.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission_name      TEXT  Mission name to display details for [required]  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type list

```
 Usage: spec-kitty mission-type list [OPTIONS]

 List activated mission types for the current project (FR-016).

 Alias for ``spec-kitty charter mission-type list``.

 Returns only mission types that are explicitly activated in this
 project's charter (activation-filtered).  For all doctrine-layer
 types regardless of activation, use ``spec-kitty doctrine mission-type list``.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output as JSON.                                              │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type reopen

```
 Usage: spec-kitty mission-type reopen [OPTIONS] HANDLE

 Re-open a merged/closed mission, returning it to an actionable state (FR-002).

 Appends a ``MissionReopened`` lifecycle event (the authority for
 actionability — ``derive_mission_lifecycle`` reports the ``reopened``
 surface_state) and clears the ``merged_*`` markers from ``meta.json``. Does
 NOT mutate WP lanes — the operator repositions WPs explicitly afterwards.

 Fail-closed (NFR-004): the mission is unrecoverable when ``meta.json`` is
 absent/corrupt OR the mission branch resolves in neither the local repo nor
 any configured remote. A missing worktree directory alone is recoverable. On
 unrecoverable input the command exits non-zero with a remediation hint and
 writes no event / no metadata change.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    handle      TEXT  Mission handle: mission_id (ULID), mid8, or slug.     │
│                        [required]                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --reason        TEXT  Why the mission is being re-opened (required,       │
│                          audited).                                           │
│                          [required]                                          │
│    --json                Emit a JSON envelope instead of a rich panel.       │
│    --help                Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type run

```
 Usage: spec-kitty mission-type run [OPTIONS] MISSION_KEY

 Start (or attach to) a runtime for a project-authored custom mission
 definition.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission_key      TEXT  The reusable custom mission key. [required]      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission                 TEXT  Tracked mission slug. [required]          │
│    --json       --no-json          Emit JSON envelope to stdout instead of a │
│                                    rich panel.                               │
│                                    [default: no-json]                        │
│    --help                          Show this message and exit.               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type show

```
 Usage: spec-kitty mission-type show [OPTIONS] MISSION_TYPE_ID

 Show the fully resolved MissionType definition for this project (FR-017).

 Displays all fields of the activated mission type:
 id, display_name, action_sequence, governance_refs, template_set,
 source_layer, extends.

 Exits with code 1 and lists registered IDs when ``mission_type_id``
 is not an activated type.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission_type_id      TEXT  Mission type ID (e.g. software-dev).         │
│                                 [required]                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output as JSON.                                              │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty mission-type switch

> **Deprecated**: this command is deprecated

```
 Usage: spec-kitty mission-type switch [OPTIONS] MISSION_NAME

 (deprecated)
 [REMOVED] Switch active mission - this command was removed in v0.8.0.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission_name      TEXT  Mission name (no longer supported) [required]   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force          (ignored)                                                   │
│ --help           Show this message and exit.                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty next

```
 Usage: spec-kitty next [OPTIONS]

 Decide and emit the next agent action for the current mission.

 Agents call this command repeatedly in a loop.  The system inspects the
 mission state machine, evaluates guards, and returns a deterministic
 decision with an action and prompt file.

 Examples:
     spec-kitty next --mission 034-my-feature --json
 # query mode
     spec-kitty next --agent claude --mission 034-my-feature --result success
 --json
     spec-kitty next --agent codex --mission 034-my-feature
     spec-kitty next --agent gemini --mission 034-my-feature --result failed
 --json
     spec-kitty next --agent claude --mission 034-my-feature --answer "yes"
 --result success --json
     spec-kitty next --agent claude --mission 034-my-feature --answer "approve"
 --decision-id "input:review" --result success --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --agent              TEXT  Agent name (required for advancing mode)          │
│ --result             TEXT  Result of previous step: success|failed|blocked.  │
│                            If omitted, returns current state without         │
│                            advancing (query mode).                           │
│ --mission            TEXT  Mission slug                                      │
│ --json                     Output JSON decision only                         │
│ --answer             TEXT  Answer to a pending decision                      │
│ --decision-id        TEXT  Decision ID (required if multiple pending)        │
│ --help                     Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty ops

_Operation history (git reflog)_

```
 Usage: spec-kitty ops [OPTIONS] COMMAND [ARGS]...

 Operation history (git reflog)

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ log   Show operation history.                                                │
│ undo  Undo is not supported for git.                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty ops log

```
 Usage: spec-kitty ops log [OPTIONS]

 Show operation history.

 Shows the git reflog (read-only history).

 Examples:
     # Show recent operations
     spec-kitty ops log

     # Show last 5 operations
     spec-kitty ops log --limit 5

     # Show with full details
     spec-kitty ops log --verbose

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --limit    -n      INTEGER  Number of operations to show [default: 20]       │
│ --verbose  -v               Show full operation IDs and details              │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty ops undo

```
 Usage: spec-kitty ops undo [OPTIONS]

 Undo is not supported for git.

 Git does not have reversible operation history.
 Consider using these alternatives manually:
   - git reset --soft HEAD~1  (undo last commit, keep changes)
   - git reset --hard HEAD~1  (undo last commit, discard changes)
   - git revert <commit>      (create reverting commit)
   - git reflog               (find previous states)

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api

_Machine-contract API for external orchestrators (JSON-first)_

```
 Usage: spec-kitty orchestrator-api [OPTIONS] COMMAND [ARGS]...

 Machine-contract API for external orchestrators (JSON-first)

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ contract-version      Return the current API contract version.               │
│ mission-state         Return the full state of a mission (all WPs, lanes,    │
│                       dependencies).                                         │
│ list-ready            List WPs that are ready to start (planned and all deps │
│                       approved or done).                                     │
│ resolve-workspace     Read-only: resolve a WP's lane workspace_path +        │
│                       prompt_path (+ lane fields).                           │
│ start-implementation  Composite transition: planned->claimed->in_progress    │
│                       (idempotent).                                          │
│ start-review          Transition a WP from for_review to in_review (reviewer │
│                       claims review).                                        │
│ transition            Emit a single lane transition for a WP.                │
│ append-history        Append a history entry to a WP prompt file.            │
│ accept-mission        Accept a mission after all WPs are approved or done.   │
│ merge-mission         Merge a lane-based mission into target.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api accept-mission

```
 Usage: spec-kitty orchestrator-api accept-mission [OPTIONS]

 Accept a mission after all WPs are approved or done.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission        TEXT  Mission slug [required]                            │
│ *  --actor          TEXT  Actor identity [required]                          │
│    --help                 Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api append-history

```
 Usage: spec-kitty orchestrator-api append-history [OPTIONS]

 Append a history entry to a WP prompt file.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission        TEXT  Mission slug [required]                            │
│ *  --wp             TEXT  Work package ID [required]                         │
│ *  --actor          TEXT  Actor identity [required]                          │
│ *  --note           TEXT  History note to append [required]                  │
│    --help                 Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api contract-version

```
 Usage: spec-kitty orchestrator-api contract-version [OPTIONS]

 Return the current API contract version.

 Pass --provider-version to check compatibility before running state-mutating
 commands.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --provider-version        TEXT  Caller's provider version; returns           │
│                                 CONTRACT_VERSION_MISMATCH if below minimum   │
│ --help                          Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api list-ready

```
 Usage: spec-kitty orchestrator-api list-ready [OPTIONS]

 List WPs that are ready to start (planned and all deps approved or done).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission        TEXT  Mission slug [required]                            │
│    --help                 Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api merge-mission

```
 Usage: spec-kitty orchestrator-api merge-mission [OPTIONS]

 Merge a lane-based mission into target.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission         TEXT  Mission slug [required]                           │
│    --target          TEXT  Target branch to merge into (auto-detected from   │
│                            meta.json)                                        │
│    --strategy        TEXT  Merge strategy: merge, squash, or rebase          │
│                            [default: merge]                                  │
│    --push                  Push target branch after merge                    │
│    --help                  Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api mission-state

```
 Usage: spec-kitty orchestrator-api mission-state [OPTIONS]

 Return the full state of a mission (all WPs, lanes, dependencies).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission        TEXT  Mission slug [required]                            │
│    --help                 Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api resolve-workspace

```
 Usage: spec-kitty orchestrator-api resolve-workspace [OPTIONS]

 Read-only: resolve a WP's lane workspace_path + prompt_path (+ lane fields).

 Does NOT allocate/create/validate-clean/transition — the read-only companion
 of ``start-implementation`` for a WP already past implementation (e.g. a
 ``for_review`` WP an external orchestrator wants to review on resume, where
 calling start-implementation would wrongly re-transition it). Contract >=
 1.2.0.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission        TEXT  Mission slug [required]                            │
│ *  --wp             TEXT  Work package ID [required]                         │
│    --help                 Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api start-implementation

```
 Usage: spec-kitty orchestrator-api start-implementation [OPTIONS]

 Composite transition: planned->claimed->in_progress (idempotent).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission        TEXT  Mission slug [required]                            │
│ *  --wp             TEXT  Work package ID [required]                         │
│ *  --actor          TEXT  Actor identity [required]                          │
│    --policy         TEXT  Policy metadata JSON (required)                    │
│    --help                 Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api start-review

```
 Usage: spec-kitty orchestrator-api start-review [OPTIONS]

 Transition a WP from for_review to in_review (reviewer claims review).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission           TEXT  Mission slug [required]                         │
│ *  --wp                TEXT  Work package ID [required]                      │
│ *  --actor             TEXT  Actor identity [required]                       │
│    --policy            TEXT  Policy metadata JSON (required)                 │
│    --review-ref        TEXT  Review feedback reference (optional, not        │
│                              required for for_review→in_review)              │
│    --help                    Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty orchestrator-api transition

```
 Usage: spec-kitty orchestrator-api transition [OPTIONS]

 Emit a single lane transition for a WP.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission                            TEXT  Mission slug [required]        │
│ *  --wp                                 TEXT  Work package ID [required]     │
│ *  --to                                 TEXT  Target lane [required]         │
│ *  --actor                              TEXT  Actor identity [required]      │
│    --note                               TEXT  Reason/note for the transition │
│    --policy                             TEXT  Policy metadata JSON (required │
│                                               for run-affecting lanes)       │
│    --force                                    Force the transition           │
│    --review-ref                         TEXT  Review reference               │
│    --evidence-json                      TEXT  JSON string with done evidence │
│    --subtasks-complete                        Whether required subtasks are  │
│                                               complete for                   │
│                                               in_progress->for_review        │
│    --implementation-evidence-pr…              Whether implementation         │
│                                               evidence exists for            │
│                                               in_progress->for_review        │
│    --help                                     Show this message and exit.    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty plan

```
 Usage: spec-kitty plan [OPTIONS]

 Scaffold plan.md for a feature.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug (e.g., 001-user-authentication)          │
│ --json                 Emit JSON result                                      │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty plugin

_Plugin bundle commands_

```
 Usage: spec-kitty plugin [OPTIONS] COMMAND [ARGS]...

 Plugin bundle commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ build  Build a Spec Kitty plugin bundle for a specific target harness.       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty plugin build

```
 Usage: spec-kitty plugin build [OPTIONS]

 Build a Spec Kitty plugin bundle for a specific target harness.

 The bundle is written to ``<output-dir>/<target>/`` and includes a
 ``plugin.json`` manifest, rendered command skills, and agent profiles.

 Example::

     spec-kitty plugin build --target claude-code
     spec-kitty plugin build --target claude-code --output-dir /tmp/out
     spec-kitty plugin build --target claude-code --skip-validate

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --target               TEXT  Plugin target (claude-code, codex).          │
│                                 [required]                                   │
│    --output-dir           PATH  Root directory under which the bundle is     │
│                                 written.                                     │
│                                 [default: dist/spec-kitty-plugins]           │
│    --skip-validate              Skip the 'claude plugin validate --strict'   │
│                                 step.                                        │
│    --help                       Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty profile-invocation

_Manage invocation records._

```
 Usage: spec-kitty profile-invocation [OPTIONS] COMMAND [ARGS]...

 Manage invocation records.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ complete  Close an open invocation record. --invocation-id and --outcome are │
│           required.                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty profile-invocation complete

```
 Usage: spec-kitty profile-invocation complete [OPTIONS]

 Close an open invocation record. --invocation-id and --outcome are required.

 Use --artifact (repeatable) to link output artifacts to this invocation.
 Use --commit (singular) to link the primary git commit produced.
 Use --evidence to promote a file to a Tier 2 evidence artifact.
 Note: --evidence is rejected for records that are not execution records.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --invocation-id  -i      TEXT  Invocation ULID to close [required]        │
│ *  --outcome                TEXT  done | failed | abandoned [required]       │
│    --evidence               TEXT  Path to evidence file (Tier 2 promotion)   │
│    --artifact               TEXT  Path (repo-relative or absolute) of an     │
│                                   artifact produced by this invocation.      │
│                                   Repeatable.                                │
│    --commit                 TEXT  Git commit SHA most directly produced by   │
│                                   this invocation. Singular.                 │
│    --json                         Output JSON payload                        │
│    --help                         Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty profiles

_Manage and list agent profiles._

```
 Usage: spec-kitty profiles [OPTIONS] COMMAND [ARGS]...

 Manage and list agent profiles.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list  List agent profiles (activated-only by default; --all for the full     │
│       catalog).                                                              │
│ show  Show the full resolved definition of an agent profile                  │
│       (FR-013/014/015).                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty profiles list

```
 Usage: spec-kitty profiles list [OPTIONS]

 List agent profiles (activated-only by default; --all for the full catalog).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                    Output JSON array.                                 │
│ --all                     Show every profile across all source layers        │
│                           (annotated by source layer and activated|available │
│                           state). Supersedes the activated-only default and  │
│                           --show-available.                                  │
│ --show-available          Also show available-but-not-activated profiles     │
│                           (annotated by state).                              │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty profiles show

```
 Usage: spec-kitty profiles show [OPTIONS] PROFILE_ID

 Show the full resolved definition of an agent profile (FR-013/014/015).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    profile_id      TEXT  Profile ID to show. [required]                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output JSON object.                                          │
│ --all           Bypass the activation gate for inspection (show              │
│                 non-activated profiles).                                     │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty research

```
 Usage: spec-kitty research [OPTIONS]

 Execute Phase 0 research workflow to scaffold artifacts.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug to target                                │
│ --force                Overwrite existing research artifacts                 │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty retrospect

_Retrospective authoring and summary (create / backfill / summary)_

```
 Usage: spec-kitty retrospect [OPTIONS] COMMAND [ARGS]...

 Retrospective authoring and summary (create / backfill / summary)

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ create    Author a retrospective for one completed mission.                  │
│ backfill  Author retrospective records for historical missions in bulk.      │
│ summary   Cross-mission retrospective summary.                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty retrospect backfill

_Author retrospective records for historical missions in bulk._

```
 Usage: spec-kitty retrospect backfill [OPTIONS]

 Author retrospective records for historical missions in bulk.

 Iterates completed missions in the given time window and authors
 retrospective.yaml records for those that don't already have one.

 Per-mission failures are NOT fatal; aggregate report shows them.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --since                TEXT  Only consider missions completed on or after    │
│                              this ISO date (default: 30 days ago)            │
│ --until                TEXT  Only consider missions completed on or before   │
│                              this ISO date (default: now)                    │
│ --mission              TEXT  Restrict backfill to a single mission handle    │
│ --dry-run                    Report what would be authored without writing   │
│ --emit-skipped               Append a RetrospectiveSkipped event for skipped │
│                              missions                                        │
│ --emit-failures              Append RetrospectiveCaptureFailed events for    │
│                              failed missions                                 │
│ --json                       Emit a single aggregate JSON object at the end  │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty retrospect create

_Author a retrospective for one completed mission._

```
 Usage: spec-kitty retrospect create [OPTIONS]

 Author a retrospective for one completed mission.

 Validates mission completion, resolves policy, runs the generator,
 and writes the record. Use --overwrite or --update to handle existing records.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --mission          TEXT  Mission handle (mission_id, mid8, or             │
│                             mission_slug)                                    │
│                             [required]                                       │
│    --overwrite              Replace an existing record (mutually exclusive   │
│                             with --update)                                   │
│    --update                 Merge into an existing record (mutually          │
│                             exclusive with --overwrite)                      │
│    --json                   Emit structured JSON output instead of Rich      │
│                             rendering                                        │
│    --help                   Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty retrospect summary

_Cross-mission retrospective summary._

```
 Usage: spec-kitty retrospect summary [OPTIONS]

 Cross-mission retrospective summary.

 Reads kitty-specs/*/retrospective.yaml and kitty-specs/*/status.events.jsonl
 to produce a cross-mission view.

 Distinguishes four record states: has_findings / ran_no_findings / missing /
 failed.

 No mutation is performed.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --project                  PATH                     Project root (default:   │
│                                                     current working          │
│                                                     directory)               │
│ --json                                              Emit JSON to stdout      │
│                                                     instead of Rich          │
│                                                     rendering                │
│ --json-out                 PATH                     Also write JSON to this  │
│                                                     file path                │
│ --limit                    INTEGER RANGE            Top-N for ranked         │
│                            [1<=x<=100]              sections (default: 20)   │
│                                                     [default: 20]            │
│ --since                    TEXT                     ISO-8601 date; only      │
│                                                     include missions started │
│                                                     on or after DATE         │
│ --include-malformed                                 Include malformed record │
│                                                     detail in output         │
│ --filter                   TEXT                     Only show missions in    │
│                                                     this record state        │
│                                                     (has_findings|ran_no_fi… │
│ --help                                              Show this message and    │
│                                                     exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty review

```
 Usage: spec-kitty review [OPTIONS]

 Validate a merged mission: WP lane check, dead-code scan, BLE001 audit.

 Writes kitty-specs/<slug>/mission-review-report.md with a machine-readable
 verdict.  See module docstring for known false-positive scenarios in the
 dead-code scan step.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission handle (id, mid8, or slug).                   │
│ --mode           TEXT  Review mode: 'lightweight' (consistency check only)   │
│                        or 'post-merge' (full release-gate contract).         │
│                        Auto-detected from meta.json.baseline_merge_commit    │
│                        when omitted.                                         │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty safe-commit

```
 Usage: spec-kitty safe-commit [OPTIONS] FILES...

 Commit only the requested files via Spec Kitty's safe-commit path.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    files      FILES...  Files or directories to commit, relative to the    │
│                           current worktree root or absolute. Directory       │
│                           arguments expand to their contained                │
│                           changed/untracked files with an explicit expansion │
│                           report.                                            │
│                           [required]                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --message    -m      TEXT  Commit message. [required]                     │
│    --to-branch          TEXT  Short branch name the commit must land on. The │
│                               helper asserts HEAD matches this branch before │
│                               staging. When omitted, the current HEAD branch │
│                               is used (deprecated; --to-branch becomes       │
│                               required in v3.3). This is the only            │
│                               destination authority — no env-var inference.  │
│    --json                     Output JSON                                    │
│    --help                     Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty session-start

_Emit spec-kitty orientation for the Claude Code SessionStart hook._

```
 Usage: spec-kitty session-start [OPTIONS]

 Emit spec-kitty orientation for the Claude Code SessionStart hook.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty session-stop

_Emit the open-Ops reminder for the Claude Code Stop hook._

```
 Usage: spec-kitty session-stop [OPTIONS]

 Emit the open-Ops reminder for the Claude Code Stop hook.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty spec-commit

```
 Usage: spec-kitty spec-commit [OPTIONS] FILES...

 Commit spec artifacts to the mission's resolved placement.

 On a protected primary the coordination worktree is materialised on demand
 so the commit lands on the coordination branch (materialize-then-retry).
 On an unprotected or flattened primary the commit is direct.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    files      FILES...  Spec artifacts to commit (absolute or relative     │
│                           paths). Must belong to the mission resolved via    │
│                           --mission or the kitty-specs/<slug>/ path.         │
│                           [required]                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --message        -m      TEXT  Commit message. [required]                 │
│    --mission                TEXT  Mission slug (e.g. '001-my-mission'). When │
│                                   omitted, the slug is derived from the      │
│                                   first file argument's kitty-specs/<slug>/  │
│                                   path.                                      │
│    --target-branch          TEXT  Short primary branch name used for the     │
│                                   post-commit ff-advance (WP09 / FR-010).    │
│                                   Optional.                                  │
│    --json                         Output JSON.                               │
│    --help                         Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty specify

```
 Usage: spec-kitty specify [OPTIONS] MISSION

 Create a feature scaffold in kitty-specs/.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    mission      TEXT  Mission name or slug (e.g., user-authentication)     │
│                         [required]                                           │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission-type        TEXT                        Mission type (e.g.,        │
│                                                   software-dev, research)    │
│ --topology            [single_branch|lanes|coord  Create-time mission shape: │
│                       |lanes_with_coord]          single_branch | lanes |    │
│                                                   coord | lanes_with_coord.  │
│                                                   Coordination-bearing       │
│                                                   shapes (coord,             │
│                                                   lanes_with_coord) mint a   │
│                                                   coordination branch;       │
│                                                   branch-flat shapes         │
│                                                   (single_branch, lanes) do  │
│                                                   not. Default: coord.       │
│                                                   [default: coord]           │
│ --json                                            Emit JSON result           │
│ --help                                            Show this message and      │
│                                                   exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync

_Synchronization commands_

```
 Usage: spec-kitty sync [OPTIONS] COMMAND [ARGS]...

 Synchronization commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ routes     Show where the current checkout sends data and which teams it is  │
│            shared with.                                                      │
│ share      Share the current repository from Private Teamspace into a team.  │
│ unshare    Stop sharing the current repository from this developer to one    │
│            team.                                                             │
│ opt-out    Disable SaaS sync for this checkout and purge its pending         │
│            uploads.                                                          │
│ opt-in     Enable SaaS sync for this checkout.                               │
│ workspace  Synchronize workspace with upstream changes.                      │
│ server     Show or set sync server URL.                                      │
│ now        Trigger immediate sync of all queued events.                      │
│ gc         Purge event payloads delivered to all known targets (explicit,    │
│            destructive).                                                     │
│ archive    Archive retained event payloads (explicit, non-destructive).      │
│ migrate    Migrate legacy hash-scoped queue DBs into the append-only event   │
│            journal.                                                          │
│ mode       Show or set the event-sync retention x delivery mode.             │
│ status     Show sync queue status, connection state, and auth info.          │
│ diagnose   Validate queued events locally against the event schema.          │
│ doctor     Diagnose sync health: queue, auth, and server connectivity.       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync archive

```
 Usage: spec-kitty sync archive [OPTIONS]

 Archive retained event payloads (explicit, non-destructive).

 Stamps the journal's archive marker so events move off the live retained
 surface without deleting bytes. Idempotent and never touches the delivery
 ledger (FR-010). Runs only on this explicit invocation.

 Examples:
     spec-kitty sync archive

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync diagnose

```
 Usage: spec-kitty sync diagnose [OPTIONS]

 Validate queued events locally against the event schema.

 Reads all pending events from the offline queue and validates each one
 against the Pydantic Event model and per-event-type payload rules.

 Valid events are reported as passing; malformed events show specific
 field errors grouped by error category.

 Examples:
     spec-kitty sync diagnose
     spec-kitty sync diagnose --json

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Output results as JSON instead of Rich table                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync doctor

```
 Usage: spec-kitty sync doctor [OPTIONS]

 Diagnose sync health: queue, auth, and server connectivity.

 Runs a comprehensive check of offline queue state, authentication
 validity, and server reachability, printing actionable remediation
 steps for any issues found.

 Examples:
     spec-kitty sync doctor

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync gc

```
 Usage: spec-kitty sync gc [OPTIONS]

 Purge event payloads delivered to all known targets (explicit, destructive).

 Deletes journal payload rows only for events with a terminal-success
 delivery to **every** registered target; payloads still owed to any known
 target are kept so the durable, re-drainable copy is never lost (FR-005).
 The delivery ledger is never touched, so delivery history survives (FR-010).
 Runs only on this explicit invocation — never from ``sync now``.

 Examples:
     spec-kitty sync gc

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync migrate

```
 Usage: spec-kitty sync migrate [OPTIONS]

 Migrate legacy hash-scoped queue DBs into the append-only event journal.

 Lifts every currently-queued payload from the legacy ``queue.db`` and each
 scoped ``queues/queue-<digest>.db`` into the WP03 event journal, recording
 per-source provenance and quarantining divergent-duplicate collisions into
 the migration-audit store. Source DBs are opened read-only and are never
 modified. Exits non-zero when an unresolved conflict blocks cleanup (SC-011).

 Examples:
     spec-kitty sync migrate

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync mode

```
 Usage: spec-kitty sync mode [OPTIONS] [NAME]

 Show or set the event-sync retention x delivery mode.

 With no argument, prints the current mode. Mode semantics (which receiver,
 whether the journal retains) are owned by the policy layer; the CLI only
 routes the operator token through it (FR-006).

 Examples:
     spec-kitty sync mode
     spec-kitty sync mode LOCAL_RETENTION
     spec-kitty sync mode EXTERNAL_RECEIVER --endpoint
 https://receiver.example/events

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   name      [NAME]  Mode to set: TEAMSPACE | EXTERNAL_RECEIVER |             │
│                     LOCAL_RETENTION | OPT_OUT                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --endpoint        TEXT  External receiver endpoint URL (required for         │
│                         EXTERNAL_RECEIVER)                                   │
│ --help                  Show this message and exit.                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync now

```
 Usage: spec-kitty sync now [OPTIONS]

 Trigger immediate sync of all queued events.

 Drains the offline queue completely, uploading events to the server
 in batches of 1000 until the queue is empty or all remaining events
 have exceeded their retry limit.

 Examples:
     spec-kitty sync now
     spec-kitty sync now --report failures.json
     spec-kitty sync now --no-strict

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --report                   PATH  Export per-event failure details to a JSON  │
│                                  file                                        │
│ --strict    --no-strict          Exit non-zero on sync errors (default:      │
│                                  strict)                                     │
│                                  [default: strict]                           │
│ --help                           Show this message and exit.                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync opt-in

```
 Usage: spec-kitty sync opt-in [OPTIONS]

 Enable SaaS sync for this checkout.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --checkout-only          Enable only this checkout; do not update the        │
│                          remembered default for future checkouts.            │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync opt-out

```
 Usage: spec-kitty sync opt-out [OPTIONS]

 Disable SaaS sync for this checkout and purge its pending uploads.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --checkout-only                Disable only this checkout; do not remember   │
│                                the repo default for future checkouts.        │
│ --delete-private-data          After disabling sync, offer to delete         │
│                                already-synced private-only SaaS data for     │
│                                this checkout.                                │
│ --yes                          Skip the confirmation prompt when used with   │
│                                --delete-private-data.                        │
│ --help                         Show this message and exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync routes

```
 Usage: spec-kitty sync routes [OPTIONS]

 Show where the current checkout sends data and which teams it is shared with.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync server

```
 Usage: spec-kitty sync server [OPTIONS] [URL]

 Show or set sync server URL.

 Examples:
spec-kitty sync server
spec-kitty sync server https://spec-kitty-dev.fly.dev
spec-kitty sync server http://localhost:8000

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   url      [URL]  Sync server URL to set (HTTPS, or loopback HTTP for local  │
│                   development)                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync share

```
 Usage: spec-kitty sync share [OPTIONS] TEAM_SLUG

 Share the current repository from Private Teamspace into a team.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    team_slug      TEXT  Team slug to share this repository into.           │
│                           [required]                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync status

```
 Usage: spec-kitty sync status [OPTIONS]

 Show sync queue status, connection state, and auth info.

 Displays:
 - Offline queue size
 - Connection / emitter status
 - Last sync timestamp
 - Auth status
 - Server URL configuration

 Use --check to test actual connectivity (adds 3s timeout if server
 unreachable).

 Examples:
     # Show status (fast)
     spec-kitty sync status

     # Test connection to server
     spec-kitty sync status --check

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --check  -c        Test connection to server AND enforce the                 │
│                    identity-boundary coherence gate (FR-009). Exits non-zero │
│                    when foreground/daemon disagree, when legacy rows remain  │
│                    in the active scope, or when any orphan daemon record is  │
│                    present.                                                  │
│ --json             When combined with --check, emit a single JSON object on  │
│                    stdout matching contracts/sync-status-output.md and       │
│                    suppress the human-readable block. Exit code 0 if         │
│                    coherent, 2 otherwise.                                    │
│ --help             Show this message and exit.                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync unshare

```
 Usage: spec-kitty sync unshare [OPTIONS] TEAM_SLUG

 Stop sharing the current repository from this developer to one team.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    team_slug      TEXT  Team slug to stop sharing this repository into.    │
│                           [required]                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty sync workspace

```
 Usage: spec-kitty sync workspace [OPTIONS]

 Synchronize workspace with upstream changes.

 Updates the current workspace with changes from its base branch or parent.
 This is equivalent to `git rebase <base-branch>`.

 Sync may FAIL on conflicts (must resolve before continuing).

 Examples:
     # Sync current workspace
     spec-kitty sync workspace

     # Sync with verbose output
     spec-kitty sync workspace --verbose

     # Attempt recovery from broken state
     spec-kitty sync workspace --repair

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --repair   -r        Attempt workspace recovery (may lose uncommitted work)  │
│ --verbose  -v        Show detailed sync output                               │
│ --help               Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tasks

```
 Usage: spec-kitty tasks [OPTIONS]

 Finalize tasks metadata after task generation.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission        TEXT  Mission slug (e.g., 001-user-authentication)          │
│ --json                 Emit JSON result                                      │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker

_Task tracker commands_

```
 Usage: spec-kitty tracker [OPTIONS] COMMAND [ARGS]...

 Task tracker commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ providers     List supported tracker providers, categorized by backend type. │
│ discover      Discover bindable tracker resources under your installation.   │
│ bind          Bind the current project to an issue tracker.                  │
│ status        Show tracker binding and sync status.                          │
│ list-tickets  Browse visible tickets for the resolved provider resource.     │
│ unbind        Remove tracker binding for this project.                       │
│ map           Work-package mapping commands                                  │
│ sync          Tracker synchronization commands                               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker bind

```
 Usage: spec-kitty tracker bind [OPTIONS]

 Bind the current project to an issue tracker.

 For SaaS-backed providers (linear, jira, github, gitlab):
   Uses discovery to find bindable resources automatically.
   Use --bind-ref for CI/automation, --select N for non-interactive.
   Authentication via ``spec-kitty auth login``.

 For local providers (beads, fp):
   Requires --provider, --workspace, and --credential flags.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --provider             TEXT     Provider name (linear, jira, github,      │
│                                    gitlab, beads, fp)                        │
│                                    [required]                                │
│    --bind-ref             TEXT     Binding reference for CI/automation       │
│                                    (validates against host)                  │
│    --select               INTEGER  Auto-select candidate by number           │
│                                    (non-interactive)                         │
│    --workspace            TEXT     Provider workspace/team/project           │
│                                    identifier (local providers only)         │
│    --doctrine-mode        TEXT     Doctrine mode: external_authoritative |   │
│                                    spec_kitty_authoritative |                │
│                                    split_ownership                           │
│                                    [default: external_authoritative]         │
│    --field-owner          TEXT     Split ownership mapping: field=owner      │
│                                    (local providers only)                    │
│    --credential           TEXT     Provider credential key/value: key=value  │
│                                    (local providers only)                    │
│    --help                          Show this message and exit.               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker discover

```
 Usage: spec-kitty tracker discover [OPTIONS]

 Discover bindable tracker resources under your installation.

 Lists all resources (projects, teams, boards) available for binding
 with the specified provider.  Each row is numbered 1-indexed to align
 with ``tracker bind --select N``.

 ``discover`` is explicitly the *pre-binding* command — it is how users
 find something to bind to — so it MUST NOT require an existing mission
 binding.  Requiring a binding here would make fresh bind flows
 impossible.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --provider        TEXT  Provider name [required]                          │
│    --json                  Output as JSON                                    │
│    --help                  Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker list-tickets

```
 Usage: spec-kitty tracker list-tickets [OPTIONS]

 Browse visible tickets for the resolved provider resource.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --provider        TEXT                       Tracker provider slug        │
│                                                 [required]                   │
│    --limit           INTEGER RANGE [1<=x<=100]  [default: 20]                │
│    --json                                       Render tickets as a JSON     │
│                                                 array                        │
│    --help                                       Show this message and exit.  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker map

_Work-package mapping commands_

```
 Usage: spec-kitty tracker map [OPTIONS] COMMAND [ARGS]...

 Work-package mapping commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add   Add or update a WP-to-external issue mapping.                          │
│ list  List tracker mappings.                                                 │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker map add

```
 Usage: spec-kitty tracker map add [OPTIONS]

 Add or update a WP-to-external issue mapping.

 For local providers: stores the mapping in the local SQLite database.

 For SaaS-backed providers: this command is not available.  Manage
 mappings in the Spec Kitty dashboard instead.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --wp-id               TEXT  Work package ID (e.g., WP01) [required]       │
│ *  --external-id         TEXT  External issue ID [required]                  │
│    --external-key        TEXT  External issue key                            │
│    --external-url        TEXT  External issue URL                            │
│    --help                      Show this message and exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker map list

```
 Usage: spec-kitty tracker map list [OPTIONS]

 List tracker mappings.

 For local providers: shows mappings from the local SQLite database.

 For SaaS-backed providers: shows SaaS-authoritative mappings from the
 control plane.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --provider        TEXT  Read SaaS mappings by provider without requiring a   │
│                         bound project                                        │
│ --json                  Render mappings as JSON                              │
│ --help                  Show this message and exit.                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker providers

```
 Usage: spec-kitty tracker providers [OPTIONS]

 List supported tracker providers, categorized by backend type.

 SaaS-backed providers authenticate through ``spec-kitty auth login`` and
 route sync operations through the Spec Kitty SaaS control plane.

 Local providers use direct connectors with locally stored credentials.

 This command is purely informational and prints the hard-coded provider
 categories.  It does **not** consult hosted readiness — the rollout gate
 itself is enforced by ``tracker_callback`` (and by the conditional
 registration in ``cli/commands/__init__.py``), which is all the gating
 this static output needs.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Render provider list as JSON                                 │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker status

```
 Usage: spec-kitty tracker status [OPTIONS]

 Show tracker binding and sync status.

 For SaaS-backed providers: displays identity path, sync state, and
 provider info from the SaaS control plane.

 For local providers: displays local cache statistics and configuration.

 With --all: shows installation-wide summary across all bindings
 (SaaS providers only).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --all           Show installation-wide status (SaaS providers only)          │
│ --json          Render status as JSON                                        │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker sync

_Tracker synchronization commands_

```
 Usage: spec-kitty tracker sync [OPTIONS] COMMAND [ARGS]...

 Tracker synchronization commands

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ pull     Pull tracker updates into the local cache.                          │
│ push     Push explicit mutations to the upstream provider.                   │
│ run      Run pull+push synchronization in one operation.                     │
│ publish  Publish local tracker snapshot.                                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker sync publish

```
 Usage: spec-kitty tracker sync publish [OPTIONS]

 Publish local tracker snapshot.

 This command is not supported for SaaS-backed providers.  Use
 ``spec-kitty tracker sync push`` instead.

 For local providers: the facade will raise an error if this operation
 is not supported by the bound provider.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Render publish result as JSON                                │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker sync pull

```
 Usage: spec-kitty tracker sync pull [OPTIONS]

 Pull tracker updates into the local cache.

 For SaaS-backed providers: pulls items via the SaaS control plane.
 The response includes an identity_path and summary envelope.

 For local providers: pulls directly from the tracker API.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --limit        INTEGER RANGE [1<=x<=10000]  [default: 100]                   │
│ --json                                      Render sync result as JSON       │
│ --help                                      Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker sync push

```
 Usage: spec-kitty tracker sync push [OPTIONS]

 Push explicit mutations to the upstream provider.

 For SaaS-backed providers: requires --items-json with a JSON array of
 PushItem objects per the PRI-12 TrackerPushRequest contract.  Each item
 must have ``ref``, ``action``, and optionally ``patch`` / ``target_status``.

 For full bidirectional sync, use ``tracker sync run`` instead.

 For local providers: pushes directly to the tracker API using --limit.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --limit             INTEGER RANGE [1<=x<=10000]  Max items (local providers  │
│                                                  only)                       │
│                                                  [default: 100]              │
│ --items-json        TEXT                         Path to JSON file with      │
│                                                  PushItem[] array (SaaS      │
│                                                  providers). Use '-' for     │
│                                                  stdin.                      │
│ --json                                           Render sync result as JSON  │
│ --help                                           Show this message and exit. │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker sync run

```
 Usage: spec-kitty tracker sync run [OPTIONS]

 Run pull+push synchronization in one operation.

 For SaaS-backed providers: executes a full sync cycle via the SaaS
 control plane.

 For local providers: runs pull then push using direct connectors.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --limit        INTEGER RANGE [1<=x<=10000]  [default: 100]                   │
│ --json                                      Render sync result as JSON       │
│ --help                                      Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty tracker unbind

```
 Usage: spec-kitty tracker unbind [OPTIONS]

 Remove tracker binding for this project.

 For SaaS-backed providers this clears only local project configuration.
 Provider unlinking remains a SaaS dashboard action.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty upgrade

```
 Usage: spec-kitty upgrade [OPTIONS]

 Upgrade a Spec Kitty project to the current version.

 Detects the project's current version and applies all necessary migrations
 to bring it up to date with the installed CLI version.

 **New flags (WP09)**:
   ``--cli``     Emit CLI upgrade guidance only.  No project detection;
                 succeeds outside any project (FR-014).
   ``--project`` Run project migrations only; suppresses CLI nag.
                 Errors outside a project.
   ``--yes``/``-y``  Non-interactive confirmation (alias for ``--force``).
                     Does NOT bypass schema-incompatibility blocks
 (CHK037/A-006).
   ``--no-nag``  Suppress upgrade-nag banner even when a CLI update exists.

 Mutual exclusion: ``--cli`` and ``--project`` together exit 2.

 **Exit codes** (R-08):
   0  Success / ALLOW / ALLOW_WITH_NAG / any ``--dry-run``
   2  ``--cli --project`` flag conflict
   4  Project migration required (BLOCK_PROJECT_MIGRATION)
   5  Project is too new for this CLI (BLOCK_CLI_UPGRADE) — not bypassable
   6  Project metadata corrupt (BLOCK_PROJECT_CORRUPT)
   1  General error

 See also: ``docs/guides/install-and-upgrade.md``

 Examples:
     spec-kitty upgrade              # Upgrade to current version
     spec-kitty upgrade --dry-run    # Preview changes
     spec-kitty upgrade --target 0.6.5  # Upgrade to specific version
     spec-kitty upgrade --cli        # Show CLI upgrade hint, no project needed
     spec-kitty upgrade --project    # Project migrations only
     spec-kitty upgrade --yes        # Non-interactive (same as --force)
     spec-kitty upgrade --dry-run --json  # Machine-readable plan

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --dry-run                     Preview changes without applying               │
│ --force                       Skip confirmation prompts                      │
│ --target                TEXT  Target version (defaults to current CLI        │
│                               version)                                       │
│ --json                        Output results as JSON                         │
│ --verbose       -v            Show detailed migration information            │
│ --no-worktrees                Skip upgrading worktrees                       │
│ --cli                         Restrict to CLI guidance only; works outside   │
│                               any project (FR-014)                           │
│ --project                     Restrict to current-project compat +           │
│                               migrations (FR-015)                            │
│ --yes           -y            Non-interactive confirmation; alias for        │
│                               --force (FR-017)                               │
│ --no-nag                      Suppress upgrade-nag output explicitly         │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty validate-encoding

```
 Usage: spec-kitty validate-encoding [OPTIONS]

 Validate and optionally fix file encoding in feature artifacts.

 Scans markdown files for Windows-1252 smart quotes and other problematic
 characters that cause UTF-8 encoding errors. Can automatically fix issues
 by replacing problematic characters with safe alternatives.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission                   TEXT  Mission slug to validate                   │
│ --fix                             Automatically fix encoding errors by       │
│                                   sanitizing files                           │
│ --all                             Check all features, not just one           │
│ --backup     --no-backup          Create .bak files before fixing            │
│                                   [default: backup]                          │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty validate-tasks

```
 Usage: spec-kitty validate-tasks [OPTIONS]

 LEGACY: Validate and repair directory/frontmatter lane mismatches.

 This command is for legacy projects that used directory-based lanes
 (tasks/planned/, tasks/doing/, etc.). Modern projects (3.0+) use
 flat tasks/ directories with canonical status in status.events.jsonl.

 For modern projects, use `spec-kitty agent mission finalize-tasks`
 to ensure canonical status state exists.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --mission          TEXT  Mission slug to validate                            │
│ --fix                    Automatically repair metadata inconsistencies       │
│ --all                    Check all features, not just one                    │
│ --agent            TEXT  Agent name for activity log                         │
│ --shell-pid        TEXT  Shell PID for activity log                          │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty verify_setup

```

```

## spec-kitty workflow

_Manage mission workflow definitions_

```
 Usage: spec-kitty workflow [OPTIONS] COMMAND [ARGS]...

 Manage mission workflow definitions

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ list    List workflow ids available to a project.                            │
│ export  Export a resolvable workflow YAML file.                              │
│ import  Import a workflow YAML into `.kittify/overrides/workflows`.          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty workflow export

```
 Usage: spec-kitty workflow export [OPTIONS] WORKFLOW_ID OUTPUT

 Export a resolvable workflow YAML file.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    workflow_id      TEXT  Workflow id to export. [required]                │
│ *    output           PATH  Destination file or directory. [required]        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --project-root        PATH  Project root used for .kittify workflow          │
│                             discovery.                                       │
│                             [default: .]                                     │
│ --force                     Overwrite an existing destination file.          │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty workflow import

```
 Usage: spec-kitty workflow import [OPTIONS] SOURCE

 Import a workflow YAML into `.kittify/overrides/workflows`.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    source      PATH  Workflow YAML file to import. [required]              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --project-root        PATH  Project root that receives the workflow          │
│                             override.                                        │
│                             [default: .]                                     │
│ --force                     Overwrite an existing workflow file.             │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## spec-kitty workflow list

```
 Usage: spec-kitty workflow list [OPTIONS]

 List workflow ids available to a project.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --project-root        PATH  Project root used for .kittify workflow          │
│                             discovery.                                       │
│                             [default: .]                                     │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```
<!-- END GENERATED -->
