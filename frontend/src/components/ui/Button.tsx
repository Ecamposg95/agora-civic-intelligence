import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  children: ReactNode;
}

const VARIANTS: Record<Variant, string> = {
  primary: "btn-primary",
  ghost: "btn-ghost",
};

export function Button({
  variant = "ghost",
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`${VARIANTS[variant]}${className ? ` ${className}` : ""}`}
      {...rest}
    >
      {children}
    </button>
  );
}
