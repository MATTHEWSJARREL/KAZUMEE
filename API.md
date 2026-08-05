# Clip Generation Pipeline API Documentation

## Overview

Production-ready REST API for clip generation, moment detection, and management with streamer-scoped access control and comprehensive monitoring.

- **Base URL**: `http://localhost:8000` (local) or `https://your-railway-domain.com` (production)
- **Authentication**: Bearer token via `Authorization: Bearer {token}` header
- **Response Format**: JSON
- **Error Handling**: Structured error objects with HTTP status codes

---

## Authentication

### Login

Create a session token for subsequent API requests.

```http
POST /auth/login
Content-Type: application/json

{
  "username": "streamer_username",
  "password": "password123"
}
```

**Response (200 OK)**:
```json
{
  "token": "eyJhbGc...",
  "expires_in": 86400,
  "user_id": 1
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid username/password
- `400 Bad Request`: Missing required fields

**Token Details**:
- Format: Opaque session token (24-hour validity)
- Storage: Stored securely in database with PBKDF2 hashing
- Usage: Pass as `Authorization: Bearer {token}` in all subsequent requests

### Token Verification

All requests require valid authentication token. Expired tokens return `401 Unauthorized`.

**Example Request**:
```bash
curl -H "Authorization: Bearer {token}" \
  https://api.example.com/api/clips/pending
```

---

## Clip Management APIs

### List Pending Clips

Retrieve all pending clips for the authenticated streamer.

```http
GET /api/clips/pending
Authorization: Bearer {token}
```

**Response (200 OK)**:
```json
{
  "clips": [
    {
      "id": 1,
      "title": "Epic Moment",
      "description": "Amazing gameplay highlight",
      "status": "pending",
      "created_at": "2026-08-05T12:30:00Z",
      "tags": ["gameplay", "highlight"],
      "duration_seconds": 45
    }
  ]
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid/expired token
- `403 Forbidden`: Viewer accounts cannot access

---

### Check Generated Clips

Check which clips have been extracted and are ready for review.

```http
GET /api/clips/check-generated
Authorization: Bearer {token}
```

**Response (200 OK)**:
```json
{
  "generated": [
    {
      "id": 2,
      "title": "Clutch Play",
      "status": "pending",
      "file_path": "/storage/extracted/clip_2.mp4",
      "file_size_mb": 145.2
    }
  ],
  "total_generated": 5
}
```

---

### Review Clip (Approve/Reject)

Approve or reject a pending clip for export.

```http
POST /api/clips/review
Authorization: Bearer {token}
Content-Type: application/json

{
  "clip_id": 1,
  "action": "approve",
  "notes": "Great highlight!"
}
```

**Parameters**:
- `clip_id` (int, required): Clip identifier
- `action` (string, required): Either `"approve"` or `"reject"`
- `notes` (string, optional): Reviewer notes (max 500 chars)

**Response (200 OK)**:
```json
{
  "clip_id": 1,
  "status": "approved",
  "updated_at": "2026-08-05T12:45:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid action (must be "approve" or "reject")
- `404 Not Found`: Clip does not exist or belongs to different streamer
- `409 Conflict`: Clip already reviewed

---

### Get Clip Details

Retrieve full details for a specific clip.

```http
GET /api/clips/{clip_id}
Authorization: Bearer {token}
```

**Response (200 OK)**:
```json
{
  "id": 1,
  "title": "Epic Moment",
  "description": "Amazing gameplay highlight",
  "status": "approved",
  "tags": ["gameplay", "highlight"],
  "duration_seconds": 45,
  "video_url": "/storage/clips/clip_1.mp4",
  "thumbnail_url": "/storage/thumbnails/clip_1.jpg",
  "created_at": "2026-08-05T12:30:00Z",
  "streamer_id": 1
}
```

---

### Update Clip Metadata

Update title, description, or tags for a clip.

```http
PUT /api/clips/{clip_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Updated Title",
  "description": "Updated description",
  "tags": ["gameplay", "clutch", "competitive"]
}
```

**Parameters**:
- `title` (string, optional): Max 255 characters
- `description` (string, optional): Max 2000 characters
- `tags` (array, optional): Max 10 tags, each max 50 characters

**Response (200 OK)**:
```json
{
  "id": 1,
  "title": "Updated Title",
  "description": "Updated description",
  "tags": ["gameplay", "clutch", "competitive"],
  "updated_at": "2026-08-05T13:00:00Z"
}
```

---

### Delete Clip

Permanently delete a clip.

```http
DELETE /api/clips/{clip_id}
Authorization: Bearer {token}
```

**Response (204 No Content)**: Empty response body

**Error Responses**:
- `404 Not Found`: Clip does not exist or belongs to different streamer
- `403 Forbidden`: Cannot delete exported clips (must reject first)

---

### List Recent Clips

Retrieve recently created clips with optional filtering.

```http
GET /api/clips/recent?limit=20&status=approved
Authorization: Bearer {token}
```

**Query Parameters**:
- `limit` (int, optional): Max results (default: 20, max: 100)
- `status` (string, optional): Filter by status ("pending", "approved", "rejected", "exported")
- `offset` (int, optional): Pagination offset (default: 0)

**Response (200 OK)**:
```json
{
  "clips": [...],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

---

### Export Clip

Export approved clip to external platform (TikTok, YouTube, etc.).

```http
POST /api/clips/{clip_id}/export
Authorization: Bearer {token}
Content-Type: application/json

{
  "platform": "tiktok",
  "preset": "tiktok"
}
```

**Parameters**:
- `platform` (string, required): Target platform ("tiktok", "youtube", "instagram", "twitch")
- `preset` (string, required): Export preset ("tiktok", "shorts", "reels", "youtube", "instagram")

**Response (200 OK)**:
```json
{
  "clip_id": 1,
  "platform": "tiktok",
  "status": "exporting",
  "export_url": "https://tiktok.com/@streamer/video/123456789",
  "exported_at": "2026-08-05T13:15:00Z"
}
```

---

## Moment Detection APIs

### Detect Moment

Send chat/activity data to detect potential clip moments.

```http
POST /moments/detect
Authorization: Bearer {token}
Content-Type: application/json

{
  "stream_id": "stream_123",
  "timestamp": 1722873000,
  "chat_events": 250,
  "emote_rate": 0.65,
  "caps_ratio": 0.45
}
```

**Parameters**:
- `stream_id` (string, required): Unique stream identifier
- `timestamp` (int, required): Unix timestamp
- `chat_events` (int, required): Number of chat messages in window
- `emote_rate` (float, required): Emote frequency (0.0-1.0)
- `caps_ratio` (float, required): All-caps message ratio (0.0-1.0)

**Response (200 OK)**:
```json
{
  "moment_id": "moment_123_abc",
  "is_moment": true,
  "score": 8.5,
  "confidence": 0.92,
  "threshold": 7.0
}
```

**Response (201 Created)** - Clip auto-created:
```json
{
  "moment_id": "moment_123_def",
  "is_moment": true,
  "clip_id": 15,
  "clip_title": "Auto-detected Moment",
  "score": 9.2,
  "confidence": 0.97
}
```

**Error Responses**:
- `400 Bad Request`: Missing required fields or invalid values
- `422 Unprocessable Entity`: Invalid data types (e.g., emote_rate > 1.0)

---

## Storage APIs

### Get Storage Statistics

Retrieve storage usage and file statistics.

```http
GET /api/clips/storage/stats
Authorization: Bearer {token}
```

**Response (200 OK)**:
```json
{
  "total_files": 42,
  "total_size_mb": 5240.5,
  "directories": {
    "extracted": {
      "count": 15,
      "size_mb": 2100.3
    },
    "approved": {
      "count": 20,
      "size_mb": 2800.2
    },
    "exported": {
      "count": 7,
      "size_mb": 340.0
    }
  },
  "cleanup_candidates_mb": 125.5
}
```

---

### Download Clip

Download a clip file via HTTP Range requests (for resumable downloads).

```http
GET /api/clips/{clip_id}/download
Authorization: Bearer {token}
Range: bytes=0-1023
```

**Response (206 Partial Content)**:
```http
HTTP/1.1 206 Partial Content
Content-Type: video/mp4
Content-Range: bytes 0-1023/5240320
Content-Length: 1024

[binary video data]
```

**Full File Response (200 OK)**:
```http
HTTP/1.1 200 OK
Content-Type: video/mp4
Content-Length: 5240320
Content-Disposition: attachment; filename="clip_1.mp4"

[binary video data]
```

**Error Responses**:
- `404 Not Found`: Clip file not found
- `416 Range Not Satisfiable`: Invalid byte range

---

## Monitoring & Logging APIs

### Health Check

System health and readiness status.

```http
GET /api/monitoring/health
Authorization: Bearer {token}
```

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "timestamp": "2026-08-05T14:00:00Z",
  "database": "connected",
  "storage": "available"
}
```

---

### Get Monitoring Statistics

Comprehensive pipeline metrics and performance data.

```http
GET /api/monitoring/stats
Authorization: Bearer {token}
```

**Response (200 OK)**:
```json
{
  "clip_pipeline": {
    "total_clips": 125,
    "pending": 8,
    "approved": 92,
    "rejected": 15,
    "exported": 10
  },
  "moments": {
    "detected_24h": 156,
    "auto_created_24h": 12
  },
  "performance": {
    "avg_extraction_time_seconds": 34.2,
    "avg_api_response_time_ms": 145
  },
  "storage": {
    "total_used_mb": 5240.5,
    "largest_file_mb": 250.3
  }
}
```

---

### Get Recent Events

Stream of system events for debugging and monitoring.

```http
GET /api/monitoring/events?limit=50&type=CLIP_APPROVED
Authorization: Bearer {token}
```

**Query Parameters**:
- `limit` (int, optional): Max events (default: 50, max: 200)
- `type` (string, optional): Filter by event type (see Event Types below)

**Response (200 OK)**:
```json
{
  "events": [
    {
      "event_type": "CLIP_APPROVED",
      "streamer_id": 1,
      "clip_id": 5,
      "timestamp": "2026-08-05T13:50:00Z",
      "duration_ms": 234
    },
    {
      "event_type": "EXTRACTION_SUCCEEDED",
      "clip_id": 5,
      "timestamp": "2026-08-05T13:45:00Z",
      "duration_ms": 2500
    }
  ]
}
```

**Event Types**:
- `CLIP_DETECTED` - Moment detected by algorithm
- `EXTRACTION_STARTED` - Video extraction beginning
- `EXTRACTION_SUCCEEDED` - Video successfully extracted
- `EXTRACTION_FAILED` - Video extraction error
- `CLIP_APPROVED` - Streamer approved clip
- `CLIP_REJECTED` - Streamer rejected clip
- `CLIP_EXPORTED` - Clip exported to platform
- `CLIP_DELETED` - Clip permanently deleted
- `API_REQUEST` - API endpoint called
- `API_ERROR` - API error occurred
- `AUTH_FAILURE` - Authentication failed
- `STORAGE_ERROR` - File system error

---

### Get Error Logs

Retrieve recent errors and failures.

```http
GET /api/monitoring/errors?limit=20
Authorization: Bearer {token}
```

**Response (200 OK)**:
```json
{
  "errors": [
    {
      "error_type": "EXTRACTION_FAILED",
      "clip_id": 3,
      "message": "Video codec not supported",
      "timestamp": "2026-08-05T12:15:00Z",
      "retry_count": 2,
      "status": "failed"
    },
    {
      "error_type": "STORAGE_ERROR",
      "message": "Disk space low (< 100MB)",
      "timestamp": "2026-08-05T11:30:00Z",
      "severity": "warning"
    }
  ]
}
```

---

### Get Clip Success Rate

Success rate of clip creation and export.

```http
GET /api/monitoring/clip-success-rate?period=24h
Authorization: Bearer {token}
```

**Query Parameters**:
- `period` (string, optional): Time period ("1h", "24h", "7d", "30d", default: "24h")

**Response (200 OK)**:
```json
{
  "period": "24h",
  "total_clips_created": 125,
  "successful": 120,
  "failed": 5,
  "success_rate_percent": 96.0,
  "trend": "up"
}
```

---

### Get Extraction Failures

Detailed report of extraction failures.

```http
GET /api/monitoring/extraction-failures?limit=20
Authorization: Bearer {token}
```

**Response (200 OK)**:
```json
{
  "failures": [
    {
      "clip_id": 3,
      "title": "Failed Clip",
      "error": "Video codec not supported",
      "timestamp": "2026-08-05T12:15:00Z",
      "retry_count": 2,
      "next_retry": "2026-08-05T13:15:00Z"
    }
  ],
  "total_failures": 5
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable error description",
  "status": 400,
  "timestamp": "2026-08-05T14:00:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful clip retrieval |
| 201 | Created | Auto-detected clip created |
| 204 | No Content | Successful deletion |
| 400 | Bad Request | Missing required field |
| 401 | Unauthorized | Invalid/expired token |
| 403 | Forbidden | Clip belongs to different streamer |
| 404 | Not Found | Clip does not exist |
| 409 | Conflict | Clip already approved/rejected |
| 422 | Unprocessable Entity | Invalid field values |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected error |
| 503 | Service Unavailable | Database unreachable |

---

## Error Codes

### Authentication Errors

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_CREDENTIALS` | 401 | Username/password incorrect |
| `TOKEN_EXPIRED` | 401 | Session token expired (24-hour limit) |
| `TOKEN_INVALID` | 401 | Token malformed or tampered |
| `MISSING_AUTH` | 401 | No Authorization header provided |

### Validation Errors

| Code | Status | Description |
|------|--------|-------------|
| `VALIDATION_FAILED` | 400 | Required field missing or invalid |
| `INVALID_ACTION` | 400 | Action must be "approve" or "reject" |
| `INVALID_PLATFORM` | 400 | Unknown export platform |
| `TITLE_TOO_LONG` | 400 | Title exceeds 255 characters |
| `DESCRIPTION_TOO_LONG` | 400 | Description exceeds 2000 characters |
| `INVALID_TAGS` | 400 | Tag validation failed |

### Access Control Errors

| Code | Status | Description |
|------|--------|-------------|
| `FORBIDDEN` | 403 | Clip belongs to different streamer (OWASP #1 protection) |
| `VIEWER_ACCESS_DENIED` | 403 | Viewer accounts cannot perform this action |
| `PERMISSION_DENIED` | 403 | User lacks required permission |

### Resource Errors

| Code | Status | Description |
|------|--------|-------------|
| `NOT_FOUND` | 404 | Clip, file, or resource does not exist |
| `DUPLICATE` | 409 | Clip already exists in requested state |
| `CONFLICT` | 409 | Cannot perform action (e.g., delete exported clip) |

### System Errors

| Code | Status | Description |
|------|--------|-------------|
| `DATABASE_ERROR` | 500 | Database connection or query failed |
| `STORAGE_ERROR` | 500 | File system operation failed |
| `EXTRACTION_FAILED` | 500 | Video extraction/encoding error |
| `EXPORT_FAILED` | 500 | Export to platform failed |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/auth/login` | 5 requests | 5 minutes |
| `/moments/detect` | 1000 requests | 1 minute |
| `/api/clips/*` | 200 requests | 1 minute |
| `/api/monitoring/*` | 100 requests | 1 minute |

**Rate Limit Headers**:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 998
X-RateLimit-Reset: 1722873060
```

When limit exceeded:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

---

## Security Headers

All responses include security headers:

```http
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

---

## CORS

CORS is enabled for configured origins (see deployment guide).

```http
Access-Control-Allow-Origin: https://yourdomain.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 3600
```

---

## Examples

### Complete Workflow

1. **Login**:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"streamer","password":"pass123"}'
# Returns token: "abc123xyz..."
```

2. **Check generated clips**:
```bash
curl http://localhost:8000/api/clips/check-generated \
  -H "Authorization: Bearer abc123xyz..."
```

3. **Approve a clip**:
```bash
curl -X POST http://localhost:8000/api/clips/review \
  -H "Authorization: Bearer abc123xyz..." \
  -H "Content-Type: application/json" \
  -d '{"clip_id":1,"action":"approve"}'
```

4. **Export to TikTok**:
```bash
curl -X POST http://localhost:8000/api/clips/1/export \
  -H "Authorization: Bearer abc123xyz..." \
  -H "Content-Type: application/json" \
  -d '{"platform":"tiktok","preset":"tiktok"}'
```

5. **Monitor system health**:
```bash
curl http://localhost:8000/api/monitoring/stats \
  -H "Authorization: Bearer abc123xyz..."
```

---

## Changelog

### v1.0.0 (Initial Release)
- ✅ Authentication with session tokens
- ✅ Clip CRUD operations
- ✅ Moment detection endpoints
- ✅ Clip review (approve/reject)
- ✅ Export to platforms
- ✅ Storage management
- ✅ Monitoring & logging
- ✅ Rate limiting
- ✅ OWASP #1 access control

---

## Support

For API issues or questions:
1. Check error response for specific error code
2. Review monitoring/error logs: `GET /api/monitoring/errors`
3. Consult this documentation for endpoint details
4. Enable detailed logging in deployment configuration

---

**Last Updated**: 2026-08-05
**Version**: 1.0.0
