import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "reactflow/dist/style.css";
import { Navigation } from "@/components/Navigation";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Smart Contract Auditor",
  description:
    "Paste any Solidity contract. Get an AI-curated security audit in seconds.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <Navigation />
        {children}
      </body>
    </html>
  );
}
