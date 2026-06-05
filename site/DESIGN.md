# Seam Design System

## Color Strategy

**Restrained with purpose**: Tinted neutrals dominate. Single accent color for critical actions and emphasis only.

### Palette

```css
/* Base - warm charcoal with subtle warmth */
--base-950: oklch(0.15 0.008 50);  /* Near black */
--base-900: oklch(0.25 0.008 50);
--base-800: oklch(0.35 0.007 50);
--base-700: oklch(0.45 0.006 50);
--base-600: oklch(0.55 0.005 50);
--base-500: oklch(0.65 0.004 50);
--base-400: oklch(0.75 0.003 50);
--base-300: oklch(0.85 0.002 50);
--base-200: oklch(0.92 0.001 50);
--base-100: oklch(0.97 0.001 50);  /* Near white */

/* Accent - amber for warmth and energy */
--accent-600: oklch(0.60 0.15 65);
--accent-500: oklch(0.70 0.14 65);
--accent-400: oklch(0.80 0.12 65);
```

## Typography

**System**: Geist Sans (already loaded in layout)
**Mono**: Geist Mono (for code, CLI examples)

### Scale

- **Hero**: 3.5rem / 56px, -0.02em tracking, 700 weight, 1.1 line-height
- **H2**: 2rem / 32px, -0.01em tracking, 600 weight, 1.2 line-height
- **H3**: 1.5rem / 24px, -0.005em tracking, 600 weight, 1.3 line-height
- **Body**: 1rem / 16px, 0 tracking, 400 weight, 1.6 line-height
- **Small**: 0.875rem / 14px, 0 tracking, 400 weight, 1.5 line-height
- **Code**: Geist Mono, 0.875rem, 0.01em tracking

Line length cap: 70ch for body text

## Layout

### Spacing Scale

- xs: 0.5rem / 8px
- sm: 0.75rem / 12px
- base: 1rem / 16px
- md: 1.5rem / 24px
- lg: 2rem / 32px
- xl: 3rem / 48px
- 2xl: 4rem / 64px
- 3xl: 6rem / 96px
- 4xl: 8rem / 128px

Vary rhythm: don't use the same spacing everywhere. Breathe between major sections (3xl-4xl). Tighter within components.

### Grid

Standard centered container: max-width 1200px, horizontal padding 2rem on mobile.

## Components

### Code Blocks

- Background: --base-100 (light mode) / --base-900 (dark mode)
- Border: 1px solid with 10% opacity base-400
- Padding: 1.5rem
- Border-radius: 0.5rem
- Font: Geist Mono, 14px
- Line numbers optional, but if used, muted color

### Buttons

**Primary**: 
- Background: --base-950
- Text: --base-100
- Padding: 0.75rem 1.5rem
- Border-radius: 0.5rem
- Transition: background 150ms ease-out
- Hover: --base-900

**Secondary**:
- Background: transparent
- Border: 1px solid --base-300
- Text: --base-950
- Hover: background --base-100

No gradients, no shadows by default.

## Motion

Subtle, fast, purposeful.

- **Duration**: 150ms for micro-interactions, 250ms for larger state changes
- **Easing**: ease-out (or cubic-bezier(0.22, 1, 0.36, 1))
- Never animate layout properties (width, height, top, left)
- Prefer: opacity, transform, filter

## Theme

Default: Light with dark mode support via system preference.

Dark mode adjustments:
- Invert base scale
- Reduce accent chroma slightly (0.13 instead of 0.15 for 600)
- Add subtle glow to accents in dark (optional, tasteful)

## Accessibility

- WCAG AA minimum, AAA for body text
- Focus states: 2px offset outline in accent color
- Reduced motion: respect prefers-reduced-motion
- Semantic HTML: proper heading hierarchy, landmark regions
