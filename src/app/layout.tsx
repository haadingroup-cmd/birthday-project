import type { Metadata } from "next";
import "./globals.css";
import { BIRTHDAY } from "@/data/content";

export const metadata: Metadata = {
  title: `Happy Birthday ${BIRTHDAY.name} 🎂`,
  description: BIRTHDAY.subtitle,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
