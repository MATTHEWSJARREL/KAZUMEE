import { Link } from "react-router";

export default function PricingSection() {
  return (
    <section id="pricing" className="relative border-t border-white/5 bg-[#0d0716]">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,420px)_1fr] lg:items-start">
          {/* Heading */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-400">
              Pricing
            </p>
            <h2 className="mt-4 text-3xl font-extrabold leading-tight text-white sm:text-4xl">
              Plans that scale with your stream.
            </h2>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-neutral-400">
              Start free, upgrade anytime. Built for creators who want AI assistance without the hassle.
            </p>
          </div>

          {/* Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <PricingCard
              title="Starter"
              price="$0"
              subtitle="/forever"
              highlight={false}
              features={["Voice assistant", "Smart clipping", "Basic insights"]}
              ctaLabel="Start Free"
            />

            <PricingCard
              title="Pro"
              price="$19"
              subtitle="/month"
              highlight={true}
              features={["Advanced clipping", "Real-time recaps", "Stream safety alerts"]}
              ctaLabel="Go Pro"
            />
          </div>

          <div className="sm:col-span-2">
            <div className="mt-2 rounded-3xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-neutral-400">
                    30-day guarantee
                  </p>
                  <p className="mt-2 text-sm text-neutral-200">
                    Try Zumi risk-free—cancel anytime.
                  </p>
                </div>
                <Link
                  to="/auth"
                  className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-pink-500 to-purple-600 px-7 py-3 text-sm font-bold uppercase tracking-wider text-white shadow-lg shadow-pink-500/40 transition-transform hover:scale-105"
                >
                  Upgrade Now
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function PricingCard({
  title,
  price,
  subtitle,
  highlight,
  features,
  ctaLabel,
}) {
  return (
    <div
      className={
        "rounded-3xl border p-6 backdrop-blur-md transition-colors " +
        (highlight
          ? "border-pink-500/40 bg-gradient-to-b from-pink-500/10 to-white/[0.02]"
          : "border-white/10 bg-white/[0.02] hover:border-pink-500/30")
      }
    >
      {highlight ? (
        <div className="inline-flex items-center rounded-lg bg-pink-500/15 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-pink-300">
          Most Popular
        </div>
      ) : (
        <div className="h-[22px]" />
      )}

      <h3 className="mt-3 text-lg font-extrabold text-white">{title}</h3>

      <div className="mt-3 flex items-end gap-2">
        <div className="text-4xl font-extrabold leading-none text-white">{price}</div>
        <div className="pb-1 text-xs font-semibold uppercase tracking-wider text-neutral-400">{subtitle}</div>
      </div>

      <ul className="mt-5 space-y-3">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-3 text-sm text-neutral-200">
            <span className={"mt-1 h-2 w-2 rounded-full " + (highlight ? "bg-pink-400" : "bg-emerald-400")} />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      <Link
        to="/auth"
        className={
          "mt-6 inline-flex w-full items-center justify-center rounded-xl px-7 py-3 text-sm font-bold uppercase tracking-wider transition-transform hover:scale-[1.02] " +
          (highlight
            ? "bg-gradient-to-r from-pink-500 to-purple-600 text-white shadow-lg shadow-pink-500/40"
            : "border border-white/15 bg-white/5 text-white hover:bg-white/10")
        }
      >
        {ctaLabel}
      </Link>
    </div>
  )
}


