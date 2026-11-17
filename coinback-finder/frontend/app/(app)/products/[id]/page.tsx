"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Archive, ArrowLeft, CheckCircle2, ExternalLink, Eye, EyeOff, FilePlus2, Pencil, Star, XCircle } from "lucide-react";

import { CHART, ChartPanel, LineSeries } from "@/components/charts/charts";
import { DataTable, StopRowClick, type Column } from "@/components/data-table/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { ArchiveDialog, EditProductDialog, ManualOfferDialog } from "@/components/offers/product-dialogs";
import { AccessBadge, Confidence, OfferStatusBadge, SourceLabel } from "@/components/offers/status";
import { CapValue, CoinsValue, Money, PercentValue, Thumb } from "@/components/offers/values";
import { VerifyDialog } from "@/components/offers/verify-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/field";
import { KeyValue, Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Segmented } from "@/components/ui/segmented";
import { EmptyState, ErrorState, NA, Notice, Skeleton } from "@/components/ui/states";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { api } from "@/services/api";
import { cn } from "@/services/cn";
import {
  formatDate,
  formatDateTime,
  formatDateTimeShort,
  formatINR,
  formatNumber,
  formatPct,
  formatRelative,
  OFFER_STATUS_LABEL,
  REWARD_TYPE_LABEL,
  SOURCE_TYPE_LABEL,
} from "@/services/format";
import type { Envelope, Offer, OfferSnapshot, PricePoint, ProductDetail } from "@/services/types";

function Tag({ kind }: { kind: "advertised" | "estimate" | "verified" | "listed" }) {
  const styles = {
    advertised: "text-accent border-accent/30",
    estimate: "text-warning border-warning/30",
    verified: "text-positive border-positive/30",
    listed: "text-muted border-line-strong",
  };
  return <span className={cn("ml-1.5 rounded-sm border px-1 text-[10px] font-medium uppercase tracking-wide", styles[kind])}>{kind}</span>;
}

const CHANGE_LABEL: Record<string, string> = {
  DETECTED: "First detected",
  REWARD_CHANGED: "Reward changed",
  STATUS_CHANGED: "Status changed",
  REACTIVATED: "Re-appeared",
  NO_LONGER_DISPLAYED: "No longer displayed",
  VALIDITY_ENDED: "Validity ended",
  SOURCE_UNAVAILABLE: "Source unavailable",
  MANUAL_VERIFIED: "Manually verified",
  MANUAL_REJECTED: "Manually rejected",
  MANUAL_ACCOUNT_CHECK_REQUIRED: "Account check recorded",
};

function CalculationPanel({ offer, detail }: { offer: Offer | null; detail: ProductDetail }) {
  const p = detail.product;
  if (!offer) {
    return (
      <Panel>
        <PanelHeader title="Reward calculation" />
        <EmptyState title="No offer selected" description="Select an offer to see the calculation." />
      </Panel>
    );
  }
  const coinValue = detail.assumptions.supercoin_value_inr;
  const restrictions = Object.entries(offer.restrictions ?? {});
  const items: { label: ReactNode; value: ReactNode; hint?: ReactNode }[] = [
    { label: <>Purchase price<Tag kind="listed" /></>, value: <Money value={p.current_price} /> },
    { label: <>Advertised coins<Tag kind="advertised" /></>, value: offer.advertised_coins !== null ? formatNumber(offer.advertised_coins) : <NA label="Not stated" /> },
    {
      label: <>Advertised percentage<Tag kind="advertised" /></>,
      value: <PercentValue offer={offer} />,
      hint: offer.eligible_purchase_amount !== null && offer.reward_type === "FIXED_COINS" ? "Derived from confirmed eligible amount" : undefined,
    },
    { label: "Maximum reward cap", value: <CapValue cap={offer.reward_cap_coins} /> },
    {
      label: <>Eligible purchase amount{offer.eligible_purchase_amount !== null ? <Tag kind="verified" /> : null}</>,
      value: offer.eligible_purchase_amount !== null ? <Money value={offer.eligible_purchase_amount} /> : <NA label="Unknown" />,
    },
    { label: <>Estimated coins<Tag kind="estimate" /></>, value: offer.estimated_coins !== null ? formatNumber(offer.estimated_coins) : <NA />, hint: offer.is_up_to ? "Upper bound for an 'up to' offer" : undefined },
    {
      label: <>Est. redemption value<Tag kind="estimate" /></>,
      value: offer.estimated_redemption_value !== null ? <Money value={offer.estimated_redemption_value} precise /> : <NA label="Not estimated" />,
      hint: coinValue === null ? <Link href="/settings" className="text-accent hover:underline">Set a SuperCoin value assumption</Link> : `Assumes ₹${coinValue} per SuperCoin`,
    },
    {
      label: <>Actual redemption value<Tag kind="verified" /></>,
      value: offer.actual_redemption_value !== null ? <Money value={offer.actual_redemption_value} precise /> : <NA label="Not verified" />,
    },
    { label: <>Est. effective cost<Tag kind="estimate" /></>, value: offer.effective_cost_estimate !== null ? <Money value={offer.effective_cost_estimate} precise /> : <NA /> },
    { label: "Min / max eligible purchase", value: `${formatINR(offer.min_eligible_purchase) ?? "–"} / ${formatINR(offer.max_eligible_purchase) ?? "–"}` },
    { label: "Valid until", value: formatDateTime(offer.valid_until) ?? <NA label="Not stated" /> },
  ];
  return (
    <Panel>
      <PanelHeader title="Reward calculation" description="Advertised, estimated and verified values are kept separate" />
      <PanelBody className="pt-1">
        <KeyValue items={items} />
        <div className="mt-2 border-t border-line pt-2">
          <p className="eyebrow mb-1">Restrictions</p>
          {restrictions.length ? (
            <ul className="space-y-1 text-xs">
              {restrictions.map(([group, values]) => (
                <li key={group}>
                  <span className="font-medium capitalize text-muted">{group}:</span> {values.join(", ")}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-faint">None detected in the source text. Account-specific conditions may still apply.</p>
          )}
        </div>
      </PanelBody>
    </Panel>
  );
}

function EvidencePanel({ offer }: { offer: Offer | null }) {
  if (!offer) return null;
  return (
    <Panel>
      <PanelHeader title="Source evidence" description={`${SOURCE_TYPE_LABEL[offer.source_type]}${offer.source_name ? ` · ${offer.source_name}` : ""}`} actions={<Confidence value={offer.confidence} />} />
      <PanelBody className="space-y-2.5">
        <p className="text-xs leading-5 text-fg">{offer.classification_reason ?? "No classification reason recorded."}</p>
        {offer.evidence_excerpt ? (
          <blockquote className="max-h-40 overflow-y-auto rounded border-l-2 border-line-strong bg-subtle/60 px-2.5 py-1.5 font-mono text-[11px] leading-5 text-muted">
            {offer.evidence_excerpt}
          </blockquote>
        ) : null}
        <KeyValue
          items={[
            { label: "Status", value: <OfferStatusBadge status={offer.status} /> },
            { label: "Reward type", value: REWARD_TYPE_LABEL[offer.reward_type] },
            { label: "First detected", value: formatDateTimeShort(offer.first_detected_at) },
            { label: "Last seen", value: formatDateTimeShort(offer.last_seen_at) },
            { label: "Verified", value: formatDateTimeShort(offer.verified_at) ?? <NA label="No" /> },
          ]}
        />
        <p className="text-2xs text-faint">Confidence reflects how clearly the wording matched. It is not proof of eligibility.</p>
      </PanelBody>
    </Panel>
  );
}

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [range, setRange] = useState<"30d" | "90d" | "365d" | "all">("90d");
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);
  const [dialog, setDialog] = useState<{ offer: Offer; mode: "verify" | "reject" } | null>(null);
  const [editing, setEditing] = useState(false);
  const [addingOffer, setAddingOffer] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const detail = useApi<Envelope<ProductDetail>>(`/products/${id}`);
  const prices = useApi<Envelope<PricePoint[]>>(`/products/${id}/price-history`, { range }, { keepPrevious: true });
  const history = useApi<Envelope<OfferSnapshot[]>>(`/products/${id}/offer-history`);

  const d = detail.data?.data;
  const offers = d?.offers ?? [];
  const best = d?.product.best_offer;
  const selected = offers.find((o) => o.id === (selectedOfferId ?? best?.id)) ?? offers[0] ?? null;

  const monitor = useApiMutation((on: boolean) => (on ? api.post(`/monitoring/${id}`, {}) : api.del(`/monitoring/${id}`)), {
    invalidate: ["/products", "/monitoring", "/dashboard"],
    success: "Monitoring updated",
  });
  const watch = useApiMutation((on: boolean) => (on ? api.post("/watchlist", { product_id: id }) : api.del(`/watchlist/${id}`)), {
    invalidate: ["/products", "/watchlist"],
    success: "Watchlist updated",
  });

  const rewardSeries = useMemo(() => {
    const snaps = (history.data?.data ?? []).filter((s) => s.offer_id === selected?.id).slice().reverse();
    return snaps.map((s) => ({ captured_at: s.captured_at, percentage: s.percentage, coins: s.reward_coins ?? s.estimated_coins }));
  }, [history.data, selected]);

  const offerColumns: Column<Offer>[] = [
    { id: "title", header: "Offer", cell: (o) => <span className="block max-w-[260px] truncate text-xs" title={o.title}>{o.title}</span> },
    { id: "pct", header: "CoinBack", align: "right", cell: (o) => <PercentValue offer={o} /> },
    { id: "coins", header: "Coins", align: "right", cell: (o) => <CoinsValue offer={o} /> },
    { id: "cap", header: "Cap", align: "right", cell: (o) => <CapValue cap={o.reward_cap_coins} /> },
    { id: "status", header: "Status", cell: (o) => <OfferStatusBadge status={o.status} /> },
    { id: "source", header: "Source", cell: (o) => <SourceLabel type={o.source_type} /> },
    { id: "valid", header: "Valid until", cell: (o) => <span className="text-xs text-muted">{formatDate(o.valid_until) ?? "Not stated"}</span> },
    {
      id: "actions",
      header: "",
      align: "right",
      cell: (o) => (
        <StopRowClick className="flex justify-end gap-0.5">
          <Button size="icon-sm" variant="ghost" title="Record verification" aria-label="Record verification" onClick={() => setDialog({ offer: o, mode: "verify" })}>
            <CheckCircle2 className="h-3.5 w-3.5" />
          </Button>
          <Button size="icon-sm" variant="ghost" title="Reject" aria-label="Reject" disabled={o.status === "REJECTED"} onClick={() => setDialog({ offer: o, mode: "reject" })}>
            <XCircle className="h-3.5 w-3.5" />
          </Button>
        </StopRowClick>
      ),
    },
  ];

  if (detail.isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-14 w-full" />
        <div className="grid gap-3 lg:grid-cols-3">
          <Skeleton className="h-72 lg:col-span-2" />
          <Skeleton className="h-72" />
        </div>
      </div>
    );
  }
  if (detail.error || !d) return <ErrorState message={detail.error?.message ?? "Product not found."} onRetry={() => detail.refetch()} />;
  const p = d.product;

  return (
    <>
      <Link href="/explorer" className="mb-2 inline-flex items-center gap-1 text-xs text-muted hover:text-fg">
        <ArrowLeft className="h-3 w-3" /> Deal Explorer
      </Link>
      <div className="mb-4 flex flex-wrap items-start gap-3">
        <Thumb src={p.image_url} alt={p.title ?? ""} size={64} />
        <div className="min-w-0 flex-1">
          <PageHeader
            title={p.title ?? "Title not available"}
            meta={
              <>
                <span>{p.brand ?? "Brand not available"}</span>
                <span className="text-faint">·</span>
                <span>{p.category ?? "Category not available"}</span>
                {p.flipkart_pid ? (
                  <>
                    <span className="text-faint">·</span>
                    <span className="font-mono">{p.flipkart_pid}</span>
                  </>
                ) : null}
                {p.is_monitored ? <Badge tone="accent">Monitored</Badge> : null}
                {d.watchlist.saved ? <Badge tone="warning">Watchlist</Badge> : null}
                <AccessBadge status={p.access_status} title={p.last_access_error} />
              </>
            }
            actions={
              <>
                <a href={p.product_url} target="_blank" rel="noopener noreferrer" className="inline-flex h-7 items-center gap-1.5 rounded border border-line-strong/70 bg-surface px-2.5 text-xs font-medium hover:bg-subtle">
                  <ExternalLink className="h-3.5 w-3.5" /> Open on Flipkart
                </a>
                <Button size="sm" loading={monitor.isPending} onClick={() => monitor.mutate(!p.is_monitored)}>
                  {p.is_monitored ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  {p.is_monitored ? "Stop monitoring" : "Monitor"}
                </Button>
                <Button size="sm" loading={watch.isPending} onClick={() => watch.mutate(!d.watchlist.saved)}>
                  <Star className={cn("h-3.5 w-3.5", d.watchlist.saved && "fill-current text-warning")} />
                  {d.watchlist.saved ? "Saved" : "Watchlist"}
                </Button>
                <Button size="sm" onClick={() => setAddingOffer(true)}>
                  <FilePlus2 className="h-3.5 w-3.5" /> Record offer
                </Button>
                <Button size="sm" onClick={() => setEditing(true)}>
                  <Pencil className="h-3.5 w-3.5" /> Edit
                </Button>
                <Button size="icon-sm" variant="ghost" onClick={() => setArchiving(true)} title="Archive product" aria-label="Archive product">
                  <Archive className="h-3.5 w-3.5" />
                </Button>
              </>
            }
          />
        </div>
      </div>

      {p.access_status === "NOT_PERMITTED" || p.access_status === "BLOCKED" || p.access_status === "UNAVAILABLE" ? (
        <Notice tone={p.access_status === "BLOCKED" ? "negative" : "warning"} title="Automatic refresh unavailable" className="mb-3">
          {p.last_access_error ?? "The product page could not be accessed."} Use “Edit” to record the current price and “Record offer” to add offer wording, then verify it.
        </Notice>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-3">
        <div className="min-w-0 space-y-3 lg:col-span-2">
          <ChartPanel
            title="Price history"
            description={`${d.price_stats.observations} observations · first ${formatDate(d.price_stats.first_recorded) ?? "n/a"}`}
            loading={prices.isLoading}
            error={prices.error?.message}
            empty={!prices.data?.data.some((x) => x.selling_price !== null)}
            actions={
              <Segmented
                size="xs"
                value={range}
                onChange={setRange}
                options={[
                  { value: "30d", label: "30D" },
                  { value: "90d", label: "90D" },
                  { value: "365d", label: "1Y" },
                  { value: "all", label: "All" },
                ]}
              />
            }
          >
            <LineSeries
              data={(prices.data?.data ?? []) as unknown as Record<string, unknown>[]}
              xKey="captured_at"
              xFormatter={(v) => formatDate(String(v)) ?? ""}
              valueFormatter={(v) => formatINR(Number(v)) ?? ""}
              yWidth={64}
              series={[
                { key: "selling_price", label: "Selling price", color: CHART.c1 },
                { key: "mrp", label: "MRP", color: CHART.c5 },
              ]}
            />
          </ChartPanel>

          <ChartPanel
            title="Reward history"
            description="Advertised percentage for the selected offer across snapshots"
            loading={history.isLoading}
            error={history.error?.message}
            empty={!rewardSeries.some((r) => r.percentage !== null)}
            height={180}
            actions={
              offers.length > 1 ? (
                <Select compact value={selected?.id ?? ""} onChange={(e) => setSelectedOfferId(e.target.value)} className="w-56" aria-label="Offer">
                  {offers.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.title.slice(0, 60)}
                    </option>
                  ))}
                </Select>
              ) : null
            }
          >
            <LineSeries
              data={rewardSeries as unknown as Record<string, unknown>[]}
              xKey="captured_at"
              xFormatter={(v) => formatDateTimeShort(String(v)) ?? ""}
              valueFormatter={(v) => formatPct(Number(v), 0) ?? ""}
              series={[{ key: "percentage", label: "Advertised %", color: CHART.c2 }]}
            />
          </ChartPanel>

          <Panel>
            <PanelHeader title="Offers" description="Click a row to inspect its calculation and evidence" />
            <DataTable
              columns={offerColumns}
              rows={offers}
              rowKey={(o) => o.id}
              onRowClick={(o) => setSelectedOfferId(o.id)}
              rowClassName={(o) => (o.id === selected?.id ? "bg-accent-soft/50" : undefined)}
              empty={<EmptyState title="No offers recorded" description="Offers appear when a permitted source detects them, or record the wording manually." action={<Button size="sm" onClick={() => setAddingOffer(true)}>Record offer</Button>} />}
            />
          </Panel>

          <Panel>
            <PanelHeader title="Offer timeline" description="Immutable snapshots; never overwritten" />
            {history.isLoading ? (
              <div className="p-3">
                <Skeleton className="h-24" />
              </div>
            ) : !history.data?.data.length ? (
              <EmptyState title="No snapshots yet" />
            ) : (
              <ol className="max-h-[360px] divide-y divide-line overflow-y-auto">
                {history.data.data.map((s) => (
                  <li key={s.id} className="grid grid-cols-[150px_1fr_auto] items-center gap-3 px-3 py-2 text-xs">
                    <span className="num text-muted">{formatDateTimeShort(s.captured_at)}</span>
                    <span className="min-w-0">
                      <span className="font-medium">{CHANGE_LABEL[s.change_type] ?? s.change_type}</span>
                      <span className="ml-2 text-muted">
                        {formatPct(s.percentage) ?? "% n/a"} · {formatNumber(s.reward_coins ?? s.estimated_coins) ?? "coins n/a"} coins · cap {formatNumber(s.cap) ?? "n/a"} · {formatINR(s.selling_price) ?? "price n/a"}
                      </span>
                    </span>
                    <span className="text-faint">{OFFER_STATUS_LABEL[s.status]}</span>
                  </li>
                ))}
              </ol>
            )}
          </Panel>
        </div>

        <div className="min-w-0 space-y-3">
          <Panel>
            <PanelHeader title="Price summary" description={`Last checked ${formatRelative(p.last_checked_at) ?? "never"}`} />
            <PanelBody className="pt-1">
              <KeyValue
                items={[
                  { label: "Selling price", value: <Money value={p.current_price} /> },
                  { label: "MRP", value: <Money value={p.mrp} /> },
                  { label: "Discount", value: formatPct(p.discount_percent, 0) ?? <NA /> },
                  { label: "Shipping", value: <Money value={p.shipping_charge} /> },
                  { label: "Stock", value: p.in_stock === null ? <NA /> : p.in_stock ? "In stock" : "Out of stock" },
                  { label: "Lowest recorded", value: <Money value={d.price_stats.lowest} /> },
                  { label: "Highest recorded", value: <Money value={d.price_stats.highest} /> },
                  { label: "Average recorded", value: <Money value={d.price_stats.average} precise /> },
                  { label: "Seller", value: p.seller ?? <NA /> },
                  { label: "First discovered", value: formatDateTimeShort(p.first_seen_at) },
                  { label: "Source", value: p.source_name ?? <NA /> },
                ]}
              />
            </PanelBody>
          </Panel>

          <CalculationPanel offer={selected} detail={d} />
          <EvidencePanel offer={selected} />

          <Panel>
            <PanelHeader title="Manual verification history" />
            {d.verifications.length === 0 ? (
              <EmptyState title="Not verified" description="Use the check icon on an offer to record what your account shows." />
            ) : (
              <ul className="divide-y divide-line">
                {d.verifications.map((v) => (
                  <li key={v.id} className="space-y-0.5 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{OFFER_STATUS_LABEL[v.status]}</span>
                      <span className="num text-faint">{formatDateTimeShort(v.verified_at)}</span>
                    </div>
                    <p className="text-muted">
                      Account showed {formatNumber(v.actual_reward_coins) ?? "n/a"} coins
                      {v.eligible_purchase_amount !== null ? ` on ${formatINR(v.eligible_purchase_amount)}` : ""}
                      {v.actual_percentage !== null ? ` (${formatPct(v.actual_percentage)})` : ""} · advertised {formatPct(v.advertised_percentage) ?? "n/a"}
                    </p>
                    {v.notes || v.eligibility_notes ? <p className="text-faint">{[v.eligibility_notes, v.notes].filter(Boolean).join(" — ")}</p> : null}
                    <p className="text-2xs text-faint">by {v.verified_by ?? "unknown"}</p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel>
            <PanelHeader title="Seller changes" />
            {d.sellers.length === 0 ? (
              <EmptyState title="No seller recorded" />
            ) : (
              <ul className="divide-y divide-line text-xs">
                {d.sellers.map((s) => (
                  <li key={s.seller} className="flex items-center justify-between px-3 py-1.5">
                    <span className="truncate">{s.seller}</span>
                    <span className="num text-faint">
                      {formatDate(s.first_seen)} – {formatDate(s.last_seen)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel>
            <PanelHeader title="Monitoring" />
            <PanelBody className="pt-1">
              <KeyValue
                items={[
                  { label: "State", value: d.monitoring.enabled ? "Enabled" : "Not monitored" },
                  { label: "Frequency", value: d.monitoring.frequency_minutes ? `Every ${d.monitoring.frequency_minutes} min` : <NA /> },
                  { label: "Last processed", value: formatDateTimeShort(d.monitoring.last_processed_at) ?? <NA label="Never" /> },
                  { label: "Next due", value: formatDateTimeShort(d.monitoring.next_due_at) ?? <NA /> },
                ]}
              />
            </PanelBody>
          </Panel>
        </div>
      </div>

      <VerifyDialog offer={dialog?.offer ?? null} product={p} mode={dialog?.mode ?? "verify"} onClose={() => setDialog(null)} />
      {editing ? <EditProductDialog product={p} open={editing} onClose={() => setEditing(false)} /> : null}
      <ManualOfferDialog productId={p.id} open={addingOffer} onClose={() => setAddingOffer(false)} />
      <ArchiveDialog productId={p.id} open={archiving} onClose={() => setArchiving(false)} />
    </>
  );
}
