import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Bricolage_Grotesque, Figtree } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";

const display = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
});

const sans = Figtree({
  variable: "--font-figtree",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Meridian — search keyword generation",
  description: "Turn product titles into short search phrases. Optional monthly catalog pipeline.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" data-scroll-behavior="smooth" className={`${display.variable} ${sans.variable} h-full`}>
      <body className="relative min-h-full">
        <div className="relative z-10">
          <SiteHeader />
          {children}
        </div>
      </body>
    </html>
  );
}
