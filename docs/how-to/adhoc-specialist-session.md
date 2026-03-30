# How to Start an Ad-Hoc Specialist Session

Use `/spec-kitty.profile-context` to open an interactive session with a named specialist agent — without starting a full mission. This is the right tool for exploration, quick questions, small fixes, and experimentation.

---

## When to use this

An ad-hoc specialist session is appropriate when:

- You have a question for a specific role ("how should I structure this API?")
- You want to explore an approach before committing to a feature
- You need a quick code review, a naming suggestion, or a small refactor
- You want to sanity-check a decision with a domain expert
- You are experimenting and do not yet know whether the result is worth keeping

It is **not** appropriate when:

- You need a tracked, reproducible workflow → use `/spec-kitty.specify` + the mission pipeline
- You want persistent state that advances work packages → use `/spec-kitty.implement`

---

## Starting a session

Invoke the command with a profile name:

```
/spec-kitty.profile-context architect
/spec-kitty.profile-context reviewer
/spec-kitty.profile-context researcher
```

The agent loads its profile — role, doctrine, specialization context, and initialization declaration — and introduces itself. From that point on, you are in a live advisory session.

**Available profiles** (shipped): `architect`, `designer`, `implementer`, `planner`, `researcher`, `reviewer`, `curator`, `manager`

---

## What happens during a session

The session is **advisory by default**. The specialist:

- Answers questions, proposes options, and explains trade-offs from its defined perspective
- May suggest involving another specialist ("this looks like it needs a Reviewer")
- Does **not** switch specialists automatically — any handoff requires your explicit approval
- Does **not** advance mission state, move work packages, or write to `kitty-specs/`

The system writes a lightweight session record (memory-dump), but does not produce full mission-grade tracing. You stay in control throughout.

---

## Switching agents mid-session

To bring in a different perspective, simply invoke the command again with another profile:

```
/spec-kitty.profile-context reviewer
```

The previous agent's session context is checkpointed. The new specialist starts with the same conversation history available as background.

You can also switch based on an agent's own suggestion — but only if you agree:

> **Architect Alphonso:** This looks like it needs a security review. Would you like to bring in the Reviewer?
>
> **You:** Yes, switch to reviewer.

---

## Keeping or discarding the output

By default, the session produces a lightweight memory-dump artefact. Nothing is committed or promoted automatically.

If the session produced something worth keeping — a decision, an approach, a pattern — you can request formalization:

> "Write down what we decided."
> "Formalize this approach."
> "Capture this as a recommendation."

The agent will produce a structured artefact. You then decide whether to commit it, file it as a doctrine candidate, or discard it.

**Nothing is promoted to doctrine without your explicit instruction.**

---

## The reasoning lifecycle

Ad-hoc sessions are the first layer in a three-layer model:

| Layer | Mode | Purpose |
|-------|------|---------|
| **Think** | Ad-hoc specialist session | Explore, question, experiment |
| **Capture** | Formalization (on request) | Turn a finding into a repeatable artefact |
| **Execute** | Mission pipeline | Structured, tracked delivery |

A session never escalates to Capture or Execute automatically. You decide if and when to move forward.

---

## Example: quick architecture question

```
/spec-kitty.profile-context architect

> I'm adding a new sync endpoint. Should it be synchronous or return a job ID?

[Architect Alphonso responds with trade-off analysis]

> Good point on the timeout risk. Let's go with job ID. Capture that decision.

[Architect Alphonso writes a short ADR-style note]
```

The decision note can then be committed to `architecture/` or used as input to the next `/spec-kitty.specify` run — at your discretion.

---

## Related

- [Slash Command Reference](../reference/slash-commands.md)
- [AI Agent Architecture](../explanation/ai-agent-architecture.md)
- [Mission System](../explanation/mission-system.md)
