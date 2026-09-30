"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

export default function AuthCallbackPage() {
  const handled = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    async function completeAuthCallback() {
      const callbackUrl = new URL(window.location.href);
      const fragment = new URLSearchParams(callbackUrl.hash.slice(1));
      const providerError =
        callbackUrl.searchParams.get("error_description") ??
        callbackUrl.searchParams.get("error") ??
        fragment.get("error_description") ??
        fragment.get("error");
      if (providerError) {
        setError(providerError);
        return;
      }

      const supabase = getSupabaseBrowserClient();
      const code = callbackUrl.searchParams.get("code");
      if (code) {
        const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
        if (exchangeError) {
          setError(exchangeError.message);
          return;
        }
      } else {
        const { error: sessionError } = await supabase.auth.getSession();
        if (sessionError) {
          setError(sessionError.message);
          return;
        }
      }
      window.location.replace(
        callbackUrl.searchParams.get("flow") === "recovery"
          ? "/?password_recovery=1"
          : "/?email_confirmed=1",
      );
    }

    void completeAuthCallback().catch((callbackError: unknown) => {
      setError(
        callbackError instanceof Error
          ? callbackError.message
          : "Could not complete the email confirmation. Please return to sign in.",
      );
    });
  }, []);

  return (
    <main className="auth-screen">
      <section className="auth-card">
        <div className="auth-brand">
          <span className="brand-mark"><span>G</span></span>
          <span className="brand-name">Umutungo</span>
        </div>
        <div className="eyebrow">EMAIL CONFIRMATION</div>
        <h1>{error ? "Confirmation link could not be completed" : "Confirming your email"}</h1>
        {error ? (
          <>
            <p className="auth-error" role="alert">{error}</p>
            <Link className="button button-primary auth-submit" href="/">Return to sign in</Link>
          </>
        ) : (
          <p role="status">Your confirmation is being verified. You will be returned to this app shortly.</p>
        )}
      </section>
    </main>
  );
}
