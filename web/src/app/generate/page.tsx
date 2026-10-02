"use client";

import { useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  candidatesFromFile,
  generateKeywords,
  MODELS,
  rankKeywordBatch,
  titlesFromFile,
  type CandidateFile,
  type Keys,
  type KeywordGroup,
  type RankedKeyword,
} from "@/lib/api";
import { ModelFields, type Engine } from "@/components/model-fields";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const emptyKeys: Keys = {
  gemini_key: "",
  openai_key: "",
  anthropic_key: "",
  cloudflare_account_id: "",
  cloudflare_api_token: "",
};

type Mode = "generate" | "rank";
type Progress = { done: number; total: number; batch: number; batches: number };
type TitlesOnly = { titles: string[]; message: string };

const sampleTitles = [
  "Bamboo Cutting Board Set of 3",
  "Rechargeable Clip On Book Light",
  "Women's High Waisted Yoga Leggings",
  "Sony WH-1000XM5 Wireless Headphones Black",
  "Gooseneck Electric Kettle with Temperature Control",
  "Orthopedic Waterproof Dog Bed Large",
  "iPhone 15 Pro Clear MagSafe Case",
  "Linen Blackout Curtains 84 Inch 2 Panels",
].join("\n");

export default function GeneratePage() {
  const [mode, setMode] = useState<Mode>("generate");
  const [raw, setRaw] = useState(sampleTitles);
  const [engine, setEngine] = useState<Engine>("Gemini");
  const [model, setModel] = useState(MODELS.Gemini[0]);
  const [keys, setKeys] = useState<Keys>(emptyKeys);
  const [generated, setGenerated] = useState<KeywordGroup[]>([]);
  const [ranked, setRanked] = useState<KeywordGroup[]>([]);
  const [parsed, setParsed] = useState<(CandidateFile & { fileName: string }) | null>(null);
  const [titlesOnly, setTitlesOnly] = useState<TitlesOnly | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState("");
  const runRef = useRef(0);

  const titles = useMemo(
    () =>
      raw
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((title) => ({ title, brand: "" })),
    [raw],
  );

  const groups = mode === "generate" ? generated : ranked;

  async function onGenerate() {
    const id = ++runRef.current;
    setBusy(true);
    setError("");
    try {
      const data = await generateKeywords({
        titles,
        method: engine === "Fast" ? "rake" : "llm",
        provider: engine === "Fast" ? "Gemini" : engine,
        model,
        keys,
      });
      if (runRef.current !== id) return;
      setGenerated(data.groups);
    } catch (err) {
      if (runRef.current !== id) return;
      setGenerated([]);
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      if (runRef.current === id) setBusy(false);
    }
  }

  async function readCandidates(file: File) {
    setReading(true);
    setError("");
    setTitlesOnly(null);
    setParsed(null);
    setRanked([]);
    setProgress(null);
    try {
      const data = await candidatesFromFile(file);
      if ("titles_only" in data) {
        setTitlesOnly({ titles: data.titles, message: data.error });
        return;
      }
      setParsed({ ...data, fileName: file.name });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read that file");
    } finally {
      setReading(false);
    }
  }

  async function onRank() {
    if (!parsed) return;
    const id = ++runRef.current;
    setBusy(true);
    setError("");
    setRanked([]);
    const total = parsed.keyword_count;
    let done = 0;
    let merged: KeywordGroup[] = [];
    setProgress({ done: 0, total, batch: 1, batches: parsed.batch_count });
    try {
      for (let index = 0; index < parsed.batches.length; index += 1) {
        if (runRef.current !== id) return;
        const batch = parsed.batches[index];
        setProgress({ done, total, batch: index + 1, batches: parsed.batches.length });
        const data = await rankKeywordBatch({ groups: batch, keys });
        if (runRef.current !== id) return;
        merged = mergeKeywordGroups(merged, data.groups);
        setRanked(merged);
        done += batch.reduce((sum, group) => sum + group.keywords.length, 0);
        setProgress({ done, total, batch: index + 1, batches: parsed.batches.length });
      }
    } catch (err) {
      if (runRef.current !== id) return;
      const message = err instanceof Error ? err.message : "Ranking failed";
      setError(done > 0 ? `${message} Ranked ${done} of ${total} before it stopped.` : message);
    } finally {
      if (runRef.current === id) {
        setProgress(null);
        setBusy(false);
      }
    }
  }

  function useTitlesForGenerate() {
    if (!titlesOnly) return;
    setRaw(titlesOnly.titles.join("\n"));
    setTitlesOnly(null);
    setError("");
    setMode("generate");
  }

  function download() {
    const header = mode === "rank" ? "title,rank,keyword,score" : "Product Title,Rank,Keyword,Score";
    const body = groups
      .flatMap((group) =>
        group.keywords.map((item) =>
          [
            csvCell(group.title),
            String(item.rank),
            csvCell(item.keyword),
            item.score == null ? "" : item.score.toFixed(2),
          ].join(","),
        ),
      )
      .join("\n");
    const blob = new Blob([`${header}\n${body}`], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = mode === "rank" ? "ranked-keywords.csv" : "keywords.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  const showLarge = mode === "rank" && Boolean(parsed?.large) && (progress !== null || ranked.length === 0);
  const showEmpty = groups.length === 0 && !busy && !error && !showLarge;

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10">
      <header className="max-w-3xl">
        <Badge>Primary task</Badge>
        <h1 className="font-display mt-4 text-5xl tracking-tight">Generate keywords</h1>
        <p className="mt-3 text-ink/70">
          {mode === "generate"
            ? "One title per line. Fast returns one phrase on this machine. Gemini, OpenAI, or Claude writes five phrases, and Clef ranks them."
            : "Upload a CSV of titles and the keywords you already have. Clef scores each phrase and ranks it against the others for that title."}
        </p>
        <div className="mt-6 inline-flex rounded-full border border-white/70 bg-white/70 p-1 shadow-[0_10px_40px_-24px_rgba(11,31,42,0.45)] backdrop-blur-xl">
          {(
            [
              ["generate", "Generate new keywords"],
              ["rank", "Rank a CSV"],
            ] as const
          ).map(([value, label]) => {
            const active = mode === value;
            return (
              <button
                key={value}
                type="button"
                disabled={busy}
                aria-pressed={active}
                onClick={() => {
                  setMode(value);
                  setError("");
                }}
                className={cn(
                  "relative rounded-full px-4 py-2 text-sm transition disabled:opacity-50",
                  active ? "text-white" : "text-ink/70 hover:text-ink",
                )}
              >
                {active && (
                  <motion.span
                    layoutId="task-mode"
                    className="absolute inset-0 rounded-full bg-ink"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                )}
                <span className="relative">{label}</span>
              </button>
            );
          })}
        </div>
      </header>

      <Card>
        <CardContent className="pt-6">
          <AnimatePresence mode="wait" initial={false}>
            {mode === "generate" ? (
              <motion.div
                key="generate"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
                className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]"
              >
                <div className="space-y-4">
                  <div>
                    <CardTitle>Titles</CardTitle>
                    <p className="mt-1 text-sm text-ink/55">One product title per line.</p>
                  </div>
                  <Textarea value={raw} onChange={(event) => setRaw(event.target.value)} className="min-h-64" />
                  <label className="flex cursor-pointer items-center justify-between gap-3 rounded-2xl border border-dashed border-ink/15 bg-white/50 px-4 py-3 text-sm text-ink/70">
                    <span>
                      Or drop a titles CSV or Excel sheet
                      <span className="mt-1 block text-xs text-ink/45">
                        A keyword column is ignored here. Use Rank a CSV to score phrases already in the file.
                      </span>
                    </span>
                    <span className="shrink-0 rounded-full bg-ink px-3 py-1.5 text-xs text-white">Choose file</span>
                    <input
                      type="file"
                      accept=".csv,.txt,.xlsx,.xls"
                      className="sr-only"
                      onChange={async (event) => {
                        const file = event.target.files?.[0];
                        event.target.value = "";
                        if (!file) return;
                        setError("");
                        try {
                          const data = await titlesFromFile(file);
                          setRaw(data.titles.join("\n"));
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Could not read that file");
                        }
                      }}
                    />
                  </label>
                </div>
                <div className="flex flex-col gap-4">
                  <ModelFields
                    includeFast
                    showRanker
                    engine={engine}
                    model={model}
                    keys={keys}
                    onEngine={(next) => {
                      setEngine(next);
                      if (next !== "Fast") setModel(MODELS[next][0]);
                    }}
                    onModel={setModel}
                    onKeys={setKeys}
                  />
                  <Button onClick={onGenerate} disabled={busy || titles.length === 0}>
                    {busy ? "Generating…" : `Generate ${titles.length || ""}`.trim()}
                  </Button>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="rank"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
                className="space-y-4"
              >
                <div>
                  <CardTitle>Keyword CSV</CardTitle>
                  <p className="mt-1 max-w-2xl text-sm text-ink/55">
                    One row per candidate. Clef compares the keywords that share a title and marks rank 1 as the best.
                  </p>
                </div>
                <label
                  className={cn(
                    "flex cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed px-6 py-10 text-center transition",
                    dragOver ? "border-coral bg-coral/10" : "border-ink/15 bg-white/50",
                  )}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(event) => {
                    event.preventDefault();
                    setDragOver(false);
                    if (busy || reading) return;
                    const file = event.dataTransfer.files?.[0];
                    if (file) void readCandidates(file);
                  }}
                >
                  <span className="font-display text-2xl tracking-tight">
                    {reading ? "Reading file…" : "Drop a CSV"}
                  </span>
                  <span className="mt-2 max-w-md text-sm text-ink/60">
                    Headers such as title, Product Title, or product name, plus keyword, Product Keyword, or search keyword.
                  </span>
                  <span className="mt-4 rounded-full bg-ink px-4 py-2 text-sm text-white">Choose CSV</span>
                  <input
                    type="file"
                    accept=".csv,.txt,.xlsx,.xls"
                    className="sr-only"
                    disabled={busy || reading}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      event.target.value = "";
                      if (file) void readCandidates(file);
                    }}
                  />
                </label>

                {parsed && (
                  <div className="rounded-2xl bg-foam px-4 py-3 text-sm">
                    <p className="font-medium">{parsed.fileName}</p>
                    <p className="mt-1 text-ink/65">
                      {parsed.title_count.toLocaleString()} titles · {parsed.keyword_count.toLocaleString()} keywords ·{" "}
                      {parsed.batch_count.toLocaleString()} {parsed.batch_count === 1 ? "batch" : "batches"} of up to 64
                    </p>
                  </div>
                )}

                {titlesOnly && (
                  <div className="rounded-2xl border border-coral/25 bg-coral/10 px-4 py-4 text-sm">
                    <p className="text-ink">{titlesOnly.message}</p>
                    <Button variant="ink" className="mt-3" onClick={useTitlesForGenerate}>
                      Generate keywords for these titles
                    </Button>
                  </div>
                )}

                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="grid gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-ink/45">
                    Cloudflare account ID
                    <Input
                      placeholder="Or leave blank to use .env"
                      value={keys.cloudflare_account_id ?? ""}
                      onChange={(event) => setKeys({ ...keys, cloudflare_account_id: event.target.value })}
                    />
                  </label>
                  <label className="grid gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-ink/45">
                    Cloudflare API token
                    <Input
                      type="password"
                      placeholder="Workers AI token, or leave blank to use .env"
                      value={keys.cloudflare_api_token ?? ""}
                      onChange={(event) => setKeys({ ...keys, cloudflare_api_token: event.target.value })}
                    />
                  </label>
                </div>

                <Button onClick={onRank} disabled={busy || reading || !parsed}>
                  {busy
                    ? "Ranking…"
                    : parsed
                      ? `Rank ${parsed.keyword_count.toLocaleString()} keywords`
                      : "Rank keywords"}
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      <section className="space-y-4" aria-busy={busy}>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-ink/45">Results</p>
            <h2 className="font-display text-3xl tracking-tight">
              {groups.length > 0
                ? `${groups.length.toLocaleString()} ranked ${groups.length === 1 ? "title" : "titles"}`
                : "Ranked keywords"}
            </h2>
            <p className="mt-1 text-sm text-ink/55">Rank 1 is the best phrase for that title.</p>
          </div>
          {groups.length > 0 && (
            <Button variant="outline" onClick={download}>
              Download CSV
            </Button>
          )}
        </div>

        {error && (
          <div className="rounded-2xl border border-coral/30 bg-coral/10 px-4 py-3 text-sm text-coral">{error}</div>
        )}

        {busy && (
          <p className="text-sm text-ink/60">
            {mode === "rank"
              ? progress
                ? `Scored ${progress.done.toLocaleString()} of ${progress.total.toLocaleString()} · batch ${progress.batch} of ${progress.batches}`
                : "Scoring keywords with Clef."
              : engine === "Fast"
                ? "Finding a phrase on this machine."
                : "Writing five phrases, then Clef ranks them."}
          </p>
        )}

        {showLarge && parsed && (
          <Card>
            <CardHeader>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-coral">Large file</p>
              <CardTitle className="mt-2 text-3xl">
                {parsed.keyword_count.toLocaleString()} keywords across {parsed.title_count.toLocaleString()} titles
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="max-w-2xl text-sm text-ink/70">
                Clef accepts 64 questions at a time. This file is scored in {parsed.batch_count} batches, and the
                keywords for each title are ranked against each other.
              </p>
              {progress && (
                <div className="h-1.5 overflow-hidden rounded-full bg-ink/10">
                  <div
                    className="h-full rounded-full bg-coral transition-[width] duration-500"
                    style={{ width: `${progress.total ? Math.round((progress.done / progress.total) * 100) : 0}%` }}
                  />
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {mode === "rank" && progress && !parsed?.large && (
          <div className="h-1.5 overflow-hidden rounded-full bg-ink/10">
            <div
              className="h-full rounded-full bg-coral transition-[width] duration-500"
              style={{ width: `${progress.total ? Math.round((progress.done / progress.total) * 100) : 0}%` }}
            />
          </div>
        )}

        {showEmpty && (
          <div className="rounded-3xl border border-dashed border-ink/15 bg-white/40 px-6 py-16 text-center">
            <p className="font-display text-2xl tracking-tight">
              {mode === "generate" ? "No ranked keywords yet" : "No CSV ranked yet"}
            </p>
            <p className="mx-auto mt-2 max-w-md text-sm text-ink/55">
              {mode === "generate"
                ? "Each title gets its own table under this form, with the best phrase in rank 1."
                : "Upload a CSV with titles and candidate keywords. The best phrase for each title will show up here."}
            </p>
          </div>
        )}

        {groups.length > 0 && (
          <div className="grid gap-4 lg:grid-cols-2">
            {groups.map((group, index) => (
              <ResultCard key={group.title} group={group} index={index} />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function ResultCard({ group, index }: { group: KeywordGroup; index: number }) {
  const best = group.keywords[0];
  const wide = group.keywords.length > 8;
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 10) * 0.035 }}
      className={cn(wide && "lg:col-span-2")}
    >
      <Card className="h-full">
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
          <CardTitle className="max-w-xl text-2xl">{group.title}</CardTitle>
          {best?.keyword && (
            <p className="max-w-xs text-right text-sm text-ink/70">
              Best <span className="font-medium text-coral">{best.keyword}</span>
              {best.score != null && (
                <span className="ml-2 tabular-nums text-ink/45">{best.score.toFixed(2)}</span>
              )}
            </p>
          )}
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[22rem] text-left text-sm">
              <thead className="text-[11px] uppercase tracking-[0.14em] text-ink/40">
                <tr>
                  <th className="w-16 pb-2 font-medium">Rank</th>
                  <th className="pb-2 font-medium">Keyword</th>
                  <th className="w-20 pb-2 text-right font-medium">Score</th>
                </tr>
              </thead>
              <tbody>
                {group.keywords.map((item) => (
                  <tr
                    key={`${item.rank}-${item.keyword}`}
                    className={cn("border-t border-ink/5", item.rank === 1 && "bg-coral/10")}
                  >
                    <td className={cn("py-2.5 pl-2", item.rank === 1 ? "font-medium text-coral" : "text-ink/45")}>
                      {item.rank}
                    </td>
                    <td className="py-2.5 pr-3">{item.keyword || "—"}</td>
                    <td className="py-2.5 pr-2 text-right tabular-nums text-ink/60">{formatScore(item)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </motion.article>
  );
}

function formatScore(item: RankedKeyword) {
  return item.score == null ? "—" : item.score.toFixed(2);
}

function csvCell(value: string) {
  return `"${value.replaceAll('"', '""')}"`;
}

function mergeKeywordGroups(existing: KeywordGroup[], incoming: KeywordGroup[]): KeywordGroup[] {
  const titles: string[] = [];
  const map = new Map<string, KeywordGroup>();
  for (const group of [...existing, ...incoming]) {
    const current = map.get(group.title);
    if (!current) {
      titles.push(group.title);
      map.set(group.title, { ...group, keywords: [...group.keywords] });
    } else {
      current.keywords.push(...group.keywords);
    }
  }
  return titles.map((title) => {
    const group = map.get(title)!;
    const keywords = group.keywords
      .map((item, index) => ({ item, index }))
      .sort((a, b) => {
        const scoreA = a.item.score ?? -1;
        const scoreB = b.item.score ?? -1;
        if (scoreA !== scoreB) return scoreB - scoreA;
        return a.index - b.index;
      })
      .map(({ item }, rank) => ({ ...item, rank: rank + 1 }));
    return { title, brand: group.brand, keywords };
  });
}
