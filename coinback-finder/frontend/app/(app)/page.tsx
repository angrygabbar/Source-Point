"use client";

import { Play, Plus } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { AddProductDialog } from "@/components/offers/add-product-dialog";
import { Button } from "@/components/ui/button";
import { analyticsParams, RangePicker, type RangeKey } from "@/dashboard/range-picker";
import { MetricStrip } from "@/dashboard/metric-strip";
import { OverviewCharts } from "@/dashboard/overview-charts";
import { OverviewPanels } from "@/dashboard/overview-panels";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { useUrlState } from "@/hooks/use-url-state";
import { api } from "@/services/api";
import { formatDateTimeShort } from "@/services/format";
import type { Analytics, DashboardPanels, DashboardSummary, Envelope } from "@/services/types";

export default function OverviewPage() {
  const { state, update } = useUrlState({ range: "7d", from: "", to: "" });
  const [adding, setAdding] = useState(false);
  const summary = useApi<Envelope<DashboardSummary>>("/dashboard/summary", undefined, { refetchInterval: 60_000 });
  const panels = useApi<Envelope<DashboardPanels>>("/dashboard/panels", undefined, { refetchInterval: 60_000 });
  const params = analyticsParams(state.range as RangeKey, state.from, state.to);
  const analytics = useApi<Envelope<Analytics>>(params ? "/dashboard/analytics" : null, params ?? undefined, { keepPrevious: true });
  const run = useApiMutation(() => api.post("/discovery/run", {}), { invalidate: ["/dashboard", "/discovery"], success: "Scan queued" });

  return (
    <>
      <PageHeader
        title="Overview"
        description="Advertised SuperCoin / CoinBack offers from permitted sources. Values are advertised unless marked verified."
        meta={summary.data ? <span>Updated {formatDateTimeShort(summary.data.data.generated_at)} IST</span> : null}
        actions={
          <>
            <Button size="sm" onClick={() => setAdding(true)}>
              <Plus className="h-3.5 w-3.5" />
              Add product URL
            </Button>
            <Button size="sm" variant="primary" loading={run.isPending} onClick={() => run.mutate(undefined)}>
              <Play className="h-3.5 w-3.5" />
              Run scan now
            </Button>
          </>
        }
      />
      <div className="space-y-4">
        <MetricStrip summary={summary.data?.data} loading={summary.isLoading} />
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">Activity</h2>
          <RangePicker range={state.range as RangeKey} from={state.from} to={state.to} onChange={(p) => update(p, { resetPage: false })} />
        </div>
        <OverviewCharts data={analytics.data?.data} loading={analytics.isLoading} error={analytics.error?.message} />
        <OverviewPanels data={panels.data?.data} loading={panels.isLoading} error={panels.error?.message} />
      </div>
      <AddProductDialog open={adding} onClose={() => setAdding(false)} />
    </>
  );
}
