import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="text-center">
        <p className="eyebrow">404</p>
        <h1 className="mt-1 text-lg font-semibold">Page not found</h1>
        <p className="mt-1 text-sm text-muted">The requested page or record does not exist.</p>
        <Link href="/" className="mt-4 inline-block text-sm text-accent hover:underline">
          Back to overview
        </Link>
      </div>
    </main>
  );
}
