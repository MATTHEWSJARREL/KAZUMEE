export type AvatarState = "idle" | "listening" | "thinking" | "speaking" | "alert";

export type AvatarEvent = "listen" | "think" | "speak" | "alert" | "idle" | "reset";

const VALID_STATES: AvatarState[] = ["idle", "listening", "thinking", "speaking", "alert"];

const TRANSITIONS: Record<AvatarState, Record<AvatarEvent, AvatarState>> = {
  idle: {
    listen: "listening",
    think: "thinking",
    speak: "speaking",
    alert: "alert",
    idle: "idle",
    reset: "idle",
  },
  listening: {
    listen: "listening",
    think: "thinking",
    speak: "speaking",
    alert: "alert",
    idle: "idle",
    reset: "idle",
  },
  thinking: {
    listen: "listening",
    think: "thinking",
    speak: "speaking",
    alert: "alert",
    idle: "idle",
    reset: "idle",
  },
  speaking: {
    listen: "listening",
    think: "thinking",
    speak: "speaking",
    alert: "alert",
    idle: "idle",
    reset: "idle",
  },
  alert: {
    listen: "listening",
    think: "thinking",
    speak: "speaking",
    alert: "alert",
    idle: "idle",
    reset: "idle",
  },
};

export const normalizeAvatarState = (state?: string | null): AvatarState => {
  const candidate = String(state || "").trim().toLowerCase();
  return (VALID_STATES.includes(candidate as AvatarState) ? candidate : "idle") as AvatarState;
};

export const getAvatarTransition = (state: string | null | undefined, event: AvatarEvent): AvatarState => {
  const current = normalizeAvatarState(state);
  return TRANSITIONS[current][event] || "idle";
};

export const getAvatarStateMeta = (state: string | null | undefined) => {
  const normalized = normalizeAvatarState(state);
  switch (normalized) {
    case "listening":
      return {
        state: normalized,
        label: "Listening",
        pulse: "listening",
        accent: "cyan",
        subtitle: "Microphone open",
      };
    case "thinking":
      return {
        state: normalized,
        label: "Thinking",
        pulse: "thinking",
        accent: "violet",
        subtitle: "Processing context",
      };
    case "speaking":
      return {
        state: normalized,
        label: "Speaking",
        pulse: "speaking",
        accent: "blue",
        subtitle: "Audio output active",
      };
    case "alert":
      return {
        state: normalized,
        label: "Alert",
        pulse: "alert",
        accent: "red",
        subtitle: "Attention required",
      };
    case "idle":
    default:
      return {
        state: "idle",
        label: "Idle",
        pulse: "idle",
        accent: "slate",
        subtitle: "Standing by",
      };
  }
};

