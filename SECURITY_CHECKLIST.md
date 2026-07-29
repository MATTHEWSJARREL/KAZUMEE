# 🔒 Kazumee Security Checklist

**BEFORE DEPLOYING TO ANY STREAMER**, verify all security measures are in place.

## Authentication & Authorization

- [x] All clip endpoints require streamer authentication
  - [x] GET /api/clips/pending - auth required
  - [x] GET /api/clips/recent - auth required
  - [x] DELETE /api/clips/{id} - auth required
  - [x] POST /api/clips/{id}/export - auth required

- [x] Clips filtered by streamer_id (no cross-streamer access)
  - [x] Streamer can only see their own clips
  - [x] Streamer can only delete their own clips
  - [x] Streamer can only export their own clips

- [x] Settings endpoints require authentication
  - [x] GET /api/moments/settings - auth required
  - [x] PUT /api/moments/settings - auth required

- [ ] **TODO: API Keys for external integrations**
  - [ ] Twitch OAuth tokens encrypted at rest
  - [ ] YouTube API keys encrypted at rest
  - [ ] Groq API key encrypted at rest
  - [ ] OBS WebSocket password encrypted at rest

## OBS Security

- [ ] **CRITICAL: OBS WebSocket connection security**
  - [ ] Verify OBS connection is to trusted host only
  - [ ] Add password authentication for OBS WebSocket
  - [ ] Use SSL/TLS for remote OBS connections
  - [ ] Validate OBS certificate on production

- [ ] **Prevent unauthorized OBS commands**
  - [ ] Whitelist allowed OBS commands
  - [ ] Prevent scene switching except by streamer
  - [ ] Prevent audio level changes except by streamer
  - [ ] Prevent stream start/stop except by streamer

## Data Security

- [x] Clips stored with file paths (can be restricted to user directories)
- [ ] **TODO: Clip files stored outside web root**
  - [ ] Prevent direct file access via HTTP
  - [ ] Only serve through authenticated API
  - [ ] Implement file access logging

- [ ] **TODO: Database encryption**
  - [ ] Encrypt sensitive fields at rest
  - [ ] Use SSL/TLS for database connections
  - [ ] Implement connection pooling limits

- [ ] **TODO: Session security**
  - [ ] Session tokens rotated on sensitive actions
  - [ ] Session timeout on inactivity
  - [ ] Logout invalidates all sessions

## API Security

- [x] CORS properly configured for known origins only
- [x] Rate limiting on authentication endpoints
- [ ] **TODO: Rate limiting on all endpoints**
  - [ ] Prevent brute force clip enumeration
  - [ ] Prevent moment spam triggering

- [x] HTTP headers for security
  - [x] X-Content-Type-Options: nosniff
  - [x] X-Frame-Options: DENY
  - [x] Referrer-Policy: strict-origin-when-cross-origin
  - [ ] TODO: Add Strict-Transport-Security: max-age=31536000
  - [ ] TODO: Add Content-Security-Policy

- [ ] **TODO: Input validation**
  - [ ] Validate clip IDs are numeric
  - [ ] Validate sensitivity is 0.0-1.0
  - [ ] Validate platform names from whitelist
  - [ ] Prevent SQL injection (use parameterized queries)

## Moment Detection Security

- [ ] **Prevent moment detection abuse**
  - [ ] Limit chat events per second
  - [ ] Limit audio peaks per second
  - [ ] Validate event source is legitimate

- [ ] **Prevent clip generation spam**
  - [ ] Rate limit clip generation to 1 per 30 seconds
  - [ ] Validate moment data before processing
  - [ ] Implement circuit breaker for pipeline failures

## File Upload/Download Security

- [ ] **Prevent path traversal attacks**
  - [ ] Validate file paths don't contain ".."
  - [ ] Validate file extensions (mp4 only)
  - [ ] Validate file size limits

- [ ] **Prevent unauthorized file access**
  - [ ] Verify user owns clip before serving file
  - [ ] Implement download logging
  - [ ] Implement download rate limiting

## External Service Security

- [ ] **Groq API**
  - [ ] API key never logged
  - [ ] API key not sent to client
  - [ ] Request/response validation

- [ ] **Twitch/YouTube APIs**
  - [ ] OAuth tokens stored securely
  - [ ] Tokens refreshed when expired
  - [ ] Proper scope validation
  - [ ] Chat events validated before processing

## Infrastructure Security

- [ ] **HTTPS/TLS**
  - [ ] All API endpoints use HTTPS
  - [ ] HTTPS certificate from trusted CA
  - [ ] Certificate auto-renewal configured
  - [ ] TLS 1.2+ only

- [ ] **Logging & Monitoring**
  - [ ] Failed auth attempts logged
  - [ ] Suspicious activity alerts
  - [ ] API error rates monitored
  - [ ] Database error rates monitored
  - [ ] **NO sensitive data in logs**

- [ ] **Secrets Management**
  - [ ] All secrets in environment variables only
  - [ ] No secrets in code or git
  - [ ] Secrets rotated regularly
  - [ ] Different secrets per environment

## Deployment Security

- [ ] **Database**
  - [ ] Unique database per deployment
  - [ ] Database backups encrypted
  - [ ] Database backups tested
  - [ ] SQL injection prevention verified

- [ ] **Environment Separation**
  - [ ] Development ≠ Production secrets
  - [ ] Staging uses staging credentials
  - [ ] Production uses production credentials
  - [ ] No production data on dev servers

- [ ] **Access Control**
  - [ ] SSH keys for server access only
  - [ ] Firewall restricts port access
  - [ ] Database only accessible from app server
  - [ ] OBS only accessible from app server

## Testing

- [ ] **Security testing completed**
  - [ ] Cross-streamer access test (should fail)
  - [ ] Unauthorized clip deletion test (should fail)
  - [ ] SQL injection test (should fail)
  - [ ] CORS origin validation test

- [ ] **End-to-end test with real stream**
  - [ ] Create clips from real moments
  - [ ] Verify clips are properly stored
  - [ ] Test all CRUD operations
  - [ ] Test export functionality
  - [ ] Verify no data leakage

## Incident Response

- [ ] **Incident response plan documented**
- [ ] **Backup restore procedure tested**
- [ ] **Security contact information established**
- [ ] **User notification procedure established**

## Before Launch

- [ ] **Code review completed**
- [ ] **Security audit completed**
- [ ] **Penetration testing completed** (if budget allows)
- [ ] **Legal review completed** (privacy policy, TOS, DMCA)
- [ ] **User testing completed**
- [ ] **Monitoring & alerting configured**
- [ ] **Support plan documented**
- [ ] **Escalation procedures documented**

## Post-Launch Monitoring

- [ ] **Daily security logs reviewed**
- [ ] **Failed authentication patterns monitored**
- [ ] **Database access patterns monitored**
- [ ] **File access patterns monitored**
- [ ] **API error rates monitored**
- [ ] **Performance metrics monitored**

## Critical Security Requirements Status

| Requirement | Status | Notes |
|---|---|---|
| Auth on all endpoints | ✅ DONE | All clip endpoints secured |
| Streamer data isolation | ✅ DONE | Clips filtered by streamer_id |
| Settings per-streamer | ✅ DONE | Settings stored in DB |
| CORS validation | ✅ DONE | Properly configured |
| File access control | 🔄 IN PROGRESS | Need to restrict file serving |
| External API security | 🔄 IN PROGRESS | Need encryption at rest |
| Rate limiting | 🔄 IN PROGRESS | Basic auth limiting only |
| HTTPS enforcement | ⏳ TODO | Deploy with HTTPS |
| Secrets management | ⏳ TODO | Use env vars only |
| Monitoring & logging | ⏳ TODO | Setup alerts |

## Next Priority Actions

1. **Immediate (before any streamer testing)**
   - [ ] Encrypt sensitive fields in database
   - [ ] Implement file access control
   - [ ] Add rate limiting to all endpoints

2. **Before public launch**
   - [ ] Setup HTTPS/TLS
   - [ ] Implement secrets rotation
   - [ ] Setup monitoring & alerting

3. **Post-launch**
   - [ ] Security audit by external firm
   - [ ] Penetration testing
   - [ ] SOC 2 compliance if needed

---

## Questions for Streamer Before Launch

When launching with a streamer, get written consent on:

1. "Do you understand Kazumee accesses your OBS?"
2. "Do you understand Kazumee can create clips automatically?"
3. "Do you authorize Kazumee to analyze your chat?"
4. "Do you authorize Kazumee to store clips on our servers?"
5. "Do you understand these clips can be exported to social platforms?"

Store this consent in the database for legal protection.
