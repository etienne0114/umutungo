import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GovAsset Insight | Fleet operations",
  description:
    "A decision-support workspace for government asset inspections and maintenance planning.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
