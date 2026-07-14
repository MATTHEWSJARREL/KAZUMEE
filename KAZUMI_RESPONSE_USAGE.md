# Kazumi Response Card System - Usage Guide

## Overview

The Kazumi Response Card system displays AI responses as modern floating notifications that appear in the bottom-right corner of the screen. They automatically dismiss after 8 seconds or when clicked.

## Files

- `frontend/web/src/components/KazumiResponseCard.tsx` - UI Component
- `frontend/web/src/lib/KazumiResponseContext.tsx` - Global Context Provider

## Setup

### 1. Wrap your app with the provider

In `frontend/web/src/app/root.tsx` or your layout file:

```tsx
import { KazumiResponseProvider } from "@/lib/KazumiResponseContext";

export default function RootLayout({ children }) {
  return (
    <KazumiResponseProvider>
      {children}
    </KazumiResponseProvider>
  );
}
```

### 2. Use anywhere in your components

```tsx
import { useKazumiResponse } from "@/lib/KazumiResponseContext";

export function MyComponent() {
  const { showInsight, showAnswer, showWarning } = useKazumiResponse();

  return (
    <div>
      <button onClick={() => showInsight("You're on fire! 🔥")}>
        Show Insight
      </button>
      <button onClick={() => showAnswer("That's a great question!")}>
        Show Answer
      </button>
      <button onClick={() => showWarning("Stream is getting lagging!")}>
        Show Warning
      </button>
    </div>
  );
}
```

## API

### `showResponse(message, options?)`

Display a custom response with full control.

```tsx
const { showResponse } = useKazumiResponse();

showResponse("Your custom message", {
  type: "insight",           // "insight" | "answer" | "suggestion" | "warning"
  icon: "✨",               // Custom emoji/icon
  duration: 8000,           // Auto-dismiss in ms (0 = no auto-dismiss)
  dismissible: true,        // Show close button
});
```

### `showInsight(message)`

Display an insight (✨ purple gradient).

```tsx
showInsight("Chat sentiment is up 45% when you play horror games!");
```

### `showAnswer(message)`

Display an answer (💡 blue gradient).

```tsx
showAnswer("Yes, you're doing great! Keep up the energy.");
```

### `showSuggestion(message)`

Display a suggestion (🎯 emerald gradient).

```tsx
showSuggestion("Try switching to the Gaming scene for higher engagement.");
```

### `showWarning(message)`

Display a warning (⚠️ amber gradient).

```tsx
showWarning("Stream bitrate dropped below 4000 kbps!");
```

## Visual Styling

### Colors by Type

| Type | Background | Icon | Use Case |
|------|------------|------|----------|
| `insight` | Purple-600 → Purple-700 | ✨ | Observations, analytics |
| `answer` | Blue-600 → Blue-700 | 💡 | Direct responses to questions |
| `suggestion` | Emerald-600 → Emerald-700 | 🎯 | Recommendations |
| `warning` | Amber-600 → Amber-700 | ⚠️ | Issues, problems |

### Display Behavior

- **Position**: Fixed bottom-right corner (6px from edges)
- **Stacking**: Up to 3 visible at once (older ones pushed up)
- **Auto-dismiss**: 8 seconds (configurable per response)
- **Animations**: Slide in from bottom + fade in, fade out on dismiss
- **Mobile**: Same position, responsive max-width

## Integration Examples

### Example 1: AI Response from Chat Command

```tsx
// In your command handler
const { showAnswer } = useKazumiResponse();

async function handleChatCommand(message: string) {
  const response = await askKazumi(message);
  showAnswer(response);  // Display response as floating card
}
```

### Example 2: Real-time Notifications

```tsx
// In a component listening to WebSocket events
const { showWarning, showInsight } = useKazumiResponse();

useEffect(() => {
  const handleMessage = (event) => {
    if (event.type === "alert") {
      showWarning(event.message);
    } else if (event.type === "insight") {
      showInsight(event.message);
    }
  };

  socket.on("message", handleMessage);
  return () => socket.off("message", handleMessage);
}, [showWarning, showInsight]);
```

### Example 3: Action Feedback

```tsx
// When user clips a moment
async function clipNow() {
  try {
    await saveCli();
    showSuggestion("Clip saved! 🎬 Share it to TikTok?");
  } catch (error) {
    showWarning("Failed to save clip. Try again.");
  }
}
```

## Keyboard Shortcuts (Optional Enhancement)

Could add in the future:
- `Escape` - Dismiss current response
- `Ctrl+K` - Open quick responses menu
- `Shift+Enter` in chat - Force broadcast response

## Customization

### Extending with New Types

To add a custom response type:

1. Update the type in `KazumiResponseCard.tsx`:
```tsx
type: "insight" | "answer" | "suggestion" | "warning" | "custom";
```

2. Add styling in the provider:
```tsx
response.type === "custom"
  ? "from-pink-600 to-pink-700 shadow-pink-600/30"
  : "..."
```

3. Create a helper method:
```tsx
const showCustom = (message: string) => {
  addResponse(message, { type: "custom", icon: "🎨" });
};
```

## Best Practices

✅ **Do:**
- Use for immediate feedback (user actions, alerts)
- Keep messages concise (1-2 sentences max)
- Use appropriate type/icon for context
- Use in response to user actions or important events

❌ **Don't:**
- Spam responses (max 3 visible at once for reason)
- Use for error handling alone (combine with error boundaries)
- Make messages longer than can fit in ~400px width
- Forget to handle no-JavaScript users (graceful degradation)

## Accessibility

- Cards use semantic color coding (type → color association)
- Close button always visible and keyboard accessible
- Messages read naturally to screen readers
- Auto-dismiss has generous timing (8s default)

## Performance Notes

- Uses React Context + local state (no Redux needed)
- Animations use Tailwind CSS (hardware accelerated)
- Max 3 visible at once (prevents DOM bloat)
- Auto-cleanup of old responses

## Migration from Old System

If replacing Kazumi Feed notifications:

**Old:**
```tsx
// Messages appear in feed at bottom (delayed, hard to see)
feed.addMessage(response);
```

**New:**
```tsx
// Messages appear immediately as floating card
showAnswer(response);
```

---

For questions or issues, check the component source files.
