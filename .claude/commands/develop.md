---
description: Implement a feature using developer-agent delegation
allowed-tools: "*"
argument-hint: "[feature name or brief description]"
---

# Develop: $ARGUMENTS

## Step 1: Delegate to developer-agent

```
Task tool → developer-agent
Prompt: "
Implement: $ARGUMENTS

App: [tarot / template / template-react]
Scope: [Backend only / Frontend only / Full-stack]

Requirements:
- [What needs to be built]

Return: Summary with file paths, migration name, test results
"
```

## Step 2: Integration (after agent completes)

```bash
# If API changed
make schema APP={app}

# Verify
make test APP={app}
make lint APP={app}
```

## Step 3: Report

Summarize what was implemented with file paths.
