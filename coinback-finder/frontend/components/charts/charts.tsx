"use client";

import type { ReactElement, ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";

import { Panel, PanelHeader } from "@/components/ui/panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { cn } from "@/services/cn";

export const CHART = {
  c1: "hsl(var(--chart-1))",
  c2: "hsl(var(--chart-2))",
  c3: "hsl(var(--chart-3))",
  c4: "hsl(var(--chart-4))",
  c5: "hsl(var(--chart-5))",
};

export interface Series {
  key: string;
  label: string;
  color: string;
}

type Fmt = (v: number | string) => string;

export function ChartPanel({
  title,
  description,
  actions,
  loading,
  error,
  empty,
  height = 220,
  children,
  className,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  height?: number;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Panel className={cn("flex flex-col", className)}>
      <PanelHeader title={title} description={description} actions={actions} />
      <div className="px-2 pb-2 pt-3" style={{ height: height + 20 }}>
        {loading ? (
          <div className="flex h-full items-end gap-2 px-2 pb-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <Skeleton key={i} className="w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState message={error} className="py-4" />
        ) : empty ? (
          <EmptyState title="No data recorded for this range" description="Values appear once scans or manual entries produce records." className="h-full py-4" />
        ) : (
          <ResponsiveContainer width="100%" height={height}>
            {children as ReactElement}
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  );
}

function TooltipBox({ active, payload, label, valueFormatter, labelFormatter }: TooltipProps<number, string> & { valueFormatter?: Fmt; labelFormatter?: Fmt }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded border border-line bg-surface px-2.5 py-1.5 text-xs shadow-pop">
      <p className="mb-1 font-medium text-fg">{labelFormatter ? labelFormatter(label as string) : label}</p>
      {payload.map((p) => (
        <p key={String(p.dataKey)} className="flex items-center justify-between gap-4 text-muted">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm" style={{ background: p.color }} />
            {p.name}
          </span>
          <span className="num font-medium text-fg">{p.value === null || p.value === undefined ? "n/a" : valueFormatter ? valueFormatter(p.value as number) : p.value}</span>
        </p>
      ))}
    </div>
  );
}

const axis = { tickLine: false, axisLine: false, fontSize: 11 } as const;

export function BarSeries({
  data,
  xKey,
  series,
  stacked,
  horizontal,
  xFormatter,
  valueFormatter,
  colorByIndex,
  yWidth = 36,
  width,
  height,
}: {
  data: Record<string, unknown>[];
  xKey: string;
  series: Series[];
  stacked?: boolean;
  horizontal?: boolean;
  xFormatter?: Fmt;
  valueFormatter?: Fmt;
  colorByIndex?: (index: number, row: Record<string, unknown>) => string;
  yWidth?: number;
  width?: number;
  height?: number;
}) {
  return (
    <BarChart width={width} height={height} data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ top: 4, right: 12, bottom: 0, left: 0 }} barCategoryGap="22%">
      <CartesianGrid vertical={Boolean(horizontal)} horizontal={!horizontal} />
      {horizontal ? (
        <>
          <XAxis type="number" {...axis} allowDecimals={false} tickFormatter={valueFormatter} />
          <YAxis type="category" dataKey={xKey} {...axis} width={yWidth} tickFormatter={xFormatter} />
        </>
      ) : (
        <>
          <XAxis dataKey={xKey} {...axis} tickFormatter={xFormatter} minTickGap={8} />
          <YAxis {...axis} width={yWidth} allowDecimals={false} tickFormatter={valueFormatter} />
        </>
      )}
      <Tooltip content={<TooltipBox valueFormatter={valueFormatter} labelFormatter={xFormatter} />} />
      {series.length > 1 ? <Legend iconType="square" iconSize={8} wrapperStyle={{ fontSize: 11 }} /> : null}
      {series.map((s) => (
        <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} stackId={stacked ? "a" : undefined} radius={stacked ? 0 : [2, 2, 0, 0]} maxBarSize={28}>
          {colorByIndex ? data.map((row, i) => <Cell key={i} fill={colorByIndex(i, row)} />) : null}
        </Bar>
      ))}
    </BarChart>
  );
}

export function LineSeries({
  data,
  xKey,
  series,
  area,
  xFormatter,
  valueFormatter,
  yWidth = 36,
  width,
  height,
}: {
  data: Record<string, unknown>[];
  xKey: string;
  series: Series[];
  area?: boolean;
  xFormatter?: Fmt;
  valueFormatter?: Fmt;
  yWidth?: number;
  width?: number;
  height?: number;
}) {
  const common = (
    <>
      <CartesianGrid vertical={false} />
      <XAxis dataKey={xKey} {...axis} tickFormatter={xFormatter} minTickGap={16} />
      <YAxis {...axis} width={yWidth} tickFormatter={valueFormatter} domain={["auto", "auto"]} />
      <Tooltip content={<TooltipBox valueFormatter={valueFormatter} labelFormatter={xFormatter} />} />
      {series.length > 1 ? <Legend iconType="plainline" iconSize={12} wrapperStyle={{ fontSize: 11 }} /> : null}
    </>
  );
  if (area) {
    return (
      <AreaChart width={width} height={height} data={data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
        {common}
        {series.map((s) => (
          <Area key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} fill={s.color} fillOpacity={0.08} strokeWidth={1.5} dot={false} connectNulls />
        ))}
      </AreaChart>
    );
  }
  return (
    <LineChart width={width} height={height} data={data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
      {common}
      {series.map((s) => (
        <Line key={s.key} type="stepAfter" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={1.5} dot={false} connectNulls isAnimationActive={false} />
      ))}
    </LineChart>
  );
}

export const isEmptySeries = (rows: Record<string, unknown>[] | undefined, keys: string[]) =>
  !rows || rows.every((r) => keys.every((k) => !r[k]));
