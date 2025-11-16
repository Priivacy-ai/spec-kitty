# 003-auto-protect-agent Development Guidelines
*Path: [templates/agent-file-template.md](templates/agent-file-template.md)*


Auto-generated from all feature plans. Last updated: 2025-11-10

## Active Technologies
- Python 3.11+ (existing spec-kitty codebase) + pathlib, Rich (for console output), subprocess (for git operations) (003-auto-protect-agent)
- Python 3.11+ (existing spec-kitty codebase) + yper, rich, httpx, pyyaml, readchar (004-modular-code-refactoring)
- File system (no database) (004-modular-code-refactoring)
- Python 3.11+ (existing spec-kitty codebase requirement) (005-refactor-mission-system)
- Filesystem only (YAML configs, CSV files, markdown templates) (005-refactor-mission-system)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.11+ (existing spec-kitty codebase): Follow standard conventions

## Recent Changes
- 005-refactor-mission-system: Added Python 3.11+ (existing spec-kitty codebase requirement)
- 004-modular-code-refactoring: Added Python 3.11+ (existing spec-kitty codebase) + yper, rich, httpx, pyyaml, readchar
- 003-auto-protect-agent: Added Python 3.11+ (existing spec-kitty codebase) + pathlib, Rich (for console output), subprocess (for git operations)

<!-- MANUAL ADDITIONS START -->

 Never claim something in the frontend works without Playwright proof.

  - API responses don't guarantee UI works
  - Frontend can break silently (404 caught, shows fallback)
  - Always test the actual user experience, not just backend

<!-- MANUAL ADDITIONS END -->
