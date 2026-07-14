import { Link } from "react-router";
import { ArrowRight, Swords, Gem, MapPin } from "lucide-react"

export default function ViewerSection() {
  return (
    <div className="grid grid-cols-1 gap-8 rounded-3xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-md lg:grid-cols-2 lg:items-center">
      {/* Copy */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-400">For Viewers</p>
        <h2 className="mt-4 text-3xl font-extrabold leading-tight text-white sm:text-4xl">
          Never join a stream
          <br />
          lost again.
        </h2>
        <p className="mt-4 max-w-md text-sm leading-relaxed text-neutral-400">
          Zumi gives every viewer the full picture with AI-powered recaps and context.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-3">
          <Link
            to="/auth"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-pink-500 to-purple-600 px-6 py-3 text-xs font-bold uppercase tracking-wider text-white shadow-lg shadow-pink-500/30 transition-transform hover:scale-105"
          >
            Watch as a Viewer
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="https://www.youtube.com/watch?v=demo"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-6 py-3 text-xs font-bold uppercase tracking-wider text-white transition-colors hover:bg-white/10"
          >
            See It In Action
            <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </div>

      {/* Recap card */}
      <div className="rounded-2xl border border-white/10 bg-[#140b22]/80 p-4 shadow-2xl shadow-black/50">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 rounded-md bg-red-500/20 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-red-400">
            <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
            Live Now
          </span>
          <span className="text-[10px] font-medium text-neutral-400">2.4k Viewers</span>
        </div>

        <div className="mt-4 flex gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <div className="h-16 w-24 flex-shrink-0 overflow-hidden rounded-lg bg-gradient-to-br from-purple-700 to-pink-600" />
          <div className="min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-bold text-pink-400">AI Recap</span>
              <span className="text-[10px] text-neutral-500">3 min ago</span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-neutral-300">
              Streamer just completed a major boss fight and unlocked a rare item!
            </p>
          </div>
        </div>

        {/* Timeline */}
        <div className="mt-4 flex items-center justify-between text-[10px] font-medium text-neutral-500">
          <span>-15m</span>
          <span>-9m</span>
        </div>
        <div className="mt-2 grid grid-cols-4 gap-2 text-[10px] text-neutral-300">
          <TimelineChip icon={Swords} label="Boss" sub="6:06" />
          <TimelineChip icon={Gem} label="Loot" sub="-10m" />
          <TimelineChip icon={MapPin} label="Live" sub="Live" />
          <TimelineChip icon={MapPin} label="Now" sub="●" accent />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {["Boss Fight", "Rare Drop", "New Area"].map((tag) => (
            <span
              key={tag}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-300"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

function TimelineChip({ icon: Icon, label, sub, accent = false }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg border border-white/10 bg-white/[0.03] py-2">
      <Icon className={`h-3.5 w-3.5 ${accent ? "text-pink-400" : "text-neutral-400"}`} />
      <span className="text-neutral-400">{sub}</span>
    </div>
  )
}
