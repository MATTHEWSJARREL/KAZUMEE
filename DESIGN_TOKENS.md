# Kazumee Design Tokens & System

## Color Palette

### Primary Colors
```
Purple-600: #9333EA (Primary action, highlights)
Purple-700: #7E22CE (Darker variant, hover states)
Purple-400: #C084FC (Lighter variant, text highlights)
```

### Secondary Colors
```
Blue-600:    #2563EB (Insights, information)
Blue-700:    #1D4ED8 (Blue hover)
Emerald-600: #059669 (Success, positive)
Emerald-700: #047857 (Success hover)
Amber-600:   #D97706 (Warning, caution)
Amber-700:   #B45309 (Warning hover)
Red-600:     #DC2626 (Error, danger)
Red-700:     #B91C1C (Error hover)
Green-600:   #16A34A (Online, active)
```

### Neutral Colors
```
White/5:     rgba(255, 255, 255, 0.05)  (Subtlest backgrounds)
White/10:    rgba(255, 255, 255, 0.10)  (Subtle borders, backgrounds)
White/20:    rgba(255, 255, 255, 0.20)  (Medium emphasis)
Gray-300:    #D1D5DB (Light text, secondary)
Gray-400:    #9CA3AF (Medium text)
Gray-500:    #6B7280 (Subtle text)
Gray-900:   #111827 (Dark backgrounds)
Slate-800:  #1E293B (Background secondary)
Slate-900:  #0F172A (Background primary)
```

## Typography

### Font Families
```
Headlines:  'Syne' (geometric, bold)
Body:       'DM Sans' (clean, readable)
Monospace:  'Monaco' or system monospace (for code)
```

### Font Sizes & Weight

**Headlines (Syne)**
```
h1: text-5xl font-800    (36px, black)
h2: text-3xl font-bold   (30px, bold)
h3: text-lg font-bold    (18px, bold)
```

**Body (DM Sans)**
```
Large:  text-base font-500   (16px, medium)
Normal: text-sm font-400     (14px, regular)
Small:  text-xs font-400     (12px, regular)
Label:  text-xs font-600     (12px, semibold, uppercase tracking-wide)
```

## Spacing Scale

```
xs: 4px    (gap-1)
sm: 8px    (gap-2)
md: 12px   (gap-3)
base: 16px (gap-4)
lg: 24px   (gap-6)
xl: 32px   (gap-8)
2xl: 48px  (gap-12)
```

**Component Padding**
```
Small cards:   p-4  (16px all sides)
Normal cards:  p-6  (24px all sides)
Large cards:   p-8  (32px all sides)
Hero sections: p-8 md:p-10 (mobile-first)
```

## Border Radius

```
Button/Input:  rounded-lg       (8px)
Cards:         rounded-2xl      (16px)
Badges:        rounded-full     (50%)
Icons:         rounded-xl       (12px)
```

## Shadows

```
Subtle:   shadow-sm (minimal depth)
Normal:   shadow-lg (16px blur, 8px offset)
Elevated: shadow-xl (20px blur, 10px offset)
Glow:     shadow-2xl shadow-purple-600/20 (colored shadow)
```

## Animations

### Timing
```
Fast:    200ms  (micro-interactions, hovers)
Normal:  300ms  (component transitions)
Slow:    500ms  (page transitions, dismissal)
```

### Easing
```
ease-in-out: Standard (most common)
ease-out:    For exits
ease-in:     For entrances
```

### Common Animations
```
Hover scale:        hover:scale-105 transform duration-300
Fade in:            fade-in opacity-100
Slide up:           slide-in-from-bottom-2
Pulse:              animate-pulse (2s)
Spin:               animate-spin (2s)
Bounce:             animate-bounce (1s)
```

## Component Sizes

### Avatar Sizes
```
Small:  w-8 h-8   (icon size)
Medium: w-12 h-12 (list items)
Large:  w-16 h-16 (dashboard)
XL:     w-20 h-20 (header)
```

### Button Sizes
```
Small:  px-3 py-1.5  text-xs
Normal: px-4 py-2    text-sm
Large:  px-6 py-3    text-base
```

### Card Widths
```
Responsive cards:  max-w-[420px]
Full-width:        w-full
Max container:     max-w-7xl
```

## States & Variants

### Button States
```
Default:  bg-purple-600 hover:bg-purple-700
Disabled: opacity-50 cursor-not-allowed
Loading:  animate-pulse or spinner
Active:   ring-2 ring-purple-400
```

### Input States
```
Default:  border-white/10 bg-white/5
Focus:    border-purple-500 ring-2 ring-purple-500/20
Error:    border-red-500 ring-2 ring-red-500/20
Success:  border-green-500 ring-2 ring-green-500/20
Disabled: bg-white/5 cursor-not-allowed opacity-50
```

### Badge States
```
Success:  bg-green-500/20 border-green-500/40 text-green-300
Warning:  bg-amber-500/20 border-amber-500/40 text-amber-300
Error:    bg-red-500/20 border-red-500/40 text-red-300
Info:     bg-blue-500/20 border-blue-500/40 text-blue-300
```

## Dark Mode

### Background Hierarchy
```
Level 1 (Darkest):   #0F172A (slate-900)
Level 2:             #1E293B (slate-800)
Level 3:             rgba(255,255,255,0.05) (white/5)
Level 4 (Lightest):  rgba(255,255,255,0.10) (white/10)
```

### Text Hierarchy
```
Primary:   #FFFFFF (white, headlines)
Secondary: #D1D5DB (gray-300, body text)
Tertiary:  #9CA3AF (gray-400, secondary text)
Disabled:  #6B7280 (gray-500, subtle text)
```

## Responsive Breakpoints

```
Mobile:    < 640px   (default)
Tablet:    640px-1024px (md:)
Desktop:   1024px+   (lg:)
Wide:      1280px+   (xl:)
```

### Common Patterns
```
md:flex        Hide on mobile, show on tablet+
lg:grid-cols-3 1 col mobile, 2 col tablet, 3 col desktop
hidden md:grid Hide on mobile
md:p-8         Smaller padding on mobile, larger on tablet+
```

## Component Library Map

### Base Components
```
UnifiedCard        - Consistent card styling (default, elevated, outlined, gradient)
Tooltip            - Help text with positioning
LabelWithTooltip   - Form label with integrated help
```

### Dashboard Components
```
DashboardHeroCard      - Main stream status (prominent)
DashboardKPICard       - Metrics (secondary)
DashboardSectionHeader - Section grouping
DashboardToolCard      - Action buttons
DashboardStatusBadge   - Status indicators
DashboardKPIGrid       - Responsive grid (4 columns)
DashboardToolGrid      - Responsive grid (3 columns)
```

### Avatar Components
```
KazumiAvatarPremium - Animated avatar with status ring
  - 4 sizes: sm/md/lg/xl
  - 5 states: online/listening/processing/warning/offline
  - Animated ripple/spin effects
```

### Response System
```
KazumiResponseCard     - Individual notification
KazumiResponseContext  - Global provider
useKazumiResponse()    - Hook for triggering responses
  - showResponse()     - Custom
  - showInsight()      - ✨ Purple
  - showAnswer()       - 💡 Blue
  - showSuggestion()   - 🎯 Green
  - showWarning()      - ⚠️ Amber
```

### Page Components
```
ClipsFilterSidebar      - Filter UI for clips
AuthSocialProof         - Trust indicators
AuthErrorMessage        - Error styling
AuthSuccessMessage      - Success styling
ViewerDashboardModern   - Viewer clip grid
```

## Accessibility Standards

### Color Contrast
```
AAA (Preferred): 7:1 ratio (white on purple-600)
AA (Minimum):    4.5:1 ratio
```

### Interactive Elements
```
Focus state:  ring-2 ring-offset-2 outline
Hover state:  scale-105 or color change
Disabled:     opacity-50 cursor-not-allowed
```

### Typography
```
Line height:  1.5 (body), 1.2 (headlines)
Letter-spacing: tracked when uppercase
Max line width: 65-75 characters for readability
```

## Usage Examples

### Creating a New Card
```tsx
import UnifiedCard from '@/components/cards/UnifiedCard';

<UnifiedCard variant="elevated" padding="lg">
  <h3 className="text-lg font-bold text-white">Title</h3>
  <p className="text-sm text-gray-400">Description</p>
</UnifiedCard>
```

### Using Response Notifications
```tsx
import { useKazumiResponse } from '@/lib/KazumiResponseContext';

const { showInsight, showWarning } = useKazumiResponse();

showInsight("Chat is very engaged right now!");
showWarning("Stream bitrate is dropping");
```

### Creating a Consistent Dashboard Section
```tsx
import { DashboardSectionHeader, DashboardKPIGrid, DashboardKPICard } from '@/components/dashboard/DashboardSections';

<DashboardSectionHeader title="Analytics" icon={TrendingUp} />
<DashboardKPIGrid>
  <DashboardKPICard label="Views" value="1.2k" trend="up" trendLabel="+15%" />
  <DashboardKPICard label="Engagement" value="68%" trend="up" trendLabel="+5%" />
</DashboardKPIGrid>
```

## Version History

```
v1.0 - Initial design system
  - Color palette (purple + neutrals)
  - Typography scale
  - Component library
  - Dark mode optimization
  - Responsive breakpoints
```

---

**Last Updated**: 2026-07-14  
**Status**: Production Ready ✅
