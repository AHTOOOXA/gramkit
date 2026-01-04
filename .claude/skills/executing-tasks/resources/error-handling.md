# Error Handling

## Test Failures

**When `make test` fails:**

1. Show test output to identify failure
2. Analyze the error
3. Attempt automatic fix (one retry)
4. If still failing:
   - Update CONTEXT.md with blocker
   - Ask user for guidance
   - Do not proceed to next phase

```markdown
# Update CONTEXT.md:
**Status:** Blocked

## Blockers
- Tests failing in {test_file}
- Error: {error message}

## Open Questions
- [ ] How to fix {specific issue}?
```

## Success Criteria Not Met

**When phase completes but criteria fail:**

1. List which criteria failed:
   ```
   Success criteria:
   - Met: {criterion 1}
   - Met: {criterion 2}
   - NOT MET: {criterion 3}
   ```

2. Ask user:
   ```
   Not all success criteria met. Options:
   1. Fix issues and retry
   2. Continue anyway (not recommended)
   3. Pause for manual intervention
   ```

3. Do not proceed without user approval

## Agent Reports Blocker

**When developer-agent returns blocker:**

1. Update README.md status → Blocked
2. Update CONTEXT.md:
   ```markdown
   **Status:** Blocked

   ## Blockers
   - {blocker description from agent}
   ```
3. Ask user how to proceed:
   ```
   Phase {N} blocked: {reason}

   Options:
   1. Retry (after fixing prerequisites)
   2. Skip phase
   3. Pause execution
   ```

## Missing Files

**Phase file not found:**
- Check for typos in filename
- List available phase files
- Ask user which to execute

**CONTEXT.md not found:**
- Create empty CONTEXT.md using template
- Start from Phase 00 or 01

## Commit Failures

**Git commit fails:**

1. Check git status
2. Common issues:
   - No changes to commit → Skip commit, proceed
   - Merge conflict → Ask user
   - Pre-commit hook failure → Fix issues, retry commit

## Recovery Protocol

After any error is resolved:

1. Update CONTEXT.md:
   ```markdown
   **Status:** In Progress

   ## Blockers
   None (resolved: {what was fixed})
   ```

2. Resume from interrupted phase
3. Continue normal execution flow
