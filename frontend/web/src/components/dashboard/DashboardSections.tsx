"use client";

import React from "react";
import { LucideIcon } from "lucide-react";

/**
 * HERO CARD - Main focus card for stream status
 */
export function DashboardHeroCard({
  title,
  subtitle,
  icon: Icon,
  value,
  status,
  children,
}: {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  value?: string | number;
  status?: "online" | "offline" | "warning";
  children?: React.ReactNode;
}) {
  const statusColor = {
    online: "from-green-600 to-green-700 border-green-500/20",
    offline: "from-gray-600 to-gray-700 border-gray-500/20",
    warning: "from-amber-600 to-amber-700 border-amber-500/20",
  };

  return (
    <div
      className={`bg-gradient-to-br ${statusColor[status || "online"]}
                  rounded-3xl p-8 mb-8 border text-white
                  shadow-2xl shadow-green-600/20
                  transform transition-all hover:shadow-2xl hover:scale-[1.02]`}
    >
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            {Icon && <Icon className="w-6 h-6 text-white/80" />}
            <h2 className="text-sm font-semibold uppercase tracking-widest text-white/70">
              {subtitle || "Stream Status"}
            </h2>
          </div>
          <h1 className="text-4xl md:text-5xl font-black">{title}</h1>
        </div>
        {value && (
          <div className="text-right">
            <div className="text-2xl md:text-3xl font-black text-white/90">
              {value}
            </div>
          </div>
        )}
      </div>
      {children}
    </div>
  );
}

/**
 * KPI CARD - Secondary card for metrics
 */
export function DashboardKPICard({
  label,
  value,
  icon: Icon,
  trend,
  trendLabel,
  color = "purple",
}: {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  trendLabel?: string;
  color?: "purple" | "blue" | "emerald" | "amber";
}) {
  const colorMap = {
    purple: "from-purple-600/20 to-purple-700/20 border-purple-500/30 bg-purple-500/5",
    blue: "from-blue-600/20 to-blue-700/20 border-blue-500/30 bg-blue-500/5",
    emerald: "from-emerald-600/20 to-emerald-700/20 border-emerald-500/30 bg-emerald-500/5",
    amber: "from-amber-600/20 to-amber-700/20 border-amber-500/30 bg-amber-500/5",
  };

  const trendColor = {
    up: "text-emerald-400",
    down: "text-red-400",
    neutral: "text-gray-400",
  };

  return (
    <div
      className={`bg-gradient-to-br ${colorMap[color]}
                  rounded-2xl p-6 border
                  transition-all hover:scale-105 hover:shadow-lg
                  transform duration-300`}
    >
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
          {label}
        </h3>
        {Icon && <Icon className="w-5 h-5 text-gray-400" />}
      </div>
      <div className="flex items-end justify-between">
        <div>
          <div className="text-3xl md:text-4xl font-black text-white mb-1">
            {value}
          </div>
          {trendLabel && (
            <div className={`text-xs font-semibold ${trendColor[trend || "neutral"]}`}>
              {trend === "up" && "↑"} {trend === "down" && "↓"} {trendLabel}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * SECTION HEADER - Groups related cards
 */
export function DashboardSectionHeader({
  title,
  subtitle,
  icon: Icon,
  action,
}: {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-6 mt-8 pt-6 border-t border-white/10 first:mt-0 first:pt-0 first:border-t-0">
      <div className="flex items-center gap-3">
        {Icon && <Icon className="w-5 h-5 text-purple-400" />}
        <div>
          <h2 className="text-lg font-bold text-white">{title}</h2>
          {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

/**
 * TOOL CARD - Small interactive cards for actions
 */
export function DashboardToolCard({
  icon: Icon,
  label,
  description,
  onClick,
  disabled,
  loading,
  variant = "secondary",
}: {
  icon: LucideIcon;
  label: string;
  description?: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: "primary" | "secondary" | "danger";
}) {
  const variantStyles = {
    primary: "from-purple-600 to-purple-700 hover:from-purple-500 hover:to-purple-600",
    secondary: "from-white/10 to-white/5 hover:from-white/20 hover:to-white/10 border-white/10",
    danger: "from-red-600 to-red-700 hover:from-red-500 hover:to-red-600",
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`bg-gradient-to-br ${variantStyles[variant]}
                  rounded-xl px-4 py-3 border transition-all
                  disabled:opacity-50 disabled:cursor-not-allowed
                  hover:scale-105 transform duration-200
                  text-left`}
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-white/10">
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold text-white">
            {loading ? "Loading..." : label}
          </div>
          {description && (
            <div className="text-xs text-gray-300 mt-0.5">{description}</div>
          )}
        </div>
      </div>
    </button>
  );
}

/**
 * STATUS BADGE - Inline status indicator
 */
export function DashboardStatusBadge({
  status,
  label,
}: {
  status: "online" | "offline" | "warning" | "recording" | "streaming";
  label: string;
}) {
  const statusStyles = {
    online: "bg-green-500/20 border-green-500/40 text-green-300",
    offline: "bg-gray-500/20 border-gray-500/40 text-gray-300",
    warning: "bg-amber-500/20 border-amber-500/40 text-amber-300",
    recording: "bg-red-500/20 border-red-500/40 text-red-300",
    streaming: "bg-blue-500/20 border-blue-500/40 text-blue-300",
  };

  const dotColor = {
    online: "bg-green-400",
    offline: "bg-gray-400",
    warning: "bg-amber-400",
    recording: "bg-red-400",
    streaming: "bg-blue-400",
  };

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold ${statusStyles[status]}`}
    >
      <div className={`w-2 h-2 rounded-full ${dotColor[status]} animate-pulse`} />
      {label}
    </div>
  );
}

/**
 * CARD GRID - Responsive grid for KPI cards
 */
export function DashboardKPIGrid({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {children}
    </div>
  );
}

/**
 * TOOL GRID - Responsive grid for tool cards
 */
export function DashboardToolGrid({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
      {children}
    </div>
  );
}

/**
 * CONTENT SECTION - Container for grouped content
 */
export function DashboardContentSection({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6 mb-8">
      {children}
    </div>
  );
}
