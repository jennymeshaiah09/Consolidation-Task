"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { consolidateCatalog } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const steps = ["Upload", "Map", "Merge", "Peaks"];

export default function PipelinePage() {
  const [file, setFile] = useState<File | null>(null);
  const [productType, setProductType] = useState("General catalog");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Awaited<ReturnType<typeof consolidateCatalog>> | null>(null);

  async function onRun() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      setResult(await consolidateCatalog(file, productType, "Latest available"));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Could not consolidate");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-12">
      <Badge>Optional</Badge>
      <h1 className="font-display mt-4 text-5xl tracking-tight">Catalog pipeline</h1>
      <p className="mt-3 max-w-2xl text-ink/70">
        Upload a ZIP of monthly CSV or Excel files. Meridian matches the columns, picks a snapshot month, and builds one product master.
      </p>

      <div className="mt-8 grid gap-3 sm:grid-cols-4">
        {steps.map((step, index) => (
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            className="rounded-2xl border border-white/70 bg-white/70 px-4 py-3 text-sm backdrop-blur"
          >
            <span className="text-coral">0{index + 1}</span>
            <p className="font-display mt-1 text-lg">{step}</p>
          </motion.div>
        ))}
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Monthly files</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <select
              className="h-11 rounded-2xl border border-ink/10 bg-white/80 px-3 text-sm"
              value={productType}
              onChange={(event) => setProductType(event.target.value)}
            >
              {[
                "General catalog",
                "Alcoholic Beverages",
                "Pets",
                "Electronics",
                "Party & Celebration",
                "Toys",
                "Baby & Toddler",
                "Health & Beauty",
                "Sporting Goods",
                "Home & Garden",
                "Luggage & Bags",
                "Furniture",
                "Cameras & Optics",
                "Hardware",
              ].map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
            <a
              href="/api/sample"
              className="inline-flex h-11 items-center rounded-full border border-ink/10 bg-white/70 px-4 text-sm hover:bg-white"
            >
              Download sample ZIP
            </a>
            <input
              type="file"
              accept=".zip"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="text-sm file:mr-3 file:rounded-full file:border-0 file:bg-ink file:px-4 file:py-2 file:text-sm file:text-white"
            />
            <Button onClick={onRun} disabled={!file || busy}>
              {busy ? "Merging…" : "Consolidate"}
            </Button>
          </div>
          {error && <p className="text-sm text-coral">{error}</p>}
          {result?.warning && <p className="text-sm text-ink/70">{result.warning}</p>}
          {result && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <p className="text-sm text-ink/60">
                {result.total} products · months {result.months.join(", ") || "—"} · snapshot {result.snapshot}
              </p>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase tracking-[0.14em] text-ink/40">
                    <tr>
                      {result.preview[0] &&
                        Object.keys(result.preview[0]).map((key) => (
                          <th key={key} className="px-2 py-2 font-medium">
                            {key.replace("Product ", "")}
                          </th>
                        ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.preview.map((row, index) => (
                      <tr key={index} className="border-t border-ink/5">
                        {Object.values(row).map((value, cell) => (
                          <td key={cell} className="max-w-48 truncate px-2 py-2">
                            {value}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
