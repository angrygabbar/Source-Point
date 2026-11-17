"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Pencil, Trash2 } from "lucide-react";

import { DataTable, StopRowClick, type Column } from "@/components/data-table/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { OfferStatusBadge } from "@/components/offers/status";
import { Money, PercentValue, Thumb } from "@/components/offers/values";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Textarea } from "@/components/ui/field";
import { Panel } from "@/components/ui/panel";
import { EmptyState, NA } from "@/components/ui/states";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { api } from "@/services/api";
import { formatINR, formatPct, formatRelative } from "@/services/format";
import type { Envelope, WatchlistItem } from "@/services/types";

function EditTargets({ item, onClose }: { item: WatchlistItem; onClose: () => void }) {
  const [note, setNote] = useState(item.note ?? "");
  const [price, setPrice] = useState(item.target_price?.toString() ?? "");
  const [pct, setPct] = useState(item.target_percentage?.toString() ?? "");
  const save = useApiMutation(
    () =>
      api.post("/watchlist", {
        product_id: item.product.id,
        note: note.trim() || null,
        target_price: price === "" ? null : Number(price),
        target_percentage: pct === "" ? null : Number(pct),
      }),
    { invalidate: ["/watchlist"], success: "Watchlist targets saved", onSuccess: onClose },
  );
  return (
    <Dialog
      open
      onClose={onClose}
      title="Watchlist targets"
      description={item.product.title ?? undefined}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" loading={save.isPending} onClick={() => save.mutate(undefined)}>
            Save
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        <Field label="Target price (₹)" htmlFor="w-price" hint="Flag when the listed price is at or below">
          <Input id="w-price" type="number" min={0} step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} />
        </Field>
        <Field label="Target CoinBack (%)" htmlFor="w-pct" hint="Flag when advertised % is at or above">
          <Input id="w-pct" type="number" min={0} max={1000} value={pct} onChange={(e) => setPct(e.target.value)} />
        </Field>
        <Field label="Note" htmlFor="w-note" className="col-span-2">
          <Textarea id="w-note" maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
      </div>
    </Dialog>
  );
}

export default function WatchlistPage() {
  const router = useRouter();
  const query = useApi<Envelope<WatchlistItem[]>>("/watchlist");
  const [editing, setEditing] = useState<WatchlistItem | null>(null);
  const remove = useApiMutation((productId: string) => api.del(`/watchlist/${productId}`), { invalidate: ["/watchlist", "/products"], success: "Removed from watchlist" });

  const columns: Column<WatchlistItem>[] = [
    {
      id: "product",
      header: "Product",
      cell: (w) => (
        <div className="flex max-w-[340px] items-center gap-2.5">
          <Thumb src={w.product.image_url} alt="" />
          <div className="min-w-0">
            <Link href={`/products/${w.product.id}`} onClick={(e) => e.stopPropagation()} className="block truncate font-medium hover:text-accent">
              {w.product.title ?? "Title not available"}
            </Link>
            <p className="truncate text-2xs text-faint">{w.note ?? "No note"}</p>
          </div>
        </div>
      ),
    },
    { id: "price", header: "Price", align: "right", cell: (w) => <Money value={w.product.current_price} /> },
    {
      id: "target_price",
      header: "Target price",
      align: "right",
      cell: (w) =>
        w.target_price === null ? (
          <NA label="Not set" />
        ) : (
          <span className="inline-flex items-center gap-1.5">
            {formatINR(w.target_price)}
            {w.target_price_met ? <Badge tone="positive">Met</Badge> : null}
          </span>
        ),
    },
    { id: "pct", header: "CoinBack", align: "right", cell: (w) => (w.best_offer ? <PercentValue offer={w.best_offer} /> : <NA label="No offer" />) },
    {
      id: "target_pct",
      header: "Target %",
      align: "right",
      cell: (w) =>
        w.target_percentage === null ? (
          <NA label="Not set" />
        ) : (
          <span className="inline-flex items-center gap-1.5">
            {formatPct(w.target_percentage, 0)}
            {w.target_percentage_met ? <Badge tone="positive">Met</Badge> : null}
          </span>
        ),
    },
    { id: "status", header: "Verification", cell: (w) => (w.best_offer ? <OfferStatusBadge status={w.best_offer.status} /> : <NA />) },
    { id: "checked", header: "Last checked", cell: (w) => <span className="text-xs text-muted">{formatRelative(w.product.last_checked_at) ?? "Never"}</span> },
    { id: "added", header: "Saved", cell: (w) => <span className="text-xs text-muted">{formatRelative(w.created_at)}</span> },
    {
      id: "actions",
      header: "",
      align: "right",
      cell: (w) => (
        <StopRowClick className="flex justify-end gap-0.5">
          <Button size="icon-sm" variant="ghost" aria-label="Edit targets" title="Edit targets" onClick={() => setEditing(w)}>
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button size="icon-sm" variant="ghost" aria-label="Remove" title="Remove" onClick={() => remove.mutate(w.product.id)}>
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </StopRowClick>
      ),
    },
  ];

  const met = (query.data?.data ?? []).filter((w) => w.target_price_met || w.target_percentage_met).length;
  return (
    <>
      <PageHeader title="Watchlist" description="Saved products with optional price and CoinBack targets." meta={query.data ? <span>{query.data.data.length} saved · {met} with a target met</span> : null} />
      <Panel>
        <DataTable
          columns={columns}
          rows={query.data?.data}
          rowKey={(w) => w.id}
          loading={query.isLoading}
          error={query.error?.message}
          onRetry={() => query.refetch()}
          onRowClick={(w) => router.push(`/products/${w.product.id}`)}
          empty={<EmptyState title="Watchlist is empty" description="Use the star action in Deal Explorer or on a product page to save it here." />}
        />
      </Panel>
      {editing ? <EditTargets item={editing} onClose={() => setEditing(null)} /> : null}
    </>
  );
}
