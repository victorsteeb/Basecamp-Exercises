---
name: saas-redesign
description: Redesign the Vue 3 inventory management UI into a modern SaaS-style interface with a vertical sidebar navigation, consistent spacing, and polished professional look. Use when asked to redesign, modernize, or convert the top nav to a sidebar.
user_invocable: true
---

# SaaS Redesign Skill

Convert this Vue 3 app from a horizontal top-nav layout to a modern SaaS-style layout with a vertical sidebar on the left.

## What to build

### Layout structure

Replace the current `flex-direction: column` app shell with a two-column shell:

```
┌─────────────────────────────────────────────┐
│  Sidebar (240px fixed) │  Main area (flex:1) │
│                        │  ┌────────────────┐ │
│  Logo + tagline        │  │  Top bar       │ │
│                        │  │  (filters)     │ │
│  Nav links (vertical)  │  ├────────────────┤ │
│                        │  │                │ │
│  ── divider ──         │  │  Page content  │ │
│                        │  │  (router-view) │ │
│  User avatar + name    │  │                │ │
│  (bottom of sidebar)   │  └────────────────┘ │
└─────────────────────────────────────────────┘
```

### Specific changes

**App.vue** — MANDATORY: delegate all `.vue` file changes to the `vue-expert` subagent.

The `vue-expert` agent must make these changes to [App.vue](client/src/App.vue):

1. Replace `.app { flex-direction: column }` with a two-column grid/flex layout:
   - Sidebar: `width: 240px`, fixed/sticky, full viewport height
   - Main area: `flex: 1`, scrollable

2. Replace the `<header class="top-nav">` with a `<aside class="sidebar">` containing:
   - Logo block at top (company name + subtitle stacked vertically, no longer inline)
   - Vertical `<nav>` with links as block elements
   - Language switcher near the bottom
   - Profile menu / user info at the very bottom (pinned with `margin-top: auto`)

3. Keep `<FilterBar />` at the top of the main content area (it becomes an inline top bar above `<router-view>`, NOT inside the sidebar)

4. The `<main class="main-content">` becomes a scrollable right column

**Sidebar nav link styles** (in the `<style>` block of App.vue):
- Links: full-width, `padding: 0.625rem 1rem`, rounded corners, left-aligned
- Active state: `background: #eff6ff; color: #2563eb;` with a left border accent `border-left: 3px solid #2563eb`
- Hover: `background: #f1f5f9`
- Add a nav section label above the links: e.g., `NAVIGATION` in small caps, `font-size: 0.6875rem`, `color: #94a3b8`

**Sidebar shell styles**:
```css
.sidebar {
  width: 240px;
  min-height: 100vh;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}
```

**Main area shell styles**:
```css
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0; /* prevent flex overflow */
  overflow: hidden;
}

.main-content {
  flex: 1;
  padding: 1.5rem 2rem;
  overflow-y: auto;
}
```

**Remove** the `max-width: 1600px` constraint from `.main-content` — the sidebar already limits overall width. Keep `max-width` only if the page content genuinely needs it.

**Logo block** (vertical, inside sidebar):
```css
.logo {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.logo h1 {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
}

.subtitle {
  font-size: 0.75rem;
  color: #94a3b8;
  border-left: none; /* remove old vertical divider */
  padding-left: 0;
}
```

**Nav section label** (above nav links):
```css
.nav-section-label {
  font-size: 0.6875rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.5rem;
  padding: 0 0.5rem;
}
```

**Sidebar nav links**:
```css
.nav-tabs {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.nav-tabs a {
  display: block;
  padding: 0.625rem 0.875rem;
  color: #475569;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.9rem;
  border-radius: 6px;
  border-left: 3px solid transparent;
  transition: all 0.15s ease;
}

.nav-tabs a:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.nav-tabs a.active {
  color: #2563eb;
  background: #eff6ff;
  border-left-color: #2563eb;
}

.nav-tabs a.active::after {
  display: none; /* remove old bottom-border indicator */
}
```

**Sidebar footer** (user/profile area pinned to bottom):
```css
.sidebar-footer {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}
```

Wrap the `<ProfileMenu>` and `<LanguageSwitcher>` in a `<div class="sidebar-footer">`.

## Constraints and rules

- **MANDATORY**: ANY `.vue` file creation or significant modification MUST be delegated to `vue-expert`.
- Preserve all existing functionality: router links, filter state, profile/tasks modals, language switcher.
- Do not touch `FilterBar.vue` internals — only move where it renders in App.vue.
- Do not change any view files (`views/*.vue`) — this is a shell/layout change only.
- Keep the design system tokens (colors, border radius, font sizes) from the existing App.vue `<style>` block — do not introduce new color values.
- No emojis in the UI.
- The app must still work at 1280px+ viewport widths. No mobile breakpoints required.

## Steps

1. Delegate the full App.vue rewrite to `vue-expert` with the above specification.
2. After vue-expert finishes, start the dev server and use Playwright to verify:
   - Sidebar is visible on the left at `http://localhost:3000`
   - All nav links are present and functional
   - Active route highlights correctly
   - Filters bar appears above the page content (not inside the sidebar)
   - Modals (profile, tasks) still open correctly
3. Report what changed and confirm the layout looks correct.

## Verification checklist

Use `mcp__playwright__browser_take_screenshot` on `http://localhost:3000` to confirm:
- [ ] Sidebar visible on left, content on right
- [ ] Logo stacked vertically at top of sidebar
- [ ] Nav links vertical, active link has left-border accent
- [ ] Filter bar spans the top of the content area
- [ ] Page content fills the rest of the viewport
- [ ] Profile menu / user info at bottom of sidebar
