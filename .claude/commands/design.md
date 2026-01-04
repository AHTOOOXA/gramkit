---
description: Brainstorm and research solutions - web search, references, ideas
allowed-tools: "*"
argument-hint: "[feature or problem description]"
---

# Design: $ARGUMENTS

**Invoke the `designing-features` skill:**

```
Skill tool → designing-features
```

## What This Does

Brainstorming and research mode:
- Web search for best practices and references
- Find how others solved similar problems
- Explore open source implementations
- Generate and discuss ideas
- Synthesize into a direction

## When to Use

- Multiple valid approaches, unclear which is best
- Need external references
- Architectural decisions
- Creative exploration needed

## When NOT to Use

Skip `/design` and use `/create-task` directly when:
- Clear path following existing patterns
- Standard CRUD features
- Bug fixes

## Output

Either:
- **Lightweight:** Summary in conversation → `/create-task`
- **Design doc:** `docs/designs/{name}.md` (for substantial explorations)

## Examples

```
/design caching strategy for API responses
/design real-time notifications (WebSocket vs SSE vs polling)
/design plugin architecture for extensibility
```
