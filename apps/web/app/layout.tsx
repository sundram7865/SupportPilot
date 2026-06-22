import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";

import { AuthSyncGate } from "@/components/auth/AuthSyncGate";
import { ReactQueryProvider } from "@/components/providers/ReactQueryProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "SupportPilot",
  description: "Agentic AI customer support platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>
          <ReactQueryProvider>
            <AuthSyncGate>{children}</AuthSyncGate>
          </ReactQueryProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}