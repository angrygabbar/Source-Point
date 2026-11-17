export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue>;
const API_BASE = "/coinback-api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public fields?: { field: string; message: string }[],
  ) {
    super(message);
  }
}

export function toQuery(params?: QueryParams): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.assign(`/login_register?next=${next}`);
}

async function request<T>(method: string, path: string, options: { params?: QueryParams; body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", "X-Requested-With": "coinback" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api${path}${toQuery(options.params)}`, {
      method,
      headers,
      credentials: "same-origin",
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
      cache: "no-store",
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(0, "Network error: the API could not be reached.");
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new ApiError(401, "Session expired.");
  }
  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    const error = (payload as { error?: { message?: string; fields?: { field: string; message: string }[] } } | null)?.error;
    throw new ApiError(response.status, error?.message || `Request failed (HTTP ${response.status}).`, error?.fields);
  }
  return payload as T;
}

export const api = {
  get: <T>(path: string, params?: QueryParams, signal?: AbortSignal) => request<T>("GET", path, { params, signal }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body: body ?? {} }),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, { body }),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, { body }),
  del: <T>(path: string) => request<T>("DELETE", path),
};

export function exportHref(path: string, params: QueryParams, format: "csv" | "xlsx"): string {
  return `${API_BASE}/api${path}${toQuery({ ...params, page: undefined, page_size: undefined, format })}`;
}
