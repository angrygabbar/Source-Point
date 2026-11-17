"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowDownRight, ArrowUpRight, Search } from "lucide-react";

import { CHART, ChartPanel, LineSeries } from "@/components/charts/charts";
import { DataTable, type Column } from "@/components/data-table/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { Money, Thumb } from "@/components/offers/values";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/field";
import { KeyValue, Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Segmented } from "@/components/ui/segmented";
import { EmptyState } from "@/components/ui/states";
import { useApi } from "@/hooks/use-api";
import { useUrlState } from "@/hooks/use-url-state";
import { cn } from "@/services/cn";
import { formatDate, formatDateTimeShort, formatINR, formatPct } from "@/services/format";
import type { Envelope, PriceMovement, PricePoint, ProductDetail, SearchResult } from "@/services/types";

function ProductPicker({ onPick }: { onPick: (id: string) => void }) {
  const [q, setQ] = useState("");
  const search = useApi<Envelope<SearchResult>>(q.trim().length >= 2 ? "/search" : null, { q: q.trim() });
  const results = search.data?.data.products ?? [];
  return (
    <div className="relative w-full max-w-sm">
      <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
      <Input compact className="pl-7" placeholder="Find a product to chart…" value={q} maxLength={200} onChange={(e) => setQ(e.target.value)} aria-label="Find product" />
      {q.trim().length >= 2 ? (
        <ul className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-line bg-surface p-1 shadow-pop">
          {results.length === 0 ? (
            <li className="px-2 py-2 text-xs text-faint">{search.isFetching ? "Searching…" : "No products found"}</li>
          ) : (
            results.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left hover:bg-subtle"
                  onClick={() => {
                    onPick(p.id);
                    setQ("");
                  }}
                >
                  <Thumb src={p.image_url} alt="" size={24} />
                  <span className="min-w-0 flex-1 truncate text-sm">{p.title ?? "Title not available"}</span>
                  <span className="num text-xs text-muted">{formatINR(p.current_price) ?? ""}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}

export default function PriceHistoryPage() {
  const { state, update } = useUrlState({ product: "", range: "90d", movement_range: "7d", direction: "all" });
  const detail = useApi<Envelope<ProductDetail>>(state.product ? `/products/${state.product}` : null);
  const points = useApi<Envelope<PricePoint[]>>(state.product ? `/products/${state.product}/price-history` : null, { range: state.range }, { keepPrevious: true });
  const movements = useApi<Envelope<PriceMovement[]>>("/price-history/movements", { range: state.movement_range, direction: state.direction, limit: 200 }, { keepPrevious: true });

  const columns: Column<PriceMovement>[] = useMemo(
    () => [
      {
        id: "product",
        header: "Product",
        cell: (m) => (
          <div className="flex max-w-[320px] items-center gap-2">
            <Thumb src={m.image_url} alt="" size={28} />
            <span className="truncate">{m.title ?? "Title not available"}</span>
          </div>
        ),
      },
      { id: "when", header: "Recorded", cell: (m) => <span className="num text-xs text-muted">{formatDateTimeShort(m.captured_at)}</span> },
      { id: "prev", header: "Previous", align: "right", cell: (m) => <Money value={m.previous_price} /> },
      { id: "new", header: "New", align: "right", cell: (m) => <Money value={m.new_price} /> },
      {
        id: "change",
        header: "Change",
        align: "right",
        cell: (m) => (
          <span className={cn("num inline-flex items-center gap-0.5", m.change < 0 ? "text-positive" : "text-negative")}>
            {m.change < 0 ? <ArrowDownRight className="h-3 w-3" /> : <ArrowUpRight className="h-3 w-3" />}
            {formatINR(Math.abs(m.change))} ({formatPct(m.change_pct, 1)})
          </span>
        ),
      },
      { id: "seller", header: "Seller", cell: (m) => <span className="flex items-center gap-1.5 text-xs">{m.seller ?? "Not available"}{m.seller_changed ? <Badge tone="warning">changed</Badge> : null}</span> },
    ],
    [],
  );

  const d = detail.data?.data;
  return (
    <>
      <PageHeader title="Price History" description="Immutable price observations per product, and recent recorded price changes across all tracked products." />
      <div className="grid gap-3 xl:grid-cols-3">
        <div className="space-y-3 xl:col-span-2">
          <ChartPanel
            title={d ? d.product.title ?? "Selected product" : "Product price chart"}
            description={d ? `${d.price_stats.observations} observations` : "Search for a product or pick one from the changes table"}
            loading={Boolean(state.product) && points.isLoading}
            error={points.error?.message}
            empty={!state.product || !points.data?.data.some((p) => p.selling_price !== null)}
            height={260}
            actions={
              <div className="flex items-center gap-2">
                <ProductPicker onPick={(product) => update({ product }, { resetPage: false })} />
                <Segmented
                  size="xs"
                  value={state.range as "30d" | "90d" | "365d" | "all"}
                  onChange={(range) => update({ range }, { resetPage: false })}
                  options={[
                    { value: "30d", label: "30D" },
                    { value: "90d", label: "90D" },
                    { value: "365d", label: "1Y" },
                    { value: "all", label: "All" },
                  ]}
                />
              </div>
            }
          >
            <LineSeries
              data={(points.data?.data ?? []) as unknown as Record<string, unknown>[]}
              xKey="captured_at"
              xFormatter={(v) => formatDate(String(v)) ?? ""}
              valueFormatter={(v) => formatINR(Number(v)) ?? ""}
              yWidth={64}
              series={[
                { key: "selling_price", label: "Selling price", color: CHART.c1 },
                { key: "mrp", label: "MRP", color: CHART.c5 },
                { key: "shipping_charge", label: "Shipping", color: CHART.c3 },
              ]}
            />
          </ChartPanel>
        </div>
        <Panel>
          <PanelHeader title="Statistics" actions={d ? <Link href={`/products/${d.product.id}`} className="text-xs text-accent hover:underline">Product detail</Link> : null} />
          {d ? (
            <PanelBody className="pt-1">
              <KeyValue
                items={[
                  { label: "Current", value: <Money value={d.product.current_price} /> },
                  { label: "Lowest recorded", value: <Money value={d.price_stats.lowest} /> },
                  { label: "Highest recorded", value: <Money value={d.price_stats.highest} /> },
                  { label: "Average recorded", value: <Money value={d.price_stats.average} precise /> },
                  { label: "First recorded", value: formatDateTimeShort(d.price_stats.first_recorded) ?? "Not available" },
                  { label: "Last recorded", value: formatDateTimeShort(d.price_stats.last_recorded) ?? "Not available" },
                  { label: "Sellers seen", value: d.sellers.length },
                ]}
              />
            </PanelBody>
          ) : (
            <EmptyState title="No product selected" />
          )}
        </Panel>
      </div>

      <Panel className="mt-3">
        <PanelHeader
          title="Recorded price changes"
          description="Differences between consecutive observations of the same product"
          actions={
            <>
              <Segmented
                size="xs"
                value={state.direction as "all" | "drop" | "rise"}
                onChange={(direction) => update({ direction }, { resetPage: false })}
                options={[
                  { value: "all", label: "All" },
                  { value: "drop", label: "Drops" },
                  { value: "rise", label: "Rises" },
                ]}
              />
              <Segmented
                size="xs"
                value={state.movement_range as "today" | "7d" | "30d" | "90d"}
                onChange={(movement_range) => update({ movement_range }, { resetPage: false })}
                options={[
                  { value: "today", label: "Today" },
                  { value: "7d", label: "7D" },
                  { value: "30d", label: "30D" },
                  { value: "90d", label: "90D" },
                ]}
              />
            </>
          }
        />
        <DataTable
          columns={columns}
          rows={movements.data?.data}
          rowKey={(m) => `${m.product_id}-${m.captured_at}`}
          loading={movements.isLoading}
          error={movements.error?.message}
          onRetry={() => movements.refetch()}
          onRowClick={(m) => update({ product: m.product_id }, { resetPage: false })}
          rowClassName={(m) => (m.product_id === state.product ? "bg-accent-soft/50" : undefined)}
          empty={<EmptyState title="No price changes recorded in this range" />}
        />
      </Panel>
    </>
  );
}
