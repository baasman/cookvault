# Stripe Webhooks in Local Dev

**Tags:** `payments`, `stripe`, `webhooks`, `development`
**Last updated:** 2026-05-15

How to run Stripe webhooks against a local backend so paid flows
(Premium subscriptions, cookbook purchases, **BookProject clean-PDF
exports**) actually fire their post-payment handlers in dev.

---

## Why you need this

Stripe Elements on the frontend collects card details and confirms a
`PaymentIntent` — but the **server-side fulfillment** (e.g. rendering a
clean BookProject PDF, granting cookbook access, upgrading a user to
premium) only happens when Stripe POSTs a `payment_intent.succeeded`
event to `POST /api/payments/webhook`. In production, Stripe sends
those events directly. In local dev, your backend isn't reachable on
the public internet, so Stripe can't reach it — the payment _looks_
successful from the frontend but the post-payment work never runs.

The Stripe CLI's `stripe listen` command forwards Stripe events from
your Stripe account to your local backend over an authenticated
tunnel. It also prints a `whsec_...` secret you put in your `.env` so
signature verification works.

---

## One-time setup

### 1. Install the Stripe CLI

```sh
brew install stripe/stripe-cli/stripe
# or download from https://stripe.com/docs/stripe-cli
```

### 2. Log in

```sh
stripe login
```

This opens a browser, you authorize the CLI, done. The CLI stores
credentials in `~/.config/stripe/`.

---

## Run the listener (every dev session)

In a dedicated terminal, with your Cookle backend running on port
5001 (default for `make dev`):

```sh
stripe listen --forward-to localhost:5001/api/payments/webhook
```

First time you run this, it prints a webhook signing secret:

```
> Ready! Your webhook signing secret is whsec_abc123... (^C to quit)
```

**Copy that `whsec_...` value into your `.env` as
`STRIPE_WEBHOOK_SECRET=`**, then restart the backend so it picks up
the new env var. The secret is stable per machine — you only need to
update it once.

The terminal stays open and prints every event it forwards:

```
2026-05-15 17:23:11 --> payment_intent.succeeded [evt_1AbC]
2026-05-15 17:23:11 <-- [200] POST http://localhost:5001/api/payments/webhook [evt_1AbC]
```

---

## End-to-end test: BookProject clean PDF purchase

With `stripe listen` running and the dev stack up:

1. Open the BookProject dashboard for any project that has at least
   one recipe.
2. Click **Buy clean PDF**.
3. Use Stripe test card `4242 4242 4242 4242` with any future expiry
   and any 3-digit CVC.
4. Stripe Elements confirms the PaymentIntent — the modal closes and
   the dashboard shows **"Rendering clean PDF…"**.
5. The `stripe listen` terminal should show
   `payment_intent.succeeded → [200]`.
6. The dashboard polls every 2.5s and within a few seconds switches
   to **Download clean PDF** — clicking it streams the file.

If step 5 happens but step 6 doesn't, check the backend logs — the
webhook arrived but the handler raised. Most likely cause is
WeasyPrint not finding its system libs (see local-https-setup.md or
the `_preload_weasyprint_dylibs` helper in
`book_project_pdf_service.py`).

If step 5 doesn't happen at all, verify:
- `stripe listen` is still running and shows your account name
- `STRIPE_WEBHOOK_SECRET` in `.env` matches the value `stripe listen`
  printed (they rotate if you re-run without `--load-from-webhooks-api`)
- The backend is on port 5001 (matches the `--forward-to` URL)

---

## Filtering events

By default `stripe listen` forwards **all** events for your account.
To narrow it to just the events Cookle actually handles:

```sh
stripe listen \
  --forward-to localhost:5001/api/payments/webhook \
  --events payment_intent.succeeded,payment_intent.payment_failed,\
customer.subscription.created,customer.subscription.updated,\
customer.subscription.deleted,invoice.payment_succeeded,\
invoice.payment_failed
```

---

## Manually triggering a test event

You don't need an actual checkout to test handler behavior. To fire a
fake `payment_intent.succeeded` from the CLI:

```sh
stripe trigger payment_intent.succeeded
```

This creates a real (test-mode) PaymentIntent in Stripe and fires the
webhook against your local backend. Useful for unit-debugging the
handler without manually clicking through the Stripe Elements form.

For BookProject-specific testing — where the handler needs a real
`book_project_export_id` in the PaymentIntent metadata — there's an
end-to-end regression test at
`backend/tests/test_payments.py::TestStripeWebhookBookProjectExport`
that mocks `stripe.Webhook.construct_event` and exercises the rest of
the stack for real. Run it with:

```sh
cd backend && uv run pytest \
  tests/test_payments.py::TestStripeWebhookBookProjectExport -v
```

---

## Production webhook configuration

For the deployed backend, the webhook is registered manually in the
Stripe dashboard at
[Developers → Webhooks → Add endpoint](https://dashboard.stripe.com/webhooks):

- **Endpoint URL:** `https://cookle-backend.onrender.com/api/payments/webhook`
- **Events to send:** the seven listed under "Filtering events"
  above.
- **Signing secret:** Stripe shows it after creating the endpoint.
  Copy it into Render's environment variables for the `cookle-backend`
  service as `STRIPE_WEBHOOK_SECRET` (the var is declared in
  `render.yaml` with `sync: false` so the value is set per-environment
  in the Render dashboard, not committed to the repo).

Once registered, monitor incoming events via the same dashboard page
— Stripe logs every delivery attempt and the backend's response code.
