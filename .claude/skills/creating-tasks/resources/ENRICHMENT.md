# Phase Enrichment Agent

## Purpose

Enrichment agents explore the codebase to find real file paths, patterns, and implementation details. Each agent writes its own phase file directly.

## Agent Configuration

```
Task tool:
  subagent_type: "general-purpose"   # Can read AND write
  model: "haiku"                      # Fast and cheap
  description: "Enrich Phase {N}: {phase-name}"
  prompt: {see template below}
```

**Why `general-purpose` not `Explore`:**
- `Explore` is read-only (cannot write files)
- `general-purpose` can explore AND write the enriched file
- Faster: parallel agents write files simultaneously

## Full Prompt Template

```markdown
**TASK:** Enrich phase file with real codebase details

**PHASE FILE:** docs/tasks/{task-name}/0{N}-{phase-name}.md

**PRD CONTEXT:**
Task: {task title}
App: {app-name}
Naming: {naming conventions from PRD}
Contract: {API contract from PRD}
Tech: {technology decisions from PRD}

**PHASE FOCUS:**
{Copy the "Focus" line from phase stub}

**ENRICHMENT HINTS:**
{Copy the "Agent should explore" items from phase stub}

**YOUR JOB:**

1. **Explore codebase** to find:
   - Existing patterns that match this phase's work
   - Similar features already implemented
   - Files that will be created or modified
   - Integration points (aggregators, routers, registries)
   - Test patterns for this type of code

2. **Web search** if needed for:
   - Library documentation (specific versions)
   - Best practices for patterns used
   - API references

3. **Write enriched phase file** to the path:

## Codebase Analysis
- Pattern source: `{file}:{lines}` - {why this is relevant}
- Integration point: `{file}:{line}` - {what to add here}
- Similar feature: `{description}` - {what to learn from it}

## Implementation Steps
1. **{Action}** at `{exact/file/path.py}`
   - {Specific detail}
   - Reference: `{pattern-file}:{lines}`

2. **{Action}** at `{exact/file/path.py}`
   ...

## Success Criteria
- [ ] {Specific file exists at specific path}
- [ ] {Specific integration done at specific location}
- [ ] Tests passing

**OUTPUT:**
Write the enriched phase file using the Write tool.
Return a brief summary of what was found and written.

**QUALITY REQUIREMENTS:**
- Every file path must be REAL (verified exists or will be created)
- Every pattern reference must include file:line
- Every step must be concrete (no "implement the feature")
- Success criteria must be verifiable
```

## Exploration Strategies by Phase Type

### Backend Model Phase

```
Explore:
- core/backend/src/core/models/ for model patterns
- Similar models (User, Subscription, Payment)
- Base classes and mixins used
- Relationship patterns

Search for:
- "class.*Model" in models/
- "__tablename__" patterns
- Existing migrations structure
```

### Backend Repository Phase

```
Explore:
- core/backend/src/core/infrastructure/database/repo/
- BaseRepo class and methods
- Composition patterns in app repos
- Aggregator structure (RequestsRepo)

Search for:
- "class.*Repo" patterns
- "@cached_property" for lazy loading
- Transaction handling patterns
```

### Backend Service Phase

```
Explore:
- Service layer patterns in app/services/
- How services compose repositories
- Transaction boundaries
- Error handling patterns

Search for:
- "class.*Service" patterns
- How services are registered
- Dependency injection patterns
```

### Backend API Phase

```
Explore:
- Webhook/router structure
- Endpoint patterns (CRUD)
- Request/response schemas
- Authentication/authorization

Search for:
- "@router" decorators
- Pydantic schemas
- Dependency injection
```

### Frontend Composable Phase

```
Explore:
- app/composables/ for patterns
- How generated hooks are wrapped
- Optimistic update patterns
- Error handling

Search for:
- "use.*" composable names
- TanStack Query patterns
- Generated hooks in gen/hooks/
```

### Frontend Component Phase

```
Explore:
- Similar components in presentation/
- Layout integration points
- Styling patterns (Tailwind)
- State management connection

Search for:
- Component structure patterns
- Props/emits conventions
- Slot usage
```

### Testing Phase

```
Explore:
- Test structure in tests/
- Fixture patterns
- Contract vs unit test separation
- Mock patterns

Search for:
- "def test_" patterns
- "@pytest.mark" usage
- Fixture definitions
```

## Parallel Execution Example

For a 4-phase task, launch all at once:

```python
# In a single message, invoke 4 Task tools:

Task 1: Enrich Phase 01 (Backend Models)
Task 2: Enrich Phase 02 (Backend API)
Task 3: Enrich Phase 03 (Frontend Store)
Task 4: Enrich Phase 04 (Frontend UI)
```

Each returns independently. Collect all results, then write to files.

## Handling Enrichment Failures

If an agent returns incomplete results:

1. Check if phase scope was too broad → Split into sub-phases
2. Check if codebase patterns unclear → Add hints to stub
3. Re-run single agent with more specific guidance

## Quality Checklist

Before accepting enrichment:

- [ ] All file paths are real or clearly marked as "new"
- [ ] Pattern references include line numbers
- [ ] Implementation steps are ordered correctly
- [ ] Dependencies between phases are clear
- [ ] Success criteria are testable
