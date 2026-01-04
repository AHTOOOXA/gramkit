---
name: executing-tasks
description: Executes structured tasks from docs/tasks/ with phase-by-phase workflow. Use when user says "execute task", "run task", or provides task path. Reads CONTEXT.md for state, delegates phases to developer-agent, updates progress automatically.
---

# Executing Tasks

## Contents
- [Execution Flow](#execution-flow)
- [Phase Execution Checklist](#phase-execution-checklist)
- [Testing-Polish Phases](#testing-polish-phases)
- [CONTEXT.md Protocol](#contextmd-protocol)
- [Output Format](#output-format)
- [References](#references)

## Execution Flow

```
1. Load task (README.md + CONTEXT.md)
2. Identify current phase from CONTEXT.md
3. If starting Phase 01: Run `make up APP={app}` first
4. For each incomplete phase:
   a. Update README → In progress
   b. Delegate to developer-agent
   c. Validate result
   d. Update README → Complete
   e. Update CONTEXT.md
   f. Continue immediately (no pausing)
5. Final summary
```

**Key rules:**
- Developer-agent handles: implementation, tests, commits
- Orchestrator handles: status updates, CONTEXT.md, continuation
- **Phase 01 only:** Run `make up APP={app}` before delegating
- Never pause between phases unless blocked
- Be concise (~3-4 lines output per phase)

## Phase Execution Checklist

Copy and track for each phase:

```
Phase 01 (first phase only):
- [ ] Run `make up APP={app}` to ensure containers are running
- [ ] Read phase file
- [ ] Update README.md → In progress
- [ ] Delegate to developer-agent
- [ ] Check result (tests passed?)
- [ ] Verify commit: feat({task}): Phase 01 - {Title}
- [ ] Update README.md → Complete
- [ ] Update CONTEXT.md
- [ ] Continue to next phase

Phase {N} (subsequent phases):
- [ ] Read phase file
- [ ] Update README.md → In progress
- [ ] Delegate to developer-agent
- [ ] Check result (tests passed?)
- [ ] Verify commit: feat({task}): Phase 0{N} - {Title}
- [ ] Update README.md → Complete
- [ ] Update CONTEXT.md
- [ ] Continue to next phase
```

## Orchestrator vs Developer-Agent

| Responsibility | Who |
|---------------|-----|
| Load task, track status | Orchestrator |
| Run `make up APP=...` (Phase 01) | Orchestrator |
| Update README.md status | Orchestrator |
| Update CONTEXT.md | Orchestrator |
| Read phase instructions | Developer-agent |
| Implement code changes | Developer-agent |
| Run `make test APP=...` | Developer-agent |
| Create commits | Developer-agent |
| Return summary | Developer-agent |

## Developer-Agent Delegation

Use Task tool with `subagent_type: "general-purpose"`:

```
**TASK:** docs/tasks/{task-name}/

**PHASE:** {N} - {phase-name}

**READ:** docs/tasks/{task-name}/0{N}-{phase-name}.md

**REQUIRED SKILLS:** (from README.md)
- skill: core/critical-rules
- skill: {domain skill}
- skill: testing/pytest

**APP:** {app-name}

**DO:**
1. Follow phase file steps exactly
2. Run tests: `make test APP={app}`
3. **COMMIT (REQUIRED):** `feat({task-name}): Phase 0{N} - {Phase Title}`

**RETURN:**
- Files changed (paths)
- Tests: Passing/Failed (count)
- Commit: {short hash} (MUST have commit)
- Success criteria: Met/Not met
```

See [delegation.md](resources/delegation.md) for full format.

## Testing-Polish Phases

Phases with `Type: testing-polish` are handled differently - they use `testing-polish-agent` instead of `developer-agent`.

### Detection

A phase is testing-polish if:
- Has `**Type:** testing-polish` in the file
- OR title contains "Testing" + "Polish"

### Agent Selection

```
Read phase file
     │
     ▼
Has "Type: testing-polish"? ──YES──► Use testing-polish-agent
     │
     NO
     │
     ▼
Use developer-agent (default)
```

### Different Handling

| Aspect | developer-agent | testing-polish-agent |
|--------|-----------------|----------------------|
| Focus | Build features | Verify & **fix** |
| Main tools | Code editors, make test | **Playwright** |
| Commit prefix | `feat({task})` | `fix({task})` |
| Success | Tests pass | Scenarios pass OR documented |
| Agent file | `.claude/agents/developer-agent.md` | `.claude/agents/testing-polish-agent.md` |

### Testing-Polish Delegation

Use Task tool with `subagent_type: "general-purpose"`:

```
**TASK:** docs/tasks/{task-name}/

**PHASE:** {N} - Testing & Polish

**TYPE:** testing-polish

**AGENT:** Read and follow `.claude/agents/testing-polish-agent.md`

**READ:**
1. `.claude/agents/testing-polish-agent.md` (agent behavior)
2. `docs/tasks/{task-name}/0{N}-testing-polish.md` (test scenarios)
3. `.claude/shared/playwright-testing.md` (Playwright commands)

**APP:** {app-name}

**KEY BEHAVIOR:**
You are a FIXER, not just a tester.
- Execute test scenarios via Playwright
- If fail → diagnose → fix code → retest
- Repeat until passing (max 3 attempts per scenario)
- After 3 failures → document in KNOWN_ISSUES.md, continue

**COMMIT (if fixes made):**
fix({task-name}): Phase 0{N} - {brief fix summary}

**RETURN:**
- Scenarios: {passed}/{total}
- Fixed: {list of what was fixed}
- Known Issues: {count} (if any)
- Commit: {hash} (if fixes made)
```

### Testing-Polish Checklist

```
Testing-Polish Phase:
- [ ] Detect phase type (look for "Type: testing-polish")
- [ ] Verify Playwright: curl http://localhost:9876/health
- [ ] Update README.md → In progress
- [ ] Delegate to testing-polish-agent (see prompt above)
- [ ] Check result (scenarios passed?)
- [ ] If fixes made: verify commit with fix() prefix
- [ ] Update README.md → Complete
- [ ] Update CONTEXT.md
- [ ] Continue to next phase
```

### Output Format (Testing-Polish)

```
Phase {N}: Testing & Polish
Delegating to testing-polish-agent...
Complete - Scenarios: {pass}/{total} | Fixed: {count} | Known Issues: {count}
```

## CONTEXT.md Protocol

### On Task Load
1. Read `CONTEXT.md` first
2. Check current phase and status
3. Resume from documented state

### After Each Phase
Update CONTEXT.md with:
```markdown
**Last Updated:** {now}
**Current Phase:** {N+1}

## Files Modified
- `{new files from this phase}`

## Next Steps
1. {What phase N+1 will do}
```

### On Blockers
```markdown
**Status:** Blocked

## Blockers
- {Description of blocker}

## Open Questions
- [ ] {Question for user}
```

### Before Session End
Always update CONTEXT.md with current state to preserve context.

## Output Format

**Per phase (concise):**
```
Phase {N}: {name}
Delegating to developer-agent...
Complete - Files: {count} | Tests: {pass}/{total} | Commit: {hash}
```

**Final summary:**
```
Task Complete: {task-name}

Phases: {N} executed
Commits: {M} created
Tests: All passing ({count})

Location: docs/tasks/{task-name}/
```

## Error Handling

| Situation | Action |
|-----------|--------|
| Tests fail | Show output, attempt fix, retry once |
| Success criteria not met | List failures, ask user |
| Agent reports blocker | Update CONTEXT.md, ask user |
| Phase file missing | Skip or ask user |

See [error-handling.md](resources/error-handling.md) for details.

## Resuming Interrupted Tasks

1. Read CONTEXT.md
2. Find current phase and status
3. Confirm with user: "Resuming from Phase {N}. Proceed?"
4. Continue execution flow

## References

- [delegation.md](resources/delegation.md) - Full agent prompt format
- [error-handling.md](resources/error-handling.md) - Error cases
- [validation.md](resources/validation.md) - Success criteria checking
- [testing-polish-agent.md](../../agents/testing-polish-agent.md) - Testing & polish agent
- [playwright-testing.md](../../shared/playwright-testing.md) - Playwright commands reference
