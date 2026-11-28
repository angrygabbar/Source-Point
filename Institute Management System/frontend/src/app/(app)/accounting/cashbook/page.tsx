"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Card, ErrorState, Field, Input, PageHeader, Select, SimpleTable, Skeleton, StatCard } from "@/components/ui";
import { ResourceList } from "@/components/data/resource-list";
import { useSession } from "@/hooks/use-session";
import { api } from "@/lib/api";
import { addDaysISO, fmtDate, fmtMoney, todayISO } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function CashbookPage() {
  const { me } = useSession();
  const cur = me?.institute?.currency ?? "INR";
  const [account, setAccount] = useState("cash");
  const [start, setStart] = useState(addDaysISO(todayISO(), -30));
  const [end, setEnd] = useState(todayISO());
  const q = useQuery({ queryKey: ["cashbook", account, start, end], queryFn: () => api<any>("/accounting/cashbook", { query: { account, start, end } }) });
  return (
    <>
      <PageHeader title="Cashbook & petty cash" description="Running balances computed from recorded entries."
        actions={<>
          <Select className="w-36" value={account} onChange={(e) => setAccount(e.target.value)}><option value="cash">Cash</option><option value="petty_cash">Petty cash</option><option value="bank">Bank</option></Select>
          <Field label=""><Input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></Field>
          <Field label=""><Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></Field>
        </>} />
      {q.isLoading ? <Skeleton className="h-40" /> : q.isError ? <ErrorState error={q.error} /> : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3"><StatCard label="Opening balance" value={fmtMoney(q.data.opening_balance, cur)} /><StatCard label="Closing balance" value={fmtMoney(q.data.closing_balance, cur)} tone="green" /></div>
          <Card bodyClass="p-0"><SimpleTable headers={["Date", "Description", "In", "Out", "Balance"]} empty="No entries in this period"
            rows={q.data.entries.map((e: any) => [fmtDate(e.entry_date), e.description, e.direction === "in" ? fmtMoney(e.amount, cur) : "", e.direction === "out" ? fmtMoney(e.amount, cur) : "", fmtMoney(e.balance, cur)])} /></Card>
        </div>
      )}
      <div className="mt-4"><ResourceList resource="cashbook-entries" title="Record cash / petty cash entries" createDefaults={{ account, entry_date: todayISO() }} compact /></div>
    </>
  );
}
