"use client";

import { motion } from "framer-motion";
import { MODELS, PROVIDERS, type Keys, type Provider } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type Engine = "Fast" | Provider;

const ENGINE_COPY: Record<Engine, string> = {
  Fast: "On this machine. No API key.",
  Gemini: "Google",
  OpenAI: "GPT",
  Claude: "Anthropic",
};

export function ModelFields({
  engine,
  model,
  keys,
  includeFast = false,
  onEngine,
  onModel,
  onKeys,
  showRanker = false,
}: {
  engine: Engine;
  model: string;
  keys: Keys;
  includeFast?: boolean;
  showRanker?: boolean;
  onEngine: (value: Engine) => void;
  onModel: (value: string) => void;
  onKeys: (value: Keys) => void;
}) {
  const engines: Engine[] = includeFast ? ["Fast", ...PROVIDERS] : [...PROVIDERS];
  const keyName = engine === "OpenAI" ? "openai_key" : engine === "Claude" ? "anthropic_key" : "gemini_key";
  const placeholder =
    engine === "OpenAI" ? "sk-... or leave blank to use .env" : engine === "Claude" ? "sk-ant-... or leave blank to use .env" : "Gemini key, or leave blank to use .env";

  return (
    <div className="space-y-4 rounded-3xl border border-ink/10 bg-foam/80 p-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-ink/45">Provider</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {engines.map((item) => {
            const active = engine === item;
            return (
              <button
                key={item}
                type="button"
                onClick={() => onEngine(item)}
                className={cn(
                  "relative rounded-full px-4 py-2 text-sm transition",
                  active ? "text-white" : "text-ink/70 hover:bg-white",
                )}
              >
                {active && (
                  <motion.span
                    layoutId={includeFast ? "engine-generate" : "engine-verify"}
                    className="absolute inset-0 rounded-full bg-ink"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                )}
                <span className="relative flex flex-col items-start leading-tight">
                  <span>{item}</span>
                  <span className={cn("text-[10px] uppercase tracking-[0.12em]", active ? "text-white/70" : "text-ink/40")}>
                    {ENGINE_COPY[item]}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {engine !== "Fast" && (
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-ink/45">Model</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {MODELS[engine].map((item) => {
              const active = model === item;
              return (
                <button
                  key={item}
                  type="button"
                  onClick={() => onModel(item)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-sm transition",
                    active
                      ? "border-coral bg-coral text-white shadow-[0_8px_20px_-12px_rgba(255,92,53,0.9)]"
                      : "border-ink/10 bg-white text-ink/75 hover:border-coral/40",
                  )}
                >
                  {item}
                </button>
              );
            })}
          </div>
          <label className="mt-4 grid gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-ink/45">
            API key
            <Input
              type="password"
              placeholder={placeholder}
              value={keys[keyName]}
              onChange={(event) => onKeys({ ...keys, [keyName]: event.target.value })}
            />
          </label>
          {showRanker && (
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-ink/45">
                Cloudflare account ID
                <Input
                  placeholder="Or leave blank to use .env"
                  value={keys.cloudflare_account_id ?? ""}
                  onChange={(event) => onKeys({ ...keys, cloudflare_account_id: event.target.value })}
                />
              </label>
              <label className="grid gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-ink/45">
                Cloudflare API token
                <Input
                  type="password"
                  placeholder="Workers AI token, or leave blank to use .env"
                  value={keys.cloudflare_api_token ?? ""}
                  onChange={(event) => onKeys({ ...keys, cloudflare_api_token: event.target.value })}
                />
              </label>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
