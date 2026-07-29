import { Link } from "react-router";
import { ArrowUpRight } from "lucide-react"

export default function CTA() {
  return (
    <section className="relative z-20 border-t border-purple-500/20 bg-[#0d0716] py-20">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <h2 className="text-4xl font-extrabold text-white sm:text-5xl">
          Ready to level up your stream?
        </h2>
        <p className="mt-4 text-lg text-neutral-400">
          Get 5 free clips. No credit card required.
        </p>

        <Link
          to="/auth"
          className="mt-8 inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-purple-500 to-pink-600 px-8 py-4 text-base font-bold text-white shadow-lg shadow-purple-500/40 transition-transform hover:scale-105"
        >
          Get Started Free
          <ArrowUpRight className="h-4 w-4" />
        </Link>

        <p className="mt-6 text-sm text-neutral-500">
          Pro starts at <span className="font-semibold text-white">$9.99/month</span>
        </p>
      </div>
    </section>
  )
}
