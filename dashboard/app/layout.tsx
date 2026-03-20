import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinClaw 🦀📈 — AI Quantitative Trading Engine",
  description:
    "AI-native quantitative finance engine powered by multi-agent debate. Crypto + A-shares, backtesting, strategy marketplace, and constitutional risk management.",
  keywords: [
    "FinClaw",
    "trading",
    "AI",
    "quantitative",
    "crypto",
    "A-shares",
    "open-source",
    "agent",
    "debate",
    "NeuZhou",
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
