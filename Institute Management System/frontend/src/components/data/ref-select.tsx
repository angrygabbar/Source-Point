"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type Page } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Row } from "@/types";

const TITLE_GUESS = ["full_name", "name", "title", "invoice_number", "receipt_number", "contact_name", "code", "session_date", "description"];

function titleOf(row: Row): string {
  for (const k of TITLE_GUESS) {
    if (row[k]) {
      const extra = row.student_code ?? row.teacher_code ?? row.code;
      return extra && k !== "code" ? `${row[k]} (${extra})` : String(row[k]);
    }
  }
  return String(row.id).slice(0, 8);
}

/** Async searchable select for foreign keys. Fetches the referenced resource with permission scoping. */
export function RefSelect({
  resource,
  value,
  onChange,
  placeholder = "Select…",
  disabled,
  filters,
  initialLabel,
  allowClear = true,
}: {
  resource: string;
  value?: string | null;
  onChange: (v: string | null, row?: Row) => void;
  placeholder?: string;
  disabled?: boolean;
  filters?: Record<string, string>;
  initialLabel?: string | null;
  allowClear?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [label, setLabel] = useState<string | null>(initialLabel ?? null);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 250);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const filterKey = useMemo(() => JSON.stringify(filters ?? {}), [filters]);
  const list = useQuery({
    queryKey: ["ref", resource, debounced, filterKey],
    queryFn: () => api<Page<Row>>(`/${resource}`, { query: { q: debounced || undefined, page_size: 20, ...(filters ?? {}) } }),
    enabled: open && !disabled,
  });

  const selected = useQuery({
    queryKey: ["ref-one", resource, value],
    queryFn: () => api<Row>(`/${resource}/${value}`),
    enabled: !!value && !label,
    retry: false,
  });

  useEffect(() => {
    if (!value) setLabel(null);
  }, [value]);
  useEffect(() => {
    if (selected.data) setLabel(titleOf(selected.data));
  }, [selected.data]);

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className={cn("input flex items-center justify-between text-left", !value && "text-slate-400")}
      >
        <span className="truncate">{value ? label ?? "Loading…" : placeholder}</span>
        <span className="flex items-center gap-1">
          {value && allowClear && !disabled && (
            <X
              className="h-3.5 w-3.5 text-slate-400 hover:text-slate-700"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
                setLabel(null);
              }}
            />
          )}
          <ChevronDown className="h-4 w-4 text-slate-400" />
        </span>
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full min-w-[220px] rounded-lg border border-slate-200 bg-white shadow-lg">
          <input autoFocus className="input rounded-b-none border-0 border-b" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} />
          <ul className="max-h-60 overflow-y-auto py-1">
            {list.isLoading && <li className="px-3 py-2 text-sm text-slate-500">Loading…</li>}
            {list.isError && <li className="px-3 py-2 text-sm text-red-600">Unable to load options</li>}
            {list.data?.items.length === 0 && <li className="px-3 py-2 text-sm text-slate-500">No matches</li>}
            {list.data?.items.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  className={cn("w-full px-3 py-1.5 text-left text-sm hover:bg-slate-100", r.id === value && "bg-indigo-50 text-brand-800")}
                  onClick={() => {
                    onChange(r.id, r);
                    setLabel(titleOf(r));
                    setOpen(false);
                  }}
                >
                  {titleOf(r)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
