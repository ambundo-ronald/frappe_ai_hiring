# Security Best Practices for AI Hiring System

## Overview
This document outlines security best practices and configurations for the AI-Driven Hiring Automation System.

## Access Control

### Role-Based Permissions

The system implements three primary roles:

1. **HR Manager**
   - Full access to all AI DocTypes
   - Can create, read, update, delete all records
   - Can configure AI Settings
   - Can run security audits and cleanup tasks
   - Can reset rate limits

2. **HR User**
   - Read-only access to AI results
   - Can create Question Sets
   - Can view candidate profiles and shortlisting results
   - Cannot modify AI Settings
   - Cannot delete records

3. **Interviewer**
   - Read-only access to assigned candidates
   - Can update Interview Brief with feedback
   - Can view question sets and evaluation results
   - Cannot access AI Settings
   - Cannot view other candidates

### Permission Files
All DocTypes have permission files configured:
- `ai_candidate_profile_permissions.json`
- `ai_shortlisting_result_permissions.json`
- `ai_question_set_permissions.json`
- `ai_evaluation_result_permissions.json`
- `ai_interview_brief_permissions.json`
- `ai_settings_permissions.json`

## Data Protection

### PII Redaction (Already Implemented)
- Automatic redaction of personally identifiable information before AI processing
- Tokenization-based approach allows data restoration when needed
- Redacts: email addresses, phone numbers, addresses
- Configured via `enable_pii_redaction` in AI Settings

### API Key Security (Already Implemented)
- API keys stored encrypted in database
- Never logged in plaintext
- Access restricted to System Manager role
- Regular rotation recommended (every 90 days)

## Rate Limiting

### Configuration
Rate limits prevent abuse and control costs:

```python
# Per user, per operation type
- Hourly limit: 100 operations (configurable)
- Daily limit: 500 operations (configurable)
```

### Implementation
- Uses Redis cache for tracking
- Separate limits per operation type (parsing, shortlisting, etc.)
- Admin can reset limits if needed
- Exceeded limits logged for review

### Usage
```python
from frappe_ai_hiring.ai_hiring.utils.security import RateLimiter

# Check before operation
if not RateLimiter.check_rate_limit("resume_parsing"):
    frappe.throw("Rate limit exceeded. Please try again later.")

# Get current status
status = RateLimiter.get_rate_limit_status("resume_parsing")
```

## Audit Logging

### What is Logged
- All LLM API calls (operation type, model, timestamp, user)
- AI decisions (shortlisting, evaluation, brief generation)
- Errors and failures
- Configuration changes
- Rate limit violations

### Log Retention
- Default retention: 90 days for audit logs
- Configurable via cleanup tasks
- Automatic cleanup scheduled jobs recommended

### Accessing Logs
Audit logs stored in:
1. **Frappe Error Log** - Searchable via UI
2. **Application logs** - File system logs in `logs/ai_hiring.log`
3. **Custom reports** - Can create custom reports on log data

## Data Retention & Cleanup

### Retention Policies

1. **Audit Logs**
   - Default retention: 90 days
   - Cleanup via: `cleanup_old_data(audit_log_days=90)`

2. **Rejected Candidates**
   - Default retention: 180 days
   - Deletes associated AI documents after retention period
   - Job Applicant record retained (only AI data removed)

3. **Hired Candidates**
   - Retain indefinitely for reference
   - Can be anonymized on employee exit

### Running Cleanup

```python
# Via Python
from frappe_ai_hiring.ai_hiring.utils.security import DataRetentionPolicy

# Cleanup old audit logs
DataRetentionPolicy.cleanup_old_audit_logs(days=90)

# Cleanup rejected candidates
DataRetentionPolicy.cleanup_rejected_candidates(days=180)

# Anonymize specific candidate
DataRetentionPolicy.anonymize_candidate_data("JOB-APP-0001")
```

```javascript
// Via API (admin only)
frappe.call({
    method: 'frappe_ai_hiring.ai_hiring.utils.security.cleanup_old_data',
    args: {
        audit_log_days: 90,
        rejected_candidates_days: 180
    }
});
```

## Security Validation

### Running Security Audit

```python
# Via Python
from frappe_ai_hiring.ai_hiring.utils.security import SecurityValidator

# Full security audit
report = SecurityValidator.audit_security_configuration()

# Check specific components
ai_settings_valid = SecurityValidator.validate_ai_settings()
permissions_valid = SecurityValidator.validate_permissions()
```

```javascript
// Via API
frappe.call({
    method: 'frappe_ai_hiring.ai_hiring.utils.security.run_security_audit',
    callback: function(r) {
        console.log(r.message);
    }
});
```

### Validation Checks
- API key configured
- LLM provider set
- Model configuration
- PII redaction enabled (warning if disabled)
- Audit logging enabled (warning if disabled)
- Rate limits configured
- Timeout settings reasonable
- DocType permissions properly set

## Configuration Recommendations

### Production Settings

```python
# AI Settings Configuration
{
    "enable_ai_processing": 1,
    "enable_pii_redaction": 1,  # CRITICAL for production
    "enable_audit_logging": 1,   # CRITICAL for compliance
    "enable_auto_shortlisting": 1,
    "rate_limit_per_hour": 100,
    "rate_limit_per_day": 500,
    "timeout_seconds": 120,
    "temperature": 0.2,  # Lower = more deterministic
    "max_retries": 3
}
```

### Development/Testing Settings

```python
{
    "enable_pii_redaction": 0,  # Can disable for easier debugging
    "enable_audit_logging": 1,  # Keep enabled
    "rate_limit_per_hour": 500, # Higher limits for testing
    "timeout_seconds": 60
}
```

## Security Checklist

### Before Production Deployment

- [ ] API keys configured and encrypted
- [ ] PII redaction enabled
- [ ] Audit logging enabled
- [ ] Rate limits configured appropriately
- [ ] All DocType permissions reviewed
- [ ] Data retention policies configured
- [ ] Backup strategy in place
- [ ] Security audit run and issues resolved
- [ ] User training completed
- [ ] Incident response plan documented

### Regular Maintenance

- [ ] Review audit logs weekly
- [ ] Rotate API keys every 90 days
- [ ] Run security audit monthly
- [ ] Review and adjust rate limits
- [ ] Clean up old data per retention policy
- [ ] Update dependencies for security patches
- [ ] Review user access and permissions

## Incident Response

### Data Breach
1. Immediately disable AI processing (set `enable_ai_processing = 0`)
2. Rotate all API keys
3. Review audit logs for suspicious activity
4. Identify affected records
5. Notify affected candidates per GDPR/local regulations
6. Document incident and remediation

### API Key Compromise
1. Immediately revoke compromised key with LLM provider
2. Generate and configure new key
3. Review recent API usage for unauthorized calls
4. Run security audit
5. Document incident

### Rate Limit Abuse
1. Identify user from audit logs
2. Suspend user access temporarily
3. Review their activity
4. Adjust rate limits if legitimate use
5. Escalate if malicious

## Compliance

### GDPR Requirements
- Right to access: Export candidate data via standard Frappe export
- Right to erasure: Use `anonymize_candidate_data()` function
- Right to rectification: Standard edit permissions
- Data minimization: PII redaction reduces exposure
- Purpose limitation: Audit logs track all AI decisions

### SOC 2 / ISO 27001
- Access controls: Role-based permissions
- Audit trail: Comprehensive logging
- Encryption: API keys encrypted at rest
- Monitoring: Rate limiting and audit reviews
- Incident response: Documented procedures

## Contact & Support

For security concerns or questions:
- Review audit logs via Frappe Error Log
- Run security audit: `bench execute frappe_ai_hiring.ai_hiring.utils.security.run_security_audit`
- Check rate limits: Access via AI Settings page
- Documentation: This file and inline code comments

---

**Last Updated:** December 15, 2025  
**Document Version:** 1.0  
**Review Schedule:** Quarterly
