import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smart Contract Auditor",
  description: "Static analysis & audit tooling for Solidity contracts",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
