import { Twitter, MessageCircle, Youtube } from "lucide-react"

export default function Footer() {
  return (
    <footer className="flex flex-col items-center justify-between gap-6 border-t border-white/5 pt-8 md:flex-row">
      <div className="flex items-center gap-3">
        <img src="/logo.png" alt="Kazumee logo" className="h-8 w-8 object-contain" />
        <div>
          <p className="text-sm font-extrabold tracking-wide text-white">KAZUMEE</p>
          <p className="text-[10px] text-neutral-500">© 2025 Kazumee. All rights reserved.</p>
        </div>
      </div>

      <div className="flex items-center gap-5 text-neutral-400">
        <a
          href="https://twitter.com/kazumee"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Twitter"
          className="transition-colors hover:text-pink-400"
        >
          <Twitter className="h-5 w-5" />
        </a>
        <a
          href="https://discord.gg/kazumee"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Discord"
          className="transition-colors hover:text-pink-400"
        >
          <MessageCircle className="h-5 w-5" />
        </a>
        <a
          href="https://youtube.com/@kazumee"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="YouTube"
          className="transition-colors hover:text-pink-400"
        >
          <Youtube className="h-5 w-5" />
        </a>
      </div>
    </footer>
  )
}
