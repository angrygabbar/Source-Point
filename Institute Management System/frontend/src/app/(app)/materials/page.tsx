"use client";

import { Camera, Upload } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button, Field, Input, Modal, PageHeader, Select, Textarea } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { ResourceList } from "@/components/data/resource-list";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage } from "@/lib/api";

const CATEGORIES = ["notes", "assignment", "question_paper", "answer_key", "reference", "student_submission", "other"];

function MaterialsInner() {
  const params = useSearchParams();
  const { can } = useSession();
  const qc = useQueryClient();
  const [open, setOpen] = useState(!!params.get("session"));
  const [f, setF] = useState<Record<string, string>>({
    category: "notes", visibility: "batch", batch_id: params.get("batch") ?? "", subject_id: params.get("subject") ?? "", session_id: params.get("session") ?? "",
  });
  const files = useRef<HTMLInputElement>(null);
  const camera = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const canUpload = can("materials.write", "materials.write_own");

  const upload = async () => {
    const list = [...Array.from(files.current?.files ?? []), ...Array.from(camera.current?.files ?? [])];
    if (!list.length) return toast.error("Choose at least one file");
    const form = new FormData();
    Object.entries(f).forEach(([k, v]) => v && form.append(k, v));
    list.forEach((file) => form.append("files", file));
    setBusy(true);
    try {
      const r = await api<{ ids: string[] }>("/materials/upload", { method: "POST", form });
      toast.success(`${r.ids.length} file(s) uploaded`);
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["list", "materials"] });
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Study materials" description="Versioned repository organised by academic year, course, batch, subject and category." />
      <ResourceList resource="materials" toolbar={canUpload && <Button size="sm" onClick={() => setOpen(true)}><Upload className="h-4 w-4" /> Upload</Button>} />
      <Modal open={open} onOpenChange={setOpen} title="Upload study material" wide
        footer={<><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={busy} disabled={!f.title} onClick={upload}>Upload</Button></>}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Title" required className="sm:col-span-2"><Input value={f.title ?? ""} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
          <Field label="Category"><Select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{CATEGORIES.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}</Select></Field>
          <Field label="Visibility"><Select value={f.visibility} onChange={(e) => setF({ ...f, visibility: e.target.value })}>
            <option value="batch">Students of the batch</option><option value="institute">Whole institute</option><option value="selected">Selected (via access grants)</option><option value="staff_only">Staff only</option>
          </Select></Field>
          <Field label="Batch"><RefSelect resource="batches" value={f.batch_id || null} onChange={(v) => setF({ ...f, batch_id: v ?? "" })} /></Field>
          <Field label="Subject"><RefSelect resource="subjects" value={f.subject_id || null} onChange={(v) => setF({ ...f, subject_id: v ?? "" })} /></Field>
          <Field label="Syllabus chapter"><RefSelect resource="syllabus-chapters" filters={f.subject_id ? { subject_id: f.subject_id } : undefined} value={f.syllabus_chapter_id || null} onChange={(v) => setF({ ...f, syllabus_chapter_id: v ?? "" })} /></Field>
          <Field label="Tags"><Input value={f.tags ?? ""} onChange={(e) => setF({ ...f, tags: e.target.value })} placeholder="comma separated" /></Field>
          <Field label="Description" className="sm:col-span-2"><Textarea value={f.description ?? ""} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
          <Field label="Files" hint="Up to 20 files. Executables and scripts are blocked." className="sm:col-span-2">
            <input ref={files} type="file" multiple className="text-sm" />
          </Field>
          <Field label="Capture with camera (mobile)" className="sm:col-span-2">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700">
              <Camera className="h-4 w-4" /> Take photo
              <input ref={camera} type="file" accept="image/*" capture="environment" className="hidden" />
            </label>
          </Field>
        </div>
      </Modal>
    </>
  );
}

export default function MaterialsPage() {
  return <Suspense><MaterialsInner /></Suspense>;
}
