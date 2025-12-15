# AI Audit Logs - User Guide

## Overview

All AI interactions in the frappe_ai_hiring system are automatically logged to the **AI Audit Log** DocType. This provides a complete audit trail of all AI operations including resume parsing, shortlisting decisions, question generation, interview briefs, and evaluations.

## Accessing Audit Logs

### Method 1: AI Audit Log List View (Easiest)

1. In ERPNext, go to the **sidebar search**
2. Type **"AI Audit Log"** and click the result
3. You'll see a list of all AI operations sorted by most recent first

### Method 2: AI Audit Log Report

1. Go to **Sidebar Search** → **"AI Audit Log Report"**
2. View all logs in a tabular format with filtering options
3. Filter by:
   - Operation Type (Resume Parsing, Shortlisting, etc.)
   - Applicant Name
   - Success/Failure Status
   - Date Range

### Method 3: From Job Applicant Form

1. Open a **Job Applicant** record
2. Scroll to see related AI interactions
3. Click on the "AI Audit Log" section to view all logs for that applicant

## Log Details

Each audit log entry contains:

| Field | Description |
|-------|-------------|
| **Log ID** | Unique identifier for the audit log entry |
| **Timestamp** | Date and time when the AI operation occurred |
| **Operation Type** | Type of operation (Resume Parsing, Shortlisting, Question Generation, Interview Brief, Evaluation) |
| **Applicant** | Job Applicant involved in the operation |
| **Job Opening** | Target job opening |
| **AI Model** | LLM model used (e.g., gpt-4, gpt-3.5-turbo) |
| **Status** | Operation status (Completed, Failed, Processing) |
| **Success** | Whether the operation succeeded (✓ or ✗) |
| **Execution Time** | Time taken for AI processing in milliseconds |
| **User** | ERPNext user who triggered the operation |
| **Error Message** | If failed, the error details |
| **Prompt Preview** | First 500 characters of the prompt sent to AI |
| **Response Preview** | First 500 characters of the AI response |
| **Full Metadata** | Complete JSON metadata including tokens used, scores, etc. |

## Filtering and Searching

### By Operation Type
```
Operation Type = "Resume Parsing"
```
Shows all resume parsing operations.

### By Applicant
```
Applicant = "John Doe"
```
Shows all AI operations for a specific candidate.

### By Status
```
Status = "Failed"
```
Shows all failed operations for troubleshooting.

### By Date Range
```
Timestamp >= 2025-12-01
Timestamp <= 2025-12-31
```
Shows operations within a date range.

### By Success Status
```
Success = ✓
```
Shows only successful operations.

## Use Cases

### 1. Verify AI Recommendations
When reviewing a candidate, check the audit log to see:
- What resume information was parsed
- How the shortlisting decision was made
- What questions were generated
- Interview brief analysis

Click on any log entry to view full details including:
- Complete prompt sent to AI
- Full AI response JSON
- Metadata and scoring details

### 2. Troubleshoot Failed Operations
1. Filter by `Status = "Failed"`
2. Review the error message
3. Check the timestamp to correlate with other system errors
4. Investigate the metadata for context

### 3. Audit Trail for Compliance
- All AI decisions are logged with user, timestamp, and model info
- Useful for regulatory audits and compliance reviews
- Shows exactly what AI saw and recommended

### 4. Performance Analysis
1. Open the AI Audit Log Report
2. Check "Execution Time" to identify slow operations
3. Correlate with AI model used and operation type
4. Identify optimization opportunities

### 5. Model Evaluation
- Compare results between different AI models
- Track which model was used for each operation
- Analyze success rates by model

## Accessing Logs Programmatically

### Python API
```python
from frappe_ai_hiring.ai_hiring.utils.audit_logger import AIAuditLogger

# Get logs for a specific applicant
logs = AIAuditLogger.get_logs_for_applicant("John Doe")

# Get logs for a specific operation
logs = AIAuditLogger.get_logs_by_operation("Shortlisting")

# Get all failed operations
failed_logs = AIAuditLogger.get_failed_operations()
```

### Frappe API
```javascript
frappe.call({
    method: 'frappe.client.get_list',
    args: {
        doctype: 'AI Audit Log',
        filters: {
            'applicant': 'John Doe'
        },
        fields: ['name', 'timestamp', 'operation_type', 'success']
    },
    callback: (r) => {
        console.log(r.message);
    }
});
```

## Data Retention Policy

Audit logs are automatically managed based on settings in **AI Settings**:

- **Audit Log Retention**: Configurable retention period (default: 90 days)
- **Data Cleanup**: Automatic deletion of old logs based on retention policy
- **Archive**: Before deletion, logs can be exported for long-term archival

To configure:
1. Go to **AI Settings** form
2. Set `enable_data_retention` = On
3. Set `audit_log_retention_days` (e.g., 90, 180, 365)
4. Save

## Permissions

- **System Manager**: Full read/export access
- **HR Manager**: Read and export access
- **Other Roles**: No access by default (add via role permissions if needed)

To grant access to additional roles:
1. Open **AI Audit Log** DocType
2. Go to **Permissions** section
3. Add new role with "Read" and "Export" permissions

## Monitoring and Alerts

### Monitor Failed Operations
Create a filtered view:
1. Open **AI Audit Log** list
2. Filter: `Status = "Failed"` or `Success = ✗`
3. Save this filter as a report

### Performance Monitoring
Create a report to identify slow operations:
```sql
SELECT 
    operation_type, 
    AVG(execution_time_ms) as avg_time,
    MAX(execution_time_ms) as max_time
FROM `tabAI Audit Log`
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY operation_type
ORDER BY avg_time DESC
```

## Exporting Logs

### Export to CSV
1. Open **AI Audit Log** list or report
2. Click **Menu** (three dots)
3. Select **Export**
4. Choose CSV format
5. Download file

### Export for Analysis
1. Filter logs as needed
2. Export to CSV
3. Open in Excel, Sheets, or data analysis tool
4. Create custom reports and visualizations

## Troubleshooting

### No Logs Appearing
1. Verify `enable_audit_logging` is On in **AI Settings**
2. Check that AI processing has actually occurred
3. Ensure you have permission to view AI Audit Log
4. Check timestamps - logs are sorted by recency

### Logs Not Recording
1. Check **Error Logs** (Sidebar → Error Log) for audit logger errors
2. Verify database write permissions
3. Check log file: `logs/ai_hiring.log`

### Slow Performance with Large Log Volume
1. Create indexes: Use the migrations tool to rebuild indexes
2. Archive old logs: Export and delete logs older than retention period
3. Filter queries: Use date range filters to reduce result set

## Example Scenarios

### Scenario 1: Review why a candidate was shortlisted
```
1. Open Job Applicant "Jane Smith"
2. Go to sidebar, search "AI Audit Log"
3. Filter: Applicant = "Jane Smith", Operation Type = "Shortlisting"
4. Click the latest entry to view full details
5. Review fit_score, decision reasoning, and technical_fit score
6. Check which AI model made the decision
```

### Scenario 2: Debug a failed question generation
```
1. Go to AI Audit Log Report
2. Filter: Status = "Failed", Operation Type = "Question Generation"
3. Find the entry with the error
4. Review Error Message field to see what went wrong
5. Check the timestamp to correlate with job applicant processing
6. Verify AI Settings configuration for that time period
```

### Scenario 3: Compliance audit of AI recommendations
```
1. Export AI Audit Log for a date range (e.g., Q4 2025)
2. Filter to only "Shortlisting" and "Evaluation" operations
3. Document:
   - Number of decisions made
   - Success/failure rates
   - AI models used
   - Average execution times
   - Applicants processed
4. Include in audit report
```

## Best Practices

1. **Regular Review**: Review audit logs weekly to catch issues early
2. **Monitor Performance**: Track execution times and identify bottlenecks
3. **Archive Old Logs**: Export and store old logs per retention policy
4. **Analyze Failures**: Set up alerts for failed operations
5. **Document Decisions**: Reference log IDs when documenting hiring decisions
6. **Compliance**: Maintain audit logs for compliance and regulatory requirements

## Support

For issues or questions about audit logs:
1. Check the logs for error messages
2. Review [Error Logs](error-log) for system errors
3. Contact System Manager or Technical Support
4. Include log ID(s) when reporting issues
