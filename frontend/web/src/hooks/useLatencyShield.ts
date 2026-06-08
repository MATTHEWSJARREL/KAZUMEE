import { useState } from "react";

export function useLatencyShield(defaultMs = 4000) {
  const [shieldMsLeft, setShieldMsLeft] = useState(0);

  const shield = async (ms = defaultMs) => {
    setShieldMsLeft(ms);
    const start = Date.now();
    return new Promise<void>((resolve) => {
      const tick = () => {
        const elapsed = Date.now() - start;
        const left = Math.max(ms - elapsed, 0);
        setShieldMsLeft(left);
        if (left <= 0) return resolve();
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  };

  return { shield, shieldMsLeft };
}
