"use client";

import { useState } from "react";
import { Link, useNavigate } from "react-router";
import {
  Bot,
  Brain,
  Home,
  MessageSquare,
  Mic,
  Radio,
  Scissors,
  Search,
  Settings,
  Shield,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";

const NAV_ITEMS = [
  { name: "Dashboard", icon: Home, href: "/dashboard", roles: ["streamer"] },
  { name: "Viewer Mode", icon: Users, href: "/viewer", roles: ["viewer"] },
  { name: "Stream Health", icon: Radio, href: "/stream-health", roles: ["streamer"] },
  { name: "Clips Library", icon: Scissors, href: "/clips", roles: ["streamer"] },
  { name: "Moderation", icon: Shield, href: "/moderation", roles: ["streamer"] },
  { name: "Command Queue", icon: MessageSquare, href: "/commands", roles: ["streamer"] },
  { name: "Analytics", icon: TrendingUp, href: "/analytics", roles: ["streamer"] },
  { name: "ML Training", icon: Brain, href: "/ml-training", roles: ["streamer"] },
  { name: "Voice Control", icon: Mic, href: "/voice", roles: ["streamer"] },
  { name: "Setup Wizard", icon: Users, href: "/setup", roles: ["streamer"] },
  { name: "Settings", icon: Settings, href: "/settings", roles: ["streamer"] },
];

export default function DashboardShell({
  children,
  header,
  userRole,
  streamers,
  activeStreamerId,
  chooseStreamer,
  authUser,
  settings,
  dashboardData,
  lastHandledActivity,
  isPanicMode,
  deactivatePanicMode,
  clipNowBusy,
  clipPulse,
  onTriggerClipNow,
  isStreaming,
}) {
  const navigate = useNavigate();
  const [mode, setMode] = useState("streamer");
  const [toolSearch, setToolSearch] = useState("");
  const [showOnboarding, setShowOnboarding] = useState(false);
  const filteredNavItems = NAV_ITEMS.filter((item) => item.roles.includes(userRole)).filter((item) =>
    item.name.toLowerCase().includes(toolSearch.trim().toLowerCase()),
  );
  return (
    <>
      <div className="flex flex-col md:flex-row min-h-screen text-[var(--text)]">
        <div className="w-full md:w-72 border-r border-white/10 p-6 flex flex-col bg-[rgba(23,20,42,0.88)] backdrop-blur-xl">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 bg-black rounded-md flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" strokeWidth={1.5} />
            </div>
            <span className="text-lg font-semibold tracking-tight">Kazumi AI</span>
          </div>

          <div className="mb-6 p-1 bg-black/5 rounded-xl flex">
            <button
              onClick={() => setMode("streamer")}
              className={`flex-1 px-3 py-2 rounded-lg text-xs font-semibold transition-colors ${
                mode === "streamer" ? "bg-black text-white" : "text-gray-600 hover:text-black"
              }`}
            >
              Streamer
            </button>
            {userRole === "viewer" && (
              <button
                onClick={() => navigate("/viewer")}
                className={`flex-1 px-3 py-2 rounded-lg text-xs font-semibold transition-colors ${
                  mode === "viewer" ? "bg-black text-white" : "text-gray-600 hover:text-black"
                }`}
              >
                Viewer
              </button>
            )}
          </div>

          {userRole === "streamer" && (
            <div className="mb-4">
              <label className="sr-only" htmlFor="tool-search">
                Search tools
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  id="tool-search"
                  value={toolSearch}
                  onChange={(event) => setToolSearch(event.target.value)}
                  placeholder="Search tools..."
                  className="w-full h-10 pl-9 pr-3 rounded-lg border border-white/10 bg-white/5 text-sm text-[var(--text)] placeholder:text-gray-500 focus:border-white/30"
                />
              </div>
            </div>
          )}

          <nav className="space-y-2 flex-1">
            {filteredNavItems.map((item) => {
              const IconComponent = item.icon;
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-xl w-full text-left text-sm transition-colors ${
                    item.active ? "bg-black text-white shadow-sm" : "text-gray-700 hover:bg-white/10"
                  }`}
                >
                  <IconComponent className="w-[18px] h-[18px]" strokeWidth={1.5} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
            {filteredNavItems.length === 0 && (
              <div className="px-3 py-2 text-xs text-gray-500">No tools match that search.</div>
            )}
          </nav>

          {userRole === "viewer" && streamers.length > 0 && (
            <div className="mt-4 rounded-2xl border border-black/5 bg-white/80 p-3">
              <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-2">Watching</div>
              <div className="space-y-1">
                {streamers.slice(0, 3).map((streamer) => (
                  <button
                    key={streamer.id}
                    onClick={() => chooseStreamer(streamer.id)}
                    className={`w-full text-left px-2 py-1 rounded-lg text-xs ${
                      Number(activeStreamerId) === Number(streamer.id)
                        ? "bg-black text-white"
                        : "bg-black/5 text-gray-700 hover:bg-black/10"
                    }`}
                  >
                    {streamer.display_name}
                  </button>
                ))}
                {streamers.length > 3 && (
                  <Link to="/auth" className="text-xs text-gray-500 hover:text-black">
                    Manage streamers {'->'}
                  </Link>
                )}
              </div>
            </div>
          )}

          <div className="kazumi-card flex items-center gap-3 p-4 mt-8">
            <Zap className={`w-5 h-5 ${dashboardData?.aiActive ? "text-green-400" : "text-gray-300"}`} fill="currentColor" />
            <div className="flex-1">
              <div className="text-sm font-bold">AI Kazumi {dashboardData?.aiActive ? "Live" : "Idle"}</div>
              <div className="text-xs text-gray-500">{dashboardData?.mlConfidence || 0}% confidence</div>
            </div>
          </div>

          <div className="kazumi-card p-4 mt-4">
            <div className="text-[9px] uppercase tracking-widest text-gray-500 mb-1">Last action</div>
            <div className="text-[11px] text-gray-700">
              {lastHandledActivity?.description || lastHandledActivity?.commentary || "No handled actions yet."}
            </div>
          </div>

          <div className="kazumi-card flex items-center justify-between p-4 mt-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-black/5 rounded-full flex items-center justify-center text-xs font-semibold">
                {authUser?.email ? authUser.email.slice(0, 2).toUpperCase() : "KP"}
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-semibold">
                  {settings?.profile?.displayName || authUser?.email || dashboardData?.userName || "KazumiPro"}
                </span>
                <span className="text-[10px] uppercase tracking-widest text-gray-500">
                  {authUser?.role || "guest"}
                </span>
              </div>
            </div>
            <Link
              to="/auth"
              className="px-3 py-1.5 text-xs font-semibold border border-gray-300 rounded-full hover:bg-gray-50"
            >
              {authUser ? "Account" : "Sign In"}
            </Link>
          </div>
        </div>

        <div className="flex-1 p-6 md:p-10 overflow-y-auto">
          {header}
          {children}
        </div>
      </div>

      {showOnboarding && userRole === "viewer" && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Welcome Viewer</div>
            <h2 className="text-xl font-bold mb-2">Who are you watching?</h2>
            <p className="text-sm text-gray-600 mb-4">Pick a streamer to sync clips, lore, and voting.</p>
            <div className="space-y-2">
              {streamers.map((streamer) => (
                <button
                  key={streamer.id}
                  onClick={() => chooseStreamer(streamer.id)}
                  className="w-full text-left px-3 py-2 rounded-md bg-gray-100 hover:bg-gray-200 text-sm"
                >
                  {streamer.display_name}{" "}
                  <span className="text-xs text-gray-500">({streamer.platform})</span>
                </button>
              ))}
              {streamers.length === 0 && <div className="text-xs text-gray-500">No streamers found yet.</div>}
            </div>
            <button
              onClick={() => setShowOnboarding(false)}
              className="mt-4 w-full px-4 py-2 border border-gray-200 rounded-md text-sm hover:bg-gray-50"
            >
              Skip for now
            </button>
          </div>
        </div>
      )}

      {isPanicMode && (
        <div className="fixed inset-0 z-50 bg-red-600 bg-opacity-90 flex items-center justify-center">
          <div className="text-center text-white">
            <Shield className="w-24 h-24 mx-auto mb-4 animate-pulse" />
            <h1 className="text-4xl font-bold mb-2">SHIELD ACTIVE</h1>
            <p className="text-lg mb-4">Panic mode engaged. Stream protected.</p>
            <button
              onClick={deactivatePanicMode}
              className="px-6 py-3 bg-white text-red-600 font-bold rounded-lg hover:bg-gray-100 transition-colors"
            >
              Deactivate Shield
            </button>
          </div>
        </div>
      )}

      {userRole === "streamer" && isStreaming && (
        <button
          onClick={() => void onTriggerClipNow()}
          disabled={clipNowBusy}
          className={`fixed bottom-6 right-6 z-40 w-14 h-14 bg-black text-white rounded-full shadow-xl flex items-center justify-center hover:scale-110 active:scale-95 transition-transform ${
            clipPulse ? "ring-4 ring-indigo-300 ring-offset-2 animate-pulse" : ""
          } ${clipNowBusy ? "opacity-60 cursor-not-allowed" : ""}`}
          title="Clip now (Ctrl/Cmd+Shift+C)"
        >
          <Scissors className="w-5 h-5" />
        </button>
      )}
    </>
  );
}
