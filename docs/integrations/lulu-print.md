# Lulu Print-on-Demand Integration

**Tags:** `integration`, `lulu`, `print-on-demand`, `cookbook-printing`, `third-party-api`
**Last updated:** 2025-11-14
**Status:** In Progress (55% complete)

Complete implementation guide for the Lulu Print-on-Demand integration, enabling users to order physical printed cookbooks directly from the application.

---

## Overview

The Lulu Print-on-Demand integration allows Cookbook Creator users to order professionally printed physical copies of their digital cookbooks. This integration handles the complete order workflow from PDF generation through payment processing to fulfillment tracking.

### Key Capabilities

- **Automated PDF Generation**: Convert digital cookbooks to print-ready PDFs meeting Lulu's specifications
- **Real-time Pricing**: Get instant quotes based on print specifications and quantity
- **Order Management**: Submit orders, track status, and handle fulfillment
- **Payment Processing**: Integrated with Stripe for secure payment handling
- **Quality Validation**: Automated validation of PDFs before submission

### Integration Status

- **Completed Tasks**: 18/33 (55%)
- **Current Phase**: Core API Integration (Phase 1) - Completed
- **Next Milestone**: MVP Print Ordering (Target: 2025-01-20)

---

## Architecture

### Components

```
┌─────────────────┐
│   Frontend UI   │  Print order flow, cover selection, preview
└────────┬────────┘
         │
┌────────▼────────┐
│  Flask Backend  │  Order orchestration, validation
└────────┬────────┘
         │
    ┌────┴────┬───────────┬─────────────┐
    │         │           │             │
┌───▼────┐ ┌─▼──────┐ ┌──▼─────┐ ┌────▼────┐
│  Lulu  │ │ Stripe │ │  PDF   │ │  Cloud  │
│  API   │ │Payment │ │ Generator│ │ Storage │
└────────┘ └────────┘ └────────┘ └─────────┘
```

### Service Layer

The integration is implemented in `app/services/lulu_service.py` with the following key methods:

- `get_oauth_token()` - OAuth authentication with automatic refresh
- `upload_pdf_file()` - Upload interior and cover PDFs
- `create_print_job()` - Submit print orders to Lulu
- `get_job_status()` - Poll order status and shipping information
- `get_service_status()` - Check Lulu API health and quotas

---

## Implementation Roadmap

### Phase 1: Core Lulu API Integration ✅ **COMPLETED**

Complete foundational API service implementation.

#### 1.1 OAuth Token Refresh ✅

**Status:** Completed
**Files:** `app/services/lulu_service.py`

**Features:**
- Automatic token refresh with 10-minute buffer before expiration
- Graceful handling of refresh failures with retry logic
- Secure token storage with expiration tracking
- Forced refresh capability for 401 error recovery

#### 1.2 File Upload ✅

**Status:** Completed
**Files:** `app/services/lulu_service.py`

**Features:**
- Three-step upload process for interior PDFs
- Cover PDF upload with validation
- Error handling with retry logic
- Enhanced validation and detailed error reporting

#### 1.3 Print Job Creation ✅

**Status:** Completed
**Files:** `app/services/lulu_service.py`

**Features:**
- Create print jobs with correct specifications
- File association with print jobs
- Returns Lulu job ID and line item ID
- Validation error handling
- Book metadata and external order reference support

#### 1.4 Order Status Polling ✅

**Status:** Completed
**Files:** `app/services/lulu_service.py`

**Features:**
- Query job status by Lulu job ID
- Comprehensive status state handling
- Batch status polling for multiple jobs
- Shipping, cost, and timeline information
- Job event history tracking

#### 1.5 Enhanced Error Handling ✅

**Status:** Completed
**Files:** `app/services/lulu_service.py`

**Features:**
- Comprehensive logging with context
- Typed exception classes for different failure modes
- Exponential backoff retry logic for transient failures
- Graceful degradation when Lulu unavailable
- Service status checking and quota monitoring
- Retry recommendations per error type

---

### Phase 2: Payment Integration ⏳ **PENDING**

Integrate Stripe for print order payments.

#### 2.1 Print Order Payments

**Status:** Pending
**Priority:** High
**Files:** `app/api/print_orders.py`, `app/services/payment_service.py`

**Requirements:**
- Create Stripe payment intents for print orders
- Handle payment confirmation flow
- Link payments to print orders in database
- Support saved payment methods

#### 2.2 Dynamic Pricing

**Status:** Pending
**Priority:** Medium
**Files:** `app/services/lulu_service.py`, `app/api/print_orders.py`

**Requirements:**
- Real-time pricing from Lulu API
- Configurable platform markup percentage
- Tax calculation where applicable
- Shipping cost calculation by destination

#### 2.3 Refund Handling

**Status:** Pending
**Priority:** Low
**Files:** `app/api/print_orders.py`, `app/services/payment_service.py`

**Requirements:**
- Cancel orders before printing starts
- Process refunds through Stripe
- Update order status correctly
- Handle partial refunds for multi-item orders

---

### Phase 3: Testing & Validation ⏳ **PENDING**

Comprehensive testing of the integration.

#### 3.1 Lulu Sandbox Testing

**Status:** Pending
**Priority:** Critical
**Files:** `tests/test_lulu_integration.py`, `scripts/test_lulu_sandbox.py`

**Test Coverage:**
- End-to-end order creation in sandbox environment
- PDF upload and validation testing
- Order status progression through all states
- Error scenario and recovery testing

#### 3.2 PDF Quality Validation

**Status:** Pending
**Priority:** High
**Files:** `tests/test_pdf_generation.py`, `app/utils/pdf_validator.py`

**Validation Requirements:**
- Print-ready PDF specifications (resolution, color space)
- Bleed and trim requirement verification
- Color space (CMYK) and resolution (300 DPI) checks
- Testing with various cookbook sizes and page counts

#### 3.3 End-to-End Testing

**Status:** Pending
**Priority:** Medium
**Files:** `tests/test_e2e_print_orders.py`

**Test Scenarios:**
- Complete user journey from order to delivery
- Payment to print job creation flow
- Status updates throughout process
- Error recovery and retry mechanisms

---

### Phase 4: User Interface ⏳ **PENDING**

Frontend implementation for print ordering.

#### 4.1 Print Order Flow UI

**Status:** Pending
**Priority:** High
**Files:** `frontend/src/components/print/`, `frontend/src/pages/PrintOrder.tsx`

**Features:**
- Trim size selection (6x9, 8x10, 8.5x11, etc.)
- Binding type selection (paperback, hardcover)
- Quantity input with bulk pricing display
- Shipping options and address entry
- Real-time cost calculation preview
- Order confirmation and review screen

#### 4.2 Cover Template Selection

**Status:** Pending
**Priority:** Medium
**Files:** `frontend/src/components/cover/`

**Features:**
- Browse cover template gallery
- Preview templates with cookbook content
- Customize cover (title, colors, layout)
- Real-time preview generation
- Cover validation feedback

#### 4.3 Order Management Dashboard

**Status:** Pending
**Priority:** Medium
**Files:** `frontend/src/components/orders/`, `frontend/src/pages/Orders.tsx`

**Features:**
- Order history table with filters
- Real-time status updates (polling)
- Order tracking information display
- Cancel/refund capabilities
- Reorder functionality

#### 4.4 Print Preview System

**Status:** Pending
**Priority:** Low
**Files:** `frontend/src/components/preview/`

**Features:**
- PDF preview in browser
- Interior and cover previews
- Print specifications display
- Download preview PDFs for review

---

### Phase 5: Production Setup ⏳ **PENDING**

Production deployment and configuration.

#### 5.1 Environment Configuration

**Status:** Pending
**Priority:** High
**Files:** `.env.production`, `app/config.py`

**Requirements:**
- Production Lulu API credentials setup
- Secure credential storage (environment variables or secrets manager)
- Environment-specific configurations (sandbox vs production)
- Deployment scripts and CI/CD integration

#### 5.2 Webhook Endpoints Setup

**Status:** Pending
**Priority:** Medium
**Files:** `app/api/print_webhooks.py`

**Requirements:**
- Webhook endpoint registration with Lulu
- Request signature verification
- Status update processing and database updates
- Error handling and retry logic for webhooks

#### 5.3 File Storage Setup

**Status:** Pending
**Priority:** Medium
**Files:** `app/services/storage_service.py`

**Requirements:**
- Cloud storage integration (AWS S3 or similar)
- PDF file organization and naming conventions
- Access control and security policies
- File cleanup policies (retention periods)

#### 5.4 Monitoring and Logging

**Status:** Pending
**Priority:** Low
**Files:** `app/utils/monitoring.py`

**Requirements:**
- Print order metrics (orders/day, success rate)
- Error rate monitoring and alerting
- Performance tracking (API latency, upload times)
- Alert configuration for critical failures

---

### Phase 6: Advanced Features ⏳ **PENDING**

Additional features and enhancements.

#### 6.1 Bulk Orders Support

**Status:** Pending
**Priority:** Medium

**Features:**
- Quantity discounts for bulk orders
- Bulk upload capabilities
- Batch processing optimization
- Inventory management tracking

#### 6.2 International Shipping

**Status:** Pending
**Priority:** Low

**Features:**
- International shipping rate calculation
- Customs documentation generation
- Currency conversion
- Regional restriction handling

#### 6.3 Order Tracking Integration

**Status:** Pending
**Priority:** Low

**Features:**
- Shipping carrier tracking number integration
- Delivery status updates
- Customer notifications (email/SMS)
- Delivery confirmation

#### 6.4 Customer Support Tools

**Status:** Pending
**Priority:** Low

**Features:**
- Admin order management interface
- Issue tracking system
- Customer communication tools
- Resolution workflows and escalation

---

### Phase 7: Documentation & Training ⏳ **PENDING**

Documentation and user guidance.

#### 7.1 API Documentation

**Status:** Pending
**Priority:** Medium

**Deliverables:**
- Complete API reference for print endpoints
- Example requests and responses
- Error code documentation
- Integration guide for developers

#### 7.2 User Guide Documentation

**Status:** Pending
**Priority:** Low

**Deliverables:**
- Step-by-step ordering guide
- Print option explanations (trim sizes, bindings)
- Quality guidelines and recommendations
- FAQ section

#### 7.3 Troubleshooting Guide

**Status:** Pending
**Priority:** Low

**Deliverables:**
- Common error scenarios and solutions
- Resolution procedures
- Diagnostic tools usage
- Escalation procedures

---

## Current Implementation

### Authentication

The LuluService handles OAuth 2.0 authentication automatically:

```python
# Authentication is handled transparently
service = LuluService()
token = service.get_oauth_token()  # Automatically refreshes if needed
```

### Uploading PDFs

```python
# Upload interior PDF (3-step process)
interior_url = service.upload_pdf_file(
    pdf_path="/path/to/interior.pdf",
    file_type="interior"
)

# Upload cover PDF
cover_url = service.upload_pdf_file(
    pdf_path="/path/to/cover.pdf",
    file_type="cover"
)
```

### Creating Print Jobs

```python
# Create a print job
job_response = service.create_print_job(
    interior_file_url=interior_url,
    cover_file_url=cover_url,
    title="My Cookbook",
    quantity=1,
    shipping_address={...}
)

lulu_job_id = job_response['id']
line_item_id = job_response['line_items'][0]['id']
```

### Checking Order Status

```python
# Get detailed order status
status = service.get_job_status(lulu_job_id)

print(f"Status: {status['status']}")
print(f"Tracking: {status.get('tracking_number')}")
print(f"Estimated delivery: {status.get('estimated_delivery_date')}")
```

---

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Lulu API Configuration
LULU_API_KEY=your_api_key
LULU_API_SECRET=your_api_secret
LULU_BASE_URL=https://api.sandbox.lulu.com  # or https://api.lulu.com for production
LULU_WEBHOOK_SECRET=your_webhook_secret

# Print Order Settings
PRINT_MARKUP_PERCENTAGE=20  # Platform markup on Lulu base price
MAX_PRINT_QUANTITY=100
```

### Print Specifications

Supported trim sizes:
- 6" x 9" (standard cookbook size)
- 8" x 10" (large format)
- 8.5" x 11" (letter size)

Supported binding types:
- Paperback (perfect binding)
- Hardcover (case laminate)

Paper options:
- Standard white (50lb/74gsm)
- Premium white (60lb/90gsm)
- Cream (50lb/74gsm)

---

## Testing

### Sandbox Environment

Lulu provides a sandbox environment for testing without creating real orders:

```bash
# Set sandbox URL in .env
LULU_BASE_URL=https://api.sandbox.lulu.com

# Run integration tests
uv run pytest tests/test_lulu_integration.py -v
```

### Test Script

Use the provided test script to verify the integration:

```bash
# Test complete order flow in sandbox
uv run python scripts/test_lulu_sandbox.py
```

---

## Milestones

### MVP Print Ordering (Target: 2025-01-20)

**Required Tasks:**
- ✅ OAuth token refresh implementation
- ✅ File upload completion
- ✅ Print job creation
- ⏳ Lulu sandbox testing
- ⏳ Print order payments

**Goal:** Users can order physical cookbooks with basic functionality.

### Production Ready (Target: 2025-02-15)

**Required Tasks:**
- Environment configuration
- Webhook endpoints setup
- PDF quality validation
- Print order flow UI

**Goal:** Stable, secure production deployment with complete user flow.

### Full Feature Set (Target: 2025-03-15)

**Required Tasks:**
- Order management dashboard
- Cover template selection
- Bulk orders support
- API documentation

**Goal:** Feature-complete print ordering system with all enhancements.

---

## Dependencies

### External Services

- **Lulu API**: Print-on-demand service (sandbox access required for testing)
- **Stripe**: Payment processing setup and configuration
- **AWS S3** (or similar): Cloud storage for generated PDFs
- **SSL Certificate**: Required for webhook endpoints

### Internal Dependencies

- PDF generation service (cookbook to PDF conversion)
- Image processing service (cover generation)
- Payment service (Stripe integration)
- Email service (order notifications)

---

## Risk Assessment

### High-Impact Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Lulu API changes | High | Version pinning, comprehensive testing, monitoring |
| Payment processing failures | High | Robust error handling, manual recovery tools, transaction logging |

### Medium-Impact Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| PDF generation performance | Medium | Background job processing, caching, optimization |
| File storage costs | Medium | Retention policies, compression, monitoring |
| International shipping complexity | Medium | Start with domestic only, phased rollout |

---

## Troubleshooting

### Common Issues

**Issue: "OAuth token expired" errors**
- **Cause:** Token refresh logic not working correctly
- **Solution:** Check `LULU_API_KEY` and `LULU_API_SECRET` are correct; verify token expiration buffer (10 minutes)

**Issue: "PDF validation failed"**
- **Cause:** PDF doesn't meet Lulu's specifications
- **Solution:** Verify resolution (300 DPI), color space (CMYK), and bleed/trim settings; use `app/utils/pdf_validator.py`

**Issue: "File upload timeout"**
- **Cause:** Large PDF files taking too long to upload
- **Solution:** Increase timeout settings; implement chunked upload; optimize PDF size

**Issue: "Order stuck in 'processing' status"**
- **Cause:** Lulu processing delay or webhook not received
- **Solution:** Poll status endpoint manually; check webhook endpoint accessibility; verify webhook signature validation

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger('app.services.lulu_service').setLevel(logging.DEBUG)
```

---

## Security Considerations

- **API Credentials**: Never commit credentials; use environment variables or secret manager
- **Webhook Signatures**: Always verify webhook request signatures
- **User Data**: Minimize PII in print orders; comply with data retention policies
- **Payment Security**: PCI compliance through Stripe; never store full card details
- **File Access**: Secure PDF storage with time-limited access URLs

---

## Performance Considerations

- **PDF Generation**: Offload to background jobs (Celery/RQ)
- **File Uploads**: Large PDFs may take 30-60 seconds; show progress indicators
- **Status Polling**: Use exponential backoff; consider webhook-based updates
- **Caching**: Cache Lulu pricing quotes for 1 hour
- **Database**: Index order status and user_id columns for fast queries

---

## See Also

- [Stripe Integration](stripe.md) - Payment processing setup
- [Cloudinary Integration](cloudinary.md) - Image handling for covers
- [API Reference: Print Orders](../api/print-orders-endpoints.md) - Print order endpoints (when created)
- [Operations: Background Jobs](../operations/background-jobs.md) - Job processing setup (when created)

---

[← Back to Integrations](README.md) | [Back to Documentation Home](../README.md)
