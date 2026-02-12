# Production Readiness Roadmap

**Created:** 2026-02-09
**Goal:** Address production gaps to ensure reliability, security, and operational excellence

---

## Phase 1: Critical (Before Public Launch)
**Timeline: 1-2 days**

### 1.1 CI/CD Pipeline
- [x] Create `.github/workflows/ci.yml` for automated testing
  - [x] Run backend tests on every PR (PDF tests - 49 passing)
  - [x] Run linting/type checks (informational, not blocking)
  - [x] Run frontend TypeScript build
  - [x] Fix API tests to include auth fixtures (67 tests now passing)
  - [x] Fix lint errors (all fixed with ruff auto-fix + config updates)
- [ ] Create `.github/workflows/deploy.yml` for deployment
  - Auto-deploy to Render on merge to main
  - Or use Render's native GitHub integration

### 1.2 Fix Sentry Configuration
- [x] Move frontend Sentry DSN to environment variable
  - [x] Update `frontend/src/main.tsx` to use `import.meta.env.VITE_SENTRY_DSN`
  - [x] Add `VITE_SENTRY_DSN` to `.env.production.example`
  - [x] Remove hardcoded DSN from source code
  - [x] Add `VITE_SENTRY_DSN` to Render environment variables

### 1.3 Basic Alerting
- [x] Create alerting setup guide (`docs/operations/ALERTING_SETUP.md`)
- [x] Configure Sentry alerts for production errors
  - Alert on first occurrence of new errors
  - Alert when error rate spikes
- [ ] Set up uptime monitoring with UptimeRobot (TODO - see guide)
  - Monitor `/api/health` endpoint
  - Email/SMS alerts on downtime

---

## Phase 2: High Priority (Week 1-2 Post-Launch)
**Timeline: 1-2 weeks**

### 2.1 GDPR/Privacy Compliance
- [x] Add cookie consent banner
  - [x] Installed `react-cookie-consent` library
  - [x] Created CookieConsentContext for managing consent state
  - [x] Created CookieConsentBanner component
  - [x] Block Sentry analytics/tracking until consent given
- [ ] Add consent tracking to database (optional - localStorage used for now)
- [x] Update Privacy Policy with cookie details

### 2.2 Log Aggregation
- [ ] Set up Papertrail (or similar) with Render
  - Configure log drain in Render dashboard
  - Set up log alerts for errors
- [ ] Create saved searches for common issues
  - 500 errors
  - Authentication failures
  - Slow requests (>5s)

### 2.3 Incident Response
- [x] Create `docs/operations/incident-response.md`
  - [x] Define severity levels (P1-P4)
  - [x] Document escalation procedures
  - [x] List key contacts
  - [x] Create runbooks for common issues:
    - [x] Database connection failures
    - [x] Redis unavailable
    - [x] High error rate
    - [x] Celery worker down
    - [x] Frontend not loading
    - [x] Payment processing failures
    - [x] API rate limiting issues
  - [x] Add post-incident report template

### 2.4 Dependency Security
- [ ] Add `npm audit` to CI pipeline
- [ ] Add `pip-audit` or `safety` check to CI pipeline
- [ ] Set up Dependabot or Renovate for automated updates

---

## Phase 3: Important (Month 1)
**Timeline: 2-4 weeks**

### 3.1 Frontend Testing
- [ ] Set up Vitest + React Testing Library
- [ ] Add tests for critical user flows:
  - [ ] Login/logout
  - [ ] Recipe upload
  - [ ] Recipe viewing
  - [ ] Cookbook creation
- [ ] Add to CI pipeline
- [ ] Target: 50% coverage of critical paths

### 3.2 Test Coverage Reporting
- [ ] Add pytest-cov to backend
- [ ] Configure coverage thresholds (e.g., fail if <70%)
- [ ] Add coverage badge to README
- [ ] Add coverage report to PR comments

### 3.3 API Documentation Improvements
- [ ] Document authentication flow with examples
- [ ] Document rate limits per endpoint
- [ ] Create error code reference
- [ ] Consider OpenAPI/Swagger spec generation

### 3.4 Performance Baseline
- [ ] Run load tests and document baseline metrics
- [ ] Set up performance monitoring in Sentry
- [ ] Document acceptable response times
- [ ] Create performance tuning guide

---

## Phase 4: Operational Excellence (Month 2-3)
**Timeline: Ongoing**

### 4.1 High Availability
- [ ] Evaluate multi-region deployment options
- [ ] Document disaster recovery plan (RTO/RPO)
- [ ] Test backup/restore procedures
- [ ] Consider read replicas for database

### 4.2 Auto-scaling
- [ ] Configure Render auto-scaling rules
- [ ] Set up scaling alerts
- [ ] Load test to find scaling thresholds

### 4.3 Security Hardening
- [ ] Schedule quarterly security audits
- [ ] Implement secrets rotation policy
- [ ] Review and tighten CSP (remove unsafe-inline where possible)
- [ ] Consider penetration testing

### 4.4 Operational Runbooks
- [ ] Create runbook for each major component
- [ ] Document common maintenance tasks
- [ ] Create on-call rotation documentation

---

## Quick Reference: External Services Needed

| Service | Purpose | Cost | Priority |
|---------|---------|------|----------|
| GitHub Actions | CI/CD | Free (2000 min/mo) | P1 |
| UptimeRobot | Uptime monitoring | Free (50 monitors) | P1 |
| Papertrail | Log aggregation | Free tier available | P2 |
| Termly/CookieBot | Cookie consent | Free tier available | P2 |
| Dependabot | Dependency updates | Free | P2 |

---

## Success Metrics

### Phase 1 Complete When:
- [ ] Every PR runs automated tests
- [ ] No secrets in source code
- [ ] Get alerted within 5 minutes of downtime

### Phase 2 Complete When:
- [ ] GDPR-compliant cookie consent in place
- [ ] Can search logs for any request
- [ ] Incident response plan documented and tested

### Phase 3 Complete When:
- [ ] Frontend has >50% test coverage on critical paths
- [ ] Backend has >70% test coverage
- [ ] API fully documented with examples

### Phase 4 Complete When:
- [ ] Can recover from regional outage in <1 hour
- [ ] Auto-scaling handles 10x normal load
- [ ] Security audit completed with no critical findings

---

## Notes

- Prioritize Phase 1 items - these are blockers for confident production operation
- Phase 2 items reduce legal risk and improve debuggability
- Phase 3 items prevent regressions and improve developer experience
- Phase 4 items are for scale and long-term operational health

This roadmap should be reviewed and updated monthly.
