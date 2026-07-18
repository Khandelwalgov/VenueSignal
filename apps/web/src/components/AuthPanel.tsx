"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { fetchPrincipal, Principal } from "@/lib/api";
import { AUTH_MODE, firebaseConfigured, observeUser, signIn, signOut } from "@/lib/auth";

export default function AuthPanel({ onPrincipal }: { onPrincipal: (principal: Principal | null) => void }) {
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshPrincipal = useCallback(async () => {
    try {
      const verified = await fetchPrincipal();
      setPrincipal(verified);
      onPrincipal(verified);
      setError(null);
    } catch (reason: unknown) {
      setPrincipal(null);
      onPrincipal(null);
      if (AUTH_MODE !== "firebase") {
        setError(reason instanceof Error ? reason.message : "Identity could not be verified.");
      }
    }
  }, [onPrincipal]);

  useEffect(() => {
    if (AUTH_MODE === "firebase") {
      return observeUser((user) => {
        if (user) void refreshPrincipal();
        else {
          setPrincipal(null);
          onPrincipal(null);
        }
      });
    }
    const timeout = window.setTimeout(() => void refreshPrincipal(), 0);
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
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  if (principal) {
    return (
      <div className="identity-card" aria-label="Verified application identity">
        <span aria-hidden="true">●</span>
        <span><strong>{principal.displayName}</strong><small>{principal.role} · {principal.authMode}</small></span>
        {principal.authMode === "firebase" && <button type="button" onClick={() => void signOut()}>Sign out</button>}
      </div>
    );
  }

  if (AUTH_MODE !== "firebase") {
    return <div className="identity-card pending"><span>○</span><strong>Checking local controller…</strong></div>;
  }

  return (
    <form className="sign-in-form" onSubmit={submit} aria-label="Controller sign in">
      <strong>Controller sign in</strong>
      {!firebaseConfigured && <span role="alert">Firebase public configuration is incomplete.</span>}
      <label>Email<input type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      <button type="submit" disabled={busy || !firebaseConfigured}>{busy ? "Verifying…" : "Sign in"}</button>
      {error && <span role="alert">{error}</span>}
    </form>
  );
}
