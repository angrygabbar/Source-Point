"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button, Card, EmptyState, Field, Input, PageHeader, Select, SimpleTable, Textarea } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, openFile } from "@/lib/api";
import { fmtDate, fmtMoney, uuid } from "@/lib/utils";

interface OpenInvoice { id: string; invoice_number: string; issue_date: string; due_date: string; total: string; balance_due: string; status: string }

function Collect() {
  const params = useSearchParams();
  const { me } = useSession();
  const cur = me?.institute?.currency ?? "INR";
  const [student, setStudent] = useState<string | null>(params.get("student"));
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("cash");
  const [ref, setRef] = useState("");
  const [chequeDate, setChequeDate] = useState("");
  const [bank, setBank] = useState("");
  const [notes, setNotes] = useState("");
  const [manual, setManual] = useState(false);
  const [alloc, setAlloc] = useState<Record<string, string>>({});
  const [key, setKey] = useState(uuid());
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState<{ id: string; receipt_number: string; unallocated_amount: string } | null>(null);

  const inv = useQuery({ queryKey: ["open-invoices", student], queryFn: () => api<OpenInvoice[]>(`/students/${student}/open-invoices`), enabled: !!student });
  const totalDue = useMemo(() => (inv.data ?? []).reduce((s, i) => s + Number(i.balance_due), 0), [inv.data]);
  useEffect(() => { setAlloc({}); setReceipt(null); setKey(uuid()); }, [student]);

  const submit = async () => {
    setBusy(true);
    try {
      const allocations = manual ? Object.entries(alloc).filter(([, v]) => Number(v) > 0).map(([invoice_id, a]) => ({ invoice_id, amount: a })) : undefined;
      const r = await api<{ id: string; receipt_number: string; unallocated_amount: string; replayed: boolean }>("/payments", {
        method: "POST",
        headers: { "Idempotency-Key": key },
        body: { student_id: student, amount, method, reference_number: ref || null, cheque_date: chequeDate || null, bank_name: bank || null, notes: notes || null, allocations },
      });
      setReceipt(r);
      toast.success(r.replayed ? "Payment already recorded (duplicate submission prevented)" : `Payment recorded: ${r.receipt_number}`);
      setKey(uuid());
      setAmount("");
      setRef("");
      inv.refetch();
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Collect payment" description="Record cash, UPI, bank transfer or cheque payments. Never record UPI PINs or bank passwords." />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Payment" className="lg:col-span-1">
          <div className="space-y-3">
            <Field label="Student" required><RefSelect resource="students" value={student} onChange={setStudent} /></Field>
            <Field label="Amount" required hint={student ? `Outstanding ${fmtMoney(totalDue, cur)}` : undefined}><Input type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
            <Field label="Method"><Select value={method} onChange={(e) => setMethod(e.target.value)}>{["cash", "upi", "bank_transfer", "cheque", "card"].map((m) => <option key={m} value={m}>{m.replace("_", " ")}</option>)}</Select></Field>
            {method !== "cash" && <Field label={method === "cheque" ? "Cheque number" : "Transaction reference / UTR"} required><Input value={ref} onChange={(e) => setRef(e.target.value)} /></Field>}
            {method === "cheque" && <div className="grid grid-cols-2 gap-2"><Field label="Cheque date"><Input type="date" value={chequeDate} onChange={(e) => setChequeDate(e.target.value)} /></Field><Field label="Bank"><Input value={bank} onChange={(e) => setBank(e.target.value)} /></Field></div>}
            <Field label="Notes"><Textarea value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={manual} onChange={(e) => setManual(e.target.checked)} /> Allocate manually (default: oldest dues first; excess kept as advance)</label>
            <Button className="w-full" loading={busy} disabled={!student || !(Number(amount) > 0) || (method !== "cash" && !ref)} onClick={submit}>Record payment</Button>
          </div>
        </Card>
        <div className="space-y-4 lg:col-span-2">
          {receipt && (
            <Card className="border-emerald-200 bg-emerald-50">
              <p className="text-sm text-emerald-800">Receipt <b>{receipt.receipt_number}</b> created. {Number(receipt.unallocated_amount) > 0 && `Advance kept: ${fmtMoney(receipt.unallocated_amount, cur)}.`}</p>
              <Button size="sm" className="mt-2" onClick={() => openFile(`/payments/${receipt.id}/receipt.pdf`)}>Print receipt</Button>
            </Card>
          )}
          <Card title="Open invoices" bodyClass="p-0" actions={student && <Link href={`/finance/ledger/${student}`} className="text-xs font-medium text-brand-800">Ledger</Link>}>
            {!student ? <EmptyState title="Select a student" /> : (
              <SimpleTable headers={["Invoice", "Issued", "Due", "Total", "Balance", manual ? "Allocate" : ""]} empty="No open invoices — payment will be kept as advance"
                rows={(inv.data ?? []).map((i) => [
                  <Link key="i" className="text-brand-800 hover:underline" href={`/finance/invoices/${i.id}`}>{i.invoice_number}</Link>, fmtDate(i.issue_date), fmtDate(i.due_date),
                  fmtMoney(i.total, cur), fmtMoney(i.balance_due, cur),
                  manual ? <Input key="a" type="number" step="0.01" className="h-8 w-28" max={i.balance_due} value={alloc[i.id] ?? ""} onChange={(e) => setAlloc({ ...alloc, [i.id]: e.target.value })} /> : "",
                ])} />
            )}
          </Card>
        </div>
      </div>
    </>
  );
}

export default function CollectPage() {
  return <Suspense><Collect /></Suspense>;
}
