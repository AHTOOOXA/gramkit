# Reviewing Code Skill

**Purpose:** Deep, critical review that questions design and implementation decisions.

**When to use:** `/review [feature or file paths]`

---

## Before Starting: Read Project Conventions

| Reviewing | Read First |
|-----------|------------|
| Backend code | `.claude/shared/backend-patterns.md` |
| Vue frontend | `.claude/shared/vue-frontend.md` |
| React frontend | `.claude/shared/react-frontend.md` |
| Tests | `.claude/shared/testing-patterns.md` |
| Any code | `.claude/shared/critical-rules.md` |

**These docs define what "correct" looks like.** Review against them.

---

## Philosophy

Don't just check if code "works". Question:
- **Why** was it built this way?
- **What** alternatives exist?
- **Where** might this break?
- **Is** this the right abstraction?

Be skeptical. Challenge assumptions. Find the weaknesses.

---

## Process

### Step 1: Understand Scope

Ask user if unclear:
- What should I review? (specific files, feature, entire PR)
- Any particular concerns?
- Is this new code or changes to existing?

### Step 2: Gather Context

Read the code and understand:
- What problem does this solve?
- How does it integrate with existing code?
- What patterns is it following (or breaking)?

### Step 3: Question the Design

**Check against project patterns** (from shared docs you read):

**Architecture (see `backend-patterns.md`, `monorepo-structure.md`):**
- Does this belong here? (core vs app - "Will 2+ apps need this?")
- Follows 3-layer? (Interface → Service → Repository)
- Uses composition pattern? (CoreRequestsRepo → RequestsRepo)
- Transaction boundaries correct? (flush not commit)

**Frontend (see `vue-frontend.md` or `react-frontend.md`):**
- Server state in TanStack Query?
- Client state only in Pinia/Zustand?
- Using generated hooks from `gen/`?
- Using shadcn components?

**Then question deeper:**
- Is this the right abstraction level?
- Will this scale? What happens with 10x load?
- What happens when this fails?
- Are there simpler alternatives?
- What about edge cases (null, empty, concurrent access)?
- Are there race conditions?

### Step 4: Question the Implementation

**Code quality:**
- Is this readable in 6 months?
- Is there hidden complexity?
- Are error cases handled?
- What's not tested?

**Performance:**
- N+1 queries?
- Missing indexes?
- Unnecessary work?

**Security:**
- Input validation?
- Authorization checks?
- Data exposure?

### Step 5: Verify with Tools

```bash
make test APP={app}    # Tests pass?
make lint APP={app}    # Quality checks?
```

For frontend:
```bash
cd apps/{app}/frontend && pnpm typecheck
```

### Step 6: Discuss with User

Present findings and **have a conversation**:
- "I noticed X - was this intentional?"
- "Have you considered Y approach instead?"
- "This might break when Z - how should we handle it?"

Use `AskUserQuestion` to clarify design decisions.

### Step 7: Report

```markdown
## Review: {Feature/Files}

### Design Assessment

**What it does:** {1-2 sentences}

**Design decision:** {The key architectural choice}

**My concern:** {Why I'm questioning it}

**Alternative:** {What else could be done}

### Issues Found

**Critical** (must fix):
- {Issue}: {file:line} - {why it's a problem}

**Major** (should fix):
- {Issue}: {file:line} - {why it matters}

**Minor** (consider):
- {Issue}: {file:line} - {suggestion}

### Questions for Discussion

- {Question about a design decision}
- {Question about edge case handling}
- {Question about future maintainability}

### Verdict

{Ready / Needs changes / Needs redesign}

{Specific actions required before approval}
```

---

## Red Flags (Project-Specific)

**Backend:**
- `commit()` in repository (should be `flush()`)
- Missing `@cached_property` on aggregator properties
- Business logic in webhook/controller layer
- Data access in service layer
- App-specific code in `core/`
- Core code duplicated in `apps/`
- No pessimistic locking on balance/payment operations
- Naive datetimes (should be `datetime.now(UTC)`)

**Frontend:**
- Server state in Pinia/Zustand (should be TanStack Query)
- Manual API calls instead of generated hooks
- Editing files in `gen/` folder
- PrimeVue components (should be shadcn)
- Missing translations (en + ru required)

**Testing:**
- Wrong markers (contract vs business_logic)
- Not using provided fixtures
- <80% coverage on new code

**General:**
- Running docker/alembic/pytest directly (should use make)
- Missing migration after model change
- Missing `make schema` after API change

---

## Key Questions to Always Ask

1. "What happens when this fails?"
2. "What's the simplest thing that could work?"
3. "Will I understand this in 6 months?"
4. "What's not being tested?"
5. "Is this solving the right problem?"
