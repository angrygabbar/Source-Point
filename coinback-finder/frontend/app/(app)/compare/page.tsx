"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { ReactNode } from "react";
import { ExternalLink, X } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Confidence, OfferStatusBadge, SourceLabel } from "@/components/offers/status";
import { CapValue, CoinsValue, Money, PercentValue, Thumb } from "@/components/offers/values";
import { Badge } from "@/components/ui/badge";
import { Panel } from "@/components/ui/panel";
import { EmptyState, ErrorState, NA, Skeleton } from "@/components/ui/states";
import { useApi } from "@/hooks/use-api";
import { cn } from "@/services/cn";
import { formatDate, formatPct, formatRelative } from "@/services/format";
import type { CompareRow, Envelope } from "@/services/types";

type Row = { label: string; render: (p: CompareRow) => ReactNode; best?: (rows: CompareRow[]) => string | null };

function minBy(rows: CompareRow[], fn: (p: CompareRow) => number | null | undefined) {
  let best: CompareRow | null = null;
  for (const r of rows) {
    const v = fn(r);
    if (v === null || v === undefined) continue;
    if (!best || v < (fn(best) as number)) best = r;
  }
  return best?.id ?? null;
}
function maxBy(rows: CompareRow[], fn: (p: CompareRow) => number | null | undefined) {
  return minBy(rows, (r) => {
    const v = fn(r);
    return v === null || v === undefined ? null : -v;
  });
}

const ROWS: Row[] = [
  { label: "Selling price", render: (p) => <Money value={p.current_price} />, best: (r) => minBy(r, (p) => p.current_price) },
  { label: "MRP", render: (p) => <Money value={p.mrp} /> },
  { label: "Discount", render: (p) => formatPct(p.discount_percent, 0) ?? <NA /> },
  { label: "Historical low", render: (p) => <Money value={p.historical_low} />, best: (r) => minBy(r, (p) => p.historical_low) },
  { label: "Advertised CoinBack", render: (p) => (p.best_offer ? <PercentValue offer={p.best_offer} /> : <NA label="No offer" />), best: (r) => maxBy(r, (p) => p.best_offer?.advertised_percentage) },
  { label: "Coins", render: (p) => <CoinsValue offer={p.best_offer} />, best: (r) => maxBy(r, (p) => p.best_offer?.advertised_coins ?? p.best_offer?.estimated_coins) },
  { label: "Maximum reward", render: (p) => (p.best_offer ? <CapValue cap={p.best_offer.reward_cap_coins} /> : <NA />) },
  { label: "Est. effective cost", render: (p) => <Money value={p.best_offer_detail?.effective_cost_estimate} precise />, best: (r) => minBy(r, (p) => p.best_offer_detail?.effective_cost_estimate) },
  { label: "Seller", render: (p) => p.seller ?? <NA /> },
  {
    label: "Conditions",
    render: (p) => {
      const r = Object.entries(p.best_offer_detail?.restrictions ?? {});
      if (!p.best_offer_detail) return <NA />;
      return r.length ? <span className="text-xs">{r.map(([k, v]) => `${k}: ${v.join(", ")}`).join("; ")}</span> : <span className="text-xs text-faint">None detected</span>;
    },
  },
  { label: "Valid until", render: (p) => formatDate(p.best_offer?.valid_until) ?? <NA label="Not stated" /> },
  { label: "Verification", render: (p) => (p.best_offer ? <OfferStatusBadge status={p.best_offer.status} /> : <NA />) },
  { label: "Confidence", render: (p) => (p.best_offer ? <Confidence value={p.best_offer.confidence} /> : <NA />) },
  { label: "Evidence source", render: (p) => (p.best_offer ? <SourceLabel type={p.best_offer.source_type} /> : <NA />) },
  { label: "Last checked", render: (p) => formatRelative(p.last_checked_at) ?? "Never" },
];

export default function ComparePage() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = (params.get("ids") ?? "").split(",").filter(Boolean).slice(0, 4);
  const query = useApi<Envelope<CompareRow[]>>(ids.length ? "/products/compare" : null, { ids: ids.join(",") });
  const rows = query.data?.data ?? [];

  const remove = (id: string) => {
    const next = ids.filter((x) => x !== id);
    router.replace(next.length ? `/compare?ids=${next.join(",")}` : "/compare");
  };

  return (
    <>
      <PageHeader title="Compare products" description="Side-by-side comparison of up to four products using their strongest active offer. Highlighted cells mark the most favourable recorded value." />
      {!ids.length ? (
        <Panel>
          <EmptyState title="No products selected" description="Select up to four products in Product Intelligence or Deal Explorer." action={<Link href="/products" className="text-sm text-accent hover:underline">Open Product Intelligence</Link>} />
        </Panel>
      ) : query.isLoading ? (
        <Skeleton className="h-96" />
      ) : query.error ? (
        <ErrorState message={query.error.message} onRetry={() => query.refetch()} />
      ) : (
        <Panel className="overflow-x-auto">
          <table className="w-full min-w-[720px] table-fixed border-separate border-spacing-0 text-sm">
            <colgroup>
              <col className="w-[170px]" />
              {rows.map((r) => (
                <col key={r.id} />
              ))}
            </colgroup>
            <thead>
              <tr>
                <th className="border-b border-line bg-subtle" />
                {rows.map((p) => (
                  <th key={p.id} className="border-b border-l border-line bg-subtle p-3 text-left align-top font-normal">
                    <div className="flex items-start gap-2.5">
                      <Thumb src={p.image_url} alt="" size={48} />
                      <div className="min-w-0 flex-1">
                        <Link href={`/products/${p.id}`} className="line-clamp-2 text-sm font-medium hover:text-accent">
                          {p.title ?? "Title not available"}
                        </Link>
                        <p className="truncate text-2xs text-faint">{p.brand ?? "Brand not available"}</p>
                        <a href={p.product_url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-2xs text-accent hover:underline">
                          Flipkart <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                      <button type="button" onClick={() => remove(p.id)} className="rounded p-0.5 text-faint hover:text-fg" aria-label="Remove from comparison">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => {
                const best = row.best && rows.length > 1 ? row.best(rows) : null;
                return (
                  <tr key={row.label}>
                    <th scope="row" className="border-b border-line px-3 py-2 text-left text-xs font-medium text-muted">
                      {row.label}
                    </th>
                    {rows.map((p) => (
                      <td key={p.id} className={cn("num border-b border-l border-line px-3 py-2", best === p.id && "bg-positive-soft/70")}>
                        <div className="flex items-center gap-1.5">
                          {row.render(p)}
                          {best === p.id ? <Badge tone="positive">Best</Badge> : null}
                        </div>
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>
      )}
    </>
  );
}
