import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KAQG — Knowledge Augmented Question Generation",
  description: "Upload syllabi, explore the knowledge graph, and generate calibrated MCQs.",
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