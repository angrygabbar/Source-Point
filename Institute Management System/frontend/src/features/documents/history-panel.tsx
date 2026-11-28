"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, EmptyState } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";

interface Entry { id: string; action: string; actor_email: string | null; old_values: Record<string, unknown>; new_values: Record<string, unknown>; reason: string | null; created_at: string }

export function HistoryPanel({ resource, id }: { resource: string; id: string }) {
  const { me } = useSession();
  const q = useQuery({ queryKey: ["history", resource, id], queryFn: () => api<Entry[]>(`/${resource}/${id}/history`) });
  return (
    <Card title="Activity & audit history">
      {!q.data?.length ? <EmptyState title="No recorded changes" /> : (
        <ol className="relative space-y-4 border-l border-slate-200 pl-5">
          {q.data.map((e) => (
            <li key={e.id} className="text-sm">
              <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white bg-brand-800" />
              <p className="font-medium text-slate-800">{e.action.replace(/_/g, " ")} <span className="font-normal text-slate-500">by {e.actor_email ?? "system"} · {fmtDateTime(e.created_at, me?.institute?.timezone)}</span></p>
              {e.reason && <p className="text-xs text-amber-700">Reason: {e.reason}</p>}
              {Object.keys(e.new_values ?? {}).length > 0 && (
                <div className="mt-1 space-y-0.5 text-xs text-slate-500">
                  {Object.entries(e.new_values).slice(0, 12).map(([k, v]) => (
                    <p key={k}><span className="font-medium text-slate-600">{k.replace(/_/g, " ")}</span>: {e.old_values?.[k] !== undefined && <><span className="line-through">{String(e.old_values[k] ?? "—")}</span> → </>}{String(v ?? "—")}</p>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
