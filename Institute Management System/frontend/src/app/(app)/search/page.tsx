"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Badge, Card, EmptyState, Input, PageHeader, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { detailHref } from "@/lib/nav";

interface Result { type: string; label: string; id: string; title: string; subtitle: string | null }

function Search() {
  const params = useSearchParams();
  const router = useRouter();
  const term = params.get("q") ?? "";
  const [q, setQ] = useState(term);
  const r = useQuery({ queryKey: ["search", term], queryFn: () => api<{ results: Result[] }>("/search", { query: { q: term } }), enabled: term.length >= 2 });
  const groups = (r.data?.results ?? []).reduce<Record<string, Result[]>>((a, x) => ((a[x.label] = [...(a[x.label] ?? []), x]), a), {});
  return (
    <>
      <PageHeader title="Search" description="Results are limited to records you are permitted to see. Search sessions by date as DD-MM-YYYY." />
      <form onSubmit={(e) => { e.preventDefault(); router.push(`/search?q=${encodeURIComponent(q)}`); }} className="mb-4">
        <Input autoFocus className="h-11 text-base" placeholder="Students, teachers, invoices, receipts, batches, materials…" value={q} onChange={(e) => setQ(e.target.value)} />
      </form>
      {r.isLoading && term ? <Skeleton className="h-40" /> : !Object.keys(groups).length ? <EmptyState title={term ? "No matches" : "Type at least two characters"} /> : (
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(groups).map(([label, items]) => (
            <Card key={label} title={label}>
              <ul className="space-y-1.5">{items.map((x) => (
                <li key={x.id}><Link href={detailHref(x.type, x.id)} className="flex justify-between text-sm hover:underline"><span>{x.title}</span>{x.subtitle && <Badge>{x.subtitle}</Badge>}</Link></li>
              ))}</ul>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

export default function SearchPage() {
  return <Suspense><Search /></Suspense>;
}
