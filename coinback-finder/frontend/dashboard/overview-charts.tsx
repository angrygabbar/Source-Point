"use client";

import { BarSeries, CHART, ChartPanel, LineSeries, isEmptySeries } from "@/components/charts/charts";
import { formatAxisDate, OFFER_STATUS_LABEL } from "@/services/format";
import type { Analytics, OfferStatus } from "@/services/types";

const STATUS_COLOR: Record<OfferStatus, string> = {
  VERIFIED: CHART.c2,
  UNVERIFIED: CHART.c1,
  DETECTED: CHART.c5,
  ACCOUNT_CHECK_REQUIRED: CHART.c3,
  REJECTED: CHART.c4,
  EXPIRED: CHART.c5,
  SOURCE_UNAVAILABLE: CHART.c4,
};

export function OverviewCharts({ data, loading, error }: { data?: Analytics; loading?: boolean; error?: string | null }) {
  const common = { loading, error };
  const pctColor = (_: number, row: Record<string, unknown>) =>
    row.bucket === "100%" || row.bucket === ">100%" ? CHART.c2 : row.bucket === "Not calculated" ? CHART.c5 : CHART.c1;
  const statusRows = (data?.status_breakdown ?? []).map((s) => ({ ...s, label: OFFER_STATUS_LABEL[s.status] }));

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <ChartPanel title="CoinBack distribution" description="Active offers by advertised percentage" {...common} empty={isEmptySeries(data?.coinback_distribution, ["count"])}>
        <BarSeries data={data?.coinback_distribution ?? []} xKey="bucket" series={[{ key: "count", label: "Offers", color: CHART.c1 }]} colorByIndex={pctColor} />
      </ChartPanel>
      <ChartPanel title="Discovery trend" description="New offers and products per day (IST)" {...common} empty={isEmptySeries(data?.discovery_trend, ["offers", "products"])}>
        <LineSeries
          area
          data={data?.discovery_trend ?? []}
          xKey="date"
          xFormatter={(v) => formatAxisDate(String(v))}
          series={[
            { key: "offers", label: "Offers", color: CHART.c1 },
            { key: "products", label: "Products", color: CHART.c3 },
          ]}
        />
      </ChartPanel>
      <ChartPanel title="Category distribution" description="Active offers by product category" {...common} empty={!data?.category_distribution.length}>
        <BarSeries horizontal yWidth={120} data={(data?.category_distribution ?? []).slice(0, 8)} xKey="category" series={[{ key: "offers", label: "Offers", color: CHART.c1 }]} />
      </ChartPanel>
      <ChartPanel title="Price movement" description="Recorded price drops and rises per day" {...common} empty={isEmptySeries(data?.price_movement, ["drops", "rises"])}>
        <BarSeries
          stacked
          data={data?.price_movement ?? []}
          xKey="date"
          xFormatter={(v) => formatAxisDate(String(v))}
          series={[
            { key: "drops", label: "Drops", color: CHART.c2 },
            { key: "rises", label: "Rises", color: CHART.c4 },
          ]}
        />
      </ChartPanel>
      <ChartPanel title="Reward distribution" description="Active offers by advertised or estimated coins" {...common} empty={isEmptySeries(data?.reward_distribution, ["count"])}>
        <BarSeries data={data?.reward_distribution ?? []} xKey="bucket" series={[{ key: "count", label: "Offers", color: CHART.c1 }]} colorByIndex={(_, r) => (r.bucket === "Unknown" ? CHART.c5 : CHART.c1)} />
      </ChartPanel>
      <ChartPanel title="Verified vs unverified" description="Offers first detected in range, by current status" {...common} empty={!statusRows.length}>
        <BarSeries
          horizontal
          yWidth={110}
          data={statusRows}
          xKey="label"
          series={[{ key: "count", label: "Offers", color: CHART.c1 }]}
          colorByIndex={(_, r) => STATUS_COLOR[(r.status as OfferStatus) ?? "UNVERIFIED"]}
        />
      </ChartPanel>
    </div>
  );
}
