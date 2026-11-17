"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CornerDownLeft, Package, Search } from "lucide-react";

import { Thumb } from "@/components/offers/values";
import { useApi } from "@/hooks/use-api";
import { cn } from "@/services/cn";
import { formatINR } from "@/services/format";
import type { Envelope, SearchResult } from "@/services/types";
import { NAV_ITEMS } from "./nav";

interface Item {
  id: string;
  label: string;
  sub?: string;
  href: string;
  kind: "page" | "product" | "category";
  image?: string | null;
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(q.trim()), 200);
    return () => window.clearTimeout(t);
  }, [q]);
  useEffect(() => {
    if (open) {
      setQ("");
      setIndex(0);
      window.setTimeout(() => input.current?.focus(), 0);
    }
  }, [open]);

  const search = useApi<Envelope<SearchResult>>(open && debounced.length >= 2 ? "/search" : null, { q: debounced });

  const items = useMemo<Item[]>(() => {
    const term = q.trim().toLowerCase();
    const pages = NAV_ITEMS.filter((n) => !term || `${n.label} ${n.keywords ?? ""}`.toLowerCase().includes(term)).map<Item>((n) => ({
      id: `page:${n.href}`,
      label: n.label,
      href: n.href,
      kind: "page",
    }));
    const products = (search.data?.data.products ?? []).map<Item>((p) => ({
      id: `product:${p.id}`,
      label: p.title ?? "Title not available",
      sub: [p.brand, p.category, formatINR(p.current_price)].filter(Boolean).join(" · "),
      href: `/products/${p.id}`,
      kind: "product",
      image: p.image_url,
    }));
    const categories = (search.data?.data.categories ?? []).map<Item>((c) => ({
      id: `category:${c.value}`,
      label: c.value,
      sub: `${c.count} products · open in Deal Explorer`,
      href: `/explorer?category=${encodeURIComponent(c.value)}`,
      kind: "category",
    }));
    return [...products, ...categories, ...pages].slice(0, 20);
  }, [q, search.data]);

  useEffect(() => setIndex(0), [items.length]);

  if (!open) return null;
  const go = (item?: Item) => {
    if (!item) return;
    router.push(item.href);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[55] flex items-start justify-center bg-[rgb(15_20_30/0.45)] p-4 pt-[12vh]" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Search" className="w-full max-w-xl overflow-hidden rounded-md border border-line bg-surface shadow-pop" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b border-line px-3">
          <Search className="h-4 w-4 text-faint" />
          <input
            ref={input}
            value={q}
            maxLength={200}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") onClose();
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setIndex((i) => Math.min(i + 1, items.length - 1));
              }
              if (e.key === "ArrowUp") {
                e.preventDefault();
                setIndex((i) => Math.max(i - 1, 0));
              }
              if (e.key === "Enter") go(items[index]);
            }}
            placeholder="Search products, brands, categories or pages…"
            className="h-11 flex-1 bg-transparent text-sm outline-none placeholder:text-faint"
            aria-label="Search"
          />
          <kbd className="rounded border border-line px-1.5 text-2xs text-faint">Esc</kbd>
        </div>
        <ul className="max-h-[50vh] overflow-y-auto p-1" role="listbox">
          {items.length === 0 ? (
            <li className="px-3 py-6 text-center text-xs text-faint">{search.isFetching ? "Searching…" : "No matches"}</li>
          ) : (
            items.map((item, i) => (
              <li key={item.id} role="option" aria-selected={i === index}>
                <button
                  type="button"
                  onMouseEnter={() => setIndex(i)}
                  onClick={() => go(item)}
                  className={cn("flex w-full items-center gap-2.5 rounded px-2 py-1.5 text-left", i === index ? "bg-subtle" : "")}
                >
                  {item.kind === "product" ? (
                    <Thumb src={item.image ?? null} alt="" size={28} />
                  ) : (
                    <span className="flex h-7 w-7 items-center justify-center rounded-sm border border-line text-faint">
                      {item.kind === "category" ? <Package className="h-3.5 w-3.5" /> : <CornerDownLeft className="h-3.5 w-3.5" />}
                    </span>
                  )}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm">{item.label}</span>
                    {item.sub ? <span className="block truncate text-2xs text-faint">{item.sub}</span> : null}
                  </span>
                  <span className="eyebrow">{item.kind}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
