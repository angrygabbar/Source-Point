"use client";

import { useEffect, useState } from "react";
import { AuthLayout } from "@/components/layout/auth-layout";
import { API_BASE, APP_BASE_PATH, setAccessToken, withBasePath } from "@/lib/api";

export default function SourcePointSignInPage() {
  const [message, setMessage] = useState("Signing you in with SourcePoint…");

  useEffect(() => {
    const token = window.location.hash.slice(1);
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    if (!token) {
      setMessage("The SourcePoint sign-in link expired. Open Institute Management from SourcePoint again.");
      return;
    }

    let active = true;
    fetch(`${API_BASE}/auth/sourcepoint`, {
      method: "POST",
      credentials: "same-origin",
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.error?.message ?? "SourcePoint sign-in failed.");
        return result as { access_token: string; must_change_password: boolean };
      })
      .then((result) => {
        if (!active) return;
        setAccessToken(result.access_token);
        const destination = result.must_change_password ? "/profile?force=1" : "/dashboard";
        window.location.replace(withBasePath(destination));
      })
      .catch((error: unknown) => {
        if (active) setMessage(error instanceof Error ? error.message : "SourcePoint sign-in failed.");
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <AuthLayout title="Signing in" subtitle="Your SourcePoint account is being connected to your institute account.">
      <div className="space-y-4 text-sm text-slate-600">
        <p role="status" aria-live="polite">{message}</p>
        {message !== "Signing you in with SourcePoint…" && (
          <div className="flex flex-col gap-2">
            <a className="text-brand-800 underline" href={`${APP_BASE_PATH}/login?local=1`}>
              Sign in with your institute account
            </a>
            <a className="text-slate-600 underline" href="/">Return to SourcePoint</a>
          </div>
        )}
      </div>
    </AuthLayout>
  );
}
