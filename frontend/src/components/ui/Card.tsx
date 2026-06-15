import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  raised?: boolean;
  className?: string;
}

export function Card({ title, action, children, raised, className }: CardProps) {
  return (
    <div
      className={`${raised ? "panel-raised" : "panel"} p-5${
        className ? ` ${className}` : ""
      }`}
    >
      {title && (
        <div className="mb-4 flex items-center justify-between">
          <span className="text-sm font-semibold tracking-tight text-ink">
            {title}
          </span>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
