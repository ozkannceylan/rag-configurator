# TechCorp Technical Troubleshooting Guide

## Overview

This guide provides solutions to common technical issues encountered when using TechCorp's platform. It's organized by service area and symptom, with step-by-step resolution procedures.

**Last Updated**: January 2025  
**Support Team**: support@techcorp.com  
**Emergency Line**: 1-800-TECH-911 (24/7 for Enterprise)

---

## Quick Reference

### Common Error Codes

| Error Code | Meaning | Section |
|------------|---------|---------|
| `AUTH_001` | Invalid credentials | [Authentication](#authentication-issues) |
| `AUTH_002` | Token expired | [Authentication](#authentication-issues) |
| `AUTH_003` | Insufficient permissions | [Authorization](#authorization-issues) |
| `UPLOAD_001` | File too large | [File Upload](#file-upload-issues) |
| `UPLOAD_002` | Invalid file type | [File Upload](#file-upload-issues) |
| `UPLOAD_003` | Virus detected | [File Upload](#file-upload-issues) |
| `SEARCH_001` | Index not found | [Search](#search-issues) |
| `CONN_001` | Connection timeout | [Connectivity](#connectivity-issues) |
| `CONN_002` | Rate limit exceeded | [Connectivity](#connectivity-issues) |
| `DB_001` | Database error | [API Errors](#api-errors) |

### Emergency Contacts

- **Severity 1** (Production down): Call +1-800-XXX-XXXX
- **Severity 2** (Major feature broken): Slack #incidents
- **Severity 3** (Minor issue): Email support@techcorp.com
- **General Questions**: Slack #tech-support

---

## Authentication Issues

### "Invalid Credentials" Error

**Symptoms**:
- Login fails with "Invalid email or password"
- API returns 401 Unauthorized
- Error code: `AUTH_001`

**Common Causes & Solutions**:

**1. Wrong Email Address**:
```
✓ Check for typos in email
✓ Verify you're using the correct domain (@techcorp.com vs personal email)
✓ Try the "Forgot Password" link to confirm email exists
```

**2. Caps Lock or Keyboard Layout**:
```
✓ Check Caps Lock is off
✓ Verify keyboard layout (e.g., QWERTY vs AZERTY)
✓ Type password in a text editor first to verify characters
```

**3. Account Locked**:
```
✓ After 5 failed attempts, account locks for 15 minutes
✓ Wait 15 minutes and try again
✓ Or contact admin to unlock immediately
```

**4. Password Expired**:
```
✓ Corporate passwords expire every 90 days
✓ Check for password reset email
✓ Use "Forgot Password" to set new password
```

**Debug Script**:
```bash
# Test authentication with curl
curl -X POST https://api.techcorp.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"your_password"}' \
  -v

# Check response headers for clues
# Look for: X-Request-ID, X-Error-Code
```

### "Token Expired" Error

**Symptoms**:
- API calls return 401 with "Token has expired"
- Automatic logout from web app
- Error code: `AUTH_002`

**Solutions**:

**Web Application**:
```
1. Refresh the page - token auto-refreshes
2. If still failing, clear browser cookies:
   - Chrome: DevTools → Application → Cookies → Clear
   - Or use incognito mode
3. Log out and log back in
```

**API Integration**:
```python
# Implement token refresh in your code
import requests
from datetime import datetime, timedelta

class TechCorpClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expires = None
    
    def get_token(self):
        if self.token and datetime.now() < self.token_expires:
            return self.token
        
        # Refresh token
        response = requests.post(
            'https://api.techcorp.com/v1/oauth/token',
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
        )
        
        data = response.json()
        self.token = data['access_token']
        self.token_expires = datetime.now() + timedelta(seconds=data['expires_in'] - 60)
        return self.token
```

**Manual Token Refresh**:
```bash
# Get new access token
curl -X POST https://api.techcorp.com/v1/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=YOUR_REFRESH_TOKEN" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

### MFA/2FA Issues

**Symptoms**:
- Can't log in with authenticator app
- "Invalid MFA code" error
- Lost access to MFA device

**Solutions**:

**1. Time Sync Issues**:
```
TOTP codes are time-based. If your device clock is off:
✓ Android: Settings → System → Date & Time → Enable automatic
✓ iOS: Settings → General → Date & Time → Set Automatically
✓ Wait 1 minute for clock to sync, try again
```

**2. Wrong Authenticator App**:
```
✓ Must use the app you originally set up with
✓ Common apps: Google Authenticator, Authy, Microsoft Authenticator
✓ If unsure which app, check your phone for "TechCorp" entry
```

**3. Lost MFA Device**:
```
Recovery Options:
✓ Use backup codes (provided when MFA was set up)
✓ Contact admin with photo ID for manual reset
✓ Security team can disable MFA after verification (24-48 hours)
```

**Reset MFA**:
```
1. Log in with backup code
2. Go to Account Settings → Security
3. Click "Disable 2FA"
4. Re-enable with new device
```

---

## File Upload Issues

### "File Too Large" Error

**Symptoms**:
- Upload fails with "File exceeds maximum size"
- Error code: `UPLOAD_001`
- Upload progress stops midway

**Solutions**:

**Size Limits by Plan**:
```
Free: 10 MB per file
Basic: 50 MB per file
Pro: 100 MB per file
Enterprise: 500 MB per file
```

**1. Compress the File**:
```bash
# Images: Reduce dimensions or quality
# Use tools like ImageOptim, TinyPNG

# Documents: Remove unnecessary content
# Compress PDFs: https://smallpdf.com/compress-pdf

# Videos: Compress or upload to external storage
ffmpeg -i input.mp4 -vcodec h264 -acodec mp2 output.mp4
```

**2. Split Large Files**:
```bash
# Split PDF into smaller chunks
# Use: https://www.ilovepdf.com/split_pdf

# Split ZIP or archive
zip -s 50m large_file.zip --out split_file.zip
```

**3. Use Chunked Upload (API)**:
```python
import requests
import os

# For files > 100MB, use chunked upload
# This is more reliable and resumable

def upload_large_file(file_path, token):
    chunk_size = 5 * 1024 * 1024  # 5MB chunks
    file_size = os.path.getsize(file_path)
    
    # Initiate upload
    response = requests.post(
        'https://api.techcorp.com/v1/uploads/initiate',
        headers={'Authorization': f'Bearer {token}'},
        json={'filename': os.path.basename(file_path), 'size': file_size}
    )
    upload_id = response.json()['upload_id']
    
    # Upload chunks
    with open(file_path, 'rb') as f:
        chunk_num = 0
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            
            requests.put(
                f'https://api.techcorp.com/v1/uploads/{upload_id}/chunks/{chunk_num}',
                headers={'Authorization': f'Bearer {token}'},
                data=chunk
            )
            chunk_num += 1
    
    # Complete upload
    response = requests.post(
        f'https://api.techcorp.com/v1/uploads/{upload_id}/complete',
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()
```

### "Invalid File Type" Error

**Symptoms**:
- Upload rejected with "Unsupported file format"
- Error code: `UPLOAD_002`
- File appears valid but rejected

**Supported Formats**:
```
Documents: PDF, DOCX, TXT, MD, RTF
Images: JPG, JPEG, PNG, GIF, WebP, SVG
Spreadsheets: XLSX, CSV, TSV
Presentations: PPTX
Archives: ZIP (for batch uploads)
```

**Solutions**:

**1. Check File Extension**:
```bash
# Verify actual file type (not just extension)
file document.pdf
# Output: document.pdf: PDF document, version 1.4
```

**2. Convert to Supported Format**:
```bash
# DOC to DOCX
libreoffice --headless --convert-to docx document.doc

# HEIC to JPG (iPhone photos)
# Use Photos app export or online converter

# Convert any format
# https://cloudconvert.com/
```

**3. Remove Password Protection**:
```
✓ Encrypted PDFs cannot be processed
✓ Remove password in Adobe Acrobat or Preview
✓ Save as new unencrypted file
```

### "Virus Detected" Error

**Symptoms**:
- Upload blocked with security warning
- Error code: `UPLOAD_003`
- File quarantined

**False Positive Resolution**:
```
If you believe this is a false positive:

1. Scan with alternative tools:
   - VirusTotal: https://www.virustotal.com
   - Your local antivirus

2. If clean on other scanners:
   - Email security@techcorp.com with file attached
   - Include business justification
   - Request whitelist review

3. Workaround:
   - Upload to external secure storage
   - Share link instead of direct upload
```

### Upload Stuck or Failing

**Symptoms**:
- Progress bar freezes
- "Network Error" messages
- Upload repeatedly fails

**Troubleshooting Steps**:

**1. Check Your Connection**:
```bash
# Test upload speed
# https://www.speedtest.net/

# Minimum required:
# - Download: 5 Mbps
# - Upload: 2 Mbps

# Test API connectivity
curl -I https://api.techcorp.com/v1/health
```

**2. Disable Interfering Software**:
```
Temporarily disable:
✓ VPN (may throttle uploads)
✓ Corporate proxy/firewall
✓ Browser extensions (ad blockers)
✓ Antivirus real-time scanning

Test upload again
```

**3. Try Different Methods**:
```
Method 1: Web Interface (Chrome)
Method 2: Web Interface (Firefox)
Method 3: API with curl
Method 4: Desktop Application
Method 5: Mobile App
```

**4. Check File Integrity**:
```bash
# Verify file isn't corrupted
md5sum myfile.pdf
# Compare with source checksum

# Repair PDF
gs -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -sOutputFile=fixed.pdf corrupted.pdf
```

---

## Search Issues

### "No Results Found" When Results Expected

**Symptoms**:
- Search returns empty results
- Documents exist but not found
- Error code: `SEARCH_001`

**Common Causes**:

**1. Indexing Delay**:
```
New documents take 1-5 minutes to appear in search
✓ Wait a few minutes and retry
✓ Check document status shows "processed"
```

**2. Permission Issues**:
```
✓ You can only search documents you have access to
✓ Check you're in the right project/workspace
✓ Verify document sharing settings
✓ Ask document owner to share with you
```

**3. Search Query Too Specific**:
```
Try broader terms:
✓ Use fewer keywords
✓ Try synonyms
✓ Remove filters temporarily
✓ Use partial word matching (e.g., "docu" for "document")
```

**4. Document Not OCR'd**:
```
Scanned PDFs need OCR to be searchable:
✓ Check if document shows "Text extracted: Yes"
✓ If "No", re-upload with OCR enabled
✓ Or use "Enhance" button on document
```

### Search Results Irrelevant

**Symptoms**:
- Top results don't match query
- Too many unrelated documents
- Poor result ranking

**Improvement Tips**:

**1. Use Advanced Search Operators**:
```
Exact phrase: "quarterly report"
AND operator: quarterly AND report
OR operator: quarterly OR annual
NOT operator: report NOT draft
Wildcard: report* (matches reports, reporting)
Field search: title:quarterly
```

**2. Apply Filters**:
```
✓ Date range: Last 30 days, This year
✓ File type: PDF only, Images only
✓ Project: Select specific project
✓ Author: Documents by specific person
✓ Tags: Filter by assigned tags
```

**3. Use Semantic Search**:
```
Instead of keyword search, try:
"documents about revenue growth in Q3"
"discussions about API rate limiting"
```

**4. Relevance Feedback**:
```
✓ Click thumbs up/down on results
✓ This trains the system for better results
✓ Feedback is anonymous and immediate
```

### Search Performance Slow

**Symptoms**:
- Search takes > 5 seconds
- Timeout errors
- Loading spinner persists

**Solutions**:

**1. Check Your Connection**:
```bash
# Test latency to search endpoint
ping api.techcorp.com

# Acceptable: < 100ms
# Problematic: > 300ms
```

**2. Reduce Query Complexity**:
```
Avoid:
✓ Extremely long queries (> 100 words)
✓ Too many filters (5+)
✓ Complex boolean logic
✓ Special characters that need escaping
```

**3. Clear Browser Cache**:
```
Chrome:
1. DevTools (F12) → Network tab
2. Check "Disable cache"
3. Refresh and retry search

Or clear site data:
Settings → Privacy → Clear browsing data → Cookies and cache
```

---

## Connectivity Issues

### "Connection Timeout" Error

**Symptoms**:
- "Request timed out" messages
- Pages load partially then hang
- Error code: `CONN_001`

**Diagnosis Steps**:

**1. Check Service Status**:
```
Visit: https://status.techcorp.com

Check for:
✓ Ongoing incidents
✓ Maintenance windows
✓ Degraded performance alerts
```

**2. Test Basic Connectivity**:
```bash
# Test if API is reachable
curl -I https://api.techcorp.com/v1/health

# Expected: HTTP/2 200
# If fails, network issue between you and TechCorp

# Check DNS resolution
nslookup api.techcorp.com

# Test with different DNS
# Google: 8.8.8.8
# Cloudflare: 1.1.1.1
```

**3. Trace the Route**:
```bash
# See where connection fails
traceroute api.techcorp.com

# Or on Windows
tracert api.techcorp.com

# Look for:
# - Timeouts (*) indicate problem hops
# - High latency (> 200ms) on intermediate nodes
```

**4. Corporate Network Issues**:
```
Common corporate blocks:
✓ Firewall blocking port 443
✓ Proxy requiring authentication
✓ SSL inspection breaking certificates
✓ Geo-blocking if traveling abroad

Contact your IT department with:
- Destination: api.techcorp.com:443
- Purpose: Business API access
- Request: Whitelist / Open firewall
```

### "Rate Limit Exceeded" Error

**Symptoms**:
- Error code: `CONN_002` or 429
- "Too many requests" message
- Works again after waiting

**Understanding Limits**:
```
Free Tier: 60 requests/minute
Basic: 300 requests/minute
Pro: 1,000 requests/minute
Enterprise: Custom limits
```

**Solutions**:

**1. Implement Exponential Backoff**:
```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(429, 500, 502, 503, 504),
):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Usage
session = requests_retry_session()
response = session.get('https://api.techcorp.com/v1/projects')
```

**2. Batch Your Requests**:
```python
# Bad: Making individual calls
for project_id in project_ids:
    requests.get(f'/projects/{project_id}')  # 100 calls

# Good: Batch in single request
response = requests.post('/batch', json={
    'operations': [
        {'method': 'GET', 'path': f'/projects/{pid}'}
        for pid in project_ids
    ]
})  # 1 call
```

**3. Check Your Usage**:
```bash
# View current rate limit status
curl -H "Authorization: Bearer {token}" \
  https://api.techcorp.com/v1/rate-limit/status

# Response:
{
  "limit": 300,
  "remaining": 247,
  "reset_at": "2024-01-30T15:00:00Z",
  "window": "minute"
}
```

**4. Upgrade Your Plan**:
```
If consistently hitting limits:
✓ Review usage patterns in dashboard
✓ Consider upgrading to higher tier
✓ Contact sales for Enterprise custom limits
✓ Implement caching to reduce API calls
```

### SSL/Certificate Errors

**Symptoms**:
- "Your connection is not private"
- Certificate warnings
- "NET::ERR_CERT_AUTHORITY_INVALID"

**Solutions**:

**1. Check System Date/Time**:
```
✓ Wrong date causes cert validation failures
✓ Enable automatic time sync
✓ Retry after correction
```

**2. Update CA Certificates**:
```bash
# macOS
brew install ca-certificates

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ca-certificates

# Windows
Update Windows via Windows Update
```

**3. Corporate SSL Inspection**:
```
If on corporate network:
✓ Install corporate root certificate
✓ Contact IT for certificate file
✓ Add to system/browser trust store
```

---

## API Errors

### "Database Error" (500 Internal Server Error)

**Symptoms**:
- Error code: `DB_001`
- HTTP 500 response
- "Something went wrong" message

**Immediate Actions**:

**1. Check Status Page**:
```
https://status.techcorp.com

Look for:
✓ Database incidents
✓ High error rates
✓ Degraded performance
```

**2. Retry with Exponential Backoff**:
```python
import random
import time

def api_call_with_retry(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except DatabaseError:
            if attempt == max_retries - 1:
                raise
            
            # Exponential backoff with jitter
            sleep_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Retry {attempt + 1}/{max_retries} after {sleep_time:.1f}s...")
            time.sleep(sleep_time)
```

**3. Reduce Request Complexity**:
```
Try:
✓ Simpler query parameters
✓ Smaller page size (limit=10 instead of 100)
✓ Fewer filters
✓ Without sorting
```

**4. Report the Issue**:
```
Include in report:
✓ Exact timestamp with timezone
✓ Request ID (from response header X-Request-ID)
✓ Endpoint URL
✓ Request parameters (sanitized)
✓ User ID

Email: support@techcorp.com
```

### Validation Errors (422 Unprocessable Entity)

**Symptoms**:
- HTTP 422 response
- "Validation failed" message
- Specific field errors listed

**Common Validation Issues**:

**1. Required Fields Missing**:
```json
{
  "error": {
    "code": "validation_error",
    "message": "Validation failed",
    "details": [
      {
        "field": "name",
        "message": "Project name is required"
      }
    ]
  }
}

# Fix: Add the missing field
{
  "name": "My Project",
  "description": "..."
}
```

**2. Format Errors**:
```json
{
  "error": {
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}

# Fix: Use valid email format
"email": "user@example.com"
```

**3. String Length Violations**:
```
Name: Max 100 characters
Description: Max 5000 characters
Tags: Max 10 per document
```

**4. Enum Values**:
```json
{
  "error": {
    "details": [
      {
        "field": "status",
        "message": "Must be one of: active, archived, deleted"
      }
    ]
  }
}
```

**Debug Script**:
```python
import requests
import json

response = requests.post(
    'https://api.techcorp.com/v1/projects',
    headers={'Authorization': 'Bearer TOKEN'},
    json={'name': ''}  # Invalid: empty name
)

if response.status_code == 422:
    error_details = response.json()['error']['details']
    for error in error_details:
        print(f"Field '{error['field']}': {error['message']}")
```

---

## Performance Issues

### Slow Page Loading

**Symptoms**:
- Pages take > 5 seconds to load
- Assets loading slowly
- Intermittent slowness

**Troubleshooting**:

**1. Check Your Connection**:
```
Run speed test: https://www.speedtest.net/
Minimum for good experience:
- Download: 10 Mbps
- Upload: 5 Mbps
- Latency: < 100ms
```

**2. Disable Browser Extensions**:
```
Common culprits:
✓ Ad blockers (uBlock, AdBlock)
✓ Privacy extensions (Privacy Badger)
✓ Password managers (slow form fill)
✓ Developer tools (if left open)

Test in incognito/private mode
```

**3. Clear Browser Data**:
```
Chrome:
1. Settings → Privacy and security
2. Clear browsing data
3. Select: Cookies, Cached images and files
4. Time range: Last 24 hours
5. Clear data

Or use keyboard shortcut:
Ctrl+Shift+Delete (Windows)
Cmd+Shift+Delete (Mac)
```

**4. Check Browser Console**:
```
Press F12 → Console tab

Look for:
✓ Red error messages
✓ Slow loading warnings
✓ Failed network requests

Common issues:
- Mixed content warnings (http vs https)
- CORS errors
- JavaScript errors
```

### Application Freezing

**Symptoms**:
- UI becomes unresponsive
- "Page unresponsive" warnings
- High CPU/memory usage

**Solutions**:

**1. Close Other Tabs**:
```
✓ Each tab consumes memory
✓ Close unnecessary tabs
✓ Use tab suspenders (The Great Suspender)
```

**2. Restart Browser**:
```
✓ Clear accumulated memory leaks
✓ Close and reopen (not just refresh)
✓ Consider using browser's task manager:
   Chrome: Shift+Esc
```

**3. Update Browser**:
```
✓ Old browsers have performance issues
✓ Update to latest version
✓ Supported browsers:
   - Chrome 90+
   - Firefox 88+
   - Safari 14+
   - Edge 90+
```

**4. Disable Hardware Acceleration** (if issues persist):
```
Chrome:
Settings → Advanced → System
Turn off "Use hardware acceleration when available"
Restart browser
```

---

## Integration Issues

### Webhook Failures

**Symptoms**:
- Not receiving webhooks
- Webhook endpoints return errors
- Delayed webhook delivery

**Debugging**:

**1. Verify Webhook URL**:
```bash
# Test your endpoint is reachable
curl -X POST https://your-app.com/webhooks/techcorp \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Should return 200 OK
```

**2. Check Endpoint Requirements**:
```
✓ Must respond within 30 seconds
✓ Must return 2xx status code
✓ Must handle duplicate deliveries (idempotency)
✓ Must verify webhook signature
```

**3. Review Webhook Logs**:
```
In TechCorp Dashboard:
Settings → Webhooks → View Logs

Check:
✓ Delivery attempts
✓ Response codes
✓ Error messages
✓ Payload sizes
```

**4. Test with Webhook.site**:
```
1. Go to https://webhook.site
2. Copy the unique URL
3. Add as webhook in TechCorp
4. Trigger an event
5. See the request on webhook.site
```

### API Integration Errors

**Symptoms**:
- Integration not working
- Data not syncing
- Authentication failures

**SDK Troubleshooting**:

**Python SDK**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from techcorp import TechCorpClient

client = TechCorpClient(api_key='your_key', debug=True)
# Debug mode shows full request/response
```

**JavaScript SDK**:
```javascript
const client = new TechCorpClient({
  apiKey: 'your_key',
  debug: true, // Logs to console
});
```

**Common SDK Issues**:
```
✓ Outdated SDK version - update to latest
✓ Mismatched API version - check compatibility
✓ Timezone issues - use ISO 8601 timestamps
✓ Encoding issues - ensure UTF-8
```

---

## Mobile App Issues

### App Crashes

**Symptoms**:
- App closes unexpectedly
- Freeze on specific screens
- "App has stopped" errors

**Solutions**:

**1. Update the App**:
```
iOS: App Store → Updates
Android: Play Store → My apps → Update
```

**2. Clear App Data**:
```
iOS:
Settings → General → iPhone Storage → TechCorp → Offload App
Reinstall from App Store

Android:
Settings → Apps → TechCorp → Storage → Clear Cache
Settings → Apps → TechCorp → Storage → Clear Data
```

**3. Check Device Storage**:
```
Ensure at least 500MB free space
Low storage causes crashes
```

### Push Notifications Not Working

**Symptoms**:
- Not receiving notifications
- Delayed notifications
- Duplicate notifications

**Troubleshooting**:

**1. Check Notification Settings**:
```
App: Profile → Settings → Notifications
Device: Settings → Notifications → TechCorp
```

**2. Re-register Push Token**:
```
Logout and login again
This refreshes push token
```

**3. Check Do Not Disturb**:
```
iOS: Control Center → Focus → Off
Android: Settings → Sound → Do Not Disturb
```

---

## Getting Help

### Before Contacting Support

1. **Check status page**: status.techcorp.com
2. **Search documentation**: docs.techcorp.com
3. **Review this guide** thoroughly
4. **Try suggested solutions**
5. **Gather information** (see below)

### Information to Include

When reporting issues, provide:

**Required**:
```
✓ User ID or email
✓ Timestamp (with timezone)
✓ Exact error message
✓ Steps to reproduce
✓ Expected vs actual behavior
```

**Helpful**:
```
✓ Browser and version
✓ Operating system
✓ Screenshot or screen recording
✓ Network environment (home, office, VPN)
✓ Request ID from API response
✓ HAR file (browser network log)
```

**How to Get HAR File**:
```
Chrome:
1. F12 → Network tab
2. Reproduce the issue
3. Right-click in network log
4. Save all as HAR with content
```

### Support Channels

| Issue Type | Channel | Response Time |
|------------|---------|---------------|
| General Questions | Slack #help | 2-4 hours |
| Technical Issues | Email support@techcorp.com | 24 hours |
| Billing | billing@techcorp.com | 24 hours |
| Security | security@techcorp.com | 4 hours |
| Emergency (P1) | Hotline 1-800-XXX-XXXX | Immediate |

---

## Quick Fix Cheat Sheet

```
GENERAL:
❓ Try incognito/private mode
❓ Clear cache and cookies
❓ Restart browser
❓ Try different browser
❓ Check status.techcorp.com

AUTHENTICATION:
❓ Reset password
❓ Clear browser cookies
❓ Check Caps Lock
❓ Verify email address

UPLOADS:
❓ Check file size < 50MB
❓ Verify file extension
❓ Try different file format
❓ Check internet connection
❓ Disable VPN/proxy

SEARCH:
❓ Wait 5 minutes for indexing
❓ Check project permissions
❓ Try broader keywords
❓ Use advanced operators

API:
❓ Check rate limits
❓ Verify API key validity
❓ Review error response details
❓ Add exponential backoff
❓ Check request format

PERFORMANCE:
❓ Close other browser tabs
❓ Disable browser extensions
❓ Update browser
❓ Check internet speed
❓ Restart computer
```

---

*This guide is continuously updated. For the latest version, visit: https://docs.techcorp.com/troubleshooting*
