import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Bumping this (e.g. the route path) resets the boundary on navigation. */
  resetKey?: string;
}
interface State {
  error: Error | null;
}

/**
 * Catches render-time exceptions in the page body so a single bad payload or
 * unexpected null degrades to a recoverable error card instead of white-screening
 * the whole SPA. The app shell (sidebar/topbar) stays mounted because this wraps
 * only `AppLayout`'s children.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Surface for debugging; never includes user PII (render errors are on shape).
    console.error("Render error in page:", error, info.componentStack);
  }

  componentDidUpdate(prev: Props): void {
    if (prev.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="mx-auto mt-10 max-w-lg rounded-card border border-line bg-panel p-6 text-center shadow-panel">
          <div className="metric-chip mx-auto h-12 w-12 text-state-critical shadow-glow">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            </svg>
          </div>
          <h2 className="mt-4 font-display text-lg font-bold text-ink">Algo salió mal en esta vista</h2>
          <p className="mt-2 text-sm text-ink-muted">
            No pudimos mostrar este módulo. El resto de la plataforma sigue disponible.
          </p>
          <button
            className="btn-primary mt-5"
            onClick={() => {
              this.setState({ error: null });
              window.location.reload();
            }}
          >
            Recargar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
