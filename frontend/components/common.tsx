"use client";
import { AlertCircle, LoaderCircle, ScanLine } from "lucide-react";
import type { Mode } from "@/types";

export function Loading({
  text = "Loading your workspace…",
}: {
  text?: string;
}) {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={22} />
      <span>{text}</span>
    </div>
  );
}
export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="error-box" role="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
      {onRetry && <button onClick={onRetry}>Try again</button>}
    </div>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <ScanLine size={34} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function ModeBadge({ mode }: { mode: Mode }) {
  return (
    <span className={`badge mode-${mode}`}>
      Output mode:{" "}
      {mode === "trained"
        ? "Trained · experimental"
        : mode[0].toUpperCase() + mode.slice(1)}
    </span>
  );
}
export function PageTitle({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {action}
    </div>
  );
}
