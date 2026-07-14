"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/apiClient";
import { useSettings } from "../../lib/SettingsContext";

export default function SuperChatSorterPanel({ userRole }) {
  const { settings, updateSetting, saveSettings } = useSettings();
  const [superChatData, setSuperChatData] = useState({ grouped_notifications: [], to_answer: [], stats: null });
  const [superChatLoading, setSuperChatLoading] = useState(false);
  const [blockedKeywordInput, setBlockedKeywordInput] = useState("");

  const fetchSuperChatSorter = async () => {
    if (userRole !== "streamer") return;
    try {
      setSuperChatLoading(true);
      const response = await apiFetch("/api/events/streamer-view?window_minutes=15&limit=300");
      if (!response.ok) return;
      const data = await response.json();
      setSuperChatData({
        grouped_notifications: data.grouped_notifications || [],
        to_answer: data.to_answer || [],
        stats: data.stats || null,
      });
    } catch (error) {
      console.error("Error fetching super-chat sorter:", error);
    } finally {
      setSuperChatLoading(false);
    }
  };

  useEffect(() => {
    if (userRole !== "streamer") return;
    void fetchSuperChatSorter();
    const interval = window.setInterval(() => {
      void fetchSuperChatSorter();
    }, 5000);
    return () => window.clearInterval(interval);
  }, [userRole]);

  const saveSuperChatSettings = async () => {
    try {
      await saveSettings();
      void fetchSuperChatSorter();
      toast.success("Sorter preferences saved");
    } catch (error) {
      console.error("Failed to save super-chat settings:", error);
      toast.error("Failed to save sorter preferences");
    }
  };

  const setQuestionMuteMinutes = (minutes) => {
    if (!minutes || minutes <= 0) {
      updateSetting("superChatSorter", "muteQuestionsUntil", null);
      return;
    }
    const until = new Date(Date.now() + minutes * 60 * 1000).toISOString();
    updateSetting("superChatSorter", "muteQuestionsUntil", until);
  };

  const isQuestionMuted = (() => {
    const raw = settings?.superChatSorter?.muteQuestionsUntil;
    if (!raw) return false;
    const until = new Date(raw);
    return !Number.isNaN(until.getTime()) && until.getTime() > Date.now();
  })();

  const mutedMinutesLeft = (() => {
    if (!isQuestionMuted) return 0;
    const until = new Date(settings?.superChatSorter?.muteQuestionsUntil).getTime();
    return Math.max(1, Math.ceil((until - Date.now()) / 60000));
  })();

  const markQuestionAnswered = async (questionKey) => {
    try {
      const res = await apiFetch("/api/events/streamer-view/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_key: questionKey }),
      });
      if (!res.ok) {
        toast.error("Could not mark question answered");
        return;
      }
      setSuperChatData((prev) => ({
        ...prev,
        to_answer: (prev.to_answer || []).filter((q) => q.question_key !== questionKey),
      }));
      toast.success("Question marked answered");
    } catch (error) {
      console.error("Failed to mark question answered:", error);
      toast.error("Could not mark question answered");
    }
  };

  if (userRole !== "streamer") {
    return null;
  }

  return (
    <div className="kazumi-card p-6 mb-8">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Super-Chat Sorter</div>
          <h2 className="text-lg font-bold">Grouped chat + To-Answer queue</h2>
        </div>
        {superChatData?.stats && (
          <div className="text-xs text-gray-500">
            {superChatData.stats.messages_scanned} scanned &middot; {superChatData.stats.groups_detected} groups &middot; {superChatData.stats.questions_detected} questions
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <label className="flex items-center justify-between rounded-lg border border-black/10 px-3 py-2">
          <span className="text-sm">Enable Super-Chat Sorter</span>
          <input
            type="checkbox"
            checked={Boolean(settings?.superChatSorter?.enabled)}
            onChange={(event) => updateSetting("superChatSorter", "enabled", event.target.checked)}
            className="accent-black"
          />
        </label>
        <label className="flex items-center justify-between rounded-lg border border-black/10 px-3 py-2">
          <span className="text-sm">Extract Questions</span>
          <input
            type="checkbox"
            checked={Boolean(settings?.superChatSorter?.extractQuestions)}
            onChange={(event) => updateSetting("superChatSorter", "extractQuestions", event.target.checked)}
            className="accent-black"
          />
        </label>
      </div>

      <div className="mb-4 grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-lg border border-black/10 px-3 py-2">
          <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Question Source</div>
          <select
            value={settings?.superChatSorter?.questionSourceMode || "all"}
            onChange={(event) => updateSetting("superChatSorter", "questionSourceMode", event.target.value)}
            className="w-full border border-black/10 rounded-md px-2 py-1 text-sm bg-white"
          >
            <option value="all">All chat users</option>
            <option value="subs_mods">Subscribers + Mods only</option>
          </select>
        </div>
        <div className="rounded-lg border border-black/10 px-3 py-2">
          <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Question Mute</div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setQuestionMuteMinutes(5)} className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5">
              5m
            </button>
            <button onClick={() => setQuestionMuteMinutes(15)} className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5">
              15m
            </button>
            <button onClick={() => setQuestionMuteMinutes(30)} className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5">
              30m
            </button>
            <button onClick={() => setQuestionMuteMinutes(0)} className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5">
              Unmute
            </button>
          </div>
          <div className="text-[11px] text-gray-500 mt-2">{isQuestionMuted ? `Questions muted for ${mutedMinutesLeft}m` : "Questions active"}</div>
        </div>
      </div>

      <div className="mb-4">
        <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Blocked Question Keywords</div>
        <div className="flex flex-col md:flex-row gap-2">
          <input
            value={blockedKeywordInput}
            onChange={(event) => setBlockedKeywordInput(event.target.value)}
            placeholder="Add keyword (example: drama)"
            className="flex-1 px-3 py-2 border border-black/10 rounded-md text-sm bg-white"
          />
          <button
            onClick={() => {
              const value = blockedKeywordInput.trim().toLowerCase();
              if (!value) return;
              const prev = settings?.superChatSorter?.blockedQuestionKeywords || [];
              if (prev.includes(value)) return;
              updateSetting("superChatSorter", "blockedQuestionKeywords", [...prev, value]);
              setBlockedKeywordInput("");
            }}
            className="px-3 py-2 text-sm rounded-md border border-black/10 bg-white hover:bg-black/5"
          >
            Add
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {(settings?.superChatSorter?.blockedQuestionKeywords || []).map((keyword) => (
            <button
              key={keyword}
              onClick={() => {
                const next = (settings?.superChatSorter?.blockedQuestionKeywords || []).filter((value) => value !== keyword);
                updateSetting("superChatSorter", "blockedQuestionKeywords", next);
              }}
              className="px-2 py-1 rounded-full text-xs bg-black/5 hover:bg-black/10"
            >
              {keyword} x
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <button onClick={saveSuperChatSettings} className="px-4 py-2 rounded-md bg-black text-white text-sm font-semibold">
          Save Sorter Preferences
        </button>
      </div>

      {superChatLoading && <div className="text-xs text-gray-500 mb-3">Refreshing sorter...</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-black/10 p-4">
          <div className="text-sm font-semibold mb-3">Grouped Notifications</div>
          {superChatData.grouped_notifications.length === 0 ? (
            <div className="text-xs text-gray-500">No repeated chat bursts detected yet.</div>
          ) : (
            <div className="space-y-2">
              {superChatData.grouped_notifications.slice(0, 8).map((group, index) => (
                <div key={`${group.message}-${index}`} className="border border-black/5 rounded-md p-3">
                  <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">{group.count} people said</div>
                  <div className="text-sm font-semibold">{group.message}</div>
                  {group.sample_users?.length > 0 && <div className="text-[11px] text-gray-500 mt-1">Sample: {group.sample_users.join(", ")}</div>}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-black/10 p-4">
          <div className="text-sm font-semibold mb-3">To-Answer Questions</div>
          {superChatData.to_answer.length === 0 ? (
            <div className="text-xs text-gray-500">No questions extracted yet.</div>
          ) : (
            <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
              {superChatData.to_answer.slice(0, 12).map((question) => (
                <div key={question.id} className="border border-black/5 rounded-md p-3">
                  <div className="text-[11px] uppercase tracking-widest text-gray-400 mb-1">
                    {question.platform} - {question.username}
                    {question.is_sub_or_mod ? " - sub/mod" : ""}
                  </div>
                  <div className="text-sm">{question.message}</div>
                  <div className="mt-2">
                    <button onClick={() => void markQuestionAnswered(question.question_key)} className="px-2 py-1 text-xs rounded-md border border-black/10 hover:bg-black/5">
                      Mark answered
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
