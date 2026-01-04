---
description: Create a structured multi-phase task plan in docs/tasks/
allowed-tools: "*"
argument-hint: "[feature/task description]"
---

# Create Task: $ARGUMENTS

**Invoke the `creating-tasks` skill:**

```
Skill tool → creating-tasks
```

## What This Does

1. Gathers requirements (goal, scope, dependencies)
2. Creates task structure in `docs/tasks/{task-name}/`
3. **Auto-detects difficulty** and chooses enrichment strategy
4. Generates README.md with phases and design decisions
5. Creates enriched phase files with `file:line` references
6. Creates CONTEXT.md for state tracking

## Difficulty Levels

| Difficulty | Criteria | Enrichment |
|------------|----------|------------|
| **SIMPLE** | ≤3 phases, single layer | Orchestrator explores directly |
| **HARD** | 4+ phases, full-stack, new entity | Hub-and-spoke: ARCHITECTURE.md → parallel agents |

## Output Structure

```
docs/tasks/{task-name}/
├── README.md           # PRD: overview, design, phases
├── ARCHITECTURE.md     # (HARD only) Shared contracts for parallel agents
├── CONTEXT.md          # State tracking (includes difficulty)
├── 01-{phase}.md       # Enriched phase (with file:line refs)
├── 02-{phase}.md
└── ...
```

**ARCHITECTURE.md (HARD tasks):** Defines all file paths, class names, and interfaces
BEFORE parallel enrichment. This prevents conflicts when agents work independently.

## After Creation

```bash
# Review the task
cat docs/tasks/{task-name}/README.md

# Execute it
/execute-task {task-name}
```

## Examples

```
/create-task user notifications feature
/create-task migrate to PostgreSQL 16
/create-task add dark mode toggle        # likely SIMPLE
/create-task new subscription system     # likely HARD
```
