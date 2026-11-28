"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, Eye } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, ErrorState, Field, Input, Modal, PageHeader, SimpleTable, Skeleton } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";
import type { Row } from "@/types";

interface Version {
  id: string; version_number: number; original_filename: string; mime_type: string; size_bytes: number; checksum_sha256: string;
  change_note: string | null; uploaded_by: string | null; created_at: string;
  comparison: { size_delta_bytes: number; content_changed: boolean; type_changed: boolean; filename_changed: boolean } | null;
}

export default function MaterialPage() {
  const { id } = useParams<{ id: string }>();
  const { me, can } = useSession();
  const m = useQuery({ queryKey: ["row", "materials", id], queryFn: () => api<Row>(`/materials/${id}`) });
  const v = useQuery({ queryKey: ["versions", id], queryFn: () => api<Version[]>(`/materials/${id}/versions`) });
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [preview, setPreview] = useState<{ url: string; mime: string } | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  if (m.isLoading) return <Skeleton className="h-64" />;
  if (m.isError || !m.data) return <ErrorState error={m.error} />;
  const r = m.data;
  const canEdit = can("materials.write") || (can("materials.write_own") && (r.created_by_id === me?.user.id || me?.batch_ids?.includes(String(r.batch_id))));

  const link = async (version?: number, show = false) => {
    try {
      const res = await api<{ url: string; mime_type: string }>(`/materials/${id}/download-link`, { query: { version } });
      if (show && (res.mime_type.startsWith("image/") || res.mime_type.startsWith("video/"))) {
        setPreview({ url: `${res.url}?inline=true`, mime: res.mime_type });
      } else window.open(res.url, "_blank", "noopener");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={<Link href="/materials" className="hover:underline">Study materials</Link>}
        title={String(r.title)}
        description={`${r.display?.subject_id ?? ""} ${r.display?.batch_id ? `· ${r.display.batch_id}` : ""} · ${String(r.category).replace("_", " ")} · v${r.current_version}`}
        actions={<>
          <Button size="sm" variant="outline" onClick={() => link(undefined, true)}><Eye className="h-4 w-4" /> Preview</Button>
          <Button size="sm" onClick={() => link()}><Download className="h-4 w-4" /> Download</Button>
          {canEdit && <Button size="sm" variant="outline" onClick={() => setOpen(true)}>Upload new version</Button>}
        </>}
      />
      {r.description ? <Card><p className="whitespace-pre-wrap text-sm text-slate-700">{String(r.description)}</p></Card> : null}
      <Card title="Version history" bodyClass="p-0">
        {v.data && (
          <SimpleTable
            headers={["Version", "File", "Size", "Uploaded by", "When", "Change note", "Compared to previous", ""]}
            rows={v.data.map((x) => [
              `v${x.version_number}`, x.original_filename, `${Math.ceil(x.size_bytes / 1024)} KB`, x.uploaded_by ?? "—", fmtDateTime(x.created_at, me?.institute?.timezone), x.change_note ?? "",
              x.comparison ? (
                <span key="c" className="flex flex-wrap gap-1">
                  {x.comparison.content_changed ? <Badge tone="indigo">content changed</Badge> : <Badge>identical content</Badge>}
                  {x.comparison.type_changed && <Badge tone="amber">type changed</Badge>}
                  <Badge>{x.comparison.size_delta_bytes >= 0 ? "+" : ""}{Math.round(x.comparison.size_delta_bytes / 1024)} KB</Badge>
                </span>
              ) : "Initial",
              <Button key="d" size="sm" variant="ghost" onClick={() => link(x.version_number)}><Download className="h-3.5 w-3.5" /></Button>,
            ])}
          />
        )}
      </Card>
      <Modal open={open} onOpenChange={setOpen} title="Upload new version" description="Previous versions are kept unchanged."
        footer={<Button loading={busy} onClick={async () => {
          const fl = file.current?.files?.[0];
          if (!fl) return toast.error("Choose a file");
          const form = new FormData();
          form.append("file", fl);
          if (note) form.append("change_note", note);
          setBusy(true);
          try { await api(`/materials/${id}/versions`, { method: "POST", form }); toast.success("New version uploaded"); setOpen(false); m.refetch(); v.refetch(); }
          catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
        }}>Upload</Button>}>
        <div className="space-y-3">
          <Field label="File"><input ref={file} type="file" className="text-sm" /></Field>
          <Field label="Change note"><Input value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        </div>
      </Modal>
      <Modal open={!!preview} onOpenChange={() => setPreview(null)} title="Preview" wide>
        {preview && (preview.mime.startsWith("image/") ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview.url} alt="Preview" className="mx-auto max-h-[70vh]" />
        ) : (
          <video src={preview.url} controls className="w-full" />
        ))}
      </Modal>
    </div>
  );
}
