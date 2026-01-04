---
name: creating-tasks
description: Creates structured task plans in docs/tasks/ with PRD and parallel phase enrichment. Use when user asks to "create a task" or "plan a feature". Auto-detects difficulty - simple tasks get inline enrichment, hard tasks get parallel agent enrichment.
---

# Creating Tasks

## Execution Order (STRICT)

```
STEP 1: Gather requirements        ← AskUserQuestion
        ↓
STEP 2: Create README.md (PRD)     ← Write file
        ↓
STEP 3: Assess difficulty          ← Auto-detect
        │
        ├─── SIMPLE ──────────────────────────────────┐
        │    ↓                                        │
        │    STEP 4S: Explore codebase directly       │
        │             (Explore agent or Glob/Grep)    │
        │    ↓                                        │
        │    STEP 5S: Write enriched phases inline    │
        │                                             │
        └─── HARD (Hub-and-Spoke) ────────────────────┤
             ↓                                        │
             STEP 4H: Create phase stubs              │
             ↓                                        │
             STEP 5H: Create ARCHITECTURE.md          │
                      (single agent - the "hub")      │
             ↓                                        │
             STEP 6H: Parallel enrichment             │
                      (agents use ARCHITECTURE.md)    │
        ┌─────────────────────────────────────────────┘
        ↓
STEP 7: Create CONTEXT.md          ← Write file
        ↓
STEP 8: Report to user
```

**CRITICAL: Steps must be done IN ORDER. Do not skip ahead.**

**Hub-and-Spoke for HARD tasks:**
- ARCHITECTURE.md defines all file paths, class names, and contracts ONCE
- Parallel agents work within these constraints → no conflicts

---

## Step 1: Gather Requirements

**Action:** Use AskUserQuestion tool

**Ask about:**
- Goal/outcome
- Scope (backend/frontend/full-stack)
- App name
- Key constraints or preferences

**Output:** Mental model of what to build

---

## Step 2: Create README.md (PRD)

**Prerequisite:** Step 1 complete

**Action:** Write `docs/tasks/{task-name}/README.md`

**Template:**
```markdown
# Task: {Title}

**Created:** {date}
**Status:** Planning
**App:** {app-name}

## Overview
{2-3 sentences}

## Design Decisions

### Naming
- Model: `{Name}`
- Table: `{name}`
- Endpoint: `/api/{resource}`

### API Contract
\`\`\`typescript
interface {Name} {
  id: string
  // fields
}
\`\`\`

### Tech Stack
- {choices made}

## Required Skills
- [ ] `skill: backend/patterns`
- [ ] `skill: testing/pytest`

## Phases
| # | Focus | Enrichment Task |
|---|-------|-----------------|
| 01 | {name} | {what to explore} |
| 02 | {name} | {what to explore} |

## Success Criteria
- [ ] {outcome}
```

---

## Step 3: Assess Difficulty

**Prerequisite:** Step 2 complete (README.md exists with phases defined)

**Action:** Evaluate task complexity based on signals below

### Detection Criteria

| Signal | SIMPLE | HARD |
|--------|--------|------|
| Phase count | 1-3 phases | 4+ phases |
| Scope | Backend OR frontend only | Full-stack (backend + frontend) |
| New entity | No new models | New model + API + UI |
| Integration points | 1-3 files to modify | 5+ files across layers |
| Pattern complexity | Follows existing patterns | Requires new patterns |

### Decision Rules

**SIMPLE if ALL true:**
- ≤3 phases
- Single layer (backend-only OR frontend-only)
- Clear existing patterns to follow

**HARD if ANY true:**
- ≥4 phases
- Full-stack changes
- New entity (model → repo → service → API → frontend)
- Multiple unfamiliar integration points

**Output:** Set `difficulty: simple` or `difficulty: hard` mentally, then follow corresponding path.

---

## SIMPLE PATH

### Step 4S: Explore Codebase Directly

**Prerequisite:** Step 3 assessed as SIMPLE

**Action:** Use `Task` tool with `Explore` agent OR direct `Glob`/`Grep` to find:
- Pattern sources (`file:line` references)
- Integration points
- Similar implementations

**Example exploration:**
```
Task tool:
  subagent_type: "Explore"
  description: "Find patterns for {phase focus}"
  prompt: |
    Find codebase patterns for: {phase description}
    App: {app}

    Look for:
    - Similar implementations
    - Files to modify
    - Pattern sources with file:line

    Return: file:line references and integration points
```

**Collect:** Pattern sources and integration points for all phases.

---

### Step 5S: Write Enriched Phases Inline

**Prerequisite:** Step 4S exploration complete

**Action:** Write enriched phase files directly (no stubs needed)

For each phase, write `docs/tasks/{task-name}/0{N}-{name}.md`:

```markdown
# Phase {N}: {Name}

**Focus:** {description}

## Codebase Analysis

**Pattern source:**
- `{file}:{lines}` - {what to follow}

**Integration points:**
- `{file}:{line}` - {what to modify}

## Implementation Steps

1. **{Action}** at `{path}`
   - {detail}
   - Reference: `{pattern-file}:{lines}`

## Success Criteria

- [ ] {verifiable criterion}
```

**Then:** Proceed to Step 7 (Create CONTEXT.md)

---

## HARD PATH

### Step 4H: Create Phase Stubs

**Prerequisite:** Step 3 assessed as HARD

**Action:** Write stub file for EACH phase listed in README.md

**Stub template** (`docs/tasks/{task-name}/01-{name}.md`):
```markdown
# Phase 01: {Name}

**Focus:** {one line from README}

## Enrichment Task
Explore:
- {hint 1}
- {hint 2}

---
## Codebase Analysis
{TO BE FILLED BY ENRICHMENT}

## Implementation Steps
{TO BE FILLED BY ENRICHMENT}

## Success Criteria
{TO BE FILLED BY ENRICHMENT}
```

**Create ALL stubs before proceeding to Step 5H.**

---

### Step 5H: Create ARCHITECTURE.md (Hub)

**Prerequisite:** ALL phase stub files exist

**Action:** Use Task tool with Explore agent to create architecture document

**Why this step exists:**
- Parallel agents make independent decisions → conflicts
- ARCHITECTURE.md defines shared contracts ONCE
- All parallel agents work within these constraints

**Prompt:**
```
Task tool:
  subagent_type: "Explore"
  model: "opus"
  description: "Create architecture for {task-name}"
  prompt: |
    **TASK:** Create ARCHITECTURE.md for task coordination

    **PRD:** docs/tasks/{task-name}/README.md
    **PHASES:** {list phase files}
    **APP:** {app}

    **DO:**
    1. Read the PRD (README.md)
    2. Read all phase stubs to understand full scope
    3. Explore codebase to find:
       - Existing patterns for similar entities
       - File naming conventions
       - Class naming conventions
       - Where to add new files
    4. Create ARCHITECTURE.md with:
       - All files to create (exact paths)
       - All files to modify (exact paths + lines)
       - Class/function names for each
       - Interface contracts between phases
       - Phase dependencies

    **WRITE TO:** docs/tasks/{task-name}/ARCHITECTURE.md

    **FORMAT:**
    # Architecture

    ## Files to Create

    | Phase | File | Creates |
    |-------|------|---------|
    | 01 | `{path}` | `{ClassName}` |

    ## Files to Modify

    | Phase | File | Line | Change |
    |-------|------|------|--------|
    | 02 | `{path}` | {N} | Add import |

    ## Naming Conventions

    | Entity | Name |
    |--------|------|
    | Model | `{Name}` |
    | Table | `{name}` |
    | Service | `{Name}Service` |
    | Repo | `{Name}Repo` |

    ## Interfaces

    ### {ServiceName}
    \`\`\`python
    class {ServiceName}:
        def method(self, param: Type) -> ReturnType: ...
    \`\`\`

    ## Phase Dependencies

    | Phase | Creates | Used By |
    |-------|---------|---------|
    | 01 | Model, Repo | 02, 03 |
    | 02 | Service | 03 |
```

**Then:** Proceed to Step 6H (Parallel Enrichment)

---

### Step 6H: Parallel Enrichment (agents write files)

**Prerequisite:** ARCHITECTURE.md exists

**Action:** Launch ONE Task tool call PER phase, ALL IN PARALLEL

**IMPORTANT:**
- Use `subagent_type: "general-purpose"` (can read AND write)
- Use `model: "haiku"` for speed
- Launch ALL agents in a SINGLE message
- Each agent MUST read ARCHITECTURE.md first
- Each agent writes its own phase file

**Per-phase prompt:**
```
Task tool:
  subagent_type: "general-purpose"
  model: "haiku"
  description: "Enrich Phase {N}"
  prompt: |
    **TASK:** Enrich phase file with real codebase details

    **CRITICAL: Read ARCHITECTURE.md first!**
    - Use EXACT file paths from ARCHITECTURE.md
    - Use EXACT class/function names from ARCHITECTURE.md
    - Follow interface contracts from ARCHITECTURE.md

    **FILES TO READ FIRST:**
    1. docs/tasks/{task-name}/ARCHITECTURE.md (required!)
    2. docs/tasks/{task-name}/0{N}-{name}.md (your phase stub)

    **APP:** {app}

    **DO:**
    1. Read ARCHITECTURE.md - note YOUR phase's files and names
    2. Read your phase stub file
    3. Explore codebase to find:
       - Pattern sources for YOUR files (with file:line)
       - Integration points matching ARCHITECTURE.md
    4. Write the enriched phase file with:
       - Codebase Analysis (real file:line references)
       - Implementation Steps (using ARCHITECTURE.md paths/names)
       - Success Criteria (verifiable)

    **WRITE TO:** docs/tasks/{task-name}/0{N}-{name}.md

    **FORMAT:**
    # Phase {N}: {Name}

    **Focus:** {description}

    ## Codebase Analysis
    **Pattern source:**
    - `{file}:{lines}` - {description}

    **Integration points:**
    - `{file}:{line}` - {what to modify}

    ## Implementation Steps
    1. **{Action}** at `{path from ARCHITECTURE.md}`
       - {detail}
       - Class name: `{from ARCHITECTURE.md}`

    ## Success Criteria
    - [ ] {verifiable criterion}
```

**Example - 3 phases launched in SINGLE message:**
```
[Task tool #1: general-purpose, haiku, "Enrich Phase 01"]
[Task tool #2: general-purpose, haiku, "Enrich Phase 02"]
[Task tool #3: general-purpose, haiku, "Enrich Phase 03"]
```

Agents run in parallel, each reads ARCHITECTURE.md first, then writes its file.

**Then:** Proceed to Step 7 (Create CONTEXT.md)

---

## BOTH PATHS CONTINUE

## Step 7: Create CONTEXT.md

**Prerequisite:** All phase files written (either path)

**Action:** Write `docs/tasks/{task-name}/CONTEXT.md`

**Content:**
```markdown
# Task Context

**Last Updated:** {date}
**Current Phase:** 0 (not started)
**Status:** Not Started
**Difficulty:** {simple|hard}

## Key Decisions
None yet.

## Files Modified
None yet.

## Next Steps
1. Begin Phase 01
```

---

## Step 8: Report to User

**Prerequisite:** CONTEXT.md written

**Output:**
```
Task created: docs/tasks/{task-name}/

Difficulty: {SIMPLE|HARD}
Enrichment: {inline|hub-and-spoke parallel}

Files:
- README.md (PRD)
- ARCHITECTURE.md (HARD only - shared contracts)
- CONTEXT.md
- 01-{name}.md (enriched)
- 02-{name}.md (enriched)
- ...

Codebase references found:
- {file1}
- {file2}

Execute: /execute-task {task-name}
```

---

## Checklists

### Simple Task Checklist
```
Task Creation (SIMPLE):
- [ ] Step 1: Asked requirements
- [ ] Step 2: Wrote README.md (PRD)
- [ ] Step 3: Assessed difficulty → SIMPLE
- [ ] Step 4S: Explored codebase directly
- [ ] Step 5S: Wrote enriched phases inline
- [ ] Step 7: Wrote CONTEXT.md
- [ ] Step 8: Reported to user
```

### Hard Task Checklist (Hub-and-Spoke)
```
Task Creation (HARD):
- [ ] Step 1: Asked requirements
- [ ] Step 2: Wrote README.md (PRD)
- [ ] Step 3: Assessed difficulty → HARD
- [ ] Step 4H: Wrote ALL phase stubs
- [ ] Step 5H: Created ARCHITECTURE.md (hub - defines contracts)
        - File paths, class names, interfaces
        - Phase dependencies
- [ ] Step 6H: Launched parallel enrichment (spoke agents)
        - Each agent reads ARCHITECTURE.md first
        - Uses exact paths/names from architecture
- [ ] Step 7: Wrote CONTEXT.md
- [ ] Step 8: Reported to user
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using parallel agents for simple task | If ≤3 phases + single layer, use inline enrichment |
| Skipping exploration for simple task | Still explore codebase, just do it directly |
| Enriching before stubs exist (HARD) | Create ALL stubs first (Step 4H) |
| Skipping ARCHITECTURE.md (HARD) | Always create architecture before parallel enrichment |
| Parallel agents use different names | ARCHITECTURE.md defines ALL names - agents must follow |
| Using wrong agent type (HARD) | Use `general-purpose` (not Explore) for enrichment so agents can write |
| Using wrong model (HARD) | Use `model: "haiku"` for enrichment speed, `opus` for architecture |
| Sequential enrichment (HARD) | Launch ALL agents in ONE message |
| Exploring before PRD | Write README.md first (Step 2) |

---

## References

- [TEMPLATE.md](TEMPLATE.md) - Full templates
- [ENRICHMENT.md](resources/ENRICHMENT.md) - Enrichment strategies
