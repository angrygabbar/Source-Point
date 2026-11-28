"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Badge, Button, Card, ErrorState, PageHeader, SimpleTable, Skeleton, StatCard } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api } from "@/lib/api";
import { fmtDate, fmtMoney } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function LedgerPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const { me, can } = useSession();
  const cur = me?.institute?.currency ?? "INR";
  const q = useQuery({ queryKey: ["ledger", studentId], queryFn: () => api<any>(`/students/${studentId}/ledger`) });
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} />;
  const { student, summary, entries } = q.data;
  return (
    <div className="space-y-4">
      <PageHeader title={`Ledger · ${student.full_name}`} description={student.student_code}
        breadcrumbs={<Link href={`/students/${studentId}`} className="hover:underline">Student profile</Link>}
        actions={can("payments.write") && <Link href={`/finance/collect?student=${studentId}`}><Button size="sm">Collect payment</Button></Link>} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Total charged" value={fmtMoney(summary.total_debits, cur)} />
        <StatCard label="Total credited" value={fmtMoney(summary.total_credits, cur)} tone="green" />
        <StatCard label="Outstanding" value={fmtMoney(summary.outstanding, cur)} tone="red" />
        <StatCard label="Advance" value={fmtMoney(summary.advance, cur)} tone="teal" />
      </div>
      <Card title="Entries (immutable)" bodyClass="p-0">
        <SimpleTable headers={["Date", "Type", "Description", "Debit", "Credit", "Running balance"]} empty="No ledger entries"
          rows={entries.map((e: any) => [fmtDate(e.entry_date), <Badge key="t">{e.entry_type.replace("_", " ")}</Badge>, e.description,
            Number(e.debit) ? fmtMoney(e.debit, cur) : "", Number(e.credit) ? fmtMoney(e.credit, cur) : "", fmtMoney(e.balance, cur)])} />
      </Card>
    </div>
  );
}
