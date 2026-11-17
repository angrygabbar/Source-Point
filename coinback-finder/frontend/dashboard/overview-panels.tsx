"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { NotificationStatusBadge, OfferStatusBadge, ScanStatusBadge } from "@/components/offers/status";
import { CoinsValue, Money, PercentValue, Thumb } from "@/components/offers/values";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { formatDate, formatDuration, formatRelative } from "@/services/format";
import type { DashboardPanels, Offer } from "@/services/types";

function ListPanel({ title, href, loading, error, empty, children }: { title: string; href: string; loading?: boolean; error?: string | null; empty: boolean; children: ReactNode }) {
  return (
    <Panel className="flex flex-col">
      <PanelHeader
        title={title}
        actions={
          <Link href={href} className="text-xs text-accent hover:underline">
            View all
          </Link>
        }
      />
      {loading ? (
        <div className="space-y-2 p-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-7" />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={error} className="py-6" />
      ) : empty ? (
        <EmptyState title="Nothing recorded yet" className="py-6" />
      ) : (
        <ul className="divide-y divide-line">{children}</ul>
      )}
    </Panel>
  );
}

function OfferLine({ offer, right }: { offer: Offer; right?: ReactNode }) {
  return (
    <li>
      <Link href={`/products/${offer.product_id}`} className="flex items-center gap-2.5 px-3 py-2 hover:bg-subtle/70">
        <Thumb src={offer.product?.image_url ?? null} alt="" size={28} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm">{offer.product?.title ?? "Title not available"}</p>
          <p className="flex items-center gap-2 text-2xs text-faint">
            <Money value={offer.product?.current_price} />
            <span>·</span>
            <OfferStatusBadge status={offer.status} />
          </p>
        </div>
        <div className="shrink-0 text-right">{right ?? <PercentValue offer={offer} />}</div>
      </Link>
    </li>
  );
}

export function OverviewPanels({ data, loading, error }: { data?: DashboardPanels; loading?: boolean; error?: string | null }) {
  const p = data;
  const common = { loading, error };
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <ListPanel title="Latest deals" href="/deals?sort=detected" {...common} empty={!p?.latest_deals.length}>
        {p?.latest_deals.map((o) => (
          <OfferLine
            key={o.id}
            offer={o}
            right={
              <div>
                <PercentValue offer={o} />
                <p className="text-2xs text-faint">{formatRelative(o.first_detected_at)}</p>
              </div>
            }
          />
        ))}
      </ListPanel>
      <ListPanel title="Highest advertised rewards" href="/deals?sort=pct" {...common} empty={!p?.highest_rewards.length}>
        {p?.highest_rewards.map((o) => (
          <OfferLine
            key={o.id}
            offer={o}
            right={
              <div>
                <PercentValue offer={o} />
                <p className="text-2xs text-faint">
                  <CoinsValue offer={o} /> coins
                </p>
              </div>
            }
          />
        ))}
      </ListPanel>
      <ListPanel title="Recently changed offers" href="/deals?sort=changed" {...common} empty={!p?.recently_changed.length}>
        {p?.recently_changed.map((o) => (
          <OfferLine
            key={o.id}
            offer={o}
            right={
              <div>
                <PercentValue offer={o} />
                <p className="text-2xs text-faint">changed {formatRelative(o.last_changed_at)}</p>
              </div>
            }
          />
        ))}
      </ListPanel>
      <ListPanel title="Expiring offers" href="/deals?sort=expiry&order=asc" {...common} empty={!p?.expiring.length}>
        {p?.expiring.map((o) => (
          <OfferLine
            key={o.id}
            offer={o}
            right={
              <div>
                <PercentValue offer={o} />
                <p className="text-2xs text-warning">ends {formatDate(o.valid_until)}</p>
              </div>
            }
          />
        ))}
      </ListPanel>
      <ListPanel title="Scanner activity" href="/scanner" {...common} empty={!p?.scanner_activity.length}>
        {p?.scanner_activity.map((r) => (
          <li key={r.id}>
            <Link href={`/scanner?run=${r.id}`} className="flex items-center gap-3 px-3 py-2 text-sm hover:bg-subtle/70">
              <ScanStatusBadge status={r.status} />
              <span className="min-w-0 flex-1 truncate text-xs text-muted">
                {r.trigger === "MANUAL" ? "Manual" : "Scheduled"} · {r.products_processed} products · {r.offers_detected} offers
                {r.errors_count ? ` · ${r.errors_count} errors` : ""}
              </span>
              <span className="num shrink-0 text-2xs text-faint">{formatDuration(r.duration_ms) ?? ""} {formatRelative(r.started_at ?? r.queued_at)}</span>
            </Link>
          </li>
        ))}
      </ListPanel>
      <ListPanel title="Recent Telegram notifications" href="/notifications" {...common} empty={!p?.recent_notifications.length}>
        {p?.recent_notifications.map((n) => (
          <li key={n.id} className="flex items-center gap-3 px-3 py-2">
            <NotificationStatusBadge status={n.status} />
            <span className="min-w-0 flex-1 truncate text-xs">
              <span className="text-muted">{n.event_type.replace("_", " ").toLowerCase()}</span> · {n.product_title ?? "Test message"}
            </span>
            <span className="shrink-0 text-2xs text-faint">{formatRelative(n.created_at)}</span>
          </li>
        ))}
      </ListPanel>
    </div>
  );
}
