"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, ExternalLink, GitCompare, Plus, RotateCcw, SlidersHorizontal, Star } from "lucide-react";

import { DataTable, StopRowClick, type Column } from "@/components/data-table/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { AddProductDialog } from "@/components/offers/add-product-dialog";
import { FilterGroup, FilterSelect, NumberFilter, SearchInput } from "@/components/offers/filters";
import { toParams } from "@/components/offers/offers-table";
import { AccessBadge, OfferStatusBadge, SourceLabel } from "@/components/offers/status";
import { ExportMenu, SavedFilters } from "@/components/offers/table-tools";
import { CapValue, CoinsValue, Money, PercentValue, Thumb } from "@/components/offers/values";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { Panel } from "@/components/ui/panel";
import { EmptyState, NA } from "@/components/ui/states";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { useUrlState } from "@/hooks/use-url-state";
import { api } from "@/services/api";
import { formatDateTimeShort, formatPct, formatRelative, OFFER_STATUS_LABEL, SOURCE_TYPE_LABEL } from "@/services/format";
import type { Envelope, Facets, OfferStatus, Paged, ProductRow, SourceType } from "@/services/types";

const DEFAULTS = {
  q: "",
  category: "",
  brand: "",
  seller: "",
  min_price: "",
  max_price: "",
  min_pct: "",
  max_pct: "",
  status: "",
  source_type: "",
  has_offer: "",
  monitored: "",
  sort: "",
  order: "desc",
  page: "1",
  page_size: "50",
};

export default function DealExplorerPage() {
  const router = useRouter();
  const url = useUrlState(DEFAULTS);
  const { state, update, replaceAll, reset, activeCount } = url;
  const [advanced, setAdvanced] = useState(activeCount > 1);
  const [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const params = useMemo(() => toParams(state), [state]);
  const query = useApi<Paged<ProductRow>>("/products", params, { keepPrevious: true, refetchInterval: 60_000 });
  const facets = useApi<Envelope<Facets>>("/products/facets");

  const monitor = useApiMutation(
    async ({ ids, on }: { ids: string[]; on: boolean }) => {
      for (const id of ids) await (on ? api.post(`/monitoring/${id}`, {}) : api.del(`/monitoring/${id}`));
      return ids.length;
    },
    { invalidate: ["/products", "/monitoring", "/dashboard"], success: (n) => `Monitoring updated for ${n} product${n === 1 ? "" : "s"}` },
  );
  const watch = useApiMutation(
    async (ids: string[]) => {
      for (const id of ids) await api.post("/watchlist", { product_id: id });
      return ids.length;
    },
    { invalidate: ["/watchlist"], success: (n) => `${n} product${n === 1 ? "" : "s"} saved to watchlist` },
  );

  const columns: Column<ProductRow>[] = useMemo(
    () => [
      { id: "thumb", header: "", label: "Thumbnail", width: "44px", cell: (p) => <Thumb src={p.image_url} alt="" /> },
      {
        id: "title",
        header: "Title",
        sortKey: "title",
        hideable: false,
        cell: (p) => (
          <div className="max-w-[320px]">
            <Link href={`/products/${p.id}`} onClick={(e) => e.stopPropagation()} className="block truncate font-medium hover:text-accent" title={p.title ?? undefined}>
              {p.title ?? "Title not available"}
            </Link>
            <div className="flex items-center gap-1.5 text-2xs text-faint">
              {p.flipkart_pid ? <span className="font-mono">{p.flipkart_pid}</span> : null}
              {p.is_monitored ? <Badge tone="accent">Monitored</Badge> : null}
              {p.access_status !== "OK" ? <AccessBadge status={p.access_status} title={p.last_access_error} /> : null}
            </div>
          </div>
        ),
      },
      { id: "brand", header: "Brand", sortKey: "brand", cell: (p) => p.brand ?? <NA /> },
      { id: "category", header: "Category", sortKey: "category", cell: (p) => <span className="block max-w-[160px] truncate">{p.category ?? <NA />}</span> },
      { id: "price", header: "Price", sortKey: "price", align: "right", cell: (p) => <Money value={p.current_price} /> },
      { id: "mrp", header: "MRP", sortKey: "mrp", align: "right", cell: (p) => <Money value={p.mrp} /> },
      { id: "discount", header: "Discount", sortKey: "discount", align: "right", cell: (p) => (p.discount_percent === null ? <NA /> : formatPct(p.discount_percent, 0)) },
      { id: "coins", header: "Adv. coins", sortKey: "coins", align: "right", cell: (p) => <CoinsValue offer={p.best_offer} /> },
      { id: "pct", header: "CoinBack", sortKey: "pct", align: "right", hideable: false, cell: (p) => (p.best_offer ? <PercentValue offer={p.best_offer} /> : <NA label="No offer" />) },
      { id: "cap", header: "Max reward", sortKey: "cap", align: "right", cell: (p) => (p.best_offer ? <CapValue cap={p.best_offer.reward_cap_coins} /> : <NA />) },
      { id: "seller", header: "Seller", sortKey: "seller", cell: (p) => <span className="block max-w-[140px] truncate">{p.seller ?? <NA />}</span> },
      { id: "status", header: "Verification", sortKey: "status", cell: (p) => (p.best_offer ? <OfferStatusBadge status={p.best_offer.status} /> : <NA />) },
      { id: "source", header: "Source", sortKey: "source", cell: (p) => (p.best_offer ? <SourceLabel type={p.best_offer.source_type} /> : <span className="text-xs text-muted">{p.source_name ?? "Not available"}</span>) },
      {
        id: "checked",
        header: "Last checked",
        sortKey: "last_checked",
        cell: (p) => (
          <span className="text-xs text-muted" title={formatDateTimeShort(p.last_checked_at) ?? undefined}>
            {formatRelative(p.last_checked_at) ?? "Never"}
          </span>
        ),
      },
      { id: "first_seen", header: "First seen", sortKey: "first_seen", defaultHidden: true, cell: (p) => <span className="text-xs text-muted">{formatDateTimeShort(p.first_seen_at)}</span> },
      {
        id: "actions",
        header: "",
        hideable: false,
        align: "right",
        cell: (p) => (
          <StopRowClick className="flex items-center justify-end gap-0.5">
            <Button
              size="icon-sm"
              variant="ghost"
              title={p.is_monitored ? "Stop monitoring" : "Monitor"}
              aria-label={p.is_monitored ? "Stop monitoring" : "Monitor"}
              onClick={() => monitor.mutate({ ids: [p.id], on: !p.is_monitored })}
            >
              {p.is_monitored ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </Button>
            <Button size="icon-sm" variant="ghost" title="Save to watchlist" aria-label="Save to watchlist" onClick={() => watch.mutate([p.id])}>
              <Star className="h-3.5 w-3.5" />
            </Button>
            <a href={p.product_url} target="_blank" rel="noopener noreferrer" title="Open on Flipkart" aria-label="Open on Flipkart" className="inline-flex h-7 w-7 items-center justify-center rounded text-muted hover:bg-subtle hover:text-fg">
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </StopRowClick>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const ids = [...selected];
  return (
    <>
      <PageHeader
        title="Deal Explorer"
        description="Product-level view of discovered and submitted Flipkart products with their strongest active CoinBack offer."
        actions={
          <Button size="sm" variant="primary" onClick={() => setAdding(true)}>
            <Plus className="h-3.5 w-3.5" />
            Add product URL
          </Button>
        }
      />
      <Panel>
        <div className="space-y-2 border-b border-line px-3 py-2.5">
          <FilterGroup>
            <SearchInput value={state.q} onChange={(q) => update({ q })} placeholder="Search title, brand or PID" />
            <FilterSelect label="Category" value={state.category} onChange={(category) => update({ category })} options={(facets.data?.data.categories ?? []).map((c) => ({ value: c.value, label: `${c.value} (${c.count})` }))} />
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
            <NumberFilter label="Min %" value={state.min_pct} onChange={(min_pct) => update({ min_pct })} width={64} />
            <Button size="sm" variant={advanced ? "secondary" : "ghost"} onClick={() => setAdvanced((v) => !v)} aria-expanded={advanced}>
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Advanced filters
            </Button>
            {activeCount > 0 ? (
              <Button size="sm" variant="ghost" onClick={reset}>
                <RotateCcw className="h-3.5 w-3.5" />
                Reset ({activeCount})
              </Button>
            ) : null}
          </FilterGroup>
          {advanced ? (
            <FilterGroup className="rounded border border-line bg-subtle/50 px-2.5 py-2">
              <FilterSelect label="Brand" value={state.brand} onChange={(brand) => update({ brand })} options={(facets.data?.data.brands ?? []).map((c) => ({ value: c.value, label: `${c.value} (${c.count})` }))} />
              <FilterSelect label="Seller" value={state.seller} onChange={(seller) => update({ seller })} options={(facets.data?.data.sellers ?? []).map((c) => ({ value: c.value, label: `${c.value} (${c.count})` }))} />
              <NumberFilter label="Price ₹" value={state.min_price} onChange={(min_price) => update({ min_price })} placeholder="min" />
              <NumberFilter label="–" value={state.max_price} onChange={(max_price) => update({ max_price })} placeholder="max" />
              <NumberFilter label="Max %" value={state.max_pct} onChange={(max_pct) => update({ max_pct })} width={64} />
              <FilterSelect
                label="Verification"
                value={state.status}
                onChange={(status) => update({ status })}
                options={(["VERIFIED", "UNVERIFIED", "ACCOUNT_CHECK_REQUIRED", "DETECTED"] as OfferStatus[]).map((s) => ({ value: s, label: OFFER_STATUS_LABEL[s] }))}
              />
              <FilterSelect
                label="Source"
                value={state.source_type}
                onChange={(source_type) => update({ source_type })}
                options={(["PRODUCT_PAGE", "THIRD_PARTY", "PUBLIC_SEARCH", "MANUAL"] as SourceType[]).map((s) => ({ value: s, label: SOURCE_TYPE_LABEL[s] }))}
              />
              <FilterSelect
                label="Monitoring"
                value={state.monitored}
                onChange={(monitored) => update({ monitored })}
                allLabel="Any"
                options={[
                  { value: "true", label: "Monitored" },
                  { value: "false", label: "Not monitored" },
                ]}
              />
            </FilterGroup>
          ) : null}
        </div>
        <DataTable
          storageKey="explorer"
          columns={columns}
          rows={query.data?.data}
          rowKey={(p) => p.id}
          loading={query.isLoading || query.isFetching}
          error={query.error?.message}
          onRetry={() => query.refetch()}
          sort={state.sort || "last_seen"}
          order={state.order as "asc" | "desc"}
          onSort={(sort, order) => update({ sort, order })}
          onRowClick={(p) => router.push(`/products/${p.id}`)}
          selection={{ selected, onChange: setSelected }}
          toolbar={
            ids.length ? (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs font-medium">{ids.length} selected</span>
                <Button size="sm" disabled={ids.length > 4} title={ids.length > 4 ? "Compare up to four products" : undefined} onClick={() => router.push(`/compare?ids=${ids.join(",")}`)}>
                  <GitCompare className="h-3.5 w-3.5" />
                  Compare{ids.length > 4 ? " (max 4)" : ""}
                </Button>
                <Button size="sm" loading={monitor.isPending} onClick={() => monitor.mutate({ ids, on: true })}>
                  <Eye className="h-3.5 w-3.5" />
                  Monitor
                </Button>
                <Button size="sm" loading={watch.isPending} onClick={() => watch.mutate(ids)}>
                  <Star className="h-3.5 w-3.5" />
                  Watchlist
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
                  Clear
                </Button>
              </div>
            ) : (
              <span className="text-xs text-muted">{query.data ? `${query.data.meta.total.toLocaleString("en-IN")} products` : "Loading products…"}</span>
            )
          }
          toolbarRight={
            <>
              <SavedFilters page="explorer" current={state} onApply={(p) => replaceAll(p)} />
              <ExportMenu path="/products/export" params={params} />
            </>
          }
          empty={
            <EmptyState
              title="No products match"
              description="Add Flipkart product URLs or enable a permitted discovery source. If no automated source is available, submitted URLs and manual entries still work."
              action={
                <Button size="sm" variant="primary" onClick={() => setAdding(true)}>
                  Add product URL
                </Button>
              }
            />
          }
          footer={<Pagination meta={query.data?.meta} onPage={(p) => update({ page: String(p) })} onPageSize={(s) => update({ page_size: String(s) })} />}
        />
      </Panel>
      <AddProductDialog open={adding} onClose={() => setAdding(false)} />
    </>
  );
}
