# Quickstart: Profile Invocation Runtime

## Prerequisites

- `spec-kitty` 3.2.0 (this feature targets the `3.2.0` release line)
- A project with at least one profile available (shipped profiles ship with spec-kitty; project-local profiles require `spec-kitty charter synthesize` to have run)

---

## 1. Discover available profiles

```bash
spec-kitty profiles list
```

**JSON output** (for host-LLM consumption):
```bash
spec-kitty profiles list --json
```

Example output:
```json
[
  {
    "profile_id": "cleo",
    "friendly_name": "Cleo — Senior Implementer",
    "role": "implementer",
    "action_domains": ["implement", "generate", "refine", "build"],
    "source": "shipped"
  },
  {
    "profile_id": "pedro",
    "friendly_name": "Pedro — Code Reviewer",
    "role": "reviewer",
    "action_domains": ["review", "audit", "assess", "inspect"],
    "source": "shipped"
  }
]
```

---

## 2. Get governance context (opens an invocation record)

### Named profile (`ask`):
```bash
spec-kitty ask pedro "review WP03" --json
```

### Anonymous dispatch (router picks profile):
```bash
spec-kitty do "implement the payment module" --json
```

### With explicit profile hint (`advise`):
```bash
spec-kitty advise "fix the authentication bug" --profile cleo --json
```

Example response:
```json
{
  "invocation_id": "01KPQRX2EVGMRVB4Q1JQBAZJV3",
  "profile_id": "cleo",
  "profile_friendly_name": "Cleo — Senior Implementer",
  "action": "implement",
  "governance_context_text": "## Governance Context\n\n### Active Directives\n...",
  "governance_context_hash": "a1b2c3d4e5f67890",
  "governance_context_available": true,
  "router_confidence": "canonical_verb"
}
```

Save the `invocation_id` — you need it to close the record.

---

## 3. Use the governance context

The `governance_context_text` field contains the full doctrine context for your `(profile, action)` pair. Inject it into your prompt or use it to guide your work.

---

## 4. Close the invocation record

```bash
spec-kitty profile-invocation complete \
  --invocation-id 01KPQRX2EVGMRVB4Q1JQBAZJV3 \
  --outcome done
```

With evidence (Tier 2 promotion):
```bash
spec-kitty profile-invocation complete \
  --invocation-id 01KPQRX2EVGMRVB4Q1JQBAZJV3 \
  --outcome done \
  --evidence /path/to/evidence.md
```

---

## 5. Review recent invocations

```bash
spec-kitty invocations list
spec-kitty invocations list --profile pedro --limit 5 --json
```

---

## Host-LLM integration (Claude Code / Codex / Cursor)

```bash
# Step 1: Get governance context and invocation ID
RESULT=$(spec-kitty advise "implement WP03" --json)
INVOCATION_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['invocation_id'])")
CONTEXT=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['governance_context_text'])")

# Step 2: Use $CONTEXT to guide work (host LLM reads it and acts)
echo "Governance context loaded: $CONTEXT"

# Step 3: After work completes, close the record
spec-kitty profile-invocation complete --invocation-id "$INVOCATION_ID" --outcome done
```

---

## Handling router ambiguity

If `spec-kitty do "help me"` returns an ambiguity error:

```json
{
  "error_code": "ROUTER_NO_MATCH",
  "message": "No profile matched the request tokens. Use 'ask' to specify a profile explicitly.",
  "candidates": [],
  "suggestion": "Use 'spec-kitty ask <profile> <request>' to specify a profile explicitly."
}
```

Use `ask` with an explicit profile name instead:
```bash
spec-kitty ask cleo "help me implement the feature"
```

---

## What happens when charter is not synthesized?

If `governance_context_available` is `false` in the response, it means `spec-kitty charter synthesize` has not been run for this project. The invocation record is still written (Tier 1 trail is always produced), but the `governance_context_text` is empty.

To fix:
```bash
spec-kitty charter synthesize
```

---

## Minimal viable trail: what gets recorded where

| Action | Tier 1 (always) | Tier 2 (optional) | Tier 3 (special) |
|--------|----------------|-------------------|------------------|
| `advise`, `ask`, `do` | ✓ InvocationRecord in `.kittify/events/` | Only if `--evidence` passed to `complete` | Never (conversational) |
| `spec-kitty.specify` | ✓ InvocationRecord | ✓ spec.md is the evidence | ✓ `kitty-specs/<mission>/spec.md` |
| `spec-kitty.implement WP##` | ✓ InvocationRecord | ✓ Implementation diff | ✓ WP status event in `status.events.jsonl` |
