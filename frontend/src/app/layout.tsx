import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ToastStack from "@/components/ui/Toast";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Distributed Chat System",
  description: "Production-grade distributed chat backend & frontend client",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} h-full antialiased`}
    >
      <body className="h-full bg-[#0f111a] text-gray-100 overflow-hidden">
        {children}
        <ToastStack />
      </body>
    </html>
  );
}
