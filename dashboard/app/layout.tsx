import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WhaleTrader — AI Quantitative Trading Engine",
  description: "The first open-source platform combining AI agent intelligence with production-grade trading infrastructure. Multi-agent debate, YAML strategy marketplace, Rust performance.",
  keywords: ["trading", "AI", "quantitative", "crypto", "Rust", "open-source", "agent", "debate"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0a0f] antialiased">
        {children}
      </body>
    </html>
  );
}
