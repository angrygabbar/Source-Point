"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button, Field, Input } from "@/components/ui";
import { AuthLayout } from "@/components/layout/auth-layout";
import { api, errorMessage } from "@/lib/api";

function ResetForm() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <form
      className="space-y-4"
      onSubmit={async (e) => {
        e.preventDefault();
        if (pw !== pw2) return setErr("Passwords do not match");
        setBusy(true);
        setErr(null);
        try {
          await api("/auth/reset-password", { method: "POST", body: { token, new_password: pw } });
          router.replace("/login");
        } catch (e2) {
          setErr(errorMessage(e2));
        } finally {
          setBusy(false);
        }
      }}
    >
      {!token && <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">The reset link is missing its token.</p>}
      <Field label="New password" hint="At least 10 characters with 3 of: upper, lower, digit, symbol">
        <Input type="password" autoComplete="new-password" required minLength={10} value={pw} onChange={(e) => setPw(e.target.value)} />
      </Field>
      <Field label="Confirm password">
        <Input type="password" autoComplete="new-password" required value={pw2} onChange={(e) => setPw2(e.target.value)} />
      </Field>
      {err && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>}
      <Button type="submit" className="w-full" loading={busy} disabled={!token}>Set password</Button>
      <p className="text-center text-sm"><Link className="text-brand-800 hover:underline" href="/login">Back to sign in</Link></p>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthLayout title="Choose a new password">
      <Suspense>
        <ResetForm />
      </Suspense>
    </AuthLayout>
  );
}
