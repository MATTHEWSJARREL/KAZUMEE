"use client";

import PricingSection from "../../components/PricingSection";
import { ArrowLeft } from "lucide-react";

export default function PricingPage() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between gap-4 mb-6">
          <div>
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Plans</div>
            <h1 className="text-3xl md:text-4xl font-bold">Kazumi Pricing</h1>
          </div>
          <button
            onClick={() => (window.location.href = "/viewer")}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-black/10 rounded-md hover:bg-black/5"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">Back to Viewer</span>
          </button>
        </div>
        <PricingSection />
      </div>
    </div>
  );
}
