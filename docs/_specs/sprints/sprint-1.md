# Sprint 1 — Frontend Foundation (Current-State Aligned)

## Objective

Establish a reusable Next.js frontend foundation (design tokens, layout shell, shared UI primitives) that later sprints could evolve into a production auth-first experience.

## What remains true in the current codebase

- Repo-root Next.js app with App Router and strict TS/lint/build flow.
- Shared visual primitives and layout shell still power the app (`components/ui/*`, `components/layout/*`, `app/globals.css`, `styles/tokens.css`).
- Foundation work enabled the later simplification to auth routes + minimal main app routes without structural rewrites.

## What changed later (important alignment note)

- Sprint-era placeholder/demo pages (design gallery, playground pages, broad dashboard sections) were removed.
- The app now exposes only:
  - `app/(auth)/login/page.tsx`
  - `app/(auth)/register/page.tsx`
  - `app/(main)/page.tsx`
  - `app/(main)/settings/page.tsx`
- Navigation is reduced to product paths only (`Home`, `Settings`).

## High-impact foundation artifacts still relevant

- Toolchain/config: `package.json`, `tsconfig.json`, `tailwind.config.ts`, `eslint.config.mjs`, `postcss.config.mjs`.
- UI/layout base: `components/ui/*`, `components/layout/*`, `styles/tokens.css`, `app/globals.css`.

## Runbook

```bash
cd opsmesh-ai
npm install
npm run dev
npm run build
```

## Exit criteria (retroactive)

- Foundation supports the current auth-first UX without architectural rework.
- Shared UI/layout remains the base for all active pages.
