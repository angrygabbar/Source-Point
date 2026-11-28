"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button, Field, Input, Select, Textarea } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { api, errorMessage } from "@/lib/api";
import type { FieldMeta, ResourceMeta, Row } from "@/types";

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const NUM_RE = /^-?\d+(\.\d{1,4})?$/;
const UUID_RE = /^[0-9a-f-]{36}$/i;

function fieldSchema(f: FieldMeta) {
  const req = f.required;
  const opt = <T extends z.ZodTypeAny>(s: T) => (req ? s : z.union([s, z.literal(""), z.null(), z.undefined()]));
  switch (f.type) {
    case "boolean":
      return z.boolean().optional();
    case "integer":
      return opt(z.union([z.number().int(), z.string().regex(/^-?\d+$/, "Whole number required")]));
    case "decimal":
    case "money":
      return opt(z.union([z.number(), z.string().regex(NUM_RE, "Enter a valid number")]));
    case "date":
      return opt(z.string().regex(DATE_RE, "Select a date"));
    case "datetime":
      return opt(z.string().min(1, "Required"));
    case "enum":
      return opt(z.enum((f.enum ?? [""]) as [string, ...string[]]));
    case "ref":
    case "uuid":
      return opt(z.string().regex(UUID_RE, "Select a value"));
    case "json":
      return opt(
        z.string().refine((v) => {
          try {
            JSON.parse(v);
            return true;
          } catch {
            return false;
          }
        }, "Enter valid JSON"),
      );
    default: {
      let s = z.string();
      if (f.max_length) s = s.max(f.max_length, `Maximum ${f.max_length} characters`);
      if (f.name.endsWith("email")) return opt(s.email("Enter a valid email"));
      return req ? s.min(1, "Required") : opt(s);
    }
  }
}

function toInput(f: FieldMeta, v: unknown): unknown {
  if (v === null || v === undefined) return f.type === "boolean" ? false : "";
  if (f.type === "json") return JSON.stringify(v, null, 2);
  if (f.type === "datetime" && typeof v === "string") {
    const d = new Date(v);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  return v;
}

function fromInput(f: FieldMeta, v: unknown): unknown {
  if (f.type === "boolean") return !!v;
  if (v === "" || v === undefined) return f.nullable ? null : undefined;
  if (v === null) return null;
  if (f.type === "integer") return Number(v);
  if (f.type === "decimal" || f.type === "money") return String(v);
  if (f.type === "json") return JSON.parse(String(v));
  if (f.type === "datetime") return new Date(String(v)).toISOString();
  return v;
}

export function ResourceForm({
  meta,
  initial,
  defaults,
  onSaved,
  onCancel,
}: {
  meta: ResourceMeta;
  initial?: Row | null;
  defaults?: Record<string, unknown>;
  onSaved: (row: Row) => void;
  onCancel?: () => void;
}) {
  const editing = !!initial;
  const fields = useMemo(
    () => meta.fields.filter((f) => (editing ? f.updatable : f.creatable)),
    [meta.fields, editing],
  );
  const schema = useMemo(() => {
    const shape: Record<string, z.ZodTypeAny> = {};
    fields.forEach((f) => (shape[f.name] = fieldSchema(editing ? { ...f, required: false } : f)));
    shape.change_reason = z.string().max(500).optional();
    return z.object(shape);
  }, [fields, editing]);
  const initialValues = useMemo(() => {
    const out: Record<string, unknown> = {};
    fields.forEach((f) => (out[f.name] = toInput(f, initial ? initial[f.name] : defaults?.[f.name])));
    return out;
  }, [fields, initial, defaults]);
  const { register, control, handleSubmit, formState } = useForm<Record<string, unknown>>({
    resolver: zodResolver(schema),
    defaultValues: initialValues,
  });
  const [busy, setBusy] = useState(false);

  const submit = handleSubmit(async (values) => {
    const payload: Record<string, unknown> = {};
    fields.forEach((f) => {
      const v = fromInput(f, values[f.name]);
      if (editing) {
        if (JSON.stringify(v ?? null) !== JSON.stringify(fromInput(f, initialValues[f.name]) ?? null)) payload[f.name] = v;
      } else if (v !== undefined && !(v === null && !f.nullable)) {
        payload[f.name] = v;
      }
    });
    if (editing && values.change_reason) payload.change_reason = values.change_reason;
    if (editing && Object.keys(payload).filter((k) => k !== "change_reason").length === 0) {
      toast.info("No changes to save");
      return;
    }
    setBusy(true);
    try {
      const row = editing
        ? await api<Row>(`/${meta.name}/${initial!.id}`, { method: "PATCH", body: payload })
        : await api<Row>(`/${meta.name}`, { method: "POST", body: payload });
      toast.success(editing ? "Changes saved" : `${meta.label} record created`);
      onSaved(row);
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  });

  const err = (n: string) => formState.errors[n]?.message as string | undefined;

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {fields.map((f) => {
          const wide = f.type === "text" || f.type === "json" || f.widget === "textarea";
          return (
            <Field key={f.name} label={f.label} required={!editing && f.required} error={err(f.name)} className={wide ? "sm:col-span-2" : undefined}>
              {f.type === "boolean" ? (
                <label className="flex h-9 items-center gap-2 text-sm text-slate-600">
                  <input type="checkbox" className="h-4 w-4 rounded border-slate-300" {...register(f.name)} /> Yes
                </label>
              ) : f.type === "enum" ? (
                <Select {...register(f.name)}>
                  <option value="">{f.required && !editing ? "Select…" : "—"}</option>
                  {f.enum?.map((o) => (
                    <option key={o} value={o}>{o.replace(/_/g, " ")}</option>
                  ))}
                </Select>
              ) : f.type === "ref" && f.ref ? (
                <Controller
                  control={control}
                  name={f.name}
                  render={({ field }) => (
                    <RefSelect
                      resource={f.ref!}
                      value={(field.value as string) || null}
                      initialLabel={initial?.display?.[f.name] ?? null}
                      onChange={(v) => field.onChange(v ?? "")}
                    />
                  )}
                />
              ) : f.type === "text" || f.type === "json" || f.widget === "textarea" ? (
                <Textarea rows={f.type === "json" ? 5 : 3} className={f.type === "json" ? "font-mono text-xs" : undefined} {...register(f.name)} />
              ) : (
                <Input
                  type={
                    f.type === "date" ? "date" : f.type === "datetime" ? "datetime-local" : f.widget === "time" ? "time"
                      : f.type === "integer" || f.type === "decimal" || f.type === "money" ? "number" : f.name.endsWith("email") ? "email" : "text"
                  }
                  step={f.type === "money" || f.type === "decimal" ? "0.01" : undefined}
                  maxLength={f.max_length ?? undefined}
                  {...register(f.name)}
                />
              )}
            </Field>
          );
        })}
      </div>
      {editing && (
        <Field label="Reason for change (recorded in audit log)">
          <Input {...register("change_reason")} placeholder="Optional for routine edits; recommended for sensitive changes" />
        </Field>
      )}
      <div className="flex justify-end gap-2 border-t border-slate-100 pt-4">
        {onCancel && (
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
        )}
        <Button type="submit" loading={busy}>{editing ? "Save changes" : "Create"}</Button>
      </div>
    </form>
  );
}
