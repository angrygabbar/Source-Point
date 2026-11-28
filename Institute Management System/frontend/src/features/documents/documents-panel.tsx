"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, History, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Button, Card, EmptyState, Field, Input, Modal, SimpleTable } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, openSignedLink } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

interface Doc { id: string; title: string; category: string; original_filename: string; size_bytes: number; version_number: number; is_archived: boolean; created_at: string }

export function DocumentsPanel({ ownerType, ownerId, title = "Documents" }: { ownerType: string; ownerId: string; title?: string }) {
  const { can } = useSession();
  const [history, setHistory] = useState(false);
  const q = useQuery({ queryKey: ["docs", ownerType, ownerId, history], queryFn: () => api<Doc[]>(`/documents/by-owner/${ownerType}/${ownerId}`, { query: { include_history: history } }) });
  const [open, setOpen] = useState(false);
  const [versionFor, setVersionFor] = useState<Doc | null>(null);
  const [category, setCategory] = useState("other");
  const [docTitle, setDocTitle] = useState("");
  const [sensitive, setSensitive] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const canWrite = can("documents.write", "students.write", "teachers.write", "parents.write", "expenses.write", "admissions.write", "hr.write");

  const upload = async () => {
    const f = file.current?.files?.[0];
    if (!f) return toast.error("Choose a file");
    const form = new FormData();
    form.append("file", f);
    setBusy(true);
    try {
      if (versionFor) {
        await api(`/documents/${versionFor.id}/versions`, { method: "POST", form });
      } else {
        form.append("owner_type", ownerType);
        form.append("owner_id", ownerId);
        form.append("category", category);
        if (docTitle) form.append("title", docTitle);
        form.append("is_sensitive", String(sensitive));
        await api("/documents/upload", { method: "POST", form });
      }
      toast.success("Uploaded");
      setOpen(false);
      setVersionFor(null);
      q.refetch();
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card
      title={title}
      actions={
        <>
          <Button variant="ghost" size="sm" onClick={() => setHistory(!history)}><History className="h-3.5 w-3.5" /> {history ? "Current only" : "Show versions"}</Button>
          {canWrite && <Button size="sm" variant="outline" onClick={() => { setVersionFor(null); setOpen(true); }}><Upload className="h-3.5 w-3.5" /> Upload</Button>}
        </>
      }
      bodyClass="p-0"
    >
      {!q.data?.length ? <EmptyState title="No documents" /> : (
        <SimpleTable
          headers={["Title", "Category", "File", "Version", "Uploaded", ""]}
          rows={q.data.map((d) => [
            <span key="t" className={d.is_archived ? "text-slate-400 line-through" : ""}>{d.title}</span>,
            d.category,
            `${d.original_filename} (${Math.ceil(d.size_bytes / 1024)} KB)`,
            `v${d.version_number}`,
            fmtDate(d.created_at),
            <span key="a" className="flex gap-1">
              <Button size="sm" variant="ghost" onClick={() => openSignedLink(`/documents/${d.id}/download-link`).catch((e) => toast.error(errorMessage(e)))}><Download className="h-3.5 w-3.5" /></Button>
              {canWrite && !d.is_archived && <Button size="sm" variant="ghost" onClick={() => { setVersionFor(d); setOpen(true); }}>New version</Button>}
            </span>,
          ])}
        />
      )}
      <Modal open={open} onOpenChange={setOpen} title={versionFor ? `New version of ${versionFor.title}` : "Upload document"}
        footer={<><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button loading={busy} onClick={upload}>Upload</Button></>}>
        <div className="space-y-3">
          {!versionFor && (
            <>
              <Field label="Title"><Input value={docTitle} onChange={(e) => setDocTitle(e.target.value)} /></Field>
              <Field label="Category"><Input value={category} onChange={(e) => setCategory(e.target.value)} /></Field>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={sensitive} onChange={(e) => setSensitive(e.target.checked)} /> Restricted / sensitive</label>
            </>
          )}
          <Field label="File" hint="PDF, Office, images; max size set by administrator. Executables are blocked.">
            <input ref={file} type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg,.webp,.txt,.csv" capture={undefined} className="text-sm" />
          </Field>
        </div>
      </Modal>
    </Card>
  );
}
