import { Link } from "react-router";
import { ArrowUpRight } from "lucide-react";

const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Pricing", href: "#pricing" },
  { label: "Docs", href: "#docs" },
  { label: "Blog", href: "#blog" },
]

export default function Navbar() {
  return (
    <header className="relative z-30 w-full">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        {/* Logo */}
        <a href="#" className="flex items-center gap-3">
          <img src="/logo.png" alt="Kazumee logo" className="h-10 w-10 object-contain" />
          <span className="flex flex-col leading-none">
            <span className="text-lg font-extrabold tracking-wide text-white">KAZUMEE</span>
            <span className="text-[10px] font-semibold tracking-[0.2em] text-pink-400">AUTO-CLIP CREATOR</span>
          </span>
        </a>

        {/* Desktop links */}
        <ul className="hidden items-center gap-8 lg:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.label}>
              <a
                href={link.href}
                className="text-xs font-semibold uppercase tracking-wider text-neutral-300 transition-colors hover:text-white"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        {/* Actions */}
        <div className="flex items-center gap-4">
          <Link
            to="/auth"
            className="hidden text-xs font-semibold uppercase tracking-wider text-neutral-300 transition-colors hover:text-white sm:block"
          >
            Log In
          </Link>
          <Link
            to="/auth"
            className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-pink-500 to-purple-600 px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-white shadow-lg shadow-pink-500/30 transition-transform hover:scale-105"
          >
            Start Free
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </nav>
    </header>
  )
}
