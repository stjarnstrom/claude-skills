---
name: design-polish-pass
description: Use when a frontend design implementation is structurally complete but needs consistency and refinement. Triggers on words like "harmonize", "polish", "clean up", "tighten up", "make consistent", or when pages within a project have drifted into inconsistent card styles, spacing, typography, color usage, or responsive behavior. Also use before design handoff, after building out multiple pages, or when mobile layouts feel rough. Use this skill whenever reviewing or refining the visual quality of a frontend codebase, even if the user doesn't explicitly ask for a "polish pass".
---

# Design Polish Pass

A systematic technique for taking a structurally complete frontend and making it feel cohesive, polished, and ship-ready. Instead of ad-hoc fixes, this skill provides an ordered audit sequence that catches the consistency issues that accumulate when building pages independently.

The core insight: most "rough" designs aren't missing features -- they're missing consistency. The same card rendered with slightly different padding on three pages, a heading scale that drifts between routes, hardcoded colors that should be tokens. A structured pass catches these faster than intuition alone.

## When to Use

- Pages are built and functional, but the design feels "off" or inconsistent across routes
- Multiple pages use similar components (cards, heroes, CTAs) but they've drifted apart visually
- Mobile layouts need attention -- stacking, navigation, image cropping
- Before handoff or shipping a design milestone
- After a batch of feature work that touched many pages independently

## When NOT to Use

- During early creative/exploratory work (polish kills experimentation)
- For structural redesigns or rearchitecting layouts (this is refinement, not rebuilding)
- On a single isolated component with no sibling pages to compare against

## The Polish Pass

Work through these passes in order. Each pass focuses on one dimension of consistency, so you're not trying to fix everything at once. Read the project's existing design tokens, CSS variables, or theme config before starting -- the goal is to align with what's already established, not invent new conventions.

### Pass 1: Surface Consistency

Cards, panels, modals, and content containers are the most visible source of inconsistency because they're built independently across pages.

**What to audit:**
- `border-radius` -- are cards `rounded-xl` on one page and `rounded-2xl` on another?
- `box-shadow` -- same shadow recipe everywhere, or `shadow-sm` here and `shadow-md` there?
- Internal `padding` -- consistent across card types, or 16px on one and 20px on another?
- Hover/focus states -- do all clickable cards have the same lift/shadow transition?
- Background -- cards using `bg-white` consistently, or some using `bg-gray-50`?

**Fix pattern:** Establish 2-3 surface recipes (e.g. "card", "panel", "overlay") and apply uniformly. If the project already has a Card component, audit pages for inline card-like markup that bypasses it.

```tsx
// Before: inconsistent surfaces across pages
<div className="rounded-lg bg-white p-4 shadow">        {/* page A */}
<div className="rounded-xl bg-white p-6 shadow-md">     {/* page B */}
<div className="rounded-2xl bg-gray-50 p-5 shadow-sm">  {/* page C */}

// After: unified surface
<div className="rounded-xl bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
```

### Pass 2: Typography

Typography inconsistency is subtle but creates a "something's off" feeling.

**What to audit:**
- Display/heading font vs body font usage -- are headings consistently using the display typeface?
- Heading size scale -- is `h2` the same size on every page? Does the hierarchy (h1 > h2 > h3) hold?
- `line-height` and `letter-spacing` -- especially on large headings (tighter tracking looks more intentional)
- Font weight consistency -- are similar elements using the same weight?
- Small text / labels -- consistent sizing and casing (uppercase with tracking? sentence case?)

**Fix pattern:** Define the heading scale once and reference it everywhere. For Tailwind projects, this means picking specific `text-*` classes per heading level and applying them uniformly.

```tsx
// Establish a consistent scale:
// h1: text-3xl md:text-5xl font-bold  (page titles)
// h2: text-2xl md:text-3xl font-bold  (section headings)
// h3: text-lg md:text-xl font-semibold (card titles, subsections)
// body: text-base leading-relaxed
// small/label: text-sm text-muted
```

### Pass 3: Color and Token Adherence

Hardcoded color values drift from design tokens over time, especially in one-off sections.

**What to audit:**
- Grep for hardcoded hex values (`#`, `rgb(`) that should be tokens or CSS variables
- Background colors -- is there a consistent page/section background, or a mix of whites, grays, and off-whites?
- Text colors -- primary text, muted/secondary text, link colors: are they tokenized?
- Accent usage -- does the same accent color carry the same semantic meaning across pages?
- Opacity patterns -- `bg-primary/10` for tags, `bg-primary/5` for hover: consistent?

**Fix pattern:** Replace hardcoded values with the project's token system. If no token system exists, this is the moment to introduce one (CSS custom properties or Tailwind theme extension).

### Pass 4: Spacing Rhythm

Inconsistent spacing is the most common cause of a design feeling "undesigned."

**What to audit:**
- Section-to-section gaps: consistent `py-*` or `my-*` between major page sections?
- Heading-to-body gap: same `mt-*` after headings across pages?
- Card grid gaps: consistent `gap-*` in grid/flex layouts?
- Page horizontal padding: same `px-*` at each breakpoint?
- Max-width containers: same `max-w-*` across pages?

**Fix pattern:** Pick a spacing scale and stick to it. For sections, establish a rhythm (e.g. `py-16 md:py-24` between major sections) and apply it uniformly. For card grids, standardize on one `gap` value.

### Pass 5: Responsive Stacking

This is where designs most often break down. Each page was probably built with desktop in mind and given a quick mobile check, but the stacking behavior across pages is rarely consistent.

**What to audit:**
- Hero sections: do they stack cleanly or create nested rounded containers ("double bubble")?
- Grid breakpoints: do similar grids break at the same point (e.g. all 3-col grids go to 1-col at `md`)?
- Text sizing: do headings scale down appropriately on mobile?
- Touch targets: are buttons/links at least 44px tap targets on mobile?
- Horizontal overflow: any content causing horizontal scroll on small screens?

**Fix pattern for the "double bubble" problem:**

```tsx
// Before: nested rounded containers both visible on mobile stack
<div className="rounded-2xl bg-teal-800 p-8">
  <div className="rounded-2xl bg-white p-6">
    Content
  </div>
</div>

// After: single outer shell, inner content fills naturally
<div className="overflow-hidden rounded-2xl bg-teal-800">
  <div className="flex flex-col md:flex-row">
    <div className="p-8 md:w-1/2">Text content</div>
    <div className="md:w-1/2">
      <img className="h-full w-full object-cover" src="..." alt="..." />
    </div>
  </div>
</div>
```

### Pass 6: Navigation and Chrome

Header, footer, mobile menu, breadcrumbs -- the structural shell that frames every page.

**What to audit:**
- Mobile menu: does it lock body scroll when open? Proper z-index above all content?
- Hamburger animation: smooth transition between states?
- Active state: does the nav highlight the current page/section?
- Header scroll behavior: sticky? Shadow on scroll? Consistent across pages?
- Breadcrumbs: consistent format and placement on subpages?
- Footer: same structure/content on every route?

**Fix pattern for mobile overlay scroll lock:**

```tsx
useEffect(() => {
  if (menuOpen) {
    document.body.style.overflow = "hidden";
  } else {
    document.body.style.overflow = "";
  }
  return () => { document.body.style.overflow = ""; };
}, [menuOpen]);
```

### Pass 7: Image Treatment

Images make or break a design's perceived quality. The most common issue: images that look fine on the developer's screen but crop badly at other aspect ratios.

**What to audit:**
- `object-cover` on all images that fill a container (never stretch/distort)
- `object-position` set when the subject (face, product) isn't centered
- Aspect ratio: `aspect-[16/10]` or similar instead of fixed `h-64` -- the latter breaks at different widths
- Image sizing: are images generous and editorial, or squeezed into tiny thumbnails?
- Alt text: descriptive, not filenames

**Fix pattern:**

```tsx
// Before: fixed height, no focal point control
<img className="h-64 w-full" src="..." alt="..." />

// After: aspect-ratio with focal point
<div className="aspect-[16/10] overflow-hidden">
  <img
    className="h-full w-full object-cover object-[center_30%]"
    src="..."
    alt="Student working at laptop in library"
  />
</div>
```

### Pass 8: Interactive States

Every clickable element needs feedback. Missing hover/focus states make a design feel inert.

**What to audit:**
- All links and buttons: hover state defined?
- Focus-visible: keyboard focus outlines present? (critical for accessibility)
- Transitions: consistent duration (200-400ms for micro-interactions, 300-600ms for reveals)?
- Cards that are links: does the entire card feel interactive (cursor, lift, shadow)?
- Disabled states: visually distinct from active states?

**Fix pattern:**

```tsx
// Clickable card with full interactive feedback
<a
  href={href}
  className="group block rounded-xl bg-white p-5 shadow-sm
             transition-all duration-200
             hover:shadow-md hover:-translate-y-0.5
             focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
>
  <h3 className="font-semibold transition-colors group-hover:text-primary">
    {title}
  </h3>
</a>
```

### Pass 9: Component Extraction

After passes 1-8 have unified the visual language, look for repeated patterns that should be components.

**What to audit:**
- Same card markup copy-pasted across 3+ pages? Extract a component.
- Repeated CTA sections (heading + description + button)? Extract.
- Icon + text patterns repeated inline? Extract.
- But: don't over-extract. If a section has unique layout personality, keep it as page-level JSX.

**The judgment call:** Extract when the markup is genuinely identical in structure and the differences can be expressed as props. Don't extract when each instance has unique layout relationships with its surrounding content -- that flattens page compositions into sameness.

### Pass 10: Accessibility

The final pass. Many accessibility issues are side effects of the visual polish above (contrast, focus states), but some need explicit attention.

**What to audit:**
- Color contrast: WCAG AA minimum (4.5:1 for normal text, 3:1 for large text)
- Icon-only buttons: `aria-label` present?
- Toggle elements: `aria-expanded` tracking state?
- Semantic HTML: `<nav>`, `<main>`, `<section>`, `<article>` used appropriately?
- Skip link: present for keyboard users to bypass navigation?
- Heading hierarchy: no skipped levels (h1 > h3 without h2)?
- Images: meaningful `alt` text (not empty unless truly decorative)?

## Common Mistakes

**Polishing pages in isolation.** The whole point is cross-page consistency. Always have sibling pages open for comparison. Audit the same element type (cards, headings, sections) across all pages, not one page at a time.

**Over-abstracting too early.** Don't create a `<UniversalSection>` component that every page uses. Pages should have layout personality. Extract components only for truly repeated, structurally identical patterns (cards, buttons, CTAs), not for every `<section>`.

**Fixing mobile with `hidden`/`block` toggles without testing the middle.** Tablet breakpoints (768-1024px) are where most responsive bugs live. Test at `md` explicitly, not just phone and desktop.

**Introducing new tokens during polish.** The polish pass should align with the project's existing design language, not introduce a new one. If the project uses `rounded-xl`, don't "fix" some cards to `rounded-2xl` because you prefer it -- match what's established.

**Fixed pixel heights on images.** Using `h-64` on images means they look fine at one width and crop poorly at every other width. Use `aspect-ratio` to maintain proportions across all viewport sizes.

## Working Method

When running a polish pass on a real codebase:

1. **Start by reading the project's design tokens** -- CSS variables, Tailwind theme, globals file. Understand what's already defined before changing anything.
2. **Audit across pages, not within pages.** For each pass, look at the same element type on every page before making changes. Cards on page A, B, C. Headings on A, B, C.
3. **Make changes in batches by pass**, not by page. Do all surface fixes, then all typography fixes. This prevents regressions from interleaved changes.
4. **Check mobile after every batch** -- don't leave responsive fixes for the end.
5. **Don't chase perfection on pass 1.** Get through all 10 passes at "good" before going back for "great" on any one pass.
