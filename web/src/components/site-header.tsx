"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const links = [
  { href: "/generate", label: "Generate" },
  { href: "/verify", label: "Verify" },
  { href: "/compare", label: "Compare" },
  { href: "/pipeline", label: "Catalog" },
];

export function SiteHeader() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-40 px-4 pt-4">
      <div className="mx-auto flex max-w-6xl items-center justify-between rounded-full border border-white/70 bg-white/70 px-4 py-2 shadow-[0_10px_40px_-24px_rgba(11,31,42,0.6)] backdrop-blur-xl">
        <Link href="/" className="font-display text-lg tracking-tight">
          Meri<span className="text-coral">dian</span>
        </Link>
        <nav className="flex flex-wrap items-center justify-end gap-1">
          {links.map((link) => {
            const active = path === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "relative rounded-full px-3 py-1.5 text-sm text-ink/70 transition hover:text-ink",
                  active && "text-ink",
                )}
              >
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-full bg-ink/5"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                <span className="relative">{link.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
