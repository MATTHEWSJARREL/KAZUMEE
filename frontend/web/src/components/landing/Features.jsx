import { Zap, Clapperboard, BarChart3 } from "lucide-react"

const FEATURES = [
  {
    icon: Zap,
    title: "AI CLIP DETECTION",
    description: "Never miss a moment. AI detects highlights, clutches, and epic reactions.",
  },
  {
    icon: Clapperboard,
    title: "AUTO-GENERATED CLIPS",
    description: "Instant, formatted clips ready for social. No manual editing required.",
  },
  {
    icon: BarChart3,
    title: "STREAM REPORTS",
    description: "Get a comprehensive breakdown of viewer spikes, clip performance, and growth metrics.",
  },
]

export default function Features() {
  return (
    <section className="relative z-20 bg-[#0d0716]">
      <div className="mx-auto max-w-7xl px-6 py-24">
        {/* Cards */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="group rounded-2xl border border-purple-500/30 bg-white/[0.05] p-8 backdrop-blur-md transition-all hover:border-pink-500/50 hover:bg-white/[0.08] hover:shadow-[0_0_40px_rgba(168,85,247,0.2)]"
            >
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500/30 to-pink-500/30 text-purple-300 shadow-lg shadow-purple-500/20">
                <Icon className="h-7 w-7" />
              </div>
              <h3 className="text-sm font-bold uppercase tracking-wide text-white">{title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-neutral-400">
                {description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
