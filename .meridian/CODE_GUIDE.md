&lt;CODE_GUIDE&gt;
FRONTEND — Next.js/React (generic baseline)

1) Scope: framework‑agnostic where possible, with practical Next.js/React specifics.
2) TypeScript: enable "strict" and "noImplicitAny" across the repo.
3) Lint/format: ESLint + Prettier (or Biome); run on commit; CI fails on lint/type errors.
4) Naming: camelCase for vars/functions, PascalCase for components/types, UPPER_SNAKE for constants.
5) Imports: prefer absolute path aliases (e.g., "@/components") over deep relative paths.
6) Structure: organize by feature/domain (e.g., billing/*) over pure technical layers.
7) Comments: explain *why*; favor clear names/code over “what” comments.
8) Component size: keep components focused (~150 lines); extract logic to hooks and pure UI parts.
9) Props: explicit interfaces; mark optional vs required; avoid "any"/"object" types.
10) Keys: use stable keys in lists; avoid array index keys if order can change.
11) State minimalism: store only necessary state; derive the rest; lift only when shared.
12) Server vs client: default to Server Components; add "use client" only when needed.
13) Client‑only code: don’t import browser APIs or stateful hooks into Server Components.
14) Data fetching (App Router): fetch on the server by default (`fetch` with caching/revalidation).
15) Avoid waterfalls: colocate route/layout data; use Suspense to stream where helpful.
16) Server Actions: validate inputs with a schema; keep actions small and side‑effect‑aware.
17) API contracts: centralize request/response types; generate from OpenAPI/GraphQL where feasible.
18) Remote vs local state: TanStack Query/SWR for remote cache; local or light store for UI state.
19) Effects discipline: avoid `useEffect` for fetching in App Router unless truly client‑only.
20) Memoization: prefer component boundaries; add `useMemo`/`useCallback` only after profiling.
21) Forms: use react‑hook‑form (or similar) + schema validation (e.g., Zod); colocate schema and form.
22) Form UX: inline field errors; disable submit while pending; support rollback on optimistic updates.
23) Errors: route‑level `error.tsx` and `not-found.tsx`; show recovery options and support links.
24) Suspense/streaming: stream above‑the‑fold content first; keep boundaries meaningful.
25) Routing: use App Router; nested layouts; colocate components/data/tests with routes.
26) URLs: human‑readable paths; encode filters/sort as query params.
27) Styling: pick one approach (CSS Modules, Tailwind, or CSS‑in‑JS); avoid mixing paradigms.
28) CSS scope: keep styles component‑scoped; limit global CSS to resets and design tokens.
29) Design tokens: define color/spacing/typography tokens (CSS variables or TS), not hardcoded values.
30) Responsive: mobile‑first; avoid fixed heights; test at small and large breakpoints.
31) Images: use `next/image`; set intrinsic dimensions; avoid layout shift; responsive sizes.
32) Fonts: use `next/font` or self‑host; subset; limit variants; enable `display: swap`.
33) Code splitting: `dynamic()` heavy widgets; keep SSR unless the widget is inherently client‑only.
34) Bundle hygiene: review `next build` stats; tree‑shake; prefer native `Intl`, `URL`, `fetch`.
35) Accessibility: semantic HTML; labeled inputs; logical tab order; ARIA used sparingly and correctly.
36) XSS: avoid `dangerouslySetInnerHTML`; sanitize any third‑party HTML.
37) CSRF: prefer Server Actions or same‑site httpOnly cookies + CSRF tokens for mutations.
38) Auth tokens: never store tokens in `localStorage`; use httpOnly cookies or short‑lived memory tokens.
39) Third‑party scripts: load late; measure cost; require consent before analytics/ads.
40) i18n: externalize strings; use ICU messages for plurals/gender; be RTL‑aware if relevant.
41) Timezones/locales: store UTC; format for display with `Intl.*`.
42) Caching: set `revalidate` intentionally; prefer stale‑while‑revalidate patterns where it fits.
43) Client cache hygiene: invalidate on mutations; leverage Next revalidation (tags/paths) when server‑fetching.
44) File uploads: validate type/size server‑side; chunk large uploads; show progress; handle retries.
45) Runtime choice: use Edge for low‑latency read endpoints; Node runtime for CPU/SDK‑heavy work.
46) SEO/Metadata: use the Metadata API; canonical, robots, and social tags; add sitemaps if indexable.
47) Analytics/Vitals: track LCP/INP/CLS; keep events minimal; avoid PII in telemetry.
48) Error reporting: capture client errors with source maps and PII redaction.
49) Tests: fast unit tests, behavior‑focused component tests, and a few E2E smoke tests.
50) Network mocking: use MSW in tests/dev; keep mocks faithful to real contracts.
51) Visual checks: optional Storybook/Chromatic for UI‑heavy surfaces.
52) Local dev: `.env.local`; never commit secrets; provide seed data and realistic mocks.
53) Scripts: include `typecheck`, `lint`, `test`, `build`, `preview`; document in README.
54) tsconfig: `isolatedModules`, `resolveJsonModule`, `moduleResolution: "bundler"`; avoid alias conflicts.
55) Dependencies: prefer small, maintained libraries; avoid full‑lib imports; don’t duplicate UI kits.
56) Profiling: use React Profiler and web perf tools; fix root causes of re‑renders first.
57) Accessibility testing: include automated checks (axe) and manual keyboard passes on key flows.
58) Security posture: never expose secrets in props or client bundles; review third‑party code usage.
59) Dead code: audit and remove unused components/deps regularly.
60) Final note: favor clarity and small, measurable improvements.

BACKEND — TypeScript/Node.js (generic baseline)

61) Runtime: target active LTS; pin in `.nvmrc`/`engines`; match CI and runtime.
62) Modules: prefer ESM with `"type": "module"`; avoid mixing CJS unless necessary.
63) TypeScript: enable `strict`; treat type errors as build blockers.
64) Layout: group by domain (`users/`, `orders/`) with clear application/infra/test areas.
65) Module boundaries: export via package/index barrels; avoid deep cross‑domain imports.
66) Config: a single `config` module; validate env vars at startup (Zod); fail fast on invalid/missing.
67) Secrets: never commit; load from env/secret store; redact in logs; use placeholders for dev.
68) Logging: structured JSON (pino/winston); include level, timestamp, requestId, and tenant/user when available.
69) Correlation: attach a requestId to inbound requests and propagate to downstream calls.
70) Errors: use typed errors; never throw raw strings; keep a stable error shape `{ code, message, details }`.
71) Error→HTTP: map domain errors consistently to precise HTTP codes.
72) Validation: validate all external inputs (HTTP, queues, webhooks, scheduled jobs) with schemas.
73) Security headers: set Helmet defaults; restrict CORS origins/methods/headers.
74) Rate limiting: basic per IP/user/endpoint; return `429` with `Retry‑After`.
75) Compression: enable gzip/br where appropriate; skip already‑compressed assets.
76) Timeouts: set server/outbound timeouts; use AbortController; avoid hung requests.
77) Authentication: prefer session cookies (httpOnly, SameSite, Secure). If JWTs, keep short‑lived and rotate refresh tokens.
78) Authorization: roles/permissions enforced in handlers and near data access.
79) Multi‑tenancy: never trust client‑sent tenant; enforce tenant scoping server‑side; consider row‑level guards.
80) Database: choose one primary store first; use an ORM/query builder with generated types.
81) Migrations: versioned and peer‑reviewed; forward‑only; back up before destructive changes.
82) Indexing: index lookups/joins/sorts; monitor slow queries; use `EXPLAIN` on hot paths.
83) Transactions: wrap multi‑step writes; retry on transient errors/deadlocks with bounds.
84) Pagination: favor cursor‑based; cap page sizes; whitelist filters/sorts to avoid expensive scans.
85) Idempotency: consider idempotency keys for unsafe POSTs on public endpoints.
86) Caching: pick cache by access pattern (in‑memory/Redis/CDN); define TTL and invalidation.
87) Stampede control: coalesce duplicate requests; add jitter to TTLs where useful.
88) Queues & background jobs: use a queue (SQS/Rabbit/etc.); define retry/backoff and DLQ behavior.
89) Scheduling: centralize cron; keep jobs idempotent; guard against duplicate runs.
90) Webhooks: verify signatures and timestamps; retry with backoff; deduplicate deliveries.
91) Observability: expose liveness/readiness endpoints; basic metrics; minimal tracing if feasible.
92) Log hygiene: redact secrets/PII; centralize logs if available; sample high‑volume logs.
93) Event‑loop safety: no CPU‑heavy/blocking calls on request paths; offload to workers/queues.
94) Pools: right‑size DB/Redis pools; close idle connections; respect serverless constraints.
95) Backpressure/streaming: stream large responses/files; apply backpressure to producers.
96) Input limits: cap body sizes; validate multipart; sanitize filenames/paths.
97) Output encoding: correct `content‑type`/charset; escape JSON/HTML.
98) Time handling: store UTC; use ISO‑8601 in APIs; avoid locale math in queries.
99) Serialization: prefer JSON; enforce payload size limits; avoid circular structures.
100) Build: tsup/esbuild; emit ESM; keep Docker images small; pin base images.
101) CI: typecheck, lint, tests, security audit, and build on every PR; block merges on failures.
102) Runtime choice: containers vs serverless—manage DB connections and cold starts accordingly.
103) Feature flags: gate risky changes; clean up stale flags promptly.
104) Unit tests: fast/deterministic; mock at module boundary; no network/DB.
105) Integration tests: use a real DB via containers in CI; reset state between tests.
106) E2E smoke tests: cover critical flows; run on staging/pre‑prod before release.
107) Test data: factories/builders; generate realistic data; avoid real PII.
108) API style: choose REST, RPC, or GraphQL; document; avoid casual mixing.
109) REST design: nouns in paths, verbs in methods; precise status codes; consistent errors.
110) Versioning: path or header versioning for breaking changes; document deprecations.
111) Query safety: limit query complexity; whitelist filters/sorts; bound results.
112) Identifiers: use UUID/ULID; avoid exposing sequential IDs publicly.
113) Content negotiation: require/emit explicit `content‑type`; reject unknown types.
114) CORS specifics: limit origins; configure credentialed requests correctly (`SameSite=None; Secure` when needed).
115) Secrets scanning: enable pre‑commit and CI scanning; block merges on hits.
116) Deployment: prefer immutable builds; avoid mutable servers; document runtime envs.
117) API docs: generate OpenAPI/SDL; publish examples; keep contracts in version control.
118) Data exports/imports: stream and throttle; audit log access; filter sensitive fields.
119) Dead code: remove unused handlers/jobs regularly; keep dependencies lean.
120) Final note: clear contracts, safe defaults, and small increments win long‑term.
&lt;/CODE_GUIDE&gt;