"use client";

import React, { ReactNode } from "react";

interface UnifiedCardProps {
  children: ReactNode;
  hover?: boolean;
  interactive?: boolean;
  onClick?: () => void;
  className?: string;
  variant?: "default" | "elevated" | "outlined" | "gradient";
  padding?: "sm" | "md" | "lg";
}

/**
 * Unified Card Component - Consistent styling across entire platform
 */
export default function UnifiedCard({
  children,
  hover = true,
  interactive = false,
  onClick,
  className = "",
  variant = "default",
  padding = "md",
}: UnifiedCardProps) {
  const paddingMap = {
    sm: "p-4",
    md: "p-6",
    lg: "p-8",
  };

  const variantStyles = {
    default:
      "bg-white/5 border border-white/10 rounded-2xl backdrop-blur-sm",
    elevated:
      "bg-gradient-to-br from-white/10 to-white/5 border border-white/20 rounded-2xl shadow-xl",
    outlined:
      "bg-transparent border-2 border-white/20 rounded-2xl hover:border-purple-500/40",
    gradient:
      "bg-gradient-to-br from-purple-600/20 to-purple-700/10 border border-purple-500/30 rounded-2xl",
  };

  const interactiveClass = interactive || onClick
    ? "cursor-pointer transition-all duration-300 hover:scale-105"
    : "";

  const hoverClass = hover
    ? "hover:border-white/20 hover:shadow-lg hover:shadow-purple-600/10"
    : "";

  return (
    <div
      onClick={onClick}
      className={`
        ${variantStyles[variant]}
        ${paddingMap[padding]}
        ${interactiveClass}
        ${hoverClass}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

/**
 * Card with Icon and Title
 */
export function CardWithIcon({
  icon: Icon,
  title,
  subtitle,
  children,
  ...props
}: UnifiedCardProps & {
  icon: React.ComponentType<{ className: string }>;
  title: string;
  subtitle?: string;
}) {
  return (
    <UnifiedCard {...props}>
      <div className="flex items-start gap-4 mb-4">
        <div className="p-3 rounded-xl bg-purple-600/20">
          <Icon className="w-6 h-6 text-purple-400" />
        </div>
        <div>
          <h3 className="font-bold text-white">{title}</h3>
          {subtitle && <p className="text-sm text-gray-400">{subtitle}</p>}
        </div>
      </div>
      {children}
    </UnifiedCard>
  );
}

/**
 * Card Group - Grid of unified cards
 */
export function CardGroup({
  children,
  cols = 3,
  gap = "md",
}: {
  children: ReactNode;
  cols?: 1 | 2 | 3 | 4;
  gap?: "sm" | "md" | "lg";
}) {
  const colsMap = {
    1: "grid-cols-1",
    2: "grid-cols-1 md:grid-cols-2",
    3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 md:grid-cols-2 lg:grid-cols-4",
  };

  const gapMap = {
    sm: "gap-4",
    md: "gap-6",
    lg: "gap-8",
  };

  return (
    <div className={`grid ${colsMap[cols]} ${gapMap[gap]}`}>{children}</div>
  );
}
