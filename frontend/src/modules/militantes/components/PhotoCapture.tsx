import { useState } from "react";
import { compressImage } from "../lib/image";

export function PhotoCapture({ label, onCapture }: { label: string; onCapture: (b: Blob | null) => void }) {
  const [preview, setPreview] = useState<string | null>(null);
  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (!f) return;
    const blob = await compressImage(f);
    setPreview(URL.createObjectURL(blob));
    onCapture(blob);
  };
  return (
    <div className="rounded-lg border border-line p-3">
      <span className="field-label">{label}</span>
      {preview ? (
        <img src={preview} alt={label} className="mt-2 max-h-40 rounded-lg" />
      ) : null}
      <label className="mt-2 flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-line py-6 text-sm text-ink-muted">
        {preview ? "Volver a tomar" : "Tomar foto"}
        <input type="file" accept="image/*" capture="environment" className="hidden" onChange={onFile} />
      </label>
    </div>
  );
}
