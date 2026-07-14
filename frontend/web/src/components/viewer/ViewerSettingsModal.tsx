"use client";

import { useState } from "react";
import { X, Settings as SettingsIcon } from "lucide-react";

interface ViewerSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: Record<string, any>;
  onSettingsChange: (key: string, value: any) => void;
}

export default function ViewerSettingsModal({
  isOpen,
  onClose,
  settings,
  onSettingsChange,
}: ViewerSettingsModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-lg shadow-2xl w-full max-w-md border border-white/10">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <SettingsIcon className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-bold text-white">Viewer Preferences</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Settings */}
        <div className="p-6 space-y-6">
          {/* Theme */}
          <div>
            <label className="block text-sm font-semibold text-white mb-2">
              Theme
            </label>
            <select
              value={settings?.theme || "auto"}
              onChange={(e) => onSettingsChange("theme", e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-white/10 text-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20"
            >
              <option value="auto">Auto (System)</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>

          {/* Chat Cleanse */}
          <div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings?.chatCleanse || false}
                onChange={(e) =>
                  onSettingsChange("chatCleanse", e.target.checked)
                }
                className="w-4 h-4 rounded border-gray-400 text-purple-600 focus:ring-2 focus:ring-purple-500"
              />
              <span className="text-sm font-medium text-white">
                Clean up chat (filter spam/caps)
              </span>
            </label>
          </div>

          {/* Compact Mode */}
          <div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings?.compactMode || false}
                onChange={(e) =>
                  onSettingsChange("compactMode", e.target.checked)
                }
                className="w-4 h-4 rounded border-gray-400 text-purple-600 focus:ring-2 focus:ring-purple-500"
              />
              <span className="text-sm font-medium text-white">
                Compact mode (smaller text/cards)
              </span>
            </label>
          </div>

          {/* Notifications */}
          <div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings?.notifications !== false}
                onChange={(e) =>
                  onSettingsChange("notifications", e.target.checked)
                }
                className="w-4 h-4 rounded border-gray-400 text-purple-600 focus:ring-2 focus:ring-purple-500"
              />
              <span className="text-sm font-medium text-white">
                Enable notifications
              </span>
            </label>
          </div>

          {/* Volume */}
          <div>
            <label className="block text-sm font-semibold text-white mb-2">
              Sound Volume
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={settings?.volume || 70}
              onChange={(e) =>
                onSettingsChange("volume", Number(e.target.value))
              }
              className="w-full"
            />
            <p className="text-xs text-gray-400 mt-1">{settings?.volume || 70}%</p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-white/10 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-colors font-medium"
          >
            Close
          </button>
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700 transition-colors font-medium"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
