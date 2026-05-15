import Image from "next/image";
import Link from "next/link";
import { ScrollReveal } from "@/components/scroll-reveal";

const problems = [
  {
    title: "Operations data is scattered",
    copy: "Important updates start as texts, hallway notes, emails, support calls, and spreadsheet rows. By the time they reach a dashboard, the context is already fading.",
  },
  {
    title: "Teams waste time translating work",
    copy: "A manager sees a suspicious transaction, a customer refund issue, or a policy exception, then someone still has to manually create the right record.",
  },
  {
    title: "Most AI tools stop at conversation",
    copy: "A chatbot can answer a question. OpsMeshAI turns the answer into a workflow: classify, create, flag, recommend, update, and audit.",
  },
  {
    title: "Risk needs proof, not vibes",
    copy: "Finance, support, and compliance teams need to know what changed, who triggered it, why the AI recommended action, and what happened next.",
  },
];

const workflowSteps = [
  {
    title: "Text a few words",
    copy: "Spent 2400 at Apple in Miami. Customer refund still missing. Add compliance note for first-class travel.",
  },
  {
    title: "The AI parses the intent",
    copy: "OpsMeshAI decides whether the message is a transaction, support ticket, compliance item, query, or approval workflow.",
  },
  {
    title: "The system does the work",
    copy: "Records are created, risk is scored, flags are applied, recommendations are generated, and audit logs are written.",
  },
  {
    title: "The dashboard updates",
    copy: "Operators see the new data immediately across transactions, support tickets, compliance queues, insights, and action inboxes.",
  },
];

const capabilities = [
  "Phone-first workflow intake",
  "Manual dashboard entry",
  "AI intent parsing",
  "Transaction risk flags",
  "Support ticket triage",
  "Compliance review queues",
  "Agent action approvals",
  "Audit logs for every change",
];

const commandExamples = [
  ["Transaction", "Spent 2400 at Apple in Miami", "Creates record, scores risk, flags review"],
  ["Support", "Customer says refund still not received", "Opens ticket and prioritizes queue"],
  ["Compliance", "Missing receipt for travel reimbursement", "Logs policy item and review status"],
];

const stats = [
  ["3", "ops domains"],
  ["2-way", "phone + dashboard"],
  ["0", "forms needed from the field"],
  ["100%", "auditable actions"],
];

export default function LandingPage() {
  return (
    <main className="landing-motion-scope min-h-[100dvh] overflow-hidden bg-canvas text-foreground">
      <ScrollReveal />
      <section className="relative min-h-[100dvh] border-b border-border/10 bg-[linear-gradient(145deg,rgb(8_10_16)_0%,rgb(18_21_32)_44%,rgb(9_42_45)_100%)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_20%,rgb(59_130_246_/_0.26),transparent_34%),radial-gradient(circle_at_15%_70%,rgb(52_211_153_/_0.16),transparent_30%)]" />
        <div className="relative mx-auto flex min-h-[100dvh] max-w-7xl flex-col px-5 py-5 sm:px-8 lg:px-10">
          <header className="sticky top-4 z-20 flex animate-[landingRise_650ms_ease-out_both] items-center justify-between gap-4 rounded-md border border-white/10 bg-slate-950/55 px-3 py-3 shadow-glass backdrop-blur">
            <Link href="/" className="motion-link flex items-center gap-2 text-sm font-semibold">
              <span className="flex h-9 w-9 items-center justify-center rounded-md border border-border/10 bg-white/10 text-xs font-bold">
                OM
              </span>
              <span>OpsMeshAI</span>
            </Link>
            <nav className="flex items-center gap-2">
              <Link href="/login" className="motion-link rounded-md px-3 py-2 text-sm text-slate-300 transition hover:bg-white/10 hover:text-white">
                Sign in
              </Link>
              <Link href="/register" className="motion-link rounded-md bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground transition hover:opacity-90">
                Try now
              </Link>
            </nav>
          </header>

          <div className="grid flex-1 items-center gap-12 py-16 lg:grid-cols-[0.92fr_1.08fr] lg:py-10">
            <div className="animate-[landingRise_900ms_ease-out_both]">
              <p className="mb-5 inline-flex rounded-md border border-emerald-300/25 bg-emerald-300/10 px-3 py-1 text-xs font-medium text-emerald-100">
                AI workflow automation, built for real operations
              </p>
              <h1 className="max-w-4xl text-5xl font-semibold leading-[0.98] tracking-normal text-white sm:text-7xl lg:text-8xl">
                Just text it. OpsMesh does the work.
              </h1>
              <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-200">
                Businesses are drowning in small operational updates that never become clean data.
                OpsMeshAI turns a few words from your phone or dashboard into structured work:
                records, risk flags, support queues, compliance reviews, recommendations, and audit logs.
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <Link href="/register" className="motion-link rounded-md bg-accent px-6 py-3 text-sm font-semibold text-accent-foreground shadow-glass transition hover:scale-[1.02] hover:opacity-90">
                  Try now
                </Link>
                <Link href="/login" className="motion-link rounded-md border border-white/15 bg-white/10 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/15">
                  Open workspace
                </Link>
              </div>
              <div className="mt-10 grid max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
                {stats.map(([value, label]) => (
                  <div key={label} className="reveal-pop motion-card rounded-md border border-white/10 bg-white/10 p-4 backdrop-blur">
                    <p className="text-2xl font-semibold text-white">{value}</p>
                    <p className="mt-1 text-xs text-slate-300">{label}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="animate-[landingFloat_1s_ease-out_200ms_both]">
              <div className="scroll-drift soft-glow motion-card relative rounded-lg border border-white/12 bg-slate-950/60 p-3 shadow-glass backdrop-blur">
                <Image
                  src="/images/opsmesh-phone-agent.png"
                  alt="A professional texting the OpsMeshAI agent and receiving an automated workflow confirmation."
                  width={1400}
                  height={900}
                  priority
                  className="aspect-[16/10] w-full rounded-md object-cover"
                />
                <div className="reveal-pop absolute bottom-5 left-5 right-5 rounded-md border border-white/15 bg-slate-950/80 p-4 backdrop-blur">
                  <p className="text-xs uppercase text-slate-400">AI agent response</p>
                  <p className="mt-2 text-sm font-medium text-white">
                    Transaction added. Risk flagged. Dashboard updated.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10">
        <div data-scroll-reveal="slide-left" className="max-w-3xl">
          <p className="text-sm font-semibold text-accent-foreground">The problem</p>
          <h2 className="mt-3 text-4xl font-semibold leading-tight tracking-normal sm:text-6xl">
            Business work is fast. Business systems are slow.
          </h2>
          <p className="mt-5 text-base leading-8 text-muted">
            Ops teams do not fail because they lack dashboards. They fail because the real work begins before
            the dashboard: in messages, phone calls, and urgent decisions that need to become structured records.
          </p>
        </div>
        <div className="mt-10 grid gap-4 lg:grid-cols-4">
          {problems.map((problem, index) => (
            <article
              key={problem.title}
              data-scroll-reveal="pop"
              className="motion-card rounded-md border border-border/10 bg-surface-elevated/60 p-5 shadow-glass"
              style={{ animationDelay: `${index * 90}ms` }}
            >
              <span className="text-sm font-semibold text-accent-foreground">0{index + 1}</span>
              <h3 className="mt-5 text-xl font-semibold">{problem.title}</h3>
              <p className="mt-3 text-sm leading-6 text-muted">{problem.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-border/10 bg-surface/70">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:px-10">
          <div data-scroll-reveal="slide-left" className="lg:sticky lg:top-24 lg:self-start">
            <p className="text-sm font-semibold text-accent-foreground">The workflow</p>
            <h2 className="mt-3 text-4xl font-semibold leading-tight tracking-normal sm:text-6xl">
              A few words become completed work.
            </h2>
            <p className="mt-5 text-base leading-8 text-muted">
              The phone is not a gimmick. It is the fastest interface for field work, managers,
              founders, support leads, and compliance reviewers who need action without logging in.
            </p>
            <div className="mt-8">
              <Link href="/register" className="motion-link rounded-md bg-accent px-5 py-3 text-sm font-semibold text-accent-foreground shadow-glass transition hover:opacity-90">
                Try now
              </Link>
            </div>
          </div>
          <div className="space-y-5">
            {workflowSteps.map((step, index) => (
              <div key={step.title} data-scroll-reveal="slide-right" className="motion-card rounded-lg border border-border/10 bg-canvas/80 p-6 shadow-glass">
                <div className="flex items-start gap-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-accent text-sm font-semibold text-accent-foreground">
                    {index + 1}
                  </span>
                  <div>
                    <h3 className="text-2xl font-semibold">{step.title}</h3>
                    <p className="mt-2 text-sm leading-7 text-muted">{step.copy}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 lg:px-10">
        <div data-scroll-reveal className="text-center">
          <p className="text-sm font-semibold text-accent-foreground">Examples</p>
          <h2 className="mx-auto mt-3 max-w-4xl text-4xl font-semibold leading-tight tracking-normal sm:text-6xl">
            Say it naturally. OpsMeshAI translates it into workflow.
          </h2>
        </div>
        <div className="mt-10 grid gap-4 lg:grid-cols-3">
          {commandExamples.map(([domain, command, outcome]) => (
            <article key={domain} data-scroll-reveal="pop" className="motion-card rounded-lg border border-border/10 bg-surface-elevated/60 p-5 shadow-glass">
              <p className="text-sm font-semibold text-accent-foreground">{domain}</p>
              <div data-scroll-reveal="pop" className="rounded-md bg-canvas/80 p-4 font-mono text-sm text-foreground">
                {command}
              </div>
              <p className="mt-4 text-sm leading-6 text-muted">{outcome}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="relative border-y border-border/10 bg-[linear-gradient(180deg,rgb(18_21_32)_0%,rgb(8_10_16)_100%)]">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[1fr_1fr] lg:px-10">
          <div data-scroll-reveal="slide-left">
            <p className="text-sm font-semibold text-accent-foreground">Why it is different</p>
            <h2 className="mt-3 text-4xl font-semibold leading-tight tracking-normal text-white sm:text-6xl">
              Not a chatbot. An operations layer.
            </h2>
            <p className="mt-5 text-base leading-8 text-slate-300">
              OpsMeshAI combines messaging, AI parsing, backend workflows, database persistence,
              dashboard visibility, and auditability. It works both ways: from the phone and from the dashboard.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {capabilities.map((capability) => (
              <div key={capability} data-scroll-reveal="pop" className="motion-card rounded-md border border-white/10 bg-white/[0.06] p-4 text-sm font-medium text-white">
                {capability}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-5 py-24 text-center sm:px-8 lg:px-10">
        <div data-scroll-reveal>
          <p className="text-sm font-semibold text-accent-foreground">Ready for the demo</p>
          <h2 className="mt-3 text-4xl font-semibold leading-tight tracking-normal sm:text-6xl">
            Give the AI agent a task. Watch the business system update.
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-muted">
            Create records manually in the dashboard or text the agent from your phone.
            Either way, OpsMeshAI keeps the workflow moving.
          </p>
          <div className="mt-9 flex justify-center gap-3">
            <Link href="/register" className="motion-link rounded-md bg-accent px-6 py-3 text-sm font-semibold text-accent-foreground shadow-glass transition hover:opacity-90">
              Try now
            </Link>
            <Link href="/login" className="motion-link rounded-md border border-border/10 bg-surface-elevated px-6 py-3 text-sm font-semibold transition hover:bg-surface">
              Sign in
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
