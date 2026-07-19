"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { fetchPrincipal, Principal } from "@/lib/api";
import { AUTH_MODE, firebaseConfigured, observeUser, signIn, signOut } from "@/lib/auth";

const DEMO_EMAIL = "admin@venuesignal.com";

export default function AuthPanel({ onPrincipal }: { onPrincipal: (principal: Principal | null) => void }) {
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshPrincipal = useCallback(async () => {
    try {
      const verified = await fetchPrincipal();
      setPrincipal(verified);
      onPrincipal(verified);
      setError(null);
      return verified;
    } catch (reason: unknown) {
      setPrincipal(null);
      onPrincipal(null);
      throw reason;
    }
  }, [onPrincipal]);

  useEffect(() => {
    if (AUTH_MODE === "firebase") {
      return observeUser((user) => {
        if (user) void refreshPrincipal().catch(() => undefined);
        else {
          setPrincipal(null);
          onPrincipal(null);
        }
      });
    }
    const timeout = window.setTimeout(
      () => void refreshPrincipal().catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Identity could not be verified.");
      }),
      0,
    );
    return () => window.clearTimeout(timeout);
  }, [onPrincipal, refreshPrincipal]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
      await refreshPrincipal();
      setPassword("");
    } catch {
      setError("Unable to sign in. Check the demo credentials and try again.");
    } finally {
      setBusy(false);
    }
  }

  if (principal) {
    return (
      <div className="identity-card" aria-label="Verified application identity">
        <span aria-hidden="true">●</span>
        <span><strong>{principal.role === "CONTROLLER" ? "Demo Controller" : principal.displayName}</strong><small>{principal.role}</small></span>
        {principal.authMode === "firebase" && <button type="button" onClick={() => void signOut()}>Sign out</button>}
      </div>
    );
  }

  if (AUTH_MODE !== "firebase") {
    return <div className="identity-card pending"><span>○</span><strong>Checking local controller…</strong></div>;
  }

  return (
    <section className="auth-entry" aria-labelledby="demo-access-title">
      <div className="auth-intro">
        <span className="eyebrow">VenueSignal</span>
        <h2>AI-assisted incident intelligence for stadium operations.</h2>
        <p>AI proposes. Deterministic logic verifies. Humans decide.</p>
      </div>

      <form className="sign-in-form" onSubmit={submit} aria-label="Demo Controller sign in" aria-busy={busy}>
        <div className="sign-in-heading">
          <span aria-hidden="true">●</span>
          <div><h3 id="demo-access-title">Demo Controller Access</h3><p>Use the dedicated demo controller account to explore the complete golden scenario.</p></div>
        </div>

        <div className="demo-account-summary">
          <span>Demo account email</span>
          <strong>{DEMO_EMAIL}</strong>
          <small>Password provided in submission instructions.</small>
        </div>

        {!firebaseConfigured && <span role="alert">Demo sign-in is temporarily unavailable because authentication configuration is incomplete.</span>}
        <label htmlFor="controller-email">Email</label>
        <input id="controller-email" type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} />
        <label htmlFor="controller-password">Password</label>
        <input id="controller-password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
        <button type="submit" className="primary-button" disabled={busy || !firebaseConfigured} aria-live="polite">{busy ? "Signing in…" : "Sign in"}</button>
        <div className="sign-in-feedback" aria-live="polite">{error && <span role="alert">{error}</span>}</div>
        <p className="auth-note">VenueSignal uses Firebase Authentication. Demo access is provided only for hackathon evaluation.</p>
      </form>
    </section>
  );
}
