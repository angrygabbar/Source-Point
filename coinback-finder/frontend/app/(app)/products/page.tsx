"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { GitCompare, RotateCcw } from "lucide-react";

import { DataTable, type Column } from "@/components/data-table/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { FilterGroup, FilterSelect, SearchInput } from "@/components/offers/filters";
import { toParams } from "@/components/offers/offers-table";
import { Money, PercentValue, Thumb } from "@/components/offers/values";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { Panel } from "@/components/ui/panel";
import { EmptyState, NA } from "@/components/ui/states";
import { useApi } from "@/hooks/use-api";
import { useUrlState } from "@/hooks/use-url-state";
import { cn } from "@/services/cn";
import { formatPct, formatRelative } from "@/services/format";
import type { Envelope, Facets, IntelligenceRow, Paged } from "@/services/types";

const DEFAULTS = { q: "", category: "", brand: "", has_offer: "", monitored: "", sort: "", order: "desc", page: "1", page_size: "50" };

function Change({ value }: { value: number | null }) {
  if (value === null || value === undefined) return <NA />;
  if (value === 0) return <span className="num text-muted">0%</span>;
  return <span className={cn("num", value < 0 ? "text-positive" : "text-negative")}>{value > 0 ? "+" : ""}{formatPct(value, 1)}</span>;
}

export default function ProductIntelligencePage() {
  const router = useRouter();
  const { state, update, reset, activeCount } = useUrlState(DEFAULTS);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const params = useMemo(() => toParams(state), [state]);
  const query = useApi<Paged<IntelligenceRow>>("/products/intelligence", params, { keepPrevious: true });
  const facets = useApi<Envelope<Facets>>("/products/facets");

  const columns: Column<IntelligenceRow>[] = [
    {
      id: "product",
      header: "Product",
      sortKey: "title",
      hideable: false,
      cell: (p) => (
        <div className="flex max-w-[340px] items-center gap-2.5">
          <Thumb src={p.image_url} alt="" />
          <div className="min-w-0">
            <Link href={`/products/${p.id}`} onClick={(e) => e.stopPropagation()} className="block truncate font-medium hover:text-accent">
              {p.title ?? "Title not available"}
            </Link>
            <p className="truncate text-2xs text-faint">{[p.brand, p.category].filter(Boolean).join(" · ") || "Not available"}</p>
          </div>
        </div>
      ),
    },
    { id: "price", header: "Current", sortKey: "price", align: "right", cell: (p) => <Money value={p.current_price} /> },
    { id: "low", header: "Lowest", align: "right", cell: (p) => <Money value={p.price_stats.lowest_price} /> },
    { id: "high", header: "Highest", align: "right", cell: (p) => <Money value={p.price_stats.highest_price} /> },
    { id: "avg", header: "Average", align: "right", cell: (p) => <Money value={p.price_stats.average_price} /> },
    {
      id: "vs_low",
      header: "vs. low",
      align: "right",
      cell: (p) => {
        const low = p.price_stats.lowest_price;
        if (low === null || low === undefined || p.current_price === null || low === 0) return <NA />;
        const diff = ((p.current_price - low) / low) * 100;
        return diff <= 0.01 ? <Badge tone="positive">At low</Badge> : <span className="num text-muted">+{formatPct(diff, 1)}</span>;
      },
    },
    { id: "change", header: "7-day change", align: "right", cell: (p) => <Change value={p.price_stats.change_7d_pct} /> },
    { id: "obs", header: "Observations", align: "right", defaultHidden: true, cell: (p) => <span className="num">{p.price_stats.observations ?? 0}</span> },
    { id: "sellers", header: "Sellers", align: "right", cell: (p) => <span className="num">{p.price_stats.distinct_sellers ?? 0}</span> },
    { id: "offers", header: "Offers", align: "right", cell: (p) => <span className="num">{p.offer_count}</span> },
    { id: "pct", header: "Best CoinBack", sortKey: "pct", align: "right", cell: (p) => (p.best_offer ? <PercentValue offer={p.best_offer} /> : <NA label="No offer" />) },
    { id: "checked", header: "Last checked", sortKey: "last_checked", cell: (p) => <span className="text-xs text-muted">{formatRelative(p.last_checked_at) ?? "Never"}</span> },
  ];

  const ids = [...selected];
  return (
    <>
      <PageHeader
        title="Product Intelligence"
        description="Recorded price ranges, seller changes and reward coverage per product. Select up to four products to compare."
        actions={
          <Button size="sm" variant="primary" disabled={ids.length < 1} onClick={() => router.push(`/compare?ids=${ids.join(",")}`)}>
            <GitCompare className="h-3.5 w-3.5" />
            Compare ({ids.length}/4)
          </Button>
        }
      />
      <Panel>
        <div className="border-b border-line px-3 py-2.5">
          <FilterGroup>
            <SearchInput value={state.q} onChange={(q) => update({ q })} placeholder="Search title, brand or PID" />
            <FilterSelect label="Category" value={state.category} onChange={(category) => update({ category })} options={(facets.data?.data.categories ?? []).map((c) => ({ value: c.value, label: c.value }))} />
            <FilterSelect label="Brand" value={state.brand} onChange={(brand) => update({ brand })} options={(facets.data?.data.brands ?? []).map((c) => ({ value: c.value, label: c.value }))} />
            <FilterSelect
              label="Offer"
              value={state.has_offer}
              onChange={(has_offer) => update({ has_offer })}
              allLabel="Any"
              options={[
                { value: "true", label: "Has active offer" },
                { value: "false", label: "No active offer" },
              ]}
            />
            {activeCount > 0 ? (
              <Button size="sm" variant="ghost" onClick={reset}>
                <RotateCcw className="h-3.5 w-3.5" /> Reset
              </Button>
            ) : null}
          </FilterGroup>
        </div>
        <DataTable
          storageKey="intelligence"
          columns={columns}
          rows={query.data?.data}
          rowKey={(p) => p.id}
          loading={query.isLoading || query.isFetching}
          error={query.error?.message}
          onRetry={() => query.refetch()}
          sort={state.sort}
          order={state.order as "asc" | "desc"}
          onSort={(sort, order) => update({ sort, order })}
          selection={{ selected, onChange: setSelected, max: 4 }}
          onRowClick={(p) => router.push(`/products/${p.id}`)}
          toolbar={<span className="text-xs text-muted">{query.data ? `${query.data.meta.total.toLocaleString("en-IN")} products` : "Loading…"}</span>}
          empty={<EmptyState title="No products recorded" description="Products appear after URL submission or permitted discovery." />}
          footer={<Pagination meta={query.data?.meta} onPage={(p) => update({ page: String(p) })} onPageSize={(s) => update({ page_size: String(s) })} />}
        />
      </Panel>
    </>
  );
}
