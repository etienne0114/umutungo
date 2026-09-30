"use client";

import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import type { AuthChangeEvent, AuthError, Session } from "@supabase/supabase-js";
import { getSupabaseBrowserClient, supabaseIsConfigured } from "@/lib/supabase/client";

type AuthStatus = "loading" | "signed_out" | "signed_in" | "misconfigured";
type AuthMode = "sign_in" | "register" | "reset_password" | "update_password" | "check_email";

export function AuthGate({
  children,
}: {
  children: (email: string, signOut: () => Promise<void>) => ReactNode;
}) {
  const [status, setStatus] = useState<AuthStatus>(() =>
    supabaseIsConfigured() ? "loading" : "misconfigured",
  );
  const [session, setSession] = useState<Session | null>(null);
  const [mode, setMode] = useState<AuthMode>("sign_in");
  const [signInError, setSignInError] = useState("");
  const [authMessage, setAuthMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!supabaseIsConfigured()) return;
    const supabase = getSupabaseBrowserClient();
    let active = true;
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(
      (event: AuthChangeEvent, nextSession: Session | null) => {
        if (!active) return;
        setSession(nextSession);
        setStatus(nextSession ? "signed_in" : "signed_out");
        if (event === "PASSWORD_RECOVERY") {
          setMode("update_password");
          setSignInError("");
          setAuthMessage("");
        }
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
      setAuthMessage("");
    } catch (error) {
      setSignInError(
        error instanceof Error ? error.message : "Sign-in failed. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "").trim();
    const password = String(formData.get("password") ?? "");
    const confirmPassword = String(formData.get("confirm_password") ?? "");
    if (password.length < 8) {
      setSignInError("Use a password with at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setSignInError("The passwords do not match.");
      return;
    }
    setBusy(true);
    setSignInError("");
    setAuthMessage("");
    try {
      const { data, error } = await getSupabaseBrowserClient().auth.signUp({
        email,
        password,
        options: { emailRedirectTo: window.location.origin },
      });
      if (error) throw error;
      if (data.session) {
        setSession(data.session);
        setStatus("signed_in");
        setMode("sign_in");
        setAuthMessage("Your account was created. API access is available after administrator approval.");
      } else {
        setMode("check_email");
        setAuthMessage(`Check ${email} for the confirmation link, then sign in. API access requires administrator approval.`);
      }
    } catch (error) {
      setSignInError(
        error instanceof Error ? error.message : "Account registration failed. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function requestPasswordReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = String(new FormData(event.currentTarget).get("email") ?? "").trim();
    setBusy(true);
    setSignInError("");
    setAuthMessage("");
    try {
      const { error } = await getSupabaseBrowserClient().auth.resetPasswordForEmail(email, {
        redirectTo: window.location.origin,
      });
      if (error) throw error;
      setMode("check_email");
      setAuthMessage(`If an account exists for ${email}, a password reset link has been sent.`);
    } catch (error) {
      setSignInError(
        error instanceof Error ? error.message : "Could not send a password reset link.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function updatePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const password = String(formData.get("password") ?? "");
    const confirmPassword = String(formData.get("confirm_password") ?? "");
    if (password.length < 8) {
      setSignInError("Use a password with at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setSignInError("The passwords do not match.");
      return;
    }
    setBusy(true);
    setSignInError("");
    try {
      const { error } = await getSupabaseBrowserClient().auth.updateUser({ password });
      if (error) throw error;
      setMode("sign_in");
      setAuthMessage("Your password has been updated. You can continue to the workspace.");
    } catch (error) {
      setSignInError(
        error instanceof Error ? error.message : "Could not update your password.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    const { error } = await getSupabaseBrowserClient().auth.signOut();
    if (error) throw error;
    setMode("sign_in");
    setAuthMessage("");
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

  if (mode === "update_password") {
    return (
      <main className="auth-screen">
        <section className="auth-card">
          <BrandMark />
          <div className="eyebrow">ACCOUNT SECURITY</div>
          <h1>Choose a new password</h1>
          <p>Set a new password for your Umutungo account.</p>
          <form className="form-stack auth-form" onSubmit={(event) => void updatePassword(event)}>
            <PasswordFields />
            {signInError && <p className="auth-error" role="alert">{signInError}</p>}
            <button className="button button-primary auth-submit" disabled={busy} type="submit">
              {busy ? "Updating…" : "Update password"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  if (mode === "check_email") {
    return (
      <main className="auth-screen">
        <section className="auth-card">
          <BrandMark />
          <div className="eyebrow">CHECK YOUR EMAIL</div>
          <h1>One more step</h1>
          <p role="status">{authMessage}</p>
          {signInError && <p className="auth-error" role="alert">{signInError}</p>}
          <button
            className="button button-primary auth-submit"
            onClick={() => {
              setMode("sign_in");
              setSignInError("");
              setAuthMessage("");
            }}
            type="button"
          >
            Back to sign in
          </button>
        </section>
      </main>
    );
  }

  if (status === "signed_out" || !session) {
    if (mode === "reset_password") {
      return (
        <main className="auth-screen">
          <section className="auth-card">
            <BrandMark />
            <div className="eyebrow">ACCOUNT RECOVERY</div>
            <h1>Reset your password</h1>
            <p>We&apos;ll email a password reset link to your account address.</p>
            <form className="form-stack auth-form" onSubmit={(event) => void requestPasswordReset(event)}>
              <label className="field">
                <span>Email address</span>
                <input autoComplete="email" name="email" required type="email" />
              </label>
              {signInError && <p className="auth-error" role="alert">{signInError}</p>}
              <button className="button button-primary auth-submit" disabled={busy} type="submit">
                {busy ? "Sending…" : "Send reset link"}
              </button>
            </form>
            <button className="auth-link" onClick={() => {
              setMode("sign_in");
              setSignInError("");
            }} type="button">Back to sign in</button>
          </section>
        </main>
      );
    }

    return (
      <main className="auth-screen">
        <section className="auth-card">
          <BrandMark />
          <div className="eyebrow">GOVERNMENT ASSET OPERATIONS</div>
          <h1>{mode === "register" ? "Create your account" : "Welcome back"}</h1>
          <p>
            {mode === "register"
              ? "Register with your work email. The project administrator must approve access before you can use the API."
              : "Sign in with your Umutungo account. New accounts require administrator approval."}
          </p>
          <form
            className="form-stack auth-form"
            onSubmit={(event) => void (mode === "register" ? register(event) : signIn(event))}
          >
            <label className="field">
              <span>Email address</span>
              <input autoComplete="email" name="email" required type="email" />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                minLength={mode === "register" ? 8 : undefined}
                name="password"
                required
                type="password"
              />
            </label>
            {mode === "register" && (
              <label className="field">
                <span>Confirm password</span>
                <input autoComplete="new-password" minLength={8} name="confirm_password" required type="password" />
              </label>
            )}
            {signInError && <p className="auth-error" role="alert">{signInError}</p>}
            <button className="button button-primary auth-submit" disabled={busy} type="submit">
              {busy
                ? mode === "register" ? "Creating account…" : "Signing in…"
                : mode === "register" ? "Create account" : "Sign in"}
            </button>
          </form>
          {authMessage && <p className="auth-success" role="status">{authMessage}</p>}
          {mode === "sign_in" && (
            <button className="auth-link" onClick={() => {
              setMode("reset_password");
              setSignInError("");
              setAuthMessage("");
            }} type="button">Forgot password?</button>
          )}
          <p className="auth-footnote">
            {mode === "register" ? "Registration does not grant API access automatically." : "New here?"}{" "}
            <button className="auth-link inline" onClick={() => {
              setMode(mode === "register" ? "sign_in" : "register");
              setSignInError("");
              setAuthMessage("");
            }} type="button">
              {mode === "register" ? "Sign in" : "Create an account"}
            </button>
          </p>
        </section>
      </main>
    );
  }

  return children(session.user.email ?? "Signed-in user", signOut);
}

function PasswordFields() {
  return (
    <>
      <label className="field">
        <span>New password</span>
        <input autoComplete="new-password" minLength={8} name="password" required type="password" />
      </label>
      <label className="field">
        <span>Confirm new password</span>
        <input autoComplete="new-password" minLength={8} name="confirm_password" required type="password" />
      </label>
    </>
  );
}

function BrandMark() {
  return (
    <div className="auth-brand">
      <span className="brand-mark"><span>G</span></span>
      <span className="brand-name">Umutungo</span>
    </div>
  );
}
