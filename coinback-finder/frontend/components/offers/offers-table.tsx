"use client";

import { useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, ExternalLink, RotateCcw, XCircle } from "lucide-react";

import { DataTable, StopRowClick, type Column } from "@/components/data-table/data-table";
import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/states";
import { useApi } from "@/hooks/use-api";
import type { QueryParams } from "@/services/api";
import { formatDate, formatDateTimeShort, formatRelative, REWARD_TYPE_LABEL } from "@/services/format";
import type { Offer, Paged } from "@/services/types";
import { FilterGroup, SearchInput } from "./filters";
import { Confidence, OfferStatusBadge, SourceLabel } from "./status";
import { ExportMenu, SavedFilters } from "./table-tools";
import { CapValue, CoinsValue, Money, PercentValue, Thumb } from "./values";
import { VerifyDialog } from "./verify-dialog";

export const OFFER_FILTER_DEFAULTS = {
  q: "",
  status: "",
  reward_type: "",
  source_type: "",
  category: "",
  min_pct: "",
  min_price: "",
  max_price: "",
  min_coins: "",
  detected: "",
  include_inactive: "",
  pct_mode: "",
  capped: "",
  verified: "",
  up_to: "",
  sort: "",
  order: "desc",
  page: "1",
  page_size: "50",
};
export type OfferFilterState = typeof OFFER_FILTER_DEFAULTS;

export function toParams(state: Record<string, string>): QueryParams {
  return Object.fromEntries(Object.entries(state).filter(([, v]) => v !== ""));
}

export function offerColumns(onVerify: (o: Offer, mode: "verify" | "reject") => void): Column<Offer>[] {
  return [
    {
      id: "product",
      header: "Product",
      sortKey: "title",
      hideable: false,
      cell: (o) => (
        <div className="flex max-w-[360px] items-center gap-2.5">
          <Thumb src={o.product?.image_url ?? null} alt="" />
          <div className="min-w-0">
            <Link href={`/products/${o.product_id}`} onClick={(e) => e.stopPropagation()} className="block truncate font-medium text-fg hover:text-accent">
              {o.product?.title ?? "Title not available"}
            </Link>
            <p className="truncate text-2xs text-faint">{[o.product?.brand, o.product?.category].filter(Boolean).join(" · ") || "Brand and category not available"}</p>
          </div>
        </div>
      ),
    },
    { id: "price", header: "Price", sortKey: "price", align: "right", cell: (o) => <Money value={o.product?.current_price} /> },
    { id: "pct", header: "CoinBack", sortKey: "pct", align: "right", hideable: false, cell: (o) => <PercentValue offer={o} /> },
    { id: "coins", header: "Coins", sortKey: "coins", align: "right", cell: (o) => <CoinsValue offer={o} /> },
    { id: "cap", header: "Max reward", sortKey: "cap", align: "right", cell: (o) => <CapValue cap={o.reward_cap_coins} /> },
    {
      id: "offer",
      header: "Offer text",
      defaultHidden: true,
      cell: (o) => (
        <span className="block max-w-[280px] truncate text-xs text-muted" title={o.title}>
          {o.title}
        </span>
      ),
    },
    { id: "type", header: "Type", cell: (o) => <span className="text-xs text-muted">{REWARD_TYPE_LABEL[o.reward_type]}</span> },
    { id: "status", header: "Status", sortKey: "status", cell: (o) => <OfferStatusBadge status={o.status} /> },
    { id: "confidence", header: "Confidence", sortKey: "confidence", cell: (o) => <Confidence value={o.confidence} /> },
    { id: "source", header: "Source", cell: (o) => <SourceLabel type={o.source_type} /> },
    {
      id: "effective",
      header: "Est. effective cost",
      sortKey: "effective_cost",
      align: "right",
      defaultHidden: true,
      cell: (o) => <Money value={o.effective_cost_estimate} />,
    },
    {
      id: "detected",
      header: "Detected",
      sortKey: "detected",
      cell: (o) => (
        <span className="text-xs text-muted" title={formatDateTimeShort(o.first_detected_at) ?? undefined}>
          {formatRelative(o.first_detected_at)}
        </span>
      ),
    },
    {
      id: "last_seen",
      header: "Last seen",
      sortKey: "last_seen",
      defaultHidden: true,
      cell: (o) => <span className="text-xs text-muted">{formatRelative(o.last_seen_at)}</span>,
    },
    {
      id: "expiry",
      header: "Valid until",
      sortKey: "expiry",
      cell: (o) => <span className="text-xs text-muted">{formatDate(o.valid_until) ?? <span className="text-faint">Not stated</span>}</span>,
    },
    {
      id: "actions",
      header: "",
      hideable: false,
      align: "right",
      cell: (o) => (
        <StopRowClick className="flex items-center justify-end gap-0.5">
          <Button size="icon-sm" variant="ghost" title="Record verification" aria-label="Record verification" onClick={() => onVerify(o, "verify")}>
            <CheckCircle2 className="h-3.5 w-3.5" />
          </Button>
          <Button size="icon-sm" variant="ghost" title="Reject offer" aria-label="Reject offer" disabled={o.status === "REJECTED"} onClick={() => onVerify(o, "reject")}>
            <XCircle className="h-3.5 w-3.5" />
          </Button>
          {o.product?.product_url ? (
            <a
              href={o.product.product_url}
              target="_blank"
              rel="noopener noreferrer"
              title="Open on Flipkart"
              aria-label="Open on Flipkart"
              className="inline-flex h-7 w-7 items-center justify-center rounded text-muted hover:bg-subtle hover:text-fg"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          ) : null}
        </StopRowClick>
      ),
    },
  ];
}

export function OffersTable({
  endpoint,
  savedPage,
  storageKey,
  state,
  update,
  replaceAll,
  reset,
  activeCount,
  filters,
  defaultSort = "detected",
  emptyHint,
}: {
  endpoint: string;
  savedPage: string;
  storageKey: string;
  state: OfferFilterState;
  update: (patch: Partial<OfferFilterState>) => void;
  replaceAll: (v: Partial<OfferFilterState>) => void;
  reset: () => void;
  activeCount: number;
  filters: ReactNode;
  defaultSort?: string;
  emptyHint?: ReactNode;
}) {
  const router = useRouter();
  const params = useMemo(() => toParams(state), [state]);
  const query = useApi<Paged<Offer>>(endpoint, params, { keepPrevious: true, refetchInterval: 60_000 });
  const [dialog, setDialog] = useState<{ offer: Offer; mode: "verify" | "reject" } | null>(null);
  const columns = useMemo(() => offerColumns((offer, mode) => setDialog({ offer, mode })), []);

  return (
    <Panel>
      <div className="space-y-2 border-b border-line px-3 py-2.5">
        <FilterGroup>
          <SearchInput value={state.q} onChange={(q) => update({ q })} placeholder="Search product, brand or offer text" />
          {filters}
          {activeCount > 0 ? (
            <Button size="sm" variant="ghost" onClick={reset}>
              <RotateCcw className="h-3.5 w-3.5" />
              Reset ({activeCount})
            </Button>
          ) : null}
        </FilterGroup>
      </div>
      <DataTable
        storageKey={storageKey}
        columns={columns}
        rows={query.data?.data}
        rowKey={(o) => o.id}
        loading={query.isLoading || query.isFetching}
        error={query.error?.message}
        onRetry={() => query.refetch()}
        sort={state.sort || defaultSort}
        order={state.order as "asc" | "desc"}
        onSort={(sort, order) => update({ sort, order })}
        onRowClick={(o) => router.push(`/products/${o.product_id}`)}
        toolbar={
          <span className="text-xs text-muted">
            {query.data ? `${query.data.meta.total.toLocaleString("en-IN")} offers` : "Loading offers…"}
            <span className="ml-2 text-faint">Advertised values. Verify eligibility before purchase.</span>
          </span>
        }
        toolbarRight={
          <>
            <SavedFilters page={savedPage} current={state} onApply={(p) => replaceAll(p as Partial<OfferFilterState>)} />
            <ExportMenu path="/offers/export" params={{ ...params, ...(endpoint.endsWith("100-percent") && !state.pct_mode ? { pct_mode: "gte_100" } : {}) }} />
          </>
        }
        empty={<EmptyState title="No offers match these filters" description={emptyHint} />}
        footer={
          <Pagination
            meta={query.data?.meta}
            onPage={(p) => update({ page: String(p) } as Partial<OfferFilterState>)}
            onPageSize={(s) => update({ page_size: String(s) })}
          />
        }
      />
      <VerifyDialog offer={dialog?.offer ?? null} product={dialog?.offer.product} mode={dialog?.mode ?? "verify"} onClose={() => setDialog(null)} />
    </Panel>
  );
}
