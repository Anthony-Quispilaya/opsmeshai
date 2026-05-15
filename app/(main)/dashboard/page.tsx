"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { TopBar } from "@/components/layout/top-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiBaseUrl, authHeaders, getStoredToken } from "@/lib/auth-token";

// ─── Types ────────────────────────────────────────────────────────────────────

type MeResponse = {
  id: string; email: string; full_name: string;
  preferred_phone_number: string | null; welcome_message_sent_at: string | null;
};
type DashboardSummary = {
  user_email: string; active_threads: number; total_messages: number; backend_status: string;
  total_transactions: number; flagged_transactions: number;
  open_support_tickets: number; pending_compliance_items: number;
};
type Transaction = {
  id: string; amount: number; merchant: string; item_name: string | null; location: string;
  category: string; risk_score: number; flagged: boolean; notes: string | null; source: string; created_at: string;
};
type SupportTicket = {
  id: string; customer_identifier: string | null; description: string;
  category: string; status: string; priority: string; created_at: string;
};
type ComplianceRecord = {
  id: string; record_type: string; description: string; status: string;
  policy_flag: boolean; severity: string | null; created_at: string;
};
type AuditLog = {
  id: string; event_type: string; domain: string;
  action_taken: string; source: string; created_at: string;
};
type AgentAction = {
  id: string; title: string; description: string; domain: string;
  action_type: string; entity_type: string; entity_id: string | null;
  status: string; priority: string; confidence: number; rationale: string | null;
  created_at: string; resolved_at: string | null;
};
type AutomationRule = {
  id: string; name: string; description: string; domain: string;
  trigger_type: string; conditions: Record<string, unknown>;
  action_type: string; enabled: boolean; created_at: string; last_run_at: string | null;
};
type Insights = {
  summary: string; flagged_transactions: number; open_tickets: number;
  pending_compliance: number; highest_risk_amount: number | null;
  highest_risk_merchant: string | null; top_ticket_category: string | null;
};
type DailyBriefing = {
  generated_at: string; summary: string; highlights: string[]; recommended_actions: string[];
};

// ─── Filter state types ───────────────────────────────────────────────────────

type TxFilters    = { flagged: "all"|"yes"|"no"; risk: "all"|"low"|"medium"|"high"; category: string; source: string };
type TkFilters    = { status: "all"|"open"|"in_review"|"resolved"; priority: "all"|"high"|"medium"|"low"; category: string };
type CrFilters    = { status: "all"|"pending"|"approved"|"rejected"; severity: "all"|"high"|"medium"|"low"; policy_flag: "all"|"yes"|"no" };
type OpsTab = "transactions"|"support"|"compliance";
type TransactionForm = {
  merchant: string; item_name: string; amount: string; location: string; category: string;
  risk_score: string; flagged: boolean; notes: string;
};
type SupportForm = {
  description: string; category: string; priority: "low"|"medium"|"high";
  status: "open"|"in_review"|"resolved"; customer_identifier: string;
};
type ComplianceForm = {
  description: string; record_type: string; status: "pending"|"approved"|"rejected";
  policy_flag: boolean; severity: "low"|"medium"|"high"; recommendation: string;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

const riskColor  = (s: number) => s >= 71 ? "text-red-400" : s >= 31 ? "text-yellow-400" : "text-success";
const riskLabel  = (s: number) => s >= 71 ? "high" : s >= 31 ? "medium" : "low";
const statusColor = (s: string) =>
  s === "open" ? "text-yellow-400" : s === "in_review" ? "text-blue-400" : s === "resolved" ? "text-success" : "text-muted";
const priorityColor = (p: string) =>
  p === "high" ? "text-red-400" : p === "medium" ? "text-yellow-400" : "text-muted";
const severityColor = (s: string | null) =>
  s === "high" ? "text-red-400" : s === "medium" ? "text-yellow-400" : "text-muted";
const fmt    = (iso: string) => new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
const fmtCat = (s: string)   => s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

// ─── Filter pill component ────────────────────────────────────────────────────

function FilterPills<T extends string>({
  label, options, value, onChange,
}: { label: string; options: { value: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-xs text-muted mr-1 shrink-0">{label}:</span>
      {options.map(o => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
            value === o.value
              ? "bg-accent/20 text-accent-foreground border border-accent/40"
              : "bg-surface-elevated/60 text-muted hover:text-foreground border border-transparent"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function FilterSelect({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-muted shrink-0">{label}:</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="rounded border border-border/20 bg-surface-elevated px-2 py-0.5 text-xs text-foreground outline-none focus:border-accent/40"
      >
        <option value="all">All</option>
        {options.map(o => <option key={o} value={o}>{fmtCat(o)}</option>)}
      </select>
    </div>
  );
}

function ActiveCount({ shown, total }: { shown: number; total: number }) {
  if (shown === total) return <span className="text-xs text-muted">{total} records</span>;
  return <span className="text-xs text-muted">{shown} of {total} records</span>;
}

const agentExamples: Record<OpsTab, { label: string; examples: string[] }> = {
  transactions: {
    label: "Transaction commands",
    examples: [
      "Are you active?",
      "Show me high-risk transactions",
      "Spent 120 at Amazon in NJ",
      "Why was the Apple Store transaction flagged?",
      "Update the Amazon transaction category to electronics",
      "Delete the Walmart transaction",
    ],
  },
  support: {
    label: "Support ticket commands",
    examples: [
      "What open support tickets need attention?",
      "Create a support ticket: Maria cannot log in after password reset",
      "Mark the Maria login ticket as resolved",
      "Escalate the duplicate charge ticket to high priority",
      "List payment failure tickets",
      "Delete the refund delay ticket",
    ],
  },
  compliance: {
    label: "Compliance commands",
    examples: [
      "What pending compliance records do we have?",
      "Add a compliance note for missing receipt on reimbursement",
      "Approve the compliance record about missing receipt",
      "Reject the premium seat reimbursement record",
      "List policy-flagged compliance items",
      "Run a risk analysis across compliance and tickets",
    ],
  },
};

const initialTxForm: TransactionForm = {
  merchant: "", item_name: "", amount: "", location: "", category: "retail", risk_score: "", flagged: false, notes: "",
};
const initialSupportForm: SupportForm = {
  description: "", category: "general", priority: "medium", status: "open", customer_identifier: "",
};
const initialComplianceForm: ComplianceForm = {
  description: "", record_type: "general", status: "pending", policy_flag: false, severity: "low", recommendation: "",
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function HomePage() {
  const apiUrl = apiBaseUrl();

  // Data
  const [me, setMe]               = useState<MeResponse | null>(null);
  const [summary, setSummary]     = useState<DashboardSummary | null>(null);
  const [transactions, setTx]     = useState<Transaction[]>([]);
  const [tickets, setTickets]     = useState<SupportTicket[]>([]);
  const [compliance, setCompliance] = useState<ComplianceRecord[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [agentActions, setAgentActions] = useState<AgentAction[]>([]);
  const [automationRules, setAutomationRules] = useState<AutomationRule[]>([]);
  const [insights, setInsights]   = useState<Insights | null>(null);
  const [dailyBriefing, setDailyBriefing] = useState<DailyBriefing | null>(null);

  // UI
  const [activeTab, setTab] = useState<OpsTab>("transactions");
  const [error, setError]   = useState<string | null>(null);
  const [welcomeLoading, setWelcomeLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [automationLoading, setAutomationLoading] = useState<string | null>(null);

  // Filters — transactions
  const [txF, setTxF] = useState<TxFilters>({ flagged: "all", risk: "all", category: "all", source: "all" });
  const [txSearch, setTxSearch] = useState("");
  // Filters — support tickets
  const [tkF, setTkF] = useState<TkFilters>({ status: "all", priority: "all", category: "all" });
  const [tkSearch, setTkSearch] = useState("");
  // Filters — compliance
  const [crF, setCrF] = useState<CrFilters>({ status: "all", severity: "all", policy_flag: "all" });
  const [crSearch, setCrSearch] = useState("");
  // Manual dashboard entry forms
  const [txForm, setTxForm] = useState<TransactionForm>(initialTxForm);
  const [supportForm, setSupportForm] = useState<SupportForm>(initialSupportForm);
  const [complianceForm, setComplianceForm] = useState<ComplianceForm>(initialComplianceForm);
  const [manualLoading, setManualLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = getStoredToken();
    if (!token) return;
    setError(null);
    const h = { ...authHeaders(token), "Content-Type": "application/json" } as HeadersInit;

    const [meRes, sumRes, txRes, tkRes, cpRes, logRes, actRes, ruleRes, briefRes, insRes] = await Promise.all([
      fetch(`${apiUrl}/api/v1/me`, { headers: h }),
      fetch(`${apiUrl}/api/v1/dashboard/summary`, { headers: h }),
      fetch(`${apiUrl}/api/v1/ops/transactions?limit=200`, { headers: h }),
      fetch(`${apiUrl}/api/v1/ops/support-tickets?limit=200`, { headers: h }),
      fetch(`${apiUrl}/api/v1/ops/compliance?limit=200`, { headers: h }),
      fetch(`${apiUrl}/api/v1/ops/audit-logs?limit=15`, { headers: h }),
      fetch(`${apiUrl}/api/v1/ops/agent-actions?limit=8&status=pending`, { headers: h }),
      fetch(`${apiUrl}/api/v1/ops/automation-rules`, { headers: h }),
      fetch(`${apiUrl}/api/v1/ops/daily-briefing`, { headers: h }),
      fetch(`${apiUrl}/api/v1/ops/insights`, { headers: h }),
    ]);

    if (!meRes.ok) { setError("Could not load profile. Try signing in again."); return; }
    setMe((await meRes.json()) as MeResponse);
    if (sumRes.ok) setSummary((await sumRes.json()) as DashboardSummary);
    if (txRes.ok)  setTx((await txRes.json()) as Transaction[]);
    if (tkRes.ok)  setTickets((await tkRes.json()) as SupportTicket[]);
    if (cpRes.ok)  setCompliance((await cpRes.json()) as ComplianceRecord[]);
    if (logRes.ok) setAuditLogs((await logRes.json()) as AuditLog[]);
    if (actRes.ok) setAgentActions((await actRes.json()) as AgentAction[]);
    if (ruleRes.ok) setAutomationRules((await ruleRes.json()) as AutomationRule[]);
    if (briefRes.ok) setDailyBriefing((await briefRes.json()) as DailyBriefing);
    if (insRes.ok) setInsights((await insRes.json()) as Insights);
  }, [apiUrl]);

  useEffect(() => { void load(); }, [load]);

  // ── Derived filter options from data ────────────────────────────────────────

  const txCategories = useMemo(() => [...new Set(transactions.map(t => t.category))].sort(), [transactions]);
  const txSources    = useMemo(() => [...new Set(transactions.map(t => t.source))].sort(), [transactions]);
  const tkCategories = useMemo(() => [...new Set(tickets.map(t => t.category))].sort(), [tickets]);

  // ── Filtered data ────────────────────────────────────────────────────────────

  const visibleTx = useMemo(() => transactions.filter(t => {
    if (txF.flagged   === "yes" && !t.flagged) return false;
    if (txF.flagged   === "no"  && t.flagged)  return false;
    if (txF.risk !== "all" && riskLabel(t.risk_score) !== txF.risk) return false;
    if (txF.category !== "all" && t.category !== txF.category) return false;
    if (txF.source   !== "all" && t.source   !== txF.source)   return false;
    if (txSearch) {
      const q = txSearch.toLowerCase();
      if (!`${t.merchant} ${t.item_name ?? ""} ${t.notes ?? ""} ${t.location} ${t.category} ${t.source}`.toLowerCase().includes(q)) return false;
    }
    return true;
  }), [transactions, txF, txSearch]);

  const visibleTk = useMemo(() => tickets.filter(t => {
    if (tkF.status   !== "all" && t.status   !== tkF.status)   return false;
    if (tkF.priority !== "all" && t.priority !== tkF.priority) return false;
    if (tkF.category !== "all" && t.category !== tkF.category) return false;
    if (tkSearch) {
      const q = tkSearch.toLowerCase();
      if (!`${t.description} ${t.category} ${t.customer_identifier ?? ""}`.toLowerCase().includes(q)) return false;
    }
    return true;
  }), [tickets, tkF, tkSearch]);

  const visibleCr = useMemo(() => compliance.filter(r => {
    if (crF.status      !== "all" && r.status            !== crF.status)   return false;
    if (crF.severity    !== "all" && (r.severity ?? "low") !== crF.severity) return false;
    if (crF.policy_flag === "yes" && !r.policy_flag) return false;
    if (crF.policy_flag === "no"  && r.policy_flag)  return false;
    if (crSearch) {
      const q = crSearch.toLowerCase();
      if (!`${r.description} ${r.record_type}`.toLowerCase().includes(q)) return false;
    }
    return true;
  }), [compliance, crF, crSearch]);

  // ── Helpers ──────────────────────────────────────────────────────────────────

  const introSent = Boolean(me?.welcome_message_sent_at);
  const currentAgentExamples = agentExamples[activeTab];

  const resetTxF = () => setTxF({ flagged: "all", risk: "all", category: "all", source: "all" });
  const resetTkF = () => setTkF({ status: "all", priority: "all", category: "all" });
  const resetCrF = () => setCrF({ status: "all", severity: "all", policy_flag: "all" });

  const anyTxActive = txF.flagged !== "all" || txF.risk !== "all" || txF.category !== "all" || txF.source !== "all";
  const anyTkActive = tkF.status  !== "all" || tkF.priority !== "all" || tkF.category !== "all";
  const anyCrActive = crF.status  !== "all" || crF.severity !== "all" || crF.policy_flag !== "all";

  async function opsRequest(path: string, options: RequestInit = {}) {
    const token = getStoredToken();
    if (!token) return null;
    const res = await fetch(`${apiUrl}${path}`, {
      ...options,
      headers: {
        ...authHeaders(token),
        "Content-Type": "application/json",
        ...(options.headers || {}),
      } as HeadersInit,
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return res;
  }

  async function createTransaction(e: FormEvent) {
    e.preventDefault();
    setManualLoading("create-transaction"); setError(null);
    try {
      await opsRequest("/api/v1/ops/transactions", {
        method: "POST",
        body: JSON.stringify({
          merchant: txForm.merchant.trim(),
          item_name: txForm.item_name.trim() || null,
          amount: Number(txForm.amount),
          location: txForm.location.trim() || "Unknown",
          category: txForm.category.trim() || "retail",
          risk_score: txForm.risk_score ? Number(txForm.risk_score) : undefined,
          flagged: txForm.flagged,
          notes: txForm.notes.trim() || null,
        }),
      });
      setTxForm(initialTxForm);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add transaction.");
    } finally { setManualLoading(null); }
  }

  async function updateTransaction(id: string, body: Partial<Transaction>) {
    setManualLoading(id); setError(null);
    try {
      await opsRequest(`/api/v1/ops/transactions/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update transaction.");
    } finally { setManualLoading(null); }
  }

  async function deleteTransaction(id: string) {
    setManualLoading(id); setError(null);
    try {
      await opsRequest(`/api/v1/ops/transactions/${id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete transaction.");
    } finally { setManualLoading(null); }
  }

  async function createSupportTicket(e: FormEvent) {
    e.preventDefault();
    setManualLoading("create-support"); setError(null);
    try {
      await opsRequest("/api/v1/ops/support-tickets", {
        method: "POST",
        body: JSON.stringify({
          description: supportForm.description.trim(),
          category: supportForm.category.trim() || "general",
          status: supportForm.status,
          priority: supportForm.priority,
          customer_identifier: supportForm.customer_identifier.trim() || null,
        }),
      });
      setSupportForm(initialSupportForm);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add support ticket.");
    } finally { setManualLoading(null); }
  }

  async function updateSupportTicket(id: string, body: Partial<SupportTicket>) {
    setManualLoading(id); setError(null);
    try {
      await opsRequest(`/api/v1/ops/support-tickets/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update support ticket.");
    } finally { setManualLoading(null); }
  }

  async function deleteSupportTicket(id: string) {
    setManualLoading(id); setError(null);
    try {
      await opsRequest(`/api/v1/ops/support-tickets/${id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete support ticket.");
    } finally { setManualLoading(null); }
  }

  async function createComplianceRecord(e: FormEvent) {
    e.preventDefault();
    setManualLoading("create-compliance"); setError(null);
    try {
      await opsRequest("/api/v1/ops/compliance", {
        method: "POST",
        body: JSON.stringify({
          description: complianceForm.description.trim(),
          record_type: complianceForm.record_type.trim() || "general",
          status: complianceForm.status,
          policy_flag: complianceForm.policy_flag,
          severity: complianceForm.severity,
          recommendation: complianceForm.recommendation.trim() || null,
        }),
      });
      setComplianceForm(initialComplianceForm);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add compliance record.");
    } finally { setManualLoading(null); }
  }

  async function updateComplianceRecord(id: string, body: Partial<ComplianceRecord>) {
    setManualLoading(id); setError(null);
    try {
      await opsRequest(`/api/v1/ops/compliance/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update compliance record.");
    } finally { setManualLoading(null); }
  }

  async function deleteComplianceRecord(id: string) {
    setManualLoading(id); setError(null);
    try {
      await opsRequest(`/api/v1/ops/compliance/${id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete compliance record.");
    } finally { setManualLoading(null); }
  }

  async function resendWelcome() {
    const token = getStoredToken();
    if (!token) return;
    setWelcomeLoading(true); setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/onboarding/welcome-imessage`, {
        method: "POST",
        headers: { ...authHeaders(token), "Content-Type": "application/json" } as HeadersInit,
      });
      const body = (await res.json().catch(() => ({}))) as { detail?: string; sent?: boolean; error_detail?: string };
      if (!res.ok) { setError(body.detail || "Could not send the welcome message."); return; }
      if (body.sent === false) { setError(body.error_detail || "Photon did not confirm delivery."); return; }
      await load();
    } finally { setWelcomeLoading(false); }
  }

  async function generateActions() {
    const token = getStoredToken();
    if (!token) return;
    setActionLoading("generate"); setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/ops/agent-actions/generate`, {
        method: "POST",
        headers: { ...authHeaders(token), "Content-Type": "application/json" } as HeadersInit,
      });
      if (!res.ok) { setError("Could not generate agent actions."); return; }
      await load();
    } finally { setActionLoading(null); }
  }

  async function resolveAction(id: string, decision: "approve" | "reject") {
    const token = getStoredToken();
    if (!token) return;
    setActionLoading(id); setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/ops/agent-actions/${id}/${decision}`, {
        method: "POST",
        headers: { ...authHeaders(token), "Content-Type": "application/json" } as HeadersInit,
        body: decision === "reject" ? JSON.stringify({ reason: "Rejected from dashboard" }) : undefined,
      });
      if (!res.ok) { setError(`Could not ${decision} action.`); return; }
      await load();
    } finally { setActionLoading(null); }
  }

  async function seedAutomationRules() {
    const token = getStoredToken();
    if (!token) return;
    setAutomationLoading("seed"); setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/ops/automation-rules/seed`, {
        method: "POST",
        headers: { ...authHeaders(token), "Content-Type": "application/json" } as HeadersInit,
      });
      if (!res.ok) { setError("Could not create automation rules."); return; }
      await load();
    } finally { setAutomationLoading(null); }
  }

  async function runAutomationRules() {
    const token = getStoredToken();
    if (!token) return;
    setAutomationLoading("run"); setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/ops/automation-rules/run`, {
        method: "POST",
        headers: { ...authHeaders(token), "Content-Type": "application/json" } as HeadersInit,
      });
      if (!res.ok) { setError("Could not run automation rules."); return; }
      await load();
    } finally { setAutomationLoading(null); }
  }

  return (
    <div className="flex flex-col gap-4">
      <TopBar
        title={me ? `Welcome, ${me.full_name}` : "Operations dashboard"}
        subtitle="Messaging-first AI workflow platform — transact, query, and analyze directly from your phone."
      />

      {error && (
        <p className="rounded-lg border border-border/20 bg-surface-elevated/40 px-4 py-3 text-sm text-red-300">{error}</p>
      )}

      {/* ── Overview cards ── */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Transactions",       value: summary?.total_transactions      ?? "—", hint: "Total records",   accent: false },
          { label: "Flagged",            value: summary?.flagged_transactions     ?? "—", hint: "Risk alerts",     accent: (summary?.flagged_transactions ?? 0) > 0 },
          { label: "Open Tickets",       value: summary?.open_support_tickets     ?? "—", hint: "Support queue",   accent: (summary?.open_support_tickets ?? 0) > 5 },
          { label: "Pending Compliance", value: summary?.pending_compliance_items ?? "—", hint: "Awaiting review", accent: (summary?.pending_compliance_items ?? 0) > 0 },
        ].map(s => (
          <Card key={s.label} className="p-5">
            <p className="text-xs uppercase tracking-wide text-muted">{s.label}</p>
            <p className={`mt-3 text-3xl font-semibold tracking-tight ${s.accent ? "text-red-400" : ""}`}>{String(s.value)}</p>
            <p className="mt-2 text-xs text-muted">{s.hint}</p>
          </Card>
        ))}
      </section>

      {/* ── Insights ── */}
      {insights && (
        <Card className="p-5">
          <p className="mb-2 text-xs uppercase tracking-wide text-muted">AI Insights</p>
          <p className="text-sm leading-relaxed">{insights.summary}</p>
          {insights.highest_risk_merchant && (
            <p className="mt-2 text-xs text-muted">
              Highest risk: <span className="text-red-400">${insights.highest_risk_amount?.toFixed(0)} at {insights.highest_risk_merchant}</span>
              {insights.top_ticket_category && (
                <> &nbsp;·&nbsp; Top ticket: <span className="text-yellow-400">{fmtCat(insights.top_ticket_category)}</span></>
              )}
            </p>
          )}
        </Card>
      )}

      {/* ── Daily briefing ── */}
      {dailyBriefing && (
        <Card className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-muted">Daily Briefing</p>
              <p className="text-sm leading-relaxed">{dailyBriefing.summary}</p>
            </div>
            <Badge tone="neutral">{fmt(dailyBriefing.generated_at)}</Badge>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Signals</p>
              <ul className="space-y-1.5 text-sm text-muted">
                {dailyBriefing.highlights.map(item => <li key={item}>{item}</li>)}
              </ul>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Next Actions</p>
              <ul className="space-y-1.5 text-sm text-muted">
                {dailyBriefing.recommended_actions.map(item => <li key={item}>{item}</li>)}
              </ul>
            </div>
          </div>
        </Card>
      )}

      {/* ── Tabbed tables ── */}
      <div>
        {/* Tab bar */}
        <div className="mb-3 flex gap-2">
          {(["transactions", "support", "compliance"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setTab(tab)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? "bg-surface-elevated text-foreground"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {tab === "transactions" ? "Transactions" : tab === "support" ? "Support Tickets" : "Compliance"}
            </button>
          ))}
        </div>

        {/* ── TRANSACTIONS ── */}
        {activeTab === "transactions" && (
          <>
          <Card className="mb-3 p-5">
            <form className="grid gap-3 lg:grid-cols-12" onSubmit={createTransaction}>
              <div className="lg:col-span-3">
                <p className="mb-1 text-xs text-muted">Merchant</p>
                <Input value={txForm.merchant} onChange={e => setTxForm(f => ({ ...f, merchant: e.target.value }))} required placeholder="Apple Store" />
              </div>
              <div className="lg:col-span-3">
                <p className="mb-1 text-xs text-muted">Item</p>
                <Input value={txForm.item_name} onChange={e => setTxForm(f => ({ ...f, item_name: e.target.value }))} placeholder="MacBook Pro" />
              </div>
              <div className="lg:col-span-2">
                <p className="mb-1 text-xs text-muted">Amount</p>
                <Input type="number" min="0.01" step="0.01" value={txForm.amount} onChange={e => setTxForm(f => ({ ...f, amount: e.target.value }))} required placeholder="2400" />
              </div>
              <div className="lg:col-span-2">
                <p className="mb-1 text-xs text-muted">Location</p>
                <Input value={txForm.location} onChange={e => setTxForm(f => ({ ...f, location: e.target.value }))} placeholder="Miami" />
              </div>
              <div className="lg:col-span-2">
                <p className="mb-1 text-xs text-muted">Category</p>
                <Input value={txForm.category} onChange={e => setTxForm(f => ({ ...f, category: e.target.value }))} placeholder="retail" />
              </div>
              <div className="lg:col-span-2">
                <p className="mb-1 text-xs text-muted">Risk</p>
                <Input type="number" min="0" max="100" value={txForm.risk_score} onChange={e => setTxForm(f => ({ ...f, risk_score: e.target.value }))} placeholder="auto" />
              </div>
              <label className="flex items-end gap-2 pb-2 text-sm lg:col-span-1">
                <input type="checkbox" checked={txForm.flagged} onChange={e => setTxForm(f => ({ ...f, flagged: e.target.checked }))} />
                Flag
              </label>
              <div className="flex items-end lg:col-span-1">
                <Button type="submit" className="w-full" disabled={manualLoading === "create-transaction"}>
                  {manualLoading === "create-transaction" ? "Adding..." : "Add"}
                </Button>
              </div>
              <div className="lg:col-span-12">
                <p className="mb-1 text-xs text-muted">Notes</p>
                <Input value={txForm.notes} onChange={e => setTxForm(f => ({ ...f, notes: e.target.value }))} placeholder="Receipt missing, manager approved, demo purchase, unusual amount..." />
              </div>
            </form>
          </Card>
          <Card className="overflow-hidden p-0">
            {/* Filter bar */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border/10 bg-surface-elevated/30 px-5 py-3">
              <input
                type="search"
                value={txSearch}
                onChange={e => setTxSearch(e.target.value)}
                placeholder="Search transactions..."
                className="h-7 w-48 rounded border border-border/20 bg-surface-elevated px-2.5 text-xs text-foreground placeholder:text-muted outline-none focus:border-accent/40"
              />
              <FilterPills
                label="Flagged"
                value={txF.flagged}
                onChange={v => setTxF(f => ({ ...f, flagged: v }))}
                options={[
                  { value: "all", label: "All" },
                  { value: "yes", label: "Flagged" },
                  { value: "no",  label: "Clean" },
                ]}
              />
              <FilterPills
                label="Risk"
                value={txF.risk}
                onChange={v => setTxF(f => ({ ...f, risk: v }))}
                options={[
                  { value: "all",    label: "All" },
                  { value: "high",   label: "High" },
                  { value: "medium", label: "Medium" },
                  { value: "low",    label: "Low" },
                ]}
              />
              {txCategories.length > 0 && (
                <FilterSelect
                  label="Category"
                  value={txF.category}
                  options={txCategories}
                  onChange={v => setTxF(f => ({ ...f, category: v }))}
                />
              )}
              {txSources.length > 1 && (
                <FilterSelect
                  label="Source"
                  value={txF.source}
                  options={txSources}
                  onChange={v => setTxF(f => ({ ...f, source: v }))}
                />
              )}
              <div className="ml-auto flex items-center gap-3">
                <ActiveCount shown={visibleTx.length} total={transactions.length} />
                {(anyTxActive || txSearch) && (
                  <button onClick={() => { resetTxF(); setTxSearch(""); }} className="text-xs text-accent-foreground hover:underline">
                    Clear filters
                  </button>
                )}
              </div>
            </div>
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/10">
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Merchant</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Item / Notes</th>
                    <th className="px-5 py-4 text-right text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Amount</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Location</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Category</th>
                    <th className="px-5 py-4 text-center text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Risk</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Date</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Source</th>
                    <th className="px-5 py-4 text-right text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleTx.length === 0 && (
                    <tr><td colSpan={9} className="px-5 py-10 text-center text-sm text-muted">No transactions match these filters.</td></tr>
                  )}
                  {visibleTx.map(tx => (
                    <tr key={tx.id} className="border-b border-border/5 hover:bg-surface-elevated/30">
                      <td className="px-5 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5 font-medium">
                          {tx.flagged && <span className="text-xs text-red-400">⚑</span>}
                          {tx.merchant}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="font-medium">{tx.item_name ?? "—"}</div>
                        {tx.notes && <div className="text-xs text-muted">{tx.notes}</div>}
                      </td>
                      <td className="px-5 py-4 whitespace-nowrap text-right font-mono tabular-nums">${tx.amount.toFixed(2)}</td>
                      <td className="px-5 py-4 whitespace-nowrap text-muted">{tx.location}</td>
                      <td className="px-5 py-4 whitespace-nowrap text-muted">{fmtCat(tx.category)}</td>
                      <td className="px-5 py-4 whitespace-nowrap text-center">
                        <span className={`text-xs font-semibold ${riskColor(tx.risk_score)}`}>{riskLabel(tx.risk_score)}</span>
                        <span className="ml-1 text-xs text-muted">({tx.risk_score})</span>
                      </td>
                      <td className="px-5 py-4 whitespace-nowrap text-xs text-muted">{fmt(tx.created_at)}</td>
                      <td className="px-5 py-4 whitespace-nowrap text-xs text-muted">{tx.source}</td>
                      <td className="px-5 py-4 whitespace-nowrap">
                        <div className="flex justify-end gap-1.5">
                          <Button
                            type="button"
                            variant="secondary"
                            className="h-7 px-2.5 text-xs"
                            onClick={() => void updateTransaction(tx.id, { flagged: !tx.flagged, risk_score: tx.flagged ? Math.min(tx.risk_score, 50) : Math.max(tx.risk_score, 65) })}
                            disabled={manualLoading === tx.id}
                          >
                            {tx.flagged ? "Unflag" : "Flag"}
                          </Button>
                          <Button
                            type="button"
                            variant="danger"
                            className="h-7 px-2.5 text-xs"
                            onClick={() => void deleteTransaction(tx.id)}
                            disabled={manualLoading === tx.id}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          </>
        )}

        {/* ── SUPPORT TICKETS ── */}
        {activeTab === "support" && (
          <>
          <Card className="mb-3 p-5">
            <form className="grid gap-3 lg:grid-cols-12" onSubmit={createSupportTicket}>
              <div className="lg:col-span-5">
                <p className="mb-1 text-xs text-muted">Issue</p>
                <Input value={supportForm.description} onChange={e => setSupportForm(f => ({ ...f, description: e.target.value }))} required placeholder="Customer says refund still not received" />
              </div>
              <div className="lg:col-span-2">
                <p className="mb-1 text-xs text-muted">Category</p>
                <Input value={supportForm.category} onChange={e => setSupportForm(f => ({ ...f, category: e.target.value }))} placeholder="refund_delay" />
              </div>
              <div className="lg:col-span-2">
                <p className="mb-1 text-xs text-muted">Priority</p>
                <select value={supportForm.priority} onChange={e => setSupportForm(f => ({ ...f, priority: e.target.value as SupportForm["priority"] }))} className="h-10 w-full rounded-md border border-border/10 bg-surface-elevated/40 px-3 py-2 text-sm">
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
              </div>
              <div className="lg:col-span-2">
                <p className="mb-1 text-xs text-muted">Customer</p>
                <Input value={supportForm.customer_identifier} onChange={e => setSupportForm(f => ({ ...f, customer_identifier: e.target.value }))} placeholder="Order 4832" />
              </div>
              <div className="flex items-end lg:col-span-1">
                <Button type="submit" className="w-full" disabled={manualLoading === "create-support"}>
                  {manualLoading === "create-support" ? "Adding..." : "Add"}
                </Button>
              </div>
            </form>
          </Card>
          <Card className="overflow-hidden p-0">
            {/* Filter bar */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border/10 bg-surface-elevated/30 px-5 py-3">
              <input
                type="search"
                value={tkSearch}
                onChange={e => setTkSearch(e.target.value)}
                placeholder="Search tickets..."
                className="h-7 w-48 rounded border border-border/20 bg-surface-elevated px-2.5 text-xs text-foreground placeholder:text-muted outline-none focus:border-accent/40"
              />
              <FilterPills
                label="Status"
                value={tkF.status}
                onChange={v => setTkF(f => ({ ...f, status: v }))}
                options={[
                  { value: "all",       label: "All" },
                  { value: "open",      label: "Open" },
                  { value: "in_review", label: "In Review" },
                  { value: "resolved",  label: "Resolved" },
                ]}
              />
              <FilterPills
                label="Priority"
                value={tkF.priority}
                onChange={v => setTkF(f => ({ ...f, priority: v }))}
                options={[
                  { value: "all",    label: "All" },
                  { value: "high",   label: "High" },
                  { value: "medium", label: "Medium" },
                  { value: "low",    label: "Low" },
                ]}
              />
              {tkCategories.length > 0 && (
                <FilterSelect
                  label="Category"
                  value={tkF.category}
                  options={tkCategories}
                  onChange={v => setTkF(f => ({ ...f, category: v }))}
                />
              )}
              <div className="ml-auto flex items-center gap-3">
                <ActiveCount shown={visibleTk.length} total={tickets.length} />
                {(anyTkActive || tkSearch) && (
                  <button onClick={() => { resetTkF(); setTkSearch(""); }} className="text-xs text-accent-foreground hover:underline">
                    Clear filters
                  </button>
                )}
              </div>
            </div>
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/10">
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Issue</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Category</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Status</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Priority</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Customer</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Created</th>
                    <th className="px-5 py-4 text-right text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleTk.length === 0 && (
                    <tr><td colSpan={7} className="px-5 py-10 text-center text-sm text-muted">No tickets match these filters.</td></tr>
                  )}
                  {visibleTk.map(tk => (
                    <tr key={tk.id} className="border-b border-border/5 hover:bg-surface-elevated/30">
                      <td className="px-5 py-4 font-medium">{tk.description}</td>
                      <td className="px-5 py-4 whitespace-nowrap text-muted">{fmtCat(tk.category)}</td>
                      <td className="px-5 py-4 whitespace-nowrap">
                        <span className={`text-xs font-semibold ${statusColor(tk.status)}`}>{fmtCat(tk.status)}</span>
                      </td>
                      <td className="px-5 py-4 whitespace-nowrap">
                        <span className={`text-xs font-semibold ${priorityColor(tk.priority)}`}>{tk.priority}</span>
                      </td>
                      <td className="px-5 py-4 whitespace-nowrap text-muted">{tk.customer_identifier ?? "—"}</td>
                      <td className="px-5 py-4 whitespace-nowrap text-xs text-muted">{fmt(tk.created_at)}</td>
                      <td className="px-5 py-4 whitespace-nowrap">
                        <div className="flex justify-end gap-1.5">
                          <Button
                            type="button"
                            variant="secondary"
                            className="h-7 px-2.5 text-xs"
                            onClick={() => void updateSupportTicket(tk.id, { status: tk.status === "resolved" ? "open" : "resolved" })}
                            disabled={manualLoading === tk.id}
                          >
                            {tk.status === "resolved" ? "Reopen" : "Resolve"}
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            className="h-7 px-2.5 text-xs"
                            onClick={() => void updateSupportTicket(tk.id, { priority: tk.priority === "high" ? "medium" : "high", status: tk.status === "resolved" ? "in_review" : tk.status })}
                            disabled={manualLoading === tk.id}
                          >
                            {tk.priority === "high" ? "Lower" : "Escalate"}
                          </Button>
                          <Button
                            type="button"
                            variant="danger"
                            className="h-7 px-2.5 text-xs"
                            onClick={() => void deleteSupportTicket(tk.id)}
                            disabled={manualLoading === tk.id}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          </>
        )}

        {/* ── COMPLIANCE ── */}
        {activeTab === "compliance" && (
          <>
          <Card className="mb-3 p-5">
            <form className="grid gap-3 lg:grid-cols-12" onSubmit={createComplianceRecord}>
              <div className="lg:col-span-5">
                <p className="mb-1 text-xs text-muted">Description</p>
                <Input value={complianceForm.description} onChange={e => setComplianceForm(f => ({ ...f, description: e.target.value }))} required placeholder="Missing receipt for reimbursement" />
              </div>
              <div className="lg:col-span-2">
                <p className="mb-1 text-xs text-muted">Type</p>
                <Input value={complianceForm.record_type} onChange={e => setComplianceForm(f => ({ ...f, record_type: e.target.value }))} placeholder="expense_policy" />
              </div>
              <div className="lg:col-span-2">
                <p className="mb-1 text-xs text-muted">Severity</p>
                <select value={complianceForm.severity} onChange={e => setComplianceForm(f => ({ ...f, severity: e.target.value as ComplianceForm["severity"] }))} className="h-10 w-full rounded-md border border-border/10 bg-surface-elevated/40 px-3 py-2 text-sm">
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
              </div>
              <label className="flex items-end gap-2 pb-2 text-sm lg:col-span-2">
                <input type="checkbox" checked={complianceForm.policy_flag} onChange={e => setComplianceForm(f => ({ ...f, policy_flag: e.target.checked }))} />
                Policy flag
              </label>
              <div className="flex items-end lg:col-span-1">
                <Button type="submit" className="w-full" disabled={manualLoading === "create-compliance"}>
                  {manualLoading === "create-compliance" ? "Adding..." : "Add"}
                </Button>
              </div>
              <div className="lg:col-span-12">
                <Input value={complianceForm.recommendation} onChange={e => setComplianceForm(f => ({ ...f, recommendation: e.target.value }))} placeholder="Optional recommendation" />
              </div>
            </form>
          </Card>
          <Card className="overflow-hidden p-0">
            {/* Filter bar */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border/10 bg-surface-elevated/30 px-5 py-3">
              <input
                type="search"
                value={crSearch}
                onChange={e => setCrSearch(e.target.value)}
                placeholder="Search compliance..."
                className="h-7 w-48 rounded border border-border/20 bg-surface-elevated px-2.5 text-xs text-foreground placeholder:text-muted outline-none focus:border-accent/40"
              />
              <FilterPills
                label="Status"
                value={crF.status}
                onChange={v => setCrF(f => ({ ...f, status: v }))}
                options={[
                  { value: "all",      label: "All" },
                  { value: "pending",  label: "Pending" },
                  { value: "approved", label: "Approved" },
                  { value: "rejected", label: "Rejected" },
                ]}
              />
              <FilterPills
                label="Severity"
                value={crF.severity}
                onChange={v => setCrF(f => ({ ...f, severity: v }))}
                options={[
                  { value: "all",    label: "All" },
                  { value: "high",   label: "High" },
                  { value: "medium", label: "Medium" },
                  { value: "low",    label: "Low" },
                ]}
              />
              <FilterPills
                label="Policy Flag"
                value={crF.policy_flag}
                onChange={v => setCrF(f => ({ ...f, policy_flag: v }))}
                options={[
                  { value: "all", label: "All" },
                  { value: "yes", label: "Flagged" },
                  { value: "no",  label: "Clean" },
                ]}
              />
              <div className="ml-auto flex items-center gap-3">
                <ActiveCount shown={visibleCr.length} total={compliance.length} />
                {(anyCrActive || crSearch) && (
                  <button onClick={() => { resetCrF(); setCrSearch(""); }} className="text-xs text-accent-foreground hover:underline">
                    Clear filters
                  </button>
                )}
              </div>
            </div>
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/10">
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Description</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Type</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Status</th>
                    <th className="px-5 py-4 text-center text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Flag</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Severity</th>
                    <th className="px-5 py-4 text-left text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Created</th>
                    <th className="px-5 py-4 text-right text-xs font-medium uppercase tracking-wide text-muted whitespace-nowrap">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleCr.length === 0 && (
                    <tr><td colSpan={7} className="px-5 py-10 text-center text-sm text-muted">No records match these filters.</td></tr>
                  )}
                  {visibleCr.map(cr => (
                    <tr key={cr.id} className="border-b border-border/5 hover:bg-surface-elevated/30">
                      <td className="px-5 py-4 font-medium">{cr.description}</td>
                      <td className="px-5 py-4 whitespace-nowrap text-muted">{fmtCat(cr.record_type)}</td>
                      <td className="px-5 py-4 whitespace-nowrap">
                        <span className={
                          cr.status === "pending"  ? "text-xs font-semibold text-yellow-400" :
                          cr.status === "rejected" ? "text-xs font-semibold text-red-400"    :
                          "text-xs font-semibold text-success"
                        }>{fmtCat(cr.status)}</span>
                      </td>
                      <td className="px-5 py-4 whitespace-nowrap text-center">
                        {cr.policy_flag ? <span className="text-red-400">⚑</span> : <span className="text-muted">—</span>}
                      </td>
                      <td className="px-5 py-4 whitespace-nowrap">
                        <span className={`text-xs font-semibold ${severityColor(cr.severity)}`}>{cr.severity ?? "—"}</span>
                      </td>
                      <td className="px-5 py-4 whitespace-nowrap text-xs text-muted">{fmt(cr.created_at)}</td>
                      <td className="px-5 py-4 whitespace-nowrap">
                        <div className="flex justify-end gap-1.5">
                          <Button
                            type="button"
                            variant="secondary"
                            className="h-7 px-2.5 text-xs"
                            onClick={() => void updateComplianceRecord(cr.id, { policy_flag: !cr.policy_flag, severity: cr.policy_flag ? cr.severity : "medium" })}
                            disabled={manualLoading === cr.id}
                          >
                            {cr.policy_flag ? "Unflag" : "Flag"}
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            className="h-7 px-2.5 text-xs"
                            onClick={() => void updateComplianceRecord(cr.id, { status: cr.status === "approved" ? "pending" : "approved" })}
                            disabled={manualLoading === cr.id}
                          >
                            {cr.status === "approved" ? "Reopen" : "Approve"}
                          </Button>
                          <Button
                            type="button"
                            variant="danger"
                            className="h-7 px-2.5 text-xs"
                            onClick={() => void deleteComplianceRecord(cr.id)}
                            disabled={manualLoading === cr.id}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          </>
        )}
      </div>

      {/* ── Automation rules ── */}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Automation Rules</CardTitle>
              <CardDescription>Reusable scans that turn operational signals into approval-ready actions</CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => void seedAutomationRules()}
                disabled={automationLoading === "seed"}
              >
                {automationLoading === "seed" ? "Creating..." : "Create defaults"}
              </Button>
              <Button
                type="button"
                onClick={() => void runAutomationRules()}
                disabled={automationLoading === "run"}
              >
                {automationLoading === "run" ? "Running..." : "Run rules"}
              </Button>
            </div>
          </div>
        </CardHeader>
        <div className="grid gap-3 px-6 pb-6 lg:grid-cols-3">
          {automationRules.length === 0 && (
            <div className="rounded-md border border-border/10 bg-surface-elevated/35 px-4 py-5 text-sm text-muted lg:col-span-3">
              No automation rules yet. Create defaults to start scanning transactions, tickets, and compliance.
            </div>
          )}
          {automationRules.map(rule => (
            <div key={rule.id} className="rounded-md border border-border/10 bg-surface-elevated/35 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge tone={rule.enabled ? "accent" : "neutral"}>{rule.enabled ? "enabled" : "off"}</Badge>
                <Badge tone="neutral">{fmtCat(rule.domain)}</Badge>
              </div>
              <h3 className="text-sm font-semibold">{rule.name}</h3>
              <p className="mt-2 text-sm text-muted">{rule.description}</p>
              <p className="mt-3 text-xs text-muted">
                Last run: {rule.last_run_at ? fmt(rule.last_run_at) : "Never"}
              </p>
            </div>
          ))}
        </div>
      </Card>

      {/* ── Agent action inbox ── */}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Agent Action Inbox</CardTitle>
              <CardDescription>AI-recommended workflow actions awaiting human approval</CardDescription>
            </div>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void generateActions()}
              disabled={actionLoading === "generate"}
            >
              {actionLoading === "generate" ? "Scanning..." : "Generate actions"}
            </Button>
          </div>
        </CardHeader>
        <div className="grid gap-3 px-6 pb-6 lg:grid-cols-3">
          {agentActions.length === 0 && (
            <div className="rounded-md border border-border/10 bg-surface-elevated/35 px-4 py-5 text-sm text-muted lg:col-span-3">
              No pending agent actions. Generate actions to scan current risk, support, and compliance queues.
            </div>
          )}
          {agentActions.map(action => (
            <div key={action.id} className="flex min-h-52 flex-col rounded-md border border-border/10 bg-surface-elevated/35 p-4">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge tone={action.priority === "high" ? "danger" : "neutral"}>{action.priority}</Badge>
                <Badge tone="accent">{fmtCat(action.domain)}</Badge>
                <span className="ml-auto text-xs text-muted">{Math.round(action.confidence * 100)}%</span>
              </div>
              <h3 className="text-sm font-semibold">{action.title}</h3>
              <p className="mt-2 line-clamp-3 text-sm text-muted">{action.description}</p>
              {action.rationale && (
                <p className="mt-3 text-xs text-muted">Why: {action.rationale}</p>
              )}
              <div className="mt-auto flex gap-2 pt-4">
                <Button
                  type="button"
                  className="flex-1"
                  onClick={() => void resolveAction(action.id, "approve")}
                  disabled={actionLoading === action.id}
                >
                  Approve
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="flex-1"
                  onClick={() => void resolveAction(action.id, "reject")}
                  disabled={actionLoading === action.id}
                >
                  Reject
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* ── Bottom row ── */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Recent activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest events across all domains</CardDescription>
          </CardHeader>
          <ul className="divide-y divide-border/5 px-6 pb-4">
            {auditLogs.length === 0 && <li className="py-3 text-sm text-muted">No activity yet.</li>}
            {auditLogs.map(log => (
              <li key={log.id} className="flex items-start gap-3 py-3">
                <span className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${
                  log.domain === "transactions" ? "bg-blue-400" :
                  log.domain === "support"      ? "bg-yellow-400" :
                  log.domain === "compliance"   ? "bg-red-400" : "bg-muted"
                }`} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">{log.action_taken}</p>
                  <p className="text-xs text-muted">{fmt(log.created_at)} · {log.source}</p>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        {/* Agent card */}
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle>iMessage agent</CardTitle>
              {introSent ? <Badge tone="accent">Active</Badge> : <Badge tone="neutral">Pending</Badge>}
            </div>
            <CardDescription>
              {me?.preferred_phone_number
                ? `Text ${me.preferred_phone_number} to operate the platform from your phone.`
                : "Add a phone number under Settings to activate the phone agent."}
            </CardDescription>
          </CardHeader>
          <div className="px-6 pb-6">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">Try these commands</p>
              <Badge tone="neutral">{currentAgentExamples.label}</Badge>
            </div>
            <ul className="space-y-1.5">
              {currentAgentExamples.examples.map(cmd => (
                <li key={cmd} className="rounded bg-surface-elevated/60 px-3 py-1.5 font-mono text-xs text-muted">
                  {cmd}
                </li>
              ))}
            </ul>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button type="button" variant="secondary" onClick={() => void load()}>Refresh</Button>
              <Button type="button" onClick={() => void resendWelcome()} disabled={welcomeLoading}>
                {welcomeLoading ? "Sending…" : "Resend intro"}
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <p className="text-center text-xs text-muted">
        Need to change your phone?{" "}
        <Link href="/settings" className="text-accent-foreground underline-offset-4 hover:underline">Open settings</Link>
      </p>
    </div>
  );
}
