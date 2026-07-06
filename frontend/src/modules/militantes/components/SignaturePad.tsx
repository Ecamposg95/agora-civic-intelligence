import { useEffect, useRef } from "react";

export function SignaturePad({ onChange }: { onChange: (b: Blob | null) => void }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  useEffect(() => {
    const c = ref.current!; const ctx = c.getContext("2d")!;
    c.width = c.offsetWidth; c.height = 180;
    ctx.lineWidth = 2.5; ctx.lineCap = "round"; ctx.strokeStyle = "#e8faff";
    const pos = (e: PointerEvent) => {
      const r = c.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    };
    const down = (e: PointerEvent) => { drawing.current = true; const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
    const move = (e: PointerEvent) => { if (!drawing.current) return; const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); };
    const up = () => { if (!drawing.current) return; drawing.current = false; c.toBlob((b) => onChange(b), "image/png"); };
    c.addEventListener("pointerdown", down); c.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => { c.removeEventListener("pointerdown", down); c.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
  }, [onChange]);
  const clear = () => { const c = ref.current!; c.getContext("2d")!.clearRect(0, 0, c.width, c.height); onChange(null); };
  return (
    <div>
      <canvas ref={ref} className="w-full touch-none rounded-lg border border-line bg-bg-sunken" />
      <button type="button" onClick={clear} className="mt-2 text-xs text-ink-muted hover:text-ink">Limpiar firma</button>
    </div>
  );
}
