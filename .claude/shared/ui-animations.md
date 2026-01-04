# Animation Patterns Guide (Vue & React)

This guide documents animation patterns for creating premium, polished UI experiences. Works identically for **Vue and React** since all animations use `tailwindcss-motion` CSS classes.

**References:**
- [tailwindcss-motion](https://github.com/romboHQ/tailwindcss-motion) - Main animation library
- [Tailwind CSS Animation Docs](https://tailwindcss.com/docs/animation) - Built-in utilities
- [tailwindcss-animate](https://github.com/jamiebuilds/tailwindcss-animate) - Used by shadcn/ui

---

## Framework Syntax Quick Reference

The animation classes are identical - only template syntax differs:

```tsx
// React
<div className="motion-preset-fade motion-duration-[0.3s]">
<p className={isActive ? 'motion-preset-pop' : ''}>
<span key={counter}>  {/* re-triggers animation */}
<div style={{ animationDelay: `${index * 50}ms` }}>
```

```vue
<!-- Vue -->
<div class="motion-preset-fade motion-duration-[0.3s]">
<p :class="isActive && 'motion-preset-pop'">
<span :key="counter">  <!-- re-triggers animation -->
<div :style="{ animationDelay: `${index * 50}ms` }">
```

---

## ⚠️ CRITICAL: Tailwind v4 Anti-Patterns

> **TL;DR:** Use inline Tailwind classes. Don't create JS objects or `@utility` shortcuts to group animation classes. If you need reuse, create components (React components or Vue components).

### The Anti-Pattern: JS Class Dictionaries

**DO NOT DO THIS:**
```tsx
// ❌ ANTI-PATTERN - lib/animations.ts
export const hover = {
  lift: 'transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg',
  press: 'transition-transform duration-150 active:scale-[0.98]',
};

export const feedback = {
  pop: 'motion-preset-pop motion-duration-[0.2s]',
  shake: 'motion-preset-shake motion-duration-[0.4s]',
};

// ❌ Using it
import { hover, feedback } from '@/lib/animations';
<Button className={cn(hover.press, hover.lift)}>Click</Button>
```

**Why it's wrong:**
- Hides what the element actually does - must jump to another file
- Breaks Tailwind IntelliSense and autocomplete
- Breaks Prettier class sorting
- Creates indirection that defeats utility-first purpose
- JS bundle always includes entire object (no tree-shaking by Tailwind)

### The Anti-Pattern: @utility for Class Grouping

**DO NOT DO THIS:**
```css
/* ❌ ANTI-PATTERN - Using @utility to group existing utilities */
@utility hero-blur {
  @apply motion-blur-in-[10px] motion-scale-in-[0.95] motion-opacity-in-[0%];
}

@utility btn-hover {
  @apply hover:-translate-y-0.5 hover:shadow-lg transition-all;
}
```

**Why it's wrong:**
- `@utility` is for CSS features Tailwind doesn't have, NOT for grouping existing utilities
- Adam Wathan (Tailwind creator): *"The way Tailwind is intended to be used is as utility classes directly in your HTML"*
- Same problems as JS dictionaries - hides implementation

### ✅ Correct Approach: Inline Classes

```tsx
// ✅ CORRECT - Inline Tailwind classes
<Button className="transition-all duration-150 active:scale-[0.98] hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/20">
  Click me
</Button>

<h1 className="text-2xl font-bold motion-blur-in-[10px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.7s] motion-ease-spring-smooth">
  {title}
</h1>
```

**Yes, the classes are long. That's intentional:**
- You see exactly what the element does
- Tailwind IntelliSense works
- Prettier sorts classes automatically
- Easy to find/replace across codebase
- No indirection to understand behavior

### ✅ Correct Approach: Components for Reuse

If you have repeated patterns, create **components** (not CSS/JS abstractions):

```tsx
// ✅ React - Component abstraction
function InteractiveButton({ children, className, ...props }) {
  return (
    <Button
      className={cn(
        "transition-all duration-150 active:scale-[0.98] hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/20",
        className
      )}
      {...props}
    >
      {children}
    </Button>
  );
}
```

```vue
<!-- ✅ Vue - Component abstraction -->
<script setup>
import { cn } from '@/lib/utils'
defineProps(['class'])
</script>

<template>
  <Button :class="cn(
    'transition-all duration-150 active:scale-[0.98] hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/20',
    $props.class
  )">
    <slot />
  </Button>
</template>
```

### When @utility IS Appropriate

Only use `@utility` for CSS features Tailwind doesn't provide:

```css
/* ✅ GOOD - CSS property Tailwind doesn't have */
@utility scrollbar-hidden {
  &::-webkit-scrollbar {
    display: none;
  }
}

/* ✅ GOOD - Complex pseudo-selector */
@utility selection-primary {
  &::selection {
    background-color: var(--color-primary);
    color: white;
  }
}

/* ✅ GOOD - Functional utility with dynamic values */
@utility text-stroke-* {
  -webkit-text-stroke-width: --value(integer)px;
  -webkit-text-stroke-color: --value(--color-*);
}
```

### Tailwind v4 Abstraction Hierarchy

1. **First choice: Inline utilities** - Just use classes directly in templates
2. **Second choice: Components** - Vue/React components for repeated UI patterns
3. **Last resort: @utility/@apply** - Only for missing CSS features

### Summary Table

| Approach | Verdict | Why |
|----------|---------|-----|
| Inline Tailwind classes | ✅ Correct | See what it does, IntelliSense works |
| Component wrapping (Vue/React) | ✅ Correct | Encapsulates behavior + styles |
| JS object dictionaries | ❌ Wrong | Hides implementation, breaks tooling |
| `@utility` for grouping | ❌ Wrong | Misuse of the directive |
| `@utility` for missing CSS | ✅ Correct | Proper use case |

**References:**
- [Reusing Styles - Tailwind CSS](https://tailwindcss.com/docs/reusing-styles)
- [Adding Custom Styles - Tailwind CSS](https://tailwindcss.com/docs/adding-custom-styles)
- [Am I Wrong about @apply? - GitHub Discussion](https://github.com/tailwindlabs/tailwindcss/discussions/7651)

---

## Tailwind CSS v4 Built-in Animations

### Core `animate-*` Utilities
```
animate-spin      - Continuous rotation (loading spinners)
animate-ping      - Scale + fade out pulse (notification badges)
animate-pulse     - Opacity 100% → 50% → 100% (skeleton loaders)
animate-bounce    - Vertical bounce (CTAs, attention)
animate-none      - Disable animations
```

### Tailwind v4 Custom Animations
Define custom animations in CSS using `@theme`:
```css
@import "tailwindcss";

@theme {
  --animate-fade-in: fade-in 0.3s ease-out;

  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
}
```
This creates `animate-fade-in` utility automatically.

### Arbitrary Values
```tsx
// Custom one-off animation
className="animate-[wiggle_1s_ease-in-out_infinite]"

// From CSS variable
className="animate-(--my-custom-animation)"
```

### Motion Variants (Accessibility)
```tsx
// Only animate when motion is OK
className="motion-safe:animate-bounce"

// Alternative for reduced motion users
className="motion-reduce:animate-none"
```

---

## tailwindcss-motion Complete Reference

### All Available Presets
```
motion-preset-fade        - Opacity fade in
motion-preset-slide       - Slide from direction
motion-preset-slide-up    - Slide from bottom
motion-preset-slide-up-sm - Small slide from bottom
motion-preset-slide-down  - Slide from top
motion-preset-slide-left  - Slide from right
motion-preset-slide-right - Slide from left
motion-preset-focus       - Focus/attention effect
motion-preset-blur        - Blur in
motion-preset-expand      - Scale up from smaller
motion-preset-shrink      - Scale down from larger
motion-preset-pop         - Quick scale overshoot (button feedback)
motion-preset-shake       - Horizontal shake (errors)
motion-preset-bounce      - Vertical bounce
motion-preset-pulse       - Pulsing scale
motion-preset-wobble      - Wobble rotation
motion-preset-seesaw      - Tilt back and forth
motion-preset-oscillate   - Small oscillation
motion-preset-oscillate-sm - Tiny oscillation
motion-preset-stretch     - Stretch effect
motion-preset-float       - Floating up/down
motion-preset-spin        - Rotation
motion-preset-blink       - Opacity blink
motion-preset-compress    - Squish effect
motion-preset-confetti    - Celebration effect
motion-preset-typewriter-[n] - Typewriter with n characters
motion-preset-flomoji     - Emoji animation
```

### Base Animation Properties
Instead of presets, animate individual properties:

```
# Opacity
motion-opacity-in-[0%]     - Fade in from 0%
motion-opacity-in-[50%]    - Fade in from 50%
motion-opacity-out-[0%]    - Fade out to 0%

# Scale
motion-scale-in-[0.5]      - Scale in from 50%
motion-scale-in-[0.95]     - Scale in from 95% (subtle)
motion-scale-in-[1.1]      - Scale in from 110% (shrink)
motion-scale-out-[0]       - Scale out to 0

# Translate X
motion-translate-x-in-[20px]   - Slide in from right 20px
motion-translate-x-in-[-20px]  - Slide in from left 20px
motion-translate-x-in-[100%]   - Slide in from off-screen right
-motion-translate-x-in-100     - Negative translate

# Translate Y
motion-translate-y-in-[20px]   - Slide up from 20px below
motion-translate-y-in-[30px]   - Slide up from 30px below
motion-translate-y-in-[-20px]  - Slide down from 20px above

# Rotate
motion-rotate-in-[90deg]       - Rotate in from 90°
motion-rotate-in-[180deg]      - Rotate in from 180°
motion-rotate-in-[0.5turn]     - Rotate in from half turn

# Blur
motion-blur-in-[4px]           - Blur in from 4px
motion-blur-in-[8px]           - Blur in from 8px (stronger)
motion-blur-in-[10px]          - Blur in from 10px (dramatic)
```

### Duration Modifiers
```
motion-duration-[0.1s]    - 100ms (quick feedback)
motion-duration-[0.15s]   - 150ms (button press)
motion-duration-[0.2s]    - 200ms (data changes)
motion-duration-[0.3s]    - 300ms (content entrance)
motion-duration-[0.35s]   - 350ms
motion-duration-[0.4s]    - 400ms
motion-duration-[0.5s]    - 500ms (page sections)
motion-duration-[0.7s]    - 700ms (hero elements)
motion-duration-[1s]      - 1000ms (dramatic)
motion-duration-[1.5s]    - 1500ms (continuous)
motion-duration-[2s]      - 2000ms (ambient)
motion-duration-[3s]      - 3000ms (subtle continuous)

# Property-specific duration
motion-duration-[0.7s]/blur   - Different duration for blur
motion-duration-[1s]/opacity  - Different duration for opacity
```

### Delay Modifiers
```
motion-delay-[0.1s]       - 100ms delay
motion-delay-[0.15s]      - 150ms delay
motion-delay-[0.2s]       - 200ms delay
motion-delay-[0.25s]      - 250ms delay
motion-delay-[0.3s]       - 300ms delay
motion-delay-[0.35s]      - 350ms delay
... and so on (any value)
```

### Easing Functions
```
motion-ease-linear        - Linear (constant speed)
motion-ease-in            - Slow start
motion-ease-out           - Slow end
motion-ease-in-out        - Slow start and end

# Spring easings (natural, bouncy feel)
motion-ease-spring        - Default spring
motion-ease-spring-smooth - Smooth spring (recommended for UI)
motion-ease-spring-snappy - Quick spring
motion-ease-spring-bouncy - Bouncy spring (playful)
motion-ease-spring-bouncier - Extra bouncy

# Other
motion-ease-bounce        - Bounce easing
```

### Loop Modifiers
```
motion-loop-infinite      - Loop forever
motion-loop-[2]           - Loop 2 times
motion-loop-[3]           - Loop 3 times
```

### Exit Animations
Replace `in` with `out` for exit animations:
```
motion-opacity-out-[0%]
motion-scale-out-[0.5]
motion-translate-y-out-[20px]
```

---

## Custom CSS Utilities (globals.css)

We added these custom utilities for effects not covered by tailwindcss-motion:

```css
/* Subtle opacity pulse (no transform, avoids overflow issues) */
@keyframes pulse-subtle {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}
.animate-pulse-subtle {
  animation: pulse-subtle 2s ease-in-out infinite;
}

/* Background gradient shift */
@keyframes gradient-shift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
.animate-gradient-shift {
  animation: gradient-shift 15s ease infinite;
}

/* Glowing pulse for active states */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 oklch(from var(--primary) l c h / 0); }
  50% { box-shadow: 0 0 20px 0 oklch(from var(--primary) l c h / 0.15); }
}
.animate-pulse-glow {
  animation: pulse-glow 2s ease-in-out infinite;
}

/* Theme transitions for smooth dark/light switch */
.theme-transition,
.theme-transition *,
.theme-transition *::before,
.theme-transition *::after {
  transition: background-color 0.3s ease, border-color 0.3s ease, color 0.2s ease !important;
}
```

---

## Common Pitfalls & Debugging

### Issue: Animation overflows container
**Problem:** `motion-preset-pulse` or scale animations cause content to overflow.
**Solution:** Add `overflow-hidden` to parent, or use `animate-pulse` (opacity-only).

### Issue: Custom CSS class not working in Tailwind v4
**Problem:** Classes like `.animate-my-custom` defined in CSS don't work.
**Solution:** Use `@theme` directive or inline `animate-[keyframe_duration_easing]`.

### Issue: Animation triggers on every render
**Problem:** Animation replays when component re-renders.
**Solution:** Use `key` prop strategically - only change key when animation should replay.

### Issue: Staggered animations look choppy
**Problem:** Too many items animating at once.
**Solution:** Use `index % 5` to reset stagger every 5 items, or use ScrollReveal for below-fold.

### Issue: Hover animations on mobile
**Problem:** `:hover` states stick on touch devices.
**Solution:** Use `@media (hover: hover)` or rely on tap feedback (`active:scale-95`).

### Issue: Animation conflicts with transitions
**Problem:** `transition-*` and `motion-*` classes interfere.
**Solution:** Be explicit - use `transition-all` for hover states, `motion-*` for entrance.

---

## 1. Page Entrance Choreography

### Header Hero Moment
Make the page title feel important with blur + scale entrance:

```tsx
<h1 className="text-2xl font-bold mb-2 motion-blur-in-[10px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.7s] motion-duration-[1s]/blur motion-ease-spring-smooth">
  {title}
</h1>
<p className="text-muted-foreground motion-blur-in-[5px] motion-opacity-in-[0%] motion-translate-y-in-[10px] motion-duration-[0.5s] motion-delay-[0.25s] motion-ease-spring-smooth">
  {subtitle}
</p>
```

### Staggered Content Entrance
Define reusable animation classes:

```tsx
// Standard cards - slide up with blur
const animBase = "motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-duration-[0.7s]/blur motion-ease-spring-smooth";

// Full-width sections - scale in (hierarchy differentiation)
const animFull = "motion-opacity-in-[0%] motion-scale-in-[0.98] motion-blur-in-[3px] motion-duration-[0.55s] motion-ease-spring-smooth";
```

### Stagger Timing Pattern
For dramatic, gradual entrance (~2s total sequence):

```tsx
// Row 1 (2 items): 0.35s, 0.45s (0.1s gap within row)
// Row 2 (full-width): 0.6s
// Row 3 (2 items): 0.75s, 0.85s
// Row 4 (2 items): 1.0s, 1.1s
// Continue pattern...

<div className={`${animBase} motion-delay-[0.35s]`}>
  <FirstCard />
</div>
<div className={`${animBase} motion-delay-[0.45s]`}>
  <SecondCard />
</div>
```

---

## 2. Scroll-Triggered Reveals

Scroll-triggered animations use IntersectionObserver-based components/hooks. Each framework has its own implementation.

> **Note:** `tailwindcss-intersect` plugin does not work with Tailwind v4.

### Vue: ScrollReveal Component

```vue
<script setup>
import ScrollReveal from '@/components/ui/animation/ScrollReveal.vue'
</script>

<template>
  <!-- Basic usage -->
  <ScrollReveal>
    <YourContent />
  </ScrollReveal>

  <!-- With stagger delay (ms) for large screens -->
  <ScrollReveal :delay="0">Section 1</ScrollReveal>
  <ScrollReveal :delay="100">Section 2</ScrollReveal>
  <ScrollReveal :delay="200">Section 3</ScrollReveal>
</template>
```

### React: ScrollReveal Wrapper

React pages define a local ScrollReveal component using the `useScrollReveal` hook:

```tsx
import { useScrollReveal } from '@/hooks';

function ScrollReveal({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const { ref, isVisible } = useScrollReveal();

  return (
    <div
      ref={ref}
      className={cn(
        'transition-all duration-700 ease-out',
        isVisible ? 'opacity-100 translate-y-0 blur-0' : 'opacity-0 translate-y-8 blur-[2px]'
      )}
      style={{ transitionDelay: isVisible ? `${delay}ms` : '0ms' }}
    >
      {children}
    </div>
  );
}

// Usage with stagger
<ScrollReveal delay={0}>Section 1</ScrollReveal>
<ScrollReveal delay={100}>Section 2</ScrollReveal>
<ScrollReveal delay={200}>Section 3</ScrollReveal>
```

### Stagger Delays (Large Screen Fix)

On large monitors, multiple sections may be visible on initial load. Without stagger delays, they all animate simultaneously which looks jarring.

**Pattern:** Increment delay by 100ms per section (0, 100, 200, 300...)

```tsx
// Marketing page sections
<ScrollReveal delay={0}>Architecture</ScrollReveal>
<ScrollReveal delay={100}>Workflow</ScrollReveal>
<ScrollReveal delay={200}>What's Included</ScrollReveal>
<ScrollReveal delay={300}>Claude Code</ScrollReveal>
<ScrollReveal delay={400}>Quick Start</ScrollReveal>
<ScrollReveal delay={500}>Footer CTA</ScrollReveal>
```

Keep delays under 600ms to avoid feeling sluggish.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `threshold` | number | 0.1 | How much of element must be visible (0-1) |
| `rootMargin` | string | '0px 0px 100px 0px' | Triggers 100px before element enters viewport |
| `triggerOnce` | boolean | true | Only animate first time |
| `delay` | number | 0 | Transition delay in ms (for stagger) |

---

## 3. Card & Container Patterns

### Interactive Card with Hover
```tsx
<section className="
  group
  h-full flex flex-col bg-card rounded-xl border p-4
  transition-all duration-300 ease-out
  hover:shadow-2xl hover:shadow-primary/10
  hover:-translate-y-1.5 hover:scale-[1.01]
  hover:border-primary/30
  hover:bg-gradient-to-br hover:from-card hover:to-primary/[0.02]
  motion-reduce:transition-none motion-reduce:hover:transform-none
">
  {/* Icon speeds up on card hover */}
  <span className="
    inline-block
    motion-preset-oscillate-sm motion-duration-[3s] motion-loop-infinite
    transition-transform duration-200
    group-hover:scale-110 group-hover:motion-duration-[1.5s]
  ">
    {icon}
  </span>
  {children}
</section>
```

### Content Container with Overflow Protection
When using pulse/scale animations inside containers:
```tsx
<div className="bg-muted rounded-lg p-4 min-h-[80px] overflow-hidden">
  {/* Animated content won't overflow */}
</div>
```

---

## 4. Button Patterns

### Standard Interactive Button
```tsx
<Button
  className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
>
  Click me
</Button>
```

### Enhanced Hover (More Noticeable)
```tsx
<Button
  className="active:scale-95 hover:scale-105 hover:-translate-y-1 hover:shadow-lg hover:shadow-primary/25 transition-all duration-150"
>
  Prominent button
</Button>
```

### Selection Button with Pop
```tsx
<Button
  variant={isSelected ? 'default' : 'outline'}
  className={`active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150 ${
    isSelected ? 'motion-preset-pop motion-duration-[0.2s]' : ''
  }`}
>
  {label}
</Button>
```

### Button with Checkmark on Selection
```tsx
<Button
  variant={isSelected ? 'default' : 'outline'}
  className={`w-full justify-start active:scale-95 transition-all duration-150 ${
    isSelected ? 'motion-preset-pop motion-duration-[0.2s]' : ''
  }`}
>
  <Icon className={`w-4 h-4 mr-2 transition-transform duration-300 ${
    isSelected ? 'rotate-[360deg]' : ''
  }`} />
  {label}
  {isSelected && (
    <Check className="w-4 h-4 ml-auto motion-preset-pop motion-duration-[0.2s]" />
  )}
</Button>
```

---

## 5. Data State Animations

### Value Change Pop
Use `key` prop to trigger re-animation on value change:
```tsx
<p
  className="text-2xl font-bold motion-preset-pop motion-duration-[0.2s]"
  key={data?.value}
>
  {data?.value ?? '...'}
</p>
```

### Loading State
```tsx
// Skeleton with pulse
<div className="animate-pulse">
  <Skeleton className="h-5 w-1/2 mb-2" />
  <Skeleton className="h-4 w-3/4" />
</div>

// Text with subtle pulse
<p className="text-muted-foreground animate-pulse">
  Loading...
</p>
```

### Error State with Shake
```tsx
<Alert variant="destructive" className="motion-preset-shake motion-duration-[0.4s]">
  <AlertDescription>{errorMessage}</AlertDescription>
</Alert>
```

### Success State with Pop
```tsx
<p className="text-green-500 font-medium motion-preset-pop motion-duration-[0.3s]">
  {successMessage}
</p>
```

### Data Entrance (Fade + Slide)
```tsx
{data && (
  <div className="motion-preset-fade motion-preset-slide-up-sm motion-duration-[0.3s]">
    <p className="font-medium">{data.title}</p>
    <p className="text-sm text-muted-foreground">{data.description}</p>
  </div>
)}
```

---

## 6. Status Indicators

### Pulsing Status Dot
```tsx
<span className={`w-2 h-2 rounded-full ${
  isActive
    ? 'bg-green-500 animate-pulse'
    : 'bg-red-500'
}`} />
```

### Status Badge with Pulse
```tsx
<span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs transition-all duration-300 ${
  isStale
    ? 'bg-yellow-500/20 text-yellow-500 motion-preset-pulse motion-duration-[2s] motion-loop-infinite'
    : 'bg-green-500/20 text-green-500'
}`}>
  {isStale && <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full" />}
  {statusText}
</span>
```

### Prefetch Indicator with Glow
```tsx
{isPrefetched && (
  <span className="absolute -top-1.5 -right-1.5 w-2.5 h-2.5 bg-green-500 rounded-full motion-preset-pop animate-pulse shadow-[0_0_8px_2px_rgba(34,197,94,0.6)]" />
)}
```

### Active State Glow
```tsx
<div className={`bg-muted rounded-lg p-4 transition-shadow duration-500 ${
  isActive ? 'animate-pulse-glow' : ''
}`}>
  {content}
</div>
```

---

## 7. List Animations

### Staggered List Items
```tsx
{items.map((item, index) => (
  <div
    key={item.id}
    className="bg-background rounded p-2 text-sm motion-preset-slide-up motion-duration-[0.2s]"
    style={{ animationDelay: `${(index % 5) * 50}ms` }}
  >
    {item.content}
  </div>
))}
```

### Staggered Cards (Fixed Count)
```tsx
<div className="grid gap-3">
  <div
    className="bg-muted rounded-lg p-3 motion-preset-slide-up motion-duration-[0.3s]"
    style={{ animationDelay: '0ms' }}
  >
    <Card1 />
  </div>
  <div
    className="bg-muted rounded-lg p-3 motion-preset-slide-up motion-duration-[0.3s]"
    style={{ animationDelay: '100ms' }}
  >
    <Card2 />
  </div>
  <div
    className="bg-muted rounded-lg p-3 motion-preset-slide-up motion-duration-[0.3s]"
    style={{ animationDelay: '200ms' }}
  >
    <Card3 />
  </div>
</div>
```

---

## 8. Icon Animations

### Floating/Oscillating Icon
```tsx
<span className="inline-block motion-preset-oscillate-sm motion-duration-[3s] motion-loop-infinite">
  {icon}
</span>
```

### Icon Pulse (Online Status)
```tsx
<Wifi className="w-5 h-5 motion-preset-pulse motion-duration-[2s] motion-loop-infinite" />
```

### Icon Shake (Error/Offline)
```tsx
<WifiOff className="w-5 h-5 motion-preset-shake motion-duration-[0.5s]" />
```

### Icon Rotate on Selection
```tsx
<Icon className={`w-4 h-4 transition-transform duration-300 ${
  isSelected ? 'rotate-[360deg]' : ''
}`} />
```

### Spinner
```tsx
<RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
```

---

## 9. Conditional Animations

### Bounce vs Shake Based on Value
```tsx
<span
  className={`${
    value >= 0
      ? 'text-green-500 motion-preset-bounce motion-duration-[0.3s]'
      : 'text-red-500 motion-preset-shake motion-duration-[0.3s]'
  }`}
  key={value}
>
  {value >= 0 ? '+' : ''}{value}%
</span>
```

### Optimistic vs Confirmed States
```tsx
<p
  className={`text-4xl font-bold mb-1 ${
    isPending ? 'motion-preset-pop motion-duration-[0.15s]' : ''
  }`}
  key={isPending ? 'pending' : confirmedValue}
>
  {displayValue}
</p>
{isPending && (
  <p className="text-xs text-yellow-500 motion-preset-slide-up-sm motion-preset-fade motion-duration-[0.2s]">
    Saving...
  </p>
)}
```

---

## 10. CTA / Call-to-Action

### Glowing CTA Card
```tsx
<div className="group relative overflow-hidden bg-muted/50 rounded-xl p-4 text-center transition-all duration-300 hover:bg-muted/70 hover:shadow-xl hover:shadow-primary/15">
  {/* Animated glow on hover */}
  <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-primary/0 via-primary/10 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

  <p className="relative text-sm text-muted-foreground mb-2">{ctaText}</p>
  <Link className="relative text-primary hover:underline font-medium inline-flex items-center gap-1">
    {ctaLink}
    <span className="inline-block transition-transform duration-300 group-hover:translate-x-2">
      &rarr;
    </span>
  </Link>
</div>
```

---

## Best Practices

### DO
- Use `key` prop to trigger re-animations on value changes
- Keep durations short: 0.15s-0.3s for interactions, 0.5s-0.7s for entrances
- Add `motion-reduce:` variants for accessibility
- Use spring easing for natural feel
- Stagger animations within rows (0.075s-0.1s gap)
- Use scroll reveals for below-fold content

### DON'T
- Don't animate everything - focus on meaningful state changes
- Don't use long durations (>1s) for interactive elements
- Don't use transform animations inside containers without `overflow-hidden`
- Don't forget loading states - they should feel alive (pulse)
- Don't use distracting continuous animations in content areas

### Performance
- Prefer `transform` and `opacity` (GPU-accelerated)
- Use `will-change` sparingly
- Disconnect IntersectionObservers after triggering
- Avoid animating layout properties (width, height, padding)

---

## Animation Timing Cheatsheet

| Use Case | Duration | Easing |
|----------|----------|--------|
| Button press | 0.1s-0.15s | ease-out |
| Button hover | 0.15s | ease-out |
| Selection pop | 0.15s-0.2s | spring |
| Data change | 0.2s-0.3s | spring |
| Content entrance | 0.3s-0.5s | spring-smooth |
| Page entrance | 0.5s-0.7s | spring-smooth |
| Hero header | 0.7s-1s | spring-smooth |
| Continuous pulse | 1.5s-2s | ease-in-out |
| Status glow | 2s | ease-in-out |

---

## Files Reference

### React Template (`apps/template-react/frontend/`)
- Demo page: `app/[locale]/(app)/demo/page.tsx`
- Interactive card: `components/demo/DemoSection.tsx`
- Globals: `styles/globals.css`

### Vue Template (`apps/template/frontend/src/`)
- Demo page: `app/presentation/screens/Demo.vue`
- Interactive card: `app/presentation/components/demo/DemoSection.vue`
- Animation components: `components/ui/animation/` (Animate.vue, Stagger.vue, ScrollReveal.vue)

---

## Current Animation Architecture

### Summary

| Animation Type | Approach | File |
|----------------|----------|------|
| Page entrance | Inline `tailwindcss-motion` classes | In component |
| Staggered entrance | Inline classes with `motion-delay-[*]` | In component |
| Scroll reveal | `useScrollReveal` hook / `<ScrollReveal>` component | Vue has component, React has hook |
| Hover/interactions | Inline Tailwind transitions | In component |
| Feedback (pop, shake) | Inline `motion-preset-*` classes | In component |

### What We DON'T Use (Anti-patterns)

- ❌ JS class dictionaries (`lib/animations.ts` with `hover`, `feedback` objects)
- ❌ `@utility` for grouping existing Tailwind classes

### What We DO Use

- ✅ Inline Tailwind/tailwindcss-motion classes
- ✅ Vue/React components only when encapsulating real behavior
- ✅ `@utility` only for CSS features Tailwind doesn't have
- ✅ Vue: `<ScrollReveal>` component for scroll-triggered animations
- ✅ Both: `useScrollReveal` hook for custom scroll behavior
