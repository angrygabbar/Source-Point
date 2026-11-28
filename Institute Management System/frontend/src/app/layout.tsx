import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import "@/styles/globals.css";
import { Providers } from "./providers";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const appName = process.env.NEXT_PUBLIC_APP_NAME || "Institute Management System";

export const metadata: Metadata = {
  title: { default: appName, template: `%s · ${appName}` },
  description: "Institute admissions, academics, finance and operations management",
  manifest: `${basePath}/manifest.webmanifest`,
  icons: { icon: `${basePath}/icon.svg`, apple: `${basePath}/icon.svg` },
  appleWebApp: { capable: true, title: "Institute Management", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: "#1e2a78",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <Suspense fallback={null}>{children}</Suspense>
        </Providers>
      </body>
    </html>
  );
}
