"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";
import { Button, Card, Field, Input, PageHeader, Select } from "@/components/ui";
import { RefSelect } from "@/components/data/ref-select";
import { useSession } from "@/hooks/use-session";
import { api, errorMessage } from "@/lib/api";
import { addDaysISO, fmtMoney, todayISO } from "@/lib/utils";

interface Item { description: string; item_type: string; quantity: string; unit_price: string; discount: string; tax_rate: string }
const blank = (): Item => ({ description: "", item_type: "tuition", quantity: "1", unit_price: "", discount: "0", tax_rate: "" });

function NewInvoice() {
  const params = useSearchParams();
  const router = useRouter();
  const { me } = useSession();
  const inst = useQuery({ queryKey: ["institute"], queryFn: () => api<{ tax_enabled: boolean; tax_rate: string; tax_label: string; currency: string }>("/institutes/current") });
  const cur = me?.institute?.currency ?? "INR";
  const [student, setStudent] = useState<string | null>(params.get("student"));
  const [issue, setIssue] = useState(todayISO());
  const [due, setDue] = useState(addDaysISO(todayISO(), 10));
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<Item[]>([blank()]);
  const [busy, setBusy] = useState(false);
  const taxOn = !!inst.data?.tax_enabled;
  const line = (i: Item) => {
    const gross = Number(i.quantity || 0) * Number(i.unit_price || 0);
    const taxable = Math.max(gross - Number(i.discount || 0), 0);
    const rate = taxOn ? Number(i.tax_rate === "" ? inst.data?.tax_rate ?? 0 : i.tax_rate) : 0;
    return taxable + (taxable * rate) / 100;
  };
  const total = items.reduce((s, i) => s + line(i), 0);

  const save = async (post: boolean) => {
    setBusy(true);
    try {
      const r = await api<{ id: string }>("/invoices", {
        method: "POST",
        body: {
          student_id: student, issue_date: issue, due_date: due, notes: notes || null, post,
          items: items.map((i) => ({ description: i.description, item_type: i.item_type, quantity: i.quantity, unit_price: i.unit_price, discount: i.discount || "0", tax_rate: i.tax_rate === "" ? null : i.tax_rate })),
        },
      });
      toast.success(post ? "Invoice issued" : "Draft saved");
      router.push(`/finance/invoices/${r.id}`);
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const set = (idx: number, patch: Partial<Item>) => setItems(items.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  const valid = student && items.every((i) => i.description.length >= 2 && Number(i.unit_price) >= 0 && i.unit_price !== "");

  return (
    <>
      <PageHeader title="New invoice" description={taxOn ? `${inst.data?.tax_label} at ${inst.data?.tax_rate}% applies by default (configurable per line).` : "Tax is disabled in institute settings."} />
      <Card>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Student" required><RefSelect resource="students" value={student} onChange={setStudent} /></Field>
          <Field label="Issue date"><Input type="date" value={issue} onChange={(e) => setIssue(e.target.value)} /></Field>
          <Field label="Due date"><Input type="date" value={due} min={issue} onChange={(e) => setDue(e.target.value)} /></Field>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead><tr className="text-left text-xs text-slate-500"><th className="py-2">Description</th><th>Type</th><th>Qty</th><th>Rate</th><th>Discount</th>{taxOn && <th>Tax %</th>}<th className="text-right">Amount</th><th /></tr></thead>
            <tbody>
              {items.map((it, idx) => (
                <tr key={idx} className="align-top">
                  <td className="py-1 pr-2"><Input value={it.description} onChange={(e) => set(idx, { description: e.target.value })} /></td>
                  <td className="pr-2"><Select value={it.item_type} onChange={(e) => set(idx, { item_type: e.target.value })}>{["tuition", "admission", "exam", "material", "lab", "transport", "late_fee", "other"].map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}</Select></td>
                  <td className="w-20 pr-2"><Input type="number" min="0.01" step="0.01" value={it.quantity} onChange={(e) => set(idx, { quantity: e.target.value })} /></td>
                  <td className="w-28 pr-2"><Input type="number" min="0" step="0.01" value={it.unit_price} onChange={(e) => set(idx, { unit_price: e.target.value })} /></td>
                  <td className="w-28 pr-2"><Input type="number" min="0" step="0.01" value={it.discount} onChange={(e) => set(idx, { discount: e.target.value })} /></td>
                  {taxOn && <td className="w-20 pr-2"><Input type="number" min="0" max="100" step="0.01" placeholder={inst.data?.tax_rate} value={it.tax_rate} onChange={(e) => set(idx, { tax_rate: e.target.value })} /></td>}
                  <td className="py-2 text-right font-medium">{fmtMoney(line(it), cur)}</td>
                  <td className="pl-2"><Button variant="ghost" size="icon" disabled={items.length === 1} onClick={() => setItems(items.filter((_, i) => i !== idx))} aria-label="Remove line"><Trash2 className="h-4 w-4" /></Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-2 flex items-center justify-between">
          <Button variant="outline" size="sm" onClick={() => setItems([...items, blank()])}><Plus className="h-4 w-4" /> Add line</Button>
          <p className="text-lg font-semibold">Total {fmtMoney(total, cur)}</p>
        </div>
        <Field label="Notes" className="mt-4"><Input value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" loading={busy} disabled={!valid} onClick={() => save(false)}>Save draft</Button>
          <Button loading={busy} disabled={!valid} onClick={() => save(true)}>Issue invoice</Button>
        </div>
      </Card>
    </>
  );
}

export default function NewInvoicePage() {
  return <Suspense><NewInvoice /></Suspense>;
}
