"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ResourceMeta } from "@/types";

export function useAllMeta() {
  return useQuery({ queryKey: ["meta"], queryFn: () => api<ResourceMeta[]>("/meta/resources"), staleTime: 5 * 60_000 });
}

export function useMeta(resource: string) {
  return useQuery({
    queryKey: ["meta", resource],
    queryFn: () => api<ResourceMeta>(`/meta/resources/${resource}`),
    staleTime: 5 * 60_000,
    enabled: !!resource,
  });
}
