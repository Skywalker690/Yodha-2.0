"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Check,
  LockKeyhole,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/common";
import { post } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <main className="login-page">
      <section className="login-story">
        <div className="brand">
          <span className="brand-wordmark">Alzhio</span>
        </div>
        <div className="login-story-body">
          <div className="eyebrow">A LONGITUDINAL PERSPECTIVE</div>
          <h1>
            Every scan is a moment.
            <br />
            <em>See the whole story.</em>
          </h1>
          <p>
            A focused research workspace to explore brain structure, compare MRI
            visits, and understand change over time.
          </p>
          <div className="login-orbit">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <span className="login-orbit-wordmark">Alzhio</span>
            <span className="orbit-tag tag-one">
              <ScanLine size={15} /> Baseline
            </span>
            <span className="orbit-tag tag-two">
              <Check size={15} /> Follow-up
            </span>
            <span className="orbit-point" />
          </div>
        </div>
        <div className="login-bottom">
          <ShieldCheck size={17} /> Locally stored. Research focused.
        </div>
      </section>
      <section className="login-form-area">
        <div className="login-form-card">
          <span className="login-icon">
            <LockKeyhole size={24} />
          </span>
          <div className="eyebrow">RESEARCHER ACCESS</div>
          <h2>Welcome to your workspace</h2>
          <p>Sign in to continue your longitudinal research.</p>
          {error && <ErrorState message={error} />}
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setError("");
              setBusy(true);
              const form = new FormData(e.currentTarget);
              try {
                await post("/auth/login", {
                  email: form.get("email"),
                  password: form.get("password"),
                });
                router.push("/dashboard");
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Email address
              <input
                name="email"
                type="email"
                placeholder="researcher@neuropredict.local"
                defaultValue={process.env.NEXT_PUBLIC_LOCAL_LOGIN_EMAIL}
                autoComplete="username"
                required
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                placeholder="Enter your password"
                defaultValue={process.env.NEXT_PUBLIC_LOCAL_LOGIN_PASSWORD}
                autoComplete="current-password"
                required
              />
            </label>
            <Button className="full-width" type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in to workspace"}
              <ArrowRight size={17} />
            </Button>
          </form>
          <p className="login-help">
            Use the researcher account configured during local setup.
          </p>
          <div className="login-disclaimer">
            <ShieldCheck size={18} />
            <span>
              <strong>Research Prototype</strong>
              <br />
              Not a medical diagnosis. Independent validation and qualified
              review are required.
            </span>
          </div>
        </div>
      </section>
    </main>
  );
}
