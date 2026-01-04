# Task Templates

## PRD Template (README.md)

```markdown
# Task: {Title}

**Created:** {YYYY-MM-DD}
**Status:** Planning | In Progress | Complete
**App:** {app-name}

---

## Overview

{2-3 sentences describing what we're building and why}

---

## Design Decisions

### Naming Conventions

| Entity | Name | Notes |
|--------|------|-------|
| Model | `{ModelName}` | |
| Table | `{table_name}` | |
| Endpoint | `/api/{resource}` | |
| Frontend route | `/{resource}` | |
| Component prefix | `{Resource}` | |

### API Contract

\`\`\`typescript
// Request
interface Create{Model}Request {
  field1: string
  field2: number
}

// Response
interface {Model}Response {
  id: string
  field1: string
  field2: number
  createdAt: string
}

// Endpoints
POST   /api/{resource}      → Create
GET    /api/{resource}      → List
GET    /api/{resource}/{id} → Get
PUT    /api/{resource}/{id} → Update
DELETE /api/{resource}/{id} → Delete
\`\`\`

### Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| {Library} | {x.y.z} | {why chosen} |
| {Pattern} | - | {description} |

### Architecture Notes

- {Key architectural decision and rationale}
- {Integration approach}
- {Performance considerations}

---

## Required Skills

Developer-agent should invoke during execution:

**Always:**
- [ ] `skill: core/critical-rules`
- [ ] `skill: testing/pytest`

**Domain-specific:**
- [ ] `skill: backend/patterns` - {if backend work}
- [ ] `skill: backend/entity-creation` - {if new entity}
- [ ] `skill: frontend/vue` - {if Vue frontend}
- [ ] `skill: frontend/react` - {if React frontend}
- [ ] `skill: operations/migrations` - {if database changes}

---

## Phases

| Phase | Focus | Status | Enrichment Task |
|-------|-------|--------|-----------------|
| [01](./{file}.md) | {name} | Not started | {what agent explores} |
| [02](./{file}.md) | {name} | Not started | {what agent explores} |
| [03](./{file}.md) | {name} | Not started | {what agent explores} |

---

## Success Criteria

### Functional
- [ ] {User-facing outcome 1}
- [ ] {User-facing outcome 2}

### Technical
- [ ] All tests passing
- [ ] No lint errors
- [ ] API schema updated
- [ ] Types generated

---

## References

- {Link to relevant docs}
- {Link to similar feature}
- {External documentation}

---

**Execute:** `/execute-task {task-name}`
```

---

## Phase Stub Template (before enrichment)

```markdown
# Phase {N}: {Phase Name}

**Focus:** {One-line description of what this phase accomplishes}

## Enrichment Task

Agent should explore:
- {Codebase area to search}
- {Patterns to find}
- {Similar features to reference}
- {Web searches if needed}

---

<!-- Content below filled by enrichment agent -->

## Codebase Analysis

{To be filled with real file:line references}

## Implementation Steps

{To be filled with concrete steps}

## Success Criteria

{To be filled with verifiable criteria}
```

---

## Enriched Phase Template (after enrichment)

```markdown
# Phase {N}: {Phase Name}

**Focus:** {One-line description}

## Codebase Analysis

**Pattern source:**
- `{file}:{lines}` - {what pattern to follow}

**Integration points:**
- `{file}:{line}` - {what to add/modify here}

**Similar implementation:**
- `{file or PR}` - {what to learn from it}

## Implementation Steps

1. **{Action verb}** at `{exact/path/to/file.ext}`
   - {Specific sub-task}
   - {Specific sub-task}
   - Reference: `{pattern-file}:{lines}`

2. **{Action verb}** at `{exact/path/to/file.ext}`
   - {Specific sub-task}
   \`\`\`{language}
   {code snippet if helpful}
   \`\`\`

3. **{Action verb}**
   \`\`\`bash
   {command to run}
   \`\`\`

## Success Criteria

- [ ] File exists: `{exact/path}`
- [ ] Integration done: `{file}:{line}`
- [ ] Tests passing: `make test APP={app}`
- [ ] {Other verifiable criterion}

## Next

→ [Phase {N+1}: {name}](./{next-file}.md)
```

---

## ARCHITECTURE.md Template (HARD tasks only)

```markdown
# Architecture

> This document defines shared contracts for parallel phase enrichment.
> All enrichment agents MUST use these exact paths and names.

## Files to Create

| Phase | File | Creates |
|-------|------|---------|
| 01 | `{app}/backend/src/app/infrastructure/database/models/{name}.py` | `{ModelName}` model |
| 01 | `{app}/backend/src/app/infrastructure/database/repo/{name}.py` | `{ModelName}Repo` class |
| 02 | `{app}/backend/src/app/services/{name}.py` | `{ModelName}Service` class |
| 03 | `{app}/backend/src/app/webhook/routers/{name}.py` | API routes |
| 04 | `{app}/frontend/src/components/{Name}/` | Frontend components |

## Files to Modify

| Phase | File | Line | Change |
|-------|------|------|--------|
| 01 | `{app}/backend/src/app/infrastructure/database/models/__init__.py` | EOF | Export model |
| 01 | `{app}/backend/src/app/infrastructure/database/repo/requests.py` | properties | Add repo property |
| 02 | `{app}/backend/src/app/services/requests.py` | properties | Add service property |
| 03 | `{app}/backend/src/app/webhook/app.py` | routers | Add router |

## Naming Conventions

| Entity | Name |
|--------|------|
| Model class | `{ModelName}` |
| Table name | `{model_names}` (plural, snake_case) |
| Repository | `{ModelName}Repo` |
| Service | `{ModelName}Service` |
| Router module | `{model_name}.py` |
| Endpoint prefix | `/{model-names}` |
| Frontend component | `{ModelName}Card.vue` |

## Interfaces

### {ModelName}Repo
\`\`\`python
class {ModelName}Repo(BaseRepo[{ModelName}]):
    def get_by_user_id(self, user_id: int) -> list[{ModelName}]: ...
    def get_by_id(self, id: int) -> {ModelName} | None: ...
\`\`\`

### {ModelName}Service
\`\`\`python
class {ModelName}Service:
    def __init__(self, repo: RequestsRepo): ...
    def create(self, user_id: int, data: Create{ModelName}Request) -> {ModelName}: ...
    def list_for_user(self, user_id: int) -> list[{ModelName}]: ...
    def get(self, id: int) -> {ModelName}: ...
\`\`\`

## Phase Dependencies

| Phase | Creates | Used By |
|-------|---------|---------|
| 01 | `{ModelName}` model, `{ModelName}Repo` | 02, 03, 04 |
| 02 | `{ModelName}Service` | 03, 04 |
| 03 | API routes | 04 |
| 04 | Frontend components | - |

## Import Paths

When phases need to import from earlier phases:

\`\`\`python
# Phase 02 imports from Phase 01
from app.infrastructure.database.models import {ModelName}
from app.infrastructure.database.repo import {ModelName}Repo

# Phase 03 imports from Phase 02
from app.services import {ModelName}Service
\`\`\`
```

---

## CONTEXT.md Template

```markdown
# Task Context

**Last Updated:** {YYYY-MM-DD HH:MM}
**Current Phase:** {N} ({phase name})
**Status:** Not Started | In Progress | Blocked | Complete

## Key Decisions

- {Decision}: {rationale}

## Files Modified

- `{path}` - {what changed}

## Open Questions

- [ ] {Question needing user input}

## Blockers

{None or description}

## Next Steps

1. {Immediate next action}
2. {Following action}
```

---

## Status Indicators

| Status | Meaning |
|--------|---------|
| Not started | Phase not begun |
| In progress | Currently executing |
| Complete | Phase finished |
| Blocked | Has blocker |

---

## Naming Conventions

**Task names:** kebab-case
- `user-notifications`
- `payment-refactor`
- `api-versioning`

**Phase files:** `{NN}-{kebab-name}.md`
- `01-backend-models.md`
- `02-backend-api.md`
- `03-frontend-components.md`
