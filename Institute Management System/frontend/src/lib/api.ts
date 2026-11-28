/**
 * API client. Access tokens live only in memory; the refresh token is an httpOnly cookie
 * scoped to /api/v1/auth and rotated by the backend. Refresh calls carry a double-submit CSRF header.
 */

export const APP_BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/v1";

export function withBasePath(path: string): string {
  if (!path.startsWith("/") || !APP_BASE_PATH || path === APP_BASE_PATH || path.startsWith(`${APP_BASE_PATH}/`)) return path;
  return `${APP_BASE_PATH}${path}`;
}

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;
  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
const listeners = new Set<() => void>();

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function onSessionExpired(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function cookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

export function selectedBranch(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("cf.branch") || null;
}

export function selectedInstitute(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("cf.institute") || null;
}

export async function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRF-Token": cookie("cf_csrf") ?? "" },
        });
        if (!res.ok) {
          accessToken = null;
          return false;
        }
        const data = await res.json();
        accessToken = data.access_token;
        return true;
      } catch {
        return false;
      } finally {
        setTimeout(() => (refreshing = null), 0);
      }
    })();
  }
  return refreshing;
}

type Query = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Query;
  headers?: Record<string, string>;
  form?: FormData;
  raw?: boolean;
}

export function buildUrl(path: string, query?: Query): string {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  if (!query) return url;
  const qs = new URLSearchParams();
  Object.entries(query).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.append(k, String(v));
  });
  const s = qs.toString();
  return s ? `${url}${url.includes("?") ? "&" : "?"}${s}` : url;
}

async function doFetch(path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { ...(opts.headers ?? {}) };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const branch = selectedBranch();
  if (branch) headers["X-Branch-Id"] = branch;
  const inst = selectedInstitute();
  if (inst) headers["X-Institute-Id"] = inst;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  return fetch(buildUrl(path, opts.query), { method: opts.method ?? "GET", headers, body, credentials: "same-origin" });
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const j = await res.json();
    const e = j.error ?? {};
    return new ApiError(res.status, e.code ?? "error", e.message ?? res.statusText, e.details);
  } catch {
    return new ApiError(res.status, "error", res.statusText || "Request failed");
  }
}

export async function apiResponse(path: string, opts: RequestOptions = {}): Promise<Response> {
  let res = await doFetch(path, opts);
  if (res.status === 401 && !path.startsWith("/auth/login")) {
    const ok = await refreshSession();
    if (ok) res = await doFetch(path, opts);
    else listeners.forEach((l) => l());
  }
  if (!res.ok) throw await toError(res);
  return res;
}

export async function api<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await apiResponse(path, opts);
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  return (ct.includes("application/json") ? res.json() : res.text()) as Promise<T>;
}

/** Fetch an authenticated binary (PDF/CSV/XLSX) and open or download it. */
export async function openFile(path: string, opts: RequestOptions & { download?: boolean } = {}) {
  const res = await apiResponse(path, opts);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const disp = res.headers.get("content-disposition") ?? "";
  const name = /filename="?([^"]+)"?/.exec(disp)?.[1] ?? "download";
  if (opts.download || !blob.type.includes("pdf")) {
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } else {
    window.open(url, "_blank", "noopener");
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** Resolve a short-lived signed download link and open it. */
export async function openSignedLink(path: string) {
  const { url } = await api<{ url: string }>(path);
  window.open(url, "_blank", "noopener");
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (Array.isArray(e.details) && e.details.length) {
      const first = e.details[0] as { field?: string; message?: string } | string;
      if (typeof first === "string") return `${e.message}: ${e.details.join("; ")}`;
      if (first?.message) return `${e.message}: ${first.field ? `${first.field} – ` : ""}${first.message}`;
    }
    return e.message;
  }
  return e instanceof Error ? e.message : "Something went wrong";
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
