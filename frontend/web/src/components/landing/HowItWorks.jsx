import { Link2, Radio, LineChart } from "lucide-react"

const STEPS = [
  {
    num: "01",
    icon: Link2,
    title: "Connect",
    body: "Link your platforms in a few clicks.",
  },
  {
    num: "02",
    icon: Radio,
    title: "Go Live",
    body: "Zumi joins your stream and starts assisting.",
  },
  {
    num: "03",
    icon: LineChart,
    title: "Grow",
    body: "Get insights, clips and engagement on autopilot.",
  },
]

export default function HowItWorks() {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-md">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-400">How It Works</p>
      <h2 className="mt-4 text-3xl font-extrabold leading-tight text-white sm:text-4xl">
        Three steps.
        <br />
        Zero hassle.
      </h2>

      <div className="mt-10 grid grid-cols-1 gap-8 sm:grid-cols-3">
        {STEPS.map(({ num, icon: Icon, title, body }) => (
          <div key={num} className="relative">
            <div className="flex h-11 w-11 items-center justify-center rounded-full border border-pink-500/40 bg-pink-500/10 text-sm font-bold text-pink-400">
              {num}
            </div>
            <div className="mt-5 flex items-center gap-2 text-pink-400">
              <Icon className="h-4 w-4" />
              <h3 className="text-base font-bold text-white">{title}</h3>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-neutral-400">{body}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
