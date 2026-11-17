"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import { useToast } from "@/components/ui/toast";
import { api, ApiError, type QueryParams } from "@/services/api";

export function useApi<T>(
  path: string | null,
  params?: QueryParams,
  options: { refetchInterval?: number | false; enabled?: boolean; keepPrevious?: boolean } = {},
) {
  return useQuery<T, ApiError>({
    queryKey: [path, params ?? {}],
    queryFn: ({ signal }) => api.get<T>(path as string, params, signal),
    enabled: Boolean(path) && (options.enabled ?? true),
    refetchInterval: options.refetchInterval,
    placeholderData: options.keepPrevious ? keepPreviousData : undefined,
  });
}

export function invalidatePrefixes(client: QueryClient, prefixes: string[]) {
  return client.invalidateQueries({
    predicate: (query) => {
      const key = query.queryKey[0];
      return typeof key === "string" && prefixes.some((p) => key.startsWith(p));
    },
  });
}

export function useApiMutation<TVars, TResult = unknown>(
  fn: (vars: TVars) => Promise<TResult>,
  options: { invalidate?: string[]; success?: string | ((r: TResult) => string); onSuccess?: (r: TResult, v: TVars) => void } = {},
) {
  const client = useQueryClient();
  const toast = useToast();
  return useMutation<TResult, ApiError, TVars>({
    mutationFn: fn,
    onSuccess: async (result, vars) => {
      if (options.invalidate?.length) await invalidatePrefixes(client, options.invalidate);
      if (options.success) toast.push({ tone: "positive", title: typeof options.success === "function" ? options.success(result) : options.success });
      options.onSuccess?.(result, vars);
    },
    onError: (error) => toast.push({ tone: "negative", title: "Action failed", description: error.message }),
  });
}
