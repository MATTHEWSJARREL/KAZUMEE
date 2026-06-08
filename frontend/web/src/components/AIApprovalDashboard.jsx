"use client";
import React, { useState, useEffect } from 'react';
import { Check, X, Zap } from "lucide-react";
import { apiFetch } from "@/lib/apiClient";

const AIApprovalDashboard = () => {
  const [suggestions, setSuggestions] = useState([]);

  const fetchSuggestions = async () => {
    try {
      const response = await apiFetch("/api/dashboard");
      const data = await response.json();
      // Filter only for pending suggestions from Kazumi
      const pending = data.recentActivity.filter(
        (a) => a.status === "pending" || a.status === "pending_approval",
      );
      setSuggestions(pending);
    } catch (e) { console.error("Poll error", e); }
  };

  useEffect(() => {
    fetchSuggestions();
    const interval = setInterval(fetchSuggestions, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (id, status) => {
    await apiFetch(`/commands/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    fetchSuggestions();
  };

  const handleBulkAction = async (ids, status) => {
    try {
      // Process each ID and collect errors
      const errors = [];
      for (const id of ids) {
        try {
          await handleAction(id, status);
        } catch (err) {
          errors.push(`ID ${id}: ${err.message}`);
        }
      }
      
      // Single refresh after all updates
      await fetchSuggestions();
      
      // Show error if any occurred
      if (errors.length > 0) {
        console.error('Some actions failed:', errors);
      }
    } catch (err) {
      console.error('Bulk action failed:', err);
    }
  };

  if (suggestions.length === 0) return null; // Hide if nothing to approve

  const groupedSuggestions = suggestions.reduce((acc, item) => {
    const actionType = item?.action_type || item?.type || item?.intent || "suggestion";
    const reasoningText = item?.reasoning_text || item?.commentary || item?.ai_reasoning || item?.description || "";
    const key = `${String(actionType).trim().toLowerCase()}::${String(reasoningText).trim().toLowerCase()}`;
    if (!acc[key]) {
      acc[key] = {
        item: {
          ...item,
          action_type: actionType,
          reasoning_text: reasoningText,
        },
        ids: [item.id],
        count: 0,
      };
    } else {
      acc[key].ids.push(item.id);
    }
    acc[key].count += 1;
    return acc;
  }, {});

  const dedupedSuggestions = Object.values(groupedSuggestions).map((entry) => entry);

  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-[7px] h-[7px] rounded-full animate-pulse bg-[#7C5CFC]" />
        <span className="text-[9px] uppercase tracking-[0.18em] text-gray-500">Zumi suggests</span>
      </div>

      <div className="space-y-3">
        {dedupedSuggestions.map(({ item, ids, count }) => (
          <div
            key={`${item.id}-${item.action_type}-${item.reasoning_text}`}
            className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-4 border border-gray-200 rounded-md bg-white hover:bg-gray-50 transition-colors"
            style={{ borderLeft: "3px solid rgba(124,92,252,0.4)" }}
          >
            {count > 1 && (
              <span className="absolute top-2 right-2 bg-black text-white text-[10px] px-2 py-0.5 rounded-full">
                x{count}
              </span>
            )}
            <div className="flex-1 pr-10">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="w-3 h-3 text-yellow-500" fill="currentColor" />
                <span className="text-xs font-bold text-gray-500 uppercase">{item.description || item.action_type}</span>
              </div>
              {item.reasoning_text?.trim() ? (
                <p className="text-sm font-medium text-black">"{item.reasoning_text}"</p>
              ) : (
                <p className="text-sm font-medium text-gray-400 italic">No reasoning provided</p>
              )}
            </div>

            <div className="flex gap-2 w-full md:w-auto">
              <button
                onClick={() => handleBulkAction(ids, 'approved')}
                className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-[#00E5A0] text-black px-4 py-2 rounded font-semibold text-xs hover:brightness-95 transition-all"
              >
                <Check className="w-4 h-4" /> Approve
              </button>
              <button
                onClick={() => handleBulkAction(ids, 'rejected')}
                className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-transparent text-gray-600 border border-gray-300 px-4 py-2 rounded font-semibold text-xs hover:bg-gray-100 transition-all"
              >
                <X className="w-4 h-4" /> Skip
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AIApprovalDashboard;

