"use client";

import Link from "next/link";

import { Skeleton } from "@/components/ui/states";
import { cn } from "@/services/cn";
import { formatNumber, formatPct } from "@/services/format";
import type { DashboardSummary } from "@/services/types";

interface Metric {
  label: string;
  value: string | null;
  sub?: string;
  href: string;
  emphasis?: "positive" | "warning";
}

export function MetricStrip({ summary, loading }: { summary?: DashboardSummary; loading?: boolean }) {
  const s = summary;
  const delta = s ? s.today_discoveries - s.yesterday_discoveries : 0;
  const metrics: Metric[] = [
    { label: "Total products", value: formatNumber(s?.total_products), sub: s ? `${formatNumber(s.today_new_products)} new today` : undefined, href: "/explorer" },
    { label: "Active offers", value: formatNumber(s?.active_offers), sub: "Not expired or rejected", href: "/deals" },
    { label: "100%+ offers", value: formatNumber(s?.offers_100_plus), sub: "Advertised, incl. conditional", href: "/deals/100", emphasis: "positive" },
    { label: "Verified offers", value: formatNumber(s?.verified_offers), sub: "Manually confirmed", href: "/deals?status=VERIFIED" },
    { label: "Awaiting verification", value: formatNumber(s?.awaiting_verification), sub: "Detected / unverified / check", href: "/deals?status=DETECTED,UNVERIFIED,ACCOUNT_CHECK_REQUIRED", emphasis: "warning" },
    { label: "Monitored products", value: formatNumber(s?.monitored_products), sub: "In scan queue", href: "/explorer?monitored=true" },
    {
      label: "Today's discoveries",
      value: formatNumber(s?.today_discoveries),
      sub: s ? `${delta >= 0 ? "+" : ""}${delta} vs yesterday` : undefined,
      href: "/deals?detected=today",
    },
    {
      label: "Scanner success (7d)",
      value: s?.scanner_success_rate === null || s?.scanner_success_rate === undefined ? null : formatPct(s.scanner_success_rate, 1),
      sub: s ? `${s.scanner_runs_7d} completed runs` : undefined,
      href: "/scanner",
    },
  ];

  return (
    <div className="grid grid-cols-2 overflow-hidden rounded-md border border-line bg-surface sm:grid-cols-4 xl:grid-cols-4">
      {metrics.map((m, i) => (
        <Link
          key={m.label}
          href={m.href}
          className={cn(
            "group flex flex-col gap-0.5 border-line px-3 py-2.5 transition-colors hover:bg-subtle/70",
            i % 2 === 0 ? "border-r" : "sm:border-r",
            "border-b xl:border-b-0",
            i === metrics.length - 1 && "border-r-0",
          )}
        >
          <span className="eyebrow truncate">{m.label}</span>
          {loading || !s ? (
            <Skeleton className="my-1 h-5 w-16" />
          ) : (
            <span
              className={cn(
                "num text-xl font-semibold leading-7 tracking-tight",
                m.emphasis === "positive" && "text-positive",
                m.emphasis === "warning" && Number(m.value?.replace(/,/g, "")) > 0 && "text-warning",
              )}
            >
              {m.value ?? <span className="text-sm font-normal text-faint">Not available</span>}
            </span>
          )}
          <span className="truncate text-2xs text-faint">{m.sub ?? "\u00a0"}</span>
        </Link>
      ))}
    </div>
  );
}
