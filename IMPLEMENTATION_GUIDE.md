# UI Design Implementation Guide

## Overview
This guide details how to integrate all new components and design improvements into the Kazumee platform.

## Quick Start Checklist

### ✅ Already Completed
- [x] KazumiResponseProvider in root.tsx
- [x] KazumiAvatarPremium component
- [x] DashboardSections components
- [x] Tooltip system with settings integration
- [x] ClipsFilterSidebar
- [x] AuthSocialProof components
- [x] ViewerDashboardModern
- [x] UnifiedCard system
- [x] Design tokens documented
- [x] Response card system fully wired

## Phase 1: Integration (Do This First)

### 1. Update Dashboard Header with Avatar

In `frontend/web/src/app/page.jsx`:

```jsx
import KazumiAvatarPremium from "@/components/avatar/KazumiAvatarPremium";

// In the header section, replace logo with:
<div className="flex items-center gap-4">
  <KazumiAvatarPremium 
    status={obsState?.connected ? "online" : "offline"} 
    size="lg"
  />
  <div>
    <h1 className="text-2xl md:text-3xl font-bold">Kazumi AI</h1>
    <p className="text-sm text-gray-400">Stream Director</p>
  </div>
</div>
```

### 2. Integrate Response Cards into Command Handlers

When responding to user commands:

```jsx
import { useKazumiResponse } from "@/lib/KazumiResponseContext";

function CommandHandler() {
  const { showAnswer, showInsight } = useKazumiResponse();

  const handleAIResponse = async (userQuestion) => {
    const response = await askKazumi(userQuestion);
    showAnswer(response);  // Appears as floating card immediately
  };
}
```

### 3. Use UnifiedCard Throughout

Before (inconsistent):
```jsx
<div className="bg-white/5 p-6 rounded-lg border border-white/10">content</div>
```

After (consistent):
```jsx
import UnifiedCard from "@/components/cards/UnifiedCard";

<UnifiedCard variant="default" padding="md">content</UnifiedCard>
```

## Component Library

### Response System
```jsx
import { useKazumiResponse } from "@/lib/KazumiResponseContext";

const { showInsight, showAnswer, showSuggestion, showWarning } = useKazumiResponse();

showInsight("Chat is very engaged!");      // ✨ Purple
showAnswer("Great question!")              // 💡 Blue
showSuggestion("Try switching scenes")     // 🎯 Green  
showWarning("Stream bitrate dropping")     // ⚠️ Amber
```

### Dashboard Components
```jsx
import {
  DashboardHeroCard,
  DashboardKPICard,
  DashboardKPIGrid,
  DashboardToolCard,
  DashboardSectionHeader,
} from "@/components/dashboard/DashboardSections";

// Hero card for stream status
<DashboardHeroCard title="LIVE" status="online" />

// KPI cards in grid
<DashboardKPIGrid>
  <DashboardKPICard label="Views" value="1.2k" trend="up" />
</DashboardKPIGrid>
```

### Avatar Component
```jsx
import KazumiAvatarPremium from "@/components/avatar/KazumiAvatarPremium";

<KazumiAvatarPremium 
  status="online"      // online|listening|processing|warning|offline
  size="lg"           // sm|md|lg|xl
  animated={true}
/>
```

## Status

✅ **All components created and tested**
✅ **Design system documented**  
✅ **Ready for page integration**

Next step: Integrate into existing pages using patterns above.

---

**Last Updated**: 2026-07-14
