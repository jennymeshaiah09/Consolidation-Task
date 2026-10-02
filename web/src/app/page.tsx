"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, ShieldCheck, Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const chips = ["northbeam desk lamp", "trail runner socks", "glass storage jar", "cedar kettle"];

const rise = {
  hidden: { opacity: 0, y: 24 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.08 * i, duration: 0.6, ease: [0.22, 1, 0.36, 1] as const },
  }),
};

export default function HomePage() {
  return (
    <main className="mx-auto max-w-6xl px-4 pb-24 pt-10">
      <section className="grid items-center gap-10 lg:grid-cols-[1.15fr_0.85fr]">
        <div>
          <motion.div initial="hidden" animate="show" custom={0} variants={rise}>
            <Badge>Keyword generation</Badge>
          </motion.div>
          <motion.h1
            className="font-display mt-5 text-5xl leading-[0.95] tracking-tight sm:text-7xl"
            initial="hidden"
            animate="show"
            custom={1}
            variants={rise}
          >
            Titles in.
            <br />
            <span className="text-coral">Search phrases</span> out.
          </motion.h1>
          <motion.p
            className="mt-5 max-w-xl text-lg text-ink/70"
            initial="hidden"
            animate="show"
            custom={2}
            variants={rise}
          >
            Meridian turns product titles into short keywords a shopper would type. Fast mode stays on this machine. Quality mode can use Gemini, OpenAI, or Claude.
          </motion.p>
          <motion.div className="mt-8 flex flex-wrap gap-3" initial="hidden" animate="show" custom={3} variants={rise}>
            <Button asChild size="lg">
              <Link href="/generate">
                Generate keywords <ArrowRight />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/pipeline">Open catalog pipeline</Link>
            </Button>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="aurora relative overflow-hidden rounded-[2rem] p-8 text-white shadow-[0_30px_80px_-30px_rgba(255,92,53,0.7)]"
        >
          <p className="text-xs uppercase tracking-[0.22em] text-white/70">Live sample</p>
          <p className="font-display mt-3 text-3xl">Wireless Desk Lamp</p>
          <div className="mt-6 space-y-3">
            {chips.map((chip, index) => (
              <motion.div
                key={chip}
                className="floaty w-fit rounded-full bg-white/15 px-4 py-2 text-sm backdrop-blur"
                style={{ animationDelay: `${index * 0.4}s` }}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + index * 0.12 }}
              >
                {chip}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="mt-16 grid gap-4 md:grid-cols-3">
        {[
          { icon: Sparkles, title: "Generate", copy: "Paste titles or upload a sheet. RAKE is instant. LLM quality uses the model you pick.", href: "/generate" },
          { icon: ShieldCheck, title: "Verify", copy: "Ask whether a keyword actually belongs on that product before you export it.", href: "/verify" },
          { icon: Layers, title: "Catalog", copy: "Optional monthly ZIP. Merge price, rank, categories, and peaks when you need the full year.", href: "/pipeline" },
        ].map((item, index) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.08 }}
            whileHover={{ y: -6 }}
          >
            <Link href={item.href} className="block rounded-3xl border border-white/70 bg-white/70 p-6 shadow-[0_20px_50px_-32px_rgba(11,31,42,0.7)] backdrop-blur">
              <item.icon className="text-coral" />
              <h2 className="font-display mt-4 text-2xl">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-ink/65">{item.copy}</p>
            </Link>
          </motion.div>
        ))}
      </section>
    </main>
  );
}
