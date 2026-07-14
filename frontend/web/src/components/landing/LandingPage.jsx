import Navbar from "./Navbar"
import Hero from "./Hero"
import Features from "./Features"
import HowItWorks from "./HowItWorks"
import ViewerSection from "./ViewerSection"
import CTA from "./CTA"
import Footer from "./Footer"
import PricingSection from "./PricingSection"

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0d0716] text-white antialiased">
      <Navbar />
      <Hero />

      <div id="features">
        <Features />
      </div>

      <main className="mx-auto max-w-7xl space-y-6 px-6 py-16">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div id="how-it-works">
            <HowItWorks />
          </div>
          <div id="for-viewers">
            <ViewerSection />
          </div>
        </div>

        <PricingSection />
        <CTA />
        <Footer />
      </main>
    </div>
  )
}
