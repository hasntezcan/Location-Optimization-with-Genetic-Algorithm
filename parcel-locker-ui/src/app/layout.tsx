import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kargo Dolabı Lokasyon Öneri Paneli",
  description: "Talep, erişilebilirlik ve bölgesel dengeye göre kargo dolabı konum önerileri",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
