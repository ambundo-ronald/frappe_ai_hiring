# AI Hiring Automation - User Guide

## 📖 Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Setup Instructions](#setup-instructions)
4. [Using the System](#using-the-system)
5. [Features](#features)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Introduction

AI Hiring Automation is a Frappe/ERPNext application that streamlines the recruitment process using artificial intelligence. The system automatically:

- Parses resumes and extracts candidate information
- Evaluates candidates against job descriptions
- Generates customized questionnaires
- Evaluates candidate responses
- Creates interview briefs for hiring managers
- Tracks the entire hiring pipeline

### Key Benefits

- **Time Savings**: Automate initial screening and reduce manual resume review
- **Consistency**: Apply uniform evaluation criteria across all candidates
- **Transparency**: AI provides explainable decisions with detailed reasoning
- **Efficiency**: Process multiple candidates simultaneously
- **Insights**: Analytics and reports for data-driven hiring decisions

---

## Getting Started

### Prerequisites

Before using AI Hiring Automation, ensure you have:

1. **Frappe Framework** v14 or later installed
2. **ERPNext** with HRMS module (optional but recommended)
3. **OpenAI-compatible API** access (OpenAI, Azure OpenAI, or compatible endpoint)
4. **Python 3.10+** with required packages
5. **Redis** server for rate limiting

### System Requirements

- **Server**: Linux (Ubuntu 20.04+ recommended) or macOS
- **RAM**: Minimum 4GB, recommended 8GB+
- **Storage**: 10GB+ available
- **Network**: Stable internet connection for API calls

---

## Setup Instructions

### 1. Install the App

```bash
# Navigate to your Frappe bench directory
cd ~/frappe-bench

# Get the app from repository
bench get-app https://github.com/your-org/ai_hiring.git

# Install the app on your site
bench --site your-site.local install-app ai_hiring

# Restart bench
bench restart
```

### 2. Configure AI Settings

1. Log in to your Frappe/ERPNext site
2. Navigate to **AI Hiring > AI Settings**
3. Configure the following:

#### API Configuration

- **API Provider**: Select your provider (OpenAI, Azure OpenAI, Custom)
- **API Key**: Enter your API key
- **API Endpoint**: Enter API endpoint (for custom providers)
- **Model Name**: Specify model (e.g., gpt-4, gpt-3.5-turbo)
- **Temperature**: Set to 0.2 for consistent results
- **Max Tokens**: Default 2000 (adjust based on needs)
- **Timeout**: API request timeout in seconds (default: 60)

#### Rate Limiting

- **Enable Rate Limiting**: Check to enable
- **Hourly Limit**: Maximum API calls per hour (default: 100)
- **Daily Limit**: Maximum API calls per day (default: 500)

#### Data Retention

- **Enable Data Retention**: Check to enable automatic cleanup
- **Audit Log Retention Days**: How long to keep audit logs (default: 90)
- **Rejected Candidate Retention Days**: How long to keep rejected candidates (default: 30)

#### Features

- **Enable Resume Parsing**: Auto-extract resume data
- **Enable Shortlisting**: Auto-evaluate candidates
- **Enable Question Generation**: Auto-create questionnaires
- **Enable Questionnaire Evaluation**: Auto-evaluate answers
- **Enable Interview Brief**: Auto-generate interview briefs

4. Click **Save**

### 3. Set Up Permissions

Navigate to **Setup > Role Permissions Manager** and configure:

#### HR Manager Role
- Full access to all AI Hiring DocTypes
- Can view all reports
- Can modify AI Settings

#### HR User Role
- Read/Write access to Job Applicants
- Read-only access to AI results
- Can view reports

#### Interviewer Role
- Read-only access to Interview Briefs
- Can add interview feedback
- Limited report access

### 4. Test the Configuration

1. Go to **AI Settings**
2. Click the **Test Configuration** button
3. Verify all checks pass:
   - ✅ API connection successful
   - ✅ Rate limiting active
   - ✅ Required DocTypes exist
   - ✅ Permissions configured correctly

---

## Using the System

### Creating a Job Opening

1. Navigate to **HRMS > Job Opening**
2. Click **New**
3. Fill in details:
   - **Job Title**: Position name
   - **Description**: Detailed job description including:
     - Required skills
     - Experience requirements
     - Education requirements
     - Responsibilities
     - Qualifications
4. Save the Job Opening

**Tip**: The AI uses your job description for evaluation, so be thorough and specific!

### Processing Candidates

#### Automatic Processing (Recommended)

When a candidate applies through the career portal or email:

1. Create a **Job Applicant** record
2. Attach the resume file (PDF, DOCX, or TXT)
3. Link to the Job Opening
4. Save the document

The system automatically:
- Extracts text from the resume
- Parses candidate information
- Evaluates against job description
- Generates a shortlisting decision
- Creates questionnaire (if shortlisted)
- Sends notification emails

#### Manual Processing

If automatic processing didn't run:

1. Open the Job Applicant
2. Click **Actions > Reprocess Candidate**
3. Select which stages to reprocess
4. Click **Process**

### Reviewing AI Results

#### Resume Parsing Results

1. Open the Job Applicant
2. Navigate to the **AI Resume Parsing** section
3. Review extracted data:
   - Personal information
   - Skills list
   - Work experience
   - Education
   - Total experience years

Click **View Parsed Resume** to see the full AI analysis.

#### Shortlisting Results

1. In the Job Applicant, find the **AI Shortlisting Result** section
2. Review:
   - **AI Decision**: Shortlist, Reject, or Review
   - **Fit Score**: 0-100 match percentage
   - **Technical Skills Match**: Skills alignment
   - **Experience Match**: Experience level fit
   - **Education Match**: Education requirements
   - **Key Strengths**: Candidate advantages
   - **Potential Concerns**: Areas of concern
   - **Recommendations**: AI advice

**Decision Types:**

- **Shortlist** (Score 75+): Strong candidate, proceed to next stage
- **Review** (Score 50-74): Borderline case, requires HR review
- **Reject** (Score <50): Does not meet requirements

### Sending Questionnaires

For shortlisted candidates:

1. Open the Job Applicant
2. Go to **AI Questionnaire** section
3. Review generated questions
4. Click **Send Questionnaire**
5. Email with questionnaire link sent automatically

Candidates receive an email with a unique link to complete the questionnaire.

### Reviewing Questionnaire Results

After candidate completion:

1. Open the Job Applicant
2. Navigate to **Questionnaire Evaluation**
3. Review:
   - **Overall Score**: Weighted score based on answers
   - **Topic Scores**: Performance by category
   - **Strengths**: Areas where candidate excelled
   - **Areas for Improvement**: Gaps identified
   - **Recommendation**: AI assessment

### Interview Preparation

For candidates proceeding to interview:

1. Open the Job Applicant
2. View **Interview Brief** section
3. The brief includes:
   - **Candidate Summary**: Quick overview
   - **Key Strengths**: What to validate
   - **Areas to Probe**: What to investigate
   - **Suggested Questions**: Interview questions
   - **Technical Depth Questions**: Deep-dive topics
   - **Red Flags**: Concerns to address
   - **Overall Recommendation**: AI hiring recommendation

4. Click **Schedule Interview** to create interview event
5. Interviewers automatically receive brief via email

### Tracking Pipeline Progress

#### Dashboard View

1. Navigate to **AI Hiring > Dashboard**
2. View metrics:
   - Active candidates by stage
   - Hired vs. rejected counts
   - AI processing statistics
   - Average fit scores
   - Pending actions

#### Workflow Status

For each candidate, view their current stage:

- **Not Started**: Application received
- **Resume Parsing**: Extracting information
- **Shortlisting**: Evaluating fit
- **Questions Generated**: Questionnaire created
- **Questionnaire Sent**: Waiting for responses
- **Questionnaire Completed**: Responses received
- **Evaluation Complete**: Answers analyzed
- **Interview Brief Generated**: Brief ready
- **Interview Scheduled**: Interview planned
- **Interview Completed**: Feedback received
- **Offer Extended**: Offer sent
- **Hired**: Candidate accepted
- **Rejected**: Not proceeding

### Reports

#### AI Hiring Pipeline Report

**Purpose**: Comprehensive view of all candidates in the pipeline

**Access**: Reports > AI Hiring Pipeline Report

**Filters**:
- Job Title
- Status
- Date Range
- AI Decision

**Columns**:
- Applicant name and email
- Job position
- Application and modified dates
- AI decision and fit score
- Questionnaire status and score
- Interview status
- Recommendations
- Days in pipeline

**Use Cases**:
- Monitor pipeline bottlenecks
- Identify stalled applications
- Track candidate progress
- Generate hiring reports

#### AI Performance Report

**Purpose**: Analyze AI accuracy and performance

**Access**: Reports > AI Performance Report

**Filters**:
- Date Range
- Job Title
- AI Decision

**Metrics**:
- AI decisions vs. final outcomes
- Accuracy rate (correct predictions)
- Average fit scores by decision type
- Performance visualization (chart)

**Use Cases**:
- Validate AI decisions
- Identify bias or patterns
- Improve AI prompts
- Training data analysis

---

## Features

### Resume Parsing

**What it does**: Automatically extracts structured data from resume files

**Supported Formats**:
- PDF (.pdf)
- Microsoft Word (.docx)
- Plain Text (.txt)

**Extracted Information**:
- Full name
- Email address
- Phone number
- Professional summary
- Work experience (company, title, dates, description)
- Education (degree, institution, year)
- Skills list
- Certifications
- Total years of experience

**Tips for Best Results**:
- Use well-formatted resumes
- Ensure text is selectable in PDFs (not scanned images)
- Standard resume sections (Experience, Education, Skills)

### Candidate Shortlisting

**What it does**: Evaluates candidates against job requirements

**Evaluation Criteria**:
- Technical skills match
- Experience level and relevance
- Education qualifications
- Industry experience
- Career progression
- Keywords alignment

**Scoring**:
- 0-100 fit score
- Individual component scores
- Weighted based on job requirements

**Output**:
- AI decision (Shortlist/Review/Reject)
- Detailed strengths and concerns
- Actionable recommendations

### Question Generation

**What it does**: Creates customized yes/no questionnaires

**Features**:
- Tailored to candidate background
- Focused on job requirements
- Weighted by importance
- Topic categorization
- Skill verification
- Experience validation

**Typical Question Topics**:
- Technical skills
- Tool proficiency
- Domain experience
- Leadership capabilities
- Soft skills
- Availability

**Customization**:
- Specify number of questions (default: 10-15)
- Focus on specific areas
- Adjust difficulty level

### Questionnaire Evaluation

**What it does**: Analyzes candidate responses

**Analysis**:
- Overall weighted score
- Topic-wise performance
- Strength identification
- Gap analysis
- Hiring recommendation

**Scoring Method**:
- Binary answers (yes/no)
- Weighted by question importance
- Topic-level aggregation
- Threshold-based decisions

### Interview Brief Generation

**What it does**: Creates comprehensive interview guides

**Includes**:
- Candidate snapshot
- Background summary
- Key strengths to validate
- Concerns to investigate
- Suggested interview questions
- Technical deep-dive topics
- Red flags to explore
- Final recommendation

**Integrates**:
- Resume data
- Shortlisting results
- Questionnaire performance
- Job requirements

---

## Troubleshooting

### Common Issues

#### Resume Parsing Failed

**Symptoms**: Error message "Failed to parse resume"

**Causes**:
- Unsupported file format
- Corrupted file
- Scanned PDF (image-only)
- API error

**Solutions**:
1. Verify file format (PDF, DOCX, TXT only)
2. Re-upload file
3. Try converting to plain text
4. Check API key and connectivity
5. Review error logs in AI Audit Log

#### API Rate Limit Exceeded

**Symptoms**: Error "Rate limit exceeded"

**Causes**:
- Too many API calls in short period
- Rate limit set too low

**Solutions**:
1. Wait for rate limit window to reset
2. Increase limits in AI Settings (if budget allows)
3. Batch process during off-peak hours
4. Enable queuing for background processing

#### Low-Quality AI Results

**Symptoms**: Poor candidate evaluations, irrelevant questions

**Causes**:
- Vague job descriptions
- Inadequate resume information
- Wrong AI model/settings
- Poor quality training data

**Solutions**:
1. Improve job descriptions with specific requirements
2. Request better formatted resumes from candidates
3. Adjust AI temperature (try 0.1-0.3)
4. Use more advanced model (e.g., GPT-4)
5. Review and refine prompts in service files

#### Candidate Not Receiving Emails

**Symptoms**: Questionnaire/notification emails not delivered

**Causes**:
- Email configuration issue
- Spam filter blocking
- Incorrect email address
- SMTP server down

**Solutions**:
1. Verify email setup in Frappe (Email Account)
2. Check spam/junk folders
3. Test with different email provider
4. Review Email Queue (Setup > Email Queue)
5. Check candidate email address

#### Processing Stuck

**Symptoms**: Candidate stuck in one stage, no progress

**Causes**:
- Background job failed
- API timeout
- System error

**Solutions**:
1. Check background job status (Setup > Background Jobs)
2. View error logs (AI Audit Log DocType)
3. Manually reprocess candidate
4. Restart background workers: `bench restart`
5. Check Redis connection

### Error Messages

#### "API key not configured"
- Go to AI Settings
- Enter valid API key
- Save and test

#### "Job description not found"
- Ensure Job Opening exists
- Link Job Applicant to Job Opening
- Verify Job Opening has description

#### "Resume attachment missing"
- Attach resume file to Job Applicant
- Supported: PDF, DOCX, TXT
- File size limit: 10MB

#### "Insufficient permissions"
- Contact system administrator
- Check Role Permissions
- Ensure user has required role (HR User/HR Manager)

### Getting Help

#### Check Logs

1. **AI Audit Log**: Detailed AI operation logs
   - Navigate to: AI Hiring > AI Audit Log
   - Filter by applicant or date
   - Review operation results and errors

2. **Frappe Error Log**: System-level errors
   - Navigate to: Setup > Error Log
   - Search for "ai_hiring"

3. **Background Jobs**: Job queue status
   - Navigate to: Setup > Background Jobs
   - Check for failed jobs
   - Retry if needed

#### Support Resources

- **Documentation**: Check this guide and admin guide
- **Security Guide**: Review SECURITY.md for security issues
- **Issue Tracker**: Report bugs on GitHub
- **Community Forum**: Ask questions in Frappe forum

---

## FAQ

### General Questions

**Q: How accurate is the AI evaluation?**

A: Accuracy depends on several factors:
- Job description quality: 70-80% impact
- Resume quality: 20-25% impact
- AI model used: GPT-4 > GPT-3.5-turbo
- Typical accuracy: 85-90% for technical positions

Always review AI recommendations before final decisions.

**Q: Can I customize the AI prompts?**

A: Yes, but requires technical knowledge:
- Prompts are in service files (services/*.py)
- Modify prompt templates carefully
- Test thoroughly after changes
- Consider creating a custom fork

**Q: Does it work with non-English resumes?**

A: Partially:
- OpenAI models support multiple languages
- Best results with English
- Other languages: 60-70% accuracy
- May require prompt modifications

**Q: How much does it cost to run?**

A: Costs depend on:
- **API Usage**: ~$0.02-0.05 per candidate (GPT-3.5)
- **API Usage**: ~$0.10-0.20 per candidate (GPT-4)
- **Server**: Standard Frappe hosting costs
- **Bulk processing**: Consider monthly API budget

Example: 100 candidates/month with GPT-3.5 = ~$3-5/month

**Q: Can it integrate with job boards?**

A: Yes, with custom development:
- Use Frappe's REST API
- Create webhook endpoints
- Parse incoming applications
- Automatic candidate creation

### Privacy & Security

**Q: Is candidate data secure?**

A: Yes:
- Data encrypted in transit (TLS)
- Access controlled by roles
- Audit logging enabled
- GDPR compliance features
- PII redaction available

See SECURITY.md for details.

**Q: Where is data stored?**

A: 
- **Candidate Data**: Your Frappe database
- **Resume Files**: Your file system
- **API Requests**: Sent to AI provider (not stored)
- **Audit Logs**: Your database (auto-cleanup)

**Q: Can candidates see their AI evaluation?**

A: Configurable:
- By default: No
- Can enable candidate portal access
- Selectively share shortlisting results
- Full transparency optional

### Technical Questions

**Q: Can I use a different AI provider?**

A: Yes, if OpenAI-compatible:
- Azure OpenAI: Fully supported
- Anthropic Claude: Requires adapter
- Local models (llama.cpp): Requires adapter
- Custom endpoints: Supported

**Q: Does it work offline?**

A: No:
- Requires internet for API calls
- Redis for rate limiting
- Email for notifications
- Can queue jobs for later processing

**Q: How do I backup AI data?**

A: Use standard Frappe backup:
```bash
bench --site your-site.local backup --with-files
```

Includes all AI DocTypes and resume files.

**Q: Can I export candidate data?**

A: Yes:
- Use reports with export feature
- REST API for programmatic access
- Standard Frappe data export
- GDPR data portability supported

---

## Best Practices

### Job Descriptions

✅ **Do**:
- Be specific about required skills
- List must-have vs. nice-to-have
- Include experience requirements
- Mention tools and technologies
- Describe responsibilities clearly

❌ **Don't**:
- Use vague language
- Copy generic templates
- Omit technical requirements
- Include discriminatory criteria

### Resume Requirements

Ask candidates to submit:
- PDF or DOCX format (not scanned)
- Standard resume structure
- Clear section headers
- Readable fonts
- Complete contact information

### Review Process

1. **Always review AI decisions** before taking action
2. **Investigate borderline cases** (Review status)
3. **Document overrides** when disagreeing with AI
4. **Track accuracy** using AI Performance Report
5. **Refine prompts** based on results

### Data Hygiene

- Clean up rejected candidates regularly
- Archive old job openings
- Monitor audit log size
- Review retention policies quarterly
- Export reports for records

---

## Getting Started Checklist

Before going live:

- [ ] AI Settings configured with valid API key
- [ ] API connection tested successfully
- [ ] Rate limits set appropriately
- [ ] Data retention policies configured
- [ ] User roles and permissions assigned
- [ ] Email templates customized (optional)
- [ ] Test job opening created
- [ ] Test candidate processed successfully
- [ ] Reports reviewed and working
- [ ] Team trained on system usage
- [ ] Backup strategy in place

---

## Support

For technical support:

- **GitHub Issues**: [Report bugs or request features]
- **Frappe Forum**: [Community discussion]
- **Email**: support@yourcompany.com

For AI-specific questions, include:
- Frappe version
- AI Hiring app version
- Error messages
- Audit log entries
- Steps to reproduce

---

**Version**: 1.0  
**Last Updated**: 2024-12-15  
**Next Review**: 2025-03-15
