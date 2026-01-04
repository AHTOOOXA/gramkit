# Agent Delegation Guide

How to effectively delegate work to subagents while preserving context and ensuring quality.

## Available Agents

### developer-agent
**Purpose:** Full-stack feature implementation (backend + frontend + tests)
**When to use:** Implementing new features, adding endpoints, creating UI
**Returns:** Concise summary with file paths, test results

### Built-in Agents

**Explore agent:** Codebase research and exploration
**Plan agent:** Architecture planning and design research

## Delegation Templates

### Template 1: Full-Stack Feature Implementation

Use `developer-agent` for implementing complete features.

**Example delegation:**

````
Task tool → developer-agent
Description: "Implement [feature name]"
Prompt: "
**CONTEXT:**
Feature: [Brief description of what needs to be built]
Scope: [Backend + Frontend / Backend only / Frontend only]
Target: [core/ or apps/template/ or both]

**REQUIREMENTS:**

Backend needs:
- Models: [describe entities needed]
- Repositories: [describe data access needed]
- Services: [describe business logic needed]
- Interface: [API endpoint / Bot handler / Worker job]

Frontend needs:
- Stores: [describe state management needed]
- Components: [describe UI components needed]
- Screens: [describe full-page views needed]
- Routes: [describe routing needed]

**TECHNICAL CONSTRAINTS:**
[Any specific technical decisions, patterns, or constraints]

**RETURN:**
Concise summary with:
- Files created/modified (paths:line_numbers)
- Migration name (if created)
- Test status (make test result)
- Any issues encountered
"
````

**When to use:**
- New feature spanning backend + frontend
- Adding API endpoints with corresponding UI
- Implementing bot commands with business logic
- Adding worker jobs with trigger UI

### Template 2: Backend-Only Implementation

Use `developer-agent` but specify backend-only scope.

**Example delegation:**

````
Task tool → developer-agent
Description: "Implement backend for [feature]"
Prompt: "
**CONTEXT:**
Feature: [Brief description]
Scope: Backend only
Target: [core/backend OR apps/template/backend]

**REQUIREMENTS:**

- Models: [describe entities]
- Repositories: [describe queries needed]
- Services: [describe business logic]
- Interface: [API endpoint / Bot handler / Worker job]
- Migration: Required

**TECHNICAL CONSTRAINTS:**
[Any specific patterns, existing code to integrate with]

**RETURN:**
Summary with files, migration name, test results
"
````

**When to use:**
- API-only features (frontend comes later)
- Background job implementation
- Bot handler additions
- Data model changes

### Template 3: Frontend-Only Implementation

Use `developer-agent` but specify frontend-only scope.

**Example delegation:**

````
Task tool → developer-agent
Description: "Implement frontend for [feature]"
Prompt: "
**CONTEXT:**
Feature: [Brief description]
Scope: Frontend only
API Available: [Yes/No, if yes, list endpoints]

**REQUIREMENTS:**

- Stores: [describe state needed]
- Components: [describe UI elements]
- Screens: [describe pages]
- Routes: [describe navigation]
- Translations: en + ru required

**DESIGN NOTES:**
[Any specific UI/UX requirements, use PrimeVue components]

**RETURN:**
Summary with files, routes added, typecheck results
"
````

**When to use:**
- UI for existing API endpoints
- Adding screens to existing features
- Improving existing UI
- New navigation flows

### Template 4: Test Coverage (Reference)

**Tests are now included in developer-agent implementation phases.**

For testing patterns, see: `.claude/shared/testing-patterns.md`

**Test distribution (80/15/5):**
- Contract tests (80%): Test all interfaces (API, bot, worker)
- Business logic tests (15%): Test complex calculations/algorithms
- Regression tests (5%): Bug fixes

**Verify tests:**
```bash
make test APP=tarot
```

### Template 5: Parallel Backend + Frontend

Launch both in a single message for parallel execution.

**Example delegation:**

````
[Single message with TWO Task tool calls]

Task tool → developer-agent
Description: "Implement backend for [feature]"
Prompt: "
**CONTEXT:**
Feature: [Brief description]
Scope: Backend only (frontend being built in parallel)

[... backend requirements ...]

**RETURN:**
Summary with files and migration
"

Task tool → developer-agent
Description: "Implement frontend for [feature]"
Prompt: "
**CONTEXT:**
Feature: [Brief description]
Scope: Frontend only (backend being built in parallel)
Note: API types will sync after backend completes

[... frontend requirements ...]

**RETURN:**
Summary with files and routes
"
````

**After both complete (main thread):**
1. Run `make schema` to sync API types
2. Fix any type errors in frontend
3. Run `make test` to verify all tests pass

**When to use:**
- Large features with independent backend/frontend work
- Time-sensitive implementations
- Clear separation between backend and frontend work

## Common Workflows

### Workflow 1: Plan → Implement → Test → Review

**Best for:** New features, complex changes

1. **Plan phase:**
   ```
   /plan [feature description]
   ```
   - Explore agent researches codebase
   - Plan agent designs architecture
   - Get user approval on plan

2. **Implement phase:**
   ```
   Task → developer-agent (use Template 1)
   ```
   - Implements backend + frontend + tests
   - Runs migrations
   - Syncs API schema
   - Returns summary with test results

3. **Verify phase (main thread):**
   ```bash
   make test APP=tarot
   make lint APP=tarot
   ```
   - All tests passing
   - Code quality verified

4. **Review phase:**
   ```
   /review [feature name or file paths]
   ```
   - Reviews implementation
   - Checks architecture adherence
   - Verifies patterns followed

### Workflow 2: Explore → Quick Implement

**Best for:** Small changes, well-understood features

1. **Explore:**
   ```
   /explore [question about codebase]
   ```
   - Understand existing implementation
   - Find relevant files

2. **Implement:**
   - If simple: Do in main thread
   - If complex: Delegate to developer-agent

### Workflow 3: Incremental Feature

**Best for:** Features built in stages

1. **Backend first:**
   ```
   Task → developer-agent (use Template 2: Backend-only)
   ```

2. **Schema sync (main thread):**
   ```bash
   make schema
   ```

3. **Frontend second:**
   ```
   Task → developer-agent (use Template 3: Frontend-only)
   ```
   - Now has correct types

4. **Verify (main thread):**
   ```bash
   make test APP=tarot
   ```

### Workflow 4: Parallel Development

**Best for:** Large features, urgent work

1. **Launch parallel (single message):**
   ```
   Task → developer-agent (backend)
   Task → developer-agent (frontend)
   ```

2. **Integration (main thread):**
   - Wait for both to complete
   - Run `make schema`
   - Fix type errors
   - Run `make test` (tests included in implementation)

## After Delegation: Main Thread Responsibilities

### Integration Steps

When agents complete, main thread handles:

1. **API Schema Sync:**
   ```bash
   make schema
   ```
   - If backend API changed
   - Regenerates frontend types
   - Fix any type errors

2. **Test Suite:**
   ```bash
   make test
   ```
   - Verify all tests pass
   - Fix any integration issues

3. **Code Quality:**
   ```bash
   make lint
   ```
   - Verify no linting issues
   - Fix if needed

4. **Type Check (Frontend):**
   ```bash
   cd apps/template/frontend && pnpm typecheck
   ```
   - Verify no type errors
   - Fix if needed

### Context Management

**Keep main context clean:**
- ✅ Read agent summaries, not full code
- ✅ Only read specific files if debugging needed
- ✅ Document checkpoints between phases
- ✅ Use `/clear` if context gets large

**Don't pollute context:**
- ❌ Don't read all agent-generated code
- ❌ Don't re-implement what agents already did
- ❌ Don't copy-paste agent code into conversation

### Checkpoint Pattern

After major phases, document state:

```markdown
## Checkpoint: [Feature Name]

**Completed:**
- Backend implementation ✅
- Frontend implementation ✅
- API schema synced ✅
- Tests written ✅
- All tests passing ✅

**Files changed:**
- [list key files with paths]

**Remaining:**
- [any follow-up work]

**Notes:**
- [important decisions or context for future work]
```

## Best Practices

### Before Delegating

**Ask yourself:**
1. Is the task clear enough for autonomous execution?
2. Have architecture decisions been made?
3. Is scope well-defined (backend, frontend, both)?
4. Are there existing patterns to follow?

**If NO to any: Clarify first, then delegate**

### Delegation Quality

**Good delegation:**
- Clear context and requirements
- Specific scope (backend/frontend/both)
- Technical constraints listed
- Expected return format specified

**Bad delegation:**
- Vague requirements ("make it better")
- No scope specified
- Missing context about existing code
- No constraints or decisions

### Agent Communication

**Agents work best when you:**
- Provide clear, structured prompts
- Include relevant context
- Specify what to return
- Set clear boundaries

**Agents struggle when:**
- Requirements are ambiguous
- Context is missing
- Scope is unclear
- No architectural guidance

### Parallel Execution

**Can parallelize:**
- Backend + frontend (independent)
- Multiple features (unrelated)
- Research + planning (different agents)

**Cannot parallelize:**
- Backend → schema sync → frontend (sequential)
- Implementation → testing (testing needs code)
- Planning → implementation (implementation needs plan)

### Error Handling

**If agent fails or produces issues:**

1. **Don't retry blindly:** Understand what went wrong
2. **Clarify requirements:** Add missing context
3. **Break down task:** Smaller pieces if too complex
4. **Fix in main thread:** If quick fix, just do it yourself

## Common Mistakes to Avoid

❌ **Don't delegate without context:** Agents need to know what exists
❌ **Don't delegate ambiguous tasks:** Clarify requirements first
❌ **Don't ignore agent summaries:** They contain important info
❌ **Don't skip integration steps:** Schema sync, tests, etc. matter
❌ **Don't delegate trivial tasks:** Edit small things yourself
❌ **Don't parallelize dependent work:** Respect dependencies
❌ **Don't pollute main context:** Keep it clean for high-level work

## When NOT to Use Agents

**Do it yourself in main thread if:**
- Simple one-line change
- Quick bug fix
- Obvious solution
- Just reading/exploring code
- Running commands (make test, etc.)

**Delegate to agent if:**
- Multi-file implementation
- New feature spanning layers
- Requires understanding existing patterns
- Time-consuming research needed
- Parallel work beneficial

## Summary

**Golden rules:**
1. **Clear context** → Better results
2. **Structured prompts** → Easier execution
3. **Appropriate scope** → Manageable tasks
4. **Integration steps** → Complete workflow
5. **Clean context** → Sustainable development

**Remember:** Agents are specialists, not magicians. Give them clear instructions, proper context, and they'll deliver quality results while keeping your main context clean.
