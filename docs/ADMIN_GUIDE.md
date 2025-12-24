# AI Hiring Automation - Admin Guide

## 📋 Table of Contents

1. [System Administration](#system-administration)
2. [Installation & Configuration](#installation--configuration)
3. [Maintenance](#maintenance)
4. [Security](#security)
5. [Performance Tuning](#performance-tuning)
6. [Monitoring](#monitoring)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)

---

## System Administration

### Architecture Overview

AI Hiring Automation consists of:

**Core Components**:
- **DocTypes**: 6 AI-specific DocTypes + Job Applicant integration
- **Services**: Resume parser, shortlisting, question generator, evaluator, interview brief
- **Background Jobs**: Async processing with retry logic
- **API Layer**: OpenAI-compatible LLM integration
- **Utilities**: Security, audit logging, PII redaction

**Data Flow**:
```
Job Applicant Created
    ↓
Resume Parsing (extract → AI parse)
    ↓
Shortlisting (evaluate → score → decision)
   ↓
Manual Actions (triggered from Job Applicant):
  - Generate Questions (no automatic generation)
  - Send Questionnaire (manual)
  - Send Rejected Mail (manual)
  - Candidate Completes → Evaluation (manual)
  - Generate Interview Brief (manual)
   ↓
Interview → Offer → Hire
```

### System Requirements

**Production Environment**:
- **OS**: Ubuntu 20.04 LTS or later
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB+ recommended
- **Storage**: 50GB+ (includes database, files, logs)
- **Redis**: 6.0+ for rate limiting and caching
- **Python**: 3.10 or later
- **Frappe**: v14 or v15

**Network**:
- Outbound HTTPS to API provider
- Port 443 for API calls
- SMTP for email notifications
- Minimum 10 Mbps connection

### Dependencies

Required Python packages (auto-installed):
```
frappe>=14.0.0
PyPDF2>=3.0.0
python-docx>=0.8.11
openai>=1.0.0
redis>=4.5.0
pydantic>=2.0.0
```

---

## Installation & Configuration

### Fresh Installation

#### 1. Install via Bench

```bash
# Get the app
cd ~/frappe-bench
bench get-app https://github.com/your-org/ai_hiring.git

# Install on site
bench --site yoursite.local install-app ai_hiring

# Migrate database
bench --site yoursite.local migrate

# Clear cache
bench --site yoursite.local clear-cache

# Restart
bench restart
```

#### 2. Run Setup Wizard

```bash
# Set up initial configuration
bench --site yoursite.local console

>>> from ai_hiring.setup import setup_wizard
>>> setup_wizard.run()
```

#### 3. Configure AI Settings

Navigate to AI Settings and configure:

**API Configuration**:
```
API Provider: OpenAI
API Key: sk-proj-xxxxx
API Endpoint: https://api.openai.com/v1
Model Name: gpt-4
Temperature: 0.2
Max Tokens: 2000
Timeout: 60
```

**Rate Limiting** (adjust based on budget):
```
Enable Rate Limiting: Yes
Hourly Limit: 100
Daily Limit: 500
Burst Allowance: 10
```

**Data Retention**:
```
Enable Data Retention: Yes
Audit Log Retention: 90 days
Rejected Candidate Retention: 30 days
Resume File Retention: 180 days
```

#### 4. Set Up Permissions

Run permission setup script:
```bash
bench --site yoursite.local execute ai_hiring.setup.permissions.setup_roles_and_permissions
```

Or manually configure in Role Permissions Manager.

### Multi-Site Installation

For multiple sites on same bench:

```bash
# Install on each site
bench --site site1.local install-app ai_hiring
bench --site site2.local install-app ai_hiring

# Separate configurations per site
# Each site has its own AI Settings
```

### Docker Deployment

Sample Dockerfile:
```dockerfile
FROM frappe/erpnext:v14

# Install AI Hiring
RUN bench get-app https://github.com/your-org/ai_hiring.git \
    && bench --site all install-app ai_hiring

# Install dependencies
RUN pip3 install PyPDF2 python-docx openai redis pydantic

EXPOSE 8000 9000 6787
```

### Environment Variables

Set in `sites/common_site_config.json` or environment:

```json
{
  "ai_hiring": {
    "api_key": "your-api-key",
    "rate_limit_hourly": 100,
    "rate_limit_daily": 500,
    "enable_audit_log": true,
    "log_level": "INFO"
  }
}
```

Or use environment variables:
```bash
export AI_HIRING_API_KEY="sk-proj-xxxxx"
export AI_HIRING_RATE_LIMIT_HOURLY=100
export AI_HIRING_RATE_LIMIT_DAILY=500
```

---

## Maintenance

### Daily Tasks

**Automated** (via scheduled jobs):
- Process queued candidates
- Clean up expired rate limits
- Send pending notifications
- Generate daily statistics

**Manual Review**:
- Check Error Log for issues
- Monitor Background Jobs queue
- Review AI Audit Log for anomalies

### Weekly Tasks

1. **Review AI Performance**:
   ```bash
   bench --site yoursite.local execute ai_hiring.utils.analytics.generate_weekly_report
   ```

2. **Check API Usage**:
   - Review API call counts
   - Compare against budget
   - Adjust rate limits if needed

3. **Update Content**:
   - Review email templates
   - Update questionnaire prompts (if needed)
   - Refine job description templates

### Monthly Tasks

1. **Data Cleanup**:
   ```bash
   # Run data retention cleanup
   bench --site yoursite.local execute ai_hiring.utils.security.DataRetentionPolicy().cleanup_old_data
   ```

2. **Performance Review**:
   - Run AI Performance Report
   - Calculate accuracy metrics
   - Identify areas for improvement

3. **Security Audit**:
   - Review access logs
   - Check permission changes
   - Validate security settings

4. **Backup Verification**:
   - Test backup restoration
   - Verify file integrity
   - Update backup documentation

### Quarterly Tasks

1. **System Updates**:
   ```bash
   # Update app
   cd ~/frappe-bench
   bench get-app ai_hiring --branch main
   bench --site yoursite.local migrate
   bench restart
   ```

2. **Comprehensive Audit**:
   - Review all configurations
   - Update documentation
   - Train new users
   - Assess ROI and metrics

3. **Prompt Optimization**:
   - Analyze AI decision accuracy
   - Refine system prompts
   - A/B test improvements

---

## Security

### Access Control

**Role-Based Permissions**:

1. **HR Manager** (full access):
   - All AI DocTypes (read/write/delete)
   - AI Settings (modify)
   - All reports
   - System configuration

2. **HR User** (standard access):
   - Job Applicant (read/write)
   - AI results (read-only)
   - Reports (view)
   - Cannot modify settings

3. **Interviewer** (limited access):
   - Interview Briefs (read)
   - Job Applicant (read-only)
   - Can add interview feedback
   - Limited reports

4. **Candidate** (restricted):
   - Own questionnaire (read/write)
   - Own application status (read)
   - No access to AI evaluations

### API Key Management

**Storage**:
- Store in Frappe Password field (encrypted)
- Never commit to version control
- Use environment variables in production

**Rotation**:
```bash
# Update API key
bench --site yoursite.local console

>>> from frappe import get_doc
>>> settings = get_doc("AI Settings")
>>> settings.api_key = "new-api-key"
>>> settings.save()
```

**Monitoring**:
- Log all API usage
- Alert on unusual patterns
- Track costs per endpoint

### Data Protection

**PII Handling**:
- Enable PII redaction in logs
- Mask sensitive fields in exports
- Anonymize before data sharing

**Encryption**:
- TLS 1.2+ for API communication
- Database encryption at rest
- Secure file storage

**GDPR Compliance**:
```bash
# Export candidate data (GDPR request)
bench --site yoursite.local execute ai_hiring.utils.security.export_candidate_data --applicant-id JOB-APP-0001

# Anonymize candidate (right to be forgotten)
bench --site yoursite.local execute ai_hiring.utils.security.anonymize_candidate --applicant-id JOB-APP-0001
```

### Rate Limiting

**Configuration**:
```python
# In AI Settings
Rate Limiting:
  - Hourly: 100 requests
  - Daily: 500 requests
  - Per user: 20 requests/hour
  - Burst: 10 requests/minute
```

**Override** (admin only):
```python
from ai_hiring.utils.security import RateLimiter

# Temporarily increase limit
limiter = RateLimiter()
limiter.set_limit("hourly", 200)
```

**Monitoring**:
```bash
# Check rate limit status
bench --site yoursite.local execute ai_hiring.utils.security.check_rate_limits
```

### Audit Logging

**What's Logged**:
- All AI operations
- API calls and responses
- User actions
- Configuration changes
- Security events

**Log Review**:
```sql
-- Recent AI operations
SELECT operation, job_applicant, result, creation 
FROM `tabAI Audit Log` 
WHERE creation > DATE_SUB(NOW(), INTERVAL 24 HOUR)
ORDER BY creation DESC;

-- Failed operations
SELECT * FROM `tabAI Audit Log` 
WHERE success = 0 
AND creation > DATE_SUB(NOW(), INTERVAL 7 DAY);
```

**Export Logs**:
```bash
# Export for compliance
bench --site yoursite.local execute ai_hiring.utils.audit.export_audit_logs --from-date 2024-01-01 --to-date 2024-12-31
```

---

## Performance Tuning

### Database Optimization

**Indexes**:
```sql
-- Add indexes for common queries
ALTER TABLE `tabJob Applicant` ADD INDEX idx_job_title (job_title);
ALTER TABLE `tabJob Applicant` ADD INDEX idx_status_creation (status, creation);
ALTER TABLE `tabAI Audit Log` ADD INDEX idx_applicant_operation (job_applicant, operation);
```

**Query Optimization**:
- Use indexes for large tables
- Limit result sets
- Cache frequent queries
- Archive old records

### Background Job Tuning

**Worker Configuration**:
```python
# bench/config.json
{
  "background_workers": 4,
  "gunicorn_workers": 4,
  "worker_timeout": 300
}
```

**Job Priorities**:
- High: Resume parsing
- Medium: Shortlisting, evaluation
- Low: Notifications, cleanup

**Retry Settings**:
```python
# In ai_hiring/jobs/job_manager.py
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds
EXPONENTIAL_BACKOFF = True
```

### API Performance

**Timeouts**:
- Resume parsing: 60s
- Shortlisting: 45s
- Question generation: 30s
- Evaluation: 30s
- Interview brief: 45s

**Caching**:
```python
# Cache common job descriptions
from frappe.cache import Cache
cache = Cache()
cache.set_value("job_desc_JOB-001", description, expires_in_sec=3600)
```

**Batch Processing**:
```bash
# Process multiple candidates
bench --site yoursite.local execute ai_hiring.jobs.batch_processor.process_batch --limit 10
```

### File Storage

**Optimization**:
- Compress old resume files
- Move to object storage (S3, MinIO)
- Implement CDN for large files

**Cleanup**:
```bash
# Remove old resume files
bench --site yoursite.local execute ai_hiring.utils.cleanup.remove_old_resume_files --days 180
```

---

## Monitoring

### Health Checks

**System Health**:
```bash
# Check all components
bench --site yoursite.local execute ai_hiring.utils.monitoring.health_check
```

Expected output:
```json
{
  "status": "healthy",
  "api_connection": true,
  "redis_connection": true,
  "db_connection": true,
  "background_workers": true,
  "disk_space": "45GB free",
  "uptime": "15 days"
}
```

### Metrics

**Key Metrics to Track**:

1. **Processing Metrics**:
   - Candidates processed per day
   - Average processing time
   - Success rate per stage
   - API call counts

2. **Quality Metrics**:
   - AI accuracy (decisions vs. outcomes)
   - User override rate
   - False positive/negative rates
   - Questionnaire completion rate

3. **Performance Metrics**:
   - API response times
   - Background job latency
   - Database query times
   - Error rates

**Monitoring Queries**:
```sql
-- Daily processing volume
SELECT DATE(creation) as date, COUNT(*) as count
FROM `tabJob Applicant`
WHERE creation > DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(creation);

-- API success rate
SELECT 
  operation,
  COUNT(*) as total,
  SUM(success) as successful,
  (SUM(success) / COUNT(*)) * 100 as success_rate
FROM `tabAI Audit Log`
WHERE creation > DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY operation;

-- Average processing time
SELECT 
  operation,
  AVG(processing_time) as avg_time,
  MAX(processing_time) as max_time
FROM `tabAI Audit Log`
WHERE creation > DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY operation;
```

### Alerting

**Set up alerts for**:
- API errors (>5% failure rate)
- Rate limit exceeded
- Background jobs failing
- Disk space low (<10GB)
- Long processing times (>5 min)

**Alert Configuration** (example with Prometheus):
```yaml
groups:
  - name: ai_hiring
    rules:
      - alert: HighAPIErrorRate
        expr: (rate(ai_api_errors[5m]) / rate(ai_api_requests[5m])) > 0.05
        for: 10m
        annotations:
          summary: "High AI API error rate"
```

### Logging

**Log Levels**:
- **DEBUG**: Detailed diagnostic info
- **INFO**: General operational messages
- **WARNING**: Warning messages
- **ERROR**: Error events
- **CRITICAL**: Critical failures

**Configure**:
```python
# In ai_hiring/utils/config.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ai_hiring.log'),
        logging.StreamHandler()
    ]
)
```

**Log Rotation**:
```bash
# /etc/logrotate.d/ai_hiring
/path/to/frappe-bench/logs/ai_hiring.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 frappe frappe
}
```

---

## Backup & Recovery

### Backup Strategy

**What to Backup**:
1. Database (all AI DocTypes)
2. Resume files
3. Configuration files
4. Custom code/modifications

**Frequency**:
- **Database**: Daily
- **Files**: Daily
- **Configuration**: After changes
- **Full system**: Weekly

### Automated Backups

**Setup**:
```bash
# Daily database backup
crontab -e

# Add line:
0 2 * * * cd ~/frappe-bench && bench --site yoursite.local backup --with-files

# Weekly full backup
0 3 * * 0 cd ~/frappe-bench && bench --site yoursite.local backup --with-files && tar -czf backup-$(date +\%Y\%m\%d).tar.gz sites/yoursite.local/private/backups
```

**Backup to Cloud**:
```bash
# S3 backup
bench --site yoursite.local backup --with-files
aws s3 cp sites/yoursite.local/private/backups/ s3://your-bucket/frappe-backups/ --recursive
```

### Recovery Procedures

#### Database Recovery

```bash
# List backups
ls -lh sites/yoursite.local/private/backups/

# Restore database
bench --site yoursite.local restore --mariadb-root-password yourpassword sites/yoursite.local/private/backups/20241215_0200_database.sql.gz

# Migrate to latest
bench --site yoursite.local migrate

# Clear cache
bench --site yoursite.local clear-cache

# Restart
bench restart
```

#### File Recovery

```bash
# Restore files
tar -xzf sites/yoursite.local/private/backups/20241215_0200_files.tar.gz -C sites/yoursite.local/

# Fix permissions
sudo chown -R frappe:frappe sites/yoursite.local/
```

#### Disaster Recovery

**Complete Site Restoration**:
```bash
# Create new site
bench new-site yoursite.local

# Restore backup
bench --site yoursite.local restore --with-public-files --with-private-files sites/yoursite.local/private/backups/20241215_0200_database.sql.gz

# Install apps
bench --site yoursite.local install-app erpnext
bench --site yoursite.local install-app ai_hiring

# Migrate
bench --site yoursite.local migrate

# Start
bench start
```

---

## Troubleshooting

### Common Issues

#### 1. API Connection Failures

**Symptoms**: "API connection failed" errors

**Diagnosis**:
```bash
# Test API connectivity
bench --site yoursite.local console

>>> from ai_hiring.utils.llm_client import LLMClient
>>> client = LLMClient()
>>> result = client.test_connection()
>>> print(result)
```

**Solutions**:
- Verify API key validity
- Check internet connectivity
- Verify endpoint URL
- Check firewall rules
- Review proxy settings

#### 2. Background Jobs Not Processing

**Symptoms**: Candidates stuck in processing

**Diagnosis**:
```bash
# Check worker status
bench --site yoursite.local doctor

# View job queue
bench --site yoursite.local console

>>> frappe.db.get_all("RQ Job", fields=["name", "status", "job_name"], limit=20)
```

**Solutions**:
```bash
# Restart workers
bench restart

# Clear stuck jobs
bench --site yoursite.local execute frappe.utils.background_jobs.clear_failed_jobs

# Requeue failed
bench --site yoursite.local execute ai_hiring.jobs.job_manager.requeue_failed_jobs
```

#### 3. High Memory Usage

**Symptoms**: System slowdown, OOM errors

**Diagnosis**:
```bash
# Check memory
free -h
top -u frappe

# Check process memory
ps aux --sort=-%mem | head
```

**Solutions**:
- Reduce gunicorn workers
- Optimize database queries
- Clear caches: `bench --site yoursite.local clear-cache`
- Restart bench: `bench restart`
- Upgrade server RAM

#### 4. Slow AI Processing

**Symptoms**: Long wait times for results

**Diagnosis**:
```sql
-- Check processing times
SELECT operation, AVG(processing_time), MAX(processing_time)
FROM `tabAI Audit Log`
WHERE creation > DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY operation;
```

**Solutions**:
- Reduce max_tokens in AI Settings
- Use faster model (gpt-3.5-turbo)
- Increase API timeout
- Check network latency
- Review prompt length

#### 5. Database Lock Issues

**Symptoms**: "Deadlock found" errors

**Diagnosis**:
```sql
-- Check for locks
SHOW PROCESSLIST;
SHOW ENGINE INNODB STATUS;
```

**Solutions**:
```sql
-- Kill blocking query
KILL <process_id>;

-- Restart MariaDB
sudo systemctl restart mariadb

-- Optimize tables
OPTIMIZE TABLE `tabJob Applicant`;
OPTIMIZE TABLE `tabAI Audit Log`;
```

### Debug Mode

**Enable**:
```bash
# In site_config.json
{
  "developer_mode": 1,
  "debug": true,
  "ai_hiring_debug": true
}

# Restart
bench restart
```

**Debug Logging**:
```python
# In service files
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.debug("Detailed debug information")
```

### Performance Profiling

**Profile API Calls**:
```python
import time

start = time.time()
result = client.generate_structured_output(...)
duration = time.time() - start

logger.info(f"API call took {duration:.2f}s")
```

**Database Query Profiling**:
```python
# In Frappe console
frappe.db.sql("SET profiling = 1")
# Run queries
frappe.db.sql("SHOW PROFILES")
frappe.db.sql("SHOW PROFILE FOR QUERY 1")
```

---

## Appendix

### Configuration Files

**Key Files**:
- `hooks.py`: App hooks and scheduled jobs
- `modules.txt`: App modules
- `patches.txt`: Database migration patches
- `ai_hiring/config.py`: App configuration
- `ai_hiring/utils/constants.py`: Constants and settings

### API Endpoints

**Public APIs** (require authentication):
- `/api/method/ai_hiring.api.parse_resume`
- `/api/method/ai_hiring.api.evaluate_candidate`
- `/api/method/ai_hiring.api.generate_questions`
- `/api/method/ai_hiring.api.evaluate_answers`
- `/api/method/ai_hiring.api.generate_interview_brief`

### Database Schema

**Key Tables**:
- `tabJob Applicant`: Candidate applications
- `tabAI Resume Parsing`: Parsed resume data
- `tabAI Shortlisting Result`: Evaluation results
- `tabAI Questionnaire`: Generated questions
- `tabAI Questionnaire Evaluation`: Answer evaluation
- `tabAI Interview Brief`: Interview briefs
- `tabAI Audit Log`: Operation audit trail
- `tabAI Settings`: Configuration

### Support Contacts

- **Technical Support**: support@yourcompany.com
- **Emergency**: emergency@yourcompany.com
- **Security Issues**: security@yourcompany.com
- **GitHub**: https://github.com/your-org/ai_hiring

---

**Document Version**: 1.0  
**Last Updated**: 2024-12-15  
**Next Review**: 2025-03-15  
**Maintained By**: DevOps Team

```
frappe.call({
    method: "frappe_ai_hiring.ai_hiring.services.resume_extractor.debug_resume_extraction",
    args: { applicant_name: "JOB-APP-2024-00001" },
    callback: (r) => console.log(r.message)
});
```