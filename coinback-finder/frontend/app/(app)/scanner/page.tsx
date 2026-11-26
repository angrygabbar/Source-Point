"use client";

import { useMemo } from "react";
import { Play } from "lucide-react";

import { DataTable, type Column } from "@/components/data-table/data-table";
import { PageHeader } from "@/components/layout/page-header";
import { FilterGroup, FilterSelect } from "@/components/offers/filters";
import { toParams } from "@/components/offers/offers-table";
import { ScanStatusBadge } from "@/components/offers/status";
import { Badge, StatusDot } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Pagination } from "@/components/ui/pagination";
import { EmptyState, Notice, Skeleton } from "@/components/ui/states";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { useUrlState } from "@/hooks/use-url-state";
import { api } from "@/services/api";
import { cn } from "@/services/cn";
import { formatDateTime, formatDateTimeShort, formatDuration, formatRelative, formatTime, SCAN_STATUS_LABEL } from "@/services/format";
import type { Envelope, Paged, ScannerStatus, ScanRun, ScanStatus } from "@/services/types";

function Stat({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="border-line px-3 py-2.5 [&:not(:last-child)]:border-r">
      <p className="eyebrow">{label}</p>
      <p className="num mt-0.5 text-base font-semibold">{value}</p>
      {sub ? <p className="text-2xs text-faint">{sub}</p> : null}
    </div>
  );
}

function RunDetails({ runId, onClose }: { runId: string; onClose: () => void }) {
  const q = useApi<Envelope<ScanRun>>(`/discovery/runs/${runId}`);
  const r = q.data?.data;
  const levelTone = { info: "text-muted", warning: "text-warning", error: "text-negative", debug: "text-faint" } as const;
  return (
    <Dialog open onClose={onClose} width="xl" title="Scan run details" description={r ? `${r.trigger === "MANUAL" ? "Manual" : "Scheduled"} · started ${formatDateTime(r.started_at) ?? "not started"}` : undefined}>
      {!r ? (
        <Skeleton className="h-60" />
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-2 overflow-hidden rounded border border-line sm:grid-cols-4">
            <Stat label="Status" value={<ScanStatusBadge status={r.status} />} />
            <Stat label="Duration" value={formatDuration(r.duration_ms) ?? "—"} />
            <Stat label="Products" value={r.products_processed} sub={`${r.products_discovered} new`} />
            <Stat label="Offers" value={r.offers_detected} sub={`${r.offers_new} new · ${r.offers_expired} expired`} />
          </div>
          {r.details?.recovery ? <Notice tone="warning">{r.details.recovery}</Notice> : null}
          {r.details?.sources?.length ? (
            <div>
              <p className="eyebrow mb-1">Sources</p>
              <table className="w-full text-xs">
                <tbody>
                  {r.details.sources.map((s, i) => (
                    <tr key={i} className="border-b border-line">
                      <td className="py-1.5 pr-3 font-medium">{String(s.source)}</td>
                      <td className="py-1.5 pr-3">{String(s.status)}</td>
                      <td className="py-1.5 text-muted">
                        {Object.entries(s)
                          .filter(([k]) => !["source", "status"].includes(k))
                          .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
                          .join(" · ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <div>
            <p className="eyebrow mb-1">Execution log</p>
            {r.details?.log?.length ? (
              <ol className="max-h-80 overflow-y-auto rounded border border-line bg-subtle/40 font-mono text-[11px] leading-5">
                {r.details.log.map((l, i) => (
                  <li key={i} className="grid grid-cols-[86px_60px_130px_1fr] gap-2 border-b border-line px-2 py-0.5 last:border-0">
                    <span className="text-faint">{formatTime(l.ts)}</span>
                    <span className={cn("uppercase", levelTone[l.level] ?? "text-muted")}>{l.level}</span>
                    <span className="truncate text-muted">{l.source ?? "scanner"}</span>
                    <span className="break-words">{l.message}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-xs text-faint">No log entries recorded.</p>
            )}
          </div>
        </div>
      )}
    </Dialog>
  );
}

export default function ScannerPage() {
  const { state, update } = useUrlState({ status: "", run: "", page: "1", page_size: "50" });
  const status = useApi<Envelope<ScannerStatus>>("/dashboard/scanner-status", undefined, { refetchInterval: 10_000 });
  const runsParams = useMemo(() => toParams({ status: state.status, page: state.page, page_size: state.page_size }), [state.status, state.page, state.page_size]);
  const runs = useApi<Paged<ScanRun>>("/discovery/runs", runsParams, { keepPrevious: true, refetchInterval: 15_000 });
  const run = useApiMutation(() => api.post("/discovery/run", {}), { invalidate: ["/discovery", "/dashboard"], success: "Scan queued; the scanner picks it up within 15 seconds" });
  const s = status.data?.data;

  const columns: Column<ScanRun>[] = [
    { id: "queued", header: "Queued", cell: (r) => <span className="num text-xs">{formatDateTimeShort(r.queued_at)}</span> },
    { id: "trigger", header: "Trigger", cell: (r) => <span className="text-xs text-muted">{r.trigger === "MANUAL" ? (r.source_id ? "Manual (single source)" : "Manual") : "Scheduled"}</span> },
    { id: "status", header: "Status", cell: (r) => <ScanStatusBadge status={r.status} /> },
    { id: "duration", header: "Duration", align: "right", cell: (r) => formatDuration(r.duration_ms) ?? "—" },
    { id: "products", header: "Products", align: "right", cell: (r) => r.products_processed },
    { id: "new_products", header: "New products", align: "right", cell: (r) => r.products_discovered },
    { id: "offers", header: "Offers", align: "right", cell: (r) => r.offers_detected },
    { id: "new_offers", header: "New offers", align: "right", cell: (r) => r.offers_new },
    { id: "expired", header: "Expired", align: "right", cell: (r) => r.offers_expired },
    { id: "notified", header: "Alerts", align: "right", cell: (r) => r.notifications_queued },
    { id: "errors", header: "Errors", align: "right", cell: (r) => (r.errors_count ? <span className="text-negative">{r.errors_count}</span> : 0) },
  ];

  const stateTone = !s ? "muted" : s.state === "running" ? "accent" : s.state === "idle" ? "positive" : "negative";
  const progress = s?.current_run?.progress;
  return (
    <>
      <PageHeader
        title="Scanner Logs"
        description="Scheduler status, execution history and per-run logs. Overlapping runs are prevented with a database lock."
        actions={
          <Button size="sm" variant="primary" loading={run.isPending} onClick={() => run.mutate(undefined)}>
            <Play className="h-3.5 w-3.5" />
            Run scan now
          </Button>
        }
      />
      {s && !s.alive ? (
        <Notice tone="negative" title="Scanner offline" className="mb-3">
          No heartbeat in the last two minutes{ s.alive_at ? ` (last ${formatRelative(s.alive_at)})` : ""}. Queued runs start when the scanner service is running.
        </Notice>
      ) : null}
      <Panel className="mb-3">
        {!s ? (
          <Skeleton className="m-3 h-14" />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-4">
            <Stat
              label="State"
              value={
                <span className="flex items-center gap-2">
                  <StatusDot tone={stateTone} pulse={s.state === "running"} />
                  {s.state === "running" ? "Running" : s.state === "idle" ? "Idle" : "Offline"}
                </span>
              }
              sub={progress?.total ? `${progress.phase} ${progress.done}/${progress.total}` : s.queued_runs ? `${s.queued_runs} queued` : `Every ${s.interval_minutes ?? "?"} min`}
            />
            <Stat label="Last success" value={formatRelative(s.last_success_at) ?? "Never"} sub={formatDateTimeShort(s.last_success_at) ?? undefined} />
            <Stat label="Next execution" value={s.next_scan_at && s.alive ? formatTime(s.next_scan_at) : "—"} sub={s.scanner_enabled === false ? "Scheduled scans disabled" : undefined} />
            <Stat label="Scans (30d)" value={s.runs_30d} />
            <Stat label="Failed (30d)" value={<span className={s.failed_30d ? "text-negative" : undefined}>{s.failed_30d}</span>} />
            <Stat label="Avg duration" value={formatDuration(s.avg_duration_ms_30d) ?? "—"} sub="30 days" />
            <Stat label="Products (24h)" value={s.products_processed_24h} sub="processed" />
            <Stat label="Offers (24h)" value={s.offers_detected_24h} sub="detected" />
          </div>
        )}
      </Panel>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Panel className="min-w-0">
          <div className="border-b border-line px-3 py-2.5">
            <FilterGroup>
              <FilterSelect
                label="Status"
                value={state.status}
                onChange={(v) => update({ status: v })}
                options={(["SUCCEEDED", "PARTIAL", "FAILED", "RUNNING", "QUEUED", "SKIPPED", "INTERRUPTED"] as ScanStatus[]).map((x) => ({ value: x, label: SCAN_STATUS_LABEL[x] }))}
              />
            </FilterGroup>
          </div>
          <DataTable
            columns={columns}
            rows={runs.data?.data}
            rowKey={(r) => r.id}
            loading={runs.isLoading}
            error={runs.error?.message}
            onRetry={() => runs.refetch()}
            onRowClick={(r) => update({ run: r.id }, { resetPage: false })}
            empty={<EmptyState title="No scan runs recorded" description="Runs appear once the scanner service has started." />}
            footer={<Pagination meta={runs.data?.meta} onPage={(p) => update({ page: String(p) }, { resetPage: false })} onPageSize={(v) => update({ page_size: String(v) })} />}
          />
        </Panel>
        <Panel>
          <PanelHeader title="Source health" />
          <ul className="divide-y divide-line">
            {(s?.sources ?? []).map((src) => {
              const backoff = src.backoff_until && new Date(src.backoff_until).getTime() > Date.now();
              return (
                <li key={src.id} className="px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm">{src.name}</span>
                    {!src.enabled ? <Badge tone="muted">Disabled</Badge> : backoff ? <Badge tone="warning">Backoff</Badge> : src.last_error ? <Badge tone="negative">Error</Badge> : <Badge tone="positive">OK</Badge>}
                  </div>
                  <p className="truncate text-2xs text-faint" title={src.last_error ?? undefined}>
                    {src.last_error ?? `Last success ${formatRelative(src.last_success_at) ?? "never"}`}
                  </p>
                </li>
              );
            })}
          </ul>
        </Panel>
      </div>
      {state.run ? <RunDetails runId={state.run} onClose={() => update({ run: "" }, { resetPage: false })} /> : null}
    </>
  );
}
