"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { TopBar } from "@/components/layout/top-bar";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiBaseUrl, authHeaders, getStoredToken } from "@/lib/auth-token";

type MeResponse = {
  id: string;
  email: string;
  full_name: string;
  preferred_phone_number: string | null;
  welcome_message_sent_at: string | null;
};

export default function SettingsPage() {
  const apiUrl = apiBaseUrl();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [phone, setPhone] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    const token = getStoredToken();
    if (!token) return;
    const res = await fetch(`${apiUrl}/api/v1/me`, { headers: authHeaders(token) as HeadersInit });
    if (!res.ok) return;
    const data = (await res.json()) as MeResponse;
    setMe(data);
    if (data.preferred_phone_number) setPhone(data.preferred_phone_number);
  }, [apiUrl]);

  useEffect(() => {
    void load();
  }, [load]);

  async function savePhone(e: FormEvent) {
    e.preventDefault();
    const token = getStoredToken();
    if (!token) return;
    setLoading(true);
    setStatus(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/me/phone`, {
        method: "PATCH",
        headers: { ...authHeaders(token), "Content-Type": "application/json" } as HeadersInit,
        body: JSON.stringify({ preferred_phone_number: phone.trim() }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        setStatus(body.detail || "Could not update phone.");
        return;
      }
      const data = (await res.json()) as MeResponse;
      setMe(data);
      setStatus("Phone saved. If the number changed, we sent a new introduction to iMessage.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <TopBar
        title="Settings"
        subtitle="Account and the phone number your OpsMesh AI agent uses in Photon / iMessage."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
            <CardDescription>Read-only details from your workspace account.</CardDescription>
          </CardHeader>
          <div className="flex flex-col gap-3 px-6 pb-6 text-sm">
            <p>
              <span className="text-muted">Name</span>
              <br />
              <span className="font-medium text-foreground">{me?.full_name ?? "—"}</span>
            </p>
            <p>
              <span className="text-muted">Email</span>
              <br />
              <span className="font-medium text-foreground">{me?.email ?? "—"}</span>
            </p>
            <p>
              <span className="text-muted">Welcome message</span>
              <br />
              <span className="font-medium text-foreground">
                {me?.welcome_message_sent_at
                  ? `Sent at ${new Date(me.welcome_message_sent_at).toLocaleString()}`
                  : "Not recorded yet"}
              </span>
            </p>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Agent phone number</CardTitle>
            <CardDescription>
              E.164 format with country code. This must match the device you use for iMessage with Photon.
            </CardDescription>
          </CardHeader>
          <form className="flex flex-col gap-4 px-6 pb-6" onSubmit={savePhone}>
            <label className="flex flex-col gap-2 text-sm">
              <span className="text-muted">Phone</span>
              <Input
                type="tel"
                autoComplete="tel"
                value={phone}
                onChange={(ev) => setPhone(ev.target.value)}
                required
                minLength={8}
                placeholder="+15551234567"
              />
            </label>
            {status ? <p className="text-sm text-muted">{status}</p> : null}
            <Button type="submit" disabled={loading}>
              {loading ? "Saving…" : "Save number"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
