import { Link } from "react-router";
import { ArrowUpRight, Play, Link2 } from "lucide-react"

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Background image + overlays */}
      <div className="absolute inset-0 z-0">
        <img src="/hero-bg.jpg" alt="" className="h-full w-full object-cover" aria-hidden="true" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#0d0716] via-[#0d0716]/85 to-[#0d0716]/30" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0d0716] via-transparent to-transparent" />
      </div>

      {/* Hero android image */}
      <img
        src="/zumee-hero.png"
        alt="Zumi, the AI co-pilot android"
        className="pointer-events-none absolute bottom-0 right-0 z-10 hidden h-[95%] max-h-[760px] w-auto object-contain object-bottom lg:block"
      />

      <div className="relative z-20 mx-auto grid max-w-7xl grid-cols-1 gap-10 px-6 pb-24 pt-12 lg:grid-cols-2">
        {/* Left column: copy */}
        <div className="max-w-xl">
          <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-pink-400">
            <span className="h-2 w-2 rounded-full bg-pink-500 shadow-[0_0_10px_2px] shadow-pink-500" />
            Global AI Co-Pilot
          </span>

          <h1 className="mt-6 text-5xl font-extrabold leading-[0.95] tracking-tight text-white sm:text-6xl lg:text-7xl">
            Your Stream.
            <br />
            <span className="bg-gradient-to-r from-pink-500 to-purple-500 bg-clip-text text-transparent">
              Superhuman.
            </span>
          </h1>

          <p className="mt-6 max-w-md text-base leading-relaxed text-neutral-300">
            Meet Zumi, your AI co-pilot that monitors, assists, clips and grows your stream in real time.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              to="/auth"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-pink-500 to-purple-600 px-7 py-3.5 text-sm font-bold uppercase tracking-wider text-white shadow-lg shadow-pink-500/40 transition-transform hover:scale-105"
            >
              Start Free
              <ArrowUpRight className="h-4 w-4" />
            </Link>
            <Link
              to="/auth"
              className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-7 py-3.5 text-sm font-bold uppercase tracking-wider text-white backdrop-blur-md transition-colors hover:bg-white/10"
            >
              Watch Demo
              <Play className="h-4 w-4 fill-pink-500 text-pink-500" />
            </Link>
          </div>

          {/* Works with */}
          <div className="mt-10 flex items-center gap-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Works With</span>
            <div className="flex items-center gap-3 text-neutral-300">
              <TwitchGlyph />
              <YouTubeGlyph />
              <TikTokGlyph />
              <span className="text-xs font-medium text-neutral-400">+ More</span>
            </div>
          </div>
        </div>

        {/* Floating status cards */}
        <div className="relative hidden lg:block">
          <div className="absolute left-0 top-4 w-64 space-y-4">
            <StatusCard>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">System Status</p>
              <div className="mt-2 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_2px] shadow-emerald-400" />
                <span className="text-sm font-bold uppercase tracking-wide text-emerald-400">Online</span>
              </div>
              <div className="mt-3 flex h-6 items-end gap-0.5">
                {[3, 6, 4, 8, 5, 9, 4, 7, 3, 6, 8, 5, 4, 7, 3].map((h, i) => (
                  <span key={i} className="flex-1 rounded-sm bg-pink-500/70" style={{ height: `${h * 10}%` }} />
                ))}
              </div>
            </StatusCard>

            <StatusCard>
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Platforms</p>
                <Link2 className="h-3.5 w-3.5 text-neutral-500" />
              </div>
              <p className="mt-2 text-sm font-bold text-white">3 Connected</p>
              <div className="mt-3 flex items-center gap-2 text-neutral-300">
                <TwitchGlyph />
                <YouTubeGlyph />
                <TikTokGlyph />
              </div>
            </StatusCard>

            <StatusCard>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Zumi Listening</p>
              <div className="mt-3 flex h-8 items-center gap-0.5">
                {Array.from({ length: 28 }).map((_, i) => {
                  const h = 20 + Math.abs(Math.sin(i * 0.9)) * 80
                  return (
                    <span
                      key={i}
                      className="flex-1 rounded-sm bg-gradient-to-t from-pink-500 to-purple-400"
                      style={{ height: `${h}%` }}
                    />
                  )
                })}
              </div>
            </StatusCard>
          </div>

          {/* Right-side telemetry */}
          <div className="absolute right-0 top-8 space-y-6 text-right">
            <Telemetry label="Link Stable" value="48ms" />
            <Telemetry label="Voice Engine" value="Active" />
            <Telemetry label="Session" value="001" accent={false} />
          </div>
        </div>
      </div>
    </section>
  )
}

function StatusCard({ children }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-xl shadow-black/40 backdrop-blur-md">
      {children}
    </div>
  )
}

function Telemetry({ label, value, accent = true }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">{label}</p>
      <p className={`text-sm font-bold uppercase tracking-wide ${accent ? "text-emerald-400" : "text-white"}`}>
        {value}
      </p>
    </div>
  )
}

/* Brand glyphs (inline SVG so no extra deps) */
function TwitchGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M4 2 3 6v14h5v3h3l3-3h4l5-5V2H4Zm16 11-3 3h-4l-3 3v-3H7V4h13v9ZM15 7h-2v5h2V7Zm-5 0H8v5h2V7Z" />
    </svg>
  )
}
function YouTubeGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M23 12s0-3.6-.5-5.3a2.7 2.7 0 0 0-1.9-1.9C18.9 4.3 12 4.3 12 4.3s-6.9 0-8.6.5A2.7 2.7 0 0 0 1.5 6.7C1 8.4 1 12 1 12s0 3.6.5 5.3a2.7 2.7 0 0 0 1.9 1.9c1.7.5 8.6.5 8.6.5s6.9 0 8.6-.5a2.7 2.7 0 0 0 1.9-1.9C23 15.6 23 12 23 12ZM9.8 15.3V8.7l5.7 3.3-5.7 3.3Z" />
    </svg>
  )
}
function TikTokGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M16.5 2h-3v13.2a3 3 0 1 1-2.3-2.9V9.1a6.2 6.2 0 1 0 5.3 6.1V9a7.3 7.3 0 0 0 4.2 1.3V7.2a4.3 4.3 0 0 1-4.2-4.2V2Z" />
    </svg>
  )
}
