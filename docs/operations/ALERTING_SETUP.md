# Alerting Setup Guide

This guide covers setting up alerts for production monitoring.

## 1. Sentry Alerts

Sentry is already integrated for error tracking. Configure alerts in the Sentry dashboard.

### Access Sentry Dashboard
1. Go to https://sentry.io
2. Navigate to your project: `cookvault` (or the project name you used)

### Recommended Alert Rules

#### Alert 1: First Occurrence of New Issues
Notifies when a new error type appears for the first time.

1. Go to **Alerts** > **Create Alert Rule**
2. Select **Issues** as the alert type
3. Configure:
   - **When:** A new issue is created
   - **Filter:** `environment:production`
   - **Then:** Send notification to your email/Slack
   - **Action interval:** 1 hour (prevents spam for same issue)

#### Alert 2: Error Rate Spike
Notifies when errors increase significantly.

1. Go to **Alerts** > **Create Alert Rule**
2. Select **Metric** as the alert type
3. Configure:
   - **Metric:** Number of errors
   - **Threshold:** When error count is above 10 in 1 hour
   - **Filter:** `environment:production`
   - **Then:** Send notification to your email/Slack

#### Alert 3: High Error Rate
Notifies when error percentage is high.

1. Create another Metric alert
2. Configure:
   - **Metric:** Error rate (percentage)
   - **Threshold:** When error rate is above 5% in 15 minutes
   - **Filter:** `environment:production`

### Notification Channels
- **Email:** Added by default
- **Slack:** Go to Settings > Integrations > Slack
- **PagerDuty:** Go to Settings > Integrations > PagerDuty (for on-call)

---

## 2. Uptime Monitoring (UptimeRobot)

UptimeRobot provides free uptime monitoring with email/SMS alerts.

### Setup Steps

1. **Create Account**
   - Go to https://uptimerobot.com
   - Sign up for free (50 monitors included)

2. **Add Health Check Monitor**
   - Click **Add New Monitor**
   - Configure:
     - **Monitor Type:** HTTP(s)
     - **Friendly Name:** CookVault API
     - **URL:** `https://cookvault-exaq.onrender.com/api/health`
     - **Monitoring Interval:** 5 minutes
   - Click **Create Monitor**

3. **Add Frontend Monitor**
   - Click **Add New Monitor**
   - Configure:
     - **Monitor Type:** HTTP(s)
     - **Friendly Name:** CookVault Frontend
     - **URL:** `https://cookvault-frontend.onrender.com`
     - **Monitoring Interval:** 5 minutes
   - Click **Create Monitor**

4. **Configure Alert Contacts**
   - Go to **My Settings** > **Alert Contacts**
   - Add your email address
   - (Optional) Add SMS number for critical alerts
   - (Optional) Add Slack webhook

5. **Associate Contacts with Monitors**
   - Edit each monitor
   - Under **Alert Contacts**, select your contacts
   - Save changes

### Recommended Monitors

| Monitor | URL | Interval |
|---------|-----|----------|
| API Health | `https://cookvault-exaq.onrender.com/api/health` | 5 min |
| Frontend | `https://cookvault-frontend.onrender.com` | 5 min |
| Simple Health | `https://cookvault-exaq.onrender.com/health` | 5 min |

---

## 3. Verification

After setup, verify alerts are working:

1. **Sentry:** Trigger a test error in development and verify it appears
2. **UptimeRobot:** Check the dashboard shows monitors as "Up"
3. **Test downtime alert:** (Optional) Temporarily change URL to invalid and verify alert

---

## Quick Reference

| Service | Dashboard | Purpose |
|---------|-----------|---------|
| Sentry | https://sentry.io | Error tracking & alerts |
| UptimeRobot | https://uptimerobot.com | Uptime monitoring |

## Health Endpoint Details

The `/api/health` endpoint checks:
- Database connectivity
- Redis connectivity
- Upload folder accessibility

Returns `200 OK` when healthy, `503 Service Unavailable` when unhealthy.
