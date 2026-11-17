"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

/** Filter state persisted in the URL so views are shareable and can be saved. */
export function useUrlState<T extends Record<string, string>>(defaults: T) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const state = useMemo(() => {
    const out = { ...defaults } as Record<string, string>;
    for (const key of Object.keys(defaults)) {
      const value = searchParams.get(key);
      if (value !== null) out[key] = value;
    }
    return out as T;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const update = useCallback(
    (patch: Partial<T>, options: { resetPage?: boolean } = { resetPage: true }) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (value === undefined || value === "" || value === defaults[key]) next.delete(key);
        else next.set(key, String(value));
      }
      if (options.resetPage && !("page" in patch)) next.delete("page");
      const query = next.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [searchParams, pathname, router],
  );

  const replaceAll = useCallback(
    (values: Partial<T>) => {
      const next = new URLSearchParams();
      for (const [key, value] of Object.entries(values)) {
        if (key in defaults && value !== undefined && value !== "" && value !== defaults[key]) next.set(key, String(value));
      }
      const query = next.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pathname, router],
  );

  const reset = useCallback(() => router.replace(pathname, { scroll: false }), [pathname, router]);

  const activeCount = useMemo(
    () => Object.keys(defaults).filter((k) => !["page", "sort", "order", "page_size"].includes(k) && state[k] !== defaults[k]).length,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state],
  );

  return { state, update, replaceAll, reset, activeCount };
}
