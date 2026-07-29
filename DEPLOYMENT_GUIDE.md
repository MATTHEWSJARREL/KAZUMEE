# Kazumee: Production Deployment Guide

**Solo Founder Deployment Strategy**  
Last Updated: 2026-07-28

---

## Table of Contents

1. [Pre-Launch Checklist](#pre-launch-checklist)
2. [Security Hardening](#security-hardening)
3. [Deployment Architecture](#deployment-architecture)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Post-Deployment Validation](#post-deployment-validation)
6. [Legal & Compliance](#legal--compliance)
7. [Payment Integration](#payment-integration)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Scaling Strategy](#scaling-strategy)

---

## Pre-Launch Checklist

### Frontend (Vercel)
- [ ] Landing page rebranded to "Kazumee" (✅ Done)
- [ ] Features section shows only real capabilities (✅ Done)
  - Auto-Detection
  - One-Click Download
  - Mobile Preview
  - Batch Export
- [ ] Pricing clearly displays free tier (5 free clips) and Pro ($9.99/month)
- [ ] Auth flow working: login → dashboard navigation smooth
- [ ] All form inputs validated
- [ ] Error messages user-friendly
- [ ] Mobile responsive design tested (iPhone, Android)
- [ ] Performance: Lighthouse score > 80

### Backend (Railway)
- [ ] DELETE /api/clips/{clip_id} endpoint working
- [ ] Rate limiting configured (development bypass for test endpoints)
- [ ] All API endpoints authenticated with RoleGuard
- [ ] Database migrations applied to production
- [ ] Environment variables securely stored
- [ ] Logging configured (exclude sensitive data)
- [ ] CORS headers set correctly for Vercel domain

### Database (PostgreSQL)
- [ ] Tables created: users, clips, stream_sessions, roles
- [ ] Indexes created for performance: user_id, stream_id, created_at
- [ ] Backup strategy in place
- [ ] Connection pooling configured

### Email & Communications
- [ ] Email provider configured (SendGrid, Resend, or similar)
- [ ] Welcome email template created
- [ ] Password reset flow tested
- [ ] Notification emails (new features, billing) configured

---

## Security Hardening

### 1. Environment Variables

**Railway Backend (.env)**
```bash
# Core
DATABASE_URL=postgresql://user:password@host:5432/kazumee
ENVIRONMENT=production
DEBUG=False

# Authentication
SECRET_KEY=<generate-with-secrets.token_hex(32)>
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# API Security
RATE_LIMIT_CALLS=100
RATE_LIMIT_PERIOD=3600
ALLOWED_ORIGINS=https://kazumee.com,https://www.kazumee.com

# Third-party APIs
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Optional: Voice & AI
GROQ_API_KEY=<your-api-key>
SERPER_API_KEY=<your-api-key>
```

**Vercel Frontend (.env.local)**
```bash
REACT_APP_API_URL=https://api.kazumee.com
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### 2. Database Security
- Enable SSL connections: `sslmode=require`
- Create read-only user for analytics queries
- Set up automated daily backups (Railway provides this)
- Rotate database password monthly

### 3. API Security Headers
Add to FastAPI backend (main.py):
```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kazumee.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.kazumee.com"]
)

# Add security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### 4. Rate Limiting
- Current: 100 requests per hour per IP
- Production: 100 for free tier, 500 for Pro tier
- Implement per-user rate limits on payment routes
- Disable rate limit bypass for test endpoints in production

### 5. Authentication
- LocalStorage tokens set to expire in 24 hours
- JWT tokens signed with SECRET_KEY (never hardcoded)
- Password hashing: bcrypt with salt rounds = 12
- Implement account lockout after 5 failed login attempts
- Two-factor authentication (2FA) roadmap item for V1.1

---

## Deployment Architecture

### Three-Service Architecture

```
┌─────────────────────────────────────────────────┐
│          Kazumee Production Stack                │
├─────────────────────────────────────────────────┤
│                                                  │
│  Vercel (Frontend)     Railway (Backend)   S3     │
│  ├─ Next.js App       ├─ FastAPI         (Object │
│  ├─ Landing Page      ├─ PostgreSQL      Storage)│
│  ├─ Dashboard         ├─ Redis (cache)   │
│  └─ Auth Pages        └─ Celery (jobs)   │
│                                          │
└─────────────────────────────────────────────────┘
```

### Service Responsibilities

**Frontend (Vercel)**
- Static landing page
- Authentication UI
- Dashboard & clip management
- Video preview & export
- Billing page

**Backend (Railway)**
- User management & auth
- Clip CRUD operations
- Stream moment detection (AI/ML)
- Batch export queueing
- Webhook handling (Stripe, Stream platform integrations)
- File uploads coordination (signed S3 URLs)

**Storage (Wasabi S3)**
- Clip video files (.mp4)
- User profile images
- Batch export temporary files
- Automated cleanup (30-day expiration for temp files)

---

## Step-by-Step Deployment

### Week 1: Setup & Configuration

#### Day 1: Railway Backend Setup
1. Create Railway project: `https://railway.app`
2. Connect GitHub repository
3. Set production environment variables
4. Deploy backend service
5. Run database migrations:
   ```bash
   railway run python -m alembic upgrade head
   ```
6. Verify API health: `GET /api/health`

#### Day 2: Vercel Frontend Setup
1. Create Vercel project
2. Connect GitHub repository
3. Set production environment variables
4. Set build command: `npm run build`
5. Set start command: `npm start`
6. Deploy frontend
7. Verify landing page loads: `https://kazumee.com`

#### Day 3-4: Database & Storage
1. Create PostgreSQL database on Railway
2. Set up Wasabi S3 bucket: `kazumee-clips`
3. Create S3 bucket policy for signed URLs
4. Test S3 upload via backend API
5. Verify video playback from S3

#### Day 5: Domain & SSL
1. Point domain to Vercel (CNAME records)
2. Point `api.` subdomain to Railway
3. Vercel auto-provisions SSL certificate
4. Railway auto-provisions SSL certificate
5. Test HTTPS on both frontend and backend

---

### Week 2: Integration & Testing

#### Day 6: Authentication Pipeline
1. Test login flow: email → password → JWT token
2. Verify token storage in localStorage
3. Test token expiry & refresh
4. Test logout & session cleanup
5. Test role-based access (streamer, viewer permissions)

#### Day 7: Core Features
1. Test clip creation workflow
2. Test batch export to TikTok/Shorts/Reels
3. Test vertical video preview (9:16)
4. Test clip deletion (soft delete)
5. Load test with 100 concurrent users

#### Day 8: Payment Integration
1. Create Stripe account (production mode)
2. Configure webhook endpoint: `/api/webhooks/stripe`
3. Test subscription flow: free tier signup → Pro upgrade
4. Test payment failure handling
5. Test invoice generation

#### Day 9: Email & Notifications
1. Configure email provider (SendGrid/Resend)
2. Test welcome email on signup
3. Test password reset email
4. Test subscription confirmation email
5. Test payment receipt email

#### Day 10: Security Audit
1. Run OWASP security checklist
2. Test SQL injection prevention
3. Test XSS protection
4. Test CSRF token validation
5. Penetration test with mock malicious requests

---

### Week 3: Launch Preparation

#### Day 11: Monitoring & Logging
1. Set up error tracking (Sentry)
2. Set up performance monitoring (DataDog or similar)
3. Set up log aggregation (CloudWatch/LogDNA)
4. Configure uptime monitoring (UptimeRobot)
5. Set up alerting for critical errors

#### Day 12: Documentation & Runbooks
1. Write deployment runbook (how to rollback, scale, etc.)
2. Write incident response guide
3. Create API documentation (OpenAPI/Swagger)
4. Document database schema
5. Document environment variables & secrets management

#### Day 13: Soft Launch
1. Beta invite 20-50 creators
2. Monitor error logs & performance
3. Gather feedback on UX/features
4. Fix critical bugs
5. Iterate on pricing or feature positioning based on feedback

#### Day 14: Production Launch
1. Update landing page: remove "Beta" tag
2. Enable all marketing channels
3. Monitor infrastructure 24/7 (enable on-call alerts)
4. Prepare communication for launch announcement
5. Celebrate 🎉

---

## Post-Deployment Validation

### Automated Tests (run on every deployment)
```bash
# Backend tests
pytest backend/tests/ -v --cov

# Frontend tests
npm test -- --coverage

# Integration tests
pytest backend/tests/integration/ -v
```

### Manual Validation Checklist
- [ ] Login with test account works
- [ ] Create clip works end-to-end
- [ ] Download clip returns valid MP4
- [ ] Batch export queues correctly
- [ ] Pricing page shows correct tiers
- [ ] Upgrade to Pro completes payment
- [ ] Cancel subscription works
- [ ] Error pages display gracefully (404, 500)
- [ ] Mobile UI works on iPhone 12 & Android
- [ ] Performance: page load < 3 seconds

### Performance Baselines
- API response time: < 200ms (p95)
- Page load time: < 2 seconds
- Database query time: < 100ms (p95)
- Uptime target: 99.5%

---

## Legal & Compliance

### 1. Terms of Service

**File:** `frontend/web/public/terms.md`

```markdown
# Terms of Service

**Last Updated:** 2026-07-28

## 1. Acceptance of Terms
By using Kazumee, you agree to these terms.

## 2. User Accounts
- You are responsible for maintaining account security
- You must not create accounts for minors
- You must not share account credentials

## 3. Content & Intellectual Property
- You retain ownership of clips you create
- You grant Kazumee license to process & store your content
- You may not use Kazumee to violate anyone's IP rights
- You may not use Kazumee to create defamatory, harassing, or illegal content

## 4. Payment Terms
- Subscriptions auto-renew monthly
- You can cancel anytime from settings
- Refunds are not available for partial months
- Kazumee reserves right to change pricing with 30 days notice

## 5. Service Level
- No guaranteed uptime (will add SLA in V1.1)
- Kazumee not responsible for lost, delayed, or corrupted files
- Backups your responsibility (we backup but don't guarantee recovery)

## 6. Limitation of Liability
- Kazumee provided "as is" without warranties
- Maximum liability: amount you paid in last 12 months
- Kazumee not liable for lost revenue or data

## 7. Termination
- Kazumee can terminate your account for ToS violation
- You can delete account anytime
- Data deletion: 30 days after account termination

## 8. Contact
- Email: support@kazumee.com
- For legal: legal@kazumee.com
```

### 2. Privacy Policy

**File:** `frontend/web/public/privacy.md`

```markdown
# Privacy Policy

**Last Updated:** 2026-07-28

## 1. Data We Collect
- Email, password hash (authentication)
- Stream metadata (for clip creation)
- Video files you upload
- Payment info (Stripe handles, we don't store)
- Usage analytics (anonymized)

## 2. How We Use Data
- Provide clip creation service
- Improve AI detection accuracy
- Send updates & billing info
- Comply with legal obligations

## 3. Data Sharing
- We do NOT sell your data
- Shared with: AWS/Railway (infrastructure), Stripe (payments)
- Shared if required by law

## 4. Data Retention
- Account data: deleted 30 days after account termination
- Clip files: kept until you delete
- Logs: kept for 90 days for security

## 5. Your Rights
- Right to access your data
- Right to delete your account
- Right to data portability
- Right to opt out of analytics

## 6. Security
- All data encrypted in transit (HTTPS)
- Database encrypted at rest
- Passwords hashed with bcrypt
- No passwords ever logged

## 7. Changes to Policy
- We'll email if material changes
- Continued use means acceptance

## 8. Contact
- Email: privacy@kazumee.com
```

### 3. Launch Checklist
- [ ] Terms of Service published at `/terms`
- [ ] Privacy Policy published at `/privacy`
- [ ] GDPR compliance reviewed
- [ ] CCPA compliance reviewed (if serving California users)
- [ ] DMCA takedown policy published
- [ ] Refund policy published
- [ ] Cookie consent banner added
- [ ] Data processing agreement ready for enterprise customers

---

## Payment Integration

### Stripe Setup

#### Step 1: Create Stripe Account
1. Go to `https://dashboard.stripe.com`
2. Create account (business type: SaaS)
3. Complete identity verification
4. Switch to live mode (after testing)

#### Step 2: Create Products & Prices
```json
{
  "products": [
    {
      "id": "free",
      "name": "Free Tier",
      "features": ["5 clips/month", "1080p export", "Basic support"]
    },
    {
      "id": "pro",
      "name": "Pro",
      "price": "$9.99/month",
      "features": ["Unlimited clips", "4K export", "Priority support", "Batch export"]
    }
  ]
}
```

#### Step 3: Webhook Configuration
1. Create webhook endpoint: `https://api.kazumee.com/api/webhooks/stripe`
2. Enable events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`

#### Step 4: Backend Integration
```python
# backend/api/routes/billing.py
from stripe import Stripe

stripe_client = Stripe(os.getenv("STRIPE_SECRET_KEY"))

@router.post("/create-subscription")
async def create_subscription(user_id: int, price_id: str):
    user = await get_user(user_id)
    customer = stripe_client.Customer.create(email=user.email)
    subscription = stripe_client.Subscription.create(
        customer=customer.id,
        items=[{"price": price_id}],
        payment_behavior="default_incomplete",
    )
    return {"session_id": subscription.id}

@router.webhook("/stripe")
async def stripe_webhook(request: Request):
    # Validate signature
    # Update user subscription status
    # Sync with database
    pass
```

---

## Monitoring & Maintenance

### Daily Monitoring
- [ ] Check error rate (target: < 0.1%)
- [ ] Check API response time (target: < 200ms)
- [ ] Check database connections (target: < 80% utilization)
- [ ] Check disk space (target: < 80% utilization)
- [ ] Review security logs for anomalies

### Weekly Maintenance
- [ ] Review error logs & fix bugs
- [ ] Check for failed webhooks (Stripe, integrations)
- [ ] Verify backups completed successfully
- [ ] Update dependencies (if patches available)
- [ ] Review user feedback & feature requests

### Monthly Tasks
- [ ] Full security audit
- [ ] Performance optimization
- [ ] Database maintenance (VACUUM, REINDEX)
- [ ] Cost optimization review
- [ ] Roadmap planning

### Incident Response

**Critical Issue (API down, data breach):**
1. Page on-call engineer immediately
2. Investigate root cause
3. Implement emergency fix
4. Post incident report
5. Schedule postmortem (48 hours later)

---

## Scaling Strategy

### Phase 1: MVP (Months 1-3)
- **Users:** 0 → 1,000
- **Infrastructure:**
  - Railway: Standard plan ($12/month)
  - Vercel: Pro ($20/month)
  - PostgreSQL: Hobby plan ($9/month)
  - S3: 100GB @ $0.023/GB = ~$2.30/month
- **Total:** ~$43/month infrastructure

### Phase 2: Growth (Months 4-12)
- **Users:** 1,000 → 10,000
- **Scaling actions:**
  - Railway: upgrade to Performance plan ($50/month)
  - Add Redis for session caching
  - Enable CDN for video files (Wasabi CDN)
  - Database connection pooling
- **Total:** ~$150/month infrastructure

### Phase 3: Scale (Year 2+)
- **Users:** 10,000+
- **Scaling actions:**
  - Move to self-managed database (better cost at scale)
  - Migrate to object-oriented S3 service (Backblaze B2)
  - Add load balancer
  - Regional deployment (API in multiple regions)
  - Implement content delivery network globally
- **Total:** $500+/month (but also generating revenue)

### Cost Management
- Set up CloudWatch alarms for cost overages
- Review cost quarterly
- Use reserved instances for predictable workloads
- Optimize database queries (monitor slow queries weekly)

---

## Day-1 Launch Checklist

### Morning (Before going live)
- [ ] All environment variables configured
- [ ] Database migrations applied
- [ ] Backups verified
- [ ] SSL certificates validated
- [ ] Rate limiting configured for production
- [ ] Error tracking enabled (Sentry)
- [ ] Monitoring enabled
- [ ] On-call rotation activated
- [ ] Support email monitored
- [ ] Runbooks reviewed by team

### Deployment
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel
- [ ] Verify DNS propagation
- [ ] Test all critical flows:
  - Sign up → login → dashboard
  - Create clip → download
  - Upgrade to Pro → payment
  - Contact support

### Post-Launch (First 24 hours)
- [ ] Monitor error logs every hour
- [ ] Respond to user issues immediately
- [ ] Check performance metrics
- [ ] Be ready to rollback if critical issues
- [ ] Celebrate with first users! 🎉

---

## Emergency Contacts

| Role | Contact | Escalation |
|------|---------|-----------|
| Stripe Support | support@stripe.com | Account manager |
| Railway Support | support@railway.app | In-app chat |
| Vercel Support | support@vercel.com | In-app chat |
| Domain Registrar | support@[registrar] | Account settings |

---

## Rollback Procedure

If critical issues post-launch:

```bash
# Frontend rollback (Vercel)
# Navigate to Deployments → select previous version → click "Promote to Production"

# Backend rollback (Railway)
# Navigate to Deployments → select previous version → click "Redeploy"

# Database rollback (if data corrupted)
# Contact Railway support for point-in-time restore
# Estimated recovery time: 1-2 hours
```

---

## Post-Launch: First 90 Days Roadmap

### Week 1-2: Stabilization
- Monitor infrastructure
- Fix critical bugs
- Respond to user support tickets
- Gather early user feedback

### Week 3-4: First Improvements
- Add 2FA security
- Improve error messages
- Optimize video export speed
- Add analytics dashboard

### Month 2: Feature Expansion
- Add caption burning (if demand high)
- Add streaming platform integrations
- Add team collaboration features
- Add advanced analytics

### Month 3: Monetization
- Implement enterprise plans
- Add Team tier ($29/month)
- Prepare affiliate program
- Plan first paid marketing campaign

---

**Created by:** Claude Code  
**For:** Kazumee Solo Founder Launch  
**Status:** Ready for Production Deployment

---

## Questions? Next Steps?

1. **Before launching:** Run through security hardening checklist with this guide
2. **During Week 1:** Follow deployment steps in order
3. **Launch Day:** Use Day-1 Launch Checklist
4. **Post-Launch:** Monitor using monitoring & maintenance guidelines

Good luck! Your first users are waiting. 🚀
