import { Mic, Clapperboard, Users, ShieldCheck } from "lucide-react"

const FEATURES = [
  {
    icon: Mic,
    title: "Voice Controlled",
    lead: "Talk naturally.",
    body: "Zumi listens, understands and acts.",
  },
  {
    icon: Clapperboard,
    title: "Smart Clipping",
    lead: "AI detects the best moments",
    body: "so you never miss a highlight.",
  },
  {
    icon: Users,
    title: "Viewer Companion",
    lead: "Helps new viewers catch up",
    body: "and stay engaged.",
  },
  {
    icon: ShieldCheck,
    title: "Stream Safety",
    lead: "Moderation, protection and",
    body: "alerts while you focus.",
  },
]

export default function Features() {
  return (
    <section className="relative z-20 border-t border-white/5 bg-[#0d0716]">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,320px)_1fr]">
          {/* Heading */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-400">Built For Creators</p>
            <h2 className="mt-4 text-3xl font-extrabold leading-tight text-white sm:text-4xl">
              Everything you need.
              <br />
              Nothing you don&apos;t.
            </h2>
          </div>

          {/* Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {FEATURES.map(({ icon: Icon, title, lead, body }) => (
              <div
                key={title}
                className="group rounded-2xl border border-white/10 bg-white/[0.03] p-5 backdrop-blur-md transition-colors hover:border-pink-500/40 hover:bg-white/[0.06]"
              >
                <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-pink-500/20 to-purple-600/20 text-pink-400 shadow-inner shadow-pink-500/20">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="text-sm font-bold text-white">{title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-neutral-400">
                  <span className="text-neutral-200">{lead}</span> {body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
