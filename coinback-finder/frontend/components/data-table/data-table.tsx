"use client";

import { useMemo, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown, Columns3 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/field";
import { MenuLabel, Popover } from "@/components/ui/popover";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/states";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { cn } from "@/services/cn";

export interface Column<T> {
  id: string;
  header: ReactNode;
  label?: string;
  cell: (row: T) => ReactNode;
  sortKey?: string;
  align?: "left" | "right" | "center";
  width?: string;
  defaultHidden?: boolean;
  hideable?: boolean;
  className?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows?: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  sort?: string;
  order?: "asc" | "desc";
  onSort?: (key: string, order: "asc" | "desc") => void;
  selection?: { selected: Set<string>; onChange: (next: Set<string>) => void; max?: number };
  onRowClick?: (row: T) => void;
  rowClassName?: (row: T) => string | undefined;
  empty?: ReactNode;
  storageKey?: string;
  toolbar?: ReactNode;
  toolbarRight?: ReactNode;
  footer?: ReactNode;
  skeletonRows?: number;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading,
  error,
  onRetry,
  sort,
  order = "desc",
  onSort,
  selection,
  onRowClick,
  rowClassName,
  empty,
  storageKey,
  toolbar,
  toolbarRight,
  footer,
  skeletonRows = 10,
  className,
}: DataTableProps<T>) {
  const defaults = useMemo(() => columns.filter((c) => c.defaultHidden).map((c) => c.id), [columns]);
  const [hidden, setHidden] = useLocalStorage<string[]>(`cbf:cols:${storageKey ?? "none"}`, defaults);
  const visible = columns.filter((c) => !storageKey || c.hideable === false || !hidden.includes(c.id));

  const pageKeys = rows?.map(rowKey) ?? [];
  const selectedOnPage = selection ? pageKeys.filter((k) => selection.selected.has(k)).length : 0;
  const allSelected = pageKeys.length > 0 && selectedOnPage === pageKeys.length;

  const toggleAll = () => {
    if (!selection) return;
    const next = new Set(selection.selected);
    if (allSelected) pageKeys.forEach((k) => next.delete(k));
    else
      for (const k of pageKeys) {
        if (selection.max && next.size >= selection.max) break;
        next.add(k);
      }
    selection.onChange(next);
  };
  const toggleOne = (key: string, checked: boolean) => {
    if (!selection) return;
    const next = new Set(selection.selected);
    if (checked) {
      if (selection.max && next.size >= selection.max) return;
      next.add(key);
    } else next.delete(key);
    selection.onChange(next);
  };

  const headerSort = (col: Column<T>) => {
    if (!col.sortKey || !onSort) return;
    if (sort === col.sortKey) onSort(col.sortKey, order === "asc" ? "desc" : "asc");
    else onSort(col.sortKey, "desc");
  };

  const colCount = visible.length + (selection ? 1 : 0);
  const showToolbar = toolbar || toolbarRight || storageKey;

  return (
    <div className={cn("flex min-w-0 flex-col", className)}>
      {showToolbar ? (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{toolbar}</div>
          <div className="flex items-center gap-1.5">
            {toolbarRight}
            {storageKey ? (
              <Popover
                align="right"
                trigger={({ toggle }) => (
                  <Button size="sm" variant="secondary" onClick={toggle} aria-label="Choose columns">
                    <Columns3 className="h-3.5 w-3.5" />
                    Columns
                  </Button>
                )}
              >
                <MenuLabel>Visible columns</MenuLabel>
                <div className="max-h-72 overflow-y-auto">
                  {columns
                    .filter((c) => c.hideable !== false)
                    .map((c) => (
                      <label key={c.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-subtle">
                        <Checkbox
                          checked={!hidden.includes(c.id)}
                          onChange={(v) => setHidden((h) => (v ? h.filter((x) => x !== c.id) : [...h, c.id]))}
                          label={c.label ?? String(c.header)}
                        />
                        {c.label ?? c.header}
                      </label>
                    ))}
                </div>
              </Popover>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="scrollbar-thin relative overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-0 text-sm">
          <thead>
            <tr>
              {selection ? (
                <th className="sticky top-0 z-10 w-8 border-b border-line bg-subtle px-3">
                  <Checkbox checked={allSelected} indeterminate={selectedOnPage > 0} onChange={toggleAll} label="Select all on page" />
                </th>
              ) : null}
              {visible.map((col) => {
                const active = sort === col.sortKey && Boolean(col.sortKey);
                return (
                  <th
                    key={col.id}
                    scope="col"
                    style={{ width: col.width }}
                    aria-sort={active ? (order === "asc" ? "ascending" : "descending") : undefined}
                    className={cn(
                      "sticky top-0 z-10 h-8 whitespace-nowrap border-b border-line bg-subtle px-3 text-2xs font-medium text-muted",
                      col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : "text-left",
                    )}
                  >
                    {col.sortKey && onSort ? (
                      <button
                        type="button"
                        onClick={() => headerSort(col)}
                        className={cn("inline-flex items-center gap-1 hover:text-fg", active && "text-fg", col.align === "right" && "flex-row-reverse")}
                      >
                        {col.header}
                        {active ? (
                          order === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                        ) : (
                          <ChevronsUpDown className="h-3 w-3 opacity-40" />
                        )}
                      </button>
                    ) : (
                      col.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading && !rows?.length
              ? Array.from({ length: skeletonRows }).map((_, i) => (
                  <tr key={`s${i}`}>
                    {Array.from({ length: colCount }).map((__, j) => (
                      <td key={j} className="table-cell border-b border-line">
                        <Skeleton className="h-3 w-full max-w-[140px]" />
                      </td>
                    ))}
                  </tr>
                ))
              : null}
            {!loading && error ? (
              <tr>
                <td colSpan={colCount}>
                  <ErrorState message={error} onRetry={onRetry} />
                </td>
              </tr>
            ) : null}
            {!error && rows?.length === 0 && !loading ? (
              <tr>
                <td colSpan={colCount}>{empty ?? <EmptyState title="No records" />}</td>
              </tr>
            ) : null}
            {!error
              ? rows?.map((row) => {
                  const key = rowKey(row);
                  const isSelected = selection?.selected.has(key);
                  return (
                    <tr
                      key={key}
                      onClick={onRowClick ? () => onRowClick(row) : undefined}
                      className={cn(
                        "group transition-colors hover:bg-subtle/70",
                        onRowClick && "cursor-pointer",
                        isSelected && "bg-accent-soft/60 hover:bg-accent-soft",
                        loading && "opacity-60",
                        rowClassName?.(row),
                      )}
                    >
                      {selection ? (
                        <td className="table-cell w-8 border-b border-line">
                          <Checkbox
                            checked={Boolean(isSelected)}
                            disabled={!isSelected && Boolean(selection.max) && selection.selected.size >= (selection.max ?? Infinity)}
                            onChange={(v) => toggleOne(key, v)}
                            label="Select row"
                          />
                        </td>
                      ) : null}
                      {visible.map((col) => (
                        <td
                          key={col.id}
                          className={cn(
                            "table-cell border-b border-line",
                            col.align === "right" ? "num text-right" : col.align === "center" ? "text-center" : "text-left",
                            col.className,
                          )}
                        >
                          {col.cell(row)}
                        </td>
                      ))}
                    </tr>
                  );
                })
              : null}
          </tbody>
        </table>
      </div>
      {footer}
    </div>
  );
}

export function StopRowClick({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={className} onClick={(e) => e.stopPropagation()}>
      {children}
    </div>
  );
}
