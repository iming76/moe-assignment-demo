import type { Metadata } from "next";
import type { ReactNode } from "react";
import Navbar from "@/components/ui/nav";
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";
import "./globals.css";

const inter = Inter({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: "Script Review — Handwritten OCR",
  description:
    "Human review tool for the handwritten student script OCR pipeline",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className={cn("font-sans", inter.variable)} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark');}}catch(e){}})();`,
          }}
        />
      </head>
      <body>
        <Navbar />
        <main className="flex h-screen w-full gap-4 bg-gray-100 dark:bg-gray-950 pt-18 pb-24 px-4">
          {children}
        </main>
        </body>
    </html>
  );
}
