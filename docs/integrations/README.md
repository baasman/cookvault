# Integrations

**Tags:** `integrations`, `third-party`, `apis`, `services`
**Last updated:** 2025-11-14

Third-party service integrations and configuration.

---

## Integrated Services

Cookbook Creator integrates with several third-party services:

### Anthropic Claude
➡️ **[Anthropic Claude Integration](anthropic-claude.md)**

AI-powered recipe extraction from images using Claude API.

**Key Features:**
- Recipe text extraction from photos
- Ingredient parsing
- Instruction formatting
- Metadata extraction

### Cloudinary
➡️ **[Cloudinary Integration](cloudinary.md)**

Image storage, optimization, and transformation.

**Key Features:**
- Image upload and storage
- Automatic optimization
- Responsive image delivery
- Image transformations

### Stripe
➡️ **[Stripe Integration](stripe.md)**

Payment processing and subscription management.

**Key Features:**
- Subscription plans
- Checkout sessions
- Webhook handling
- Payment history

### Lulu Print
➡️ **[Lulu Print Integration](lulu-print.md)**

Print-on-demand cookbook publishing.

**Key Features:**
- PDF generation
- Print order submission
- Order tracking
- Shipping integration

---

## Integration Architecture

```
┌──────────────┐
│   Frontend   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Backend    │
│   API        │
└──────┬───────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
┌─────────────┐ ┌──────────────┐
│  Anthropic  │ │  Cloudinary  │
│   Claude    │ │              │
└─────────────┘ └──────────────┘
       │             │
       ▼             ▼
┌─────────────┐ ┌──────────────┐
│   Stripe    │ │    Lulu      │
│             │ │    Print     │
└─────────────┘ └──────────────┘
```

---

## Configuration

### Environment Variables

All integrations require API keys configured in environment variables:

**Backend (.env):**
```bash
# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# Cloudinary
CLOUDINARY_URL=cloudinary://...

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Lulu
LULU_API_KEY=...
LULU_API_URL=https://api.lulu.com/
```

**Frontend (.env.local):**
```bash
# Stripe (public key)
VITE_STRIPE_PUBLIC_KEY=pk_live_...
```

### API Key Security

- Never commit API keys to repository
- Use different keys for development and production
- Rotate keys regularly
- Monitor API key usage
- Revoke compromised keys immediately

---

## Rate Limits

Each service has rate limits:

| Service | Rate Limit | Notes |
|---------|------------|-------|
| Anthropic Claude | 50 req/min | Per API key |
| Cloudinary | 500 req/hour | Free tier |
| Stripe | 100 req/sec | Per account |
| Lulu | 60 req/min | Per API key |

**Best Practices:**
- Implement exponential backoff
- Cache responses where possible
- Monitor usage to avoid limits
- Handle rate limit errors gracefully

---

## Error Handling

### Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def call_external_api():
    # API call here
    pass
```

### Circuit Breaker

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_external_api():
    # API call here
    pass
```

---

## Monitoring

### Metrics to Track

- **Request count** - Total API calls
- **Success rate** - Successful vs failed requests
- **Response time** - API latency
- **Error rate** - Failed requests
- **Cost** - API usage costs

### Alerts

Set up alerts for:
- Error rate > 5%
- Response time > 5s
- Rate limit approaching
- Unexpected cost increases

---

## Testing

### Development Testing

Use test/sandbox modes for development:

- **Anthropic:** Use lower-cost models for testing
- **Cloudinary:** Use test cloud name
- **Stripe:** Use test API keys (sk_test_...)
- **Lulu:** Use sandbox environment

### Integration Tests

```python
# Example integration test
def test_claude_recipe_extraction():
    response = claude_client.extract_recipe(image_url)
    assert response.status == "success"
    assert "ingredients" in response.data
    assert len(response.data["ingredients"]) > 0
```

---

## Cost Optimization

### Anthropic Claude
- Use appropriate model for task (Claude 3 Haiku for simple tasks)
- Cache common prompts
- Batch requests when possible
- Set max_tokens limits

### Cloudinary
- Enable automatic format optimization
- Use responsive images
- Set appropriate quality settings
- Clean up unused images

### Stripe
- Use webhooks instead of polling
- Cache subscription data
- Batch operations

### Lulu
- Validate before submission
- Use proof copies for testing
- Optimize PDF generation

---

## See Also

- [Backend Architecture](../architecture/backend-architecture.md)
- [Environment Variables](../deployment/environment-variables.md)
- [API Reference](../api/README.md)

---

[← Back to Documentation Home](../README.md)
