// frontend/src/components/ui/Avatar.tsx

export type AvatarVariant = "brand" | "warm";

const VARIANT_STYLES: Record<AvatarVariant, string> = {
  brand: "bg-accent/15 text-accent",
  warm: "bg-warm/15 text-warm",
};

interface Props {
  /** Up to ~2 characters shown inside the avatar. */
  initials: string;
  variant?: AvatarVariant;
}

/** Rounded-square initials avatar, for dense table rows / lists. */
export function Avatar({ initials, variant = "brand" }: Props) {
  return (
    <span
      className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-semibold ${VARIANT_STYLES[variant]}`}
    >
      {initials}
    </span>
  );
}
