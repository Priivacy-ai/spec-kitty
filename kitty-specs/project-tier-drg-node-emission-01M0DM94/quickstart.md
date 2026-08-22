# Quickstart — Verify a project-tier agent_profile reaches the cascade

Prove the M6 fix end-to-end in a scratch project.

## 1. Author a project-tier agent profile

```bash
mkdir -p .kittify/doctrine/agent_profiles
cat > .kittify/doctrine/agent_profiles/reviewer-rhonda.agent.yaml <<'YAML'
profile-id: reviewer-rhonda
name: Reviewer Rhonda
description: Project-local reviewer specialisation.
YAML
```

No synthesis interview answer is created — this is a **hand-authored** profile.

## 2. Re-synthesize the project overlay

```bash
spec-kitty charter activate agent-profile reviewer-rhonda   # or any activate/synthesize path
```

## 3. Verify the node reached the cascade-read graph

```bash
grep -A2 'agent_profile:reviewer-rhonda' .kittify/doctrine/graph.yaml
```

Expected (after M6): a node block

```yaml
- urn: agent_profile:reviewer-rhonda
  kind: agent_profile
  label: Reviewer Rhonda
```

**Before M6** the file contains no such node — the profile loaded and validated but was cascade-invisible.

## 4. Confirm cascade reachability (programmatic)

```python
from pathlib import Path
from charter._drg_helpers import load_validated_graph

graph = load_validated_graph(Path("."))
assert graph.get_node("agent_profile:reviewer-rhonda") is not None
```

## Scope reminders

- `asset:*` project nodes are **not** emitted (deferred behind #3037).
- The emitted node carries **no** inbound edges — edge authoring is M5. It is still a valid graph node and is reachable once activated as a cascade source.
