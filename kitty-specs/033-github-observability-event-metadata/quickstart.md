# Quickstart: GitHub Observability Event Metadata

**Feature**: 033-github-observability-event-metadata

## What Changed

Every CLI-emitted event now includes three new correlation fields:

```
git_branch         → current git branch (per-event)
head_commit_sha    → HEAD commit SHA (per-event)
repo_slug          → owner/repo from origin remote (per-session)
```

## Verify It Works

After implementing this feature, emit any event and inspect the envelope:

```python
from specify_cli.sync.events import emit_wp_status_changed

event = emit_wp_status_changed("WP01", "planned", "doing")
print(event["git_branch"])       # e.g., "2.x"
print(event["head_commit_sha"])  # e.g., "68b09b04..."
print(event["repo_slug"])        # e.g., "Priivacy-ai/spec-kitty"
```

## Override Repo Slug

If auto-derivation picks the wrong `owner/repo` (mirrors, forks, non-standard remotes):

```yaml
# .kittify/config.yaml
project:
  uuid: "..."
  slug: "spec-kitty"
  node_id: "..."
  repo_slug: "my-org/my-repo"  # Manual override
```

**Validation**: Must contain at least one `/` with non-empty segments. Invalid values produce a warning and fall back to auto-derived.

## Key Files

| File | Role |
|------|------|
| `src/specify_cli/sync/git_metadata.py` | GitMetadataResolver (branch, SHA, repo slug) |
| `src/specify_cli/sync/project_identity.py` | ProjectIdentity (extended with repo_slug) |
| `src/specify_cli/sync/emitter.py` | _emit() injection point |
| `tests/sync/test_git_metadata.py` | Unit tests |
| `tests/sync/conftest.py` | Test fixtures |

## Testing

```bash
# Run all sync tests
python -m pytest tests/sync/ -x -q

# Run only git metadata tests
python -m pytest tests/sync/test_git_metadata.py -x -v

# Run event emission integration tests
python -m pytest tests/sync/test_event_emission.py -x -v
```
