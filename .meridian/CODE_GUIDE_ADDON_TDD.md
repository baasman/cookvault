&lt;CODE_GUIDE_ADDON_TDD&gt;
> ⚠️ IMPORTANT — READ BASELINE FIRST  
> This file is an **add-on** to `CODE_GUIDE.md`.  
> It does **not** replace the Baseline and is **not** a complete code guide.  
> Before reading or applying any rule in this add-on, you **must** first read  
> and load the Baseline guide at `.meridian/CODE_GUIDE.md`.  
>
> If you have not read the Baseline yet, stop and read it now before continuing.

⚠️ OVERRIDE NOTICE (READ FIRST)

This TDD add-on **overrides all prior rules related to testing**, including:
- The baseline CODE_GUIDE.md testing guidelines
- Hackathon add-on rules (“keep tests minimal/optional”)
- Production add-on rules (stricter coverage requirements)

When TDD mode is enabled:
**TDD is mandatory. Tests MUST be written first (Red → Green → Refactor) regardless of project type.**

Other add-ons may still influence *style, scope, and depth*, but **none of them may cancel, weaken, or deprioritize the TDD workflow**.

In hackathon mode: tests remain minimal but **still written first**.
In production mode: tests follow TDD and may need more depth per production rules.

If any instruction conflicts with TDD, **TDD wins**.

---

## TDD Operating Rules

1) **Start with behavior.** Pick the smallest observable behavior to specify as a test.
   - New feature → write one acceptance/integration test for the main happy path.
   - Bug → write a failing **regression test** that reproduces the bug.
   - Refactor → write **characterization tests** for current behavior first.

2) **Red → Green → Refactor (tight loop).**
   - **Red:** Add the test; ensure it fails for the expected reason.
   - **Green:** Implement the minimal change to pass.
   - **Refactor:** Improve design without changing behavior. Keep tests green.

3) **Level selection (pragmatic).**
   - Prefer **integration** at boundaries (HTTP handler, route, component interaction).
   - Use **unit** tests for pure logic (parsers, validators, reducers, utilities).
   - Use **E2E** for critical journeys only (checkout, auth, onboarding).

4) **Mocks & fakes.**
   - Prefer **fakes/testcontainers** for data stores and queues where feasible.
   - Use **MSW** (browser/node) for HTTP boundaries over ad‑hoc `fetch` mocks.
   - Spy on side‑effects; avoid mocking the system under test.
   - Control non‑determinism (time, random, UUID) via adapters or test doubles.

5) **Data builders over fixtures.**
   - Use small **test-data builders** (factory functions) rather than giant fixtures.
   - Keep builders in `/test/` or colocated `*.test-data.ts`.

6) **Coverage (sane defaults).**
   - Aim for **changed‑lines** coverage in CI (if enforced).
   - Don’t chase 100%; write the **next** test that proves the next behavior.

7) **Commit discipline.**
   - Optional but clean: `test:` commit (failing), then `feat:/fix:` commit (make green), then `refactor:` commit.
   - Squash if your repo prefers.

---

## Standard Commands (suggested)
- Unit/integration: `npm run test` (Vitest/Jest)
- Watch mode: `npm run test:watch`
- Coverage: `npm run test:coverage`
- E2E: `npm run e2e` (Playwright/Cypress)

> Ensure these exist in `package.json`. If missing, propose minimal scripts.

---

## Frontend (Next.js/React) — TDD specifics

- **Frameworks**: Vitest or Jest; React Testing Library; Playwright for E2E; **MSW** for HTTP.
- **Colocation**: Prefer `*.test.tsx` next to source; E2E in `/e2e/`.
- **Server Components**: Test at the **route/segment** boundary when possible; avoid shallow‑testing implementation details.
- **Client Components**: Test via DOM behavior (text, roles, events). Avoid snapshot‑as‑spec; use snapshots only for stable presentational parts.
- **Routing & forms**: Test navigation via `<Link>` and form submissions through **user events**, not implementation internals.
- **Data fetching**: For client fetches, use **MSW** to simulate server responses; assert cache invalidation where relevant.
- **Accessibility**: Prefer queries by role/label; add one axe check for critical screens.

**React component test skeleton**
```ts
import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MyWidget} from "./MyWidget";

test("shows total and updates on add", async () => {
  render(<MyWidget />);
  expect(screen.getByRole("status", {name: /total/i})).toHaveTextContent("0");

  await userEvent.click(screen.getByRole("button", {name: /add item/i}));
  expect(screen.getByRole("status", {name: /total/i})).toHaveTextContent("1");
});
```

**Route handler (integration)**

```ts
import request from "supertest";
import {app} from "../../test/app"; // your test app wrapper for Next route handlers

test("POST /api/cart adds item", async () => {
  const res = await request(app).post("/api/cart").send({sku: "X", qty: 1});
  expect(res.status).toBe(201);
  expect(res.body).toMatchObject({items: [{sku: "X", qty: 1}]});
});
```

---

## Backend (TypeScript/Node.js) — TDD specifics

* **Frameworks**: Vitest/Jest; **Supertest** for HTTP; **MSW (node)** or `MockAgent`/`nock` for outbound HTTP.
* **Data**: Prefer testcontainers or an ephemeral DB for integration paths; otherwise a fast in‑memory adapter/fake.
* **HTTP boundaries**: Start tests at the handler/router; assert status codes + response bodies (not internal function calls).
* **Domain logic**: Keep pure functions testable without I/O.
* **Webhooks**: Verify signature & timestamp; include replay/dup checks in tests where applicable.

**HTTP handler test skeleton**

```ts
import request from "supertest";
import {createServer} from "../server";

test("GET /health returns OK", async () => {
  const app = await createServer();
  const res = await request(app).get("/health");
  expect(res.status).toBe(200);
  expect(res.body).toEqual({ok: true});
});
```

**Domain logic test skeleton**

```ts
import {calcTotal} from "./calcTotal";

test("calcTotal applies discount for VIP", () => {
  expect(calcTotal([{price: 100}], {vip: true})).toBe(90);
});
```

---

## Agent Output Templates (use these during implementation)

### A) Start the TDD loop (RED)

* **Plan** (1–3 bullets): behavior to specify, test level, files to create.
* **Diff**: add new `*.test.ts[x]` (or Playwright test). Ensure it fails.
* **Run**: show the exact command (e.g., `npm run test -w web -- -t "adds item"`).

### B) Make it pass (GREEN)

* **Diff**: minimal code change to pass the test.
* **Run**: show tests passing.
* **Note**: mention any assumptions you made.

### C) Improve design (REFACTOR)

* **Diff**: refactor without changing behavior (naming, extraction, types).
* **Run**: show tests still passing.

*(If user asks for a single patch only, you can combine A+B; still keep the test‑first ordering in the diff.)*

---

## Exceptions (when TDD‑first can be skipped)

* One‑off exploratory **spike**: create prototype code quickly, then write tests before merging.
* Unknown third‑party behavior: first create a **contract test** against the real API in a safe env, then TDD locally with mocks/fakes.
* Massive refactor with inadequate coverage: write **characterization tests** first, then proceed TDD for new behavior.

Document the exception in `TASK-###-context.md` briefly.

---

## When to Write Tests vs Code (Order of Operations)

- After the user approves the plan:
  - Add a **TDD Test Plan** section to `TASK-###-plan.md` that maps each
    acceptance criterion to at least one planned test (name + level:
    unit/integration/e2e).

- During implementation:
  - Do **not** try to write all tests for the entire task upfront.
  - Instead, follow this loop for each small behavior or plan step:
    1. Pick the next behavior (usually one acceptance criterion or a part of it).
    2. Write a failing test that expresses that behavior.
    3. Run the tests and confirm the failure is for the expected reason.
    4. Implement the minimal code to make that test pass.
    5. Refactor safely with tests green.

- For bug-fix tasks:
  - The **first step** is always to write a failing regression test that
    reproduces the bug, then fix it.

- For refactors on weakly-tested code:
  - Start by writing **characterization tests** that capture current
    behavior, then refactor. Use TDD (test-first) for any new behavior.

---

## Task Manager Integration

In `TASK-###-plan.md`, include:

* **Steps** starting with “Write failing test for …” then “Implement minimal code …” then “Refactor …”.
* **Mapping to Acceptance Criteria**: each AC references the corresponding test name(s).
* **Validation**: exact commands to run tests locally and in CI.

---

## Memory Curator Integration

If TDD reveals a **repeatable pattern** (e.g., “prefer MSW for outbound HTTP in tests”, or “characterization tests before refactor in legacy modules”), add a `memory.jsonl` entry via `memory-curator`.
&lt;/CODE_GUIDE_ADDON_TDD&gt;