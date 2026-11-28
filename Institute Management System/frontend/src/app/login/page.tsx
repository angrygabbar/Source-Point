"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AuthLayout } from "@/components/layout/auth-layout";
import { Button, Field, Input } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { errorMessage } from "@/lib/api";

function LoginForm() {
  const { signIn, status } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const next = params.get("next");
  const safeNext = next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";

  useEffect(() => {
    if (status === "authenticated") router.replace(safeNext);
  }, [status, router, safeNext]);

  return (
    <form
      className="space-y-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
          const { mustChange } = await signIn(email.trim(), password);
          router.replace(mustChange ? "/profile?force=1" : safeNext);
        } catch (err) {
          setError(errorMessage(err));
        } finally {
          setBusy(false);
        }
      }}
    >
      <Field label="Email">
        <Input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </Field>
      <Field label="Password">
        <Input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      </Field>
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <Button type="submit" className="w-full" loading={busy}>Sign in</Button>
      <div className="text-center text-sm">
        <Link href="/forgot-password" className="text-brand-800 hover:underline">Forgot password?</Link>
      </div>
    </form>
  );
}

export default function LoginPage() {
  return (
    <AuthLayout title="Sign in" subtitle="Use the account issued by your institute.">
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
