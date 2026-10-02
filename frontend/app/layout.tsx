import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Alzhio | Longitudinal research",
  description:
    "A local workspace for longitudinal brain MRI research. Research prototype, not a medical diagnosis.",
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
