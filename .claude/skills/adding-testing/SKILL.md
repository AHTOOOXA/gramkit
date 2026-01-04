---
name: adding-testing
description: Adds testing & polish phases to existing tasks. Analyzes task phases, identifies frontend-touching work, generates test scenarios from success criteria, inserts testing-polish phases.
---

# Adding Testing Phases

## When to Use

After `/create-task` when you want to add UI testing/polishing phases to verify frontend work.

## Execution Flow

```
1. Load existing task
2. Analyze phases → find frontend-touching ones
3. Determine granularity (flexible)
4. Generate testing phase(s) with test scenarios
5. Insert into task structure
6. Update README.md and CONTEXT.md
```

---

## Step 1: Load Task

**Read:**
- `docs/tasks/{task-name}/README.md`
- `docs/tasks/{task-name}/CONTEXT.md`
- All phase files (`0*.md`)

**Extract:**
- App name
- Phase list with descriptions
- Success criteria (will become test scenarios)
- Which phases touch frontend

---

## Step 2: Identify Frontend-Touching Phases

**Indicators:**
- Phase name: UI, Frontend, Component, Page, Polish
- Files mention: `frontend/`, `.tsx`, `.vue`, `components/`
- Success criteria: visible, click, form, navigation, user sees, displays

**Mark each phase:**
```
01-backend.md      → implementation
02-api.md          → implementation
03-frontend-ui.md  → FRONTEND ✓
04-polish.md       → FRONTEND ✓
```

---

## Step 3: Determine Granularity

| Frontend Phases | Strategy |
|-----------------|----------|
| 1-4 | One testing phase at end |
| 5+ | Multiple testing phases, grouped by feature |

**Simple case (most common):** Add single testing phase after all implementation.

---

## Step 4: Generate Testing Phase

### Convert Success Criteria to Test Scenarios

**From phase success criteria:**
```markdown
- [ ] User can see their role on admin page
- [ ] Protected action shows feedback
```

**To test scenarios:**
```markdown
### Scenario 1: Role Display
**Steps:**
1. Navigate to `/admin`
2. Verify "Your Access" card visible
3. Verify role text shows correctly

**Pass:** Role displayed matches user's actual role

### Scenario 2: Protected Action Feedback
**Steps:**
1. On admin page, click "Execute Protected Action"
2. Verify feedback appears

**Pass:** Shows success or "access denied" message
```

### Phase Template

```markdown
# Phase {N}: Testing & Polish

**Type:** testing-polish
**Depends on:** Phase {N-1}

**Objective:** Verify and fix {covered features} until working

---

## Test Scenarios

### Scenario 1: {Name}
**Steps:**
1. {action}
2. {verification}

**Pass:** {clear success state}

### Scenario 2: {Name}
...

---

## Verification Checklist

- [ ] No console errors
- [ ] All API calls succeed
- [ ] Visual appearance correct

---

## Fix Protocol

For each scenario:
1. Execute via Playwright
2. If PASS → next
3. If FAIL → diagnose → fix → retest (up to 3x)
4. After 3 failures → document in KNOWN_ISSUES.md

**Reference:** `.claude/shared/playwright-testing.md`
```

---

## Step 5: Insert Phase File

Write to: `docs/tasks/{task-name}/{NN}-testing-polish.md`

**Numbering:** Use next available number after last implementation phase.

---

## Step 6: Update Task Files

### Update README.md

Add to Phases Overview table:
```markdown
| {N} | Testing & Polish | testing-polish |
```

### Update CONTEXT.md

Add note:
```markdown
## Testing Phases

- Phase {N}: Testing & Polish (added via /add-testing)
- Type: testing-polish
- Agent: testing-polish-agent
```

---

## Output Format

```
Testing phases added: docs/tasks/{task-name}/

Analyzed:
- Total phases: {N}
- Frontend-touching: {M}

Added:
- {NN}-testing-polish.md

Test scenarios ({count}):
1. {scenario 1}
2. {scenario 2}
...

Next: /execute-task {task-name}
```

---

## Checklist

```
Adding Testing Phases:
- [ ] Read README.md + CONTEXT.md + all phase files
- [ ] Identified frontend-touching phases
- [ ] Determined granularity (usually: one at end)
- [ ] Converted success criteria to test scenarios
- [ ] Wrote testing-polish phase file
- [ ] Updated README.md phases table
- [ ] Updated CONTEXT.md with note
- [ ] Reported to user
```
