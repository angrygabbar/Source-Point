"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button, Field, Input, Modal, Select, Textarea } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { api, errorMessage, openFile, openSignedLink } from "@/lib/api";
import type { PromptField, ResourceAction } from "@/lib/resource-actions";
import type { Row } from "@/types";

export function PromptForm({ fields, values, setValues }: { fields: PromptField[]; values: Record<string, unknown>; setValues: (v: Record<string, unknown>) => void }) {
  const set = (k: string, v: unknown) => setValues({ ...values, [k]: v });
  return (
    <div className="space-y-3">
      {fields.map((f) => (
        <Field key={f.name} label={f.label} required={f.required}>
          {f.type === "textarea" ? (
            <Textarea value={String(values[f.name] ?? "")} onChange={(e) => set(f.name, e.target.value)} />
          ) : f.type === "select" ? (
            <Select value={String(values[f.name] ?? "")} onChange={(e) => set(f.name, e.target.value)}>
              <option value="">Select…</option>
              {f.options?.map((o) => <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
            </Select>
          ) : f.type === "ref" ? (
            <RefSelect resource={f.ref!} value={(values[f.name] as string) || null} onChange={(v) => set(f.name, v)} />
          ) : f.type === "checkbox" ? (
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!values[f.name]} onChange={(e) => set(f.name, e.target.checked)} /> Yes</label>
          ) : (
            <Input
              type={f.type === "datetime" ? "datetime-local" : f.type}
              step={f.type === "number" ? "0.01" : undefined}
              value={String(values[f.name] ?? "")}
              onChange={(e) => set(f.name, e.target.value)}
            />
          )}
        </Field>
      ))}
    </div>
  );
}

export function normalizePrompt(fields: PromptField[], values: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    const v = values[f.name];
    if (v === "" || v === undefined || v === null) continue;
    if (f.type === "datetime") out[f.name] = new Date(String(v)).toISOString();
    else if (f.type === "number") out[f.name] = String(v);
    else out[f.name] = v;
  }
  return out;
}

export function useActionRunner(onDone?: () => void) {
  const router = useRouter();
  const [active, setActive] = useState<{ action: ResourceAction; row: Row } | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);

  const execute = async (action: ResourceAction, row: Row, vals: Record<string, unknown>) => {
    const path = action.path(row);
    if (action.kind === "link") return router.push(path);
    if (action.kind === "external") return window.open(path, "_blank", "noopener");
    try {
      if (action.kind === "pdf") return await openFile(path);
      if (action.kind === "signed") return await openSignedLink(path);
      const body = action.body ? action.body(row, vals) : vals;
      await api(path, { method: action.method ?? "POST", body });
      toast.success(`${action.label}: done`);
      onDone?.();
    } catch (e) {
      toast.error(errorMessage(e));
      throw e;
    }
  };

  const run = (action: ResourceAction, row: Row) => {
    if (action.fields?.length || action.confirm) {
      const init: Record<string, unknown> = {};
      action.fields?.forEach((f) => f.default !== undefined && (init[f.name] = f.default));
      setValues(init);
      setActive({ action, row });
    } else {
      void execute(action, row, {}).catch(() => undefined);
    }
  };

  const missing = active?.action.fields?.some((f) => f.required && (values[f.name] === undefined || values[f.name] === "")) ?? false;

  const dialog = (
    <Modal
      open={!!active}
      onOpenChange={(v) => !v && setActive(null)}
      title={active?.action.label ?? ""}
      description={active?.action.confirm}
      footer={
        <>
          <Button variant="outline" onClick={() => setActive(null)}>Cancel</Button>
          <Button
            variant={active?.action.danger ? "danger" : "primary"}
            loading={busy}
            disabled={missing}
            onClick={async () => {
              if (!active) return;
              setBusy(true);
              try {
                await execute(active.action, active.row, normalizePrompt(active.action.fields ?? [], values));
                setActive(null);
              } catch {
                /* toast already shown */
              } finally {
                setBusy(false);
              }
            }}
          >
            Confirm
          </Button>
        </>
      }
    >
      {active?.action.fields?.length ? <PromptForm fields={active.action.fields} values={values} setValues={setValues} /> : null}
    </Modal>
  );

  return { run, dialog };
}
