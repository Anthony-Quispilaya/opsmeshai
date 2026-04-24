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
} from "@/lib/auth-token";

type RegisterResponse = {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    preferred_phone_number: string | null;
  };
};

export default function RegisterPage() {
  const router = useRouter();
  const apiUrl = apiBaseUrl();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
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
      const res = await fetch(`${apiUrl}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          password,
          full_name: fullName.trim(),
          preferred_phone_number: phone.trim(),
        }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        setError(body.detail || `Registration failed (${res.status})`);
        setLoading(false);
        return;
      }
      const data = (await res.json()) as RegisterResponse;
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
        <CardTitle>Create your workspace</CardTitle>
        <CardDescription>
          Your iMessage number is required: as soon as you sign up, we send a short introduction from your OpsMesh
          AI agent to that device via Photon.
        </CardDescription>
      </CardHeader>
      <form className="flex flex-col gap-4 px-6 pb-6" onSubmit={onSubmit}>
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-muted">Full name</span>
          <Input
            autoComplete="name"
            value={fullName}
            onChange={(ev) => setFullName(ev.target.value)}
            required
            minLength={2}
          />
        </label>
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
          <span className="text-muted">Password (min 8 characters)</span>
          <Input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(ev) => setPassword(ev.target.value)}
            required
            minLength={8}
          />
        </label>
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-muted">iMessage / SMS number (E.164, e.g. +15551234567)</span>
          <Input
            type="tel"
            autoComplete="tel"
            placeholder="+15551234567"
            value={phone}
            onChange={(ev) => setPhone(ev.target.value)}
            required
            minLength={8}
          />
        </label>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
        <Button type="submit" disabled={loading}>
          {loading ? "Creating account…" : "Create account & text my phone"}
        </Button>
        <p className="text-center text-xs text-muted">
          Already registered?{" "}
          <Link href="/login" className="text-accent-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </Card>
  );
}
