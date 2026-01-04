# Phase Validation

## Validation Checklist

After developer-agent returns, verify:

```
Phase Validation:
- [ ] Agent returned successfully
- [ ] Tests reported as passing
- [ ] Commit hash provided
- [ ] Success criteria marked as met
```

## Validating Agent Results

**Parse agent response for:**

| Field | Expected | Action if Missing |
|-------|----------|-------------------|
| Files changed | List of paths | Ask agent to clarify |
| Tests | "Passing (N)" | Run `make test` manually |
| Commit | Short hash | Check `git log -1` |
| Success criteria | "Met" | Review each criterion |

## Success Criteria Validation

**From phase file, check each criterion:**

```markdown
## Success Criteria (from phase file)
- [ ] Model created at expected path
- [ ] Migration exists and applied
- [ ] Repository follows composition pattern
- [ ] Tests written and passing
```

**Validation methods:**

| Criterion Type | How to Validate |
|---------------|-----------------|
| File exists | Agent reports file path |
| Tests pass | Agent reports test count |
| Migration applied | Agent ran `make upgrade` |
| Pattern followed | Trust agent (invoked skill) |

## Post-Phase Validation

**Run after each implementation phase:**

```bash
# Verify tests still pass
make test APP={app}

# Verify no lint errors
make lint APP={app}

# Verify clean git status
git status
```

**If any fail:** Do not proceed, update CONTEXT.md with blocker.

## Integration Validation

**After phases that change backend API:**

```bash
# Regenerate frontend types
make schema APP={app}

# Verify frontend types
cd apps/{app}/frontend && pnpm typecheck
```

**After phases that add migrations:**

```bash
# Test rollback works
make downgrade APP={app}
make upgrade APP={app}
```

## Final Task Validation

**Before marking task complete:**

```
Final Validation:
- [ ] All phases marked Complete in README.md
- [ ] All tests passing: `make test APP={app}`
- [ ] Lint clean: `make lint APP={app}`
- [ ] CONTEXT.md updated to Complete status
- [ ] All commits created
```
