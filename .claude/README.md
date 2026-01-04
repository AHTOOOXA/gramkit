# Claude Code Orchestration Setup

**Version**: 1.0.0
**Created**: 2025-01-15
**Status**: Core architecture complete, skills layer pending

This directory contains the Claude Code configuration for the web application monorepo, implementing an **orchestration-first architecture** that maximizes context efficiency and enables parallel development.

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [File Structure](#file-structure)
- [How It Works](#how-it-works)
- [Usage Guide](#usage-guide)
- [Implemented Features](#implemented-features)
- [Backlog](#backlog)
- [Development Workflow](#development-workflow)
- [Best Practices](#best-practices)

---

## Architecture Overview

### The Problem We Solved

Previously, a monolithic 1100+ line `CLAUDE.md` file:
- ❌ Loaded entire context on every request
- ❌ Caused context window depletion quickly
- ❌ Made Claude handle both orchestration and implementation
- ❌ No parallelization of work
- ❌ Difficult to maintain and extend

### The Solution: 4-Layer Orchestration

```
┌─────────────────────────────────────────────────────────┐
│ Layer 0: Root CLAUDE.md (Orchestration Philosophy)     │
│ • When to delegate vs execute                           │
│ • Context preservation strategies                       │
│ • Quick command reference                               │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Layer 1:     │  │ Layer 2:     │  │ Layer 3:     │
│ Commands     │  │ Skills       │  │ Subagents    │
│ (Workflows)  │  │ (Procedures) │  │ (Execution)  │
└──────────────┘  └──────────────┘  └──────────────┘
│ User-triggered│  │ Auto-invoked │  │ Delegated    │
│ /plan         │  │ architecture-│  │ developer-   │
│ /develop      │  │ review       │  │ agent        │
│ /review       │  │ pytest-      │  │ (full-stack  │
│ /commit       │  │ testing      │  │ + tests)     │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Key Benefits

✅ **Context Efficiency**: Root CLAUDE.md only 345 lines (down from 1100+)
✅ **Parallel Execution**: Up to 10 concurrent Tasks
✅ **Isolated Context**: Each subagent has its own context window
✅ **Auto-Enforcement**: Skills enforce conventions automatically
✅ **Team Collaboration**: Configuration shared via git
✅ **Scalability**: Easy to add new domains/workflows

---

## File Structure

```
.claude/
├── README.md                    # This file
│
├── agents/                      # Layer 3: Subagents (Execution)
│   └── developer-agent.md       # Full-stack implementation (backend + frontend + tests)
│
├── commands/                    # Layer 1: Commands (Workflows)
│   ├── catchup.md               # Catch up on current work
│   ├── commit.md                # Clean up, lint, prepare commit
│   ├── create-task.md           # Create structured task plan
│   ├── develop.md               # Feature implementation
│   ├── execute-task.md          # Execute task phases
│   ├── explore.md               # Codebase exploration
│   ├── handoff.md               # Create handoff document
│   ├── plan.md                  # Architecture planning
│   ├── review.md                # Code review
│   └── review-task.md           # Task design review
│
├── shared/                      # Shared knowledge for all agents
│   ├── critical-rules.md        # Core/app split, whitespace, commands
│   ├── monorepo-structure.md    # Monorepo layout and navigation
│   ├── backend-patterns.md      # Backend 3-layer architecture
│   ├── frontend-patterns.md     # Frontend patterns (TanStack Query)
│   ├── vue-frontend.md          # Vue + shadcn-vue patterns
│   ├── react-frontend.md        # React + Next.js patterns
│   ├── testing-patterns.md      # Testing 80/15/5 pattern
│   ├── error-handling.md        # Error handling patterns
│   └── playwright-testing.md    # Browser testing
│
└── skills/                      # Layer 2: Skills (Auto-invoked)
    ├── architecture-review/     # Code/architecture reviewer
    ├── pytest-testing/          # Test writing guidelines
    ├── task-creation/           # Structured task planning
    └── task-execution/          # Phase-by-phase execution
```

---

## How It Works

### Layer 0: Root CLAUDE.md (Orchestration Guide)

**Location**: `/CLAUDE.md` (345 lines)

**Purpose**: High-level orchestration philosophy and quick reference

**Always Loaded**: Yes (part of every conversation)

**Contains**:
- 🎯 Orchestration philosophy (when to delegate vs execute)
- 📋 Quick command reference (Docker, testing, migrations)
- 🏗️ Architecture overview (patterns, file structure)
- 📖 Best practices (hot reload, type safety, code quality)

### Layer 1: Commands (User-Triggered Workflows)

**Location**: `.claude/commands/`

**Purpose**: Shortcut workflows that users explicitly trigger

**Invocation**: User types `/plan`, `/develop`, `/review`, or `/explore`

**How it works**:
```
User: /plan add payment refunds
  ↓
Command loads and expands
  ↓
Delegates to Plan agent (built-in)
  ↓
Returns architecture design
  ↓
User approves
  ↓
User: /develop
  ↓
Command orchestrates parallel implementation
  ↓
Done!
```

### Layer 2: Skills (Auto-Invoked Procedures)

**Location**: `.claude/skills/` (TO BE IMPLEMENTED)

**Purpose**: Standardized procedures that enforce conventions

**Invocation**: Automatic based on context (model-invoked)

**How it works**:
```
User: "Add Payment entity"
  ↓
Claude recognizes entity creation pattern
  ↓
backend-entity-core skill auto-invokes
  ↓
Guides through: model → repo → service → migration → tests
  ↓
Ensures conventions followed
```

**Status**: ⚠️ Not yet implemented (see Backlog)

### Layer 3: Subagents (Delegated Execution)

**Location**: `.claude/agents/`

**Purpose**: Specialized experts with isolated context

**Invocation**: Via Task tool from main orchestrator or commands

**How it works**:
```
Main thread: /develop payment refunds
  ↓
Task 1: backend-agent → Implement backend (parallel)
Task 2: frontend-agent → Implement frontend (parallel)
  ↓
Subagents work in isolated context
  ↓
Return concise summaries (implementation + tests)
  ↓
Main thread coordinates integration
  ↓
Done!
```

**Built-in agents also available**:
- **Plan**: Research and architecture design
- **Explore**: Codebase understanding and pattern identification

---

## Usage Guide

### Basic Workflow

**1. Planning Phase**
```
User: /plan add notification system
```
- Plan agent researches existing code
- Returns architecture design
- Shows task breakdown
- User approves or requests changes

**2. Development Phase**
```
User: /develop notification system
```
- Orchestrator delegates to developer-agent:
  - Backend: Models, repos, services, API
  - Frontend: Stores, components, screens
  - Tests: Following 80/15/5 pattern
- Main thread coordinates integration
- Returns summary with file paths

**3. Review Phase**
```
User: /review notification system
```
- Checks architecture patterns
- Verifies code quality
- Validates test coverage
- Returns detailed report with issues/recommendations

**4. Exploration (Anytime)**
```
User: /explore how payments work
```
- Explore agent searches codebase
- Identifies patterns and conventions
- Shows data flow
- Recommends approach

### Advanced Patterns

**Parallel Development**
```
User: "Add payments and notifications features"

Orchestrator:
1. /plan payments     → Plan agent researches
2. /plan notifications → Plan agent researches
3. User approves both
4. Launch parallel Tasks:
   - Task 1: developer-agent → payments (full-stack + tests)
   - Task 2: developer-agent → notifications (full-stack + tests)
5. Coordinate integration
```

**Direct Subagent Delegation**
```
User: "Create Payment refund repository method"

Orchestrator:
- Task: backend-agent
- Prompt: "Add get_refunds_by_user_id method to PaymentRepo"
- Returns: Summary with file path
```

---

## Implemented Features

### ✅ Root CLAUDE.md (Layer 0)
- [x] Orchestration philosophy
- [x] Context management strategies
- [x] Quick command reference
- [x] Architecture overview
- [x] Development best practices
- [x] Subagent/command/skill references

### ✅ Subagents (Layer 3)
- [x] **developer-agent**: Full-stack implementation (backend + frontend + tests)
  - Repository patterns (composition + aggregator)
  - Service patterns (lazy loading, cross-service calls)
  - Transaction management (flush, pessimistic locking)
  - API endpoints, bot handlers, worker jobs
  - Database migrations
  - Frontend: Stores, components, screens
  - Tests following 80/15/5 pattern

### ✅ Shared Knowledge
- [x] **testing-patterns.md**: Complete testing guide
  - Contract tests (80%), Business logic (15%), Regression (5%)
  - Pytest markers & fixtures
  - Snapshot testing

### ✅ Commands (Layer 1)
- [x] **/plan**: Delegates to Plan agent for architecture design
- [x] **/develop**: Orchestrates parallel implementation
- [x] **/review**: Comprehensive code review
- [x] **/explore**: Delegates to Explore agent for codebase understanding

---

## Backlog

### 🔴 High Priority

#### Skills Layer (Layer 2) Implementation

**Why Important**: Skills auto-enforce conventions and prevent common mistakes

**Tasks**:

1. **api-schema-sync** (CRITICAL - Most Commonly Forgotten)
   - Auto-invokes after backend API changes
   - Runs `make schema`
   - Verifies frontend types updated
   - Blocks work until types synced
   - **Impact**: Prevents type mismatches between frontend/backend
   - **Estimated effort**: 1-2 hours

2. **backend-entity-core** (HIGH VALUE)
   - Triggers: "create User entity", "add Payment model", "reusable entity"
   - Guides: model → CoreRequestsRepo → delegate → service → migration → tests
   - Ensures proper core/app separation
   - **Impact**: Standardizes core entity creation
   - **Estimated effort**: 2-3 hours

3. **backend-entity-app** (HIGH VALUE)
   - Triggers: "create Order entity", "add Product", "app entity"
   - Guides: model → RequestsRepo → service → migration → tests
   - No delegation needed (app-specific)
   - **Impact**: Standardizes app entity creation
   - **Estimated effort**: 2 hours

4. **frontend-store** (HIGH VALUE)
   - Triggers: "create store", "Pinia store", "manage payments state"
   - Guides: extract @schema types → create store → actions → getters
   - Enforces NO SERVICE LAYER pattern
   - **Impact**: Ensures type-safe API integration
   - **Estimated effort**: 2 hours

5. **transaction-safety** (MEDIUM - Critical for Payments)
   - Triggers: "payment", "balance deduction", "race condition"
   - Guides pessimistic locking patterns
   - Ensures transaction boundaries correct
   - **Impact**: Prevents race conditions in financial operations
   - **Estimated effort**: 2 hours

### 🟡 Medium Priority

6. **test-entity** (Consistency)
   - Triggers: "write tests", "test this entity"
   - Guides: proper markers → fixtures → contract/business logic split
   - Ensures >80% coverage
   - **Impact**: Standardizes test quality
   - **Estimated effort**: 2 hours

7. **bot-handler** (Telegram-Specific)
   - Triggers: "Telegram command", "bot handler", "aiogram handler"
   - Guides: handler creation → middleware usage → error handling
   - Ensures consistent bot patterns
   - **Impact**: Standardizes bot development
   - **Estimated effort**: 1-2 hours

8. **monorepo-split** (Advanced)
   - Triggers: "move to core", "make reusable", "extract to core"
   - Guides: dependency check → core migration → update imports
   - Maintains clean dependency graph
   - **Impact**: Keeps core/app boundaries clean
   - **Estimated effort**: 3 hours

### 🟢 Low Priority / Future Enhancements

9. **Additional Commands**
   - `/migrate` - Database migration workflow
   - `/refactor` - Code refactoring guidance
   - `/debug` - Debugging session orchestration
   - **Estimated effort**: 1 hour each

10. **Subagent Specialization**
    - `devops-agent` - Docker, CI/CD, deployment
    - `security-agent` - Security reviews, vulnerability checks
    - `performance-agent` - Performance optimization
    - **Estimated effort**: 3-4 hours each

11. **Documentation Integration**
    - Auto-generate API docs after changes
    - Update architecture diagrams
    - Create feature documentation
    - **Estimated effort**: 4-5 hours

---

## Development Workflow

### For Feature Development

**Recommended flow**:
```
1. /explore [feature area]          # Understand existing code
2. /plan [feature name]             # Create architecture design
3. Review plan with team            # Get approval
4. /develop [feature name]          # Parallel implementation
5. Manual testing                   # Verify functionality
6. /review [feature name]           # Quality check
7. Fix issues if any                # Address review findings
8. Create PR                        # Ready for merge
```

### For Bug Fixes

**Quick flow**:
```
1. /explore [bug area]              # Understand the issue
2. Direct fix (main thread)         # If simple
   OR
   /develop [bug fix]               # If complex
3. /review [bug fix]                # Verify fix
```

### For Refactoring

**Careful flow**:
```
1. /explore [code to refactor]      # Understand current structure
2. /plan [refactoring]              # Design approach
3. /develop [refactoring]           # Implement changes
4. /review [refactoring]            # Verify no regressions
5. Run full test suite              # Ensure everything works
```

---

## Best Practices

### For Users (Developers)

**Do:**
- ✅ Use `/plan` before implementing complex features
- ✅ Approve plans before running `/develop`
- ✅ Let subagents handle implementation details
- ✅ Run `/review` before creating PRs
- ✅ Use `/explore` when unfamiliar with code area
- ✅ Trust the orchestration system

**Don't:**
- ❌ Jump straight to `/develop` without planning
- ❌ Micromanage subagent implementation
- ❌ Mix orchestration and implementation in main thread
- ❌ Skip `/review` step
- ❌ Modify generated files (schema/api.d.ts)

### For Claude (Orchestrator)

**Do:**
- ✅ Delegate to subagents proactively
- ✅ Launch parallel Tasks when possible
- ✅ Ask subagents to return summaries, not full code
- ✅ Keep main context clean
- ✅ Create checkpoints between phases
- ✅ Use `/clear` if context gets cluttered

**Don't:**
- ❌ Read large files in main thread (delegate)
- ❌ Implement complex logic in main thread (delegate)
- ❌ Return full code listings (return summaries)
- ❌ Work sequentially when parallel is possible
- ❌ Pollute main context with implementation details

---

## Metrics & Success Criteria

### Context Efficiency
- **Before**: 1100+ lines loaded on every request
- **After**: 345 lines root + on-demand subagents
- **Improvement**: ~70% context reduction

### Development Speed
- **Before**: Sequential implementation only
- **After**: Up to 10 parallel Tasks
- **Improvement**: 3-5x faster for multi-component features

### Code Quality
- **Architecture compliance**: Automated via skills
- **Test coverage**: >80% (see `.claude/shared/testing-patterns.md`)
- **Convention adherence**: Guided by developer-agent
- **Review quality**: Standardized via /review command

---

## Contributing to This Setup

### Adding New Subagents

1. Create `.claude/agents/new-agent.md`
2. Define YAML frontmatter:
   ```yaml
   ---
   name: new-agent
   description: Brief description with trigger keywords
   tools: [Read, Write, Edit, Glob, Grep, Bash]
   ---
   ```
3. Document expertise domain comprehensively
4. Update root CLAUDE.md "Available Subagents" section

### Adding New Commands

1. Create `.claude/commands/new-command.md`
2. Define YAML frontmatter:
   ```yaml
   ---
   description: Brief description of workflow
   allowed-tools: Task, Read, Glob, Grep
   argument-hint: "[what user provides]"
   ---
   ```
3. Document workflow steps and orchestration pattern
4. Update root CLAUDE.md "Available Commands" section

### Adding New Skills

1. Create `.claude/skills/new-skill/SKILL.md`
2. Define YAML frontmatter:
   ```yaml
   ---
   name: new-skill
   description: Brief description with trigger keywords (critical for auto-invocation)
   allowed-tools: Read, Write, Edit, Bash
   ---
   ```
3. Document procedure step-by-step
4. Test trigger keyword recognition
5. Update root CLAUDE.md "Skills" section

---

## Maintenance

### Regular Updates Needed

**Monthly**:
- Review and update subagent expertise as patterns evolve
- Add new common procedures as skills
- Update command workflows based on team feedback

**Quarterly**:
- Audit context efficiency (measure actual token usage)
- Review success metrics (development speed, code quality)
- Gather team feedback on orchestration effectiveness

**As Needed**:
- Add new subagents for new domains (e.g., mobile, desktop)
- Update architecture patterns in root CLAUDE.md
- Retire unused commands or skills

---

## Version History

### v1.0.0 (2025-01-15) - Initial Release
- ✅ Created orchestration architecture (4 layers)
- ✅ Root CLAUDE.md reduced from 1100+ to 345 lines
- ✅ 3 specialized subagents implemented
- ✅ 4 workflow commands implemented
- ⏳ Skills layer designed but not implemented

---

## Support & Resources

**Documentation**:
- Root CLAUDE.md: Orchestration philosophy and quick reference
- Subagent files: Detailed domain expertise
- Command files: Workflow step-by-step guides
- Shared files: Cross-cutting patterns and tools
  - `.claude/shared/playwright-testing.md`: Browser testing for frontend validation

**External Resources**:
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Subagents Guide](https://docs.claude.com/en/docs/claude-code/sub-agents)
- [Skills Guide](https://docs.claude.com/en/docs/claude-code/skills)

**Team Contact**:
- For questions about this setup, consult this README
- For bugs or improvements, create an issue or discuss with team
- For new patterns, propose updates to relevant agent/command/skill

---

## License

This Claude Code configuration is part of the web application monorepo and follows the same license as the main project.
