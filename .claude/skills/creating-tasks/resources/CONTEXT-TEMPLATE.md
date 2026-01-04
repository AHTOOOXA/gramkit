# CONTEXT.md Template

Use this template when creating CONTEXT.md for new tasks.

```markdown
# Task Context

**Last Updated:** {creation date}
**Current Phase:** 0 (not started)
**Status:** Not Started

## Key Decisions
None yet.

## Files Modified
None yet.

## Open Questions
- [ ] {Any questions identified during task creation}

## Blockers
None.

## Next Steps
1. Review README.md and phase files
2. Begin with Phase 00 (if exists) or Phase 01
```

## Update Protocol

**When to update CONTEXT.md:**
- After each phase completes
- When key decisions are made
- When blockers are encountered
- Before session ends (context preservation)

**What to update:**

| Field | When to Update |
|-------|----------------|
| Last Updated | Every update |
| Current Phase | Phase transitions |
| Status | State changes |
| Key Decisions | Architecture/approach choices |
| Files Modified | After implementation phases |
| Open Questions | When needing user input |
| Blockers | When stuck |
| Next Steps | After each phase |

## Example: Mid-Task CONTEXT.md

```markdown
# Task Context

**Last Updated:** 2025-01-15 14:30
**Current Phase:** 3 (Backend Services)
**Status:** In Progress

## Key Decisions
- Using composition pattern for NotificationService
- Storing notification preferences in user_settings table (not separate)
- WebSocket for real-time, fallback to polling

## Files Modified
- `core/backend/src/core/models/notification.py` - New model
- `apps/template/backend/src/app/infrastructure/database/repo/notifications.py` - Repo
- `apps/template/backend/src/app/migrations/versions/xxx_add_notifications.py` - Migration

## Open Questions
- [ ] Should notifications expire after 30 days or be kept forever?

## Blockers
None.

## Next Steps
1. Complete NotificationService.send() method
2. Add to RequestsService aggregator
3. Write contract tests
```
