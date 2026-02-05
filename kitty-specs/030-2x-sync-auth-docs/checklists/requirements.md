# Requirements Checklist — 030-2x-sync-auth-docs

## Functional Requirements

- [ ] **FR-001**: Tutorial for first-time server connection (server URL config, `auth login`, verify with `auth status`)
- [ ] **FR-002**: How-to for each `auth` subcommand (`login`, `logout`, `status`)
- [ ] **FR-003**: How-to for each new `sync` subcommand (`workspace`, `now`, `status`)
- [ ] **FR-004**: Reference entries for all `auth` subcommands (flags, args, return behavior)
- [ ] **FR-005**: Reference entries for all new `sync` subcommands (flags, args, return behavior)
- [ ] **FR-006**: Reference for server config (`config.toml` server_url) and credential storage (`credentials.json`)
- [ ] **FR-007**: Explanation of sync architecture (event-sourced, WebSocket, offline queue, batch REST)
- [ ] **FR-008**: How-to/tutorial for SaaS dashboard views (overview, board, activity)
- [ ] **FR-009**: Proper heading hierarchy, accessible language, DocFX conventions (YAML front matter, toc.yml)
- [ ] **FR-010**: Working CLI examples for all auth and sync commands
- [ ] **FR-011**: Clear distinction between local workspace sync and new server sync commands
- [ ] **FR-012**: New doc files added to `toc.yml` but marked hidden/unpublished
- [ ] **FR-013**: Translation markup consistent with existing docs site

## Success Criteria

- [ ] **SC-001**: Every `auth`/`sync` subcommand reference matches `--help` output
- [ ] **SC-002**: New-to-2.x developer can follow tutorial to authenticate and sync without help
- [ ] **SC-003**: Sync architecture explanation covers all three data paths
- [ ] **SC-004**: All docs build with `docfx build` with zero warnings
- [ ] **SC-005**: No placeholder text or TODOs in any doc file

## Quality Gates

- [ ] Heading hierarchy is proper (H1 > H2 > H3, no skipping)
- [ ] All CLI examples tested against 2.x branch
- [ ] No broken internal links between doc pages
- [ ] Existing `sync-workspaces.md` unmodified
- [ ] Each doc page has "See Also" section
