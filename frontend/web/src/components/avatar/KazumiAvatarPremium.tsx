"use client";

import { useState, useEffect } from "react";

type AvatarStatus = "online" | "listening" | "processing" | "warning" | "offline";

type KazumiAvatarPremiumProps = {
  status?: AvatarStatus;
  size?: "sm" | "md" | "lg" | "xl";
  animated?: boolean;
  onClick?: () => void;
  className?: string;
};

export default function KazumiAvatarPremium({
  status = "online",
  size = "lg",
  animated = true,
  onClick,
  className = "",
}: KazumiAvatarPremiumProps) {
  const [isListening, setIsListening] = useState(false);

  useEffect(() => {
    if (status === "listening" && animated) {
      const interval = setInterval(() => {
        setIsListening((prev) => !prev);
      }, 600);
      return () => clearInterval(interval);
    }
  }, [status, animated]);

  // Size configs
  const sizeMap = {
    sm: {
      container: "w-8 h-8",
      ring: "ring-2",
      indicator: "w-2 h-2",
      text: "text-lg",
    },
    md: {
      container: "w-12 h-12",
      ring: "ring-2",
      indicator: "w-2.5 h-2.5",
      text: "text-2xl",
    },
    lg: {
      container: "w-16 h-16",
      ring: "ring-3",
      indicator: "w-3 h-3",
      text: "text-4xl",
    },
    xl: {
      container: "w-20 h-20",
      ring: "ring-4",
      indicator: "w-4 h-4",
      text: "text-5xl",
    },
  };

  const config = sizeMap[size];

  // Status configurations
  const statusMap = {
    online: {
      ring: "ring-green-400/60",
      indicator: "bg-green-400",
      glow: "shadow-lg shadow-green-400/20",
      pulse: false,
    },
    listening: {
      ring: "ring-blue-400/60",
      indicator: "bg-blue-400",
      glow: "shadow-lg shadow-blue-400/40",
      pulse: true,
    },
    processing: {
      ring: "ring-purple-400/60",
      indicator: "bg-purple-400",
      glow: "shadow-lg shadow-purple-400/40",
      pulse: true,
    },
    warning: {
      ring: "ring-amber-400/60",
      indicator: "bg-amber-400",
      glow: "shadow-lg shadow-amber-400/30",
      pulse: true,
    },
    offline: {
      ring: "ring-gray-500/40",
      indicator: "bg-gray-500",
      glow: "shadow-lg shadow-gray-500/20",
      pulse: false,
    },
  };

  const currentStatus = statusMap[status];

  const pulseScale = animated && currentStatus.pulse && isListening ? 1.2 : 1;

  return (
    <div
      onClick={onClick}
      className={`relative cursor-pointer transition-transform ${className}`}
    >
      {/* Main Avatar Circle */}
      <div
        className={`${config.container} rounded-full
                    bg-gradient-to-br from-purple-500 via-purple-600 to-purple-700
                    flex items-center justify-center flex-shrink-0
                    border-2 border-purple-400/30
                    ${currentStatus.ring} ring-offset-2 ring-offset-slate-900
                    ${currentStatus.glow}
                    transition-all duration-300
                    hover:shadow-xl hover:scale-105`}
        style={{
          transform: `scale(${pulseScale})`,
        }}
      >
        {/* Kazumi Face Emoji/Icon */}
        <span className={`${config.text} select-none`}>🤖</span>
      </div>

      {/* Status Indicator (LED Ring) */}
      <div
        className={`absolute -bottom-1 -right-1 ${config.indicator} rounded-full
                    ${currentStatus.indicator} ring-2 ring-slate-900
                    transition-all duration-300
                    ${animated && currentStatus.pulse ? "animate-pulse" : ""}`}
      />

      {/* Listening Animation (ripple effect) */}
      {animated && status === "listening" && (
        <>
          <div
            className={`absolute inset-0 ${config.container} rounded-full
                        border-2 border-blue-400/40
                        animate-pulse`}
          />
          <div
            className={`absolute inset-0 ${config.container} rounded-full
                        border-2 border-blue-400/20
                        animate-ping`}
          />
        </>
      )}

      {/* Processing Animation (spinning ring) */}
      {animated && status === "processing" && (
        <div
          className={`absolute inset-0 ${config.container} rounded-full
                      border-2 border-transparent border-t-purple-400 border-r-purple-400
                      animate-spin`}
        />
      )}
    </div>
  );
}
