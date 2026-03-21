import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinClaw — Quantitative Research Platform",
  description:
    "Open-source quantitative finance engine. Multi-market coverage, backtesting, strategy analysis, and risk management.",
  keywords: [
    "FinClaw",
    "trading",
    "quantitative",
    "crypto",
    "A-shares",
    "open-source",
    "backtesting",
    "risk management",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0a0f] antialiased">
        {children}
      </body>
    </html>
  );
}
