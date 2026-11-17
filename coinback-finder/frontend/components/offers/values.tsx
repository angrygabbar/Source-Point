import { ImageOff } from "lucide-react";

import { NA } from "@/components/ui/states";
import { cn } from "@/services/cn";
import { formatINR, formatNumber, formatPct } from "@/services/format";
import type { OfferBrief } from "@/services/types";

export function PercentValue({ offer, size = "sm" }: { offer: Pick<OfferBrief, "advertised_percentage" | "is_up_to" | "reward_type" | "per_spend_coins" | "per_spend_amount"> | null; size?: "sm" | "lg" }) {
  if (!offer) return <NA />;
  if (offer.advertised_percentage === null) {
    if (offer.reward_type === "PER_SPEND_RATE" && offer.per_spend_coins && offer.per_spend_amount) {
      return (
        <span className="text-xs text-muted" title="Per-spend rate. Percentage not calculated until the eligible base is confirmed.">
          {offer.per_spend_coins}/{formatINR(offer.per_spend_amount)}
        </span>
      );
    }
    return <NA label="Not calculated" />;
  }
  const high = offer.advertised_percentage >= 100;
  return (
    <span className="inline-flex items-baseline justify-end gap-1" title={offer.is_up_to ? "Conditional 'up to' statement: not a guaranteed percentage." : "Advertised percentage."}>
      {offer.is_up_to ? <span className="text-2xs font-medium uppercase text-warning">up to</span> : null}
      <span className={cn("num font-semibold", size === "lg" ? "text-lg" : "text-sm", high ? "text-positive" : "text-fg")}>
        {formatPct(offer.advertised_percentage)}
      </span>
    </span>
  );
}

export function CoinsValue({ offer }: { offer: Pick<OfferBrief, "advertised_coins" | "estimated_coins"> | null }) {
  if (!offer) return <NA />;
  if (offer.advertised_coins !== null) return <span className="num">{formatNumber(offer.advertised_coins)}</span>;
  if (offer.estimated_coins !== null)
    return (
      <span className="num text-muted" title="Estimate derived from listed price and advertised percentage; not an advertised amount.">
        {formatNumber(offer.estimated_coins)}
        <span className="ml-1 text-2xs text-faint">est.</span>
      </span>
    );
  return <NA />;
}

export function CapValue({ cap }: { cap: number | null }) {
  return cap === null ? <NA label="Not confirmed" /> : <span className="num">{formatNumber(cap)}</span>;
}

export function Money({ value, precise }: { value: number | null | undefined; precise?: boolean }) {
  const text = formatINR(value, precise);
  return text ? <span className="num">{text}</span> : <NA />;
}

export function Thumb({ src, alt, size = 32 }: { src: string | null; alt: string; size?: number }) {
  return (
    <span className="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-sm border border-line bg-surface" style={{ width: size, height: size }}>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={alt} loading="lazy" referrerPolicy="no-referrer" className="h-full w-full object-contain" />
      ) : (
        <ImageOff className="h-3.5 w-3.5 text-faint" aria-hidden />
      )}
    </span>
  );
}
