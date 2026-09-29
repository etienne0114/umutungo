"use client";

import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import type { AuthChangeEvent, AuthError, Session } from "@supabase/supabase-js";
import { getSupabaseBrowserClient, supabaseIsConfigured } from "@/lib/supabase/client";

type AuthStatus = "loading" | "signed_out" | "signed_in" | "misconfigured";

export function AuthGate({
  children,
}: {
  children: (email: string, signOut: () => Promise<void>) => ReactNode;
}) {
  const [status, setStatus] = useState<AuthStatus>(() =>
    supabaseIsConfigured() ? "loading" : "misconfigured",
  );
  const [session, setSession] = useState<Session | null>(null);
  const [signInError, setSignInError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!supabaseIsConfigured()) return;
    const supabase = getSupabaseBrowserClient();
    let active = true;
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(
      (_event: AuthChangeEvent, nextSession: Session | null) => {
        if (!active) return;
        setSession(nextSession);
        setStatus(nextSession ? "signed_in" : "signed_out");
      },
    );
    void supabase.auth.getSession().then(
      (result: { data: { session: Session | null }; error: AuthError | null }) => {
        const { data, error } = result;
        if (!active) return;
        if (error) {
          setSignInError(error.message);
          setStatus("signed_out");
          return;
        }
        setSession(data.session);
        setStatus(data.session ? "signed_in" : "signed_out");
      },
    );
    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setBusy(true);
    setSignInError("");
    try {
      const { error } = await getSupabaseBrowserClient().auth.signInWithPassword({
        email: String(formData.get("email") ?? "").trim(),
        password: String(formData.get("password") ?? ""),
      });
      if (error) throw error;
    } catch (error) {
      setSignInError(
        error instanceof Error ? error.message : "Sign-in failed. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    const { error } = await getSupabaseBrowserClient().auth.signOut();
    if (error) throw error;
  }

  if (status === "loading") {
    return (
      <main className="auth-screen">
        <div className="auth-card auth-loading"><span className="spinner" /> Checking session…</div>
      </main>
    );
  }

  if (status === "misconfigured") {
    return (
      <main className="auth-screen">
        <section className="auth-card">
          <BrandMark />
          <div className="eyebrow">SETUP REQUIRED</div>
          <h1>Connect your Supabase project</h1>
          <p>
            Add <code>NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
            <code>NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY</code> to the web environment,
            then restart the frontend.
          </p>
        </section>
      </main>
    );
  }

  if (status === "signed_out" || !session) {
    return (
      <main className="auth-screen">
        <section className="auth-card">
          <BrandMark />
          <div className="eyebrow">GOVERNMENT ASSET OPERATIONS</div>
          <h1>Welcome back</h1>
          <p>Sign in with an account provisioned by your project administrator.</p>
          <form className="form-stack auth-form" onSubmit={(event) => void signIn(event)}>
            <label className="field">
              <span>Email address</span>
              <input autoComplete="username" name="email" required type="email" />
            </label>
            <label className="field">
              <span>Password</span>
              <input autoComplete="current-password" name="password" required type="password" />
            </label>
            {signInError && <p className="auth-error" role="alert">{signInError}</p>}
            <button className="button button-primary auth-submit" disabled={busy} type="submit">
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="auth-footnote">Access is invitation-only. New account registration is disabled.</p>
        </section>
      </main>
    );
  }

  return children(session.user.email ?? "Signed-in user", signOut);
}

function BrandMark() {
  return (
    <div className="auth-brand">
      <span className="brand-mark"><span>G</span></span>
      <span className="brand-name">GovAsset <span>Insight</span></span>
    </div>
  );
}
