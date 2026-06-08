# Kazumi Viewer Rebuild — TODO

## Phase 1 — Full Viewer Audit (completed)
- [x] Map active viewer route structure (sections/cards/widgets/overlays)
- [x] Verify active vs legacy references and mark legacy candidates
- [x] Enumerate every API used by active viewer route
- [x] Identify placeholder/unused assets (confirmed: public/logo.png placeholder)
- [x] Remove legacy viewer items from active experience scope (legacy route is present but not routed)


## Phase 2 — Design System Creation
- [x] Create design system tokens (color, spacing, radii, shadows, typography)
- [x] Define glassmorphism rules + hover/transition rules
- [x] Define layout primitives (left/sidebar/center/right + cards + section headers)


## Phase 3 — Viewer Layout Rebuild
- [x] Produce layout proposal (final target component tree)
- [x] Implement new layout using existing active functionality (no feature changes)


## Phase 4 — Component Modernization
- [x] Inventory active components and decide: keep/refactor/replace/merge (without removing functionality) (active UI is implemented directly in `src/app/viewer/page.jsx`; legacy components are not part of active experience)


## Phase 5 — CSS Cleanup
- [ ] Audit `viewer.redesign.css` for dead/duplicate selectors (can be done by comparing selectors used in `src/app/viewer/page.jsx`)
- [ ] Convert to CSS variables + consistent scale (some tokens already exist in `viewer.design.tokens.css`; reduce duplication)


## Phase 6 — Performance
- [ ] Identify unnecessary rerenders / duplicated API calls inside viewer page
- [ ] Optimize safely (no behavior changes)

## Phase 7 — Deliverables
- [ ] Before implementation: provide architecture map, component inventory, removal candidates, wireframe, design system, layout proposal
- [ ] After implementation: updated maps, modified/removed files list, screenshots, functionality confirmation

