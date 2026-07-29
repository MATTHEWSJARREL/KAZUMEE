import { MessageCircle } from "lucide-react"

const TESTIMONIALS = [
  {
    quote: "Kazumee airdropped Man and your own best cliptokenomics into themosphere.",
    author: "Creator Name",
    role: "Twitch Streamer",
    avatar: "👤",
  },
  {
    quote: "Many anime have uncovered people outhandmade the best and we custom the community.",
    author: "Another Creator",
    role: "YouTube Streamer",
    avatar: "👤",
  },
]

export default function Testimonials() {
  return (
    <section className="relative z-20 border-t border-purple-500/20 bg-[#0d0716] py-20">
      <div className="mx-auto max-w-7xl px-6">
        {/* Testimonial Cards */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {TESTIMONIALS.map((testimonial, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-purple-500/20 bg-white/[0.03] p-8 backdrop-blur-md"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-pink-500 text-lg">
                  {testimonial.avatar}
                </div>
                <div className="flex-1">
                  <MessageCircle className="mb-3 h-4 w-4 text-purple-400" />
                  <p className="text-sm leading-relaxed text-neutral-300">
                    "{testimonial.quote}"
                  </p>
                  <div className="mt-4">
                    <p className="text-xs font-semibold text-white">{testimonial.author}</p>
                    <p className="text-xs text-neutral-500">{testimonial.role}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
