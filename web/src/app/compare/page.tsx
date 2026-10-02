"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { candidatesFromFile, compareKeywordBatch, type CandidateFile, type CompareRow, type CompareUsage } from "@/lib/api";
import { assembleComparison, expectedKeywordCounts, readyRows, summarize, type ComparedTitle, type RankedKeyword } from "@/lib/compare";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 40;

const emptyUsage: CompareUsage = {
  jev_input_tokens: 0,
  clef_input_tokens: 0,
  jev_estimated: false,
  clef_estimated: false,
};

type Progress = { done: number; total: number; batch: number; batches: number; waiting: boolean };

export default function ComparePage() {
  const [parsed, setParsed] = useState<(CandidateFile & { fileName: string }) | null>(null);
  const [accountId, setAccountId] = useState("");
  const [cloudflareToken, setCloudflareToken] = useState("");
  const [jevKey, setJevKey] = useState("");
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [usage, setUsage] = useState<CompareUsage>(emptyUsage);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState("");
  const [fileError, setFileError] = useState("");
  const [query, setQuery] = useState("");
  const [titlePage, setTitlePage] = useState(0);
  const [openTitle, setOpenTitle] = useState<string | null>(null);
  const runRef = useRef(0);

  useEffect(() => {
    if (!busy || startedAt == null) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [busy, startedAt]);

  const expected = useMemo(() => (parsed ? expectedKeywordCounts(parsed.batches) : new Map<string, number>()), [parsed]);
  const titles = useMemo(() => assembleComparison(readyRows(rows, expected)), [rows, expected]);
  const summary = useMemo(() => summarize(titles, usage), [titles, usage]);
  const disagreements = useMemo(() => titles.filter((title) => !title.agree), [titles]);
  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return titles;
    return titles.filter((title) => title.title.toLocaleLowerCase().includes(needle));
  }, [titles, query]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(titlePage, pageCount - 1);
  const visible = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const elapsed = startedAt && now ? Math.max(0, Math.round((now - startedAt) / 1000)) : 0;

  async function readFile(file: File) {
    setReading(true);
    setError("");
    setFileError("");
    setParsed(null);
    setRows([]);
    setUsage(emptyUsage);
    setProgress(null);
    setQuery("");
    setTitlePage(0);
    setOpenTitle(null);
    try {
      const data = await candidatesFromFile(file);
      if ("titles_only" in data) {
        setFileError("This file has titles but no keyword column. Add keyword, Product Keyword, or search keyword. This page only ranks phrases already in the file.");
        return;
      }
      setParsed({ ...data, fileName: file.name });
    } catch (err) {
      setFileError(err instanceof Error ? err.message : "Could not read that file");
    } finally {
      setReading(false);
    }
  }

  async function onCompare() {
    if (!parsed) return;
    const id = ++runRef.current;
    setBusy(true);
    setError("");
    setRows([]);
    setUsage(emptyUsage);
    setOpenTitle(null);
    setTitlePage(0);
    const total = parsed.keyword_count;
    let done = 0;
    let merged: CompareRow[] = [];
    let tokens: CompareUsage = { ...emptyUsage };
    setStartedAt(Date.now());
    setProgress({ done: 0, total, batch: 1, batches: parsed.batch_count, waiting: true });
    try {
      for (let index = 0; index < parsed.batches.length; index += 1) {
        if (runRef.current !== id) return;
        const batch = parsed.batches[index];
        setProgress({ done, total, batch: index + 1, batches: parsed.batches.length, waiting: true });
        const data = await compareKeywordBatch({
          groups: batch,
          cloudflare_account_id: accountId,
          cloudflare_api_token: cloudflareToken,
          typesafe_api_key: jevKey,
        });
        if (runRef.current !== id) return;
        merged = merged.concat(data.rows);
        tokens = {
          jev_input_tokens: tokens.jev_input_tokens + data.usage.jev_input_tokens,
          clef_input_tokens: tokens.clef_input_tokens + data.usage.clef_input_tokens,
          jev_estimated: tokens.jev_estimated || data.usage.jev_estimated,
          clef_estimated: tokens.clef_estimated || data.usage.clef_estimated,
        };
        done += batch.reduce((sum, group) => sum + group.keywords.length, 0);
        setRows(merged);
        setUsage(tokens);
        setProgress({ done, total, batch: index + 1, batches: parsed.batches.length, waiting: false });
      }
    } catch (err) {
      if (runRef.current !== id) return;
      const message = err instanceof Error ? err.message : "Comparison failed";
      setError(done > 0 ? `${message} Scored ${done.toLocaleString()} of ${total.toLocaleString()} keywords before it stopped.` : message);
    } finally {
      if (runRef.current === id) {
        setProgress(null);
        setBusy(false);
      }
    }
  }

  function download() {
    const header = "title,keyword,jev_rank,jev_score,clef_rank,clef_score,winner";
    const body = titles
      .flatMap((title) => {
        const clefBy = new Map(title.clef.map((item) => [item.keyword.toLocaleLowerCase(), item]));
        return [...title.jev]
          .sort((left, right) => left.rank - right.rank)
          .map((item) => {
            const clef = clefBy.get(item.keyword.toLocaleLowerCase());
            return [
              csvCell(title.title),
              csvCell(item.keyword),
              String(item.rank),
              item.score.toFixed(2),
              clef ? String(clef.rank) : "",
              clef ? clef.score.toFixed(2) : "",
              title.winner,
            ].join(",");
          });
      })
      .join("\n");
    const blob = new Blob([`${header}\n${body}`], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "jev-clef-comparison.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  const showEmpty = titles.length === 0 && !busy && !error;

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10">
      <header className="max-w-3xl">
        <Badge>Jev and Clef</Badge>
        <h1 className="font-display mt-4 text-5xl tracking-tight">Compare rankings</h1>
        <p className="mt-3 text-ink/70">
          Upload titles and the keywords you already have. Jev and Clef score the same candidates, and rank 1 is the highest score for that title. This page does not write new keywords.
        </p>
      </header>

      <Card>
        <CardContent className="space-y-4 pt-6">
          <div>
            <CardTitle>Keyword CSV</CardTitle>
            <p className="mt-1 max-w-2xl text-sm text-ink/55">
              One row per candidate. About 2,000 rows is fine. Headers such as title, Product Title, or product name, plus keyword, Product Keyword, or search keyword.
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
              if (file) void readFile(file);
            }}
          >
            <span className="font-display text-2xl tracking-tight">{reading ? "Reading file…" : "Drop a CSV"}</span>
            <span className="mt-2 max-w-md text-sm text-ink/60">CSV or Excel. Blank rows and repeated keywords for the same title are skipped.</span>
            <span className="mt-4 rounded-full bg-ink px-4 py-2 text-sm text-white">Choose file</span>
            <input
              type="file"
              accept=".csv,.txt,.xlsx,.xls"
              className="sr-only"
              disabled={busy || reading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (file) void readFile(file);
              }}
            />
          </label>

          {parsed && (
            <div className="rounded-2xl bg-foam px-4 py-4 text-sm">
              <p className="font-medium">{parsed.fileName}</p>
              <div className="mt-3 grid grid-cols-3 gap-3">
                <Count label="Rows" value={parsed.row_count} />
                <Count label="Titles" value={parsed.title_count} />
                <Count label="Keywords" value={parsed.keyword_count} />
              </div>
              <p className="mt-3 text-ink/55">
                {parsed.batch_count.toLocaleString()} {parsed.batch_count === 1 ? "batch" : "batches"} of up to 64 questions. Jev and Clef run together on each batch.
              </p>
            </div>
          )}

          {fileError && <div className="rounded-2xl border border-coral/30 bg-coral/10 px-4 py-3 text-sm text-coral">{fileError}</div>}

          <div className="grid gap-3 lg:grid-cols-3">
            <label className="grid gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-ink/45">
              Cloudflare account ID
              <Input
                autoComplete="off"
                spellCheck={false}
                placeholder="Or leave blank to use .env"
                value={accountId}
                onChange={(event) => setAccountId(event.target.value)}
              />
            </label>
            <label className="grid gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-ink/45">
              Cloudflare API token
              <Input
                type="password"
                autoComplete="off"
                spellCheck={false}
                placeholder="Or leave blank to use .env"
                value={cloudflareToken}
                onChange={(event) => setCloudflareToken(event.target.value)}
              />
            </label>
            <label className="grid gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-ink/45">
              Jev API key
              <Input
                type="password"
                autoComplete="off"
                spellCheck={false}
                placeholder="Or leave blank to use .env"
                value={jevKey}
                onChange={(event) => setJevKey(event.target.value)}
              />
            </label>
          </div>

          <Button onClick={onCompare} disabled={busy || reading || !parsed}>
            {busy ? "Comparing…" : parsed ? `Run comparison · ${parsed.keyword_count.toLocaleString()} keywords` : "Run comparison"}
          </Button>
        </CardContent>
      </Card>

      <section className="space-y-4" aria-busy={busy}>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-ink/45">Results</p>
            <h2 className="font-display text-3xl tracking-tight">
              {titles.length > 0 ? `${titles.length.toLocaleString()} compared ${titles.length === 1 ? "title" : "titles"}` : "Jev beside Clef"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-ink/55">
              The CSV winner is same when both rank-1 keywords match. Otherwise it is the model with the higher rank-1 score. Equal scores are labeled jev.
            </p>
          </div>
          {titles.length > 0 && (
            <Button variant="outline" onClick={download}>
              Download CSV
            </Button>
          )}
        </div>

        {error && <div className="rounded-2xl border border-coral/30 bg-coral/10 px-4 py-3 text-sm text-coral">{error}</div>}

        {busy && progress && (
          <div className="space-y-2">
            <p className="text-sm text-ink/70">
              {progress.waiting ? "Scoring" : "Finished"} batch {progress.batch.toLocaleString()} of {progress.batches.toLocaleString()} with Jev and Clef · {progress.done.toLocaleString()} of {progress.total.toLocaleString()} keywords
              {elapsed > 0 ? ` · ${elapsed}s` : ""}
            </p>
            <div className="h-1.5 overflow-hidden rounded-full bg-ink/10">
              <div
                className="h-full rounded-full bg-coral transition-[width] duration-500"
                style={{ width: `${progress.total ? Math.round((progress.done / progress.total) * 100) : 0}%` }}
              />
            </div>
          </div>
        )}

        {showEmpty && (
          <div className="rounded-3xl border border-dashed border-ink/15 bg-white/40 px-6 py-16 text-center">
            <p className="font-display text-2xl tracking-tight">{parsed ? "Ready to compare" : "No comparison yet"}</p>
            <p className="mx-auto mt-2 max-w-md text-sm text-ink/55">
              {parsed
                ? "Run the comparison to see where the two models pick the same rank-1 keyword, and where they do not."
                : "Upload a CSV with titles and candidate keywords. Counts appear before anything is sent."}
            </p>
          </div>
        )}

        {titles.length > 0 && (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <SummaryCard label="Titles compared" value={summary.titles.toLocaleString()} detail="Fully scored on both models" />
              <SummaryCard
                label="Same rank 1"
                value={summary.same.toLocaleString()}
                detail={`${percent(summary.same, summary.titles)} of titles`}
              />
              <SummaryCard
                label="Disagree"
                value={summary.disagree.toLocaleString()}
                detail={`${percent(summary.disagree, summary.titles)} of titles`}
                emphasis
              />
              <Card className="h-full">
                <CardHeader>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink/45">Average score</p>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-[11px] uppercase tracking-[0.14em] text-ink/40">Jev</p>
                      <p className="font-display text-2xl tabular-nums">{summary.jevAverage.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] uppercase tracking-[0.14em] text-ink/40">Clef</p>
                      <p className="font-display text-2xl tabular-nums">{summary.clefAverage.toFixed(2)}</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-ink/55">Across every candidate</p>
                </CardContent>
              </Card>
              <SummaryCard label="Cost" value={formatUsd(summary.cost)} detail={costDetail(summary)} />
            </div>

            <Card>
              <CardHeader>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-coral">Disagreements</p>
                <CardTitle className="mt-2 text-3xl">
                  {disagreements.length === 0 ? "They agreed on every title" : `${disagreements.length.toLocaleString()} titles where rank 1 differs`}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {disagreements.length === 0 ? (
                  <p className="text-sm text-ink/60">Jev and Clef picked the same rank-1 keyword for every title scored so far.</p>
                ) : (
                  <div className="max-h-[32rem] overflow-auto">
                    <table className="w-full min-w-[40rem] text-left text-sm">
                      <thead className="text-[11px] uppercase tracking-[0.14em] text-ink/40">
                        <tr>
                          <th className="pb-2 pr-3 font-medium">Title</th>
                          <th className="pb-2 pr-3 font-medium">Jev best</th>
                          <th className="pb-2 pr-3 text-right font-medium">Score</th>
                          <th className="pb-2 pr-3 font-medium">Clef best</th>
                          <th className="pb-2 text-right font-medium">Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {disagreements.map((title) => {
                          const jev = title.jev[0];
                          const clef = title.clef[0];
                          return (
                            <tr key={title.title} className="border-t border-ink/5 bg-coral/5">
                              <td className="py-2.5 pr-3 font-medium">{title.title}</td>
                              <td className="py-2.5 pr-3">{jev?.keyword}</td>
                              <td className="py-2.5 pr-3 text-right tabular-nums">{jev ? jev.score.toFixed(2) : "—"}</td>
                              <td className="py-2.5 pr-3">{clef?.keyword}</td>
                              <td className="py-2.5 text-right tabular-nums">{clef ? clef.score.toFixed(2) : "—"}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink/45">Every title</p>
                  <CardTitle className="mt-2 text-3xl">Ranked lists side by side</CardTitle>
                </div>
                <Input
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setTitlePage(0);
                  }}
                  placeholder="Filter titles"
                  className="max-w-xs"
                />
              </CardHeader>
              <CardContent className="space-y-3">
                {visible.length === 0 && <p className="text-sm text-ink/55">No titles match that filter.</p>}
                {visible.map((title) => (
                  <TitleRow
                    key={title.title}
                    title={title}
                    open={openTitle === title.title}
                    onToggle={() => setOpenTitle((current) => (current === title.title ? null : title.title))}
                  />
                ))}
                {pageCount > 1 && (
                  <div className="flex items-center justify-between pt-2 text-sm text-ink/60">
                    <span>
                      {safePage * PAGE_SIZE + 1}–{Math.min(filtered.length, (safePage + 1) * PAGE_SIZE)} of {filtered.length.toLocaleString()}
                    </span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" disabled={safePage === 0} onClick={() => setTitlePage(safePage - 1)}>
                        Previous
                      </Button>
                      <Button variant="outline" size="sm" disabled={safePage >= pageCount - 1} onClick={() => setTitlePage(safePage + 1)}>
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </section>
    </main>
  );
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-ink/40">{label}</p>
      <p className="font-display mt-1 text-2xl tabular-nums">{value.toLocaleString()}</p>
    </div>
  );
}

function SummaryCard({ label, value, detail, emphasis = false }: { label: string; value: string; detail: string; emphasis?: boolean }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="h-full">
        <CardHeader>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink/45">{label}</p>
          <CardTitle className={cn("mt-2 text-3xl tabular-nums", emphasis && "text-coral")}>{value}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-ink/55">{detail}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function TitleRow({ title, open, onToggle }: { title: ComparedTitle; open: boolean; onToggle: () => void }) {
  const jev = title.jev[0];
  const clef = title.clef[0];
  return (
    <div className="rounded-2xl border border-ink/10 bg-white/60">
      <button type="button" className="flex w-full items-start justify-between gap-4 px-4 py-3 text-left" aria-expanded={open} onClick={onToggle}>
        <span>
          <span className="block font-medium">{title.title}</span>
          <span className="mt-1 block text-sm text-ink/55">
            Jev <span className={cn(!title.agree && "text-coral")}>{jev?.keyword}</span>
            <span className="mx-2 text-ink/30">·</span>
            Clef <span className={cn(!title.agree && "text-coral")}>{clef?.keyword}</span>
          </span>
        </span>
        <span className={cn("shrink-0 rounded-full px-3 py-1 text-xs", title.agree ? "bg-ink/5 text-ink/60" : "bg-coral/10 text-coral")}>
          {title.agree ? "Same rank 1" : "Disagree"}
        </span>
      </button>
      {open && (
        <div className="grid gap-4 border-t border-ink/5 px-4 py-4 lg:grid-cols-2">
          <RankTable label="Jev" rows={title.jev} />
          <RankTable label="Clef" rows={title.clef} />
        </div>
      )}
    </div>
  );
}

function RankTable({ label, rows }: { label: string; rows: RankedKeyword[] }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-ink/45">{label}</p>
      <table className="mt-2 w-full text-left text-sm">
        <thead className="text-[11px] uppercase tracking-[0.14em] text-ink/40">
          <tr>
            <th className="w-14 pb-2 font-medium">Rank</th>
            <th className="pb-2 font-medium">Keyword</th>
            <th className="w-16 pb-2 text-right font-medium">Score</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((item) => (
            <tr key={`${label}-${item.rank}-${item.keyword}`} className={cn("border-t border-ink/5", item.rank === 1 && "bg-coral/10")}>
              <td className={cn("py-2 pl-2", item.rank === 1 ? "font-medium text-coral" : "text-ink/45")}>{item.rank}</td>
              <td className="py-2 pr-3">{item.keyword}</td>
              <td className="py-2 pr-2 text-right tabular-nums text-ink/60">{item.score.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function percent(part: number, total: number) {
  if (!total) return "0%";
  return `${Math.round((part / total) * 100)}%`;
}

function formatUsd(value: number) {
  return `$${value.toFixed(4)}`;
}

function costDetail(summary: { jevCost: number; clefCost: number; estimated: boolean; jevEstimated: boolean; clefEstimated: boolean }) {
  const source =
    summary.jevEstimated && summary.clefEstimated
      ? "Estimated from request size"
      : summary.estimated
        ? "Partly estimated from request size"
        : "From API token usage";
  return `Jev ${formatUsd(summary.jevCost)} · Clef ${formatUsd(summary.clefCost)} · ${source}`;
}

function csvCell(value: string) {
  return `"${value.replaceAll('"', '""')}"`;
}
