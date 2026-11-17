"use client";

import Link from "next/link";

import { BarSeries, CHART, ChartPanel, LineSeries, isEmptySeries } from "@/components/charts/charts";
import { PageHeader } from "@/components/layout/page-header";
import { OfferStatusBadge, SourceLabel } from "@/components/offers/status";
import { CoinsValue, Money, PercentValue } from "@/components/offers/values";
import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { analyticsParams, RangePicker, type RangeKey } from "@/dashboard/range-picker";
import { useApi } from "@/hooks/use-api";
import { useUrlState } from "@/hooks/use-url-state";
import { formatAxisDate, formatDate, formatDateTimeShort, WEEKDAY_LABEL } from "@/services/format";
import type { Analytics, Envelope } from "@/services/types";

export default function AnalyticsPage() {
  const { state, update } = useUrlState({ range: "30d", from: "", to: "" });
  const params = analyticsParams(state.range as RangeKey, state.from, state.to);
  const q = useApi<Envelope<Analytics>>(params ? "/dashboard/analytics" : null, params ?? undefined, { keepPrevious: true });
  const a = q.data?.data;
  const common = { loading: q.isLoading, error: q.error?.message };

  const weekday = (a?.detection_by_weekday ?? []).map((w) => ({ ...w, label: WEEKDAY_LABEL[w.weekday - 1] }));
  const hours = (a?.detection_by_hour ?? []).map((h) => ({ ...h, label: `${String(h.hour).padStart(2, "0")}:00` }));

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Category coverage, reward patterns, price and reward trends, source and scanner performance. Times in IST."
        meta={a ? <span>{formatDate(a.range.start)} – {formatDate(a.range.end)}</span> : null}
        actions={<RangePicker range={state.range as RangeKey} from={state.from} to={state.to} onChange={(p) => update(p, { resetPage: false })} />}
      />
      <div className="space-y-3">
        <div className="grid gap-3 lg:grid-cols-2">
          <ChartPanel title="Offers by category" description="Active offers per category (top 12)" {...common} empty={!a?.category_distribution.length} height={280}>
            <BarSeries horizontal yWidth={130} data={a?.category_distribution ?? []} xKey="category" series={[{ key: "offers", label: "Offers", color: CHART.c1 }]} />
          </ChartPanel>
          <ChartPanel title="Average advertised % by category" description="Mean of offers with a calculated percentage" {...common} empty={!a?.category_distribution.some((c) => c.avg_pct !== null)} height={280}>
            <BarSeries
              horizontal
              yWidth={130}
              data={(a?.category_distribution ?? []).filter((c) => c.avg_pct !== null)}
              xKey="category"
              valueFormatter={(v) => `${Math.round(Number(v))}%`}
              series={[{ key: "avg_pct", label: "Average %", color: CHART.c2 }]}
            />
          </ChartPanel>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <ChartPanel title="Reward trend" description="Average and maximum advertised % of offers detected each day" {...common} empty={!a?.discovery_trend.some((d) => d.avg_pct !== null)}>
            <LineSeries
              data={a?.discovery_trend ?? []}
              xKey="date"
              xFormatter={(v) => formatAxisDate(String(v))}
              valueFormatter={(v) => `${Math.round(Number(v))}%`}
              series={[
                { key: "avg_pct", label: "Average %", color: CHART.c1 },
                { key: "max_pct", label: "Maximum %", color: CHART.c2 },
              ]}
            />
          </ChartPanel>
          <ChartPanel title="Price trend" description="Recorded price drops vs rises per day" {...common} empty={isEmptySeries(a?.price_movement, ["drops", "rises"])}>
            <BarSeries
              stacked
              data={a?.price_movement ?? []}
              xKey="date"
              xFormatter={(v) => formatAxisDate(String(v))}
              series={[
                { key: "drops", label: "Drops", color: CHART.c2 },
                { key: "rises", label: "Rises", color: CHART.c4 },
              ]}
            />
          </ChartPanel>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <ChartPanel title="Campaign timing – hour" description="Offer first detections by hour of day (IST)" {...common} empty={isEmptySeries(hours, ["count"])}>
            <BarSeries data={hours} xKey="label" series={[{ key: "count", label: "Detections", color: CHART.c1 }]} />
          </ChartPanel>
          <ChartPanel title="Campaign timing – weekday" description="Offer first detections by weekday (IST)" {...common} empty={isEmptySeries(weekday, ["count"])}>
            <BarSeries data={weekday} xKey="label" series={[{ key: "count", label: "Detections", color: CHART.c1 }]} />
          </ChartPanel>
          <ChartPanel title="Expiry profile" description="Active offers by time to stated expiry" {...common} empty={isEmptySeries(a?.expiry_distribution, ["count"])}>
            <BarSeries data={a?.expiry_distribution ?? []} xKey="bucket" series={[{ key: "count", label: "Offers", color: CHART.c3 }]} colorByIndex={(_, r) => (r.bucket === "No expiry stated" ? CHART.c5 : r.bucket === "< 24 h" ? CHART.c4 : CHART.c3)} />
          </ChartPanel>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <ChartPanel title="Discovery performance" description="Scan runs per day and products processed" {...common} empty={isEmptySeries(a?.scan_performance, ["runs"])}>
            <BarSeries
              data={a?.scan_performance ?? []}
              xKey="date"
              xFormatter={(v) => formatAxisDate(String(v))}
              series={[
                { key: "products_processed", label: "Products processed", color: CHART.c1 },
                { key: "offers_detected", label: "Offers detected", color: CHART.c2 },
              ]}
            />
          </ChartPanel>
          <ChartPanel title="Scan reliability" description="Failed runs and average duration (seconds)" {...common} empty={isEmptySeries(a?.scan_performance, ["runs"])}>
            <LineSeries
              data={(a?.scan_performance ?? []).map((s) => ({ ...s, avg_seconds: s.avg_duration_ms === null ? null : Math.round(s.avg_duration_ms / 100) / 10 }))}
              xKey="date"
              xFormatter={(v) => formatAxisDate(String(v))}
              series={[
                { key: "failed", label: "Failed runs", color: CHART.c4 },
                { key: "avg_seconds", label: "Avg duration (s)", color: CHART.c5 },
              ]}
            />
          </ChartPanel>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <Panel>
            <PanelHeader title="Source performance" description="Health and offers detected in range" actions={<Link href="/sources" className="text-xs text-accent hover:underline">Manage sources</Link>} />
            {q.isLoading ? (
              <Skeleton className="m-3 h-40" />
            ) : q.error ? (
              <ErrorState message={q.error.message} />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-2xs uppercase tracking-[0.04em] text-muted">
                    <th className="border-b border-line bg-subtle px-3 py-2 text-left font-medium">Source</th>
                    <th className="border-b border-line bg-subtle px-3 py-2 text-left font-medium">State</th>
                    <th className="border-b border-line bg-subtle px-3 py-2 text-right font-medium">Offers</th>
                    <th className="border-b border-line bg-subtle px-3 py-2 text-left font-medium">Last success</th>
                    <th className="border-b border-line bg-subtle px-3 py-2 text-right font-medium">Failures</th>
                  </tr>
                </thead>
                <tbody>
                  {a?.source_performance.map((s) => (
                    <tr key={s.id}>
                      <td className="border-b border-line px-3 py-2">
                        <p className="font-medium">{s.name}</p>
                        <SourceLabel type={s.source_type} />
                      </td>
                      <td className="border-b border-line px-3 py-2">
                        {!s.enabled ? <Badge tone="muted">Disabled</Badge> : s.consecutive_failures ? <Badge tone="negative">Failing</Badge> : <Badge tone="positive">Enabled</Badge>}
                      </td>
                      <td className="num border-b border-line px-3 py-2 text-right">{s.offers_in_range ?? 0}</td>
                      <td className="border-b border-line px-3 py-2 text-xs text-muted">{formatDateTimeShort(s.last_success_at) ?? "Never"}</td>
                      <td className="num border-b border-line px-3 py-2 text-right">{s.consecutive_failures}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
          <Panel>
            <PanelHeader title="Highest advertised rewards" description="Active offers ranked by advertised %" />
            {q.isLoading ? (
              <Skeleton className="m-3 h-40" />
            ) : !a?.highest_rewards.length ? (
              <EmptyState title="No active offers with a calculated percentage" />
            ) : (
              <ul className="divide-y divide-line">
                {a.highest_rewards.map((o, i) => (
                  <li key={o.id}>
                    <Link href={`/products/${o.product_id}`} className="grid grid-cols-[20px_1fr_auto_auto] items-center gap-3 px-3 py-2 hover:bg-subtle/70">
                      <span className="num text-xs text-faint">{i + 1}</span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm">{o.product?.title ?? "Title not available"}</span>
                        <span className="flex items-center gap-2 text-2xs text-faint">
                          <Money value={o.product?.current_price} /> · <CoinsValue offer={o} /> coins
                        </span>
                      </span>
                      <OfferStatusBadge status={o.status} />
                      <PercentValue offer={o} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
        <p className="text-2xs text-faint">
          All analytics derive from stored observations. Percentages are advertised values; 100% means advertised coins equal the eligible purchase value, not a rupee refund.
        </p>
      </div>
    </>
  );
}
