import { Link } from "react-router";
import { Play } from "lucide-react"

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Background image + overlays */}
      <div className="absolute inset-0 z-0">
        <img src="/hero-bg.jpg" alt="" className="h-full w-full object-cover" aria-hidden="true" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#0d0716] via-[#0d0716]/85 to-[#0d0716]/30" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0d0716] via-transparent to-transparent" />
      </div>

      <div className="relative z-20 mx-auto grid max-w-7xl grid-cols-1 gap-10 px-6 pb-32 pt-12 lg:grid-cols-2">
        {/* Left column: copy */}
        <div className="flex flex-col justify-center">
          <h1 className="text-6xl font-extrabold leading-[1.1] tracking-tight text-white sm:text-7xl lg:text-8xl">
            Stream.
            <br />
            Clip.
            <br />
            Report.
            <br />
            Repeat.
          </h1>

          <p className="mt-6 max-w-lg text-lg leading-relaxed text-neutral-300">
            The AI Co-Pilot that automatically clips your best stream moments and delivers a detailed post-stream report. Effortlessly.
          </p>

          <div className="mt-8 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
            <Link
              to="/auth"
              className="inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-purple-500 to-pink-600 px-8 py-3.5 text-base font-bold text-white shadow-lg shadow-purple-500/40 transition-transform hover:scale-105"
            >
              Connect Your Stream
            </Link>
            <button className="inline-flex items-center gap-2 text-sm font-semibold text-neutral-300 transition-colors hover:text-white">
              <Play className="h-4 w-4 fill-pink-400 text-pink-400" />
              Watch how it works (30s)
            </button>
          </div>
        </div>

        {/* Right column: avatar image */}
        <div className="relative flex items-center justify-center">
          <img
            src="/zumee-hero.png"
            alt="Kazumee AI Co-Pilot"
            className="relative z-10 w-full max-w-2xl drop-shadow-[0_0_60px_rgba(168,85,247,0.4)]"
          />
        </div>
      </div>
    </section>
  );
}
