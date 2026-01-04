---
description: Execute structured task from docs/tasks/ with strict phase-by-phase flow
allowed-tools: "*"
argument-hint: "[task-name or path]"
---

# Execute Task: $ARGUMENTS

**Invoke the `executing-tasks` skill:**

```
Skill tool → executing-tasks
Task path: $ARGUMENTS
```

## What This Does

1. Loads task from `docs/tasks/{task-name}/`
2. Reads CONTEXT.md for current state (resumes if interrupted)
3. Executes phases sequentially via developer-agent
4. Updates CONTEXT.md after each phase
5. Tracks progress in README.md

## Execution Flow

```
For each phase:
1. Update README → In progress
2. Delegate to developer-agent (implementation + tests + commit)
3. Validate result
4. Update README → Complete
5. Update CONTEXT.md
6. Continue automatically
```

## Key Rules

- Developer-agent handles: code, tests, commits
- Orchestrator handles: status updates, CONTEXT.md
- Never pause between phases unless blocked
- Output is concise (~3-4 lines per phase)

## Example Output

```
Task: user-notifications (5 phases)

Phase 01: Planning
Delegating to developer-agent...
Complete - Files: 3 | Tests: 167/167 | Commit: a1b2c3d

Phase 02: Backend
Delegating to developer-agent...
Complete - Files: 8 | Tests: 172/172 | Commit: d4e5f6g

...

Task Complete: user-notifications
Phases: 5 | Commits: 5 | Tests: All passing
```

## Usage

```bash
/execute-task user-notifications
/execute-task docs/tasks/payment-refactor/
```
