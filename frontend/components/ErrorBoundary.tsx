"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (error) {
      return (
        this.props.fallback ?? (
          <div className="flex flex-col items-center gap-4 py-20 text-center">
            <p className="text-slate-700 font-medium">Something went wrong.</p>
            <p className="text-sm text-slate-500">{error.message}</p>
            <button
              onClick={this.reset}
              className="rounded-md border border-slate-300 px-4 py-1.5 text-sm hover:bg-slate-100"
            >
              Try again
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
