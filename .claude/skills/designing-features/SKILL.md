# Designing Features Skill

**Purpose:** Brainstorm, research, and explore solutions for complex or ambiguous problems.

**When to use:**
- Multiple valid approaches, unclear which is best
- Need external references (how do others solve this?)
- Want to think through tradeoffs before committing
- Creative exploration needed

**NOT needed for:** Clear features that follow existing patterns → use `/create-task` directly.

---

## Mindset

This is **exploration and ideation**, not documentation.

- Cast a wide net first, narrow later
- Web search for how others solved similar problems
- Look at open source implementations
- Question assumptions
- Generate many ideas, not just "safe" ones

---

## Process (Flexible)

### 1. Clarify the Problem

Quick chat with user:
- What are we really trying to solve?
- What constraints exist?
- What have you already considered?

### 2. Research Phase

**Web Search** (use WebSearch tool liberally):
- "best practices for {problem}"
- "{framework} {feature} implementation"
- "how to {solve problem} in {tech stack}"
- Look for blog posts, tutorials, GitHub discussions

**Find References:**
- Open source projects that solved this
- Libraries that could help
- Patterns from other ecosystems

**Codebase Exploration:**
- How do we handle similar things?
- What patterns already exist?
- What would feel native here?

### 3. Ideation

Generate ideas freely:
- Conventional approaches
- Unconventional approaches
- "What if we..." ideas
- Combinations of approaches
- Quick-and-dirty vs proper solutions

Don't filter too early. Quantity over quality initially.

### 4. Discussion

Share findings with user:
- "I found these interesting approaches..."
- "Company X solved it by..."
- "The tradeoff seems to be between..."
- "What if we tried..."

Use `AskUserQuestion` to get feedback:
- What resonates?
- What concerns do you have?
- Any constraints I missed?

### 5. Synthesis

Distill the conversation into a direction:
- What approach are we leaning toward?
- What are the key decisions?
- What's still uncertain?

---

## Output Options

### Option A: Lightweight Summary (default)

Just summarize in conversation:
```
We've decided to go with {approach} because {reasons}.

Key decisions:
- {decision 1}
- {decision 2}

Next: /create-task {feature-name}
```

### Option B: Design Doc (for complex features)

Only if the exploration was substantial and worth documenting.

Create `docs/designs/{feature-name}.md`:
```markdown
# Design: {Feature Name}

**Date:** {date}
**Status:** Explored

## Problem
{1-2 sentences}

## Research

**References found:**
- [{title}]({url}) - {what we learned}
- [{title}]({url}) - {what we learned}

**Codebase patterns:**
- `{file}` - {relevant pattern}

## Ideas Explored

### {Idea 1}
{Description, pros, cons}

### {Idea 2}
{Description, pros, cons}

## Direction

Going with: {chosen approach}

**Why:** {rationale}

**Key decisions:**
- {decision}: {choice} because {reason}

**Open questions:**
- {question}

---
Next: `/create-task {feature-name}`
```

---

## Tools to Use

| Tool | When |
|------|------|
| `WebSearch` | Find best practices, references, how others solved it |
| `WebFetch` | Read specific articles, docs, GitHub READMEs |
| `Task` (Explore) | Search codebase for patterns |
| `AskUserQuestion` | Get feedback, clarify constraints |
| `Glob/Grep` | Quick codebase checks |

**Web search is encouraged!** This is the brainstorming phase - gather information widely.

---

## Examples

**Good use of /design:**
- "Design a caching strategy" (many valid approaches)
- "Design real-time updates" (WebSocket vs SSE vs polling)
- "Design a plugin system" (architectural decision)

**Skip /design, use /create-task:**
- "Add a new API endpoint" (follow existing patterns)
- "Add a settings page" (standard CRUD)
- "Fix the login bug" (not a design problem)
