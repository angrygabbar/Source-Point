"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button, Field, Input, Modal, PageHeader, Textarea } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { ResourceList } from "@/components/data/resource-list";
import { api, errorMessage } from "@/lib/api";

export default function DiscussionsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [f, setF] = useState<{ title: string; body: string; batch_id: string | null; subject_id: string | null; is_doubt: boolean }>({ title: "", body: "", batch_id: null, subject_id: null, is_doubt: true });
  return (
    <>
      <PageHeader title="Discussions & doubt solving" description="Batch discussion boards. Teacher replies to doubts are highlighted; posts can be reported for moderation." />
      <ResourceList resource="discussion-threads" toolbar={<Button size="sm" onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> New thread</Button>} />
      <Modal open={open} onOpenChange={setOpen} title="Start a discussion"
        footer={<Button disabled={f.title.length < 3 || !f.body} onClick={async () => {
          try { const r = await api<{ id: string }>("/discussions", { method: "POST", body: f }); qc.invalidateQueries({ queryKey: ["list", "discussion-threads"] }); router.push(`/discussions/${r.id}`); } catch (e) { toast.error(errorMessage(e)); }
        }}>Post</Button>}>
        <div className="space-y-3">
          <Field label="Title" required><Input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Batch"><RefSelect resource="batches" value={f.batch_id} onChange={(v) => setF({ ...f, batch_id: v })} /></Field>
            <Field label="Subject"><RefSelect resource="subjects" value={f.subject_id} onChange={(v) => setF({ ...f, subject_id: v })} /></Field>
          </div>
          <Field label="Message" required><Textarea rows={5} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} /></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_doubt} onChange={(e) => setF({ ...f, is_doubt: e.target.checked })} /> This is a doubt for a teacher</label>
        </div>
      </Modal>
    </>
  );
}
