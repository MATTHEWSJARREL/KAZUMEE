import { pricingData } from "@/lib/pricing";

function PriceTag({ monthly, annual }) {
  if (!monthly) {
    return <div className="text-3xl font-bold">$0</div>;
  }
  return (
    <div>
      <div className="text-3xl font-bold">${monthly}</div>
      <div className="text-xs text-gray-500">or ${annual}/year</div>
    </div>
  );
}

function PlanCard({ plan }) {
  return (
    <div className={`kazumi-card p-5 relative ${plan.popular ? "border-black" : ""}`}>
      {plan.popular && (
        <div className="absolute -top-3 right-4 px-2 py-1 text-[10px] uppercase tracking-widest rounded-full bg-black text-white">
          Popular
        </div>
      )}
      <div className="mb-3">
        <div className="text-sm font-semibold">{plan.name}</div>
        <PriceTag monthly={plan.priceMonthly} annual={plan.priceAnnual} />
      </div>
      <div className="mb-4">
        <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Limits</div>
        <ul className="space-y-1">
          {plan.limits.map((item) => (
            <li key={item} className="text-sm text-gray-700">- {item}</li>
          ))}
        </ul>
      </div>
      <div className="mb-5">
        <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Includes</div>
        <ul className="space-y-1">
          {plan.features.map((item) => (
            <li key={item} className="text-sm text-gray-700">- {item}</li>
          ))}
        </ul>
      </div>
      <button className={`w-full px-4 py-2 rounded-md text-sm font-semibold ${plan.popular ? "bg-black text-white" : "bg-black/5 text-black"}`}>
        {plan.cta}
      </button>
    </div>
  );
}

export default function PricingSection() {
  return (
    <div className="kazumi-card p-6">
      <div className="flex items-center justify-between gap-4 mb-6">
        <div>
          <div className="text-xs uppercase tracking-widest text-gray-400 mb-1">Pricing</div>
          <h2 className="text-lg font-bold">Simple plans for viewers and streamers</h2>
        </div>
        <div className="text-xs text-gray-500">
          Annual saves {pricingData.annualDiscountPercent}%
        </div>
      </div>

      <div className="mb-7">
        <div className="text-sm font-semibold mb-3">Viewer Plans</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {pricingData.viewerPlans.map((plan) => (
            <PlanCard key={plan.id} plan={plan} />
          ))}
        </div>
      </div>

      <div>
        <div className="text-sm font-semibold mb-3">Streamer Plans</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {pricingData.streamerPlans.map((plan) => (
            <PlanCard key={plan.id} plan={plan} />
          ))}
        </div>
      </div>
    </div>
  );
}
