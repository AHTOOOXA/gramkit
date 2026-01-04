---
description: Add testing & polish phases to an existing task
allowed-tools: "*"
argument-hint: "[task-name or path]"
---

# Add Testing Phases: $ARGUMENTS

**Invoke the `adding-testing` skill:**

```
Skill tool → adding-testing
Task path: $ARGUMENTS
```

## What This Does

1. Loads task from `docs/tasks/{task-name}/`
2. Analyzes phases to identify frontend-touching work
3. Converts success criteria into test scenarios
4. Creates testing-polish phase file(s)
5. Updates README.md and CONTEXT.md

## Output

```
docs/tasks/{task-name}/
├── ...existing phases...
└── {NN}-testing-polish.md  ← NEW (Type: testing-polish)
```

## After Adding

```bash
# Execute task including testing phases
/execute-task {task-name}
```

The `execute-task` skill recognizes `Type: testing-polish` phases and delegates them to the `testing-polish-agent` instead of `developer-agent`.

## Examples

```
/add-testing rbac-admin-panel
/add-testing template-react-demo-expansion
/add-testing docs/tasks/user-notifications/
```
