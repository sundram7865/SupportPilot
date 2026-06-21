import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";

import { AuthSyncGate } from "@/components/auth/AuthSyncGate";

import "./globals.css";

export const metadata: Metadata = {
  title: "SupportPilot",
  description: "Agentic support workspace for ecommerce teams",
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
          <AuthSyncGate>{children}</AuthSyncGate>
        </body>
      </html>
    </ClerkProvider>
  );
}