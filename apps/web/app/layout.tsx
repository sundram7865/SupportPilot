import type { Metadata } from "next";
// @ts-ignore: allow side-effect CSS import in Next.js app router layout
import "./globals.css";

export const metadata: Metadata = {
  title: "SupportPilot",
  description: "Agentic AI customer support platform for e-commerce brands"
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}