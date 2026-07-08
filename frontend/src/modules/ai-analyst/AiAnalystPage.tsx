// frontend/src/modules/ai-analyst/AiAnalystPage.tsx
import { useState } from "react";

import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { PreviewBanner } from "@/components/modules/PreviewBanner";
import { Avatar } from "@/components/ui/Avatar";
import { Card } from "@/components/ui/Card";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { AiIcon } from "@/components/ui/icons";
import { PANEL_HEIGHTS } from "@/constants/ui";
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
    try {
      const ans: Answer = await ask(prompt);
      setTurns((t) => [...t, { role: "assistant", text: ans.text, sample: ans.sample }]);
    } finally {
      setBusy(false);
    }
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

      <SectionHeading
        eyebrow="Copiloto"
        title="Conversación"
        note={turns.length > 0 ? `${turns.length} mensaje${turns.length === 1 ? "" : "s"}` : undefined}
      />

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="reveal lg:col-span-2" style={{ animationDelay: "120ms" }}>
          <Card title="Copiloto" accentDot className="h-full">
            <div className={`flex ${PANEL_HEIGHTS.copilot} flex-col`}>
              <div className="flex-1 space-y-3 overflow-y-auto pr-1">
                {turns.length === 0 && (
                  <div className="flex h-full flex-col items-center justify-center gap-4 px-4 text-center">
                    <span className="metric-chip h-14 w-14 text-warm shadow-glow">
                      <AiIcon width={28} height={28} />
                    </span>
                    <div>
                      <p className="text-sm font-medium text-ink">Copiloto de Análisis Cívico</p>
                      <p className="mt-1 max-w-xs text-xs leading-relaxed text-ink-faint">
                        Consulta participación, cobertura territorial, auditoría y más en lenguaje natural.
                        Respuestas de muestra — conecta Claude API para análisis en vivo.
                      </p>
                    </div>
                    <div className="flex flex-wrap justify-center gap-2">
                      {SUGGESTED.map((q) => (
                        <button
                          key={q}
                          type="button"
                          disabled={busy}
                          onClick={() => send(q)}
                          className="focus-ring rounded-full border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs text-accent transition-colors hover:border-accent/60 hover:bg-accent/20 disabled:opacity-40"
                          aria-label={`Usar pregunta: ${q}`}
                        >
                          {q}
                        </button>
                      ))}
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
                      <div className="mt-0.5 shrink-0">
                        <Avatar initials="IA" variant="warm" />
                      </div>
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
                    <div className="mt-0.5 shrink-0">
                      <Avatar initials="IA" variant="warm" />
                    </div>
                    <div className="inline-flex items-center gap-1 rounded-2xl rounded-tl-sm border border-line bg-bg-sunken px-3.5 py-2.5 text-sm text-ink-faint">
                      <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-warm" />
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
                  className="focus-ring reveal group flex w-full items-start gap-2.5 rounded-lg border border-line bg-bg-sunken px-3 py-2.5 text-left text-sm text-ink-muted transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:bg-panel-hover hover:text-ink disabled:opacity-40"
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
