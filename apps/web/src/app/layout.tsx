import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Intent Tracker",
  description: "DeFi Intent Ecosystem Intelligence",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans bg-white text-gray-700 min-h-screen antialiased`}>
        <Nav />
        <main className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16">
          {children}
        </main>
      </body>
    </html>
  );
}
