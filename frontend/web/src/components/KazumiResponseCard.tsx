"use client";

import { useEffect, useState } from "react";
import { X, Copy, Share2 } from "lucide-react";

export type KazumiResponse = {
  id: string;
  message: string;
  type?: "insight" | "answer" | "suggestion" | "warning";
  icon?: string;
  dismissible?: boolean;
  duration?: number;
};

type KazumiResponseCardProps = {
  response: KazumiResponse;
  onDismiss: (id: string) => void;
};

const KazumiResponseCard = ({ response, onDismiss }: KazumiResponseCardProps) => {
  const [shouldAutoClose, setShouldAutoClose] = useState(false);
  const duration = response.duration || 8000;
  const icon = response.icon || "✨";

  const typeStyles = {
    insight: "from-purple-600 to-purple-700 shadow-purple-600/30",
    answer: "from-blue-600 to-blue-700 shadow-blue-600/30",
    suggestion: "from-emerald-600 to-emerald-700 shadow-emerald-600/30",
    warning: "from-amber-600 to-amber-700 shadow-amber-600/30",
  };

  const style = typeStyles[response.type || "insight"];

  useEffect(() => {
    if (response.dismissible !== false) {
      const timer = setTimeout(() => {
        setShouldAutoClose(true);
        setTimeout(() => onDismiss(response.id), 300);
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [response.id, duration, response.dismissible, onDismiss]);

  return (
    <div
      className={`transition-all duration-300 ${
        shouldAutoClose ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0"
      }`}
    >
      <div
        className={`bg-gradient-to-br ${style} text-white rounded-2xl p-5
                    shadow-2xl backdrop-blur-xl border border-white/10
                    max-w-[420px] animate-in slide-in-from-bottom-2 fade-in`}
      >
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0 text-lg">
            {icon}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm leading-relaxed break-words">
              {response.message}
            </p>

            {/* Action Buttons */}
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => navigator.clipboard.writeText(response.message)}
                className="text-xs px-2.5 py-1.5 hover:bg-white/20 rounded-lg transition-colors flex items-center gap-1"
                title="Copy response"
              >
                <Copy className="w-3 h-3" />
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
                className="text-xs px-2.5 py-1.5 hover:bg-white/20 rounded-lg transition-colors flex items-center gap-1"
                title="Share response"
              >
                <Share2 className="w-3 h-3" />
                Share
              </button>
            </div>
          </div>

          {/* Close Button */}
          <button
            onClick={() => onDismiss(response.id)}
            className="p-1 hover:bg-white/20 rounded-lg transition-colors flex-shrink-0"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

type KazumiResponseContainerProps = {
  maxVisible?: number;
};

export const KazumiResponseContainer = ({
  maxVisible = 3,
}: KazumiResponseContainerProps) => {
  const [responses, setResponses] = useState<KazumiResponse[]>([]);

  const addResponse = (message: string, options?: Partial<KazumiResponse>) => {
    const id = `response-${Date.now()}`;
    const newResponse: KazumiResponse = {
      id,
      message,
      type: options?.type || "insight",
      icon: options?.icon || "✨",
      dismissible: options?.dismissible !== false,
      duration: options?.duration || 8000,
    };
    setResponses((prev) => [...prev, newResponse]);
  };

  const removeResponse = (id: string) => {
    setResponses((prev) => prev.filter((r) => r.id !== id));
  };

  return {
    container: (
      <div className="fixed bottom-6 right-6 z-40 pointer-events-none space-y-3">
        {responses.slice(-maxVisible).map((response) => (
          <div key={response.id} className="pointer-events-auto">
            <KazumiResponseCard
              response={response}
              onDismiss={removeResponse}
            />
          </div>
        ))}
      </div>
    ),
    addResponse,
    removeResponse,
  };
};

export default KazumiResponseCard;
