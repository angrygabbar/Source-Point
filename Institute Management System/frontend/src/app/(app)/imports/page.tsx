"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, Field, PageHeader, Select, SimpleTable } from "@/components/ui";
import { api, errorMessage, openFile } from "@/lib/api";

/* eslint-disable @typescript-eslint/no-explicit-any */
const ENTITIES = ["students", "teachers", "courses", "subjects", "batches", "enrollments", "attendance"];

export default function ImportsPage() {
  const [entity, setEntity] = useState("students");
  const file = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const cols = preview?.rows?.[0] ? Object.keys(preview.rows[0].data) : [];
  return (
    <>
      <PageHeader title="Import & export" description="Upload CSV or Excel, preview row-level validation, then commit. Duplicates are rejected. Every list also has CSV/Excel/PDF export." />
      <Card title="1 · Choose type and template">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Import type"><Select value={entity} onChange={(e) => { setEntity(e.target.value); setPreview(null); setResult(null); }}>{ENTITIES.map((x) => <option key={x}>{x}</option>)}</Select></Field>
          <Button variant="outline" onClick={() => openFile(`/imports/templates/${entity}`, { download: true })}>Download template</Button>
          <Field label="File (.csv / .xlsx)"><input ref={file} type="file" accept=".csv,.xlsx" className="text-sm" /></Field>
          <Button loading={busy} onClick={async () => {
            const f = file.current?.files?.[0];
            if (!f) return toast.error("Choose a file");
            const form = new FormData();
            form.append("file", f);
            setBusy(true);
            setResult(null);
            try { setPreview(await api(`/imports/${entity}/preview`, { method: "POST", form })); } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
          }}>2 · Validate & preview</Button>
        </div>
        <p className="mt-2 text-xs text-slate-500">Dates: DD-MM-YYYY or YYYY-MM-DD. References use codes (branch_code, batch_code, course_code, student_code). Historical attendance needs an existing class session for the batch/subject/date.</p>
      </Card>
      {preview && (
        <Card className="mt-4" title={<span className="flex items-center gap-2">Preview <Badge tone="green">{preview.valid} valid</Badge> <Badge tone={preview.invalid ? "red" : "slate"}>{preview.invalid} with errors</Badge></span>}
          actions={<Button disabled={!preview.valid || busy} loading={busy} onClick={async () => {
            setBusy(true);
            try { const r = await api<any>(`/imports/${preview.job_id}/commit`, { method: "POST" }); setResult(r); setPreview(null); toast.success(`${r.created} record(s) imported`); } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
          }}>3 · Import {preview.valid} valid rows</Button>} bodyClass="p-0">
          <SimpleTable headers={["Row", "Errors", ...cols]} rows={preview.rows.map((r: any) => [r.row, r.errors.length ? <span key="e" className="text-xs text-red-600">{r.errors.join("; ")}</span> : <Badge key="ok" tone="green">ok</Badge>, ...cols.map((c) => String(r.data[c] ?? ""))])} />
        </Card>
      )}
      {result && (
        <Card className="mt-4" title="Import result">
          <p className="text-sm">Created {result.created}, skipped {result.skipped}.</p>
          {result.errors?.length > 0 && <SimpleTable headers={["Row", "Errors"]} rows={result.errors.map((e: any) => [e.row, e.errors.join("; ")])} />}
        </Card>
      )}
    </>
  );
}
