import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Enoki — Focus Together",
  description: "A networked AI mushroom companion that keeps you and your study group focused.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        {children}
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
