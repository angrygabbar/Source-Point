"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { Button, Card, ErrorState, PageHeader, Skeleton, StatusBadge } from "@/components/ui";
import { openSignedLink } from "@/lib/api";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const q = useQuery({ queryKey: ["job", id], queryFn: () => api<any>(`/jobs/${id}/status`), refetchInterval: (query) => (["queued", "running"].includes(query.state.data?.status) ? 3000 : false) });
  if (q.isLoading) return <Skeleton className="h-40" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} />;
  const j = q.data;
  return (
    <>
      <PageHeader title={`Background job · ${j.job_type}`} description={`Created ${fmtDateTime(j.created_at)}`} />
      <Card>
        <p className="flex items-center gap-2 text-sm">Status: <StatusBadge value={j.status} /> {j.progress}%</p>
        {j.error && <p className="mt-2 text-sm text-red-600">Error: {j.error}</p>}
        {j.result && <pre className="mt-3 overflow-x-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(j.result, null, 2)}</pre>}
        {j.has_file && <Button className="mt-3" onClick={() => openSignedLink(`/jobs/${id}/download-link`)}>Download file</Button>}
      </Card>
    </>
  );
}
