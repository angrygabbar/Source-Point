"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import type { PageMeta } from "@/services/types";
import { Button } from "./button";
import { Select } from "./field";

export function Pagination({ meta, onPage, onPageSize, pageSizes = [25, 50, 100, 200] }: { meta?: PageMeta; onPage: (p: number) => void; onPageSize?: (s: number) => void; pageSizes?: number[] }) {
  if (!meta) return null;
  const from = meta.total === 0 ? 0 : (meta.page - 1) * meta.page_size + 1;
  const to = Math.min(meta.page * meta.page_size, meta.total);
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-3 py-2 text-xs text-muted">
      <span className="num">
        {from.toLocaleString("en-IN")}–{to.toLocaleString("en-IN")} of {meta.total.toLocaleString("en-IN")}
      </span>
      <div className="flex items-center gap-2">
        {onPageSize ? (
          <label className="flex items-center gap-1.5">
            Rows
            <Select compact value={meta.page_size} onChange={(e) => onPageSize(Number(e.target.value))} className="w-[70px]">
              {pageSizes.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </label>
        ) : null}
        <span className="num">
          Page {meta.page} / {meta.pages}
        </span>
        <Button size="icon-sm" variant="secondary" aria-label="Previous page" disabled={meta.page <= 1} onClick={() => onPage(meta.page - 1)}>
          <ChevronLeft className="h-3.5 w-3.5" />
        </Button>
        <Button size="icon-sm" variant="secondary" aria-label="Next page" disabled={meta.page >= meta.pages} onClick={() => onPage(meta.page + 1)}>
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
