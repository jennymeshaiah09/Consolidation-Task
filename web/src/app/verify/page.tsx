"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { MODELS, verifyKeyword, type Keys, type Provider } from "@/lib/api";
import { ModelFields, type Engine } from "@/components/model-fields";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const emptyKeys: Keys = { gemini_key: "", openai_key: "", anthropic_key: "" };

export default function VerifyPage() {
  const [title, setTitle] = useState("Wireless Desk Lamp");
  const [keyword, setKeyword] = useState("northbeam desk lamp");
  const [provider, setProvider] = useState<Provider>("Gemini");
  const [model, setModel] = useState(MODELS.Gemini[0]);
  const [keys, setKeys] = useState<Keys>(emptyKeys);
  const [result, setResult] = useState<{ match: boolean; reason: string } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onCheck() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await verifyKeyword({ title, keyword, provider, model, keys }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Check failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <Badge>Quality check</Badge>
      <h1 className="font-display mt-4 text-5xl tracking-tight">Does this keyword fit?</h1>
      <p className="mt-3 text-ink/70">Compare one title with one search phrase. The model explains the match in a sentence.</p>
      <Card className="mt-8">
        <CardContent className="space-y-4 pt-6">
          <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Product title" />
          <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="Keyword" />
          <ModelFields
            engine={provider}
            model={model}
            keys={keys}
            onEngine={(next: Engine) => {
              if (next === "Fast") return;
              setProvider(next);
              setModel(MODELS[next][0]);
            }}
            onModel={setModel}
            onKeys={setKeys}
          />
          <Button onClick={onCheck} disabled={busy || !title || !keyword}>
            {busy ? "Checking…" : "Check keyword"}
          </Button>
          {error && <p className="text-sm text-coral">{error}</p>}
          {result && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className={`rounded-3xl p-6 ${result.match ? "bg-emerald-50 text-emerald-950" : "bg-coral/10 text-ink"}`}
            >
              <p className="text-xs uppercase tracking-[0.18em]">{result.match ? "Match" : "Not a fit"}</p>
              <p className="font-display mt-2 text-2xl">{result.reason}</p>
            </motion.div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
