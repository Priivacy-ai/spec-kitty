# Tracer: Tooling Friction

No friction encountered during spec authoring. `gh issue view 3701 --repo Priivacy-ai/spec-kitty --json title,body,comments` returned cleanly once `GITHUB_TOKEN` was unset (as instructed by the mission brief); the mission scaffold (`meta.json`, stub `spec.md`, `checklists/`, `research/`, `tasks/`, `status.events.jsonl`) was already present and correctly pointed at `fix/mission-types-empty-action-sequence-3701`; `.venv/bin/spec-kitty spec-commit --help` resolved without needing a fallback lookup.
