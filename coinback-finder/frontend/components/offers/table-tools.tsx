"use client";

import { useState } from "react";
import { Bookmark, Download, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { MenuItem, MenuLabel, MenuSeparator, Popover } from "@/components/ui/popover";
import { useApi, useApiMutation } from "@/hooks/use-api";
import { api, exportHref, type QueryParams } from "@/services/api";
import type { Envelope, SavedFilter } from "@/services/types";

export function ExportMenu({ path, params }: { path: string; params: QueryParams }) {
  return (
    <Popover
      align="right"
      trigger={({ toggle }) => (
        <Button size="sm" onClick={toggle}>
          <Download className="h-3.5 w-3.5" />
          Export
        </Button>
      )}
    >
      {(close) => (
        <>
          <MenuLabel>Current filters, up to 10,000 rows</MenuLabel>
          <a className="flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-subtle" href={exportHref(path, params, "csv")} onClick={close} download>
            CSV (.csv)
          </a>
          <a className="flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-subtle" href={exportHref(path, params, "xlsx")} onClick={close} download>
            Excel (.xlsx)
          </a>
        </>
      )}
    </Popover>
  );
}

export function SavedFilters({ page, current, onApply }: { page: string; current: Record<string, string>; onApply: (params: Record<string, string>) => void }) {
  const [name, setName] = useState("");
  const list = useApi<Envelope<SavedFilter[]>>("/saved-filters", { page });
  const save = useApiMutation((body: { page: string; name: string; params: Record<string, string> }) => api.post("/saved-filters", body), {
    invalidate: ["/saved-filters"],
    success: "Filter saved",
    onSuccess: () => setName(""),
  });
  const remove = useApiMutation((id: string) => api.del(`/saved-filters/${id}`), { invalidate: ["/saved-filters"] });
  const params = Object.fromEntries(Object.entries(current).filter(([k, v]) => v !== "" && k !== "page"));

  return (
    <Popover
      align="right"
      className="w-72"
      trigger={({ toggle }) => (
        <Button size="sm" onClick={toggle}>
          <Bookmark className="h-3.5 w-3.5" />
          Saved views
        </Button>
      )}
    >
      {(close) => (
        <>
          <MenuLabel>Saved views</MenuLabel>
          {list.data?.data.length ? (
            list.data.data.map((f) => (
              <div key={f.id} className="group flex items-center">
                <MenuItem
                  onClick={() => {
                    onApply(f.params);
                    close();
                  }}
                >
                  <span className="truncate">{f.name}</span>
                </MenuItem>
                <button
                  type="button"
                  aria-label={`Delete ${f.name}`}
                  className="mr-1 rounded p-1 text-faint opacity-0 hover:text-negative group-hover:opacity-100"
                  onClick={() => remove.mutate(f.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))
          ) : (
            <p className="px-2 py-1.5 text-xs text-faint">{list.isLoading ? "Loading…" : "No saved views yet."}</p>
          )}
          <MenuSeparator />
          <form
            className="flex items-center gap-1.5 p-1"
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) save.mutate({ page, name: name.trim(), params });
            }}
          >
            <Input compact placeholder="Save current filters as…" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} />
            <Button size="sm" type="submit" variant="primary" loading={save.isPending} disabled={!name.trim()}>
              Save
            </Button>
          </form>
        </>
      )}
    </Popover>
  );
}
