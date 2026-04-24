"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  apiBaseUrl,
  getStoredToken,
  setStoredToken,
  TOKEN_STORAGE_KEY,
} from "@/lib/auth-token";

type TokenResponse = {
  access_token: string;
  token_type: string;
};

export default function LoginPage() {
  const router = useRouter();
  const apiUrl = apiBaseUrl();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (getStoredToken()) router.replace("/");
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        setError(body.detail || `Sign-in failed (${res.status})`);
        setLoading(false);
        return;
      }
      const data = (await res.json()) as TokenResponse;
      setStoredToken(data.access_token);
      router.replace("/");
    } catch {
      setError(`Cannot reach the API at ${apiUrl}. Is the backend running?`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>
          Use the workspace account your team invited. Session is stored in{" "}
          <span className="font-mono text-xs">{TOKEN_STORAGE_KEY}</span> on this device.
        </CardDescription>
      </CardHeader>
      <form className="flex flex-col gap-4 px-6 pb-6" onSubmit={onSubmit}>
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-muted">Work email</span>
          <Input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(ev) => setEmail(ev.target.value)}
            required
          />
        </label>
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-muted">Password</span>
          <Input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(ev) => setPassword(ev.target.value)}
            required
            minLength={8}
          />
        </label>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
        <Button type="submit" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </Button>
        <p className="text-center text-xs text-muted">
          New to OpsMeshAI?{" "}
          <Link href="/register" className="text-accent-foreground underline-offset-4 hover:underline">
            Create an account
          </Link>
        </p>
      </form>
    </Card>
  );
}
