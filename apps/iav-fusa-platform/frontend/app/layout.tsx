import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IAV FuSa Platform",
  description: "AI-powered functional safety analysis platform for ISO 26262",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
