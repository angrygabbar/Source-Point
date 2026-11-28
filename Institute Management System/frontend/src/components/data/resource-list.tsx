"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Download, MoreHorizontal, Plus, RotateCcw, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { Badge, Button, ConfirmDialog, EmptyState, ErrorState, Menu, Modal, Select, Skeleton, StatusBadge } from "@/components/ui";
import { useActionRunner } from "@/components/data/action-runner";
import { RefSelect } from "@/components/data/ref-select";
import { ResourceForm } from "@/components/data/resource-form";
import { useMeta } from "@/hooks/use-meta";
import { useSession } from "@/hooks/use-session";
import { api, apiResponse, errorMessage, type Page, withBasePath } from "@/lib/api";
import { detailHref } from "@/lib/nav";
import { RESOURCE_ACTIONS } from "@/lib/resource-actions";
import { fmtDate, fmtDateTime, fmtMoney } from "@/lib/utils";
import type { FieldMeta, ResourceMeta, Row } from "@/types";

export function renderCell(f: FieldMeta | undefined, row: Row, currency = "INR"): ReactNode {
  if (!f) return null;
  const v = row[f.name];
  if (f.type === "ref") return row.display?.[f.name] ?? (v ? <span className="text-slate-400">{String(v).slice(0, 8)}</span> : "—");
  if (v === null || v === undefined || v === "") return <span className="text-slate-400">—</span>;
  switch (f.type) {
    case "enum":
      return f.name.includes("status") || f.name === "stage" || f.name.endsWith("_state") ? <StatusBadge value={String(v)} /> : <Badge>{String(v).replace(/_/g, " ")}</Badge>;
    case "boolean":
      return v ? <Badge tone="green">Yes</Badge> : <Badge>No</Badge>;
    case "money":
      return fmtMoney(String(v), currency);
    case "date":
      return fmtDate(String(v));
    case "datetime":
      return fmtDateTime(String(v));
    case "json":
      return <span className="font-mono text-xs text-slate-500">{JSON.stringify(v).slice(0, 40)}</span>;
    default: {
      const s = String(v);
      return s.length > 60 ? `${s.slice(0, 60)}…` : s;
    }
  }
}

function defaultColumns(meta: ResourceMeta): FieldMeta[] {
  const byName = new Map(meta.fields.map((f) => [f.name, f]));
  if (meta.list_columns.length) return meta.list_columns.map((c) => byName.get(c)).filter(Boolean) as FieldMeta[];
  return meta.fields.filter((f) => !f.system && f.type !== "json" && f.type !== "text" && f.name !== "branch_id").slice(0, 6);
}

export function ResourceList({
  resource,
  fixedFilters,
  title,
  createDefaults,
  hideCreate,
  compact,
  toolbar,
}: {
  resource: string;
  fixedFilters?: Record<string, string>;
  title?: string;
  createDefaults?: Record<string, unknown>;
  hideCreate?: boolean;
  compact?: boolean;
  toolbar?: ReactNode;
}) {
  const { me, can } = useSession();
  const qc = useQueryClient();
  const metaQ = useMeta(resource);
  const meta = metaQ.data;
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(compact ? 10 : 25);
  const [sort, setSort] = useState<string | undefined>();
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [archived, setArchived] = useState(false);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);
  const [deleting, setDeleting] = useState<Row | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkDelete, setBulkDelete] = useState(false);
  const currency = me?.institute?.currency ?? "INR";

  const query = useMemo(
    () => ({ page, page_size: pageSize, sort, q: search || undefined, include_archived: archived || undefined, ...filters, ...(fixedFilters ?? {}) }),
    [page, pageSize, sort, search, archived, filters, fixedFilters],
  );
  const list = useQuery({
    queryKey: ["list", resource, query],
    queryFn: () => api<Page<Row>>(`/${resource}`, { query }),
    enabled: !!meta,
    placeholderData: (prev) => prev,
  });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["list", resource] });
    setSelected(new Set());
  };
  const runner = useActionRunner(refresh);

  if (metaQ.isLoading) return <div className="card p-4"><Skeleton className="h-40" /></div>;
  if (metaQ.isError || !meta) return <ErrorState error={metaQ.error ?? new Error("This module is not available for your account")} />;

  const cols = defaultColumns(meta);
  const enumFilters = meta.fields.filter((f) => f.type === "enum" && !fixedFilters?.[f.name]).slice(0, 2);
  const refFilters = meta.fields.filter((f) => f.type === "ref" && f.ref && ["batch_id", "student_id", "teacher_id", "subject_id", "course_id", "branch_id"].includes(f.name) && !fixedFilters?.[f.name]).slice(0, compact ? 0 : 2);
  const dateField = meta.fields.find((f) => f.type === "date" && !f.system);
  const actions = (RESOURCE_ACTIONS[resource] ?? []).filter((a) => !a.perms || can(...a.perms));
  const total = list.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / pageSize));

  const toggleSort = (name: string) => {
    setSort((s) => (s === name ? `-${name}` : s === `-${name}` ? undefined : name));
    setPage(1);
  };

  const doExport = async (format: string) => {
    try {
      const res = await apiResponse(`/${resource}/export`, { query: { ...query, page: undefined, page_size: undefined, format } });
      if (res.status === 202) {
        toast.info("Large export queued. You will be notified when it is ready.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = /filename="?([^"]+)"?/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? `${resource}.${format}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-slate-100 p-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          {title && <h3 className="mr-2 text-sm font-semibold text-slate-800">{title}</h3>}
          {meta.search && (
            <form
              className="relative"
              onSubmit={(e) => {
                e.preventDefault();
                setSearch(q);
                setPage(1);
              }}
            >
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <input className="input w-56 pl-8" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} onBlur={() => { setSearch(q); setPage(1); }} />
            </form>
          )}
          {enumFilters.map((f) => (
            <Select key={f.name} className="w-40" value={filters[f.name] ?? ""} onChange={(e) => { setFilters({ ...filters, [f.name]: e.target.value }); setPage(1); }}>
              <option value="">{f.label}: all</option>
              {f.enum?.map((o) => <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
            </Select>
          ))}
          {refFilters.map((f) => (
            <div key={f.name} className="w-48">
              <RefSelect resource={f.ref!} value={filters[f.name] || null} placeholder={`${f.label}: all`} onChange={(v) => { setFilters({ ...filters, [f.name]: v ?? "" }); setPage(1); }} />
            </div>
          ))}
          {dateField && !compact && (
            <div className="flex items-center gap-1 text-xs text-slate-500">
              <input type="date" className="input w-36" value={filters[`${dateField.name}__gte`] ?? ""} onChange={(e) => { setFilters({ ...filters, [`${dateField.name}__gte`]: e.target.value }); setPage(1); }} aria-label={`${dateField.label} from`} />
              <span>–</span>
              <input type="date" className="input w-36" value={filters[`${dateField.name}__lte`] ?? ""} onChange={(e) => { setFilters({ ...filters, [`${dateField.name}__lte`]: e.target.value }); setPage(1); }} aria-label={`${dateField.label} to`} />
            </div>
          )}
          {meta.archive && meta.read_mode === "all" && (
            <label className="flex items-center gap-1.5 text-xs text-slate-600">
              <input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} /> Include archived
            </label>
          )}
          {(Object.values(filters).some(Boolean) || search) && (
            <Button variant="ghost" size="sm" onClick={() => { setFilters({}); setSearch(""); setQ(""); }}>
              <RotateCcw className="h-3.5 w-3.5" /> Reset
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2">
          {toolbar}
          {selected.size > 0 && meta.can.delete && (
            <Button variant="danger" size="sm" onClick={() => setBulkDelete(true)}>
              {meta.archive ? "Archive" : "Delete"} {selected.size}
            </Button>
          )}
          {meta.read_mode === "all" && (
            <Menu
              trigger={<Button variant="outline" size="sm"><Download className="h-3.5 w-3.5" /> Export</Button>}
              items={[
                { label: "CSV", onClick: () => doExport("csv") },
                { label: "Excel", onClick: () => doExport("xlsx") },
                { label: "PDF", onClick: () => doExport("pdf") },
              ]}
            />
          )}
          {meta.can.create && !hideCreate && (
            <Button size="sm" onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New</Button>
          )}
        </div>
      </div>

      {list.isError ? (
        <div className="p-4"><ErrorState error={list.error} onRetry={() => list.refetch()} /></div>
      ) : list.isLoading ? (
        <div className="space-y-2 p-4">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8" />)}</div>
      ) : !list.data?.items.length ? (
        <EmptyState
          title={`No ${meta.label.toLowerCase()} found`}
          description={meta.can.create ? "Create the first record or adjust the filters." : "Nothing to show for the current filters."}
          action={meta.can.create && !hideCreate ? <Button size="sm" onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New</Button> : undefined}
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100">
            <thead className="bg-slate-50">
              <tr>
                {meta.can.delete && (
                  <th className="w-8 px-3">
                    <input
                      type="checkbox"
                      aria-label="Select all"
                      checked={selected.size === list.data.items.length}
                      onChange={(e) => setSelected(e.target.checked ? new Set(list.data!.items.map((r) => r.id)) : new Set())}
                    />
                  </th>
                )}
                {cols.map((c) => (
                  <th key={c.name} className="th cursor-pointer select-none" onClick={() => toggleSort(c.name)}>
                    <span className="inline-flex items-center gap-1">
                      {c.label}
                      {sort === c.name && <ArrowUp className="h-3 w-3" />}
                      {sort === `-${c.name}` && <ArrowDown className="h-3 w-3" />}
                    </span>
                  </th>
                ))}
                <th className="th w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {list.data.items.map((row) => (
                <tr key={row.id} className="group hover:bg-slate-50/70">
                  {meta.can.delete && (
                    <td className="px-3">
                      <input
                        type="checkbox"
                        aria-label="Select row"
                        checked={selected.has(row.id)}
                        onChange={(e) => {
                          const n = new Set(selected);
                          if (e.target.checked) n.add(row.id);
                          else n.delete(row.id);
                          setSelected(n);
                        }}
                      />
                    </td>
                  )}
                  {cols.map((c, i) => (
                    <td key={c.name} className="td">
                      {i === 0 ? (
                        <Link href={detailHref(resource, row.id)} className="font-medium text-brand-800 hover:underline">
                          {renderCell(c, row, currency)}
                        </Link>
                      ) : (
                        renderCell(c, row, currency)
                      )}
                      {i === 0 && row.is_archived === true && <Badge className="ml-2">archived</Badge>}
                    </td>
                  ))}
                  <td className="td text-right">
                    <Menu
                      trigger={<Button variant="ghost" size="icon" aria-label="Row actions"><MoreHorizontal className="h-4 w-4" /></Button>}
                      items={[
                        { label: "Open", onClick: () => (window.location.href = withBasePath(detailHref(resource, row.id))) },
                        { label: "Edit", onClick: () => setEditing(row), hidden: !meta.can.update },
                        ...actions.filter((a) => !a.when || a.when(row)).map((a) => ({ label: a.label, danger: a.danger, onClick: () => runner.run(a, row) })),
                        {
                          label: row.is_archived ? "Restore" : meta.archive ? "Archive" : "Delete",
                          danger: !row.is_archived,
                          hidden: !meta.can.delete,
                          onClick: async () => {
                            if (row.is_archived) {
                              try {
                                await api(`/${resource}/${row.id}/restore`, { method: "POST" });
                                toast.success("Restored");
                                refresh();
                              } catch (e) {
                                toast.error(errorMessage(e));
                              }
                            } else setDeleting(row);
                          },
                        },
                      ]}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > 0 && (
        <div className="flex flex-col items-center justify-between gap-2 border-t border-slate-100 px-3 py-2 text-xs text-slate-500 sm:flex-row">
          <span>
            {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
          </span>
          <div className="flex items-center gap-2">
            <Select className="h-8 w-20 text-xs" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
              {[10, 25, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
            </Select>
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
            <span>Page {page} / {pages}</span>
            <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button>
          </div>
        </div>
      )}

      <Modal open={creating} onOpenChange={setCreating} title={`New ${meta.label.replace(/s$/, "").toLowerCase()}`} wide>
        <ResourceForm meta={meta} defaults={{ ...(fixedFilters ?? {}), ...(createDefaults ?? {}) }} onSaved={() => { setCreating(false); refresh(); }} onCancel={() => setCreating(false)} />
      </Modal>
      <Modal open={!!editing} onOpenChange={(v) => !v && setEditing(null)} title={`Edit ${meta.label.replace(/s$/, "").toLowerCase()}`} wide>
        {editing && <ResourceForm meta={meta} initial={editing} onSaved={() => { setEditing(null); refresh(); }} onCancel={() => setEditing(null)} />}
      </Modal>
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(v) => !v && setDeleting(null)}
        title={meta.archive ? "Archive record" : "Delete record"}
        message={meta.archive ? "The record will be archived and hidden from lists. History is preserved." : "This permanently deletes the record if it is not referenced elsewhere."}
        danger
        requireReason={meta.archive}
        confirmLabel={meta.archive ? "Archive" : "Delete"}
        onConfirm={async (reason) => {
          try {
            await api(`/${resource}/${deleting!.id}`, { method: "DELETE", query: { reason } });
            toast.success(meta.archive ? "Archived" : "Deleted");
            refresh();
          } catch (e) {
            toast.error(errorMessage(e));
          }
        }}
      />
      <ConfirmDialog
        open={bulkDelete}
        onOpenChange={setBulkDelete}
        title={`${meta.archive ? "Archive" : "Delete"} ${selected.size} records`}
        danger
        requireReason={meta.archive}
        onConfirm={async (reason) => {
          let ok = 0;
          for (const id of Array.from(selected)) {
            try {
              await api(`/${resource}/${id}`, { method: "DELETE", query: { reason } });
              ok += 1;
            } catch (e) {
              toast.error(errorMessage(e));
            }
          }
          toast.success(`${ok} record(s) processed`);
          refresh();
        }}
      />
      {runner.dialog}
    </div>
  );
}
