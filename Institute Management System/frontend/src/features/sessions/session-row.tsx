"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { StatusBadge } from "@/components/ui";
import { fmtDate, fmtTime } from "@/lib/utils";

export interface SessionItem {
  id: string;
  session_date: string;
  start: string;
  end: string;
  status: string;
  session_type: string;
  batch?: string | null;
  subject?: string | null;
  teacher?: string | null;
  classroom?: string | null;
  attendance_state: string;
  substitutes: { id: string; name: string | null }[];
}

export function SessionRow({ s, tz, showDate, extra }: { s: SessionItem; tz?: string; showDate?: boolean; extra?: ReactNode }) {
  return (
    <Link href={`/sessions/${s.id}`} className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-slate-50">
      <div className="w-20 shrink-0 text-xs font-medium text-slate-600">
        {showDate && <div className="text-[11px] text-slate-400">{fmtDate(s.session_date)}</div>}
        {fmtTime(s.start, tz)}–{fmtTime(s.end, tz)}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-800">
          {s.subject} · {s.batch}
        </p>
        <p className="truncate text-xs text-slate-500">
          {s.teacher}
          {s.substitutes.length > 0 && ` → substitute: ${s.substitutes.map((x) => x.name).join(", ")}`}
          {s.classroom && ` · ${s.classroom}`}
          {s.session_type !== "regular" && ` · ${s.session_type}`}
        </p>
      </div>
      {extra}
      <StatusBadge value={s.status} />
    </Link>
  );
}
