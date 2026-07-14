"use client";

export function AuthSocialProof() {
  return (
    <div className="text-center py-6">
      {/* Trust Metrics */}
      <div className="space-y-4">
        <div>
          <div className="text-3xl font-black text-white">500+</div>
          <p className="text-sm text-gray-400">Active Streamers</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="text-xl font-bold text-purple-400">10k+</div>
            <p className="text-xs text-gray-500">Clips Created</p>
          </div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="text-xl font-bold text-purple-400">99%</div>
            <p className="text-xs text-gray-500">Uptime</p>
          </div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="text-xl font-bold text-purple-400">24/7</div>
            <p className="text-xs text-gray-500">Support</p>
          </div>
        </div>

        {/* Review Snippet */}
        <div className="mt-6 p-4 rounded-lg bg-gradient-to-r from-yellow-500/10 to-amber-500/10
                       border border-yellow-500/20">
          <div className="flex items-center justify-center gap-1 mb-2">
            {[...Array(5)].map((_, i) => (
              <span key={i} className="text-lg">
                ⭐
              </span>
            ))}
          </div>
          <p className="text-sm text-gray-300 italic">
            "Kazumi transformed how I run my stream. Game changer!"
          </p>
          <p className="text-xs text-gray-500 mt-1">— Creator, Twitch</p>
        </div>

        {/* Feature List */}
        <div className="mt-6 space-y-2 text-left">
          <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-3">
            Why Choose Kazumi?
          </p>
          {[
            "AI-powered clip generation",
            "Real-time chat analytics",
            "Voice-controlled commands",
            "Multi-platform support",
          ].map((feature, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-purple-400">✓</span>
              <span className="text-sm text-gray-300">{feature}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function AuthErrorMessage({ message }: { message: string }) {
  // Parse specific errors for better UX
  const getHelpText = (err: string) => {
    if (err.includes("already exists")) {
      return "This account is already registered. Try signing in instead.";
    }
    if (err.includes("password")) {
      return "Password must be at least 8 characters with numbers and symbols.";
    }
    if (err.includes("invalid email")) {
      return "Please enter a valid email address.";
    }
    if (err.includes("credentials")) {
      return "Email or password incorrect. Please try again.";
    }
    return null;
  };

  const helpText = getHelpText(message);

  return (
    <div
      className="p-4 rounded-lg bg-red-500/10 border border-red-500/30
                 text-red-200 text-sm space-y-1"
    >
      <p className="font-semibold">⚠️ {message}</p>
      {helpText && <p className="text-xs text-red-300/70">{helpText}</p>}
    </div>
  );
}

export function AuthSuccessMessage({ message }: { message: string }) {
  return (
    <div
      className="p-4 rounded-lg bg-green-500/10 border border-green-500/30
                 text-green-200 text-sm font-medium"
    >
      ✓ {message}
    </div>
  );
}
