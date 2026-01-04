# Developer-Agent Delegation Format

## Full Prompt Template

When delegating a phase to developer-agent via Task tool:

```markdown
**TASK:** docs/tasks/{task-name}/

**PHASE:** {N} - {phase-name}

**CONTEXT:**
{Contents of CONTEXT.md - key decisions, files modified so far}

**READ & FOLLOW:**
docs/tasks/{task-name}/0{N}-{phase-name}.md

**REQUIRED SKILLS:**
Invoke these before implementing:
1. skill: core/critical-rules (always)
2. skill: core/project-structure (always)
3. skill: {domain skill from README}
4. skill: testing/pytest (always)

**APP:** {app-name}

**IMPLEMENTATION:**
1. Follow all steps in phase file
2. Apply project architecture patterns
3. Database changes: `make migration msg=...` then `make upgrade APP=...`
4. After implementation: `make test APP=...`
5. After tests pass: `git add . && git commit`

**COMMIT FORMAT (REQUIRED):**
```
feat({task-name}): Phase 0{N} - {Phase Title}

{brief changes - max 3 bullets}
```
Example: `feat(user-notifications): Phase 01 - Database Models`

**IMPORTANT:**
- Every phase MUST be committed before returning
- NEVER use `--no-verify` (pre-commit hooks must run)

**SUCCESS CRITERIA:**
{Copy from phase file}

**RETURN (CONCISE):**
- Files changed: {paths only}
- Migration: {name or "None"}
- Tests: Passing ({count}) / Failed ({show errors})
- Commit: {short hash} / Not committed
- Success criteria: Met / Not met (list failures)
```

## Task Tool Parameters

```
Task tool:
  subagent_type: "general-purpose"
  description: "Phase {N}: {phase-name}"
  prompt: {above template filled in}
```

## Example Delegation

```markdown
**TASK:** docs/tasks/user-notifications/

**PHASE:** 2 - Backend Models

**CONTEXT:**
Current Phase: 2
Key Decisions:
- Using composition pattern for NotificationService
- Storing in notifications table (not embedded)

**READ & FOLLOW:**
docs/tasks/user-notifications/02-backend-models.md

**REQUIRED SKILLS:**
1. skill: core/critical-rules
2. skill: core/project-structure
3. skill: backend/patterns
4. skill: testing/pytest

**APP:** tarot

**IMPLEMENTATION:**
1. Follow all steps in phase file
2. Create Notification model in core/backend/
3. Create migration: `make migration msg="add notifications" APP=tarot`
4. Apply: `make upgrade APP=tarot`
5. Test: `make test APP=tarot`
6. **COMMIT:** `feat(user-notifications): Phase 02 - Backend Models`

**SUCCESS CRITERIA:**
- [ ] Notification model created
- [ ] Migration applied successfully
- [ ] Tests passing
- [ ] Phase committed

**RETURN (CONCISE):**
Files, migration name, test results, commit hash (REQUIRED), success criteria status
```
