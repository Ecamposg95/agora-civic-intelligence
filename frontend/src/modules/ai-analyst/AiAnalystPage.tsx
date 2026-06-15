// frontend/src/modules/ai-analyst/AiAnalystPage.tsx
import { useState } from "react";

import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { PreviewBanner } from "@/components/modules/PreviewBanner";
import { Card } from "@/components/ui/Card";
import { AiIcon } from "@/components/ui/icons";
import { ask, type Answer } from "./client";
import { SUGGESTED } from "./fixtures";

interface Turn { role: "user" | "assistant"; text: string; sample?: boolean; }

export function AiAnalystPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(prompt: string) {
    if (!prompt.trim() || busy) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", text: prompt }]);
    setBusy(true);
    const ans: Answer = await ask(prompt);
    setTurns((t) => [...t, { role: "assistant", text: ans.text, sample: ans.sample }]);
    setBusy(false);
  }

  return (
    <AppLayout title="AI Analyst / Copiloto" crumb="Ciudadanía">
      <PageHeader
        eyebrow="Ciudadanía"
        title="AI Analyst"
        accent="Copiloto"
        subtitle="Consulta tus datos cívicos en lenguaje natural. Resúmenes, comparativos y lecturas territoriales bajo demanda."
      />
      <PreviewBanner note="Respuestas de muestra · Conecta Claude API para análisis en vivo." />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="reveal lg:col-span-2" style={{ animationDelay: "120ms" }}>
          <Card title="Copiloto" accentDot className="h-full">
            <div className="flex h-[440px] flex-col">
              <div className="flex-1 space-y-3 overflow-y-auto pr-1">
                {turns.length === 0 && (
                  <div className="grid h-full place-items-center text-center text-sm text-ink-faint">
                    <div>
                      <span className="metric-chip mx-auto mb-3 h-12 w-12 text-accent shadow-glow-accent">
                        <AiIcon width={24} height={24} />
                      </span>
                      <p className="text-ink-muted">Pregúntale al copiloto sobre tus datos.</p>
                      <p className="mt-1 text-xs text-ink-faint">
                        Usa una pregunta sugerida o escribe la tuya.
                      </p>
                    </div>
                  </div>
                )}
                {turns.map((t, i) =>
                  t.role === "user" ? (
                    <div key={i} className="flex justify-end">
                      <div className="max-w-[85%] rounded-2xl rounded-br-sm border border-accent/30 bg-accent/15 px-3.5 py-2.5 text-sm text-ink shadow-glow-accent">
                        {t.text}
                      </div>
                    </div>
                  ) : (
                    <div key={i} className="flex items-start gap-2.5">
                      <span className="metric-chip mt-0.5 h-7 w-7 shrink-0 text-accent">
                        <AiIcon width={15} height={15} />
                      </span>
                      <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-line bg-bg-sunken px-3.5 py-2.5 text-sm leading-relaxed text-ink-muted">
                        {t.text}
                        {t.sample && (
                          <span className="pill ml-2 border-state-warning/30 bg-state-warning/10 align-middle text-state-warning">
                            muestra
                          </span>
                        )}
                      </div>
                    </div>
                  ),
                )}
                {busy && (
                  <div className="flex items-center gap-2.5">
                    <span className="metric-chip mt-0.5 h-7 w-7 shrink-0 text-accent">
                      <AiIcon width={15} height={15} />
                    </span>
                    <div className="inline-flex items-center gap-1 rounded-2xl rounded-tl-sm border border-line bg-bg-sunken px-3.5 py-2.5 text-sm text-ink-faint">
                      <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-accent" />
                      Pensando…
                    </div>
                  </div>
                )}
              </div>

              <form
                className="mt-3 flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  send(input);
                }}
              >
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Escribe una pregunta…"
                  className="field-input flex-1"
                />
                <button
                  type="submit"
                  disabled={busy}
                  className="btn-primary shadow-glow-accent disabled:opacity-40"
                >
                  Enviar
                </button>
              </form>
            </div>
          </Card>
        </div>

        <div className="reveal" style={{ animationDelay: "200ms" }}>
          <Card title="Preguntas sugeridas" accentDot className="h-full">
            <div className="space-y-2.5">
              {SUGGESTED.map((q, i) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  disabled={busy}
                  className="reveal group flex w-full items-start gap-2.5 rounded-lg border border-line bg-bg-sunken px-3 py-2.5 text-left text-sm text-ink-muted transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:bg-panel-hover hover:text-ink disabled:opacity-40"
                  style={{ animationDelay: `${260 + i * 60}ms` }}
                >
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-accent transition-colors group-hover:bg-teal" />
                  {q}
                </button>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
