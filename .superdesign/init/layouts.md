# Layouts

## frontend/app/layout.tsx

```
import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "NeuroPredict AI | Longitudinal research",
  description:
    "A local workspace for longitudinal brain MRI research. Research prototype, not a medical diagnosis.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

```

## frontend/app/(workspace)/layout.tsx

```
import { Shell } from "@/components/shell";
export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Shell>{children}</Shell>;
}

```

## frontend/components/shell.tsx

```
"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  Brain,
  ChevronRight,
  FileText,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Menu,
  ScanLine,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { api, post } from "@/lib/api";
import { useResource } from "@/lib/use-resource";
import { Loading } from "./common";
import type { Health } from "@/types";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/patients", label: "Patients", icon: Users },
  { href: "/analysis", label: "MRI Analysis", icon: ScanLine },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [open, setOpen] = useState(false);
  const { data: health } = useResource<Health>("/health", 30000);
  useEffect(() => {
    api<{ email: string }>("/auth/me")
      .then((u) => setEmail(u.email))
      .catch(() => router.replace("/login"));
  }, [router]);
  if (!email)
    return (
      <div className="center-screen">
        <Loading text="Opening secure workspace…" />
      </div>
    );
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <Link href="/dashboard" className="brand">
          <span className="brand-mark">
            <Brain size={26} />
          </span>
          <span>
            NeuroPredict<span className="brand-ai">AI</span>
            <small>LONGITUDINAL INTELLIGENCE</small>
          </span>
        </Link>
        <button
          className="mobile-close"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        >
          <X />
        </button>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(({ href, label, icon: Icon }) => (
            <Link
              onClick={() => setOpen(false)}
              href={href}
              key={href}
              className={path.startsWith(href) ? "nav-item active" : "nav-item"}
            >
              <Icon size={19} />
              {label}
              {path.startsWith(href) && (
                <ChevronRight className="nav-arrow" size={15} />
              )}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <div>
              <ShieldCheck size={17} /> Local workspace
            </div>
            <p>Your scans stay on this machine.</p>
            <span>
              <i className="status-dot" />
              {health?.database === "connected"
                ? "Database connected"
                : "Checking connection"}
            </span>
          </div>
          <div className="research-label">
            <FlaskConical size={15} /> Research Prototype <span>v1.0</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-menu"
              aria-label="Open navigation"
              onClick={() => setOpen(true)}
            >
              <Menu />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>
              {nav.find((n) => path.startsWith(n.href))?.label ||
                "Patient review"}
            </strong>
          </div>
          <div className="topbar-right">
            <span className="online">
              <i className={health ? "status-dot" : "status-dot offline"} />
              {health ? "Local system online" : "Connecting"}
            </span>
            <span className="top-divider" />
            <span className="avatar">R</span>
            <div className="researcher">
              <strong>Researcher</strong>
              <small title={email}>{email}</small>
            </div>
            <button
              className="icon-button"
              aria-label="Sign out"
              onClick={async () => {
                await post("/auth/logout");
                router.replace("/login");
              }}
            >
              <LogOut size={17} />
            </button>
          </div>
        </header>
        <main id="main-content" className="main-content">
          {children}
          <footer className="footer">
            <span>
              <Activity size={14} /> NeuroPredict AI
            </span>
            <span>
              Research Prototype <b>·</b> Not a medical diagnosis
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}

```

