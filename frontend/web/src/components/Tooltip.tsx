"use client";

import { useState, ReactNode } from "react";
import { HelpCircle } from "lucide-react";

interface TooltipProps {
  content: string;
  children?: ReactNode;
  position?: "top" | "right" | "bottom" | "left";
  className?: string;
}

export default function Tooltip({
  content,
  children,
  position = "top",
  className = "",
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);

  const positionStyles = {
    top: "bottom-full mb-2 -translate-x-1/2 left-1/2",
    right: "left-full ml-2 top-1/2 -translate-y-1/2",
    bottom: "top-full mt-2 -translate-x-1/2 left-1/2",
    left: "right-full mr-2 top-1/2 -translate-y-1/2",
  };

  const arrowStyles = {
    top: "top-full left-1/2 -translate-x-1/2 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent",
    right: "right-full top-1/2 -translate-y-1/2 border-t-8 border-b-8 border-r-8 border-t-transparent border-b-transparent",
    bottom: "bottom-full left-1/2 -translate-x-1/2 border-l-8 border-r-8 border-b-8 border-l-transparent border-r-transparent",
    left: "left-full top-1/2 -translate-y-1/2 border-t-8 border-b-8 border-l-8 border-t-transparent border-b-transparent",
  };

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        type="button"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onClick={() => setIsVisible(!isVisible)}
        className="inline-flex items-center justify-center p-1 hover:bg-gray-200 rounded-full transition-colors"
        title={content}
      >
        {children || <HelpCircle className="w-4 h-4 text-gray-500" />}
      </button>

      {isVisible && (
        <div
          className={`absolute z-50 px-3 py-2 text-sm font-medium text-white
                      bg-gray-900 rounded-lg shadow-lg whitespace-nowrap pointer-events-none
                      ${positionStyles[position]}`}
        >
          {content}
          <div
            className={`absolute w-0 h-0 border-gray-900 ${arrowStyles[position]}`}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Label with integrated tooltip
 */
export function LabelWithTooltip({
  label,
  tooltip,
}: {
  label: string;
  tooltip: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <label className="block text-sm font-semibold">{label}</label>
      <Tooltip content={tooltip}>
        <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600" />
      </Tooltip>
    </div>
  );
}
