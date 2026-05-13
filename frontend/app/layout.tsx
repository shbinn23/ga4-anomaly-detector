import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GA4 Operations Dashboard",
  description: "Operations dashboard for GA4 anomaly monitoring.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
