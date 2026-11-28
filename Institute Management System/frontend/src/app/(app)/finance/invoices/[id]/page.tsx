"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button, Card, ConfirmDialog, ErrorState, Field, Input, Modal, PageHeader, SimpleTable, Skeleton, StatusBadge } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage, openFile } from "@/lib/api";
import { fmtDate, fmtMoney } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
declare global {
  interface Window { Razorpay?: new (opts: Record<string, unknown>) => { open: () => void } }
}

function loadRazorpay(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

export default function InvoicePage() {
  const { id } = useParams<{ id: string }>();
  const { me, can } = useSession();
  const cur = me?.institute?.currency ?? "INR";
  const q = useQuery({ queryKey: ["invoice", id], queryFn: () => api<any>(`/invoices/${id}/detail`) });
  const [dlg, setDlg] = useState<null | "credit" | "cancel">(null);
  const [credit, setCredit] = useState({ amount: "", reason: "" });
  const [paying, setPaying] = useState(false);
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.isError || !q.data) return <ErrorState error={q.error} />;
  const { invoice: inv, student, items, allocations, credit_notes } = q.data;
  const open = ["issued", "partially_paid", "overdue"].includes(inv.status);

  const payOnline = async () => {
    setPaying(true);
    try {
      const order = await api<any>("/payments/online/order", { method: "POST", body: { invoice_id: id } });
      if (!(await loadRazorpay()) || !window.Razorpay) throw new Error("Payment gateway script could not be loaded");
      const rz = new window.Razorpay({
        key: order.key_id, order_id: order.order_id, amount: order.amount, currency: order.currency, name: me?.institute?.name,
        description: `Invoice ${order.invoice_number}`, prefill: { name: order.student_name },
        handler: async (resp: Record<string, string>) => {
          try {
            const r = await api<{ receipt_number: string }>("/payments/online/verify", { method: "POST", body: { invoice_id: id, ...resp } });
            toast.success(`Payment confirmed by gateway: ${r.receipt_number}`);
            q.refetch();
          } catch (e) {
            toast.error(`Verification pending: ${errorMessage(e)}. The payment will be reconciled from the gateway webhook if captured.`);
          }
        },
      });
      rz.open();
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setPaying(false);
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={<Link href="/r/invoices" className="hover:underline">Invoices</Link>}
        title={<span className="flex items-center gap-2">{inv.invoice_number ?? "Draft invoice"} <StatusBadge value={inv.status} /></span>}
        description={<>{student.full_name} ({student.student_code}) · issued {fmtDate(inv.issue_date)} · due {fmtDate(inv.due_date)}</>}
        actions={<>
          <Button size="sm" variant="outline" onClick={() => openFile(`/invoices/${id}/pdf`)}>PDF</Button>
          {inv.status === "draft" && can("invoices.write") && <Button size="sm" onClick={async () => { try { await api(`/invoices/${id}/issue`, { method: "POST" }); toast.success("Issued"); q.refetch(); } catch (e) { toast.error(errorMessage(e)); } }}>Issue</Button>}
          {open && can("payments.write") && <Link href={`/finance/collect?student=${student.id}`}><Button size="sm">Record payment</Button></Link>}
          {open && q.data.online_payment_available && <Button size="sm" variant="accent" loading={paying} onClick={payOnline}>Pay online</Button>}
          {open && can("invoices.adjust") && <Button size="sm" variant="outline" onClick={() => setDlg("credit")}>Credit note</Button>}
          {inv.status !== "cancelled" && can("invoices.cancel") && Number(inv.amount_paid) === 0 && Number(inv.credit_applied) === 0 && <Button size="sm" variant="danger" onClick={() => setDlg("cancel")}>Cancel</Button>}
        </>}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Line items" bodyClass="p-0" className="lg:col-span-2">
          <SimpleTable headers={["Description", "Qty", "Rate", "Discount", "Tax", "Amount"]}
            rows={items.map((i: any) => [i.description, i.quantity, fmtMoney(i.unit_price, cur), fmtMoney(i.discount, cur), `${i.tax_rate}% · ${fmtMoney(i.tax_amount, cur)}`, fmtMoney(i.amount, cur)])} />
        </Card>
        <Card title="Summary">
          <dl className="space-y-1.5 text-sm">
            {[["Subtotal", inv.subtotal], ["Discounts", inv.discount_total], ["Tax", inv.tax_total], ["Total", inv.total], ["Paid", inv.amount_paid], ["Credits", inv.credit_applied]].map(([k, v]) => (
              <div key={k} className="flex justify-between"><dt className="text-slate-500">{k}</dt><dd>{fmtMoney(v, cur)}</dd></div>
            ))}
            <div className="flex justify-between border-t pt-2 text-base font-semibold"><dt>Balance due</dt><dd>{fmtMoney(inv.balance_due, cur)}</dd></div>
          </dl>
          {inv.cancellation_reason && <p className="mt-3 text-sm text-red-700">Cancelled: {inv.cancellation_reason}</p>}
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Payments applied" bodyClass="p-0">
          <SimpleTable headers={["Receipt", "Date", "Amount", ""]} empty="No payments applied"
            rows={allocations.map((a: any) => [a.receipt_number, fmtDate(a.paid_at), fmtMoney(a.amount, cur), a.is_reversed ? <StatusBadge key="r" value="reversed" /> : <Button key="p" size="sm" variant="ghost" onClick={() => openFile(`/payments/${a.payment_id}/receipt.pdf`)}>Receipt</Button>])} />
        </Card>
        <Card title="Credit notes" bodyClass="p-0">
          <SimpleTable headers={["Number", "Amount", "Reason", "Date"]} empty="No credit notes"
            rows={credit_notes.map((c: any) => [c.credit_note_number, fmtMoney(c.amount, cur), c.reason, fmtDate(c.created_at)])} />
        </Card>
      </div>
      <Modal open={dlg === "credit"} onOpenChange={() => setDlg(null)} title="Issue credit note" description="Reduces the invoice balance. Over-payments are released to the student's advance balance."
        footer={<Button disabled={!(Number(credit.amount) > 0) || credit.reason.length < 3} onClick={async () => { try { await api(`/invoices/${id}/credit-note`, { method: "POST", body: credit }); toast.success("Credit note issued"); setDlg(null); q.refetch(); } catch (e) { toast.error(errorMessage(e)); } }}>Issue</Button>}>
        <div className="space-y-3">
          <Field label="Amount" required><Input type="number" step="0.01" value={credit.amount} onChange={(e) => setCredit({ ...credit, amount: e.target.value })} /></Field>
          <Field label="Reason" required><Input value={credit.reason} onChange={(e) => setCredit({ ...credit, reason: e.target.value })} /></Field>
        </div>
      </Modal>
      <ConfirmDialog open={dlg === "cancel"} onOpenChange={() => setDlg(null)} title="Cancel invoice" danger requireReason confirmLabel="Cancel invoice"
        message="Posted invoices are never deleted; a cancellation entry is added to the ledger."
        onConfirm={async (reason) => { try { await api(`/invoices/${id}/cancel`, { method: "POST", body: { reason } }); toast.success("Cancelled"); q.refetch(); } catch (e) { toast.error(errorMessage(e)); } }} />
    </div>
  );
}
