---
description: Critical architectural review of task solution design
allowed-tools: "*"
argument-hint: "[task-name or path]"
---

# Review Task Architecture: $ARGUMENTS

**You are in ARCHITECTURE REVIEW MODE** - Critically analyze the proposed solution for gaps, over-engineering, and feasibility.

## Review Objective

**NOT checking documentation structure** - checking if the solution is:
- ✅ **Sound:** Architecturally correct for the problem
- ✅ **Minimal:** No unnecessary complexity
- ✅ **Complete:** No gaps or missing pieces
- ✅ **Feasible:** Each phase can actually be built as described
- ✅ **Robust:** Handles edge cases and failure modes
- ✅ **Aligned:** Follows project patterns correctly

---

## Review Process

### Step 1: Understand the Problem

Read task docs to extract:
1. **What problem are we solving?** (stated vs actual)
2. **What's the proposed solution?** (high-level approach)
3. **What's the scope?** (what changes, what doesn't)
4. **What are the phases?** (how we're building it)

### Step 2: Critical Analysis

For each phase AND the overall solution, ask:

#### Architecture Questions
- **Is this the right pattern?** Or are we forcing a pattern that doesn't fit?
- **Are we solving the root cause?** Or just treating symptoms?
- **What are we assuming?** Are those assumptions valid?
- **What could break?** Edge cases, race conditions, failure modes
- **What's missing?** Gaps in the design, unconsidered scenarios
- **What's unnecessary?** Over-engineering, premature optimization
- **Does it compose well?** Fits with existing architecture or creates friction?

#### Implementation Questions
- **Can this phase actually be built?** Dependencies, blockers, chicken-egg problems
- **Is the order correct?** Could we get stuck because phase N needs phase N+1?
- **Are the boundaries clear?** Core vs app, frontend vs backend, what goes where?
- **Is it testable?** Can we verify each phase works?
- **What's the rollback story?** If phase N fails, can we undo cleanly?

#### Minimalism Questions
- **Do we need all this?** Could we solve it with less?
- **Are we adding new patterns?** Why not use existing ones?
- **Is the scope creep hidden?** Are we sneaking in "nice to haves"?
- **Could we ship earlier?** Is there a smaller MVP we're missing?

#### Reality Check Questions
- **Has this been done before?** Learn from similar work in codebase
- **What will actually happen?** When we implement, what surprises await?
- **Time estimates realistic?** Or are we underestimating complexity?
- **Will it actually get used?** Or building something nobody needs?

### Step 3: Codebase Validation

**Don't trust the plan - verify against reality:**

1. **Check existing patterns:**
   - Grep for similar features already implemented
   - Read how they're structured
   - Compare with proposed approach
   - Identify deviations and question why

2. **Validate assumptions:**
   - If task says "we don't have X", search codebase to confirm
   - If task says "we'll use Y pattern", verify Y exists and works that way
   - If task assumes API shape, check actual API

3. **Find landmines:**
   - Search for related TODOs or FIXMEs
   - Check git history for previous attempts
   - Look for commented-out code that hints at problems
   - Review related test failures or skipped tests

### Step 4: Generate Critical Review

**IMPORTANT: Follow this exact output structure:**

```markdown
## Architecture Review: {Task Name}

**Problem Statement:** {What we're solving - restate clearly in 1-2 sentences}

**Proposed Solution:** {High-level approach - one paragraph summary}

**Overall Assessment:** {🟢 Sound | 🟡 Has Issues | 🔴 Fundamentally Flawed}

---

### 🎯 Solution Analysis

#### ✅ What's Good
{Genuinely good decisions - be specific:}
- **{Decision}**: {Why it's right} {What benefit it brings}
- **{Decision}**: {Why it's right} {What benefit it brings}

#### ⚠️ What's Questionable
{Things that need deeper thought:}
- **{Concern}**: {Why it's questionable} {What could go wrong} {Alternative approach?}
- **{Concern}**: {Why it's questionable} {What could go wrong} {Alternative approach?}

#### ❌ What's Wrong
{Fundamental flaws - only if they exist:}
- **{Flaw}**: {Why it's wrong} {Impact if not fixed} {What to do instead}

---

### 🔍 Phase-by-Phase Analysis

{Analyze EVERY phase - this is critical}

#### Phase 01: {Phase Name}

**Goal:** {What this phase achieves in 1 sentence}

**Approach:** {How the phase plans to achieve it - 1-2 sentences}

**Analysis:**
- ✅ **Strengths:** {What's good about this phase}
- ⚠️ **Concerns:** {Risks, assumptions, dependencies}
- ❓ **Questions:** {Unanswered questions about feasibility}

**Dependencies:**
- Requires: {What must exist before this phase}
- Blocks: {What depends on this phase completing}
- Circular: {Any chicken-egg problems}

**Testability:** {How do we verify this phase worked?}

**Recommendation:** {✅ Proceed | ⚠️ Modify | 🔄 Split | ❌ Skip}
{If not "Proceed", explain why and what to do instead}

---

#### Phase 02: {Phase Name}

{Same structure as Phase 01}

---

{Repeat for ALL phases}

---

### 🚨 Critical Gaps

**Missing Pieces:**
1. **{Gap}**: {What's not addressed} {Why it matters} {Which phase should handle it}
2. **{Gap}**: {What's not addressed} {Why it matters} {Which phase should handle it}

**Edge Cases Not Covered:**
1. **{Scenario}**: {What happens in this case?} {Current plan doesn't handle it because...}
2. **{Scenario}**: {What happens in this case?} {Current plan doesn't handle it because...}

**Failure Modes:**
1. **{What fails}**: {When/how it could fail} {Impact} {Mitigation needed}
2. **{What fails}**: {When/how it could fail} {Impact} {Mitigation needed}

{If none, explicitly state: "No critical gaps identified"}

---

### 🏗️ Architectural Issues

{Only include sections that have actual issues}

#### Pattern Misuse
{If patterns are being misused:}
- **{Pattern Name}**:
  - **Misuse:** {How it's being misused}
  - **Why Wrong:** {Why this violates the pattern}
  - **Correct Usage:** {How to use it properly}
  - **Impact:** {What breaks if we misuse it}

#### Over-Engineering
{If solution is too complex:}
- **{Component/Aspect}**:
  - **Why Over-Engineered:** {What makes it too complex}
  - **Simpler Alternative:** {How to simplify}
  - **Trade-off:** {What we lose by simplifying}

#### Under-Engineering
{If solution is too simple:}
- **{Component/Aspect}**:
  - **What's Missing:** {Critical functionality not included}
  - **Why Needed:** {Why we can't skip this}
  - **How Complex:** {What needs to be added}

#### Coupling Issues
{If creating unwanted dependencies:}
- **{What's Coupled}**:
  - **Why Bad:** {Why this coupling is problematic}
  - **Impact:** {How it limits future changes}
  - **Decoupling:** {How to break the coupling}

#### Abstraction Problems
{Wrong abstraction level:}
- **{Abstraction}**:
  - **Issue:** {Too abstract or too concrete}
  - **Why Wrong:** {Problems this creates}
  - **Right Level:** {Where abstraction should be}

{If no issues: "No significant architectural issues identified"}

---

### 🔬 Codebase Reality Check

**Existing Patterns Found:**
{Search codebase and report what actually exists:}
- **{Pattern/Feature}** at `{file:line}`:
  - **Current Implementation:** {How it's actually done}
  - **Plan Difference:** {How plan differs from reality}
  - **Implication:** {Does this affect our approach?}

**Assumptions Validated:**
✅ **{Assumption}**: Confirmed - {evidence from codebase}
❌ **{Assumption}**: Wrong - {actual reality is different because...}
⚠️ **{Assumption}**: Partially true - {nuance from codebase}

**Previous Attempts:**
{Search git history, commented code, TODOs:}
- **{Location}**: {What was tried} {Why it failed/succeeded} {Lessons to apply}

**Hidden Dependencies:**
{Things in codebase that affect this:}
- **{Dependency}** in `{file:line}`: {How it impacts our plan}

{If nothing found: "No conflicting patterns or previous attempts found"}

---

### 🎲 Risk Assessment

| Risk | Probability | Impact | Current Mitigation | Recommended Action |
|------|-------------|--------|-------------------|-------------------|
| {Risk} | {Low/Med/High} | {Low/Med/High/Critical} | {What plan says (or "None")} | {What we should do} |
| {Risk} | {Low/Med/High} | {Low/Med/High/Critical} | {What plan says (or "None")} | {What we should do} |

**Overall Risk Level:** {🟢 Low | 🟡 Medium | 🔴 High}

**Top 3 Risks Explained:**
1. **{Risk}**: {Why it's the biggest concern} {Probability × Impact} {How to mitigate}
2. **{Risk}**: {Why it's concerning} {Probability × Impact} {How to mitigate}
3. **{Risk}**: {Why it's concerning} {Probability × Impact} {How to mitigate}

---

### 💡 Alternative Approaches

**Could we instead...?**

#### Alternative 1: {Approach Name}
- **Approach:** {How we'd solve it differently}
- **Pros:**
  - {Benefit 1}
  - {Benefit 2}
- **Cons:**
  - {Drawback 1}
  - {Drawback 2}
- **Verdict:** {✅ Better | ❌ Worse | ⚖️ Equivalent | 🤔 Worth Considering}
- **Reasoning:** {Why this verdict}

#### Alternative 2: {Approach Name}
{Same structure}

**Minimal Viable Solution:**
{What's the smallest thing that solves the core problem?}
- **MVP Scope:** {Bare minimum to solve problem}
- **Cut from Plan:** {What we'd remove}
- **Add Back Later:** {What we'd defer to v2}
- **Time Savings:** {How much faster MVP is}
- **Trade-off:** {What we lose}

---

### ⏱️ Time Estimate Reality Check

**Claimed Estimate:** {X-Y hours total}

**Phase-by-Phase Reality Check:**
{For each phase:}
- **Phase {N}**: Claimed {X}h → Realistic {Y}h
  - {Why different if different}

**Reality Check:**
- **Underestimated Areas:**
  - {What will take longer}: {Why} {Add +{N}h}
- **Overestimated Areas:**
  - {What will be faster}: {Why} {Reduce -{N}h}
- **Hidden Complexity:**
  - {What's not accounted for}: {Time needed} {Add +{N}h}

**Revised Estimate:** {A-B hours}
**Reasoning:** {Why this is more realistic}
**Confidence:** {Low/Medium/High} {Why}

---

### ✅ Recommendations

#### Must Fix Before Starting
{Critical blockers - if any:}
1. **{Critical Issue}**:
   - **Problem:** {What's wrong}
   - **Fix:** {Specific action to take}
   - **Effort:** {Time to fix}

#### Should Modify
{Major improvements - if any:}
1. **{Major Issue}**:
   - **Problem:** {What could be better}
   - **Fix:** {How to improve}
   - **Benefit:** {Why worth doing}

#### Consider
{Nice-to-haves - if any:}
1. **{Suggestion}**:
   - **Improvement:** {What could be enhanced}
   - **Benefit:** {Why it might help}
   - **Trade-off:** {Cost vs benefit}

#### Phase Reordering
{If phases should be reordered - otherwise omit:}
- **Current Order:** Phase {A} → {B} → {C}
- **Better Order:** Phase {A} → {C} → {B}
- **Reasoning:** {Why reordering helps} {What dependency this resolves}

---

### 🎯 Final Verdict

**Ready to execute:** {✅ Yes | ⚠️ With Modifications | ❌ No}

**If Yes:**
{Brief confirmation}
- Good to proceed as planned
- Watch for: {1-2 key risks to monitor}
- Validate: {1-2 assumptions to verify during execution}

**If With Modifications:**
{What must change:}
- **Before Starting:** {Critical changes needed}
- **During Execution:** {Adjustments to make}
- **After Changes:** Re-review {specific aspects} before proceeding

**If No:**
{Why fundamentally flawed:}
- **Core Problem:** {What's wrong with approach}
- **Needed:** {What complete rethinking is required}
- **Next Steps:** {How to redesign}

---

### 📝 Questions to Answer Before Starting

{Unanswered questions that need research:}
1. **{Question}**:
   - **Why Critical:** {Why we need to know}
   - **How to Find Out:** {Research approach}
   - **Blocks:** {Which phase needs this answer}

2. **{Question}**: {Same structure}

{If no questions: "All critical questions answered by plan"}

---

### 🎓 Lessons for Future Tasks

{Patterns to apply or avoid:}
- ✅ **Good Pattern:** {What worked well in this design} {Apply to: ...}
- ❌ **Anti-Pattern:** {What to avoid} {Why problematic}
- 💡 **Insight:** {Learning from this review} {Application: ...}
```

---

## Example Output

Here's what a real review would look like:

### Example: Loading States Task Review

```markdown
## Architecture Review: Loading States Standardization

**Problem Statement:** Users see jarring empty → loaded transitions. No consistent loading patterns across stores. Buttons don't show loading state during operations.

**Proposed Solution:** Create reusable loading components in core, standardize store loading pattern (isLoading/isValidating/lastFetched), implement skeleton loaders with progressive loading, add button loading states, and implement advanced patterns (optimistic updates, stale-while-revalidate).

**Overall Assessment:** 🟡 Has Issues

---

### 🎯 Solution Analysis

#### ✅ What's Good
- **Core component library**: Centralizing loading components prevents duplication across 3 apps
- **Store pattern standardization**: Consistent isLoading/isValidating pattern makes code predictable
- **Progressive loading**: Skeleton → content transition is UX best practice
- **Phase breakdown**: Logical sequence from foundation (stores) → components → integration

#### ⚠️ What's Questionable
- **Optimistic updates scope**: Adding optimistic updates for "critical operations" is vague - which operations? This could expand scope significantly
- **Stale-while-revalidate everywhere**: Is SWR needed for all data or just user-facing queries? May be over-engineering for admin data
- **Three apps simultaneously**: Updating template, template-react, AND tarot in parallel could multiply effort if issues found

#### ❌ What's Wrong
- **Missing error states**: Plan focuses on loading but doesn't address error → retry patterns. Loading states fail into error states - need consistent error handling too
- **No performance baseline**: Claims to improve "perceived performance" but doesn't measure current loading times. How will we validate improvement?

---

### 🔍 Phase-by-Phase Analysis

#### Phase 01: Store Standardization

**Goal:** Add isLoading, isValidating, lastFetched to all stores

**Approach:** Update userStore, paymentsStore, subscriptionStore, appStore in all 3 apps

**Analysis:**
- ✅ **Strengths:** Foundation for all other phases. Clear success criteria.
- ⚠️ **Concerns:**
  - 12 stores to update (4 stores × 3 apps). Time estimate of 3-4h seems tight.
  - What if stores already have different loading patterns? Task assumes they don't.
  - Backend API contracts might need updating if adding "lastFetched" persistence.
- ❓ **Questions:**
  - Do we need backend changes for lastFetched persistence?
  - Are there other stores beyond these 4?

**Dependencies:**
- Requires: Nothing
- Blocks: All other phases (they assume this pattern exists)
- Circular: None

**Testability:** Check each store has the 3 new properties. Run existing tests.

**Recommendation:** ⚠️ Modify
- Add 1h for codebase audit to find ALL stores (not just 4 listed)
- Clarify if backend changes needed
- Add migration guide for existing loading patterns

---

#### Phase 02: Loading Component Library

**Goal:** Create LoadingSpinner, LoadingScreen, Skeleton*, ContentState components in core

**Approach:** Build 8 components in Vue + React, export from core/frontend/src/ui/loading/

**Analysis:**
- ✅ **Strengths:**
  - Reusable across all apps
  - Skeleton variants cover common use cases
- ⚠️ **Concerns:**
  - 8 components × 2 frameworks = 16 components in 4-5h is aggressive
  - No mention of Telegram theme integration. Do skeletons respect dark mode?
  - React version uses what UI library? Plan assumes PrimeVue but React template might differ
- ❓ **Questions:**
  - Do skeleton animations work performantly on low-end mobile?
  - Are skeleton shapes customizable or fixed?

**Dependencies:**
- Requires: Phase 01 (stores need loading state to trigger skeletons)
- Blocks: Phase 04 (progressive loading needs ContentState)
- Circular: None

**Testability:** Visual test in each app. Component renders without errors.

**Recommendation:** ⚠️ Modify
- Increase estimate to 6-7h (16 components is a lot)
- Add Telegram theme integration explicitly
- Create 2-3 base components first, test thoroughly, then variants

---

#### Phase 03: Button Loading States

**Goal:** Add loading prop to Button component, update all forms

**Approach:** Enhance Button in Vue + React, update form usages

**Analysis:**
- ✅ **Strengths:** High impact, simple change
- ⚠️ **Concerns:**
  - "All forms" - how many? If 20+ forms this could be 4-5h alone
  - What about buttons outside forms? (Navigation, actions, etc.)
  - Disabled vs loading state - are they mutually exclusive?
- ❓ **Questions:**
  - Does loading state disable the button automatically?
  - What about keyboard accessibility during loading?

**Dependencies:**
- Requires: Phase 02 (needs LoadingSpinner for button)
- Blocks: None
- Circular: None

**Testability:** Click button, see spinner. Button disabled during operation.

**Recommendation:** ⚠️ Modify
- Count actual forms/buttons first
- Revise time estimate based on count
- Define loading + disabled interaction

---

#### Phase 04: Progressive Loading & ContentState

**Goal:** Implement skeleton → data fade transition

**Approach:** Create ContentState wrapper, update Profile/Payments/Subscription pages

**Analysis:**
- ✅ **Strengths:** This is where UX improvement happens
- ⚠️ **Concerns:**
  - CSS transitions can be tricky cross-browser
  - What if data loads instantly (cached)? Still show skeleton flash?
  - "3 pages" understates it - 3 pages × 3 apps = 9 pages
- ❓ **Questions:**
  - Minimum skeleton display time to avoid flash?
  - What about lists that load incrementally?

**Dependencies:**
- Requires: Phase 01, 02 (needs stores + skeletons)
- Blocks: None
- Circular: None

**Testability:** Throttle network, observe skeleton → content transition

**Recommendation:** ⚠️ Modify
- Add minimum display time (200ms) for skeletons
- Increase estimate to 5-6h (9 pages not 3)
- Test on slow connections explicitly

---

#### Phase 05: Advanced Patterns

**Goal:** Add optimistic updates, stale-while-revalidate, loading timeouts

**Approach:** Implement patterns for "critical operations"

**Analysis:**
- ⚠️ **Concerns:**
  - Which operations are critical? This is completely undefined
  - Optimistic updates require rollback logic - complex!
  - SWR conflicts with always-fresh data requirements (payments)
  - Loading timeouts - what happens on timeout? Retry? Fail?
- ❓ **Questions:**
  - What's the rollback strategy for failed optimistic updates?
  - Which stores need SWR vs always fresh?
  - Timeout duration per operation or global?

**Dependencies:**
- Requires: Phase 01-04 (full foundation)
- Blocks: None
- Circular: None

**Testability:** ???

**Recommendation:** 🔄 Split into two phases
- Phase 5A: SWR for read operations (clear scope)
- Phase 5B: Optimistic updates for writes (research + design first)
- Defer loading timeouts to v2 (edge case)

---

#### Phase 06: App Initialization

**Goal:** Add branded loading screen during app startup

**Approach:** Update initialization in all 3 apps, add route-level loading

**Analysis:**
- ✅ **Strengths:** Professional polish
- ⚠️ **Concerns:**
  - What if app loads instantly? Show spinner anyway?
  - Next.js already has loading.tsx - is this compatible?
  - "Route-level loading" - every route or just slow ones?

**Dependencies:**
- Requires: Phase 02 (needs LoadingScreen component)
- Blocks: None
- Circular: None

**Testability:** App startup shows branded screen

**Recommendation:** ✅ Proceed
- But clarify Next.js integration
- Define which routes need loading (not all)

---

### 🚨 Critical Gaps

**Missing Pieces:**
1. **Error state handling**: Plan covers loading → success but not loading → error → retry. Need consistent error patterns.
2. **Performance metrics**: No way to measure if this actually improves perceived performance. Need timing instrumentation.
3. **Accessibility**: No mention of screen readers announcing loading states or ARIA live regions.

**Edge Cases Not Covered:**
1. **Instant loads (cached)**: What if data loads in <50ms? Still flash skeleton?
2. **Multiple concurrent loads**: If user triggers 3 actions simultaneously, how do loading states compose?
3. **Background refresh failures**: If SWR refresh fails, do we show error or keep stale data?

**Failure Modes:**
1. **Optimistic update fails**: User sees success → rollback. Jarring UX. Need confirmation pattern.
2. **Skeleton never resolves**: If API hangs, skeleton shows forever. Need timeout.
3. **Animation performance**: Skeleton animations on low-end devices could jank.

---

### 🏗️ Architectural Issues

#### Over-Engineering
- **Phase 05 scope**: Adding optimistic updates + SWR + timeouts is premature. Start with basic loading → success/error first. Can add advanced patterns in v2 once basics are proven.

#### Under-Engineering
- **Error states**: Only addressing loading, not the full loading → success/error state machine. This is incomplete.

#### Abstraction Problems
- **ContentState component**: Proposed as generic wrapper but usage is unclear. Is it `<ContentState :loading :error :data>` or does it infer from store? Abstraction level unclear.

---

### 🔬 Codebase Reality Check

**Existing Patterns Found:**
- **appStore.isLoading** at `apps/template/frontend/src/app/store/appStore.ts:15`:
  - **Current Implementation:** Simple boolean isLoading
  - **Plan Difference:** Plan adds isValidating and lastFetched
  - **Implication:** Pattern already exists, extending it (not creating new) ✅

- **LoadingSpinner** at `core/frontend/src/ui/LoadingSpinner.vue`:
  - **Current Implementation:** Basic spinner component exists!
  - **Plan Difference:** Plan says "create LoadingSpinner" but it exists
  - **Implication:** Should extend existing, not recreate ⚠️

**Assumptions Validated:**
✅ **Store pattern**: Confirmed stores use Pinia (Vue) and have loading states
❌ **No loading components**: Wrong - LoadingSpinner already exists in core
⚠️ **4 stores**: Partially true - found 5 stores (missed readingsStore in tarot)

**Previous Attempts:**
- None found

**Hidden Dependencies:**
- **Telegram theme** in `core/frontend/src/composables/useTelegramTheme.ts`: Skeleton colors must respect theme. Plan doesn't mention this.

---

### 🎲 Risk Assessment

| Risk | Probability | Impact | Current Mitigation | Recommended Action |
|------|-------------|--------|-------------------|-------------------|
| Time underestimated (3 apps) | High | Medium | None | Multiply estimates by 2-2.5x for 3-app work |
| Optimistic updates complexity | High | High | None | Defer to v2 or separate task |
| Skeleton flash on fast loads | Medium | Low | None | Add minimum display time |
| Accessibility violations | Medium | Medium | None | Add ARIA annotations |
| Animation performance on mobile | Low | Medium | None | Test on low-end devices |

**Overall Risk Level:** 🟡 Medium

**Top 3 Risks Explained:**
1. **Optimistic updates backfire**: High probability we underestimate rollback complexity. High impact if UX feels broken on failures. Mitigation: Cut from v1, research first.
2. **Three apps multiply effort**: High probability issues found in one app need fixing in all three. Medium impact on timeline. Mitigation: Do one app fully first, then replicate.
3. **Accessibility oversight**: Medium probability we ship without screen reader support. Medium impact (excludes users). Mitigation: Add ARIA requirements to success criteria.

---

### 💡 Alternative Approaches

#### Alternative 1: Incremental Rollout (Single App First)
- **Approach:** Implement all phases in Tarot first, then replicate to templates once proven
- **Pros:**
  - Find issues early in one codebase
  - Validate patterns before replicating
  - Easier to rollback if approach wrong
- **Cons:**
  - Templates diverge temporarily
  - Tarot users are "guinea pigs"
- **Verdict:** ✅ Better
- **Reasoning:** Lower risk, faster learning

#### Alternative 2: MVP (Loading Only, No Advanced Patterns)
- **Approach:** Cut Phase 05 entirely. Just do: store pattern + components + basic loading
- **Pros:**
  - Ship faster (cut 4-5h)
  - Simpler, less can go wrong
  - Can add advanced patterns later based on real need
- **Cons:**
  - Less "complete"
  - May need to revisit stores later for SWR
- **Verdict:** 🤔 Worth Considering
- **Reasoning:** Get 80% of value with 60% of effort

**Minimal Viable Solution:**
- **MVP Scope:**
  - Phase 01: Store isLoading only (skip isValidating, lastFetched)
  - Phase 02: Just LoadingSpinner and basic Skeleton (skip variants)
  - Phase 03: Button loading states
  - Phase 04: Skip (or just 1 page as example)
  - Phase 05: Skip
  - Phase 06: Skip
- **Cut from Plan:** Progressive loading, advanced patterns, app initialization
- **Add Back Later:** Once basic loading proven, iterate
- **Time Savings:** 18-22h → 8-10h
- **Trade-off:** Less polished, but functional faster

---

### ⏱️ Time Estimate Reality Check

**Claimed Estimate:** 18-22 hours

**Phase-by-Phase Reality Check:**
- **Phase 01**: Claimed 3-4h → Realistic 5-6h (12 stores is a lot)
- **Phase 02**: Claimed 4-5h → Realistic 7-8h (16 components + Telegram theme)
- **Phase 03**: Claimed 2-3h → Realistic 4-5h (need to count forms first)
- **Phase 04**: Claimed 3-4h → Realistic 6-7h (9 pages not 3)
- **Phase 05**: Claimed 4-5h → Realistic 8-10h (optimistic updates are complex)
- **Phase 06**: Claimed 2-3h → Realistic 3-4h (seems reasonable)

**Reality Check:**
- **Underestimated Areas:**
  - Three apps multiply effort: Add +40% across all phases
  - Optimistic updates rollback: Add +3h for complexity
  - Telegram theme integration: Add +2h not mentioned
- **Overestimated Areas:**
  - Some components exist already: Reduce -2h
- **Hidden Complexity:**
  - Error state handling missing: Add +4h
  - Accessibility (ARIA): Add +3h
  - Performance testing: Add +2h

**Revised Estimate:** 32-40 hours
**Reasoning:** 3 apps × 6 phases with proper error handling and a11y
**Confidence:** Medium (could go higher if issues found)

---

### ✅ Recommendations

#### Must Fix Before Starting
1. **Define error handling strategy**:
   - **Problem:** Only addresses loading, not loading → error → retry
   - **Fix:** Add Phase 02B: Error state patterns (ErrorDisplay component, retry logic)
   - **Effort:** +4h

2. **Audit existing components**:
   - **Problem:** LoadingSpinner already exists but plan says "create"
   - **Fix:** Search core/frontend for all loading-related components, extend not recreate
   - **Effort:** +1h

3. **Cut or defer Phase 05**:
   - **Problem:** Optimistic updates are complex, vague scope
   - **Fix:** Defer to separate task after basics proven
   - **Effort:** Saves 8-10h

#### Should Modify
1. **Incremental app rollout**:
   - **Problem:** Doing 3 apps in parallel multiplies risk
   - **Fix:** Tarot first → validate → then templates
   - **Benefit:** Find issues early

2. **Add accessibility requirements**:
   - **Problem:** No mention of ARIA or screen readers
   - **Fix:** Add ARIA live regions for loading announcements
   - **Benefit:** Inclusive design

3. **Count forms/pages first**:
   - **Problem:** Estimates assume small numbers
   - **Fix:** Audit before committing to timeline
   - **Benefit:** Realistic timeline

#### Consider
1. **Performance instrumentation**:
   - **Improvement:** Add timing metrics to measure perceived performance
   - **Benefit:** Validate improvement objectively
   - **Trade-off:** +2h but proves value

#### Phase Reordering
- **Current Order:** Phase 01 → 02 → 03 → 04 → 05 → 06
- **Better Order:** Phase 01 → 02 → 02B (errors) → 03 → 04 → 06, defer 05
- **Reasoning:** Error handling is foundational, optimistic updates are advanced. Build solid base first.

---

### 🎯 Final Verdict

**Ready to execute:** ⚠️ With Modifications

**What must change:**
- **Before Starting:**
  - Audit existing loading components (don't recreate)
  - Define error state handling (add Phase 02B)
  - Cut Phase 05 (defer optimistic updates to v2)
  - Count forms/pages to revise estimates

- **During Execution:**
  - Start with Tarot only (validate before replicating)
  - Add ARIA live regions for accessibility
  - Test on low-end devices for animation performance

- **After Changes:**
  - Revised estimate: 24-30h (not 18-22h)
  - Re-review Phase 05 scope if you decide to keep it

---

### 📝 Questions to Answer Before Starting

1. **How many forms/buttons exist across all apps?**:
   - **Why Critical:** Drives Phase 03 time estimate
   - **How to Find Out:** `grep -r "AppButton\|BaseButton" apps/*/frontend/src`
   - **Blocks:** Phase 03 planning

2. **What error patterns already exist?**:
   - **Why Critical:** Need consistency with existing error handling
   - **How to Find Out:** Search for error state management in stores
   - **Blocks:** Phase 02B design

3. **Which operations need optimistic updates?**:
   - **Why Critical:** Defines Phase 05 scope (if kept)
   - **How to Find Out:** User research + analytics on frustrating waits
   - **Blocks:** Phase 05 (or decision to defer)

---

### 🎓 Lessons for Future Tasks

- ✅ **Good Pattern:** Building component library in core first prevents duplication. Apply to: Any shared UI.
- ❌ **Anti-Pattern:** Assuming component doesn't exist without checking. Why problematic: Wastes time recreating.
- 💡 **Insight:** Three apps means 3× effort, not 1×. Application: Always multiply cross-app estimates by app count.
```

---

## Review Philosophy

**Be skeptical, not cynical:**
- Question everything, but fairly
- Look for what's wrong, but acknowledge what's right
- Suggest alternatives, don't just criticize
- Focus on making it better, not perfect

**Prioritize:**
1. **Correctness** > Elegance (does it work?)
2. **Simplicity** > Completeness (minimal solution?)
3. **Feasibility** > Ambition (can we build it?)
4. **Maintainability** > Performance (can we maintain it?)

**Red flags to watch for:**
- 🚩 New patterns when existing ones would work
- 🚩 "This will be easy" for complex problems
- 🚩 Missing error handling / edge cases
- 🚩 Tight coupling between unrelated components
- 🚩 Premature optimization
- 🚩 Scope creep disguised as "while we're at it"
- 🚩 Solutions looking for problems
- 🚩 Copy-paste from other projects without adaptation

---

## How to Use This Review

### For Task Creator
Use review to:
- Validate technical approach
- Identify gaps before starting
- Get alternative perspectives
- Refine time estimates
- Improve phasing

### For Task Executor
Use review to:
- Understand risks upfront
- Know what to watch for
- Have contingency plans
- Question the plan if reality differs
- Make informed decisions

### For Both
- Not all recommendations need to be implemented
- Weigh trade-offs explicitly
- Document decisions and rationale
- Revisit if assumptions change
- Learn patterns for future tasks

---

## After Review

**If fundamentally flawed:**
1. Stop - don't execute as-is
2. Identify root cause of flaw
3. Redesign approach
4. Re-review before starting

**If has issues:**
1. Prioritize fixes (critical vs nice-to-have)
2. Update task docs with changes
3. Document known risks
4. Proceed with caution

**If sound:**
1. Document review findings
2. Note areas to watch during execution
3. Proceed with confidence
4. Validate assumptions as you go
