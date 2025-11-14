&lt;CODE_GUIDE_ADDON_HACKATHON&gt;
> ⚠️ IMPORTANT — READ BASELINE FIRST  
> This file is an **add-on** to `CODE_GUIDE.md`.  
> It does **not** replace the Baseline and is **not** a complete code guide.  
> Before reading or applying any rule in this add-on, you **must** first read  
> and load the Baseline guide at `.meridian/CODE_GUIDE.md`.  
>
> If you have not read the Baseline yet, stop and read it now before continuing.

Agent Instructions (READ ME FIRST)

- Purpose: This add-on modifies the Baseline for fast prototypes and short demos.
- Precedence: If any rule here conflicts with the Baseline, follow this add-on.
- Non-destructive: Do not remove Baseline rules that aren’t mentioned here.
- Security floor: Never relax the following: no committed secrets, safe handling of user data, no stack traces to clients, and basic input validation.
- Interpretation:
  • “Relax”: The Baseline rule still exists, but you may choose a simpler path.
  • “Cancel”: You may ignore that Baseline rule for this mode.
  • “Override”: Prefer this guidance instead of the Baseline for the same topic.
  • “Optional”: Use if it’s trivial; otherwise skip for speed.

FRONTEND — Hackathon add-on

1) Override Structure: a flat, minimal layout (`/components`, `/routes`, `/lib`) is fine; refactor only if the project continues.
2) Relax Data fetching: client-side fetching is acceptable for simple pages; prefer server fetch only when equally easy.
3) Relax Component size: allow larger components temporarily; extract only when reuse is obvious.
4) Override Styling: pick the fastest path (e.g., Tailwind + small component kit); skip tokens, theming, and design systems.
5) Cancel Theming: no dark mode/theming unless the demo requires it.
6) Relax State/networking: keep a single data layer (TanStack Query or plain `fetch`); skip optimistic updates unless trivial.
7) Relax Assets: default `next/image` settings; skip font subsetting.
8) Cancel Aggressive prefetching/polish: keep defaults; avoid micro-optimizations.
9) Relax Security extras: avoid `dangerouslySetInnerHTML` and insecure token storage, but skip CSP and advanced headers on day one.
10) Relax Tests: one E2E happy-path test and (optionally) one key component test; manual testing acceptable for the demo.
11) Optional Error reporting: `console.error` is fine; add a lightweight tracker only if trivial.
12) Relax Uploads: basic server-side validation; skip chunking/resume unless required.
13) Add README “Graduation” checklist: list follow-ups (tokens, accessibility sweep, caching strategy).

BACKEND — Hackathon add-on

14) Override Architecture: single service; avoid heavy layering and microservices.
15) Relax Config: single `.env`; validate only truly required values; document in README.
16) Override Data: SQLite or hosted dev DB; “migrate by push” acceptable; provide a seed script.
17) Override Auth/integrations: use hosted providers (Auth0/Clerk/Firebase/Supabase, Stripe, file storage) rather than custom builds.
18) Relax API surface: minimal endpoints; return a simple, consistent error shape; stub unimplemented features with 501.
19) Relax Rate limits/idempotency: skip unless public-facing; if public, add a basic per-IP limit.
20) Relax Observability: console logs with request path/status; add `/health`; skip tracing.
21) Cancel Queues/cron: use in-process timers only if essential; avoid external queues/schedulers.
22) Relax Webhooks: shared secret; retries optional; log deliveries.
23) Optional Tests: write a single integration test for the main flow if time allows.
24) Security floor (do not relax): never commit secrets; hash passwords if handling real users; verify webhook signatures if present; don’t return stack traces to clients.
&lt;/CODE_GUIDE_ADDON_HACKATHON&gt;