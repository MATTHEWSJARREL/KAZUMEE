import { Link } from "react-router";
import { ArrowUpRight } from "lucide-react"

export default function CTA() {
  return (
    <div className="flex flex-col items-center justify-between gap-6 rounded-3xl border border-white/10 bg-white/[0.02] p-8 backdrop-blur-md md:flex-row">
      <div>
        <h2 className="text-2xl font-extrabold text-white sm:text-3xl">Ready to elevate your stream?</h2>
        <p className="mt-2 text-sm text-neutral-400">
          Join thousands of creators who trust Zumi every day.
        </p>
      </div>

      <div className="flex flex-col items-center gap-6 sm:flex-row">
        <Link
          to="/auth"
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-pink-500 to-purple-600 px-7 py-3.5 text-sm font-bold uppercase tracking-wider text-white shadow-lg shadow-pink-500/40 transition-transform hover:scale-105"
        >
          Start Your Journey
          <ArrowUpRight className="h-4 w-4" />
        </Link>
        <div className="text-center sm:text-left">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Starting At</p>
          <p className="text-lg font-extrabold text-white">
            $19 <span className="text-xs font-medium text-neutral-400">/month</span>
          </p>
        </div>
      </div>
    </div>
  )
}
