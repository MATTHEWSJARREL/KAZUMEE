"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { KazumiResponseContainer, type KazumiResponse } from "@/components/KazumiResponseCard";

type ResponseOptions = Partial<Omit<KazumiResponse, "id" | "message">>;

interface KazumiResponseContextType {
  showResponse: (message: string, options?: ResponseOptions) => void;
  showInsight: (message: string) => void;
  showAnswer: (message: string) => void;
  showSuggestion: (message: string) => void;
  showWarning: (message: string) => void;
}

const KazumiResponseContext = createContext<KazumiResponseContextType | null>(
  null
);

export const KazumiResponseProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const [responses, setResponses] = useState<KazumiResponse[]>([]);

  const addResponse = useCallback(
    (message: string, options?: ResponseOptions) => {
      const id = `response-${Date.now()}-${Math.random()}`;
      const newResponse: KazumiResponse = {
        id,
        message,
        type: options?.type || "insight",
        icon: options?.icon || "✨",
        dismissible: options?.dismissible !== false,
        duration: options?.duration || 8000,
      };
      setResponses((prev) => [...prev, newResponse]);

      if (options?.duration !== -1) {
        const timeout = setTimeout(() => {
          setResponses((prev) => prev.filter((r) => r.id !== id));
        }, newResponse.duration);

        return () => clearTimeout(timeout);
      }
    },
    []
  );

  const showResponse = useCallback(
    (message: string, options?: ResponseOptions) => {
      addResponse(message, options);
    },
    [addResponse]
  );

  const showInsight = useCallback(
    (message: string) => {
      addResponse(message, {
        type: "insight",
        icon: "✨",
      });
    },
    [addResponse]
  );

  const showAnswer = useCallback(
    (message: string) => {
      addResponse(message, {
        type: "answer",
        icon: "💡",
      });
    },
    [addResponse]
  );

  const showSuggestion = useCallback(
    (message: string) => {
      addResponse(message, {
        type: "suggestion",
        icon: "🎯",
      });
    },
    [addResponse]
  );

  const showWarning = useCallback(
    (message: string) => {
      addResponse(message, {
        type: "warning",
        icon: "⚠️",
      });
    },
    [addResponse]
  );

  const removeResponse = useCallback((id: string) => {
    setResponses((prev) => prev.filter((r) => r.id !== id));
  }, []);

  return (
    <KazumiResponseContext.Provider
      value={{
        showResponse,
        showInsight,
        showAnswer,
        showSuggestion,
        showWarning,
      }}
    >
      {children}
      {/* Response Container */}
      <div className="fixed bottom-6 right-6 z-40 pointer-events-none space-y-3 max-w-[420px]">
        {responses.slice(-3).map((response) => (
          <div key={response.id} className="pointer-events-auto">
            <div
              className={`transition-all duration-300 bg-gradient-to-br
                ${
                  response.type === "answer"
                    ? "from-blue-600 to-blue-700 shadow-blue-600/30"
                    : response.type === "suggestion"
                      ? "from-emerald-600 to-emerald-700 shadow-emerald-600/30"
                      : response.type === "warning"
                        ? "from-amber-600 to-amber-700 shadow-amber-600/30"
                        : "from-purple-600 to-purple-700 shadow-purple-600/30"
                }
                text-white rounded-2xl p-5 shadow-2xl backdrop-blur-xl
                border border-white/10 animate-in slide-in-from-bottom-2 fade-in`}
            >
              <div className="flex items-start gap-3">
                {/* Icon */}
                <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0 text-lg">
                  {response.icon || "✨"}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm leading-relaxed break-words">
                    {response.message}
                  </p>

                  {/* Action Buttons */}
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() =>
                        navigator.clipboard.writeText(response.message)
                      }
                      className="text-xs px-2.5 py-1.5 hover:bg-white/20 rounded-lg transition-colors"
                    >
                      Copy
                    </button>
                    <button
                      onClick={() => {
                        if (navigator.share) {
                          navigator.share({
                            text: response.message,
                            title: "Kazumi Insight",
                          });
                        }
                      }}
                      className="text-xs px-2.5 py-1.5 hover:bg-white/20 rounded-lg transition-colors"
                    >
                      Share
                    </button>
                  </div>
                </div>

                {/* Close Button */}
                <button
                  onClick={() => removeResponse(response.id)}
                  className="p-1 hover:bg-white/20 rounded-lg transition-colors flex-shrink-0 text-lg"
                >
                  ✕
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </KazumiResponseContext.Provider>
  );
};

export const useKazumiResponse = (): KazumiResponseContextType => {
  const context = useContext(KazumiResponseContext);
  if (!context) {
    throw new Error(
      "useKazumiResponse must be used within KazumiResponseProvider"
    );
  }
  return context;
};
