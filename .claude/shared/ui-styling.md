# UI/UX & Styling Patterns

## Quick Checklist

- [ ] **Use shadcn/ui components** - don't build from scratch
- [ ] **Use Tailwind utilities** - no custom CSS unless absolutely necessary
- [ ] **Read parent layout first** before styling any page
- [ ] **Use CSS variables** for layout dimensions (`--header-height`, `--page-padding-x`)
- [ ] **Check AppShell** for existing padding before adding spacing
- [ ] **Position sticky/fixed elements** relative to header and bottom nav
- [ ] **Use semantic color tokens** - never hardcode colors
- [ ] **Test both themes** - light and dark mode

---

## Use shadcn/ui First (Critical!)

**ALWAYS check if a shadcn/ui component exists before building custom UI.**

### Available Components

```
Layout:        Card, Separator, AspectRatio, ScrollArea, Resizable
Navigation:    Tabs, NavigationMenu, Breadcrumb, Pagination, Menubar
Overlay:       Dialog, Sheet, Drawer, AlertDialog, Popover, HoverCard, Tooltip
Form:          Input, Textarea, Select, Checkbox, RadioGroup, Switch, Slider, Calendar
              Form, Label, InputOTP, PasswordInput
Feedback:      Alert, Badge, Progress, Skeleton, Spinner, Sonner (toasts)
Data:          Table, Accordion, Collapsible, Carousel
Actions:       Button, ButtonGroup, Toggle, ToggleGroup, DropdownMenu, ContextMenu, Command
```

### Component Selection Guide

| Need | Use This | Not This |
|------|----------|----------|
| Modal/popup | `<Dialog>` or `<Sheet>` | Custom portal div |
| Dropdown | `<DropdownMenu>` or `<Select>` | Custom div with onClick |
| Tabs | `<Tabs>` | Custom state + buttons |
| Toast notification | `toast()` from Sonner | Custom alert div |
| Loading state | `<Skeleton>` or `<Spinner>` | Custom CSS animation |
| Form validation | `<Form>` with react-hook-form | Manual validation |
| Sidebar panel | `<Sheet>` | Custom sliding div |
| Tooltip | `<Tooltip>` | Title attribute |
| Confirmation | `<AlertDialog>` | window.confirm() |
| Search/command | `<Command>` | Custom search input |

### Import Pattern

```tsx
// ✅ CORRECT: Import from @/components/ui
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

// ❌ WRONG: Don't rebuild these yourself
const CustomButton = styled.button`...`;
```

---

## Tailwind First (No Custom CSS!)

### The Rule

```
Need styling? → Use Tailwind utilities
Need a component? → Use shadcn/ui
Need custom CSS? → You probably don't. Ask yourself why.
```

### When Tailwind Is Enough

```tsx
// ✅ Layout
className="flex items-center justify-between gap-4"
className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"

// ✅ Spacing
className="p-4 mt-6 mb-8 space-y-4"

// ✅ Typography
className="text-2xl font-bold tracking-tight"
className="text-sm text-muted-foreground leading-relaxed"

// ✅ Colors (semantic tokens)
className="bg-card text-card-foreground border-border"
className="bg-primary text-primary-foreground"

// ✅ Effects
className="rounded-xl shadow-lg hover:shadow-xl transition-shadow"
className="backdrop-blur-sm bg-background/80"

// ✅ Responsive
className="hidden md:flex lg:grid-cols-4"

// ✅ States
className="hover:bg-accent focus:ring-2 active:scale-95 disabled:opacity-50"
```

### When Custom CSS Is Acceptable

Only use custom CSS in `globals.css` for:

1. **Keyframe animations** not covered by tailwindcss-motion
2. **CSS properties Tailwind doesn't have** (scrollbar styling, etc.)
3. **Third-party component overrides** (Sonner toasts, etc.)

```css
/* ✅ OK: Custom keyframes */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 oklch(from var(--primary) l c h / 0); }
  50% { box-shadow: 0 0 20px 0 oklch(from var(--primary) l c h / 0.15); }
}

/* ✅ OK: Scrollbar (no Tailwind equivalent) */
* { scrollbar-width: none; }

/* ❌ NOT OK: Should be Tailwind classes */
.my-card { border-radius: 12px; padding: 16px; }
```

---

## Component Composition Patterns

### Extending shadcn/ui Components

```tsx
// ✅ CORRECT: Extend via className prop
<Button
  className="shadow-xl shadow-primary/20 hover:shadow-2xl transition-all"
>
  Enhanced Button
</Button>

// ✅ CORRECT: Create wrapper for repeated patterns
function PrimaryButton({ children, className, ...props }: ButtonProps) {
  return (
    <Button
      className={cn(
        "shadow-xl shadow-primary/20 hover:shadow-2xl hover:scale-105 transition-all",
        className
      )}
      {...props}
    >
      {children}
    </Button>
  );
}

// ❌ WRONG: Don't copy-paste shadcn source and modify
// ❌ WRONG: Don't use styled-components or CSS modules
```

### Card Patterns

```tsx
// Basic card
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
  </CardHeader>
  <CardContent>Content here</CardContent>
</Card>

// Interactive card (add hover effects via className)
<Card className="transition-all duration-300 hover:shadow-lg hover:border-primary/50 cursor-pointer">
  <CardContent className="p-6">
    Clickable card
  </CardContent>
</Card>

// Glass card
<Card className="bg-card/50 backdrop-blur-sm border-border/50">
  <CardContent>Glass effect</CardContent>
</Card>
```

### Dialog/Sheet Patterns

```tsx
// Confirmation dialog
<AlertDialog>
  <AlertDialogTrigger asChild>
    <Button variant="destructive">Delete</Button>
  </AlertDialogTrigger>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Are you sure?</AlertDialogTitle>
      <AlertDialogDescription>This action cannot be undone.</AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction>Continue</AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>

// Side panel (filters, cart, etc.)
<Sheet>
  <SheetTrigger asChild>
    <Button variant="outline">Open Panel</Button>
  </SheetTrigger>
  <SheetContent side="right" className="w-80">
    <SheetHeader>
      <SheetTitle>Panel Title</SheetTitle>
    </SheetHeader>
    {/* Panel content */}
  </SheetContent>
</Sheet>
```

### Form Patterns

```tsx
// With react-hook-form + zod
<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
    <FormField
      control={form.control}
      name="email"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Email</FormLabel>
          <FormControl>
            <Input placeholder="email@example.com" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
    <Button type="submit" disabled={isPending}>
      {isPending && <Spinner className="mr-2 h-4 w-4" />}
      Submit
    </Button>
  </form>
</Form>
```

### Loading States

```tsx
// Skeleton for content loading
<div className="space-y-3">
  <Skeleton className="h-8 w-48" />  {/* Title */}
  <Skeleton className="h-4 w-full" /> {/* Line 1 */}
  <Skeleton className="h-4 w-3/4" />  {/* Line 2 */}
</div>

// Spinner for action loading
<Button disabled={isPending}>
  {isPending && <Spinner className="mr-2 h-4 w-4" />}
  {isPending ? 'Saving...' : 'Save'}
</Button>

// Full page loading
<div className="flex items-center justify-center min-h-[400px]">
  <Spinner className="h-8 w-8" />
</div>
```

### Toast Notifications

```tsx
import { toast } from 'sonner';

// Success
toast.success('Saved successfully');

// Error
toast.error('Something went wrong');

// With description
toast.success('Added to cart', {
  description: 'Premium Headphones x1',
});

// Loading → Success pattern
const promise = saveData();
toast.promise(promise, {
  loading: 'Saving...',
  success: 'Saved!',
  error: 'Failed to save',
});
```

---

## Layout Hierarchy (Critical!)

**Before styling ANY page, understand the layout chain:**

```
app/[locale]/layout.tsx          → Providers, i18n
└── (app)/layout.tsx             → <AppShell> wrapper
    └── AppShell                 → AppNav (header) + main (padded)
        └── shop/layout.tsx      → Page-specific wrapper
            └── shop/page.tsx    → Your page content
```

### AppShell Structure

```tsx
// components/shells/AppShell.tsx
<div className="min-h-screen bg-background flex flex-col">
  <AppNav />                    {/* Fixed header: var(--header-height) = 3.5rem */}
  <main className="
    flex-1 w-full mx-auto
    px-[var(--page-padding-x)]  {/* 16px mobile, 24px desktop */}
    py-[var(--page-padding-y)]  {/* 16px */}
    pb-[var(--bottom-nav-height)] md:pb-[var(--page-padding-y)]  {/* 66px mobile */}
    max-w-[var(--page-max-width)]  {/* 1280px */}
  ">
    {children}
  </main>
</div>
```

### Key Implications

1. **Pages already have padding** - don't add `px-*` or `pt-*` redundantly
2. **Bottom nav on mobile** - AppShell handles `pb-[var(--bottom-nav-height)]`
3. **Max width constrained** - content is centered with max-width
4. **Header offset** - sticky elements need `top-[calc(var(--header-height)+...)]`

---

## CSS Variables Reference

### Layout Dimensions

```css
--header-height: 3.5rem;        /* 56px */
--bottom-nav-height: 4.125rem;  /* 66px mobile, 0 desktop */
--page-padding-x: 1rem;         /* 16px mobile, 24px desktop */
--page-padding-y: 1rem;         /* 16px */
--page-max-width: 80rem;        /* 1280px */
```

### Using in Tailwind

```tsx
// Sticky below header
className="sticky top-[calc(var(--header-height)+1rem)]"

// Full-bleed section
className="-mx-[var(--page-padding-x)] -mt-[var(--page-padding-y)]"

// Fixed above bottom nav
className="fixed bottom-[calc(var(--bottom-nav-height)+1.5rem)] md:bottom-6"
```

---

## Common Layout Patterns

### Sticky Sidebar

```tsx
<aside className="hidden w-64 shrink-0 lg:block">
  <div className="sticky top-[calc(var(--header-height)+1rem)]">
    <FilterSidebar />
  </div>
</aside>
```

### Full-Bleed Hero

```tsx
<div className="-mx-[var(--page-padding-x)] -mt-[var(--page-padding-y)]">
  <div className="bg-gradient-to-br from-background to-accent/20">
    <div className="max-w-[var(--page-max-width)] mx-auto px-[var(--page-padding-x)] py-12">
      <h1>Hero Title</h1>
    </div>
  </div>
</div>
```

### Floating Action Button

```tsx
<div className="fixed bottom-[calc(var(--bottom-nav-height)+1.5rem)] md:bottom-6 right-4 md:right-6 z-40">
  <Button size="lg" className="h-14 w-14 rounded-2xl shadow-xl">
    <Plus className="h-6 w-6" />
  </Button>
</div>
```

### Two-Column Layout

```tsx
<div className="flex gap-8">
  {/* Sidebar - desktop only */}
  <aside className="hidden w-64 shrink-0 lg:block">
    <div className="sticky top-[calc(var(--header-height)+1rem)]">
      <Sidebar />
    </div>
  </aside>

  {/* Main content */}
  <main className="flex-1 min-w-0">
    <Content />
  </main>
</div>
```

---

## Design Tokens

### Semantic Colors (Always Use These!)

```tsx
// Backgrounds
className="bg-background"      // Page background
className="bg-card"            // Card/elevated surfaces
className="bg-muted"           // Subtle/secondary backgrounds
className="bg-accent"          // Hover/selected states
className="bg-primary"         // Primary actions
className="bg-destructive"     // Danger/error

// Text
className="text-foreground"        // Primary text
className="text-muted-foreground"  // Secondary text
className="text-primary"           // Accent text
className="text-destructive"       // Error text

// Borders
className="border-border"      // Default borders
className="border-input"       // Form input borders
```

### Opacity Modifiers

```tsx
// Semi-transparent backgrounds
className="bg-primary/10"      // 10% opacity
className="bg-card/50"         // 50% opacity
className="border-border/50"   // Subtle border

// Colored shadows
className="shadow-xl shadow-primary/20"
```

### Dark Mode

```tsx
// ✅ Semantic tokens auto-switch (preferred)
className="bg-card text-card-foreground"

// ✅ Explicit dark variant when needed
className="text-blue-600 dark:text-blue-400"
className="bg-white dark:bg-gray-900"

// ❌ Avoid - breaks in dark mode
className="bg-white text-gray-900"
```

---

## Responsive Design

### Mobile-First Breakpoints

```tsx
// Base = mobile, then override
className="text-sm md:text-base lg:text-lg"
className="grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
className="p-4 md:p-6 lg:p-8"
```

### Common Breakpoint Patterns

```tsx
// Hide on mobile, show on desktop
className="hidden lg:block"

// Show on mobile, hide on desktop
className="lg:hidden"

// Different layouts
className="flex flex-col md:flex-row"
className="grid grid-cols-2 lg:grid-cols-4"
```

### Touch Targets (44px minimum)

```tsx
<Button size="icon" className="h-11 w-11">
  <Icon className="h-5 w-5" />
</Button>
```

---

## Anti-Patterns

### ❌ Building What shadcn Has

```tsx
// ❌ BAD: Custom modal
<div className="fixed inset-0 bg-black/50" onClick={close}>
  <div className="bg-card p-6 rounded-lg">...</div>
</div>

// ✅ GOOD: Use Dialog
<Dialog open={open} onOpenChange={setOpen}>
  <DialogContent>...</DialogContent>
</Dialog>
```

### ❌ Custom CSS for Tailwind Features

```tsx
// ❌ BAD: CSS file
.my-button { transition: all 0.2s; transform: scale(0.98); }

// ✅ GOOD: Tailwind
className="transition-all duration-200 active:scale-[0.98]"
```

### ❌ Hardcoded Colors

```tsx
// ❌ BAD
className="bg-white text-gray-900 border-gray-200"

// ✅ GOOD
className="bg-card text-card-foreground border-border"
```

### ❌ Ignoring Parent Layout

```tsx
// ❌ BAD: Redundant padding
<div className="px-4 py-4">

// ✅ GOOD: AppShell already provides padding
<div className="max-w-2xl">
```

### ❌ Hardcoded Layout Values

```tsx
// ❌ BAD
className="sticky top-14"

// ✅ GOOD
className="sticky top-[calc(var(--header-height)+1rem)]"
```

---

## Pre-Flight Checklist

Before styling any page:

1. **Check shadcn/ui** - Does a component already exist?
2. **Read parent layout** - What padding/structure is inherited?
3. **Use Tailwind** - Can this be done with utility classes?
4. **Check similar pages** - How do other pages handle this?
5. **Test themes** - Does it work in light and dark mode?
6. **Test responsive** - Does it work on mobile?

---

## Reference Files

- **shadcn/ui components:** `apps/{app}/frontend/components/ui/`
- **CSS Variables:** `apps/{app}/frontend/styles/globals.css`
- **AppShell:** `apps/{app}/frontend/components/shells/AppShell.tsx`
- **Animation Patterns:** `.claude/shared/react-animations.md`
- **Shop Page (example):** `apps/{app}/frontend/app/[locale]/(app)/shop/page.tsx`
